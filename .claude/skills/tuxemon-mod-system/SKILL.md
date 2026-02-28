---
name: tuxemon-mod-system
description: "Manage the Tuxemon mod architecture — mod.yaml config, db_config, translations (l18n), asset loading, state machine, event action plugins, PC menu providers, and the plugin discovery system. Use when creating mod components, extending the engine, or debugging mod loading issues."
---

# Tuxemon Mod System

Use this skill when working on the Tuxemon engine mod infrastructure at `demo/tuxemon_src/`.

## Mod Directory Layout

```
mods/aethermoor/
├── mod.yaml                    # Mod metadata and config
├── db/                         # Game data (monsters, NPCs, encounters, elements)
│   ├── monster/
│   ├── npc/
│   ├── encounter/
│   ├── element/
│   └── music/
├── maps/                       # TMX maps + YAML events
│   ├── aethermoor_chen_home.tmx
│   ├── aethermoor_chen_home.yaml
│   └── aethermoor.yaml         # Global scenario events
├── gfx/sprites/battle/         # Monster battle sprite sheets
├── data/                       # Mod-specific data files (journal.json)
├── music/                      # Music files + guide
├── l18n/en_US/LC_MESSAGES/     # Translation PO files
│   └── base.po
├── states/                     # Custom game states (auto-discovered)
│   └── aethernet.py
├── event/                      # Custom event actions/conditions (auto-discovered)
│   └── actions/
│       ├── track_deed.py
│       └── track_tongue.py
├── pollypad.py                 # PC menu provider (imported at launch)
├── battle_hook.py              # Combat telemetry monkey-patch
├── combat_bridge.py            # Combat -> SCBE event bridge
├── combat_blockchain.py        # Blockchain data generation
├── ai_schedule.py              # NPC schedule system
├── ai_reactive.py              # Fable-style deed tracking + LLM NPC dialogue
├── scbe_core.py                # SCBE math (L5-L13)
└── colab_server.py             # Colab AI backend
```

## mod.yaml Schema

```yaml
slug: aethermoor
name: "Aethermoor: Six Tongues Protocol"
description: >
  The first game where NPCs are stakeholders...
version: 0.1.0
authors:
  - MoeShaun
  - SCBE-AETHERMOORE
startup_rules: []
starting_players: ["npc_izack"]
starting_map: "aethermoor_chen_home.tmx"
starting_position: [4, 4]
starting_money: [100, 100]
starting_names:
  - Izack
sprite: adventurerblack
combat_sheet: adventurerblack
```

## db_config.yaml

```yaml
mod_base_path: "mods"
mod_db_subfolder: "db"
file_extensions: [".json", ".yaml"]
default_lookup_table: "monster"
active_mods: ["aethermoor", "tuxemon"]
mod_activation:
  aethermoor: true
  tuxemon: true
mod_dependencies:
  aethermoor: ["tuxemon"]
```

## Asset Loading Pipeline

```
fetch_asset("gfx/sprites/battle/korath-sheet.png")
  -> searches _MOD_ASSET_ROOTS in order:
    1. mods/aethermoor/gfx/sprites/battle/korath-sheet.png  <- found
    2. mods/tuxemon/gfx/sprites/battle/korath-sheet.png     <- fallback
```

### Key: `fetch_mod_asset_roots(config)` builds `_MOD_ASSET_ROOTS` from `config.mods` (reversed: first mod = highest priority)

## State Machine

States in `mods/<mod>/states/` are auto-discovered. Subclass `State` from `tuxemon.state.state`.

## Event Action Plugins

Actions in `mods/<mod>/event/actions/` are auto-discovered. Subclass `EventAction` with `name` matching the YAML action name.

## PC Menu Providers

Subclass `MenuProvider`, set `target_tags`, register with `PCMenuRegistry.register()`.

## Translations (l18n)

PO files in `l18n/en_US/LC_MESSAGES/base.po`. Multi-mod merge is patched in `tuxemon/locale/compiler.py`.

## Launcher Integration

```python
CONFIG.mods = ["aethermoor", "tuxemon"]  # BEFORE database imports
import mods.aethermoor.pollypad
import mods.aethermoor.battle_hook
import mods.aethermoor.combat_bridge
from mods.aethermoor.ai_schedule import init_schedules
init_schedules()
```

## Key Engine Files

| File | Purpose |
|---|---|
| `tuxemon/constants/paths.py` | LIBDIR, mods_folder, PLUGIN_CATEGORY_MAP |
| `tuxemon/constants/asset_loader.py` | fetch_asset, fetch_mod_asset_roots |
| `tuxemon/config.py` | TuxemonConfig (Pydantic), all config sections |
| `tuxemon/computer.py` | PCMenuRegistry, MenuProvider, PCMenuBuilder |
| `tuxemon/event/eventaction.py` | EventAction base class |
| `tuxemon/plugin.py` | PluginManager (auto-discovery) |
| `tuxemon/database/config.py` | DatabaseConfig, ModMetadata |
| `tuxemon/locale/compiler.py` | PO->MO compilation (multi-mod merge) |
