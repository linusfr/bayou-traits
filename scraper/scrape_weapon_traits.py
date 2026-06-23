#!/usr/bin/env python3
"""Scrapes 'Recommended Traits' from each weapon page on huntshowdown.wiki.gg
and rebuilds weapon/trait synergy data from that authoritative source."""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

WIKI_API = "https://huntshowdown.wiki.gg/api.php"
HEADERS = {"User-Agent": "HuntTraitsFinder/1.0 (build-script; github.com/linusfr/bayou-traits)"}

DATA_JSON = Path(__file__).parent.parent / "frontend" / "src" / "data.json"


def trait_name_to_id(name: str) -> str:
	return name.strip().lower().replace(" ", "_").replace("-", "_")


async def fetch_html(client: httpx.AsyncClient, title: str) -> str | None:
	params = {
		"action": "parse",
		"page": title,
		"prop": "text",
		"disablelimitreport": "1",
		"format": "json",
	}
	r = await client.get(WIKI_API, params=params, headers=HEADERS)
	r.raise_for_status()
	data = r.json()
	if "error" in data:
		return None
	return data["parse"]["text"]["*"]


def extract_recommended_traits(html: str) -> list[str]:
	"""Return list of trait IDs from the 'Recommended Traits' section."""
	soup = BeautifulSoup(html, "lxml")
	traits = []
	for heading in soup.find_all(["h2", "h3"]):
		span = heading.find("span", class_="mw-headline")
		if span and "recommended trait" in span.get_text(strip=True).lower():
			ul = heading.find_next_sibling("ul")
			if not ul:
				# sometimes wrapped in a div
				nxt = heading.find_next_sibling()
				if nxt:
					ul = nxt.find("ul")
			if ul:
				for li in ul.find_all("li", recursive=False):
					a = li.find("a")
					if a and "/wiki/Traits/" in a.get("href", ""):
						raw = a.get("href").split("/wiki/Traits/")[-1]
						traits.append(trait_name_to_id(raw.replace("_", " ")))
	return traits


def weapon_name_to_wiki_title(name: str) -> str:
	"""Convert weapon name to wiki page title (Weapons/<Name>)."""
	return "Weapons/" + name.replace(" ", "_")


async def fetch_html_with_retry(client: httpx.AsyncClient, title: str, retries: int = 5) -> str | None:
	for attempt in range(retries):
		try:
			html = await fetch_html(client, title)
			return html
		except httpx.HTTPStatusError as e:
			if e.response.status_code == 429:
				wait = 2 ** (attempt + 2)  # 4s, 8s, 16s, 32s, 64s
				print(f"  429 on {title}, waiting {wait}s…", file=sys.stderr)
				await asyncio.sleep(wait)
			elif e.response.status_code == 404:
				return None
			else:
				print(f"  HTTP {e.response.status_code} on {title}", file=sys.stderr)
				return None
		except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
			if attempt == retries - 1:
				print(f"  ERROR {title}: {e}", file=sys.stderr)
				return None
			await asyncio.sleep(2 ** attempt)
	return None


async def scrape_all(weapons: list[dict], trait_ids: set[str]) -> dict[str, list[str]]:
	"""Returns {weapon_id: [trait_id, ...]} from wiki pages. Sequential to respect rate limits."""
	results: dict[str, list[str]] = {}

	async with httpx.AsyncClient(timeout=60) as client:
		for w in weapons:
			wid = w["id"]
			name = w["name"]
			title = weapon_name_to_wiki_title(name)

			html = await fetch_html_with_retry(client, title)
			if html is None:
				# Wiki uses subpage format for variants: Weapons/Base/Variant
				# Try splitting off the last word as a subpage before falling back to base page
				parts = name.split()
				for drop in range(1, len(parts)):
					base = " ".join(parts[:-drop])
					suffix = "_".join(parts[-drop:])
					subpage_title = f"Weapons/{base.replace(' ', '_')}/{suffix}"
					html = await fetch_html_with_retry(client, subpage_title)
					if html is not None:
						break
					# Also try the plain underscore form one more time (shouldn't be needed but defensive)
					base_title = weapon_name_to_wiki_title(base)
					html = await fetch_html_with_retry(client, base_title)
					if html is not None:
						break

			if html is None:
				print(f"  MISS  {wid} ({name})", file=sys.stderr)
				results[wid] = []
				await asyncio.sleep(0.5)
				continue

			traits_found = extract_recommended_traits(html)
			valid = [t for t in traits_found if t in trait_ids]
			unknown = [t for t in traits_found if t not in trait_ids]
			if unknown:
				print(f"  UNKNOWN traits on {name}: {unknown}", file=sys.stderr)
			print(f"  OK    {name:50} → {valid}", file=sys.stderr)
			results[wid] = valid
			await asyncio.sleep(0.4)  # polite delay between requests

	return results


def rebuild_synergies(data: dict, wiki_map: dict[str, list[str]]) -> dict:
	"""Replace weapon/trait synergies using wiki_map as ground truth.
	Keeps existing reason text where synergies survive."""
	trait_idx = {t["id"]: t for t in data["traits"]}
	weapon_idx = {w["id"]: w for w in data["weapons"]}

	# Build existing reason lookup: (weapon_id, trait_id) -> reason
	existing_reasons: dict[tuple, str] = {}
	for w in data["weapons"]:
		for s in w.get("trait_synergies", []):
			existing_reasons[(w["id"], s["trait_id"])] = s.get("reason", "")
	for t in data["traits"]:
		for s in t.get("weapon_synergies", []):
			existing_reasons[(s["weapon_id"], t["id"])] = s.get("reason", "")

	# Clear all weapon←→trait synergies
	for w in data["weapons"]:
		w["trait_synergies"] = []
	for t in data["traits"]:
		t["weapon_synergies"] = []

	added = 0
	skipped = 0
	for wid, trait_ids in wiki_map.items():
		w = weapon_idx.get(wid)
		if not w:
			continue
		if not trait_ids:
			skipped += 1
			continue
		for tid in trait_ids:
			t = trait_idx.get(tid)
			if not t:
				continue
			reason = (
				existing_reasons.get((wid, tid))
				or existing_reasons.get((tid, wid))
				or ""
			)
			w["trait_synergies"].append({"trait_id": tid, "reason": reason})
			t["weapon_synergies"].append({"weapon_id": wid, "reason": reason})
			added += 1

	print(f"\nRebuilt: {added} synergies added, {skipped} weapons with no wiki traits", file=sys.stderr)
	return data


async def main():
	data = json.loads(DATA_JSON.read_text())
	trait_ids = {t["id"] for t in data["traits"]}
	weapons = data["weapons"]

	print(f"Scraping {len(weapons)} weapon pages…", file=sys.stderr)
	wiki_map = await scrape_all(weapons, trait_ids)

	data = rebuild_synergies(data, wiki_map)

	DATA_JSON.write_text(json.dumps(data, indent="\t"))
	print("Done — data.json updated.", file=sys.stderr)


if __name__ == "__main__":
	asyncio.run(main())
