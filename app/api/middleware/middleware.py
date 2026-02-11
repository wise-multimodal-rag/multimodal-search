"""FastAPI application middleware and middleware configuration."""

from fastapi import FastAPI

from app.config.config import settings
from app.api.exceptions.handlers import EnhancedExceptionHandlerMiddleware


def configure_middleware(app: FastAPI) -> None:
    """Configure middleware for the FastAPI application."""
    # Add enhanced exception handling middleware
    app.add_middleware(
        EnhancedExceptionHandlerMiddleware,
        include_debug_info=settings.debug
    )


def configure_handlers(app: FastAPI) -> None:
    """Configure additional middleware for the FastAPI application."""
    # Global exception handling is managed by EnhancedExceptionHandlerMiddleware
    pass
