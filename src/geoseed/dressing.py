"""
GeoSeed Bit Dressing
====================

Deterministic token-to-bit dressing through the SCBE 14-layer stack.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Dict, Iterable, List, Mapping, Sequence

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]


@dataclass(frozen=True)
class DressedBit:
    """A token-derived bit with layer and semantic context."""

    token: str
    tongue: str
    bit_value: int
    bit_index: int
    layer_path: List[int]
    state21d: List[float]
    run_id: str


class BitDresser:
    """Create deterministic dressed bits from tongue-token streams."""

    def __init__(self, layer_count: int = 14):
        self.layer_count = max(1, int(layer_count))

    @staticmethod
    def _state21d_from_digest(digest: bytes) -> List[float]:
        # 21 signed values in [-1, 1], deterministic from SHA-256 bytes.
        dims: List[float] = []
        for i in range(21):
            b = digest[i % len(digest)]
            dims.append(round(-1.0 + 2.0 * (b / 255.0), 6))
        return dims

    def dress_tokens(
        self,
        tokens_by_tongue: Mapping[str, Sequence[str]],
        *,
        run_id: str = "m6-run",
    ) -> List[DressedBit]:
        dressed: List[DressedBit] = []

        for tongue in TONGUES:
            tokens = tokens_by_tongue.get(tongue, [])
            for idx, token in enumerate(tokens):
                material = f"{run_id}|{tongue}|{idx}|{token}".encode("utf-8")
                digest = hashlib.sha256(material).digest()
                bit_value = digest[0] & 1
                dressed.append(
                    DressedBit(
                        token=token,
                        tongue=tongue,
                        bit_value=bit_value,
                        bit_index=idx,
                        layer_path=list(range(1, self.layer_count + 1)),
                        state21d=self._state21d_from_digest(digest),
                        run_id=run_id,
                    )
                )

        return dressed

    def dress_text(
        self,
        text: str,
        *,
        tongue: str = "KO",
        run_id: str = "m6-run",
    ) -> List[DressedBit]:
        clean_tongue = (tongue or "KO").upper()
        if clean_tongue not in TONGUES:
            clean_tongue = "KO"
        tokens = [t for t in str(text or "").split() if t]
        return self.dress_tokens({clean_tongue: tokens}, run_id=run_id)
