from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class KernelSnapshot:
    t: int
    E: float
    J: float
    q: float
    p: np.ndarray
    R: float
    tier: str


class KarySimplexKernel:
    """K-ary intent-risk kernel (K=3 or K=4) with time dynamics."""

    def __init__(
        self,
        k: int = 4,
        lambda_e: float = 0.1,
        lambda_j: float = 0.05,
        tau: float = 0.8,
        epsilon: float = 1e-6,
        theta1: float = 0.35,
        theta2: float = 0.7,
        risk_weights: np.ndarray | None = None,
    ):
        if k not in (3, 4):
            raise ValueError("k must be 3 or 4")
        self.k = k
        self.lambda_e = float(lambda_e)
        self.lambda_j = float(lambda_j)
        self.tau = float(tau)
        self.epsilon = float(epsilon)
        self.theta1 = float(theta1)
        self.theta2 = float(theta2)

        if risk_weights is None:
            self.r = np.array([0.1, 0.5, 0.95, 0.2], dtype=np.float64) if k == 4 else np.array([0.1, 0.5, 0.95], dtype=np.float64)
        else:
            self.r = np.asarray(risk_weights, dtype=np.float64)
            if self.r.shape != (k,):
                raise ValueError("risk_weights shape mismatch")

        self.E = 0.0
        self.J = 0.0
        self.t = 0

    @staticmethod
    def _softmax(z: np.ndarray) -> np.ndarray:
        z = z - np.max(z)
        ez = np.exp(z)
        return ez / np.sum(ez)

    def _logits(self, E: float, J: float) -> np.ndarray:
        z_care = 1.8 * J - 1.2 * E
        z_neutral = 0.8 - abs(J) - 0.2 * E
        z_harm = -1.5 * J + 1.8 * E
        if self.k == 3:
            return np.array([z_care, z_neutral, z_harm], dtype=np.float64)
        z_repair = 1.2 * J + 1.2 * E - 0.5
        return np.array([z_care, z_neutral, z_harm, z_repair], dtype=np.float64)

    def _tier(self, R: float) -> str:
        if R < self.theta1:
            return "T1"
        if R < self.theta2:
            return "T2"
        return "T3"

    def step(self, P_t: float, D_t: float, v_t: float, I_t: float, dt: float = 1.0) -> KernelSnapshot:
        self.E = (1.0 - self.lambda_e) * self.E + float(v_t) * float(P_t) * float(D_t) * float(dt)
        self.J = (1.0 - self.lambda_j) * self.J + float(I_t) * float(dt)
        q = self.E / (abs(self.J) + self.epsilon)

        z = self._logits(self.E, self.J) / max(self.tau, self.epsilon)
        p = self._softmax(z)
        R = float(np.dot(p, self.r))
        tier = self._tier(R)

        snap = KernelSnapshot(t=self.t, E=float(self.E), J=float(self.J), q=float(q), p=p, R=R, tier=tier)
        self.t += 1
        return snap

    def simulate(self, sequence: List[Dict[str, float]]) -> List[KernelSnapshot]:
        out: List[KernelSnapshot] = []
        for row in sequence:
            out.append(
                self.step(
                    P_t=row.get("P_t", 1.0),
                    D_t=row.get("D_t", 0.5),
                    v_t=row.get("v_t", 0.5),
                    I_t=row.get("I_t", 0.0),
                    dt=row.get("dt", 1.0),
                )
            )
        return out


def snapshots_to_rows(snaps: List[KernelSnapshot]) -> List[Dict]:
    rows = []
    for s in snaps:
        rows.append(
            {
                "t": s.t,
                "E": s.E,
                "J": s.J,
                "q": s.q,
                "p": [float(x) for x in s.p],
                "R": s.R,
                "tier": s.tier,
            }
        )
    return rows


def default_sequence(n: int = 30) -> List[Dict[str, float]]:
    seq: List[Dict[str, float]] = []
    for i in range(n):
        # Controlled oscillation: this keeps data deterministic and easy to inspect.
        seq.append(
            {
                "P_t": 1.0,
                "D_t": 0.4 + 0.3 * np.sin(i / 6.0),
                "v_t": 0.5 + 0.4 * np.cos(i / 7.0),
                "I_t": 0.2 * np.sin(i / 5.0),
                "dt": 1.0,
            }
        )
    return seq
