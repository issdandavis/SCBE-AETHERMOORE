"""
@file headless.py
@module spiral-word-app/headless
@layer Layer 13, Layer 14
@component Headless record generation with BraidLedger binding

Provides generate_record() — the primary entry point for creating
braid-sealed audit records without a running server. Used by CLI
tooling, batch processors, and test harnesses.

record_id = sha256(loop_root || phdm_node_id || prompt_hash || docx_hash)[:32]

All 32-char hex record_id guarantees are preserved for backwards compat.
"""

import hashlib
import os
import sys
from dataclasses import dataclass
from typing import Optional

# Ensure repo root and src/ are importable
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
_src_root = os.path.join(_repo_root, "src")
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

from governance import AuditLog, classify_intent
from braid_ledger import BraidLedger

# Process-wide BraidLedger instance, lazily initialized
_process_ledger: Optional[BraidLedger] = None
_process_audit_log = AuditLog()


def _get_ledger() -> BraidLedger:
    """Get or create the process-wide BraidLedger."""
    global _process_ledger
    if _process_ledger is None:
        session_key = os.environ.get("SCBE_SESSION_KEY", "").encode("utf-8")
        if not session_key:
            session_key = hashlib.sha256(b"spiralword-headless-default").digest()
        _process_ledger = BraidLedger(session_key=session_key)
    return _process_ledger


def reset_ledger(session_key: Optional[bytes] = None) -> BraidLedger:
    """Reset the process-wide ledger (useful for testing).

    Args:
        session_key: New session key. If None, generates a random one.

    Returns:
        The new BraidLedger instance.
    """
    global _process_ledger
    if session_key is None:
        session_key = os.urandom(32)
    _process_ledger = BraidLedger(session_key=session_key)
    return _process_ledger


def _sha256_hex(data: str) -> str:
    """Compute SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass
class GeneratedRecord:
    """Result of generate_record()."""

    record_id: str  # 32-char hex
    prompt_hash: str
    docx_hash: str
    phdm_node_id: str
    loop_index: int
    braid_receipt: str  # hex HMAC tag
    loop_root: str
    tube_ok: bool


def generate_record(
    doc_id: str,
    site_id: str,
    prompt: str,
    doc_content: str,
    provider: str = "echo",
) -> GeneratedRecord:
    """Generate a braid-sealed audit record.

    Steps:
    1. Hash prompt and document content
    2. Commit to BraidLedger → receipt
    3. Compute record_id = sha256(loop_root || phdm_node_id || prompt_hash || docx_hash)[:32]
    4. Record in audit log with braid fields
    5. If tube violation: raise ValueError

    Args:
        doc_id: Document identifier
        site_id: Site/user identifier
        prompt: AI prompt text
        doc_content: Current document content
        provider: AI provider name

    Returns:
        GeneratedRecord with all braid fields

    Raises:
        ValueError: If braid tube violation detected
    """
    ledger = _get_ledger()

    prompt_hash = _sha256_hex(prompt)
    docx_hash = _sha256_hex(doc_content)

    receipt = ledger.commit(prompt_hash, docx_hash)

    record_id = hashlib.sha256(
        (receipt.loop_root + receipt.phdm_node_id + prompt_hash + docx_hash).encode("utf-8")
    ).hexdigest()[:32]

    tongue, confidence = classify_intent(prompt)

    _process_audit_log.record(
        doc_id=doc_id,
        site_id=site_id,
        action=f"ai_edit:{provider}",
        op_checksum=docx_hash[:16],
        governance_decision=f"AI:{provider}",
        tongue=tongue,
        confidence=confidence,
        phdm_node_id=receipt.phdm_node_id,
        loop_index=receipt.loop_index,
        braid_receipt=receipt.hmac_tag,
    )

    if not receipt.tube_ok:
        raise ValueError("braid tube violation")

    return GeneratedRecord(
        record_id=record_id,
        prompt_hash=prompt_hash,
        docx_hash=docx_hash,
        phdm_node_id=receipt.phdm_node_id,
        loop_index=receipt.loop_index,
        braid_receipt=receipt.hmac_tag,
        loop_root=receipt.loop_root,
        tube_ok=receipt.tube_ok,
    )
