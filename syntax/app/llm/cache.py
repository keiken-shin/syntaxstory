import json
import logging
import os
from pathlib import Path
from app.llm.providers.base import LLMProvider, GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)

CACHE_FILE = Path("storage/llm_cache.json")

def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load LLM cache: {e}")
    return {}

def save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save LLM cache: {e}")

def cached_generate(provider: LLMProvider, request: GenerateRequest) -> GenerateResponse:
    prompt = request.prompt
    
    # Try retrieving a model property safely
    model_val = "default_model"
    if request.model:
        model_val = request.model
    elif hasattr(provider, 'config') and hasattr(provider.config, 'model'):
        model_val = provider.config.model
        
    cache_key = f"{provider.provider_id}::{model_val}::{prompt}"
    
    cache = load_cache()
    if cache_key in cache:
        logger.info(f"LLM Cache hit for {provider.provider_id} ({model_val})!")
        return GenerateResponse(
            provider=provider.provider_id,
            content=cache[cache_key]
        )
        
    logger.info(f"LLM Cache miss for {provider.provider_id} ({model_val}). Calling provider...")
    response = provider.generate(request)
    
    if response and response.content and "stub" not in response.content.lower():
        # Load fresh before save
        cache = load_cache()
        cache[cache_key] = response.content
        save_cache(cache)
        
    return response