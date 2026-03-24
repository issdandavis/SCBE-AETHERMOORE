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
    def test_scrape_intent(self, router):
        assert router.classify_intent("scrape the top 50 arXiv papers") == TaskIntent.SCRAPE
        assert router.classify_intent("extract all links from this page") == TaskIntent.SCRAPE
        assert router.classify_intent("crawl github.com for repos") == TaskIntent.SCRAPE
        assert router.classify_intent("bulk download PDFs") == TaskIntent.SCRAPE

    def test_interact_intent(self, router):
        assert router.classify_intent("click the login button") == TaskIntent.INTERACT
        assert router.classify_intent("fill out the contact form") == TaskIntent.INTERACT
        assert router.classify_intent("navigate to github.com and open settings") == TaskIntent.INTERACT
        assert router.classify_intent("type my username into the field") == TaskIntent.INTERACT

    def test_verify_intent(self, router):
        assert router.classify_intent("check if the shopify store looks right") == TaskIntent.VERIFY
        assert router.classify_intent("verify the homepage screenshot") == TaskIntent.VERIFY
        assert router.classify_intent("inspect the layout visually") == TaskIntent.VERIFY

    def test_post_intent(self, router):
        assert router.classify_intent("post this article to dev.to") == TaskIntent.POST
        assert router.classify_intent("publish the blog post") == TaskIntent.POST
        assert router.classify_intent("tweet about the new release") == TaskIntent.POST
        assert router.classify_intent("share the new release on twitter") == TaskIntent.POST

    def test_monitor_intent(self, router):
        assert router.classify_intent("watch for price changes on amazon") == TaskIntent.MONITOR
        assert router.classify_intent("monitor the CI pipeline") == TaskIntent.MONITOR
        assert router.classify_intent("track when the page updates") == TaskIntent.MONITOR

    def test_research_intent(self, router):
        assert router.classify_intent("research AI safety papers") == TaskIntent.RESEARCH
        assert router.classify_intent("find information about transformers") == TaskIntent.RESEARCH
        assert router.classify_intent("search for competitor products") == TaskIntent.RESEARCH

    def test_train_intent(self, router):
        assert router.classify_intent("train the model by watching me browse") == TaskIntent.TRAIN
        assert router.classify_intent("capture this session for SFT dataset") == TaskIntent.TRAIN
        assert router.classify_intent("shadow learn from this interaction") == TaskIntent.TRAIN

    def test_default_to_research(self, router):
        assert router.classify_intent("tell me about the weather") == TaskIntent.RESEARCH

    def test_url_boosts_scrape(self, router):
        assert router.classify_intent("https://arxiv.org/list/cs.AI") == TaskIntent.SCRAPE

    def test_large_number_boosts_scrape(self, router):
        assert router.classify_intent("get 100 papers from arxiv") == TaskIntent.SCRAPE


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
