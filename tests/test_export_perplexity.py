from __future__ import annotations

import json

from scripts.export_perplexity import likely_thread_url
from scripts.export_perplexity import save_thread
from scripts.export_perplexity import slugify


def test_slugify_normalizes_text() -> None:
    assert slugify("  Hello, Spiralverse!  ") == "hello-spiralverse"
    assert slugify("___") == "thread"


def test_likely_thread_url_filters_non_threads() -> None:
    host = "www.perplexity.ai"
    assert likely_thread_url("https://www.perplexity.ai/search/example-query", host)
    assert likely_thread_url("https://www.perplexity.ai/library/thread-abc", host)
    assert not likely_thread_url("https://www.perplexity.ai/library", host)
    assert not likely_thread_url("https://www.perplexity.ai/settings/account", host)
    assert not likely_thread_url("https://example.com/library/foo", host)


def test_save_thread_writes_expected_shape(tmp_path) -> None:
    out_path = save_thread(
        output_dir=tmp_path,
        thread_id="abc123",
        title="Test Thread",
        url="https://www.perplexity.ai/search/test-thread",
        messages=[{"role": "user", "content": "Q?"}, {"role": "assistant", "content": "A."}],
        label="label-x",
    )
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["id"] == "abc123"
    assert data["title"] == "Test Thread"
    assert data["url"] == "https://www.perplexity.ai/search/test-thread"
    assert data["label"] == "label-x"
    assert data["message_count"] == 2
    assert len(data["messages"]) == 2
    assert data["messages"][0]["content"] == "Q?"
