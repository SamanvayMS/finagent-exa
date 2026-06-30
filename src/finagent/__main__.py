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
