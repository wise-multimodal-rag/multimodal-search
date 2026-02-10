"""공통 응답 모델 및 표준화된 응답 구조"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field


# =============================================================================
# Response Status and Metadata
# =============================================================================

class ResponseStatus(str, Enum):
    """API 응답 상태"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"  # 일부만 성공
    FAILURE = "failure"
    ERROR = "error"


class ResponseMetadata(BaseModel):
    """응답 메타데이터"""

    # 타이밍 정보
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="응답 생성 시간 (UTC)")
    processing_time_ms: Optional[int] = Field(default=None, description="처리 시간 (밀리초)")

    # 요청 정보
    request_id: Optional[str] = Field(default=None, description="요청 ID (추적용)")
    api_version: str = Field(default="v1", description="API 버전")

    # 성능 정보
    cache_hit: Optional[bool] = Field(default=None, description="캐시 히트 여부")
    external_api_calls: Optional[int] = Field(default=None, description="외부 API 호출 횟수")

    # 디버그 정보 (개발/디버그 모드에서만)
    debug_info: Optional[Dict[str, Any]] = Field(default=None, description="디버그 정보")


class PaginationInfo(BaseModel):
    """페이지네이션 정보"""

    page: int = Field(ge=1, description="현재 페이지 번호")
    page_size: int = Field(ge=1, le=1000, description="페이지 크기")
    total_items: int = Field(ge=0, description="전체 항목 수")
    total_pages: int = Field(ge=0, description="전체 페이지 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")
    has_previous: bool = Field(description="이전 페이지 존재 여부")


# =============================================================================
# Generic Response Wrappers
# =============================================================================

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """표준 API 응답 래퍼"""

    # 핵심 응답 정보
    success: bool = Field(description="요청 처리 성공 여부")
    status: ResponseStatus = Field(description="상세 응답 상태")
    message: Optional[str] = Field(default=None, description="응답 메시지 또는 설명")

    # 실제 데이터
    data: Optional[T] = Field(default=None, description="응답 데이터")

    # 메타데이터
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata, description="응답 메타데이터")

    # 오류 정보 (실패 시)
    error: Optional[Dict[str, Any]] = Field(default=None, description="오류 정보")

    # 경고 정보
    warnings: Optional[List[str]] = Field(default=None, description="경고 메시지들")


class PaginatedResponse(ApiResponse[List[T]]):
    """페이지네이션이 적용된 응답"""

    pagination: Optional[PaginationInfo] = Field(default=None, description="페이지네이션 정보")


class StreamResponse(BaseModel):
    """스트리밍 응답용 개별 이벤트"""

    event_type: str = Field(description="이벤트 타입")
    event_id: Optional[str] = Field(default=None, description="이벤트 ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="이벤트 발생 시간")
    data: Dict[str, Any] = Field(description="이벤트 데이터")
    is_final: bool = Field(default=False, description="최종 이벤트 여부")


# =============================================================================
# Specific Response Models (기존 모델들과 호환)
# =============================================================================

class SearchResponseData(BaseModel):
    """검색 응답 데이터 (기존 SearchResponse 내용)"""

    query: str = Field(description="검색 쿼리")
    total_hits: int = Field(ge=0, description="전체 히트 수")
    max_score: float = Field(ge=0.0, description="최대 스코어")
    results: List[Any] = Field(description="검색 결과들")  # SearchResult 타입은 기존 유지
    took_ms: int = Field(ge=0, description="검색 소요 시간")
    element_types_used: List[str] = Field(description="사용된 요소 타입들")
    query_analysis: Optional[Dict[str, Any]] = Field(default=None, description="쿼리 분석 결과")


class GenerationResponseData(BaseModel):
    """답변 생성 응답 데이터 (기존 GenerationResponse 내용)"""

    final_answer: Optional[str] = Field(description="최종 생성된 답변")
    query: str = Field(description="원본 검색 쿼리")
    total_attempts: int = Field(ge=1, description="총 생성 시도 횟수")
    generation_attempts: List[Any] = Field(description="생성 시도별 상세 정보")  # GenerationAttempt
    search_context: Dict[str, Any] = Field(description="검색 컨텍스트 정보")


class HealthCheckData(BaseModel):
    """헬스 체크 응답 데이터"""

    status: str = Field(description="전체 상태")
    services: Dict[str, Dict[str, Any]] = Field(description="서비스별 상태")
    uptime_seconds: Optional[float] = Field(default=None, description="업타임 (초)")
    version: Optional[str] = Field(default=None, description="애플리케이션 버전")


# =============================================================================
# Response Builder Utilities
# =============================================================================

class ResponseBuilder:
    """표준 응답 생성 유틸리티"""

    @staticmethod
    def success(
        data: T,
        message: Optional[str] = None,
        metadata: Optional[ResponseMetadata] = None,
        warnings: Optional[List[str]] = None
    ) -> ApiResponse[T]:
        """성공 응답 생성"""
        return ApiResponse[T](
            success=True,
            status=ResponseStatus.SUCCESS,
            message=message or "Request completed successfully",
            data=data,
            metadata=metadata or ResponseMetadata(),
            warnings=warnings
        )

    @staticmethod
    def partial_success(
        data: T,
        message: str,
        warnings: List[str],
        metadata: Optional[ResponseMetadata] = None
    ) -> ApiResponse[T]:
        """부분 성공 응답 생성"""
        return ApiResponse[T](
            success=True,
            status=ResponseStatus.PARTIAL_SUCCESS,
            message=message,
            data=data,
            metadata=metadata or ResponseMetadata(),
            warnings=warnings
        )

    @staticmethod
    def failure(
        message: str,
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[ResponseMetadata] = None
    ) -> ApiResponse[None]:
        """실패 응답 생성"""
        return ApiResponse[None](
            success=False,
            status=ResponseStatus.FAILURE,
            message=message,
            data=None,
            metadata=metadata or ResponseMetadata(),
            error=error_details
        )

    @staticmethod
    def error(
        message: str,
        error_details: Dict[str, Any],
        metadata: Optional[ResponseMetadata] = None
    ) -> ApiResponse[None]:
        """에러 응답 생성"""
        return ApiResponse[None](
            success=False,
            status=ResponseStatus.ERROR,
            message=message,
            data=None,
            metadata=metadata or ResponseMetadata(),
            error=error_details
        )

    @staticmethod
    def paginated(
        data: List[T],
        pagination: PaginationInfo,
        message: Optional[str] = None,
        metadata: Optional[ResponseMetadata] = None
    ) -> PaginatedResponse[T]:
        """페이지네이션 응답 생성"""
        return PaginatedResponse[T](
            success=True,
            status=ResponseStatus.SUCCESS,
            message=message or "Request completed successfully",
            data=data,
            metadata=metadata or ResponseMetadata(),
            pagination=pagination
        )


# =============================================================================
# Response Decorators
# =============================================================================

def standard_response(
    message: Optional[str] = None,
    include_processing_time: bool = True
):
    """표준 응답 형식 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 메타데이터 생성
                metadata = ResponseMetadata()
                if include_processing_time:
                    metadata.processing_time_ms = int((time.time() - start_time) * 1000)

                # 이미 ApiResponse인 경우 그대로 반환
                if isinstance(result, ApiResponse):
                    if include_processing_time and not result.metadata.processing_time_ms:
                        result.metadata.processing_time_ms = metadata.processing_time_ms
                    return result

                # 일반 데이터인 경우 래핑
                return ResponseBuilder.success(
                    data=result,
                    message=message,
                    metadata=metadata
                )

            except Exception as e:
                # 에러 발생 시 에러 응답 생성
                metadata = ResponseMetadata()
                if include_processing_time:
                    metadata.processing_time_ms = int((time.time() - start_time) * 1000)

                return ResponseBuilder.error(
                    message=f"Request failed: {str(e)}",
                    error_details={"exception_type": type(e).__name__, "details": str(e)},
                    metadata=metadata
                )

        return wrapper
    return decorator


# =============================================================================
# Backward Compatibility
# =============================================================================

# 기존 모델들과의 호환성을 위한 타입 별칭
SearchResponse = ApiResponse[SearchResponseData]
GenerationResponse = ApiResponse[GenerationResponseData]
HealthCheckResponse = ApiResponse[HealthCheckData]