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
