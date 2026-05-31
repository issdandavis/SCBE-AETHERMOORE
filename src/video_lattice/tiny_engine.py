"""Tiny symbolic engine for AI-directed rendering experiments.

Old games stayed small because they stored reusable primitives: tile IDs,
palettes, sprites, entity state, and rules. This module applies that idea to
AI video generation. The model should not invent every pixel every frame; it
can manipulate a compact world state, render a sketch/control frame, then use
the video lattice to check whether the rendered result stayed coherent.

In Aethermoore terms this is a pocket dimension: a bounded local world with its
own rules, symbols, actors, and render surface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class Tile:
    tile_id: str
    glyph: str
    color: str = "#6b7280"
    solid: bool = False
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Sprite:
    sprite_id: str
    glyph: str
    color: str = "#f8f8f2"
    tags: tuple[str, ...] = ()


@dataclass
class Entity:
    entity_id: str
    sprite_id: str
    x: int
    y: int
    z: int = 0
    state: dict[str, object] = field(default_factory=dict)


@dataclass
class TinyWorld:
    pocket_id: str
    width: int
    height: int
    tiles: dict[str, Tile]
    sprites: dict[str, Sprite]
    grid: list[list[str]]
    entities: dict[str, Entity] = field(default_factory=dict)
    frame_index: int = 0

    @classmethod
    def blank(
        cls,
        width: int,
        height: int,
        *,
        pocket_id: str = "pocket.demo",
        default_tile: Tile | None = None,
        tiles: Iterable[Tile] = (),
        sprites: Iterable[Sprite] = (),
    ) -> "TinyWorld":
        base_tile = default_tile or Tile("floor", ".", "#3b4252")
        tile_map = {base_tile.tile_id: base_tile}
        tile_map.update({tile.tile_id: tile for tile in tiles})
        return cls(
            pocket_id=pocket_id,
            width=width,
            height=height,
            tiles=tile_map,
            sprites={sprite.sprite_id: sprite for sprite in sprites},
            grid=[[base_tile.tile_id for _ in range(width)] for _ in range(height)],
        )

    def set_tile(self, x: int, y: int, tile_id: str) -> None:
        self._check_bounds(x, y)
        if tile_id not in self.tiles:
            raise KeyError(f"unknown tile_id {tile_id}")
        self.grid[y][x] = tile_id

    def add_entity(self, entity: Entity) -> None:
        self._check_bounds(entity.x, entity.y)
        if entity.sprite_id not in self.sprites:
            raise KeyError(f"unknown sprite_id {entity.sprite_id}")
        self.entities[entity.entity_id] = entity

    def move_entity(self, entity_id: str, dx: int = 0, dy: int = 0, dz: int = 0) -> bool:
        entity = self.entities[entity_id]
        nx = entity.x + dx
        ny = entity.y + dy
        self._check_bounds(nx, ny)
        tile = self.tiles[self.grid[ny][nx]]
        if tile.solid:
            return False
        entity.x = nx
        entity.y = ny
        entity.z += dz
        self.frame_index += 1
        return True

    def to_symbol_grid(self) -> list[str]:
        rows = [[self.tiles[tile_id].glyph for tile_id in row] for row in self.grid]
        for entity in sorted(self.entities.values(), key=lambda item: (item.z, item.entity_id)):
            if 0 <= entity.x < self.width and 0 <= entity.y < self.height:
                rows[entity.y][entity.x] = self.sprites[entity.sprite_id].glyph
        return ["".join(row) for row in rows]

    def render_svg(self, *, cell: int = 32) -> str:
        width = self.width * cell
        height = self.height * cell
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#111827" />',
        ]
        for y, row in enumerate(self.grid):
            for x, tile_id in enumerate(row):
                tile = self.tiles[tile_id]
                lines.append(
                    f'<rect x="{x * cell}" y="{y * cell}" width="{cell}" height="{cell}" '
                    f'fill="{tile.color}" stroke="#1f2937" stroke-width="1" />'
                )
                if tile.glyph.strip():
                    lines.append(_text(tile.glyph, x, y, cell, "#9ca3af", size=cell * 0.45))
        for entity in sorted(self.entities.values(), key=lambda item: (item.z, item.entity_id)):
            sprite = self.sprites[entity.sprite_id]
            lines.append(_text(sprite.glyph, entity.x, entity.y, cell, sprite.color, size=cell * 0.72))
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    def save_svg(self, path: Path | str, *, cell: int = 32) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render_svg(cell=cell), encoding="utf-8")
        return out

    def to_json(self) -> dict:
        return {
            "schema": "scbe_tiny_world_v1",
            "pocket_id": self.pocket_id,
            "width": self.width,
            "height": self.height,
            "frame_index": self.frame_index,
            "tiles": {key: tile.__dict__ for key, tile in self.tiles.items()},
            "sprites": {key: sprite.__dict__ for key, sprite in self.sprites.items()},
            "grid": self.grid,
            "entities": {key: entity.__dict__ for key, entity in self.entities.items()},
        }

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> "TinyWorld":
        tiles = {
            key: Tile(
                tile_id=value["tile_id"],
                glyph=value["glyph"],
                color=value.get("color", "#6b7280"),
                solid=bool(value.get("solid", False)),
                tags=tuple(value.get("tags", ())),
            )
            for key, value in dict(data["tiles"]).items()
        }
        sprites = {
            key: Sprite(
                sprite_id=value["sprite_id"],
                glyph=value["glyph"],
                color=value.get("color", "#f8f8f2"),
                tags=tuple(value.get("tags", ())),
            )
            for key, value in dict(data["sprites"]).items()
        }
        world = cls(
            width=int(data["width"]),
            height=int(data["height"]),
            pocket_id=str(data.get("pocket_id", "pocket.loaded")),
            tiles=tiles,
            sprites=sprites,
            grid=[list(row) for row in data["grid"]],
            frame_index=int(data.get("frame_index", 0)),
        )
        for key, value in dict(data.get("entities", {})).items():
            world.entities[key] = Entity(
                entity_id=value["entity_id"],
                sprite_id=value["sprite_id"],
                x=int(value["x"]),
                y=int(value["y"]),
                z=int(value.get("z", 0)),
                state=dict(value.get("state", {})),
            )
        return world

    def save_json(self, path: Path | str) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_json(), indent=2, sort_keys=True), encoding="utf-8")
        return out

    @classmethod
    def load_json(cls, path: Path | str) -> "TinyWorld":
        return cls.from_json(json.loads(Path(path).read_text(encoding="utf-8")))

    def _check_bounds(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"position out of bounds: {x}, {y}")


def demo_world() -> TinyWorld:
    wall = Tile("wall", "#", "#263241", solid=True, tags=("boundary",))
    water = Tile("water", "~", "#1d4ed8", tags=("fluid", "depth"))
    floor = Tile("floor", ".", "#374151", tags=("walkable",))
    hero = Sprite("hero", "@", "#facc15", tags=("actor", "controlled"))
    hand = Sprite("hand_marker", "*", "#fb7185", tags=("hand", "attention"))
    world = TinyWorld.blank(
        12,
        8,
        pocket_id="pocket.aether.video_lattice.demo",
        default_tile=floor,
        tiles=(wall, water),
        sprites=(hero, hand),
    )
    for x in range(world.width):
        world.set_tile(x, 0, "wall")
        world.set_tile(x, world.height - 1, "wall")
    for y in range(world.height):
        world.set_tile(0, y, "wall")
        world.set_tile(world.width - 1, y, "wall")
    for x in range(4, 8):
        world.set_tile(x, 4, "water")
    world.add_entity(Entity("hero", "hero", 2, 2, state={"intent": "explore"}))
    world.add_entity(Entity("hand_focus", "hand_marker", 8, 2, z=1, state={"intent": "inspect"}))
    return world


def _text(glyph: str, x: int, y: int, cell: int, color: str, *, size: float) -> str:
    return (
        f'<text x="{x * cell + cell / 2:.2f}" y="{y * cell + cell * 0.66:.2f}" '
        f'text-anchor="middle" font-family="Consolas, monospace" font-size="{size:.2f}" '
        f'fill="{color}">{glyph}</text>'
    )
