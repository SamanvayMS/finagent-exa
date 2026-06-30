"""Orchestration: analyze_ticker ties discovery, news, and synthesis together."""
from __future__ import annotations

from datetime import datetime, timezone

from .analysis import synthesize_impact
from .client import ExaClient
from .config import DEFAULT_NUM_RESULTS, DEFAULT_RECENCY_HOURS
from .discovery import discover_entities
from .models import Entities, TickerAnalysis
from .news import fetch_news


def analyze_ticker(
    ticker: str,
    *,
    recency_hours: int = DEFAULT_RECENCY_HOURS,
    num_results: int = DEFAULT_NUM_RESULTS,
    include_subsidiaries: bool = True,
    include_competitors: bool = True,
    system_prompt: str | None = None,
    api_key: str | None = None,
    now_iso: str | None = None,
    client: ExaClient | None = None,
) -> TickerAnalysis:
    """Analyze recent-news impact for a stock ticker and return a handoff object."""
    if client is None:
        client = ExaClient(api_key=api_key)
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    company_name, entities = discover_entities(client, ticker)
    entities = Entities(
        subsidiaries=entities.subsidiaries if include_subsidiaries else [],
        competitors=entities.competitors if include_competitors else [],
    )

    news_items = fetch_news(
        client,
        ticker,
        company_name,
        entities,
        now_iso=now_iso,
        recency_hours=recency_hours,
        num_results=num_results,
    )

    impact, citations = synthesize_impact(
        client, ticker, company_name, news_items, system_prompt=system_prompt
    )

    return TickerAnalysis(
        ticker=ticker,
        company_name=company_name,
        as_of=now_iso,
        recency_hours=recency_hours,
        entities=entities,
        news_items=news_items,
        impact=impact,
        citations=citations,
    )
