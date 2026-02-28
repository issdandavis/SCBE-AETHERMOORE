"""
BraidedVoxelStore — Semantic Encoder
=====================================

Encodes raw bytes into Sacred Tongue semantic bits using
BitDresserF1 (bit-level fingerprinting) and TernaryHybridEncoder
(tongue classification + governance decision).

@layer Layer 1-5 (bit dressing), Layer 9, 12, 13 (hybrid encoder)
@component BraidedStorage.SemanticEncoder
"""

from __future__ import annotations

import hashlib
from typing import List, Optional

from src.braided_storage.types import SemanticBits
from src.geoseed.bit_dresser import BitDresserF1
from src.hybrid_encoder.types import EncoderInput
from src.hybrid_encoder.pipeline import TernaryHybridEncoder

TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Keyword heuristic for tongue classification when hybrid encoder
# is not needed (fallback for small/binary payloads)
_TONGUE_KEYWORDS = {
    "KO": ["fire", "attack", "force", "strike", "power", "destroy"],
    "AV": ["water", "flow", "adapt", "heal", "calm", "wave"],
    "RU": ["earth", "stone", "root", "build", "anchor", "stable"],
    "CA": ["compute", "calculate", "logic", "process", "analyze", "code"],
    "UM": ["dream", "vision", "imagine", "create", "design", "art"],
    "DR": ["shadow", "hide", "stealth", "secret", "encrypt", "dark"],
}


class SemanticEncoder:
    """Encodes raw content into Sacred Tongue semantic bits.

    Combines:
    - BitDresserF1 for bit-level L1-L5 fingerprinting
    - TernaryHybridEncoder for tongue classification + governance
    - SHA-256 content hashing
    - Keyword-based tongue fallback for non-text content
    """

    def __init__(
        self,
        *,
        dresser: Optional[BitDresserF1] = None,
        hybrid_encoder: Optional[TernaryHybridEncoder] = None,
        max_dress_bytes: int = 64,
    ):
        self._dresser = dresser or BitDresserF1()
        self._hybrid = hybrid_encoder or TernaryHybridEncoder(chemistry_threat_level=3)
        self._max_dress_bytes = max(1, max_dress_bytes)

    def encode(
        self,
        raw_bytes: bytes,
        mime_type: str = "application/octet-stream",
        tongue_hint: Optional[str] = None,
    ) -> SemanticBits:
        """Encode raw bytes into SemanticBits.

        Args:
            raw_bytes: Content to encode.
            mime_type: MIME type hint for routing.
            tongue_hint: Optional Sacred Tongue override.

        Returns:
            SemanticBits with tongue classification, fingerprints, etc.
        """
        data = bytes(raw_bytes or b"")
        content_hash = hashlib.sha256(data).hexdigest()

        # Bit-level fingerprinting (cap at max_dress_bytes for perf)
        dress_data = data[: self._max_dress_bytes]
        fingerprints = self._dresser.dress_bytes(dress_data) if dress_data else []
        fingerprint_ids = [fp.fingerprint_id for fp in fingerprints]

        # Determine if content is text-like
        is_text = mime_type.startswith("text/") or mime_type in (
            "application/json",
            "application/xml",
            "application/javascript",
        )

        # Use hybrid encoder for tongue classification + governance
        tongue_trits: List[int] = [0, 0, 0, 0, 0, 0]
        threat_score = 0.0
        governance_decision = "ALLOW"
        molecular_bonds = []

        if data:
            try:
                encoder_input = self._build_encoder_input(data, is_text, tongue_hint)
                result = self._hybrid.encode(encoder_input)
                tongue_trits = result.tongue_trits
                threat_score = result.threat_score
                governance_decision = result.decision
                molecular_bonds = result.molecular_bonds
            except Exception:
                # Fallback: keyword classification for text
                if is_text:
                    tongue_trits = self._keyword_classify(data)

        # Determine dominant tongue
        dominant_tongue = tongue_hint or self._dominant_from_trits(tongue_trits)

        return SemanticBits(
            dominant_tongue=dominant_tongue,
            tongue_trits=tongue_trits,
            fingerprint_ids=fingerprint_ids,
            sha256_hash=content_hash,
            threat_score=threat_score,
            governance_decision=governance_decision,
            molecular_bonds=molecular_bonds,
        )

    def _build_encoder_input(
        self,
        data: bytes,
        is_text: bool,
        tongue_hint: Optional[str],
    ) -> EncoderInput:
        """Build an EncoderInput from raw bytes."""
        if is_text:
            text = data.decode("utf-8", errors="replace")
            # Check if it looks like code
            code_indicators = ("def ", "class ", "import ", "function ", "const ", "var ", "{", "}")
            if any(ind in text for ind in code_indicators):
                return EncoderInput(code_text=text, tongue_hint=tongue_hint)
            # Use raw_signal from text length as a simple signal
            return EncoderInput(raw_signal=float(len(text)), tongue_hint=tongue_hint)

        # Binary: use byte entropy as signal
        if data:
            byte_set = set(data[:256])
            entropy_proxy = len(byte_set) / 256.0
            return EncoderInput(raw_signal=entropy_proxy, tongue_hint=tongue_hint)

        return EncoderInput(raw_signal=0.0, tongue_hint=tongue_hint)

    @staticmethod
    def _keyword_classify(data: bytes) -> List[int]:
        """Fallback tongue classification via keyword matching."""
        text = data.decode("utf-8", errors="replace").lower()
        scores = []
        for tongue in TONGUE_NAMES:
            keywords = _TONGUE_KEYWORDS.get(tongue, [])
            count = sum(1 for kw in keywords if kw in text)
            scores.append(count)

        if max(scores) == 0:
            return [0, 0, 0, 0, 0, 0]

        # Convert to trits: +1 for max, -1 for min, 0 otherwise
        max_score = max(scores)
        trits = []
        for s in scores:
            if s == max_score and s > 0:
                trits.append(1)
            elif s == 0 and max_score > 0:
                trits.append(-1)
            else:
                trits.append(0)
        return trits

    @staticmethod
    def _dominant_from_trits(trits: List[int]) -> str:
        """Pick the dominant tongue from trit values."""
        if not trits:
            return "KO"
        max_val = -2
        max_idx = 0
        for i, t in enumerate(trits):
            if t > max_val:
                max_val = t
                max_idx = i
        if max_idx < len(TONGUE_NAMES):
            return TONGUE_NAMES[max_idx]
        return "KO"
