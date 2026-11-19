"""Private, offline CPU runner for the reviewed persistent operand-context experiment.

The checked-in packet is launch-disabled. A later, explicitly authorized release
must replace EXECUTION_ADMISSION.json with a hash-bound authorized admission.
No network access, accelerator, promotion, merge, or tool dispatch is used.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

import torch


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE / "source"
BASE_PATH = SOURCE_ROOT / "kernel" / "run_cap_then_grow_kaggle.py"
SUCCESSOR_PATH = SOURCE_ROOT / "successor" / "run_persistent_operand_context.py"
PREREGISTRATION_PATH = SOURCE_ROOT / "successor" / "PREREGISTRATION.json"
REVIEW_PATH = SOURCE_ROOT / "successor" / "REVIEW_RESULT.json"
ADMISSION_PATH = HERE / "EXECUTION_ADMISSION.json"
REPLAY_PATH = HERE / "independent_replay.py"

SCHEMA = "clay.persistent-operand-context.cloud.v1"
SOURCE_COMMITS = {
    "prototype": "d864f35d085a148a8e6f3171fd1ad9f0888b6bf4",
    "review_repair": "57519aa385b22330d249da724b52b265216c96e9",
}
EXPECTED_SOURCE_HASHES = {
    "base": "e1e8b916fe21da734c327c1d85db9dbf7b8de333cb4a57eace5f3640e3d5f63f",
    "successor": "13b3784d4c1de6cf57f6d9dc6046a5c04849a50a9aab5ab99445fd52b0bb6d09",
    "preregistration": "b9e3283f1881b0846a5a5f35f93d0245067ac269b683fcf2c85a824737581ce6",
    "review": "a7624b1e9f03ef4f68689c15a399d0f66010bae2026741043a1c4a7eb5b57df5",
}
SEEDS = (20261134, 20261135, 20261136)
TRAINED_ARMS = ("candidate", "context_permuted", "target_shuffle")
ARMS = (*TRAINED_ARMS, "zero_update")
UPDATES = 18_000
CHECKPOINT_EVERY = 500
BATCH_SIZE = 128
LEARNING_RATE = 0.002
EXPECTED_TRAINABLE = 142_164
BOOTSTRAP_SEED = 20261201
BOOTSTRAP_DRAWS = 4096
OUTPUT_ROOT = Path("/kaggle/working/clay-persistent-operand-context-20261119-v1")
TARGET_VOLUME = Path("/tmp")
AUTHORITY = "CONTROLLED_MEASUREMENT_ONLY_NO_PROMOTION"
TRAINABLE_PREFIXES = ("context_projection.", "adapter.", "adapter_head.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object: {path}")
    return value


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_module("clay_operand_context_cloud_base", BASE_PATH)
SUCCESSOR = load_module("clay_operand_context_cloud_successor", SUCCESSOR_PATH)


def verify_sources() -> dict[str, str]:
    paths = {
        "base": BASE_PATH,
        "successor": SUCCESSOR_PATH,
        "preregistration": PREREGISTRATION_PATH,
        "review": REVIEW_PATH,
    }
    observed = {name: sha256_file(path) for name, path in paths.items()}
    if observed != EXPECTED_SOURCE_HASHES:
        raise RuntimeError(f"reviewed source identity differs: {observed}")
    prereg = load_json(PREREGISTRATION_PATH)
    review = load_json(REVIEW_PATH)
    if prereg.get("status") != "SEALED_NOT_LAUNCHED":
        raise RuntimeError("preregistration state differs")
    if review.get("status") != "PASS_REPAIRED_PROTOTYPE_SCOPE":
        raise RuntimeError("independent review state differs")
    return observed


def require_execution_admission() -> dict[str, Any]:
    admission = load_json(ADMISSION_PATH)
    if admission.get("schema") != "clay.execution-admission.v1":
        raise RuntimeError("execution admission schema differs")
    if admission.get("state") != "NOT_CONSUMED":
        raise RuntimeError("execution admission is not available")
    if admission.get("execution_authorized") is not True:
        raise RuntimeError("execution admission is staged but not authorized")
    if admission.get("source_commits") != SOURCE_COMMITS:
        raise RuntimeError("execution admission source commits differ")
    if admission.get("source_hashes") != EXPECTED_SOURCE_HASHES:
        raise RuntimeError("execution admission source hashes differ")
    return admission


def trainable_hash(model: torch.nn.Module) -> str:
    state = {
        name: value
        for name, value in model.state_dict().items()
        if name.startswith(TRAINABLE_PREFIXES)
    }
    return BASE.tensor_map_hash(state)


def new_model(core: Any, parent: Mapping[str, Any], seed: int) -> torch.nn.Module:
    torch.manual_seed(seed)
    model_type = SUCCESSOR.persistent_model_class(core)
    model = model_type(len(parent["vocab"]))
    SUCCESSOR.load_parent_state(model, parent["model_state"])
    return model


def save_model(
    path: Path,
    *,
    model: torch.nn.Module,
    seed: int,
    arm: str,
    dataset_sha256: str,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".pt.pending")
    torch.save(
        {
            "schema": f"{SCHEMA}.model",
            "seed": seed,
            "arm": arm,
            "dataset_sha256": dataset_sha256,
            "source_commits": SOURCE_COMMITS,
            "model_state": model.state_dict(),
        },
        pending,
    )
    os.replace(pending, path)
    return sha256_file(path)


def train_one(
    core: Any,
    *,
    parent: Mapping[str, Any],
    rows: Sequence[Any],
    seed: int,
    arm: str,
    checkpoint_root: Path,
    dataset_sha256: str,
    status_path: Path,
) -> tuple[torch.nn.Module, dict[str, Any]]:
    arm_rows = SUCCESSOR.build_arm_rows(rows, seed, arm)
    model = new_model(core, parent, seed)
    frozen_before = BASE.tensor_map_hash(model.state_dict(), BASE.FROZEN_PREFIXES)
    initial_trainable = trainable_hash(model)
    selected = SUCCESSOR.selected_trainable(model)
    optimizer = torch.optim.Adam(selected, lr=LEARNING_RATE)
    sampler = core.DeterministicBatchSampler(len(rows), BATCH_SIZE, seed)
    checkpoint = core.TwoSlotCheckpoint(checkpoint_root / f"seed-{seed}" / arm)
    restored = checkpoint.load()
    step = 0
    generation = 0
    final_loss = math.nan
    if restored is not None:
        payload, pointer = restored
        expected = {
            "schema": f"{SCHEMA}.checkpoint",
            "seed": seed,
            "arm": arm,
            "dataset_sha256": dataset_sha256,
            "context_assignment_sha256": arm_rows.assignment_sha256,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise RuntimeError("checkpoint identity differs")
        model.load_state_dict(payload["model_state"])
        optimizer.load_state_dict(payload["optimizer_state"])
        sampler.load_state_dict(payload["sampler_state"])
        torch.set_rng_state(payload["torch_rng_state"])
        step = int(payload["step"])
        generation = int(pointer["generation"]) + 1
        final_loss = float(payload["loss"])
    stoi = {character: index for index, character in enumerate(parent["vocab"])}
    while step < UPDATES:
        model.train()
        indices = sampler.next_indices()
        inputs, labels, masks, context = SUCCESSOR.make_context_batch(
            core, arm_rows, indices, stoi, "cpu"
        )
        loss = SUCCESSOR.action_loss(model, inputs, labels, masks, context)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        step += 1
        final_loss = float(loss.detach())
        if step % CHECKPOINT_EVERY == 0 or step == UPDATES:
            checkpoint.save(
                {
                    "schema": f"{SCHEMA}.checkpoint",
                    "seed": seed,
                    "arm": arm,
                    "dataset_sha256": dataset_sha256,
                    "context_assignment_sha256": arm_rows.assignment_sha256,
                    "step": step,
                    "loss": final_loss,
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "sampler_state": sampler.state_dict(),
                    "torch_rng_state": torch.get_rng_state(),
                },
                generation,
            )
            atomic_json(
                status_path,
                {
                    "schema": f"{SCHEMA}.status",
                    "status": "TRAINING",
                    "seed": seed,
                    "arm": arm,
                    "step": step,
                    "updates": UPDATES,
                    "loss": final_loss,
                    "checkpoint_generation": generation,
                    "updated_at_utc": utc_now(),
                },
            )
            print(
                json.dumps(
                    {"status": "TRAINING", "seed": seed, "arm": arm, "step": step, "loss": final_loss}
                ),
                flush=True,
            )
            generation += 1
    frozen_after = BASE.tensor_map_hash(model.state_dict(), BASE.FROZEN_PREFIXES)
    if frozen_after != frozen_before:
        raise RuntimeError(f"frozen tensors changed: {seed}/{arm}")
    return model, {
        "steps": step,
        "final_loss": final_loss,
        "trainable_parameters": sum(parameter.numel() for parameter in selected),
        "initial_trainable_sha256": initial_trainable,
        "final_trainable_sha256": trainable_hash(model),
        "frozen_before_sha256": frozen_before,
        "frozen_after_sha256": frozen_after,
        "frozen_core_bit_identical": True,
        "context_assignment_sha256": arm_rows.assignment_sha256,
    }


def run_record(
    core: Any,
    model: torch.nn.Module,
    *,
    parent_result: Mapping[str, Any],
    held_rows: Sequence[Any],
    seed: int,
    arm: str,
    training: Mapping[str, Any],
    output_root: Path,
    dataset_sha256: str,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
) -> dict[str, Any]:
    held_arm = SUCCESSOR.build_arm_rows(held_rows, seed, arm)
    predictions, metrics = SUCCESSOR.evaluate_rows(
        core, model, held_rows, held_arm.context_rows, stoi, itos
    )
    count_score = core.counting_accuracy(
        model=model,
        rows=core.counting_rows(True),
        stoi=stoi,
        itos=itos,
        device="cpu",
    )
    model_path = output_root / "models" / f"seed-{seed}" / f"{arm}.pt"
    model_sha256 = save_model(
        model_path,
        model=model,
        seed=seed,
        arm=arm,
        dataset_sha256=dataset_sha256,
    )
    return {
        "seed": seed,
        "arm": arm,
        "steps": int(training["steps"]),
        "training": dict(training),
        "metrics": metrics,
        "predictions": predictions,
        "counting_accuracy": count_score,
        "parent_counting_accuracy": float(parent_result["counting_accuracy"]),
        "retention_exact": count_score == float(parent_result["counting_accuracy"]),
        "model_relative_path": model_path.relative_to(output_root).as_posix(),
        "model_sha256": model_sha256,
        "held_context_assignment_sha256": held_arm.assignment_sha256,
    }


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    admission = require_execution_admission()
    source_hashes = verify_sources()
    capacity = BASE.require_target_capacity(args.target_volume)
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    status_path = output_root / "STATUS.json"
    runtime_root = args.target_volume / "clay-persistent-operand-context-runtime"
    checkpoint_root = args.target_volume / "clay-persistent-operand-context-checkpoints"
    if runtime_root.exists():
        raise RuntimeError("foreign or stale runtime root exists")
    packet = BASE.extract_packet(args.input_root.resolve(strict=True), runtime_root)
    scbe_root = runtime_root / "scbe_repo"
    sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_frozen_multiview_adapter as core

    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))
    torch.use_deterministic_algorithms(True)
    train_rows, held_rows, dataset_sha256 = BASE.build_rows()
    if (len(train_rows), len(held_rows), dataset_sha256) != (
        1534,
        1509,
        SUCCESSOR.EXPECTED_DATASET_SHA256,
    ):
        raise RuntimeError("dataset identity differs")

    runs: list[dict[str, Any]] = []
    vocab: list[str] | None = None
    for seed in SEEDS:
        parent_path = runtime_root / f"baseline_run/parents/seed-{seed}/PARENT.pt"
        parent_result_path = runtime_root / f"baseline_run/parents/seed-{seed}/RESULT.json"
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        parent_result = BASE.load_json(parent_result_path)
        if int(parent.get("seed", seed)) != seed:
            raise RuntimeError(f"parent seed differs: {seed}")
        if vocab is None:
            vocab = list(parent["vocab"])
        elif vocab != list(parent["vocab"]):
            raise RuntimeError("parent vocab differs by seed")
        missing = [value for value in range(256) if chr(0xE100 + value) not in vocab]
        if missing:
            raise RuntimeError(f"byte-token vocab incomplete: {missing[:8]}")
        stoi = {character: index for index, character in enumerate(vocab)}
        itos = {index: character for index, character in enumerate(vocab)}
        initial_hashes: dict[str, str] = {}
        for arm in TRAINED_ARMS:
            model, training = train_one(
                core,
                parent=parent,
                rows=train_rows,
                seed=seed,
                arm=arm,
                checkpoint_root=checkpoint_root,
                dataset_sha256=dataset_sha256,
                status_path=status_path,
            )
            initial_hashes[arm] = str(training["initial_trainable_sha256"])
            runs.append(
                run_record(
                    core,
                    model,
                    parent_result=parent_result,
                    held_rows=held_rows,
                    seed=seed,
                    arm=arm,
                    training=training,
                    output_root=output_root,
                    dataset_sha256=dataset_sha256,
                    stoi=stoi,
                    itos=itos,
                )
            )
        if len(set(initial_hashes.values())) != 1:
            raise RuntimeError(f"matched arms did not start identically: {seed}")
        zero_model = new_model(core, parent, seed)
        zero_parameters = SUCCESSOR.selected_trainable(zero_model)
        zero_hash = trainable_hash(zero_model)
        if zero_hash != next(iter(initial_hashes.values())):
            raise RuntimeError(f"zero arm initialization differs: {seed}")
        zero_training = {
            "steps": 0,
            "final_loss": None,
            "trainable_parameters": sum(parameter.numel() for parameter in zero_parameters),
            "initial_trainable_sha256": zero_hash,
            "final_trainable_sha256": zero_hash,
            "frozen_core_bit_identical": True,
            "context_assignment_sha256": SUCCESSOR.build_arm_rows(
                train_rows, seed, "zero_update"
            ).assignment_sha256,
        }
        runs.append(
            run_record(
                core,
                zero_model,
                parent_result=parent_result,
                held_rows=held_rows,
                seed=seed,
                arm="zero_update",
                training=zero_training,
                output_root=output_root,
                dataset_sha256=dataset_sha256,
                stoi=stoi,
                itos=itos,
            )
        )

    by_arm = {
        arm: sorted(
            (run for run in runs if run["arm"] == arm),
            key=lambda run: int(run["seed"]),
        )
        for arm in ARMS
    }
    gate = SUCCESSOR.admission_gate(
        by_arm["candidate"],
        {name: by_arm[name] for name in ("context_permuted", "target_shuffle", "zero_update")},
        independent_replay=False,
        bootstrap_seed=BOOTSTRAP_SEED,
        bootstrap_draws=BOOTSTRAP_DRAWS,
    )
    result = {
        "schema": SCHEMA,
        "status": "AWAITING_INDEPENDENT_REPLAY",
        "authority": AUTHORITY,
        "created_at_utc": utc_now(),
        "admission_id": admission["admission_id"],
        "source_commits": SOURCE_COMMITS,
        "source_hashes": source_hashes,
        "packet": {
            "dataset_id": BASE.DATASET_ID,
            "descriptor_sha256": BASE.DESCRIPTOR_SHA256,
            "archive_sha256": BASE.ARCHIVE_SHA256,
            "packet_manifest_sha256": BASE.PACKET_MANIFEST_SHA256,
            "manifest_source_commit": packet["source_commit"],
            "parent_hashes": BASE.PARENT_HASHES,
        },
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "threads": torch.get_num_threads(),
            "target_capacity": capacity,
        },
        "contract": {
            "seeds": list(SEEDS),
            "arms": list(ARMS),
            "updates": UPDATES,
            "checkpoint_every": CHECKPOINT_EVERY,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "loss": "ordinary_torch_cross_entropy",
            "optimizer": "Adam",
            "trainable_parameters": EXPECTED_TRAINABLE,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "promotion": "NONE",
        },
        "dataset": {
            "identity_sha256": dataset_sha256,
            "train_rows": len(train_rows),
            "held_out_rows": len(held_rows),
            "record_layout": "opcode:u8 || x:u16be || y:u16be",
        },
        "vocab": vocab,
        "runs": runs,
        "measurement_gate": gate,
    }
    result_path = output_root / "RESULT.json"
    atomic_json(result_path, result)
    replay_receipt = output_root / "INDEPENDENT_REPLAY.json"
    command = [
        sys.executable,
        str(REPLAY_PATH),
        "--result",
        str(result_path),
        "--runtime-root",
        str(runtime_root),
        "--output-root",
        str(output_root),
        "--output",
        str(replay_receipt),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"independent replay failed: {completed.stdout[-1000:]} {completed.stderr[-1000:]}")
    replay = load_json(replay_receipt)
    if replay.get("status") != "PASS":
        raise RuntimeError("independent replay did not pass")
    gate = SUCCESSOR.admission_gate(
        by_arm["candidate"],
        {name: by_arm[name] for name in ("context_permuted", "target_shuffle", "zero_update")},
        independent_replay=True,
        bootstrap_seed=BOOTSTRAP_SEED,
        bootstrap_draws=BOOTSTRAP_DRAWS,
    )
    result["status"] = "COMPLETE_CONTROLLED_MEASUREMENT_NO_PROMOTION"
    result["measurement_gate"] = gate
    result["independent_replay"] = {
        "program_sha256": sha256_file(REPLAY_PATH),
        "receipt_sha256": sha256_file(replay_receipt),
        "checks": len(replay["checks"]),
    }
    atomic_json(result_path, result)
    atomic_json(
        status_path,
        {
            "schema": f"{SCHEMA}.status",
            "status": "COMPLETE",
            "result_sha256": sha256_file(result_path),
            "all_measurement_gates": gate["all_measurement_gates"],
            "promotion": "NONE",
            "completed_at_utc": utc_now(),
        },
    )
    return result


def smoke(output: Path) -> dict[str, Any]:
    source_hashes = verify_sources()
    receipt = SUCCESSOR.run_smoke()
    receipt.update(
        {
            "schema": f"{SCHEMA}.release-smoke",
            "source_commits": SOURCE_COMMITS,
            "source_hashes": source_hashes,
            "cloud_execution": False,
            "admission_state": load_json(ADMISSION_PATH).get("state"),
            "runner_sha256": sha256_file(Path(__file__)),
        }
    )
    atomic_json(output, receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--target-volume", type=Path, default=TARGET_VOLUME)
    parser.add_argument("--smoke-output", type=Path)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    if args.smoke_output is not None:
        receipt = smoke(args.smoke_output)
        print(json.dumps({"status": receipt["status"], "cloud_execution": False}, sort_keys=True))
        return 0
    result = run_campaign(args)
    print(json.dumps({"status": result["status"], "promotion": "NONE"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
