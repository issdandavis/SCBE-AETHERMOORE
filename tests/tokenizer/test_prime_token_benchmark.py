"""Controlled evaluation for the six-view catalog."""

from pathlib import Path
from hashlib import sha256

import pytest

import python.scbe.prime_token_benchmark as benchmark_module
import python.scbe.prime_token_catalog as catalog_module
from python.scbe.prime_token_benchmark import (
    audit_benchmark_disjointness,
    build_late_output_route_evidence,
    evaluate_catalog,
    evaluate_explicit_routed_catalog,
    evaluate_late_output_fused_catalog,
    evaluate_lexical_banded_catalog,
    evaluate_lexical_first_catalog,
)
from python.scbe.prime_token_catalog import (
    InputRecord,
    PrimeTokenCatalogBuilder,
    VIEW_NAMES,
    explicit_route,
    search_goal,
    search_explicit_routed,
    search_late_output_fused,
    search_lexical_banded,
    search_lexical_first,
)


def _fixture(tmp_path: Path) -> Path:
    output = tmp_path / "catalog"
    builder = PrimeTokenCatalogBuilder(output, section_chars=256, range_size=128)
    records = [
        (
            "local://catalog/prime.md",
            "The prime sieve marks multiples, preserves survivors, and records exact strike factors.",
        ),
        (
            "local://catalog/wall.md",
            "Because the highway route is one way, the car turns under the bridge to reach town.",
        ),
        (
            "local://catalog/package.md",
            "The package guide builds wheels, verifies hashes, and installs from an offline wheelhouse.",
        ),
    ]
    for uri, text in records:
        builder.ingest_record(InputRecord(text=text, source_uri=uri, source_kind="fixture", license_name="fixture"))
    builder.finalize()
    return output / "catalog.sqlite3"


def _benchmark() -> dict:
    return {
        "schema": "scbe.prime-token-benchmark.v1",
        "query_provenance": "curated_paraphrase",
        "queries": [
            {
                "id": "prime",
                "query_source_uri": "benchmark://fixture/prime",
                "query": "which sieve keeps survivors and strike factors",
                "relevant_source_suffix": "prime.md",
                "review": {"review_stratum": "prime_sieve"},
            },
            {
                "id": "wall",
                "query_source_uri": "benchmark://fixture/wall",
                "query": "why turn beneath a bridge when the road is one way",
                "relevant_source_suffix": "wall.md",
                "review": {"review_stratum": "five_w"},
            },
            {
                "id": "package",
                "query_source_uri": "benchmark://fixture/package",
                "query": "how are offline wheels built and hash checked",
                "relevant_source_suffix": "package.md",
                "review": {"review_stratum": "publication"},
            },
        ],
    }


def test_benchmark_runs_all_controls_and_stays_underpowered(tmp_path):
    result = evaluate_catalog(
        _fixture(tmp_path),
        _benchmark(),
        benchmark_sha256="b" * 64,
        control_seeds=(3, 5, 7),
        limit=5,
    )

    assert result["status"] == "UNDERPOWERED"
    assert set(result["arms"]) == {
        "full",
        "lexical_only",
        "no_intervention",
        "no_five_w",
        "no_prime",
        "no_source",
        "no_atomic",
        "no_speech",
        "no_topology",
        "shuffled_binding",
    }
    assert len(result["arms"]["shuffled_binding"]) == 3
    assert len(result["arms"]["full"]) == 1
    assert set(result["gates"]) == {
        "lexical_only",
        "no_intervention",
        "shuffled_binding",
    }
    assert result["underpowered_reasons"]


def test_paired_gate_requires_finite_sample_evidence_beyond_two_pooled_sd():
    underpowered = benchmark_module._paired_gate(
        [1.0, 1.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 0.0],
    )
    supported = benchmark_module._paired_gate(
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    )

    assert underpowered["passes_two_pooled_sd"] is True
    assert underpowered["exact_one_sided_p_value"] == pytest.approx(0.0625)
    assert underpowered["passes_finite_sample_uncertainty"] is False
    assert underpowered["passes_gate"] is False
    assert supported["exact_one_sided_p_value"] == pytest.approx(0.015625)
    assert supported["passes_finite_sample_uncertainty"] is True
    assert supported["passes_gate"] is True


def test_benchmark_rejects_query_source_leakage(tmp_path):
    benchmark = _benchmark()
    benchmark["queries"][0]["query_source_uri"] = "local://catalog/prime.md"

    with pytest.raises(ValueError, match="query text or source entered"):
        evaluate_catalog(
            _fixture(tmp_path),
            benchmark,
            benchmark_sha256="b" * 64,
            control_seeds=(0, 1, 2),
            limit=5,
        )


def test_benchmark_rejects_query_text_leakage_under_a_different_uri(tmp_path):
    benchmark = _benchmark()
    database = _fixture(tmp_path)
    benchmark["queries"][0][
        "query"
    ] = "The prime sieve marks multiples, preserves survivors, and records exact strike factors."

    audit = audit_benchmark_disjointness(
        database,
        benchmark,
        benchmark_sha256="b" * 64,
    )

    assert audit["status"] == "EXACT_LEAKAGE_DETECTED"
    assert audit["collision_count"] == 1
    assert audit["collisions"][0]["query_id"] == "prime"
    assert "source_content_sha256" in audit["collisions"][0]["reasons"]
    assert "source_token_sha256" in audit["collisions"][0]["reasons"]
    with pytest.raises(ValueError, match="query text or source entered"):
        evaluate_catalog(
            database,
            benchmark,
            benchmark_sha256="b" * 64,
            control_seeds=(0, 1, 2),
            limit=5,
        )


def test_disjoint_audit_passes_without_scoring_and_binds_query_hashes(tmp_path):
    benchmark = _benchmark()
    database = _fixture(tmp_path)
    audit = audit_benchmark_disjointness(
        database,
        benchmark,
        benchmark_sha256="c" * 64,
    )

    assert audit["status"] == "NO_EXACT_LEAKAGE_DETECTED"
    assert audit["collision_count"] == 0
    assert audit["query_count"] == 3
    benchmark["queries"][0]["query_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="query text hash mismatch"):
        audit_benchmark_disjointness(
            database,
            benchmark,
            benchmark_sha256="c" * 64,
        )


def test_prospective_benchmark_must_target_the_evaluated_catalog(tmp_path):
    benchmark = _benchmark()
    benchmark["prospective_boundary"] = {"catalog_sha256": "0" * 64}

    with pytest.raises(ValueError, match="targets a different catalog hash"):
        audit_benchmark_disjointness(
            _fixture(tmp_path),
            benchmark,
            benchmark_sha256="d" * 64,
        )


def test_prospective_benchmark_requires_every_query_after_freeze(tmp_path):
    database = _fixture(tmp_path)
    benchmark = _benchmark()
    benchmark["prospective_boundary"] = {
        "catalog_sha256": sha256(database.read_bytes()).hexdigest(),
        "catalog_generated_at_utc": "2026-11-07T09:36:44Z",
    }

    with pytest.raises(ValueError, match="missing a timestamp"):
        audit_benchmark_disjointness(
            database,
            benchmark,
            benchmark_sha256="e" * 64,
        )
    for query in benchmark["queries"]:
        query["authored_at_utc"] = "2026-11-07T09:36:45+00:00"
    audit = audit_benchmark_disjointness(
        database,
        benchmark,
        benchmark_sha256="e" * 64,
    )
    assert audit["status"] == "NO_EXACT_LEAKAGE_DETECTED"
    benchmark["queries"][0]["authored_at_utc"] = "2026-11-07T09:36:44Z"
    with pytest.raises(ValueError, match="not strictly after"):
        audit_benchmark_disjointness(
            database,
            benchmark,
            benchmark_sha256="e" * 64,
        )


def test_lexical_first_is_lexical_primary_and_runs_controls(tmp_path):
    database = _fixture(tmp_path)
    lexical = search_goal(
        database,
        "prime sieve survivors",
        limit=5,
        ablate_views=("five_w", "speech", "atomic", "prime", "source"),
    )
    cascade = search_lexical_first(database, "prime sieve survivors", limit=5)
    assert cascade["results"][0]["section_id"] == lexical["results"][0]["section_id"]
    keys = [
        (
            row["cascade_scores"]["lexical_primary"],
            row["cascade_scores"]["auxiliary_tiebreak"],
        )
        for row in cascade["results"]
    ]
    assert keys == sorted(keys, reverse=True)

    result = evaluate_lexical_first_catalog(
        database,
        _benchmark(),
        benchmark_sha256="c" * 64,
        control_seeds=(3, 5, 7),
        limit=5,
    )
    assert result["status"] == "UNDERPOWERED"
    assert result["candidate_arm"] == "lexical_first"
    assert set(result["arms"]) == {
        "lexical_first",
        "full",
        "lexical_only",
        "no_intervention",
        "shuffled_binding",
    }
    assert len(result["arms"]["shuffled_binding"]) == 3
    assert set(result["gates"]) == {
        "lexical_only",
        "no_intervention",
        "shuffled_binding",
    }


def test_lexical_band_zero_reproduces_ties_and_full_width_reproduces_auxiliary(
    tmp_path,
):
    database = _fixture(tmp_path)
    goal = "prime sieve survivors"
    lexical_first = search_lexical_first(database, goal, limit=5)
    zero_band = search_lexical_banded(database, goal, lexical_band_width=0.0, limit=5)
    full_band = search_lexical_banded(database, goal, lexical_band_width=1.0, limit=5)
    auxiliary = search_goal(database, goal, limit=5)

    assert [row["section_id"] for row in zero_band["results"]] == [
        row["section_id"] for row in lexical_first["results"]
    ]
    assert [row["section_id"] for row in full_band["results"]] == [row["section_id"] for row in auxiliary["results"]]
    assert all(row["probability"] is None for row in zero_band["results"])

    result = evaluate_lexical_banded_catalog(
        database,
        _benchmark(),
        benchmark_sha256="d" * 64,
        lexical_band_width=0.01,
        control_seeds=(3, 5, 7),
        limit=5,
    )
    assert result["status"] == "UNDERPOWERED"
    assert result["candidate_arm"] == "lexical_banded"
    assert result["lexical_band_width"] == 0.01
    assert set(result["arms"]) == {
        "lexical_banded",
        "full",
        "lexical_only",
        "no_intervention",
        "shuffled_binding",
    }
    assert sum(result["query_changes_vs_lexical"].values()) == 3


def test_explicit_route_is_bounded_deterministic_and_has_null_control():
    route = explicit_route("Why does this prime sieve code preserve a composite factor?")
    assert route["selected_views"] == ["prime", "five_w"]
    assert route["source_kinds"] == ["code"]
    assert route["marker_hits"]["prime"] == ["prime", "sieve", "factor", "composite"]

    null_route = explicit_route(
        "Why does this prime sieve code preserve a composite factor?",
        null_control=True,
    )
    assert null_route["matched_views"] == route["matched_views"]
    assert null_route["selected_views"] == ["source", "speech"]
    assert route["route_width"] == 2
    assert null_route["route_width"] == route["route_width"]
    assert null_route["matched_route_width"] == route["matched_route_width"]
    assert null_route["width_matched"] is True
    assert null_route["source_kinds"] == ["code"]


def test_explicit_routed_search_keeps_lexical_score_and_limits_views(tmp_path):
    database = _fixture(tmp_path)
    routed = search_explicit_routed(
        database,
        "prime sieve survivors",
        lexical_band_width=0.005,
        limit=5,
    )
    assert routed["algorithm_revision"] == "six-view-explicit-route-v1"
    assert routed["explicit_route"]["selected_views"] == ["prime"]
    assert routed["auxiliary_views"] == ["prime"]
    assert routed["ranking_rule"][0] == "lexical_score_band_descending"
    assert all(row["probability"] is None for row in routed["results"])

    lexical_fallback = search_explicit_routed(
        database,
        "survivors remain exact",
        lexical_band_width=0.005,
        limit=5,
    )
    assert lexical_fallback["explicit_route"]["selected_views"] == []
    assert lexical_fallback["auxiliary_views"] == []


def test_explicit_route_evaluator_runs_null_shuffled_and_macro_controls(tmp_path):
    result = evaluate_explicit_routed_catalog(
        _fixture(tmp_path),
        _benchmark(),
        benchmark_sha256="e" * 64,
        control_seeds=(3, 5, 7),
        limit=5,
    )

    assert result["status"] == "UNDERPOWERED"
    assert result["candidate_arm"] == "explicit_routed"
    assert result["algorithm_revision"] == "six-view-explicit-route-v1"
    assert set(result["arms"]) == {
        "explicit_routed",
        "route_null",
        "full",
        "lexical_banded",
        "lexical_only",
        "no_intervention",
        "shuffled_binding",
    }
    assert len(result["arms"]["shuffled_binding"]) == 3
    assert set(result["gates"]) == {
        "lexical_only",
        "no_intervention",
        "route_null",
        "shuffled_binding_seed_3",
        "shuffled_binding_seed_5",
        "shuffled_binding_seed_7",
    }
    assert result["arms"]["explicit_routed"][0]["macro_source_metrics"]["sources"] == 3
    assert result["route_control_contract"]["equal_parameter_count"] is True
    assert result["route_control_contract"]["all_route_widths_match"] is True
    assert result["route_control_contract"]["passes"] is True
    assert result["diversity"]["topic_strata_count"] == 3
    assert result["diversity"]["relevant_source_count"] == 3
    assert "fewer than six distinct relevant catalog sources" in result["underpowered_reasons"]
    assert sum(result["route_usage"].values()) == 3


def test_late_output_fusion_keeps_no_marker_queries_exactly_lexical(tmp_path):
    database = _fixture(tmp_path)
    query = "survivors remain exact"
    lexical = search_goal(
        database,
        query,
        limit=5,
        ablate_views=[view for view in VIEW_NAMES if view != "lexical"],
    )
    fused = search_late_output_fused(database, query, limit=5)

    assert fused["algorithm_revision"] == "six-view-late-output-fusion-v1"
    assert fused["route_action"] == "CORE_PASS"
    assert fused["fusion_active"] is False
    assert fused["auxiliary_views"] == []
    assert fused["child_search_ids"]["auxiliary"] is None
    assert [row["section_id"] for row in fused["results"]] == [row["section_id"] for row in lexical["results"]]
    assert [row["score"] for row in fused["results"]] == [row["score"] for row in lexical["results"]]


def test_late_output_fusion_is_deterministic_rank_only_and_controlled(tmp_path):
    database = _fixture(tmp_path)
    query = "Why does this prime sieve code preserve a composite factor?"
    first = search_late_output_fused(database, query, limit=5)
    second = search_late_output_fused(database, query, limit=5)
    null = search_late_output_fused(database, query, limit=5, null_control=True)
    shuffled = search_late_output_fused(
        database,
        query,
        limit=5,
        control="shuffled",
        control_seed=17,
    )

    assert first == second
    assert first["route_action"] == "SPECIALIST"
    assert first["fusion_active"] is True
    assert first["rrf_k"] == 60.0
    assert first["auxiliary_views"] == ["prime", "five_w"]
    assert null["auxiliary_views"] == ["source", "speech"]
    assert shuffled["control"] == "shuffled"
    assert shuffled["search_id"] != first["search_id"]
    assert len(shuffled["results"]) == len(first["results"])
    for row in first["results"]:
        fusion = row["late_output_fusion"]
        assert row["probability"] is None
        assert fusion["rrf_k"] == 60.0
        assert fusion["active"] is True
        assert fusion["fusion_score"] == pytest.approx(
            fusion["lexical_contribution"] + fusion["auxiliary_contribution"]
        )
        assert row["score"] == pytest.approx(fusion["fusion_score"])


def test_late_output_fusion_evaluator_runs_declared_controls(tmp_path):
    result = evaluate_late_output_fused_catalog(
        _fixture(tmp_path),
        _benchmark(),
        benchmark_sha256="f" * 64,
        control_seeds=(3, 5, 7),
        limit=5,
    )

    assert result["status"] == "UNDERPOWERED"
    assert result["candidate_arm"] == "late_output_fused"
    assert result["algorithm_revision"] == "six-view-late-output-fusion-v1"
    assert set(result["arms"]) == {
        "late_output_fused",
        "route_null",
        "explicit_routed",
        "lexical_only",
        "no_intervention",
        "shuffled_binding",
        "random_rank_fusion",
    }
    assert len(result["arms"]["shuffled_binding"]) == 3
    assert result["route_control_contract"]["equal_parameter_count"] is True
    assert result["route_control_contract"]["all_route_widths_match"] is True
    assert result["route_control_contract"]["passes"] is True
    assert len(result["arms"]["random_rank_fusion"]) == 3
    assert set(result["gates"]) == {
        "lexical_only",
        "no_intervention",
        "route_null",
        "shuffled_binding_seed_3",
        "shuffled_binding_seed_5",
        "shuffled_binding_seed_7",
        "random_rank_fusion_seed_3",
        "random_rank_fusion_seed_5",
        "random_rank_fusion_seed_7",
    }
    random_search_ids = {
        outcome["search_id"] for run in result["arms"]["random_rank_fusion"] for outcome in run["outcomes"]
    }
    assert len(random_search_ids) == 9
    assert sum(result["route_usage"].values()) == 3

    with pytest.raises(ValueError, match="at least three distinct control seeds"):
        evaluate_late_output_fused_catalog(
            _fixture(tmp_path / "too-few"),
            _benchmark(),
            benchmark_sha256="f" * 64,
            control_seeds=(3, 5),
            limit=5,
        )


def test_late_output_fusion_evaluator_hashes_catalog_only_at_boundaries(
    tmp_path,
    monkeypatch,
):
    database = _fixture(tmp_path)
    original_sha256_file = catalog_module.sha256_file
    hashed_paths = []

    def counted_sha256_file(path):
        hashed_paths.append(Path(path).resolve())
        return original_sha256_file(path)

    monkeypatch.setattr(catalog_module, "sha256_file", counted_sha256_file)
    monkeypatch.setattr(benchmark_module, "sha256_file", counted_sha256_file)

    result = evaluate_late_output_fused_catalog(
        database,
        _benchmark(),
        benchmark_sha256="f" * 64,
        control_seeds=(3, 5, 7),
        limit=5,
    )

    assert result["catalog_sha256"] == original_sha256_file(database)
    assert hashed_paths == [database.resolve(), database.resolve()]


def test_route_evidence_keeps_raw_values_beside_trits(tmp_path):
    database = _fixture(tmp_path)
    benchmark = _benchmark()
    benchmark["queries"][2]["query"] = "offline wheels install cleanly after hash checks"
    evidence = build_late_output_route_evidence(
        database,
        benchmark,
        benchmark_sha256="e" * 64,
        control_seeds=(3, 5, 7),
        limit=5,
    )

    assert evidence["schema"] == "scbe.prime-token-route-evidence.v1"
    assert evidence["status"] == "EVIDENCE_ONLY_NO_PROMOTION"
    assert evidence["promotion"] == "NONE"
    assert evidence["disjointness_audit"]["status"] == "NO_EXACT_LEAKAGE_DETECTED"
    assert evidence["query_count"] == 3
    assert sum(evidence["route_usage"].values()) == 3
    assert sum(evidence["winner_counts"].values()) == sum(len(query["rows"]) for query in evidence["queries"])
    assert evidence["no_marker_identity"]["queries"] >= 1
    assert evidence["no_marker_identity"]["passes"] is True
    for query in evidence["queries"]:
        assert "query" not in query
        if not query["selected_views"]:
            assert all(
                control["aligned_advantage_rank_delta"] == 0
                for row in query["rows"]
                for control in row["aligned_vs_random_rank_fusion"]
            )
        for row in query["rows"]:
            assert row["primary_trit"] in {-1, 0, 1}
            assert row["mirror_trit"] in {-1, 0, 1}
            assert row["fusion_score"] == pytest.approx(row["lexical_contribution"] + row["auxiliary_contribution"])
            assert len(row["aligned_vs_shuffled"]) == 3
            assert len(row["aligned_vs_random_rank_fusion"]) == 3
            assert row["primary_signed_value"] == pytest.approx(
                row["auxiliary_contribution"] - row["lexical_contribution"]
            )
        assert len(query["random_rank_fusion_search_ids"]) == 3
        assert len(query["relevant_source_ranks"]["random_rank_fusion"]) == 3


def test_route_evidence_rejects_exact_catalog_leakage(tmp_path):
    database = _fixture(tmp_path)
    benchmark = _benchmark()
    benchmark["queries"][0][
        "query"
    ] = "The prime sieve marks multiples, preserves survivors, and records exact strike factors."

    with pytest.raises(ValueError, match="exact-source-disjoint benchmark"):
        build_late_output_route_evidence(
            database,
            benchmark,
            benchmark_sha256="e" * 64,
            control_seeds=(3, 5, 7),
            limit=5,
        )
