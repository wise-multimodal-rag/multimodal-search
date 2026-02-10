from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.api import config, generation, search
from app.handlers import configure_cors, configure_handlers, configure_middleware
from app.interfaces import get_opensearch_service
from app.schemas import ApiResponse, HealthCheckData, ResponseBuilder


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

# Configure application middleware and handlers
configure_middleware(app)
configure_handlers(app)
configure_cors(app)

# Get project root directory (parent of app directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Mount static files
static_dir = PROJECT_ROOT / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Setup templates
templates_dir = PROJECT_ROOT / "templates"
if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))
else:
    logger.warning(f"Templates directory not found: {templates_dir}")
    templates = None

# Include routers
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(generation.router, prefix="/api/v1", tags=["generation"])
app.include_router(config.router, prefix="/api/v1", tags=["config"])


# Global exception handling is now managed by EnhancedExceptionHandlerMiddleware


@app.get("/")
async def root():
    return {"message": "Multimodal Search API", "version": "0.1.0"}


@app.get("/health", response_model=ApiResponse[HealthCheckData])
async def health_check():
    opensearch_service = get_opensearch_service()
    opensearch_status = await opensearch_service.health_check()

    health_data = HealthCheckData(
        status="healthy",
        services={"opensearch": opensearch_status},
        version="0.2.0"
    )

    return ResponseBuilder.success(
        data=health_data,
        message="Health check completed successfully"
    )


@app.get("/health/external-apis", response_model=ApiResponse[HealthCheckData])
async def external_apis_health_check():
    """Check health of all external APIs."""
    import httpx

    from app.interfaces import (
        get_embedding_client,
        get_feature_extraction_client,
        get_llm_client,
    )

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
    overall_status = "healthy" if all_healthy else "degraded"

    health_data = HealthCheckData(
        status=overall_status,
        services=results,
        version="0.2.0"
    )

    return ResponseBuilder.success(
        data=health_data,
        message=f"External APIs health check completed - status: {overall_status}"
    )


@app.get("/search")
async def search_page(request: Request):
    if templates is None:
        return {"error": "Templates not available"}
    return templates.TemplateResponse("search.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    # Setup logging before starting uvicorn
    from app.utils.logging import setup_logging
    setup_logging()

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        # Disable uvicorn's default logging configuration
        log_config=None
    )
