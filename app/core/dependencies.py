from functools import lru_cache

from app.clients.embedding_client import EmbeddingClient
from app.clients.feature_extraction_client import FeatureExtractionClient
from app.clients.llm_client import LLMClient
from app.core.container import container
from app.core.validators import InputValidator
from app.services import (EmbeddingService, FilePreprocessingService, InputProcessor,
                          MultimodalFeatureExtractor, MultimodalStreamService,
                          OpenSearchService, QueryAnalyzer, ResultEnricher,
                          SearchExecutor, SearchService)
from app.services.generation import AnswerGenerationService


# DI 컨테이너 초기화
def _initialize_container():
    """DI 컨테이너에 모든 서비스 등록"""
    if container.is_registered(EmbeddingClient):
        return  # 이미 초기화됨
    
    # Clients
    container.register(EmbeddingClient)
    container.register(FeatureExtractionClient)
    container.register(LLMClient)
    
    # Core services
    container.register(InputValidator)
    
    # Services
    container.register(EmbeddingService)
    container.register(InputProcessor)
    container.register(MultimodalFeatureExtractor)
    container.register(QueryAnalyzer)
    container.register(OpenSearchService)
    container.register(ResultEnricher)
    container.register(SearchExecutor)
    container.register(SearchService)
    container.register(AnswerGenerationService)
    container.register(MultimodalStreamService)

# 컨테이너 초기화
_initialize_container()


@lru_cache()
def get_feature_extraction_client() -> FeatureExtractionClient:
    """Get singleton instance of FeatureExtractionClient"""
    return container.get(FeatureExtractionClient)


@lru_cache()
def get_embedding_client() -> EmbeddingClient:
    """Get singleton instance of EmbeddingClient"""
    return container.get(EmbeddingClient)


@lru_cache()
def get_llm_client() -> LLMClient:
    """Get singleton instance of LLMClient"""
    return container.get(LLMClient)


@lru_cache()
def get_input_validator() -> InputValidator:
    """Get singleton instance of InputValidator"""
    return container.get(InputValidator)


@lru_cache()
def get_opensearch_service() -> OpenSearchService:
    """Get singleton instance of OpenSearchService"""
    return container.get(OpenSearchService)




@lru_cache()
def get_search_service() -> SearchService:
    """Get singleton instance of SearchService with injected dependencies"""
    return container.get(SearchService)


@lru_cache()
def get_answer_generation_service() -> AnswerGenerationService:
    """Get singleton instance of AnswerGenerationService"""
    return container.get(AnswerGenerationService)


@lru_cache()
def get_multimodal_stream_service() -> MultimodalStreamService:
    """Get singleton instance of MultimodalStreamService"""
    return container.get(MultimodalStreamService)
