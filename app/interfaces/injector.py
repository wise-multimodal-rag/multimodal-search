"""FastAPI와 통합된 의존성 주입 시스템"""

import os
from typing import Any, Dict, Type, TypeVar

from fastapi import Depends

from app.clients.embedding_client import EmbeddingClient
from app.clients.feature_extraction_client import FeatureExtractionClient
from app.clients.llm_client import LLMClient
from app.interfaces.container import container
from app.interfaces.protocols import (
    AnswerGenerationServiceProtocol,
    EmbeddingClientProtocol,
    FeatureExtractionClientProtocol,
    InputValidatorProtocol,
    LLMClientProtocol,
    OpenSearchServiceProtocol,
    SearchServiceProtocol,
)
from app.utils.validation import InputValidator
from app.src.embeddings import EmbeddingService
from app.src.processing import (
    FilePreprocessingService,
    InputProcessor,
    MultimodalFeatureExtractor,
)
from app.src.generation import AnswerGenerationService, MultimodalStreamService
from app.src.search import (
    OpenSearchService,
    QueryAnalyzer,
    ResultEnricher,
    SearchExecutor,
    SearchService,
)

T = TypeVar('T')


class DependencyRegistry:
    """의존성 레지스트리 - 프로덕션/테스트 구현 분리"""

    def __init__(self):
        self._overrides: Dict[Type, Any] = {}
        self._initialized = False

    def override_dependency(self, interface: Type[T], implementation: T) -> None:
        """의존성 오버라이드 (주로 테스트용)"""
        self._overrides[interface] = implementation

    def clear_overrides(self) -> None:
        """모든 오버라이드 제거"""
        self._overrides.clear()

    def get_implementation(self, interface: Type[T]) -> T:
        """인터페이스에 대한 구현체 반환"""
        # 오버라이드가 있는 경우 우선 사용
        if interface in self._overrides:
            return self._overrides[interface]

        # 프로덕션 구현체 반환
        return container.get(interface)

    def initialize_dependencies(self) -> None:
        """의존성 초기화 (한 번만 실행)"""
        if self._initialized:
            return

        # 기존 컨테이너에 인터페이스 매핑 등록
        # 클라이언트들
        container.register(LLMClientProtocol, LLMClient)
        container.register(EmbeddingClientProtocol, EmbeddingClient)
        container.register(FeatureExtractionClientProtocol, FeatureExtractionClient)

        # 서비스들
        container.register(InputValidatorProtocol, InputValidator)
        container.register(OpenSearchServiceProtocol, OpenSearchService)
        container.register(SearchServiceProtocol, SearchService)
        container.register(AnswerGenerationServiceProtocol, AnswerGenerationService)

        # 구체 클래스들도 계속 지원 (기존 호환성)
        container.register(LLMClient)
        container.register(EmbeddingClient)
        container.register(FeatureExtractionClient)
        container.register(InputValidator)
        container.register(OpenSearchService)
        container.register(SearchService)
        container.register(AnswerGenerationService)
        container.register(MultimodalStreamService)

        # 기타 서비스들
        container.register(EmbeddingService)
        container.register(InputProcessor)
        container.register(MultimodalFeatureExtractor)
        container.register(QueryAnalyzer)
        container.register(ResultEnricher)
        container.register(SearchExecutor)
        container.register(FilePreprocessingService)

        self._initialized = True


# 글로벌 레지스트리
_registry = DependencyRegistry()


# =============================================================================
# FastAPI Dependency Providers (인터페이스 기반)
# =============================================================================

def get_llm_client() -> LLMClientProtocol:
    """LLM 클라이언트 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(LLMClientProtocol)


def get_embedding_client() -> EmbeddingClientProtocol:
    """임베딩 클라이언트 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(EmbeddingClientProtocol)


def get_feature_extraction_client() -> FeatureExtractionClientProtocol:
    """특성 추출 클라이언트 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(FeatureExtractionClientProtocol)


def get_input_validator() -> InputValidatorProtocol:
    """입력 검증기 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(InputValidatorProtocol)


def get_opensearch_service() -> OpenSearchServiceProtocol:
    """OpenSearch 서비스 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(OpenSearchServiceProtocol)


def get_search_service() -> SearchServiceProtocol:
    """검색 서비스 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(SearchServiceProtocol)


def get_answer_generation_service() -> AnswerGenerationServiceProtocol:
    """답변 생성 서비스 의존성 제공"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(AnswerGenerationServiceProtocol)


def get_multimodal_stream_service() -> MultimodalStreamService:
    """멀티모달 스트림 서비스 의존성 제공 (아직 인터페이스 미적용)"""
    _registry.initialize_dependencies()
    return _registry.get_implementation(MultimodalStreamService)


# =============================================================================
# FastAPI Dependencies (Depends()와 함께 사용)
# =============================================================================

# 인터페이스 기반 의존성들
LLMClientDep = Depends(get_llm_client)
EmbeddingClientDep = Depends(get_embedding_client)
FeatureExtractionClientDep = Depends(get_feature_extraction_client)
InputValidatorDep = Depends(get_input_validator)
OpenSearchServiceDep = Depends(get_opensearch_service)
SearchServiceDep = Depends(get_search_service)
AnswerGenerationServiceDep = Depends(get_answer_generation_service)
MultimodalStreamServiceDep = Depends(get_multimodal_stream_service)


# =============================================================================
# Testing Support
# =============================================================================

class DependencyOverrideContext:
    """의존성 오버라이드 컨텍스트 매니저 (테스트용)"""

    def __init__(self, overrides: Dict[Type, Any]):
        self.overrides = overrides

    def __enter__(self):
        """Context manager entry point"""
        for interface, implementation in self.overrides.items():
            _registry.override_dependency(interface, implementation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point"""
        _registry.clear_overrides()


def override_dependencies(**overrides) -> DependencyOverrideContext:
    """의존성 오버라이드 헬퍼 함수

    사용 예:
    ```python
    with override_dependencies(
        LLMClientProtocol=MockLLMClient(),
        SearchServiceProtocol=MockSearchService()
    ):
        # 테스트 코드
        pass
    ```
    """
    return DependencyOverrideContext(overrides)


# =============================================================================
# Environment-based Configuration
# =============================================================================

def get_environment() -> str:
    """현재 환경 반환 (test/development/production)"""
    return os.getenv("ENVIRONMENT", "development").lower()


def is_testing() -> bool:
    """테스트 환경 여부 확인"""
    return get_environment() == "test"


def configure_for_testing():
    """테스트 환경 설정"""
    _registry.clear_overrides()


# =============================================================================
# Health Check Dependencies
# =============================================================================

async def health_check_dependencies() -> Dict[str, str]:
    """모든 의존성 헬스 체크"""
    results = {}

    try:
        opensearch_service = get_opensearch_service()
        results["opensearch"] = await opensearch_service.health_check()
    except Exception as e:
        results["opensearch"] = {"status": "unhealthy", "error": str(e)}

    # 추가 헬스 체크가 필요한 경우 여기에 추가

    return results


# 초기화 실행
_registry.initialize_dependencies()
