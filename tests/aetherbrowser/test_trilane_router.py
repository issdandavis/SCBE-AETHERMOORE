"""Tests for the TriLane Browser Router."""

import pytest
from src.aetherbrowser.trilane_router import (
    TriLaneRouter,
    BrowserLane,
    TaskIntent,
    LaneResult,
    TriLaneResult,
)


@pytest.fixture
def router():
    return TriLaneRouter(enable_shadow_training=True)


# =============================================================================
# Intent Classification
# =============================================================================


class TestIntentClassification:
    @pytest.mark.parametrize(
        "text,expected_intent",
        [
            # scrape intent
            ("scrape the top 50 arXiv papers", TaskIntent.SCRAPE),
            ("extract all links from this page", TaskIntent.SCRAPE),
            ("crawl github.com for repos", TaskIntent.SCRAPE),
            ("bulk download PDFs", TaskIntent.SCRAPE),
            # interact intent
            ("click the login button", TaskIntent.INTERACT),
            ("fill out the contact form", TaskIntent.INTERACT),
            ("navigate to github.com and open settings", TaskIntent.INTERACT),
            ("type my username into the field", TaskIntent.INTERACT),
            # verify intent
            ("check if the shopify store looks right", TaskIntent.VERIFY),
            ("verify the homepage screenshot", TaskIntent.VERIFY),
            ("inspect the layout visually", TaskIntent.VERIFY),
            # post intent
            ("post this article to dev.to", TaskIntent.POST),
            ("publish the blog post", TaskIntent.POST),
            ("tweet about the new release", TaskIntent.POST),
            ("share the new release on twitter", TaskIntent.POST),
            # monitor intent
            ("watch for price changes on amazon", TaskIntent.MONITOR),
            ("monitor the CI pipeline", TaskIntent.MONITOR),
            ("track when the page updates", TaskIntent.MONITOR),
            # research intent
            ("research AI safety papers", TaskIntent.RESEARCH),
            ("find information about transformers", TaskIntent.RESEARCH),
            ("search for competitor products", TaskIntent.RESEARCH),
            # train intent
            ("train the model by watching me browse", TaskIntent.TRAIN),
            ("capture this session for SFT dataset", TaskIntent.TRAIN),
            ("shadow learn from this interaction", TaskIntent.TRAIN),
            # default to research
            ("tell me about the weather", TaskIntent.RESEARCH),
            # url boosts scrape
            ("https://arxiv.org/list/cs.AI", TaskIntent.SCRAPE),
            # large number boosts scrape
            ("get 100 papers from arxiv", TaskIntent.SCRAPE),
        ],
    )
    def test_classify_intent(self, router, text, expected_intent):
        assert router.classify_intent(text) == expected_intent


# =============================================================================
# Lane Selection
# =============================================================================


class TestLaneSelection:
    def test_scrape_uses_headless(self, router):
        lanes = router.select_lanes(TaskIntent.SCRAPE, "scrape pages")
        assert lanes == [BrowserLane.HEADLESS]

    def test_monitor_uses_headless(self, router):
        lanes = router.select_lanes(TaskIntent.MONITOR, "monitor site")
        assert lanes == [BrowserLane.HEADLESS]

    def test_interact_uses_mcp(self, router):
        lanes = router.select_lanes(TaskIntent.INTERACT, "click button")
        assert lanes == [BrowserLane.MCP]

    def test_post_uses_mcp(self, router):
        lanes = router.select_lanes(TaskIntent.POST, "post article")
        assert lanes == [BrowserLane.MCP]

    def test_verify_uses_visual(self, router):
        lanes = router.select_lanes(TaskIntent.VERIFY, "check layout")
        assert lanes == [BrowserLane.VISUAL]

    def test_research_uses_headless_and_visual(self, router):
        lanes = router.select_lanes(TaskIntent.RESEARCH, "research papers")
        assert BrowserLane.HEADLESS in lanes
        assert BrowserLane.VISUAL in lanes

    def test_train_uses_mcp_and_visual(self, router):
        lanes = router.select_lanes(TaskIntent.TRAIN, "shadow train")
        assert BrowserLane.MCP in lanes
        assert BrowserLane.VISUAL in lanes


# =============================================================================
# SFT Shadow Training
# =============================================================================


class TestShadowTraining:
    def test_sft_pair_structure(self, router):
        result = TriLaneResult(
            task="research AI safety",
            intent=TaskIntent.RESEARCH,
            lanes_used=[BrowserLane.HEADLESS],
            plan={"risk_tier": "low", "targets": ["arxiv.org"]},
            results=[LaneResult(lane=BrowserLane.HEADLESS, success=True, actions_taken=1)],
        )
        sft = router._build_sft_pair(result)
        assert "instruction" in sft
        assert "input" in sft
        assert "output" in sft
        assert "label" in sft
        assert sft["label"] == "browser_routing_research"
        assert sft["model"] == "issdandavis/scbe-unified-governance"

    def test_shadow_disabled(self):
        router = TriLaneRouter(enable_shadow_training=False)
        assert router._shadow_training is False


# =============================================================================
# TriLaneResult
# =============================================================================


class TestTriLaneResult:
    def test_success_when_any_lane_succeeds(self):
        result = TriLaneResult(
            task="test",
            intent=TaskIntent.RESEARCH,
            lanes_used=[BrowserLane.HEADLESS, BrowserLane.VISUAL],
            results=[
                LaneResult(lane=BrowserLane.HEADLESS, success=True),
                LaneResult(lane=BrowserLane.VISUAL, success=False, error="no screenshot"),
            ],
        )
        assert result.success is True

    def test_failure_when_all_lanes_fail(self):
        result = TriLaneResult(
            task="test",
            intent=TaskIntent.SCRAPE,
            lanes_used=[BrowserLane.HEADLESS],
            results=[
                LaneResult(lane=BrowserLane.HEADLESS, success=False, error="connection refused"),
            ],
        )
        assert result.success is False

    def test_to_dict(self):
        result = TriLaneResult(
            task="scrape arxiv",
            intent=TaskIntent.SCRAPE,
            lanes_used=[BrowserLane.HEADLESS],
            results=[LaneResult(lane=BrowserLane.HEADLESS, success=True, actions_taken=3)],
            total_duration_ms=150.5,
        )
        d = result.to_dict()
        assert d["task"] == "scrape arxiv"
        assert d["intent"] == "scrape"
        assert d["lanes_used"] == ["headless"]
        assert d["success"] is True
        assert d["total_duration_ms"] == 150.5


# =============================================================================
# Router Stats
# =============================================================================


class TestRouterStats:
    def test_empty_stats(self, router):
        stats = router.get_stats()
        assert stats["total_tasks"] == 0

    def test_stats_after_classification(self, router):
        # Manually add a result to the log
        router._action_log.append(
            TriLaneResult(
                task="scrape stuff",
                intent=TaskIntent.SCRAPE,
                lanes_used=[BrowserLane.HEADLESS],
                results=[LaneResult(lane=BrowserLane.HEADLESS, success=True)],
                shadow_sft={"instruction": "test"},
            )
        )
        stats = router.get_stats()
        assert stats["total_tasks"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["intent_distribution"]["scrape"] == 1
        assert stats["lane_usage"]["headless"] == 1
        assert stats["sft_pairs_generated"] == 1
