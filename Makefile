.PHONY: install scrape enrich data build dev clean hooks

# First-time setup: hermit tools + pre-commit hooks + deps
install: hooks
	cd scraper && uv sync
	cd frontend && pnpm install

# Install pre-commit hooks via prek
hooks:
	prek install

scrape:
	cd scraper && uv run python scrape.py

enrich:
	cd scraper && uv run python enrich.py

# Copy enriched data into the frontend — run after enrich
data:
	cp scraper/data/enriched.json frontend/src/data.json
	@echo "data.json ready"

# Full pipeline: scrape → enrich → copy → build
build:
	cd scraper && uv run python build.py
	cd frontend && pnpm build
	@echo "Built → dist/"

# Dev server (uses whatever data.json is currently in frontend/src/)
dev:
	cd frontend && pnpm dev

clean:
	rm -rf dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
