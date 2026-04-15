# SyntaxStory: Giving your code a voice.

SyntaxStory turns codebases into chapter-based learning narratives using AI.

Near-term output is structured text tutorials. Later phases will add script generation for podcasts and video explainers where the narration references code shown on screen.

The name "SyntaxStory" captures the cognitive dissonance of programming: **Syntax** is rigid, logical, and unforgiving, while **Story** is human, warm, and engaging. The product promise is: *"We take the cold logic of your machine and give it a human heartbeat."*

---

## Foundation

### 1. The Core Value Proposition (The "Why")

- **The Problem:** Codebases are silent, intimidating, and difficult to understand; reading raw syntax at scale becomes overwhelming quickly.
- **The Solution:** **SyntaxStory** breathes life into code, turning static repositories into engaging multi-modal narratives (video, audio, text).
- **The Promise:** *Bridging the gap between logic and language.*

## Getting Started

### Backend setup (FastAPI)

From the project root:

1. Create and activate a virtual environment in `syntax`:
    ```bash
    python -m venv syntax/.venv
    # Windows
    .\syntax\.venv\Scripts\activate
    # Linux
    source .\syntax\.venv\Scripts\activate
    ```
2. Install dependencies:
   ```bash
   pip install -r syntax/requirements.txt
   ```
3. Run the API (from `syntax` directory):
    ```bash
    cd syntax
    fastapi dev

    # Fallback: 
    python -m uvicorn app.main:app --reload
    ```

The FastAPI CLI entrypoint is configured in `syntax/pyproject.toml`.

### Run tests

    ```bash
    cd syntax
    python -m pytest -q`
    ```


### Provider configuration

The app uses `syntax/storage/provider_config.json` as its live config store (gitignored — may contain API keys and local model choices).

On first run the file is **auto-generated** from hardcoded defaults. To start from a custom baseline:

```bash
cp syntax/storage/provider_config.template.json syntax/storage/provider_config.json
# Edit provider_config.json with your keys / preferred models
```

The committed template (`provider_config.template.json`) shows the full default shape with all secrets set to `null`.

### Health check endpoint

Once running, verify:

- `GET http://127.0.0.1:8000/api/health`
- Expected response: `{"status":"ok"}`

### Config endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/config/providers` | List all providers (secrets redacted) |
| `GET` | `/api/config/providers/{id}` | Single provider config |
| `PATCH` | `/api/config/provider` | Update model / base_url / api_key |
| `PUT` | `/api/config/provider/active` | Switch the active provider |
