import pytest

from finagent.config import (
    get_api_key, ConfigError, DEFAULT_RECENCY_HOURS, DEFAULT_NUM_RESULTS,
)


def test_defaults():
    assert DEFAULT_RECENCY_HOURS == 24
    assert DEFAULT_NUM_RESULTS == 10


def test_explicit_key_wins(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    assert get_api_key("abc") == "abc"


def test_env_key(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "envkey")
    assert get_api_key() == "envkey"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        get_api_key()
