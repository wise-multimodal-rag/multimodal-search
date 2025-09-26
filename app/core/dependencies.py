from functools import lru_cache
from app.clients.feature_extraction_client import FeatureExtractionClient
from app.clients.embedding_client import EmbeddingClient
from app.clients.llm_client import LLMClient
from app.services.opensearch_service import OpenSearchService
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
def get_search_service() -> SearchService:
    """Get singleton instance of SearchService with injected dependencies"""
    return SearchService(
        opensearch_service=get_opensearch_service(),
        llm_client=get_llm_client(),
        embedding_client=get_embedding_client(),
        feature_extraction_client=get_feature_extraction_client()
    )