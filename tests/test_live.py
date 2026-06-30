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
