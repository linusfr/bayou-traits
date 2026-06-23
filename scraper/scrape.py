#!/usr/bin/env python3
"""Scrapes Hunt: Showdown wiki for traits and weapons via the MediaWiki API."""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

WIKI_API = "https://huntshowdown.fandom.com/api.php"
DATA_DIR = Path(__file__).parent / "data"

HEADERS = {
    "User-Agent": "HuntTraitsFinder/1.0 (build-script; github.com/yourusername/hunt-traits)"
}

SKIP_PAGES = {
    "Weapons", "Ammunition", "Book of Weapons", "Traits",
    "Melee weapons", "Melee Weapons", "Firearms",
}

# Keywords in trait descriptions that hint at weapon type affinity
WEAPON_TYPE_HINTS = {
    "lever_action": ["lever-action", "lever action"],
    "bolt_action": ["bolt-action", "bolt action"],
    "semi_auto": ["semi-auto", "semi-automatic"],
    "revolver": ["revolver"],
    "pistol": ["pistol"],
    "shotgun": ["shotgun"],
    "sniper": ["sniper"],
    "melee": ["melee weapon", "knife", "blade", "axe", "saber", "hammer"],
    "bow": ["bow", "crossbow"],
    "single_shot": ["single-shot", "single shot"],
}

AMMO_HINTS = {
    "long": ["long ammo", "long-ammo"],
    "medium": ["medium ammo", "medium-ammo"],
    "compact": ["compact ammo", "compact-ammo"],
    "shotgun": ["shotgun ammo", "shotgun shell"],
    "sparks": ["sparks"],
    "nitro": ["nitro express"],
}


async def fetch_category_members(client: httpx.AsyncClient, category: str) -> list[str]:
    titles = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "500",
        "cmnamespace": "0",
        "format": "json",
    }
    while True:
        r = await client.get(WIKI_API, params=params, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        titles.extend(m["title"] for m in data["query"]["categorymembers"])
        if "continue" not in data:
            break
        params.update(data["continue"])
    return titles


async def fetch_page_html(client: httpx.AsyncClient, title: str) -> str:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }
    r = await client.get(WIKI_API, params=params, headers=HEADERS)
    if r.status_code != 200:
        return ""
    data = r.json()
    if "error" in data:
        return ""
    return data.get("parse", {}).get("text", {}).get("*", "")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def extract_image_url(soup: BeautifulSoup) -> str:
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "static.wikia.nocookie.net" in src and ".png" in src.lower():
            # Strip revision suffix to get clean URL
            return re.sub(r"/revision/latest.*", "", src)
    return ""


def parse_infobox_table(soup: BeautifulSoup) -> dict:
    """Extract label→value pairs from any table on the page."""
    fields: dict[str, str] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).lower()
                val = cells[1].get_text(strip=True)
                if key and val:
                    fields[key] = val
    return fields


def first_real_paragraph(soup: BeautifulSoup) -> str:
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 20 and not text.startswith("["):
            return text
    return ""


def parse_trait(html: str, title: str) -> dict | None:
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    name = title.removeprefix("Traits/").strip()
    if not name:
        return None

    fields = parse_infobox_table(soup)

    description = ""
    cost = 0
    rank = 0
    category = ""
    trait_type = "normal"

    for key, val in fields.items():
        if "category" in key:
            category = val.lower()
        elif key in ("cost", "upgrade points", "points"):
            m = re.search(r"\d+", val)
            if m:
                cost = int(m.group())
        elif "rank" in key:
            m = re.search(r"\d+", val)
            if m:
                rank = int(m.group())
        elif "description" in key or "effect" in key:
            description = val

    if not description:
        description = first_real_paragraph(soup)

    page_text = soup.get_text().lower()
    if "burn trait" in page_text or "is burned" in page_text:
        trait_type = "burn"
    elif "scarce" in page_text:
        trait_type = "scarce"
    elif "catalyst" in page_text:
        trait_type = "catalyst"

    desc_lower = description.lower()
    weapon_type_hints = [wt for wt, kws in WEAPON_TYPE_HINTS.items() if any(k in desc_lower for k in kws)]
    ammo_hints = [at for at, kws in AMMO_HINTS.items() if any(k in desc_lower for k in kws)]

    return {
        "id": slugify(name),
        "name": name,
        "description": description,
        "cost": cost,
        "rank": rank,
        "category": category or "unknown",
        "trait_type": trait_type,
        "image_url": extract_image_url(soup),
        "_weapon_type_hints": weapon_type_hints,
        "_ammo_hints": ammo_hints,
        "weapon_synergies": [],
    }


def parse_weapon(html: str, title: str) -> dict | None:
    if not html or title in SKIP_PAGES:
        return None
    soup = BeautifulSoup(html, "lxml")

    fields = parse_infobox_table(soup)

    weapon_type = ""
    size = ""
    ammo = ""
    description = first_real_paragraph(soup)

    for key, val in fields.items():
        if key in ("type", "weapon type", "class", "action"):
            weapon_type = val.lower()
        elif key in ("size", "slot", "category"):
            size = val.lower()
        elif "ammo" in key or "ammunition" in key or "caliber" in key:
            ammo = val.lower()

    # Infer size from weapon type if missing
    if not size:
        name_lower = title.lower()
        if any(x in name_lower for x in ["rifle", "mosin", "springfield", "lebel", "martini", "sparks", "nitro", "mako", "berthier", "vetterli", "krag", "winfield m18", "winfield 1893"]):
            size = "large"
        elif any(x in name_lower for x in ["romero", "specter", "drilling", "auto-5", "terminus", "1893 slate"]):
            size = "medium"
        elif any(x in name_lower for x in ["pistol", "dolch", "bornheim", "nagant", "caldwell", "scottfield", "lemat", "derringer", "pax", "new army"]):
            size = "small"
        elif any(x in name_lower for x in ["knife", "sword", "axe", "hammer", "saber", "machete", "katana", "bat", "lance"]):
            size = "melee"

    # Infer ammo from known weapon names if not found
    if not ammo:
        name_lower = title.lower()
        if any(x in name_lower for x in ["sparks"]):
            ammo = "sparks"
        elif any(x in name_lower for x in ["nitro"]):
            ammo = "nitro"
        elif any(x in name_lower for x in ["romero", "specter", "auto-5", "drilling", "rival", "terminus", "1893 slate"]):
            ammo = "shotgun"
        elif any(x in name_lower for x in ["mosin", "springfield krag", "lebel", "martini", "winfield m1876", "berthier", "vetterli"]):
            ammo = "long"
        elif any(x in name_lower for x in ["winfield m1873", "mako", "springfield 1866", "caldwell marathon", "winfield 1893"]):
            ammo = "medium"
        elif any(x in name_lower for x in ["dolch", "bornheim", "nagant", "caldwell", "scottfield", "lemat", "derringer", "pax", "new army"]):
            ammo = "compact"

    # Parse "Key Traits" section from weapon wiki pages
    wiki_synergy_traits = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "key trait" in heading.get_text(strip=True).lower():
            # Walk siblings to find the next ul
            sibling = heading.find_next_sibling()
            while sibling and sibling.name not in ("ul", "h2", "h3"):
                sibling = sibling.find_next_sibling()
            if sibling and sibling.name == "ul":
                for li in sibling.find_all("li", recursive=False):
                    link = li.find("a")
                    trait_name = link.get_text(strip=True) if link else li.get_text(strip=True).split(":")[0].strip()
                    li_text = li.get_text(strip=True)
                    reason = li_text[len(trait_name):].lstrip(": ").strip()
                    if trait_name:
                        wiki_synergy_traits.append({"trait_name": trait_name, "reason": reason})

    return {
        "id": slugify(title),
        "name": title,
        "type": weapon_type or "unknown",
        "size": size or "unknown",
        "ammo": ammo or "unknown",
        "description": description,
        "image_url": extract_image_url(soup),
        "_wiki_synergy_traits": wiki_synergy_traits,
        "trait_synergies": [],
    }


async def get_patch_version(client: httpx.AsyncClient) -> str:
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Updates",
        "cmlimit": "5",
        "cmdir": "desc",
        "cmsort": "timestamp",
        "format": "json",
    }
    try:
        r = await client.get(WIKI_API, params=params, headers=HEADERS)
        data = r.json()
        for m in data["query"]["categorymembers"]:
            match = re.search(r"(\d+\.\d+(?:\.\d+)*)", m["title"])
            if match:
                return match.group(1)
    except Exception as e:
        print(f"  Warning: could not detect patch version: {e}")
    return "unknown"


async def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(5)

    async def rate_limited_fetch(client: httpx.AsyncClient, title: str) -> tuple[str, str]:
        async with sem:
            await asyncio.sleep(0.25)
            html = await fetch_page_html(client, title)
            # Some traits live at "Traits/Name" rather than "Name"
            if not html and "/" not in title:
                html = await fetch_page_html(client, f"Traits/{title}")
            return title, html

    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        print("Detecting patch version...")
        patch = await get_patch_version(client)
        print(f"  Patch: {patch}")

        print("Fetching trait list...")
        raw_trait_titles = await fetch_category_members(client, "Traits")
        trait_titles = [
            t for t in raw_trait_titles
            if t not in SKIP_PAGES and not t.startswith("Template:")
        ]
        print(f"  Found {len(trait_titles)} trait entries")

        print("Fetching weapon list...")
        weapon_titles = await fetch_category_members(client, "Weapons")
        weapon_titles = [
            t for t in weapon_titles
            if t not in SKIP_PAGES and not t.startswith("Template:")
        ]
        print(f"  Found {len(weapon_titles)} weapon entries")

        print("Scraping trait pages...")
        trait_results = await asyncio.gather(*[rate_limited_fetch(client, t) for t in trait_titles])
        traits = [r for t, h in trait_results if (r := parse_trait(h, t)) and r["description"]]
        print(f"  Parsed {len(traits)} traits")

        print("Scraping weapon pages...")
        weapon_results = await asyncio.gather(*[rate_limited_fetch(client, t) for t in weapon_titles])
        weapons = [r for t, h in weapon_results if (r := parse_weapon(h, t))]
        print(f"  Parsed {len(weapons)} weapons")

    output = {
        "meta": {
            "patch": patch,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "trait_count": len(traits),
            "weapon_count": len(weapons),
        },
        "traits": traits,
        "weapons": weapons,
    }

    out_path = DATA_DIR / "raw.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
