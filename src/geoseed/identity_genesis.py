"""
GeoSeed Identity Genesis (F3)
=============================

Creates deterministic Sacred Egg-style birth identities for agents.
This is a lightweight, local implementation for origin fingerprinting
and verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import List, Sequence

import numpy as np

from src.geoseed.sphere_grid import TONGUE_NAMES


@dataclass(frozen=True)
class SacredIdentity:
    """Deterministic identity packet produced at agent birth."""

    agent_name: str
    egg_id: str
    origin_tongue: str
    origin_coords_6d: List[float]
    traversal_seed: str
    fingerprint_id: str
    created_at_utc: str


class IdentityGenesis:
    """Create and verify Sacred Egg-style origin identities."""

    def __init__(self, *, secret: str = "geoseed_identity_v1"):
        self.secret = str(secret)

    @staticmethod
    def _normalize_tongues(requested_tongues: Sequence[str] | None) -> List[str]:
        if not requested_tongues:
            return []
        normalized: List[str] = []
        for tongue in requested_tongues:
            clean = str(tongue).upper().strip()
            if clean in TONGUE_NAMES and clean not in normalized:
                normalized.append(clean)
        return normalized

    @staticmethod
    def _coords_from_digest(digest: bytes) -> List[float]:
        raw = np.array([((digest[i] / 255.0) * 2.0) - 1.0 for i in range(6)], dtype=float)
        # Keep coordinates in a stable bounded radius.
        coords = np.tanh(raw * 1.2) * 0.85
        return [round(float(v), 6) for v in coords.tolist()]

    @staticmethod
    def _fingerprint_material(
        *,
        agent_name: str,
        egg_id: str,
        origin_tongue: str,
        origin_coords_6d: Sequence[float],
        traversal_seed: str,
    ) -> str:
        coord_blob = ",".join(f"{float(v):.8f}" for v in origin_coords_6d)
        return f"{agent_name}|{egg_id}|{origin_tongue}|{coord_blob}|{traversal_seed}"

    def create_identity(
        self,
        *,
        agent_name: str,
        payload: bytes | None = None,
        requested_tongues: Sequence[str] | None = None,
    ) -> SacredIdentity:
        clean_name = (agent_name or "unnamed-agent").strip() or "unnamed-agent"
        clean_tongues = self._normalize_tongues(requested_tongues)

        payload_bytes = payload if payload is not None else clean_name.encode("utf-8")
        tongue_blob = ",".join(clean_tongues) if clean_tongues else "-"
        seed_material = b"|".join(
            [
                self.secret.encode("utf-8"),
                clean_name.encode("utf-8"),
                tongue_blob.encode("utf-8"),
                payload_bytes,
            ]
        )
        digest = hashlib.sha256(seed_material).digest()

        origin_tongue = clean_tongues[0] if clean_tongues else TONGUE_NAMES[digest[0] % len(TONGUE_NAMES)]
        origin_coords_6d = self._coords_from_digest(digest)
        traversal_seed = hashlib.sha256((digest.hex() + origin_tongue).encode("utf-8")).hexdigest()[:16]
        egg_id = f"egg-{digest.hex()[:12]}"

        fp_material = self._fingerprint_material(
            agent_name=clean_name,
            egg_id=egg_id,
            origin_tongue=origin_tongue,
            origin_coords_6d=origin_coords_6d,
            traversal_seed=traversal_seed,
        )
        fingerprint_id = hashlib.sha256(fp_material.encode("utf-8")).hexdigest()

        return SacredIdentity(
            agent_name=clean_name,
            egg_id=egg_id,
            origin_tongue=origin_tongue,
            origin_coords_6d=origin_coords_6d,
            traversal_seed=traversal_seed,
            fingerprint_id=fingerprint_id,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def verify_identity(self, identity: SacredIdentity) -> bool:
        material = self._fingerprint_material(
            agent_name=identity.agent_name,
            egg_id=identity.egg_id,
            origin_tongue=identity.origin_tongue,
            origin_coords_6d=identity.origin_coords_6d,
            traversal_seed=identity.traversal_seed,
        )
        expected = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return expected == identity.fingerprint_id
