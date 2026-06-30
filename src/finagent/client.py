"""Thin wrapper around exa_py — the ONLY module that imports the Exa SDK."""
from __future__ import annotations

from typing import Any

from .config import FinAgentError, get_api_key


class ExaClient:
    def __init__(self, api_key: str | None = None, _exa: Any = None):
        if _exa is not None:
            self._exa = _exa
        else:
            from exa_py import Exa  # imported lazily so tests need no SDK/key

            self._exa = Exa(api_key=get_api_key(api_key))

    def search(self, query: str, *, stage: str, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for _attempt in range(2):  # initial try + one retry
            try:
                return self._exa.search(query, **kwargs)
            except Exception as exc:  # noqa: BLE001 - wrapped and re-raised
                last_exc = exc
        raise FinAgentError(f"Exa {stage} call failed: {last_exc}") from last_exc
