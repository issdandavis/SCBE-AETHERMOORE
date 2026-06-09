"""Meet-in-the-middle codegen protocol over the bijective Sacred Tongues.

Idea
----
A coding task is split between two agents:

    [input contract] --→ FORWARD agent --→ [seam] ←-- REVERSE agent ←-- [output contract]

The two agents work in parallel. The seam is a precise contract — a typed
state at one chosen line in the file. The bijective Sacred Tongues
tokenizer gives both agents a shared deterministic coordinate system: the
token stream of the seam contract is a single canonical byte sequence with
a single canonical hash. Convergence is defined as byte-exact agreement at
the seam.

This module is a thin protocol harness. It does not call language models;
it accepts two `CodeHalf` proposals (e.g. produced by two agents) and
verifies that they meet at the seam, then assembles the merged file and
runs it.

Why this is real and not magic
------------------------------
1. The "geometry" is just a contract. Code is one-dimensional text. The
   reason two halves converge is not because of natural geometry — it's
   because the seam contract was specified up-front and both halves were
   tasked with hitting it. The tokenizer is what makes byte-equality
   testable; it does not produce the convergence on its own.

2. Bijection gives a deterministic equality test, nothing else. Two
   identical strings encode to identical token streams; there is no
   semantic understanding.

3. The win is *parallelism* + *bug isolation*: when the seams disagree,
   you know which half drifted. That is independently useful and does
   not require AI mysticism to defend.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER as _TOK

# ---------------------------------------------------------------------------
#  Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeamContract:
    """Precise contract at the seam where the two halves meet.

    Attributes:
        names: Names that must be in scope at the seam, in declaration order.
        types: Optional type strings, parallel to `names`, for documentation
               and for the seam canonical hash. Use empty string when unknown.
        notes: Free-text guidance for the agents. NOT included in the seam
               canonical hash so notes can change without breaking convergence.
    """

    names: tuple[str, ...]
    types: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if self.types and len(self.types) != len(self.names):
            raise ValueError("types must be parallel to names or empty")
        if any(not n.isidentifier() for n in self.names):
            raise ValueError("seam names must be valid Python identifiers")

    def canonical_bytes(self) -> bytes:
        """Bytes that two agents must agree on for the seam to converge."""
        canonical = {"names": list(self.names), "types": list(self.types)}
        return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def seam_tongue_hash(self, tongue: str = "ko") -> str:
        """SHA-256 over the bijective tongue stream of the canonical bytes."""
        tokens = _TOK.encode_bytes(tongue, self.canonical_bytes())
        token_str = " ".join(tokens).encode("utf-8")
        return hashlib.sha256(token_str).hexdigest()


@dataclass
class CodeHalf:
    """One half of the meet-in-the-middle pair.

    `code` is the literal Python source for this half.
    `direction` is "forward" (input → seam) or "reverse" (seam → output).
    """

    direction: str
    code: str
    declared_seam: SeamContract

    def __post_init__(self) -> None:
        if self.direction not in ("forward", "reverse"):
            raise ValueError(f"direction must be 'forward' or 'reverse', got {self.direction!r}")
        if not self.code.endswith("\n"):
            self.code = self.code + "\n"


@dataclass
class MergeReport:
    converged: bool
    forward_seam_hash: str
    reverse_seam_hash: str
    diagnostics: List[str] = field(default_factory=list)
    merged_source: Optional[str] = None
    execution_stdout: Optional[str] = None
    execution_stderr: Optional[str] = None
    execution_returncode: Optional[int] = None


# ---------------------------------------------------------------------------
#  Protocol
# ---------------------------------------------------------------------------

SEAM_MARKER = "# === SCBE_MEET_SEAM ==="


def _has_seam_marker(code: str) -> bool:
    return SEAM_MARKER in code


def _names_in_scope_at_seam(code: str) -> List[str]:
    """Best-effort: pick up names that look bound up to the seam.

    We do not run the user's code. We only scan for top-level assignment and
    function-definition names that appear *before* the seam marker. Two halves
    that disagree on which names exist by the seam will be flagged.
    """
    names: List[str] = []
    for line in code.split("\n"):
        if SEAM_MARKER in line:
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("def ") and "(" in stripped:
            n = stripped[4:].split("(", 1)[0].strip()
            if n.isidentifier():
                names.append(n)
            continue
        if "=" in stripped and not stripped.startswith(("if ", "for ", "while ", "with ", "return ")):
            head = stripped.split("=", 1)[0].strip()
            if head.isidentifier():
                names.append(head)
    return names


def merge_halves(
    forward: CodeHalf,
    reverse: CodeHalf,
    *,
    execute: bool = False,
    timeout: float = 10.0,
) -> MergeReport:
    """Verify that two halves agree on the seam, then assemble + optionally run.

    The two halves must:
      1. Each carry a SEAM_MARKER somewhere in the source.
      2. Both carry the same `declared_seam` (byte-equal canonical form).
      3. The forward half must have all seam `names` in scope by the marker.
    """
    diagnostics: List[str] = []

    if forward.direction != "forward":
        diagnostics.append(f"forward.direction = {forward.direction!r}")
    if reverse.direction != "reverse":
        diagnostics.append(f"reverse.direction = {reverse.direction!r}")

    if not _has_seam_marker(forward.code):
        diagnostics.append("forward half missing SEAM_MARKER")
    if not _has_seam_marker(reverse.code):
        diagnostics.append("reverse half missing SEAM_MARKER")

    fwd_hash = forward.declared_seam.seam_tongue_hash()
    rev_hash = reverse.declared_seam.seam_tongue_hash()
    if fwd_hash != rev_hash:
        diagnostics.append(f"seam contracts differ: fwd={fwd_hash[:12]} rev={rev_hash[:12]}")

    if _has_seam_marker(forward.code):
        scope = set(_names_in_scope_at_seam(forward.code))
        missing = [n for n in forward.declared_seam.names if n not in scope]
        if missing:
            diagnostics.append(f"forward half does not bind seam names: {missing}")

    if diagnostics:
        return MergeReport(
            converged=False,
            forward_seam_hash=fwd_hash,
            reverse_seam_hash=rev_hash,
            diagnostics=diagnostics,
        )

    # Assemble: forward up to and including the seam marker, then the part of
    # the reverse half that appears after its seam marker.
    fwd_lines = forward.code.split("\n")
    rev_lines = reverse.code.split("\n")
    fwd_idx = next(i for i, l in enumerate(fwd_lines) if SEAM_MARKER in l)
    rev_idx = next(i for i, l in enumerate(rev_lines) if SEAM_MARKER in l)

    merged = "\n".join(fwd_lines[: fwd_idx + 1]) + "\n" + "\n".join(rev_lines[rev_idx + 1 :])
    if not merged.endswith("\n"):
        merged += "\n"

    report = MergeReport(
        converged=True,
        forward_seam_hash=fwd_hash,
        reverse_seam_hash=rev_hash,
        merged_source=merged,
    )

    if execute:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "merged.py"
            path.write_text(merged, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            report.execution_stdout = proc.stdout
            report.execution_stderr = proc.stderr
            report.execution_returncode = proc.returncode

    return report


__all__ = [
    "SeamContract",
    "CodeHalf",
    "MergeReport",
    "SEAM_MARKER",
    "merge_halves",
]
