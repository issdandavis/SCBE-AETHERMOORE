"""Tamper and downgrade boundaries for custom composition and legacy signing."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

from src.crypto.braid_vault import BraidVault, BraidWord

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(params=["src/symphonic_cipher", "symphonic_cipher"])
def signatures(request, monkeypatch):
    monkeypatch.setenv("SCBE_FORCE_SKIP_LIBOQS", "1")
    monkeypatch.delenv("SCBE_ALLOW_MOCK_PQC", raising=False)
    monkeypatch.delenv("SCBE_ENV", raising=False)
    path = ROOT / request.param / "scbe_aethermoore/spiral_seal/signatures.py"
    spec = importlib.util.spec_from_file_location("review_sig_" + request.param.replace("/", "_"), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_signature_format_alone_never_authenticates(signatures):
    assert not signatures.dilithium_verify(b"not-a-key", b"forged", b"FALLBACK_SIG:" + b"x" * 32)


def test_missing_native_signer_fails_closed(signatures):
    with pytest.raises(RuntimeError):
        signatures.dilithium_keygen()
    with pytest.raises(RuntimeError):
        signatures.dilithium_sign(b"k" * 32, b"message")


def test_explicit_development_signatures_bind_message_and_key(signatures, monkeypatch):
    monkeypatch.setenv("SCBE_ALLOW_MOCK_PQC", "1")
    monkeypatch.setenv("SCBE_ENV", "test")
    sk, pk = signatures.dilithium_keygen()
    _, wrong_pk = signatures.dilithium_keygen()
    signature = signatures.dilithium_sign(sk, b"message")
    assert signatures.dilithium_verify(pk, b"message", signature)
    assert not signatures.dilithium_verify(pk, b"changed", signature)
    assert not signatures.dilithium_verify(wrong_pk, b"message", signature)
    assert not signatures.dilithium_verify(pk, b"message", signature[:-1])
    assert signatures.get_pqc_sig_status()["algorithm"] == "Ed25519-development"
    monkeypatch.delenv("SCBE_ALLOW_MOCK_PQC")
    assert not signatures.dilithium_verify(pk, b"message", signature)


def test_production_cannot_enable_development_signer(signatures, monkeypatch):
    monkeypatch.setenv("SCBE_ALLOW_MOCK_PQC", "1")
    monkeypatch.setenv("SCBE_ENV", "production")
    with pytest.raises(RuntimeError):
        signatures.dilithium_keygen()


@pytest.fixture
def vault():
    return BraidVault(b"public-test-seed" * 3, BraidWord.decode("s1"))


@pytest.mark.parametrize(
    "part",
    [
        "ciphertext",
        "salt",
        "nonce",
        "metadata",
        "entry_id",
        "tongue_affinity",
        "expires_at",
        "created_at",
        "format_version",
    ],
)
def test_vault_rejects_altered_entry(vault, part):
    entry = vault.store("demo", b"public test content", metadata={"scope": "test"})
    if part in {"ciphertext", "salt", "nonce"}:
        data = bytearray(getattr(entry, part))
        data[4] ^= 1
        setattr(entry, part, bytes(data))
    elif part == "metadata":
        entry.metadata["scope"] = "other"
    elif part in {"expires_at", "created_at"}:
        setattr(entry, part, 1.0)
    elif part == "format_version":
        entry.format_version = 1
    else:
        setattr(entry, part, "different")
    with pytest.raises(ValueError):
        vault.retrieve("demo")


def test_rotation_validates_all_entries_before_committing(vault):
    vault.store("a", b"first")
    entry = vault.store("b", b"second")
    entry.ciphertext = entry.ciphertext[:-1] + bytes([entry.ciphertext[-1] ^ 1])
    old_key, old_cipher = vault._vault_key, vault._entries["a"].ciphertext
    with pytest.raises(ValueError):
        vault.rotate("a", BraidWord.decode("s2"))
    assert vault._vault_key == old_key
    assert vault._entries["a"].ciphertext == old_cipher
    assert vault.retrieve("a") == b"first"


def test_zero_ttl_is_expired_not_immortal(vault):
    vault.store("instant", b"test", ttl_seconds=0)
    assert vault.retrieve("instant") is None


@pytest.mark.parametrize("result", [False, None, True])
def test_pqcrypto_boolean_verdict_is_respected(signatures, monkeypatch, result):
    # Contract test only; real native validation runs separately in CI.
    monkeypatch.setattr(signatures, "PQC_SIG_BACKEND", "pqcrypto")
    monkeypatch.setattr(signatures, "dilithium", types.SimpleNamespace(verify=lambda *args: result), raising=False)
    assert signatures.dilithium_verify(b"key", b"msg", b"sig") is (result is True)


@pytest.fixture(params=["src/symphonic_cipher", "symphonic_cipher"])
def legacy_seal(request, monkeypatch):
    monkeypatch.setenv("SCBE_FORCE_SKIP_LIBOQS", "1")
    name = "review_seal_" + request.param.replace("/", "_")
    directory = ROOT / request.param / "scbe_aethermoore/spiral_seal"
    package = types.ModuleType(name)
    package.__path__ = [str(directory)]
    monkeypatch.setitem(sys.modules, name, package)
    return __import__(name + ".seal", fromlist=["seal"])


def test_legacy_unsigned_roundtrip_and_aad_binding(legacy_seal):
    api = legacy_seal.SpiralSealSS1(master_secret=b"x" * 32)
    blob = api.seal(b"test", aad="purpose=test")
    assert api.unseal(blob, aad="purpose=test") == b"test"
    with pytest.raises(ValueError):
        api.unseal(blob, aad="other")


def test_legacy_required_signature_cannot_be_ignored(legacy_seal):
    api = legacy_seal.SpiralSealSS1(master_secret=b"x" * 32)
    blob = api.seal(b"test")
    with pytest.raises(ValueError):
        api.unseal(blob, verify_sig=True)
    with pytest.raises(ValueError):
        api.seal(b"test", sign=True)


@pytest.mark.parametrize("field", ["signature", "kyber_ct"])
def test_legacy_serializer_never_discards_security_fields(legacy_seal, field):
    payload = legacy_seal.SealedPayload("k01", "", b"s" * 16, b"n" * 12, b"ct", b"tag", None, None)
    setattr(payload, field, b"supplied security data")
    with pytest.raises(ValueError):
        payload.to_ss1()


def test_vault_metadata_copy_and_rotation_preserve_lifetime(vault):
    metadata = {"nested": {"scope": "demo"}}
    entry = vault.store("a", b"first", ttl_seconds=300, metadata=metadata)
    vault.store("b", b"second")
    metadata["nested"]["scope"] = "changed"
    assert vault.retrieve("a") == b"first"
    rotated = vault.rotate("a", BraidWord.decode("s2"))
    assert rotated.created_at == entry.created_at
    assert rotated.expires_at == entry.expires_at
    assert rotated.nonce != entry.nonce
    assert rotated.metadata == {"nested": {"scope": "demo"}}
    assert vault.retrieve("a") == b"first"
    assert vault.retrieve("b") == b"second"


@pytest.mark.parametrize("attack", ["truncated", "wrong_master", "swapped_id", "legacy"])
def test_vault_alternate_tampering(vault, attack):
    entry = vault.store("a", b"first")
    if attack == "truncated":
        entry.ciphertext = entry.ciphertext[:8]
    elif attack == "wrong_master":
        vault._vault_key = b"w" * 32
    elif attack == "legacy":
        entry.nonce = b""
    else:
        entry.entry_id = "b"
        vault._entries["b"] = entry
    with pytest.raises(ValueError):
        vault.retrieve("b" if attack == "swapped_id" else "a")


def test_rotation_staging_failure_leaves_old_state(vault, monkeypatch):
    vault.store("a", b"first")
    vault.store("b", b"second")
    old_key, old_entries = vault._vault_key, vault._entries
    original = vault._seal_entry

    def fail_second(entry_id, *args):
        if entry_id == "b":
            raise RuntimeError("simulated encryption failure")
        return original(entry_id, *args)

    monkeypatch.setattr(vault, "_seal_entry", fail_second)
    with pytest.raises(RuntimeError):
        vault.rotate("a", BraidWord.decode("s2"))
    assert vault._vault_key == old_key
    assert vault._entries is old_entries
    assert vault.retrieve("a") == b"first"
    assert vault.retrieve("b") == b"second"
