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
