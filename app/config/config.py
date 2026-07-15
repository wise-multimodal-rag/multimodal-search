from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE_PATH), env_file_encoding="utf-8", extra="ignore")

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
    litellm_timeout: float = Field(default=180.0, alias="LITELLM_TIMEOUT")  # LLM API 타임아웃 (초)

    # Langfuse Configuration - Prompt Management
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")
    langfuse_enabled: bool = Field(default=True, alias="LANGFUSE_ENABLED")

    # Reranker Configuration (vLLM 직접 호출)
    reranker_enabled: bool = Field(default=True, alias="RERANKER_ENABLED")
    reranker_api_url: str = Field(default="", alias="RERANKER_API_URL")
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

    # Storage Configuration
    storage_path: str = Field(default="/storage", alias="STORAGE_PATH")

    @property
    def opensearch_url(self) -> str:
        protocol = "https" if self.opensearch_use_ssl else "http"
        return f"{protocol}://{self.opensearch_host}:{self.opensearch_port}"


settings = Settings()
