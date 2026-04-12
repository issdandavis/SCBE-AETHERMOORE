"""
Holographic Bit Matrix
======================

Minimal, deterministic implementation used by the SCBE test suite.

This module intentionally emphasizes:
- determinism (same inputs -> same outputs)
- bounded numeric behavior
- simple, inspectable state for governance/audit paths
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np

PHI: float = (1.0 + 5.0**0.5) / 2.0

TONGUE_KEYS: List[str] = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_LONGITUDES: Dict[str, float] = {k: (2.0 * np.pi * i) / 6.0 for i, k in enumerate(TONGUE_KEYS)}
TONGUE_WEIGHTS: Dict[str, float] = {k: float(PHI**i) for i, k in enumerate(TONGUE_KEYS)}


@dataclass(frozen=True)
class HoloState:
    size: int
    tongues_active: List[str]
    tongues_null: List[str]
    bit_density: float
    trit_distribution: Dict[str, int]
    governance_cost: float
    mera_level: int


class HolographicBitMatrix:
    def __init__(self, size: int = 32):
        if size <= 0:
            raise ValueError("size must be positive")
        self.size = int(size)

        ii, jj = np.meshgrid(np.arange(self.size), np.arange(self.size), indexing="ij")
        field = np.sin((ii + 1) * PHI) + np.cos((jj + 1) * PHI * 0.5)
        self.bit_matrix = (field > 0.0).astype(np.int8)

        self.trit_matrix = np.zeros((self.size, self.size), dtype=np.int8)
        self.holo_field = np.zeros((self.size, self.size), dtype=np.float64)
        self.tongue_activation: Dict[str, float] = {k: 0.0 for k in TONGUE_KEYS}
        self.mera_level: int = 0

    def modulate_tongues(self, active_tongues: Sequence[str]) -> None:
        active = [t for t in active_tongues if t in TONGUE_KEYS]
        if len(active) == 0:
            self.trit_matrix[:] = -1
        elif len(active) == len(TONGUE_KEYS):
            self.trit_matrix[:] = 1
        else:
            self.trit_matrix[:] = -1
            mask = self.bit_matrix == 1
            self.trit_matrix[mask] = 1

        for k in TONGUE_KEYS:
            self.tongue_activation[k] = TONGUE_WEIGHTS[k] if k in active else 0.0

    def encode(self, signal: np.ndarray) -> None:
        signal = np.asarray(signal, dtype=np.float64)
        if signal.size == 0 or float(np.max(np.abs(signal))) == 0.0:
            self.holo_field[:] = 0.0
            return

        self.holo_field[:] = 0.0
        for idx, val in enumerate(signal.tolist()):
            i = idx % self.size
            j = (idx * 7 + 3) % self.size
            self.holo_field[i, j] += float(val)

        self.holo_field *= 0.5 + 0.5 * self.bit_matrix.astype(np.float64)
        if np.any(self.trit_matrix != 0):
            self.holo_field *= np.where(self.trit_matrix == 0, 1.0, self.trit_matrix.astype(np.float64))

    def decode(self, signal_length: int) -> np.ndarray:
        n = int(signal_length)
        if n <= 0:
            return np.zeros(0, dtype=np.float64)
        out = np.zeros(n, dtype=np.float64)
        for idx in range(n):
            i = idx % self.size
            j = (idx * 7 + 3) % self.size
            denom = 0.5 + 0.5 * float(self.bit_matrix[i, j])
            denom = denom if denom != 0.0 else 1.0
            val = self.holo_field[i, j] / denom
            out[idx] = val
        return out

    def mera_compress(self, level: int = 0) -> np.ndarray:
        lvl = max(0, int(level))
        self.mera_level = lvl
        field = self.holo_field
        for _ in range(lvl):
            if field.shape[0] <= 1 or field.shape[1] <= 1:
                break
            h = field.shape[0] // 2
            w = field.shape[1] // 2
            field = field[: 2 * h, : 2 * w].reshape(h, 2, w, 2).mean(axis=(1, 3))
        return field

    def combine(self) -> np.ndarray:
        combined = self.bit_matrix.astype(np.float64) * 0.5
        if np.any(self.trit_matrix != 0):
            combined = combined + 0.3 * self.trit_matrix.astype(np.float64)
        if np.any(self.holo_field != 0):
            combined = combined + 0.2 * self.holo_field.astype(np.float64)
        return combined.astype(np.float64)

    def to_weight_matrix(self) -> np.ndarray:
        return self.combine()

    def governance_cost(self) -> float:
        return float(sum(self.tongue_activation.values()))

    def harmonic_wall(self, drift: float, phi: float = PHI) -> float:
        d = float(drift)
        if d <= 0.0:
            return 1.0
        r = max(self.governance_cost(), 1.0)
        return float(r ** ((phi * d) ** 2))

    def state(self) -> HoloState:
        active = [k for k, v in self.tongue_activation.items() if v > 0.0]
        null = [k for k in TONGUE_KEYS if k not in active]
        vals, counts = np.unique(self.trit_matrix, return_counts=True)
        dist = {"-1": 0, "0": 0, "+1": 0}
        for v, c in zip(vals.tolist(), counts.tolist()):
            if v == -1:
                dist["-1"] = int(c)
            elif v == 0:
                dist["0"] = int(c)
            elif v == 1:
                dist["+1"] = int(c)
        return HoloState(
            size=self.size,
            tongues_active=active,
            tongues_null=null,
            bit_density=float(np.mean(self.bit_matrix)),
            trit_distribution=dist,
            governance_cost=self.governance_cost(),
            mera_level=self.mera_level,
        )

    def reconstruction_error(self, original: np.ndarray) -> float:
        original = np.asarray(original, dtype=np.float64)
        if original.size == 0 or float(np.max(np.abs(original))) == 0.0:
            return 0.0
        decoded = self.decode(signal_length=int(original.size))
        if decoded.size == 0:
            return 0.0
        return float(np.mean((decoded - original) ** 2))


def holographic_scatter_pipeline(
    signal: np.ndarray,
    active_tongues: Sequence[str],
    matrix_size: int = 32,
    mera_level: int = 0,
) -> Dict:
    hbm = HolographicBitMatrix(size=matrix_size)
    hbm.modulate_tongues(active_tongues)
    hbm.encode(np.asarray(signal, dtype=np.float64))
    compressed = hbm.mera_compress(level=mera_level)
    err = hbm.reconstruction_error(np.asarray(signal, dtype=np.float64))
    return {
        "weight_matrix": hbm.to_weight_matrix(),
        "compressed_field": compressed,
        "reconstruction_error": float(err),
        "state": hbm.state(),
    }
