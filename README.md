# Installation recommendation.

- pyenv
- python 3.10+

# Install models at root folder.

- create models folder at root
  ```
  /
  /apps
  */models*
  /...
  ```
- Installing model sample:

- `wget -P ./models https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/blob/main/nomic-embed-text-v1.5.Q4_K_M.gguf`
- `wget -P ./models https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/blob/main/qwen2.5-3b-instruct-q4_k_m.gguf`
- `wget -P ./models https://huggingface.co/moondream/moondream2-gguf/blob/main/moondream2-text-model-f16.gguf`

# To run apps/ai

1. `cd /apps/ai`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install fastapi uvicorn ollama python-dotenv psycopg2-binary httpx`
5. `uvicorn main:app --port 8000 --reload`

# Local environment:

### Podman for Ollama, Open Web UI and Postgres

### at project root

#### Docker

```
docker compose up -d
```

#### Podman

```
podman compose up -d
```

OR

```
# Create a shared pod
podman pod create --name ai-stack \
  -p 5433:5432 \
  -p 11434:11434 \
  -p 3000:8080

# Run PostgreSQL with pgvector
podman run -d \
  --name pgvector \
  --pod ai-stack \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=123 \
  -e POSTGRES_DB=postgres \
  -v pgvector-data:/var/lib/postgresql/data \
  docker.io/pgvector/pgvector:pg16

# Run Ollama
podman run -d \
  --name ollama \
  --pod ai-stack \
  -e OLLAMA_HOST=0.0.0.0 \
  -v ollama:/root/.ollama \
  docker.io/ollama/ollama:latest serve

# Run Open WebUI
podman run -d \
  --name open-webui \
  --pod ai-stack \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main

```
