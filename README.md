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
