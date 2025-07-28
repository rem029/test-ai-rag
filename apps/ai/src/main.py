from fastapi import FastAPI
from dotenv import load_dotenv
from services.db import initialize_database
from routes.health import router as health_router
from routes.message import router as message_router
from routes.embed import router as embed_router

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

initialize_database()

# Include routers
app.include_router(health_router)
app.include_router(message_router)
app.include_router(embed_router)
