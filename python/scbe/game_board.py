"""game_board: a task IS a board game -- the rules are the governance, winning is the work.

The control surface for weak/free models, built as ONE recursive protocol. A board game is a small,
finite, ruled surface a weak model can reason over completely -- a 2D thinking scaffold standing in
for a deeper task ("2d so they can think 3d", not a literal chessboard). Three things make it a
governance surface, not just a metaphor:

  * RULES ARE WALLS -- a Game exposes ``legal_moves()``; the referee refuses anything else. You
    cannot make a move the game forbids, so an out-of-bounds action is impossible by construction.
  * MOVES ARE GOVERNED + SEALED -- every committed move goes through the desktop_access registry
    (allowlist + the never-delete screen) and is SHA-256 sealed, so a run is a tamper-evident record.
  * WINNING IS THE WORK -- a leaf game (``Task``) is one unit of real work; its single winning move
    fires a governed action (e.g. a sandboxed rename). Clear the field, do the job.

And it NESTS: a ``Field`` of mini-games is itself a ``Game`` (its moves advance its cells), so a cube
face is a Field of Fields -- the "field of mini-games on a cube" -- all driven by the same loop. Cells
are addressed on the reversible board.py cube, and the move record replays losslessly.

HONEST CAVEAT: this is a control/governance/audit surface. It keeps a weak model in-bounds and makes
every run provable -- it does NOT raise the model's raw coding ability. The benchmark number lives in
the engine; this is the chassis you bolt around it.

    python -m python.scbe.game_board     # play a governed tic-tac-toe, then clear a field of work
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field as dfield
from pathlib import Path
from typing import Callable, List, Optional, Protocol, Sequence, runtime_checkable

from . import board
from .desktop_access import Action, ActionRegistry
from .level_slice import build_registry, normalize

Player = Callable[["Game"], str]  # given a game, propose a move (a string the game understands)


@runtime_checkable
class Game(Protocol):
    """The uniform surface: rules (legal_moves), moves (play), and an objective end (over/won)."""

    def legal_moves(self) -> List[str]: ...
    def play(self, move: str) -> bool: ...  # apply iff legal; return whether it was applied
    def over(self) -> bool: ...
    def won(self) -> bool: ...  # the objective was met (the cell is "cleared")
    def render(self) -> str: ...


# --- a real, non-trivial game: proves the protocol is not a stub --------------------
_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


@dataclass
class TicTacToe:
    """3x3 tic-tac-toe. The solver plays ``solver``; ``won()`` means that mark made a line."""

    solver: str = "X"
    cells: List[str] = dfield(default_factory=lambda: [" "] * 9)
    turn: str = "X"

    def legal_moves(self) -> List[str]:
        return [str(i) for i in range(9) if self.cells[i] == " "]

    def _winner(self) -> Optional[str]:
        for a, b, c in _LINES:
            if self.cells[a] != " " and self.cells[a] == self.cells[b] == self.cells[c]:
                return self.cells[a]
        return None

    def play(self, move: str) -> bool:
        if move not in self.legal_moves():
            return False
        self.cells[int(move)] = self.turn
        self.turn = "O" if self.turn == "X" else "X"
        return True

    def over(self) -> bool:
        return self._winner() is not None or " " not in self.cells

    def won(self) -> bool:
        return self._winner() == self.solver

    def render(self) -> str:
        r = self.cells
        return " | ".join("".join(r[i : i + 3]).replace(" ", ".") for i in (0, 3, 6))


# --- a leaf game = one unit of real work: winning fires a governed action ------------
@dataclass
class Task:
    """A leaf mini-game. Its only legal move is the correct one (the wall); winning fires a governed,
    sealed action -- so clearing this cell DOES a unit of the job."""

    name: str
    target: str  # the single legal, winning move
    on_solve: Callable[[str], dict]  # governed action invoked on the winning move -> receipt
    solved: bool = False
    receipt: Optional[dict] = None

    def legal_moves(self) -> List[str]:
        return [] if self.solved else [self.target]

    def play(self, move: str) -> bool:
        if self.solved or move != self.target:
            return False
        self.solved = True
        self.receipt = self.on_solve(move)
        return True

    def over(self) -> bool:
        return self.solved

    def won(self) -> bool:
        return self.solved and (self.receipt or {}).get("decision") == "ALLOWED"

    def render(self) -> str:
        return "[%s] %s" % ("x" if self.solved else " ", self.name)


# --- the composite: a field of mini-games that is ITSELF a game (so it nests) --------
@dataclass
class Field:
    """A field of mini-games -- the pieces are games, clearing them is the work. A Field is a Game, so
    fields nest (a cube face is a Field of Fields). Cells are addressed on the board.py cube."""

    cells: List[Game]
    name: str = "field"

    def legal_moves(self) -> List[str]:
        # a move is "<cell> <submove>": advance an unfinished cell by one of its legal submoves
        out: List[str] = []
        for i, g in enumerate(self.cells):
            if not g.over():
                out += ["%d %s" % (i, m) for m in g.legal_moves()]
        return out

    def play(self, move: str) -> bool:
        head, _, sub = move.partition(" ")
        if not head.isdigit():
            return False
        i = int(head)
        if i >= len(self.cells) or self.cells[i].over():
            return False
        return self.cells[i].play(sub)

    def over(self) -> bool:
        return all(g.over() for g in self.cells)

    def won(self) -> bool:
        return bool(self.cells) and all(g.won() for g in self.cells)

    def addresses(self) -> List[tuple]:
        """Each cell's coordinate on the reversible board.py 4x4x4 cube (band, mid, col)."""
        return [board.to_cube(i) for i in range(len(self.cells))]

    def render(self) -> str:
        addr = self.addresses()
        return "\n".join("    %d @ %s  %s" % (i, addr[i], g.render()) for i, g in enumerate(self.cells))


# --- the one loop that drives ANY game, governed + sealed ---------------------------
def greedy_player(game: Game) -> str:
    """The simplest player: take the first legal move. Good enough to clear a Task field."""
    moves = game.legal_moves()
    return moves[0] if moves else ""


def add_move_action(reg: ActionRegistry) -> ActionRegistry:
    """Give a registry a sealed, screened ``commit_move`` action (the move audit channel)."""
    reg.register(
        Action(
            "commit_move",
            "Commit a game move (sealed)",
            {"move": "string"},
            "safe",
            "#move",
            "button",
            "Move",
            lambda p: "move %s" % p.get("move", ""),
            # no text_param: a move is screened for destructive content by the deterministic all-param
            # screen, but it is NOT free-text intent (the L13 heuristic false-positives on short ids).
        )
    )
    return reg


def play_governed(
    game: Game, player: Player = greedy_player, reg: Optional[ActionRegistry] = None, budget: int = 81
) -> dict:
    """Play a game to its end. The referee (the game's rules) refuses illegal moves; every committed
    move is screened + SHA-256 sealed; the move record replays losslessly off the board.py cube."""
    reg = reg if reg is not None else add_move_action(ActionRegistry())
    if "commit_move" not in reg.actions:
        add_move_action(reg)
    program: List[int] = []
    transcript: List[dict] = []
    plies = 0
    while not game.over() and plies < budget:
        plies += 1
        move = player(game)
        if move not in game.legal_moves():  # the rules are the walls -- referee refuses
            transcript.append({"ply": plies, "move": move, "status": "ILLEGAL"})
            break
        rec = reg.invoke("commit_move", {"move": move})  # the screen is a WALL, not just a log entry
        if rec["decision"] != "ALLOWED":  # a screened-out move is NOT played
            transcript.append({"ply": plies, "move": move, "status": "BLOCKED", "decision": rec["decision"]})
            break
        game.play(move)
        head = move.split()[0] if move else "0"
        program.append(int(head) & 0xF if head.isdigit() else 0)
        transcript.append({"ply": plies, "move": move, "status": "ok"})
    stones = board.place(program)
    return {
        "over": game.over(),
        "won": game.won(),
        "plies": plies,
        "sealed": reg.verify(),  # the move audit is tamper-evident
        "reversible": board.recover(stones) == program,  # the game record replays losslessly
        "transcript": transcript,
        "render": game.render(),
    }


def file_field(files: Sequence[str], reg: ActionRegistry) -> Field:
    """Build a field where each cell is a 'name this file' mini-game wired to a governed rename --
    clearing the field normalizes every file. This is level_slice expressed as a field of games."""
    cells: List[Game] = []
    for src in sorted(files):
        target = normalize(src)
        cells.append(
            Task(
                name=src,
                target=target,
                on_solve=lambda mv, s=src: reg.invoke("rename_file", {"src": s, "dst": mv}, confirm="game move"),
            )
        )
    return Field(cells, name="normalize-field")


def main(argv: Optional[Sequence[str]] = None) -> int:
    print("GAME BOARD  a task is a board game: rules = walls, moves = sealed, winning = the work\n")

    print("== a real game, governed + sealed: tic-tac-toe (greedy solver) ==")
    ttt = play_governed(TicTacToe())
    print("  final:", ttt["render"], " won(X):", ttt["won"], " plies:", ttt["plies"])
    print("  every move sealed:", ttt["sealed"], "  record replays losslessly:", ttt["reversible"])

    print("\n== a FIELD of mini-games whose wins do real work (sandbox only) ==")
    names = ["Draft One.tmp", "report.tmp", "NOTES final.tmp"]
    with tempfile.TemporaryDirectory(prefix="scbe-game-") as td:
        sandbox = Path(td)
        for f in names:
            (sandbox / f).write_text("x", encoding="utf-8")
        reg = add_move_action(build_registry(sandbox))
        fld = file_field(names, reg)
        print("  field (cells addressed on the cube):")
        print(fld.render())
        res = play_governed(fld, reg=reg)
        print("\n  cleared:", res["over"], " won (all cells did their work):", res["won"])
        print("  on disk:", sorted(p.name for p in sandbox.iterdir()))
        print("  all moves + renames sealed in one transcript:", res["sealed"])
    print("\n  same loop drove a 2-player game AND a field of work -- one recursive protocol.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
