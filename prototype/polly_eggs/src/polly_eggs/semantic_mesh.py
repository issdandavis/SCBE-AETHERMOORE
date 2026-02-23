from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

import numpy as np

MESH_BITS = 230


@dataclass
class SemanticMesh:
    bits: np.ndarray  # shape (230,), values {0,1}

    @staticmethod
    def zeros() -> "SemanticMesh":
        return SemanticMesh(bits=np.zeros(MESH_BITS, dtype=np.uint8))

    def to_hex(self) -> str:
        # Pack to bytes then hex; includes zero-padding to byte boundary.
        padded_len = ((MESH_BITS + 7) // 8) * 8
        padded = np.zeros(padded_len, dtype=np.uint8)
        padded[:MESH_BITS] = self.bits
        by = np.packbits(padded)
        return by.tobytes().hex()

    @staticmethod
    def from_hex(data: str) -> "SemanticMesh":
        raw = bytes.fromhex(data)
        arr = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
        return SemanticMesh(bits=arr[:MESH_BITS].astype(np.uint8))


def _index_for_token(token: str, lane: int) -> int:
    h = hashlib.sha256(f"{lane}:{token}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % MESH_BITS


def encode_tokens(tokens: Iterable[str], lanes: int = 3) -> SemanticMesh:
    m = np.zeros(MESH_BITS, dtype=np.uint8)
    for tok in tokens:
        t = str(tok).strip().lower()
        if not t:
            continue
        for lane in range(lanes):
            idx = _index_for_token(t, lane)
            m[idx] = 1
    return SemanticMesh(bits=m)


def overlay(mesh_a: SemanticMesh, mesh_b: SemanticMesh) -> SemanticMesh:
    return SemanticMesh(bits=np.bitwise_or(mesh_a.bits, mesh_b.bits))


def hamming_distance(mesh_a: SemanticMesh, mesh_b: SemanticMesh) -> int:
    return int(np.sum(np.bitwise_xor(mesh_a.bits, mesh_b.bits)))


def density(mesh: SemanticMesh) -> float:
    return float(np.mean(mesh.bits))


def governance_signal(mesh: SemanticMesh, baseline_density: float = 0.15) -> float:
    # Positive when sparse/structured, negative when over-saturated.
    d = density(mesh)
    return float(1.0 - abs(d - baseline_density) / max(baseline_density, 1e-6))
