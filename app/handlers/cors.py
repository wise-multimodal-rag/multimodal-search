"""CORS configuration for the FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings


def configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI application."""
    # Default CORS origins for development and production
    cors_origins = ["*"] if settings.debug else [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )