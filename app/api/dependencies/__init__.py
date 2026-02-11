"""Interface and dependency injection layer.

This package provides:
- Protocol definitions for service dependencies
- Dependency injection container and injector
- Service abstractions for testing and modularity
"""

from .container import DIContainer, container
from .injector import (
    AnswerGenerationService,
    EmbeddingClient,
    FeatureExtractionClient,
    InputValidator,
    LLMClient,
    MultimodalStreamService,
    OpenSearchService,
    SearchService,
    get_answer_generation_service,
    get_embedding_client,
    get_feature_extraction_client,
    get_input_validator,
    get_llm_client,
    get_multimodal_stream_service,
    get_opensearch_service,
    get_search_service,
)
from .protocols import (
    AnswerGenerationServiceProtocol,
    EmbeddingClientProtocol,
    FeatureExtractionClientProtocol,
    InputValidatorProtocol,
    LLMClientProtocol,
    OpenSearchServiceProtocol,
    SearchServiceProtocol,
)

__all__ = [
    # Protocols
    "LLMClientProtocol",
    "EmbeddingClientProtocol",
    "FeatureExtractionClientProtocol",
    "InputValidatorProtocol",
    "OpenSearchServiceProtocol",
    "SearchServiceProtocol",
    "AnswerGenerationServiceProtocol",
    # Container
    "DIContainer",
    "container",
    # Registry and Injector
    "get_llm_client",
    "get_embedding_client",
    "get_feature_extraction_client",
    "get_input_validator",
    "get_opensearch_service",
    "get_search_service",
    "get_answer_generation_service",
    "get_multimodal_stream_service",
    # FastAPI Dependencies
    "LLMClient",
    "EmbeddingClient",
    "FeatureExtractionClient",
    "InputValidator",
    "OpenSearchService",
    "SearchService",
    "AnswerGenerationService",
    "MultimodalStreamService",
]