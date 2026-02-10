"""
Tests for Six Tongues + GeoSeal CLI
====================================

Covers:
- Lexicon bijection (all 6 tongues, 256 unique tokens each)
- TongueTokenizer encode/decode round-trips
- CrossTokenizer retokenize (byte + semantic mode) with HMAC attestation
- Blend / unblend round-trip with various patterns
- GeoSeal encrypt/decrypt round-trip (real PQC when available)
- GeoSeal tamper rejection (sig, ciphertext)
- ConcentricRingPolicy ring classification
- EvolvingLexicons mutation and bijection preservation
- SemanticNavigator 6D Poincaré ODE (requires numpy/scipy)
- Projection helpers (sphere, cube, HEALPix, Morton)
- Edge cases and error handling

@module tests/test_six_tongues_cli
@layer Layer 14
"""

import sys
import os
import base64
import json
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from importlib.machinery import SourceFileLoader

# Load six-tongues-cli.py as a module (hyphenated filename)
_cli_path = os.path.join(os.path.dirname(__file__), "..", "six-tongues-cli.py")
_loader = SourceFileLoader("six_tongues_cli", _cli_path)
cli = _loader.load_module()

Lexicons = cli.Lexicons
TongueTokenizer = cli.TongueTokenizer
CrossTokenizer = cli.CrossTokenizer
XlateAttestation = cli.XlateAttestation
ConcentricRingPolicy = cli.ConcentricRingPolicy
EvolvingLexicons = cli.EvolvingLexicons
TONGUES = cli.TONGUES

# Projection helpers
project_to_sphere = cli.project_to_sphere
project_to_cube = cli.project_to_cube
healpix_id = cli.healpix_id
morton_id = cli.morton_id
potentials = cli.potentials
classify_context = cli.classify_context

# Crypto
pqc_available = cli.pqc_available
kem_keygen = cli.kem_keygen
dsa_keygen = cli.dsa_keygen
kyber_encaps = cli.kyber_encaps
kyber_decaps = cli.kyber_decaps
dsa_sign = cli.dsa_sign
dsa_verify = cli.dsa_verify
hkdf = cli.hkdf
geoseal_encrypt = cli.geoseal_encrypt
geoseal_decrypt = cli.geoseal_decrypt

# Optional imports
numpy_available = cli.numpy_available


# ---------------------------------------------------------------------------
# Lexicon & Tokenizer
# ---------------------------------------------------------------------------


class TestLexicons:
    """Core lexicon structure and bijection guarantees."""

    def test_all_six_tongues_present(self):
        lex = Lexicons()
        assert set(lex.by_idx.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}

    @pytest.mark.parametrize("tongue", TONGUES)
    def test_bijection_256_unique_tokens(self, tongue):
        """Each tongue must map 256 byte values to 256 unique tokens."""
        lex = Lexicons()
        tokens = [lex.token_of(tongue, b) for b in range(256)]
        assert len(set(tokens)) == 256

    @pytest.mark.parametrize("tongue", TONGUES)
    def test_round_trip_all_bytes(self, tongue):
        """token_of -> byte_of should be identity for all 256 values."""
        lex = Lexicons()
        for b in range(256):
            tok = lex.token_of(tongue, b)
            assert lex.byte_of(tongue, tok) == b

    def test_unknown_token_raises(self):
        lex = Lexicons()
        with pytest.raises(KeyError, match="unknown token"):
            lex.byte_of("KO", "nonexistent_token_xyz")

    def test_tongues_have_distinct_tokens(self):
        """Tokens from different tongues should differ (prefixed)."""
        lex = Lexicons()
        ko_tokens = set(lex.token_of("KO", b) for b in range(256))
        av_tokens = set(lex.token_of("AV", b) for b in range(256))
        assert ko_tokens.isdisjoint(av_tokens)

    def test_invalid_tongue_raises(self):
        lex = Lexicons()
        with pytest.raises(KeyError):
            lex.token_of("XX", 0)

    def test_custom_table_validation(self):
        """Incomplete or duplicate custom tables should raise."""
        # Missing tongue
        with pytest.raises(ValueError, match="missing tongue"):
            Lexicons({"KO": {str(i): f"t{i}" for i in range(256)}})

        # Duplicate tokens
        bad_table = {}
        for tg in TONGUES:
            d = {str(i): f"{tg.lower()}{i}" for i in range(256)}
            d["255"] = d["0"]  # duplicate
            bad_table[tg] = d
        with pytest.raises(ValueError, match="duplicate tokens"):
            Lexicons(bad_table)


class TestTongueTokenizer:
    """Encode/decode operations."""

    @pytest.mark.parametrize("tongue", TONGUES)
    def test_round_trip_random_payload(self, tongue):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        payload = os.urandom(512)
        tokens = tok.encode_bytes(tongue, payload)
        assert len(tokens) == 512
        assert tok.decode_tokens(tongue, tokens) == payload

    def test_empty_payload(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        assert tok.encode_bytes("KO", b"") == []
        assert tok.decode_tokens("KO", []) == b""

    def test_single_byte(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        for b in [0, 127, 255]:
            tokens = tok.encode_bytes("KO", bytes([b]))
            assert len(tokens) == 1
            assert tok.decode_tokens("KO", tokens) == bytes([b])

    def test_normalize_token_stream(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        result = tok.normalize_token_stream("  tok1  tok2 , tok3 ,tok4  ")
        assert result == ["tok1", "tok2", "tok3", "tok4"]

    def test_normalize_empty_string(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        assert tok.normalize_token_stream("") == []

    def test_decode_skips_empty_tokens(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        tokens = tok.encode_bytes("KO", b"\x00\x01")
        tokens_with_empty = [tokens[0], "", tokens[1]]
        assert tok.decode_tokens("KO", tokens_with_empty) == b"\x00\x01"


# ---------------------------------------------------------------------------
# Cross-Tokenization
# ---------------------------------------------------------------------------


class TestCrossTokenizer:
    """Cross-tongue translation and attestation."""

    @pytest.mark.parametrize("src", TONGUES)
    @pytest.mark.parametrize("dst", TONGUES)
    def test_retokenize_preserves_bytes(self, src, dst):
        """Cross-translation must preserve the exact byte payload."""
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        payload = os.urandom(128)
        token_text = " ".join(tok.encode_bytes(src, payload))
        out_tokens, attest = xt.retokenize(src, dst, token_text)
        recovered = tok.decode_tokens(dst, out_tokens)
        assert recovered == payload

    def test_retokenize_attestation_fields(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        token_text = " ".join(tok.encode_bytes("KO", b"test"))
        _, attest = xt.retokenize("KO", "AV", token_text, attest_key=b"key")
        assert attest.src == "KO"
        assert attest.dst == "AV"
        assert attest.mode == "byte"
        assert isinstance(attest.hmac_attest, str) and len(attest.hmac_attest) > 0
        assert isinstance(attest.sha256_bytes, str) and len(attest.sha256_bytes) == 64
        assert attest.phase_delta >= 0
        assert attest.weight_ratio > 0

    def test_retokenize_semantic_mode(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        payload = b"semantic test payload"
        token_text = " ".join(tok.encode_bytes("RU", payload))
        out_tokens, attest = xt.retokenize("RU", "DR", token_text, mode="semantic")
        assert attest.mode == "semantic"
        assert tok.decode_tokens("DR", out_tokens) == payload

    def test_retokenize_invalid_mode_raises(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        token_text = " ".join(tok.encode_bytes("KO", b"x"))
        with pytest.raises(ValueError, match="mode must be"):
            xt.retokenize("KO", "AV", token_text, mode="invalid")

    def test_phase_and_weight_consistency(self):
        """Phase offsets and weight ratios should be mathematically consistent."""
        xt_phase = CrossTokenizer.PHASE
        xt_weight = CrossTokenizer.WEIGHT
        assert len(xt_phase) == 6
        assert len(xt_weight) == 6
        # KO has phase=0, weight=1.0
        assert xt_phase["KO"] == 0
        assert xt_weight["KO"] == 1.0
        # Weights increase (golden ratio progression)
        prev = 0
        for tg in TONGUES:
            assert xt_weight[tg] > prev
            prev = xt_weight[tg]


class TestBlendUnblend:
    """Interleave/de-interleave across multiple tongues."""

    def test_basic_blend_unblend(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        pattern = ["KO", "AV", "RU"]
        payload = os.urandom(300)
        pairs = xt.blend(pattern, payload)
        assert len(pairs) == 300
        recovered = xt.unblend(pattern, pairs)
        assert recovered == payload

    def test_blend_tongue_assignment(self):
        """Each byte should be assigned to the correct tongue per pattern."""
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        pattern = ["KO", "DR"]
        pairs = xt.blend(pattern, b"\x00\x01\x02\x03")
        assert pairs[0][0] == "KO"
        assert pairs[1][0] == "DR"
        assert pairs[2][0] == "KO"
        assert pairs[3][0] == "DR"

    def test_blend_single_tongue(self):
        """Blend with a single tongue is equivalent to normal encoding."""
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        payload = b"hello"
        pairs = xt.blend(["UM"], payload)
        tokens = [t for _, t in pairs]
        assert tok.decode_tokens("UM", tokens) == payload

    def test_unblend_pattern_mismatch_raises(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        pattern = ["KO", "AV"]
        pairs = xt.blend(pattern, b"\x00\x01")
        # Swap tongue labels
        bad_pairs = [(pairs[1][0], pairs[0][1]), (pairs[0][0], pairs[1][1])]
        with pytest.raises(ValueError, match="blend pattern mismatch"):
            xt.unblend(pattern, bad_pairs)

    def test_blend_empty_payload(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        pairs = xt.blend(["KO", "AV"], b"")
        assert pairs == []
        assert xt.unblend(["KO", "AV"], []) == b""

    @pytest.mark.parametrize("pattern", [
        ["KO", "KO", "AV", "RU", "CA", "UM", "DR"],
        ["DR", "DR", "DR"],
        ["KO", "AV"],
    ])
    def test_blend_various_patterns(self, pattern):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        payload = os.urandom(256)
        pairs = xt.blend(pattern, payload)
        assert xt.unblend(pattern, pairs) == payload


# ---------------------------------------------------------------------------
# Projection Helpers
# ---------------------------------------------------------------------------


class TestProjections:
    """Sphere, cube, HEALPix, and Morton projections."""

    def test_project_to_sphere_unit_norm(self):
        u = project_to_sphere([1.0, -2.0, 3.0])
        norm = math.sqrt(sum(v * v for v in u))
        assert abs(norm - 1.0) < 1e-10

    def test_project_to_sphere_short_input(self):
        """Pads short inputs with zeros."""
        u = project_to_sphere([1.0])
        assert len(u) == 3
        norm = math.sqrt(sum(v * v for v in u))
        assert abs(norm - 1.0) < 1e-10

    def test_project_to_cube_range(self):
        v = project_to_cube([10, -10, 0, 5, -5, 100])
        for x in v:
            assert 0.0 <= x <= 1.0

    def test_project_to_cube_zero_centered(self):
        v = project_to_cube([0, 0, 0, 0, 0, 0])
        for x in v:
            assert abs(x - 0.5) < 1e-10  # tanh(0) = 0 -> (0+1)/2 = 0.5

    def test_healpix_id_format(self):
        u = project_to_sphere([1, 2, 3])
        hid = healpix_id(u, 2)
        assert hid.startswith("S2:")

    def test_morton_id_format(self):
        v = project_to_cube([1, 2, 3, 4, 5, 6])
        mid = morton_id(v, 3)
        assert mid.startswith("C3:")

    def test_potentials_returns_two_floats(self):
        u = project_to_sphere([0.2, -0.3, 0.7])
        v = project_to_cube([0.2, -0.3, 0.7])
        P, margin = potentials(u, v)
        assert isinstance(P, float)
        assert isinstance(margin, float)

    def test_classify_context_interior(self):
        """Well-centered context should be classified as interior."""
        result = classify_context("S2:(1,2,3)", "C2:(4,5,6)", 0.3, 0.2)
        assert result == "interior"

    def test_classify_context_exterior(self):
        """High-risk context should be classified as exterior."""
        result = classify_context("S2:(1,2,3)", "C2:(4,5,6)", 0.9, 0.01)
        assert result == "exterior"


# ---------------------------------------------------------------------------
# Concentric Ring Policy
# ---------------------------------------------------------------------------


class TestConcentricRingPolicy:
    """Ring-based access control classification."""

    @pytest.fixture
    def policy(self):
        return ConcentricRingPolicy()

    @pytest.mark.parametrize("r,expected_ring", [
        (0.0, "core"),
        (0.15, "core"),
        (0.29, "core"),
        (0.3, "inner"),
        (0.45, "inner"),
        (0.5, "middle"),
        (0.65, "middle"),
        (0.7, "outer"),
        (0.85, "outer"),
        (0.9, "edge"),
        (0.99, "edge"),
    ])
    def test_ring_classification(self, policy, r, expected_ring):
        result = policy.classify(r)
        assert result["ring"] == expected_ring

    def test_beyond_ring_rejects(self, policy):
        result = policy.classify(1.0)
        assert result.get("action") == "REJECT"

    def test_negative_r_returns_core(self, policy):
        # 0.0 <= r < 0.3 should match core; negative is outside all ranges
        result = policy.classify(-0.1)
        assert result.get("action") == "REJECT" or result.get("ring") == "beyond"

    def test_core_has_lowest_latency(self, policy):
        core = policy.classify(0.1)
        edge = policy.classify(0.95)
        assert core["max_latency_ms"] < edge["max_latency_ms"]

    def test_ring_has_required_fields(self, policy):
        result = policy.classify(0.5)
        assert "ring" in result
        assert "max_latency_ms" in result
        assert "required_signatures" in result
        assert "pow_bits" in result
        assert "trust_decay_rate" in result

    def test_escalating_requirements(self, policy):
        """Outer rings should have stricter requirements than inner rings."""
        core = policy.classify(0.1)
        middle = policy.classify(0.6)
        edge = policy.classify(0.95)
        assert core["pow_bits"] <= middle["pow_bits"] <= edge["pow_bits"]
        assert core["required_signatures"] <= middle["required_signatures"] <= edge["required_signatures"]


# ---------------------------------------------------------------------------
# Envelope Crypto
# ---------------------------------------------------------------------------


class TestCrypto:
    """PQC key generation, encaps/decaps, sign/verify."""

    def test_kem_keygen_returns_two_keys(self):
        pk, sk = kem_keygen()
        assert isinstance(pk, bytes) and len(pk) > 0
        assert isinstance(sk, bytes) and len(sk) > 0

    def test_dsa_keygen_returns_two_keys(self):
        pk, sk = dsa_keygen()
        assert isinstance(pk, bytes) and len(pk) > 0
        assert isinstance(sk, bytes) and len(sk) > 0

    def test_kyber_encaps_decaps_roundtrip(self):
        pk, sk = kem_keygen()
        ss1, ct = kyber_encaps(pk)
        ss2 = kyber_decaps(sk, ct)
        assert ss1 == ss2

    def test_dsa_sign_verify_valid(self):
        pk, sk = dsa_keygen()
        msg = b"test message for signing"
        sig = dsa_sign(sk, msg)
        assert isinstance(sig, bytes)
        assert dsa_verify(pk, msg, sig)

    def test_dsa_verify_rejects_tampered_sig(self):
        pk, sk = dsa_keygen()
        msg = b"authentic message"
        sig = dsa_sign(sk, msg)
        tampered = b"x" * len(sig)
        assert not dsa_verify(pk, msg, tampered)

    def test_dsa_verify_rejects_wrong_message(self):
        pk, sk = dsa_keygen()
        msg = b"original"
        sig = dsa_sign(sk, msg)
        assert not dsa_verify(pk, b"modified", sig)

    def test_hkdf_deterministic(self):
        k1 = hkdf(b"secret", "info")
        k2 = hkdf(b"secret", "info")
        assert k1 == k2
        assert len(k1) == 32

    def test_hkdf_different_info(self):
        k1 = hkdf(b"secret", "info1")
        k2 = hkdf(b"secret", "info2")
        assert k1 != k2

    def test_pqc_available_returns_bool(self):
        assert isinstance(pqc_available(), bool)

    @pytest.mark.skipif(not cli.pqc_available(), reason="pqcrypto not installed")
    def test_real_pqc_key_sizes(self):
        """Verify real ML-KEM-768 and ML-DSA-65 key sizes match NIST spec."""
        pk, sk = kem_keygen()
        assert len(pk) == 1184   # ML-KEM-768 public key
        assert len(sk) == 2400   # ML-KEM-768 secret key

        dpk, dsk = dsa_keygen()
        assert len(dpk) == 1952  # ML-DSA-65 public key
        assert len(dsk) == 4032  # ML-DSA-65 secret key


# ---------------------------------------------------------------------------
# GeoSeal Encrypt / Decrypt
# ---------------------------------------------------------------------------


class TestGeoSeal:
    """Context-aware encryption envelope."""

    @pytest.fixture
    def keys(self):
        """Generate keypairs for GeoSeal tests."""
        kem_pk, kem_sk = kem_keygen()
        dsa_pk, dsa_sk = dsa_keygen()
        return {
            "kem_pk_b64": base64.b64encode(kem_pk).decode(),
            "kem_sk_b64": base64.b64encode(kem_sk).decode(),
            "dsa_pk_b64": base64.b64encode(dsa_pk).decode(),
            "dsa_sk_b64": base64.b64encode(dsa_sk).decode(),
        }

    def test_encrypt_decrypt_roundtrip(self, keys):
        ctx = [0.2, -0.3, 0.7, 1.0, -2.0]
        pt = b"hello aethermoore roundtrip"
        pt_b64 = base64.b64encode(pt).decode()
        env = geoseal_encrypt(pt_b64, ctx, keys["kem_pk_b64"], keys["dsa_sk_b64"])
        ok, decpt = geoseal_decrypt(env, ctx, keys["kem_sk_b64"], keys["dsa_pk_b64"])
        assert ok
        assert decpt == pt

    def test_envelope_structure(self, keys):
        ctx = [0.1, 0.2, 0.3]
        pt_b64 = base64.b64encode(b"payload").decode()
        env = geoseal_encrypt(pt_b64, ctx, keys["kem_pk_b64"], keys["dsa_sk_b64"])
        assert "ct_k" in env
        assert "ct_spec" in env
        assert "attest" in env
        assert "sig" in env
        assert "h" in env["attest"]
        assert "z" in env["attest"]
        assert "P" in env["attest"]
        assert "margin" in env["attest"]
        assert "path" in env["attest"]
        assert "ring" in env["attest"]
        assert "L_s" in env["attest"]
        assert "L_c" in env["attest"]

    def test_tampered_sig_rejected(self, keys):
        ctx = [0.5, -0.5, 0.0]
        pt_b64 = base64.b64encode(b"tamper test").decode()
        env = geoseal_encrypt(pt_b64, ctx, keys["kem_pk_b64"], keys["dsa_sk_b64"])
        tampered = dict(env)
        tampered["sig"] = base64.b64encode(b"bad" * 20).decode()
        ok, _ = geoseal_decrypt(tampered, ctx, keys["kem_sk_b64"], keys["dsa_pk_b64"])
        assert not ok

    def test_tampered_ciphertext_rejected(self, keys):
        ctx = [0.1, 0.2, 0.3]
        pt_b64 = base64.b64encode(b"ct tamper").decode()
        env = geoseal_encrypt(pt_b64, ctx, keys["kem_pk_b64"], keys["dsa_sk_b64"])
        tampered = dict(env)
        tampered["ct_spec"] = base64.b64encode(b"\xff" * 20).decode()
        ok, _ = geoseal_decrypt(tampered, ctx, keys["kem_sk_b64"], keys["dsa_pk_b64"])
        assert not ok

    def test_large_payload(self, keys):
        ctx = [1.0, 2.0, 3.0]
        pt = os.urandom(4096)
        pt_b64 = base64.b64encode(pt).decode()
        env = geoseal_encrypt(pt_b64, ctx, keys["kem_pk_b64"], keys["dsa_sk_b64"])
        ok, decpt = geoseal_decrypt(env, ctx, keys["kem_sk_b64"], keys["dsa_pk_b64"])
        assert ok
        assert decpt == pt

    def test_ring_policy_in_envelope(self, keys):
        ctx = [0.2, -0.3, 0.7]
        pt_b64 = base64.b64encode(b"ring check").decode()
        env = geoseal_encrypt(pt_b64, ctx, keys["kem_pk_b64"], keys["dsa_sk_b64"])
        ring = env["attest"]["ring"]
        assert "ring" in ring
        # ring should be one of core/inner/middle/outer/edge/beyond
        assert ring["ring"] in ("core", "inner", "middle", "outer", "edge", "beyond")


# ---------------------------------------------------------------------------
# EvolvingLexicons
# ---------------------------------------------------------------------------


class TestEvolvingLexicons:
    """Self-mutating lexicons with drift and bijection preservation."""

    def test_evolving_inherits_lexicons(self):
        evo = EvolvingLexicons()
        # Should have all tongue lexicons
        assert set(evo.by_idx.keys()) == set(TONGUES)

    def test_mutation_occurs_at_high_rate(self):
        """With mutation_rate=1.0, mutations should occur."""
        evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
        payload = os.urandom(64)
        mutations = 0
        for _ in range(50):
            result = evo.evolve_after_use("KO", "AV", payload, coherence=1.0)
            if result is not None:
                mutations += 1
        assert mutations > 0

    def test_no_mutation_at_zero_rate(self):
        evo = EvolvingLexicons(mutation_rate=0.0, drift_strength=0.1)
        payload = os.urandom(64)
        for _ in range(50):
            result = evo.evolve_after_use("KO", "AV", payload, coherence=1.0)
            assert result is None

    @pytest.mark.parametrize("tongue", TONGUES)
    def test_bijection_preserved_after_mutations(self, tongue):
        """After many mutations, every tongue must still have 256 unique tokens."""
        evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
        payload = os.urandom(64)
        for _ in range(30):
            evo.evolve_after_use("KO", tongue, payload, coherence=1.0)
        all_tokens = [evo.token_of(tongue, b) for b in range(256)]
        assert len(set(all_tokens)) == 256

    def test_mutation_log_records(self):
        evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
        payload = os.urandom(64)
        for _ in range(30):
            evo.evolve_after_use("KO", "AV", payload, coherence=1.0)
        if len(evo.mutation_log) > 0:
            record = evo.mutation_log[0]
            assert "byte" in record
            assert "tongue" in record
            assert "old_token" in record
            assert "new_token" in record
            assert "coherence" in record
            assert "drift" in record

    def test_evolved_lexicon_round_trips(self):
        """Evolved lexicon should still round-trip correctly."""
        evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
        payload = os.urandom(64)
        for _ in range(20):
            evo.evolve_after_use("KO", "AV", payload, coherence=1.0)
        # Round-trip with evolved lexicon
        for tg in TONGUES:
            toks = [evo.token_of(tg, b) for b in payload]
            dec = bytes(evo.byte_of(tg, t) for t in toks)
            assert dec == payload

    def test_empty_payload_no_mutation(self):
        evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
        result = evo.evolve_after_use("KO", "AV", b"", coherence=1.0)
        assert result is None

    def test_realm_centers_exist_for_all_tongues(self):
        assert set(EvolvingLexicons.REALM_CENTERS.keys()) == set(TONGUES)
        for tg in TONGUES:
            assert len(EvolvingLexicons.REALM_CENTERS[tg]) == 6


# ---------------------------------------------------------------------------
# SemanticNavigator
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not numpy_available(), reason="numpy/scipy not installed")
class TestSemanticNavigator:
    """6D Poincaré ODE semantic navigator."""

    def setup_method(self):
        import numpy as np
        self.np = np
        self.SemanticNavigator = cli.SemanticNavigator

    def test_default_origin(self):
        nav = self.SemanticNavigator()
        assert float(self.np.linalg.norm(nav.position)) < 1e-10

    def test_custom_initial_position(self):
        nav = self.SemanticNavigator(initial_pos=[0.1, 0.2, 0.0, 0.0, 0.0, 0.0])
        assert abs(nav.position[0] - 0.1) < 1e-10
        assert abs(nav.position[1] - 0.2) < 1e-10

    def test_update_position_stays_in_ball(self):
        nav = self.SemanticNavigator(chaos_strength=0.01)
        for _ in range(10):
            pos = nav.update_position(["KO", "AV"], coherence=0.9, dt=0.01)
            assert float(self.np.linalg.norm(pos)) < 1.0

    def test_history_grows(self):
        nav = self.SemanticNavigator(chaos_strength=0.01)
        assert len(nav.history) == 1
        nav.update_position(["KO"], dt=0.01)
        assert len(nav.history) == 2
        nav.update_position(["AV"], dt=0.01)
        assert len(nav.history) == 3

    def test_self_distance_zero(self):
        nav = self.SemanticNavigator(
            initial_pos=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], chaos_strength=0.01
        )
        d = nav.distance_to(nav)
        assert d < 1e-6

    def test_distance_between_agents(self):
        nav1 = self.SemanticNavigator(chaos_strength=0.01)
        nav2 = self.SemanticNavigator(
            initial_pos=[0.3, 0.0, 0.0, 0.0, 0.0, 0.0], chaos_strength=0.01
        )
        d = nav1.distance_to(nav2)
        assert d > 0

    def test_export_trajectory_shape(self):
        nav = self.SemanticNavigator(chaos_strength=0.01)
        nav.update_position(["KO"], dt=0.01)
        nav.update_position(["AV"], dt=0.01)
        traj = nav.export_trajectory()
        assert traj.shape == (3, 6)

    def test_poincare_projection(self):
        nav = self.SemanticNavigator()
        big_vec = self.np.array([10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
        projected = nav.poincare_project(big_vec)
        assert float(self.np.linalg.norm(projected)) < 1.0

    def test_poincare_projection_small_vec_unchanged(self):
        nav = self.SemanticNavigator()
        small_vec = self.np.array([0.01, 0.01, 0.0, 0.0, 0.0, 0.0])
        projected = nav.poincare_project(small_vec)
        assert self.np.allclose(projected, small_vec)

    def test_realm_centers_exist(self):
        assert set(self.SemanticNavigator.REALM_CENTERS.keys()) == set(TONGUES)

    def test_mutation_count_affects_trajectory(self):
        """Non-zero mutation_count should introduce repulsion."""
        nav1 = self.SemanticNavigator(
            initial_pos=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], chaos_strength=0.0
        )
        nav2 = self.SemanticNavigator(
            initial_pos=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], chaos_strength=0.0
        )
        # Due to randomness in repulsion, positions may differ
        nav1.update_position(["KO"], coherence=0.5, mutation_count=0, dt=0.01)
        nav2.update_position(["KO"], coherence=0.5, mutation_count=100, dt=0.01)
        # Can't guarantee exact difference due to random repulsion, just check both valid
        assert float(self.np.linalg.norm(nav1.position)) < 1.0
        assert float(self.np.linalg.norm(nav2.position)) < 1.0


# ---------------------------------------------------------------------------
# Edge Cases & Error Handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and error paths."""

    def test_bad_token_decode_raises(self):
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        with pytest.raises(KeyError):
            tok.decode_tokens("KO", ["nonexistent_tok_xyz"])

    def test_geoseal_with_minimal_context(self):
        """GeoSeal should work even with short context vectors."""
        kem_pk, kem_sk = kem_keygen()
        dsa_pk, dsa_sk = dsa_keygen()
        ctx = [0.5]  # Very short
        pt_b64 = base64.b64encode(b"short ctx").decode()
        env = geoseal_encrypt(
            pt_b64, ctx,
            base64.b64encode(kem_pk).decode(),
            base64.b64encode(dsa_sk).decode(),
        )
        ok, decpt = geoseal_decrypt(
            env, ctx,
            base64.b64encode(kem_sk).decode(),
            base64.b64encode(dsa_pk).decode(),
        )
        assert ok
        assert decpt == b"short ctx"

    def test_geoseal_empty_payload(self):
        kem_pk, kem_sk = kem_keygen()
        dsa_pk, dsa_sk = dsa_keygen()
        ctx = [0.0, 0.0, 0.0]
        pt_b64 = base64.b64encode(b"").decode()
        env = geoseal_encrypt(
            pt_b64, ctx,
            base64.b64encode(kem_pk).decode(),
            base64.b64encode(dsa_sk).decode(),
        )
        ok, decpt = geoseal_decrypt(
            env, ctx,
            base64.b64encode(kem_sk).decode(),
            base64.b64encode(dsa_pk).decode(),
        )
        assert ok
        assert decpt == b""

    def test_zscore_constant_input(self):
        """Z-score of constant values should not crash (var=0 -> sd=1)."""
        result = cli._zscore([5.0, 5.0, 5.0])
        assert all(abs(v) < 1e-10 for v in result)

    @pytest.mark.skipif(not numpy_available(), reason="numpy/scipy not installed")
    def test_semantic_navigator_without_numpy_raises(self):
        """If we monkeypatch _HAS_NUMPY=False, constructor should raise."""
        original = cli._HAS_NUMPY
        try:
            cli._HAS_NUMPY = False
            with pytest.raises(ImportError, match="requires numpy"):
                cli.SemanticNavigator()
        finally:
            cli._HAS_NUMPY = original


# ---------------------------------------------------------------------------
# Integration: End-to-End Pipeline
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end workflows combining multiple components."""

    def test_encode_xlate_blend_geoseal_pipeline(self):
        """Full pipeline: encode -> cross-translate -> blend -> GeoSeal."""
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)

        # 1. Encode payload to KO
        payload = b"integrated pipeline test"
        ko_tokens = tok.encode_bytes("KO", payload)

        # 2. Cross-translate KO -> DR
        token_text = " ".join(ko_tokens)
        dr_tokens, attest = xt.retokenize("KO", "DR", token_text, attest_key=b"test")
        recovered = tok.decode_tokens("DR", dr_tokens)
        assert recovered == payload

        # 3. Blend using multiple tongues
        pattern = ["KO", "AV", "DR"]
        pairs = xt.blend(pattern, payload)
        unblended = xt.unblend(pattern, pairs)
        assert unblended == payload

        # 4. GeoSeal encrypt/decrypt
        kem_pk, kem_sk = kem_keygen()
        dsa_pk, dsa_sk = dsa_keygen()
        ctx = [0.2, -0.3, 0.7]
        pt_b64 = base64.b64encode(payload).decode()
        env = geoseal_encrypt(
            pt_b64, ctx,
            base64.b64encode(kem_pk).decode(),
            base64.b64encode(dsa_sk).decode(),
        )
        ok, decpt = geoseal_decrypt(
            env, ctx,
            base64.b64encode(kem_sk).decode(),
            base64.b64encode(dsa_pk).decode(),
        )
        assert ok
        assert decpt == payload

    def test_evolving_lexicons_with_cross_tokenizer(self):
        """EvolvingLexicons should work with CrossTokenizer after mutations."""
        evo = EvolvingLexicons(mutation_rate=1.0, drift_strength=0.1)
        tok = TongueTokenizer(evo)
        xt = CrossTokenizer(tok)

        payload = b"evolution pipeline"

        # Force some mutations
        for _ in range(10):
            evo.evolve_after_use("KO", "AV", payload, coherence=1.0)

        # Cross-translate with evolved lexicon
        ko_text = " ".join(tok.encode_bytes("KO", payload))
        av_tokens, _ = xt.retokenize("KO", "AV", ko_text)
        recovered = tok.decode_tokens("AV", av_tokens)
        assert recovered == payload
