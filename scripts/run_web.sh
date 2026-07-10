#!/usr/bin/env bash
#
# Launch the local Flask web UI at http://127.0.0.1:5000
# Loads EXA_API_KEY from .env automatically.
#
# Usage: ./scripts/run_web.sh
#
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ] && [ -z "${EXA_API_KEY:-}" ]; then
  printf '\033[1;33m! No .env found and EXA_API_KEY is not set.\033[0m\n'
  echo "  Run ./scripts/setup.sh first, then add your key to .env"
  exit 1
fi

echo "Starting finagent web UI on http://127.0.0.1:5000  (Ctrl+C to stop)"
exec uv run python app.py
