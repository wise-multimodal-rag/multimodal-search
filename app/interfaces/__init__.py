"""Interface and dependency injection layer.

This package provides:
- Protocol definitions for service interfaces
- Dependency injection container and injector
- Service abstractions for testing and modularity
"""

from .container import DIContainer, container
from .injector import (
    AnswerGenerationServiceDep,
    DependencyRegistry,
    EmbeddingClientDep,
    FeatureExtractionClientDep,
    InputValidatorDep,
    LLMClientDep,
    MultimodalStreamServiceDep,
    OpenSearchServiceDep,
    SearchServiceDep,
    get_answer_generation_service,
    get_embedding_client,
    get_feature_extraction_client,
    get_input_validator,
    get_llm_client,
    get_multimodal_stream_service,
    get_opensearch_service,
    get_search_service,
    override_dependencies,
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
    "DependencyRegistry",
    "get_llm_client",
    "get_embedding_client",
    "get_feature_extraction_client",
    "get_input_validator",
    "get_opensearch_service",
    "get_search_service",
    "get_answer_generation_service",
    "get_multimodal_stream_service",
    "override_dependencies",
    # FastAPI Dependencies
    "LLMClientDep",
    "EmbeddingClientDep",
    "FeatureExtractionClientDep",
    "InputValidatorDep",
    "OpenSearchServiceDep",
    "SearchServiceDep",
    "AnswerGenerationServiceDep",
    "MultimodalStreamServiceDep",
]