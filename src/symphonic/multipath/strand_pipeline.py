"""Stage 3.5 + 4 integration: strand -> op_binary -> rhombic fusion.

Wires the three existing encoder pieces into one pass:

    extrude_strand (group_alignment.py)   -- organic dominant tongue per op
        v
    phi-discounted bitstream (op_binary)  -- sustained-interaction grooves
        v
    symbolic x vector + rhombic_fusion    -- cross-modal coupling score

Before this module, each piece lived alone. The strand picked a dominant
tongue but didn't emit bits; the ledger discounted repeat ops but had no
semantic home; the rhombic functional scored sensory coupling but was
never driven by the symbolic encoder. One call now produces all four
outputs.

The rhombic math is inlined from python/scbe/rhombic_bridge.py so this
module stays self-contained inside src/symphonic/multipath/.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ._trit_common import PHI_WEIGHTS
from .group_alignment import Strand, extrude_strand
from .op_binary import PHI, TONGUE_PREFIX, TONGUE_WIDTH


# --- String-keyed usage ledger -------------------------------------------
@dataclass
class StringLedger:
    """UsageLedger keyed on (op_name, tongue) strings.

    op_binary.UsageLedger keys on the 64-op FnIR Op enum. The strand
    extruder speaks each tongue's native vocab (add, bind_d, if_, ...),
    so we need a parallel ledger that indexes on those strings directly.
    The discount law is identical: cost = base_width / phi^path_width.
    """

    width: Dict[Tuple[str, str], float] = field(default_factory=dict)
    interactions: int = 0
    decay: float = 0.997
    growth: float = 1.0

    def touch(self, op: str, tongue: str, intensity: float = 1.0) -> None:
        k = (op, tongue)
        self.width[k] = self.width.get(k, 0.0) + self.growth * intensity
        self.interactions += 1
        if self.interactions % 16 == 0:
            for kk in list(self.width.keys()):
                self.width[kk] *= self.decay
                if self.width[kk] < 1e-4:
                    del self.width[kk]

    def path_width(self, op: str, tongue: str) -> float:
        return self.width.get((op, tongue), 0.0)

    def effective_cost(self, op: str, tongue: str) -> float:
        base = float(TONGUE_WIDTH[tongue])
        w = self.path_width(op, tongue)
        return base / (PHI ** w)


# --- Bead-local bit encoding ---------------------------------------------
def _encode_bead_bits(op_name: str, tongue: str) -> str:
    """Tongue prefix + hashed 6/7/8-bit body for a string op.

    Matches op_binary.TONGUE_WIDTH / TONGUE_PREFIX so the bitstream has
    the same tongue-specific shape, but indexes on the op name so any
    strand-native vocab (including cross-tongue unknowns) encodes.
    """
    width = TONGUE_WIDTH[tongue]
    prefix = TONGUE_PREFIX[tongue]
    body_width = width - len(prefix)
    # Stable cross-session hash: Python's builtin hash() is salted per
    # interpreter run (PYTHONHASHSEED), so use sha256 for determinism.
    digest = hashlib.sha256(op_name.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") & ((1 << body_width) - 1)
    return prefix + format(idx, f"0{body_width}b")


# --- Inlined rhombic fusion (from python/scbe/rhombic_bridge.py) ---------
def _rhombic_fusion(
    x: np.ndarray,
    audio: np.ndarray,
    vision: np.ndarray,
    governance: np.ndarray,
    k: int = 0,
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
    eta: float = 0.5,
    phi: float = 1.618033988749895,
) -> float:
    x = np.asarray(x, dtype=float).reshape(-1)
    a = np.abs(np.asarray(audio, dtype=float).reshape(-1))
    v = np.abs(np.asarray(vision, dtype=float).reshape(-1))
    g = np.asarray(governance, dtype=float).reshape(-1)

    e01 = float(np.linalg.norm(x - a) ** 2)
    e02 = float(np.linalg.norm(x - v) ** 2)
    e13 = float(np.linalg.norm(a - g) ** 2)
    e23 = float(np.linalg.norm(v - g) ** 2)
    e12 = float(np.linalg.norm(a - v) ** 2)

    phase = float((-1.0 / phi) ** (k % 3))
    return float(
        alpha * (e01 + e02)
        + beta * (e13 + e23)
        + gamma * e12
        + eta * phase * e12
    )


# --- Pipeline result + driver --------------------------------------------
@dataclass
class PipelineResult:
    strand: Strand
    bitstream: str
    per_bead_bits: List[str]
    ledger_cost: float
    symbolic_x: np.ndarray
    rhombic_R: Optional[float] = None
    rhombic_score: Optional[float] = None
    decision: Optional[str] = None

    def dominants(self) -> List[str]:
        return self.strand.dominant_sequence()


# L13 thresholds on rhombic_score = exp(-R). High score = coherent = safe.
# Tuned against the demo distribution: random sensors produce R in [1, 50+]
# so scores cluster near 0; coherent runs sit above 0.5.
DECISION_THRESHOLDS = (
    (0.50, "ALLOW"),
    (0.20, "QUARANTINE"),
    (0.05, "ESCALATE"),
)


def decide(rhombic_score: Optional[float]) -> str:
    """Map rhombic_score -> ALLOW/QUARANTINE/ESCALATE/DENY.

    No sensors -> ALLOW (symbolic path only, nothing to adjudicate).
    """
    if rhombic_score is None:
        return "ALLOW"
    for threshold, label in DECISION_THRESHOLDS:
        if rhombic_score >= threshold:
            return label
    return "DENY"


def run_pipeline(
    ops: Sequence[str],
    ledger: StringLedger,
    *,
    audio: Optional[np.ndarray] = None,
    vision: Optional[np.ndarray] = None,
    governance: Optional[np.ndarray] = None,
    phase_k: int = 0,
) -> PipelineResult:
    """One pass: ops -> strand -> bitstream -> x -> optional rhombic score.

    The ledger is mutated in place (grooves wear in across repeated calls).
    Sensory inputs (audio/vision/governance) are optional; if any is
    missing, the rhombic fields stay None.
    """
    strand = extrude_strand(ops)

    per_bead_bits: List[str] = []
    x_accum = np.zeros(6, dtype=np.float64)
    for bead in strand.beads:
        bits = _encode_bead_bits(bead.op_name, bead.dominant)
        per_bead_bits.append(bits)
        ledger.touch(bead.op_name, bead.dominant)
        x_accum += bead.coactivation * np.asarray(PHI_WEIGHTS, dtype=np.float64)

    if len(strand.beads) > 0:
        x_accum /= float(len(strand.beads))

    bitstream = "".join(per_bead_bits)
    ledger_cost = float(
        sum(ledger.effective_cost(b.op_name, b.dominant) for b in strand.beads)
    )

    result = PipelineResult(
        strand=strand,
        bitstream=bitstream,
        per_bead_bits=per_bead_bits,
        ledger_cost=ledger_cost,
        symbolic_x=x_accum,
    )

    if audio is not None and vision is not None and governance is not None:
        R = _rhombic_fusion(
            x_accum, audio, vision, governance, k=phase_k,
        )
        result.rhombic_R = R
        result.rhombic_score = float(np.exp(-R))

    result.decision = decide(result.rhombic_score)
    return result


if __name__ == "__main__":
    demo_ops = ["add", "if_", "own", "promise", "matrix", "bind_d"]
    ledger = StringLedger(growth=1.5)

    print("=== cold run ===")
    r1 = run_pipeline(demo_ops, ledger)
    print(f"  dominants   = {r1.dominants()}")
    print(f"  bitstream   = {r1.bitstream}")
    print(f"  bits        = {len(r1.bitstream)}")
    print(f"  ledger cost = {r1.ledger_cost:.3f}")
    print(f"  x           = {r1.symbolic_x}")

    print("\n=== warm run (8 repeats, same ops) ===")
    for _ in range(8):
        r = run_pipeline(demo_ops, ledger)
    print(f"  ledger cost = {r.ledger_cost:.3f}  (was {r1.ledger_cost:.3f})")

    print("\n=== with sensors ===")
    rng = np.random.default_rng(0)
    r3 = run_pipeline(
        demo_ops, ledger,
        audio=rng.normal(size=6),
        vision=rng.normal(size=6),
        governance=rng.normal(size=6),
    )
    print(f"  rhombic R = {r3.rhombic_R:.3f}")
    print(f"  score     = {r3.rhombic_score:.6f}")
