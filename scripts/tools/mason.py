#!/usr/bin/env python3
"""mason — build working code by setting pre-verified procedural STONES into a schematic.

The Dark Cloud / Georama model for code, made literal:

  - PIECE (a "stone"): a procedural code block with chisel-holes (parameters). The
    library holds stones for the common shapes a program needs.
  - SCHEMATIC (the "town plan"): an ordered list of SLOTS. Each slot names the stone
    to set, the chisel values, and the RESIDENT'S REQUEST — an executable acceptance
    check the set stone must satisfy *in place, next to the stones already set*.
  - The MASON (the small model's job, here scripted to prove the mechanism): for each
    slot, chisel the stone to fit, set it, and RUN the resident's request. A stone
    that passes is SEALED (a GeoSeal-style receipt) and kept; a stone that fails is
    CAPTURED — never placed (no empty spheres) — and the slot is flagged to ESCALATE
    to a bigger model.
  - The TOWN is complete when every stone is set, sealed, and the final integration
    request (the whole thing actually runs) passes.

The load-bearing core is honest: stones are real code, every "set" is verified by
real execution, and a stub cannot be placed. The kid-with-a-gauntlet theming is just
the legible interface. A model plugs in later as the mason — choosing and chiseling
stones — without changing any of this.

Run:
  python scripts/tools/mason.py build pacman_core [--json] [--out PATH]
  python scripts/tools/mason.py build pacman_core --inject-stub game   # show capture+escalate
  python scripts/tools/mason.py schematics
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The model ladder a real mason climbs when a block is too big to chisel or a stone
# keeps cracking. Escalation names the next rung; it does not call it here.
# boundary: this is the CAPABILITY axis (how HARD) — distinct from the AUTHORITY
# gate's ESCALATE verdict (how DANGEROUS) in src/governance. See docs/BOUNDARIES.md §2.
MODEL_LADDER = ["small (ollama/local)", "mid (hf)", "big (claude)"]


@dataclass(frozen=True)
class Piece:
    """A procedural stone: code with __H_<hole>__ chisel-points."""

    name: str
    shape: str
    template: str
    holes: tuple[str, ...] = ()

    def chisel(self, fills: dict) -> str:
        code = self.template
        for hole in self.holes:
            if hole not in fills:
                raise KeyError(f"piece {self.name!r} needs chisel value for {hole!r}")
            code = code.replace(f"__H_{hole}__", str(fills[hole]))
        return code.strip("\n")


@dataclass
class Slot:
    """One position in the town plan: which stone, how to chisel it, and the
    resident's request (acceptance) it must satisfy once set next to the others."""

    name: str
    piece: str
    acceptance: str
    fills: dict = field(default_factory=dict)


@dataclass
class Schematic:
    name: str
    slots: list[Slot]
    integration: str  # the whole-town request: does the assembled thing actually run?
    out_name: str


def _seal(code: str) -> str:
    return "geoseal:" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def _verify(defs_code: str, request_code: str) -> tuple[bool, str]:
    """Assemble the stones set so far + run the resident's request as a real program.

    Exit 0 means the request is satisfied in place. This is the only signal that
    counts — a stone is sealed only if the assembled module actually executes it
    correctly. No static guessing.
    """
    body = (
        defs_code
        + "\n\nif __name__ == '__main__':\n"
        + textwrap.indent(request_code.strip("\n"), "    ")
        + "\n    print('REQUEST_OK')\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as fh:
        fh.write(body)
        tmp = Path(fh.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(tmp)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        tmp.unlink(missing_ok=True)
    ok = proc.returncode == 0 and "REQUEST_OK" in proc.stdout
    detail = (proc.stderr or proc.stdout).strip().splitlines()
    return ok, (detail[-1] if detail else "")


def build(schematic: Schematic, pieces: dict, *, inject_stub: str | None = None, stubs: dict | None = None) -> dict:
    placed: list[str] = []
    log: list[dict] = []
    town_complete = False
    escalation = None
    stubs = stubs or {}

    for slot in schematic.slots:
        use_stub = inject_stub == slot.name and slot.piece in stubs
        piece = stubs[slot.piece] if use_stub else pieces[slot.piece]
        chiseled = piece.chisel(slot.fills)
        candidate = "\n\n".join(placed + [chiseled])
        ok, detail = _verify(candidate, slot.acceptance)
        if ok:
            placed.append(chiseled)
            log.append(
                {
                    "slot": slot.name,
                    "stone": piece.name,
                    "shape": piece.shape,
                    "stub_injected": use_stub,
                    "set": True,
                    "captured": False,
                    "seal": _seal(chiseled),
                }
            )
        else:
            # Captured: the stone does not fit in place. Never set an empty sphere —
            # flag the slot to a bigger model and stop (the town cannot rest on it).
            escalation = {
                "slot": slot.name,
                "stone": piece.name,
                "reason": detail or "resident's request failed",
                "escalate_to": MODEL_LADDER[1],
            }
            log.append(
                {
                    "slot": slot.name,
                    "stone": piece.name,
                    "shape": piece.shape,
                    "stub_injected": use_stub,
                    "set": False,
                    "captured": True,
                    "seal": None,
                    "reason": detail,
                }
            )
            break

    out_path = None
    if not escalation:
        assembled = "\n\n".join(placed) + "\n"
        ok, detail = _verify(assembled.rstrip("\n"), schematic.integration)
        town_complete = ok
        if ok:
            out_path = ROOT / "artifacts" / "mason" / schematic.out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            header = f'"""Built by mason from schematic {schematic.name!r}. Every block verified in place."""\n\n'
            out_path.write_text(header + assembled, encoding="utf-8")
        else:
            escalation = {
                "slot": "integration",
                "stone": "(whole town)",
                "reason": detail or "integration request failed",
                "escalate_to": MODEL_LADDER[2],
            }

    return {
        "schema_version": "scbe_mason_build_v1",
        "schematic": schematic.name,
        "stones_set": sum(1 for r in log if r["set"]),
        "stones_total": len(schematic.slots),
        "town_complete": town_complete,
        "escalation": escalation,
        "artifact": str(out_path.relative_to(ROOT)) if out_path else None,
        "log": log,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Procedural stone library — real, runnable, headless Pac-Man CORE (no graphics).
# These are the pre-cut stones; the mason only chooses, chisels, and sets them.
# ─────────────────────────────────────────────────────────────────────────────

PIECES: dict[str, Piece] = {
    "world": Piece(
        name="world",
        shape="config+level",
        holes=("POINTS",),
        template=(
            "LEVEL = '''\n" "#####\n" "#P..#\n" "#.#.#\n" "#...#\n" "#####\n" "'''\n" "POINTS_PER_DOT = __H_POINTS__"
        ),
    ),
    "maze": Piece(
        name="maze",
        shape="board",
        template=textwrap.dedent("""
            class Maze:
                def __init__(self, text):
                    self.grid = [list(r) for r in text.strip('\\n').splitlines()]
                    self.dots = set()
                    self.start = (1, 1)
                    for y, row in enumerate(self.grid):
                        for x, c in enumerate(row):
                            if c == '.':
                                self.dots.add((x, y))
                            elif c == 'P':
                                self.start = (x, y)

                def is_wall(self, x, y):
                    if y < 0 or y >= len(self.grid):
                        return True
                    row = self.grid[y]
                    if x < 0 or x >= len(row):
                        return True
                    return row[x] == '#'
            """).strip(),
    ),
    "player": Piece(
        name="player",
        shape="mover",
        template=textwrap.dedent("""
            class Player:
                def __init__(self, pos):
                    self.pos = pos

                def move(self, maze, dx, dy):
                    nx, ny = self.pos[0] + dx, self.pos[1] + dy
                    if not maze.is_wall(nx, ny):
                        self.pos = (nx, ny)
                    return self.pos
            """).strip(),
    ),
    "game": Piece(
        name="game",
        shape="rules+scorer",
        template=textwrap.dedent("""
            class Game:
                DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

                def __init__(self, text=LEVEL):
                    self.maze = Maze(text)
                    self.player = Player(self.maze.start)
                    self.score = 0
                    self.won = False

                def step(self, direction):
                    dx, dy = self.DIRS[direction]
                    self.player.move(self.maze, dx, dy)
                    if self.player.pos in self.maze.dots:
                        self.maze.dots.discard(self.player.pos)
                        self.score += POINTS_PER_DOT
                    self.won = not self.maze.dots
                    return self.score
            """).strip(),
    ),
}

# An "empty sphere" for the game slot: looks like a Game, but scoring never works.
# Used to demonstrate capture + escalation (the resident's request will reject it).
STUBS: dict[str, Piece] = {
    "game": Piece(
        name="game(STUB)",
        shape="rules+scorer",
        template=textwrap.dedent("""
            class Game:
                DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

                def __init__(self, text=LEVEL):
                    self.maze = Maze(text)
                    self.player = Player(self.maze.start)
                    self.score = 0
                    self.won = False

                def step(self, direction):
                    return self.score  # TODO: never eats dots, never scores
            """).strip(),
    ),
}

PACMAN_CORE = Schematic(
    name="pacman_core",
    out_name="pacman_core.py",
    slots=[
        Slot(
            name="world",
            piece="world",
            fills={"POINTS": 1},
            acceptance="assert POINTS_PER_DOT == 1\nassert 'P' in LEVEL",
        ),
        Slot(
            name="maze",
            piece="maze",
            acceptance=(
                "m = Maze(LEVEL)\n"
                "assert m.is_wall(0, 0)\n"
                "assert not m.is_wall(*m.start)\n"
                "assert len(m.dots) == 7, len(m.dots)"
            ),
        ),
        Slot(
            name="player",
            piece="player",
            acceptance=(
                "m = Maze(LEVEL)\n"
                "p = Player(m.start)\n"
                "p.move(m, 1, 0)\n"
                "assert p.pos == (2, 1), p.pos\n"
                "q = Player((1, 1))\n"
                "q.move(m, 0, -1)\n"
                "assert q.pos == (1, 1), q.pos"
            ),
        ),
        Slot(
            name="game",
            piece="game",
            acceptance=(
                "g = Game()\n" "g.step('right')\n" "assert g.score == POINTS_PER_DOT, g.score\n" "assert not g.won"
            ),
        ),
    ],
    integration=(
        "g = Game()\n"
        "for mv in ['right', 'right', 'down', 'down', 'left', 'left', 'up']:\n"
        "    g.step(mv)\n"
        "assert g.score == 7 * POINTS_PER_DOT, g.score\n"
        "assert g.won is True\n"
        "assert len(g.maze.dots) == 0\n"
        "g2 = Game()\n"
        "before = g2.player.pos\n"
        "g2.step('up')\n"
        "assert g2.player.pos == before, 'wall must block'"
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# Stone packs — drop a pure-data module into scripts/tools/mason_stones/ and its
# stones + schematics join the library. A pack module defines one PACK dict of
# plain strings/dicts and never executes anything itself; the loader builds the
# Piece/Slot/Schematic objects. A cracked pack is reported, never fatal.
# ─────────────────────────────────────────────────────────────────────────────

PACKS_DIR = Path(__file__).resolve().parent / "mason_stones"


def _piece_from_data(name: str, data: dict, *, stub: bool = False) -> Piece:
    return Piece(
        name=f"{name}(STUB)" if stub else name,
        shape=str(data["shape"]),
        template=str(data["template"]),
        holes=tuple(data.get("holes", ())),
    )


def _pack_entries(pack: dict) -> dict[str, tuple[Schematic, dict, dict]]:
    pieces = {n: _piece_from_data(n, d) for n, d in pack["pieces"].items()}
    stubs = {n: _piece_from_data(n, d, stub=True) for n, d in pack.get("stubs", {}).items()}
    unknown = set(stubs) - set(pieces)
    if unknown:
        raise ValueError(f"stubs for unknown pieces: {sorted(unknown)}")
    entries: dict[str, tuple[Schematic, dict, dict]] = {}
    for sname, sc in pack["schematics"].items():
        slots = [
            Slot(name=sl["name"], piece=sl["piece"], fills=dict(sl.get("fills", {})), acceptance=sl["request"])
            for sl in sc["slots"]
        ]
        for slot in slots:
            if slot.piece not in pieces:
                raise ValueError(f"schematic {sname!r} slot {slot.name!r} names unknown piece {slot.piece!r}")
        entries[sname] = (
            Schematic(name=sname, slots=slots, integration=sc["integration"], out_name=sc["out"]),
            pieces,
            stubs,
        )
    return entries


def _load_registry() -> tuple[dict[str, tuple[Schematic, dict, dict]], dict[str, str]]:
    registry: dict[str, tuple[Schematic, dict, dict]] = {"pacman_core": (PACMAN_CORE, PIECES, STUBS)}
    errors: dict[str, str] = {}
    if PACKS_DIR.is_dir():
        for path in sorted(PACKS_DIR.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"mason_stones_{path.stem}", path)
                mod = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(mod)
                pack = getattr(mod, "PACK", None)
                if not isinstance(pack, dict):
                    raise ValueError("module defines no PACK dict")
                for sname, entry in _pack_entries(pack).items():
                    if sname in registry:
                        raise ValueError(f"duplicate schematic name {sname!r}")
                    registry[sname] = entry
            except Exception as exc:  # a cracked pack must not break the library
                errors[path.name] = f"{type(exc).__name__}: {exc}"
    return registry, errors


REGISTRY, PACK_ERRORS = _load_registry()
SCHEMATICS = {name: entry[0] for name, entry in REGISTRY.items()}


def _print_human(result: dict) -> None:
    print(f"=== mason · building '{result['schematic']}' ===\n")
    for row in result["log"]:
        if row["set"]:
            stub = " (stub injected!)" if row["stub_injected"] else ""
            print(f"  set   {row['slot']:8s} <- {row['stone']:14s} [{row['shape']}]{stub}  sealed {row['seal'][8:20]}")
        else:
            reason = row.get("reason", "")
            print(f"  CRACK {row['slot']:8s} <- {row['stone']:14s}  resident's request failed: {reason}")
    print()
    if result["town_complete"]:
        print(f"  TOWN COMPLETE — {result['stones_set']}/{result['stones_total']} stones set + integration passed")
        print(f"  artifact: {result['artifact']} (real and runnable — every stone verified in place)")
    else:
        esc = result["escalation"] or {}
        print(f"  HALTED at '{esc.get('slot')}' — {result['stones_set']}/{result['stones_total']} stones set")
        print(f"  escalate to {esc.get('escalate_to')}: {esc.get('reason')}")
        print("  (no empty sphere was placed — the town does not rest on an unverified block)")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="scbe mason", description="Build code by setting verified procedural stones.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("build", help="build a schematic")
    pb.add_argument("schematic", choices=sorted(REGISTRY))
    pb.add_argument("--inject-stub", default=None, help="swap a slot's stone for an empty sphere (demo capture)")
    pb.add_argument("--json", action="store_true")
    sub.add_parser("schematics", help="list available schematics")

    args = ap.parse_args(argv)
    if args.cmd == "schematics":
        for name in sorted(REGISTRY):
            sc = REGISTRY[name][0]
            print(f"{name}: {len(sc.slots)} stones -> {sc.out_name}")
        for pack_file, err in PACK_ERRORS.items():
            print(f"CRACKED PACK {pack_file}: {err}")
        return 0

    schematic, pieces, stubs = REGISTRY[args.schematic]
    result = build(schematic, pieces, inject_stub=args.inject_stub, stubs=stubs)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)
    return 0 if result["town_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
