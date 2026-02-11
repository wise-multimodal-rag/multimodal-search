"""Pydantic schemas for multimodal search application.

This module contains all Pydantic models used for:
- Request validation
- Response formatting
- Data serialization
- API documentation
"""

from .common import (
    ApiResponse,
    GenerationResponseData,
    HealthCheckData,
    PaginatedResponse,
    PaginationInfo,
    ResponseBuilder,
    ResponseMetadata,
    ResponseStatus,
    StreamResponse,
    standard_response,
)
from .features import (
    AudioFeatures,
    ImageFeatures,
    MultimodalFeatures,
    TextFeatures,
    VideoFeatures,
)
from .generation import (
    GenerationAttempt,
    GenerationRequest,
    GenerationResponse,
    ReflectionResult,
    ReflectionScores,
    SearchContext,
)
from .requests import (
    ConfigRequest,
    HealthCheckRequest,
    SearchRequest,
)
from .search import (
    ChunkMeta,
    Element,
    Embeddings,
    MediaMeta,
    QualityScores,
    SearchResponse,
    SearchResult,
)

__all__ = [
    # Common response models
    "ApiResponse",
    "GenerationResponseData",
    "PaginatedResponse",
    "StreamResponse",
    "ResponseBuilder",
    "ResponseStatus",
    "ResponseMetadata",
    "PaginationInfo",
    "HealthCheckData",
    "standard_response",
    # Search models
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "Element",
    "ChunkMeta",
    "MediaMeta",
    "Embeddings",
    "QualityScores",
    # Generation models
    "GenerationRequest",
    "GenerationResponse",
    "GenerationAttempt",
    "SearchContext",
    "ReflectionResult",
    "ReflectionScores",
    # Feature models
    "MultimodalFeatures",
    "TextFeatures",
    "ImageFeatures",
    "VideoFeatures",
    "AudioFeatures",
    # Request models
    "ConfigRequest",
    "HealthCheckRequest",
]