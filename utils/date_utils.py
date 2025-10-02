"""Utilities for handling timestamps and dates."""

from __future__ import annotations

from datetime import UTC, datetime


def safe_format_timestamp(timestamp: float | None) -> str:
    """
    Safely convert a timestamp to a formatted string.

    Args:
        timestamp: Unix timestamp (seconds since epoch) or None

    Returns:
        Formatted datetime string (YYYY-MM-DD HH:MM:SS)
    """
    try:
        if timestamp:
            return datetime.fromtimestamp(timestamp, tz=UTC).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError, OverflowError):
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
