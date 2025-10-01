#!/usr/bin/env python3
"""
Development server runner
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # Setup logging before starting uvicorn
    from app.core.logging import setup_logging
    setup_logging()
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        # Disable uvicorn's default logging configuration
        log_config=None
    )