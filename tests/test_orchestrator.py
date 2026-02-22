"""Tests for SCBE-AETHERMOORE Unified MCP Orchestrator

Tests the combined SCBE crypto + HYDRA swarm + SFT training tools.
Uses importlib to avoid mcp package name collision.
"""

import asyncio
import base64
import importlib.util
import json
import os
import sys
import tempfile

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_orch = _load_module(
    "orchestrator_mod",
    os.path.join(_PROJECT_ROOT, "mcp", "orchestrator.py"),
)


# ═══════════════════════════════════════════════════════════════════════════
# Tool Registration
# ═══════════════════════════════════════════════════════════════════════════


class TestToolRegistration:
    """Verify all 24 tools are registered on the unified server."""

    def test_total_tool_count(self):
        tools = _orch.mcp._tool_manager.list_tools()
        assert len(tools) == 24

    def test_scbe_tools_registered(self):
        names = {t.name for t in _orch.mcp._tool_manager.list_tools()}
        expected = [
            "tongue_encode", "tongue_decode", "cross_tokenize",
            "geoseal_seal", "geoseal_unseal", "ring_classify",
            "scbe_sacred_egg_create", "scbe_sacred_egg_hatch",
            "egg_paint", "egg_register", "cube_mint", "cube_verify",
        ]
        for n in expected:
            assert n in names, f"SCBE tool {n} missing"

    def test_hydra_tools_registered(self):
        names = {t.name for t in _orch.mcp._tool_manager.list_tools()}
        expected = [
            "hydra_swarm_launch", "hydra_swarm_run_task",
            "hydra_swarm_navigate", "hydra_swarm_screenshot",
            "hydra_swarm_get_content", "hydra_swarm_click",
            "hydra_swarm_type", "hydra_swarm_status",
        ]
        for n in expected:
            assert n in names, f"HYDRA tool {n} missing"

    def test_training_tools_registered(self):
        names = {t.name for t in _orch.mcp._tool_manager.list_tools()}
        expected = [
            "training_append_sft_record", "training_daily_summary",
            "training_list_waves", "training_export_dataset",
        ]
        for n in expected:
            assert n in names, f"Training tool {n} missing"


# ═══════════════════════════════════════════════════════════════════════════
# SCBE Crypto Tools (via orchestrator)
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchSCBE:
    """Test SCBE crypto tools through the unified orchestrator."""

    def test_tongue_roundtrip(self):
        original = b"orchestrator roundtrip"
        b64 = base64.b64encode(original).decode()
        encoded = json.loads(_orch.tongue_encode("KO", b64))
        assert encoded["token_count"] == len(original)

        tokens_text = " ".join(encoded["tokens"])
        decoded = json.loads(_orch.tongue_decode("KO", tokens_text))
        assert base64.b64decode(decoded["data_b64"]) == original

    def test_tongue_encode_bad_tongue(self):
        result = json.loads(_orch.tongue_encode("ZZ", base64.b64encode(b"x").decode()))
        assert "error" in result

    def test_cross_tokenize(self):
        b64 = base64.b64encode(b"cross test").decode()
        enc = json.loads(_orch.tongue_encode("RU", b64))
        tokens = " ".join(enc["tokens"])
        result = json.loads(_orch.cross_tokenize("RU", "DR", tokens))
        assert result["src"] == "RU"
        assert result["dst"] == "DR"
        assert result["attestation"]["hmac_attest"]

    def test_geoseal_roundtrip(self):
        pt = b"sealed data"
        pt_b64 = base64.b64encode(pt).decode()
        ctx = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

        sealed = _orch.geoseal_seal(pt_b64, ctx, kem, dsa)
        unsealed = json.loads(_orch.geoseal_unseal(sealed, ctx, kem, dsa))
        assert unsealed["success"] is True
        assert base64.b64decode(unsealed["plaintext_b64"]) == pt

    def test_ring_classify_all_rings(self):
        cases = [(0.05, "core"), (0.35, "inner"), (0.55, "middle"), (0.75, "outer"), (0.95, "edge")]
        for radius, expected_ring in cases:
            result = json.loads(_orch.ring_classify(radius))
            assert result["ring"] == expected_ring, f"radius {radius} expected {expected_ring} got {result['ring']}"


# ═══════════════════════════════════════════════════════════════════════════
# Sacred Egg Tools (via orchestrator)
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchEggs:
    """Test Sacred Egg tools through the unified orchestrator."""

    def _make_egg(self, payload=b"test yolk", tongue="KO", glyph="star"):
        ctx = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()
        egg_json = _orch.scbe_sacred_egg_create(
            payload_b64=base64.b64encode(payload).decode(),
            primary_tongue=tongue, glyph=glyph,
            hatch_condition_json="{}",
            context=ctx, pk_kem_b64=kem, sk_dsa_b64=dsa,
        )
        return egg_json, ctx, kem, dsa

    def test_egg_create(self):
        egg_json, _, _, _ = self._make_egg()
        egg = json.loads(egg_json)
        assert egg["egg_id"]
        assert egg["primary_tongue"] == "KO"
        assert egg["glyph"] == "star"

    def test_egg_hatch(self):
        egg_json, ctx, kem, dsa = self._make_egg(payload=b"hatch me")
        result = json.loads(_orch.scbe_sacred_egg_hatch(egg_json, ctx, "KO", kem, dsa))
        assert result["success"] is True
        assert len(result["tokens"]) == len(b"hatch me")

    def test_egg_paint(self):
        egg_json, _, _, _ = self._make_egg(glyph="plain")
        painted = json.loads(_orch.egg_paint(egg_json, glyph="golden"))
        assert painted["glyph"] == "golden"

    def test_egg_register(self):
        egg_json, _, _, _ = self._make_egg()
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "test.db")
            result = json.loads(_orch.egg_register(egg_json, ttl_seconds=600, db_path=db))
            assert result["status"] == "SEALED"
            assert result["egg_id"]

    def test_cube_mint_and_verify(self):
        ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()
        payloads = [base64.b64encode(f"ai-{i}".encode()).decode() for i in range(2)]

        result = json.loads(_orch.cube_mint(payloads, "AV", ctx, kem, dsa, kem, dsa))
        assert result["total"] == 2
        assert result["batch_id"]

        for cube in result["cubes"]:
            if cube:
                vr = json.loads(_orch.cube_verify(json.dumps(cube)))
                assert vr["valid"] is True


# ═══════════════════════════════════════════════════════════════════════════
# HYDRA Swarm Tools (via orchestrator)
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchSwarm:
    """Test HYDRA swarm tools through the unified orchestrator (dry-run)."""

    @pytest.mark.asyncio
    async def test_swarm_status_before_launch(self):
        old = _orch._swarm
        _orch._swarm = None
        try:
            result = json.loads(await _orch.hydra_swarm_status())
            assert result["launched"] is False
        finally:
            _orch._swarm = old

    @pytest.mark.asyncio
    async def test_swarm_launch_dry(self):
        result = json.loads(await _orch.hydra_swarm_launch(dry_run=True))
        assert result["launched"] is True
        assert result["dry_run"] is True
        assert len(result["agents"]) == 6

    @pytest.mark.asyncio
    async def test_swarm_navigate_dry(self):
        await _orch.hydra_swarm_launch(dry_run=True)
        result = json.loads(await _orch.hydra_swarm_navigate("https://example.com"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_swarm_execute_task_dry(self):
        await _orch.hydra_swarm_launch(dry_run=True)
        result = json.loads(await _orch.hydra_swarm_run_task("search for SCBE"))
        assert "results" in result


# ═══════════════════════════════════════════════════════════════════════════
# SFT Training Tools
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchTraining:
    """Test SFT training data collection tools."""

    def test_sft_auto_recording(self):
        """Tool calls should auto-record SFT data."""
        # Call a tool — it should write an SFT record
        _orch.tongue_encode("KO", base64.b64encode(b"sft test").decode())
        summary = json.loads(_orch.training_daily_summary())
        assert summary["total_records"] > 0
        assert "tongue_encode" in summary["by_tool"]

    def test_manual_sft_record(self):
        result = json.loads(_orch.training_append_sft_record(
            tool_name="test_tool",
            instruction="What is SCBE?",
            response="SCBE is a governance framework",
            score=0.95,
        ))
        assert result["recorded"] is True

    def test_training_list_waves(self):
        result = json.loads(_orch.training_list_waves())
        assert result["wave_count"] >= 1
        assert result["waves"][0]["file"].startswith("sft_")

    def test_training_export_jsonl(self):
        result = json.loads(_orch.training_export_dataset(format="jsonl"))
        assert result["exported"] is True
        assert result["total_records"] > 0
        assert result["file"].endswith(".jsonl")

    def test_training_export_json(self):
        result = json.loads(_orch.training_export_dataset(format="json"))
        assert result["exported"] is True
        assert result["file"].endswith(".json")

    def test_daily_summary_structure(self):
        summary = json.loads(_orch.training_daily_summary())
        assert "date" in summary
        assert "total_records" in summary
        assert "by_tool" in summary


# ═══════════════════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchResources:
    """Test resource endpoints on the orchestrator."""

    def test_tongues_resource(self):
        data = json.loads(_orch.resource_tongues())
        assert len(data) == 6
        codes = {t["code"] for t in data}
        assert codes == {"KO", "AV", "RU", "CA", "UM", "DR"}

    def test_rings_resource(self):
        data = json.loads(_orch.resource_rings())
        assert len(data) == 5
        names = {r["ring"] for r in data}
        assert "core" in names
        assert "edge" in names
