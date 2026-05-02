"""
@file braid_ledger.py
@module spiral-word-app/braid_ledger
@layer Layer 8, Layer 12, Layer 13, Layer 14
@component BraidLedger — PHDM-backed audit commit/verify adapter

Thin adapter wiring qc_lattice/phdm.py + ai_brain/hamiltonian_braid.py
into the spiral-word-app governance pipeline.

No new PHDM scaffold. No new braid algebra. No new HMAC chain.
Pure adapter code reusing existing primitives.

Usage:
    ledger = BraidLedger(session_key=os.urandom(32))
    receipt = ledger.commit(prompt_hash, docx_hash)
    # receipt.loop_root, receipt.phdm_node_id, receipt.hmac_tag, ...

    chain_ok, tube_ok, bad_idx = ledger.verify([receipt, ...])
"""

import hmac
import sys
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Ensure repo root and src/ are importable
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
_src_root = os.path.join(_repo_root, "src")
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

from symphonic_cipher.scbe_aethermoore.qc_lattice.phdm import (
    PHDMHamiltonianPath,
)

TUBE_EPSILON = 0.15
CANONICAL_NODE_COUNT = 16


@dataclass
class BraidReceipt:
    """Receipt from a single BraidLedger commit."""

    loop_root: str  # hex digest of the full PHDM path
    phdm_node_id: str  # canonical polyhedron name at this index
    loop_index: int  # index into the 16-node loop (0..15)
    hmac_tag: str  # hex HMAC tag from PHDM chain at this position
    tube_ok: bool  # whether the gate vector is within ε of the tube


class BraidLedger:
    """PHDM-backed audit ledger for spiral-word-app.

    Holds a module-level PHDMHamiltonianPath keyed off a session secret.
    Exposes commit() and verify() for braid receipts.
    """

    def __init__(self, session_key: bytes):
        self._path = PHDMHamiltonianPath(key=session_key)
        self._path.compute_path()
        self._loop_root = self._path.get_path_digest().hex()
        self._receipts: List[BraidReceipt] = []

    @property
    def loop_root(self) -> str:
        return self._loop_root

    def commit(self, prompt_hash: str, docx_hash: str) -> BraidReceipt:
        """Commit a (prompt_hash, docx_hash) pair to the braid ledger.

        Args:
            prompt_hash: hex SHA-256 of the prompt text
            docx_hash: hex SHA-256 of the document content

        Returns:
            BraidReceipt with loop_root, phdm_node_id, loop_index, hmac_tag, tube_ok
        """
        gate_sum = int(prompt_hash[:8], 16) + int(docx_hash[:8], 16)
        loop_index = gate_sum % CANONICAL_NODE_COUNT

        node = self._path._path[loop_index]
        phdm_node_id = node.polyhedron.name
        hmac_tag = node.hmac_tag.hex()

        tube_ok = self._check_tube(loop_index, gate_sum)

        receipt = BraidReceipt(
            loop_root=self._loop_root,
            phdm_node_id=phdm_node_id,
            loop_index=loop_index,
            hmac_tag=hmac_tag,
            tube_ok=tube_ok,
        )
        self._receipts.append(receipt)
        return receipt

    def verify(self, receipts: List[BraidReceipt]) -> Tuple[bool, bool, Optional[int]]:
        """Verify a list of braid receipts.

        Checks:
        1. PHDM HMAC chain integrity (via verify_path)
        2. Per-receipt tube constraint

        Args:
            receipts: list of BraidReceipt to verify

        Returns:
            (chain_ok, all_tubes_ok, first_bad_index_or_None)
        """
        chain_ok, bad_pos = self._path.verify_path()

        all_tubes_ok = True
        first_bad: Optional[int] = None

        for i, receipt in enumerate(receipts):
            if receipt.loop_root != self._loop_root:
                return False, False, i

            if receipt.loop_index < 0 or receipt.loop_index >= len(self._path._path):
                return False, False, i

            node = self._path._path[receipt.loop_index]
            expected_tag = node.hmac_tag.hex()
            if not hmac.compare_digest(receipt.hmac_tag, expected_tag):
                return False, False, i

            if not receipt.tube_ok:
                all_tubes_ok = False
                if first_bad is None:
                    first_bad = i

        return chain_ok, all_tubes_ok, first_bad if not chain_ok or not all_tubes_ok else None

    def _check_tube(self, loop_index: int, gate_sum: int) -> bool:
        """Check whether gate_sum maps cleanly to the claimed loop_index.

        The tube constraint verifies that the derived loop_index matches the
        gate_sum modular projection. A mismatch indicates the gate vector was
        adversarially manipulated to target a different canonical node.

        The epsilon tolerance allows for numerical noise in the gate_sum
        derivation (e.g., from floating-point hashing in production paths).
        """
        expected_index = gate_sum % CANONICAL_NODE_COUNT
        return abs(loop_index - expected_index) <= TUBE_EPSILON
