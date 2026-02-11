"""Base exception classes and error management system."""

from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


# =============================================================================
# Error Categories and Codes
# =============================================================================

class ErrorCategory(str, Enum):
    """에러 카테고리 분류"""
    VALIDATION = "VALIDATION"           # 입력 검증 에러
    AUTHENTICATION = "AUTHENTICATION"  # 인증 에러
    AUTHORIZATION = "AUTHORIZATION"    # 권한 에러
    NOT_FOUND = "NOT_FOUND"            # 리소스 없음
    EXTERNAL_API = "EXTERNAL_API"      # 외부 API 에러
    DEPENDENCY = "DEPENDENCY"          # 의존성 주입 에러
    BUSINESS_LOGIC = "BUSINESS_LOGIC"  # 비즈니스 로직 에러
    SYSTEM = "SYSTEM"                  # 시스템 에러
    UNKNOWN = "UNKNOWN"                # 알 수 없는 에러


class ErrorCode(str, Enum):
    """표준 에러 코드"""

    # Validation Errors (4xx)
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_PARAMETER_VALUE = "INVALID_PARAMETER_VALUE"

    # Authentication & Authorization Errors (4xx)
    INVALID_API_KEY = "INVALID_API_KEY"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Resource Errors (4xx)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"

    # External API Errors (5xx)
    EXTERNAL_API_UNAVAILABLE = "EXTERNAL_API_UNAVAILABLE"
    EXTERNAL_API_TIMEOUT = "EXTERNAL_API_TIMEOUT"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"

    # Dependency Injection Errors (5xx)
    SERVICE_NOT_REGISTERED = "SERVICE_NOT_REGISTERED"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    DEPENDENCY_RESOLUTION_FAILED = "DEPENDENCY_RESOLUTION_FAILED"

    # Business Logic Errors (4xx/5xx)
    SEARCH_FAILED = "SEARCH_FAILED"
    GENERATION_FAILED = "GENERATION_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"

    # System Errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# =============================================================================
# Base Exception Classes
# =============================================================================

class BaseAppException(Exception):
    """애플리케이션 기본 예외 클래스"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        category: ErrorCategory,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error": self.error_code.value,
            "category": self.category.value,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


# =============================================================================
# Specific Exception Classes
# =============================================================================

class ValidationException(BaseAppException):
    """입력 검증 예외"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_INPUT,
            category=ErrorCategory.VALIDATION,
            status_code=400,
            details=details,
            **kwargs
        )


class ExternalAPIException(BaseAppException):
    """외부 API 예외"""

    def __init__(self, service: str, message: str, **kwargs):
        details = kwargs.pop("details", {})
        details["service"] = service

        super().__init__(
            message=f"{service} API error: {message}",
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            category=ErrorCategory.EXTERNAL_API,
            status_code=503,
            details=details,
            **kwargs
        )


class DependencyException(BaseAppException):
    """의존성 주입 예외"""

    def __init__(self, message: str, service_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if service_type:
            details["service_type"] = service_type

        super().__init__(
            message=message,
            error_code=ErrorCode.DEPENDENCY_RESOLUTION_FAILED,
            category=ErrorCategory.DEPENDENCY,
            status_code=500,
            details=details,
            **kwargs
        )


class BusinessLogicException(BaseAppException):
    """비즈니스 로직 예외"""

    def __init__(self, message: str, operation: str, **kwargs):
        details = kwargs.pop("details", {})
        details["operation"] = operation

        super().__init__(
            message=f"{operation} failed: {message}",
            error_code=ErrorCode.SEARCH_FAILED,  # 기본값, 필요시 override
            category=ErrorCategory.BUSINESS_LOGIC,
            status_code=422,
            details=details,
            **kwargs
        )


class ResourceNotFoundException(BaseAppException):
    """리소스 없음 예외"""

    def __init__(self, resource_type: str, identifier: str, **kwargs):
        super().__init__(
            message=f"{resource_type} not found: {identifier}",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            category=ErrorCategory.NOT_FOUND,
            status_code=404,
            details={"resource_type": resource_type, "identifier": identifier},
            **kwargs
        )


# =============================================================================
# Error Response Builder
# =============================================================================

class ErrorResponseBuilder:
    """에러 응답 구조 표준화"""

    @staticmethod
    def build_error_response(
        error_code: str,
        message: str,
        status_code: int,
        category: str = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """표준 에러 응답 구조 생성"""
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "category": category,
                "message": message,
            },
            "status_code": status_code,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        if details:
            response["error"]["details"] = details

        if request_id:
            response["request_id"] = request_id

        return response

    @staticmethod
    def from_exception(
        exc: BaseAppException,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """예외 객체에서 에러 응답 생성"""
        return ErrorResponseBuilder.build_error_response(
            error_code=exc.error_code.value,
            message=exc.message,
            status_code=exc.status_code,
            category=exc.category.value,
            details=exc.details,
            request_id=request_id,
        )


# =============================================================================
# Exception Handler Decorators
# =============================================================================

def handle_external_api_errors(service_name: str):
    """외부 API 에러 처리 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise ExternalAPIException(
                    service=service_name,
                    message=str(e),
                    cause=e
                )
        return wrapper
    return decorator


def handle_business_logic_errors(operation: str):
    """비즈니스 로직 에러 처리 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseAppException:
                # 이미 처리된 예외는 다시 raise
                raise
            except Exception as e:
                raise BusinessLogicException(
                    message=str(e),
                    operation=operation,
                    cause=e
                )
        return wrapper
    return decorator