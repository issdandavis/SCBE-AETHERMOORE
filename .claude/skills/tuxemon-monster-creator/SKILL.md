---
name: tuxemon-monster-creator
description: "Create and edit Tuxemon monsters, NPCs, encounters, elements, items, and techniques. Use when adding new creatures, defining NPC templates, setting up wild encounter zones, or editing game database entries."
---

# Tuxemon Monster & Entity Creator

Use this skill when working with the `db/` directories in the Tuxemon Aethermoor mod at `demo/tuxemon_src/mods/aethermoor/db/`.

## Database Directory Structure

```
mods/aethermoor/db/
├── monster/          # Monster definitions (JSON)
│   ├── korath.json
│   ├── avewing.json
│   └── runecub.json
├── npc/              # NPC templates (JSON)
│   ├── npc_izack.json
│   ├── npc_mom.json
│   ├── npc_eldrin.json
│   ├── npc_traveler.json
│   └── npc_marcus_chen.json
├── encounter/        # Wild encounter zones (YAML)
│   └── coastal_path.yaml
├── element/          # Element type definitions (YAML)
│   ├── fire.yaml
│   ├── water.yaml
│   ├── earth.yaml
│   ├── metal.yaml
│   ├── shadow.yaml
│   └── aether.yaml
└── music/            # Music definitions (YAML)
    └── aethermoor_music.yaml
```

## Monster JSON Schema

```json
{
  "slug": "korath",
  "species": "false_dragon",
  "txmn_id": 1001,
  "shape": "dragon",
  "stage": "basic",
  "types": ["fire"],
  "height": 70,
  "weight": 20,
  "catch_rate": 45.0,
  "lower_catch_resistance": 0.9,
  "upper_catch_resistance": 1.3,
  "gender_weights": {"male": 0.5, "female": 0.5},
  "terrains": ["mountains", "desert"],
  "tags": ["flame", "claws"],
  "moveset": [
    {"level_learned": 1, "technique": "struggle", "learning_method": "fallback"},
    {"level_learned": 1, "technique": "gnaw"},
    {"level_learned": 5, "technique": "fire_claw"},
    {"level_learned": 10, "technique": "fire_ball"}
  ],
  "evolutions": [],
  "history": [
    {"slug": "korath", "stage": "basic", "evolves_from": [], "evolves_into": []}
  ],
  "sounds": {
    "combat_call": {"sfx": "sound_foom_0", "volume": 1.5},
    "faint_call": {"sfx": "sound_foom_0_faint", "volume": 1.5}
  }
}
```

### Monster Fields Reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `slug` | string | yes | Unique identifier, lowercase |
| `species` | string | yes | Display species name |
| `txmn_id` | int | yes | Unique numeric ID (Aethermoor: 1001+) |
| `shape` | string | yes | Body type: dragon, serpent, flier, brute, etc. |
| `stage` | string | yes | basic, stage1, stage2, mega |
| `types` | string[] | yes | Element types (fire, water, earth, etc.) |
| `moveset` | object[] | yes | Techniques learned by level |
| `evolutions` | object[] | no | Evolution paths |
| `history` | object[] | yes | Evolution chain history |
| `catch_rate` | float | yes | Base catch rate (1-255) |
| `gender_weights` | object | yes | Male/female distribution |
| `terrains` | string[] | no | Where they spawn naturally |
| `tags` | string[] | no | Descriptive tags |
| `sounds` | object | no | Combat call and faint SFX |

### Sacred Tongue Alignments

Each element type maps to a Sacred Tongue in the SCBE system:

| Element | Tongue | Code | Lore |
|---|---|---|---|
| fire | Kor'aelin | KO | Binding (fire forges bonds) |
| water | Avali | AV | I/O (water carries data) |
| earth | Runethic | RU | Oaths (earth keeps promises) |
| metal | Cassivadan | CA | Compute (metal = circuitry) |
| shadow | Umbroth | UM | Shadow (darkness, stealth) |
| aether | Draumric | DR | Schema (pure energy) |
| frost | Avali | AV | Crystallized data |
| lightning | Cassivadan | CA | Electric computation |
| wood | Umbroth | UM | Organic shadow |
| sky | Avali | AV | Aerial transmission |
| heroic | Kor'aelin | KO | Bonds of courage |

### Aethermoor Sacred Tongue Starters

| Monster | Type | Tongue | Lore Role |
|---|---|---|---|
| Korath | fire | KO | Fire drake, starter for binding affinity |
| Avewing | water | AV | Water bird, starter for I/O affinity |
| Runecub | earth | RU | Stone cub, starter for oath affinity |

## NPC JSON Schema

```json
{
  "slug": "npc_izack",
  "speech": {"profile": {"default": {}}},
  "combat": {},
  "audio": {},
  "template": {
    "sprite_name": "adventurerblack",
    "combat_sheet": "adventurerblack",
    "slug": "noclass"
  }
}
```

### NPC Fields Reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `slug` | string | yes | Must start with `npc_` |
| `template.sprite_name` | string | yes | Must match a sprite in `mods/tuxemon/gfx/sprites/` |
| `template.combat_sheet` | string | yes | Front-facing battle sprite sheet |
| `template.slug` | string | yes | Class slug (noclass for no specialization) |
| `speech.profile` | object | no | Dialogue profiles |
| `combat` | object | no | Combat configuration |

### Available Sprite Names

Sprites live in `mods/tuxemon/gfx/sprites/`. Common names:
- `adventurerblack`, `adventurer` -- player characters
- `boss`, `spyderboss` -- boss NPCs
- `manblue`, `manred`, `womangreen` -- generic NPCs
- `scientist`, `nurse`, `shopkeeper` -- profession NPCs

## Encounter YAML Schema

```yaml
slug: coastal_path
monsters:
- monster: rockitten
  encounter_rate: 3.5
  exp_req_mod: 3
  held_items: []
  level_range:
  - 3
  - 6
  variables:
    - key: daytime
      value: "true"
```

### Encounter Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `slug` | string | yes | Matches map slug |
| `monsters[].monster` | string | yes | Monster slug |
| `monsters[].encounter_rate` | float | yes | Relative spawn weight |
| `monsters[].exp_req_mod` | int | yes | XP modifier |
| `monsters[].level_range` | [int, int] | yes | Min/max level |
| `monsters[].held_items` | list | yes | Items held (can be empty) |
| `monsters[].variables` | list | yes | Conditions (daytime, weather) |

### Variable Conditions

```yaml
variables:
  - key: daytime
    value: "true"     # Only during day
  - key: weather
    value: "rain"     # Only during rain
```

## Element YAML Schema

```yaml
slug: fire
icon: gfx/ui/icons/element/fire_icon.png
types:
  fire:
    multiplier: 2.0
  water:
    multiplier: 0.5
  earth:
    multiplier: 1.0
```

## Monster Battle Sprites

Located at `mods/aethermoor/gfx/sprites/battle/`:
- Format: `<slug>-sheet.png`
- Sheet layout: 4 frames (front, back, front-alt, back-alt)
- Native frame size: 64x64 pixels

## Adding a New Monster

1. Create `db/monster/<slug>.json` with required fields
2. Create battle sprite sheet at `gfx/sprites/battle/<slug>-sheet.png` (256x64, 4 frames)
3. Add to encounter YAML if it spawns in the wild
4. Add evolution entries if it evolves
5. Map its types to Sacred Tongues in `scbe_core.py` TYPE_TO_TONGUE
6. Add to `l18n/en_US/LC_MESSAGES/base.po` for translations

## Key Engine Files

| File | Purpose |
|---|---|
| `tuxemon/database/config.py` | DatabaseConfig, ModMetadata schemas |
| `tuxemon/database/query.py` | Database query/lookup system |
| `tuxemon/database/runtime.py` | Runtime database singleton |
| `tuxemon/db.py` | Pydantic models (MonsterModel, NpcModel, etc.) |
| `tuxemon/encounter.py` | EncounterItemModel validation |
| `tuxemon/monster/` | Monster class, stats, sprites, evolution |
| `tuxemon/entity/npc.py` | NPC entity class |
| `tuxemon/entity/appearance.py` | Sprite/appearance management |
