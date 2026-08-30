#!/usr/bin/env python3
"""Orchestrates the full data pipeline: scrape → synergy scrape → copy to frontend."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRAPER_DIR = Path(__file__).parent
DATA_DIR = SCRAPER_DIR / "data"
FRONTEND_DATA = SCRAPER_DIR.parent / "frontend" / "src" / "data.json"


def _materially_changed(previous: bytes, current: bytes) -> bool:
	previous_data = json.loads(previous)
	current_data = json.loads(current)
	previous_data.get("meta", {}).pop("scraped_at", None)
	current_data.get("meta", {}).pop("scraped_at", None)
	return previous_data != current_data


def run(cmd: list[str]) -> None:
	print(f"\n$ {' '.join(cmd)}")
	result = subprocess.run(cmd, cwd=SCRAPER_DIR)
	if result.returncode != 0:
		sys.exit(result.returncode)


def main() -> None:
	print("=== Hunt Trait Finder — Data Build ===")
	previous_data = FRONTEND_DATA.read_bytes() if FRONTEND_DATA.exists() else None

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

	if previous_data is not None and not _materially_changed(
		previous_data, FRONTEND_DATA.read_bytes()
	):
		# Keep timestamp tied to actual data updates and avoid empty weekly commits.
		FRONTEND_DATA.write_bytes(previous_data)
		print("\nNo data changes; kept existing frontend data.")

	print("\nDone.")


if __name__ == "__main__":
	main()
