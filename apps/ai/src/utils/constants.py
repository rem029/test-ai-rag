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

MODEL_PORT = {
    "main": os.getenv("PORT_MODEL_MM", "http://localhost:9001"),
    "embed": os.getenv("PORT_MODEL_EMBED", "http://localhost:9002"),
}
