from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.api.routes import search
from app.core.config import settings
from app.core.dependencies import get_opensearch_service
from app.core.exceptions import ExceptionHandlerMiddleware
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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

# Add exception handling middleware
app.add_middleware(ExceptionHandlerMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(search.router, prefix="/api/v1", tags=["search"])


# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {type(exc).__name__}: {exc}")
    logger.error(f"Request: {request.method} {request.url}")
    if hasattr(request, "body") and request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            body_str = body.decode("utf-8")
            # If body is too long (likely contains base64), just show size
            if len(body_str) > 1000:
                logger.error(f"Request body size: {len(body_str)} bytes (truncated)")
            else:
                logger.error(f"Request body: {body_str}")
        except:
            logger.error("Could not read request body")
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(exc)}"})


@app.get("/")
async def root():
    return {"message": "Multimodal Search API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    opensearch_service = get_opensearch_service()
    return {"status": "healthy", "opensearch": await opensearch_service.health_check()}


@app.get("/health/external-apis")
async def external_apis_health_check():
    """Check health of all external APIs."""
    import httpx

    from app.core.dependencies import get_embedding_client, get_feature_extraction_client, get_llm_client

    results = {}

    # Check embedding API
    try:
        embedding_client = get_embedding_client()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{embedding_client.base_url}/health")
            results["embedding_api"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000 if response.elapsed else 0,
            }
    except Exception as e:
        results["embedding_api"] = {"status": "unhealthy", "error": str(e)}

    # Check feature extraction API
    try:
        feature_client = get_feature_extraction_client()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{feature_client.base_url}/health")
            results["feature_extraction_api"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000 if response.elapsed else 0,
            }
    except Exception as e:
        results["feature_extraction_api"] = {"status": "unhealthy", "error": str(e)}

    # Check LLM API
    try:
        llm_client = get_llm_client()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{llm_client.base_url}/health")
            results["llm_api"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000 if response.elapsed else 0,
            }
    except Exception as e:
        results["llm_api"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(result.get("status") == "healthy" for result in results.values())

    return {"status": "healthy" if all_healthy else "degraded", "external_apis": results}


@app.get("/search")
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})
