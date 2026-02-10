"""Application constants and configuration values."""

from typing import Dict

# Application Information
APP_NAME = "Multimodal Search API"
APP_VERSION = "0.2.0"
APP_DESCRIPTION = "Multimodal search and RAG system using OpenSearch"

# API Configuration
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# File Upload Limits (in bytes)
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_VIDEO_SIZE = 20 * 1024 * 1024  # 20MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024  # 20MB
MAX_DOCUMENT_SIZE = 512 * 1024 * 1024  # 512MB

# Supported File Types
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
SUPPORTED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/avi", "video/mov"]
SUPPORTED_AUDIO_TYPES = ["audio/mp3", "audio/wav", "audio/ogg", "audio/m4a"]
SUPPORTED_TEXT_TYPES = [
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

# Search Configuration
DEFAULT_MAX_RESULTS = 10
MAX_ALLOWED_RESULTS = 100
MIN_ALLOWED_RESULTS = 1

# Generation Configuration
DEFAULT_TEMPERATURE = 0.7
MAX_TEMPERATURE = 2.0
MIN_TEMPERATURE = 0.0
DEFAULT_MAX_RETRIES = 2
MAX_ALLOWED_RETRIES = 5

# OpenSearch Index Names
OPENSEARCH_MEDIA_INDEX = "multimodal_rag_media"
OPENSEARCH_CHUNK_INDEX = "multimodal_rag_chunk"
OPENSEARCH_ELEMENTS_INDEX = "multimodal_rag_element"

# Timeouts (in seconds)
DEFAULT_HTTP_TIMEOUT = 30.0
EXTERNAL_API_TIMEOUT = 60.0
HEALTH_CHECK_TIMEOUT = 5.0

# Feature Flags
FEATURES: Dict[str, bool] = {
    "multimodal_search": True,
    "answer_generation": True,
    "streaming_responses": True,
    "file_upload": True,
    "search_history": True,
    "analytics": False,
    "experimental_features": False,
}

# Error Messages
ERROR_MESSAGES: Dict[str, str] = {
    "file_too_large": "File size exceeds maximum allowed limit",
    "unsupported_file_type": "File type is not supported",
    "invalid_query": "Query is invalid or empty",
    "search_failed": "Search operation failed",
    "generation_failed": "Answer generation failed",
    "external_api_error": "External API is unavailable",
}

# Logging Configuration
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
LOG_LEVELS = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]

# Cache Configuration
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_SIZE = 1000

# Rate Limiting
RATE_LIMIT_PER_MINUTE = 60
BURST_LIMIT = 10
