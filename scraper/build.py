#!/usr/bin/env python3
"""Orchestrates the full data pipeline: scrape → enrich → copy to frontend."""

import shutil
import subprocess
import sys
from pathlib import Path

SCRAPER_DIR = Path(__file__).parent
FRONTEND_DATA = SCRAPER_DIR.parent / "frontend" / "src" / "data.json"


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRAPER_DIR)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    print("=== Hunt Trait Finder — Data Build ===")

    print("\n[1/3] Scraping wiki...")
    run([sys.executable, "scrape.py"])

    print("\n[2/3] Enriching synergies...")
    run([sys.executable, "enrich.py"])

    print("\n[3/3] Copying to frontend...")
    src = SCRAPER_DIR / "data" / "enriched.json"
    FRONTEND_DATA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, FRONTEND_DATA)
    print(f"  {src} → {FRONTEND_DATA}")

    print("\nDone.")


if __name__ == "__main__":
    main()
