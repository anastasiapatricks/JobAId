import os
from typing import Dict, Any


def get_latest_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the results array into a dict with the latest value per field.

    Iterates through all entries in state["results"] and returns a dict
    containing the most recent value for each field (excluding 'action' and 'timestamp').
    """
    flat: Dict[str, Any] = {}
    for entry in state.get("results", []):
        for k, v in entry.items():
            if k not in ("action", "timestamp"):
                flat[k] = v
    return flat


def debug(message, prefix="DEBUG"):
    """
    Print debug message in gray if DEBUG env var is true.

    Args:
        message: The debug message to print
        prefix: Prefix for the debug message (default: "DEBUG")
    """
    if os.getenv("DEBUG", "false").lower() == "true":
        print(f"    \033[2m[{prefix}] {message}\033[0m")
