from types import SimpleNamespace

from finagent.news import iso_since, fetch_news
from finagent.models import Entities, Entity


def test_iso_since_subtracts_hours():
    assert iso_since("2026-06-30T12:00:00Z", 24) == "2026-06-29T12:00:00Z"


class StubClient:
    def __init__(self):
        self.queries = []

    def search(self, query, *, stage, **kwargs):
        self.queries.append((query, kwargs))
        return SimpleNamespace(results=[
            SimpleNamespace(
                title=f"news about {query[:6]}",
                url="https://example.com/a",
                published_date="2026-06-30",
                highlights=["h1", "h2"],
            )
        ])


def test_fetch_news_tags_source_and_filters_date():
    client = StubClient()
    entities = Entities(
        subsidiaries=[Entity(name="Beats", relation="subsidiary")],
        competitors=[Entity(name="Samsung", relation="competitor")],
    )
    items = fetch_news(
        client, "AAPL", "Apple Inc.", entities,
        now_iso="2026-06-30T12:00:00Z", recency_hours=24, num_results=5,
    )
    # one item per searched group: ticker + 1 sub + 1 competitor = 3
    assert len(items) == 3
    sources = {i.source_entity for i in items}
    assert "AAPL" in sources and "Beats" in sources and "Samsung" in sources
    for _q, kwargs in client.queries:
        assert kwargs["contents"] == {"highlights": True}
        assert kwargs["type"] == "auto"
        assert kwargs["start_published_date"] == "2026-06-29T12:00:00Z"
        assert kwargs["num_results"] == 5


def test_fetch_news_handles_missing_fields():
    class SparseClient:
        def search(self, query, *, stage, **kwargs):
            return SimpleNamespace(results=[SimpleNamespace(url="https://x")])

    items = fetch_news(
        SparseClient(), "AAPL", None, Entities(),
        now_iso="2026-06-30T12:00:00Z", recency_hours=24,
    )
    assert len(items) == 1
    assert items[0].title == "(untitled)"
    assert items[0].highlights == []
