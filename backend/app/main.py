import os
import sys

# Ensure parent directory of 'app' is in sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn

from app.database.connection import Base, engine
from app.api.routes import router

# Automatically create SQLAlchemy database tables (migration fallback for dev env)
try:
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")
except Exception as e:
    logger.error(f"Error during database initialization: {e}")

app = FastAPI(
    title="Business Research Agent API",
    description="Backend API for AI-Powered Business Research, discovery, verification, and streaming.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set up CORS middleware to allow communication with frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Business Research Agent API. Visit /docs for OpenAPI documentation."
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
