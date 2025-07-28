# AI RAG Application

This application consists of:

- PostgreSQL with pgvector extension
- Ollama for local LLM hosting
- Open WebUI for chat interface
- Python FastAPI application for AI processing

## Environment Variables

The application uses the following environment variables defined in `.env`:

- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `PG_PORT`: PostgreSQL port (default: 5432)
- `OLLAMA_PORT`: Ollama service port (default: 11434)
- `WEBUI_PORT`: Open WebUI port (default: 3000)
- `AI_APP_PORT`: Python AI application port (default: 8000)

## Running the Application

1. Ensure you have Docker and Docker Compose installed
2. Create/update the `.env` file with your desired configuration
3. Run the application:

```bash
docker-compose up -d
```

## Services

- **PostgreSQL + pgvector**: Database with vector extension - `localhost:${PG_PORT}`
- **Ollama**: Local LLM server - `localhost:${OLLAMA_PORT}`
- **Open WebUI**: Web interface for chat - `localhost:${WEBUI_PORT}`
- **AI App**: Python FastAPI application - `localhost:${AI_APP_PORT}`

## Health Checks

The AI application includes a health check endpoint at `/health` that can be used to verify the service is running properly.

## Development

The Python application is located in `apps/ai/` and includes:

- FastAPI web framework
- Ollama client for LLM integration
- PostgreSQL integration with psycopg2
- Docker containerization with Ubuntu base image
