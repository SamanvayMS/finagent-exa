# finagent-exa — Ticker Impact-Analysis Tool Library

**Date:** 2026-06-30
**Status:** Approved design

## Purpose

A self-contained Python library that, given a stock ticker, discovers the
company's subsidiaries and competitors, pulls recent news on all of them via the
Exa web-search API, and returns a **grounded, structured impact-analysis object**.

The object is designed as a clean handoff: it is consumed as a *tool result* by a
host agent (Pydantic AI, Claude Agent SDK, Strands, or any generic agent loop).
The host agent is the "other model" referenced in the original request.

## Core Decisions

| Decision | Choice |
|----------|--------|
| Model pipeline | Library stops at a clean structured analysis object; downstream model is the calling agent. |
| Entity discovery | Live via Exa structured search (`output_schema`). |
| Packaging | Importable library first; thin CLI for testing; adapters so it wraps as a tool/skill. |
| Synthesis engine | **Exa-only** — `deep` search + `output_schema` produces the grounded analysis. Only `EXA_API_KEY` required; no second LLM key. |
| News recency | Configurable per call. **Default: 24 hours.** |
| Search type (news) | `auto` (balanced). |
| Search type (synthesis) | `deep` + `output_schema`. |
| Content mode | `highlights` (token-efficient). |

## Pipeline

Three Exa calls, orchestrated by `analyze_ticker()`:

1. **Entity discovery** — `exa.search(query, type="auto", output_schema=...)` returns
   `{subsidiaries: [...], competitors: [...]}` for the ticker/company.
2. **News retrieval** — for the ticker and the discovered entities, run Exa search
   with `type="auto"`, `contents={"highlights": True}`, and a recency filter
   (`start_published_date` derived from the `recency_hours` argument; `max_age_hours`
   used to control cache/livecrawl freshness). Highlights + URLs collected.
3. **Impact synthesis** — `exa.search(..., type="deep", system_prompt=..., output_schema=...)`
   produces a grounded impact analysis. Field-level citations come from
   `output.grounding`; never put citation/confidence fields in the schema itself.

The library never calls a second LLM. Synthesis grounding (sources + confidence)
is taken directly from Exa's `output.grounding`.

## Public Surface

```python
from finagent import analyze_ticker, TickerAnalysis

result: TickerAnalysis = analyze_ticker(
    "AAPL",
    recency_hours=24,        # configurable; default 24
    num_results=10,
    include_subsidiaries=True,
    include_competitors=True,
)
payload = result.model_dump()   # clean JSON for handoff
```

A `build_tool_spec()` helper (and small adapters) exposes the function as a tool
definition for the major agent frameworks.

## Data Model (Pydantic)

`TickerAnalysis`:
- `ticker: str`
- `company_name: str | None`
- `as_of: str` (ISO timestamp, supplied by caller / orchestrator — not generated
  inside pure functions, to keep them deterministic and testable)
- `recency_hours: int`
- `entities: Entities` → `{ subsidiaries: list[Entity], competitors: list[Entity] }`
  where `Entity = { name: str, relation: str, description: str | None }`
- `news_items: list[NewsItem]` → `{ title, url, source_entity, published_date?, highlights: list[str] }`
- `impact: Impact` → `{ sentiment: Literal["bullish","bearish","neutral","mixed"],
  score: float (-1..1), summary: str, drivers: list[ImpactDriver] }`
  where `ImpactDriver = { headline: str, effect: str, magnitude: Literal["low","medium","high"], related_entity: str | None }`
- `citations: list[Citation]` → `{ field: str, url: str, title: str | None, confidence: str }`
  (mapped from Exa `output.grounding`)

All models are strict Pydantic v2 so any agent framework gets a clean JSON schema.

## Module Layout

```
finagent-exa/
  pyproject.toml            # uv-managed; deps: exa-py==2.14.0, pydantic>=2
  .env.example              # EXA_API_KEY=
  .gitignore
  README.md
  src/finagent/
    __init__.py             # exports analyze_ticker, TickerAnalysis, build_tool_spec
    config.py               # settings (api key, defaults: recency_hours=24, num_results=10)
    client.py               # thin Exa wrapper: construct client, basic retry/error mapping
    models.py               # Pydantic models above
    discovery.py            # discover_entities(ticker) -> Entities
    news.py                 # fetch_news(ticker, entities, recency_hours, num_results) -> list[NewsItem]
    analysis.py             # synthesize_impact(ticker, entities, news) -> Impact + citations
    agent.py                # analyze_ticker(...) orchestration
    tool.py                 # build_tool_spec() + adapter examples
    __main__.py             # CLI: python -m finagent AAPL --recency-hours 24
  tests/
    test_models.py
    test_discovery.py       # mocked Exa
    test_news.py            # mocked Exa
    test_analysis.py        # mocked Exa
    test_agent.py           # end-to-end with mocked Exa client
```

## Boundaries & Responsibilities

- `client.py` — the ONLY module that touches `exa_py`. Everything else depends on
  its typed wrapper, which makes mocking trivial in tests.
- `discovery.py`, `news.py`, `analysis.py` — each does one Exa interaction and maps
  the raw response into Pydantic models. Pure given a client.
- `agent.py` — orchestration only; no Exa SDK imports.
- `tool.py` — framework-facing; no business logic.

## Error Handling

- Missing `EXA_API_KEY` → clear `ConfigError` at client construction.
- Exa API/network errors → wrapped in `FinAgentError` with the failing stage named
  (`discovery`/`news`/`synthesis`); basic retry (1 retry) on transient errors in `client.py`.
- Empty news (quiet ticker / tight recency window) → returns a valid `TickerAnalysis`
  with `news_items=[]` and `impact.sentiment="neutral"`, `summary` noting no recent news.
- Entity discovery returning nothing → proceed with ticker-only news (degrade gracefully).

## Testing Strategy

- Unit tests mock the `client.py` wrapper (no live API calls in CI).
- One opt-in integration test (skipped unless `EXA_API_KEY` set and `RUN_LIVE=1`)
  that hits the real API for a known ticker.
- TDD: write the failing test for each module before implementing it.

## Out of Scope (YAGNI)

- The downstream "other model" / trading-engine integration.
- Persistence/caching beyond Exa's own `max_age_hours`.
- Historical backtesting or price data.
- Multiple-ticker batch mode (single ticker per call for now).

## Staleness Note

The provided setup guide pins `exa-py==2.14.0`; the live canonical docs
(https://exa.ai/docs/reference/search-api-guide-for-coding-agents) say
`pip install exa-py` (latest). We pin `2.14.0` for reproducibility. All other API
surface (search types, `output_schema`/`system_prompt` snake_case, `output.content`
/ `output.grounding`, deprecated params) matches the canonical docs as of 2026-06-30.
