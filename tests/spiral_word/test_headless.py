"""Headless Word generation: render + AI-driven record pipeline."""

from __future__ import annotations

import io
import zipfile

import pytest

pytest.importorskip("docx", reason="python-docx not installed")

from headless import (  # noqa: E402
    DOCX_MIME,
    HeadlessRecord,
    _split_paragraphs,
    generate_record,
    render_docx,
)
from sync_engine import SyncEngine  # noqa: E402


@pytest.fixture
def sync():
    return SyncEngine()


def _is_docx(data: bytes) -> bool:
    """A real .docx is a zip archive containing word/document.xml."""
    if not data.startswith(b"PK"):
        return False
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
    return "word/document.xml" in names


def test_split_paragraphs_blank_line_boundaries():
    text = "alpha line\nstill alpha\n\nbeta\n\n\ngamma"
    out = _split_paragraphs(text)
    assert out == ["alpha line\nstill alpha", "beta", "gamma"]


def test_split_paragraphs_empty():
    assert _split_paragraphs("") == []
    assert _split_paragraphs("\n\n\n") == []


def test_render_docx_returns_valid_docx_bytes(sync):
    doc = sync.get_or_create("doc-1")
    doc.insert(0, "Hello world.\n\nSecond paragraph here.")
    data = render_docx(doc)
    assert _is_docx(data)
    assert len(data) > 0


def test_render_docx_with_title_and_author(sync):
    doc = sync.get_or_create("doc-2")
    doc.insert(0, "Body content.")
    data = render_docx(doc, title="Quarterly Report", author="Issac Davis")
    assert _is_docx(data)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        body = zf.read("word/document.xml").decode("utf-8")
        core = zf.read("docProps/core.xml").decode("utf-8")
    assert "Quarterly Report" in body
    assert "Issac Davis" in core


def test_render_docx_promotes_markdown_headings(sync):
    doc = sync.get_or_create("doc-3")
    doc.insert(
        0,
        "# Top Heading\n\n## Sub Heading\nfollow-up line\n\nNormal paragraph.",
    )
    data = render_docx(doc)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        body = zf.read("word/document.xml").decode("utf-8")
    assert "Top Heading" in body
    assert "Sub Heading" in body
    # Heading runs must use a Heading style (not the default body style).
    assert "Heading" in body


def test_render_docx_includes_audit_footer_when_enabled(sync):
    doc = sync.get_or_create("audit-doc")
    doc.insert(0, "Body.")
    data = render_docx(doc, include_audit_footer=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        body = zf.read("word/document.xml").decode("utf-8")
    assert "audit-doc" in body
    assert "version=" in body


def test_generate_record_with_echo_provider(sync):
    data, record, ai_text = generate_record(
        sync=sync,
        doc_id="record-doc",
        prompt="Write a memo about cache invalidation.",
        provider="echo",
        site_id="ai-1",
    )
    assert isinstance(record, HeadlessRecord)
    assert record.doc_id == "record-doc"
    assert record.site_id == "ai-1"
    assert record.provider == "echo"
    assert record.docx_bytes == len(data)
    assert _is_docx(data)
    assert "[echo]" in ai_text
    assert len(record.record_id) == 32
    assert len(record.docx_sha256) == 64


def test_generate_record_replace_vs_append(sync):
    sync.get_or_create("dual").insert(0, "Pre-existing content.")
    _, _, _ = generate_record(
        sync=sync,
        doc_id="dual",
        prompt="Append-only run.",
        provider="echo",
        replace=False,
    )
    text_after_append = sync.get_or_create("dual").text
    assert "Pre-existing content." in text_after_append
    assert "[echo]" in text_after_append

    _, _, _ = generate_record(
        sync=sync,
        doc_id="dual",
        prompt="Replace-mode run.",
        provider="echo",
        replace=True,
    )
    text_after_replace = sync.get_or_create("dual").text
    assert "Pre-existing content." not in text_after_replace
    assert "Replace-mode run" in text_after_replace


def test_generate_record_blocked_provider_raises(sync, monkeypatch):
    from ai_ports import ai_ports

    def blocked(prompt, options=None):  # noqa: ARG001
        return "[BLOCKED] policy violation"

    monkeypatch.setitem(ai_ports._providers, "echo", blocked)
    with pytest.raises(ValueError, match="policy violation"):
        generate_record(
            sync=sync,
            doc_id="blocked-doc",
            prompt="anything",
            provider="echo",
        )


def test_generate_record_provider_error_raises(sync, monkeypatch):
    from ai_ports import ai_ports

    def errored(prompt, options=None):  # noqa: ARG001
        return "[ERROR] upstream timeout"

    monkeypatch.setitem(ai_ports._providers, "echo", errored)
    with pytest.raises(RuntimeError, match="upstream timeout"):
        generate_record(
            sync=sync,
            doc_id="err-doc",
            prompt="anything",
            provider="echo",
        )


def test_generate_record_writes_audit_entry(sync):
    from governance import audit_log

    before = len(audit_log.entries)
    _, record, _ = generate_record(
        sync=sync,
        doc_id="audited",
        prompt="Audit this run.",
        provider="echo",
    )
    after = len(audit_log.entries)
    assert after == before + 1
    last = audit_log.entries[-1]
    assert last.action == "headless_generate"
    assert record.record_id in last.governance_decision


def test_docx_mime_constant_is_correct():
    assert DOCX_MIME == ("application/vnd.openxmlformats-officedocument." "wordprocessingml.document")
