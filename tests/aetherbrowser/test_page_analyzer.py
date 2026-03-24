"""Tests for the 'This Page' analyzer."""
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

    def test_analyze_detects_topics(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://example.com",
            title="AI Research",
            text="Machine learning and artificial intelligence are transforming security research. Neural networks provide new capabilities for threat detection.",
        )
        assert "topics" in result
        assert len(result["topics"]) > 0

    def test_analyze_empty_text(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(url="https://empty.com", title="Empty", text="")
        assert result["word_count"] == 0
        assert result["summary"] == ""

    def test_analyze_truncates_long_text(self):
        analyzer = PageAnalyzer()
        long_text = "word " * 100_000
        result = analyzer.analyze_sync(url="https://long.com", title="Long", text=long_text)
        assert result["truncated"] is True

    def test_repository_review_uses_hostname_not_url_substring(self):
        analyzer = PageAnalyzer()
        result = analyzer.analyze_sync(
            url="https://example.com/docs/github.com-notes",
            title="Governance Notes",
            text="This page explains governance checkpoints and operator notes.",
        )
        assert result["intent"] == "inspect_page"
