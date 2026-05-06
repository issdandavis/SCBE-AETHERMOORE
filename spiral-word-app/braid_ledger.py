"""
PHDM-backed braid receipts for SpiralWord headless records.

This adapter binds SpiralWord audit events to the existing 16-node PHDM
Hamiltonian path. It does not define new braid algebra; it exposes the
current path digest, node id, and HMAC tag as a compact receipt that can be
verified later.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from src.symphonic_cipher.scbe_aethermoore.ai_brain.hamiltonian_braid import (
    PHASE_STATES,
    Rail,
    RailPoint,
    constraint_project,
)
from src.symphonic_cipher.scbe_aethermoore.qc_lattice.phdm import PHDMHamiltonianPath


SCHEMA_VERSION = "spiral_word_braid_receipt_v1"
_DEFAULT_SESSION_KEY = "spiralword-braid-ledger-dev-key"
_LEDGER: Optional["BraidLedger"] = None


@dataclass(frozen=True)
class BraidReceipt:
    """Compact receipt tying one audit event to a PHDM Hamiltonian node."""

    loop_root: str
    phdm_node_id: str
    loop_index: int
    hmac_tag: str
    tube_ok: bool
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "loop_root": self.loop_root,
            "phdm_node_id": self.phdm_node_id,
            "loop_index": self.loop_index,
            "hmac_tag": self.hmac_tag,
            "tube_ok": self.tube_ok,
        }


def _session_key_from_env() -> bytes:
    raw = os.environ.get("SCBE_BRAID_LEDGER_KEY", _DEFAULT_SESSION_KEY)
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _normalize_sha256(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("sha256:"):
        value = value.split(":", 1)[1]
    if len(value) < 16:
        raise ValueError("expected at least 16 hex characters")
    int(value[:16], 16)
    return value


class BraidLedger:
    """
    Thin SpiralWord adapter over PHDMHamiltonianPath.

    The tube check uses the existing Hamiltonian braid projection primitives.
    Normal hash-derived commits are placed on the rail center; explicit gate
    vectors perturb the 21D state and may fall outside ``tube_epsilon``.
    """

    def __init__(self, session_key: Optional[bytes] = None, tube_epsilon: float = 0.15):
        self.session_key = session_key or _session_key_from_env()
        self.tube_epsilon = tube_epsilon
        self.path = PHDMHamiltonianPath(key=self.session_key)
        self.nodes = self.path.compute_path()
        self.loop_root = self.path.get_path_digest().hex()
        self.rail = self._build_receipt_rail()

    def commit(
        self,
        prompt_hash: str,
        docx_hash: str,
        *,
        gate_vector: Optional[Iterable[int]] = None,
    ) -> BraidReceipt:
        prompt_hash = _normalize_sha256(prompt_hash)
        docx_hash = _normalize_sha256(docx_hash)
        seed = int(prompt_hash[:8] + docx_hash[:8], 16)

        gates = None if gate_vector is None else [int(value) for value in gate_vector]
        loop_index = seed % len(self.nodes) if gates is None else sum(gates) % len(self.nodes)
        tube_ok = self._tube_check(loop_index, seed, gates)

        node = self.nodes[loop_index]
        return BraidReceipt(
            loop_root=self.loop_root,
            phdm_node_id=node.polyhedron.name,
            loop_index=loop_index,
            hmac_tag=node.hmac_tag.hex(),
            tube_ok=tube_ok,
        )

    def verify(self, receipts: Iterable[BraidReceipt]) -> tuple[bool, bool, Optional[int]]:
        chain_ok, first_bad = self.path.verify_path()
        if not chain_ok:
            return False, False, first_bad

        for index, receipt in enumerate(receipts):
            if receipt.loop_root != self.loop_root:
                return False, bool(receipt.tube_ok), index
            if not 0 <= receipt.loop_index < len(self.nodes):
                return False, bool(receipt.tube_ok), index

            node = self.nodes[receipt.loop_index]
            node_ok = (
                receipt.phdm_node_id == node.polyhedron.name
                and receipt.hmac_tag == node.hmac_tag.hex()
                and receipt.schema_version == SCHEMA_VERSION
            )
            if not node_ok:
                return False, bool(receipt.tube_ok), index
            if not receipt.tube_ok:
                return True, False, index

        return True, True, None

    def _build_receipt_rail(self) -> Rail:
        points: list[RailPoint] = []
        denom = max(1, len(self.nodes) - 1)
        for index in range(len(self.nodes)):
            position = np.zeros(21, dtype=float)
            position[0] = (index / denom) * 0.20
            position[1] = ((index * 7) % len(self.nodes)) / denom * 0.10
            position[2] = ((index * 11) % len(self.nodes)) / denom * 0.10
            points.append(
                RailPoint(
                    position=position,
                    expected_phase=PHASE_STATES[index % len(PHASE_STATES)],
                    index=index,
                )
            )
        return Rail(points=points)

    def _tube_check(self, loop_index: int, seed: int, gate_vector: Optional[list[int]]) -> bool:
        if gate_vector is None:
            return True
        if any(value < 0 or value > 255 for value in gate_vector):
            return False
        spread = max(gate_vector) - min(gate_vector)
        normalized_spread = spread / 255.0
        state = np.array(self.rail.points[loop_index].position, dtype=float)
        state[3] = normalized_spread
        state[4] = ((seed >> 8) & 0xFF) / 255.0 * 0.05
        phase = PHASE_STATES[loop_index % len(PHASE_STATES)]
        projection = constraint_project(state, phase, self.rail)
        return projection.braid_dist <= self.tube_epsilon


def get_braid_ledger() -> BraidLedger:
    """Return the process-wide SpiralWord braid ledger."""
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = BraidLedger()
    return _LEDGER
