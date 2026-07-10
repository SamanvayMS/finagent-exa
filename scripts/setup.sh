#!/usr/bin/env bash
#
# One-shot setup for finagent-exa.
#   - verifies uv is installed
#   - creates a virtual environment
#   - installs the package with dev + web extras
#   - bootstraps a .env from .env.example (if missing)
#   - runs the test suite to confirm everything works
#
# Usage: ./scripts/setup.sh
#
set -euo pipefail

cd "$(dirname "$0")/.."

info()  { printf '\033[1;36m▸ %s\033[0m\n' "$*"; }
ok()    { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn()  { printf '\033[1;33m! %s\033[0m\n' "$*"; }

if ! command -v uv >/dev/null 2>&1; then
  warn "uv is not installed. Install it first:"
  echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  (docs: https://docs.astral.sh/uv/getting-started/installation/)"
  exit 1
fi
ok "uv found: $(uv --version)"

if [ -d .venv ]; then
  ok "Virtual environment already exists (.venv)"
else
  info "Creating virtual environment (.venv)"
  uv venv
fi

info "Installing finagent with dev + web extras"
uv pip install -e ".[dev,web]"

if [ ! -f .env ]; then
  info "Creating .env from .env.example"
  cp .env.example .env
  warn "Add your Exa API key to .env  ->  EXA_API_KEY=your_key_here"
  echo "  Get a key at https://dashboard.exa.ai"
else
  ok ".env already exists (left untouched)"
fi

info "Running the test suite"
uv run pytest -q

echo
ok "Setup complete."
echo "  Next:"
echo "    1. Put your key in .env         (EXA_API_KEY=...)"
echo "    2. Launch the web UI            ./scripts/run_web.sh"
echo "       or the CLI                   ./scripts/run_cli.sh AAPL"
