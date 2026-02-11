import logging
import sys
from pathlib import Path

from loguru import logger

from app.config.config import settings

# 통일된 로그 포맷
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
CONSOLE_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"

# 필터링할 노이즈 패턴들
NOISE_PATTERNS = [
    "Calling on_part_begin", "Calling on_header_field", "Calling on_header_value",
    "Calling on_header_end", "Calling on_headers_finished", "Calling on_part_data",
    "Calling on_part_end", "Calling on_end with no data", "Using proactor:",
    "Unclosed connector", "Unclosed client session", "connections:", "connector:",
    "SSL error in data received", "SSL handshake failed", "Connection broken:",
    "Task was destroyed but it is pending", "Task exception was never retrieved",
    "_log_request_response", "> None", "< ", "opensearchpy.connection",
    "LLM API response keys:", "Text embedding first_5_values", "Text embedding API response:",
    "LLM request:", "LLM response received, length:", "response_cleaned=", "Attempting to parse JSON"
]


class UnifiedInterceptHandler(logging.Handler):
    """모든 로깅을 loguru로 통일"""

    def emit(self, record):
        message = record.getMessage()

        # 노이즈 메시지 필터링
        if any(pattern in message for pattern in NOISE_PATTERNS):
            return

        # 로그 레벨이 너무 낮은 것들 필터링
        if record.levelno < 20 and any(name in record.name.lower() for name in ["asyncio", "aiohttp", "multipart"]):
            return

        # OpenSearch 로그에서 긴 임베딩 벡터 축약
        if "opensearchpy" in record.name and "query_vector" in message:
            import re
            # 임베딩 벡터 부분을 찾아서 축약
            message = re.sub(
                r'"query_vector":\s*\[([^\]]{50,})\]',
                r'"query_vector": "[EMBEDDING_VECTOR: \1...]"',
                message
            )
            # 너무 긴 메시지는 잘라내기
            if len(message) > 500:
                message = message[:500] + "... [TRUNCATED]"

        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, message)


def setup_unified_logging() -> None:
    """통일된 로깅 설정"""
    logger.remove()

    # 로그 디렉토리 생성
    logs_dir = Path("app_logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 콘솔 로그 (컬러)
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level=settings.log_level.upper(),
        colorize=True,
        filter=lambda record: record["level"].name != "ERROR"  # ERROR는 stderr로
    )

    # 콘솔 에러 로그 (stderr)
    logger.add(
        sys.stderr,
        format=CONSOLE_FORMAT,
        level="ERROR",
        colorize=True
    )

    # 통합 애플리케이션 로그 파일
    logger.add(
        "app_logs/app.log",
        format=LOG_FORMAT,
        level="INFO",
        rotation="50 MB",
        retention="10 days",
        compression="gz"
    )

    # 에러 전용 로그 파일
    logger.add(
        "app_logs/error.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="gz"
    )

    # 모든 기본 로깅을 loguru로 리다이렉트
    logging.root.handlers = [UnifiedInterceptHandler()]
    logging.root.setLevel(0)

    # 모든 로거를 loguru로 통일
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # 노이즈가 심한 라이브러리들 조용하게
    for noisy_logger in [
        "multipart", "httpcore", "httpx", "aiohttp", "asyncio",
        "urllib3", "requests", "botocore", "boto3", "opensearchpy",
        "opensearch", "elasticsearch", "opensearchpy.connection",
        "app.clients.llm_client", "app.clients.embedding_client",
        "app.clients.feature_extraction_client"
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


# 이전 함수와의 호환성을 위해 별칭 유지
def setup_logging():
    """기존 호환성을 위한 별칭"""
    return setup_unified_logging()
