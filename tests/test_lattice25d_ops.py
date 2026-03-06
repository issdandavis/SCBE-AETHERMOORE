from __future__ import annotations

from hydra.lattice25d_ops import (
    NoteRecord,
    build_lattice25d_payload,
    metric_tags,
    sample_notes,
    text_metrics,
)


def test_text_metrics_and_tags_capture_expected_signals():
    text = "IMPORTANT: Visit https://example.com on 2026-03-05.\nSwarm lane update."
    metrics = text_metrics(text)
    tags = metric_tags(
        metrics,
        base_tags=["swarm", "update"],
        source="notion",
        authority="internal",
        tongue="DR",
    )

    assert metrics["has_url"] is True
    assert metrics["word_count"] > 0
    assert "contains:url" in tags
    assert "tag:swarm" in tags
    assert "source:notion" in tags


def test_build_lattice25d_payload_from_notes():
    notes = [
        NoteRecord(
            note_id="note-a",
            text="Research note with topology and hyperbolic projection details.",
            tags=("research",),
            source="repo",
            authority="internal",
            tongue="KO",
        ),
        NoteRecord(
            note_id="note-b",
            text="Governance note for council vote and risk thresholds.",
            tags=("governance",),
            source="repo",
            authority="sealed",
            tongue="DR",
        ),
    ]

    payload = build_lattice25d_payload(notes, query_top_k=2)
    assert payload["ingested_count"] == 2
    assert payload["stats"]["bundle_count"] == 2
    assert len(payload["nearest"]) == 2
    assert payload["dimensions"] == ["x", "y", "phase", "tongue", "authority", "intent"]


def test_sample_notes_builder_count():
    notes = sample_notes(7)
    assert len(notes) == 7
    assert notes[0].note_id.startswith("sample-")
