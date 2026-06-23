.PHONY: install scrape synergies data build dev clean hooks

# First-time setup: hermit tools + pre-commit hooks + deps
install: hooks
	cd scraper && uv sync
	cd frontend && pnpm install

# Install pre-commit hooks via prek
hooks:
	prek install

scrape:
	cd scraper && uv run python scrape.py

# Scrape synergies from wiki (run after scrape + data)
synergies:
	cd scraper && uv run python scrape_weapon_traits.py
	cd scraper && uv run python scrape_tool_traits.py

# Copy raw scraped data into the frontend — run after scrape
data:
	cp scraper/data/raw.json frontend/src/data.json
	@echo "data.json ready"

# Full pipeline: scrape → copy → synergies → build
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
