from __future__ import annotations

import hashlib
import pickle
import zipfile
from pathlib import Path

import pytest

import audit_parent_vocab
import clay_vqcc_byte_codec as codec
from test_clay_vqcc_byte_codec import parent_vocab_fixture


def _checkpoint(path: Path, payload: object) -> str:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("PARENT.pt/data.pkl", pickle.dumps(payload, protocol=4))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_safe_opcode_audit_closes_exact_parent_vocab_gate(tmp_path: Path) -> None:
    checkpoints = {}
    hashes = {}
    for seed in ("20261134", "20261135", "20261136"):
        path = tmp_path / f"{seed}.pt"
        checkpoints[seed] = path
        hashes[seed] = _checkpoint(path, {"vocab": parent_vocab_fixture(), "seed": seed})
    receipt = audit_parent_vocab.audit_checkpoints(
        checkpoints,
        expected_checkpoint_sha256=hashes,
    )
    assert receipt["status"] == "PASS_SAFE_OPCODE_SCAN"
    assert receipt["exact_fixture_match"] is True
    assert receipt["vocab"]["vocab_sha256"] == codec.PARENT_VOCAB_SHA256
    assert receipt["vocab"]["label_token_ids"]["gate_count"]["T"] == 104
    assert receipt["torch_imported"] is False
    assert receipt["pickle_executed"] is False
    assert receipt["model_loaded"] is False


def test_safe_opcode_audit_rejects_ambiguous_or_drifted_metadata(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.pt"
    _checkpoint(malformed, {"vocab": tuple(parent_vocab_fixture())})
    with pytest.raises(ValueError, match="explicit empty list"):
        audit_parent_vocab.extract_vocab(malformed)

    drifted = tmp_path / "drifted.pt"
    vocab = parent_vocab_fixture()
    vocab[-1] = "X"
    _checkpoint(drifted, {"vocab": vocab})
    with pytest.raises(codec.ByteCodecError, match="lacks byte tokens"):
        audit_parent_vocab.extract_vocab(drifted)
