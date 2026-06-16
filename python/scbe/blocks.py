"""
SCBE Blocks — Scratch-style command blocks with a built-in destructive double-check.
======================================================================================

Elementary-school block coding (Scratch / Blockly / Code.org) makes programming
safe by *construction*: commands are drag-and-drop BLOCKS whose SHAPES only snap
together when valid, so "it's nearly impossible to break anything permanently."

This module brings that idea to AI operations on a real system:

  * every command is a Block with a SHAPE (stack_in -> stack_out) — like Incan
    masonry, blocks only interlock when their shapes match, so a program is a
    wall that "compiles no matter what" or refuses to assemble;
  * every block has a Sacred-Tongue CATEGORY (the Scratch "color"): KO control,
    AV i/o, RU scope, CA math, UM security, DR transform;
  * every block has a SAFETY class — SAFE / CAUTION / DESTRUCTIVE. Destructive
    blocks (delete, overwrite, format, drop, wipe...) are RED and GATED: a block
    program refuses to run them unless each is explicitly confirmed with a reason,
    and hard-drive-scope deletes are refused outright. That is the elementary-school
    "are you sure?" double-check, enforced in the system itself.

Blocks compile across languages (the cube faces) via polyglot.emit for the math
core; system blocks emit guarded calls. One block, every language — interlocking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


def _norm(target: str) -> str:
    return target.replace("\\", "/").lower().strip().rstrip("/")


# bulk/recursive destroyers that can take out a whole tree or volume
_BULK = {"delete_dir", "format_disk", "wipe"}
# broad scopes that must NEVER be destroyed, even with confirmation
_BROAD = {
    "",
    "*",
    ".",
    "~",
    "/",
    "c:/users",
    "c:/users/issda",
    "c:/windows",
    "c:/program files",
    "c:/program files (x86)",
    "/home",
    "/root",
    "/usr",
    "/etc",
    "/var",
    "/bin",
    "onedrive",
}


def _is_broad_scope(target: str) -> bool:
    n = _norm(target)
    if n in _BROAD:
        return True
    if re.match(r"^[a-z]:$", n):  # bare drive root  c:  d:
        return True
    if n.endswith("/*") or n.endswith("/."):
        return True
    return False


def _is_system_path(target: str) -> bool:
    n = _norm(target)
    segs = n.split("/")
    return (
        "windows" in segs
        or "system32" in segs
        or "program files" in n
        or n.startswith("/etc")
        or n.startswith("/usr")
        or n.startswith("/bin")
    )


try:
    from python.scbe.ca_opcode_table import ARITHMETIC, LOGIC, COMPARISON, AGGREGATION
except Exception:  # pragma: no cover - allow standalone import
    ARITHMETIC = LOGIC = COMPARISON = AGGREGATION = []


class Safety(Enum):
    SAFE = "safe"  # read-only / pure compute — run freely
    CAUTION = "caution"  # writes / mutations / network — run with notice
    DESTRUCTIVE = "destructive"  # delete / overwrite / format — GATED, double-check


# Sacred-Tongue category == the Scratch block "color".
TONGUE_GLYPH = {
    "KO": ("control", "▶", "yellow"),
    "AV": ("i/o", "◂▸", "blue"),
    "RU": ("scope", "▦", "purple"),
    "CA": ("math", "●", "green"),
    "UM": ("security", "⚠", "red"),
    "DR": ("transform", "◆", "orange"),
}
SAFETY_GLYPH = {Safety.SAFE: "·", Safety.CAUTION: "!", Safety.DESTRUCTIVE: "⛔"}


@dataclass(frozen=True)
class Block:
    """One command block. The shape (stack_in -> stack_out) is the interlock."""

    name: str
    tongue: str  # KO/AV/RU/CA/UM/DR — category/color
    stack_in: int  # operands consumed (the bottom notch)
    stack_out: int  # results produced (the top nub)
    safety: Safety
    desc: str = ""
    # words that, if they appear in a target/argument, escalate to hard-refuse
    hard_refuse_scopes: tuple = ()

    @property
    def glyph(self) -> str:
        cat = TONGUE_GLYPH.get(self.tongue, ("?", "?", "?"))
        return f"{cat[1]}{SAFETY_GLYPH[self.safety]}"


# --------------------------------------------------------------------------
# Block catalog: the CA math core (all SAFE) + real system operations.
# --------------------------------------------------------------------------
CATALOG: Dict[str, Block] = {}


def _add(block: Block) -> None:
    CATALOG[block.name] = block


# CA opcode blocks — pure compute, always SAFE. Category by op group.
for _group, _tongue in ((ARITHMETIC, "CA"), (LOGIC, "CA"), (COMPARISON, "KO"), (AGGREGATION, "DR")):
    for _entry in _group:
        _id, _name = _entry[0], _entry[1]
        # arithmetic/logic binary->1, comparison binary->1, aggregation list->1
        _add(Block(_name, _tongue, stack_in=2, stack_out=1, safety=Safety.SAFE, desc=f"CA op 0x{_id:02x}"))

# System / file / process blocks — where real danger lives.
_SYSTEM_BLOCKS = [
    # name, tongue, in, out, safety, desc, hard_refuse_scopes
    ("read_file", "AV", 1, 1, Safety.SAFE, "read a file's contents", ()),
    ("list_dir", "AV", 1, 1, Safety.SAFE, "list a directory", ()),
    ("stat", "AV", 1, 1, Safety.SAFE, "inspect file metadata", ()),
    ("search", "AV", 1, 1, Safety.SAFE, "search file contents", ()),
    ("print", "AV", 1, 0, Safety.SAFE, "emit output", ()),
    ("write_file", "DR", 2, 0, Safety.CAUTION, "write/create a file", ()),
    ("append_file", "DR", 2, 0, Safety.CAUTION, "append to a file", ()),
    ("make_dir", "RU", 1, 0, Safety.CAUTION, "create a directory", ()),
    ("move", "DR", 2, 0, Safety.CAUTION, "move/rename a path", ()),
    ("copy", "DR", 2, 1, Safety.CAUTION, "copy a path", ()),
    ("run_shell", "AV", 1, 1, Safety.CAUTION, "run a shell command", ()),
    ("network_send", "AV", 2, 1, Safety.CAUTION, "send data to a remote", ()),
    # ---- DESTRUCTIVE: gated, double-checked, drive-scope refused outright ----
    (
        "delete_file",
        "UM",
        1,
        0,
        Safety.DESTRUCTIVE,
        "delete a file",
        ("C:\\", "/", "system32", "windows", "users", "home"),
    ),
    (
        "delete_dir",
        "UM",
        1,
        0,
        Safety.DESTRUCTIVE,
        "remove a directory tree",
        ("C:\\", "/", "system32", "windows", "users", "home", "onedrive"),
    ),
    ("overwrite", "DR", 2, 0, Safety.DESTRUCTIVE, "overwrite existing file contents", ()),
    ("truncate", "DR", 1, 0, Safety.DESTRUCTIVE, "truncate a file to zero", ()),
    ("format_disk", "UM", 1, 0, Safety.DESTRUCTIVE, "format a volume", ("C:", "D:", "/", "*")),
    ("drop_table", "UM", 1, 0, Safety.DESTRUCTIVE, "drop a database table", ()),
    ("kill_process", "UM", 1, 0, Safety.DESTRUCTIVE, "terminate a process", ()),
    ("wipe", "UM", 1, 0, Safety.DESTRUCTIVE, "secure-wipe a path", ("C:\\", "/", "*")),
]
for _n, _t, _i, _o, _s, _d, _scopes in _SYSTEM_BLOCKS:
    _add(Block(_n, _t, _i, _o, _s, _d, _scopes))


class BlockError(Exception):
    """Invalid block wall (shapes don't interlock) or blocked destructive op."""


@dataclass
class Step:
    block: Block
    args: tuple = ()
    confirm: Optional[str] = None  # the explicit "are you sure?" reason (double-check)


@dataclass
class BlockProgram:
    """A wall of interlocking blocks. Validates shape AND safety before it runs."""

    steps: List[Step] = field(default_factory=list)

    def add(self, name: str, *args: object, confirm: Optional[str] = None) -> "BlockProgram":
        if name not in CATALOG:
            raise BlockError(f"unknown block {name!r}")
        self.steps.append(Step(CATALOG[name], tuple(args), confirm))
        return self

    # ---- shape: do the blocks interlock? (Scratch "snap" / Incan fit) --------
    def shape_ok(self, seed: int = 3) -> bool:
        depth = seed
        for st in self.steps:
            if depth < st.block.stack_in:
                return False
            depth = depth - st.block.stack_in + st.block.stack_out
        return True

    def shape_report(self, seed: int = 3) -> List[str]:
        out, depth = [], seed
        for st in self.steps:
            ok = depth >= st.block.stack_in
            nxt = depth - st.block.stack_in + st.block.stack_out if ok else depth
            out.append(
                f"   {st.block.glyph} {st.block.name:<14} "
                f"[{depth}->{nxt}] {'fits' if ok else 'GAP — does not interlock'}"
            )
            depth = nxt
        return out

    # ---- safety: the elementary-school destructive double-check --------------
    def destructive_steps(self) -> List[Step]:
        return [s for s in self.steps if s.block.safety is Safety.DESTRUCTIVE]

    def safety_audit(self) -> List[str]:
        """Return blocking reasons; empty list == cleared to run."""
        problems: List[str] = []
        for st in self.steps:
            b = st.block
            if b.safety is not Safety.DESTRUCTIVE:
                continue
            target = " ".join(str(a) for a in st.args)
            shown = target or "<no target>"
            # 1) hard refuse: drive/home/system scope — never, even with confirm.
            if (b.name in _BULK and _is_broad_scope(target)) or _is_system_path(target) or _is_broad_scope(target):
                problems.append(
                    f"REFUSED: {b.name}({shown}) hits a drive/home/system scope. "
                    f"Bulk/system destruction is never allowed — no confirmation can override it."
                )
                continue
            # 2) otherwise require an explicit confirmation reason (the double-check)
            if not st.confirm:
                problems.append(
                    f"BLOCKED: {b.name}({shown}) is DESTRUCTIVE. Re-add with "
                    f"confirm='<why this is safe and intended>' to pass the double-check."
                )
        return problems

    def run_plan(self) -> Dict[str, object]:
        """Validate the wall. Raises BlockError if it won't interlock or is gated."""
        if not self.shape_ok():
            raise BlockError("blocks do not interlock:\n" + "\n".join(self.shape_report()))
        problems = self.safety_audit()
        if problems:
            raise BlockError("destructive double-check failed:\n  " + "\n  ".join(problems))
        return {
            "steps": len(self.steps),
            "destructive": len(self.destructive_steps()),
            "cleared": True,
        }

    # ---- visual: the snapped block wall --------------------------------------
    def render(self) -> str:
        lines = ["┌─ block program ──────────────────────────"]
        for i, st in enumerate(self.steps):
            cat = TONGUE_GLYPH.get(st.block.tongue, ("?", "?", "?"))
            danger = (
                "  ⛔ DESTRUCTIVE"
                if st.block.safety is Safety.DESTRUCTIVE
                else ("  ! caution" if st.block.safety is Safety.CAUTION else "")
            )
            arg = ("(" + ", ".join(str(a) for a in st.args) + ")") if st.args else ""
            lines.append(f"│ {i:>2} {st.block.glyph} [{st.block.tongue}/{cat[0]:<8}] " f"{st.block.name}{arg}{danger}")
        lines.append("└──────────────────────────────────────────")
        return "\n".join(lines)


def catalog_summary() -> str:
    by_safety = {s: [] for s in Safety}
    for b in CATALOG.values():
        by_safety[b.safety].append(b.name)
    out = [f"SCBE Blocks — {len(CATALOG)} blocks across 6 tongues"]
    for s in Safety:
        out.append(
            f"  {SAFETY_GLYPH[s]} {s.value:<12} {len(by_safety[s])}: "
            + ", ".join(sorted(by_safety[s])[:12])
            + (" …" if len(by_safety[s]) > 12 else "")
        )
    return "\n".join(out)


def _demo() -> None:
    print(catalog_summary())
    print("\n--- a valid compute wall (interlocks, all SAFE) ---")
    p = BlockProgram().add("add").add("mul").add("read_file", "notes.md")
    print(p.render())
    print("\n".join(p.shape_report()))
    print("run:", p.run_plan())

    print("\n--- AI tries a destructive op WITHOUT the double-check ---")
    p2 = BlockProgram().add("delete_file", "scratch/tmp.log")
    print(p2.render())
    try:
        p2.run_plan()
    except BlockError as e:
        print("✋", e)

    print("\n--- same op WITH an explicit confirmation reason ---")
    p3 = BlockProgram().add("delete_file", "scratch/tmp.log", confirm="temp log in a scratch dir, recreated each run")
    print("run:", p3.run_plan())

    print("\n--- AI tries to delete the HARD DRIVE (refused outright) ---")
    p4 = BlockProgram().add("delete_dir", "C:\\Users\\issda", confirm="cleanup")  # confirm cannot override drive-scope
    try:
        p4.run_plan()
    except BlockError as e:
        print("✋", e)


if __name__ == "__main__":
    _demo()
