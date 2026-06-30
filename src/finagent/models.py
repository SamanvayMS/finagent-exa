"""Pydantic models for the ticker impact-analysis handoff object."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class Entity(BaseModel):
    name: str
    relation: str  # "subsidiary" | "competitor" | "self"
    description: str | None = None


class Entities(BaseModel):
    subsidiaries: list[Entity] = []
    competitors: list[Entity] = []


class NewsItem(BaseModel):
    title: str
    url: str
    source_entity: str  # which entity this news relates to (ticker/sub/competitor name)
    published_date: str | None = None
    highlights: list[str] = []


class ImpactDriver(BaseModel):
    headline: str
    effect: str
    magnitude: Literal["low", "medium", "high"]
    related_entity: str | None = None


class Impact(BaseModel):
    sentiment: Literal["bullish", "bearish", "neutral", "mixed"]
    score: float  # -1.0 (very bearish) .. 1.0 (very bullish)
    summary: str
    drivers: list[ImpactDriver] = []

    @field_validator("score")
    @classmethod
    def _clamp_score(cls, v: float) -> float:
        return max(-1.0, min(1.0, v))


class Citation(BaseModel):
    field: str
    url: str
    title: str | None = None
    confidence: str = "unknown"


class TickerAnalysis(BaseModel):
    ticker: str
    company_name: str | None = None
    as_of: str
    recency_hours: int
    entities: Entities = Entities()
    news_items: list[NewsItem] = []
    impact: Impact
    citations: list[Citation] = []
