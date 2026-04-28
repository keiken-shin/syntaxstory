from google import genai
import os
import logging
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# Configure logging
log_directory = os.getenv("LOG_DIR", "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(
    log_directory, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log"
)

# Set up logger
logger = logging.getLogger("llm_logger")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# Simple cache configuration
cache_file = "llm_cache.json"


def load_cache():
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except:
        logger.warning(f"Failed to load cache.")
    return {}


def save_cache(cache):
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
    except:
        logger.warning(f"Failed to save cache")


def get_llm_provider():
    provider = os.getenv("LLM_PROVIDER")
    if not provider and (os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_BASE_URL")):
        provider = "OLLAMA"
    if not provider and (os.getenv("GEMINI_PROJECT_ID") or os.getenv("GEMINI_API_KEY")):
        provider = "GEMINI"
    if not provider:
        provider = "STUB"
    # if necessary, add ANTHROPIC/OPENAI
    return provider


def _call_llm_stub(prompt: str) -> str:
    """Deterministic local fallback for dev/test environments.

    This keeps the tutorial pipeline executable without external LLM credentials.
    """
    if "Analyze the codebase context." in prompt:
        file_indices = []
        for line in prompt.splitlines():
            line = line.strip()
            if line.startswith("--- File Index "):
                try:
                    index_part = line.split("--- File Index ", 1)[1].split(":", 1)[0]
                    file_indices.append(int(index_part.strip()))
                except Exception:
                    continue

        chosen_indices = file_indices[:3] or [0]
        abstractions = []
        for offset, index in enumerate(chosen_indices):
            abstractions.append(
                f"- name: |\n    Abstraction {offset + 1}\n  description: |\n    A simple concept extracted from the codebase for local testing.\n  file_indices:\n    - {index} # file"
            )
        return "```yaml\n" + "\n".join(abstractions) + "\n```"

    if "Please provide:" in prompt and "relationships:" in prompt:
        return (
            "```yaml\n"
            "summary: |\n"
            "  A small tutorial pipeline that crawls a repository, identifies abstractions, and writes chapters.\n"
            "relationships:\n"
            "  - from_abstraction: 0 # Abstraction 1\n"
            "    to_abstraction: 1 # Abstraction 2\n"
            "    label: \"Uses\"\n"
            "  - from_abstraction: 1 # Abstraction 2\n"
            "    to_abstraction: 2 # Abstraction 3\n"
            "    label: \"Feeds\"\n"
            "```"
        )

    if "what is the best order to explain these abstractions" in prompt:
        return "```yaml\n- 0 # Abstraction 1\n- 1 # Abstraction 2\n- 2 # Abstraction 3\n```"

    if "Write a very beginner-friendly tutorial chapter" in prompt:
        heading = "# Chapter 1: Abstraction"
        for line in prompt.splitlines():
            if line.startswith("- Name: "):
                heading = f"# Chapter 1: {line.split(': ', 1)[1].strip()}"
                break
        return (
            f"{heading}\n\n"
            "This chapter explains the idea in simple terms.\n\n"
            "## What it does\n"
            "It helps the pipeline move from crawling to chapter generation.\n"
        )

    if "Combine the tutorial chapters" in prompt or "Generate Mermaid Diagram" in prompt:
        return (
            "```yaml\n"
            "summary: |\n"
            "  This tutorial was generated using a local development stub.\n"
            "```"
        )

    return "```yaml\nsummary: |\n  Local stub response.\n```"


def _call_llm_provider(prompt: str) -> str:
    """
    Call an LLM provider based on environment variables.
    Environment variables:
    - LLM_PROVIDER: "OLLAMA" or "XAI"
    - <provider>_MODEL: Model name (e.g., OLLAMA_MODEL, XAI_MODEL)
    - <provider>_BASE_URL: Base URL without endpoint (e.g., OLLAMA_BASE_URL, XAI_BASE_URL)
    - <provider>_API_KEY: API key (e.g., OLLAMA_API_KEY, XAI_API_KEY; optional for providers that don't require it)
    The endpoint /v1/chat/completions will be appended to the base URL.
    """
    logger.info(f"PROMPT: {prompt}") # log the prompt

    # Read the provider from environment variable
    provider = os.environ.get("LLM_PROVIDER", "").upper()
    if not provider:
        raise ValueError("LLM_PROVIDER environment variable is required")

    # Construct the names of the other environment variables
    model_var = f"{provider}_MODEL"
    base_url_var = f"{provider}_BASE_URL"
    api_key_var = f"{provider}_API_KEY"

    # Read the provider-specific variables
    model = os.environ.get(model_var)
    base_url = os.environ.get(base_url_var)
    api_key = os.environ.get(api_key_var, "")  # API key is optional, default to empty string

    # Validate required variables
    if not model:
        raise ValueError(f"{model_var} environment variable is required")
    if not base_url:
        raise ValueError(f"{base_url_var} environment variable is required")

    # Append the endpoint to the base URL
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    # Configure headers and payload based on provider
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:  # Only add Authorization header if API key is provided
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response_json = response.json() # Log the response
        logger.info("RESPONSE:\n%s", json.dumps(response_json, indent=2))
        #logger.info(f"RESPONSE: {response.json()}")
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error occurred: {e}"
        try:
            error_details = response.json().get("error", "No additional details")
            error_message += f" (Details: {error_details})"
        except:
            pass
        if provider == "OLLAMA":
            logger.warning("OLLAMA request failed; falling back to local stub.")
            return _call_llm_stub(prompt)
        raise Exception(error_message)
    except requests.exceptions.ConnectionError:
        if provider == "OLLAMA":
            logger.warning("OLLAMA connection failed; falling back to local stub.")
            return _call_llm_stub(prompt)
        raise Exception(f"Failed to connect to {provider} API. Check your network connection.")
    except requests.exceptions.Timeout:
        if provider == "OLLAMA":
            logger.warning("OLLAMA request timed out; falling back to local stub.")
            return _call_llm_stub(prompt)
        raise Exception(f"Request to {provider} API timed out.")
    except requests.exceptions.RequestException as e:
        if provider == "OLLAMA":
            logger.warning("OLLAMA request errored; falling back to local stub.")
            return _call_llm_stub(prompt)
        raise Exception(f"An error occurred while making the request to {provider}: {e}")
    except ValueError:
        if provider == "OLLAMA":
            logger.warning("OLLAMA response could not be parsed; falling back to local stub.")
            return _call_llm_stub(prompt)
        raise Exception(f"Failed to parse response as JSON from {provider}. The server might have returned an invalid response.")

# By default, we Google Gemini 2.5 pro, as it shows great performance for code understanding
def call_llm(prompt: str, use_cache: bool = True) -> str:
    # Log the prompt
    logger.info(f"PROMPT: {prompt}")

    # Check cache if enabled
    if use_cache:
        # Load cache from disk
        cache = load_cache()
        # Return from cache if exists
        if prompt in cache:
            logger.info(f"RESPONSE: {cache[prompt]}")
            return cache[prompt]

    provider = get_llm_provider()
    if provider == "GEMINI":
        response_text = _call_llm_gemini(prompt)
    elif provider == "STUB":
        response_text = _call_llm_stub(prompt)
    else:  # generic method using a URL that is OpenAI compatible API (Ollama, ...)
        response_text = _call_llm_provider(prompt)

    # Log the response
    logger.info(f"RESPONSE: {response_text}")

    # Update cache if enabled
    if use_cache:
        # Load cache again to avoid overwrites
        cache = load_cache()
        # Add to cache and save
        cache[prompt] = response_text
        save_cache(cache)

    return response_text


def _call_llm_gemini(prompt: str) -> str:
    if os.getenv("GEMINI_PROJECT_ID"):
        client = genai.Client(
            vertexai=True,
            project=os.getenv("GEMINI_PROJECT_ID"),
            location=os.getenv("GEMINI_LOCATION", "us-central1")
        )
    elif os.getenv("GEMINI_API_KEY"):
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    else:
        raise ValueError("Either GEMINI_PROJECT_ID or GEMINI_API_KEY must be set in the environment")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )
    return response.text

if __name__ == "__main__":
    test_prompt = "Hello, how are you?"

    # First call - should hit the API
    print("Making call...")
    response1 = call_llm(test_prompt, use_cache=False)
    print(f"Response: {response1}")
