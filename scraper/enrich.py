#!/usr/bin/env python3
"""
Enriches raw scraped data with trait-weapon synergy reasoning via DeepSeek.
Reads scraper/data/raw.json → writes scraper/data/enriched.json.
"""

import asyncio
import json
import os
from pathlib import Path

from openai import AsyncOpenAI

DATA_DIR = Path(__file__).parent / "data"
RAW_PATH = DATA_DIR / "raw.json"
OUT_PATH = DATA_DIR / "enriched.json"

DEEPSEEK_BASE = "https://api.deepseek.com"
MODEL = "deepseek-chat"

BATCH_SIZE = 8
AUGMENT_BATCH = 15

AUGMENT_PROMPT = """\
You are an expert at Hunt: Showdown. For each trait below, improve the description \
by adding specific numbers, percentages, or durations where you know them from the game. \
Keep changes minimal — only add concrete mechanics you are confident about. \
If you don't know the exact values, return the original description unchanged.

{traits}

Respond ONLY with valid JSON: {{"traits": [{{"id": "...", "description": "..."}}]}}
"""

ENRICH_PROMPT = """\
You are an expert at Hunt: Showdown. For each trait-weapon pair below, write \
a single sentence (max 25 words) explaining concretely WHY that trait benefits \
that specific weapon. Focus on game mechanics, not flavor.

{pairs}

Respond ONLY with valid JSON: {{"pairs": [{{"weapon_id": "...", "trait_id": "...", "reason": "..."}}]}}
"""

ENRICH_TOOL_PROMPT = """\
You are an expert at Hunt: Showdown. For each trait-tool pair below, write \
a single sentence (max 25 words) explaining concretely WHY that trait benefits \
that specific consumable tool. Focus on game mechanics, not flavor.

{pairs}

Respond ONLY with valid JSON: {{"pairs": [{{"tool_id": "...", "trait_id": "...", "reason": "..."}}]}}
"""


def get_client() -> AsyncOpenAI:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")
    return AsyncOpenAI(api_key=key, base_url=DEEPSEEK_BASE)


def build_index(items: list, key: str = "id") -> dict:
    return {item[key]: item for item in items}


def find_wiki_pairs(traits: list, weapons: list) -> list[tuple[str, str, str]]:
    """Extract (weapon_id, trait_id, raw_reason) from wiki Key Traits data."""
    trait_by_name = {t["name"].lower(): t["id"] for t in traits}
    pairs: list[tuple[str, str, str]] = []

    for weapon in weapons:
        for entry in weapon.get("_wiki_synergy_traits", []):
            t_name = entry["trait_name"].lower().strip()
            t_id = trait_by_name.get(t_name)
            if not t_id:
                # Partial match fallback
                for name, tid in trait_by_name.items():
                    if t_name in name or name in t_name:
                        t_id = tid
                        break
            if t_id:
                pairs.append((weapon["id"], t_id, entry.get("reason", "")))

    return pairs


def find_description_pairs(
    traits: list, weapons: list, known: set[tuple[str, str]]
) -> list[tuple[str, str, str]]:
    """Infer synergies from keyword matches in trait descriptions."""
    pairs: list[tuple[str, str, str]] = []

    for trait in traits:
        type_hints = set(trait.get("_weapon_type_hints", []))
        ammo_hints = set(trait.get("_ammo_hints", []))
        if not type_hints and not ammo_hints:
            continue

        for weapon in weapons:
            if (weapon["id"], trait["id"]) in known:
                continue
            w_ammo = weapon.get("ammo", "").lower()
            w_type = weapon.get("type", "").lower()

            type_match = any(
                hint in w_type or hint.replace("_", " ") in w_type or hint.replace("_", "-") in w_type
                for hint in type_hints
            )
            ammo_match = w_ammo in ammo_hints

            if type_match or ammo_match:
                pairs.append((weapon["id"], trait["id"], ""))

    return pairs


def find_tool_pairs(
    traits: list, tools: list, known: set[tuple[str, str]]
) -> list[tuple[str, str, str]]:
    """Infer trait-tool synergies from keyword matches against tool type field."""
    pairs: list[tuple[str, str, str]] = []

    for trait in traits:
        type_hints = set(trait.get("_weapon_type_hints", []))
        if not type_hints:
            continue

        for tool in tools:
            if (tool["id"], trait["id"]) in known:
                continue
            t_type = tool.get("type", "").lower()

            type_match = any(
                hint in t_type or hint.replace("_", " ") in t_type or hint.replace("_", "-") in t_type
                for hint in type_hints
            )

            if type_match:
                pairs.append((tool["id"], trait["id"], ""))

    return pairs


async def enrich_tool_batch(
    client: AsyncOpenAI,
    batch: list[tuple[str, str, str]],
    tool_idx: dict,
    trait_idx: dict,
) -> list[dict]:
    lines = []
    for t_id, tr_id, existing in batch:
        t = tool_idx.get(t_id, {})
        tr = trait_idx.get(tr_id, {})
        note = f' Existing note: "{existing}"' if existing else ""
        lines.append(
            f'- tool_id="{t_id}" tool="{t.get("name", t_id)}" '
            f'(class: {t.get("tool_class", "?")})\n'
            f'  trait_id="{tr_id}" trait="{tr.get("name", tr_id)}": '
            f'"{tr.get("description", "")}"{note}'
        )

    prompt = ENRICH_TOOL_PROMPT.format(pairs="\n".join(lines))

    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("pairs", [])
    except Exception as e:
        print(f"  Warning: tool batch failed ({e}), using raw reasons")
        return [{"tool_id": t, "trait_id": tr, "reason": r or "Synergy noted."} for t, tr, r in batch]


async def enrich_batch(
    client: AsyncOpenAI,
    batch: list[tuple[str, str, str]],
    weapon_idx: dict,
    trait_idx: dict,
) -> list[dict]:
    lines = []
    for w_id, t_id, existing in batch:
        w = weapon_idx.get(w_id, {})
        t = trait_idx.get(t_id, {})
        note = f' Existing note: "{existing}"' if existing else ""
        lines.append(
            f'- weapon_id="{w_id}" weapon="{w.get("name", w_id)}" '
            f'({w.get("ammo", "?")} ammo, {w.get("type", "?")})\n'
            f'  trait_id="{t_id}" trait="{t.get("name", t_id)}": '
            f'"{t.get("description", "")}"{note}'
        )

    prompt = ENRICH_PROMPT.format(pairs="\n".join(lines))

    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("pairs", [])
    except Exception as e:
        print(f"  Warning: batch failed ({e}), using raw reasons")
        return [{"weapon_id": w, "trait_id": t, "reason": r or "Synergy noted in wiki."} for w, t, r in batch]


async def augment_descriptions(
    client: AsyncOpenAI,
    traits: list,
) -> None:
    """Ask DeepSeek to add specific numbers/percentages to vague trait descriptions."""
    print(f"\nAugmenting trait descriptions ({len(traits)} traits)...")
    for i in range(0, len(traits), AUGMENT_BATCH):
        batch = traits[i : i + AUGMENT_BATCH]
        lines = "\n".join(
            f'- id="{t["id"]}" name="{t["name"]}": "{t["description"]}"'
            for t in batch
        )
        prompt = AUGMENT_PROMPT.format(traits=lines)
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            by_id = {t["id"]: t["description"] for t in result.get("traits", [])}
            for trait in batch:
                if trait["id"] in by_id and by_id[trait["id"]]:
                    trait["description"] = by_id[trait["id"]]
        except Exception as e:
            print(f"  Warning: augment batch failed ({e})")
        await asyncio.sleep(0.4)


async def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"{RAW_PATH} not found — run scrape.py first")

    data = json.loads(RAW_PATH.read_text())
    traits: list = data["traits"]
    weapons: list = data["weapons"]
    tools: list = data.get("tools", [])

    weapon_idx = build_index(weapons)
    trait_idx = build_index(traits)
    tool_idx = build_index(tools)

    print("Building synergy pairs from wiki data...")
    wiki_pairs = find_wiki_pairs(traits, weapons)
    print(f"  Wiki-confirmed: {len(wiki_pairs)}")

    known = {(w, t) for w, t, _ in wiki_pairs}
    desc_pairs = find_description_pairs(traits, weapons, known)
    print(f"  Description-inferred: {len(desc_pairs)}")

    all_pairs = wiki_pairs + desc_pairs
    print(f"  Total weapon pairs: {len(all_pairs)}")

    print("Building trait-tool synergy pairs...")
    tool_known: set[tuple[str, str]] = set()
    tool_pairs = find_tool_pairs(traits, tools, tool_known)
    print(f"  Tool pairs: {len(tool_pairs)}")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    enriched_entries: list[dict] = []
    enriched_tool_entries: list[dict] = []

    if api_key:
        client = get_client()
        n_batches = (len(all_pairs) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\nEnriching {len(all_pairs)} weapon pairs via DeepSeek ({n_batches} batches)...")
        for i in range(0, len(all_pairs), BATCH_SIZE):
            batch = all_pairs[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{n_batches}...")
            results = await enrich_batch(client, batch, weapon_idx, trait_idx)
            enriched_entries.extend(results)
            await asyncio.sleep(0.4)

        n_tool_batches = (len(tool_pairs) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\nEnriching {len(tool_pairs)} tool pairs via DeepSeek ({n_tool_batches} batches)...")
        for i in range(0, len(tool_pairs), BATCH_SIZE):
            batch = tool_pairs[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{n_tool_batches}...")
            results = await enrich_tool_batch(client, batch, tool_idx, trait_idx)
            enriched_tool_entries.extend(results)
            await asyncio.sleep(0.4)
    else:
        print("\nNo DEEPSEEK_API_KEY set — skipping LLM enrichment, using raw reasons")
        enriched_entries = [
            {"weapon_id": w, "trait_id": t, "reason": r or ""}
            for w, t, r in all_pairs
        ]
        enriched_tool_entries = [
            {"tool_id": tl, "trait_id": tr, "reason": r or ""}
            for tl, tr, r in tool_pairs
        ]

    # Build final weapon synergy maps
    weapon_syns: dict[str, list] = {w["id"]: [] for w in weapons}
    trait_weapon_syns: dict[str, list] = {t["id"]: [] for t in traits}

    for entry in enriched_entries:
        w_id = entry.get("weapon_id", "")
        t_id = entry.get("trait_id", "")
        reason = entry.get("reason", "").strip()
        if w_id in weapon_syns and t_id in trait_idx:
            weapon_syns[w_id].append({"trait_id": t_id, "reason": reason})
        if t_id in trait_weapon_syns and w_id in weapon_idx:
            trait_weapon_syns[t_id].append({"weapon_id": w_id, "reason": reason})

    for weapon in weapons:
        weapon["trait_synergies"] = weapon_syns.get(weapon["id"], [])
        weapon.pop("_wiki_synergy_traits", None)

    # Build final tool synergy maps
    tool_syns: dict[str, list] = {t["id"]: [] for t in tools}
    trait_tool_syns: dict[str, list] = {t["id"]: [] for t in traits}

    for entry in enriched_tool_entries:
        tl_id = entry.get("tool_id", "")
        tr_id = entry.get("trait_id", "")
        reason = entry.get("reason", "").strip()
        if tl_id in tool_syns and tr_id in trait_idx:
            tool_syns[tl_id].append({"trait_id": tr_id, "reason": reason})
        if tr_id in trait_tool_syns and tl_id in tool_idx:
            trait_tool_syns[tr_id].append({"tool_id": tl_id, "reason": reason})

    for tool in tools:
        tool["trait_synergies"] = tool_syns.get(tool["id"], [])

    for trait in traits:
        trait["weapon_synergies"] = trait_weapon_syns.get(trait["id"], [])
        trait["tool_synergies"] = trait_tool_syns.get(trait["id"], [])
        trait.pop("_weapon_type_hints", None)
        trait.pop("_ammo_hints", None)

    if api_key:
        client = get_client()
        await augment_descriptions(client, traits)

    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\nSaved enriched data to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
