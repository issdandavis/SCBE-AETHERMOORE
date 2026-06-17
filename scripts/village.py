#!/usr/bin/env python3
"""Aether Village -- a spatial / flow-based face on the Forge. Made inside-out.

Flow-based programming (NoFlo / Node-RED) says: a program is a network of black-box
components wired by data flow, and "the graph IS the program." Flowgorithm says:
draw a shape, give it a definition, and it runs. This is that -- as a VILLAGE.

  - a BUILDING is a defined shape: one Forge move (a real, verified capability).
  - a ROAD is data flow between buildings (the order things happen).
  - the MAP is the program: it compiles, runs, and carries one lossless deed.

It is AI-FIRST: the village is DATA the AI authors (to_dict / from_dict / from_plan),
and renders as a map for humans -- same object, two views. The semantic core (moves,
signature, Turing base) is the inside; this form grows out of it.

    python scripts/village.py            # an AI lays out a village, renders + compiles it
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge import _MOVES, _exec, assemble, prime_signature, render_glyph  # noqa: E402


class Village:
    def __init__(self):
        self.buildings: list[dict] = []   # {id, move, x, y}
        self.roads: list[tuple] = []      # (from_id, to_id) -- data flows along it

    # ---- authoring (what an AI does: it writes the village as data) ----
    def place(self, move: str, x: int | None = None, y: int = 0) -> int:
        bid = len(self.buildings)
        self.buildings.append({"id": bid, "move": move, "x": bid if x is None else x, "y": y})
        return bid

    def road(self, a: int, b: int):
        self.roads.append((a, b))

    @classmethod
    def from_plan(cls, moves: list[str]) -> "Village":
        """AI hands a flow; lay it out as a street with roads between the buildings."""
        v = cls()
        prev = None
        for m in moves:
            bid = v.place(m)
            if prev is not None:
                v.road(prev, bid)
            prev = bid
        return v

    @classmethod
    def from_dict(cls, d: dict) -> "Village":
        v = cls()
        v.buildings = d["buildings"]
        v.roads = [tuple(r) for r in d["roads"]]
        return v

    def to_dict(self) -> dict:
        return {"buildings": self.buildings, "roads": self.roads}

    # ---- the program = the flow order of the buildings ----
    def flow_order(self) -> list[str]:
        succ = {a: b for a, b in self.roads}
        starts = {b["id"] for b in self.buildings} - {b for _, b in self.roads}
        order, seen = [], set()
        cur = min(starts) if starts else (self.buildings[0]["id"] if self.buildings else None)
        by_id = {b["id"]: b for b in self.buildings}
        while cur is not None and cur not in seen:
            seen.add(cur)
            order.append(by_id[cur]["move"])
            cur = succ.get(cur)
        for b in self.buildings:  # any unwired buildings, in placement order
            if b["id"] not in seen:
                order.append(b["move"])
        return order

    # ---- the MAP (the human view) ----
    def render(self) -> str:
        order_ids = []
        succ = {a: b for a, b in self.roads}
        starts = {b["id"] for b in self.buildings} - {b for _, b in self.roads}
        cur = min(starts) if starts else (self.buildings[0]["id"] if self.buildings else None)
        by_id = {b["id"]: b for b in self.buildings}
        seen = set()
        while cur is not None and cur not in seen:
            seen.add(cur); order_ids.append(cur); cur = succ.get(cur)
        for b in self.buildings:
            if b["id"] not in seen:
                order_ids.append(b["id"])
        labels = [by_id[i]["move"][:6].center(6) for i in order_ids]
        tops = "  ".join(".----." for _ in labels)
        mids = "->".join(f"|{l}|" for l in labels)
        bots = "  ".join("'----'" for _ in labels)
        return "\n".join(["   " + tops, "   " + mids, "   " + bots])

    # ---- compile + verify (the graph really runs) ----
    def compile_and_verify(self):
        moves = ["app village"] + self.flow_order()
        name, src, warnings, used = assemble(moves)
        with tempfile.TemporaryDirectory() as d:
            app = Path(d) / f"{name}.py"
            app.write_text(src, encoding="utf-8")
            rc, _out = _exec(app, ["--help"])
        sig = prime_signature(used)
        return {"moves": used, "lines": src.count("\n") + 1, "runs": rc == 0,
                "warnings": warnings, "deed": sig, "glyph": render_glyph(sig)}


def main():
    # An AI lays out a village -- it just writes the flow; the form follows.
    print("\n  An AI authors a village (it writes data; the map + program follow):\n")
    v = Village.from_plan(["add", "due", "agenda", "find"])

    print(v.render())
    print("\n  the village IS the program. compiling it...")
    r = v.compile_and_verify()
    print(f"   -> {len(r['moves'])} buildings: {', '.join(r['moves'])}")
    print(f"   -> {r['lines']} lines of real code; assembles + runs: {'YES' if r['runs'] else 'NO'}")
    print(f"   -> the village's deed (one lossless number): {r['deed']}")
    print("   -> its shape (the deed, folded):")
    for row in r["glyph"]:
        print("        " + row)

    print("\n  what the AI sees (the village as data it can read + rewrite):")
    import json
    print("   " + json.dumps(v.to_dict())[:200] + " ...")
    print()


if __name__ == "__main__":
    main()
