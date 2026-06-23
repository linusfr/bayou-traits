# Bayou Traits

> *The bayou remembers. Your hunter doesn't have to.*

A fast, searchable reference for Hunt: Showdown trait-weapon synergies — built for hunters who are tired of alt-tabbing to the wiki mid-lobby.

Search by weapon to find the traits that make it sing. Search by trait to see which weapons it transforms. Cross-reference in both directions. Know your loadout before you step into the fog.

**[→ Open the finder](https://linusfr.github.io/bayou-traits)**

---

## What it does

- **By Weapon** — pick a gun, see exactly which traits make it dangerous and why
- **By Trait** — find which weapons benefit from a given perk
- Filter by ammo type (long, medium, compact, shotgun, sparks, nitro) or trait category
- Fuzzy search across names and descriptions
- Responsive — works on mobile, desktop, and your cursed ultrawide

Data is scraped from the official wiki and enriched with DeepSeek to explain *why* each synergy works, not just that it does.

---

## Setup

Requires [hermit](https://cashapp.github.io/hermit/) and [direnv](https://direnv.net/).

```bash
# Activate hermit (installs prek, gitleaks, uv into bin/)
. bin/activate-hermit

# Set up DeepSeek API key via 1Password (see .envrc.example)
cp .envrc.example .envrc
direnv allow

# Install pre-commit hooks
prek install

# Install all dependencies
make install
```

## Running locally

```bash
# Dev server (hot reload, uses whatever data.json is in frontend/src/)
make dev

# Rebuild data from scratch (scrape wiki → enrich with DeepSeek → copy)
make build
```

## Refreshing data after a Hunt patch

The wiki scraper picks up the current patch version automatically. Run the pipeline locally or trigger the [Refresh Data](../../actions/workflows/refresh-data.yml) workflow manually on GitHub.

```bash
# Needs DEEPSEEK_API_KEY in your environment
make build
git add frontend/src/data.json
git commit -m "chore(data): refresh for patch X.X.X"
git push
```

Pushing to `main` automatically triggers the deploy workflow.

---

## Architecture

```
scraper/           Python pipeline (uv)
  scrape.py        → fetches traits + weapons from the wiki via MediaWiki API
  enrich.py        → calls DeepSeek to write "why it helps" for each synergy
  build.py         → orchestrates scrape → enrich → copy to frontend

frontend/          Preact + Tailwind + Fuse.js (pnpm, Vite 8)
  src/data.json    → committed build artifact, updated by refresh pipeline

dist/              built static site (gitignored, deployed to Pages)

.github/
  workflows/
    deploy.yml         → push to main → build frontend → deploy Pages (no API key needed)
    refresh-data.yml   → manual/scheduled → scrape + enrich + commit data.json
```

---

## Contributing

Conventional commits, please. prek will tell you if you got it wrong.

```
feat(scraper): add variant parsing for weapon pages
fix(ui): correct ammo color for nitro express
chore(data): refresh for patch 1.18
```
