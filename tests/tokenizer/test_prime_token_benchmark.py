"""Controlled evaluation for the six-view catalog."""

from pathlib import Path

import pytest

from python.scbe.prime_token_benchmark import evaluate_catalog
from python.scbe.prime_token_catalog import InputRecord, PrimeTokenCatalogBuilder


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
            },
            {
                "id": "wall",
                "query_source_uri": "benchmark://fixture/wall",
                "query": "why turn beneath a bridge when the road is one way",
                "relevant_source_suffix": "wall.md",
            },
            {
                "id": "package",
                "query_source_uri": "benchmark://fixture/package",
                "query": "how are offline wheels built and hash checked",
                "relevant_source_suffix": "package.md",
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
    assert set(result["gates"]) == {"lexical_only", "no_intervention", "shuffled_binding"}
    assert result["underpowered_reasons"]


def test_benchmark_rejects_query_source_leakage(tmp_path):
    benchmark = _benchmark()
    benchmark["queries"][0]["query_source_uri"] = "local://catalog/prime.md"

    with pytest.raises(ValueError, match="query source entered"):
        evaluate_catalog(
            _fixture(tmp_path),
            benchmark,
            benchmark_sha256="b" * 64,
            control_seeds=(0, 1, 2),
            limit=5,
        )
