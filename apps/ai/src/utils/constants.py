from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5454"),
    "database": os.getenv("POSTGRES_DB", "vectordb"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "123"),
}

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
