"""Business logic layer for the multimodal search application.

This package contains domain-specific business logic organized by:
- search: Search functionality and OpenSearch integration
- generation: Answer generation and streaming services
- processing: File processing and feature extraction
- embeddings: Embedding generation and management

Each domain is self-contained with its own services and utilities.
"""

from .embeddings import EmbeddingService
from .generation import AnswerGenerationService, MultimodalStreamService
from .processing import FilePreprocessingService, InputProcessor, MultimodalFeatureExtractor
from .search import (
    OpenSearchService,
    QueryAnalyzer,
    ResultEnricher,
    SearchExecutor,
    SearchService,
)

__all__ = [
    # Search domain
    "SearchService",
    "OpenSearchService",
    "QueryAnalyzer",
    "SearchExecutor",
    "ResultEnricher",
    # Generation domain
    "AnswerGenerationService",
    "MultimodalStreamService",
    # Processing domain
    "FilePreprocessingService",
    "InputProcessor",
    "MultimodalFeatureExtractor",
    # Embedding domain
    "EmbeddingService",
]