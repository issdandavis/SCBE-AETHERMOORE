from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

PHI = (1.0 + 5.0 ** 0.5) / 2.0


@dataclass
class State21:
    """Canonical 21D state with M4 mapped to dims 13-15 (0-based slice 12:15)."""

    vec: np.ndarray

    @staticmethod
    def zeros() -> "State21":
        return State21(vec=np.zeros(21, dtype=np.float64))

    def model_pos(self) -> np.ndarray:
        return self.vec[12:15]

    def perp_space(self) -> np.ndarray:
        return self.vec[3:6]

    def swarm_state(self) -> np.ndarray:
        return self.vec[15:18]

    def trust_context(self) -> np.ndarray:
        return self.vec[0:3]

    def set_model_pos(self, xyz: np.ndarray) -> None:
        xyz = np.asarray(xyz, dtype=np.float64)
        if xyz.shape != (3,):
            raise ValueError("model position must be 3D")
        self.vec[12:15] = xyz

    def set_swarm_state(self, s: np.ndarray) -> None:
        s = np.asarray(s, dtype=np.float64)
        if s.shape != (3,):
            raise ValueError("swarm state must be 3D")
        self.vec[15:18] = s


def quantize_ternary(x: float) -> int:
    if x > 0.33:
        return 1
    if x < -0.33:
        return -1
    return 0


def crosses_negative_space(v1: np.ndarray, v2: np.ndarray) -> bool:
    mid = (np.asarray(v1) + np.asarray(v2)) / 2.0
    return any(quantize_ternary(float(v)) == -1 for v in mid)


def poincare_bound_ok(m: np.ndarray) -> bool:
    return float(np.linalg.norm(m)) < 1.0


def harmonic_energy(perp_distance: float) -> float:
    return float(PHI ** (perp_distance ** 2))


def compose_models(state: State21, other_model_pos: np.ndarray, threshold: float = 1000.0) -> Tuple[str, np.ndarray]:
    """Return (decision, composite_xyz).

    Decision: ALLOW, QUARANTINE, DENY
    """
    v_i = state.model_pos()
    v_j = np.asarray(other_model_pos, dtype=np.float64)
    if v_j.shape != (3,):
        raise ValueError("other_model_pos must be 3D")

    if not poincare_bound_ok(v_i) or not poincare_bound_ok(v_j):
        return "DENY", v_i

    if crosses_negative_space(v_i, v_j):
        return "DENY", v_i

    # 6D lift by concatenating shared perpendicular space.
    v_perp = state.perp_space()
    V_i = np.concatenate([v_i, v_perp])
    V_j = np.concatenate([v_j, v_perp])

    d_perp = np.linalg.norm(V_i[3:6] - V_j[3:6])
    e = harmonic_energy(float(d_perp))

    if e > threshold:
        return "QUARANTINE", v_i

    emergence_offset = np.array([0.01, 0.0, -0.01], dtype=np.float64)
    composite = (v_i + v_j) / 2.0 + emergence_offset

    if not poincare_bound_ok(composite):
        return "QUARANTINE", v_i

    state.set_model_pos(composite)
    # dim16: hash bucket, dim17: depth, dim18: emergence score proxy
    composite_id_bucket = float(abs(hash((float(v_i[0]), float(v_j[0])))) % 10_000)
    depth = float(state.swarm_state()[1] + 1.0)
    emergence = float(np.linalg.norm(composite - v_i))
    state.set_swarm_state(np.array([composite_id_bucket, depth, emergence], dtype=np.float64))

    return "ALLOW", composite
