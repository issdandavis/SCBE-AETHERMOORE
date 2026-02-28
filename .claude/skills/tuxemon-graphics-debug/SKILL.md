---
name: tuxemon-graphics-debug
description: "Debug and fix Tuxemon rendering issues — pyscroll/pytmx tile rendering, sprite loading, camera system, scaling pipeline, tileset validation, and display configuration. Use when tiles render incorrectly, sprites are missing, maps show black gaps, or the camera/viewport behaves wrong."
---

# Tuxemon Graphics Debugging

Use this skill when debugging visual/rendering issues in the Tuxemon game at `demo/tuxemon_src/`.

## Rendering Pipeline

```
TMX Map File
  -> pytmx.TiledMap (parse XML, decode base64+zlib tile data)
  -> scaled_image_loader (scale tileset images by factor)
  -> pyscroll.BufferedRenderer (pre-render visible tiles to buffer)
  -> MapRenderer.draw() (blit buffer + NPC sprites to screen)
  -> pygame.display.flip()
```

## Scale Factor

```python
NATIVE_RESOLUTION = (256, 144)
TILE_SIZE = (16, 16)
scale = int(SCREEN_SIZE[0] / NATIVE_RESOLUTION[0])  # 1280/256 = 5
tile_size = (16 * scale, 16 * scale)  # 80x80 at 1280x720
```

## Common Issues

### Black Gaps / Patchy Tiles
- Check `DISPLAY_CONTEXT.tile_size` should be `(80, 80)` at 1280x720
- Check `scaled_image_loader` is being called (not default pytmx loader)
- Verify TMX `tilewidth="16" tileheight="16"` matches TILE_SIZE
- Fix location: `tuxemon/graphics.py:scaled_image_loader()`

### Missing Sprites
- Check NPC JSON `template.sprite_name` matches file in `mods/tuxemon/gfx/sprites/`
- Verify `_MOD_ASSET_ROOTS` includes tuxemon mod
- Monster sheets: `mods/aethermoor/gfx/sprites/battle/<slug>-sheet.png`

### Tileset Path Errors
- TMX tileset `source` paths are relative to TMX file
- Aethermoor: `../../tuxemon/gfx/tilesets/<name>.tsx`
- TSX image paths are relative to TSX file

## Key Functions

- `scaled_image_loader` (graphics.py) -- pyscroll tile loader, must return scaled tiles
- `load_and_scale` (graphics.py) -- general image loader with scale factor
- `TuxemonMap.initialize_renderer` (map/tuxemon.py) -- creates pyscroll.BufferedRenderer
- `MapRenderer.draw` (map/view.py) -- per-frame rendering

## Debug Tools

```python
# Check asset loading
from tuxemon.constants.asset_loader import _MOD_ASSET_ROOTS, fetch_asset
print(f"Mod roots: {_MOD_ASSET_ROOTS}")

# Validate TMX tilesets
import pytmx
tiled_map = pytmx.TiledMap("path/to/map.tmx")
for ts in tiled_map.tilesets:
    print(f"Tileset: {ts.name}, firstgid: {ts.firstgid}")

# Compare vanilla vs mod
CONFIG.mods = ['tuxemon']  # Test without aethermoor
```

## Engine Files

| File | Purpose |
|---|---|
| `tuxemon/graphics.py` | scaled_image_loader, load_and_scale |
| `tuxemon/prepare.py` | pygame_init, DisplayContext, SCREEN_SIZE |
| `tuxemon/scaling.py` | DefaultScaling, ResolutionScaling |
| `tuxemon/map/tuxemon.py` | TuxemonMap, pyscroll.BufferedRenderer |
| `tuxemon/map/view.py` | MapRenderer, SpriteController |
| `tuxemon/map/loader.py` | MapLoader, TMXMapLoader |
| `tuxemon/camera/camera.py` | Camera management |
| `tuxemon/platform/const/sizes.py` | NATIVE_RESOLUTION, TILE_SIZE, SPRITE_SIZE |
