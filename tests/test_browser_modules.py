"""
Tests for the new browser modules:
  - polly_vision.py  (PollyVision observation window)
  - research_funnel.py (Cloud storage sync)
  - hydra_hand.py (PollyVision integration)

These tests are unit-level and don't require Playwright or network access.
They verify data structures, logic, and module integration.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── PollyVision Tests ─────────────────────────────────────────────────


class TestPollyVisionImports:
    """Verify polly_vision module loads and exports correctly."""

    def test_import_polly_vision(self):
        from src.browser.polly_vision import PollyVision, ObservationTier, PageObservation, InteractiveElement

        assert PollyVision is not None
        assert ObservationTier is not None

    def test_observation_tiers(self):
        from src.browser.polly_vision import ObservationTier

        assert ObservationTier.TIER_1.value == "accessibility_only"
        assert ObservationTier.TIER_2.value == "accessibility_plus"
        assert ObservationTier.TIER_3.value == "full_visual"

    def test_tier_is_string_enum(self):
        from src.browser.polly_vision import ObservationTier

        assert isinstance(ObservationTier.TIER_1, str)
        assert ObservationTier.TIER_1 == "accessibility_only"


class TestInteractiveElement:
    """Test InteractiveElement dataclass."""

    def test_create_element(self):
        from src.browser.polly_vision import InteractiveElement

        el = InteractiveElement(ref_id=1, role="button", name="Submit", tag="button", selector="#submit-btn")
        assert el.ref_id == 1
        assert el.role == "button"
        assert el.name == "Submit"
        assert el.bounding_box is None
        assert el.state == ""

    def test_element_with_state(self):
        from src.browser.polly_vision import InteractiveElement

        el = InteractiveElement(
            ref_id=5, role="checkbox", name="Agree", tag="input", selector="#agree", state="checked"
        )
        assert el.state == "checked"

    def test_element_with_bbox(self):
        from src.browser.polly_vision import InteractiveElement

        bbox = {"x": 10, "y": 20, "width": 100, "height": 30}
        el = InteractiveElement(ref_id=2, role="link", name="Home", tag="a", selector="a.home", bounding_box=bbox)
        assert el.bounding_box["width"] == 100


class TestPageObservation:
    """Test PageObservation dataclass and methods."""

    def _make_observation(self, **kwargs):
        from src.browser.polly_vision import PageObservation, ObservationTier, InteractiveElement

        defaults = dict(
            url="https://example.com",
            title="Example",
            accessibility_tree="@1 button: Submit\n@2 link: Home",
            interactive_elements=[
                InteractiveElement(ref_id=1, role="button", name="Submit", tag="button", selector="#sub"),
                InteractiveElement(ref_id=2, role="link", name="Home", tag="a", selector="a.home"),
            ],
            screenshot_bytes=None,
            screenshot_b64=None,
            page_summary="Example | 1 buttons, 1 links",
            observation_tier=ObservationTier.TIER_2,
            content_hash="abc123",
            elapsed_ms=42.0,
            token_estimate=150,
        )
        defaults.update(kwargs)
        return PageObservation(**defaults)

    def test_has_screenshot_false(self):
        obs = self._make_observation()
        assert obs.has_screenshot is False

    def test_has_screenshot_true(self):
        obs = self._make_observation(screenshot_bytes=b"\x89PNG")
        assert obs.has_screenshot is True

    def test_element_count(self):
        obs = self._make_observation()
        assert obs.element_count == 2

    def test_get_element_found(self):
        obs = self._make_observation()
        el = obs.get_element(1)
        assert el is not None
        assert el.name == "Submit"

    def test_get_element_not_found(self):
        obs = self._make_observation()
        el = obs.get_element(99)
        assert el is None

    def test_compact_repr(self):
        obs = self._make_observation()
        text = obs.compact_repr()
        assert "Page: Example" in text
        assert "@1 button: Submit" in text
        assert "@2 link: Home" in text

    def test_compact_repr_includes_state(self):
        from src.browser.polly_vision import InteractiveElement, ObservationTier, PageObservation

        obs = self._make_observation(
            interactive_elements=[
                InteractiveElement(
                    ref_id=1, role="checkbox", name="Agree", tag="input", selector="#a", state="checked"
                ),
            ]
        )
        text = obs.compact_repr()
        assert "[checked]" in text


class TestPollyVisionEngine:
    """Test PollyVision class initialization and helpers."""

    def test_default_init(self):
        from src.browser.polly_vision import PollyVision, ObservationTier

        v = PollyVision()
        assert v.tier == ObservationTier.TIER_2
        assert v.viewport_width == 1280
        assert v.viewport_height == 720
        assert v.max_elements == 50

    def test_custom_tier(self):
        from src.browser.polly_vision import PollyVision, ObservationTier

        v = PollyVision(tier=ObservationTier.TIER_1)
        assert v.tier == ObservationTier.TIER_1

    def test_session_stats_initial(self):
        from src.browser.polly_vision import PollyVision

        v = PollyVision()
        stats = v.session_stats
        assert stats["observations"] == 0
        assert stats["screenshots"] == 0
        assert stats["total_tokens_est"] == 0

    def test_estimate_tokens_text_only(self):
        from src.browser.polly_vision import PollyVision

        tokens = PollyVision._estimate_tokens("Hello world test", None)
        assert tokens == len("Hello world test") // 4

    def test_estimate_tokens_with_screenshot(self):
        from src.browser.polly_vision import PollyVision

        tokens = PollyVision._estimate_tokens("Hello world test", b"\x89PNG")
        text_tokens = len("Hello world test") // 4
        assert tokens == text_tokens + 200

    def test_generate_summary(self):
        from src.browser.polly_vision import PollyVision, InteractiveElement

        elements = [
            InteractiveElement(ref_id=1, role="button", name="Go", tag="button", selector="#go"),
            InteractiveElement(ref_id=2, role="button", name="Stop", tag="button", selector="#stop"),
            InteractiveElement(ref_id=3, role="link", name="Home", tag="a", selector="a"),
        ]
        summary = PollyVision._generate_summary("My Page", "https://x.com", elements)
        assert "My Page" in summary
        assert "2 buttons" in summary
        assert "1 links" in summary

    def test_generate_summary_empty(self):
        from src.browser.polly_vision import PollyVision

        summary = PollyVision._generate_summary("Empty", "https://x.com", [])
        assert summary == "Empty"


# ── Research Funnel Tests ─────────────────────────────────────────────


class TestResearchFunnelImports:
    """Verify research_funnel module loads."""

    def test_import_funnel(self):
        from src.browser.research_funnel import ResearchFunnel, FunnelReceipt

        assert ResearchFunnel is not None
        assert FunnelReceipt is not None


class TestFunnelReceipt:
    """Test FunnelReceipt dataclass."""

    def test_default_receipt(self):
        from src.browser.research_funnel import FunnelReceipt

        r = FunnelReceipt(run_id="20260227T120000Z")
        assert r.run_id == "20260227T120000Z"
        assert r.records_written == 0
        assert r.local_path is None
        assert r.notion_url is None
        assert r.hf_committed is False
        assert r.errors == []


class TestResearchFunnelRecordBuilder:
    """Test record building logic."""

    def test_build_records(self):
        from src.browser.research_funnel import ResearchFunnel
        from datetime import datetime, timezone

        funnel = ResearchFunnel(intake_dir=Path(tempfile.mkdtemp()))
        extractions = [
            {"url": "https://example.com", "title": "Example", "text": "Hello world"},
            {"url": "https://test.com", "title": "Test", "text": "Test content"},
        ]
        now = datetime(2026, 2, 27, 12, 0, 0, tzinfo=timezone.utc)
        records = funnel._build_records(extractions, "test_run", ["AI safety"], now)

        assert len(records) == 2
        assert records[0]["event_type"] == "web_research_chunk"
        assert records[0]["dataset"] == "scbe_web_research_intake"
        assert records[0]["source_url"] == "https://example.com"
        assert records[0]["topics"] == ["AI safety"]
        assert records[0]["chunk_index"] == 1
        assert records[1]["chunk_index"] == 2

    def test_records_have_content_hash(self):
        from src.browser.research_funnel import ResearchFunnel
        from datetime import datetime, timezone

        funnel = ResearchFunnel(intake_dir=Path(tempfile.mkdtemp()))
        extractions = [{"url": "https://x.com", "title": "X", "text": "content"}]
        now = datetime(2026, 2, 27, tzinfo=timezone.utc)
        records = funnel._build_records(extractions, "r1", ["test"], now)

        expected_hash = hashlib.sha256(b"content").hexdigest()
        assert records[0]["content_sha256"] == expected_hash


class TestResearchFunnelLocalWrite:
    """Test local JSONL writing."""

    def test_write_local_jsonl(self):
        from src.browser.research_funnel import ResearchFunnel

        tmp_dir = Path(tempfile.mkdtemp())
        funnel = ResearchFunnel(intake_dir=tmp_dir)

        records = [
            {"event_type": "test", "url": "https://a.com"},
            {"event_type": "test", "url": "https://b.com"},
        ]
        path = funnel._write_local_jsonl(records, "20260227T120000Z")

        assert path.exists()
        assert path.name == "web_research_20260227T120000Z.jsonl"

        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        parsed = json.loads(lines[0])
        assert parsed["url"] == "https://a.com"


class TestResearchFunnelPush:
    """Test the main push() method (mocked backends)."""

    @pytest.mark.asyncio
    async def test_push_empty_extractions(self):
        from src.browser.research_funnel import ResearchFunnel

        funnel = ResearchFunnel(intake_dir=Path(tempfile.mkdtemp()))
        receipt = await funnel.push({"extractions": []})
        assert receipt.records_written == 0
        assert "No extractions" in receipt.errors[0]

    @pytest.mark.asyncio
    async def test_push_local_only(self):
        from src.browser.research_funnel import ResearchFunnel

        tmp_dir = Path(tempfile.mkdtemp())
        funnel = ResearchFunnel(
            intake_dir=tmp_dir,
            notion_token=None,
            hf_token=None,
        )
        research = {
            "query": "test query",
            "extractions": [
                {"url": "https://example.com", "title": "Ex", "text": "Hello"},
            ],
        }
        receipt = await funnel.push(research)
        assert receipt.records_written == 1
        assert receipt.local_path is not None
        assert Path(receipt.local_path).exists()
        assert receipt.notion_url is None
        assert receipt.hf_committed is False

    @pytest.mark.asyncio
    async def test_push_merged_extractions(self):
        """swarm_research() output uses 'merged_extractions' key."""
        from src.browser.research_funnel import ResearchFunnel

        tmp_dir = Path(tempfile.mkdtemp())
        funnel = ResearchFunnel(intake_dir=tmp_dir)
        research = {
            "queries": ["q1", "q2"],
            "merged_extractions": [
                {"url": "https://a.com", "title": "A", "text": "aaa"},
                {"url": "https://b.com", "title": "B", "text": "bbb"},
            ],
        }
        receipt = await funnel.push(research)
        assert receipt.records_written == 2


# ── HydraHand Integration Tests ──────────────────────────────────────


class TestHydraHandImports:
    """Verify hydra_hand module loads with PollyVision integration."""

    def test_import_hydra_hand(self):
        from src.browser.hydra_hand import HydraHand, Tongue, Finger, BrowsingResult

        assert HydraHand is not None

    def test_tongue_enum(self):
        from src.browser.hydra_hand import Tongue

        assert Tongue.KO.value == "KO"
        assert Tongue.AV.value == "AV"
        assert Tongue.DR.value == "DR"
        assert len(Tongue) == 6


class TestFingerVision:
    """Test that Finger has PollyVision attached."""

    def test_finger_has_vision(self):
        from src.browser.hydra_hand import Finger, Tongue
        from src.browser.polly_vision import PollyVision, ObservationTier

        f = Finger(tongue=Tongue.CA, vision=PollyVision(tier=ObservationTier.TIER_2))
        assert f.vision is not None
        assert f.vision.tier == ObservationTier.TIER_2

    def test_finger_vision_default_none(self):
        from src.browser.hydra_hand import Finger, Tongue

        f = Finger(tongue=Tongue.AV)
        assert f.vision is None

    @pytest.mark.asyncio
    async def test_finger_observe_no_vision(self):
        from src.browser.hydra_hand import Finger, Tongue

        f = Finger(tongue=Tongue.CA)
        result = await f.observe()
        assert result is None

    @pytest.mark.asyncio
    async def test_finger_observe_no_page(self):
        from src.browser.hydra_hand import Finger, Tongue
        from src.browser.polly_vision import PollyVision

        f = Finger(tongue=Tongue.CA, vision=PollyVision())
        result = await f.observe()
        assert result is None


class TestHydraHandVisionInit:
    """Test HydraHand creates PollyVision per finger."""

    def test_hand_default_vision_tier(self):
        from src.browser.hydra_hand import HydraHand, Tongue
        from src.browser.polly_vision import ObservationTier

        hand = HydraHand(head_id="test")
        assert hand.vision_tier == ObservationTier.TIER_2

        for tongue, finger in hand.fingers.items():
            assert finger.vision is not None
            assert finger.vision.tier == ObservationTier.TIER_2

    def test_hand_custom_vision_tier(self):
        from src.browser.hydra_hand import HydraHand
        from src.browser.polly_vision import ObservationTier

        hand = HydraHand(head_id="visual", vision_tier=ObservationTier.TIER_3)
        assert hand.vision_tier == ObservationTier.TIER_3

        for finger in hand.fingers.values():
            assert finger.vision.tier == ObservationTier.TIER_3

    def test_hand_has_six_fingers(self):
        from src.browser.hydra_hand import HydraHand

        hand = HydraHand()
        assert len(hand.fingers) == 6

    def test_hand_status(self):
        from src.browser.hydra_hand import HydraHand

        hand = HydraHand(head_id="status-test")
        status = hand.status()
        assert status["head_id"] == "status-test"
        assert status["open"] is False
        assert len(status["fingers"]) == 6

    def test_hand_research_and_funnel_method_exists(self):
        from src.browser.hydra_hand import HydraHand

        hand = HydraHand()
        assert hasattr(hand, "research_and_funnel")
        assert callable(hand.research_and_funnel)


class TestDomainSafety:
    """Test domain safety checks."""

    def test_trusted_domain(self):
        from src.browser.hydra_hand import check_domain_safety

        decision, risk = check_domain_safety("https://github.com/openclaw")
        assert decision == "ALLOW"
        assert risk == 0.0

    def test_blocked_domain(self):
        from src.browser.hydra_hand import check_domain_safety

        decision, risk = check_domain_safety("https://malware.com/payload")
        assert decision == "DENY"
        assert risk == 1.0

    def test_unknown_domain(self):
        from src.browser.hydra_hand import check_domain_safety

        decision, risk = check_domain_safety("https://random-site-xyz.com")
        assert decision == "QUARANTINE"
        assert risk == 0.5


class TestTongueWeights:
    """Test Sacred Tongue phi-weights are correct."""

    def test_phi_weights(self):
        from src.browser.hydra_hand import TONGUE_WEIGHT, Tongue

        phi = 1.618033988749895

        assert TONGUE_WEIGHT[Tongue.KO] == pytest.approx(1.0, abs=0.01)
        assert TONGUE_WEIGHT[Tongue.AV] == pytest.approx(phi, abs=0.01)
        assert TONGUE_WEIGHT[Tongue.RU] == pytest.approx(phi**2, abs=0.01)
        assert TONGUE_WEIGHT[Tongue.CA] == pytest.approx(phi**3, abs=0.01)

    def test_weight_ordering(self):
        from src.browser.hydra_hand import TONGUE_WEIGHT, Tongue

        weights = [TONGUE_WEIGHT[t] for t in [Tongue.KO, Tongue.AV, Tongue.RU, Tongue.CA, Tongue.UM, Tongue.DR]]
        assert weights == sorted(weights), "Tongue weights should be in ascending phi order"


class TestProximityMapping:
    """Test proximity urgency model."""

    def test_all_tongues_have_proximity(self):
        from src.browser.hydra_hand import TONGUE_PROXIMITY, Tongue

        for t in Tongue:
            assert t in TONGUE_PROXIMITY

    def test_throttle_delays(self):
        from src.browser.hydra_hand import HydraHand, Proximity

        assert HydraHand._throttle_delay(Proximity.ROCK) == 0.0
        assert HydraHand._throttle_delay(Proximity.OWL) == 1.0
        assert HydraHand._throttle_delay(Proximity.VOICE) == 0.05
