#!/usr/bin/env python3
"""Local YouTube video QA, tail repair, and upload planning.

This tool checks the rendered media file, not just the task state that produced it.
It is intentionally local-first: inspect, extract a tail clip, append a repaired ending,
then hand off to the existing YouTube uploader only after the media passes the gate.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_DIR = REPO_ROOT / "artifacts" / "youtube" / "reviews"
DEFAULT_WORDS_PER_SECOND = 2.6
DEFAULT_TAIL_SECONDS = 8.0
DEFAULT_MIN_SCORE = 80
CTA_PATTERN = re.compile(r"\b(subscribe|notification|bell|like|comment|share)\b", re.IGNORECASE)
RECAP_PATTERN = re.compile(r"\b(previously|last time|last chapter|recap|what happened before)\b", re.IGNORECASE)
CHAPTER_SETUP_PATTERN = re.compile(r"\b(this chapter|in this episode|today we|we begin|chapter \d+)\b", re.IGNORECASE)
NEXT_LEAD_PATTERN = re.compile(r"\b(next chapter|next time|next episode|coming up|sets up|stay tuned)\b", re.IGNORECASE)


@dataclass(frozen=True)
class MediaProbe:
    """Normalized media facts from ffprobe."""

    file: str
    exists: bool
    size_bytes: int = 0
    format_name: str = ""
    duration_seconds: float = 0.0
    video_duration_seconds: float | None = None
    audio_duration_seconds: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    width: int | None = None
    height: int | None = None
    frame_rate: float | None = None
    video_streams: int = 0
    audio_streams: int = 0
    probe_error: str | None = None


@dataclass(frozen=True)
class ScriptPlan:
    """What the intended script says about expected runtime."""

    path: str | None
    available: bool
    word_count: int = 0
    expected_seconds: float | None = None
    final_words: str = ""


@dataclass(frozen=True)
class ChapterPackage:
    """Viewer-facing chapter framing detected in the upload package text."""

    recap_present: bool
    chapter_setup_present: bool
    outro_present: bool
    next_lead_present: bool
    required: bool = False


def build_chapter_package(
    *,
    package_text: str,
    script: ScriptPlan,
    require_chapter_package: bool = False,
) -> ChapterPackage:
    """Detect recap / chapter-setup / outro / next-lead framing in the viewer package.

    ``package_text`` is the upload-facing text (description plus transcript
    tail). The script's final words also count toward detection, since closing
    CTA and lead-in language often live in the narration rather than the
    description.
    """
    haystack = " ".join(part for part in (package_text, script.final_words) if part)
    return ChapterPackage(
        recap_present=bool(RECAP_PATTERN.search(haystack)),
        chapter_setup_present=bool(CHAPTER_SETUP_PATTERN.search(haystack)),
        outro_present=bool(CTA_PATTERN.search(haystack)),
        next_lead_present=bool(NEXT_LEAD_PATTERN.search(haystack)),
        required=require_chapter_package,
    )


@dataclass(frozen=True)
class TailSignal:
    """What we can tell about the final seconds of audio."""

    checked: bool
    seconds: float
    mostly_silent: bool | None = None
    silence_events: list[dict[str, float]] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class TranscriptAlignment:
    """Optional check that an external transcript includes the script ending."""

    checked: bool
    path: str | None = None
    final_words_found: bool | None = None
    error: str | None = None


@dataclass(frozen=True)
class YouTubeTreatment:
    """Packaging artifacts that make a rendered MP4 upload-ready for YouTube."""

    description_present: bool
    cta_present: bool
    captions_present: bool
    captions_path: str | None = None
    multilingual_ready: bool = False


@dataclass(frozen=True)
class InspectionReport:
    """Complete upload-readiness report."""

    file: str
    ready_for_upload: bool
    readiness_score: int
    issues: list[str]
    suggestions: list[str]
    media: MediaProbe
    script: ScriptPlan
    tail: TailSignal
    transcript: TranscriptAlignment
    treatment: YouTubeTreatment
    upload_command: list[str] | None
    generated_at: str
    understandings: dict[str, Any]


def run(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def parse_frame_rate(rate: str | None) -> float | None:
    if not rate:
        return None
    if "/" not in rate:
        return parse_float(rate)
    left, right = rate.split("/", 1)
    numerator = parse_float(left)
    denominator = parse_float(right)
    if numerator is None or not denominator:
        return None
    return numerator / denominator


def media_probe_from_ffprobe(path: Path, payload: dict[str, Any], error: str | None = None) -> MediaProbe:
    streams = payload.get("streams", []) if isinstance(payload, dict) else []
    fmt = payload.get("format", {}) if isinstance(payload, dict) else {}
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    duration = parse_float(fmt.get("duration")) or 0.0

    def stream_duration(stream_list: list[dict[str, Any]]) -> float | None:
        for stream in stream_list:
            parsed = parse_float(stream.get("duration"))
            if parsed is not None:
                return parsed
        return None

    first_video = video_streams[0] if video_streams else {}
    first_audio = audio_streams[0] if audio_streams else {}
    return MediaProbe(
        file=str(path),
        exists=path.exists(),
        size_bytes=path.stat().st_size if path.exists() else 0,
        format_name=str(fmt.get("format_name", "")),
        duration_seconds=duration,
        video_duration_seconds=stream_duration(video_streams),
        audio_duration_seconds=stream_duration(audio_streams),
        video_codec=first_video.get("codec_name"),
        audio_codec=first_audio.get("codec_name"),
        width=first_video.get("width"),
        height=first_video.get("height"),
        frame_rate=parse_frame_rate(first_video.get("avg_frame_rate") or first_video.get("r_frame_rate")),
        video_streams=len(video_streams),
        audio_streams=len(audio_streams),
        probe_error=error,
    )


def probe_media(path: Path) -> MediaProbe:
    if not path.exists():
        return MediaProbe(file=str(path), exists=False, probe_error="file does not exist")
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    if result.returncode != 0:
        return media_probe_from_ffprobe(path, {}, result.stderr.strip() or result.stdout.strip())
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return media_probe_from_ffprobe(path, {}, f"invalid ffprobe JSON: {exc}")
    return media_probe_from_ffprobe(path, payload)


def strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^---[\s\S]*?---", " ", text)
    text = re.sub(r"[#>*_`~-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", strip_markdown(text))


def read_script_plan(path: Path | None, words_per_second: float = DEFAULT_WORDS_PER_SECOND) -> ScriptPlan:
    if not path:
        return ScriptPlan(path=None, available=False)
    if not path.exists():
        return ScriptPlan(path=str(path), available=False)
    text = path.read_text(encoding="utf-8", errors="replace")
    tokens = words(text)
    final_words = " ".join(tokens[-16:])
    expected = len(tokens) / words_per_second if words_per_second > 0 else None
    return ScriptPlan(
        path=str(path), available=True, word_count=len(tokens), expected_seconds=expected, final_words=final_words
    )


def parse_silencedetect(stderr: str, tail_seconds: float) -> TailSignal:
    events: list[dict[str, float]] = []
    current_start: float | None = None
    for line in stderr.splitlines():
        start_match = re.search(r"silence_start:\s*([0-9.]+)", line)
        if start_match:
            current_start = float(start_match.group(1))
            continue
        end_match = re.search(r"silence_end:\s*([0-9.]+).*silence_duration:\s*([0-9.]+)", line)
        if end_match:
            start = (
                current_start
                if current_start is not None
                else max(0.0, float(end_match.group(1)) - float(end_match.group(2)))
            )
            events.append({"start": start, "end": float(end_match.group(1)), "duration": float(end_match.group(2))})
            current_start = None

    silent_seconds = sum(event["duration"] for event in events)
    mostly_silent = silent_seconds >= max(2.0, tail_seconds * 0.65)
    return TailSignal(checked=True, seconds=tail_seconds, mostly_silent=mostly_silent, silence_events=events)


def check_tail_signal(path: Path, tail_seconds: float = DEFAULT_TAIL_SECONDS) -> TailSignal:
    if not path.exists():
        return TailSignal(checked=False, seconds=tail_seconds, error="file does not exist")
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-sseof",
            f"-{tail_seconds:g}",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-45dB:d=1",
            "-f",
            "null",
            "-",
        ]
    )
    if result.returncode != 0 and "silence_" not in result.stderr:
        return TailSignal(checked=False, seconds=tail_seconds, error=result.stderr.strip()[-500:])
    return parse_silencedetect(result.stderr, tail_seconds)


def align_transcript(transcript_path: Path | None, script: ScriptPlan) -> TranscriptAlignment:
    if not transcript_path:
        return TranscriptAlignment(checked=False)
    if not transcript_path.exists():
        return TranscriptAlignment(checked=False, path=str(transcript_path), error="transcript file does not exist")
    if not script.final_words:
        return TranscriptAlignment(checked=False, path=str(transcript_path), error="no script ending to compare")
    transcript_words = " ".join(words(transcript_path.read_text(encoding="utf-8", errors="replace"))).lower()
    final_tokens = script.final_words.lower().split()
    if len(final_tokens) > 8:
        final_tokens = final_tokens[-8:]
    final_words_found = " ".join(final_tokens) in transcript_words
    return TranscriptAlignment(checked=True, path=str(transcript_path), final_words_found=final_words_found)


def load_text_argument(text: str | None, path: Path | None) -> str:
    if text:
        return text
    if path and path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def build_treatment(
    *,
    description_text: str = "",
    script: ScriptPlan,
    transcript_path: Path | None = None,
    captions_path: Path | None = None,
    require_multilingual: bool = False,
) -> YouTubeTreatment:
    combined = " ".join(part for part in [description_text, script.final_words] if part)
    captions_file = captions_path or transcript_path
    captions_present = bool(captions_file and captions_file.exists())
    return YouTubeTreatment(
        description_present=bool(description_text.strip()),
        cta_present=bool(CTA_PATTERN.search(combined)),
        captions_present=captions_present,
        captions_path=str(captions_file) if captions_file else None,
        multilingual_ready=not require_multilingual,
    )


def build_upload_command(
    video_file: Path, title: str | None, article: Path | None = None, description_text: str = ""
) -> list[str] | None:
    if not title:
        return None
    command = [
        sys.executable,
        "scripts/publish/post_to_youtube.py",
        "--file",
        str(video_file),
        "--title",
        title,
        "--privacy",
        "unlisted",
    ]
    if article:
        command.extend(["--article", str(article)])
    if description_text.strip():
        command.extend(["--description", description_text.strip()])
    return command


def score_inspection(
    media: MediaProbe,
    script: ScriptPlan,
    tail: TailSignal,
    transcript: TranscriptAlignment,
    treatment: YouTubeTreatment | None = None,
    *,
    min_score: int = DEFAULT_MIN_SCORE,
    require_youtube_treatment: bool = False,
) -> tuple[int, bool, list[str], list[str]]:
    score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    if not media.exists:
        return 0, False, ["Video file does not exist"], ["Render the video before upload."]
    if media.probe_error:
        score -= 40
        issues.append(f"ffprobe could not fully inspect the file: {media.probe_error}")
        suggestions.append("Re-render or remux the MP4, then inspect again.")
    if media.duration_seconds <= 0:
        score -= 45
        issues.append("Container duration is missing or zero")
        suggestions.append("Rebuild the MP4 with FFmpeg before upload.")
    if media.video_streams < 1:
        score -= 45
        issues.append("No video stream found")
    if media.audio_streams < 1:
        score -= 35
        issues.append("No audio stream found")
        suggestions.append("Attach narration/audio before upload.")

    if media.video_duration_seconds and media.audio_duration_seconds:
        delta = abs(media.video_duration_seconds - media.audio_duration_seconds)
        if delta > 2.0:
            score -= min(20, 8 + round(delta))
            issues.append(f"Audio/video duration mismatch is {delta:.1f}s")
            suggestions.append("Remux or rebuild so audio and video end together.")

    if not script.available:
        score -= 8
        issues.append("No script/source text was provided for runtime comparison")
        suggestions.append("Pass --script to detect cut endings against the intended narration.")
    elif script.expected_seconds is not None:
        allowed_gap = max(12.0, script.expected_seconds * 0.12)
        if script.expected_seconds > media.duration_seconds + allowed_gap:
            gap = script.expected_seconds - media.duration_seconds
            score -= min(35, 12 + round(gap / 3))
            issues.append(f"Script runtime estimate exceeds video by {gap:.1f}s")
            suggestions.append("The render may be cut short; inspect the tail and append/rerender the ending.")

    if tail.checked and tail.mostly_silent is True:
        score -= 18
        issues.append(f"Final {tail.seconds:g}s are mostly silent")
        suggestions.append("Check whether the narration ended early or the outro is dead air.")
    elif not tail.checked:
        score -= 4
        suggestions.append("Tail audio could not be checked; run on a machine with ffmpeg available.")

    if transcript.checked and transcript.final_words_found is False:
        score -= 22
        issues.append("Transcript does not include the script ending")
        suggestions.append("The spoken/rendered ending likely does not match the source script.")

    if treatment:
        if require_youtube_treatment and not treatment.description_present:
            score -= 10
            issues.append("YouTube description/treatment text is missing")
            suggestions.append("Provide --description or --description-file before upload planning.")
        if require_youtube_treatment and not treatment.cta_present:
            score -= 8
            issues.append("YouTube treatment lacks subscribe/notification-bell CTA language")
            suggestions.append("Add a short subscribe/bell CTA to the description or closing script.")
        if require_youtube_treatment and not treatment.captions_present:
            score -= 15
            issues.append("Caption/transcript artifact is missing")
            suggestions.append("Pass --captions or --transcript so the upload has a caption source.")
        if require_youtube_treatment and not treatment.multilingual_ready:
            suggestions.append(
                "Multilingual captions are a Phase 2 gate; current requirement is source-language captions."
            )

    score = max(0, min(100, score))
    ready = score >= min_score and not any(
        marker in issue.lower() for issue in issues for marker in ("does not exist", "no video stream", "zero")
    )
    if ready:
        suggestions.append("Upload as unlisted first, then review on YouTube before making public.")
    return score, ready, issues, suggestions


def inspect_video(
    video_file: Path,
    *,
    script_path: Path | None = None,
    transcript_path: Path | None = None,
    captions_path: Path | None = None,
    description_text: str = "",
    title: str | None = None,
    min_score: int = DEFAULT_MIN_SCORE,
    tail_seconds: float = DEFAULT_TAIL_SECONDS,
    words_per_second: float = DEFAULT_WORDS_PER_SECOND,
    require_youtube_treatment: bool = False,
    require_multilingual: bool = False,
) -> InspectionReport:
    media = probe_media(video_file)
    script = read_script_plan(script_path, words_per_second)
    tail = (
        check_tail_signal(video_file, tail_seconds)
        if media.exists and media.audio_streams
        else TailSignal(False, tail_seconds)
    )
    transcript = align_transcript(transcript_path, script)
    treatment = build_treatment(
        description_text=description_text,
        script=script,
        transcript_path=transcript_path,
        captions_path=captions_path,
        require_multilingual=require_multilingual,
    )
    score, ready, issues, suggestions = score_inspection(
        media,
        script,
        tail,
        transcript,
        treatment,
        min_score=min_score,
        require_youtube_treatment=require_youtube_treatment,
    )
    upload_command = build_upload_command(video_file, title, script_path, description_text) if ready else None
    understandings = {
        "container_probe": {
            "duration_seconds": media.duration_seconds,
            "video_streams": media.video_streams,
            "audio_streams": media.audio_streams,
            "resolution": f"{media.width}x{media.height}" if media.width and media.height else None,
        },
        "script_plan": asdict(script),
        "audio_tail": asdict(tail),
        "transcript_alignment": asdict(transcript),
        "youtube_treatment": asdict(treatment),
        "ai_video_review": {
            "frame_export_command": (
                f"python scripts/publish/youtube_video_tool.py frames --file {video_file} "
                f"--out-dir {DEFAULT_REVIEW_DIR / (video_file.stem + '.frames')}"
            ),
            "tail_export_command": (
                f"python scripts/publish/youtube_video_tool.py tail --file {video_file} --seconds 12 "
                f"--out {DEFAULT_REVIEW_DIR / (video_file.stem + '.tail.mp4')}"
            ),
        },
        "upload_gate": {"min_score": min_score, "ready": ready, "score": score},
    }
    return InspectionReport(
        file=str(video_file),
        ready_for_upload=ready,
        readiness_score=score,
        issues=issues,
        suggestions=suggestions,
        media=media,
        script=script,
        tail=tail,
        transcript=transcript,
        treatment=treatment,
        upload_command=upload_command,
        generated_at=datetime.now(timezone.utc).isoformat(),
        understandings=understandings,
    )


def default_report_path(video_file: Path) -> Path:
    return DEFAULT_REVIEW_DIR / f"{video_file.stem}.inspection.json"


def write_report(report: InspectionReport, output_path: Path | None) -> Path:
    path = output_path or default_report_path(Path(report.file))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    return path


def export_tail(video_file: Path, output_file: Path, seconds: float) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result = run(["ffmpeg", "-y", "-sseof", f"-{seconds:g}", "-i", str(video_file), "-c", "copy", str(output_file)])
    if result.returncode == 0:
        return 0
    fallback = run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            f"-{seconds:g}",
            "-i",
            str(video_file),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_file),
        ]
    )
    if fallback.returncode != 0:
        print(fallback.stderr or result.stderr, file=sys.stderr)
    return fallback.returncode


def export_frames(video_file: Path, output_dir: Path, *, fps: float = 1.0, every_frame: bool = False) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%06d.jpg"
    vf = "fps=1" if every_frame else f"fps={fps:g}"
    if every_frame:
        command = ["ffmpeg", "-y", "-i", str(video_file), str(pattern)]
    else:
        command = ["ffmpeg", "-y", "-i", str(video_file), "-vf", vf, str(pattern)]
    result = run(command, timeout=600)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    frames = sorted(output_dir.glob("frame_*.jpg"))
    manifest = {
        "video": str(video_file),
        "output_dir": str(output_dir),
        "every_frame": every_frame,
        "fps": None if every_frame else fps,
        "frame_count": len(frames),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "frames_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Frames: {len(frames)}")
    print(f"Manifest: {output_dir / 'frames_manifest.json'}")
    return 0


def concat_line(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
    return f"file '{escaped}'\n"


def append_ending(video_file: Path, ending_file: Path, output_file: Path, *, reencode: bool = False) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        concat_path = Path(handle.name)
        handle.write(concat_line(video_file))
        handle.write(concat_line(ending_file))
    try:
        command = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path)]
        if reencode:
            command.extend(["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"])
        else:
            command.extend(["-c", "copy"])
        command.append(str(output_file))
        result = run(command)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            if not reencode:
                print("Concat copy failed. Retry with --reencode if the clips use different codecs.", file=sys.stderr)
        return result.returncode
    finally:
        concat_path.unlink(missing_ok=True)


def print_report_summary(report: InspectionReport, report_path: Path | None = None) -> None:
    print(f"Video: {report.file}")
    print(f"Readiness: {report.readiness_score}/100")
    print(f"Ready for upload: {'YES' if report.ready_for_upload else 'NO'}")
    if report_path:
        print(f"Report: {report_path}")
    if report.issues:
        print("\nIssues:")
        for issue in report.issues:
            print(f"- {issue}")
    if report.suggestions:
        print("\nSuggestions:")
        for suggestion in report.suggestions:
            print(f"- {suggestion}")
    if report.upload_command:
        print("\nUpload command:")
        print(" ".join(f'"{item}"' if " " in item else item for item in report.upload_command))


def add_common_inspect_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--file", required=True, type=Path, help="Rendered video file to inspect")
    parser.add_argument("--script", type=Path, help="Original script/article text used to render narration")
    parser.add_argument(
        "--transcript", type=Path, help="Optional transcript/caption text to compare against the script"
    )
    parser.add_argument("--captions", type=Path, help="Caption/subtitle artifact intended for upload")
    parser.add_argument("--description", help="YouTube description/treatment text")
    parser.add_argument("--description-file", type=Path, help="File containing YouTube description/treatment text")
    parser.add_argument("--title", help="YouTube title; enables upload command planning when the gate passes")
    parser.add_argument(
        "--require-youtube-treatment",
        action="store_true",
        help="Require description, subscribe/bell CTA, and captions before upload planning",
    )
    parser.add_argument(
        "--require-multilingual",
        action="store_true",
        help="Reserve the multilingual caption gate for Phase 2 reports",
    )
    parser.add_argument(
        "--min-score", type=int, default=DEFAULT_MIN_SCORE, help="Minimum readiness score to plan upload"
    )
    parser.add_argument(
        "--tail-seconds", type=float, default=DEFAULT_TAIL_SECONDS, help="Final seconds to scan for silence"
    )
    parser.add_argument(
        "--words-per-second", type=float, default=DEFAULT_WORDS_PER_SECOND, help="Narration speed estimate"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect, repair, and plan YouTube uploads for rendered videos.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect media and write an upload-readiness report")
    add_common_inspect_args(inspect_parser)
    inspect_parser.add_argument("--out", type=Path, help="Inspection JSON path")

    plan_parser = subparsers.add_parser(
        "plan-upload", help="Inspect media and print an unlisted upload command if ready"
    )
    add_common_inspect_args(plan_parser)
    plan_parser.add_argument("--out", type=Path, help="Inspection JSON path")

    tail_parser = subparsers.add_parser("tail", help="Export the final seconds of a video for quick review")
    tail_parser.add_argument("--file", required=True, type=Path)
    tail_parser.add_argument("--seconds", type=float, default=12.0)
    tail_parser.add_argument("--out", required=True, type=Path)

    frames_parser = subparsers.add_parser("frames", help="Export video frames for AI/human visual review")
    frames_parser.add_argument("--file", required=True, type=Path)
    frames_parser.add_argument("--out-dir", required=True, type=Path)
    frames_parser.add_argument("--fps", type=float, default=1.0, help="Sampled frames per second")
    frames_parser.add_argument("--every-frame", action="store_true", help="Export every frame; can be large")

    append_parser = subparsers.add_parser(
        "append-ending", help="Append a fixed ending clip without regenerating the full video"
    )
    append_parser.add_argument("--file", required=True, type=Path)
    append_parser.add_argument("--ending", required=True, type=Path)
    append_parser.add_argument("--out", required=True, type=Path)
    append_parser.add_argument("--reencode", action="store_true", help="Use when the original and ending codecs differ")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"inspect", "plan-upload"}:
        description_text = load_text_argument(args.description, args.description_file)
        report = inspect_video(
            args.file,
            script_path=args.script,
            transcript_path=args.transcript,
            captions_path=args.captions,
            description_text=description_text,
            title=args.title,
            min_score=args.min_score,
            tail_seconds=args.tail_seconds,
            words_per_second=args.words_per_second,
            require_youtube_treatment=args.require_youtube_treatment,
            require_multilingual=args.require_multilingual,
        )
        report_path = write_report(report, args.out)
        print_report_summary(report, report_path)
        return 0 if report.ready_for_upload or args.command == "inspect" else 2
    if args.command == "tail":
        return export_tail(args.file, args.out, args.seconds)
    if args.command == "frames":
        return export_frames(args.file, args.out_dir, fps=args.fps, every_frame=args.every_frame)
    if args.command == "append-ending":
        return append_ending(args.file, args.ending, args.out, reencode=args.reencode)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
