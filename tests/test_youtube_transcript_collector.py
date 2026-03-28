"""Tests for Apollo YouTube Transcript Collector."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from scripts.apollo.youtube_transcript_collector import (
    _TRANSCRIPT_DELAY,
    get_transcript,
    scrub_transcript,
    generate_sft_from_transcript,
    load_channels,
    search_channel_videos,
)


class TestSearchChannelVideos:
    """Verify handle-based search to avoid ambiguous channel matches."""

    @patch("subprocess.run")
    def test_uses_handle_when_provided(self, mock_run):
        """When a handle is given, yt-dlp search should use it instead of the display name."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="abc123 Some Video Title\n"
        )
        search_channel_videos("Robert Miles", max_results=3, handle="@RobertMilesAI")
        call_args = mock_run.call_args[0][0]
        # The search query should contain the handle, not the display name
        assert any("@RobertMilesAI" in arg for arg in call_args)
        assert not any("Robert Miles" in arg for arg in call_args)

    @patch("subprocess.run")
    def test_falls_back_to_name_without_handle(self, mock_run):
        """Without a handle, yt-dlp search should use the display name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="xyz789 Another Video\n")
        search_channel_videos("3Blue1Brown", max_results=2)
        call_args = mock_run.call_args[0][0]
        assert any("3Blue1Brown" in arg for arg in call_args)

    @patch("subprocess.run")
    def test_handle_none_uses_name(self, mock_run):
        """Explicitly passing handle=None should fall back to name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="vid1 Title One\n")
        search_channel_videos("Fireship", max_results=1, handle=None)
        call_args = mock_run.call_args[0][0]
        assert any("Fireship" in arg for arg in call_args)


class TestTranscriptDelay:
    def test_delay_is_30_seconds(self):
        """Delay should be 30s to avoid aggressive YouTube rate limiting."""
        assert _TRANSCRIPT_DELAY == 30


class TestChannelHandles:
    def test_all_channels_have_handles(self):
        """Every curated channel should have a handle field for unambiguous search."""
        for c in load_channels():
            assert "handle" in c, f"Channel {c['name']} missing 'handle' field"
            assert c["handle"].startswith(
                "@"
            ), f"Handle for {c['name']} must start with @"


class TestLoadChannels:
    def test_loads_channel_list(self):
        channels = load_channels()
        assert len(channels) >= 10

    def test_channels_have_required_fields(self):
        for c in load_channels():
            assert "name" in c
            assert "tongue" in c
            assert c["tongue"] in ("KO", "AV", "RU", "CA", "UM", "DR")
            assert "rating" in c
            assert 1 <= c["rating"] <= 5

    def test_all_tongues_represented(self):
        tongues = set(c["tongue"] for c in load_channels())
        assert tongues == {"KO", "AV", "RU", "CA", "UM", "DR"}


class TestGetTranscript:
    @pytest.mark.skipif(
        not pytest.importorskip(
            "youtube_transcript_api", reason="youtube-transcript-api not installed"
        ),
        reason="network-dependent",
    )
    def test_real_video_returns_text(self):
        """Integration test — pulls a real transcript. May fail if IP rate-limited."""
        result = get_transcript("sD0NjbwqlYw")  # Riemann zeta
        if result is None:
            pytest.skip("YouTube rate-limited this IP")
        assert len(result) > 1000
        assert "zeta" in result.lower()

    def test_invalid_video_returns_none(self):
        result = get_transcript("ZZZZZZZZZZZZ")
        assert result is None

    def test_api_v2_fetch_interface(self):
        """Verify we use the new fetch() API, not the old get_transcript()."""
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        assert hasattr(api, "fetch"), "API must have fetch() method"
        assert not hasattr(
            YouTubeTranscriptApi, "get_transcript"
        ), "Old get_transcript class method should not exist in v2"


class TestScrubTranscript:
    def test_clean_text_unchanged(self):
        clean, count = scrub_transcript("This is a normal transcript about math.")
        assert "normal transcript" in clean
        assert count == 0

    def test_urls_scrubbed(self):
        clean, _ = scrub_transcript("Visit https://evil.com/steal for more info.")
        assert "evil.com" not in clean
        assert "[URL]" in clean

    def test_secrets_scrubbed(self):
        clean, count = scrub_transcript(
            "Use api_key=sk-1234567890abcdef to authenticate."
        )
        assert "sk-1234567890abcdef" not in clean
        assert count > 0


class TestGenerateSFT:
    def test_generates_pairs_from_long_transcript(self):
        channel = {
            "name": "Test Channel",
            "tongue": "CA",
            "domain": "math",
            "rating": 5,
        }
        transcript = "This is a long transcript about mathematics. " * 50
        pairs = generate_sft_from_transcript(channel, "Test Video", transcript)
        assert len(pairs) >= 1
        assert all("instruction" in p for p in pairs)
        assert all("response" in p for p in pairs)
        assert all(p["tongue"] == "CA" for p in pairs)

    def test_short_transcript_generates_fewer_pairs(self):
        channel = {"name": "Test", "tongue": "KO", "domain": "test", "rating": 3}
        pairs = generate_sft_from_transcript(channel, "Short", "Too short.")
        assert len(pairs) == 0

    def test_sft_pairs_are_valid_json(self):
        channel = {
            "name": "Test Channel",
            "tongue": "DR",
            "domain": "structure",
            "rating": 4,
        }
        transcript = (
            "Here we explain complex system architecture and design patterns. " * 30
        )
        pairs = generate_sft_from_transcript(
            channel, "Architecture Deep Dive", transcript
        )
        for p in pairs:
            # Must be serializable
            serialized = json.dumps(p)
            loaded = json.loads(serialized)
            assert loaded["source"].startswith("youtube_")
            assert loaded["category"].startswith("youtube_")


class TestVideoMetadata:
    """Verify transcript collection saves auditable metadata."""

    def test_transcript_file_naming(self):
        """Transcript files should follow channel_videoid.txt pattern."""
        import re

        pattern = re.compile(r"^[a-z0-9_]+_[A-Za-z0-9_-]+\.txt$")
        # Check that our naming convention is valid
        assert pattern.match("3blue1brown_sD0NjbwqlYw.txt")
        assert pattern.match("own_channel_PTT5R9TEhds.txt")
        assert not pattern.match("bad file name.txt")
