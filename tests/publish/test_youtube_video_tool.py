from __future__ import annotations

import json
from pathlib import Path

from scripts.publish.youtube_video_tool import (
    MediaProbe,
    ScriptPlan,
    TailSignal,
    TranscriptAlignment,
    YouTubeTreatment,
    build_upload_command,
    build_treatment,
    media_probe_from_ffprobe,
    read_script_plan,
    score_inspection,
)


def test_media_probe_from_ffprobe_normalizes_streams(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    payload = {
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "10.5"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "duration": "10.5",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30000/1001",
            },
            {"codec_type": "audio", "codec_name": "aac", "duration": "10.1"},
        ],
    }

    probe = media_probe_from_ffprobe(video, payload)

    assert probe.exists is True
    assert probe.video_streams == 1
    assert probe.audio_streams == 1
    assert probe.duration_seconds == 10.5
    assert round(probe.frame_rate or 0, 2) == 29.97


def test_read_script_plan_estimates_runtime_and_final_words(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    script.write_text("# Title\n\nOne two three four five six seven eight nine ten.", encoding="utf-8")

    plan = read_script_plan(script, words_per_second=2.0)

    assert plan.available is True
    assert plan.word_count == 11
    assert plan.expected_seconds == 5.5
    assert plan.final_words.endswith("eight nine ten")


def test_score_inspection_blocks_probably_cut_ending() -> None:
    media = MediaProbe(
        file="video.mp4",
        exists=True,
        duration_seconds=30.0,
        video_duration_seconds=30.0,
        audio_duration_seconds=30.0,
        video_streams=1,
        audio_streams=1,
    )
    script = ScriptPlan(
        path="script.md", available=True, word_count=220, expected_seconds=90.0, final_words="the real ending"
    )

    score, ready, issues, suggestions = score_inspection(
        media,
        script,
        TailSignal(checked=True, seconds=8.0, mostly_silent=False),
        TranscriptAlignment(checked=False),
    )

    assert ready is False
    assert score < 80
    assert any("Script runtime estimate exceeds video" in issue for issue in issues)
    assert any("cut short" in suggestion for suggestion in suggestions)


def test_score_inspection_flags_transcript_missing_ending() -> None:
    media = MediaProbe(file="video.mp4", exists=True, duration_seconds=60.0, video_streams=1, audio_streams=1)
    script = ScriptPlan(
        path="script.md", available=True, word_count=120, expected_seconds=46.0, final_words="final line here"
    )

    score, ready, issues, _suggestions = score_inspection(
        media,
        script,
        TailSignal(checked=True, seconds=8.0, mostly_silent=False),
        TranscriptAlignment(checked=True, path="transcript.txt", final_words_found=False),
    )

    assert ready is False
    assert score == 78
    assert "Transcript does not include the script ending" in issues


def test_score_inspection_allows_good_media_with_script() -> None:
    media = MediaProbe(
        file="video.mp4",
        exists=True,
        duration_seconds=60.0,
        video_duration_seconds=60.0,
        audio_duration_seconds=59.8,
        video_streams=1,
        audio_streams=1,
    )
    script = ScriptPlan(
        path="script.md", available=True, word_count=130, expected_seconds=50.0, final_words="final line here"
    )

    score, ready, issues, suggestions = score_inspection(
        media,
        script,
        TailSignal(checked=True, seconds=8.0, mostly_silent=False),
        TranscriptAlignment(checked=False),
    )

    assert score == 100
    assert ready is True
    assert issues == []
    assert any("Upload as unlisted" in suggestion for suggestion in suggestions)


def test_score_inspection_requires_youtube_treatment_when_enabled() -> None:
    media = MediaProbe(file="video.mp4", exists=True, duration_seconds=60.0, video_streams=1, audio_streams=1)
    script = ScriptPlan(path="script.md", available=True, word_count=120, expected_seconds=46.0)
    treatment = YouTubeTreatment(description_present=False, cta_present=False, captions_present=False)

    score, ready, issues, suggestions = score_inspection(
        media,
        script,
        TailSignal(checked=True, seconds=8.0, mostly_silent=False),
        TranscriptAlignment(checked=False),
        treatment,
        require_youtube_treatment=True,
    )

    assert ready is False
    assert score == 67
    assert "YouTube description/treatment text is missing" in issues
    assert "Caption/transcript artifact is missing" in issues
    assert any("subscribe/bell CTA" in suggestion for suggestion in suggestions)


def test_build_treatment_detects_cta_and_caption_file(tmp_path: Path) -> None:
    captions = tmp_path / "captions.srt"
    captions.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    script = ScriptPlan(path="script.md", available=True, final_words="ring the notification bell")

    treatment = build_treatment(
        description_text="Subscribe for the next SCBE video.",
        script=script,
        captions_path=captions,
    )

    assert treatment.description_present is True
    assert treatment.cta_present is True
    assert treatment.captions_present is True
    assert treatment.captions_path == str(captions)


def test_build_upload_command_uses_existing_uploader() -> None:
    command = build_upload_command(
        Path("artifacts/youtube/demo.mp4"),
        "Demo",
        Path("content/articles/demo.md"),
        "Subscribe and ring the notification bell.",
    )

    assert command is not None
    command_text = json.dumps(command)
    assert "scripts/publish/post_to_youtube.py" in command_text
    assert "--privacy" in command
    assert "unlisted" in command
    assert "--description" in command
