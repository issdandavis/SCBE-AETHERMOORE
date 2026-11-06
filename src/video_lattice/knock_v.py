"""KNOCK-V: a content-addressed, analysis-only view of a local video.

The bundle keeps sampled frames, extracted audio, transcript timing, and hashes
together so an agent can inspect evidence by timestamp. It is never admitted to
training by this module; training requires a separate signed rights decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable
import uuid

SCHEMA = "scbe.knock-v.evidence.v1"
RIGHTS_POLICY = "ANALYSIS_ONLY_SEPARATE_SIGNED_TRAINING_ADMISSION_REQUIRED"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _run(command: list[str], timeout: float = 600.0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "media command failed").strip()
        raise RuntimeError(message[-2000:])
    return result


def _tool_version(binary: str) -> dict[str, str]:
    resolved = shutil.which(binary)
    if not resolved:
        raise FileNotFoundError(f"Required media tool not found: {binary}")
    line = _run([resolved, "-version"], timeout=10).stdout.splitlines()
    return {
        "path": str(Path(resolved).resolve()),
        "version": line[0] if line else "unknown",
    }


def _parse_rate(value: str) -> float:
    if not value:
        return 0.0
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        if float(denominator) == 0:
            return 0.0
        return float(numerator) / float(denominator)
    return float(value)


def probe_video(source: Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    tool = _tool_version(ffprobe)
    result = _run(
        [
            tool["path"],
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,avg_frame_rate",
            "-of",
            "json",
            str(source),
        ]
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    if not video_streams:
        raise ValueError("Source has no video stream")
    duration = float(payload.get("format", {}).get("duration", 0.0) or 0.0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Video duration is invalid")
    source_fps = _parse_rate(str(video_streams[0].get("avg_frame_rate", "")))
    return {
        "duration_seconds": duration,
        "source_fps": source_fps,
        "has_audio": any(stream.get("codec_type") == "audio" for stream in streams),
        "streams": streams,
        "ffprobe": tool,
    }


def extract_media(
    source: Path,
    staging: Path,
    probe: dict[str, Any],
    sample_fps: float,
    ffmpeg: str = "ffmpeg",
) -> dict[str, Any]:
    tool = _tool_version(ffmpeg)
    frame_dir = staging / "frames"
    frame_dir.mkdir()
    _run(
        [
            tool["path"],
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(source),
            "-vf",
            f"fps={sample_fps:.8g}",
            "-q:v",
            "2",
            str(frame_dir / "frame_%08d.jpg"),
        ]
    )
    audio_path: Path | None = None
    if probe["has_audio"]:
        audio_path = staging / "audio_16000hz_mono.wav"
        _run(
            [
                tool["path"],
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(audio_path),
            ]
        )
    return {"ffmpeg": tool, "audio_path": audio_path}


def load_transcript(path: Path | None, duration_seconds: float) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_segments = payload.get("segments", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_segments, list) or len(raw_segments) > 100_000:
        raise ValueError("Transcript must contain a bounded segment list")
    segments: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, dict):
            raise ValueError("Transcript segment must be an object")
        text = str(raw.get("text", "")).strip()
        start = float(raw.get("start", 0.0) or 0.0)
        duration = float(raw.get("duration", 0.0) or 0.0)
        if (
            not text
            or len(text) > 100_000
            or not math.isfinite(start)
            or not math.isfinite(duration)
            or start < 0
            or duration < 0
            or start > duration_seconds + 2.0
        ):
            raise ValueError("Transcript segment is invalid or outside the video")
        end = min(duration_seconds, start + duration)
        segments.append(
            {
                "segment_id": f"segment_{index:08d}",
                "start_seconds": start,
                "end_seconds": max(start, end),
                "text": text,
            }
        )
    return sorted(segments, key=lambda item: (item["start_seconds"], item["segment_id"]))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(canonical_json(row) + "\n")


def _nearest_frame(frames: list[dict[str, Any]], timestamp: float) -> list[str]:
    if not frames:
        return []
    nearest = min(frames, key=lambda frame: abs(frame["timestamp_seconds"] - timestamp))
    return [nearest["path"]]


def build_knock_v(
    source: Path | str,
    output: Path | str,
    *,
    transcript: Path | str | None = None,
    sample_fps: float = 1.0,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    probe_fn: Callable[[Path, str], dict[str, Any]] = probe_video,
    extract_fn: Callable[[Path, Path, dict[str, Any], float, str], dict[str, Any]] = extract_media,
) -> dict[str, Any]:
    source_path = Path(source).expanduser().resolve()
    output_path = Path(output).expanduser().resolve()
    transcript_path = Path(transcript).expanduser().resolve() if transcript else None
    if not source_path.is_file():
        raise FileNotFoundError("KNOCK-V requires a local video file")
    if output_path.exists():
        raise FileExistsError("KNOCK-V output is create-only")
    if not math.isfinite(sample_fps) or not 0.1 <= sample_fps <= 10.0:
        raise ValueError("sample_fps must be between 0.1 and 10")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = output_path.parent / f".{output_path.name}.{uuid.uuid4().hex}.pending"
    staging.mkdir()
    try:
        probe = probe_fn(source_path, ffprobe)
        media = extract_fn(source_path, staging, probe, sample_fps, ffmpeg)
        frame_files = sorted((staging / "frames").glob("frame_*.jpg"))
        if not frame_files:
            raise RuntimeError("Frame extraction produced no frames")
        frames = [
            {
                "frame_id": f"frame_{index:08d}",
                "timestamp_seconds": min(
                    float(probe["duration_seconds"]),
                    (index - 1) / sample_fps,
                ),
                "path": frame.relative_to(staging).as_posix(),
                "sha256": sha256_file(frame),
                "bytes": frame.stat().st_size,
            }
            for index, frame in enumerate(frame_files, start=1)
        ]
        segments = load_transcript(transcript_path, float(probe["duration_seconds"]))
        timeline: list[dict[str, Any]] = []
        for segment in segments:
            matched = [
                frame["path"]
                for frame in frames
                if segment["start_seconds"] <= frame["timestamp_seconds"] <= segment["end_seconds"]
            ]
            if not matched:
                matched = _nearest_frame(frames, segment["start_seconds"])
            timeline.append({**segment, "frame_refs": matched})

        frames_path = staging / "frames.jsonl"
        timeline_path = staging / "timeline.jsonl"
        _write_jsonl(frames_path, frames)
        _write_jsonl(timeline_path, timeline)
        audio_path = media.get("audio_path")
        artifacts = {
            "frames_index": {
                "path": frames_path.relative_to(staging).as_posix(),
                "sha256": sha256_file(frames_path),
                "count": len(frames),
            },
            "timeline": {
                "path": timeline_path.relative_to(staging).as_posix(),
                "sha256": sha256_file(timeline_path),
                "segments": len(timeline),
            },
            "audio": (
                None
                if audio_path is None
                else {
                    "path": Path(audio_path).relative_to(staging).as_posix(),
                    "sha256": sha256_file(Path(audio_path)),
                    "bytes": Path(audio_path).stat().st_size,
                    "sample_rate_hz": 16000,
                    "channels": 1,
                }
            ),
        }
        identity = {
            "source_sha256": sha256_file(source_path),
            "duration_seconds": float(probe["duration_seconds"]),
            "sample_fps": sample_fps,
            "artifacts": artifacts,
        }
        manifest = {
            "schema": SCHEMA,
            "bundle_id": digest_json(identity),
            "source": {
                "path": str(source_path),
                "sha256": identity["source_sha256"],
                "bytes": source_path.stat().st_size,
                "duration_seconds": identity["duration_seconds"],
                "source_fps": float(probe.get("source_fps", 0.0)),
                "streams": probe.get("streams", []),
            },
            "view": {
                "kind": "timestamped multimodal evidence",
                "sample_fps": sample_fps,
                "transcript_status": "PROVIDED" if transcript_path else "MISSING",
                "transcript_source": str(transcript_path) if transcript_path else None,
                "artifacts": artifacts,
            },
            "usage": {
                "analysis_allowed": True,
                "training_eligible": False,
                "policy": RIGHTS_POLICY,
            },
            "tools": {
                "ffprobe": probe.get("ffprobe"),
                "ffmpeg": media.get("ffmpeg"),
            },
        }
        manifest_path = staging / "MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, output_path)
        return manifest
    except BaseException:
        if staging.parent == output_path.parent and staging.name.endswith(".pending"):
            shutil.rmtree(staging, ignore_errors=True)
        raise


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def inspect_window(bundle: Path | str, start_seconds: float, end_seconds: float) -> dict[str, Any]:
    """Return a hash-verified frame/transcript window for a vision-capable agent."""

    bundle_path = Path(bundle).expanduser().resolve()
    manifest_path = bundle_path / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("usage", {}).get("training_eligible") is not False:
        raise ValueError("Unsupported or training-admitted bundle")
    duration = float(manifest["source"]["duration_seconds"])
    if (
        not math.isfinite(start_seconds)
        or not math.isfinite(end_seconds)
        or start_seconds < 0
        or end_seconds <= start_seconds
        or start_seconds > duration
    ):
        raise ValueError("Invalid KNOCK-V inspection window")
    end_seconds = min(end_seconds, duration)
    artifacts = manifest["view"]["artifacts"]
    frames_path = bundle_path / artifacts["frames_index"]["path"]
    timeline_path = bundle_path / artifacts["timeline"]["path"]
    if sha256_file(frames_path) != artifacts["frames_index"]["sha256"]:
        raise ValueError("KNOCK-V frame index hash mismatch")
    if sha256_file(timeline_path) != artifacts["timeline"]["sha256"]:
        raise ValueError("KNOCK-V timeline hash mismatch")
    frames = _read_jsonl(frames_path)
    timeline = _read_jsonl(timeline_path)
    selected_frames = [frame for frame in frames if start_seconds <= float(frame["timestamp_seconds"]) <= end_seconds]
    if not selected_frames:
        selected_paths = set(_nearest_frame(frames, start_seconds))
        selected_frames = [frame for frame in frames if frame["path"] in selected_paths]
    for frame in selected_frames:
        frame_path = bundle_path / frame["path"]
        if sha256_file(frame_path) != frame["sha256"]:
            raise ValueError("KNOCK-V frame content hash mismatch")
        frame["absolute_path"] = str(frame_path)
    selected_segments = [
        segment
        for segment in timeline
        if float(segment["end_seconds"]) >= start_seconds and float(segment["start_seconds"]) <= end_seconds
    ]
    audio = artifacts.get("audio")
    if audio:
        audio_path = bundle_path / audio["path"]
        if sha256_file(audio_path) != audio["sha256"]:
            raise ValueError("KNOCK-V audio hash mismatch")
    return {
        "schema": "scbe.knock-v.window.v1",
        "bundle_id": manifest["bundle_id"],
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "frames": selected_frames,
        "transcript_segments": selected_segments,
        "audio": (None if not audio else {**audio, "absolute_path": str(bundle_path / audio["path"])}),
        "usage": manifest["usage"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="Local video file; URLs are intentionally not downloaded",
    )
    parser.add_argument("output", type=Path, help="New create-only KNOCK-V bundle directory")
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Optional transcript JSON with timestamped segments",
    )
    parser.add_argument("--sample-fps", type=float, default=1.0)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    manifest = build_knock_v(
        args.source,
        args.output,
        transcript=args.transcript,
        sample_fps=args.sample_fps,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
    )
    print(
        json.dumps(
            {"bundle": str(args.output.resolve()), "bundle_id": manifest["bundle_id"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
