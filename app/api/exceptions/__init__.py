"""Exception handling system for multimodal search application.

This module provides a centralized exception handling system with:
- Base exception classes
- Service-specific exceptions
- Exception middleware and middleware
- Error response formatting
"""

from .base import (
    BaseAppException,
    BusinessLogicException,
    DependencyException,
    ErrorCategory,
    ErrorCode,
    ErrorResponseBuilder,
    ExternalAPIException,
    ResourceNotFoundException,
    ValidationException,
)
from .handlers import EnhancedExceptionHandlerMiddleware
from .service import (
    AnalysisException,
    EmbeddingException,
    GenerationException,
    SearchException,
)

__all__ = [
    # Base exceptions
    "BaseAppException",
    "ValidationException",
    "ExternalAPIException",
    "DependencyException",
    "BusinessLogicException",
    "ResourceNotFoundException",
    # Enums
    "ErrorCategory",
    "ErrorCode",
    # Utilities
    "ErrorResponseBuilder",
    # Handlers
    "EnhancedExceptionHandlerMiddleware",
    # Service exceptions
    "SearchException",
    "GenerationException",
    "EmbeddingException",
    "AnalysisException",
]