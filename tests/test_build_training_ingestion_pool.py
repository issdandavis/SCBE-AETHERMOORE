from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "build_training_ingestion_pool.py"
SPEC = importlib.util.spec_from_file_location("build_training_ingestion_pool", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_build_doc_sft_records_maps_source_paths() -> None:
    rows = [
        {
            "source_path": "docs/guides/CORE_SYSTEM_MAP.md",
            "chunk_index": 0,
            "source_text": "This is a bounded explanation of the core system map.",
        },
        {
            "source_path": "notebooks/scbe_finetune_colab.ipynb",
            "chunk_index": 2,
            "source_text": "Notebook cell description for training behavior.",
        },
    ]
    records = MODULE.build_doc_sft_records(rows)
    assert len(records) == 2
    assert records[0]["category"] == "architecture-reference"
    assert records[0]["metadata"]["track"] == "system"
    assert records[1]["category"] == "notebook-reference"
    assert records[1]["metadata"]["track"] == "functions"


def test_build_ingestion_pool_uses_existing_doc_chunks_when_refresh_skipped(
    tmp_path: Path,
) -> None:
    doc_output = tmp_path / "doc_chunks.jsonl"
    with doc_output.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "source_path": "notes/round-table/session.md",
                    "chunk_index": 1,
                    "source_text": "Round-table note content for agent training.",
                }
            )
            + "\n"
        )

    output_path = tmp_path / "sft_ingestion_pool.jsonl"
    run_root = tmp_path / "runs"
    summary = MODULE.build_ingestion_pool(
        output_path=output_path,
        doc_output_path=doc_output,
        run_root=run_root,
        skip_codebase_refresh=True,
        skip_doc_ingest=True,
        patterns=("notes/**/*.md",),
    )

    assert summary["codebase_refresh"]["status"] == "skipped"
    assert summary["doc_ingest"]["status"] == "skipped"
    assert summary["sft_ingestion_pool"]["record_count"] == 1
    rows = MODULE.read_jsonl(output_path)
    assert len(rows) == 1
    assert rows[0]["metadata"]["source_type"] == "doc_chunk"
