"""Group alignment + strand extruder — Stage 3.5 of Prism->Rainbow->Beam.

Each Sacred Tongue has its own trit table (one "lane"). This module
reads all 6 lanes at once and produces:

    1. channel_profile(table)   -- per-channel activity for ONE tongue
    2. alignment_line(order)    -- 1D polyhedral line of deltas between
                                   adjacent tongues along a given order
    3. kink_points / flat_segments -- where groups break vs where they
                                      stay aligned
    4. extrude_strand(ops)      -- the playdough stringer: takes a list
                                   of FnIR ops and produces ONE rich
                                   token sequence where each position
                                   carries all 6 tongue contributions,
                                   a dominant tongue (organic winner),
                                   and a phi-weighted composite cost

The alignment line encodes WHERE tongues agree/disagree as a 1D walk
through the 6-channel lattice -- flat segments are group membership,
kinks are group boundaries. The strand turns that alignment data into
a single extrudable sequence you can reshape by reordering tongues.

The "dominant tongue" per op is NOT hard-coded; it emerges from
whichever lane shows the highest co-activation magnitude for that op,
weighted by phi. That's the "organic" behavior the pipeline is aiming
for: operations surface their natural home tongue without a rulebook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np

from ._trit_common import PHI_WEIGHTS, TONGUE_NAMES, TritTable
from . import trit_table_CA as _ca_module
from .trit_table_KO import TABLE as KO_TABLE
from .trit_table_AV import TABLE as AV_TABLE
from .trit_table_RU import TABLE as RU_TABLE
from .trit_table_UM import TABLE as UM_TABLE
from .trit_table_DR import TABLE as DR_TABLE

# Stage 4 recast order: most -> least ownership information.
PROMOTION_ORDER: Tuple[str, ...] = ("DR", "RU", "AV", "UM", "KO", "CA")

# Canonical tongue_id order (matches trit channel index 0..5).
CANONICAL_ORDER: Tuple[str, ...] = TONGUE_NAMES  # ("KO","AV","RU","CA","UM","DR")


def _ca_trit_matrix() -> np.ndarray:
    return np.asarray(_ca_module.TRIT_MATRIX)


def _trit_matrix_for(tongue: str) -> np.ndarray:
    if tongue == "CA":
        return _ca_trit_matrix()
    return {
        "KO": KO_TABLE,
        "AV": AV_TABLE,
        "RU": RU_TABLE,
        "UM": UM_TABLE,
        "DR": DR_TABLE,
    }[tongue].trit_matrix


# --- 1. Per-tongue channel profile ---------------------------------------
def channel_profile(tongue: str) -> np.ndarray:
    """Return a 6-vector: |activity| per channel for this tongue's 64 ops.

    Sum of absolute trit values per channel -- how loud is each channel
    across the whole op vocabulary. Negative blocks count as activity.
    """
    m = _trit_matrix_for(tongue).astype(np.int32)
    return np.sum(np.abs(m), axis=0)  # shape (6,)


def all_profiles(order: Sequence[str] = CANONICAL_ORDER) -> np.ndarray:
    """Stack channel profiles for `order` tongues -> shape (len(order), 6)."""
    return np.stack([channel_profile(t) for t in order])


# --- 2. Alignment line ---------------------------------------------------
def alignment_line(order: Sequence[str] = PROMOTION_ORDER) -> np.ndarray:
    """1D polyhedral line: deltas between adjacent tongues along `order`.

    Shape (len(order)-1, 6). Row i is profile[i+1] - profile[i].
    A row of all zeros = perfect alignment (flat segment, same group).
    Any nonzero entry = a "kink" where the two tongues diverge on
    that channel. Read the sequence of kink magnitudes and you get
    the 1D walk that encodes group-alignment structure.
    """
    profiles = all_profiles(order)
    return np.diff(profiles, axis=0)


def kink_magnitudes(line: np.ndarray) -> np.ndarray:
    """L1 norm per step -- how sharp each bend is. Shape (steps,)."""
    return np.sum(np.abs(line), axis=1)


def flat_segments(line: np.ndarray, order: Sequence[str] = PROMOTION_ORDER) -> List[Tuple[str, str, int]]:
    """Adjacent pairs with zero delta on at least one channel.

    Returns (a, b, shared_channels) triples. "Shared" = channel where
    both tongues emit the same absolute activity -- the alignment
    survives the boundary for that channel.
    """
    out: List[Tuple[str, str, int]] = []
    for i, row in enumerate(line):
        shared = int(np.sum(row == 0))
        if shared > 0:
            out.append((order[i], order[i + 1], shared))
    return out


def kink_points(
    line: np.ndarray,
    order: Sequence[str] = PROMOTION_ORDER,
    min_magnitude: int = 1,
) -> List[Tuple[str, str, int]]:
    """Adjacent pairs where the alignment bends.

    Returns (a, b, magnitude) where magnitude is the L1 delta.
    Larger magnitude = stronger group boundary.
    """
    mags = kink_magnitudes(line)
    return [(order[i], order[i + 1], int(mags[i])) for i in range(len(mags)) if mags[i] >= min_magnitude]


# --- 3. Interoperability matrix -----------------------------------------
def interop_matrix() -> np.ndarray:
    """6x6 symmetric matrix of channel-profile correlations.

    entry[i,j] = cosine similarity of tongue_i profile vs tongue_j
    profile. High = tongues that speak through the same channels
    (should co-fire cleanly). Low = tongues that need arbitration.
    """
    profiles = all_profiles(CANONICAL_ORDER).astype(np.float64)
    norms = np.linalg.norm(profiles, axis=1, keepdims=True)
    unit = profiles / np.where(norms == 0, 1, norms)
    return unit @ unit.T


# --- 4. The strand extruder ---------------------------------------------
@dataclass
class StrandBead:
    """One position in the rich token strand.

    Each bead is the simultaneous view of ONE op across all 6 tongues:
    the 6 co-activation magnitudes, the dominant tongue (organic
    winner), and the phi-weighted composite cost.
    """

    op_index: int  # position in input op sequence
    op_name: str  # the op (assumed shared vocab surface form)
    coactivation: np.ndarray  # shape (6,), float
    dominant: str  # winning tongue name
    phi_cost: float  # phi-weighted composite
    tongue_order: Tuple[str, ...] = CANONICAL_ORDER

    def to_tuple(self) -> Tuple:
        return (
            self.op_index,
            self.op_name,
            tuple(float(x) for x in self.coactivation),
            self.dominant,
            self.phi_cost,
        )


@dataclass
class Strand:
    """The extruded rich token sequence. Read it like DNA."""

    beads: List[StrandBead] = field(default_factory=list)
    tongue_order: Tuple[str, ...] = CANONICAL_ORDER

    def dominant_sequence(self) -> List[str]:
        return [b.dominant for b in self.beads]

    def phi_total(self) -> float:
        return float(sum(b.phi_cost for b in self.beads))

    def reshape(self, new_order: Sequence[str]) -> "Strand":
        """Re-project the strand through a different tongue ordering.

        The same invariant core -- each op's co-activation pattern --
        is preserved, but the channel order changes so the dominant
        tongue may shift. This is the "playdough through the stringer"
        operation: same dough, different extrusion die.
        """
        perm = [CANONICAL_ORDER.index(t) for t in new_order]
        new_beads: List[StrandBead] = []
        for b in self.beads:
            new_co = b.coactivation[perm]
            idx = int(np.argmax(new_co))
            phi = float(new_co[idx] * PHI_WEIGHTS[idx])
            new_beads.append(
                StrandBead(
                    op_index=b.op_index,
                    op_name=b.op_name,
                    coactivation=new_co,
                    dominant=new_order[idx],
                    phi_cost=phi,
                    tongue_order=tuple(new_order),
                )
            )
        return Strand(beads=new_beads, tongue_order=tuple(new_order))

    def as_rich_tokens(self) -> List[str]:
        """Human-readable token stream. One string per bead."""
        return [f"{b.op_name}@{b.dominant}[{b.phi_cost:.3f}]" for b in self.beads]


def _lookup_trit_row(tongue: str, op: str) -> np.ndarray | None:
    """Try to fetch the 6-channel trit row for (tongue, op).

    Returns None if the op doesn't exist in that tongue's vocabulary --
    different tongues expose different op names, so cross-tongue lookup
    is naturally sparse. That sparsity IS the organic-dominance signal:
    an op that only CA knows about will always win on CA.
    """
    if tongue == "CA":
        ids = _ca_module.OP_ID
        if op not in ids:
            return None
        return _ca_trit_matrix()[ids[op]].astype(np.int32)
    table: TritTable = {
        "KO": KO_TABLE,
        "AV": AV_TABLE,
        "RU": RU_TABLE,
        "UM": UM_TABLE,
        "DR": DR_TABLE,
    }[tongue]
    if op not in table.op_id:
        return None
    return table.trit_matrix[table.op_id[op]].astype(np.int32)


def extrude_strand(ops: Sequence[str]) -> Strand:
    """The stringer: take an op sequence, produce one rich token strand.

    For each op, look it up in every tongue's vocabulary. The ones that
    know the op contribute their trit row's L1 magnitude. The ones that
    don't contribute zero. The dominant tongue is whichever has the
    strongest phi-weighted activation -- organic emergence, no rules.

    Ops that no tongue recognizes are still emitted as silent beads
    (coactivation all zero) so positional alignment is preserved.
    """
    beads: List[StrandBead] = []
    for idx, op in enumerate(ops):
        coact = np.zeros(6, dtype=np.float64)
        for ch, t in enumerate(CANONICAL_ORDER):
            row = _lookup_trit_row(t, op)
            if row is not None:
                # Use the tongue's own channel (its home +1) + total
                # abs activity as the contribution magnitude.
                coact[ch] = float(np.sum(np.abs(row)))
        phi_scaled = coact * np.asarray(PHI_WEIGHTS, dtype=np.float64)
        if float(np.sum(phi_scaled)) == 0.0:
            dominant = "CA"  # silent -> fall back to raw-compute tongue
            phi_cost = 0.0
        else:
            dom_idx = int(np.argmax(phi_scaled))
            dominant = CANONICAL_ORDER[dom_idx]
            phi_cost = float(phi_scaled[dom_idx])
        beads.append(
            StrandBead(
                op_index=idx,
                op_name=op,
                coactivation=coact,
                dominant=dominant,
                phi_cost=phi_cost,
            )
        )
    return Strand(beads=beads)


if __name__ == "__main__":
    print("=== channel profiles (canonical order KO AV RU CA UM DR) ===")
    prof = all_profiles(CANONICAL_ORDER)
    for t, row in zip(CANONICAL_ORDER, prof):
        print(f"  {t}: {row}")

    print("\n=== alignment line (promotion order DR->RU->AV->UM->KO->CA) ===")
    line = alignment_line(PROMOTION_ORDER)
    mags = kink_magnitudes(line)
    for i, (a, b, m) in enumerate(zip(PROMOTION_ORDER, PROMOTION_ORDER[1:], mags)):
        print(f"  {a}->{b}: delta={line[i]}  mag={int(m)}")

    print("\n=== interop matrix (cosine, canonical order) ===")
    M = interop_matrix()
    for t, row in zip(CANONICAL_ORDER, M):
        print(f"  {t}: " + " ".join(f"{v:+.2f}" for v in row))

    print("\n=== strand demo ===")
    demo_ops = ["add", "if_", "own", "promise", "matrix", "bind_d", "unknown_op"]
    strand = extrude_strand(demo_ops)
    for tok in strand.as_rich_tokens():
        print(f"  {tok}")
    print(f"  phi_total = {strand.phi_total():.3f}")
    print(f"  dominants = {strand.dominant_sequence()}")

    print("\n=== reshaped through promotion order ===")
    reshaped = strand.reshape(PROMOTION_ORDER)
    print(f"  dominants = {reshaped.dominant_sequence()}")
    print(f"  phi_total = {reshaped.phi_total():.3f}")
