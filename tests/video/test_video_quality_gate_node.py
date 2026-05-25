from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
QUALITY_GATE = REPO_ROOT / "scripts" / "video" / "quality_gate.js"
STORY_PACKAGE = REPO_ROOT / "scripts" / "video" / "story_package.js"


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe required for video quality gate tests",
)


def render_fixture_video(path: Path, *, duration: float = 5.0) -> None:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=1280x720:rate=24:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-shortest",
            str(path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def write_story_assets(tmp_path: Path, *, description: str, final_caption: str) -> tuple[Path, Path, Path]:
    srt = tmp_path / "captions.srt"
    srt.write_text(
        "1\n"
        "00:00:00,000 --> 00:00:01,800\n"
        "The story opens cleanly.\n\n"
        "2\n"
        "00:00:02,000 --> 00:00:04,200\n"
        f"{final_caption}\n",
        encoding="utf-8",
    )
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "youtube": {
                    "title": "Miracle Memory Chapter Quality Gate Demo",
                    "description": description,
                    "tags": ["AetherMoore", "audiobook", "story"],
                    "privacy": "private",
                    "chapters": [
                        {"timestamp": "0:00", "title": "Opening"},
                        {"timestamp": "0:01", "title": "Turn"},
                        {"timestamp": "0:03", "title": "Ending"},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "source.md"
    source.write_text(
        "This chapter closes when viewers ring the bell and find the next chapter after this ending.",
        encoding="utf-8",
    )
    return srt, metadata, source


def run_quality_gate(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    out = tmp_path / "quality.json"
    result = subprocess.run(
        ["node", str(QUALITY_GATE), *args, "--out", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    return result, payload


def test_story_quality_gate_accepts_complete_story_package(tmp_path: Path) -> None:
    video = tmp_path / "story.mp4"
    render_fixture_video(video)
    srt, metadata, source = write_story_assets(
        tmp_path,
        description=(
            "A finished story package with chapters, captions, and a clear closing invitation. "
            "Subscribe and ring the notification bell for the next chapter."
        ),
        final_caption="Viewers ring the bell and find the next chapter after this ending.",
    )

    result, payload = run_quality_gate(
        tmp_path,
        "--file",
        str(video),
        "--srt",
        str(srt),
        "--metadata",
        str(metadata),
        "--source-text",
        str(source),
        "--story",
    )

    assert result.returncode == 0, result.stderr
    assert payload["summary"]["ok"] is True
    assert payload["summary"]["storyReady"] is True
    assert payload["summary"]["readinessScore"] >= 80


def test_story_quality_gate_rejects_missing_cta_and_cut_ending(tmp_path: Path) -> None:
    video = tmp_path / "story.mp4"
    render_fixture_video(video)
    srt, metadata, source = write_story_assets(
        tmp_path,
        description="A stub description without the full upload treatment.",
        final_caption="The story ends before the final words",
    )

    result, payload = run_quality_gate(
        tmp_path,
        "--file",
        str(video),
        "--srt",
        str(srt),
        "--metadata",
        str(metadata),
        "--source-text",
        str(source),
        "--story",
    )

    assert result.returncode == 1
    failed = {check["reason"] for check in payload["checks"] if not check["ok"]}
    assert "story_youtube_treatment_has_cta" in failed
    assert "source_text_final_words_present_in_final_captions" in failed
    assert payload["summary"]["storyReady"] is False


def test_story_package_builds_metadata_quality_and_manifest(tmp_path: Path) -> None:
    video = tmp_path / "story.mp4"
    render_fixture_video(video)
    srt, _metadata, source = write_story_assets(
        tmp_path,
        description="unused",
        final_caption="Viewers ring the bell and find the next chapter after this ending.",
    )
    description = tmp_path / "description.md"
    description.write_text(
        "A complete story video package with captions and chapters. "
        "Subscribe and ring the notification bell for the next chapter.",
        encoding="utf-8",
    )
    chapters = tmp_path / "chapters.json"
    chapters.write_text(
        json.dumps(
            [
                {"timestamp": "0:00", "title": "Opening"},
                {"timestamp": "0:01", "title": "Turn"},
                {"timestamp": "0:03", "title": "Ending"},
            ]
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "package"

    result = subprocess.run(
        [
            "node",
            str(STORY_PACKAGE),
            "--video",
            str(video),
            "--title",
            "Miracle Memory Chapter Quality Gate Demo",
            "--description-file",
            str(description),
            "--chapters",
            str(chapters),
            "--srt",
            str(srt),
            "--source-text",
            str(source),
            "--tags",
            "AetherMoore,audiobook,story",
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    quality = json.loads((out_dir / "quality-gate.json").read_text(encoding="utf-8"))
    manifest = json.loads((out_dir / "video-package.json").read_text(encoding="utf-8"))
    assert quality["summary"]["storyReady"] is True
    assert manifest["quality"]["storyReady"] is True
    assert manifest["quality"]["readinessScore"] >= 80
