"""Custom exceptions and error handling middleware for the multimodal search application."""

import asyncio
import time
import traceback
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class MultimodalSearchException(Exception):
    """Base exception for multimodal search application."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or "MULTIMODAL_SEARCH_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class EmbeddingServiceException(MultimodalSearchException):
    """Exception raised when embedding service fails."""
    
    def __init__(self, message: str, service_type: str = "unknown", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EMBEDDING_SERVICE_ERROR", details)
        self.service_type = service_type


class SearchServiceException(MultimodalSearchException):
    """Exception raised when search service fails."""
    
    def __init__(self, message: str, search_type: str = "unknown", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SEARCH_SERVICE_ERROR", details)
        self.search_type = search_type


class ExternalAPIException(MultimodalSearchException):
    """Exception raised when external API calls fail."""
    
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EXTERNAL_API_ERROR", details)
        self.api_name = api_name
        self.status_code = status_code


class CircuitBreakerException(MultimodalSearchException):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, service_name: str):
        super().__init__(f"Circuit breaker is open for service: {service_name}", "CIRCUIT_BREAKER_OPEN")
        self.service_name = service_name


class CircuitBreaker:
    """Circuit breaker pattern implementation for external services."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker moving to HALF_OPEN state")
            else:
                raise CircuitBreakerException(func.__name__)
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RetryHandler:
    """Retry handler with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def retry(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(f"Function {func.__name__} failed after {self.max_retries + 1} attempts: {e}")
                    break
                
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        if last_exception:
            raise last_exception


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-raise HTTP exceptions (they're handled by FastAPI)
            raise
        except MultimodalSearchException as e:
            logger.error(f"Multimodal search error: {e.message}", extra={
                "error_code": e.error_code,
                "details": e.details,
                "path": request.url.path,
                "method": request.method
            })
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": e.error_code,
                    "message": e.message,
                    "details": e.details
                }
            )
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error: {str(e)}", extra={
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            })
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred"
                }
            )


# Global instances
retry_handler = RetryHandler()
embedding_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
search_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
llm_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=45)