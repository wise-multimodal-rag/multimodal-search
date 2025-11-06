"""Custom exceptions and error handling middleware for the multimodal search application."""

import traceback

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handling middleware."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-raise HTTP exceptions (they're handled by FastAPI)
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(
                f"Unexpected error: {str(e)}",
                extra={"path": request.url.path, "method": request.method, "traceback": traceback.format_exc()},
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"},
            )

