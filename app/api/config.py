"""클라이언트 설정 제공 API"""
from typing import Any, Dict

from fastapi import APIRouter

from app.config import settings
from app.schemas.common import ApiResponse, ResponseBuilder

router = APIRouter()


@router.get("/config/client", response_model=ApiResponse[Dict[str, Any]])
async def get_client_config():
    """클라이언트에서 사용할 설정 정보 제공
    
    보안상 중요한 정보는 제외하고 필요한 설정만 전달
    """
    client_config = {
        "api": {
            "baseUrl": "",  # 클라이언트에서 현재 도메인 사용
            "timeout": 30000,
            "endpoints": {
                "search": "/api/v1/search/multimodal",
                "searchStream": "/api/v1/search/multimodal/stream",
                "health": "/health"
            }
        },
        "search": {
            "maxResults": 50,  # 최대 허용 결과 수
            "defaultResults": 5,
            "supportedFileTypes": {
                "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
                "video": [".mp4", ".avi", ".mov", ".webm", ".mkv"],
                "audio": [".mp3", ".wav", ".ogg", ".m4a", ".aac"],
                "text": [".txt", ".md", ".csv", ".json", ".xml", ".html", ".pdf"]
            },
            "maxFileSize": 10 * 1024 * 1024,  # 10MB
        },
        "ui": {
            "animationDuration": 300,
            "debounceDelay": 500,
            "themes": ["light", "dark", "auto"]
        },
        "streaming": {
            "maxSteps": 50,
            "reconnectAttempts": 3,
            "heartbeatInterval": 30000
        },
        "features": {
            "answerGeneration": True,
            "fileUpload": True,
            "historyTracking": True,
            "exportResults": False  # 향후 기능
        },
        "limits": {
            "queryLength": 1000,
            "filesPerRequest": 4,
            "requestsPerMinute": 60
        },
        "environment": {
            "mode": "development" if settings.debug else "production",
            "version": "1.0.0",  # 버전 정보
            "buildTime": "2024-01-01T00:00:00Z"  # 빌드 시간
        }
    }

    return ResponseBuilder.success(
        data=client_config,
        message="Client configuration retrieved successfully"
    )


@router.get("/config/features", response_model=ApiResponse[Dict[str, Any]])
async def get_feature_flags():
    """기능 플래그 정보 제공
    
    A/B 테스트나 점진적 배포에 사용
    """
    features = {
        "multimodal_search": True,
        "answer_generation": True,
        "file_upload": True,
        "search_history": True,
        "real_time_suggestions": False,  # 향후 기능
        "advanced_filters": False,  # 향후 기능
        "export_results": False,  # 향후 기능
        "collaborative_search": False,  # 향후 기능
    }

    return ResponseBuilder.success(
        data={"features": features},
        message="Feature flags retrieved successfully"
    )
