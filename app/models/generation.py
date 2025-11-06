from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerationAttempt(BaseModel):
    """단일 답변 생성 시도 정보"""
    attempt: int = Field(description="시도 번호")
    draft_answer: str = Field(description="생성된 초안 답변")
    reflection: Dict[str, Any] = Field(description="Reflection 결과")
    is_acceptable: bool = Field(description="답변 수용 여부")
    improvement_suggestions: List[str] = Field(default_factory=list, description="개선 제안사항")


class SearchContext(BaseModel):
    """검색 컨텍스트 정보"""
    total_results: int = Field(description="총 검색 결과 수")
    element_types_used: List[str] = Field(description="사용된 요소 타입들")


class GenerationRequest(BaseModel):
    """답변 생성 요청"""
    text_query: str = Field(description="텍스트 검색 쿼리")
    image: Optional[Dict[str, Any]] = Field(default=None, description="이미지 파일 정보")
    video: Optional[Dict[str, Any]] = Field(default=None, description="비디오 파일 정보")
    audio: Optional[Dict[str, Any]] = Field(default=None, description="오디오 파일 정보")
    text_file: Optional[Dict[str, Any]] = Field(default=None, description="텍스트 파일 정보")
    include_chunk_meta: bool = Field(default=True, description="Chunk 메타데이터 포함 여부")
    include_media_meta: bool = Field(default=True, description="Media 메타데이터 포함 여부")
    max_results: int = Field(default=5, ge=1, le=100, description="최대 검색 결과 수")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="생성 온도")
    max_retries: int = Field(default=2, ge=0, le=5, description="재생성 최대 횟수")


class GenerationResponse(BaseModel):
    """답변 생성 응답"""
    success: bool = Field(description="생성 성공 여부")
    final_answer: Optional[str] = Field(description="최종 생성된 답변")
    query: str = Field(description="원본 검색 쿼리")
    total_attempts: int = Field(description="총 생성 시도 횟수")
    generation_attempts: List[GenerationAttempt] = Field(description="생성 시도별 상세 정보")
    search_context: SearchContext = Field(description="검색 컨텍스트 정보")
    error: Optional[str] = Field(default=None, description="오류 메시지")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    processing_time_ms: Optional[int] = Field(default=None, description="처리 시간(밀리초)")


class ReflectionScores(BaseModel):
    """Reflection 평가 점수"""
    accuracy: int = Field(ge=0, le=10, description="정확성 점수")
    completeness: int = Field(ge=0, le=10, description="완성도 점수")
    clarity: int = Field(ge=0, le=10, description="명확성 점수")
    structure: int = Field(ge=0, le=10, description="구조 점수")
    relevance: int = Field(ge=0, le=10, description="관련성 점수")


class ReflectionResult(BaseModel):
    """Reflection 결과"""
    scores: ReflectionScores = Field(description="평가 점수들")
    total_score: int = Field(description="총점")
    is_acceptable: bool = Field(description="수용 가능 여부")
    strengths: List[str] = Field(description="강점들")
    improvement_suggestions: List[str] = Field(description="개선 제안사항")
    overall_assessment: str = Field(description="전체 평가")