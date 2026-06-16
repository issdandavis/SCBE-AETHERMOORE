"""
Origami — when the cube goes flat, it becomes paper you can fold.
=================================================================

A cube unfolds to a flat NET (six faces in a cross). A flat net is a sheet of paper.
Once you have paper, a FOLD is a real operation — a crease that reflects part of the
sheet — and you can fold the sheet into figures: a fan (accordion), a crane (bird
base), or the number-folding game (a fortune teller / cootie-catcher).

The fortune teller is the interesting one: it's a little PAPER COMPUTER. Eight cells
hold values; you pick numbers, the picks fold your way through the flaps, and you land
on one value — a deterministic map from a number sequence to a result. Build one from
a cube program and its eight cells become opcodes, so folding picks you a command.
"""

from __future__ import annotations

from typing import List, Sequence

from . import polyglot as P

# the standard cross net of a cube — six faces, the four arms creased to the centre.
# faces double as the six Sacred Tongues (U=RU, F=UM, R=KO, B=DR, L=AV, D=CA).
NET = [
    [" ", "U", " ", " "],
    ["L", "F", "R", "B"],
    [" ", "D", " ", " "],
]


def unfold() -> List[List[str]]:
    """The cube as a flat sheet: its six-face cross net (the 'flat surface' moment)."""
    return [row[:] for row in NET]


def render_net(net: Sequence[Sequence[str]] | None = None) -> str:
    net = net or NET
    out = []
    for row in net:
        out.append(" ".join("[%s]" % c if c.strip() else "   " for c in row))
    return "\n".join(out)


# --- folds: a crease is a mountain (M) or a valley (V) -------------------------
def accordion(n: int) -> List[str]:
    """A fan: n parallel creases alternating mountain/valley."""
    return ["M" if i % 2 == 0 else "V" for i in range(n)]


def crease_pattern(folds: Sequence[str], height: int = 3) -> str:
    """Render parallel creases: mountain = solid │, valley = dashed ┊."""
    glyph = {"M": "│", "V": "┊"}
    cols = "   ".join(glyph.get(f, "│") for f in folds)
    label = "   ".join(folds)
    rows = "\n".join(cols for _ in range(height))
    return rows + "\n" + label


# the crane, as its real fold sequence (bird base -> neck/tail/head/wings)
CRANE_STEPS = (
    "square base (fold both diagonals + both midlines, collapse)",
    "petal fold front flap up", "petal fold back flap up",
    "valley-fold lower edges to centre (both sides)",
    "inside-reverse-fold the two points up (neck + tail)",
    "inside-reverse-fold the neck tip down (head)",
    "fold the wings down",
)


def crane() -> List[str]:
    return list(CRANE_STEPS)


# --- the number-folding game: a fortune teller / paper computer ----------------
class FortuneTeller:
    """Eight cells under eight flaps. Pick numbers; the picks fold (open/close) your
    way to one cell. Deterministic: all picks but the last set the orientation by the
    PARITY of opens; the last pick chooses among the four flaps then visible."""

    def __init__(self, values: Sequence[object]):
        vals = list(values)
        if len(vals) != 8:
            raise ValueError("a fortune teller has exactly 8 cells, got %d" % len(vals))
        self.values = vals

    def play(self, picks: Sequence[int]) -> object:
        if not picks:
            raise ValueError("need at least one pick (the final flap)")
        orient = 0
        for n in picks[:-1]:                 # each open/close flips orientation by parity
            orient ^= (int(n) & 1)
        visible = [orient + 2 * k for k in range(4)]   # the 4 flaps showing in this orientation
        cell = visible[(int(picks[-1]) - 1) % 4]
        return self.values[cell]

    def flaps(self) -> List[object]:
        return list(self.values)

    @classmethod
    def from_program(cls, op_names: Sequence[str]) -> "FortuneTeller":
        """Eight cells = the program's opcodes, cycled/padded to 8 (cube -> paper)."""
        ops = list(op_names) or ["add"]
        cells = [ops[i % len(ops)] for i in range(8)]
        return cls(cells)


def _run_op(op_name: str) -> object:
    """Run a single-op program on the default args (for a landed fortune)."""
    prog = P.program_bytes(op_name)
    ns: dict = {}
    try:
        exec(compile(P.emit(prog, "python", safe=True), "<fortune>", "exec"), ns)  # noqa: S102
        return ns["tongue_fn"](2.0, 3.0, 4.0)
    except Exception:                        # pragma: no cover - defensive
        return None


def _demo() -> None:
    print("Origami — the flat cube as paper\n")
    print("the cube unfolds to a sheet (its net):")
    print(render_net(), "\n")
    print("fold it into a fan (6 creases):")
    print(crease_pattern(accordion(6)), "\n")
    print("...or a crane:", " -> ".join(CRANE_STEPS[:3]), "...\n")
    ft = FortuneTeller.from_program(["add", "mul", "sqrt", "inc"])
    picks = [4, 3, 2]
    landed = ft.play(picks)
    print("fortune teller built from [add mul sqrt inc], cells:", ft.flaps())
    print("pick %s -> flap '%s' -> runs to %s" % (picks, landed, _run_op(landed)))


if __name__ == "__main__":
    _demo()
