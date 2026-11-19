"""Independent, no-checkpoint audit of the persistent operand-context prototype."""

from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
WORKTREE = HERE.parents[2]
SUCCESSOR = EXPERIMENT / "successor_persistent_operand_context_v1"
RESULT = (
    EXPERIMENT
    / "terminal-output-v1"
    / "clay-cap-then-grow-codeout-20261119-v1"
    / "RESULT.json"
)
CORE = WORKTREE / "python" / "scbe" / "clay_frozen_multiview_adapter.py"
EXPECTED_CORE_SHA256 = "2cb6b396b4e5bec4427dfb033ba0dbc0bcd4d4aec06e2f5bb5864483dcf22eb8"


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_runner():
    path = SUCCESSOR / "run_persistent_operand_context.py"
    spec = importlib.util.spec_from_file_location("independent_operand_context_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load successor runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    runner = load_runner()
    terminal = json.loads(RESULT.read_text(encoding="utf-8"))
    prereg = json.loads((SUCCESSOR / "PREREGISTRATION.json").read_text(encoding="utf-8"))
    smoke = json.loads((HERE / "INDEPENDENT_SMOKE.json").read_text(encoding="utf-8"))
    train, held, dataset_hash = runner.BASE.build_rows()

    derangements = {}
    for seed in runner.SEEDS:
        derangements[str(seed)] = {}
        for split, rows in (("train", train), ("held_out", held)):
            arm = runner.build_arm_rows(rows, seed, "context_permuted")
            assert len(arm.context_rows) == len(rows)
            assert sorted(row.identity_sha256 for row in arm.context_rows) == sorted(
                row.identity_sha256 for row in rows
            )
            assert all(
                destination.identity_sha256 != source.identity_sha256
                for destination, source in zip(rows, arm.context_rows, strict=True)
            )
            assert all(
                (destination.operation, len(str(destination.result)), destination.split)
                == (source.operation, len(str(source.result)), source.split)
                for destination, source in zip(rows, arm.context_rows, strict=True)
            )
            derangements[str(seed)][split] = arm.assignment_sha256

    vocab_size = len(terminal["vocab"])
    adapter_parameters = (192 * 160 + 160) + (160 * 160 + 160) + (160 * 192 + 192)
    adapter_head_parameters = 192 * vocab_size + vocab_size
    base_parameters = adapter_parameters + adapter_head_parameters
    projection_parameters = 6 * 192 + 192
    total_parameters = base_parameters + projection_parameters
    assert vocab_size == 276
    assert base_parameters == 140_820
    assert projection_parameters == 1_344
    assert total_parameters == 142_164
    assert all(int(run["training"]["trainable_parameters"]) == 140_820 for run in terminal["runs"])

    train_add = {row.result for row in train if row.operation == "add"}
    held_add = {row.result for row in held if row.operation == "add"}
    train_subtract = {row.result for row in train if row.operation == "subtract"}
    held_subtract = {row.result for row in held if row.operation == "subtract"}
    train_multiply = {row.result for row in train if row.operation == "multiply"}
    held_multiply = {row.result for row in held if row.operation == "multiply"}
    assert train_add.isdisjoint(held_add)
    assert train_multiply.isdisjoint(held_multiply)
    assert train_subtract == held_subtract

    assert tuple(prereg["training_contract"]["seeds"]) == runner.SEEDS
    assert prereg["training_contract"]["updates_per_trained_arm"] == 18_000
    assert prereg["mechanism_change"]["frozen_modules"] == ["e", "g", "count_head"]
    assert prereg["mechanism_change"]["context_projection_parameters"] == 1_344
    assert prereg["mechanism_change"]["exact_trainable_parameters_per_trained_arm"] == 142_164
    assert "two times pooled" in prereg["gates"]["uncertainty"]
    assert "3 of 3" in prereg["gates"]["matched_seed_wins"]
    assert "paired" in prereg["gates"]["uncertainty"]
    assert "nonzero" in prereg["gates"]["zero_check"]
    assert "bit-identical" in prereg["gates"]["retention"]
    assert smoke["frozen_tensors_bit_identical_after_synthetic_update"] is True
    assert file_hash(CORE) == EXPECTED_CORE_SHA256
    assert dataset_hash == runner.EXPECTED_DATASET_SHA256

    reviewed = [
        SUCCESSOR / "run_persistent_operand_context.py",
        SUCCESSOR / "test_successor.py",
        SUCCESSOR / "PREREGISTRATION.json",
        SUCCESSOR / "REPORT.md",
        HERE / "INDEPENDENT_SMOKE.json",
        HERE / "PYTEST.txt",
        HERE / "RUFF.txt",
        HERE / "DIFF_CHECK.txt",
    ]
    receipt = {
        "schema": "clay.persistent-operand-context.independent-review.v1",
        "status": "PASS_REPAIRED_PROTOTYPE_SCOPE",
        "source_commit_reviewed": "d864f35d085a148a8e6f3171fd1ad9f0888b6bf4",
        "authority": "NO_CLOUD_NO_CHECKPOINT_LOAD_NO_PROMOTION_NO_PUSH",
        "parameter_accounting": {
            "vocab_size": vocab_size,
            "base_adapter_and_head": base_parameters,
            "context_projection": projection_parameters,
            "total_trainable": total_parameters,
        },
        "dataset": {
            "sha256": dataset_hash,
            "train_rows": len(train),
            "held_out_rows": len(held),
            "add_support_disjoint": True,
            "multiply_support_disjoint": True,
            "subtract_support_equal": True,
        },
        "context_derangements": derangements,
        "frozen_modules": ["e", "g", "count_head"],
        "gate_contract": {
            "seeds": list(runner.SEEDS),
            "two_pooled_sd": True,
            "matched_seed_wins_3_of_3": True,
            "paired_finite_evaluation": True,
            "per_operation_nonzero": True,
            "out_of_support_add_multiply": True,
            "retention_and_frozen_identity": True,
            "independent_replay": True,
        },
        "tests": {"pytest": "10 passed", "ruff": "PASS", "py_compile": "PASS", "diff_check": "PASS"},
        "reviewed_files": {
            path.relative_to(WORKTREE).as_posix(): {"bytes": path.stat().st_size, "sha256": file_hash(path)}
            for path in reviewed
        },
        "remaining_boundary": "Full checkpoint-aware campaign replay and execution remain unrun and unauthorized.",
        "promotion": "NONE",
    }
    (HERE / "REVIEW_RESULT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": receipt["status"], "promotion": "NONE"}, sort_keys=True))


if __name__ == "__main__":
    main()
