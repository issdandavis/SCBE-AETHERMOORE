"""Op-binary tables — Stage 2 of Prism->Rainbow->Beam.

One FnIR op (6-bit) -> six tongue-specific bitstrings. Each tongue gets
its own width and prefix structure because each language expresses the
op differently:

    KO  python      6-bit  (broad, dynamic)
    AV  typescript  7-bit  (+ type prefix)
    RU  rust        8-bit  (+ ownership prefix)
    CA  c           6-bit  (tight primitives)
    UM  julia       7-bit  (+ dispatch prefix)
    DR  haskell     8-bit  (+ purity/monad prefix)

ALL-SCALE INVERSE COMPLEXITY
============================
The base table is just the starting cost. A `UsageLedger` tracks
sustained semantic co-activation of (op, tongue) pairs across time.
The longer the system spends inside a coding block, the wider the
paths get worn through the lattice -- and the effective cost of a
familiar op->token transition drops by phi^path_width.

This is the gravity-battery / Sisyphus-trajectory memory applied to
token encoding: the first traversal pays full cost, repeated traversal
wears a groove, the groove makes the next traversal cheaper. Same
mechanism at every scale (one op or one million) because phi^w compounds
multiplicatively -- scale-invariant by construction.

Every N sustained interactions the table re-mods: ops with the widest
paths drift toward shorter prefixes (Huffman-style remap), so the
binary representation literally reshapes itself around how the system
is being used. Inverse complexity: more use -> simpler encoding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

from .fnir import Op


PHI = (1 + 5 ** 0.5) / 2

# Stage 4 trit-arbiter recast walks tongues from most → least ownership
# information so the recast resolves toward the tongue with the strongest
# static guarantees first. Order:
#     DR  (monadic effects, total purity tracking)
#  -> RU  (affine borrow checker)
#  -> AV  (TS structural types)  /  UM  (Julia multiple dispatch)
#  -> KO  (Python GC, dynamic)
#  -> CA  (raw C, manual everything)
# Lock this order before band.py lands — Stage 4 depends on it.
TONGUE_PROMOTION_ORDER: tuple[str, ...] = ("DR", "RU", "AV", "UM", "KO", "CA")

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WIDTH: Dict[str, int] = {
    "KO": 6, "AV": 7, "RU": 8, "CA": 6, "UM": 7, "DR": 8,
}
TONGUE_PREFIX: Dict[str, str] = {
    "KO": "",       # no prefix, raw 6-bit
    "AV": "1",      # type-tag bit
    "RU": "11",     # ownership-tag prefix
    "CA": "",       # raw 6-bit
    "UM": "0",      # dispatch-tag bit
    "DR": "10",     # purity / monad prefix
}


def _base_bits(op: Op, tongue: str) -> str:
    """Initial binary code: tongue prefix + 6-bit op id, padded."""
    width = TONGUE_WIDTH[tongue]
    prefix = TONGUE_PREFIX[tongue]
    body_width = width - len(prefix)
    body = format(int(op), f"0{body_width}b")
    return prefix + body


# Frozen base table — every (op, tongue) -> initial bitstring.
OP_BINARY: Dict[Tuple[Op, str], str] = {
    (op, t): _base_bits(op, t) for op in Op for t in TONGUES
}


# --- Sustained-interaction ledger ----------------------------------------
@dataclass
class UsageLedger:
    """Tracks sustained semantic co-activation per (op, tongue) pair.

    `width[k]` is the path width worn into the lattice. It grows on
    activation and decays slowly on neglect, so a path stays wide only
    while the system keeps using it -- sustained interaction, not raw
    historical count.
    """

    width: Dict[Tuple[Op, str], float] = field(default_factory=dict)
    interactions: int = 0
    decay: float = 0.997           # per-tick passive decay
    growth: float = 1.0            # additive bump on activation
    remap_every: int = 256         # re-mod cadence
    remap_count: int = 0

    def _key(self, op: Op, tongue: str) -> Tuple[Op, str]:
        return (op, tongue)

    def touch(self, op: Op, tongue: str, intensity: float = 1.0) -> None:
        """Record a sustained interaction. Intensity scales the bump."""
        k = self._key(op, tongue)
        self.width[k] = self.width.get(k, 0.0) + self.growth * intensity
        self.interactions += 1
        # Passive decay across the whole ledger -- neglected paths fade.
        if self.interactions % 16 == 0:
            for kk in list(self.width.keys()):
                self.width[kk] *= self.decay
                if self.width[kk] < 1e-4:
                    del self.width[kk]
        if self.interactions % self.remap_every == 0:
            self.remap_count += 1

    def path_width(self, op: Op, tongue: str) -> float:
        return self.width.get(self._key(op, tongue), 0.0)

    def effective_cost(self, op: Op, tongue: str) -> float:
        """Bits-equivalent cost after path-widening discount.

        cost = base_width / phi^path_width

        Scale-invariant: a wider path multiplies the discount, never
        adds to it, so the same mechanism works for one op or a million.
        """
        base = float(TONGUE_WIDTH[tongue])
        w = self.path_width(op, tongue)
        return base / (PHI ** w)

    def total_cost(self, ops: list[tuple[Op, str]]) -> float:
        return sum(self.effective_cost(o, t) for o, t in ops)


# --- Re-mod: Huffman-style remap on widest paths -------------------------
def remap_tongue_table(ledger: UsageLedger, tongue: str) -> Dict[Op, str]:
    """Reissue the binary table for one tongue, sorted by path width.

    Ops with the widest worn paths get the shortest prefixes -- the
    encoding literally reshapes itself around how the block system is
    being used. Returns a fresh {Op: bitstring} table.
    """
    width = TONGUE_WIDTH[tongue]
    prefix = TONGUE_PREFIX[tongue]
    body_width = width - len(prefix)

    ranked = sorted(
        Op,
        key=lambda o: -ledger.path_width(o, tongue),
    )
    table: Dict[Op, str] = {}
    for rank, op in enumerate(ranked):
        body = format(rank, f"0{body_width}b")
        table[op] = prefix + body
    return table


def remap_all(ledger: UsageLedger) -> Dict[str, Dict[Op, str]]:
    return {t: remap_tongue_table(ledger, t) for t in TONGUES}


# --- Stream encoder ------------------------------------------------------
def encode_stream(
    ops: list[Op],
    tongue: str,
    table: Dict[Op, str] | None = None,
    ledger: UsageLedger | None = None,
) -> str:
    """Encode an op sequence into a bitstream for one tongue.

    If a ledger is supplied, every encoded op also touches the ledger
    so the lattice paths widen as the stream is consumed.
    """
    if table is None:
        table = {op: OP_BINARY[(op, tongue)] for op in Op}
    out = []
    for op in ops:
        out.append(table[op])
        if ledger is not None:
            ledger.touch(op, tongue)
    return "".join(out)


if __name__ == "__main__":
    # Quick demo: same op sequence, watch the cost shrink as the
    # ledger learns the groove.
    seq = [Op.CALL, Op.ADD, Op.READ, Op.RETURN, Op.BRANCH, Op.READ, Op.CALL]
    ledger = UsageLedger(growth=1.5, decay=0.999)

    print("op sequence:", [o.name for o in seq])
    print(f"\n{'tick':<6}{'KO bits':<10}{'KO cost':<12}"
          f"{'DR bits':<10}{'DR cost':<12}")
    for tick in range(1, 9):
        bits_ko = encode_stream(seq, "KO", ledger=ledger)
        bits_dr = encode_stream(seq, "DR", ledger=ledger)
        cost_ko = ledger.total_cost([(o, "KO") for o in seq])
        cost_dr = ledger.total_cost([(o, "DR") for o in seq])
        print(f"{tick:<6}{len(bits_ko):<10}{cost_ko:<12.3f}"
              f"{len(bits_dr):<10}{cost_dr:<12.3f}")

    print(f"\ninteractions: {ledger.interactions}")
    print(f"remaps fired: {ledger.remap_count}")
    print(f"widest KO paths:")
    ko_paths = sorted(
        ((o, ledger.path_width(o, "KO")) for o in Op),
        key=lambda kv: -kv[1],
    )[:5]
    for op, w in ko_paths:
        print(f"  {op.name:<12} width={w:.3f}  "
              f"cost={ledger.effective_cost(op, 'KO'):.3f}")
