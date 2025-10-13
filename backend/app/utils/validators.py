"""Validation utilities for the application."""

import re
from typing import Optional


def is_valid_email(email: Optional[str]) -> bool:
    """
    Validate email format using regex pattern.

    Args:
        email: Email address to validate. Can be None or empty string.

    Returns:
        True if email is valid format or None/empty, False otherwise.
    """
    if not email:
        return True

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_pattern, email))


def validate_email_format(email: Optional[str]) -> Optional[str]:
    """
    Validate email format and return error message if invalid.

    Args:
        email: Email address to validate. Can be None or empty string.

    Returns:
        None if email is valid, error message string if invalid.
    """
    if not email:
        return None

    if not is_valid_email(email):
        return "Invalid email format"

    return None