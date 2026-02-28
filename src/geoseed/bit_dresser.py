"""
GeoSeed Bit Dresser (F1)
========================

Deterministic bit-level dressing for training data (F1 tier).
This module intentionally focuses on the L1-L5 path for a stable
"hello world" fingerprint pipeline:

L1: complex state
L2: realification
L3: weighted transform
L4: Poincare embedding
L5: hyperbolic distance
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Dict, List

import numpy as np

from src.geoseed.sphere_grid import TONGUE_NAMES, TONGUE_PHASES
from src.scbe_14layer_reference import (
    layer_0_intent_modulation,
    layer_1_complex_state,
    layer_2_realification,
    layer_3_weighted_transform,
    layer_4_poincare_embedding,
    layer_5_hyperbolic_distance,
)


@dataclass
class BitFingerprint:
    """Deterministic geometric fingerprint for one dressed bit."""

    byte_index: int
    bit_index: int
    bit_position: int
    bit_value: int
    tongue: str
    layer_path: List[int]
    complex_state_real: List[float]
    complex_state_imag: List[float]
    real_state: List[float]
    weighted_state: List[float]
    poincare_pos: List[float]
    hyperbolic_distance: float
    fingerprint_id: str


class BitDresserF1:
    """Bit-level deterministic dresser for F1 training flows."""

    def __init__(self, *, dimension: int = 6, key: str = "geoseed_f1"):
        self.dimension = max(2, int(dimension))
        self.key = str(key)

    @staticmethod
    def _round_list(values: np.ndarray, places: int = 6) -> List[float]:
        return [round(float(v), places) for v in values.tolist()]

    def _build_input_vector(
        self,
        *,
        byte_value: int,
        bit_value: int,
        byte_index: int,
        bit_index: int,
        tongue: str,
    ) -> np.ndarray:
        """
        Build the 2D input vector expected by layer_1_complex_state.

        We keep this deterministic and non-zero even when bit_value = 0 to avoid
        degenerate all-zero trajectories.
        """
        d = self.dimension
        t = np.zeros(2 * d, dtype=float)

        tongue_index = TONGUE_NAMES.index(tongue)
        byte_norm = max(0.0, min(1.0, byte_value / 255.0))
        bit_norm = float(bit_value & 1)

        # Primary channel for this bit/tongue.
        amplitude = 0.15 + (0.70 * bit_norm) + (0.15 * byte_norm)
        t[tongue_index] = amplitude
        t[d + tongue_index] = TONGUE_PHASES[tongue] + ((bit_index + 1) / 8.0) * 0.05

        # Small neighboring channel encodes byte-position context.
        neighbor = (tongue_index + 1) % d
        t[neighbor] = 0.05 * byte_norm
        t[d + neighbor] = 0.01 * ((byte_index + bit_index) % 10)

        return t

    def dress_bit(
        self,
        *,
        byte_value: int,
        byte_index: int,
        bit_index: int,
        bit_position: int,
        bit_value: int,
    ) -> BitFingerprint:
        """Dress a single bit through L1-L5 and return a deterministic fingerprint."""
        clean_byte = int(byte_value) & 0xFF
        clean_bit = 1 if int(bit_value) else 0
        clean_byte_index = max(0, int(byte_index))
        clean_bit_index = max(0, int(bit_index))
        clean_bit_position = max(0, min(7, int(bit_position)))

        global_position = clean_byte_index * 8 + clean_bit_index
        tongue = TONGUE_NAMES[global_position % len(TONGUE_NAMES)]

        t = self._build_input_vector(
            byte_value=clean_byte,
            bit_value=clean_bit,
            byte_index=clean_byte_index,
            bit_index=clean_bit_index,
            tongue=tongue,
        )

        key_material = f"{self.key}|{clean_byte_index}|{clean_bit_index}|{clean_bit}|{clean_byte}"
        t_mod = layer_0_intent_modulation(t, key=key_material)

        l1_complex = layer_1_complex_state(t_mod, self.dimension)
        l2_real = layer_2_realification(l1_complex)
        l3_weighted = layer_3_weighted_transform(l2_real)
        l4_poincare = layer_4_poincare_embedding(l3_weighted)
        l5_distance = layer_5_hyperbolic_distance(l4_poincare, np.zeros_like(l4_poincare))

        fingerprint_material = [
            f"{clean_byte_index}:{clean_bit_index}:{clean_bit_position}:{clean_bit}:{tongue}",
            ",".join(f"{v:.8f}" for v in np.real(l1_complex)),
            ",".join(f"{v:.8f}" for v in np.imag(l1_complex)),
            ",".join(f"{v:.8f}" for v in l2_real),
            ",".join(f"{v:.8f}" for v in l3_weighted),
            ",".join(f"{v:.8f}" for v in l4_poincare),
            f"{l5_distance:.12f}",
        ]
        fingerprint_id = hashlib.sha256("|".join(fingerprint_material).encode("utf-8")).hexdigest()

        return BitFingerprint(
            byte_index=clean_byte_index,
            bit_index=clean_bit_index,
            bit_position=clean_bit_position,
            bit_value=clean_bit,
            tongue=tongue,
            layer_path=[1, 2, 3, 4, 5],
            complex_state_real=self._round_list(np.real(l1_complex)),
            complex_state_imag=self._round_list(np.imag(l1_complex)),
            real_state=self._round_list(l2_real),
            weighted_state=self._round_list(l3_weighted),
            poincare_pos=self._round_list(l4_poincare),
            hyperbolic_distance=round(float(l5_distance), 8),
            fingerprint_id=fingerprint_id,
        )

    def dress_byte(self, byte_value: int, *, byte_index: int = 0, msb_first: bool = True) -> List[BitFingerprint]:
        """Dress all 8 bits of one byte."""
        clean_byte = int(byte_value) & 0xFF
        bit_positions = list(range(7, -1, -1)) if msb_first else list(range(8))

        results: List[BitFingerprint] = []
        for bit_index, bit_position in enumerate(bit_positions):
            bit_value = (clean_byte >> bit_position) & 1
            results.append(
                self.dress_bit(
                    byte_value=clean_byte,
                    byte_index=byte_index,
                    bit_index=bit_index,
                    bit_position=bit_position,
                    bit_value=bit_value,
                )
            )
        return results

    def dress_bytes(self, data: bytes) -> List[BitFingerprint]:
        """Dress an arbitrary byte stream."""
        all_fingerprints: List[BitFingerprint] = []
        for byte_index, byte_value in enumerate(data):
            all_fingerprints.extend(self.dress_byte(byte_value, byte_index=byte_index))
        return all_fingerprints

    def hello_world(self, *, byte_value: int = 0x41) -> Dict[str, object]:
        """Minimal proof-of-concept report for one byte."""
        first = self.dress_byte(byte_value)
        second = self.dress_byte(byte_value)
        first_ids = [fp.fingerprint_id for fp in first]
        second_ids = [fp.fingerprint_id for fp in second]

        return {
            "byte_value": int(byte_value) & 0xFF,
            "fingerprint_count": len(first_ids),
            "unique_fingerprint_count": len(set(first_ids)),
            "deterministic_repeat": first_ids == second_ids,
            "layer_path": [1, 2, 3, 4, 5],
            "sample_fingerprint": first_ids[0] if first_ids else "",
        }
