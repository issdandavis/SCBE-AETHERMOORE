"""Tests for the 'This Page' analyzer."""

import pytest
from src.aetherbrowser.page_analyzer import PageAnalyzer


class TestPageAnalyzer:
    def test_analyze_returns_summary(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://example.com/article",
            title="Example Article",
            text="This is a test article about AI safety. It discusses governance frameworks and security models. The key findings are that hyperbolic geometry provides exponential cost scaling.",
        )
        assert "summary" in result
        assert len(result["summary"]) > 0

    def test_analyze_extracts_metadata(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://example.com",
            title="Test Page",
            text="Short page content.",
        )
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert "word_count" in result
        assert "page_summary" in result
        assert "intent" in result
        assert "topology_lens" in result

    def test_analyze_detects_topics(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://example.com",
            title="AI Research",
            text="Machine learning and artificial intelligence are transforming security research. Neural networks provide new capabilities for threat detection.",
        )
        assert "topics" in result
        assert len(result["topics"]) > 0
        assert result["intent"] in {"read_article", "inspect_page"}
        assert result["topology_lens"]["primary_axis"] in {
            "AI/ML",
            "Security",
            "Research",
            "Finance",
            "Code",
        }

    def test_analyze_empty_text(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(url="https://empty.com", title="Empty", text="")
        assert result["word_count"] == 0
        assert result["summary"] == ""
        assert result["risk_tier"] == "low"
        assert result["topology_lens"]["zone"] == "GREEN"

    def test_analyze_truncates_long_text(self):
        analyzer = PageAnalyzer()
        long_text = "word " * 100_000
        result = analyzer.analyze_sync(
            url="https://long.com", title="Long", text=long_text
        )
        assert result["truncated"] is True

    def test_analyze_structured_page_context(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://example.com/form",
            title="Checkout",
            text="Pay now using the secure checkout form for your order.",
            headings=[{"level": "H1", "text": "Checkout"}],
            links=[{"text": "Cart", "href": "https://example.com/cart"}],
            forms=[
                {
                    "index": 0,
                    "method": "post",
                    "fields": [{"name": "email", "type": "email"}],
                }
            ],
            buttons=[{"text": "Pay now", "type": "submit"}],
            tabs=[
                {"title": "Checkout", "url": "https://example.com/form", "active": True}
            ],
            selection="secure checkout form",
            page_type="form",
            screenshot="data:image/jpeg;base64,abc",
        )
        assert result["page_type"] == "form"
        assert result["form_count"] == 1
        assert result["tab_count"] == 1
        assert result["selected_text"] == "secure checkout form"
        assert result["has_screenshot"] is True
        assert result["intent"] == "checkout"
        assert result["risk_tier"] == "high"
        assert result["required_approvals"]
        assert result["next_actions"]
        assert result["topology_lens"]["zone"] == "RED"
        assert result["topology_lens"]["trust_distance"] > 0
        assert (
            "commerce boundary present" in result["topology_lens"]["boundary_signals"]
        )

    def test_topology_lens_emits_ranked_semantic_compass(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://research.example.com/paper",
            title="AI Research Security Paper",
            text=(
                "This research paper studies machine learning security, model governance, "
                "experimental analysis, and neural network threat detection."
            ),
            headings=[{"level": "H1", "text": "Research Findings"}],
            links=[
                {"text": "Dataset", "href": "https://data.example.net/set"},
                {"text": "Code Repo", "href": "https://github.com/example/repo"},
            ],
        )

        compass = result["topology_lens"]["semantic_compass"]
        assert len(compass) == 5
        assert compass[0]["score"] >= compass[-1]["score"]
        assert all(0 <= axis["score"] <= 1 for axis in compass)
        assert result["topology_lens"]["primary_axis"] in {
            axis["axis"] for axis in compass
        }
