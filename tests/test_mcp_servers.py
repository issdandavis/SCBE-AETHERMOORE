"""Tests for SCBE MCP Servers

Tests tool functions directly (bypasses MCP transport) and verifies
FastMCP tool registration for all three servers.
"""

import asyncio
import base64
import importlib.util
import json
import os
import sys
import tempfile

import pytest

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Import helpers — load server modules by file path to avoid collision
# with the installed `mcp` package.
# ---------------------------------------------------------------------------

def _load_module(name: str, path: str):
    """Load a Python module from an absolute file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_scbe_mod = _load_module(
    "scbe_server",
    os.path.join(_PROJECT_ROOT, "mcp", "scbe_server.py"),
)
_notion_mod = _load_module(
    "notion_server",
    os.path.join(_PROJECT_ROOT, "mcp", "notion_server.py"),
)
_swarm_mod = _load_module(
    "swarm_server",
    os.path.join(_PROJECT_ROOT, "mcp", "swarm_server.py"),
)


# ═══════════════════════════════════════════════════════════════════════════
# SCBE Server Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSCBEServer:
    """Test the SCBE Cryptographic Toolkit MCP server tools."""

    def test_tongue_encode_decode_roundtrip(self):
        original = b"hello sacred tongues"
        b64 = base64.b64encode(original).decode()

        for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
            encoded = json.loads(_scbe_mod.tongue_encode(tongue, b64))
            assert "tokens" in encoded
            assert encoded["token_count"] == len(original)

            tokens_text = " ".join(encoded["tokens"])
            decoded = json.loads(_scbe_mod.tongue_decode(tongue, tokens_text))
            assert decoded["data_b64"] == b64
            assert decoded["byte_count"] == len(original)

    def test_tongue_encode_invalid_tongue(self):
        result = json.loads(_scbe_mod.tongue_encode("XX", base64.b64encode(b"test").decode()))
        assert "error" in result

    def test_cross_tokenize(self):
        original = b"cross-tongue test"
        b64 = base64.b64encode(original).decode()

        encoded = json.loads(_scbe_mod.tongue_encode("KO", b64))
        tokens_text = " ".join(encoded["tokens"])

        result = json.loads(_scbe_mod.cross_tokenize("KO", "AV", tokens_text))
        assert result["src"] == "KO"
        assert result["dst"] == "AV"
        assert "tokens" in result
        assert "attestation" in result
        assert result["attestation"]["hmac_attest"]

    def test_geoseal_roundtrip(self):
        plaintext = b"secret payload"
        pt_b64 = base64.b64encode(plaintext).decode()
        ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

        sealed = _scbe_mod.geoseal_seal(pt_b64, ctx, kem, dsa)
        env = json.loads(sealed)
        assert "ct_k" in env
        assert "ct_spec" in env

        unsealed = json.loads(_scbe_mod.geoseal_unseal(sealed, ctx, kem, dsa))
        assert unsealed["success"] is True
        assert base64.b64decode(unsealed["plaintext_b64"]) == plaintext

    def test_ring_classify(self):
        core = json.loads(_scbe_mod.ring_classify(0.1))
        assert core["ring"] == "core"

        edge = json.loads(_scbe_mod.ring_classify(0.95))
        assert edge["ring"] == "edge"

        middle = json.loads(_scbe_mod.ring_classify(0.6))
        assert middle["ring"] == "middle"

    def test_egg_create_and_hatch(self):
        payload = b"egg yolk data"
        ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

        egg_json = _scbe_mod.egg_create(
            payload_b64=base64.b64encode(payload).decode(),
            primary_tongue="KO",
            glyph="diamond",
            hatch_condition_json=json.dumps({}),
            context=ctx,
            pk_kem_b64=kem,
            sk_dsa_b64=dsa,
        )
        egg = json.loads(egg_json)
        assert egg["egg_id"]
        assert egg["primary_tongue"] == "KO"
        assert egg["glyph"] == "diamond"

        # Hatch with matching tongue
        result = json.loads(_scbe_mod.egg_hatch(egg_json, ctx, "KO", kem, dsa))
        assert result["success"] is True
        assert result["reason"] == "hatched"
        assert len(result["tokens"]) == len(payload)

    def test_egg_paint(self):
        ctx = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

        egg_json = _scbe_mod.egg_create(
            payload_b64=base64.b64encode(b"paint me").decode(),
            primary_tongue="AV",
            glyph="plain",
            hatch_condition_json="{}",
            context=ctx,
            pk_kem_b64=kem,
            sk_dsa_b64=dsa,
        )

        painted_json = _scbe_mod.egg_paint(egg_json, glyph="golden")
        painted = json.loads(painted_json)
        assert painted["glyph"] == "golden"
        assert painted["primary_tongue"] == "AV"
        assert painted["egg_id"] == json.loads(egg_json)["egg_id"]

    def test_egg_register(self):
        ctx = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

        egg_json = _scbe_mod.egg_create(
            payload_b64=base64.b64encode(b"register me").decode(),
            primary_tongue="RU",
            glyph="iron",
            hatch_condition_json="{}",
            context=ctx,
            pk_kem_b64=kem,
            sk_dsa_b64=dsa,
        )

        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_eggs.db")
            result = json.loads(_scbe_mod.egg_register(egg_json, ttl_seconds=3600, db_path=db_path))
            assert result["status"] == "SEALED"
            assert result["egg_id"]

    def test_cube_mint_and_verify(self):
        ctx = [0.2, -0.3, 0.7, 1.0, -2.0, 0.5]
        kem = base64.b64encode(b"kem-key-32bytes-demo____").decode()
        dsa = base64.b64encode(b"dsa-key-32bytes-demo____").decode()

        payloads = [base64.b64encode(f"ai-{i}".encode()).decode() for i in range(3)]
        result = json.loads(_scbe_mod.cube_mint(
            payloads_b64=payloads,
            tongue="KO",
            context=ctx,
            pk_kem_b64=kem,
            sk_dsa_b64=dsa,
            sk_kem_b64=kem,
            pk_dsa_b64=dsa,
        ))
        assert result["total"] == 3
        assert result["batch_id"]

        for cube_data in result["cubes"]:
            if cube_data is not None:
                verify_result = json.loads(_scbe_mod.cube_verify(json.dumps(cube_data)))
                assert verify_result["valid"] is True

    def test_tool_registration(self):
        tool_names = [t.name for t in _scbe_mod.mcp._tool_manager.list_tools()]
        expected = [
            "tongue_encode", "tongue_decode", "cross_tokenize",
            "geoseal_seal", "geoseal_unseal", "ring_classify",
            "egg_create", "egg_hatch", "egg_paint", "egg_register",
            "cube_mint", "cube_verify",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"


# ═══════════════════════════════════════════════════════════════════════════
# Notion Server Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestNotionServer:
    """Test the Notion Workspace Sweeper MCP server tools."""

    def test_index_resource(self):
        content = _notion_mod.resource_index()
        assert "SCBE-AETHERMOORE" in content
        assert "Notion" in content

    def test_list_pages(self):
        result = json.loads(_notion_mod.notion_list_pages())
        assert "count" in result
        assert "pages" in result
        assert result["count"] > 0

    def test_list_pages_with_filter(self):
        result = json.loads(_notion_mod.notion_list_pages(status_filter="BUILT"))
        assert "count" in result
        for page in result["pages"]:
            combined = (page.get("status", "") + page.get("gap", "")).lower()
            assert "built" in combined

    @pytest.mark.asyncio
    async def test_search_cached(self):
        result = json.loads(await _notion_mod.notion_search("Sacred Egg"))
        assert result["source"] == "cached_index"
        assert result["count"] > 0

    def test_gap_analysis(self):
        result = json.loads(_notion_mod.notion_gap_analysis())
        assert "summary" in result
        assert result["summary"]["total"] > 0
        assert "built" in result
        assert "not_built" in result

    def test_refresh_index(self):
        result = json.loads(_notion_mod.notion_refresh_index())
        assert result["refreshed"] is True
        assert result["page_count"] > 0

    def test_tool_registration(self):
        tool_names = [t.name for t in _notion_mod.mcp._tool_manager.list_tools()]
        expected = [
            "notion_search", "notion_fetch_page", "notion_list_pages",
            "notion_gap_analysis", "notion_refresh_index",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"


# ═══════════════════════════════════════════════════════════════════════════
# Swarm Server Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSwarmServer:
    """Test the HYDRA Swarm Browser Control MCP server tools."""

    @pytest.mark.asyncio
    async def test_swarm_launch_dry_run(self):
        result = json.loads(await _swarm_mod.swarm_launch(dry_run=True))
        assert result["launched"] is True
        assert result["dry_run"] is True
        assert len(result["agents"]) == 6

    @pytest.mark.asyncio
    async def test_swarm_status_before_launch(self):
        old = _swarm_mod._swarm
        _swarm_mod._swarm = None
        try:
            result = json.loads(await _swarm_mod.swarm_status())
            assert result["launched"] is False
        finally:
            _swarm_mod._swarm = old

    @pytest.mark.asyncio
    async def test_swarm_navigate_dry_run(self):
        await _swarm_mod.swarm_launch(dry_run=True)
        result = json.loads(await _swarm_mod.swarm_navigate("https://example.com"))
        assert result["success"] is True
        assert result["dry_run"] is True

    @pytest.mark.asyncio
    async def test_swarm_execute_task_dry_run(self):
        await _swarm_mod.swarm_launch(dry_run=True)
        result = json.loads(await _swarm_mod.swarm_execute_task("search for SCBE on GitHub"))
        assert "results" in result
        assert result["total_steps"] >= 1

    @pytest.mark.asyncio
    async def test_swarm_status_after_launch(self):
        await _swarm_mod.swarm_launch(dry_run=True)
        result = json.loads(await _swarm_mod.swarm_status())
        assert result["launched"] is True
        assert "KO" in result["agents"]
        assert result["dry_run"] is True

    def test_tool_registration(self):
        tool_names = [t.name for t in _swarm_mod.mcp._tool_manager.list_tools()]
        expected = [
            "swarm_launch", "swarm_execute_task", "swarm_navigate",
            "swarm_screenshot", "swarm_get_content", "swarm_click",
            "swarm_type", "swarm_status",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name} not registered"
