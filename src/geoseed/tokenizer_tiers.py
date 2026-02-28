"""
GeoSeed Tokenizer Tiers
=======================

Three-tier dispatch:
- F1: raw binary training data (bit-level L1-L5 dressing)
- F2: public interop tokenizer streams (token-level dressing)
- F3: Sacred Egg identity genesis
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Sequence

from src.geoseed.bit_dresser import BitDresserF1, BitFingerprint
from src.geoseed.dressing import BitDresser, DressedBit
from src.geoseed.identity_genesis import IdentityGenesis, SacredIdentity


class TokenizerTier(str, Enum):
    F1 = "f1_training"
    F2 = "f2_public"
    F3 = "f3_genesis"


@dataclass
class TierEncodingResult:
    tier: TokenizerTier
    item_count: int
    payload: Any
    metadata: Dict[str, Any]


class GeoSeedTokenizerTiers:
    """High-level tier dispatcher for GeoSeed tokenization flows."""

    def __init__(
        self,
        *,
        f1_dresser: BitDresserF1 | None = None,
        f2_dresser: BitDresser | None = None,
        identity_genesis: IdentityGenesis | None = None,
    ):
        self.f1_dresser = f1_dresser or BitDresserF1()
        self.f2_dresser = f2_dresser or BitDresser(layer_count=14)
        self.identity_genesis = identity_genesis or IdentityGenesis()

    @staticmethod
    def _normalize_tokens_by_tongue(tokens_by_tongue: Mapping[str, Sequence[str]] | None) -> Dict[str, Sequence[str]]:
        if not tokens_by_tongue:
            return {}
        normalized: Dict[str, Sequence[str]] = {}
        for tongue, tokens in tokens_by_tongue.items():
            clean_tongue = str(tongue).upper().strip()
            clean_tokens = [str(t) for t in tokens if str(t).strip()]
            if clean_tokens:
                normalized[clean_tongue] = clean_tokens
        return normalized

    def encode_f1_training(self, data: bytes) -> list[BitFingerprint]:
        clean_data = bytes(data or b"")
        return self.f1_dresser.dress_bytes(clean_data)

    def encode_f2_public(
        self,
        *,
        tokens_by_tongue: Mapping[str, Sequence[str]],
        run_id: str = "f2-public",
    ) -> list[DressedBit]:
        clean = self._normalize_tokens_by_tongue(tokens_by_tongue)
        return self.f2_dresser.dress_tokens(clean, run_id=run_id)

    def encode_f3_birth_identity(
        self,
        *,
        agent_name: str,
        payload: bytes | None = None,
        requested_tongues: Sequence[str] | None = None,
    ) -> SacredIdentity:
        return self.identity_genesis.create_identity(
            agent_name=agent_name,
            payload=payload,
            requested_tongues=requested_tongues,
        )

    def encode(
        self,
        tier: TokenizerTier,
        *,
        data: bytes | None = None,
        tokens_by_tongue: Mapping[str, Sequence[str]] | None = None,
        run_id: str = "tier-run",
        agent_name: str | None = None,
        payload: bytes | None = None,
        requested_tongues: Sequence[str] | None = None,
    ) -> TierEncodingResult:
        if tier == TokenizerTier.F1:
            fingerprints = self.encode_f1_training(data or b"")
            return TierEncodingResult(
                tier=tier,
                item_count=len(fingerprints),
                payload=fingerprints,
                metadata={"mode": "bit-level", "layer_path": [1, 2, 3, 4, 5]},
            )

        if tier == TokenizerTier.F2:
            dressed = self.encode_f2_public(tokens_by_tongue=tokens_by_tongue or {}, run_id=run_id)
            return TierEncodingResult(
                tier=tier,
                item_count=len(dressed),
                payload=dressed,
                metadata={"mode": "token-level", "run_id": run_id, "layer_count": 14},
            )

        if tier == TokenizerTier.F3:
            identity = self.encode_f3_birth_identity(
                agent_name=agent_name or "unnamed-agent",
                payload=payload,
                requested_tongues=requested_tongues,
            )
            return TierEncodingResult(
                tier=tier,
                item_count=1,
                payload=identity,
                metadata={"mode": "identity-genesis", "egg_id": identity.egg_id},
            )

        raise ValueError(f"unsupported tier: {tier}")
