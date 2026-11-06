from __future__ import annotations

import json
from pathlib import Path

import pytest

from video_lattice.knock_v import (
    RIGHTS_POLICY,
    SCHEMA,
    build_knock_v,
    inspect_window,
    load_transcript,
    sha256_file,
)


def fake_probe(source: Path, binary: str):
    assert source.is_file()
    return {
        "duration_seconds": 3.0,
        "source_fps": 30.0,
        "has_audio": True,
        "streams": [{"index": 0, "codec_type": "video", "codec_name": "fake"}],
        "ffprobe": {"path": binary, "version": "fixture"},
    }


def fake_extract(source: Path, staging: Path, probe: dict, sample_fps: float, binary: str):
    frame_dir = staging / "frames"
    frame_dir.mkdir()
    for index in range(1, 4):
        (frame_dir / f"frame_{index:08d}.jpg").write_bytes(f"frame-{index}".encode())
    audio = staging / "audio_16000hz_mono.wav"
    audio.write_bytes(b"fixture-audio")
    return {"ffmpeg": {"path": binary, "version": "fixture"}, "audio_path": audio}


def test_builds_hashed_analysis_only_frame_audio_transcript_bundle(tmp_path: Path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"fixture-video")
    transcript = tmp_path / "transcript.json"
    transcript.write_text(
        json.dumps(
            {
                "segments": [
                    {"text": "opening", "start": 0.0, "duration": 0.8},
                    {"text": "later", "start": 1.8, "duration": 0.4},
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "knock-v"
    manifest = build_knock_v(
        source,
        output,
        transcript=transcript,
        probe_fn=fake_probe,
        extract_fn=fake_extract,
    )

    assert manifest["schema"] == SCHEMA
    assert manifest["source"]["sha256"] == sha256_file(source)
    assert manifest["view"]["artifacts"]["frames_index"]["count"] == 3
    assert manifest["view"]["artifacts"]["timeline"]["segments"] == 2
    assert manifest["view"]["artifacts"]["audio"]["sample_rate_hz"] == 16000
    assert manifest["usage"] == {
        "analysis_allowed": True,
        "training_eligible": False,
        "policy": RIGHTS_POLICY,
    }
    rows = [json.loads(line) for line in (output / "timeline.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["frame_refs"] == ["frames/frame_00000001.jpg"]
    assert rows[1]["frame_refs"] == ["frames/frame_00000003.jpg"]
    assert json.loads((output / "MANIFEST.json").read_text(encoding="utf-8")) == manifest
    window = inspect_window(output, 0.5, 2.1)
    assert window["bundle_id"] == manifest["bundle_id"]
    assert [frame["frame_id"] for frame in window["frames"]] == [
        "frame_00000002",
        "frame_00000003",
    ]
    assert [segment["text"] for segment in window["transcript_segments"]] == [
        "opening",
        "later",
    ]
    assert window["audio"]["absolute_path"].endswith("audio_16000hz_mono.wav")


def test_window_inspection_rejects_tampered_frame_index(tmp_path: Path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"fixture-video")
    output = tmp_path / "knock-v"
    build_knock_v(source, output, probe_fn=fake_probe, extract_fn=fake_extract)
    (output / "frames.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="index hash"):
        inspect_window(output, 0, 1)


def test_output_is_create_only(tmp_path: Path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"fixture-video")
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        build_knock_v(source, output, probe_fn=fake_probe, extract_fn=fake_extract)


def test_invalid_transcript_is_rejected_and_pending_bundle_removed(tmp_path: Path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"fixture-video")
    transcript = tmp_path / "bad.json"
    transcript.write_text(json.dumps([{"text": "bad", "start": -1, "duration": 1}]), encoding="utf-8")
    output = tmp_path / "knock-v"
    with pytest.raises(ValueError, match="Transcript"):
        build_knock_v(
            source,
            output,
            transcript=transcript,
            probe_fn=fake_probe,
            extract_fn=fake_extract,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".*.pending"))


def test_transcript_loader_accepts_existing_youtube_payload_shape(tmp_path: Path):
    transcript = tmp_path / "youtube.json"
    transcript.write_text(
        json.dumps(
            {
                "video_id": "abcdefghijk",
                "segments": [{"text": "hello", "start": 1, "duration": 2}],
            }
        ),
        encoding="utf-8",
    )
    assert load_transcript(transcript, 10.0) == [
        {
            "segment_id": "segment_00000000",
            "start_seconds": 1.0,
            "end_seconds": 3.0,
            "text": "hello",
        }
    ]
