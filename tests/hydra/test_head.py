"""
Tests for HYDRA Head -- Universal AI Interface.
================================================

Covers:
- Connect to spine
- Execute commands (routed through spine)
- Callsign generation per AI type
- Polly Pad equip and capability queries
- Status transitions (DISCONNECTED -> CONNECTED -> BUSY -> CONNECTED)
- Error handling (not connected, spine missing)
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.head import (
    HydraHead,
    HeadStatus,
    create_claude_head,
    create_codex_head,
    create_gpt_head,
    create_local_head,
)
from hydra.spine import HydraSpine
from hydra.ledger import Ledger


@pytest.fixture
def ledger(tmp_path):
    db_path = str(tmp_path / "test_ledger.db")
    return Ledger(db_path=db_path)


@pytest.fixture
def spine(tmp_path, ledger):
    sb_path = str(tmp_path / "switchboard.db")
    return HydraSpine(
        ledger=ledger,
        use_dual_lattice=False,
        use_switchboard=True,
        switchboard_db=sb_path,
    )


# =========================================================================
# Connect to spine
# =========================================================================


class TestConnection:
    """Head connect/disconnect lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_succeeds(self, spine: HydraSpine):
        head = HydraHead(ai_type="claude", model="opus")
        result = await head.connect(spine)
        assert result is True
        assert head.status == HeadStatus.CONNECTED
        assert head._spine is spine
        assert head.head_id in spine.heads

    @pytest.mark.asyncio
    async def test_disconnect(self, spine: HydraSpine):
        head = HydraHead(ai_type="claude", model="opus")
        await head.connect(spine)
        await head.disconnect()
        assert head.status == HeadStatus.DISCONNECTED
        assert head._spine is None
        assert head.head_id not in spine.heads

    @pytest.mark.asyncio
    async def test_double_disconnect_is_safe(self, spine: HydraSpine):
        head = HydraHead()
        await head.connect(spine)
        await head.disconnect()
        await head.disconnect()  # should not raise
        assert head.status == HeadStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_initial_status_disconnected(self):
        head = HydraHead()
        assert head.status == HeadStatus.DISCONNECTED


# =========================================================================
# Execute commands
# =========================================================================


class TestExecute:
    """Commands routed through the spine."""

    @pytest.mark.asyncio
    async def test_execute_remember_recall(self, spine: HydraSpine):
        head = HydraHead(ai_type="claude", model="sonnet")
        await head.connect(spine)

        result = await head.execute({"action": "remember", "key": "color", "value": "red"})
        assert result["success"] is True

        result = await head.execute({"action": "recall", "key": "color"})
        assert result["success"] is True
        assert result["value"] == "red"

    @pytest.mark.asyncio
    async def test_execute_increments_action_count(self, spine: HydraSpine):
        head = HydraHead()
        await head.connect(spine)
        assert head.action_count == 0
        await head.execute({"action": "recall", "key": "x"})
        assert head.action_count == 1

    @pytest.mark.asyncio
    async def test_execute_not_connected_returns_error(self):
        head = HydraHead()
        result = await head.execute({"action": "recall", "key": "x"})
        assert result["success"] is False
        assert "not connected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_status_transitions_during_execute(self, spine: HydraSpine):
        """Head should transition CONNECTED -> BUSY -> CONNECTED."""
        head = HydraHead()
        await head.connect(spine)

        # We can observe the final state; BUSY is transient
        result = await head.execute({"action": "recall", "key": "x"})
        assert head.status == HeadStatus.CONNECTED


# =========================================================================
# Callsign generation
# =========================================================================


class TestCallsign:
    """Callsign prefix matches AI type."""

    def test_claude_callsign_prefix(self):
        head = HydraHead(ai_type="claude", model="opus")
        assert head.callsign.startswith("CT-")

    def test_codex_callsign_prefix(self):
        head = HydraHead(ai_type="codex", model="code-davinci-002")
        assert head.callsign.startswith("CX-")

    def test_gpt_callsign_prefix(self):
        head = HydraHead(ai_type="gpt", model="gpt-4")
        assert head.callsign.startswith("GP-")

    def test_gemini_callsign_prefix(self):
        head = HydraHead(ai_type="gemini", model="pro")
        assert head.callsign.startswith("GM-")

    def test_local_callsign_prefix(self):
        head = HydraHead(ai_type="local", model="llama-3")
        assert head.callsign.startswith("LC-")

    def test_custom_callsign_prefix(self):
        head = HydraHead(ai_type="custom", model="my-model")
        assert head.callsign.startswith("XX-")

    def test_unknown_type_gets_xx_prefix(self):
        head = HydraHead(ai_type="alien", model="m1")
        assert head.callsign.startswith("XX-")

    def test_explicit_callsign_overrides(self):
        head = HydraHead(ai_type="claude", model="opus", callsign="ALPHA-1")
        assert head.callsign == "ALPHA-1"

    def test_callsign_uniqueness(self):
        heads = [HydraHead(ai_type="claude", model="sonnet") for _ in range(20)]
        callsigns = {h.callsign for h in heads}
        assert len(callsigns) == 20  # all unique


# =========================================================================
# Polly Pad
# =========================================================================


class TestPollyPad:
    """Polly Pad equip and capability queries."""

    def test_equip_polly_pad(self):
        head = HydraHead()
        pad = {
            "id": "pad-001",
            "loadout": [
                {"id": "code_review", "name": "Code Review"},
                {"id": "web_search", "name": "Web Search"},
            ]
        }
        head.equip_polly_pad(pad)
        assert head._polly_pad == pad

    def test_get_loadout(self):
        head = HydraHead()
        head.equip_polly_pad({
            "id": "pad-001",
            "loadout": [{"id": "code_review", "name": "Code Review"}]
        })
        loadout = head.get_loadout()
        assert len(loadout) == 1
        assert loadout[0]["id"] == "code_review"

    def test_get_loadout_no_pad(self):
        head = HydraHead()
        assert head.get_loadout() == []

    def test_has_capability(self):
        head = HydraHead()
        head.equip_polly_pad({
            "id": "pad-001",
            "loadout": [
                {"id": "code_review", "name": "Code Review"},
                {"id": "web_search", "name": "Web Search"},
            ]
        })
        assert head.has_capability("code_review") is True
        assert head.has_capability("web_search") is True
        assert head.has_capability("teleport") is False

    def test_has_capability_no_pad(self):
        head = HydraHead()
        assert head.has_capability("anything") is False


# =========================================================================
# Factory functions
# =========================================================================


class TestFactoryFunctions:
    """create_*_head convenience constructors."""

    def test_create_claude_head(self):
        head = create_claude_head(model="opus", callsign="HERO-1")
        assert head.ai_type == "claude"
        assert head.model == "opus"
        assert head.callsign == "HERO-1"

    def test_create_codex_head(self):
        head = create_codex_head()
        assert head.ai_type == "codex"

    def test_create_gpt_head(self):
        head = create_gpt_head(model="gpt-4o")
        assert head.ai_type == "gpt"
        assert head.model == "gpt-4o"

    def test_create_local_head(self):
        head = create_local_head(model="llama-3")
        assert head.ai_type == "local"


# =========================================================================
# Convenience methods
# =========================================================================


class TestConvenienceMethods:
    """Shortcut methods: remember, recall, send_message."""

    @pytest.mark.asyncio
    async def test_remember_convenience(self, spine: HydraSpine):
        head = HydraHead()
        await head.connect(spine)
        ok = await head.remember("pet", "dog")
        assert ok is True

    @pytest.mark.asyncio
    async def test_recall_convenience(self, spine: HydraSpine):
        head = HydraHead()
        await head.connect(spine)
        await head.remember("pet", "dog")
        value = await head.recall("pet")
        assert value == "dog"

    @pytest.mark.asyncio
    async def test_send_message(self, spine: HydraSpine):
        h1 = HydraHead(ai_type="claude")
        h2 = HydraHead(ai_type="codex")
        await h1.connect(spine)
        await h2.connect(spine)

        result = await h1.send_message(h2.head_id, {"task": "help"})
        assert result["success"] is True

        msgs = await h2.receive_messages()
        assert len(msgs) == 1
        assert msgs[0]["message"]["task"] == "help"

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self):
        head = HydraHead()
        result = await head.send_message("someone", {"hello": True})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_receive_messages_not_connected(self):
        head = HydraHead()
        msgs = await head.receive_messages()
        assert msgs == []
