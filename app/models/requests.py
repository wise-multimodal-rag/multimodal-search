from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import UploadFile


class MultimodalSearchRequest(BaseModel):
    # 텍스트 입력
    text_query: Optional[str] = Field(default=None, description="텍스트 검색 쿼리")
    
    # 멀티모달 입력은 multipart/form-data로 처리
    # image: Optional[UploadFile] = Field(default=None, description="이미지 파일")
    # video: Optional[UploadFile] = Field(default=None, description="비디오 파일") 
    # audio: Optional[UploadFile] = Field(default=None, description="오디오 파일")
    
    # 검색 옵션
    include_chunk_meta: bool = Field(default=True, description="Chunk 메타데이터 포함 여부")
    include_media_meta: bool = Field(default=True, description="Media 메타데이터 포함 여부")
    max_results: int = Field(default=10, ge=1, le=100, description="최대 결과 수")
    offset: int = Field(default=0, ge=0, description="결과 오프셋")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="추가 필터")




class FeatureExtractionRequest(BaseModel):
    query: str = Field(..., description="특징 추출할 쿼리")
    element_types: List[str] = Field(..., description="대상 element_type 목록")


class FeatureExtractionResponse(BaseModel):
    features: Dict[str, Any] = Field(..., description="추출된 특징")
    embeddings: Dict[str, List[float]] = Field(..., description="임베딩 벡터")
    processing_info: Dict[str, Any] = Field(..., description="처리 정보")