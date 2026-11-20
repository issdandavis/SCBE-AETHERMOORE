from __future__ import annotations

from pathlib import Path

import pytest

import findings_task
import task_manifest
import vqcc_task


def _gate_examples() -> list[vqcc_task.GateCountExample]:
    result: list[vqcc_task.GateCountExample] = []
    index = 0
    for count in range(4):
        for member in range(8):
            opcodes = [0x01] * 32
            for position in range(count):
                opcodes[position] = tuple(vqcc_task.TOFFOLI_OPCODES)[position % 6]
            result.append(
                vqcc_task.GateCountExample(
                    record_id=f"gate-{index:03d}",
                    family_id=f"gate-family-{member % 4}",
                    opcodes=tuple(opcodes),
                    count=count,
                )
            )
            index += 1
    return result


def _finding_examples() -> list[findings_task.FindingExample]:
    result = []
    for index in range(12):
        row = {
            "record_id": f"finding-{index:03d}",
            "lane": "public.experimental_findings",
            "question": (
                f"What limitation did the public dqi experiment report for mechanism-{index:03d}? "
                "Evidence tier: full-verifier."
            ),
            "answer": f"measured limitation {index:03d}",
        }
        result.append(
            findings_task.parse_finding_row(
                row,
                family_id=f"finding-family-{index:03d}",
            )
        )
    return result


def test_exact_task_artifacts_roundtrip_and_are_reproducible(tmp_path: Path) -> None:
    gates = vqcc_task.build_balanced_comparisons(_gate_examples(), seed=7, per_label=4)
    shuffled_gates = vqcc_task.shuffled_binding(gates, seed=11)
    findings = _finding_examples()
    comparisons = findings_task.build_finding_comparisons(
        findings,
        seed=13,
        length_bucket_width=64,
    )
    candidate, shuffled = findings_task.build_finding_training_occurrences(
        findings,
        comparisons,
        seed=17,
        length_bucket_width=64,
    )

    first = tmp_path / "first"
    second = tmp_path / "second"
    receipts = []
    for root in (first, second):
        local_receipts = [
            task_manifest.write_cost_artifact(
                root / "train/gate.jsonl",
                gates,
                relative_path="train/gate.jsonl",
                dataset_role="train",
                population="balanced",
                binding="intact",
            ),
            task_manifest.write_cost_artifact(
                root / "train/gate-shuffled.jsonl",
                shuffled_gates,
                relative_path="train/gate-shuffled.jsonl",
                dataset_role="train",
                population="balanced",
                binding="shuffled_binding",
            ),
            task_manifest.write_finding_artifact(
                root / "train/findings.jsonl",
                comparisons,
                relative_path="train/findings.jsonl",
                dataset_role="train",
            ),
            task_manifest.write_finding_training_artifact(
                root / "train/findings-candidate.jsonl",
                candidate,
                relative_path="train/findings-candidate.jsonl",
                dataset_role="train",
                binding="intact",
            ),
            task_manifest.write_finding_training_artifact(
                root / "train/findings-shuffled.jsonl",
                shuffled,
                relative_path="train/findings-shuffled.jsonl",
                dataset_role="train",
                binding="shuffled_binding",
            ),
        ]
        task_manifest.write_task_manifest(
            root,
            local_receipts,
            authorities={"fixture": "task-manifest-test-v1"},
        )
        receipts.append(local_receipts)

    assert receipts[0] == receipts[1]
    assert {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    } == {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert set(
        task_manifest.load_cost_artifact(
            first / "train/gate.jsonl",
            dataset_role="train",
            population="balanced",
            binding="intact",
        )
    ) == set(gates)
    assert set(
        task_manifest.load_finding_artifact(
            first / "train/findings.jsonl",
            dataset_role="train",
        )
    ) == set(comparisons)
    assert set(
        task_manifest.load_finding_training_artifact(
            first / "train/findings-shuffled.jsonl",
            dataset_role="train",
            binding="shuffled_binding",
            comparisons=comparisons,
            examples=findings,
            length_bucket_width=64,
        )
    ) == set(shuffled)


def test_noncanonical_or_tampered_task_artifacts_fail_closed(tmp_path: Path) -> None:
    gates = vqcc_task.build_balanced_comparisons(_gate_examples(), seed=19, per_label=2)
    path = tmp_path / "gate.jsonl"
    task_manifest.write_cost_artifact(
        path,
        gates,
        relative_path="gate.jsonl",
        dataset_role="train",
        population="balanced",
        binding="intact",
    )
    canonical = path.read_bytes()
    path.write_bytes(canonical.replace(b'"a_count":', b'"a_count" :', 1))
    with pytest.raises(ValueError, match="canonical JSON"):
        task_manifest.load_cost_artifact(
            path,
            dataset_role="train",
            population="balanced",
            binding="intact",
        )

    path.write_bytes(canonical.replace(b'"a_count":0', b'"a_count":true', 1))
    with pytest.raises(ValueError, match="payload SHA-256 differs"):
        task_manifest.load_cost_artifact(
            path,
            dataset_role="train",
            population="balanced",
            binding="intact",
        )
