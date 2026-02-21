from __future__ import annotations

import json

from scripts.normalize_perplexity import build_record
from scripts.normalize_perplexity import clean_text
from scripts.normalize_perplexity import normalize_messages
from scripts.normalize_perplexity import normalize_perplexity_dataset


def test_clean_text_compacts_whitespace() -> None:
    assert clean_text("  a   b \n\n\n c  ") == "a b\n\nc"


def test_normalize_messages_handles_text_or_content() -> None:
    msgs = [
        {"role": "Assistant", "text": "hello"},
        {"role": "assistant", "content": "hello"},
        {"role": "question", "content": "what now?"},
    ]
    out = normalize_messages(msgs, min_message_chars=2)
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == "hello"
    assert out[1]["role"] == "user"


def test_build_record_returns_none_for_missing_messages(tmp_path) -> None:
    payload = {"id": "x", "title": "T", "url": "https://a", "messages": []}
    assert build_record(payload, tmp_path / "x.json") is None


def test_normalize_perplexity_dataset_writes_jsonl(tmp_path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": "thread-1",
        "title": "Sample",
        "url": "https://www.perplexity.ai/search/sample",
        "messages": [
            {"role": "user", "content": "What is SCBE?"},
            {"role": "assistant", "content": "A governance architecture."},
        ],
    }
    (raw / "thread-1.json").write_text(json.dumps(payload), encoding="utf-8")

    out_jsonl = tmp_path / "normalized" / "threads.jsonl"
    out_stats = tmp_path / "normalized" / "stats.json"

    stats = normalize_perplexity_dataset(
        raw_dir=raw,
        output_jsonl=out_jsonl,
        output_stats=out_stats,
        min_message_chars=3,
        min_message_count=1,
        max_records=0,
    )

    lines = out_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    row0 = json.loads(lines[0])
    row1 = json.loads(lines[1])
    assert row0["thread_id"] == "thread-1"
    assert row0["turn_index"] == 0
    assert row1["turn_index"] == 1
    assert stats["records_written"] == 2
    assert stats["threads_written"] == 1
