"""Tests for sealed memory packets."""

import copy
import json

import pytest

from src.crypto.sealed_memory_packets import (
    seal_memory_packet,
    unseal_memory_packet,
    verify_memory_packet,
)


def test_sealed_memory_packet_roundtrips_exact_bytes():
    payload = b"system: keep spacing\ncommand: run-tests --target=crypto\n\xff\x00tail"
    packet = seal_memory_packet(
        b"test-secret",
        payload,
        tongue="ca",
        label="agent-instruction",
        metadata={"agent": "codex", "priority": 1},
    )

    opened = unseal_memory_packet(b"test-secret", packet)

    assert opened["payload"] == payload
    assert opened["text"] is None
    assert opened["tongue"] == "ca"
    assert opened["label"] == "agent-instruction"
    assert opened["metadata"] == {"agent": "codex", "priority": 1}
    assert opened["roundtrip_ok"] is True
    assert len(opened["tokens"]) == len(payload)
    json.dumps(packet, sort_keys=True)
    assert verify_memory_packet(b"test-secret", packet) is True


def test_sealed_memory_packet_roundtrips_text():
    packet = seal_memory_packet(
        "test-secret", "Seal this instruction exactly.", tongue="dr"
    )
    opened = unseal_memory_packet("test-secret", packet)

    assert opened["text"] == "Seal this instruction exactly."
    assert opened["payload"] == b"Seal this instruction exactly."


def test_wrong_secret_rejects_packet():
    packet = seal_memory_packet("correct-secret", "private instruction")

    with pytest.raises(ValueError, match="AEAD authentication failed"):
        unseal_memory_packet("wrong-secret", packet)

    assert verify_memory_packet("wrong-secret", packet) is False


def test_metadata_tamper_rejects_packet():
    packet = seal_memory_packet(
        "test-secret",
        "private instruction",
        metadata={"role": "operator"},
    )
    tampered = copy.deepcopy(packet)
    tampered["metadata"]["role"] = "admin"

    with pytest.raises(ValueError, match="sealed packet AAD mismatch"):
        unseal_memory_packet("test-secret", tampered)


def test_token_hash_tamper_rejects_packet():
    packet = seal_memory_packet("test-secret", "private instruction")
    tampered = copy.deepcopy(packet)
    tampered["token_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="sealed packet AAD mismatch"):
        unseal_memory_packet("test-secret", tampered)


def test_invalid_tongue_rejected_before_seal():
    with pytest.raises(ValueError, match="unknown Sacred Tongue code"):
        seal_memory_packet("test-secret", "payload", tongue="invalid")


def test_empty_secret_rejected():
    with pytest.raises(ValueError, match="secret must not be empty"):
        seal_memory_packet("", "payload")
