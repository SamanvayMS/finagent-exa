from types import SimpleNamespace

from finagent.analysis import synthesize_impact, IMPACT_SCHEMA
from finagent.models import Impact, NewsItem


def test_schema_has_no_citation_fields():
    props = IMPACT_SCHEMA["properties"]
    assert set(["sentiment", "score", "summary", "drivers"]).issubset(props)
    assert "citations" not in props and "grounding" not in props


class StubClient:
    def __init__(self):
        self.called = False
        self.last_kwargs = None

    def search(self, query, *, stage, **kwargs):
        self.called = True
        self.last_kwargs = kwargs
        return SimpleNamespace(output=SimpleNamespace(
            content={
                "sentiment": "bullish",
                "score": 0.6,
                "summary": "Strong earnings",
                "drivers": [
                    {"headline": "Q3 beat", "effect": "raises guidance",
                     "magnitude": "high", "related_entity": "AAPL"}
                ],
            },
            grounding=[
                {"field": "summary", "citations": [{"url": "https://x", "title": "T"}],
                 "confidence": "high"}
            ],
        ))


def test_synthesize_maps_impact_and_citations():
    client = StubClient()
    news = [NewsItem(title="t", url="https://x", source_entity="AAPL", highlights=["h"])]
    impact, citations = synthesize_impact(client, "AAPL", "Apple Inc.", news)
    assert isinstance(impact, Impact)
    assert impact.sentiment == "bullish"
    assert impact.drivers[0].magnitude == "high"
    assert citations[0].url == "https://x"
    assert citations[0].confidence == "high"
    assert client.last_kwargs["type"] == "deep"
    assert client.last_kwargs["output_schema"] is IMPACT_SCHEMA


def test_default_system_prompt_used():
    from finagent.analysis import IMPACT_SYSTEM_PROMPT

    client = StubClient()
    news = [NewsItem(title="t", url="https://x", source_entity="AAPL")]
    synthesize_impact(client, "AAPL", "Apple Inc.", news)
    assert client.last_kwargs["system_prompt"] == IMPACT_SYSTEM_PROMPT


def test_system_prompt_override_passed_through():
    client = StubClient()
    news = [NewsItem(title="t", url="https://x", source_entity="AAPL")]
    synthesize_impact(
        client, "AAPL", "Apple Inc.", news, system_prompt="Be extra skeptical."
    )
    assert client.last_kwargs["system_prompt"] == "Be extra skeptical."


def test_blank_system_prompt_falls_back_to_default():
    from finagent.analysis import IMPACT_SYSTEM_PROMPT

    client = StubClient()
    news = [NewsItem(title="t", url="https://x", source_entity="AAPL")]
    synthesize_impact(client, "AAPL", "Apple Inc.", news, system_prompt="   ")
    assert client.last_kwargs["system_prompt"] == IMPACT_SYSTEM_PROMPT


def test_no_news_returns_neutral_without_calling_exa():
    client = StubClient()
    impact, citations = synthesize_impact(client, "AAPL", "Apple Inc.", [])
    assert client.called is False
    assert impact.sentiment == "neutral"
    assert impact.score == 0.0
    assert citations == []
