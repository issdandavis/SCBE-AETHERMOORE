"""
@file transfer_recorder.py
@module geoseed/transfer_recorder
@component AtomTransferRecorder

Tracks token/atom transfers between GeoSeed orbital shells (tongues).

Analogy: isotope tracing in chemistry — label each token with the shell
it enters on, follow where it resolves, record the hop.

Each shell-to-shell hop costs a geodesic distance that is a multiple of
ln(φ): adjacent shells = ln(φ), two apart = 2·ln(φ), etc.  Because all
adjacent gaps are uniform (proven by tests/geoseed/test_orbital_model.py),
the transfer cost is simply n·ln(φ) where n = |from_index - to_index|.

This is a STUB — the interface is fixed; the tokenizer wires in later.
The recorder itself has no tokenizer dependency.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PHI = (1.0 + math.sqrt(5.0)) / 2.0
LN_PHI = math.log(PHI)

# Canonical tongue order — index is the shell index
TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_INDEX: Dict[str, int] = {t: i for i, t in enumerate(TONGUE_ORDER)}
TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


# ── Core types ────────────────────────────────────────────────────────────────

@dataclass
class TransferEvent:
    """One atom/token moving from one orbital shell to another."""
    from_tongue: str        # e.g. "KO"
    to_tongue: str          # e.g. "AV"
    token: str              # the token that transferred
    geodesic_cost: float    # n·ln(φ), n = |from_idx - to_idx|
    is_self: bool           # True when from == to (no hop)
    step: int               # sequence number within this recording session
    metadata: dict = field(default_factory=dict)


@dataclass
class TransferMatrix:
    """
    6×6 count matrix M[from_idx][to_idx] and derived rate/cost matrices.
    Rows = source shell, columns = destination shell.
    """
    counts: List[List[int]]         # raw hop counts
    rates: List[List[float]]        # counts / total_events (row-normalised)
    costs: List[List[float]]        # geodesic cost per cell (n·ln(φ))
    total_events: int
    self_transfer_count: int        # diagonal sum
    cross_transfer_count: int       # off-diagonal sum

    def dominant_flow(self) -> List[Tuple[str, str, int]]:
        """Top-5 (from, to) pairs by count, excluding self-transfers."""
        flows = []
        for i, row in enumerate(self.counts):
            for j, cnt in enumerate(row):
                if i != j and cnt > 0:
                    flows.append((TONGUE_ORDER[i], TONGUE_ORDER[j], cnt))
        flows.sort(key=lambda x: -x[2])
        return flows[:5]

    def to_dict(self) -> dict:
        return {
            "schema_version": "geoseed_transfer_matrix_v1",
            "tongues": TONGUE_ORDER,
            "counts": self.counts,
            "rates": [[round(v, 6) for v in row] for row in self.rates],
            "costs": self.costs,
            "total_events": self.total_events,
            "self_transfer_count": self.self_transfer_count,
            "cross_transfer_count": self.cross_transfer_count,
            "dominant_flow": [
                {"from": f, "to": t, "count": c}
                for f, t, c in self.dominant_flow()
            ],
        }


# ── Geodesic cost helper ──────────────────────────────────────────────────────

def transfer_cost(from_tongue: str, to_tongue: str) -> float:
    """
    Geodesic distance between two orbital shells.
    Cost = |from_index - to_index| · ln(φ).
    Same-shell transfer costs 0.
    """
    fi = TONGUE_INDEX.get(from_tongue, -1)
    ti = TONGUE_INDEX.get(to_tongue, -1)
    if fi < 0 or ti < 0:
        raise ValueError(f"Unknown tongue: '{from_tongue}' or '{to_tongue}'")
    return abs(fi - ti) * LN_PHI


# ── Recorder ─────────────────────────────────────────────────────────────────

class AtomTransferRecorder:
    """
    Accumulates TransferEvents and computes the 6×6 transfer matrix.

    Usage (standalone):
        rec = AtomTransferRecorder()
        rec.record("KO", "AV", "def")
        rec.record("CA", "CA", "heapq")   # self-transfer (no hop)
        matrix = rec.transfer_matrix()
        print(rec.summary())

    Usage (from tokenizer — wired later):
        for token, from_t, to_t in tokenizer.route_tokens(text):
            rec.record(from_t, to_t, token)
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or "default"
        self._events: List[TransferEvent] = []
        self._step = 0

    # ── Recording ─────────────────────────────────────────────────────────

    def record(
        self,
        from_tongue: str,
        to_tongue: str,
        token: str,
        metadata: Optional[dict] = None,
    ) -> TransferEvent:
        """Record one atom/token transfer between shells."""
        if from_tongue not in TONGUE_INDEX:
            raise ValueError(f"Unknown from_tongue: '{from_tongue}'")
        if to_tongue not in TONGUE_INDEX:
            raise ValueError(f"Unknown to_tongue: '{to_tongue}'")
        cost = transfer_cost(from_tongue, to_tongue)
        evt = TransferEvent(
            from_tongue=from_tongue,
            to_tongue=to_tongue,
            token=token,
            geodesic_cost=cost,
            is_self=(from_tongue == to_tongue),
            step=self._step,
            metadata=metadata or {},
        )
        self._events.append(evt)
        self._step += 1
        return evt

    def record_batch(self, triples: List[Tuple[str, str, str]]) -> None:
        """Record many (from_tongue, to_tongue, token) triples at once."""
        for from_t, to_t, token in triples:
            self.record(from_t, to_t, token)

    def reset(self) -> None:
        self._events.clear()
        self._step = 0

    # ── Queries ───────────────────────────────────────────────────────────

    @property
    def events(self) -> List[TransferEvent]:
        return list(self._events)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def events_for_token(self, token: str) -> List[TransferEvent]:
        return [e for e in self._events if e.token == token]

    def events_from(self, tongue: str) -> List[TransferEvent]:
        return [e for e in self._events if e.from_tongue == tongue]

    def events_to(self, tongue: str) -> List[TransferEvent]:
        return [e for e in self._events if e.to_tongue == tongue]

    def total_geodesic_cost(self) -> float:
        return sum(e.geodesic_cost for e in self._events)

    def mean_hop_distance(self) -> float:
        cross = [e for e in self._events if not e.is_self]
        if not cross:
            return 0.0
        return sum(e.geodesic_cost for e in cross) / len(cross)

    # ── Matrix computation ─────────────────────────────────────────────────

    def transfer_matrix(self) -> TransferMatrix:
        n = len(TONGUE_ORDER)
        counts = [[0] * n for _ in range(n)]
        for e in self._events:
            fi = TONGUE_INDEX[e.from_tongue]
            ti = TONGUE_INDEX[e.to_tongue]
            counts[fi][ti] += 1

        total = sum(sum(row) for row in counts)
        rates: List[List[float]] = []
        for row in counts:
            row_sum = sum(row)
            if row_sum == 0:
                rates.append([0.0] * n)
            else:
                rates.append([c / row_sum for c in row])

        costs = [
            [abs(i - j) * LN_PHI for j in range(n)]
            for i in range(n)
        ]

        self_count = sum(counts[i][i] for i in range(n))
        cross_count = total - self_count

        return TransferMatrix(
            counts=counts,
            rates=rates,
            costs=costs,
            total_events=total,
            self_transfer_count=self_count,
            cross_transfer_count=cross_count,
        )

    # ── Summary ───────────────────────────────────────────────────────────

    def summary(self) -> str:
        if not self._events:
            return "AtomTransferRecorder: no events recorded."

        mx = self.transfer_matrix()
        lines = [
            f"AtomTransferRecorder  session={self.session_id}",
            f"  events       : {self.event_count}",
            f"  self-hops    : {mx.self_transfer_count}",
            f"  cross-hops   : {mx.cross_transfer_count}",
            f"  total cost   : {self.total_geodesic_cost():.4f}  (units: ln φ = {LN_PHI:.4f})",
            f"  mean hop Δρ  : {self.mean_hop_distance():.4f}",
            "",
            "  Transfer matrix (counts):",
            "        " + "  ".join(f"{t:>4}" for t in TONGUE_ORDER),
        ]
        for i, row in enumerate(mx.counts):
            lines.append(
                f"  {TONGUE_ORDER[i]:<4}  " + "  ".join(f"{c:>4}" for c in row)
            )

        if mx.dominant_flow():
            lines.append("")
            lines.append("  Dominant flows:")
            for f, t, c in mx.dominant_flow():
                cost = transfer_cost(f, t)
                lines.append(f"    {f} → {t}  ×{c}  (Δρ={cost:.3f})")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        mx = self.transfer_matrix()
        return {
            "schema_version": "geoseed_transfer_recorder_v1",
            "session_id": self.session_id,
            "event_count": self.event_count,
            "total_geodesic_cost": round(self.total_geodesic_cost(), 6),
            "mean_hop_distance": round(self.mean_hop_distance(), 6),
            "ln_phi": round(LN_PHI, 9),
            "matrix": mx.to_dict(),
        }
