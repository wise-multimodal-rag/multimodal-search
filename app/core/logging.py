import sys
import os
from pathlib import Path
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    """Setup logging configuration"""
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