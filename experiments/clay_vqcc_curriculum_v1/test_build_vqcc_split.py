from __future__ import annotations

import json
from pathlib import Path

import pytest

import build_vqcc_split as split


LIBRARY = "public/library"
PARTS = "public/parts"
NEGATIVE = "public/negative"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(split.canonical_bytes(row).decode() for row in rows), encoding="utf-8")


def refresh_manifest(root: Path, train_count: int) -> str:
    names = [
        "source-catalog.jsonl",
        "block-index.jsonl",
        "circuit-sequences.jsonl",
        "train-0000.jsonl",
    ]
    manifest = {
        "schema": "clay.vqcc-research-corpus.v1",
        "counts": {"train": train_count, "holdout": 48, "ordinary": 48, "retention": 48},
        "public_sources": {
            "library": [LIBRARY, 1, "manifest.csv", 1, "a" * 64],
            "parts": [PARTS, 1, "module.csv", 1, "b" * 64],
            "negative": [NEGATIVE, 1, "ledger.csv", 1, "c" * 64],
        },
        "files": {
            name: {"bytes": (root / name).stat().st_size, "sha256": split.sha256_file(root / name)}
            for name in names
        },
    }
    (root / "CORPUS_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return split.sha256_file(root / "CORPUS_MANIFEST.json")


def make_corpus(root: Path) -> str:
    circuits = [
        {"type": "public_circuit", "record": {"sha256": "a" * 64, "task": "invsqrt"}},
        {"type": "public_circuit", "record": {"sha256": "b" * 64, "task": "dqi"}},
    ]
    regions = [
        {
            "type": "public_region",
            "circuit_sha256": "a" * 64,
            "label": "left",
            "metrics": {"toffoli": 5, "conditional_toffoli": 2},
        },
        {
            "type": "public_region",
            "circuit_sha256": "b" * 64,
            "label": "right",
            "metrics": {},
        },
    ]
    factor = {
        "type": "public_factorization_array",
        "source": "chem-a",
        "array": "weights",
        "shape": [2, 3],
    }
    negatives = [
        {
            "type": "negative",
            "record": {
                "id": "negative-a",
                "task": "dqi",
                "mechanism": "a",
                "why_it_failed": "a-result",
                "link": "https://example.test/shared-link",
                "family_target": "target-a",
            },
        },
        {
            "type": "negative",
            "record": {
                "id": "negative-b",
                "task": "dqi",
                "mechanism": "b",
                "why_it_failed": "b-result",
                "link": "https://example.test/shared-link",
                "family_target": "target-b",
            },
        },
        {
            "type": "negative",
            "record": {
                "id": "negative-c",
                "task": "dqi",
                "mechanism": "c",
                "why_it_failed": "c-result",
                "link": "https://example.test/other-link",
                "family_target": "target-b",
            },
        },
        {
            "type": "negative",
            "record": {
                "id": "negative-d",
                "task": "invsqrt",
                "mechanism": "d",
                "why_it_failed": "d-result",
                "family_target": "target-d",
                "supersedes": "negative-e",
            },
        },
        {
            "type": "negative",
            "record": {
                "id": "negative-e",
                "task": "invsqrt",
                "mechanism": "e",
                "why_it_failed": "e-result",
                "family_target": "target-e",
            },
        },
    ]
    write_jsonl(root / "source-catalog.jsonl", circuits + regions + [factor, *negatives])
    write_jsonl(
        root / "block-index.jsonl",
        [
            {"block_id": 0, "sha256": "1" * 64},
            {"block_id": 1, "sha256": "2" * 64},
            {"block_id": 2, "sha256": "3" * 64},
        ],
    )
    write_jsonl(
        root / "circuit-sequences.jsonl",
        [
            {"task": "invsqrt", "published_entry": "entry-a", "blocks": [0, 1]},
            {"task": "dqi", "published_entry": "entry-b", "blocks": [1, 2]},
        ],
    )

    def pair(source: str, group: str, lane: str, ordinal, answer: str = "1") -> dict:
        return {
            "record_id": split.pair_record_id(source, lane, ordinal),
            "split": "train",
            "split_group": group,
            "lane": lane,
            "source": source,
            "question": "question",
            "answer": answer,
        }

    rows = [
        pair(LIBRARY, "public-vqcc-regions", "public.region_extent", ["a" * 64, 0]),
        pair(LIBRARY, "public-vqcc-regions", "public.region_cost", ["a" * 64, 0]),
        pair(LIBRARY, "public-vqcc-regions", "public.region_extent", ["b" * 64, 0]),
        pair("public-vqcc-opcode-windows", "windows", "public.gate_count", "1" * 64),
        pair("public-vqcc-opcode-windows", "windows", "public.gate_count", "2" * 64),
        pair("public-vqcc-opcode-windows", "windows", "public.gate_count", "3" * 64),
        pair(LIBRARY, "factor", "public.array_shape", ["chem-a", "weights"]),
        *[
            pair(NEGATIVE, "negative", "public.experimental_findings", f"negative-{suffix}")
            for suffix in ("a", "b", "c", "d", "e")
        ],
        {
            "record_id": "notebook-a-v4",
            "split": "train",
            "split_group": "public-kaggle-notebooks",
            "lane": "public.notebook_code",
            "source": "author/a",
            "version": "4",
            "text": "print(1)",
        },
        {
            "record_id": "notebook-a-v7",
            "split": "train",
            "split_group": "public-kaggle-notebooks",
            "lane": "public.notebook_code",
            "source": "author/a",
            "version": "7",
            "text": "print(1, 2)",
        },
        {
            "record_id": "notebook-b-v1",
            "split": "train",
            "split_group": "public-kaggle-notebooks",
            "lane": "public.notebook_code",
            "source": "author/b",
            "version": "1",
            "text": "print(2)",
        },
        {
            "record_id": "source-a",
            "split": "train",
            "split_group": "generator",
            "lane": "public.generator_source",
            "source": "portfolio",
            "source_sha256": "f" * 64,
            "path": "dqi/build.py",
            "text": "pass",
        },
        {
            "record_id": "dyadic",
            "split": "train",
            "split_group": "owned",
            "lane": "owned.dyadic",
            "source": "owned",
            "question": "x",
            "answer": "y",
        },
    ]
    write_jsonl(root / "train-0000.jsonl", rows)
    return refresh_manifest(root, len(rows))


def read_jsonl(path: Path) -> list[dict]:
    return list(split.iter_jsonl(path))


def test_build_is_deterministic_and_family_disjoint(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    digest = make_corpus(corpus)
    first = tmp_path / "first"
    second = tmp_path / "second"
    result = split.build_split(
        corpus,
        first,
        expected_manifest_sha256=digest,
        seed="fixed",
        holdout_fraction=0.5,
    )
    split.build_split(
        corpus,
        second,
        expected_manifest_sha256=digest,
        seed="fixed",
        holdout_fraction=0.5,
    )
    assert result["counts"]["eligible_rows"] == 16
    assert result["counts"]["train_rows"] + result["counts"]["holdout_rows"] == 16
    assert (first / "family-assignments.jsonl").read_bytes() == (
        second / "family-assignments.jsonl"
    ).read_bytes()
    assert (first / "row-assignments.jsonl").read_bytes() == (
        second / "row-assignments.jsonl"
    ).read_bytes()
    rows = read_jsonl(first / "row-assignments.jsonl")
    by_family: dict[str, set[str]] = {}
    for row in rows:
        by_family.setdefault(row["family"], set()).add(row["split"])
    assert all(len(roles) == 1 for roles in by_family.values())
    a_regions = [row for row in rows if row["family"] == f"circuit:sha256:{'a' * 64}"]
    assert len(a_regions) == 2
    assert len({row["split"] for row in a_regions}) == 1
    opcode_rows = [row for row in rows if row["lane"] == "public.gate_count"]
    assert len(opcode_rows) == 3
    assert len({row["family"] for row in opcode_rows}) == 1
    assert len({row["split"] for row in opcode_rows}) == 1
    assert {row["task"] for row in opcode_rows} == {"dqi+invsqrt"}
    notebook_versions = [row for row in rows if row["record_id"].startswith("notebook-a-")]
    assert len(notebook_versions) == 2
    assert len({row["family"] for row in notebook_versions}) == 1
    assert len({row["split"] for row in notebook_versions}) == 1
    negative_rows = {
        row["record_id"]: row
        for row in rows
        if row["lane"] == "public.experimental_findings"
    }
    linked = [
        negative_rows[split.pair_record_id(NEGATIVE, "public.experimental_findings", item)]
        for item in ("negative-a", "negative-b", "negative-c")
    ]
    card_linked = [
        negative_rows[split.pair_record_id(NEGATIVE, "public.experimental_findings", item)]
        for item in ("negative-d", "negative-e")
    ]
    assert len({row["family"] for row in linked}) == 1
    assert len({row["split"] for row in linked}) == 1
    assert len({row["family"] for row in card_linked}) == 1
    assert len({row["split"] for row in card_linked}) == 1
    assert linked[0]["family"] != card_linked[0]["family"]
    assert "dqi" in result["balance"]["train"]["task"] or "dqi" in result["balance"]["holdout"]["task"]
    assert all(row["record_id"] != "dyadic" for row in rows)


def test_manifest_hash_is_required(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    with pytest.raises(ValueError, match="manifest hash differs"):
        split.build_split(
            corpus,
            tmp_path / "out",
            expected_manifest_sha256="0" * 64,
            seed="fixed",
            holdout_fraction=0.2,
        )


def test_output_is_immutable(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    digest = make_corpus(corpus)
    output = tmp_path / "out"
    split.build_split(
        corpus,
        output,
        expected_manifest_sha256=digest,
        seed="fixed",
        holdout_fraction=0.5,
    )
    with pytest.raises(FileExistsError):
        split.build_split(
            corpus,
            output,
            expected_manifest_sha256=digest,
            seed="fixed",
            holdout_fraction=0.5,
        )


def test_unlisted_train_shard_is_rejected(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    digest = make_corpus(corpus)
    write_jsonl(
        corpus / "train-9999.jsonl",
        [
            {
                "record_id": "smuggled",
                "split": "train",
                "split_group": "public-kaggle-notebooks",
                "lane": "public.notebook_code",
                "source": "author/smuggled",
                "text": "not declared by the manifest",
            }
        ],
    )
    with pytest.raises(ValueError, match="Unlisted train shards"):
        split.build_split(
            corpus,
            tmp_path / "out",
            expected_manifest_sha256=digest,
            seed="fixed",
            holdout_fraction=0.5,
        )


def test_mutated_catalog_is_rejected_before_use(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    digest = make_corpus(corpus)
    with (corpus / "source-catalog.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="file (size|hash) differs for source-catalog.jsonl"):
        split.build_split(
            corpus,
            tmp_path / "out",
            expected_manifest_sha256=digest,
            seed="fixed",
            holdout_fraction=0.5,
        )


def test_partial_output_is_removed_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    digest = make_corpus(corpus)
    original = split.sha256_file

    def fail_on_output(path: Path) -> str:
        if path.name == "row-assignments.jsonl":
            raise RuntimeError("injected output failure")
        return original(path)

    monkeypatch.setattr(split, "sha256_file", fail_on_output)
    with pytest.raises(RuntimeError, match="injected output failure"):
        split.build_split(
            corpus,
            tmp_path / "out",
            expected_manifest_sha256=digest,
            seed="fixed",
            holdout_fraction=0.5,
        )
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".out.tmp-*"))


def test_ambiguous_broad_group_fails_closed(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_corpus(corpus)
    with (corpus / "train-0000.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(
            split.canonical_bytes(
                {
                    "record_id": "unresolved",
                    "split": "train",
                    "split_group": "public-vqcc-regions",
                    "lane": "public.region_extent",
                    "source": LIBRARY,
                    "question": "unknown region",
                    "answer": "1",
                }
            ).decode()
        )
    count = sum(1 for line in (corpus / "train-0000.jsonl").read_text(encoding="utf-8").splitlines() if line)
    digest = refresh_manifest(corpus, count)
    with pytest.raises(ValueError, match="Cannot establish fine source family"):
        split.build_split(
            corpus,
            tmp_path / "out",
            expected_manifest_sha256=digest,
            seed="fixed",
            holdout_fraction=0.5,
        )
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".out.tmp-*"))
