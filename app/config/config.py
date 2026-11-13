from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


# 비어 있으면 기동 시 경고한다. 리랭커 · Langfuse · 이미지 프록시는 선택이라 빠진다.
REQUIRED_API_SETTINGS = (
    "EMBEDDING_API_URL", "EMBEDDING_API_EMBED_PATH", "EMBEDDING_API_CAPTION_PATH",
    "FEATURE_EXTRACTION_API_URL", "FEATURE_API_SUMMARY_PATH", "FEATURE_API_KEYWORD_PATH", "FEATURE_API_ENTITIES_PATH",
    "MULTIMODAL_API_KEY_HEADER", "LITELLM_URL", "LITELLM_CHAT_PATH", "LITELLM_MODEL", "LITELLM_GENERATION_MODEL",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE_PATH), env_file_encoding="utf-8", extra="ignore",
                                      env_ignore_empty=True)  # 빈 값(KEY=)은 아래 기본값을 쓴다

    # OpenSearch Configuration
    opensearch_host: str = Field(default="localhost", alias="OPENSEARCH_HOST")
    opensearch_port: int = Field(default=9200, alias="OPENSEARCH_PORT")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_USE_SSL")
    opensearch_verify_certs: bool = Field(default=False, alias="OPENSEARCH_VERIFY_CERTS")
    opensearch_username: str = Field(default="", alias="OPENSEARCH_USERNAME")
    opensearch_password: str = Field(default="", alias="OPENSEARCH_PASSWORD")

    # OpenSearch Index Configuration
    opensearch_media_index: str = Field(default="multimodal_rag_media", alias="OPENSEARCH_MEDIA_INDEX")
    opensearch_chunk_index: str = Field(default="multimodal_rag_chunk", alias="OPENSEARCH_CHUNK_INDEX")
    opensearch_elements_index: str = Field(default="multimodal_rag_element", alias="OPENSEARCH_ELEMENTS_INDEX")

    # External API Configuration — 주소 · 경로 · 인증 헤더는 전부 외부에서 주입한다(코드 기본값 없음)
    embedding_api_url: str = Field(default="", alias="EMBEDDING_API_URL")
    embedding_api_embed_path: str = Field(default="", alias="EMBEDDING_API_EMBED_PATH")
    embedding_api_caption_path: str = Field(default="", alias="EMBEDDING_API_CAPTION_PATH")
    feature_extraction_api_url: str = Field(default="", alias="FEATURE_EXTRACTION_API_URL")
    feature_api_summary_path: str = Field(default="", alias="FEATURE_API_SUMMARY_PATH")
    feature_api_keyword_path: str = Field(default="", alias="FEATURE_API_KEYWORD_PATH")
    feature_api_entities_path: str = Field(default="", alias="FEATURE_API_ENTITIES_PATH")
    multimodal_api_key: str = Field(default="", alias="MULTIMODAL_API_KEY")
    multimodal_api_key_header: str = Field(default="", alias="MULTIMODAL_API_KEY_HEADER")  # 키를 담을 헤더 이름

    # LiteLLM Configuration - Query Analysis & Processing
    litellm_url: str = Field(default="", alias="LITELLM_URL")
    litellm_chat_path: str = Field(default="", alias="LITELLM_CHAT_PATH")
    litellm_api_key: str = Field(default="", alias="LITELLM_API_KEY")
    litellm_model: str = Field(default="", alias="LITELLM_MODEL")

    # LiteLLM Configuration - Generation
    litellm_generation_model: str = Field(default="", alias="LITELLM_GENERATION_MODEL")
    litellm_timeout: float = Field(default=180.0, alias="LITELLM_TIMEOUT")  # LLM API 타임아웃 (초)

    # Langfuse Configuration - Prompt Management
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="", alias="LANGFUSE_HOST")
    langfuse_enabled: bool = Field(default=True, alias="LANGFUSE_ENABLED")

    # Reranker Configuration (vLLM 직접 호출)
    reranker_enabled: bool = Field(default=True, alias="RERANKER_ENABLED")
    reranker_api_url: str = Field(default="", alias="RERANKER_API_URL")
    reranker_classify_path: str = Field(default="", alias="RERANKER_CLASSIFY_PATH")
    reranker_model: str = Field(default="", alias="RERANKER_MODEL")  # 비우면 서버 기본 모델
    reranker_timeout: float = Field(default=5.0, alias="RERANKER_TIMEOUT")
    reranker_top_k: int = Field(default=20, alias="RERANKER_TOP_K")
    reranker_weight: float = Field(default=0.7, alias="RERANKER_WEIGHT")
    reranker_oversample: int = Field(default=3, alias="RERANKER_OVERSAMPLE")
    reranker_modality_boost: bool = Field(default=True, alias="RERANKER_MODALITY_BOOST")

    # Application Configuration
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    # 이미지 경로(origins/...)만 있는 검색 결과를 미리보기할 프록시 주소. 비우면 미리보기 생략
    image_proxy_url: str = Field(default="", alias="IMAGE_PROXY_URL")

    # Storage Configuration
    storage_path: str = Field(default="/storage", alias="STORAGE_PATH")

    def missing_api_settings(self) -> list[str]:
        """검색·생성에 꼭 필요한데 비어 있는 외부 API 설정 이름(기동 시 경고용)."""
        return [n for n in REQUIRED_API_SETTINGS if not getattr(self, n.lower())]

    @property
    def opensearch_url(self) -> str:
        protocol = "https" if self.opensearch_use_ssl else "http"
        return f"{protocol}://{self.opensearch_host}:{self.opensearch_port}"


settings = Settings()
