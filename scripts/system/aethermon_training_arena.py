#!/usr/bin/env python3
"""AETHERMON training arena.

Small Godot-friendly game gym for AI play/training:

    observe -> choose action -> mutate world -> verify -> receipt

The Python gym is the source of truth. Godot can mirror the board using the
manifest this script writes under game/godot/assets/aethermon/.
"""

from __future__ import annotations

import argparse
import json
import random
import struct
import zlib
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
GODOT_AETHERMON_DIR = REPO_ROOT / "game" / "godot" / "assets" / "aethermon"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "aethermon_training_arena"

BOARD = [
    "##########",
    "#A..T...N#",
    "#..##....#",
    "#..B..H..#",
    "#....##..#",
    "#..R.....#",
    "##########",
]

MOVE_DELTAS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}

TONGUE_COLORS = {
    "KO": (220, 60, 60, 255),
    "AV": (220, 180, 60, 255),
    "RU": (60, 220, 120, 255),
    "CA": (60, 220, 220, 255),
    "UM": (90, 90, 230, 255),
    "DR": (220, 60, 220, 255),
}

SPRITE_SPECS = {
    "kindlemote": {"name": "Kindlemote", "tongue": "KO", "role": "starter"},
    "galewing": {"name": "Galewing", "tongue": "AV", "role": "wind partner"},
    "bitling": {"name": "Bitling", "tongue": "CA", "role": "logic partner"},
    "gloomkit": {"name": "Gloomkit", "tongue": "UM", "role": "shadow partner"},
    "rival_venom": {"name": "Rival Venom", "tongue": "UM", "role": "sparring rival"},
}


@dataclass
class Creature:
    species_id: str
    name: str
    tongue: str
    hp: int
    energy: int
    atk: int
    bond: int = 3
    xp: int = 0


@dataclass
class ArenaState:
    seed: int
    turn: int
    board: list[str]
    player_pos: tuple[int, int]
    rival_pos: tuple[int, int]
    creature: Creature
    berries: set[tuple[int, int]] = field(default_factory=set)
    hazards: set[tuple[int, int]] = field(default_factory=set)
    training_pads: set[tuple[int, int]] = field(default_factory=set)
    nexus_pos: tuple[int, int] = (0, 0)
    done: bool = False
    success: bool = False


def parse_board(seed: int, species_id: str = "kindlemote") -> ArenaState:
    start = rival = nexus = None
    berries: set[tuple[int, int]] = set()
    hazards: set[tuple[int, int]] = set()
    training_pads: set[tuple[int, int]] = set()
    for row, line in enumerate(BOARD):
        for col, cell in enumerate(line):
            pos = (row, col)
            if cell == "A":
                start = pos
            elif cell == "R":
                rival = pos
            elif cell == "N":
                nexus = pos
            elif cell == "B":
                berries.add(pos)
            elif cell == "H":
                hazards.add(pos)
            elif cell == "T":
                training_pads.add(pos)
    if start is None or rival is None or nexus is None:
        raise ValueError("board must include A start, R rival, and N nexus")
    spec = SPRITE_SPECS[species_id]
    return ArenaState(
        seed=seed,
        turn=0,
        board=BOARD,
        player_pos=start,
        rival_pos=rival,
        creature=Creature(
            species_id=species_id,
            name=spec["name"],
            tongue=spec["tongue"],
            hp=24,
            energy=18,
            atk=5,
        ),
        berries=berries,
        hazards=hazards,
        training_pads=training_pads,
        nexus_pos=nexus,
    )


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def cell_at(state: ArenaState, pos: tuple[int, int]) -> str:
    return state.board[pos[0]][pos[1]]


def is_open(state: ArenaState, pos: tuple[int, int]) -> bool:
    row, col = pos
    return 0 <= row < len(state.board) and 0 <= col < len(state.board[0]) and cell_at(state, pos) != "#"


def legal_actions(state: ArenaState) -> list[str]:
    actions: list[str] = []
    for action, (dr, dc) in MOVE_DELTAS.items():
        target = (state.player_pos[0] + dr, state.player_pos[1] + dc)
        if is_open(state, target):
            actions.append(action)
    actions.extend(["REST", "BOND"])
    if state.player_pos in state.training_pads:
        actions.append("TRAIN")
    if manhattan(state.player_pos, state.rival_pos) <= 1:
        actions.append("BATTLE")
    return actions


def observation(state: ArenaState) -> dict[str, Any]:
    creature = state.creature
    return {
        "turn": state.turn,
        "position": list(state.player_pos),
        "cell": cell_at(state, state.player_pos),
        "creature": asdict(creature),
        "rival_distance": manhattan(state.player_pos, state.rival_pos),
        "nexus_distance": manhattan(state.player_pos, state.nexus_pos),
        "berries_remaining": [list(pos) for pos in sorted(state.berries)],
        "legal_actions": legal_actions(state),
        "objective": "train once, win one battle, then reach the nexus",
    }


def shortest_move(state: ArenaState, goals: set[tuple[int, int]]) -> str:
    queue = deque([(state.player_pos, [])])
    seen = {state.player_pos}
    while queue:
        pos, path = queue.popleft()
        if pos in goals and path:
            return path[0]
        for action, (dr, dc) in MOVE_DELTAS.items():
            nxt = (pos[0] + dr, pos[1] + dc)
            if nxt in seen or not is_open(state, nxt):
                continue
            seen.add(nxt)
            queue.append((nxt, [*path, action]))
    return "REST"


def choose_policy_action(state: ArenaState) -> tuple[str, str]:
    creature = state.creature
    legal = legal_actions(state)
    if creature.hp <= 10 or creature.energy <= 3:
        return "REST", "recover before pushing the route"
    if state.player_pos in state.berries and creature.energy < 20:
        return "REST", "consume berry cell recovery"
    if creature.atk < 7:
        if "TRAIN" in legal:
            return "TRAIN", "raise attack before sparring"
        return shortest_move(state, state.training_pads), "route to training pad"
    if creature.xp < 1:
        if "BATTLE" in legal:
            return "BATTLE", "sparring rival is adjacent"
        return shortest_move(state, {state.rival_pos}), "route to rival"
    if state.player_pos == state.nexus_pos:
        return "BOND", "arrived at nexus; stabilize bond receipt"
    return shortest_move(state, {state.nexus_pos}), "route to nexus after verified win"


def step(state: ArenaState, action: str) -> dict[str, Any]:
    before = observation(state)
    creature = state.creature
    reward = -0.05
    events: list[str] = []
    valid = action in legal_actions(state)
    if not valid:
        reward -= 2.0
        events.append("invalid_action")
    elif action in MOVE_DELTAS:
        dr, dc = MOVE_DELTAS[action]
        state.player_pos = (state.player_pos[0] + dr, state.player_pos[1] + dc)
        creature.energy = max(0, creature.energy - 1)
        events.append(f"move:{action.lower()}")
        if state.player_pos in state.hazards:
            creature.hp = max(0, creature.hp - 4)
            reward -= 1.0
            events.append("hazard_damage")
        if state.player_pos in state.berries:
            creature.energy = min(24, creature.energy + 6)
            creature.hp = min(28, creature.hp + 3)
            state.berries.remove(state.player_pos)
            reward += 0.7
            events.append("berry_recovered")
    elif action == "REST":
        creature.energy = min(24, creature.energy + 5)
        creature.hp = min(28, creature.hp + 2)
        reward += 0.1
        events.append("rest")
    elif action == "BOND":
        creature.bond = min(10, creature.bond + 1)
        creature.energy = max(0, creature.energy - 1)
        reward += 0.1
        events.append("bond")
    elif action == "TRAIN":
        creature.energy = max(0, creature.energy - 4)
        creature.atk += 1
        creature.bond = min(10, creature.bond + 1)
        reward += 1.0
        events.append("train_atk")
    elif action == "BATTLE":
        rng = random.Random(state.seed + state.turn * 17 + creature.atk * 31)
        rival_power = 8 + rng.randint(-1, 2)
        power = creature.atk + creature.bond
        if power >= rival_power:
            creature.xp += 1
            creature.energy = max(0, creature.energy - 3)
            reward += 2.0
            events.append("battle_win")
        else:
            creature.hp = max(0, creature.hp - 7)
            creature.energy = max(0, creature.energy - 2)
            reward -= 1.5
            events.append("battle_loss")

    if creature.hp <= 0:
        state.done = True
        state.success = False
        reward -= 4.0
        events.append("fainted")
    elif creature.xp >= 1 and creature.atk >= 7 and state.player_pos == state.nexus_pos:
        state.done = True
        state.success = True
        reward += 5.0
        events.append("nexus_complete")

    state.turn += 1
    after = observation(state)
    return {
        "tick": state.turn,
        "before": before,
        "action": action,
        "valid": valid,
        "events": events,
        "reward": round(reward, 3),
        "after": after,
        "done": state.done,
        "success": state.success,
    }


def run_episode(seed: int, *, max_ticks: int = 40, species_id: str = "kindlemote") -> dict[str, Any]:
    state = parse_board(seed, species_id)
    ticks: list[dict[str, Any]] = []
    total_reward = 0.0
    while not state.done and state.turn < max_ticks:
        obs = observation(state)
        action, reason = choose_policy_action(state)
        record = step(state, action)
        record["policy"] = {
            "name": "simple_aethermon_curriculum_policy",
            "reason": reason,
            "observed_legal_actions": obs["legal_actions"],
        }
        total_reward += record["reward"]
        ticks.append(record)
    return {
        "schema": "aethermon_training_episode_v1",
        "seed": seed,
        "species_id": species_id,
        "board": BOARD,
        "success": state.success,
        "turns": state.turn,
        "total_reward": round(total_reward, 3),
        "final_observation": observation(state),
        "ticks": ticks,
    }


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    height = len(pixels)
    width = len(pixels[0])
    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in pixels)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def blank(size: int = 24) -> list[list[tuple[int, int, int, int]]]:
    return [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]


def put(pixels: list[list[tuple[int, int, int, int]]], x: int, y: int, color: tuple[int, int, int, int]) -> None:
    if 0 <= y < len(pixels) and 0 <= x < len(pixels[0]):
        pixels[y][x] = color


def draw_blob(
    base: tuple[int, int, int, int],
    *,
    wings: bool = False,
    horns: bool = False,
    square: bool = False,
) -> list[list[tuple[int, int, int, int]]]:
    pixels = blank()
    outline = (35, 35, 45, 255)
    shade = tuple(max(0, c - 42) if i < 3 else c for i, c in enumerate(base))
    for y in range(5, 19):
        for x in range(5, 19):
            if square:
                inside = 6 <= x <= 17 and 6 <= y <= 17
            else:
                inside = ((x - 12) / 7.0) ** 2 + ((y - 12) / 6.5) ** 2 <= 1.0
            if inside:
                put(pixels, x, y, base if y < 13 else shade)
    for y in range(4, 20):
        for x in range(4, 20):
            if pixels[y][x][3] == 0 and any(
                pixels[ny][nx][3] > 0
                for ny in range(max(0, y - 1), min(24, y + 2))
                for nx in range(max(0, x - 1), min(24, x + 2))
            ):
                put(pixels, x, y, outline)
    if wings:
        for y in range(8, 16):
            for x in range(1, 7):
                if abs(y - 12) + x < 9:
                    put(pixels, x, y, base)
                    put(pixels, 23 - x, y, base)
    if horns:
        for i in range(4):
            put(pixels, 7 + i, 4 - i // 2, outline)
            put(pixels, 16 - i, 4 - i // 2, outline)
    put(pixels, 9, 10, (255, 255, 255, 255))
    put(pixels, 15, 10, (255, 255, 255, 255))
    put(pixels, 9, 11, (20, 20, 30, 255))
    put(pixels, 15, 11, (20, 20, 30, 255))
    return pixels


def write_sprite_assets() -> dict[str, Any]:
    sprite_dir = GODOT_AETHERMON_DIR / "sprites"
    sprite_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": "aethermon_godot_training_manifest_v1",
        "tile_size": 24,
        "sprites": {},
        "board": BOARD,
        "legend": {
            "#": "wall",
            ".": "floor",
            "A": "aethermon start",
            "T": "training pad",
            "B": "berry recovery",
            "H": "hazard",
            "R": "rival",
            "N": "nexus goal",
        },
    }
    for species_id, spec in SPRITE_SPECS.items():
        color = TONGUE_COLORS[spec["tongue"]]
        pixels = draw_blob(
            color,
            wings=species_id == "galewing",
            horns=species_id in {"gloomkit", "rival_venom"},
            square=species_id == "bitling",
        )
        path = sprite_dir / f"{species_id}.png"
        write_png(path, pixels)
        manifest["sprites"][species_id] = {
            **spec,
            "path": f"res://assets/aethermon/sprites/{species_id}.png",
        }

    tile_specs = {
        "berry": (70, 190, 95, 255),
        "training_pad": (245, 185, 75, 255),
        "hazard": (180, 70, 80, 255),
        "nexus": (105, 220, 225, 255),
    }
    for tile_id, color in tile_specs.items():
        pixels = blank()
        for y in range(6, 18):
            for x in range(6, 18):
                if tile_id == "nexus":
                    if abs(x - 12) + abs(y - 12) < 9:
                        put(pixels, x, y, color)
                elif tile_id == "hazard":
                    if y >= 6 + abs(x - 12):
                        put(pixels, x, y, color)
                else:
                    put(pixels, x, y, color)
        path = sprite_dir / f"{tile_id}.png"
        write_png(path, pixels)
        manifest["sprites"][tile_id] = {
            "name": tile_id.replace("_", " ").title(),
            "role": "tile",
            "path": f"res://assets/aethermon/sprites/{tile_id}.png",
        }

    manifest_path = GODOT_AETHERMON_DIR / "training_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def write_outputs(episode: dict[str, Any], artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "episode_summary.json").write_text(
        json.dumps({k: v for k, v in episode.items() if k != "ticks"}, indent=2),
        encoding="utf-8",
    )
    with (artifact_dir / "episode_receipts.jsonl").open("w", encoding="utf-8") as f:
        for tick in episode["ticks"]:
            f.write(json.dumps(tick, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AETHERMON AI training arena.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-ticks", type=int, default=40)
    parser.add_argument("--species", default="kindlemote", choices=sorted(SPRITE_SPECS))
    parser.add_argument("--out", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--no-assets", action="store_true", help="Do not rewrite Godot sprite manifest/assets.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.no_assets:
        write_sprite_assets()
    episode = run_episode(args.seed, max_ticks=args.max_ticks, species_id=args.species)
    write_outputs(episode, args.out)

    summary = {
        "success": episode["success"],
        "turns": episode["turns"],
        "total_reward": episode["total_reward"],
        "summary": str(args.out / "episode_summary.json"),
        "receipts": str(args.out / "episode_receipts.jsonl"),
        "godot_manifest": str(GODOT_AETHERMON_DIR / "training_manifest.json"),
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("AETHERMON training arena")
        print(f"  success:       {summary['success']}")
        print(f"  turns:         {summary['turns']}")
        print(f"  total reward:  {summary['total_reward']}")
        print(f"  summary:       {summary['summary']}")
        print(f"  receipts:      {summary['receipts']}")
        print(f"  Godot manifest:{summary['godot_manifest']}")
    return 0 if episode["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
