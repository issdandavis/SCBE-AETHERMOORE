"""Tests for the Python port of HyperLane governance."""

from src.aetherbrowser.hyperlane_py import HyperLanePy, Zone, Decision


class TestZoneClassification:
    def test_github_is_green(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://github.com/issdandavis/repo") == Zone.GREEN

    def test_huggingface_is_green(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://huggingface.co/datasets/test") == Zone.GREEN

    def test_notion_is_green(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://api.notion.com/v1/pages") == Zone.GREEN

    def test_localhost_is_green(self):
        hl = HyperLanePy()
        assert hl.classify_zone("http://localhost:8001/health") == Zone.GREEN

    def test_ai_api_is_yellow(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://api.anthropic.com/v1/messages") == Zone.YELLOW

    def test_social_is_yellow(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://api.twitter.com/2/tweets") == Zone.YELLOW

    def test_unknown_is_red(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://random-sketchy-site.xyz/api") == Zone.RED

    def test_financial_is_red(self):
        hl = HyperLanePy()
        assert hl.classify_zone("https://api.stripe.com/v1/charges") == Zone.RED


class TestDecisionMaking:
    def test_green_read_allows(self):
        hl = HyperLanePy()
        d = hl.evaluate("https://github.com/test", action="read", agent_id="AV")
        assert d.decision == Decision.ALLOW
        assert d.zone == Zone.GREEN

    def test_yellow_write_quarantines(self):
        hl = HyperLanePy()
        d = hl.evaluate(
            "https://api.anthropic.com/v1/messages", action="write", agent_id="CA"
        )
        assert d.decision == Decision.QUARANTINE
        assert d.zone == Zone.YELLOW

    def test_red_auto_quarantines(self):
        hl = HyperLanePy()
        d = hl.evaluate("https://evil.example.com", action="read", agent_id="AV")
        assert d.decision == Decision.QUARANTINE
        assert d.zone == Zone.RED

    def test_green_write_allows(self):
        hl = HyperLanePy()
        d = hl.evaluate(
            "http://localhost:8001/v1/training/ingest", action="write", agent_id="DR"
        )
        assert d.decision == Decision.ALLOW


class TestRateLimiting:
    def test_rate_limit_after_burst(self):
        hl = HyperLanePy(rate_limit_per_min=3)
        for _ in range(3):
            hl.evaluate("https://github.com/test", action="read", agent_id="AV")
        d = hl.evaluate("https://github.com/test", action="read", agent_id="AV")
        assert d.decision == Decision.DENY
        assert "rate" in d.reason.lower()


class TestCustomZones:
    def test_add_domain_to_green(self):
        hl = HyperLanePy()
        hl.add_domain("safe.example.com", Zone.GREEN)
        assert hl.classify_zone("https://safe.example.com/api") == Zone.GREEN

    def test_add_domain_to_yellow(self):
        hl = HyperLanePy()
        hl.add_domain("semi-trusted.com", Zone.YELLOW)
        assert hl.classify_zone("https://semi-trusted.com/write") == Zone.YELLOW
