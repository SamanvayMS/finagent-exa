"""Configuration, defaults, and error types."""
from __future__ import annotations

import os

DEFAULT_RECENCY_HOURS = 24
DEFAULT_NUM_RESULTS = 10


class FinAgentError(Exception):
    """Base error for finagent."""


class ConfigError(FinAgentError):
    """Raised when required configuration is missing."""


def get_api_key(explicit: str | None = None) -> str:
    key = explicit or os.environ.get("EXA_API_KEY")
    if not key:
        raise ConfigError(
            "EXA_API_KEY is not set. Export it or pass api_key= explicitly."
        )
    return key
