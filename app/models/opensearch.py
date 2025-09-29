from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MediaMeta(BaseModel):
    media_id: str
    media_type: str  # video|audio|image|document|web|other
    mime_type: str
    title: Optional[str] = None
    source_uri: str
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    width_pixels: Optional[int] = None
    height_pixels: Optional[int] = None
    language_primary: Optional[str] = None
    chunk_count: Optional[int] = None
    element_count: Optional[int] = None
    metadata_flat: Optional[Dict[str, Any]] = None
    owner: Optional[str] = None
    visibility: Optional[str] = None  # public|internal|restricted
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChunkMeta(BaseModel):
    chunk_id: str
    media_id: str
    chunk_seq: int
    chunk_type: str  # overview|section|scene|figure|table|paragraph|clip
    modality_set: List[str]  # ["text","image","video","audio","table"]
    element_count: int
    label: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class QualityScores(BaseModel):
    extraction_confidence: Optional[float] = None
    content_quality: Optional[float] = None
    structural_importance: Optional[float] = None
    completeness: Optional[float] = None
    combined_static: Optional[float] = None


class Embeddings(BaseModel):
    text: Optional[List[float]] = None
    image: Optional[List[float]] = None
    video: Optional[List[float]] = None
    audio: Optional[List[float]] = None


class Element(BaseModel):
    element_id: str
    chunk_id: str
    media_id: str
    description: Optional[str] = None
    modality: str  # text|image|video|audio
    element_type: str  # summary|stt|caption|ocr|paragraph|table|chart|...
    content_type: str  # plain|uri|json|markdown|...
    content: str
    embeddings: Optional[Embeddings] = None
    quality_scores: Optional[QualityScores] = None
    element_seq: Optional[int] = None
    language: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SearchResult(BaseModel):
    element: Element
    chunk_meta: Optional[ChunkMeta] = None
    media_meta: Optional[MediaMeta] = None
    score: float


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    max_score: float
    results: List[SearchResult]
    took_ms: int
    element_types_used: List[str]
    query_analysis: Optional[Dict[str, Any]] = None