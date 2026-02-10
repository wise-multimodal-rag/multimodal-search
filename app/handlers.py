"""FastAPI application handlers and middleware configuration."""

from fastapi import FastAPI

from .config import settings
from .exceptions.handlers import EnhancedExceptionHandlerMiddleware


def configure_middleware(app: FastAPI) -> None:
    """Configure middleware for the FastAPI application."""
    # Add enhanced exception handling middleware
    app.add_middleware(
        EnhancedExceptionHandlerMiddleware,
        include_debug_info=settings.debug
    )


def configure_handlers(app: FastAPI) -> None:
    """Configure additional handlers for the FastAPI application."""
    # Global exception handling is managed by EnhancedExceptionHandlerMiddleware
    pass


def configure_cors(app: FastAPI) -> None:
    """Configure CORS settings."""
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )