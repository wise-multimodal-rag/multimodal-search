"""Exception handlers and middleware for the multimodal search application."""

import traceback
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from .base import BaseAppException, ErrorResponseBuilder


class EnhancedExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """향상된 글로벌 예외 처리 미들웨어"""

    def __init__(self, app, include_debug_info: bool = False):
        super().__init__(app)
        self.include_debug_info = include_debug_info

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except BaseAppException as exc:
            # 커스텀 애플리케이션 예외 처리
            return await self._handle_app_exception(exc, request)
        except HTTPException as exc:
            # FastAPI HTTPException 처리
            return await self._handle_http_exception(exc, request)
        except Exception as exc:
            # 예상하지 못한 예외 처리
            return await self._handle_unexpected_exception(exc, request)

    async def _handle_app_exception(
        self, exc: BaseAppException, request: Request
    ) -> JSONResponse:
        """애플리케이션 예외 처리"""
        request_id = getattr(request.state, "request_id", None)

        # 로그 레벨 결정 (4xx는 warning, 5xx는 error)
        log_level = "warning" if exc.status_code < 500 else "error"
        logger_method = getattr(logger, log_level)

        logger_method(
            f"{exc.category.value} Exception: {exc.message}",
            extra={
                "error_code": exc.error_code.value,
                "category": exc.category.value,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details,
                "request_id": request_id,
            }
        )

        error_response = ErrorResponseBuilder.from_exception(exc, request_id)

        if self.include_debug_info and exc.cause:
            error_response["error"]["debug"] = {
                "cause": str(exc.cause),
                "traceback": traceback.format_exception(
                    type(exc.cause), exc.cause, exc.cause.__traceback__
                )[-3:]  # 마지막 3줄만 포함
            }

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )

    async def _handle_http_exception(
        self, exc: HTTPException, request: Request
    ) -> JSONResponse:
        """HTTP 예외 처리"""
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            f"HTTP Exception: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "request_id": request_id,
            }
        )

        error_response = ErrorResponseBuilder.build_error_response(
            error_code="HTTP_ERROR",
            message=exc.detail,
            status_code=exc.status_code,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )

    async def _handle_unexpected_exception(
        self, exc: Exception, request: Request
    ) -> JSONResponse:
        """예상하지 못한 예외 처리"""
        request_id = getattr(request.state, "request_id", None)

        # 더 자세한 디버깅을 위해 traceback을 직접 출력
        full_traceback = traceback.format_exc()
        logger.error(f"Unexpected Exception: {str(exc)}")
        logger.error(f"Full traceback:\n{full_traceback}")
        logger.error(f"Request: {request.method} {request.url.path}")
        logger.error(f"Request ID: {request_id}")

        error_response = ErrorResponseBuilder.build_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred" if not self.include_debug_info else str(exc),
            status_code=500,
            category="SYSTEM",
            request_id=request_id,
        )

        if self.include_debug_info:
            error_response["error"]["debug"] = {
                "traceback": traceback.format_exc().split('\n')[-5:]  # 마지막 5줄
            }

        return JSONResponse(
            status_code=500,
            content=error_response
        )


# =============================================================================
# Legacy Exception Handler (기존 호환성)
# =============================================================================

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
                status_code=500,
                content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"},
            )


# =============================================================================
# Exception Handler Functions
# =============================================================================

async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """검증 예외 처리 함수"""
    from .base import ValidationException

    if isinstance(exc, ValidationException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponseBuilder.from_exception(exc)
        )

    # 일반 검증 오류 처리
    return JSONResponse(
        status_code=422,
        content=ErrorResponseBuilder.build_error_response(
            error_code="VALIDATION_ERROR",
            message=str(exc),
            status_code=422,
            category="VALIDATION"
        )
    )


async def external_api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """외부 API 예외 처리 함수"""
    from .base import ExternalAPIException

    if isinstance(exc, ExternalAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponseBuilder.from_exception(exc)
        )

    # 일반 외부 API 오류 처리
    return JSONResponse(
        status_code=503,
        content=ErrorResponseBuilder.build_error_response(
            error_code="EXTERNAL_API_ERROR",
            message=str(exc),
            status_code=503,
            category="EXTERNAL_API"
        )
    )