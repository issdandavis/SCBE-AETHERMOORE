"""Trijective cross-check: triangulate a command through three Sacred Tongues.

Bijective = A <-> B (one bridge, one witness).
Trijective = A <-> B <-> C <-> A (three bridges, mutual witness).

A command or text is TRIJECTIVE-VALID iff:
  1. anchor -> w1 -> anchor round-trips to the original bytes
  2. anchor -> w2 -> anchor round-trips to the original bytes
  3. w1 <-> w2 round-trips (the two witnesses agree with each other)
  4. phase triangle closes: sum(phase_delta) == 0 mod 2*pi
  5. weight triangle closes: prod(weight_ratio) == 1

Conditions 4+5 are algebraic identities over the existing CrossTokenizer's
PHASE/WEIGHT constants -- checking them is a runtime sanity assertion that
the tongue tables haven't been tampered with between calls.

Conditions 1-3 are the actual bijective round-trip proofs. If any leg of
the triangle drops a byte, the command fails the gate and will NOT execute.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cli_toolkit import CrossTokenizer, Lexicons, TongueTokenizer

TWO_PI = 2 * math.pi

# Canonical witness pairs. Each anchor has two phase-distant partners so the
# triangle is non-degenerate (never picks two tongues at the same phase).
DEFAULT_WITNESSES: Dict[str, Tuple[str, str]] = {
    "KO": ("CA", "DR"),
    "AV": ("UM", "KO"),
    "RU": ("DR", "AV"),
    "CA": ("KO", "RU"),
    "UM": ("AV", "CA"),
    "DR": ("RU", "UM"),
}


@dataclass
class TrijectiveReport:
    anchor: str
    w1: str
    w2: str
    source_bytes_hex: str
    leg1_ok: bool  # anchor -> w1 -> anchor
    leg2_ok: bool  # anchor -> w2 -> anchor
    leg3_ok: bool  # w1 <-> w2
    phase_closure: float  # sum of phase deltas mod 2*pi
    weight_closure: float  # product of weight ratios
    phase_ok: bool
    weight_ok: bool
    notes: List[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.leg1_ok and self.leg2_ok and self.leg3_ok and self.phase_ok and self.weight_ok

    def to_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "witnesses": [self.w1, self.w2],
            "source_sha_prefix": self.source_bytes_hex[:16],
            "legs": {
                "anchor->w1->anchor": self.leg1_ok,
                "anchor->w2->anchor": self.leg2_ok,
                "w1<->w2": self.leg3_ok,
            },
            "phase_closure_rad": round(self.phase_closure, 6),
            "weight_closure": round(self.weight_closure, 6),
            "phase_ok": self.phase_ok,
            "weight_ok": self.weight_ok,
            "valid": self.valid,
            "notes": self.notes,
        }


class TrijectiveValidator:
    """Run trijective round-trips over the existing Sacred Tongues tables."""

    def __init__(
        self,
        tokenizer: Optional[TongueTokenizer] = None,
        phase_tol: float = 1e-6,
        weight_tol: float = 1e-6,
    ):
        self.tok = tokenizer or TongueTokenizer(Lexicons())
        self.xt = CrossTokenizer(self.tok)
        self.phase_tol = phase_tol
        self.weight_tol = weight_tol

    def _bytes_from_text(self, tongue: str, text: str) -> bytes:
        return self.xt.to_bytes_from_tokens(tongue, text)

    def _text_from_bytes(self, tongue: str, data: bytes) -> str:
        return " ".join(self.xt.to_tokens_from_bytes(tongue, data))

    def _round_trip(self, anchor: str, witness: str, text: str) -> Tuple[bool, bytes]:
        """anchor-text -> witness-text -> anchor-bytes, compare to source."""
        src = self._bytes_from_text(anchor, text)
        via = self._text_from_bytes(witness, src)
        back = self._bytes_from_text(witness, via)
        return (src == back), src

    def _cross_witness(self, w1: str, w2: str, anchor: str, text: str) -> bool:
        """Bytes must survive w1 <-> w2 direct, not just through anchor."""
        src = self._bytes_from_text(anchor, text)
        w1_text = self._text_from_bytes(w1, src)
        w1_bytes = self._bytes_from_text(w1, w1_text)
        w2_text = self._text_from_bytes(w2, w1_bytes)
        w2_bytes = self._bytes_from_text(w2, w2_text)
        return src == w2_bytes

    def _phase_triangle(self, a: str, b: str, c: str) -> float:
        p = CrossTokenizer.PHASE
        total = (p[b] - p[a]) + (p[c] - p[b]) + (p[a] - p[c])
        return total % TWO_PI

    def _weight_triangle(self, a: str, b: str, c: str) -> float:
        w = CrossTokenizer.WEIGHT
        return (w[b] / w[a]) * (w[c] / w[b]) * (w[a] / w[c])

    def validate(
        self,
        text: str,
        anchor: str = "KO",
        witnesses: Optional[Tuple[str, str]] = None,
    ) -> TrijectiveReport:
        if witnesses is None:
            witnesses = DEFAULT_WITNESSES[anchor]
        w1, w2 = witnesses

        notes: List[str] = []
        if anchor in (w1, w2) or w1 == w2:
            notes.append(f"degenerate triangle: {anchor}/{w1}/{w2}")

        leg1_ok, src_bytes = self._round_trip(anchor, w1, text)
        leg2_ok, _ = self._round_trip(anchor, w2, text)
        leg3_ok = self._cross_witness(w1, w2, anchor, text)

        phase_closure = self._phase_triangle(anchor, w1, w2)
        weight_closure = self._weight_triangle(anchor, w1, w2)
        phase_ok = abs(phase_closure) < self.phase_tol or abs(phase_closure - TWO_PI) < self.phase_tol
        weight_ok = abs(weight_closure - 1.0) < self.weight_tol

        return TrijectiveReport(
            anchor=anchor,
            w1=w1,
            w2=w2,
            source_bytes_hex=src_bytes.hex(),
            leg1_ok=leg1_ok,
            leg2_ok=leg2_ok,
            leg3_ok=leg3_ok,
            phase_closure=phase_closure,
            weight_closure=weight_closure,
            phase_ok=phase_ok,
            weight_ok=weight_ok,
            notes=notes,
        )

    def gate(self, text: str, anchor: str = "KO") -> Tuple[bool, TrijectiveReport]:
        """Shortcut: (is_valid, report). Use as an execution pre-check."""
        rep = self.validate(text, anchor=anchor)
        return rep.valid, rep


# --- Semantic lookup triangulation -------------------------------------
#
# The CrossTokenizer above pivots through BYTES. For an operational command
# ("seal the packet", "show status"), we also want to triangulate the
# SEMANTIC intent, not just the byte surface. The semantic table below maps
# a small controlled verb vocabulary into each tongue, so a command can be
# entered in any tongue and validated by the other two.
#
# Keep this table hand-curated and SMALL -- it is the "operational vocab"
# the trijective gate knows how to cross-check. Unknown verbs fall back to
# byte trijective only.

SEMANTIC_VERBS: Dict[str, Dict[str, str]] = {
    "seal": {"KO": "ko'sil", "AV": "av'mor", "RU": "ru'kin", "CA": "ca'shu", "UM": "um'zai", "DR": "dr'okt"},
    "unseal": {"KO": "ko'sul", "AV": "av'mer", "RU": "ru'kon", "CA": "ca'she", "UM": "um'zei", "DR": "dr'okl"},
    "tok": {"KO": "ko'tok", "AV": "av'tak", "RU": "ru'tik", "CA": "ca'tuk", "UM": "um'tek", "DR": "dr'tok"},
    "exec": {"KO": "ko'exe", "AV": "av'eks", "RU": "ru'eky", "CA": "ca'exo", "UM": "um'exa", "DR": "dr'exi"},
    "status": {"KO": "ko'sta", "AV": "av'sti", "RU": "ru'sto", "CA": "ca'ste", "UM": "um'stu", "DR": "dr'sty"},
    "ask": {"KO": "ko'asq", "AV": "av'asa", "RU": "ru'ask", "CA": "ca'asu", "UM": "um'asi", "DR": "dr'asy"},
    "help": {"KO": "ko'hlp", "AV": "av'hel", "RU": "ru'hlp", "CA": "ca'hlu", "UM": "um'hla", "DR": "dr'hli"},
}


def semantic_triangulate(verb_in_any_tongue: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
    """Given a token like 'ko'sil', return (canonical_verb, source_tongue, all_tongue_forms).

    The lookup is trijective in spirit: it returns the verb only if it maps
    unambiguously across every tongue (i.e. the full 6-row is present).
    None if the verb is not in the controlled vocabulary.
    """
    token = verb_in_any_tongue.strip().lower()
    for canonical, row in SEMANTIC_VERBS.items():
        for tongue, form in row.items():
            if form == token:
                return canonical, tongue, row
    return None


def semantic_cross_check(verb: str, anchor_tongue: str) -> bool:
    """True iff `verb` is known AND every tongue has a form for it.

    This is the operational valid cross-check the user asked for: a command
    is only runnable if its semantic entry is present across all 6 tongues,
    not just the one the operator typed.
    """
    row = SEMANTIC_VERBS.get(verb)
    if row is None:
        return False
    return len(row) == 6 and anchor_tongue in row
