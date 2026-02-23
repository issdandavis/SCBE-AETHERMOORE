"""Sacred Egg Integrator Tests — Chapter 7 Ritual-Based Secret Distribution

Tests cover:
  - SacredEgg create/serialize/deserialize
  - Solitary hatch: matching tongue succeeds, mismatch fails
  - Triadic hatch: phi-weight threshold, tongue count
  - Ring descent: monotonic inward path, core requirement
  - Fail-to-noise: indistinguishable output on any failure
  - Cross-tokenization: agent tongue != primary tongue
  - Context binding: wrong context fails GeoSeal decrypt
  - GeoSeal roundtrip: encrypt → hatch with correct context

@layer Layer 12, Layer 13
@component Sacred Egg Integrator Tests
"""

import base64
import json
import os

import pytest

from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    CrossTokenizer,
    TongueTokenizer,
    Lexicons,
    ConcentricRingPolicy,
    TONGUES,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_integrator import (
    SacredEgg,
    SacredEggIntegrator,
    HatchResult,
    context_radius,
    _RING_ORDER,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def xt():
    """CrossTokenizer with default lexicons."""
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    return CrossTokenizer(tok)


@pytest.fixture
def integrator(xt):
    """SacredEggIntegrator instance."""
    return SacredEggIntegrator(xt)


@pytest.fixture
def key_pair():
    """Deterministic KEM/DSA key pair for tests (base64)."""
    # Demo stubs: pk == sk for simplicity (cli_toolkit uses HMAC-based mocks)
    pk = base64.b64encode(os.urandom(32)).decode()
    sk = pk  # In the demo stub, pk/sk are interchangeable
    return pk, sk


@pytest.fixture
def interior_context():
    """A context vector that classifies as 'interior' path.

    First 3 values equal → zscore zeros → u=[0,0,0] → P < 0.6.
    Last 3 negative → cube projection < 0.2 → T high.
    Result: path=interior, ring=inner, r≈0.31.
    """
    return [0.0, 0.0, 0.0, -5.0, -5.0, -5.0]


@pytest.fixture
def egg_solitary(integrator, key_pair, interior_context):
    """A solitary Sacred Egg bound to KO tongue, inner ring, interior path."""
    pk, sk = key_pair
    return integrator.create_egg(
        payload=b"Hello, Sacred World!",
        primary_tongue="KO",
        glyph="diamond",
        hatch_condition={"path": "interior"},
        context=interior_context,
        pk_kem_b64=pk,
        sk_dsa_b64=sk,
    )


# =============================================================================
# SacredEgg Creation
# =============================================================================


class TestSacredEggCreation:
    """Tests for egg creation and structure."""

    def test_create_egg_fields(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        egg = integrator.create_egg(
            payload=b"test payload",
            primary_tongue="KO",
            glyph="diamond",
            hatch_condition={"ring": "inner"},
            context=interior_context,
            pk_kem_b64=pk,
            sk_dsa_b64=sk,
        )

        assert len(egg.egg_id) == 16
        assert egg.primary_tongue == "KO"
        assert egg.glyph == "diamond"
        assert egg.hatch_condition == {"ring": "inner"}
        assert "ct_k" in egg.yolk_ct
        assert "ct_spec" in egg.yolk_ct
        assert "attest" in egg.yolk_ct
        assert "sig" in egg.yolk_ct

    def test_create_egg_rejects_unknown_tongue(self, integrator, key_pair):
        pk, sk = key_pair
        with pytest.raises(ValueError, match="Unknown tongue"):
            integrator.create_egg(
                payload=b"test",
                primary_tongue="XX",
                glyph="?",
                hatch_condition={},
                context=[0.0] * 6,
                pk_kem_b64=pk,
                sk_dsa_b64=sk,
            )

    def test_different_payloads_different_ids(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        egg1 = integrator.create_egg(b"payload A", "KO", "a", {}, interior_context, pk, sk)
        egg2 = integrator.create_egg(b"payload B", "KO", "b", {}, interior_context, pk, sk)
        assert egg1.egg_id != egg2.egg_id

    def test_all_six_tongues(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        for tongue in TONGUES:
            egg = integrator.create_egg(b"test", tongue, "g", {}, interior_context, pk, sk)
            assert egg.primary_tongue == tongue


# =============================================================================
# Serialization
# =============================================================================


class TestSerialization:
    """Tests for JSON serialization roundtrip."""

    def test_to_json_roundtrip(self, integrator, egg_solitary):
        json_str = integrator.to_json(egg_solitary)
        restored = integrator.from_json(json_str)

        assert restored.egg_id == egg_solitary.egg_id
        assert restored.primary_tongue == egg_solitary.primary_tongue
        assert restored.glyph == egg_solitary.glyph
        assert restored.hatch_condition == egg_solitary.hatch_condition
        assert restored.yolk_ct == egg_solitary.yolk_ct

    def test_json_is_valid(self, integrator, egg_solitary):
        json_str = integrator.to_json(egg_solitary)
        parsed = json.loads(json_str)
        assert "egg_id" in parsed
        assert "yolk_ct" in parsed


# =============================================================================
# Solitary Ritual
# =============================================================================


class TestSolitaryRitual:
    """Tests for solitary hatch mode: tongue must match."""

    def test_matching_tongue_succeeds(self, integrator, egg_solitary, key_pair, interior_context):
        pk, sk = key_pair
        result = integrator.hatch_egg(
            egg_solitary, interior_context, "KO", sk, pk, ritual_mode="solitary"
        )
        assert result.success is True
        assert result.reason == "hatched"
        assert result.tokens is not None
        assert len(result.tokens) > 0
        assert result.attestation is not None

    def test_wrong_tongue_fails(self, integrator, egg_solitary, key_pair, interior_context):
        pk, sk = key_pair
        result = integrator.hatch_egg(
            egg_solitary, interior_context, "DR", sk, pk, ritual_mode="solitary"
        )
        assert result.success is False
        assert result.reason == "sealed"
        assert result.tokens is not None  # noise tokens, not None

    def test_all_wrong_tongues_fail(self, integrator, egg_solitary, key_pair, interior_context):
        pk, sk = key_pair
        for tongue in ["AV", "RU", "CA", "UM", "DR"]:
            result = integrator.hatch_egg(
                egg_solitary, interior_context, tongue, sk, pk, ritual_mode="solitary"
            )
            assert result.success is False
            assert result.reason == "sealed"


# =============================================================================
# Triadic Ritual
# =============================================================================


class TestTriadicRitual:
    """Tests for triadic hatch mode: 3+ tongues with phi-weight threshold."""

    @pytest.fixture
    def egg_triadic(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        return integrator.create_egg(
            payload=b"triadic secret",
            primary_tongue="KO",
            glyph="triangle",
            hatch_condition={
                "path": "interior",
                "min_tongues": 3,
                "min_weight": 10.0,
            },
            context=interior_context,
            pk_kem_b64=pk,
            sk_dsa_b64=sk,
        )

    def test_sufficient_tongues_and_weight(self, integrator, egg_triadic, key_pair, interior_context):
        pk, sk = key_pair
        # KO(1.0) + RU(2.618) + UM(6.854) = 10.472 >= 10.0
        result = integrator.hatch_egg(
            egg_triadic, interior_context, "KO", sk, pk,
            ritual_mode="triadic",
            additional_tongues=["RU", "UM"],
        )
        assert result.success is True
        assert result.reason == "hatched"

    def test_insufficient_tongues(self, integrator, egg_triadic, key_pair, interior_context):
        pk, sk = key_pair
        # Only 2 tongues (KO + AV), need 3
        result = integrator.hatch_egg(
            egg_triadic, interior_context, "KO", sk, pk,
            ritual_mode="triadic",
            additional_tongues=["AV"],
        )
        assert result.success is False

    def test_insufficient_weight(self, integrator, egg_triadic, key_pair, interior_context):
        pk, sk = key_pair
        # KO(1.0) + AV(1.618) + RU(2.618) = 5.236 < 10.0
        result = integrator.hatch_egg(
            egg_triadic, interior_context, "KO", sk, pk,
            ritual_mode="triadic",
            additional_tongues=["AV", "RU"],
        )
        assert result.success is False

    def test_heavy_tongues_pass(self, integrator, egg_triadic, key_pair, interior_context):
        pk, sk = key_pair
        # KO(1.0) + UM(6.854) + DR(11.090) = 18.944 >= 10.0
        result = integrator.hatch_egg(
            egg_triadic, interior_context, "KO", sk, pk,
            ritual_mode="triadic",
            additional_tongues=["UM", "DR"],
        )
        assert result.success is True


# =============================================================================
# Ring Descent Ritual
# =============================================================================


class TestRingDescentRitual:
    """Tests for ring_descent mode: monotonic inward path to core."""

    @pytest.fixture
    def egg_descent(self, integrator, key_pair):
        pk, sk = key_pair
        # Context that maps to core ring (r < 0.3)
        # All zeros → tanh(0/5) = 0, (0+1)/2 = 0.5 → avg = 0.5 → middle ring
        # Need context that gives low radius. Try large negative values:
        # tanh(-10/5) = tanh(-2) ≈ -0.964, (-0.964+1)/2 ≈ 0.018
        core_context = [-10.0, -10.0, -10.0, -10.0, -10.0, -10.0]
        return integrator.create_egg(
            payload=b"descent secret",
            primary_tongue="DR",
            glyph="spiral",
            hatch_condition={"ring": "core"},
            context=core_context,
            pk_kem_b64=pk,
            sk_dsa_b64=sk,
        ), core_context

    def test_valid_descent(self, integrator, egg_descent, key_pair):
        pk, sk = key_pair
        egg, ctx = egg_descent
        result = integrator.hatch_egg(
            egg, ctx, "DR", sk, pk,
            ritual_mode="ring_descent",
            path_history=[
                {"ring": "outer"},
                {"ring": "middle"},
                {"ring": "inner"},
                {"ring": "core"},
            ],
        )
        assert result.success is True
        assert result.reason == "hatched"

    def test_non_monotonic_path_fails(self, integrator, egg_descent, key_pair):
        pk, sk = key_pair
        egg, ctx = egg_descent
        # Goes outward: outer → edge (wrong direction)
        result = integrator.hatch_egg(
            egg, ctx, "DR", sk, pk,
            ritual_mode="ring_descent",
            path_history=[
                {"ring": "outer"},
                {"ring": "edge"},  # went outward, not inward
            ],
        )
        assert result.success is False

    def test_empty_history_fails(self, integrator, egg_descent, key_pair):
        pk, sk = key_pair
        egg, ctx = egg_descent
        result = integrator.hatch_egg(
            egg, ctx, "DR", sk, pk,
            ritual_mode="ring_descent",
            path_history=[],
        )
        assert result.success is False

    def test_not_at_core_fails(self, integrator, key_pair):
        pk, sk = key_pair
        # Context that gives middle ring (r ≈ 0.5)
        middle_context = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        egg = integrator.create_egg(
            payload=b"test",
            primary_tongue="DR",
            glyph="s",
            hatch_condition={"ring": "core"},
            context=middle_context,
            pk_kem_b64=pk,
            sk_dsa_b64=sk,
        )
        result = integrator.hatch_egg(
            egg, middle_context, "DR", sk, pk,
            ritual_mode="ring_descent",
            path_history=[{"ring": "outer"}, {"ring": "inner"}, {"ring": "core"}],
        )
        # Context puts us at middle ring, not core
        assert result.success is False


# =============================================================================
# Fail-to-Noise
# =============================================================================


class TestFailToNoise:
    """Theorem 7.1: all failure modes return identically-structured output."""

    def test_noise_has_tokens(self, integrator, egg_solitary, key_pair, interior_context):
        pk, sk = key_pair
        # Wrong tongue → fail
        result = integrator.hatch_egg(
            egg_solitary, interior_context, "DR", sk, pk, ritual_mode="solitary"
        )
        assert result.success is False
        assert result.tokens is not None
        assert len(result.tokens) > 0

    def test_noise_same_token_count(self, integrator, key_pair, interior_context):
        """Noise tokens have same count as real output."""
        pk, sk = key_pair
        payload = b"exactly twenty bytes"
        egg = integrator.create_egg(payload, "KO", "d", {"path": "interior"},
                                     interior_context, pk, sk)

        # Successful hatch
        ok_result = integrator.hatch_egg(
            egg, interior_context, "KO", sk, pk, ritual_mode="solitary"
        )
        # Failed hatch (wrong tongue)
        fail_result = integrator.hatch_egg(
            egg, interior_context, "DR", sk, pk, ritual_mode="solitary"
        )

        assert ok_result.success is True
        assert fail_result.success is False
        # Both should have same number of tokens (same byte length)
        assert len(ok_result.tokens) == len(fail_result.tokens)

    def test_noise_reason_is_sealed(self, integrator, egg_solitary, key_pair, interior_context):
        """All failures say 'sealed' — never reveals which predicate failed."""
        pk, sk = key_pair
        result = integrator.hatch_egg(
            egg_solitary, interior_context, "UM", sk, pk, ritual_mode="solitary"
        )
        assert result.reason == "sealed"

    def test_unknown_ritual_mode_fails(self, integrator, egg_solitary, key_pair, interior_context):
        pk, sk = key_pair
        result = integrator.hatch_egg(
            egg_solitary, interior_context, "KO", sk, pk, ritual_mode="unknown_mode"
        )
        assert result.success is False
        assert result.reason == "sealed"


# =============================================================================
# Cross-Tokenization
# =============================================================================


class TestCrossTokenization:
    """When agent tongue != egg's primary tongue, tokens are retokenized."""

    def test_cross_tongue_hatch(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        # Create egg in KO, hatch as triadic (so tongue match isn't required)
        egg = integrator.create_egg(
            payload=b"cross-tongue test",
            primary_tongue="KO",
            glyph="x",
            hatch_condition={"path": "interior", "min_tongues": 1, "min_weight": 0.0},
            context=interior_context,
            pk_kem_b64=pk,
            sk_dsa_b64=sk,
        )
        # Hatch in UM tongue via triadic with minimal requirements
        result = integrator.hatch_egg(
            egg, interior_context, "UM", sk, pk,
            ritual_mode="triadic",
            additional_tongues=[],
        )
        assert result.success is True
        assert result.attestation is not None
        assert "xlate" in result.attestation

        # Verify attestation contains cross-tongue info
        xlate = result.attestation["xlate"]
        assert xlate["src"] == "KO"
        assert xlate["dst"] == "UM"

    def test_same_tongue_no_xlate(self, integrator, egg_solitary, key_pair, interior_context):
        pk, sk = key_pair
        result = integrator.hatch_egg(
            egg_solitary, interior_context, "KO", sk, pk, ritual_mode="solitary"
        )
        assert result.success is True
        # No xlate when tongues match
        assert "xlate" not in result.attestation


# =============================================================================
# Context Binding
# =============================================================================


class TestContextBinding:
    """GeoSeal context binding: wrong context fails decrypt."""

    def test_wrong_context_fails(self, integrator, egg_solitary, key_pair):
        pk, sk = key_pair
        # Completely different context
        wrong_context = [9.9, -9.9, 9.9, -9.9, 9.9, -9.9]
        result = integrator.hatch_egg(
            egg_solitary, wrong_context, "KO", sk, pk, ritual_mode="solitary"
        )
        # GeoSeal decrypt will fail (different h/z) → sealed
        assert result.success is False
        assert result.reason == "sealed"


# =============================================================================
# Context Radius + Ring Policy
# =============================================================================


class TestContextRadius:
    """Test context_radius() and ring classification."""

    def test_zero_context_gives_middle(self):
        # tanh(0/5) = 0, (0+1)/2 = 0.5 → avg = 0.5 → middle ring
        r = context_radius([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert 0.49 < r < 0.51
        policy = ConcentricRingPolicy()
        ring = policy.classify(r)
        assert ring["ring"] == "middle"

    def test_large_negative_gives_core(self):
        # tanh(-10/5) ≈ -0.964, (-0.964+1)/2 ≈ 0.018
        r = context_radius([-10.0] * 6)
        assert r < 0.1
        policy = ConcentricRingPolicy()
        ring = policy.classify(r)
        assert ring["ring"] == "core"

    def test_large_positive_gives_edge(self):
        # tanh(10/5) ≈ 0.964, (0.964+1)/2 ≈ 0.982
        r = context_radius([10.0] * 6)
        assert r > 0.9
        policy = ConcentricRingPolicy()
        ring = policy.classify(r)
        assert ring["ring"] == "edge"

    def test_clamped_below_one(self):
        r = context_radius([100.0] * 6)
        assert r < 1.0


# =============================================================================
# GeoSeal Roundtrip
# =============================================================================


class TestGeoSealRoundtrip:
    """End-to-end encrypt → hatch with correct conditions."""

    def test_full_roundtrip(self, integrator, key_pair, interior_context, xt):
        pk, sk = key_pair
        payload = b"The dragon egg hatches!"
        egg = integrator.create_egg(
            payload, "RU", "star", {"path": "interior"},
            interior_context, pk, sk,
        )

        result = integrator.hatch_egg(
            egg, interior_context, "RU", sk, pk, ritual_mode="solitary"
        )
        assert result.success is True

        # Decode tokens back to bytes and verify payload
        recovered = xt.tok.decode_tokens("RU", result.tokens)
        assert recovered == payload

    def test_roundtrip_all_tongues(self, integrator, key_pair, interior_context, xt):
        pk, sk = key_pair
        payload = b"universal payload"
        for tongue in TONGUES:
            egg = integrator.create_egg(
                payload, tongue, "g", {"path": "interior"},
                interior_context, pk, sk,
            )
            result = integrator.hatch_egg(
                egg, interior_context, tongue, sk, pk, ritual_mode="solitary"
            )
            assert result.success is True, f"Failed for tongue {tongue}"
            recovered = xt.tok.decode_tokens(tongue, result.tokens)
            assert recovered == payload, f"Payload mismatch for tongue {tongue}"


# =============================================================================
# Egg Painting — Easter egg customization
# =============================================================================


class TestPaintEgg:
    """Paint an egg: change the shell, keep the yolk intact."""

    def test_paint_glyph(self, integrator, egg_solitary):
        painted = integrator.paint_egg(egg_solitary, glyph="easter_bunny")
        assert painted.glyph == "easter_bunny"
        # Yolk untouched
        assert painted.yolk_ct == egg_solitary.yolk_ct
        assert painted.egg_id == egg_solitary.egg_id
        assert painted.primary_tongue == egg_solitary.primary_tongue

    def test_paint_hatch_condition(self, integrator, egg_solitary):
        new_cond = {"ring": "outer", "path": "exterior"}
        painted = integrator.paint_egg(egg_solitary, hatch_condition=new_cond)
        assert painted.hatch_condition == new_cond
        assert painted.glyph == egg_solitary.glyph  # unchanged
        assert painted.yolk_ct == egg_solitary.yolk_ct  # yolk untouched

    def test_paint_both(self, integrator, egg_solitary):
        painted = integrator.paint_egg(
            egg_solitary, glyph="golden", hatch_condition={"min_tongues": 5}
        )
        assert painted.glyph == "golden"
        assert painted.hatch_condition == {"min_tongues": 5}
        assert painted.yolk_ct == egg_solitary.yolk_ct

    def test_paint_none_keeps_original(self, integrator, egg_solitary):
        painted = integrator.paint_egg(egg_solitary)
        assert painted.glyph == egg_solitary.glyph
        assert painted.hatch_condition == egg_solitary.hatch_condition
        assert painted.yolk_ct == egg_solitary.yolk_ct

    def test_painted_egg_still_hatches(self, integrator, key_pair, interior_context, xt):
        """A painted egg should still hatch with correct conditions."""
        pk, sk = key_pair
        payload = b"paint me red"
        egg = integrator.create_egg(
            payload, "KO", "plain", {"path": "interior"},
            interior_context, pk, sk,
        )
        painted = integrator.paint_egg(egg, glyph="red_sparkle")

        result = integrator.hatch_egg(
            painted, interior_context, "KO", sk, pk, ritual_mode="solitary"
        )
        assert result.success is True
        recovered = xt.tok.decode_tokens("KO", result.tokens)
        assert recovered == payload

    def test_shell_property_reflects_paint(self, integrator, egg_solitary):
        painted = integrator.paint_egg(egg_solitary, glyph="striped")
        shell = painted.shell
        assert shell["glyph"] == "striped"
        assert shell["egg_id"] == egg_solitary.egg_id

    def test_whole_property_preserves_yolk(self, integrator, egg_solitary):
        painted = integrator.paint_egg(egg_solitary, glyph="galaxy")
        whole = painted.whole
        original_whole = egg_solitary.whole
        # Yolk (encrypted payload) identical
        assert whole["yolk"] == original_whole["yolk"]
        assert whole["white"] == original_whole["white"]
        assert whole["sig"] == original_whole["sig"]
        # Shell changed
        assert whole["shell"]["glyph"] == "galaxy"


# =============================================================================
# CLI Commands (egg-create, egg-hatch, egg-paint)
# =============================================================================


class TestCLIEggCommands:
    """Test the CLI handler functions directly."""

    def test_cmd_egg_create(self, tmp_path, interior_context, key_pair):
        """egg-create writes valid JSON with all egg fields."""
        import argparse
        from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import cmd_egg_create

        pk, sk = key_pair
        outfile = str(tmp_path / "egg.json")
        args = argparse.Namespace(
            payload_b64=base64.b64encode(b"CLI test payload").decode(),
            primary_tongue="AV",
            glyph="star",
            hatch_condition=json.dumps({"path": "interior"}),
            context=json.dumps(interior_context),
            kem_key=pk,
            dsa_key=sk,
            outfile=outfile,
        )
        cmd_egg_create(args)

        data = json.loads(open(outfile).read())
        assert "egg_id" in data
        assert data["primary_tongue"] == "AV"
        assert data["glyph"] == "star"
        assert "yolk_ct" in data

    def test_cmd_egg_hatch_success(self, tmp_path, interior_context, key_pair, capsys):
        """egg-hatch with correct conditions prints success JSON."""
        import argparse
        from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
            cmd_egg_create,
            cmd_egg_hatch,
        )

        pk, sk = key_pair
        egg_file = str(tmp_path / "egg.json")

        # Create egg
        create_args = argparse.Namespace(
            payload_b64=base64.b64encode(b"hatch me").decode(),
            primary_tongue="KO",
            glyph="test",
            hatch_condition=json.dumps({"path": "interior"}),
            context=json.dumps(interior_context),
            kem_key=pk,
            dsa_key=sk,
            outfile=egg_file,
        )
        cmd_egg_create(create_args)

        # Hatch egg
        hatch_args = argparse.Namespace(
            egg_json=egg_file,
            agent_tongue="KO",
            ritual_mode="solitary",
            additional_tongues="[]",
            path_history="[]",
            context=json.dumps(interior_context),
            kem_key=sk,
            dsa_pk=pk,
            lexicons=None,
        )
        cmd_egg_hatch(hatch_args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] is True
        assert result["reason"] == "hatched"
        assert len(result["tokens"]) > 0

    def test_cmd_egg_hatch_failure_exits_1(self, tmp_path, interior_context, key_pair):
        """egg-hatch with wrong tongue exits with code 1."""
        import argparse
        from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
            cmd_egg_create,
            cmd_egg_hatch,
        )

        pk, sk = key_pair
        egg_file = str(tmp_path / "egg.json")

        create_args = argparse.Namespace(
            payload_b64=base64.b64encode(b"sealed").decode(),
            primary_tongue="KO",
            glyph="locked",
            hatch_condition=json.dumps({"path": "interior"}),
            context=json.dumps(interior_context),
            kem_key=pk,
            dsa_key=sk,
            outfile=egg_file,
        )
        cmd_egg_create(create_args)

        hatch_args = argparse.Namespace(
            egg_json=egg_file,
            agent_tongue="DR",  # wrong tongue
            ritual_mode="solitary",
            additional_tongues="[]",
            path_history="[]",
            context=json.dumps(interior_context),
            kem_key=sk,
            dsa_pk=pk,
            lexicons=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_egg_hatch(hatch_args)
        assert exc_info.value.code == 1

    def test_cmd_egg_paint(self, tmp_path, interior_context, key_pair, capsys):
        """egg-paint changes glyph, keeps yolk intact."""
        import argparse
        from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
            cmd_egg_create,
            cmd_egg_paint,
        )

        pk, sk = key_pair
        egg_file = str(tmp_path / "egg.json")
        painted_file = str(tmp_path / "painted.json")

        # Create original egg
        create_args = argparse.Namespace(
            payload_b64=base64.b64encode(b"paint me").decode(),
            primary_tongue="RU",
            glyph="plain",
            hatch_condition=json.dumps({}),
            context=json.dumps(interior_context),
            kem_key=pk,
            dsa_key=sk,
            outfile=egg_file,
        )
        cmd_egg_create(create_args)

        # Paint the egg
        paint_args = argparse.Namespace(
            egg_json=egg_file,
            glyph="rainbow_sparkle",
            hatch_condition=None,
            outfile=painted_file,
        )
        cmd_egg_paint(paint_args)

        original = json.loads(open(egg_file).read())
        painted = json.loads(open(painted_file).read())

        # Shell changed
        assert painted["glyph"] == "rainbow_sparkle"
        # Yolk untouched
        assert painted["yolk_ct"] == original["yolk_ct"]
        assert painted["egg_id"] == original["egg_id"]

    def test_cmd_egg_paint_hatch_condition(self, tmp_path, interior_context, key_pair):
        """egg-paint can change hatch conditions."""
        import argparse
        from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
            cmd_egg_create,
            cmd_egg_paint,
        )

        pk, sk = key_pair
        egg_file = str(tmp_path / "egg.json")
        painted_file = str(tmp_path / "painted.json")

        create_args = argparse.Namespace(
            payload_b64=base64.b64encode(b"recondition").decode(),
            primary_tongue="CA",
            glyph="egg",
            hatch_condition=json.dumps({"ring": "inner"}),
            context=json.dumps(interior_context),
            kem_key=pk,
            dsa_key=sk,
            outfile=egg_file,
        )
        cmd_egg_create(create_args)

        paint_args = argparse.Namespace(
            egg_json=egg_file,
            glyph=None,
            hatch_condition=json.dumps({"ring": "outer", "min_tongues": 4}),
            outfile=painted_file,
        )
        cmd_egg_paint(paint_args)

        painted = json.loads(open(painted_file).read())
        assert painted["hatch_condition"] == {"ring": "outer", "min_tongues": 4}
        assert painted["glyph"] == "egg"  # unchanged
