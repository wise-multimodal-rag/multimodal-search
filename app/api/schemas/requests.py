"""Request schemas for API endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """멀티모달 검색 요청 스키마"""

    text_query: Optional[str] = Field(default=None, description="텍스트 검색 쿼리")
    include_chunk_meta: bool = Field(default=True, description="Chunk 메타데이터 포함 여부")
    include_media_meta: bool = Field(default=True, description="Media 메타데이터 포함 여부")
    max_results: int = Field(default=10, ge=1, le=100, description="최대 결과 수")

    # File uploads are handled separately in FastAPI Form parameters


class HealthCheckRequest(BaseModel):
    """헬스 체크 요청 스키마"""

    check_external_apis: bool = Field(default=False, description="외부 API 상태 확인 여부")
    timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0, description="타임아웃 시간")


class ConfigRequest(BaseModel):
    """설정 요청 스키마"""

    include_features: bool = Field(default=True, description="기능 플래그 포함 여부")
    include_limits: bool = Field(default=True, description="제한사항 포함 여부")
    include_environment: bool = Field(default=False, description="환경 정보 포함 여부")