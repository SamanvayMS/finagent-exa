"""Local Flask frontend for trying finagent — a ticker form + rendered report.

Run:
    uv pip install -e ".[dev,web]"
    export EXA_API_KEY=...
    uv run python app.py
Then open http://127.0.0.1:5000
"""
from __future__ import annotations

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from finagent import IMPACT_SYSTEM_PROMPT, analyze_ticker
from finagent.config import FinAgentError

# Load EXA_API_KEY from a local .env before any request is served.
load_dotenv()

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", default_prompt=IMPACT_SYSTEM_PROMPT)


@app.post("/api/analyze")
def api_analyze():
    data = request.get_json(silent=True) or {}
    ticker = (data.get("ticker") or "").strip()
    if not ticker:
        return jsonify({"error": "Please enter a ticker symbol."}), 400

    try:
        result = analyze_ticker(
            ticker.upper(),
            recency_hours=int(data.get("recency_hours") or 24),
            num_results=int(data.get("num_results") or 10),
            include_subsidiaries=bool(data.get("include_subsidiaries", True)),
            include_competitors=bool(data.get("include_competitors", True)),
            system_prompt=(data.get("system_prompt") or None),
        )
    except FinAgentError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:  # noqa: BLE001 - surface anything to the UI
        return jsonify({"error": f"Unexpected error: {exc}"}), 500

    return jsonify(result.model_dump())


def main() -> None:
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)


if __name__ == "__main__":
    main()
