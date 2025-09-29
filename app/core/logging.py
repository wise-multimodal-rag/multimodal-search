import sys
import os
import logging
from pathlib import Path
from loguru import logger
from app.core.config import settings


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages and redirect them to loguru"""
    
    def emit(self, record):
        # Filter out noisy messages
        message = record.getMessage()
        
        # Skip multipart parsing debug messages
        if any(pattern in message for pattern in [
            "Calling on_part_begin",
            "Calling on_header_field", 
            "Calling on_header_value",
            "Calling on_header_end",
            "Calling on_headers_finished",
            "Calling on_part_data",
            "Calling on_part_end"
        ]):
            return
            
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, message)


def setup_logging() -> None:
    """Setup logging configuration with uvicorn and other libraries integration"""
    logger.remove()
    
    # Ensure app_logs directory exists
    try:
        logs_dir = Path("app_logs")
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # If directory creation fails, just continue - loguru will handle it
        pass
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level.upper(),
        colorize=True,
    )
    
    # File logging for errors
    logger.add(
        "app_logs/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 day",
        retention="30 days",
    )
    
    # Debug file logging
    if settings.debug:
        logger.add(
            "app_logs/debug.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="1 day",
            retention="7 days",
        )
    
    # Intercept standard logging and redirect to loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set log levels for third-party libraries
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False
    
    # Reduce verbosity of specific noisy loggers
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("opensearch").setLevel(logging.INFO)
    logging.getLogger("elasticsearch").setLevel(logging.INFO)