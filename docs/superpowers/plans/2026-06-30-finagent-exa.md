# finagent-exa Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Python library that, given a stock ticker, discovers its subsidiaries/competitors, pulls recent news via Exa, and returns a grounded, strongly-typed `TickerAnalysis` object ready to hand to any agent framework as a tool result.

**Architecture:** A layered library. `client.py` is the sole module touching `exa_py`; `discovery.py`/`news.py`/`analysis.py` each perform one Exa interaction (taking the client wrapper as a dependency, so they mock trivially); `agent.py` orchestrates them into `analyze_ticker()`; `tool.py` exposes a framework-agnostic tool spec; `__main__.py` is a thin CLI.

**Tech Stack:** Python 3.12+, `exa-py==2.14.0`, `pydantic>=2`, `pytest`, managed with `uv`.

## Global Constraints

- Python package name: `finagent`; project dir: `finagent-exa` (cwd, already git-initialized on `main`).
- Dependencies: `exa-py==2.14.0`, `pydantic>=2`. Dev: `pytest`. No other LLM SDKs.
- Only `EXA_API_KEY` is required at runtime; no second LLM key anywhere.
- `client.py` is the ONLY module that imports `exa_py`. All other modules depend on the `ExaClient` wrapper.
- Exa snake_case params: `type`, `num_results`, `output_schema`, `system_prompt`, `contents`, `start_published_date`, `max_age_hours`, `include_domains`, `exclude_domains`. Never use deprecated `useAutoprompt`, `livecrawl`, `numSentences`, `highlightsPerUrl`.
- `contents={"highlights": True}` for news; `output_schema` for discovery & synthesis; never put citation/confidence fields inside an `output_schema`.
- Default `recency_hours=24`, `num_results=10`; both overridable per call.
- `as_of` timestamps are passed INTO functions by the caller/orchestrator — pure functions never call `datetime.now()` internally (keeps them deterministic/testable).
- All tests mock the `ExaClient`; no live API calls in CI. TDD: failing test first. Commit after each task.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/finagent/__init__.py` (empty placeholder for now)
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an installed, importable `finagent` package; `pytest` runnable.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "finagent"
version = "0.1.0"
description = "Ticker impact-analysis tool library powered by Exa web search"
requires-python = ">=3.12"
dependencies = [
    "exa-py==2.14.0",
    "pydantic>=2",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
finagent = "finagent.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/finagent"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.env.example`**

```env
EXA_API_KEY=
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
.env
.pytest_cache/
*.egg-info/
dist/
build/
.DS_Store
```

- [ ] **Step 4: Create empty package files**

`src/finagent/__init__.py`:
```python
"""finagent — ticker impact-analysis tool library powered by Exa."""
```

`tests/__init__.py`: (empty file)

- [ ] **Step 5: Create venv and install**

Run: `uv venv && uv pip install -e ".[dev]"`
Expected: installs `exa-py`, `pydantic`, `pytest` without error.

- [ ] **Step 6: Verify import and pytest**

Run: `uv run python -c "import finagent; print('ok')" && uv run pytest -q`
Expected: prints `ok`; pytest reports "no tests ran" (exit 5 is acceptable here).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold finagent-exa package"
```

---

### Task 2: Pydantic data models

**Files:**
- Create: `src/finagent/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Entity(name: str, relation: str, description: str | None = None)`
  - `Entities(subsidiaries: list[Entity] = [], competitors: list[Entity] = [])`
  - `NewsItem(title: str, url: str, source_entity: str, published_date: str | None = None, highlights: list[str] = [])`
  - `ImpactDriver(headline: str, effect: str, magnitude: Literal["low","medium","high"], related_entity: str | None = None)`
  - `Impact(sentiment: Literal["bullish","bearish","neutral","mixed"], score: float, summary: str, drivers: list[ImpactDriver] = [])`
  - `Citation(field: str, url: str, title: str | None = None, confidence: str = "unknown")`
  - `TickerAnalysis(ticker, company_name, as_of, recency_hours, entities, news_items, impact, citations)`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.models).

- [ ] **Step 3: Write the implementation**

`src/finagent/models.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/models.py tests/test_models.py
git commit -m "feat: add Pydantic models for ticker analysis"
```

---

### Task 3: Config and errors

**Files:**
- Create: `src/finagent/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class FinAgentError(Exception)` — base error.
  - `class ConfigError(FinAgentError)` — missing config.
  - `DEFAULT_RECENCY_HOURS = 24`, `DEFAULT_NUM_RESULTS = 10`.
  - `get_api_key(explicit: str | None = None) -> str` — returns explicit or `os.environ["EXA_API_KEY"]`, raising `ConfigError` if absent/empty.

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import pytest

from finagent.config import (
    get_api_key, ConfigError, DEFAULT_RECENCY_HOURS, DEFAULT_NUM_RESULTS,
)


def test_defaults():
    assert DEFAULT_RECENCY_HOURS == 24
    assert DEFAULT_NUM_RESULTS == 10


def test_explicit_key_wins(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    assert get_api_key("abc") == "abc"


def test_env_key(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "envkey")
    assert get_api_key() == "envkey"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        get_api_key()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.config).

- [ ] **Step 3: Write the implementation**

`src/finagent/config.py`:
```python
"""Configuration, defaults, and error types."""
from __future__ import annotations

import os

DEFAULT_RECENCY_HOURS = 24
DEFAULT_NUM_RESULTS = 10


class FinAgentError(Exception):
    """Base error for finagent."""


class ConfigError(FinAgentError):
    """Raised when required configuration is missing."""


def get_api_key(explicit: str | None = None) -> str:
    key = explicit or os.environ.get("EXA_API_KEY")
    if not key:
        raise ConfigError(
            "EXA_API_KEY is not set. Export it or pass api_key= explicitly."
        )
    return key
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/config.py tests/test_config.py
git commit -m "feat: add config and error types"
```

---

### Task 4: Exa client wrapper

**Files:**
- Create: `src/finagent/client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: `get_api_key`, `FinAgentError` from `config`.
- Produces:
  - `class ExaClient` wrapping `exa_py.Exa`.
    - `__init__(self, api_key: str | None = None, _exa=None)` — `_exa` injectable for tests; otherwise builds `Exa(api_key=get_api_key(api_key))`.
    - `search(self, query: str, *, stage: str, **kwargs) -> Any` — calls `self._exa.search(query, **kwargs)`, retries once on exception, then wraps the final exception in `FinAgentError(f"Exa {stage} call failed: ...")`.
  - This is the ONLY module importing `exa_py`.

- [ ] **Step 1: Write the failing test**

`tests/test_client.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.client).

- [ ] **Step 3: Write the implementation**

`src/finagent/client.py`:
```python
"""Thin wrapper around exa_py — the ONLY module that imports the Exa SDK."""
from __future__ import annotations

from typing import Any

from .config import FinAgentError, get_api_key


class ExaClient:
    def __init__(self, api_key: str | None = None, _exa: Any = None):
        if _exa is not None:
            self._exa = _exa
        else:
            from exa_py import Exa  # imported lazily so tests need no SDK/key

            self._exa = Exa(api_key=get_api_key(api_key))

    def search(self, query: str, *, stage: str, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for _attempt in range(2):  # initial try + one retry
            try:
                return self._exa.search(query, **kwargs)
            except Exception as exc:  # noqa: BLE001 - wrapped and re-raised
                last_exc = exc
        raise FinAgentError(f"Exa {stage} call failed: {last_exc}") from last_exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/client.py tests/test_client.py
git commit -m "feat: add Exa client wrapper with retry"
```

---

### Task 5: Entity discovery

**Files:**
- Create: `src/finagent/discovery.py`
- Test: `tests/test_discovery.py`

**Interfaces:**
- Consumes: `ExaClient`, `Entity`, `Entities`.
- Produces:
  - `DISCOVERY_SCHEMA: dict` — Exa `output_schema` for `{company_name, subsidiaries[], competitors[]}`.
  - `discover_entities(client: ExaClient, ticker: str) -> tuple[str | None, Entities]` — returns `(company_name, Entities)`. Calls `client.search(..., type="auto", output_schema=DISCOVERY_SCHEMA)`; reads `result.output.content`; degrades to empty `Entities` and `None` company name if output is missing/malformed.

- [ ] **Step 1: Write the failing test**

`tests/test_discovery.py`:
```python
from types import SimpleNamespace

from finagent.discovery import discover_entities, DISCOVERY_SCHEMA
from finagent.models import Entities


class StubClient:
    def __init__(self, output):
        self._output = output
        self.last_kwargs = None

    def search(self, query, *, stage, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(output=SimpleNamespace(content=self._output))


def test_schema_has_no_citation_fields():
    props = DISCOVERY_SCHEMA["properties"]
    assert "subsidiaries" in props and "competitors" in props
    assert "citations" not in props and "confidence" not in props


def test_discover_parses_entities():
    client = StubClient({
        "company_name": "Apple Inc.",
        "subsidiaries": [{"name": "Beats", "description": "audio"}],
        "competitors": [{"name": "Samsung"}],
    })
    name, entities = discover_entities(client, "AAPL")
    assert name == "Apple Inc."
    assert isinstance(entities, Entities)
    assert entities.subsidiaries[0].name == "Beats"
    assert entities.subsidiaries[0].relation == "subsidiary"
    assert entities.competitors[0].relation == "competitor"
    assert client.last_kwargs["type"] == "auto"
    assert client.last_kwargs["output_schema"] is DISCOVERY_SCHEMA


def test_discover_degrades_gracefully():
    client = StubClient(None)
    name, entities = discover_entities(client, "AAPL")
    assert name is None
    assert entities.subsidiaries == [] and entities.competitors == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discovery.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.discovery).

- [ ] **Step 3: Write the implementation**

`src/finagent/discovery.py`:
```python
"""Discover a ticker's subsidiaries and competitors via Exa structured search."""
from __future__ import annotations

from .client import ExaClient
from .models import Entities, Entity

DISCOVERY_SCHEMA: dict = {
    "type": "object",
    "description": "The company behind a stock ticker, its subsidiaries and competitors",
    "required": ["company_name"],
    "properties": {
        "company_name": {
            "type": "string",
            "description": "Full legal name of the company for the ticker",
        },
        "subsidiaries": {
            "type": "array",
            "description": "Notable subsidiaries / owned brands of the company",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "description": "Subsidiary name"},
                    "description": {"type": "string", "description": "What it does"},
                },
            },
        },
        "competitors": {
            "type": "array",
            "description": "Primary publicly-known competitors of the company",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "description": "Competitor name"},
                    "description": {"type": "string", "description": "What it does"},
                },
            },
        },
    },
}


def _to_entities(raw_list, relation: str) -> list[Entity]:
    out: list[Entity] = []
    for item in raw_list or []:
        if isinstance(item, dict) and item.get("name"):
            out.append(
                Entity(
                    name=item["name"],
                    relation=relation,
                    description=item.get("description"),
                )
            )
    return out


def discover_entities(client: ExaClient, ticker: str) -> tuple[str | None, Entities]:
    query = (
        f"Identify the company for stock ticker {ticker}, listing its major "
        f"subsidiaries and its primary competitors."
    )
    result = client.search(
        query,
        stage="discovery",
        type="auto",
        output_schema=DISCOVERY_SCHEMA,
    )
    content = getattr(getattr(result, "output", None), "content", None)
    if not isinstance(content, dict):
        return None, Entities()
    return (
        content.get("company_name"),
        Entities(
            subsidiaries=_to_entities(content.get("subsidiaries"), "subsidiary"),
            competitors=_to_entities(content.get("competitors"), "competitor"),
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discovery.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/discovery.py tests/test_discovery.py
git commit -m "feat: add Exa entity discovery"
```

---

### Task 6: News retrieval

**Files:**
- Create: `src/finagent/news.py`
- Test: `tests/test_news.py`

**Interfaces:**
- Consumes: `ExaClient`, `Entities`, `NewsItem`, `DEFAULT_NUM_RESULTS`.
- Produces:
  - `iso_since(now_iso: str, recency_hours: int) -> str` — given an ISO-8601 `now` string (e.g. `"2026-06-30T12:00:00Z"`), returns the ISO start timestamp `recency_hours` before it. Pure, deterministic (no clock).
  - `fetch_news(client, ticker, company_name, entities, *, now_iso, recency_hours, num_results=DEFAULT_NUM_RESULTS) -> list[NewsItem]` — runs one Exa search per entity group label, with `type="auto"`, `contents={"highlights": True}`, `start_published_date=iso_since(...)`, `num_results=...`. Maps each `result.results[*]` to a `NewsItem` tagged with its `source_entity`. Skips groups that error is NOT required (client wraps errors), but malformed/empty results yield no items.

- [ ] **Step 1: Write the failing test**

`tests/test_news.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_news.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.news).

- [ ] **Step 3: Write the implementation**

`src/finagent/news.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_news.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/news.py tests/test_news.py
git commit -m "feat: add Exa news retrieval"
```

---

### Task 7: Impact synthesis

**Files:**
- Create: `src/finagent/analysis.py`
- Test: `tests/test_analysis.py`

**Interfaces:**
- Consumes: `ExaClient`, `Impact`, `ImpactDriver`, `Citation`, `NewsItem`.
- Produces:
  - `IMPACT_SCHEMA: dict` — Exa `output_schema` for `{sentiment, score, summary, drivers[]}` (NO citation fields).
  - `IMPACT_SYSTEM_PROMPT: str`.
  - `synthesize_impact(client, ticker, company_name, news_items: list[NewsItem]) -> tuple[Impact, list[Citation]]` — builds a query referencing the ticker; calls `client.search(..., type="deep", system_prompt=IMPACT_SYSTEM_PROMPT, output_schema=IMPACT_SCHEMA, contents={"highlights": True})`; maps `output.content` → `Impact` and `output.grounding` → `list[Citation]`. If no news, returns a neutral `Impact` and `[]` WITHOUT calling Exa.

- [ ] **Step 1: Write the failing test**

`tests/test_analysis.py`:
```python
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


def test_no_news_returns_neutral_without_calling_exa():
    client = StubClient()
    impact, citations = synthesize_impact(client, "AAPL", "Apple Inc.", [])
    assert client.called is False
    assert impact.sentiment == "neutral"
    assert impact.score == 0.0
    assert citations == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_analysis.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.analysis).

- [ ] **Step 3: Write the implementation**

`src/finagent/analysis.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_analysis.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/analysis.py tests/test_analysis.py
git commit -m "feat: add Exa impact synthesis"
```

---

### Task 8: Orchestration — `analyze_ticker`

**Files:**
- Create: `src/finagent/agent.py`
- Modify: `src/finagent/__init__.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `ExaClient`, `discover_entities`, `fetch_news`, `synthesize_impact`, `TickerAnalysis`, defaults.
- Produces:
  - `analyze_ticker(ticker: str, *, recency_hours=DEFAULT_RECENCY_HOURS, num_results=DEFAULT_NUM_RESULTS, include_subsidiaries=True, include_competitors=True, api_key: str | None = None, now_iso: str | None = None, client: ExaClient | None = None) -> TickerAnalysis`.
    - Builds an `ExaClient` if none given. If `now_iso` is None, uses `datetime.now(timezone.utc)` (the ONE place a clock is read).
    - Discovers entities; zeroes out subs/competitors per the include flags; fetches news; synthesizes impact; assembles `TickerAnalysis`.
  - `__init__.py` re-exports `analyze_ticker`, `TickerAnalysis`.

- [ ] **Step 1: Write the failing test**

`tests/test_agent.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.agent).

- [ ] **Step 3: Write the implementation**

`src/finagent/agent.py`:
```python
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

    impact, citations = synthesize_impact(client, ticker, company_name, news_items)

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
```

- [ ] **Step 4: Update `__init__.py`**

`src/finagent/__init__.py`:
```python
"""finagent — ticker impact-analysis tool library powered by Exa."""
from .agent import analyze_ticker
from .models import (
    Citation,
    Entities,
    Entity,
    Impact,
    ImpactDriver,
    NewsItem,
    TickerAnalysis,
)

__all__ = [
    "analyze_ticker",
    "TickerAnalysis",
    "Entity",
    "Entities",
    "NewsItem",
    "Impact",
    "ImpactDriver",
    "Citation",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/finagent/agent.py src/finagent/__init__.py tests/test_agent.py
git commit -m "feat: add analyze_ticker orchestration"
```

---

### Task 9: Tool spec + adapters

**Files:**
- Create: `src/finagent/tool.py`
- Modify: `src/finagent/__init__.py` (export `build_tool_spec`, `TOOL_NAME`, `TOOL_DESCRIPTION`, `run_tool`)
- Test: `tests/test_tool.py`

**Interfaces:**
- Consumes: `analyze_ticker`, `TickerAnalysis`.
- Produces:
  - `TOOL_NAME: str = "analyze_ticker_impact"`, `TOOL_DESCRIPTION: str`.
  - `TOOL_PARAMETERS: dict` — JSON Schema for `{ticker (required), recency_hours, num_results, include_subsidiaries, include_competitors}`.
  - `build_tool_spec(flavor: str = "openai") -> dict` — returns a tool/function definition. `flavor="openai"` → `{"type":"function","function":{name,description,parameters}}`; `flavor="anthropic"` → `{name,description,input_schema}`.
  - `run_tool(arguments: dict) -> dict` — calls `analyze_ticker(**arguments)` and returns `TickerAnalysis.model_dump()` (the result an agent feeds back as the tool result).

- [ ] **Step 1: Write the failing test**

`tests/test_tool.py`:
```python
import finagent.tool as tool_mod
from finagent.tool import build_tool_spec, run_tool, TOOL_NAME, TOOL_PARAMETERS


def test_openai_spec_shape():
    spec = build_tool_spec("openai")
    assert spec["type"] == "function"
    assert spec["function"]["name"] == TOOL_NAME
    assert spec["function"]["parameters"]["required"] == ["ticker"]


def test_anthropic_spec_shape():
    spec = build_tool_spec("anthropic")
    assert spec["name"] == TOOL_NAME
    assert spec["input_schema"] is TOOL_PARAMETERS


def test_run_tool_invokes_analyze(monkeypatch):
    captured = {}

    class FakeResult:
        def model_dump(self):
            return {"ticker": "AAPL", "ok": True}

    def fake_analyze(ticker, **kwargs):
        captured["ticker"] = ticker
        captured["kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr(tool_mod, "analyze_ticker", fake_analyze)
    out = run_tool({"ticker": "AAPL", "recency_hours": 48})
    assert out == {"ticker": "AAPL", "ok": True}
    assert captured["ticker"] == "AAPL"
    assert captured["kwargs"]["recency_hours"] == 48
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tool.py -v`
Expected: FAIL (ModuleNotFoundError: finagent.tool).

- [ ] **Step 3: Write the implementation**

`src/finagent/tool.py`:
```python
"""Framework-agnostic tool spec + adapters for agent frameworks."""
from __future__ import annotations

from typing import Any

from .agent import analyze_ticker

TOOL_NAME = "analyze_ticker_impact"
TOOL_DESCRIPTION = (
    "Analyze how the latest news about a stock ticker, its subsidiaries, and its "
    "competitors is likely to impact the ticker. Returns a grounded, structured "
    "analysis object with sentiment, impact drivers, news items, and citations."
)

TOOL_PARAMETERS: dict = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol, e.g. AAPL",
        },
        "recency_hours": {
            "type": "integer",
            "description": "How many hours back to include news (default 24)",
        },
        "num_results": {
            "type": "integer",
            "description": "Max news results per entity (default 10)",
        },
        "include_subsidiaries": {
            "type": "boolean",
            "description": "Whether to include subsidiary news (default true)",
        },
        "include_competitors": {
            "type": "boolean",
            "description": "Whether to include competitor news (default true)",
        },
    },
    "required": ["ticker"],
}


def build_tool_spec(flavor: str = "openai") -> dict:
    if flavor == "anthropic":
        return {
            "name": TOOL_NAME,
            "description": TOOL_DESCRIPTION,
            "input_schema": TOOL_PARAMETERS,
        }
    if flavor == "openai":
        return {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": TOOL_DESCRIPTION,
                "parameters": TOOL_PARAMETERS,
            },
        }
    raise ValueError(f"Unknown flavor: {flavor!r} (use 'openai' or 'anthropic')")


def run_tool(arguments: dict[str, Any]) -> dict:
    """Execute the tool and return a JSON-serializable analysis dict."""
    result = analyze_ticker(**arguments)
    return result.model_dump()
```

- [ ] **Step 4: Update `__init__.py` exports**

Add to imports and `__all__` in `src/finagent/__init__.py`:
```python
from .tool import TOOL_DESCRIPTION, TOOL_NAME, TOOL_PARAMETERS, build_tool_spec, run_tool
```
Append to `__all__`: `"build_tool_spec"`, `"run_tool"`, `"TOOL_NAME"`, `"TOOL_DESCRIPTION"`, `"TOOL_PARAMETERS"`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_tool.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/finagent/tool.py src/finagent/__init__.py tests/test_tool.py
git commit -m "feat: add framework-agnostic tool spec and adapters"
```

---

### Task 10: CLI

**Files:**
- Create: `src/finagent/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `analyze_ticker`.
- Produces:
  - `main(argv: list[str] | None = None) -> int` — parses `ticker` (positional) and `--recency-hours`, `--num-results`, `--no-subsidiaries`, `--no-competitors`; calls `analyze_ticker`; prints `result.model_dump_json(indent=2)`; returns 0. On `FinAgentError`/`ConfigError`, prints the message to stderr and returns 1.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import json

import finagent.__main__ as cli


def test_cli_prints_json(monkeypatch, capsys):
    class FakeResult:
        def model_dump_json(self, indent=2):
            return json.dumps({"ticker": "AAPL"})

    captured = {}

    def fake_analyze(ticker, **kwargs):
        captured.update({"ticker": ticker, **kwargs})
        return FakeResult()

    monkeypatch.setattr(cli, "analyze_ticker", fake_analyze)
    rc = cli.main(["AAPL", "--recency-hours", "48", "--no-competitors"])
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out)["ticker"] == "AAPL"
    assert captured["recency_hours"] == 48
    assert captured["include_competitors"] is False


def test_cli_handles_error(monkeypatch, capsys):
    from finagent.config import ConfigError

    def boom(ticker, **kwargs):
        raise ConfigError("no key")

    monkeypatch.setattr(cli, "analyze_ticker", boom)
    rc = cli.main(["AAPL"])
    assert rc == 1
    assert "no key" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL (ModuleNotFoundError or AttributeError).

- [ ] **Step 3: Write the implementation**

`src/finagent/__main__.py`:
```python
"""CLI: python -m finagent AAPL --recency-hours 24"""
from __future__ import annotations

import argparse
import sys

from .agent import analyze_ticker
from .config import FinAgentError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="finagent",
        description="Analyze recent-news impact for a stock ticker via Exa.",
    )
    parser.add_argument("ticker", help="Stock ticker symbol, e.g. AAPL")
    parser.add_argument("--recency-hours", type=int, default=24)
    parser.add_argument("--num-results", type=int, default=10)
    parser.add_argument("--no-subsidiaries", action="store_true")
    parser.add_argument("--no-competitors", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = analyze_ticker(
            args.ticker,
            recency_hours=args.recency_hours,
            num_results=args.num_results,
            include_subsidiaries=not args.no_subsidiaries,
            include_competitors=not args.no_competitors,
        )
    except FinAgentError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/finagent/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point"
```

---

### Task 11: README, optional live test, full suite

**Files:**
- Create: `README.md`
- Create: `tests/test_live.py`

**Interfaces:**
- Consumes: everything.
- Produces: docs + an opt-in live integration test (skipped unless `RUN_LIVE=1` and `EXA_API_KEY` set).

- [ ] **Step 1: Write `tests/test_live.py`**

```python
import os

import pytest

from finagent import analyze_ticker

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE") != "1" or not os.environ.get("EXA_API_KEY"),
    reason="set RUN_LIVE=1 and EXA_API_KEY to run live Exa integration test",
)


def test_live_analyze_aapl():
    result = analyze_ticker("AAPL", recency_hours=72, num_results=5)
    assert result.ticker == "AAPL"
    assert result.impact.sentiment in {"bullish", "bearish", "neutral", "mixed"}
    # at least produced a structured object; news may be empty in quiet windows
    assert isinstance(result.model_dump(), dict)
```

- [ ] **Step 2: Write `README.md`**

```markdown
# finagent-exa

Ticker impact-analysis tool library powered by [Exa](https://exa.ai) web search.

Given a stock ticker, it discovers the company's subsidiaries and competitors,
pulls recent news on all of them, and returns a grounded, strongly-typed
`TickerAnalysis` object — designed to be handed to any agent (Pydantic AI,
Claude Agent SDK, Strands, …) as a tool result.

Only `EXA_API_KEY` is required. The library performs both retrieval and grounded
synthesis via Exa; the calling agent is the downstream "other model."

## Install

```bash
uv venv && uv pip install -e ".[dev]"
cp .env.example .env   # then set EXA_API_KEY
export EXA_API_KEY=...  # or load your .env
```

## Library usage

```python
from finagent import analyze_ticker

result = analyze_ticker("AAPL", recency_hours=24)
print(result.model_dump_json(indent=2))
```

Key arguments (all optional except `ticker`): `recency_hours` (default 24),
`num_results` (default 10), `include_subsidiaries`, `include_competitors`,
`api_key`.

## CLI

```bash
python -m finagent AAPL --recency-hours 24
```

## Use as an agent tool

```python
from finagent import build_tool_spec, run_tool

# Anthropic (Claude) tool definition
tool = build_tool_spec("anthropic")        # {name, description, input_schema}
# OpenAI / Pydantic AI / Strands function definition
tool = build_tool_spec("openai")           # {type: function, function: {...}}

# When the model calls the tool, execute it and feed the dict back as the result:
result_dict = run_tool({"ticker": "AAPL", "recency_hours": 24})
```

## Output shape

`TickerAnalysis` → `ticker`, `company_name`, `as_of`, `recency_hours`,
`entities {subsidiaries[], competitors[]}`, `news_items[]`,
`impact {sentiment, score, summary, drivers[]}`, `citations[]`
(citations come from Exa's grounding).

## Testing

```bash
uv run pytest                 # unit tests (mocked Exa)
RUN_LIVE=1 uv run pytest tests/test_live.py   # opt-in live API test
```
```

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -q`
Expected: all unit tests pass; live test skipped.

- [ ] **Step 4: Commit**

```bash
git add README.md tests/test_live.py
git commit -m "docs: add README and opt-in live integration test"
```

---

## Self-Review Notes

- **Spec coverage:** entity discovery (T5), news 24h-default configurable (T6/T8/T10), Exa-only deep synthesis (T7), Pydantic handoff object (T2), client isolation of `exa_py` (T4), tool/skill adapters (T9), CLI (T10), graceful degradation & errors (T3/T5/T7), tests mock client (T2–T10), opt-in live test (T11). All spec sections map to tasks.
- **Type consistency:** `analyze_ticker`, `discover_entities`, `fetch_news`, `synthesize_impact`, `ExaClient.search(..., stage=...)`, and all model field names are used identically across tasks.
