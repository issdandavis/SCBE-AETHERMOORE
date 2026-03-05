"""
Quasi-Crystal Voxel Storage Drive - 6D Sparse Tensor Arrays

This module fuses:
- 6D quasi-crystal projection (3D physical + 3D perpendicular windows)
- Cymatic/Chladni access gating from 6D vectors
- Sacred Tongues weighting and phase-state routing
- Fail-closed retrieval verification using stored content hash

The drive is sparse: only touched 6D tensor coordinates are materialized.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

try:
    import qutip as qt  # type: ignore

    _QUTIP_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    qt = None
    _QUTIP_AVAILABLE = False

PHI = float((1 + np.sqrt(5)) / 2)
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI**i for i in range(6)]

# Lower value means higher flow.
TONGUE_VISCOSITY = {
    "KO": 1 / (1 + 1.00 * PHI),
    "AV": 1 / (1 + 0.80 * PHI),
    "RU": 1 / (1 + 0.30 * PHI),
    "CA": 1 / (1 + 0.40 * PHI),
    "UM": 0.50,
    "DR": 0.50,
}

RETENTION_POLICIES = {
    "default": timedelta(days=30),
    "ephemeral": timedelta(hours=1),
    "persistent": timedelta(days=365),
    "compliance": timedelta(days=2555),  # 7 years
}

TIER_LABELS = {0: "hot", 1: "warm", 2: "cold"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class VoxelCell:
    """A single occupied cell in the 6D sparse tensor."""

    cell_id: str
    tongue_index: List[int]  # 6D tensor index
    tongue_coords: List[float]  # 6D normalized coordinates in [-1, 1]
    physical_projection: List[float]  # 3D
    perpendicular_projection: List[float]  # 3D
    chladni_mode: Tuple[int, int]
    content_hash: str
    content_size: int
    category: str
    depth: int = 0
    parent_id: str = ""
    children: List[str] = field(default_factory=list)
    phase: str = "laminar"  # laminar | turbulent | emulsion
    viscosity: float = 0.5
    is_valid: bool = True
    created_at_utc: str = ""
    expires_at_utc: str = ""
    storage_tier: int = 1
    stored_phason_epoch: int = 0
    cipher_scheme: str = "xor-v1"


@dataclass
class TensorSlab:
    """A sparse slab focused on one dominant Sacred Tongue."""

    tongue: str
    tongue_index: int
    cells: Dict[str, VoxelCell]
    total_content_bytes: int = 0
    phase_state: str = "laminar"


class QuasiCrystalVoxelDrive:
    """
    6D sparse tensor storage with quasicrystal + cymatic access gating.

    Fail-closed principles:
    - Invalid 6D placements can be rejected on write.
    - Retrieval returns None unless hash verification succeeds (strict mode).
    - Expired cells are treated as absent.
    """

    def __init__(
        self,
        resolution: int = 64,
        lattice_constant: float = 1.0,
        default_retention_policy: str = "default",
    ) -> None:
        if not isinstance(resolution, int) or resolution <= 1:
            raise ValueError("resolution must be an integer > 1")
        if lattice_constant <= 0:
            raise ValueError("lattice_constant must be > 0")
        if default_retention_policy not in RETENTION_POLICIES:
            raise ValueError(f"unknown retention policy: {default_retention_policy}")

        self.resolution = resolution
        self.lattice_constant = float(lattice_constant)
        self.default_retention_policy = default_retention_policy

        # 6D -> 3D projection matrices with icosahedral symmetry.
        self.M_par, self.M_perp = self._build_projection_matrices()
        self.acceptance_radius = 1.5 * self.lattice_constant
        self._phason_strain = np.zeros(3, dtype=float)
        self._phason_epoch = 0

        self.cells: Dict[str, VoxelCell] = {}
        self.tensor_slabs: Dict[str, TensorSlab] = {
            name: TensorSlab(tongue=name, tongue_index=i, cells={})
            for i, name in enumerate(TONGUE_NAMES)
        }
        self.depth_trees: Dict[str, List[str]] = {}

        # Sparse tensor index map: (i0..i5) -> [cell_id...]
        self.tensor_index_map: Dict[Tuple[int, int, int, int, int, int], List[str]] = {}

        # Backward-compatible blob map:
        # - legacy: bytes (xor-v1)
        # - new: dict envelope (aead-v1)
        self.content_store: Dict[str, Any] = {}
        self.tier_content_store: Dict[int, Dict[str, Any]] = {0: {}, 1: {}, 2: {}}

        # category -> preferred phase
        self.phase_map: Dict[str, str] = {}

        # Storage metrics for monitoring exports.
        self._metrics: Dict[str, int] = {
            "storage_size_bytes": 0,
            "memory_count": 0,
            "expired_total": 0,
        }

        # Runtime master key for AEAD wraps.
        self._aead_master_key = hashlib.sha256(
            f"qc-voxel-drive:{self.resolution}:{self.lattice_constant}".encode("utf-8")
        ).digest()

    @property
    def phason_epoch(self) -> int:
        return self._phason_epoch

    @property
    def phason_strain(self) -> np.ndarray:
        return self._phason_strain.copy()

    def _build_projection_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        norm = 1 / np.sqrt(1 + PHI**2)
        e_par = (
            np.array(
                [
                    [1, PHI, 0],
                    [-1, PHI, 0],
                    [0, 1, PHI],
                    [0, -1, PHI],
                    [PHI, 0, 1],
                    [PHI, 0, -1],
                ],
                dtype=float,
            ).T
            * norm
        )
        e_perp = (
            np.array(
                [
                    [1, -1 / PHI, 0],
                    [-1, -1 / PHI, 0],
                    [0, 1, -1 / PHI],
                    [0, -1, -1 / PHI],
                    [-1 / PHI, 0, 1],
                    [-1 / PHI, 0, -1],
                ],
                dtype=float,
            ).T
            * norm
        )
        return e_par, e_perp

    def _validate_coords(self, coords: List[float]) -> List[float]:
        if len(coords) != 6:
            raise ValueError(f"tongue_coords must have length 6, got {len(coords)}")
        if not all(np.isfinite(coords)):
            raise ValueError("tongue_coords must be finite numbers")
        # Normalize into bounded 6D range for deterministic tensor indexing.
        return [float(np.tanh(c)) for c in coords]

    def _project_6d(self, coords: List[float]) -> Tuple[List[float], List[float]]:
        n = np.array(coords, dtype=float)
        r_phys = (self.M_par @ n).tolist()
        r_perp = (self.M_perp @ n).tolist()
        return r_phys, r_perp

    def _coords_to_chladni(self, coords: List[float]) -> Tuple[int, int]:
        # Velocity axes: KO/AV/RU. Security axes: CA/UM/DR.
        vel = np.linalg.norm(coords[:3])
        sec = np.linalg.norm(coords[3:])
        n = max(1, int(vel * 10) % 20 + 1)
        m = max(1, int(sec * 10) % 20 + 1)
        if n == m:
            m += 1
        return (n, m)

    def _legacy_chladni_xor(self, data: bytes, n: int, m: int, phason_epoch: Optional[int] = None) -> bytes:
        # Stateless stream generation tied to mode and phason epoch.
        epoch = self._phason_epoch if phason_epoch is None else int(phason_epoch)
        seed = hashlib.sha256(f"chladni:{n}:{m}:{epoch}".encode("utf-8")).digest()
        key_stream = bytearray()
        block = seed
        while len(key_stream) < len(data):
            block = hashlib.sha256(block).digest()
            key_stream.extend(block)
        return bytes(d ^ k for d, k in zip(data, key_stream[: len(data)]))

    def _route_tier(self, dominant_tongue: str, phase: str) -> int:
        token = f"{dominant_tongue}:{phase}:{self._phason_epoch}"
        return int(hashlib.sha256(token.encode("utf-8")).digest()[0] % len(TIER_LABELS))

    def _derive_cell_key(self, chunk_id: str, stored_phason_epoch: int, tier: int) -> bytes:
        return hashlib.sha256(
            self._aead_master_key + f"{chunk_id}:{stored_phason_epoch}:{tier}".encode("utf-8")
        ).digest()

    @staticmethod
    def _chladni_aad(n: int, m: int) -> bytes:
        return f"chladni:{n}:{m}".encode("utf-8")

    def _aead_encrypt(self, plaintext: bytes, *, chunk_id: str, n: int, m: int, tier: int, epoch: int) -> Dict[str, Any]:
        key = self._derive_cell_key(chunk_id=chunk_id, stored_phason_epoch=epoch, tier=tier)
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(key)
        ciphertext = cipher.encrypt(nonce, plaintext, self._chladni_aad(n, m))
        return {
            "scheme": "aead-v1",
            "ciphertext": ciphertext,
            "nonce": nonce,
            "tier": tier,
            "stored_phason_epoch": epoch,
        }

    def _aead_decrypt(self, envelope: Dict[str, Any], *, chunk_id: str, n: int, m: int) -> Optional[bytes]:
        try:
            key = self._derive_cell_key(
                chunk_id=chunk_id,
                stored_phason_epoch=int(envelope.get("stored_phason_epoch", self._phason_epoch)),
                tier=int(envelope.get("tier", 1)),
            )
            cipher = ChaCha20Poly1305(key)
            nonce = envelope["nonce"]
            ciphertext = envelope["ciphertext"]
            return cipher.decrypt(nonce, ciphertext, self._chladni_aad(n, m))
        except (InvalidTag, KeyError, TypeError, ValueError):
            return None

    def _blob_size_bytes(self, blob: Any) -> int:
        if isinstance(blob, bytes):
            return len(blob)
        if isinstance(blob, dict):
            total = 0
            for key in ("ciphertext", "nonce"):
                val = blob.get(key)
                if isinstance(val, (bytes, bytearray)):
                    total += len(val)
            return total
        return 0

    def _update_metrics(self) -> None:
        size = 0
        for tier_bucket in self.tier_content_store.values():
            for blob in tier_bucket.values():
                size += self._blob_size_bytes(blob)
        self._metrics["storage_size_bytes"] = size
        self._metrics["memory_count"] = len(self.cells)

    def _apply_harmonic_modifier(self, coords: List[float], spin_coherence: Optional[List[float]]) -> List[float]:
        if not spin_coherence:
            return coords

        vec = np.array(spin_coherence[:6], dtype=float)
        if vec.size < 6:
            vec = np.pad(vec, (0, 6 - vec.size), mode="constant")
        norm = float(np.linalg.norm(vec))
        if norm == 0:
            return coords
        vec = vec / norm

        if _QUTIP_AVAILABLE and qt is not None:
            # Layer-12 style hook: derive a bounded coherence signal from a simple qubit Hamiltonian.
            hx = float(vec[0])
            hz = float(vec[1])
            H = hx * qt.sigmax() + hz * qt.sigmaz()
            result = qt.mesolve(H, qt.basis(2, 0), [0, 0.5, 1.0], [])
            psi = result.states[-1]
            coherence = abs(complex(psi.full()[0, 0]))
        else:
            coherence = float((np.dot(vec[:3], vec[3:6]) + 1.0) / 2.0)

        modifier = 1.0 + (coherence - 0.5) * 0.2  # bounded to +/-10%
        return [float(np.tanh(c * modifier)) for c in coords]

    def _dominant_tongue(self, coords: List[float]) -> Tuple[str, int, float]:
        weighted = [abs(c) * w for c, w in zip(coords, TONGUE_WEIGHTS)]
        dom_idx = weighted.index(max(weighted))
        dom_name = TONGUE_NAMES[dom_idx]
        return dom_name, dom_idx, TONGUE_VISCOSITY[dom_name]

    def _tensor_index(self, coords: List[float]) -> List[int]:
        out: List[int] = []
        for c in coords:
            idx = int(((c + 1.0) / 2.0) * (self.resolution - 1))
            out.append(max(0, min(self.resolution - 1, idx)))
        return out

    def _determine_phase(self, category: str, viscosity: float, dominant_tongue: str) -> str:
        # UM/DR are explicit emulsifier tongues in the design notes.
        if dominant_tongue in {"UM", "DR"}:
            return "emulsion"

        existing = self.phase_map.get(category)
        if existing:
            return existing

        if viscosity > 0.55:
            phase = "laminar"
        elif viscosity < 0.35 and len(self.cells) > 64:
            phase = "turbulent"
        else:
            phase = "laminar"

        self.phase_map[category] = phase
        return phase

    def _get_depth(self, cell_id: str) -> int:
        cell = self.cells.get(cell_id)
        return cell.depth if cell else 0

    def _get_expiry(self, retention_policy: str, ttl_seconds: Optional[int]) -> datetime:
        now = _utc_now()
        if ttl_seconds is not None:
            if ttl_seconds <= 0:
                raise ValueError("ttl_seconds must be > 0")
            return now + timedelta(seconds=ttl_seconds)
        if retention_policy not in RETENTION_POLICIES:
            raise ValueError(f"unknown retention policy: {retention_policy}")
        return now + RETENTION_POLICIES[retention_policy]

    def store(
        self,
        chunk_id: str,
        content: bytes,
        tongue_coords: List[float],
        category: str = "general",
        parent_id: str = "",
        retention_policy: str = "default",
        ttl_seconds: Optional[int] = None,
        fail_closed: bool = True,
        spin_coherence: Optional[List[float]] = None,
    ) -> VoxelCell:
        """
        Store content under a 6D tongue coordinate.

        If fail_closed=True, invalid quasicrystal window placement raises.
        """
        if not chunk_id.strip():
            raise ValueError("chunk_id must not be empty")
        if not isinstance(content, (bytes, bytearray)) or len(content) == 0:
            raise ValueError("content must be non-empty bytes")

        coords = self._validate_coords(tongue_coords)
        coords = self._apply_harmonic_modifier(coords, spin_coherence)
        phys, perp = self._project_6d(coords)
        n, m = self._coords_to_chladni(coords)
        t_index = self._tensor_index(coords)

        dominant_tongue, _, viscosity = self._dominant_tongue(coords)
        phase = self._determine_phase(category=category, viscosity=viscosity, dominant_tongue=dominant_tongue)
        storage_tier = self._route_tier(dominant_tongue=dominant_tongue, phase=phase)

        r_perp = np.array(perp, dtype=float)
        distance = float(np.linalg.norm(r_perp - self._phason_strain))
        is_valid = distance < self.acceptance_radius
        if fail_closed and not is_valid:
            raise PermissionError(
                f"QUARANTINE: chunk '{chunk_id}' outside acceptance window at phason_epoch={self._phason_epoch}"
            )

        now = _utc_now()
        expires_at = self._get_expiry(retention_policy=retention_policy, ttl_seconds=ttl_seconds)
        content_hash = hashlib.sha256(bytes(content)).hexdigest()

        depth = 0 if not parent_id else self._get_depth(parent_id) + 1
        cell = VoxelCell(
            cell_id=chunk_id,
            tongue_index=t_index,
            tongue_coords=coords,
            physical_projection=phys,
            perpendicular_projection=perp,
            chladni_mode=(n, m),
            content_hash=content_hash,
            content_size=len(content),
            category=category,
            depth=depth,
            parent_id=parent_id,
            phase=phase,
            viscosity=viscosity,
            is_valid=is_valid,
            created_at_utc=_utc_iso(now),
            expires_at_utc=_utc_iso(expires_at),
            storage_tier=storage_tier,
            stored_phason_epoch=self._phason_epoch,
            cipher_scheme="aead-v1",
        )

        encoded = self._aead_encrypt(
            bytes(content),
            chunk_id=chunk_id,
            n=n,
            m=m,
            tier=storage_tier,
            epoch=self._phason_epoch,
        )

        self.cells[chunk_id] = cell
        self.content_store[chunk_id] = encoded
        self.tier_content_store[storage_tier][chunk_id] = encoded
        self.tensor_slabs[dominant_tongue].cells[chunk_id] = cell
        self.tensor_slabs[dominant_tongue].total_content_bytes += len(content)

        index_key = tuple(t_index)
        self.tensor_index_map.setdefault(index_key, []).append(chunk_id)

        if parent_id and parent_id in self.cells:
            self.cells[parent_id].children.append(chunk_id)
            self.depth_trees.setdefault(parent_id, []).append(chunk_id)

        self._update_metrics()
        return cell

    def retrieve(
        self,
        chunk_id: str,
        access_coords: List[float],
        strict: bool = True,
        spin_coherence: Optional[List[float]] = None,
    ) -> Optional[bytes]:
        """
        Retrieve content with a 6D access vector.

        strict=True:
          - verify decoded hash matches stored hash
          - return None on mismatch or expiry
        """
        cell = self.cells.get(chunk_id)
        blob = self.content_store.get(chunk_id)
        if cell is None or blob is None:
            return None

        # Expired cells are fail-closed hidden.
        if datetime.strptime(cell.expires_at_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) < _utc_now():
            self._remove_cell(chunk_id, expired=True)
            return None

        coords = self._validate_coords(access_coords)
        coords = self._apply_harmonic_modifier(coords, spin_coherence)
        n, m = self._coords_to_chladni(coords)
        decoded: Optional[bytes] = None
        if isinstance(blob, dict) and blob.get("scheme") == "aead-v1":
            decoded = self._aead_decrypt(blob, chunk_id=chunk_id, n=n, m=m)
        elif isinstance(blob, bytes):
            # Legacy XOR compatibility.
            decoded = self._legacy_chladni_xor(blob, n, m, phason_epoch=cell.stored_phason_epoch)
        elif isinstance(blob, dict) and blob.get("scheme") == "xor-v1":
            payload = blob.get("ciphertext")
            if isinstance(payload, (bytes, bytearray)):
                decoded = self._legacy_chladni_xor(
                    bytes(payload), n, m, phason_epoch=int(blob.get("stored_phason_epoch", self._phason_epoch))
                )

        if decoded is None:
            return None

        if strict:
            decoded_hash = hashlib.sha256(decoded).hexdigest()
            if decoded_hash != cell.content_hash:
                return None

        return decoded

    def phason_rekey(self, entropy: bytes) -> np.ndarray:
        """Apply phason shift to rotate the acceptance window."""
        h = hashlib.sha256(entropy).digest()
        self._phason_strain = np.array(
            [
                int.from_bytes(h[0:4], "big") / (2**32) * 2 - 1,
                int.from_bytes(h[4:8], "big") / (2**32) * 2 - 1,
                int.from_bytes(h[8:12], "big") / (2**32) * 2 - 1,
            ],
            dtype=float,
        ) * self.acceptance_radius * 2.0
        self._phason_epoch += 1
        return self._phason_strain.copy()

    def _remove_cell(self, cell_id: str, *, expired: bool = False) -> None:
        cell = self.cells.pop(cell_id, None)
        blob = self.content_store.pop(cell_id, None)
        if cell is None:
            return

        if blob is not None:
            tier = cell.storage_tier if cell.storage_tier in self.tier_content_store else 1
            self.tier_content_store[tier].pop(cell_id, None)
        if expired:
            self._metrics["expired_total"] += 1

        index_key = tuple(cell.tongue_index)
        ids = self.tensor_index_map.get(index_key, [])
        if cell_id in ids:
            ids.remove(cell_id)
            if not ids:
                self.tensor_index_map.pop(index_key, None)

        tongue = self._dominant_tongue(cell.tongue_coords)[0]
        self.tensor_slabs[tongue].cells.pop(cell_id, None)
        self.tensor_slabs[tongue].total_content_bytes = max(
            0, self.tensor_slabs[tongue].total_content_bytes - int(cell.content_size)
        )

        if cell.parent_id and cell.parent_id in self.depth_trees:
            descendants = self.depth_trees[cell.parent_id]
            if cell_id in descendants:
                descendants.remove(cell_id)
        if cell.parent_id and cell.parent_id in self.cells:
            parent_children = self.cells[cell.parent_id].children
            if cell_id in parent_children:
                parent_children.remove(cell_id)

        self._update_metrics()

    def cleanup_expired(self) -> int:
        """Drop expired cells from all indices and return removed count."""
        now = _utc_now()
        to_remove: List[str] = []
        for cell_id, cell in self.cells.items():
            expires_at = datetime.strptime(cell.expires_at_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            if expires_at < now:
                to_remove.append(cell_id)

        for cell_id in to_remove:
            self._remove_cell(cell_id, expired=True)

        return len(to_remove)

    def get_slab(self, tongue: str) -> Dict[str, object]:
        slab = self.tensor_slabs.get(tongue)
        if not slab:
            return {}
        return {
            "tongue": slab.tongue,
            "total_cells": len(slab.cells),
            "total_bytes": slab.total_content_bytes,
            "phase_state": slab.phase_state,
            "cells": list(slab.cells.keys()),
        }

    def query_nearby(self, coords: List[float], radius: float = 0.3) -> List[str]:
        q = self._validate_coords(coords)
        results: List[Tuple[str, float]] = []
        weight_sum = float(sum(TONGUE_WEIGHTS))
        for cell_id, cell in self.cells.items():
            dist = math.sqrt(
                sum((a - b) ** 2 * w for a, b, w in zip(q, cell.tongue_coords, TONGUE_WEIGHTS))
            ) / weight_sum
            if dist < radius:
                results.append((cell_id, dist))
        results.sort(key=lambda x: x[1])
        return [cell_id for cell_id, _ in results]

    @staticmethod
    def _chladni_mode_similarity(mode_a: Tuple[int, int], mode_b: Tuple[int, int]) -> float:
        # 1.0 is identical. Values near 1.0 are near-collision candidates.
        va = np.array([mode_a[0], mode_a[1]], dtype=float)
        vb = np.array([mode_b[0], mode_b[1]], dtype=float)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def red_team_probe_near_collision(
        self,
        chunk_id: str,
        access_coords: List[float],
        *,
        attempts: int = 64,
        similarity_min: float = 0.985,
        noise_scale: float = 0.04,
    ) -> Dict[str, Any]:
        cell = self.cells.get(chunk_id)
        if cell is None:
            return {
                "chunk_id": chunk_id,
                "attempts": 0,
                "near_collision_attempts": 0,
                "unexpected_accepts": 0,
                "max_similarity": 0.0,
                "status": "missing",
            }

        base_coords = self._validate_coords(access_coords)
        base_mode = self._coords_to_chladni(base_coords)
        near_collision_attempts = 0
        unexpected_accepts = 0
        max_similarity = 0.0

        for _ in range(max(1, attempts)):
            candidate = np.array(base_coords, dtype=float) + np.random.normal(0, noise_scale, 6)
            candidate_coords = [float(np.tanh(c)) for c in candidate.tolist()]
            cand_mode = self._coords_to_chladni(candidate_coords)
            if cand_mode == base_mode:
                continue
            similarity = self._chladni_mode_similarity(base_mode, cand_mode)
            if similarity < similarity_min:
                continue
            near_collision_attempts += 1
            max_similarity = max(max_similarity, similarity)
            if self.retrieve(chunk_id, candidate_coords, strict=True) is not None:
                unexpected_accepts += 1

        return {
            "chunk_id": chunk_id,
            "attempts": attempts,
            "near_collision_attempts": near_collision_attempts,
            "unexpected_accepts": unexpected_accepts,
            "max_similarity": round(max_similarity, 6),
            "status": "ok" if unexpected_accepts == 0 else "alert",
        }

    def metrics(self) -> Dict[str, int]:
        self._update_metrics()
        return dict(self._metrics)

    def export_metrics(self, path: Optional[str] = None) -> Dict[str, int]:
        payload = self.metrics()
        if path:
            out = Path(path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def stats(self) -> Dict[str, object]:
        categories: Dict[str, int] = {}
        phase_distribution: Dict[str, int] = {}
        for cell in self.cells.values():
            categories[cell.category] = categories.get(cell.category, 0) + 1
            phase_distribution[cell.phase] = phase_distribution.get(cell.phase, 0) + 1

        return {
            "total_cells": len(self.cells),
            "total_content_bytes": sum(c.content_size for c in self.cells.values()),
            "phason_epoch": self._phason_epoch,
            "resolution": self.resolution,
            "sparse_tensor_slots": len(self.tensor_index_map),
            "slabs": {
                name: {"cells": len(slab.cells), "bytes": slab.total_content_bytes}
                for name, slab in self.tensor_slabs.items()
            },
            "categories": categories,
            "max_depth": max((c.depth for c in self.cells.values()), default=0),
            "phase_distribution": phase_distribution,
            "tiers": {
                TIER_LABELS[tier]: len(bucket) for tier, bucket in self.tier_content_store.items()
            },
            "metrics": self.metrics(),
        }

    def export(self, path: str) -> str:
        data = {
            "drive_type": "QuasiCrystalVoxelDrive",
            "dimensions": 6,
            "phason_epoch": self._phason_epoch,
            "phason_strain": self._phason_strain.tolist(),
            "tongue_names": TONGUE_NAMES,
            "tongue_weights": [float(w) for w in TONGUE_WEIGHTS],
            "tongue_viscosity": TONGUE_VISCOSITY,
            "resolution": self.resolution,
            "total_cells": len(self.cells),
            "sparse_tensor_slots": len(self.tensor_index_map),
            "metrics": self.metrics(),
            "tiers": {TIER_LABELS[tier]: len(bucket) for tier, bucket in self.tier_content_store.items()},
            "cells": {
                cid: {
                    "tongue_index": c.tongue_index,
                    "tongue_coords": c.tongue_coords,
                    "physical_3d": c.physical_projection,
                    "perpendicular_3d": c.perpendicular_projection,
                    "chladni_mode": list(c.chladni_mode),
                    "content_hash": c.content_hash,
                    "content_size": c.content_size,
                    "category": c.category,
                    "depth": c.depth,
                    "parent_id": c.parent_id,
                    "children": c.children,
                    "phase": c.phase,
                    "viscosity": c.viscosity,
                    "is_valid": c.is_valid,
                    "created_at_utc": c.created_at_utc,
                    "expires_at_utc": c.expires_at_utc,
                    "storage_tier": c.storage_tier,
                    "stored_phason_epoch": c.stored_phason_epoch,
                    "cipher_scheme": c.cipher_scheme,
                }
                for cid, c in self.cells.items()
            },
            "index_map": {",".join(map(str, k)): v for k, v in self.tensor_index_map.items()},
            "slabs": {
                name: {"cells": len(slab.cells), "bytes": slab.total_content_bytes}
                for name, slab in self.tensor_slabs.items()
            },
        }

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(out)


def demo() -> None:
    print("=" * 60)
    print("Quasi-Crystal Voxel Drive - 6D Sparse Tensor Storage")
    print("=" * 60)

    drive = QuasiCrystalVoxelDrive(resolution=64)
    records = [
        (
            "chunk-001",
            b"Hyperbolic geometry provides exponential cost scaling for adversarial behavior",
            [0.3, 0.1, 0.2, 0.7, 0.1, 0.1],
            "math",
        ),
        (
            "chunk-002",
            b"Post-quantum lattice cryptography resists Shor-type attacks",
            [0.2, 0.1, 0.2, 0.8, 0.2, 0.3],
            "security",
        ),
        (
            "chunk-003",
            b"Multi-agent governance consensus under Byzantine assumptions",
            [0.8, 0.1, 0.3, 0.1, 0.1, 0.2],
            "governance",
        ),
    ]

    for cid, payload, coords, cat in records:
        cell = drive.store(cid, payload, coords, category=cat)
        print(
            f"stored {cid} mode={cell.chladni_mode} phase={cell.phase} valid={cell.is_valid} "
            f"index={tuple(cell.tongue_index)}"
        )

    ok = drive.retrieve("chunk-001", [0.3, 0.1, 0.2, 0.7, 0.1, 0.1], strict=True)
    bad = drive.retrieve("chunk-001", [0.9, 0.9, 0.9, 0.1, 0.1, 0.1], strict=True)
    print(f"correct retrieval ok={ok is not None}, wrong retrieval rejected={bad is None}")

    print("stats:", json.dumps(drive.stats(), indent=2))
    export_path = drive.export("training/intake/qc_voxel_drive.json")
    print(f"exported {export_path}")


if __name__ == "__main__":
    demo()
