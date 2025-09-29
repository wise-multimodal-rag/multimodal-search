from typing import Optional, List, Dict, Any
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

    def get_all_keywords(self) -> List[Dict[str, Any]]:
        """Get all keywords from all modalities"""
        all_keywords = []
        
        for feature in [self.text, self.video, self.audio]:
            if feature and hasattr(feature, 'keywords') and feature.keywords:
                all_keywords.extend(feature.keywords)
                
        return all_keywords

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Get all entities from all modalities"""
        all_entities = []
        
        for feature in [self.text, self.audio]:
            if feature and hasattr(feature, 'entities') and feature.entities:
                all_entities.extend(feature.entities)
                
        return all_entities

    def has_any_features(self) -> bool:
        """Check if any features were extracted"""
        return any([
            self.text and any([self.text.keywords, self.text.entities, self.text.summary, self.text.classification]),
            self.image and any([self.image.caption, self.image.objects]),
            self.video and any([self.video.keywords, self.video.scenes, self.video.objects, self.video.activities, self.video.description]),
            self.audio and any([self.audio.keywords, self.audio.entities, self.audio.sounds, self.audio.audio_type, self.audio.transcription])
        ])