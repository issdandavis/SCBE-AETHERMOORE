"""level_slice: the vertical slice -- one weak/free model clears ONE governed level, end to end.

This is the "Mario for weak AIs" loop wired together from the primitives, proving they COMPOSE:

  * the LEVEL is a real task with walls: a sandbox full of messy ``*.tmp`` files; winning is every
    file normalized to ``*.bak``. The win is checked by READING THE FILESYSTEM, not by trusting the
    model -- objective verification is the whole point (the user cannot read the output himself).
  * desktop_access is the GOVERNED HANDS: a path-confined ``rename_file`` action. Every move goes
    through the allowlist + the destructive-command screen (never-delete) and is SHA-256 sealed. A
    move that escapes the sandbox, or smuggles a destructive string in the new name, is refused.
  * pair_loop is the JUGGLING: the only genuine choice point -- the new filename -- is a BLANK with
    capability "name". The model is called ONLY there (improvise only when needed); a wrong guess is
    caught by the wall (the allowed set) and dropped, never corrupting the run. The name model is
    pluggable: the deterministic ``normalize`` stub proves the loop; drop a real free model in to
    measure it. Route by strength -- the model only ever does the one thing the slot needs.
  * context_ledger is the SELF-MEMORY: a todo per file, marked done as each clears, then PACKed to
    shorthand. A stateless model rehydrates its place by running ``recall``.
  * board.py is the LEDGER SURFACE -- the "rules as the board to etch onto" idea: each cleared move
    is a STONE placed in move order on the Go-board token grid, and the move record is REVERSIBLE
    (recover(stones) == the program). So the run leaves a replayable game record, not just a log.

    python -m python.scbe.level_slice          # build a sandbox, clear the level, print the receipts
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from . import board
from .context_ledger import Ledger
from .desktop_access import Action, ActionRegistry
from .pair_loop import BLANK, Blank, accepting_checker, run_loop, template_level

# capability the only blank needs; a real free model can be dropped into this slot
NAME = "name"
RENAME_OP = 0x1  # action code etched into each stone's opcode byte (board.py embedding)

NameModel = Callable[[str, str, Sequence[str]], str]  # (goal, out, allowed) -> proposed name


def normalize(name: str) -> str:
    """The target filename: lowercase, spaces -> dashes, ``.tmp`` -> ``.bak``. Pure + deterministic."""
    return name.lower().replace(" ", "-").replace(".tmp", ".bak")


def normalize_model(goal: str, out: str, allowed: Sequence[str]) -> str:
    """The default name model: computes the normalized name from the source (carried in ``goal``).

    Pluggable -- this is the slot a real free model fills. It is routed ONLY to the naming blank, so
    the model is measured purely on the one thing it is asked to do.
    """
    return normalize(goal)


def _confined(sandbox: Path, name: str) -> Optional[Path]:
    """Resolve ``name`` inside the sandbox, or None if it escapes (path-traversal wall)."""
    p = (sandbox / name).resolve()
    root = sandbox.resolve()
    return p if root == p or root in p.parents else None


def build_registry(sandbox: Path) -> ActionRegistry:
    """A registry whose hands can only touch the sandbox -- governed, sealed, path-confined."""
    reg = ActionRegistry()

    def list_files(_p: Dict[str, object]) -> object:
        return {"files": sorted(f.name for f in sandbox.iterdir() if f.is_file())}

    def rename_file(p: Dict[str, object]) -> object:
        src = _confined(sandbox, str(p.get("src", "")))
        dst = _confined(sandbox, str(p.get("dst", "")))
        if src is None or dst is None:
            return "refused: path escapes the sandbox"
        if not src.exists():
            return "no such file: %s" % p.get("src")
        if dst.exists():
            return "refused: %s already exists" % p.get("dst")
        src.rename(dst)
        return "renamed %s -> %s" % (src.name, dst.name)

    reg.register(Action("list_files", "List files in the sandbox", {}, "safe", "#files", "list", "Files", list_files))
    reg.register(
        Action(
            "rename_file",
            "Rename a file within the sandbox",
            {"src": "string", "dst": "string"},
            "guarded",  # a write -> needs a confirm reason; still screened + sealed
            "#rename",
            "button",
            "Rename",
            rename_file,
            text_param="dst",  # the proposed name is gated for destructive strings (never-delete)
        )
    )
    return reg


def run_level(
    files: Sequence[str],
    sandbox: Path,
    name_model: NameModel = normalize_model,
) -> dict:
    """Clear one governed normalization level; return every receipt so the win can be verified.

    The fixed structure (which file, the rename verb) is emitted free; the model is called only at
    the naming blank, and only its in-bounds answers are committed through the governed registry.
    """
    reg = build_registry(sandbox)
    led = Ledger("free-model")
    led.run("set goal normalize-tmp-to-bak")
    for f in files:
        led.run("todo %s" % f)

    program: List[int] = []  # the move record, as opcode bytes for the board embedding
    moves: List[dict] = []
    for i, src in enumerate(sorted(files)):
        target = normalize(src)
        # the ONE choice point: name the output. Walls = {target}; a wrong guess is dropped.
        lvl = template_level(BLANK, blanks=[Blank(NAME, [target])], name="rename:%s" % src, goal=src)
        res = run_loop(lvl, {NAME: name_model}, accepting_checker, default=name_model)
        if not res["cleared"]:
            led.run("note FAILED to name %s" % src)
            moves.append({"src": src, "decision": "NO_NAME", "result": "model never proposed a legal name"})
            continue
        proposed = res["output"]
        rec = reg.invoke("rename_file", {"src": src, "dst": proposed}, confirm="normalize")
        if rec["decision"] == "ALLOWED":
            led.run("done %s" % src)
            led.run("note %s -> %s" % (src, proposed))
            program.append((RENAME_OP << 4) | (i & 0xF))  # etch this move as a stone
        else:
            led.run("note REFUSED %s: %s" % (src, rec["result"]))
        moves.append({"src": src, "proposed": proposed, "decision": rec["decision"], "model_calls": res["model_calls"]})

    stones = board.place(program)  # the move record on the Go-board token grid
    on_disk = sorted(f.name for f in sandbox.iterdir() if f.is_file())
    won = bool(on_disk) and all(n.endswith(".bak") for n in on_disk)
    return {
        "won": won,
        "on_disk": on_disk,
        "moves": moves,
        "sealed": reg.verify(),  # the governed action receipts are tamper-evident
        "ledger_sealed": led.verify(),  # the self-memory event log is tamper-evident
        "pack": led.run("pack")["result"],  # the model's context, compacted to shorthand
        "stones": stones,
        "reversible": board.recover(stones) == program,  # the etched move record replays losslessly
    }


def _with_sandbox(files: Sequence[str], name_model: NameModel = normalize_model) -> dict:
    """Run a level in a throwaway tempdir sandbox -- never touches the real machine."""
    with tempfile.TemporaryDirectory(prefix="scbe-level-") as td:
        sandbox = Path(td)
        for f in files:
            (sandbox / f).write_text("x", encoding="utf-8")
        return run_level(files, sandbox, name_model=name_model)


def main(argv: Optional[Sequence[str]] = None) -> int:
    print("LEVEL SLICE  one free model clears a governed level end-to-end (sandbox only)\n")
    files = ["Draft One.tmp", "report.tmp", "NOTES final.tmp"]
    print("  level: normalize %d messy files  %s" % (len(files), files))
    out = _with_sandbox(files)
    print("\n  moves (each new name improvised at the blank, then governed + sealed):")
    for m in out["moves"]:
        tail = "-> %s" % m.get("proposed", "?")
        print("    %-18s %-9s %s  (model_calls=%s)" % (m["src"], m["decision"], tail, m.get("model_calls", "-")))
    print("\n  on disk now:", out["on_disk"])
    print("  WON (filesystem says every file is .bak):", out["won"])
    print("  action receipts sealed:", out["sealed"], " ledger sealed:", out["ledger_sealed"])
    print("  packed context (shorthand):", out["pack"])
    print("  move record etched as %d stones; reversible replay:" % len(out["stones"]), out["reversible"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
