from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SOURCE_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_persona_source_records.py"
SOURCE_SPEC = importlib.util.spec_from_file_location("build_persona_source_records", SOURCE_MODULE_PATH)
assert SOURCE_SPEC and SOURCE_SPEC.loader
SOURCE_MODULE = importlib.util.module_from_spec(SOURCE_SPEC)
sys.modules[SOURCE_SPEC.name] = SOURCE_MODULE
SOURCE_SPEC.loader.exec_module(SOURCE_MODULE)


def test_compile_persona_source_records_collects_jsonl_and_markdown_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    registry_path = tmp_path / "npc_registry.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "name": "Polly",
                    "role": "Living Codex and governance raven",
                    "canon_status": "STABLE",
                    "source_file": "training-data/lore_sessions/characters_and_world.jsonl",
                }
            ]
        ),
        encoding="utf-8",
    )

    jsonl_path = tmp_path / "characters_and_world.jsonl"
    jsonl_record = {
        "prompt": "Who is Polly and why is she important to the Spiralverse narrative?",
        "response": (
            "Polly is a sentient raven intelligence, co-equal guide, archivist, and meta-narrator. "
            "She represents the living governance system and preserves continuity across generations."
        ),
        "event_type": "lore_character",
        "metadata": {"character": "Polly", "role": "sentient raven archivist", "canon_status": "STABLE"},
    }
    pollyoneth_record = {
        "prompt": "What is Pollyoneth?",
        "response": "Pollyoneth is the sentient academy-realm and should not be conflated with Polly the raven archivist.",
        "event_type": "lore_character",
        "metadata": {"character": "Pollyoneth", "role": "sentient academy realm", "canon_status": "STABLE"},
    }
    jsonl_path.write_text(
        json.dumps(jsonl_record) + "\n" + json.dumps(pollyoneth_record) + "\n",
        encoding="utf-8",
    )

    markdown_root = tmp_path / "docs" / "specs"
    markdown_root.mkdir(parents=True)
    markdown_path = markdown_root / "polly_notes.md"
    markdown_path.write_text(
        "# Polly\n\n"
        "Polly is the Living Codex. She is watchful, archival, and governance-conscious.\n\n"
        "Her archive role should keep retrieval ahead of invention whenever continuity is at risk.\n",
        encoding="utf-8",
    )
    noisy_markdown_path = markdown_root / "ops_notes.md"
    noisy_markdown_path.write_text(
        "# Operations\n\n"
        "The Polly browser lane should stay read-only during smoke tests.\n",
        encoding="utf-8",
    )

    output_path = tmp_path / "persona_source_records.jsonl"
    compiled_dir = tmp_path / "compiled"

    manifest = SOURCE_MODULE.compile_persona_source_records(
        registry_path=registry_path,
        jsonl_sources=[jsonl_path],
        markdown_roots=[markdown_root],
        output_path=output_path,
        compile_output_dir=compiled_dir,
    )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert manifest["subject_count"] == 1
    assert len(rows) == 1

    row = rows[0]
    assert row["subject_id"] == "polly"
    assert row["display_name"] == "Polly"
    assert row["canon_role"] == "Living Codex and governance raven"
    assert row["source_type"] == "lore_character"
    assert row["tongue_weights"]["UM"] >= 0.35
    dominant_tongue = sorted(row["tongue_weights"].items(), key=lambda item: (-item[1], item[0]))[0][0]
    assert dominant_tongue == "UM"
    assert row["tongue_weights"]["UM"] > row["tongue_weights"]["AV"]
    assert len(row["evidence_spans"]) >= 2
    assert any(span["kind"] == "markdown_excerpt" for span in row["evidence_spans"])
    assert not any("Pollyoneth is the sentient academy-realm" in span["text"] for span in row["evidence_spans"])
    assert not any(span["source_ref"].endswith("ops_notes.md") for span in row["evidence_spans"])
    assert any(axis["axis"] == "canon_stability" for axis in row["body_axes"])
    assert any(axis["axis"] == "retrieval_before_invention" for axis in row["mind_axes"])
    assert len(row["state_vector_21d"]) == 21
    assert row["region_anchors"][0]["brain_block"] == "BLOCK_SPEC"
    assert row["summary"].startswith("Polly is a sentient raven intelligence")
    assert all("_explicit_tongues" not in span for span in row["evidence_spans"])
    assert all("_track" not in span for span in row["evidence_spans"])
    assert "compiled_outputs" in manifest
    compiled_profiles_path = Path(manifest["compiled_outputs"]["outputs"]["persona_profiles"])
    assert compiled_profiles_path.exists()
