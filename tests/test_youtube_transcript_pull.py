from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "system" / "youtube_transcript_pull.py"
SPEC = importlib.util.spec_from_file_location("youtube_transcript_pull", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_extract_video_id_from_watch_url() -> None:
    assert MODULE.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_shorts_url() -> None:
    assert MODULE.extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_fetch_transcript_normalizes_legacy_api(monkeypatch) -> None:
    class FakeApi:
        @staticmethod
        def get_transcript(video_id: str, languages: list[str]) -> list[dict[str, object]]:
            assert video_id == "dQw4w9WgXcQ"
            assert languages == ["en", "es"]
            return [
                {"text": "Hello", "start": 0, "duration": 1.5},
                {"text": "world", "start": 1.5, "duration": 1.0},
            ]

    monkeypatch.setitem(sys.modules, "youtube_transcript_api", SimpleNamespace(YouTubeTranscriptApi=FakeApi))
    segments = MODULE.fetch_transcript("dQw4w9WgXcQ", ["en", "es"])
    assert segments == [
        {"text": "Hello", "start": 0.0, "duration": 1.5},
        {"text": "world", "start": 1.5, "duration": 1.0},
    ]


def test_write_output_writes_plain_text(tmp_path: Path) -> None:
    payload = {
        "video_id": "dQw4w9WgXcQ",
        "languages": ["en"],
        "segment_count": 1,
        "segments": [{"text": "Hello world", "start": 0.0, "duration": 1.0}],
        "text": "Hello world",
    }
    output_path = tmp_path / "transcript.txt"
    MODULE.write_output(output_path, payload, as_json=False)
    assert output_path.read_text(encoding="utf-8") == "Hello world"
