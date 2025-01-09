"""Core configuration utilities

This module provides utility functions for the application.
All state operations should go through StateManager.
"""

import logging
from datetime import datetime, timedelta

from core.utils.exceptions import SystemException

logger = logging.getLogger(__name__)


def get_greeting(name: str) -> str:
    """Get time-appropriate greeting

    Args:
        name: User's name to include in greeting

    Returns:
        Time-appropriate greeting message

    Raises:
        SystemException: If greeting generation fails
    """
    try:
        current_time = datetime.now() + timedelta(hours=2)
        hour = current_time.hour

        if 5 <= hour < 12:
            return f"Good Morning {name} 🌅"
        elif 12 <= hour < 18:
            return f"Good Afternoon {name} ☀️"
        elif 18 <= hour < 22:
            return f"Good Evening {name} 🌆"
        else:
            return f"Hello There {name} 🌙"

    except Exception as e:
        logger.error(f"Failed to generate greeting: {str(e)}")
        raise SystemException(
            message="Failed to generate greeting",
            code="GREETING_ERROR",
            service="config",
            action="get_greeting"
        ) from e
