"""Search result data structures and types."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StandardSearchResult(BaseModel):
    """표준화된 검색 결과 구조"""
    results: List[Dict[str, Any]] = Field(
        description="검색된 결과 목록 (score 정보 포함)"
    )
    total_hits: int = Field(
        description="전체 검색 결과 수"
    )
    max_score: float = Field(
        description="최고 점수"
    )
    took_ms: int = Field(
        description="검색 소요 시간 (밀리초)"
    )


class SearchResultItem(BaseModel):
    """검색 결과 개별 아이템"""
    # Element 데이터 (모든 필드들이 포함됨)
    element_id: str
    chunk_id: str  
    media_id: str
    content: str
    modality: str
    element_type: str
    
    # 점수 정보
    score: float = Field(description="검색 점수")
    original_score: Optional[float] = Field(None, description="원본 점수")
    
    # 추가 메타데이터는 모델에 의해 자동 처리됨
    class Config:
        extra = "allow"  # 추가 필드 허용


