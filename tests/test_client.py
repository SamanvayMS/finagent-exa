import pytest

from finagent.client import ExaClient
from finagent.config import FinAgentError


class FakeExa:
    def __init__(self):
        self.calls = []
        self.fail_times = 0

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if len(self.calls) <= self.fail_times:
            raise RuntimeError("transient")
        return {"query": query, "kwargs": kwargs}


def test_search_passes_through():
    fake = FakeExa()
    client = ExaClient(_exa=fake)
    out = client.search("q", stage="news", type="auto", num_results=3)
    assert out["query"] == "q"
    assert out["kwargs"]["type"] == "auto"
    assert len(fake.calls) == 1


def test_search_retries_once_then_succeeds():
    fake = FakeExa()
    fake.fail_times = 1
    client = ExaClient(_exa=fake)
    out = client.search("q", stage="discovery")
    assert out["query"] == "q"
    assert len(fake.calls) == 2  # one fail + one success


def test_search_wraps_persistent_failure():
    fake = FakeExa()
    fake.fail_times = 99
    client = ExaClient(_exa=fake)
    with pytest.raises(FinAgentError) as exc:
        client.search("q", stage="synthesis")
    assert "synthesis" in str(exc.value)
    assert len(fake.calls) == 2  # initial + one retry
