"""Embedding selection logic for different element types"""

from typing import Dict, List, Optional, Any


class EmbeddingSelector:
    """Selects appropriate embeddings based on element types"""
    
    def __init__(self):
        # Define element_type to modality mapping
        self.text_element_types = [
            "paragraph", "title", "summary", "stt", "caption", 
            "scene", "ocr", "table", "translation"
        ]
        self.image_element_types = [
            "origin", "cropped", "detected_object", "chart", 
            "diagram", "keyframe", "thumbnail"
        ]
        self.video_element_types = ["clip", "segment"]
        self.audio_element_types = ["speech", "music", "sound_effect", "ambient"]
    
    def select_for_element_type(
        self, 
        element_type: str, 
        embeddings: Optional[Dict[str, List[float]]]
    ) -> Optional[Dict[str, List[float]]]:
        """Select appropriate embedding based on element_type"""
        if not embeddings:
            return None
        
        # Select embedding based on element_type with fallback priority
        if element_type in self.text_element_types:
            return self._select_with_fallback(embeddings, ["text", "image", "video", "audio"])
        elif element_type in self.image_element_types:
            return self._select_with_fallback(embeddings, ["image", "text", "video", "audio"])
        elif element_type in self.video_element_types:
            return self._select_with_fallback(embeddings, ["video", "image", "text", "audio"])
        elif element_type in self.audio_element_types:
            return self._select_with_fallback(embeddings, ["audio", "text", "image", "video"])
        
        # If no match, return first available embedding
        for key, value in embeddings.items():
            return {key: value}
        
        return None
    
    def _select_with_fallback(
        self, 
        embeddings: Dict[str, List[float]], 
        priority_order: List[str]
    ) -> Optional[Dict[str, List[float]]]:
        """Select embedding with fallback priority"""
        for key in priority_order:
            if key in embeddings:
                return {key: embeddings[key]}
        return None