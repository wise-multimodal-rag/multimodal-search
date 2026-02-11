"""의존성 주입을 위한 인터페이스/프로토콜 정의"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol


# =============================================================================
# LLM Client Interface
# =============================================================================

class LLMClientProtocol(Protocol):
    """LLM 클라이언트 인터페이스"""

    base_url: str

    async def complete(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.3,
            max_tokens: Optional[int] = None,
            force_json: bool = False,
            use_generation_model: bool = False,
    ) -> Optional[str]:
        """LLM 완성 요청"""
        ...

    async def analyze_query_intent(
            self, query: str, available_element_types: List[str], input_modalities: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """쿼리 의도 분석"""
        ...

    async def expand_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """쿼리 확장"""
        ...


# =============================================================================
# Embedding Client Interface
# =============================================================================

class EmbeddingClientProtocol(Protocol):
    """임베딩 클라이언트 인터페이스"""

    base_url: str

    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """텍스트 임베딩 생성"""
        ...

    async def get_image_embedding(self, image_data: bytes) -> Optional[List[float]]:
        """이미지 임베딩 생성"""
        ...

    async def get_video_embedding(self, video_data: bytes) -> Optional[List[float]]:
        """비디오 임베딩 생성"""
        ...

    async def get_audio_embedding(self, audio_data: bytes) -> Optional[List[float]]:
        """오디오 임베딩 생성"""
        ...

    async def detect_objects(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """객체 감지"""
        ...

    async def generate_image_caption(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """이미지 캡션 생성"""
        ...


# =============================================================================
# Feature Extraction Client Interface
# =============================================================================

class FeatureExtractionClientProtocol(Protocol):
    """특성 추출 클라이언트 인터페이스"""

    base_url: str

    async def extract_text_summary(
            self, text: str, max_length: int = 500, min_length: int = 100, use_keywords: bool = True
    ) -> Optional[Dict[str, Any]]:
        """텍스트 요약 추출"""
        ...

    async def extract_keywords(
            self, text: str, max_keywords: int = 10, include_scores: bool = True
    ) -> Optional[Dict[str, Any]]:
        """키워드 추출"""
        ...

    async def classify_text(self, text: str, top_k: int = 3) -> Optional[Dict[str, Any]]:
        """텍스트 분류"""
        ...

    async def extract_entities(
            self, text: str, entity_types: Optional[List[str]] = None, include_confidence: bool = True
    ) -> Optional[Dict[str, Any]]:
        """개체명 추출"""
        ...

    async def analyze_sentiment(self, text: str, detail_level: str = "simple") -> Optional[Dict[str, Any]]:
        """감정 분석"""
        ...

    async def extract_document_text(
            self, file_data: bytes, filename: str, content_type: str
    ) -> Optional[Dict[str, Any]]:
        """문서 텍스트 추출"""
        ...


# =============================================================================
# Search Service Interface
# =============================================================================

class SearchServiceProtocol(Protocol):
    """검색 서비스 인터페이스"""

    async def search_multimodal(
            self,
            text_query: Optional[str] = None,
            image: Optional[bytes] = None,
            video: Optional[bytes] = None,
            audio: Optional[bytes] = None,
            text_file: Optional[bytes] = None,
            max_results: int = 10,
            temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """멀티모달 검색"""
        ...

    async def search_multimodal_stream(
            self,
            text_query: Optional[str] = None,
            image: Optional[bytes] = None,
            video: Optional[bytes] = None,
            audio: Optional[bytes] = None,
            text_file: Optional[bytes] = None,
            max_results: int = 10,
            temperature: float = 0.7,
            max_retries: int = 2,
    ):
        """스트리밍 멀티모달 검색"""
        ...


# =============================================================================
# Answer Generation Service Interface
# =============================================================================

class AnswerGenerationServiceProtocol(Protocol):
    """답변 생성 서비스 인터페이스"""

    async def generate_answer(
            self,
            query: str,
            search_results: List[Dict[str, Any]],
            temperature: float = 0.7,
            max_retries: int = 2,
    ) -> Dict[str, Any]:
        """답변 생성"""
        ...

    async def generate_answer_stream(
            self,
            query: str,
            search_results: List[Dict[str, Any]],
            temperature: float = 0.7,
            max_retries: int = 2,
    ):
        """스트리밍 답변 생성"""
        ...


# =============================================================================
# Input Validator Interface
# =============================================================================

class InputValidatorProtocol(Protocol):
    """입력 검증기 인터페이스"""

    def validate_files(
            self,
            image: Optional[Any] = None,
            video: Optional[Any] = None,
            audio: Optional[Any] = None,
            text_file: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """파일 검증"""
        ...

    def validate_text_query(self, query: Optional[str]) -> str:
        """텍스트 쿼리 검증"""
        ...


# =============================================================================
# OpenSearch Service Interface
# =============================================================================

class OpenSearchServiceProtocol(Protocol):
    """OpenSearch 서비스 인터페이스"""

    client: Any
    elements_index: str

    async def initialize(self) -> None:
        """서비스 초기화"""
        ...

    async def close(self) -> None:
        """서비스 종료"""
        ...

    async def health_check(self) -> Dict[str, str]:
        """헬스 체크"""
        ...

    async def hybrid_search(
            self,
            query: str,
            vector_field: str,
            query_embedding: List[float],
            indices: List[str],
            element_type_weights: Optional[Dict[str, float]] = None,
            additional_filters: Optional[Dict[str, Any]] = None,
            size: int = 10,
    ) -> Dict[str, Any]:
        """하이브리드 검색"""
        ...


# =============================================================================
# Abstract Base Classes (for concrete implementations)
# =============================================================================

class LLMClientBase(ABC):
    """LLM 클라이언트 베이스 클래스"""

    @abstractmethod
    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        pass

    @abstractmethod
    async def analyze_query_intent(self, query: str, available_element_types: List[str], **kwargs) -> Optional[
        Dict[str, Any]]:
        pass


class EmbeddingClientBase(ABC):
    """임베딩 클라이언트 베이스 클래스"""

    @abstractmethod
    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        pass

    @abstractmethod
    async def get_image_embedding(self, image_data: bytes) -> Optional[List[float]]:
        pass


class SearchServiceBase(ABC):
    """검색 서비스 베이스 클래스"""

    @abstractmethod
    async def search_multimodal(self, **kwargs) -> Dict[str, Any]:
        pass
