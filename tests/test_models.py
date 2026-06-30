from finagent.models import (
    Entity, Entities, NewsItem, ImpactDriver, Impact, Citation, TickerAnalysis,
)


def test_entity_defaults():
    e = Entity(name="Beats", relation="subsidiary")
    assert e.description is None


def test_impact_score_clamped():
    imp = Impact(sentiment="bullish", score=5.0, summary="x")
    assert imp.score == 1.0
    imp2 = Impact(sentiment="bearish", score=-9.0, summary="y")
    assert imp2.score == -1.0


def test_ticker_analysis_roundtrip():
    ta = TickerAnalysis(
        ticker="AAPL",
        company_name="Apple Inc.",
        as_of="2026-06-30T00:00:00Z",
        recency_hours=24,
        entities=Entities(
            subsidiaries=[Entity(name="Beats", relation="subsidiary")],
            competitors=[Entity(name="Samsung", relation="competitor")],
        ),
        news_items=[NewsItem(title="t", url="https://x", source_entity="AAPL", highlights=["h"])],
        impact=Impact(
            sentiment="bullish", score=0.4, summary="ok",
            drivers=[ImpactDriver(headline="h", effect="e", magnitude="high")],
        ),
        citations=[Citation(field="impact.summary", url="https://x", confidence="high")],
    )
    dumped = ta.model_dump()
    assert dumped["ticker"] == "AAPL"
    assert dumped["impact"]["sentiment"] == "bullish"
    assert TickerAnalysis.model_validate(dumped).recency_hours == 24
