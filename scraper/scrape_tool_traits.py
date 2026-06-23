#!/usr/bin/env python3
"""Scrapes 'Recommended Traits' from each consumable/tool page on huntshowdown.wiki.gg
and rebuilds tool/trait synergy data from that authoritative source."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

WIKI_API = "https://huntshowdown.wiki.gg/api.php"
HEADERS = {"User-Agent": "HuntTraitsFinder/1.0 (build-script; github.com/linusfr/bayou-traits)"}

DATA_JSON = Path(__file__).parent.parent / "frontend" / "src" / "data.json"

# Full wiki page title overrides (tool_id → exact "namespace/Title" for the MediaWiki API)
WIKI_TITLE_OVERRIDES = {
	"knife":                    "Tools/Knife",
	"heavy_knife":              "Tools/Heavy_Knife",
	"throwing_knives":          "Tools/Throwing_Knives",
	"throwing_axes":            "Tools/Throwing_Axes",
	"throwing_spear":           "Tools/Throwing_Spear",
	"dusters":                  "Tools/Dusters",
	"knuckle_knife":            "Tools/Knuckle_Knife",
	"decoys":                   "Tools/Decoys",
	"blank_fire_decoys":        "Tools/Blank_Fire_Decoys",
	"decoy_fuses":              "Tools/Decoy_Fuses",
	"alert_trip_mine":          "Tools/Alert_Trip_Mines",
	"poison_trip_mine":         "Tools/Poison_Trip_Mines",
	"concertina_trip_mine":     "Tools/Concertina_Trip_Mines",
	"bear_traps":               "Tools/Bear_Traps",
	"fusees":                   "Tools/Fusees",
	"flare_pistol":             "Tools/Flare_Pistol",
	"first_aid_kit":            "Tools/First_Aid_Kit",
}


def trait_name_to_id(name: str) -> str:
	return name.strip().lower().replace(" ", "_").replace("-", "_")


def tool_name_to_wiki_title(name: str) -> str:
	return "Consumables/" + name.replace(" ", "_").replace("(", "(").replace(")", ")")


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


async def fetch_html_with_retry(client: httpx.AsyncClient, title: str, retries: int = 5) -> str | None:
	for attempt in range(retries):
		try:
			return await fetch_html(client, title)
		except httpx.HTTPStatusError as e:
			if e.response.status_code == 429:
				wait = 2 ** (attempt + 2)
				print(f"  429 on {title}, waiting {wait}s…", file=sys.stderr)
				await asyncio.sleep(wait)
			else:
				return None
		except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
			if attempt == retries - 1:
				print(f"  ERROR {title}: {e}", file=sys.stderr)
				return None
			await asyncio.sleep(2 ** attempt)
	return None


def extract_recommended_traits(html: str) -> list[str]:
	soup = BeautifulSoup(html, "lxml")
	traits = []
	for heading in soup.find_all(["h2", "h3"]):
		span = heading.find("span", class_="mw-headline")
		if span and "recommended trait" in span.get_text(strip=True).lower():
			ul = heading.find_next_sibling("ul")
			if not ul:
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


async def scrape_all(tools: list[dict], trait_ids: set[str]) -> dict[str, list[str]]:
	results: dict[str, list[str]] = {}

	async with httpx.AsyncClient(timeout=60) as client:
		for tool in tools:
			tid = tool["id"]
			name = tool["name"]

			# Use explicit override if available, else default to Consumables/ prefix
			if tid in WIKI_TITLE_OVERRIDES:
				title = WIKI_TITLE_OVERRIDES[tid]
			else:
				title = tool_name_to_wiki_title(name)

			html = await fetch_html_with_retry(client, title)

			# Fallback: try Tools/ prefix if Consumables/ missed
			if html is None and title.startswith("Consumables/"):
				alt = "Tools/" + title[len("Consumables/"):]
				html = await fetch_html_with_retry(client, alt)

			if html is None:
				print(f"  MISS  {tid} ({name})", file=sys.stderr)
				results[tid] = []
				await asyncio.sleep(0.4)
				continue

			traits_found = extract_recommended_traits(html)
			valid = [t for t in traits_found if t in trait_ids]
			unknown = [t for t in traits_found if t not in trait_ids]
			if unknown:
				print(f"  UNKNOWN traits on {name}: {unknown}", file=sys.stderr)
			print(f"  OK    {name:45} → {valid}", file=sys.stderr)
			results[tid] = valid
			await asyncio.sleep(0.4)

	return results


def rebuild_tool_synergies(data: dict, wiki_map: dict[str, list[str]]) -> dict:
	trait_idx = {t["id"]: t for t in data["traits"]}
	tool_idx  = {t["id"]: t for t in data["tools"]}

	# Preserve existing reasons
	existing_reasons: dict[tuple, str] = {}
	for tool in data["tools"]:
		for s in tool.get("trait_synergies", []):
			existing_reasons[(tool["id"], s["trait_id"])] = s.get("reason", "")
	for t in data["traits"]:
		for s in t.get("tool_synergies", []):
			existing_reasons[(s["tool_id"], t["id"])] = s.get("reason", "")

	# Clear all tool↔trait synergies
	for tool in data["tools"]:
		tool["trait_synergies"] = []
	for t in data["traits"]:
		t["tool_synergies"] = []

	added = 0
	for tool_id, trait_ids in wiki_map.items():
		tool = tool_idx.get(tool_id)
		if not tool or not trait_ids:
			continue
		for tid in trait_ids:
			t = trait_idx.get(tid)
			if not t:
				continue
			reason = (
				existing_reasons.get((tool_id, tid))
				or existing_reasons.get((tid, tool_id))
				or ""
			)
			tool["trait_synergies"].append({"trait_id": tid, "reason": reason})
			t["tool_synergies"].append({"tool_id": tool_id, "reason": reason})
			added += 1

	print(f"\nRebuilt: {added} tool synergies", file=sys.stderr)
	return data


async def main():
	data = json.loads(DATA_JSON.read_text())
	trait_ids = {t["id"] for t in data["traits"]}
	tools = data["tools"]

	print(f"Scraping {len(tools)} tool/consumable pages…", file=sys.stderr)
	wiki_map = await scrape_all(tools, trait_ids)

	data = rebuild_tool_synergies(data, wiki_map)
	DATA_JSON.write_text(json.dumps(data, indent="\t"))
	print("Done — data.json updated.", file=sys.stderr)


if __name__ == "__main__":
	asyncio.run(main())
