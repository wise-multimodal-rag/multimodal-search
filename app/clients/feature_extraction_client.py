from typing import List, Optional, Dict, Any
import httpx
from loguru import logger

from app.core.config import settings


class FeatureExtractionClient:
    def __init__(self):
        self.base_url = settings.feature_extraction_api_url
        self.timeout = 60.0
        self.headers = {
            "x-token": settings.multimodal_api_key,
            "Content-Type": "application/json"
        }
        self.file_headers = {
            "x-token": settings.multimodal_api_key
        }

    async def extract_text_summary(
        self, 
        text: str, 
        summary_type: str = "abstractive", 
        max_length: int = 200,
        language: str = "ko"
    ) -> Optional[Dict[str, Any]]:
        """Extract text summary"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extraction/text/summarization",
                    json={
                        "text": text,
                        "summary_type": summary_type,
                        "max_length": max_length,
                        "language": language
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Text summarization API response: {result}")
                if result.get("code") == 200:
                    return result["result"]
                else:
                    logger.error(f"Text summarization failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Text summarization request failed: {e}")
                return None

    async def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10,
        min_score: float = 0.3,
        include_phrases: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extract keywords from text"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extraction/text/keyword",
                    json={
                        "text": text,
                        "max_keywords": max_keywords,
                        "min_score": min_score,
                        "include_phrases": include_phrases
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Keyword extraction API response: {result}")
                if result.get("code") == 200:
                    return result["result"]
                else:
                    logger.error(f"Keyword extraction failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Keyword extraction request failed: {e}")
                return None

    async def classify_text(self, text: str, top_k: int = 3) -> Optional[Dict[str, Any]]:
        """Classify text document type"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extraction/text/classify",
                    json={"text": text, "top_k": top_k},
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Text classification API response: {result}")
                if result.get("code") == 200:
                    return result["result"]
                else:
                    logger.error(f"Text classification failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Text classification request failed: {e}")
                return None

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        min_confidence: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """Extract named entities from text"""
        payload = {"text": text, "min_confidence": min_confidence}
        if entity_types:
            payload["entity_types"] = entity_types
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extraction/text/entities",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Entity extraction API response: {result}")
                if result.get("code") == 200:  # Fixed: API returns 200, not 100200
                    return result["result"]
                else:
                    logger.error(f"Entity extraction failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Entity extraction request failed: {e}")
                return None

    async def analyze_sentiment(
        self, 
        text: str, 
        detail_level: str = "simple"
    ) -> Optional[Dict[str, Any]]:
        """Analyze text sentiment"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extraction/text/sentiment",
                    json={"text": text, "detail_level": detail_level},
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Sentiment analysis API response: {result}")
                if result.get("code") == 200:
                    return result["result"]
                else:
                    logger.error(f"Sentiment analysis failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Sentiment analysis request failed: {e}")
                return None

    async def generate_image_caption(
        self,
        image_data: bytes
    ) -> Optional[Dict[str, Any]]:
        """Generate image caption"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"image_file": ("image.jpg", image_data, "image/jpeg")}
                
                response = await client.post(
                    f"{self.base_url}/analysis/image/captioning",
                    files=files,
                    headers=self.file_headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Image caption API response: {result}")
                if result.get("status") == "success":
                    return result["data"]
                else:
                    logger.error(f"Image caption generation failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Image caption request failed: {e}")
                return None

    async def detect_objects(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Detect objects in image"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"image": ("image.jpg", image_data, "image/jpeg")}
                response = await client.post(
                    f"{self.base_url}/analysis/image/detection",
                    files=files,
                    headers=self.file_headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Object detection API response: {result}")
                if result.get("status") == "success":
                    return result["data"]
                else:
                    logger.error(f"Object detection failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Object detection request failed: {e}")
                return None

    async def extract_document_text(
        self,
        document_data: bytes,
        language: str = "ko",
        detect_layout: bool = True,
        output_format: str = "structured"
    ) -> Optional[Dict[str, Any]]:
        """Extract text from document using OCR"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"document": ("document.pdf", document_data, "application/pdf")}
                data = {
                    "language": language,
                    "detect_layout": str(detect_layout).lower(),
                    "output_format": output_format
                }
                
                response = await client.post(
                    f"{self.base_url}/parsing/document/ocr",
                    files=files,
                    data=data,
                    headers=self.file_headers
                )
                response.raise_for_status()
                
                result = response.json()
                if result["code"] == 200:
                    return result["result"]
                else:
                    logger.error(f"Document OCR failed: {result.get('message')}")
                    return None
                    
            except Exception as e:
                logger.error(f"Document OCR request failed: {e}")
                return None


    async def analyze_document_layout(
        self,
        document_data: bytes,
        extract_images: bool = True,
        extract_tables: bool = True,
        confidence_threshold: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """Analyze document layout structure"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"document": ("document.pdf", document_data, "application/pdf")}
                data = {
                    "extract_images": str(extract_images).lower(),
                    "extract_tables": str(extract_tables).lower(),
                    "confidence_threshold": confidence_threshold
                }
                
                response = await client.post(
                    f"{self.base_url}/parsing/document/layout",
                    files=files,
                    data=data,
                    headers=self.file_headers
                )
                response.raise_for_status()
                
                result = response.json()
                if result["code"] == 200:
                    return result["result"]
                else:
                    logger.error(f"Document layout analysis failed: {result.get('message')}")
                    return None
                    
            except Exception as e:
                logger.error(f"Document layout analysis request failed: {e}")
                return None

    async def extract_document_elements(
        self,
        document_data: bytes,
        extract_type: str = "table,image",
        table_format: str = "csv",
        image_format: str = "png"
    ) -> Optional[Dict[str, Any]]:
        """Extract tables and images from document"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"document": ("document.pdf", document_data, "application/pdf")}
                data = {
                    "extract_type": extract_type,
                    "table_format": table_format,
                    "image_format": image_format
                }
                
                response = await client.post(
                    f"{self.base_url}/parsing/document/extract",
                    files=files,
                    data=data,
                    headers=self.file_headers
                )
                response.raise_for_status()
                
                result = response.json()
                if result["code"] == 200:
                    return result["result"]
                else:
                    logger.error(f"Document element extraction failed: {result.get('message')}")
                    return None
                    
            except Exception as e:
                logger.error(f"Document element extraction request failed: {e}")
                return None


