from __future__ import annotations

import json

from scripts.merge_chat_sft_corpus import (
    DEFAULT_SYSTEM_PROMPT,
    merge_chat_corpus,
    write_sharded_jsonl,
)


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_merge_chat_corpus_converts_instruction_rows(tmp_path):
    root = tmp_path / "root.jsonl"
    lore = tmp_path / "lore.jsonl"
    _write_jsonl(root, [])
    _write_jsonl(
        lore,
        [
            {
                "instruction": "Explain Avalon",
                "response": "Avalon is a realm.",
                "metadata": {"project_name": "Avalon story"},
            }
        ],
    )

    merged, stats = merge_chat_corpus([root, lore])

    assert stats["rows_read"] == 1
    assert stats["rows_written"] == 1
    assert merged[0]["messages"][0]["content"] == DEFAULT_SYSTEM_PROMPT
    assert merged[0]["messages"][1]["content"] == "Explain Avalon"
    assert merged[0]["messages"][2]["content"] == "Avalon is a realm."


def test_merge_chat_corpus_preserves_chat_rows(tmp_path):
    chat = tmp_path / "chat.jsonl"
    _write_jsonl(
        chat,
        [
            {
                "messages": [
                    {"role": "system", "content": "Custom system"},
                    {"role": "user", "content": "Question"},
                    {"role": "assistant", "content": "Answer"},
                ],
                "metadata": {"topic": "test"},
            }
        ],
    )

    merged, _stats = merge_chat_corpus([chat])

    assert merged[0]["messages"][0]["content"] == "Custom system"
    assert merged[0]["messages"][1]["content"] == "Question"
    assert merged[0]["messages"][2]["content"] == "Answer"
    assert merged[0]["metadata"] == {"topic": "test"}


def test_merge_chat_corpus_deduplicates_by_user_and_assistant(tmp_path):
    one = tmp_path / "one.jsonl"
    two = tmp_path / "two.jsonl"
    shared = {
        "messages": [
            {"role": "system", "content": "A"},
            {"role": "user", "content": "Same prompt"},
            {"role": "assistant", "content": "Same answer"},
        ]
    }
    _write_jsonl(one, [shared])
    _write_jsonl(
        two,
        [
            {
                "instruction": "Same prompt",
                "response": "Same answer",
            }
        ],
    )

    merged, stats = merge_chat_corpus([one, two])

    assert len(merged) == 1
    assert stats["duplicates_removed"] == 1


def test_write_sharded_jsonl_splits_output(tmp_path, monkeypatch):
    repo_root = tmp_path
    monkeypatch.setattr("scripts.merge_chat_sft_corpus.REPO_ROOT", repo_root)
    base = repo_root / "training-data" / "sft" / "merged.jsonl"
    rows = [
        {"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"u{i}"}, {"role": "assistant", "content": f"a{i}"}]}
        for i in range(5)
    ]

    shards = write_sharded_jsonl(base, rows, shard_lines=2)

    assert shards == [
        "training-data/sft/merged/part-0001.jsonl",
        "training-data/sft/merged/part-0002.jsonl",
        "training-data/sft/merged/part-0003.jsonl",
    ]
