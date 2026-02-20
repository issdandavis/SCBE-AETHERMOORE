from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.build_rag_index import build_rag_index
from scripts.build_rag_index import hashed_embedding
from scripts.build_rag_index import load_saved_index
from scripts.build_rag_index import query_rag_index


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_hashed_embedding_is_deterministic() -> None:
    a = hashed_embedding("Hyperbolic RAG signal", dimension=64, salt="test-salt")
    b = hashed_embedding("Hyperbolic RAG signal", dimension=64, salt="test-salt")
    c = hashed_embedding("Different payload", dimension=64, salt="test-salt")

    assert a.shape == (64,)
    assert np.allclose(a, b)
    assert not np.allclose(a, c)
    assert np.isclose(float(np.linalg.norm(a)), 1.0, atol=1e-5)


def test_build_rag_index_writes_artifacts(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "normalized.jsonl"
    out_dir = tmp_path / "rag_index"
    rows = [
        {"thread_id": "t1", "turn_index": 0, "text": "Hyperbolic retrieval context."},
        {"thread_id": "t1", "turn_index": 1, "text": "Poincare distance and trust score."},
        {"thread_id": "t2", "turn_index": 0, "text": "Gumroad uploader selenium session."},
    ]
    write_jsonl(input_jsonl, rows)

    summary = build_rag_index(
        input_jsonl=input_jsonl,
        output_dir=out_dir,
        text_fields=("text", "content"),
        id_fields=("thread_id", "id"),
        min_text_chars=5,
        max_records=0,
        backend="hash",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=96,
        batch_size=8,
        hash_salt="unit-test-salt",
    )

    assert summary["record_count"] == 3
    assert summary["embedding_backend"] == "hash"
    assert Path(summary["files"]["index"]).exists()
    assert Path(summary["files"]["documents"]).exists()
    assert Path(summary["files"]["manifest"]).exists()

    vectors, ids, manifest, docs = load_saved_index(index_dir=out_dir)
    assert vectors.shape == (3, 96)
    assert len(ids) == 3
    assert manifest["embedding_backend"] == "hash"
    assert "t1:0" in docs


def test_query_rag_index_returns_relevant_doc(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "normalized.jsonl"
    out_dir = tmp_path / "rag_index"
    rows = [
        {
            "thread_id": "hyper",
            "turn_index": 0,
            "text": "Hyperbolic Poincare retrieval with trust gating and rag scoring.",
        },
        {
            "thread_id": "shopify",
            "turn_index": 0,
            "text": "Shopify liquid section hero template and metafields.",
        },
        {
            "thread_id": "gumroad",
            "turn_index": 0,
            "text": "Gumroad image uploader with selenium and chrome profile.",
        },
    ]
    write_jsonl(input_jsonl, rows)

    build_rag_index(
        input_jsonl=input_jsonl,
        output_dir=out_dir,
        text_fields=("text",),
        id_fields=("thread_id",),
        min_text_chars=5,
        max_records=0,
        backend="hash",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=128,
        batch_size=8,
        hash_salt="query-test-salt",
    )

    results = query_rag_index(
        index_dir=out_dir,
        query="hyperbolic poincare rag trust scoring",
        top_k=2,
    )

    assert len(results) == 2
    assert results[0]["id"].startswith("hyper")
    assert results[0]["score"] >= results[1]["score"]

