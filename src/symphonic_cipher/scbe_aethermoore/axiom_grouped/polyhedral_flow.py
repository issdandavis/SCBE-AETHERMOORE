"""Polyhedral flow routing + confinement metrics (test-driven).

This module provides deterministic, dependency-light primitives used by the unit tests in
`tests/test_polyhedral_flow.py`. It is not intended to be a full physics simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import math
import random

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INV: float = 1.0 / PHI


TONGUE_WEIGHTS: Dict[str, float] = {
    "KO": PHI**0,
    "AV": PHI**1,
    "RU": PHI**2,
    "CA": PHI**3,
    "UM": PHI**4,
    "DR": PHI**5,
}


FIB_SEQUENCE: List[int] = [0, 1]
for _ in range(62):
    FIB_SEQUENCE.append(FIB_SEQUENCE[-1] + FIB_SEQUENCE[-2])


@dataclass(frozen=True)
class Polyhedron:
    index: int
    name: str
    family: str
    faces: int
    edges: int
    vertices: int
    euler_chi: int
    depth: float
    dual_index: Optional[int] = None


POLYHEDRA: List[Polyhedron] = [
    Polyhedron(0, "tetrahedron", "platonic", 4, 6, 4, 2, 0.05),
    Polyhedron(1, "cube", "platonic", 6, 12, 8, 2, 0.08, dual_index=2),
    Polyhedron(2, "octahedron", "platonic", 8, 12, 6, 2, 0.10, dual_index=1),
    Polyhedron(3, "dodecahedron", "platonic", 12, 30, 20, 2, 0.12, dual_index=4),
    Polyhedron(4, "icosahedron", "platonic", 20, 30, 12, 2, 0.15, dual_index=3),
    Polyhedron(5, "cuboctahedron", "archimedean", 14, 24, 12, 2, 0.18),
    Polyhedron(6, "icosidodecahedron", "archimedean", 32, 60, 30, 2, 0.22),
    Polyhedron(7, "truncated_tetrahedron", "archimedean", 8, 18, 12, 2, 0.25),
    Polyhedron(8, "truncated_cube", "archimedean", 14, 36, 24, 2, 0.28),
    Polyhedron(9, "truncated_octahedron", "archimedean", 14, 36, 24, 2, 0.30),
    Polyhedron(10, "toroidal_7_21_14", "toroidal", 14, 21, 7, 0, 0.33),
    Polyhedron(11, "toroidal_9_27_18", "toroidal", 18, 27, 9, 0, 0.36),
    Polyhedron(12, "toroidal_12_36_24", "toroidal", 24, 36, 12, 0, 0.40),
    Polyhedron(13, "toroidal_16_48_32", "toroidal", 32, 48, 16, 0, 0.44),
    Polyhedron(14, "toroidal_20_60_40", "toroidal", 40, 60, 20, 0, 0.48),
    Polyhedron(15, "toroidal_24_72_48", "toroidal", 48, 72, 24, 0, 0.52),
]


FLOW_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 2],
    1: [0, 3],
    2: [0, 3, 4],
    3: [1, 2, 5],
    4: [2, 6],
    5: [3, 7],
    6: [4, 8],
    7: [5, 9],
    8: [6, 10],
    9: [7, 11],
    10: [8, 12],
    11: [9, 13],
    12: [10, 14],
    13: [11, 15],
    14: [12, 15],
    15: [13, 14],
}


PLATONIC_CONSTRAINT_ORDERS: Dict[str, int] = {
    "tetrahedron": 12,
    "cube": 24,
    "octahedron": 24,
    "dodecahedron": 60,
    "icosahedron": 60,
}


def fibonacci_spin(step: int, n_bits: int = 8) -> List[int]:
    step = int(step) % int(n_bits)
    base = [(FIB_SEQUENCE[i + 2] % 2) for i in range(n_bits)]
    return base[step:] + base[:step]


def fibonacci_phase(step: int) -> float:
    step = int(step)
    golden_angle = 2.0 * math.pi / (PHI * PHI)
    return float((step * golden_angle) % (2.0 * math.pi))


class FibonacciLFSR:
    def __init__(self, *, n_bits: int = 8, state: int = 1):
        self.n_bits = int(n_bits)
        self.state = int(state) & ((1 << self.n_bits) - 1)
        if self.state == 0:
            self.state = 1

        if self.n_bits == 8:
            self.taps = (7, 5, 4, 3)
        elif self.n_bits == 16:
            self.taps = (15, 13, 8, 5)
        elif self.n_bits == 32:
            self.taps = (31, 21, 13, 8)
        else:
            self.taps = tuple(sorted({self.n_bits - 1, self.n_bits - 2, max(self.n_bits - 5, 0)}))

    def step(self) -> int:
        bit = 0
        for t in self.taps:
            bit ^= (self.state >> t) & 1
        self.state = ((self.state << 1) & ((1 << self.n_bits) - 1)) | bit
        if self.state == 0:
            self.state = 1
        return bit

    def generate(self, n: int) -> List[int]:
        return [self.step() for _ in range(int(n))]

    def current_bits(self) -> List[int]:
        return [int((self.state >> i) & 1) for i in reversed(range(self.n_bits))]


class DualSpin:
    def __init__(self, *, seed: int = 0):
        self.seed = int(seed)
        self.lfsr_a = FibonacciLFSR(n_bits=8, state=(self.seed or 1) & 0xFF)
        self.lfsr_b = FibonacciLFSR(n_bits=8, state=((self.seed ^ 0xA5) or 1) & 0xFF)

    def spin(self) -> List[int]:
        a = self.lfsr_a.generate(8)
        b = self.lfsr_b.generate(8)
        return [ai ^ bi for ai, bi in zip(a, b)]

    def route_index(self) -> int:
        bits = self.spin()
        val = 0
        for b in bits:
            val = (val << 1) | int(b)
        return int(val % 16)

    def ternary_state(self) -> List[int]:
        bits = self.spin()
        ternary: List[int] = []
        for i in range(0, len(bits), 2):
            a = bits[i]
            b = bits[i + 1] if i + 1 < len(bits) else 0
            v = a - b
            ternary.append(-1 if v < 0 else (1 if v > 0 else 0))
        return ternary


class PolyhedralFlowRouter:
    TONGUE_START: Dict[str, int] = {"KO": 0, "AV": 1, "RU": 2, "CA": 3, "UM": 4, "DR": 5}

    def __init__(self, *, max_hops: int = 5):
        self.max_hops = int(max_hops)

    def route(
        self, tongue: str, *, seed: Optional[int] = None, friction_penalty: bool = False
    ) -> List[Dict[str, object]]:
        tongue = str(tongue)
        if tongue not in TONGUE_WEIGHTS:
            raise ValueError(f"Unknown tongue: {tongue}")

        rng = random.Random(seed)
        idx = self.TONGUE_START.get(tongue, 0)
        path: List[Dict[str, object]] = []
        cumulative = 0.0
        ds = DualSpin(seed=seed or 0)

        for hop in range(self.max_hops):
            poly = POLYHEDRA[idx]
            zone = "SAFE" if poly.depth < 0.25 else ("EDGE" if poly.depth < 0.4 else "DEEP")
            entry: Dict[str, object] = {
                "hop": hop,
                "polyhedron": poly.name,
                "poly_index": poly.index,
                "zone": zone,
                "family": poly.family,
                "depth": poly.depth,
                "phi_weight": TONGUE_WEIGHTS[tongue],
                "ternary_state": ds.ternary_state(),
                "fibonacci_phase": fibonacci_phase(hop),
                "faces": poly.faces,
                "euler_chi": poly.euler_chi,
            }

            if friction_penalty and hop > 0:
                prev = POLYHEDRA[int(path[-1]["poly_index"])]  # type: ignore[index]
                fr = contact_friction(prev, poly)
                cumulative += float(fr["friction_magnitude"])
                entry["friction"] = fr
                entry["cumulative_friction"] = cumulative

            path.append(entry)
            idx = rng.choice(FLOW_ADJACENCY[idx])

        return path

    def generate_flow_address(self, tongue: str, *, seed: Optional[int] = None) -> str:
        path = self.route(tongue, seed=seed)
        return f"{tongue}:" + "->".join(str(h["polyhedron"]) for h in path)


def composite_harmonic_wall(
    distances: Dict[str, float],
    *,
    phase_deviation: float = 0.0,
    phi: float = PHI,
) -> Dict[str, object]:
    vals = [float(v) for v in distances.values()] or [0.0]
    mean_d = sum(vals) / len(vals)
    h = math.exp(-phi * mean_d) * math.exp(-abs(float(phase_deviation)) / 5.0)
    h *= math.exp(-0.03 * max(len(vals) - 1, 0))
    h = float(max(min(h, 1.0), 1e-12))
    tier = "ALLOW" if h >= 0.75 else ("DENY" if h < 0.15 else "QUARANTINE")
    return {"h_composite": h, "tier": tier, "mitm_immune": True}


def poincare_distance(x1: float, x2: float, depth: float) -> float:
    r1 = abs(float(x1))
    r2 = abs(float(x2))
    if r1 >= 1.0 or r2 >= 1.0 or abs(float(depth)) >= 1.0:
        return float("inf")
    diff = abs(float(x1) - float(x2)) + abs(float(depth))
    return float(2.0 * math.atanh(min(diff, 0.999999)))


def evaluate_flow_confinement(path: Sequence[Dict[str, object]], tongue: str) -> Dict[str, object]:
    dists: Dict[str, float] = {}
    for hop in path:
        name = str(hop["polyhedron"])
        if name in PLATONIC_CONSTRAINT_ORDERS:
            dists[name] = float(hop["depth"])
    result = composite_harmonic_wall(dists or {"tetrahedron": 0.0}, phase_deviation=0.0)
    return {**result, "path_length": len(list(path))}


def polyhedral_natural_frequency(p: Polyhedron) -> float:
    euler_term = abs(float(p.euler_chi)) + 1.0
    return float((p.faces + 0.5 * p.edges + 0.25 * p.vertices) / euler_term + (1.0 + p.depth) * PHI_INV)


def contact_friction(a: Polyhedron, b: Polyhedron) -> Dict[str, float]:
    fa = polyhedral_natural_frequency(a)
    fb = polyhedral_natural_frequency(b)
    beat = abs(fa - fb)
    torsion = abs(a.faces - b.faces) * PHI_INV
    magnitude = beat + torsion
    return {"beat_frequency": float(beat), "torsional_moment": float(torsion), "friction_magnitude": float(magnitude)}


def compute_friction_spectrum() -> List[Dict[str, object]]:
    spectrum: List[Dict[str, object]] = []
    for i in range(len(POLYHEDRA) - 1):
        a = POLYHEDRA[i]
        b = POLYHEDRA[i + 1]
        spectrum.append({"a": a.name, "b": b.name, **contact_friction(a, b)})
    spectrum.sort(key=lambda x: float(x["friction_magnitude"]), reverse=True)
    return spectrum


def friction_laplacian() -> Dict[str, object]:
    n = 16
    W = [[0.0 for _ in range(n)] for _ in range(n)]
    for i, neighbors in FLOW_ADJACENCY.items():
        for j in neighbors:
            fr = contact_friction(POLYHEDRA[i], POLYHEDRA[j])
            w = 1.0 / (1.0 + float(fr["friction_magnitude"]))
            W[i][j] = max(W[i][j], w)
            W[j][i] = max(W[j][i], w)

    L = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        deg = sum(W[i])
        for j in range(n):
            L[i][j] = (deg if i == j else 0.0) - W[i][j]
    trace = sum(L[i][i] for i in range(n))
    return {"n_nodes": n, "trace": float(trace), "laplacian_matrix": L}


def geometric_training_signal(path: Sequence[Dict[str, object]], tongue: str) -> Dict[str, object]:
    tongue = str(tongue)
    total = 0.0
    seq: List[float] = []
    for i in range(1, len(path)):
        a = POLYHEDRA[int(path[i - 1]["poly_index"])]  # type: ignore[index]
        b = POLYHEDRA[int(path[i]["poly_index"])]  # type: ignore[index]
        fr = contact_friction(a, b)
        seq.append(float(fr["friction_magnitude"]))
        total += float(fr["friction_magnitude"])

    energy = float(total * TONGUE_WEIGHTS[tongue])
    return {"friction_sequence": seq, "training_energy": energy, "tongue": tongue, "total_friction": float(total)}


def generate_hash_training_pair(tongue: str, *, seed: int = 0, adversarial: bool = False) -> Dict[str, object]:
    router = PolyhedralFlowRouter()
    path = router.route(tongue, seed=seed, friction_penalty=True)
    confinement = evaluate_flow_confinement(path, tongue)
    flow_address = router.generate_flow_address(tongue, seed=seed)
    instruction = f"Generate and evaluate {tongue} polyhedral flow confinement."
    output = {"flow_address": flow_address, **confinement}
    return {
        "instruction": instruction,
        "output": output,
        "flow_address": flow_address,
        "h_composite": confinement["h_composite"],
        "tier": confinement["tier"],
        "adversarial": bool(adversarial),
    }


def generate_flow_training_pairs(*, n_pairs: int = 12) -> List[Dict[str, object]]:
    tongues = list(TONGUE_WEIGHTS.keys())
    pairs: List[Dict[str, object]] = []
    for i in range(int(n_pairs)):
        tongue = tongues[i % len(tongues)]
        pairs.append(generate_hash_training_pair(tongue, seed=i))
    return pairs
