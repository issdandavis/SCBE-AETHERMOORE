"""TicTac Spin Grid — Complex Spin Encoded as Simple 2D Patterns
================================================================

Encodes 6D tongue state as six 3x3 grids (tic-tac-toe boards).
Each cell is a trit: +1, 0, -1 (X, empty, O).

Stack 6 boards = 6 layers of 9 cells = 54 trits total.
That's 3^54 possible states = 2.6 × 10^25 unique patterns.
More than enough to encode any governance state.

The pattern on the board — not just the cell values — carries
information. Same values in different positions = different meaning.
Rotations, reflections, and symmetries of the board reveal
structural properties of the input.

Grid layout per tongue:
  [0][1][2]     Each cell maps to a text feature:
  [3][4][5]     0=length, 1=density, 2=diversity
  [6][7][8]     3=numeric, 4=CENTROID, 5=uppercase
                6=punctuation, 7=urls, 8=entropy

Cell 4 (center) = distance from centroid in that tongue dimension.
Corner cells = primary features. Edge cells = secondary features.
Center = the anchor. Like tic-tac-toe: center is strategically dominant.

Cross-board patterns:
  - Same cell position across all 6 boards = a "column" through the stack
  - If all 6 boards agree on a cell → strong signal
  - If boards disagree → the disagreement pattern IS the semantic spin
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI ** k for k in range(6))
WORD_RE = re.compile(r"[A-Za-z0-9_']+")


# =========================================================================== #
#  Single board
# =========================================================================== #

@dataclass(frozen=True)
class SpinBoard:
    """One 3x3 tic-tac-toe board filled with trits."""
    tongue: str
    cells: Tuple[int, ...]  # 9 values, each in {-1, 0, +1}

    @property
    def pattern(self) -> str:
        """Visual pattern: X=+1, .=0, O=-1."""
        chars = {1: "X", 0: ".", -1: "O"}
        return "".join(chars[c] for c in self.cells)

    @property
    def grid_str(self) -> str:
        """3x3 visual grid."""
        chars = {1: "X", 0: ".", -1: "O"}
        rows = []
        for r in range(3):
            rows.append(" ".join(chars[self.cells[r * 3 + c]] for c in range(3)))
        return "\n".join(rows)

    @property
    def magnitude(self) -> int:
        """Count of non-zero cells."""
        return sum(abs(c) for c in self.cells)

    @property
    def balance(self) -> int:
        """Sum of all cells. Positive = X-dominant, negative = O-dominant."""
        return sum(self.cells)

    @property
    def center(self) -> int:
        """Center cell value (strategically dominant)."""
        return self.cells[4]

    @property
    def corners(self) -> Tuple[int, int, int, int]:
        """Corner cells (primary features)."""
        return (self.cells[0], self.cells[2], self.cells[6], self.cells[8])

    @property
    def edges(self) -> Tuple[int, int, int, int]:
        """Edge cells (secondary features)."""
        return (self.cells[1], self.cells[3], self.cells[5], self.cells[7])

    def has_line(self, value: int) -> bool:
        """Check if there's a winning line of the given value."""
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
            (0, 4, 8), (2, 4, 6),              # diagonals
        ]
        return any(
            all(self.cells[i] == value for i in line)
            for line in lines
        )

    def rotation_invariant_hash(self) -> str:
        """Hash that's the same for all 4 rotations of the board."""
        rotations = [self.cells]
        # 90° rotation: (r,c) → (c, 2-r)
        def rotate(cells):
            return tuple(cells[6 - 3 * (i % 3) + i // 3] for i in range(9))
        current = self.cells
        for _ in range(3):
            current = rotate(current)
            rotations.append(current)
        # Use lexicographically smallest rotation as canonical form
        canonical = min(rotations)
        return hashlib.blake2s(str(canonical).encode(), digest_size=4).hexdigest()


# =========================================================================== #
#  Six-board stack
# =========================================================================== #

@dataclass(frozen=True)
class SpinStack:
    """6 boards stacked = full 6D spin state encoded as patterns."""
    boards: Tuple[SpinBoard, ...]  # 6 boards, one per tongue

    @property
    def total_trits(self) -> int:
        return 54

    @property
    def pattern_code(self) -> str:
        """54-character pattern code (concatenated board patterns)."""
        return "|".join(b.pattern for b in self.boards)

    @property
    def total_magnitude(self) -> int:
        return sum(b.magnitude for b in self.boards)

    @property
    def column(self, cell_idx: int) -> Tuple[int, ...]:
        """Get a vertical column through all 6 boards at one cell position."""
        return tuple(b.cells[cell_idx] for b in self.boards)

    def column_at(self, cell_idx: int) -> Tuple[int, ...]:
        """Get a vertical column through all 6 boards at one cell position."""
        return tuple(b.cells[cell_idx] for b in self.boards)

    def column_agreement(self, cell_idx: int) -> float:
        """How much do all 6 boards agree on this cell? 1.0 = unanimous."""
        col = self.column_at(cell_idx)
        if all(c == col[0] for c in col):
            return 1.0
        # Count most common value
        counts = {v: col.count(v) for v in set(col)}
        return max(counts.values()) / 6

    def cross_board_disagreement(self) -> float:
        """Average disagreement across all 9 cell positions. 0=total agreement, 1=total chaos."""
        return 1.0 - sum(self.column_agreement(i) for i in range(9)) / 9

    def winning_lines(self) -> Dict[str, List[int]]:
        """Which boards have winning lines (3-in-a-row of +1 or -1)?"""
        result = {}
        for board in self.boards:
            lines = []
            if board.has_line(1):
                lines.append(1)
            if board.has_line(-1):
                lines.append(-1)
            if lines:
                result[board.tongue] = lines
        return result

    def stack_hash(self) -> str:
        """Rotation-invariant hash of the full stack."""
        hashes = [b.rotation_invariant_hash() for b in self.boards]
        combined = ":".join(hashes)
        return hashlib.blake2s(combined.encode(), digest_size=8).hexdigest()


# =========================================================================== #
#  Encoder: text → spin stack
# =========================================================================== #

def _quantize(value: float, centroid: float, threshold: float = 0.05) -> int:
    """Quantize a single value to trit relative to centroid."""
    diff = value - centroid
    if diff > threshold:
        return 1
    elif diff < -threshold:
        return -1
    return 0


def text_to_features(text: str) -> Dict[str, float]:
    """Extract 9 features from text (one per grid cell)."""
    words = WORD_RE.findall(text)
    wc = len(words)
    chars = max(len(text), 1)
    unique = len(set(w.lower() for w in words))

    return {
        "length": min(1.0, chars / 2000.0),                              # cell 0
        "density": min(1.0, wc / 400.0),                                 # cell 1
        "diversity": unique / max(wc, 1),                                 # cell 2
        "numeric": min(1.0, sum(c.isdigit() for c in text) / chars * 8), # cell 3
        "centroid": 0.5,  # placeholder — filled per tongue               # cell 4
        "uppercase": min(1.0, sum(c.isupper() for c in text) / chars * 4),# cell 5
        "punctuation": min(1.0, sum(c in ".,;:!?-_/()" for c in text) / chars * 6),  # cell 6
        "urls": min(1.0, len(re.findall(r"https?://", text)) * 0.3),     # cell 7
        "entropy": _text_entropy(text),                                    # cell 8
    }


def _text_entropy(text: str) -> float:
    """Shannon entropy of character distribution, normalized to [0,1]."""
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for c in text.lower():
        freq[c] = freq.get(c, 0) + 1
    n = len(text)
    entropy = -sum((count / n) * math.log(count / n + 1e-15) for count in freq.values())
    return min(1.0, entropy / 4.7)  # max English char entropy ~4.7


def encode_spin_stack(
    text: str,
    centroid_features: Optional[Dict[str, float]] = None,
    threshold: float = 0.05,
) -> SpinStack:
    """Encode text into a 6-board spin stack.

    Each tongue gets a board where the features are weighted by that
    tongue's phi-weight. The same text feature hits differently on
    different boards because each tongue amplifies different aspects.
    """
    features = text_to_features(text)
    feature_keys = ["length", "density", "diversity", "numeric", "centroid",
                    "uppercase", "punctuation", "urls", "entropy"]
    feature_values = [features[k] for k in feature_keys]

    if centroid_features is None:
        centroid_values = [0.5, 0.2, 0.5, 0.05, 0.5, 0.1, 0.15, 0.05, 0.5]
    else:
        centroid_values = [centroid_features.get(k, 0.5) for k in feature_keys]

    boards = []
    for tongue_idx, tongue in enumerate(TONGUES):
        weight = TONGUE_WEIGHTS[tongue_idx]
        cells = []
        for cell_idx in range(9):
            if cell_idx == 4:
                # Center cell: weighted distance from centroid across ALL features
                weighted_dist = sum(
                    abs(feature_values[j] - centroid_values[j]) * (1.0 if j != 4 else 0.0)
                    for j in range(9)
                ) / 8.0
                # Scale by tongue weight — higher tongues are more sensitive
                scaled = weighted_dist * weight
                cells.append(_quantize(scaled, 0.3 * weight, threshold=threshold * weight))
            else:
                # Regular cell: feature weighted by tongue
                weighted_val = feature_values[cell_idx] * (1.0 + 0.1 * weight)
                weighted_centroid = centroid_values[cell_idx] * (1.0 + 0.1 * weight)
                cells.append(_quantize(weighted_val, weighted_centroid, threshold=threshold * weight))

        boards.append(SpinBoard(tongue=tongue, cells=tuple(cells)))

    return SpinStack(boards=tuple(boards))


# =========================================================================== #
#  Comparison: detect tampering via board pattern changes
# =========================================================================== #

def board_distance(a: SpinBoard, b: SpinBoard) -> int:
    """Hamming distance between two boards (count differing cells)."""
    return sum(1 for x, y in zip(a.cells, b.cells) if x != y)


def stack_distance(a: SpinStack, b: SpinStack) -> Dict[str, Any]:
    """Compare two stacks. Returns per-tongue and aggregate distances."""
    per_tongue = {}
    total_diff = 0
    for ba, bb in zip(a.boards, b.boards):
        d = board_distance(ba, bb)
        per_tongue[ba.tongue] = d
        total_diff += d

    return {
        "total_diff": total_diff,
        "max_possible": 54,
        "diff_ratio": round(total_diff / 54, 4),
        "per_tongue": per_tongue,
        "pattern_match": a.pattern_code == b.pattern_code,
        "hash_match": a.stack_hash() == b.stack_hash(),
    }
