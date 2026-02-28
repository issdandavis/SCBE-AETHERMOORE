---
name: tuxemon-map-editor
description: "Create and edit Tuxemon TMX tile maps, YAML event scripts, collision geometry, tileset references, and map transitions. Use when building new areas, fixing map rendering, editing events/triggers, or debugging tile display issues."
---

# Tuxemon Map Editor

Use this skill when working on maps in the Tuxemon Aethermoor mod at `demo/tuxemon_src/mods/aethermoor/maps/`.

## File Types

| File | Format | Purpose |
|---|---|---|
| `*.tmx` | XML (Tiled) | Tile layers, collision objects, tileset refs |
| `*.yaml` | YAML | Event scripts (dialogue, teleports, triggers) |
| `*.tsx` | XML (Tiled) | Tileset definitions (shared across maps) |
| `aethermoor.yaml` | YAML | Global scenario events (day/night, evolution, faint) |

## TMX Map Structure

Maps use Tiled TMX format with base64+zlib compressed tile data.

```xml
<map version="1.10" orientation="orthogonal" renderorder="right-down"
     width="9" height="7" tilewidth="16" tileheight="16">

  <!-- Map properties (required) -->
  <properties>
    <property name="edges" value="clamped"/>
    <property name="inside" type="bool" value="true"/>
    <property name="scenario" value="aethermoor"/>
    <property name="slug" value="bedroom"/>
    <property name="map_type" value="notype"/>
  </properties>

  <!-- Tilesets (relative paths to tuxemon gfx) -->
  <tileset firstgid="1" source="../../tuxemon/gfx/tilesets/core_indoor_walls.tsx"/>
  <tileset firstgid="3865" source="../../tuxemon/gfx/tilesets/core_indoor_stairs.tsx"/>

  <!-- Standard 4 tile layers -->
  <layer name="Tile Layer 1"/>
  <layer name="Tile Layer 2"/>
  <layer name="Tile Layer 3"/>
  <layer name="Above player"/>

  <!-- Collision objects -->
  <objectgroup name="Collisions">
    <object type="collision" x="0" y="16" width="144" height="16"/>
  </objectgroup>
</map>
```

### Tileset Path Convention

Aethermoor maps reference tuxemon core tilesets via relative path:
```
../../tuxemon/gfx/tilesets/<tileset>.tsx
```
This resolves from `mods/aethermoor/maps/` to `mods/tuxemon/gfx/tilesets/`.

### Available Core Tilesets

| Tileset | Content |
|---|---|
| `core_indoor_walls.tsx` | Interior walls, windows, doors |
| `core_indoor_stairs.tsx` | Staircases, ladders |
| `core_indoor_floors.tsx` | Floor tiles, carpets, wood |
| `core_set pieces.tsx` | Furniture, beds, tables, computers |
| `core_outdoor.tsx` | Grass, trees, paths, fences |
| `core_outdoor_water.tsx` | Water, bridges, shores |

### firstgid Values

The `firstgid` for each tileset must be calculated correctly:
- First tileset: `firstgid="1"`
- Subsequent: previous firstgid + (tileset columns x tileset rows)
- Get tile count from the TSX file's `tilecount` attribute

## YAML Event Scripts

Each map has a corresponding YAML file defining events.

```yaml
events:

  Event Name:
    actions:
    - action_name param1,param2
    - translated_dialog dialog_key
    conditions:
    - is condition_name param
    - not other_condition param
    type: event
    x: 3
    y: 1
    width: 1
    height: 1
```

### Common Event Actions

| Action | Syntax | Purpose |
|---|---|---|
| `translated_dialog` | `translated_dialog key` | Show localized dialog |
| `transition_teleport` | `transition_teleport player,map.tmx,x,y,time` | Teleport with fade |
| `char_face` | `char_face player,direction` | Face up/down/left/right |
| `play_music` | `play_music slug` | Play background music |
| `set_variable` | `set_variable name:value` | Set game variable |
| `add_monster` | `add_monster slug,level` | Give player a monster |
| `start_battle` | `start_battle npc_slug` | Initiate combat |
| `access_pc` | `access_pc player,tags` | Open PC menu |
| `screen_transition` | `screen_transition duration` | Fade to black |
| `set_monster_health` | `set_monster_health` | Heal all monsters |
| `set_teleport_faint` | `set_teleport_faint player,map,x,y` | Set faint respawn |
| `track_deed` | `track_deed deed_name` | SCBE deed tracking (custom) |
| `track_tongue` | `track_tongue tongue_code` | SCBE tongue tracking (custom) |

### Common Event Conditions

| Condition | Syntax | Purpose |
|---|---|---|
| `variable_set` | `variable_set name:value` | Check game variable |
| `char_at` | `char_at player` | Player at event tile |
| `char_facing_tile` | `char_facing_tile player` | Player facing event tile |
| `button_pressed` | `button_pressed INTERACT` | Button held |
| `music_playing` | `music_playing slug` | Music is playing |
| `party_size` | `party_size player,greater_than,0` | Check party |
| `current_state` | `current_state WorldState` | Check game state |

### Negating Conditions

Prefix with `not` to negate: `- not variable_set quest_done:yes`

## Global Scenario Events (aethermoor.yaml)

The `aethermoor.yaml` file defines events that apply across ALL maps with `scenario=aethermoor`:
- Day/Night cycle (set_layer for outdoor maps)
- Evolution checks (check_evolution -> evolution action)
- Faint teleport (char_defeated -> teleport_faint)
- Party status updates
- Tech overflow management

## Existing Aethermoor Maps

| Map | Size | Type | Description |
|---|---|---|---|
| `aethermoor_chen_home` | 9x7 | inside | Player's bedroom (starting map) |
| `aethermoor_chen_downstairs` | 12x10 | inside | Kitchen/living room |
| `aethermoor_starter_village` | 30x30 | outside | Main village area |
| `aethermoor_lab` | 15x12 | inside | Professor Eldrin's lab |
| `aethermoor_coastal_path` | 40x20 | outside | Wild encounter route |

## Creating a New Map

1. Create `maps/aethermoor_<name>.tmx` in Tiled (16x16 tile size, orthogonal)
2. Add required properties: `slug`, `edges`, `inside`, `scenario=aethermoor`, `map_type`
3. Reference tilesets with `../../tuxemon/gfx/tilesets/` paths
4. Add 4 tile layers + Collisions object group
5. Create `maps/aethermoor_<name>.yaml` for events
6. Add transition events in connected maps to link them

## Rendering Pipeline

```
TMX file -> pytmx.TiledMap -> scaled_image_loader -> pyscroll.BufferedRenderer -> screen
```

- **NATIVE_RESOLUTION**: (256, 144) -- "Game Boy" resolution
- **TILE_SIZE**: (16, 16) native, scaled by factor
- **Scale factor**: `int(screen_width / 256)` -- e.g., 1280/256 = 5
- **Scaled tile size**: 16 x 5 = 80px per tile at 1280x720

The `scaled_image_loader` in `graphics.py` scales tileset images at load time for pyscroll.

## Key Engine Files

| File | Purpose |
|---|---|
| `tuxemon/map/loader.py` | MapLoader, TMXMapLoader, YAMLEventLoader |
| `tuxemon/map/tuxemon.py` | TuxemonMap class, pyscroll.BufferedRenderer |
| `tuxemon/map/view.py` | MapRenderer, SpriteController, NPC rendering |
| `tuxemon/graphics.py` | scaled_image_loader, load_and_scale, strip_from_sheet |
| `tuxemon/prepare.py` | DisplayContext, SCREEN_SIZE, scale computation |
| `tuxemon/platform/const/sizes.py` | TILE_SIZE, NATIVE_RESOLUTION, SPRITE_SIZE |
| `tuxemon/constants/asset_loader.py` | fetch_asset, _MOD_ASSET_ROOTS |
| `tuxemon/event/eventaction.py` | EventAction base class for plugins |
