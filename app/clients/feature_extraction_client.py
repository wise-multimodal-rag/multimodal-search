from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.config.config import settings
from app.utils.authentication import security_manager


class FeatureExtractionClient:
    def __init__(self):
        self.base_url = settings.feature_extraction_api_url
        self.timeout = 60.0
        api_key = security_manager.get_api_key("MULTIMODAL_API_KEY") or settings.multimodal_api_key
        header = settings.multimodal_api_key_header
        auth = {header: api_key} if header and api_key else {}
        self.headers = {**auth, "Content-Type": "application/json"}

    async def extract_text_summary(
        self, text: str, summary_type: str = "abstractive", max_length: int = 200, language: str = "ko"
    ) -> Optional[Dict[str, Any]]:
        """Extract text summary"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{settings.feature_api_summary_path}",
                    json={"text": text, "summary_type": summary_type, "max_length": max_length, "language": language},
                    headers=self.headers,
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
        self, text: str, max_keywords: int = 10, min_score: float = 0.3, include_phrases: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Extract keywords from text"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{settings.feature_api_keyword_path}",
                    json={
                        "text": text,
                        "max_keywords": max_keywords,
                        "min_score": min_score,
                        "include_phrases": include_phrases,
                    },
                    headers=self.headers,
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

    async def extract_entities(
        self, text: str, entity_types: Optional[List[str]] = None, min_confidence: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """Extract named entities from text"""
        payload = {"text": text, "min_confidence": min_confidence}
        if entity_types:
            payload["entity_types"] = entity_types

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}{settings.feature_api_entities_path}", json=payload, headers=self.headers)
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
