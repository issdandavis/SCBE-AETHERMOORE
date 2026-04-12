from __future__ import annotations

from pathlib import Path

from src.knowledge.tokenizer_graph.overlay_graphs import build_overlay_graph
from scripts.system.memory_overlay_benchmark import (
    build_features,
    compute_idf,
    evaluate,
    load_corpus,
    load_eval_items,
    rank_paths,
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


def test_overlay_graph_extracts_intention_policy_and_code_language_relations() -> None:
    overlay = build_overlay_graph(
        "Verify policy bridges, then connect KO to Python token language mappings.",
        context_class="memory",
    )

    assert overlay.intention_nodes["govern"] >= 1
    assert overlay.intention_nodes["connect"] >= 1
    assert overlay.policy_nodes["verify"] >= 1
    assert overlay.policy_nodes["scope"] >= 1
    assert overlay.code_tongue_nodes["tongue:KO"] >= 1
    assert overlay.code_tongue_nodes["lane:python"] >= 1
    assert overlay.code_tongue_edges["lane:python->tongue:AV"] >= 1


def test_overlay_ranking_widens_margin_for_relation_aware_match(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    alpha = corpus_dir / "alpha.md"
    beta = corpus_dir / "beta.md"
    alpha.write_text(
        "Connect KO Python lane mappings connect KO Python lane mappings connect KO Python lane mappings.",
        encoding="utf-8",
    )
    beta.write_text(
        "Verify policy scope before connecting KO to Python lane mappings.",
        encoding="utf-8",
    )

    corpus = build_features(load_corpus([corpus_dir], chunk_chars=600, overlap_chars=0))
    idf = compute_idf(corpus)
    query = "Which note verifies policy scope before connecting KO to Python lane mappings?"

    baseline_hits = rank_paths(query, corpus, idf, top_k=2, mode="baseline")
    overlay_hits = rank_paths(query, corpus, idf, top_k=2, mode="overlay")

    assert Path(baseline_hits[0].path).name == "beta.md"
    assert Path(overlay_hits[0].path).name == "beta.md"

    baseline_gap = baseline_hits[0].score - baseline_hits[1].score
    overlay_gap = overlay_hits[0].score - overlay_hits[1].score

    assert overlay_gap > baseline_gap + 0.1
