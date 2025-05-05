import inspect
import traceback

import pytest


def test_failure(reason: str | None = None):
    """
    Helper function to fail a pytest test, automatically including the
    calling test function's name and the current exception traceback.

    Parameters
    ----------
    reason : str | None
        Optional reason for the failure. If provided, it will be included in the
        failure message.
    """
    try:
        caller_frame = inspect.stack()[1]
        test_function_name = caller_frame.function
    except IndexError:
        test_function_name = "Unknown Function"

    message = f"Test failed in '{test_function_name}'"
    if reason:
        message += f": {reason}"
    # Append the traceback
    exc_traceback = traceback.format_exc()
    if exc_traceback == "None\n":
        exc_traceback = "No active exception traceback available."
    message += f"\n{exc_traceback}"
    pytest.fail(message, pytrace=False)
