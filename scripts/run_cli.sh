#!/usr/bin/env bash
#
# Run the finagent CLI. All arguments are forwarded to `python -m finagent`.
# Loads EXA_API_KEY from .env automatically.
#
# Usage:
#   ./scripts/run_cli.sh AAPL
#   ./scripts/run_cli.sh TSLA --recency-hours 48 --num-results 5 --no-competitors
#
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$#" -eq 0 ]; then
  echo "Usage: ./scripts/run_cli.sh <TICKER> [--recency-hours N] [--num-results N] [--no-subsidiaries] [--no-competitors]"
  exit 1
fi

exec uv run python -m finagent "$@"
