from fastapi import FastAPI
from dotenv import load_dotenv
from services.clients import check_model
from services.db import initialize_database
from routes.health import router as health_router
from routes.message import router as message_router
from routes.embed import router as embed_router

import httpx

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()


async def test_model_server_connection():
    """Test connection to OpenAI-compatible model server"""
    print("🔗 Testing model server connection...")

    for model_name in ["main", "embed"]:
        ok = await check_model(model_name)
        if ok:
            print(f"✅ {model_name.capitalize()} model server connected!")
        else:
            print(f"❌ {model_name.capitalize()} model server connection failed!")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting application...")
    initialize_database()
    await test_model_server_connection()
    print("✅ Startup complete!")


# Include routers
app.include_router(health_router)
app.include_router(message_router)
app.include_router(embed_router)
