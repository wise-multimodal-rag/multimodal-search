"""Version information for the multimodal search application."""

import os
import sys
from datetime import datetime
from typing import Dict, Any

# Version information
__version__ = "0.2.0"


def get_version_info() -> Dict[str, Any]:
    """Get comprehensive version information."""
    return {
        "version": __version__,
        "build_time": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": sys.version,
        "api_version": "v1",
        "features": {
            "multimodal_search": True,
            "answer_generation": True,
            "streaming": True,
            "file_upload": True,
        }
    }