from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TextFeatures(BaseModel):
    """Text modality feature extraction results"""

    keywords: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    classification: Optional[Dict[str, Any]] = None


class ImageFeatures(BaseModel):
    """Image modality feature extraction results"""

    caption: Optional[str] = None
    objects: Optional[List[Dict[str, Any]]] = None


class VideoFeatures(BaseModel):
    """Video modality feature extraction results"""

    keywords: Optional[List[Dict[str, Any]]] = None
    scenes: Optional[List[str]] = None
    objects: Optional[List[str]] = None
    activities: Optional[List[str]] = None
    description: Optional[str] = None


class AudioFeatures(BaseModel):
    """Audio modality feature extraction results"""

    keywords: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    sounds: Optional[List[str]] = None
    audio_type: Optional[str] = None
    transcription: Optional[str] = None


class MultimodalFeatures(BaseModel):
    """Complete multimodal feature extraction results"""

    text: Optional[TextFeatures] = None
    image: Optional[ImageFeatures] = None
    video: Optional[VideoFeatures] = None
    audio: Optional[AudioFeatures] = None
