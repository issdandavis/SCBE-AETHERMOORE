"""Agent senses — give the AI eyes and hands through YOUR tools, governed.

This is the bridge the doctrine asks for: "I want my tools to let YOU as well be
able to see and use things." It wires two existing, dependency-free modules into
a toolset an AI agent (or a human) can drive, where EVERY call is first judged by
the SCBE governance seam and written to the GeoSeal receipt ledger.

    SEE / ACT      src/video_lattice/tiny_engine.py  — a small world the agent can
                   look at (a symbol grid) and move an entity inside.
    REMEMBER /     src/video_lattice/vector_index.py — a local cosine memory the
    RECALL         agent writes notes into and recalls by meaning.

Nothing here invents new math or pulls new dependencies. The embedding for memory
is a deterministic hashed bag-of-trigrams (stdlib hashlib), so recall is stable
across separate process invocations — which is what lets the agent call the CLI
one action at a time and still share state.

Doctrine: programmatic for the AI (``--json`` on every command), simple and
useful for a human (a readable board + one-line receipt by default).

CLI (state persists under .scbe/aether/senses/):
    python agent_senses.py look
    python agent_senses.py move <entity_id> <dx> <dy>
    python agent_senses.py remember <key> "<text>"
    python agent_senses.py recall "<query>" [-k N]
    python agent_senses.py reset
Add --json to any command for a machine-readable result.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parents[1]
for _p in (str(_REPO_ROOT), str(_PKG_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@contextlib.contextmanager
def _silence_native_stdout():
    """Redirect C-level stdout (fd 1) to devnull so import-time banners from
    native libs (e.g. liboqs' 'faulthandler is disabled') can't corrupt the
    --json contract. Restores fd 1 on exit."""
    saved = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        sys.stdout.flush()
        os.dup2(devnull, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(devnull)
        os.close(saved)


with _silence_native_stdout():  # the governance seam pulls in liboqs
    from src.video_lattice.tiny_engine import Entity, TinyWorld, demo_world  # noqa: E402,F401
    from src.video_lattice.vector_index import LocalVectorIndex  # noqa: E402
    from governance_seam import GovernanceSeam, SeamDecision  # noqa: E402
    from tongue_embed import dominant_tongue, tongue_embed  # noqa: E402

_STATE_DIR = _REPO_ROOT / ".scbe" / "aether" / "senses"
_WORLD_PATH = _STATE_DIR / "world.json"
_MEMORY_PATH = _STATE_DIR / "memory.json"
_EMBED_DIM = 96  # the tongue embedding's dimension (6 governance axes + fingerprint)


# --------------------------------------------------------------------------- #
# Memory embedding: the Six Sacred Tongues basis (see tongue_embed.py). The
# governance channel is load-bearing (null-tested in bench_tongue_embed.py); the
# fingerprint channel is a graceful fallback for text the tongue lexicon doesn't
# cover. Deterministic across processes so memory survives separate CLI calls.
# --------------------------------------------------------------------------- #
def embed_text(text: str, dim: int = _EMBED_DIM) -> np.ndarray:
    return tongue_embed(text, dim=dim)


# --------------------------------------------------------------------------- #
# The governed senses.
# --------------------------------------------------------------------------- #
class AgentSenses:
    """Eyes (look / recall) and hands (move / remember), each one governed."""

    def __init__(self, seam: Optional[GovernanceSeam] = None) -> None:
        self.seam = seam or GovernanceSeam()
        self.world = self._load_world()
        self.memory = self._load_memory()

    # ---- persistence -------------------------------------------------- #
    def _load_world(self) -> TinyWorld:
        if _WORLD_PATH.exists():
            return TinyWorld.from_json(json.loads(_WORLD_PATH.read_text(encoding="utf-8")))
        return demo_world()

    def _save_world(self) -> None:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _WORLD_PATH.write_text(json.dumps(self.world.to_json(), sort_keys=True), encoding="utf-8")

    def _load_memory(self) -> LocalVectorIndex:
        if _MEMORY_PATH.exists():
            idx = LocalVectorIndex.load(_MEMORY_PATH)
            if idx.dim == _EMBED_DIM:
                return idx  # else fall through: old-dim memory, start fresh
        return LocalVectorIndex(dim=_EMBED_DIM)

    def _save_memory(self) -> None:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.memory.save(_MEMORY_PATH)

    # ---- the four senses ---------------------------------------------- #
    def look(self) -> dict[str, Any]:
        """SEE: render the world as a symbol grid + list what can be moved."""
        d = self.seam.govern("perceive_world", {"action": "look"})
        if not d.allowed:
            return _blocked(d)
        grid = self.world.to_symbol_grid()
        entities = {
            e.entity_id: {"glyph": self.world.sprites[e.sprite_id].glyph, "x": e.x, "y": e.y, "z": e.z}
            for e in self.world.entities.values()
        }
        return {"ok": True, "grid": grid, "entities": entities, "frame": self.world.frame_index, "receipt": d.receipt}

    def act(self, entity_id: str, dx: int, dy: int) -> dict[str, Any]:
        """ACT: move an entity in the world (governed before it happens)."""
        d = self.seam.govern("move_entity", {"entity_id": entity_id, "dx": dx, "dy": dy})
        if not d.allowed:
            return _blocked(d)
        if entity_id not in self.world.entities:
            return {"ok": False, "error": f"no entity '{entity_id}'", "receipt": d.receipt}
        try:
            moved = self.world.move_entity(entity_id, int(dx), int(dy))
        except (KeyError, IndexError, ValueError) as exc:
            return {"ok": False, "error": f"blocked move: {exc}", "receipt": d.receipt}
        self._save_world()
        return {"ok": moved, "moved": moved, "entity": entity_id, "frame": self.world.frame_index, "receipt": d.receipt}

    def remember(self, key: str, text: str) -> dict[str, Any]:
        """REMEMBER: store a note in semantic memory (governed)."""
        d = self.seam.govern("write_memory", {"key": key, "text": text})
        if not d.allowed:
            return _blocked(d)
        tongue = dominant_tongue(text)  # governance tag: which tongue the note speaks
        self.memory.add(key, embed_text(text), modality="note", metadata={"key": key, "text": text, "tongue": tongue})
        self._save_memory()
        return {"ok": True, "stored": key, "tongue": tongue, "count": len(self.memory.records), "receipt": d.receipt}

    def recall(self, query: str, k: int = 3) -> dict[str, Any]:
        """RECALL: retrieve the closest notes by meaning (governed)."""
        d = self.seam.govern("read_memory", {"query": query, "k": k})
        if not d.allowed:
            return _blocked(d)
        hits = self.memory.search(embed_text(query), top_k=k)
        matches = [
            {
                "key": h.record_id,
                "score": round(h.score, 3),
                "tongue": h.metadata.get("tongue"),
                "text": h.metadata.get("text", ""),
            }
            for h in hits
        ]
        return {"ok": True, "query": query, "tongue": dominant_tongue(query), "matches": matches, "receipt": d.receipt}

    def reset(self) -> dict[str, Any]:
        """Fresh world + empty memory."""
        self.world = demo_world()
        self.memory = LocalVectorIndex(dim=_EMBED_DIM)
        self._save_world()
        self._save_memory()
        return {"ok": True, "reset": True}


def _blocked(d: SeamDecision) -> dict[str, Any]:
    return {"ok": False, "blocked": True, "decision": d.decision, "reason": d.reason, "receipt": d.receipt}


# --------------------------------------------------------------------------- #
# CLI — dual surface (human board by default, --json for the agent).
# --------------------------------------------------------------------------- #
def _print_human(cmd: str, result: dict[str, Any], seam: GovernanceSeam) -> None:
    if result.get("blocked"):
        print(f"  ✗ governance blocked this {cmd}: {result['reason']}")
    if cmd == "look" and result.get("ok"):
        print("\n  the agent sees:\n")
        for row in result["grid"]:
            print("    " + row)
        print()
        for eid, e in result["entities"].items():
            print(f"    {e['glyph']}  {eid:<14} at ({e['x']},{e['y']})")
        print(f"\n  frame {result['frame']}")
    elif cmd == "move" and "moved" in result:
        verb = "moved" if result["moved"] else "could not move (blocked by terrain)"
        print(f"  {verb}: {result['entity']}  → frame {result.get('frame')}")
    elif cmd == "remember" and result.get("ok"):
        tag = f" · speaks {result['tongue']}" if result.get("tongue") else ""
        print(f"  remembered '{result['stored']}'{tag}  (memory holds {result['count']} notes)")
    elif cmd == "recall" and result.get("ok"):
        qtag = f" (query speaks {result['tongue']})" if result.get("tongue") else ""
        print(f"\n  recall \"{result['query']}\"{qtag}:")
        for m in result["matches"]:
            mtag = f" {m['tongue']}" if m.get("tongue") else ""
            print(f"    {m['score']:+.2f} [{mtag.strip() or '··'}] {m['text']}")
        if not result["matches"]:
            print("    (nothing remembered yet)")
    elif cmd == "reset":
        print("  world + memory reset.")
    rec = result.get("receipt")
    if rec:
        d = SeamDecision(decision=rec["decision"], allowed=rec["allowed"], tripped=False, reason="", receipt=rec)
        print(seam.stamp(d))


def main(argv: Optional[list[str]] = None) -> int:
    # --json is shared so it works before OR after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output for the agent")

    parser = argparse.ArgumentParser(
        description="Governed agent senses (see / act / remember / recall).", parents=[common]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("look", help="see the world", parents=[common])
    p_move = sub.add_parser("move", help="move an entity", parents=[common])
    p_move.add_argument("entity_id")
    p_move.add_argument("dx", type=int)
    p_move.add_argument("dy", type=int)
    p_rem = sub.add_parser("remember", help="store a note", parents=[common])
    p_rem.add_argument("key")
    p_rem.add_argument("text")
    p_rec = sub.add_parser("recall", help="recall notes by meaning", parents=[common])
    p_rec.add_argument("query")
    p_rec.add_argument("-k", type=int, default=3)
    sub.add_parser("reset", help="fresh world + empty memory", parents=[common])

    args = parser.parse_args(argv)
    # A subparser's --json default can clobber the parent's True, so trust argv.
    want_json = args.json or ("--json" in (argv if argv is not None else sys.argv[1:]))
    senses = AgentSenses()

    if args.cmd == "look":
        result = senses.look()
    elif args.cmd == "move":
        result = senses.act(args.entity_id, args.dx, args.dy)
    elif args.cmd == "remember":
        result = senses.remember(args.key, args.text)
    elif args.cmd == "recall":
        result = senses.recall(args.query, args.k)
    else:
        result = senses.reset()

    if want_json:
        print(json.dumps(result, sort_keys=True))
    else:
        _print_human(args.cmd, result, senses.seam)
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
