#!/usr/bin/env python3
"""Orchestrates the full data pipeline: scrape → synergy scrape → copy to frontend."""

import shutil
import subprocess
import sys
from pathlib import Path

SCRAPER_DIR = Path(__file__).parent
DATA_DIR = SCRAPER_DIR / "data"
FRONTEND_DATA = SCRAPER_DIR.parent / "frontend" / "src" / "data.json"


def run(cmd: list[str]) -> None:
	print(f"\n$ {' '.join(cmd)}")
	result = subprocess.run(cmd, cwd=SCRAPER_DIR)
	if result.returncode != 0:
		sys.exit(result.returncode)


def main() -> None:
	print("=== Hunt Trait Finder — Data Build ===")

	print("\n[1/4] Scraping wiki metadata...")
	run([sys.executable, "scrape.py"])

	print("\n[2/4] Copying raw data to frontend...")
	src = DATA_DIR / "raw.json"
	FRONTEND_DATA.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy(src, FRONTEND_DATA)
	print(f"  {src} → {FRONTEND_DATA}")

	print("\n[3/4] Scraping weapon synergies from wiki...")
	run([sys.executable, "scrape_weapon_traits.py"])

	print("\n[4/4] Scraping tool synergies from wiki...")
	run([sys.executable, "scrape_tool_traits.py"])

	print("\nDone.")


if __name__ == "__main__":
	main()
