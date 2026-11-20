from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import build_vqcc_split as split
import findings_task
from load_vqcc_corpus import SampleConfig, sample_corpus
from vqcc_task import (
    build_balanced_comparisons,
    parse_gate_count_row,
    task_set_report,
    validate_family_disjoint,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_bytes(b"".join(split.canonical_bytes(row) for row in rows))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _opcode_window(count: int, salt: int) -> tuple[int, ...]:
    if not 0 <= count <= 2:
        raise ValueError(count)
    result = [0x30 + index for index in range(count)]
    result.extend(((salt * 17 + index) % 0x2F) for index in range(32 - count))
    return tuple(result)


def _make_corpus(root: Path) -> tuple[str, dict[str, int]]:
    root.mkdir()
    catalog: list[dict[str, object]] = []
    block_index: list[dict[str, object]] = []
    sequences: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    block_id = 0

    # Six source families, each with the same count histogram.  A 50/50 family
    # split therefore leaves both roles able to build exact A/B/T task balance.
    for family_index in range(6):
        circuit_sha = f"{family_index + 1:064x}"
        catalog.append(
            {"type": "public_circuit", "record": {"sha256": circuit_sha, "task": "invsqrt"}}
        )
        family_blocks: list[int] = []
        for local_index, count in enumerate((0, 0, 1, 1, 2, 2)):
            block_sha = hashlib.sha256(
                f"integration-block:{family_index}:{local_index}".encode()
            ).hexdigest()
            opcodes = _opcode_window(count, family_index * 10 + local_index)
            measured = sum(opcode in {0x30, 0x31, 0x32, 0xB0, 0xB1, 0xB2} for opcode in opcodes)
            assert measured == count
            block_index.append({"block_id": block_id, "sha256": block_sha})
            family_blocks.append(block_id)
            record_id = split.pair_record_id(
                "public-vqcc-opcode-windows", "public.gate_count", block_sha
            )
            rows.append(
                {
                    "record_id": record_id,
                    "split": "train",
                    "split_group": "public-vqcc-opcode-windows",
                    "lane": "public.gate_count",
                    "source": "public-vqcc-opcode-windows",
                    "question": (
                        "How many Toffoli-class gates occur in this Kickmix opcode sequence? "
                        "Count 30, 31, 32, b0, b1 and b2 (hexadecimal).\n"
                        + " ".join(f"{opcode:02x}" for opcode in opcodes)
                    ),
                    "answer": str(count),
                }
            )
            block_id += 1
        sequences.append(
            {
                "task": "invsqrt",
                "published_entry": f"integration-entry-{family_index}",
                "blocks": family_blocks,
            }
        )

    for task in ("invsqrt", "dqi", "chemistry", "all"):
        for finding_index in range(4):
            item_id = f"integration-{task}-finding-{finding_index:02d}"
            mechanism = f"mechanism {finding_index:02d}"
            answer = f"Measured limitation {task} {finding_index:02d}."
            catalog.append(
                {
                    "type": "negative",
                    "record": {
                        "id": item_id,
                        "task": task,
                        "mechanism": mechanism,
                        "family_target": f"integration target {task} {finding_index:02d}",
                        "why_it_failed": answer,
                    },
                }
            )
            rows.append(
                {
                    "record_id": split.pair_record_id(
                        "public/negative", "public.experimental_findings", item_id
                    ),
                    "split": "train",
                    "split_group": "public-negative-findings",
                    "lane": "public.experimental_findings",
                    "source": "public/negative",
                    "question": (
                        f"What limitation did the public {task} experiment report for {mechanism}? "
                        "Evidence tier: measured."
                    ),
                    "answer": answer,
                }
            )

    _write_jsonl(root / "source-catalog.jsonl", catalog)
    _write_jsonl(root / "block-index.jsonl", block_index)
    _write_jsonl(root / "circuit-sequences.jsonl", sequences)
    _write_jsonl(root / "train-0000.jsonl", rows)

    counts = {"train": len(rows), "holdout": 0, "ordinary": 0, "retention": 0}
    names = (
        "source-catalog.jsonl",
        "block-index.jsonl",
        "circuit-sequences.jsonl",
        "train-0000.jsonl",
    )
    manifest = {
        "schema": "clay.vqcc-research-corpus.v1",
        "counts": counts,
        "lanes": {
            "public.experimental_findings": 16,
            "public.gate_count": 36,
        },
        "files": {
            name: {"bytes": (root / name).stat().st_size, "sha256": _sha256(root / name)}
            for name in names
        },
        "public_sources": {
            "library": ["public/library", 1, "manifest.csv", 1, "a" * 64],
            "parts": ["public/parts", 1, "module.csv", 1, "b" * 64],
            "negative": ["public/negative", 1, "ledger.csv", 1, "c" * 64],
        },
        "submission_archive_members": 0,
        "official_competition_mounts": 0,
        "model_checkpoints": 0,
    }
    manifest_path = root / "CORPUS_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return _sha256(manifest_path), counts


def _sample_role(
    root: Path,
    assignments: Path,
    *,
    manifest_sha256: str,
    counts: dict[str, int],
    role: str,
):
    return sample_corpus(
        root,
        SampleConfig(
            lane_caps={"public.experimental_findings": 100, "public.gate_count": 100},
            seed=739,
            max_chars_per_record=1_000,
            max_tokens_per_record=1_000,
            total_token_budget=100_000,
            campaign_role=role,
        ),
        assignments_path=assignments,
        expected_assignments_sha256=_sha256(assignments),
        expected_manifest_sha256=manifest_sha256,
        expected_counts=counts,
    )


def test_manifest_to_family_disjoint_balanced_tasks(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    manifest_sha256, counts = _make_corpus(corpus)
    split_dir = tmp_path / "campaign-split"
    split_receipt = split.build_split(
        corpus,
        split_dir,
        expected_manifest_sha256=manifest_sha256,
        seed="integration-split-v1",
        holdout_fraction=0.5,
    )

    assert split_receipt["counts"] == {
        "eligible_rows": 52,
        "families": 22,
        "train_families": 11,
        "holdout_families": 11,
        "train_rows": 26,
        "holdout_rows": 26,
    }
    assignments_path = split_dir / "row-assignments.jsonl"
    assignments = {
        row["record_id"]: row
        for row in (
            json.loads(line)
            for line in assignments_path.read_text(encoding="utf-8").splitlines()
        )
    }

    train_sample = _sample_role(
        corpus,
        assignments_path,
        manifest_sha256=manifest_sha256,
        counts=counts,
        role="train",
    )
    holdout_sample = _sample_role(
        corpus,
        assignments_path,
        manifest_sha256=manifest_sha256,
        counts=counts,
        role="holdout",
    )
    assert len(train_sample.rows) == len(holdout_sample.rows) == 26
    assert set(train_sample.receipt["campaign_assignments"]["roles"]) == {"holdout", "train"}
    assert set(holdout_sample.receipt["campaign_assignments"]["roles"]) == {"holdout", "train"}

    def parse_gate_counts(rows: tuple[dict[str, object], ...]):
        return [
            parse_gate_count_row(row, family_id=assignments[str(row["record_id"])]["family"])
            for row in rows
            if row["lane"] == "public.gate_count"
        ]

    train_examples = parse_gate_counts(train_sample.rows)
    holdout_examples = parse_gate_counts(holdout_sample.rows)
    assert Counter(example.count for example in train_examples) == {0: 6, 1: 6, 2: 6}
    assert Counter(example.count for example in holdout_examples) == {0: 6, 1: 6, 2: 6}

    train_tasks = build_balanced_comparisons(train_examples, seed=11, gap_strata=(1,))
    holdout_tasks = build_balanced_comparisons(holdout_examples, seed=29, gap_strata=(1,))
    validate_family_disjoint(train_tasks, holdout_tasks)

    for task_rows in (train_tasks, holdout_tasks):
        report = task_set_report(task_rows)
        assert report["label_counts"] == {"A": 2, "B": 2, "T": 2}
        assert report["maximum_record_reuse"] == 1
        assert report["gap_distribution_by_label"]["A"] == {1: 2}
        assert report["gap_distribution_by_label"]["B"] == {1: 2}

    def parse_findings(rows: tuple[dict[str, object], ...]):
        return [
            findings_task.parse_finding_row(
                row, family_id=assignments[str(row["record_id"])]["family"]
            )
            for row in rows
            if row["lane"] == "public.experimental_findings"
        ]

    train_findings = findings_task.build_finding_comparisons(
        parse_findings(train_sample.rows), seed=41
    )
    holdout_findings = findings_task.build_finding_comparisons(
        parse_findings(holdout_sample.rows), seed=43
    )
    findings_task.validate_family_disjoint(train_findings, holdout_findings)
    assert Counter(row.target for row in train_findings) == {"A": 4, "B": 4}
    assert Counter(row.target for row in holdout_findings) == {"A": 4, "B": 4}
    assert {row.task for row in train_findings} == {"invsqrt", "dqi", "chemistry", "all"}
    assert {row.task for row in holdout_findings} == {"invsqrt", "dqi", "chemistry", "all"}
