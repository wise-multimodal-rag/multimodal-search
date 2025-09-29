from functools import lru_cache

from app.clients.embedding_client import EmbeddingClient
from app.clients.feature_extraction_client import FeatureExtractionClient
from app.clients.llm_client import LLMClient
from app.services.embedding_service import EmbeddingService
from app.services.input_processor import InputProcessor
from app.services.multimodal_feature_extractor import MultimodalFeatureExtractor
from app.services.opensearch_service import OpenSearchService
from app.services.query_analyzer import QueryAnalyzer
from app.services.result_enricher import ResultEnricher
from app.services.search_service import SearchService


@lru_cache()
def get_feature_extraction_client() -> FeatureExtractionClient:
    """Get singleton instance of FeatureExtractionClient"""
    return FeatureExtractionClient()


@lru_cache()
def get_embedding_client() -> EmbeddingClient:
    """Get singleton instance of EmbeddingClient"""
    return EmbeddingClient()


@lru_cache()
def get_llm_client() -> LLMClient:
    """Get singleton instance of LLMClient"""
    return LLMClient()


@lru_cache()
def get_opensearch_service() -> OpenSearchService:
    """Get singleton instance of OpenSearchService"""
    return OpenSearchService()


@lru_cache()
def get_input_processor() -> InputProcessor:
    """Get singleton instance of InputProcessor"""
    return InputProcessor()


@lru_cache()
def get_multimodal_feature_extractor() -> MultimodalFeatureExtractor:
    """Get singleton instance of MultimodalFeatureExtractor"""
    return MultimodalFeatureExtractor(
        feature_extraction_client=get_feature_extraction_client(),
        llm_client=get_llm_client()
    )


@lru_cache()
def get_query_analyzer() -> QueryAnalyzer:
    """Get singleton instance of QueryAnalyzer"""
    return QueryAnalyzer(llm_client=get_llm_client())


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get singleton instance of EmbeddingService"""
    return EmbeddingService(embedding_client=get_embedding_client())


@lru_cache()
def get_result_enricher() -> ResultEnricher:
    """Get singleton instance of ResultEnricher"""
    return ResultEnricher(opensearch_service=get_opensearch_service())


@lru_cache()
def get_search_service() -> SearchService:
    """Get singleton instance of SearchService with injected dependencies"""
    return SearchService(
        opensearch_service=get_opensearch_service(),
        input_processor=get_input_processor(),
        feature_extractor=get_multimodal_feature_extractor(),
        query_analyzer=get_query_analyzer(),
        embedding_service=get_embedding_service(),
        result_enricher=get_result_enricher()
    )
