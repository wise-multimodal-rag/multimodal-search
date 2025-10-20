"""Security utilities and middleware for the multimodal search application."""

import os
import secrets
from typing import Optional
from loguru import logger


class SecurityManager:
    """Security manager for handling sensitive information and API keys."""
    
    def __init__(self):
        self._api_keys = {}
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from settings object."""
        # Import here to avoid circular imports
        from app.core.config import settings
        
        # API 키 검증 설정
        key_configs = {
            'MULTIMODAL_API_KEY': {
                'value': settings.multimodal_api_key,
                'invalid_values': ['your-api-key-here', 'your-api-key'],
                'min_length': 3
            },
            'LITELLM_API_KEY': {
                'value': settings.litellm_api_key,
                'invalid_values': ['your-api-key-here', 'your-api-key'],
                'min_length': 10  # Bearer 토큰이므로 더 긴 길이 요구
            },
            'OPENSEARCH_USERNAME': {
                'value': settings.opensearch_username,
                'invalid_values': [],  # admin도 유효한 값으로 허용
                'min_length': 1
            },
            'OPENSEARCH_PASSWORD': {
                'value': settings.opensearch_password,
                'invalid_values': [],  # admin도 유효한 값으로 허용  
                'min_length': 1
            }
        }
        
        for key, config in key_configs.items():
            value = config['value']
            if value and len(value) >= config['min_length'] and value not in config['invalid_values']:
                self._api_keys[key] = value
                logger.debug(f"Security: {key} loaded successfully")
            elif value:
                # 값이 있지만 기본값인 경우
                if value in config['invalid_values']:
                    logger.warning(f"Security: {key} is using default value, please set a secure key")
                else:
                    # 길이가 짧은 경우는 개발 환경에서 허용하되 경고
                    self._api_keys[key] = value
                    logger.info(f"Security: {key} loaded (development key detected)")
            else:
                logger.warning(f"Security: {key} is not configured")
    
    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key safely."""
        return self._api_keys.get(key_name)
    
    def validate_api_key(self, key_name: str) -> bool:
        """Validate if API key is properly configured."""
        return key_name in self._api_keys
    
    def mask_sensitive_data(self, data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """Mask sensitive data for logging."""
        if not data or len(data) <= visible_chars:
            return mask_char * len(data) if data else ""
        
        return data[:visible_chars] + mask_char * (len(data) - visible_chars)




# Global security manager instance
security_manager = SecurityManager()