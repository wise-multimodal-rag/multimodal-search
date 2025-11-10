from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenSearch Configuration
    opensearch_host: str = Field(default="localhost", alias="OPENSEARCH_HOST")
    opensearch_port: int = Field(default=9200, alias="OPENSEARCH_PORT")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_USE_SSL")
    opensearch_verify_certs: bool = Field(default=False, alias="OPENSEARCH_VERIFY_CERTS")
    opensearch_username: str = Field(default="admin", alias="OPENSEARCH_USERNAME")
    opensearch_password: str = Field(default="admin", alias="OPENSEARCH_PASSWORD")

    # OpenSearch Index Configuration
    opensearch_media_index: str = Field(default="multimodal_rag_media", alias="OPENSEARCH_MEDIA_INDEX")
    opensearch_chunk_index: str = Field(default="multimodal_rag_chunk", alias="OPENSEARCH_CHUNK_INDEX")
    opensearch_elements_index: str = Field(default="multimodal_rag_element", alias="OPENSEARCH_ELEMENTS_INDEX")

    # External API Configuration
    embedding_api_url: str = Field(default="http://localhost:8001", alias="EMBEDDING_API_URL")
    feature_extraction_api_url: str = Field(default="http://localhost:8002", alias="FEATURE_EXTRACTION_API_URL")
    multimodal_api_key: str = Field(default="your-api-key-here", alias="MULTIMODAL_API_KEY")

    # LiteLLM Configuration - Query Analysis & Processing
    litellm_url: str = Field(default="http://localhost:4000", alias="LITELLM_URL")
    litellm_api_key: str = Field(default="your-api-key", alias="LITELLM_API_KEY")
    litellm_model: str = Field(default="gpt-3.5-turbo", alias="LITELLM_MODEL")

    # LiteLLM Configuration - Generation
    litellm_generation_model: str = Field(default="claude-3-5-sonnet-20241022", alias="LITELLM_GENERATION_MODEL")

    # Application Configuration
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    # Storage Configuration
    storage_path: str = Field(default="/storage", alias="STORAGE_PATH")

    @property
    def opensearch_url(self) -> str:
        protocol = "https" if self.opensearch_use_ssl else "http"
        return f"{protocol}://{self.opensearch_host}:{self.opensearch_port}"


class WeightingConfig(BaseSettings):
    """
    검색 가중치 설정을 중앙화하는 설정 클래스
    
    멀티모달 검색 시스템의 모든 가중치 설정을 관리합니다.
    가중치는 검색 결과의 관련성과 우선순위를 결정하는 핵심 요소입니다.
    
    모든 가중치는 환경변수로 설정 가능하며, 기본값이 제공됩니다.
    자세한 설명과 예시는 README.md의 '가중치 시스템' 섹션을 참조하세요.
    
    주요 개념:
    - 쿼리별 가중치: 확장된 쿼리들의 중요도 조절 (1.0 → 0.9 → 0.8...)
    - Element Type 가중치: 콘텐츠 타입별 중요도 (origin=1.0, paragraph=0.8...)
    - 동적 계산: 쿼리 내용에 따라 가중치 자동 조정
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="WEIGHT_", extra="ignore")

    # === 쿼리별 가중치 설정 ===
    query_weight_decay: float = Field(default=0.1, alias="WEIGHT_QUERY_DECAY")  # 각 쿼리마다 감소할 가중치 (1.0 → 0.9 → 0.8...)

    # === Element Type별 기본 가중치 ===
    paragraph_default: float = Field(default=0.8, alias="WEIGHT_PARAGRAPH_DEFAULT")  # 일반 문단 기본 가중치
    summary_default: float = Field(default=0.6, alias="WEIGHT_SUMMARY_DEFAULT")  # AI 요약문 기본 가중치
    caption_default: float = Field(default=0.3, alias="WEIGHT_CAPTION_DEFAULT")  # 이미지 캡션 기본 가중치
    origin_default: float = Field(default=1.0, alias="WEIGHT_ORIGIN_DEFAULT")  # 원본 이미지 기본 가중치

    @property
    def DEFAULT_ELEMENT_WEIGHTS(self) -> Dict[str, float]:
        return {
            "paragraph": self.paragraph_default,
            "summary": self.summary_default,
            "caption": self.caption_default,
            "origin": self.origin_default,
        }

    @property
    def QUERY_WEIGHT_DECAY(self) -> float:
        return self.query_weight_decay

    # === 텍스트 분석 동적 가중치 계산 ===
    text_summary_base_weight: float = Field(default=0.8, alias="WEIGHT_TEXT_SUMMARY_BASE")  # 요약 키워드 감지 시 기본 가중치
    text_summary_boost: float = Field(default=0.1, alias="WEIGHT_TEXT_SUMMARY_BOOST")  # 요약 키워드 개수당 추가 가중치
    text_paragraph_base_weight: float = Field(default=0.7, alias="WEIGHT_TEXT_PARAGRAPH_BASE")  # 문단 기본 가중치 (요약 우선 시)
    text_paragraph_penalty: float = Field(default=0.1, alias="WEIGHT_TEXT_PARAGRAPH_PENALTY")  # 요약 우선 시 문단 가중치 감소량
    text_min_weight: float = Field(default=0.4, alias="WEIGHT_TEXT_MIN")  # 텍스트 가중치 최소값

    # === 텍스트 폴백 가중치 (키워드 없을 때) ===
    text_paragraph_default: float = Field(default=0.8, alias="WEIGHT_TEXT_PARAGRAPH_DEFAULT")  # 문단 폴백 가중치
    text_summary_default: float = Field(default=0.6, alias="WEIGHT_TEXT_SUMMARY_DEFAULT")  # 요약 폴백 가중치

    # === 이미지 분석 동적 가중치 계산 ===
    image_origin_weight: float = Field(default=1.0, alias="WEIGHT_IMAGE_ORIGIN")  # 원본 이미지 고정 가중치 (항상 최우선)
    image_caption_base_weight: float = Field(default=0.3, alias="WEIGHT_IMAGE_CAPTION_BASE")  # 캡션 기본 가중치
    image_caption_boost: float = Field(default=0.05, alias="WEIGHT_IMAGE_CAPTION_BOOST")  # 캡션 키워드 개수당 추가 가중치
    image_caption_max_weight: float = Field(default=0.4, alias="WEIGHT_IMAGE_CAPTION_MAX")  # 캡션 최대 가중치
    image_caption_min_weight: float = Field(default=0.2, alias="WEIGHT_IMAGE_CAPTION_MIN")  # 캡션 최소 가중치 (이미지 쿼리 시)

    # === 전체 시스템 기본값 ===
    universal_default_weight: float = Field(default=0.6, alias="WEIGHT_UNIVERSAL_DEFAULT")  # 모달리티 정보 없을 때 기본 가중치
    opensearch_default_weight: float = Field(default=1.0, alias="WEIGHT_OPENSEARCH_DEFAULT")  # OpenSearch 기본 가중치

    # === 우선순위 분류 임계값 ===
    high_priority_threshold: float = Field(default=0.8, alias="WEIGHT_HIGH_PRIORITY_THRESHOLD")  # 높은 우선순위 임계값 (≥0.8)
    medium_priority_threshold: float = Field(default=0.5,
                                             alias="WEIGHT_MEDIUM_PRIORITY_THRESHOLD")  # 중간 우선순위 임계값 (0.5~0.8)
    low_priority_threshold: float = Field(default=0.0, alias="WEIGHT_LOW_PRIORITY_THRESHOLD")  # 낮은 우선순위 임계값 (>0.0)

    # === Modality Boost 설정 ===
    modality_boost_min_multiplier: float = Field(default=0.5, alias="WEIGHT_MODALITY_BOOST_MIN")  # 최소 boost 배수 (0.5배)
    modality_boost_max_multiplier: float = Field(default=2.0, alias="WEIGHT_MODALITY_BOOST_MAX")  # 최대 boost 배수 (2.0배)
    modality_boost_range: float = Field(default=1.5, alias="WEIGHT_MODALITY_BOOST_RANGE")  # boost 범위 (max - min = 1.5)

    # Property 기존 상수명 호환성 유지
    @property
    def TEXT_SUMMARY_BASE_WEIGHT(self) -> float:
        return self.text_summary_base_weight

    @property
    def TEXT_SUMMARY_BOOST(self) -> float:
        return self.text_summary_boost

    @property
    def TEXT_PARAGRAPH_BASE_WEIGHT(self) -> float:
        return self.text_paragraph_base_weight

    @property
    def TEXT_PARAGRAPH_PENALTY(self) -> float:
        return self.text_paragraph_penalty

    @property
    def TEXT_MIN_WEIGHT(self) -> float:
        return self.text_min_weight

    @property
    def TEXT_PARAGRAPH_DEFAULT(self) -> float:
        return self.text_paragraph_default

    @property
    def TEXT_SUMMARY_DEFAULT(self) -> float:
        return self.text_summary_default

    @property
    def IMAGE_ORIGIN_WEIGHT(self) -> float:
        return self.image_origin_weight

    @property
    def IMAGE_CAPTION_BASE_WEIGHT(self) -> float:
        return self.image_caption_base_weight

    @property
    def IMAGE_CAPTION_BOOST(self) -> float:
        return self.image_caption_boost

    @property
    def IMAGE_CAPTION_MAX_WEIGHT(self) -> float:
        return self.image_caption_max_weight

    @property
    def IMAGE_CAPTION_MIN_WEIGHT(self) -> float:
        return self.image_caption_min_weight

    @property
    def UNIVERSAL_DEFAULT_WEIGHT(self) -> float:
        return self.universal_default_weight

    @property
    def OPENSEARCH_DEFAULT_WEIGHT(self) -> float:
        return self.opensearch_default_weight

    @property
    def HIGH_PRIORITY_THRESHOLD(self) -> float:
        return self.high_priority_threshold

    @property
    def MEDIUM_PRIORITY_THRESHOLD(self) -> float:
        return self.medium_priority_threshold

    @property
    def LOW_PRIORITY_THRESHOLD(self) -> float:
        return self.low_priority_threshold

    @property
    def MODALITY_BOOST_MIN_MULTIPLIER(self) -> float:
        return self.modality_boost_min_multiplier

    @property
    def MODALITY_BOOST_MAX_MULTIPLIER(self) -> float:
        return self.modality_boost_max_multiplier

    @property
    def MODALITY_BOOST_RANGE(self) -> float:
        return self.modality_boost_range

    @property
    def MODALITY_FALLBACK_WEIGHTS(self) -> Dict[str, Dict[str, float]]:
        return {
            "text": {
                "paragraph": self.text_paragraph_default,
                "summary": 0.5,  # 기본값 사용
            },
            "image": {
                "origin": self.image_origin_weight,
                "caption": self.image_caption_base_weight,
            }
        }


settings = Settings()
weighting_config = WeightingConfig()
