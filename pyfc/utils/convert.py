import logging
import math  # Import the math module
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def is_int(value: Any) -> bool:
    """Check if a value is an integer."""
    if isinstance(value, int):
        return True
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def as_int(value: Any) -> int | None:
    """Convert a value to an integer."""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Value '{value}' cannot be converted to int.")
        return None


def is_float(value: Any) -> bool:
    """Check if a value is a float."""
    if isinstance(value, float):
        return True
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def as_float(value: Any) -> float | None:
    """Convert a value to a float."""
    if isinstance(value, float):
        return value
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Value '{value}' cannot be converted to float.")
        return None


def is_close(a: Any, b: Any, rel_tol: float = 1e-9, abs_tol: float = 0.0) -> bool:
    """
    Determine whether two floating point numbers are close in value.

    Handles cases where inputs might not be floats.

    Parameters
    ----------
    a : Any
        First value to compare.
    b : Any
        Second value to compare.
    rel_tol : float, optional
        Relative tolerance - it is the maximum allowed difference between a and b,
        relative to the larger absolute value of a or b. For example, to set a
        tolerance of 5%, pass rel_tol=0.05. Defaults to 1e-9.
    abs_tol : float, optional
        Absolute tolerance - minimum absolute difference allowed between a and b.
        Useful for comparisons near zero. Defaults to 0.0.

    Returns
    -------
    bool
        True if the values are considered close, False otherwise.
    """
    try:
        # Attempt conversion to float if not already float or int
        if not isinstance(a, (float, int)):
            a = float(a)
        if not isinstance(b, (float, int)):
            b = float(b)
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
    except (ValueError, TypeError):
        # If conversion fails or inputs are incompatible, they are not close
        return a == b  # Fallback to direct comparison for non-numeric types


TRUE_VALUES = ("true", "yes", "ja", "1")
FALSE_VALUES = ("false", "no", "nein", "0")


def is_bool(value: Any) -> bool:
    """Check if a value is a boolean."""
    if isinstance(value, bool):
        return True
    value = str(value).lower()
    if value in TRUE_VALUES:
        return True
    return value in FALSE_VALUES


def as_bool(value: Any) -> bool | None:
    """Convert a value to a boolean."""
    if isinstance(value, bool):
        return value
    value = str(value).lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    logger.warning(f"Value '{value}' cannot be converted to bool.")
    return None


def timestamp_as_str(value: Any) -> str | None:
    """Convert a datetime value to a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if isinstance(value, datetime):
        return value.isoformat()
    logger.warning(f"Value '{value}' cannot be converted to ISO 8601 string.")
    return None


def datetime_as_str(value: Any, format_str: str = "%Y-%m-%d %H:%M:%S") -> str | None:
    """Convert a datetime value to a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if isinstance(value, datetime):
        return value.strftime(format_str)
    logger.warning(f"Value '{value}' cannot be converted to datetime string.")
    return None


def date_as_str(value: Any, format_str: str = "%Y-%m-%d") -> str | None:
    """Convert a date value to a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value).date()
    if isinstance(value, datetime):
        return value.strftime(format_str)
    logger.warning(f"Value '{value}' cannot be converted to date string.")
    return None


def time_as_str(value: Any, format_str: str = "%H:%M:%S") -> str | None:
    """Convert a time value to a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value).time()
    if isinstance(value, datetime):
        return value.strftime(format_str)
    logger.warning(f"Value '{value}' cannot be converted to time string.")
    return None
