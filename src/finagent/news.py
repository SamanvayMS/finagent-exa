"""Fetch recent news for the ticker and its related entities via Exa."""
from __future__ import annotations

from datetime import datetime, timedelta

from .client import ExaClient
from .config import DEFAULT_NUM_RESULTS
from .models import Entities, NewsItem


def iso_since(now_iso: str, recency_hours: int) -> str:
    now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    since = now - timedelta(hours=recency_hours)
    return since.strftime("%Y-%m-%dT%H:%M:%SZ")


def _map_results(raw, source_entity: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    for r in getattr(raw, "results", None) or []:
        items.append(
            NewsItem(
                title=getattr(r, "title", None) or "(untitled)",
                url=getattr(r, "url", "") or "",
                source_entity=source_entity,
                published_date=getattr(r, "published_date", None),
                highlights=list(getattr(r, "highlights", None) or []),
            )
        )
    return items


def fetch_news(
    client: ExaClient,
    ticker: str,
    company_name: str | None,
    entities: Entities,
    *,
    now_iso: str,
    recency_hours: int,
    num_results: int = DEFAULT_NUM_RESULTS,
) -> list[NewsItem]:
    start = iso_since(now_iso, recency_hours)
    # (label, source_entity) groups: the ticker itself, then each entity by name
    groups: list[tuple[str, str]] = [(company_name or ticker, ticker)]
    for e in entities.subsidiaries + entities.competitors:
        groups.append((e.name, e.name))

    items: list[NewsItem] = []
    for label, source_entity in groups:
        raw = client.search(
            f"latest financial news and developments about {label}",
            stage="news",
            type="auto",
            num_results=num_results,
            start_published_date=start,
            contents={"highlights": True},
        )
        items.extend(_map_results(raw, source_entity))
    return items
