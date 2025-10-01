"""Utilities for demo mode."""

import os


def is_demo_mode() -> bool:
    """Check if demo mode is enabled."""
    return os.getenv("DEMO_MODE", "false").lower() == "true"


def get_demo_reset_interval() -> int:
    """Get reset interval in minutes (default 60 minutes)."""
    try:
        return int(os.getenv("DEMO_RESET_INTERVAL_MINUTES", "60"))
    except ValueError:
        return 60
