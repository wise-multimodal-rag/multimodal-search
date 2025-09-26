from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import search
from app.core.dependencies import get_opensearch_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("Starting multimodal search application")
    
    # Initialize OpenSearch connection
    opensearch_service = get_opensearch_service()
    await opensearch_service.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down multimodal search application")
    await opensearch_service.close()


app = FastAPI(
    title="Multimodal Search API",
    description="Multimodal search and RAG system using OpenSearch",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(search.router, prefix="/api/v1", tags=["search"])


@app.get("/")
async def root():
    return {"message": "Multimodal Search API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    opensearch_service = get_opensearch_service()
    return {"status": "healthy", "opensearch": await opensearch_service.health_check()}