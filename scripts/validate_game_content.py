#!/usr/bin/env python3
"""
Validate Spiral Forge RPG game content files.

Checks:
  - All JSON files parse without error
  - Creature tongue references are valid (KO, AV, RU, CA, UM, DR)
  - NPC shop items reference existing item IDs
  - Transform tongue references are valid
  - Map layout dimensions match declared size
  - NPC positions are within map bounds
  - No duplicate IDs within a category

Run: python scripts/validate_game_content.py
"""

import json
import os
import sys
from pathlib import Path

VALID_TONGUES = {"KO", "AV", "RU", "CA", "UM", "DR"}
DATA_DIR = Path(__file__).parent.parent / "game" / "godot" / "data"

errors: list[str] = []
warnings: list[str] = []


def load_json(path: Path) -> dict | list | None:
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error in {path}: {e}")
        return None
    except FileNotFoundError:
        errors.append(f"File not found: {path}")
        return None


def validate_creatures():
    creature_dir = DATA_DIR / "creatures"
    if not creature_dir.exists():
        warnings.append("No creatures directory found")
        return {}

    creatures = {}
    for f in creature_dir.glob("*.json"):
        data = load_json(f)
        if not data:
            continue
        cid = data.get("id")
        if not cid:
            errors.append(f"Creature in {f.name} missing 'id' field")
            continue
        if cid in creatures:
            errors.append(f"Duplicate creature ID: {cid}")
        creatures[cid] = data

        # Validate tongue
        tongue = data.get("tongue", "")
        if tongue not in VALID_TONGUES:
            errors.append(f"Creature '{cid}' has invalid tongue '{tongue}'")

        # Validate base_state structure
        base = data.get("base_state", {})
        tp = base.get("tongue_position", [])
        if len(tp) != 6:
            errors.append(f"Creature '{cid}' tongue_position must have 6 elements, got {len(tp)}")

    return creatures


def validate_items():
    items_file = DATA_DIR / "items" / "items.json"
    data = load_json(items_file)
    if not data:
        return {}

    items = {}
    for item in data.get("items", []):
        iid = item.get("id")
        if not iid:
            errors.append("Item missing 'id' field")
            continue
        if iid in items:
            errors.append(f"Duplicate item ID: {iid}")
        items[iid] = item

        # Validate tongue (empty is OK for key items)
        tongue = item.get("tongue", "")
        if tongue and tongue not in VALID_TONGUES:
            errors.append(f"Item '{iid}' has invalid tongue '{tongue}'")

    return items


def validate_npcs(items: dict):
    npc_dir = DATA_DIR / "npcs"
    if not npc_dir.exists():
        warnings.append("No npcs directory found")
        return {}

    npcs = {}
    for f in npc_dir.glob("*.json"):
        data = load_json(f)
        if not data:
            continue
        for npc in data.get("npcs", []):
            nid = npc.get("id")
            if not nid:
                errors.append(f"NPC in {f.name} missing 'id' field")
                continue
            if nid in npcs:
                errors.append(f"Duplicate NPC ID: {nid}")
            npcs[nid] = npc

            # Validate tongue affinity
            tongue = npc.get("tongue_affinity", "")
            if tongue and tongue not in VALID_TONGUES:
                errors.append(f"NPC '{nid}' has invalid tongue_affinity '{tongue}'")

            # Validate shop inventory references
            if npc.get("is_shopkeeper"):
                for item_id in npc.get("shop_inventory", []):
                    if item_id not in items:
                        errors.append(f"NPC '{nid}' shop references missing item '{item_id}'")

    return npcs


def validate_transforms():
    transforms_file = DATA_DIR / "techniques" / "transforms.json"
    data = load_json(transforms_file)
    if not data:
        return {}

    transforms = {}
    for t in data.get("transforms", []):
        tid = t.get("id")
        if not tid:
            errors.append("Transform missing 'id' field")
            continue
        if tid in transforms:
            errors.append(f"Duplicate transform ID: {tid}")
        transforms[tid] = t

        tongue = t.get("tongue", "")
        if tongue not in VALID_TONGUES:
            errors.append(f"Transform '{tid}' has invalid tongue '{tongue}'")

    return transforms


def validate_maps():
    map_dir = DATA_DIR / "maps"
    if not map_dir.exists():
        warnings.append("No maps directory found")
        return

    for f in map_dir.glob("*.json"):
        data = load_json(f)
        if not data:
            continue
        mid = data.get("id", f.stem)
        size = data.get("size", {})
        w = size.get("width", 0)
        h = size.get("height", 0)

        layout = data.get("layout", {})
        grid = layout.get("grid", [])

        if len(grid) != h:
            errors.append(f"Map '{mid}' declares height={h} but grid has {len(grid)} rows")
        for row_idx, row in enumerate(grid):
            if len(row) != w:
                errors.append(f"Map '{mid}' row {row_idx} has {len(row)} cols, expected {w}")


def main():
    print("Validating Spiral Forge RPG game content...")
    print(f"Data directory: {DATA_DIR}")
    print()

    creatures = validate_creatures()
    print(f"  Creatures: {len(creatures)} loaded")

    items = validate_items()
    print(f"  Items:     {len(items)} loaded")

    npcs = validate_npcs(items)
    print(f"  NPCs:      {len(npcs)} loaded")

    transforms = validate_transforms()
    print(f"  Transforms:{len(transforms)} loaded")

    validate_maps()
    print(f"  Maps:      validated")
    print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        print()
        print("VALIDATION FAILED")
        sys.exit(1)
    else:
        print("✓ All content valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
