"""
GPT world director — LLM as pocket-dimension operator.

The TinyWorld is the script. GPT reads the current state (ASCII grid + JSON)
and outputs a WorldDelta: structured commands + a one-line narrative. The delta
is applied to the world, sketches are rendered, and the lattice checks coherence.

Round-table mode: run the same state through multiple models, score each
delta by the lattice drift it would produce, keep the most coherent one.

Quick start:
    from src.video_lattice.gpt_world import WorldDirector, RoundTableDirector
    from src.video_lattice.tiny_engine import demo_world

    director = WorldDirector()              # reads OPENAI_API_KEY from env
    world = demo_world()
    delta = director.step(world, "the hero moves toward the water")
    director.apply_delta(world, delta)
    print("\\n".join(world.to_symbol_grid()))

Round table:
    table = RoundTableDirector([
        WorldDirector(model="gpt-4.1"),
        WorldDirector(model="gpt-4o-mini"),
    ])
    best_delta, report = table.step(world, "hero investigates the water")

API key sources (first found wins):
    1. WorldDirector(api_key="sk-...")
    2. OPENAI_API_KEY env var
    3. config/connector_oauth/.env.connector.oauth  →  OPENAI_API_KEY=...
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .poincare_lattice import PoincareLattice
from .tiny_engine import Entity, Tile, TinyWorld

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONNECTOR_ENV = _REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
_DEFAULT_MODEL = "gpt-4.1"

# ------------------------------------------------------------------
# Command schema — what GPT may output
# ------------------------------------------------------------------

COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "commands": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["move", "set_tile", "add_entity", "remove_entity", "set_entity_state", "narrate"],
                    },
                    "entity_id": {"type": "string"},
                    "dx": {"type": "integer"},
                    "dy": {"type": "integer"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "tile_id": {"type": "string"},
                    "sprite_id": {"type": "string"},
                    "state_key": {"type": "string"},
                    "state_value": {},
                    "text": {"type": "string"},
                },
                "required": ["type"],
            },
        },
        "narrative": {"type": "string"},
    },
    "required": ["commands", "narrative"],
}

SYSTEM_PROMPT = """\
You are a pocket-dimension director. You receive the current state of a small
symbolic world and a director note. You respond with a JSON object containing:

1. "commands": a list of world-mutation commands to advance the scene.
2. "narrative": one sentence describing what just happened.

Available command types:
  move            — {type:"move", entity_id:"...", dx:int, dy:int}
  set_tile        — {type:"set_tile", x:int, y:int, tile_id:"..."}
  add_entity      — {type:"add_entity", entity_id:"...", sprite_id:"...", x:int, y:int}
  remove_entity   — {type:"remove_entity", entity_id:"..."}
  set_entity_state — {type:"set_entity_state", entity_id:"...", state_key:"...", state_value:any}

Rules:
- Only reference tile_ids and sprite_ids that exist in the world spec.
- Do not move entities into solid tiles.
- Keep commands minimal — prefer one or two well-chosen moves over many small ones.
- The narrative must be one sentence, present tense, no fluff.

Respond ONLY with the JSON object. No other text.
"""


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------


@dataclass
class WorldCommand:
    """One parsed command from a GPT delta."""

    type: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldDelta:
    """GPT's response for one step: commands + narrative."""

    commands: List[WorldCommand]
    narrative: str
    model: str
    raw_response: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "narrative": self.narrative,
            "commands": [{"type": c.type, **c.data} for c in self.commands],
            "tokens": {"prompt": self.prompt_tokens, "completion": self.completion_tokens},
        }


@dataclass
class RoundTableReport:
    """Multi-model comparison result."""

    winner_model: str
    winner_delta: WorldDelta
    winner_drift: float
    all_results: List[Tuple[str, WorldDelta, float]]  # (model, delta, drift)

    def summary(self) -> str:
        lines = [f"winner: {self.winner_model} (drift={self.winner_drift:.4f})"]
        for model, delta, drift in self.all_results:
            lines.append(f"  {model}: drift={drift:.4f}  '{delta.narrative}'")
        return "\n".join(lines)


# ------------------------------------------------------------------
# WorldDirector
# ------------------------------------------------------------------


class WorldDirector:
    """GPT-powered operator for a TinyWorld.

    Args:
        model: OpenAI model ID (default gpt-4.1).
        api_key: OpenAI API key. If None, reads from env / connector file.
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Max tokens for the completion.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._api_key = api_key or _load_api_key()
        self._client = None  # lazy init — don't import openai at module load

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError("openai package required: pip install openai") from exc
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def generate(self, prompt: str, width: int = 12, height: int = 8) -> TinyWorld:
        """Ask GPT to create a new pocket world from a text description.

        GPT returns world JSON; we parse it into a TinyWorld.
        Falls back to demo_world() if parsing fails.
        """
        from .tiny_engine import demo_world

        system = """\
You are a pocket-dimension architect. Given a description, return a JSON object
that matches the scbe_tiny_world_v1 schema exactly:
  schema, pocket_id, width, height, frame_index, tiles, sprites, grid, entities.

Each tile: {tile_id, glyph, color, solid, tags}.
Each sprite: {sprite_id, glyph, color, tags}.
Grid: array of height arrays, each of width tile_id strings.
Entities: dict of {entity_id: {entity_id, sprite_id, x, y, z, state}}.

Use single-character glyphs. Keep it small and symbolic. Respond ONLY with JSON."""
        user = f"Create a {width}x{height} pocket world: {prompt}"
        raw = self._call(system, user, temperature=0.9)
        try:
            data = json.loads(raw)
            return TinyWorld.from_json(data)
        except Exception:
            return demo_world()

    def step(self, world: TinyWorld, director_note: str = "") -> WorldDelta:
        """Ask GPT what happens next in the world.

        Args:
            world: current world state.
            director_note: optional guidance ("hero moves toward water").

        Returns:
            WorldDelta with commands and narrative.
        """
        user = self._build_user_message(world, director_note)
        raw = self._call(SYSTEM_PROMPT, user)
        return self._parse_delta(raw)

    def describe(self, world: TinyWorld) -> str:
        """Ask GPT to narrate the current world state in one paragraph."""
        system = "You are a vivid storyteller. Describe what you see in one paragraph, present tense."
        user = f"World: {world.pocket_id}\n\n{chr(10).join(world.to_symbol_grid())}"
        return self._call(system, user, temperature=0.85)

    # ------------------------------------------------------------------
    # Apply delta
    # ------------------------------------------------------------------

    def apply_delta(self, world: TinyWorld, delta: WorldDelta) -> List[str]:
        """Apply delta commands to the world. Returns list of skipped command reasons."""
        skipped = []
        for cmd in delta.commands:
            try:
                self._apply_command(world, cmd)
            except Exception as exc:
                skipped.append(f"{cmd.type}: {exc}")
        return skipped

    # ------------------------------------------------------------------
    # Lattice coherence scoring
    # ------------------------------------------------------------------

    def score_delta(self, world: TinyWorld, delta: WorldDelta) -> float:
        """Compute hyperbolic drift that would result from applying this delta.

        Embeds the current world state feature vector and the post-delta
        feature vector into a PoincareLattice and returns d_H between them.
        Lower = more coherent continuation.
        """
        import copy

        world_copy = TinyWorld.from_json(world.to_json())
        self.apply_delta(world_copy, delta)
        v_before = _world_feature_vector(world)
        v_after = _world_feature_vector(world_copy)
        dim = len(v_before)
        lattice = PoincareLattice(dim=dim, name="world_coherence")
        p_before = lattice.embed(v_before)
        p_after = lattice.embed(v_after)
        return lattice.distance(p_before, p_after)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call(self, system: str, user: str, temperature: Optional[float] = None) -> str:
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def _build_user_message(self, world: TinyWorld, director_note: str) -> str:
        grid_str = "\n".join(world.to_symbol_grid())
        spec = {
            "pocket_id": world.pocket_id,
            "width": world.width,
            "height": world.height,
            "frame": world.frame_index,
            "tiles": {k: {"glyph": t.glyph, "solid": t.solid, "tags": list(t.tags)} for k, t in world.tiles.items()},
            "sprites": {k: {"glyph": s.glyph} for k, s in world.sprites.items()},
            "entities": {
                k: {"sprite": e.sprite_id, "x": e.x, "y": e.y, "state": e.state} for k, e in world.entities.items()
            },
        }
        parts = [
            f"GRID:\n{grid_str}",
            f"\nSPEC:\n{json.dumps(spec, indent=2)}",
        ]
        if director_note:
            parts.append(f"\nDIRECTOR NOTE: {director_note}")
        return "\n".join(parts)

    def _parse_delta(self, raw: str) -> WorldDelta:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return WorldDelta(commands=[], narrative=raw[:120], model=self.model, raw_response=raw)
        commands = []
        for item in data.get("commands", []):
            if not isinstance(item, dict) or "type" not in item:
                continue
            cmd_type = item.pop("type")
            commands.append(WorldCommand(type=cmd_type, data=dict(item)))
        return WorldDelta(
            commands=commands,
            narrative=str(data.get("narrative", "")),
            model=self.model,
            raw_response=raw,
        )

    @staticmethod
    def _apply_command(world: TinyWorld, cmd: WorldCommand) -> None:
        d = cmd.data
        if cmd.type == "move":
            world.move_entity(d["entity_id"], dx=int(d.get("dx", 0)), dy=int(d.get("dy", 0)))
        elif cmd.type == "set_tile":
            world.set_tile(int(d["x"]), int(d["y"]), d["tile_id"])
        elif cmd.type == "add_entity":
            e = Entity(
                entity_id=d["entity_id"],
                sprite_id=d["sprite_id"],
                x=int(d.get("x", 0)),
                y=int(d.get("y", 0)),
                z=int(d.get("z", 0)),
                state=dict(d.get("state", {})),
            )
            world.add_entity(e)
        elif cmd.type == "remove_entity":
            world.entities.pop(d["entity_id"], None)
        elif cmd.type == "set_entity_state":
            entity = world.entities[d["entity_id"]]
            entity.state[d["state_key"]] = d.get("state_value")
        elif cmd.type == "narrate":
            pass  # narrate-only commands are captured in delta.narrative


# ------------------------------------------------------------------
# Round-table director
# ------------------------------------------------------------------


class RoundTableDirector:
    """Run a step through multiple models, keep the most coherent delta.

    Coherence = lowest hyperbolic drift from current world state.
    If all deltas have the same drift (e.g., all no-ops), the first model wins.

    Args:
        directors: list of WorldDirector instances (one per model/config).
    """

    def __init__(self, directors: List[WorldDirector]) -> None:
        if not directors:
            raise ValueError("need at least one director")
        self.directors = directors

    def step(self, world: TinyWorld, director_note: str = "") -> Tuple[WorldDelta, RoundTableReport]:
        """Run all models, return (best_delta, report).

        Args:
            world: current world state (not mutated).
            director_note: optional guidance passed to all models.

        Returns:
            (winning_delta, RoundTableReport)
        """
        results: List[Tuple[str, WorldDelta, float]] = []
        for director in self.directors:
            delta = director.step(world, director_note)
            drift = director.score_delta(world, delta)
            results.append((director.model, delta, drift))

        # Sort by drift ascending — lowest drift = most coherent
        results.sort(key=lambda r: r[2])
        winner_model, winner_delta, winner_drift = results[0]

        report = RoundTableReport(
            winner_model=winner_model,
            winner_delta=winner_delta,
            winner_drift=winner_drift,
            all_results=results,
        )
        return winner_delta, report

    def add_director(self, director: WorldDirector) -> None:
        self.directors.append(director)


# ------------------------------------------------------------------
# World feature vector for lattice coherence scoring
# ------------------------------------------------------------------


def _world_feature_vector(world: TinyWorld) -> np.ndarray:
    """Compact numeric descriptor of a world state.

    Encodes: tile type counts (normalized), entity positions (normalized),
    entity count, frame index. Fixed-length regardless of world size.
    """
    tile_ids = sorted(world.tiles.keys())
    # Tile frequency histogram
    tile_counts = {t: 0 for t in tile_ids}
    for row in world.grid:
        for cell in row:
            tile_counts[cell] = tile_counts.get(cell, 0) + 1
    total_cells = world.width * world.height
    tile_freq = np.array([tile_counts.get(t, 0) / total_cells for t in tile_ids], dtype=np.float64)

    # Entity centroid (normalized to [0,1])
    if world.entities:
        xs = [e.x / world.width for e in world.entities.values()]
        ys = [e.y / world.height for e in world.entities.values()]
        centroid = np.array([np.mean(xs), np.mean(ys)], dtype=np.float64)
        spread = np.array([np.std(xs) if len(xs) > 1 else 0.0, np.std(ys) if len(ys) > 1 else 0.0], dtype=np.float64)
    else:
        centroid = np.zeros(2, dtype=np.float64)
        spread = np.zeros(2, dtype=np.float64)

    entity_count = np.array([len(world.entities) / max(total_cells, 1)], dtype=np.float64)
    frame = np.array([world.frame_index / max(world.frame_index + 1, 1)], dtype=np.float64)

    # Pad tile_freq to 8 bins (handles worlds with fewer tile types)
    if len(tile_freq) < 8:
        tile_freq = np.pad(tile_freq, (0, 8 - len(tile_freq)))
    else:
        tile_freq = tile_freq[:8]

    return np.concatenate([tile_freq, centroid, spread, entity_count, frame])


# ------------------------------------------------------------------
# API key loader
# ------------------------------------------------------------------


def _load_api_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    if _CONNECTOR_ENV.exists():
        for line in _CONNECTOR_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None
