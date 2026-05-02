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

    The tube check is intentionally conservative for this first adapter:
    normal hash-derived commits stay inside the tube, while explicit gate
    vectors can mark a receipt as outside the tube for validation tests and
    future controller wiring.
    """

    def __init__(self, session_key: Optional[bytes] = None, tube_epsilon: float = 0.15):
        self.session_key = session_key or _session_key_from_env()
        self.tube_epsilon = tube_epsilon
        self.path = PHDMHamiltonianPath(key=self.session_key)
        self.nodes = self.path.compute_path()
        self.loop_root = self.path.get_path_digest().hex()

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

        if gate_vector is None:
            loop_index = seed % len(self.nodes)
            tube_ok = True
        else:
            gates = [int(value) for value in gate_vector]
            loop_index = sum(gates) % len(self.nodes)
            tube_ok = self._gate_vector_in_tube(gates)

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

    def _gate_vector_in_tube(self, gate_vector: list[int]) -> bool:
        if not gate_vector:
            return True
        if any(value < 0 or value > 255 for value in gate_vector):
            return False
        spread = max(gate_vector) - min(gate_vector)
        normalized_spread = spread / 255
        return normalized_spread <= self.tube_epsilon


def get_braid_ledger() -> BraidLedger:
    """Return the process-wide SpiralWord braid ledger."""
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = BraidLedger()
    return _LEDGER
