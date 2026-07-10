# finagent-exa — common tasks
# Run `make help` to list targets.

.DEFAULT_GOAL := help
.PHONY: help setup install test test-live web cli lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Full setup: venv, install, .env, run tests
	./scripts/setup.sh

install: ## Install package with dev + web extras
	uv pip install -e ".[dev,web]"

test: ## Run the unit test suite (Exa mocked)
	uv run pytest -q

test-live: ## Run the opt-in live Exa integration test (needs EXA_API_KEY)
	RUN_LIVE=1 uv run pytest tests/test_live.py -v

web: ## Launch the local web UI on http://127.0.0.1:5000
	./scripts/run_web.sh

cli: ## Run the CLI, e.g. `make cli TICKER=AAPL`
	uv run python -m finagent $(TICKER)

clean: ## Remove build/venv/cache artifacts
	rm -rf .venv .pytest_cache *.egg-info src/*.egg-info dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
