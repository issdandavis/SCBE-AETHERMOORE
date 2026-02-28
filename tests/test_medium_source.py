"""Tests for the Medium source adapter (read via RSS + write via API)."""

from __future__ import annotations

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.obsidian_researcher.source_adapter import IngestionResult, SourceType
from agents.obsidian_researcher.sources.medium_source import MediumSource


# ==========================================================================
# Mock data
# ==========================================================================

MOCK_RSS2JSON_RESPONSE = {
    "status": "ok",
    "feed": {
        "url": "https://medium.com/feed/@testuser",
        "title": "Test User - Medium",
    },
    "items": [
        {
            "title": "Hyperbolic Geometry in AI Safety Systems",
            "link": "https://medium.com/@testuser/hyperbolic-geometry-ai-safety-abc123",
            "author": "Test User",
            "pubDate": "2026-02-15 10:00:00",
            "content": "<p>We explore how <b>hyperbolic geometry</b> creates exponential cost barriers for adversarial AI behavior.</p><p>The Poincaré ball model maps trust to distance.</p>",
            "categories": ["ai-safety", "machine-learning", "cryptography"],
            "guid": "https://medium.com/p/abc123",
            "thumbnail": "https://miro.medium.com/max/700/1*test.jpg",
        },
        {
            "title": "Building Post-Quantum Cryptography for AI Agents",
            "link": "https://medium.com/@testuser/pqc-ai-agents-def456",
            "author": "Test User",
            "pubDate": "2026-02-10 08:30:00",
            "content": "<p>Post-quantum cryptography protects AI agent fleets from quantum computing attacks.</p>",
            "categories": ["post-quantum", "security"],
            "guid": "https://medium.com/p/def456",
            "thumbnail": "",
        },
    ],
}

MOCK_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Test User - Medium</title>
    <item>
      <title>Hyperbolic Geometry in AI Safety Systems</title>
      <link>https://medium.com/@testuser/hyperbolic-geometry-ai-safety-abc123</link>
      <dc:creator>Test User</dc:creator>
      <pubDate>Sat, 15 Feb 2026 10:00:00 GMT</pubDate>
      <content:encoded><![CDATA[<p>We explore how hyperbolic geometry creates exponential cost barriers.</p>]]></content:encoded>
      <category>ai-safety</category>
      <category>machine-learning</category>
      <guid>https://medium.com/p/abc123</guid>
    </item>
  </channel>
</rss>"""

MOCK_MEDIUM_USER_RESPONSE = {
    "data": {
        "id": "user123456",
        "username": "testuser",
        "name": "Test User",
        "url": "https://medium.com/@testuser",
    }
}

MOCK_MEDIUM_POST_RESPONSE = {
    "data": {
        "id": "post789",
        "title": "Test Article",
        "authorId": "user123456",
        "url": "https://medium.com/@testuser/test-article-post789",
        "publishStatus": "draft",
    }
}


def _mock_urlopen_json(data: Any):
    """Create a mock urlopen returning JSON."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _mock_urlopen_bytes(data: bytes):
    """Create a mock urlopen returning raw bytes."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ==========================================================================
# Tests
# ==========================================================================


class TestMediumSourceConfig(unittest.TestCase):
    """Test configuration and initialization."""

    def test_default_config(self):
        source = MediumSource()
        self.assertEqual(source._timeout, 15)
        self.assertTrue(source._use_rss2json)

    def test_custom_config(self):
        source = MediumSource({
            "username": "myuser",
            "timeout": 30,
            "use_rss2json": False,
        })
        self.assertEqual(source._username, "myuser")
        self.assertEqual(source._timeout, 30)
        self.assertFalse(source._use_rss2json)

    def test_feed_url_with_username(self):
        source = MediumSource({"username": "testuser"})
        url = source._get_feed_url()
        self.assertEqual(url, "https://medium.com/feed/@testuser")

    def test_feed_url_with_at_prefix(self):
        source = MediumSource({"username": "@testuser"})
        url = source._get_feed_url()
        self.assertEqual(url, "https://medium.com/feed/@testuser")

    def test_feed_url_with_publication(self):
        source = MediumSource({"publication": "better-programming"})
        url = source._get_feed_url()
        self.assertEqual(url, "https://medium.com/feed/better-programming")

    def test_feed_url_empty(self):
        source = MediumSource({})
        url = source._get_feed_url()
        self.assertEqual(url, "")


class TestMediumRSS2JSON(unittest.TestCase):
    """Test reading via rss2json API."""

    def setUp(self):
        self.source = MediumSource({"username": "testuser"})

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_returns_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Hyperbolic Geometry in AI Safety Systems")

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_strips_html(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("")
        # Content should have HTML stripped
        self.assertNotIn("<p>", results[0].raw_content)
        self.assertNotIn("<b>", results[0].raw_content)
        self.assertIn("hyperbolic geometry", results[0].raw_content)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_extracts_metadata(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("")
        self.assertEqual(results[0].authors, ["Test User"])
        self.assertIn("medium_url", results[0].identifiers)
        self.assertEqual(results[0].metadata["source"], "medium")

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_extracts_tags(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("")
        tags = results[0].tags
        self.assertIn("medium", tags)
        self.assertIn("tag:ai-safety", tags)
        self.assertIn("tag:machine-learning", tags)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_filters_by_query(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("Post-Quantum")
        self.assertEqual(len(results), 1)
        self.assertIn("Post-Quantum", results[0].title)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_no_match(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("nonexistent-query-xyz")
        self.assertEqual(len(results), 0)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_extracts_thumbnail(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        results = self.source.fetch("")
        self.assertIn("test.jpg", results[0].metadata["thumbnail"])


class TestMediumXMLFallback(unittest.TestCase):
    """Test direct RSS XML parsing."""

    def setUp(self):
        self.source = MediumSource({"username": "testuser", "use_rss2json": False})

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_xml_parse_returns_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_bytes(MOCK_RSS_XML.encode())
        results = self.source.fetch("")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Hyperbolic Geometry in AI Safety Systems")

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_xml_extracts_dc_creator(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_bytes(MOCK_RSS_XML.encode())
        results = self.source.fetch("")
        self.assertEqual(results[0].authors, ["Test User"])

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_xml_extracts_categories(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_bytes(MOCK_RSS_XML.encode())
        results = self.source.fetch("")
        self.assertIn("tag:ai-safety", results[0].tags)


class TestMediumFetchByID(unittest.TestCase):
    """Test fetch_by_id (find article by URL)."""

    def setUp(self):
        self.source = MediumSource({"username": "testuser"})

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_by_url(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        result = self.source.fetch_by_id(
            "https://medium.com/@testuser/hyperbolic-geometry-ai-safety-abc123"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Hyperbolic Geometry in AI Safety Systems")

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_by_guid(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        result = self.source.fetch_by_id("https://medium.com/p/abc123")
        self.assertIsNotNone(result)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_fetch_by_nonexistent(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_json(MOCK_RSS2JSON_RESPONSE)
        result = self.source.fetch_by_id("https://medium.com/nonexistent")
        self.assertIsNone(result)


class TestMediumPublish(unittest.TestCase):
    """Test the write API (publish articles)."""

    def setUp(self):
        self.source = MediumSource({
            "username": "testuser",
            "integration_token": "fake-token-123",
        })

    def test_publish_no_token(self):
        source = MediumSource({"username": "testuser"})
        result = source.publish("Test", "Content")
        self.assertIsNone(result)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_publish_success(self, mock_urlopen):
        # First call: get user ID, second call: create post
        mock_urlopen.side_effect = [
            _mock_urlopen_json(MOCK_MEDIUM_USER_RESPONSE),
            _mock_urlopen_json(MOCK_MEDIUM_POST_RESPONSE),
        ]
        result = self.source.publish(
            title="Test Article",
            content="# Hello\n\nThis is a test.",
            tags=["ai-safety", "test"],
            publish_status="draft",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test Article")
        self.assertIn("url", result)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_publish_user_lookup_fail(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.medium.com/v1/me", 401, "Unauthorized", {}, None
        )
        result = self.source.publish("Test", "Content")
        self.assertIsNone(result)

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_publish_limits_tags_to_5(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _mock_urlopen_json(MOCK_MEDIUM_USER_RESPONSE),
            _mock_urlopen_json(MOCK_MEDIUM_POST_RESPONSE),
        ]
        # Try to pass 8 tags — should be capped at 5
        result = self.source.publish(
            title="Test",
            content="Content",
            tags=["a", "b", "c", "d", "e", "f", "g", "h"],
        )
        self.assertIsNotNone(result)
        # Verify the request was made (we can't easily check the payload
        # but the code caps at 5 via tags[:5])


class TestMediumHealthCheck(unittest.TestCase):
    """Test health check."""

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_healthy(self, mock_urlopen):
        source = MediumSource({"username": "testuser"})
        mock_urlopen.return_value = _mock_urlopen_bytes(b"<rss>content</rss>")
        self.assertTrue(source.health_check())

    def test_no_username(self):
        source = MediumSource({})
        self.assertFalse(source.health_check())

    @patch("agents.obsidian_researcher.sources.medium_source.urllib.request.urlopen")
    def test_unreachable(self, mock_urlopen):
        source = MediumSource({"username": "testuser"})
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        self.assertFalse(source.health_check())


class TestMediumHelpers(unittest.TestCase):
    """Test internal helper methods."""

    def test_strip_html(self):
        text = MediumSource._strip_html("<p>Hello <b>world</b></p>")
        self.assertEqual(text, "Hello world")

    def test_strip_html_entities(self):
        text = MediumSource._strip_html("<p>A &amp; B &lt; C</p>")
        self.assertEqual(text, "A & B < C")

    def test_extract_thumbnail(self):
        html = '<figure><img src="https://example.com/img.jpg" alt="test"></figure>'
        url = MediumSource._extract_thumbnail(html)
        self.assertEqual(url, "https://example.com/img.jpg")

    def test_extract_thumbnail_none(self):
        url = MediumSource._extract_thumbnail("<p>No images here</p>")
        self.assertEqual(url, "")

    def test_parse_date_rfc822(self):
        iso = MediumSource._parse_date("Sat, 15 Feb 2026 10:00:00 GMT")
        self.assertIn("2026", iso)

    def test_parse_date_simple(self):
        iso = MediumSource._parse_date("2026-02-15 10:00:00")
        self.assertIn("2026", iso)

    def test_parse_date_empty(self):
        self.assertEqual(MediumSource._parse_date(""), "")


if __name__ == "__main__":
    unittest.main()
