from fastapi import FastAPI
from dotenv import load_dotenv
from utils.constants import OLLAMA_HOST
from services.db import initialize_database
from routes.health import router as health_router
from routes.message import router as message_router
from routes.embed import router as embed_router

import httpx

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()


async def test_ollama_connection():
    """Test Ollama connection using httpx"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                print(
                    "✅ Ollama connected! Available models:\n"
                )
                for model in models:
                    print(f"{model}")   
                print("\n")             
                return True
            else:
                print("❌ Ollama API returned status")
                print(f"{response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print(f"   Trying to connect to: {OLLAMA_HOST}/api/tags")
        return False


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting application...")
    initialize_database()
    await test_ollama_connection()
    print("✅ Startup complete!")


# Include routers
app.include_router(health_router)
app.include_router(message_router)
app.include_router(embed_router)
