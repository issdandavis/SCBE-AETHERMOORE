from __future__ import annotations

from pathlib import Path

from scripts.system.memory_overlay_benchmark import (
    build_features,
    compute_idf,
    evaluate,
    load_corpus,
    load_eval_items,
)


def test_memory_overlay_benchmark_prefers_expected_paths(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "alpha.md").write_text(
        "MemPalace keeps verbatim memory and SCBE reranks with semantic tokens.",
        encoding="utf-8",
    )
    (corpus_dir / "beta.md").write_text(
        "Rhombic bridge scores and Fibonacci trust ladders live in a separate runtime lane.",
        encoding="utf-8",
    )

    eval_path = tmp_path / "evals.jsonl"
    eval_path.write_text(
        "\n".join(
            [
                f'{{"id":"e1","query":"Which note explains verbatim memory plus SCBE reranking?","expected_paths":["{(corpus_dir / "alpha.md").as_posix()}"],"type":"note"}}',
                f'{{"id":"e2","query":"Which note mentions rhombic bridge scores and Fibonacci trust ladders?","expected_paths":["{(corpus_dir / "beta.md").as_posix()}"],"type":"code"}}',
            ]
        ),
        encoding="utf-8",
    )

    corpus = build_features(load_corpus([corpus_dir], chunk_chars=600, overlap_chars=0))
    idf = compute_idf(corpus)
    eval_items = load_eval_items(eval_path)
    results = evaluate(eval_items, corpus, idf, top_k=2)

    assert results["metrics"]["baseline"]["recall_at_k"] == 1.0
    assert results["metrics"]["mempalace_style"]["recall_at_k"] == 1.0
    assert results["metrics"]["overlay"]["recall_at_k"] == 1.0
