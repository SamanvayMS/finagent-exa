from types import SimpleNamespace

from finagent.agent import analyze_ticker
from finagent.models import TickerAnalysis


class ScriptedClient:
    """Returns canned responses based on the `stage` of each call."""

    def __init__(self):
        self.stages = []

    def search(self, query, *, stage, **kwargs):
        self.stages.append(stage)
        if stage == "discovery":
            return SimpleNamespace(output=SimpleNamespace(content={
                "company_name": "Apple Inc.",
                "subsidiaries": [{"name": "Beats"}],
                "competitors": [{"name": "Samsung"}],
            }))
        if stage == "news":
            return SimpleNamespace(results=[SimpleNamespace(
                title="t", url="https://x", published_date="2026-06-30",
                highlights=["h"])])
        if stage == "synthesis":
            return SimpleNamespace(output=SimpleNamespace(
                content={"sentiment": "bullish", "score": 0.5, "summary": "s",
                         "drivers": []},
                grounding=[{"field": "summary",
                            "citations": [{"url": "https://x"}],
                            "confidence": "high"}]))
        raise AssertionError(stage)


def test_analyze_ticker_end_to_end():
    client = ScriptedClient()
    result = analyze_ticker(
        "AAPL", recency_hours=24, client=client,
        now_iso="2026-06-30T12:00:00Z",
    )
    assert isinstance(result, TickerAnalysis)
    assert result.ticker == "AAPL"
    assert result.company_name == "Apple Inc."
    assert result.recency_hours == 24
    assert result.entities.subsidiaries[0].name == "Beats"
    assert result.impact.sentiment == "bullish"
    assert result.citations[0].url == "https://x"
    assert "discovery" in client.stages
    assert client.stages.count("news") == 3  # ticker + sub + competitor
    assert "synthesis" in client.stages


def test_include_flags_skip_entities():
    client = ScriptedClient()
    result = analyze_ticker(
        "AAPL", client=client, now_iso="2026-06-30T12:00:00Z",
        include_subsidiaries=False, include_competitors=False,
    )
    assert result.entities.subsidiaries == []
    assert result.entities.competitors == []
    assert client.stages.count("news") == 1  # ticker only
