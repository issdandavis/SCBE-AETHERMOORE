"""
SCBE Atomic Tokenizer — GAP-1 close.

Assigns stable integer IDs to Sacred Tongue atoms and produces
BPE-compatible token sequences from any text input.

Atom IDs are stable across versions (frozen here as constants).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Stable atom vocabulary (frozen integer IDs)
# ---------------------------------------------------------------------------

ATOM_VOCAB: dict[str, int] = {
    # Domain atoms
    "BLOCK":     0,
    "TRANSFORM": 1,
    "FLOW":      2,
    "WATER":     3,
    # Discourse atoms
    "ANNOUNCE":  4,
    "EXPAND":    5,
    "REQUEST":   6,
    "PIVOT":     7,
    "CARRY":     8,
    "HOLD":      9,
}

ID_TO_ATOM: dict[int, str] = {v: k for k, v in ATOM_VOCAB.items()}

# ---------------------------------------------------------------------------
# Surface forms → atom ID (ordered longest-match first)
# ---------------------------------------------------------------------------

_SURFACE_MAP: list[tuple[str, int]] = [
    # BLOCK
    ("blocked", 0), ("barrier", 0), ("error", 0), ("exception", 0),
    ("deny", 0), ("denied", 0), ("failed", 0), ("block", 0),
    # TRANSFORM
    ("transform", 1), ("convert", 1), ("compile", 1), ("compute", 1),
    ("calculate", 1), ("subtract", 1), ("multiply", 1), ("divide", 1),
    ("refactor", 1), ("change", 1), ("add", 1),
    # FLOW
    ("pipeline", 2), ("control flow", 2), ("data flow", 2), ("stream", 2),
    ("event", 2), ("flow", 2), ("flows", 2),
    # WATER
    ("liquid", 3), ("steam", 3), ("river", 3), ("water", 3), ("rain", 3),
    # ANNOUNCE
    ("let me explain", 4), ("what you need to know", 4), ("to give you context", 4),
    ("the thing about", 4), ("three things", 4), ("two things", 4),
    ("one thing", 4), ("announce", 4),
    # EXPAND
    ("for example", 5), ("for instance", 5), ("to illustrate", 5),
    ("similarly", 5), ("consider this", 5), ("expand", 5),
    # REQUEST
    ("bear with me", 6), ("one more thing", 6), ("almost done", 6),
    ("request", 6),
    # PIVOT
    ("actually", 7), ("however", 7), ("on the other hand", 7),
    ("instead", 7), ("pivot", 7),
    # CARRY
    ("therefore", 8), ("because", 8), ("as i mentioned", 8),
    ("given that", 8), ("carry", 8),
    # HOLD
    ("right", 9), ("okay", 9), ("yes", 9), ("uh huh", 9), ("hold", 9),
]

# Sort by surface form length descending for greedy longest-match
_SURFACE_MAP.sort(key=lambda x: -len(x[0]))


@dataclass
class AtomToken:
    atom: str
    atom_id: int
    surface: str
    start: int
    end: int


def tokenize(text: str) -> List[AtomToken]:
    """Greedy longest-match tokenization → list of AtomTokens."""
    lower = text.lower()
    tokens: list[AtomToken] = []
    pos = 0
    n = len(lower)
    while pos < n:
        matched = False
        for surface, atom_id in _SURFACE_MAP:
            if lower[pos:pos + len(surface)] == surface:
                tokens.append(AtomToken(
                    atom=ID_TO_ATOM[atom_id],
                    atom_id=atom_id,
                    surface=surface,
                    start=pos,
                    end=pos + len(surface),
                ))
                pos += len(surface)
                matched = True
                break
        if not matched:
            pos += 1
    return tokens


def token_ids(text: str) -> List[int]:
    """Return sequence of stable atom integer IDs for any text."""
    return [t.atom_id for t in tokenize(text)]


def hex_fingerprint(text: str) -> str:
    """
    Produce a 12-char hex fingerprint from the token ID sequence.

    Aggregates atom frequency counts into a 6D DimVec (one bucket per axis
    pair), quantizes to 8 bits per dim, returns 48-bit hex.
    """
    ids = token_ids(text)
    if not ids:
        return "000000000000"

    # Map atom IDs to 6 axes: KO=0,1  AV=2,3  RU=4,5  CA=6,7  UM=8,9  DR=...
    # Simple bucketing: atom 0-1 → KO/AV, 2-3 → RU/CA, 4-5 → UM/DR, 6-9 → blend
    axis_weights = [
        [1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.3, 0.1, 0.2, 0.0],  # KO
        [0.1, 0.8, 0.9, 0.1, 0.3, 0.5, 0.2, 0.7, 0.1, 0.1],  # AV
        [0.9, 0.8, 0.5, 0.2, 0.9, 0.4, 0.5, 0.3, 0.4, 0.2],  # RU
        [0.9, 0.9, 0.2, 0.1, 0.2, 0.9, 0.1, 0.2, 0.8, 0.1],  # CA
        [0.8, 0.1, 0.4, 0.5, 0.4, 0.2, 0.9, 0.3, 0.1, 0.2],  # UM
        [0.0, 0.5, 0.8, 0.6, 0.9, 0.7, 0.1, 0.2, 0.1, 0.3],  # DR
    ]

    counts = [0] * 10
    for aid in ids:
        counts[aid] += 1
    total = sum(counts) or 1

    dims = []
    for axis_w in axis_weights:
        val = sum(counts[i] * axis_w[i] for i in range(10)) / total
        dims.append(min(1.0, val))

    hex_chars = ""
    for d in dims:
        quantized = int(d * 255)
        hex_chars += format(quantized, "02x")
    return hex_chars


def vocab_size() -> int:
    return len(ATOM_VOCAB)
