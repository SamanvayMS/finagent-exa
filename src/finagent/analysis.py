"""Synthesize a grounded impact analysis from collected news via Exa deep search."""
from __future__ import annotations

from .client import ExaClient
from .models import Citation, Impact, ImpactDriver, NewsItem

IMPACT_SYSTEM_PROMPT = (
    "You are a financial analyst. Using only the retrieved sources, assess how the "
    "recent news about the company, its subsidiaries, and its competitors is likely "
    "to impact the company's stock. Prefer official and reputable financial sources, "
    "collapse duplicate reporting, and stay strictly grounded in the sources."
)

IMPACT_SCHEMA: dict = {
    "type": "object",
    "description": "Grounded assessment of news impact on a stock",
    "required": ["sentiment", "score", "summary"],
    "properties": {
        "sentiment": {
            "type": "string",
            "description": "Overall impact direction: bullish, bearish, neutral, or mixed",
        },
        "score": {
            "type": "number",
            "description": "Impact score from -1.0 (very bearish) to 1.0 (very bullish)",
        },
        "summary": {
            "type": "string",
            "description": "Concise grounded summary of how the news impacts the stock",
        },
        "drivers": {
            "type": "array",
            "description": "Specific news items driving the impact",
            "items": {
                "type": "object",
                "required": ["headline", "effect", "magnitude"],
                "properties": {
                    "headline": {"type": "string", "description": "Short news headline"},
                    "effect": {"type": "string", "description": "Why it moves the stock"},
                    "magnitude": {
                        "type": "string",
                        "description": "Impact magnitude: low, medium, or high",
                    },
                    "related_entity": {
                        "type": "string",
                        "description": "Ticker, subsidiary, or competitor the item concerns",
                    },
                },
            },
        },
    },
}

_VALID_SENTIMENTS = {"bullish", "bearish", "neutral", "mixed"}
_VALID_MAGNITUDES = {"low", "medium", "high"}


def _neutral(summary: str) -> Impact:
    return Impact(sentiment="neutral", score=0.0, summary=summary, drivers=[])


def _to_drivers(raw) -> list[ImpactDriver]:
    out: list[ImpactDriver] = []
    for d in raw or []:
        if not isinstance(d, dict):
            continue
        mag = d.get("magnitude")
        if mag not in _VALID_MAGNITUDES:
            mag = "low"
        out.append(
            ImpactDriver(
                headline=d.get("headline") or "(unknown)",
                effect=d.get("effect") or "",
                magnitude=mag,
                related_entity=d.get("related_entity"),
            )
        )
    return out


def _to_citations(grounding) -> list[Citation]:
    out: list[Citation] = []
    for g in grounding or []:
        if not isinstance(g, dict):
            continue
        field = g.get("field", "")
        confidence = g.get("confidence", "unknown")
        for c in g.get("citations") or []:
            if isinstance(c, dict) and c.get("url"):
                out.append(
                    Citation(
                        field=field,
                        url=c["url"],
                        title=c.get("title"),
                        confidence=confidence,
                    )
                )
    return out


def synthesize_impact(
    client: ExaClient,
    ticker: str,
    company_name: str | None,
    news_items: list[NewsItem],
) -> tuple[Impact, list[Citation]]:
    if not news_items:
        return _neutral(f"No recent news found for {ticker} in the selected window."), []

    name = company_name or ticker
    query = (
        f"How does the latest news about {name} ({ticker}), its subsidiaries, and its "
        f"competitors impact {ticker}'s stock?"
    )
    result = client.search(
        query,
        stage="synthesis",
        type="deep",
        system_prompt=IMPACT_SYSTEM_PROMPT,
        output_schema=IMPACT_SCHEMA,
        contents={"highlights": True},
    )
    output = getattr(result, "output", None)
    content = getattr(output, "content", None)
    if not isinstance(content, dict):
        return _neutral(f"Synthesis returned no structured output for {ticker}."), []

    sentiment = content.get("sentiment")
    if sentiment not in _VALID_SENTIMENTS:
        sentiment = "mixed"
    score = content.get("score")
    score = float(score) if isinstance(score, (int, float)) else 0.0

    impact = Impact(
        sentiment=sentiment,
        score=score,
        summary=content.get("summary") or "",
        drivers=_to_drivers(content.get("drivers")),
    )
    citations = _to_citations(getattr(output, "grounding", None))
    return impact, citations
