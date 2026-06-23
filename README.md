# Bayou Traits

> *This project is primarily vibe-coded and experimental — an end-to-end test of how Claude handles a full project, including a scraping pipeline and a simple frontend. It is not meant to replace the [official wiki](https://huntshowdown.wiki.gg) in any way.*

A fast, searchable reference for Hunt: Showdown trait, weapon, and tool synergies — built for hunters who are tired of alt-tabbing to the wiki mid-lobby.

Search by weapon to find the traits that make it sing. Search by tool to see which perks improve your consumables. Search by trait to see everything it affects. Cross-reference in all directions. Know your loadout before you step into the fog.

**[→ Open the finder](https://linusfr.github.io/bayou-traits)**

---

## What it does

- **By Weapon** — pick a gun, see exactly which traits make it dangerous and why
- **By Tool** — pick a consumable (throwables, healing shots, First Aid Kits…) and see which traits improve it
- **By Trait** — find which weapons and tools benefit from a given perk, in one view
- Filter by weapon class (ammo type + melee / bow / launcher), tool category, or trait category
- Traits are tagged: **scarce** (in-run pickups only), **burn** (lost when your hunter dies), **solo** (bonus when playing alone), **event** (limited availability)
- Fuzzy search across names and descriptions
- Responsive — works on mobile, desktop, and your cursed ultrawide

Synergy data is scraped directly from the "Recommended Traits" section on each weapon and tool page on [huntshowdown.wiki.gg](https://huntshowdown.wiki.gg) — no LLM guessing.

---

## Setup

Requires [hermit](https://cashapp.github.io/hermit/) and [direnv](https://direnv.net/).

```bash
# Activate hermit (installs prek, gitleaks, uv into bin/)
. bin/activate-hermit

# Install pre-commit hooks
prek install

# Install all dependencies
make install
```

## Running locally

```bash
# Dev server (hot reload, uses whatever data.json is in frontend/src/)
make dev

# Rebuild data from scratch (scrape wiki metadata → scrape synergies → copy)
make build
```

## Refreshing data after a Hunt patch

The wiki scrapers pick up the current patch version automatically. Run the pipeline locally or trigger the [Refresh Data](../../actions/workflows/refresh-data.yml) workflow manually on GitHub.

```bash
make build
git add frontend/src/data.json
git commit -m "chore(data): refresh for patch X.X.X"
git push
```

Pushing to `main` automatically triggers the deploy workflow.

---

## Architecture

```
scraper/                  Python pipeline (uv)
  scrape.py               → fetches trait/weapon/tool metadata from wiki.gg
  scrape_weapon_traits.py → scrapes "Recommended Traits" from each weapon page
  scrape_tool_traits.py   → scrapes "Recommended Traits" from each tool/consumable page
  enrich.py               → (legacy) DeepSeek enrichment, no longer used for synergies
  build.py                → orchestrates scrape → synergy scrape → copy to frontend

frontend/                 Preact + Tailwind + Fuse.js (pnpm, Vite 6)
  src/data.json           → committed build artifact, updated by refresh pipeline

dist/                     built static site (gitignored, deployed to Pages)

.github/
  workflows/
    deploy.yml            → push to main → build frontend → deploy Pages
    refresh-data.yml      → manual/scheduled → scrape + commit data.json
```

---

## Contributing

Conventional commits, please. prek will tell you if you got it wrong.

```
feat(scraper): add variant parsing for weapon pages
fix(ui): correct ammo color for nitro express
chore(data): refresh for patch 1.18
```

---

## License

[MIT](LICENSE) — use it however you want.
