#!/usr/bin/env python3
"""Scrapes Hunt: Showdown wiki for traits and weapons via the MediaWiki API."""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# wiki.gg is the current, maintained wiki. Fandom is kept only for tools (group pages).
WIKI_API   = "https://huntshowdown.wiki.gg/api.php"
FANDOM_API = "https://huntshowdown.fandom.com/api.php"
DATA_DIR = Path(__file__).parent / "data"

HEADERS = {
    "User-Agent": "HuntTraitsFinder/1.0 (build-script; github.com/linusfr/bayou-traits)"
}

SKIP_PAGES = {
    "Weapons", "Ammunition", "Book of Weapons", "Traits",
    "Melee weapons", "Melee Weapons", "Firearms",
}

# Keywords in trait descriptions that hint at weapon type affinity
WEAPON_TYPE_HINTS = {
    "lever_action": ["lever-action", "lever action", "repeating rifle"],
    "bolt_action": ["bolt-action", "bolt action"],
    "semi_auto": ["semi-auto", "semi-automatic"],
    "revolver": ["revolver", "single-action", "double-action"],
    "pistol": ["pistol", "handgun"],
    "shotgun": ["shotgun", "pump-action"],
    "sniper": ["sniper"],
    "melee": ["melee weapon", "knife", "blade", "sword", "axe", "saber", "hammer", "machete", "bat"],
    "bow": ["bow", "crossbow"],
    "single_shot": ["single-shot", "single shot"],
    "aim_helper": ["aim helper", "throwing range"],
    "healing": ["first aid", "bandage", "vitality shot", "stamina shot", "regeneration shot"],
}

AMMO_NAMES = {"compact", "medium", "long", "shotgun", "sparks", "nitro"}

AMMO_HINTS = {
    "long": ["long ammo", "long-ammo"],
    "medium": ["medium ammo", "medium-ammo"],
    "compact": ["compact ammo", "compact-ammo"],
    "shotgun": ["shotgun ammo", "shotgun shell"],
    "sparks": ["sparks"],
    "nitro": ["nitro express"],
}


async def fetch_category_members(client: httpx.AsyncClient, category: str, api: str = WIKI_API) -> list[str]:
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
        r = await client.get(api, params=params, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        titles.extend(m["title"] for m in data["query"]["categorymembers"])
        if "continue" not in data:
            break
        params.update(data["continue"])
    return titles


async def fetch_page_html(client: httpx.AsyncClient, title: str, api: str = WIKI_API) -> str:
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
    }
    for attempt in range(4):
        try:
            r = await client.get(api, params=params, headers=HEADERS)
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"  Rate limited fetching {title!r}, waiting {wait}s...")
                await asyncio.sleep(wait)
                continue
            if r.status_code != 200:
                return ""
            data = r.json()
            if "error" in data:
                return ""
            return data.get("parse", {}).get("text", {}).get("*", "")
        except Exception as e:
            if attempt < 3:
                await asyncio.sleep(5)
            else:
                print(f"  Failed fetching {title!r}: {e}")
    return ""


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def extract_image_url(soup: BeautifulSoup) -> str:
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.lower().endswith(".png") and ("wiki.gg" in src or "wikia.nocookie.net" in src):
            return re.sub(r"/revision/latest.*", "", src)
    return ""


def parse_druid_infobox(soup: BeautifulSoup) -> dict:
    """Parse wiki.gg's druid-infobox format (div-based, druid-label / druid-data pairs)."""
    fields: dict[str, str] = {}
    # Labels and data are siblings inside druid-item containers
    for item in soup.find_all(class_=re.compile(r"druid-item|pi-item")):
        label_el = item.find(class_=re.compile(r"druid-label|pi-data-label"))
        data_el  = item.find(class_=re.compile(r"druid-data|pi-data-value"))
        if label_el and data_el:
            key = re.sub(r"\s+", " ", label_el.get_text(separator=" ", strip=True)).lower()
            val = re.sub(r"\s+", " ", data_el.get_text(separator=" ", strip=True)).strip()
            if key and val and '{{{' not in val:
                fields[key] = val
    # Fallback: also try adjacent druid-label / druid-data siblings anywhere on page
    if not fields:
        labels = soup.find_all(class_=re.compile(r"druid-label"))
        for lbl in labels:
            key = re.sub(r"\s+", " ", lbl.get_text(separator=" ", strip=True)).lower()
            nxt = lbl.find_next_sibling()
            if nxt:
                val = re.sub(r"\s+", " ", nxt.get_text(separator=" ", strip=True)).strip()
                if key and val and '{{{' not in val:
                    fields[key] = val
    return fields


def parse_infobox_table(soup: BeautifulSoup) -> dict:
    """Extract label→value pairs from any table on the page."""
    fields: dict[str, str] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) == 2:
                key = re.sub(r"\s+", " ", cells[0].get_text(separator=" ", strip=True)).strip().lower()
                val = re.sub(r"\s+", " ", cells[1].get_text(separator=" ", strip=True)).strip()
                if key and val:
                    if '{{{' in val:
                        continue
                    fields[key] = val
    return fields


def first_real_paragraph(soup: BeautifulSoup) -> str:
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(separator=" ", strip=True)).strip()
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

    # Try wiki.gg druid format first, fall back to fandom wikitable
    fields = parse_druid_infobox(soup) or parse_infobox_table(soup)

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
        elif "unlock" in key or "rank" in key:
            m = re.search(r"\d+", val)
            if m:
                rank = int(m.group())
        elif "description" in key or "effect" in key:
            description = val
        elif key == "type":
            # wiki.gg infobox type can be multi-value, e.g. "Burn, Scarce"
            vl = val.lower()
            if "event" in vl:
                trait_type = "event"
            elif "scarce" in vl:
                trait_type = "scarce"

    if not description:
        description = first_real_paragraph(soup)

    if not category:
        desc_lower = description.lower()
        if any(k in desc_lower for k in ['damage', 'attack', 'kill']):
            category = 'offensive'
        elif any(k in desc_lower for k in ['heal', 'health', 'resist', 'reviv', 'protect']):
            category = 'defensive'
        elif any(k in desc_lower for k in ['speed', 'sprint', 'move', 'run', 'walk']):
            category = 'movement'
        else:
            category = 'supportive'

    page_text = soup.get_text().lower()
    # Detect burn trait independently of the primary type classification
    is_burn = (
        "burn" in (fields.get("type", "").lower())
        or "burn trait" in page_text
        or "is burned" in page_text
    )
    if trait_type == "normal" and is_burn:
        pass  # keep normal; is_burn flag carries the information
    elif trait_type == "normal":
        if "scarce" in page_text:
            trait_type = "scarce"

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
        "is_burn": is_burn,
        "image_url": extract_image_url(soup),
        "_weapon_type_hints": weapon_type_hints,
        "_ammo_hints": ammo_hints,
        "weapon_synergies": [],
    }


def parse_weapon(html: str, title: str) -> dict | None:
    # title is "Weapons/Name" or "Weapons/Name/Variant"; normalise to display name
    name = title.removeprefix("Weapons/").replace("/", " ").strip()
    if not html or not name or name in SKIP_PAGES:
        return None
    soup = BeautifulSoup(html, "lxml")

    # Try wiki.gg druid infobox first, fall back to fandom wikitable
    fields = parse_druid_infobox(soup) or parse_infobox_table(soup)

    weapon_type = ""
    size = ""
    ammo = ""
    description = first_real_paragraph(soup)

    for key, val in fields.items():
        if key in ("type", "weapon type", "class", "action"):
            weapon_type = val.lower()
        elif key in ("size", "slot"):
            # wiki.gg uses numeric slot sizes: 4=large, 2=medium, 1=small
            m = re.search(r"\d+", val)
            if m:
                n = int(m.group())
                size = {4: "large", 3: "large", 2: "medium", 1: "small"}.get(n, val.lower())
            else:
                size = val.lower()
        elif "ammo type" in key or "ammunition" in key or "caliber" in key:
            ammo = val.lower().split()[0]  # e.g. "Long Ammo" → "long"
        elif key == "ammo" and not ammo:
            ammo = val.lower()
        elif key == "name" and not ammo:
            # Fandom fallback: "Name" row value may encode the ammo type
            val_lower = val.lower()
            for ammo_name in AMMO_NAMES:
                if ammo_name in val_lower:
                    ammo = ammo_name
                    break

    # Infer weapon type from name + description when the infobox has no type field
    if not weapon_type:
        combined = f"{title.lower()} {description.lower()}"
        matched = [k for k, kws in WEAPON_TYPE_HINTS.items() if any(kw in combined for kw in kws)]
        if matched:
            # Store as space-joined hyphenated forms so enrich.py substring matching works
            weapon_type = " ".join(k.replace("_", "-") for k in matched)

    # Normalise wiki.gg ammo values to our system
    # wiki.gg uses "Shells" for shotguns and "Special" for proprietary ammo
    name_lower = name.lower()
    if ammo == "shells":
        ammo = "shotgun"
    elif ammo in ("special", "oil", ""):
        ammo = ""  # will be resolved by name inference below

    # Hard overrides
    if "sparks" in name_lower:
        ammo = "sparks"
    if name in ("Bomb Lance", "Bomb Launcher"):
        weapon_type = "explosive aim-helper"
        ammo = ""
    if "nitro" in name_lower:
        ammo = "nitro"

    # Infer weapon type from name + description when the infobox has no type field
    if not weapon_type:
        combined = f"{name_lower} {description.lower()}"
        matched = [k for k, kws in WEAPON_TYPE_HINTS.items() if any(kw in combined for kw in kws)]
        if matched:
            weapon_type = " ".join(k.replace("_", "-") for k in matched)

    # Infer ammo from known name patterns when wiki gave "Special"/empty
    if not ammo:
        if any(x in name_lower for x in ["romero", "specter", "homestead", "haymaker", "auto-5", "auto-4", "shredder", "drilling", "rival", "terminus", "slate"]):
            ammo = "shotgun"
        elif any(x in name_lower for x in ["mosin", "krag", "lebel", "martini", "infantry", "berthier", "vetterli", "centennial", "maynard", "1865 carbine", "wildland"]):
            ammo = "long"
        elif any(x in name_lower for x in ["mako", "springfield 1866", "marathon", "frontier", "ranger", "vandal", "mosin obrez"]):
            ammo = "medium"
        elif any(x in name_lower for x in ["dolch", "bornheim", "nagant", "scottfield", "lemat", "derringer", "pax", "new army", "conversion", "1890 cavalry", "uppercut", "winfield m1873"]):
            ammo = "compact"
        elif any(x in name_lower for x in ["bow", "crossbow", "chu ko nu"]):
            ammo = ""  # bows: weapon_class comes from type

    # Infer size from slot count if wiki.gg didn't provide it
    if not size:
        if any(x in name_lower for x in ["rifle", "mosin", "springfield", "lebel", "martini", "sparks", "nitro", "mako", "berthier", "vetterli", "krag", "centennial", "maynard", "infantry", "1865 carbine", "wildland"]):
            size = "large"
        elif any(x in name_lower for x in ["romero", "specter", "drilling", "auto-5", "terminus", "slate", "haymaker", "homestead", "shredder"]):
            size = "medium"
        elif any(x in name_lower for x in ["dolch", "bornheim", "nagant", "scottfield", "lemat", "derringer", "pax", "new army", "conversion", "1890 cavalry", "uppercut"]):
            size = "small"
        elif any(x in name_lower for x in ["knife", "sword", "axe", "hammer", "saber", "machete", "katana", "bat", "lance"]):
            size = "melee"

    # Parse "Key Traits" section (may exist on some wiki pages)
    wiki_synergy_traits = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "key trait" in heading.get_text(strip=True).lower():
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

    # Stable filter category used by the frontend
    _ammo = ammo or "unknown"
    _type = weapon_type or "unknown"
    if _ammo not in ("unknown", ""):
        weapon_class = _ammo
    elif "melee" in _type:
        weapon_class = "melee"
    elif "bow" in _type:
        weapon_class = "bow"
    elif "explosive" in _type or "aim-helper" in _type:
        weapon_class = "launcher"
    else:
        weapon_class = "unknown"

    return {
        "id": slugify(name),
        "name": name,
        "type": _type,
        "size": size or "unknown",
        "ammo": _ammo,
        "weapon_class": weapon_class,
        "description": description,
        "image_url": extract_image_url(soup),
        "_wiki_synergy_traits": wiki_synergy_traits,
        "trait_synergies": [],
    }


TOOL_GROUPS = {
    "Explosives":     "explosive",
    "Fire":           "fire",
    "Knife":          "melee",
    "Deception":      "decoy",
    "Light":          "support",
    "First Aid Kit":  "healing",
    "Healing Shots":  "healing",
    "Poison":         "poison",
    "Choke Bomb":     "poison",
    "Dusters":        "melee",
    "Spyglass":       "support",
    "Stalker Beetle": "decoy",
    "Ammo Box":          "support",
    "Tactical Gadgets":  "explosive",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()



def parse_tool_page(html: str, tool_class: str) -> list[dict]:
    """Parse tool items from a group page using <h2> section boundaries."""
    if not html:
        return []
    from bs4 import NavigableString
    soup = BeautifulSoup(html, "lxml")
    content = soup.find("div", class_="mw-parser-output") or soup

    # Collect document elements grouped by h2 heading (each h2 = one item)
    sections: list[tuple[str, list]] = []
    current_name: str | None = None
    current_els: list = []

    for el in content.children:
        if isinstance(el, NavigableString):
            continue
        if el.name == "h2":
            if current_name:
                sections.append((current_name, current_els))
            raw = re.sub(r"\[.*?\]", "", el.get_text(strip=True)).strip()
            current_name = raw if raw and raw != "Contents" else None
            current_els = []
        elif current_name:
            current_els.append(el)
    if current_name:
        sections.append((current_name, current_els))

    throwable_classes = {"explosive", "fire", "melee", "decoy", "poison"}
    tool_type = f"throwable {tool_class} aim-helper" if tool_class in throwable_classes else tool_class

    tools: list[dict] = []
    for name, els in sections:
        if not name or len(name) > 60:
            continue
        if "not available" in name.lower():
            continue
        description = ""
        cost = 0
        for el in els:
            if el.name == "p" and not description:
                t = clean(el.get_text(separator=" ", strip=True))
                if len(t) > 15 and not t.startswith("["):
                    description = t
            elif el.name == "table":
                for row in el.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) == 2:
                        k = clean(cells[0].get_text(separator=" ", strip=True)).lower()
                        v = clean(cells[1].get_text(separator=" ", strip=True))
                        if k == "cost":
                            m = re.search(r"\d+", v)
                            if m:
                                cost = int(m.group())
        if description:
            tools.append({
                "id": slugify(name),
                "name": name,
                "description": description,
                "cost": cost,
                "tool_class": tool_class,
                "type": tool_type,
                "trait_synergies": [],
            })
    return tools


async def scrape_tools(client: httpx.AsyncClient, sem: asyncio.Semaphore) -> list[dict]:
    tools: list[dict] = []
    seen_ids: set[str] = set()

    async def fetch_group(page: str, tool_class: str) -> None:
        async with sem:
            await asyncio.sleep(0.25)
            html = await fetch_page_html(client, page, api=FANDOM_API)
        for item in parse_tool_page(html, tool_class):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                tools.append(item)

    await asyncio.gather(*[fetch_group(page, tc) for page, tc in TOOL_GROUPS.items()])
    return tools


async def get_patch_version(client: httpx.AsyncClient) -> str:
    # Try wiki.gg updates category first, fall back to fandom
    for api, cat in [(WIKI_API, "Updates"), (FANDOM_API, "Updates")]:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{cat}",
            "cmlimit": "5",
            "cmdir": "desc",
            "cmsort": "timestamp",
            "format": "json",
        }
        try:
            r = await client.get(api, params=params, headers=HEADERS)
            data = r.json()
            for m in data.get("query", {}).get("categorymembers", []):
                match = re.search(r"(\d+\.\d+(?:\.\d+)*)", m["title"])
                if match:
                    return match.group(1)
        except Exception:
            pass
    return "unknown"


async def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(3)

    async def rate_limited_fetch(client: httpx.AsyncClient, title: str, api: str = WIKI_API) -> tuple[str, str]:
        async with sem:
            await asyncio.sleep(0.6)
            html = await fetch_page_html(client, title, api)
            return title, html

    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        print("Detecting patch version...")
        patch = await get_patch_version(client)
        print(f"  Patch: {patch}")

        print("Fetching trait list from wiki.gg...")
        raw_trait_titles = await fetch_category_members(client, "Traits")
        # wiki.gg: traits live at "Traits/Name"; filter out sub-pages and meta pages
        trait_titles = [
            t for t in raw_trait_titles
            if t.startswith("Traits/") and t.count("/") == 1
        ]
        print(f"  Found {len(trait_titles)} trait pages")

        print("Fetching weapon list from wiki.gg...")
        raw_weapon_titles = await fetch_category_members(client, "Weapons")
        # wiki.gg: base weapons at "Weapons/Name" (one slash), variants at "Weapons/Name/Variant" (two slashes)
        weapon_titles = [
            t for t in raw_weapon_titles
            if t.startswith("Weapons/") and t.count("/") in (1, 2)
        ]
        print(f"  Found {len(weapon_titles)} weapon pages ({sum(1 for t in weapon_titles if t.count('/') == 1)} base, {sum(1 for t in weapon_titles if t.count('/') == 2)} variants)")

        print("Scraping trait pages from wiki.gg...")
        trait_results = await asyncio.gather(*[rate_limited_fetch(client, t) for t in trait_titles])
        traits = [r for t, h in trait_results if (r := parse_trait(h, t)) and r["description"]]
        print(f"  Parsed {len(traits)} traits")

        print("Scraping weapon pages from wiki.gg...")
        weapon_results = await asyncio.gather(*[rate_limited_fetch(client, t) for t in weapon_titles])
        weapons = [r for t, h in weapon_results if (r := parse_weapon(h, t))]
        print(f"  Parsed {len(weapons)} weapons")

        print("Scraping tool pages from Fandom (group pages)...")
        tools = await scrape_tools(client, sem)
        print(f"  Parsed {len(tools)} tools")

    wiki_weapon_count = len(weapon_titles)
    wiki_trait_count = len(trait_titles)
    if wiki_weapon_count != len(weapons):
        print(f"\n⚠ Coverage gap: scraped {len(weapons)} weapons but wiki lists {wiki_weapon_count}")
        scraped_names = {w["name"].lower() for w in weapons}
        missing = [t.removeprefix("Weapons/").replace("/", " ") for t in weapon_titles
                   if t.removeprefix("Weapons/").replace("/", " ").lower() not in scraped_names]
        if missing:
            print(f"  Possibly missing: {missing[:10]}")
    if wiki_trait_count != len(traits):
        print(f"\n⚠ Coverage gap: scraped {len(traits)} traits but wiki lists {wiki_trait_count}")
        scraped_trait_names = {t["name"].lower() for t in traits}
        missing_traits = [t.removeprefix("Traits/") for t in trait_titles
                          if t.removeprefix("Traits/").lower() not in scraped_trait_names]
        if missing_traits:
            print(f"  Possibly missing: {missing_traits[:10]}")

    output = {
        "meta": {
            "patch": patch,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "trait_count": len(traits),
            "weapon_count": len(weapons),
            "tool_count": len(tools),
            "wiki_weapon_count": wiki_weapon_count,
            "wiki_trait_count": wiki_trait_count,
        },
        "traits": traits,
        "weapons": weapons,
        "tools": tools,
    }

    out_path = DATA_DIR / "raw.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
