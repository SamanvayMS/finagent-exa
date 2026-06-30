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
