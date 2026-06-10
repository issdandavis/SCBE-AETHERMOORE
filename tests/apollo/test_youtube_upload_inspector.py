from __future__ import annotations

from scripts.apollo.youtube_upload_inspector import (
    UploadSourceEvidence,
    inspect_video_record,
    parse_iso_duration,
)


def test_parse_iso_duration_handles_youtube_format() -> None:
    assert parse_iso_duration("PT1H2M3S") == 3723
    assert parse_iso_duration("PT7M10S") == 430
    assert parse_iso_duration("PT45S") == 45
    assert parse_iso_duration("bad") == 0


def test_inspect_video_record_flags_missing_transcript(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.apollo.youtube_upload_inspector.get_transcript_text",
        lambda video_id: (True, ""),
    )

    report = inspect_video_record(
        {
            "id": "abc123",
            "snippet": {
                "title": "Demo",
                "description": (
                    "Previously, the chapter set up the conflict. In this chapter, the next choice lands. "
                    "Subscribe and click the notification bell. Next chapter continues the aftermath."
                ),
            },
            "contentDetails": {"duration": "PT2M"},
            "status": {"privacyStatus": "unlisted", "uploadStatus": "processed"},
            "processingDetails": {"processingStatus": "succeeded"},
        },
        {},
    )

    assert report.risk == "medium"
    assert "No YouTube transcript/captions were available" in report.issues
    assert any("cannot overwrite" in suggestion for suggestion in report.suggestions)


def test_inspect_video_record_flags_transcript_tail_without_terminal_punctuation(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.apollo.youtube_upload_inspector.get_transcript_text",
        lambda video_id: (
            True,
            (
                "This is a complete enough transcript with enough words to avoid the short transcript "
                "duration warning while still carrying a realistic spoken cadence for inspection. "
                "The ending should look suspicious because the final clause stops in the middle of a"
            ),
        ),
    )

    report = inspect_video_record(
        {
            "id": "abc123",
            "snippet": {
                "title": "Demo",
                "description": (
                    "Previously, the chapter set up the conflict. In this chapter, the next choice lands. "
                    "Subscribe and click the notification bell. Next chapter continues the aftermath."
                ),
            },
            "contentDetails": {"duration": "PT5S"},
            "status": {"privacyStatus": "public", "uploadStatus": "processed"},
            "processingDetails": {"processingStatus": "succeeded"},
        },
        {},
    )

    assert report.risk == "low"
    assert "Transcript tail does not end with terminal punctuation" in report.issues


def test_inspect_video_record_emits_tail_repair_commands_for_known_source(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.apollo.youtube_upload_inspector.get_transcript_text",
        lambda video_id: (True, "This transcript has a clean ending."),
    )

    source_index = {
        "title:demo": UploadSourceEvidence(
            file="artifacts/youtube/demo.mp4",
            evidence_file="artifacts/publish_browser/youtube_demo.json",
            dry_run=False,
        )
    }
    report = inspect_video_record(
        {
            "id": "abc123",
            "snippet": {
                "title": "Demo",
                "description": (
                    "Previously, the chapter set up the conflict. In this chapter, the next choice lands. "
                    "Subscribe and click the notification bell. Next chapter continues the aftermath."
                ),
            },
            "contentDetails": {"duration": "PT60S"},
            "status": {"privacyStatus": "unlisted", "uploadStatus": "processed"},
            "processingDetails": {"processingStatus": "succeeded"},
        },
        source_index,
    )

    assert any("youtube_video_tool.py tail" in suggestion for suggestion in report.suggestions)
    assert any("append-ending" in suggestion for suggestion in report.suggestions)


def test_inspect_video_record_flags_missing_viewer_chapter_package(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.apollo.youtube_upload_inspector.get_transcript_text",
        lambda video_id: (True, "This transcript has a clean ending."),
    )

    report = inspect_video_record(
        {
            "id": "abc123",
            "snippet": {"title": "Demo", "description": "Plain upload description."},
            "contentDetails": {"duration": "PT60S"},
            "status": {"privacyStatus": "public", "uploadStatus": "processed"},
            "processingDetails": {"processingStatus": "succeeded"},
        },
        {},
    )

    assert "Viewer package lacks a pre-chapter recap" in report.issues
    assert "Viewer package lacks next-chapter lead-in" in report.issues
    assert any("what happened before" in suggestion for suggestion in report.suggestions)
