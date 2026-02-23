from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np

from .state21 import PHI, crosses_negative_space, poincare_bound_ok


@dataclass
class ModelNode:
    name: str
    pos: np.ndarray  # shape (3,)
    trust: float


@dataclass
class SynthesisResult:
    decision: str
    composite_pos: np.ndarray
    inherited_trust: float
    harmonic_energy: float
    reason: str


def _harmonic_energy(nodes: List[ModelNode], perp: np.ndarray) -> float:
    lifted = [np.concatenate([n.pos, perp]) for n in nodes]
    if len(lifted) < 2:
        return 0.0
    dists = []
    for i in range(len(lifted)):
        for j in range(i + 1, len(lifted)):
            d = np.linalg.norm(lifted[i][3:6] - lifted[j][3:6])
            dists.append(float(d))
    d_bar = float(np.mean(dists)) if dists else 0.0
    return float(PHI ** (d_bar ** 2))


def synthesize(nodes: Iterable[ModelNode], perp_space: np.ndarray, threshold: float = 1000.0) -> SynthesisResult:
    models = list(nodes)
    if len(models) not in (2, 3):
        raise ValueError("synthesis requires exactly 2 or 3 model nodes")

    for n in models:
        if n.pos.shape != (3,):
            raise ValueError(f"{n.name} position must be shape (3,)")
        if not poincare_bound_ok(n.pos):
            return SynthesisResult("DENY", n.pos, n.trust, 0.0, f"{n.name} violates poincare bound")

    # Pairwise negative-space checks.
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            if crosses_negative_space(models[i].pos, models[j].pos):
                return SynthesisResult("DENY", models[i].pos, min(m.trust for m in models), 0.0, "negative-space crossing")

    # Weighted centroid by trust.
    trust_vec = np.array([max(0.001, float(m.trust)) for m in models], dtype=np.float64)
    pos_stack = np.stack([m.pos for m in models], axis=0)
    composite = np.average(pos_stack, axis=0, weights=trust_vec)

    if not poincare_bound_ok(composite):
        composite = composite / max(np.linalg.norm(composite), 1e-9) * 0.99

    energy = _harmonic_energy(models, np.asarray(perp_space, dtype=np.float64))
    inherited = float(min(m.trust for m in models))

    if energy > threshold:
        return SynthesisResult("QUARANTINE", composite, inherited, energy, "harmonic wall threshold exceeded")

    return SynthesisResult("ALLOW", composite, inherited, energy, "valid synthesis")


def from_payload(payload: dict) -> Tuple[List[ModelNode], np.ndarray, float]:
    raw = payload.get("models", [])
    if not isinstance(raw, list):
        raise ValueError("models must be a list")
    nodes: List[ModelNode] = []
    for item in raw:
        nodes.append(
            ModelNode(
                name=str(item["name"]),
                pos=np.array(item["pos"], dtype=np.float64),
                trust=float(item.get("trust", 0.5)),
            )
        )
    perp = np.array(payload.get("perp_space", [0.0, 0.0, 0.0]), dtype=np.float64)
    if perp.shape != (3,):
        raise ValueError("perp_space must be 3D")
    threshold = float(payload.get("threshold", 1000.0))
    return nodes, perp, threshold
