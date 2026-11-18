"""Resume-safe causal campaign for matched pre-GRU byte feature tables.

This runner reuses the sealed frozen parents, source-disjoint action dataset,
evaluator, exposure ledger, and two-slot checkpoints from the frozen multiview
campaign.  It adds exactly one action-only 256 -> 64 projection before the
frozen GRU.  Candidate and learned controls have identical topology, trainable
parameter count, batches, steps, parents, and seeds.

No result produced here grants execution, promotion, or partial-unfreeze
authority.  The default 25 GiB admission floor is intentionally inherited and
must not be lowered to work around local storage pressure.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import inspect
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import clay_math.prime_lane_scissors as prime_lane_module
import clay_math.universal_cycle_curriculum as universal_cycle_module
import clay_math.universal_prime_scissors as universal_prime_module
from python.scbe.clay_frozen_multiview_adapter import (
    BOS,
    EOS,
    SEP,
    DeterministicBatchSampler,
    FrozenActionModel,
    RunConfig,
    TwoSlotCheckpoint,
    action_metrics,
    atomic_json,
    atomic_torch,
    counting_accuracy,
    counting_rows,
    file_sha256,
    flattened_trainable,
    frozen_state,
    frozen_state_identical,
    make_batch,
    metric_comparison,
    paired_exact_p,
    paired_prediction_comparison,
    set_trainable,
    stable_hash,
    utc_now,
)
from python.scbe.clay_frozen_multiview_data import (
    ActionTextRow,
    BYTE_TOKEN_BASE,
    FrozenMultiviewDataset,
    action_prompt,
    build_frozen_multiview_dataset,
    decode_byte_token_text,
)
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter
from python.scbe.clay_prime_scissor_input import (
    ARMS,
    ActionGatedPrimeScissorInput,
    FeatureTables,
    SealedOccurrenceDerangement,
    build_feature_tables,
    build_occurrence_derangement,
    tensor_sha256,
)
from python.scbe.concept_exposure_ledger import (
    ConceptExposureLedger,
    ExposureSample,
    weight_effect_receipt,
)

SCHEMA = "clay.prime-scissor-input-campaign.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_PARTIAL_UNFREEZE"
PRIMARY = "prime_scissor_input"
CONTROLS = tuple(arm for arm in ARMS if arm != PRIMARY)
SHUFFLED = "shuffled_binding_matched"
CLAY_MATH_COMMIT = "0a5a06bed57e922f7e9ca04229664266aa8d215c"
CLAY_MATH_SOURCE_HASHES = {
    "prime_lane_scissors.py": "dfa36d57002ca5842bb5a4237be856a16974ac89cbbd460e79db5bb8a08cbb66",
    "universal_cycle_curriculum.py": "e7124402ab30d35b08695153d1b17aab16b7ed2dd557a9f06128ba047b3a4e69",
    "universal_prime_scissors.py": "9ac2543ea5aa7d7360c02fbee3d22f04b00e61aa6dac502f6c391d8b33a9c19a",
}
DEFAULT_MINIMUM_FREE_GIB = 25.0
ARM_SEED_OFFSET = 1701
TRAIN_BINDING_SEED = 0x51A55EED
HOLDOUT_BINDING_SEED = 0xA117D07


@dataclass(frozen=True, slots=True)
class PrimeScissorCampaignConfig:
    baseline_run: str
    baseline_manifest_sha256: str
    baseline_result_sha256: str
    dataset_manifest_sha256: str
    train_occurrence_binding_sha256: str
    holdout_occurrence_binding_sha256: str
    feature_table_receipt_sha256: str
    runner_sha256: str
    input_module_sha256: str
    preregistration_sha256: str
    preflight_receipt_sha256: str
    clay_math_commit: str
    clay_math_source_hashes: Mapping[str, str]
    seeds: tuple[int, ...]
    grow_steps: int
    checkpoint_every: int
    batch_size: int
    learning_rate: float
    threads: int
    requested_device: str
    actual_device: str
    source_dir_authority: str
    source_hashes: Mapping[str, str]
    authority: str = AUTHORITY
    arms: tuple[str, ...] = ARMS


def require_storage(output: Path, minimum_free_gib: float) -> float:
    if minimum_free_gib < DEFAULT_MINIMUM_FREE_GIB:
        raise ValueError(
            f"minimum-free-gib cannot be below {DEFAULT_MINIMUM_FREE_GIB:.1f}"
        )
    anchor = Path(output.anchor or "C:/")
    free = shutil.disk_usage(anchor).free / (1024**3)
    if free < minimum_free_gib:
        raise RuntimeError(
            f"storage admission closed: {free:.3f} GiB < {minimum_free_gib:.3f} GiB"
        )
    return free


def resolve_device(requested: str) -> str:
    if requested not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"unsupported device request: {requested}")
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false")
    return requested


def verify_preflight_authority(
    receipt: Mapping[str, Any], actual: Mapping[str, Any]
) -> None:
    """Require regenerated tables and bindings to match the local PASS receipt."""

    if receipt.get("status") != "PASS_NO_MATERIAL_RUN":
        raise RuntimeError("preflight receipt is not an admitted PASS receipt")
    expected = {
        "dataset_manifest_sha256": receipt["dataset_manifest_sha256"],
        "feature_receipt_sha256": receipt["feature_tables"]["feature_receipt_sha256"],
        "table_sha256": {
            "prime_scissor": receipt["feature_tables"]["prime_scissor_sha256"],
            "canonical_onehot_matched": receipt["feature_tables"][
                "canonical_onehot_matched_sha256"
            ],
            "deterministic_random_matched": receipt["feature_tables"][
                "deterministic_random_matched_sha256"
            ],
            "no_intervention": receipt["feature_tables"]["no_intervention_sha256"],
        },
        "pivot_indices_sha256": receipt["feature_tables"]["pivot_indices_sha256"],
        "pivot_descriptors_sha256": receipt["feature_tables"][
            "pivot_descriptors_sha256"
        ],
        "empirical_conditioning_receipt_sha256": receipt[
            "empirical_conditioning_receipt_sha256"
        ],
        "train_binding_seal_sha256": receipt["train_binding"]["seal_sha256"],
        "train_binding_mapped_sha256": receipt["train_binding"]["mapped_values_sha256"],
        "holdout_binding_seal_sha256": receipt["holdout_binding"]["seal_sha256"],
        "holdout_binding_mapped_sha256": receipt["holdout_binding"][
            "mapped_values_sha256"
        ],
    }
    if dict(actual) != expected:
        raise RuntimeError(
            "runtime-regenerated experiment surfaces differ from the preflight receipt"
        )


def configure_determinism(*, seed: int, device: str) -> None:
    if device == "cuda":
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    if device == "cuda":
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def _optimizer_to_device(optimizer: torch.optim.Optimizer, device: str) -> None:
    for state in optimizer.state.values():
        for key, value in state.items():
            if isinstance(value, Tensor):
                state[key] = value.to(device)


def clay_math_provenance(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    loaded = {
        "prime_lane_scissors.py": Path(inspect.getfile(prime_lane_module)).resolve(
            strict=True
        ),
        "universal_cycle_curriculum.py": Path(
            inspect.getfile(universal_cycle_module)
        ).resolve(strict=True),
        "universal_prime_scissors.py": Path(
            inspect.getfile(universal_prime_module)
        ).resolve(strict=True),
    }
    candidate_parents = [root / "clay-math" / "clay_math", root / "clay_math"]
    expected_parent = next(
        (
            candidate.resolve(strict=True)
            for candidate in candidate_parents
            if candidate.is_dir()
        ),
        None,
    )
    if expected_parent is None:
        raise RuntimeError(
            "declared clay_math root has neither supported package layout"
        )
    for name, path in loaded.items():
        if path.parent != expected_parent or path.name != name:
            raise RuntimeError(
                f"loaded clay_math module is outside the declared source root: {path}"
            )
    source_hashes = {name: file_sha256(path) for name, path in sorted(loaded.items())}
    if source_hashes != CLAY_MATH_SOURCE_HASHES:
        raise RuntimeError(
            "clay_math source hashes differ from commit-pinned packet provenance"
        )
    git_probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if git_probe.returncode == 0:
        commit = git_probe.stdout.strip()
        if commit != CLAY_MATH_COMMIT:
            raise RuntimeError(
                f"clay_math commit differs: {commit} != {CLAY_MATH_COMMIT}"
            )
        if subprocess.run(
            ["git", "-C", str(root), "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip():
            raise RuntimeError("clay_math source worktree is not clean")
        mode = "clean-git-commit-and-file-hashes"
    else:
        commit = CLAY_MATH_COMMIT
        mode = "vendored-commit-pinned-file-hashes"
    return {
        "commit": commit,
        "mode": mode,
        "package_layout": str(expected_parent.relative_to(root)).replace("\\", "/"),
        "source_hashes": source_hashes,
    }


def _training_config(
    campaign: PrimeScissorCampaignConfig, baseline_manifest: Mapping[str, Any]
) -> RunConfig:
    base = baseline_manifest["config"]
    return RunConfig(
        seeds=campaign.seeds,
        data_seed=int(base["data_seed"]),
        rows_per_view=int(base["rows_per_view"]),
        holdout_rows=int(base["holdout_rows"]),
        count_steps=int(base["count_steps"]),
        grow_steps=campaign.grow_steps,
        checkpoint_every=campaign.checkpoint_every,
        batch_size=campaign.batch_size,
        learning_rate=campaign.learning_rate,
        threads=campaign.threads,
        device=campaign.actual_device,
        source_dir=campaign.source_dir_authority,
        source_hashes=campaign.source_hashes,
        dataset_manifest_sha256=campaign.dataset_manifest_sha256,
        authority=campaign.authority,
        arms=campaign.arms,
    )


def empirical_conditioning_receipt(
    tables: FeatureTables, dataset: FrozenMultiviewDataset
) -> dict[str, Any]:
    """Receipt train/holdout-frequency-weighted table geometry without using labels."""

    result: dict[str, Any] = {
        "schema": f"{SCHEMA}.empirical-conditioning",
        "labels_used": False,
        "note": "controls match different conditioning classes; no whole-arm equal-conditioning claim",
        "splits": {},
    }
    for split_name, rows in (
        ("train", dataset.multiview_rows),
        ("holdout", dataset.holdout_rows),
    ):
        counts = torch.zeros(256, dtype=torch.float64)
        for row in rows:
            payload = decode_byte_token_text(row.prompt[3:-3])
            counts += torch.bincount(
                torch.tensor(list(payload), dtype=torch.long), minlength=256
            ).double()
        weights = counts / counts.sum()
        metrics: dict[str, Any] = {}
        grams: dict[str, Tensor] = {}
        for table_name in (
            "prime_scissor",
            "canonical_onehot_matched",
            "deterministic_random_matched",
        ):
            table = tables.tables[table_name].double()
            gram = table.T @ (weights[:, None] * table)
            grams[table_name] = gram
            row_norm_squared = torch.linalg.vector_norm(table, dim=1).square()
            metrics[table_name] = {
                "frequency_weighted_gram_sha256": tensor_sha256(gram),
                "frequency_weighted_mean_row_norm_squared": float(
                    torch.dot(weights, row_norm_squared)
                ),
                "frequency_weighted_gram_frobenius": float(
                    torch.linalg.vector_norm(gram)
                ),
            }
        candidate_gram = grams["prime_scissor"]
        for control in (
            "canonical_onehot_matched",
            "deterministic_random_matched",
        ):
            metrics[control]["gram_difference_from_candidate_frobenius"] = float(
                torch.linalg.vector_norm(grams[control] - candidate_gram)
            )
        result["splits"][split_name] = {
            "occurrence_count": int(counts.sum()),
            "byte_histogram_sha256": tensor_sha256(counts),
            "byte_zero_frequency": float(weights[0]),
            "tables": metrics,
        }
    return {**result, "receipt_sha256": stable_hash(result)}


def _checkpoint_payload(
    *,
    model: ActionGatedPrimeScissorInput,
    optimizer: torch.optim.Optimizer,
    sampler: DeterministicBatchSampler,
    ledger: ConceptExposureLedger,
    step: int,
    generation: int,
    loss: float,
    arm: str,
    seed: int,
    config_hash: str,
) -> dict[str, Any]:
    payload = {
        "schema": f"{SCHEMA}.checkpoint",
        "arm": arm,
        "seed": seed,
        "config_hash": config_hash,
        "step": step,
        "generation": generation,
        "loss": loss,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "sampler_state": sampler.state_dict(),
        "ledger_state": ledger.state_dict(),
        "torch_cpu_rng_state": torch.get_rng_state(),
        "actual_device": next(model.parameters()).device.type,
    }
    if payload["actual_device"] == "cuda":
        payload["torch_cuda_rng_state_all"] = torch.cuda.get_rng_state_all()
    return payload


def feature_owner_mask(
    rows: Sequence[ActionTextRow],
    indices: Sequence[int],
    *,
    input_width: int,
    device: str,
) -> Tensor:
    """Mark only source payload bytes, excluding wrappers and teacher-forced targets."""

    result = torch.zeros((len(indices), input_width), dtype=torch.bool)
    for batch_index, row_index in enumerate(indices):
        prompt = rows[row_index].prompt
        payload = decode_byte_token_text(prompt[3:-3])
        start = 1 + 3  # BOS followed by the three-character ``K :`` wrapper.
        stop = start + len(payload)
        if stop > input_width:
            raise RuntimeError("owned payload positions exceed the encoded input width")
        result[batch_index, start:stop] = True
    return result.to(device)


def train_feature_steps(
    *,
    model: ActionGatedPrimeScissorInput,
    arm: str,
    seed: int,
    rows: Sequence[ActionTextRow],
    binding: SealedOccurrenceDerangement,
    ledger: ConceptExposureLedger,
    stoi: Mapping[str, int],
    config: RunConfig,
    total_steps: int,
    checkpoint_dir: Path,
    config_hash: str,
) -> tuple[int, float, int]:
    """Train one matched arm with exact sampler/checkpoint continuation."""

    model.set_path("adapter")
    trainable = set_trainable(model, arm)
    optimizer = torch.optim.Adam(trainable, lr=config.learning_rate)
    sampler = DeterministicBatchSampler(
        len(rows), config.batch_size, seed + ARM_SEED_OFFSET
    )
    checkpoint = TwoSlotCheckpoint(checkpoint_dir)
    restored = checkpoint.load()
    step = 0
    generation = 0
    last_loss = math.nan
    if restored is not None:
        payload, pointer = restored
        expected = {
            "schema": f"{SCHEMA}.checkpoint",
            "arm": arm,
            "seed": seed,
            "config_hash": config_hash,
            "actual_device": config.device,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise RuntimeError("prime-scissor checkpoint identity differs")
        model.load_state_dict(payload["model_state"])
        optimizer.load_state_dict(payload["optimizer_state"])
        _optimizer_to_device(optimizer, config.device)
        sampler.load_state_dict(payload["sampler_state"])
        ledger.restore_state(payload["ledger_state"])
        torch.set_rng_state(payload["torch_cpu_rng_state"])
        if config.device == "cuda":
            if "torch_cuda_rng_state_all" not in payload:
                raise RuntimeError("CUDA checkpoint lacks CUDA RNG state")
            torch.cuda.set_rng_state_all(payload["torch_cuda_rng_state_all"])
        step = int(payload["step"])
        generation = int(pointer["generation"]) + 1
        last_loss = float(payload["loss"])

    pairs = tuple(row.pair() for row in rows)
    loss_function = nn.CrossEntropyLoss(reduction="none")
    while step < total_steps:
        model.train()
        indices = sampler.next_indices()
        inputs, labels, masks = make_batch(pairs, indices, stoi, config.device)
        batch_rows = [rows[index] for index in indices]
        kwargs: dict[str, Any] = {
            "feature_owner_mask": feature_owner_mask(
                rows, indices, input_width=inputs.shape[1], device=config.device
            )
        }
        if arm == SHUFFLED:
            kwargs.update(
                {
                    "sample_ids": [row.sample.sample_id for row in batch_rows],
                    "binding": binding,
                }
            )
        logits, _ = model(inputs, "action", **kwargs)
        token_loss = loss_function(
            logits.reshape(-1, logits.size(-1)), labels.reshape(-1)
        ).reshape(labels.shape)
        denominators = masks.sum(dim=1).clamp(min=1)
        sample_loss = (token_loss * masks).sum(dim=1) / denominators
        loss = sample_loss.mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ledger.observe_batch(
            [row.sample.sample_id for row in batch_rows],
            sample_loss.detach().cpu().numpy(),
            np.zeros((len(indices), 5), dtype=np.float64),
        )
        step += 1
        last_loss = float(loss.detach().cpu())
        if step % config.checkpoint_every == 0 or step == total_steps:
            checkpoint.save(
                _checkpoint_payload(
                    model=model,
                    optimizer=optimizer,
                    sampler=sampler,
                    ledger=ledger,
                    step=step,
                    generation=generation,
                    loss=last_loss,
                    arm=arm,
                    seed=seed,
                    config_hash=config_hash,
                ),
                generation,
            )
            generation += 1
    return step, last_loss, sum(parameter.numel() for parameter in trainable)


@torch.inference_mode()
def _generate_action(
    model: ActionGatedPrimeScissorInput,
    row: ActionTextRow,
    *,
    binding: SealedOccurrenceDerangement,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    device: str,
) -> int | None:
    model.eval()
    ids = [stoi[BOS], *(stoi[character] for character in row.prompt), stoi[SEP]]
    payload_width = len(decode_byte_token_text(row.prompt[3:-3]))
    owner_mask = torch.zeros((1, len(ids)), dtype=torch.bool, device=device)
    owner_mask[0, 4 : 4 + payload_width] = True
    kwargs: dict[str, Any] = {"feature_owner_mask": owner_mask}
    if model.arm == SHUFFLED:
        kwargs.update({"sample_ids": [row.sample.sample_id], "binding": binding})
    logits, state = model(torch.tensor([ids], device=device), "action", **kwargs)
    token = int(logits[0, -1].argmax())
    output = []
    for _ in range(2):
        if token == stoi[EOS]:
            break
        output.append(itos[token])
        continuation = torch.tensor([[token]], device=device)
        logits, state = model(
            continuation,
            "action",
            state,
            feature_owner_mask=torch.zeros_like(continuation, dtype=torch.bool),
        )
        token = int(logits[0, -1].argmax())
    try:
        return int("".join(output).strip().split()[0])
    except (ValueError, IndexError):
        return None


@torch.inference_mode()
def predict_feature_rows(
    model: ActionGatedPrimeScissorInput,
    *,
    rows: Sequence[ActionTextRow],
    binding: SealedOccurrenceDerangement,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    device: str,
) -> list[dict[str, Any]]:
    predictions = []
    for index, row in enumerate(rows):
        prediction = _generate_action(
            model, row, binding=binding, stoi=stoi, itos=itos, device=device
        )
        predictions.append(
            {
                "example_index": index,
                "sample_id": row.sample.sample_id,
                "payload_sha256": row.sample.payload_sha256,
                "target": row.label,
                "prediction": prediction,
                "correct": prediction == row.label,
                "sector": row.sector,
                "operation_id": row.sample.operation_id,
                "view_id": row.sample.view_id,
                "source_family": row.sample.source_family,
            }
        )
    return predictions


def train_arm(
    *,
    arm: str,
    seed: int,
    output: Path,
    campaign: PrimeScissorCampaignConfig,
    baseline_manifest: Mapping[str, Any],
    parent: Mapping[str, Any],
    parent_result: Mapping[str, Any],
    dataset: FrozenMultiviewDataset,
    tables: FeatureTables,
    train_binding: SealedOccurrenceDerangement,
    holdout_binding: SealedOccurrenceDerangement,
    config_hash: str,
) -> dict[str, Any]:
    directory = output / "horses" / f"{arm}-seed-{seed}"
    model_path = directory / "MODEL.pt"
    result_path = directory / "RESULT.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("config_hash") != config_hash
            or result.get("arm") != arm
            or int(result.get("seed", -1)) != seed
        ):
            raise RuntimeError("existing prime-scissor horse identity differs")
        if file_sha256(model_path) != result["model_sha256"]:
            raise RuntimeError("prime-scissor horse model hash differs")
        return result

    vocab = list(parent["vocab"])
    stoi = {token: index for index, token in enumerate(vocab)}
    itos = {index: token for token, index in stoi.items()}
    configure_determinism(seed=seed + ARM_SEED_OFFSET, device=campaign.actual_device)
    model = ActionGatedPrimeScissorInput(vocab, arm=arm, tables=tables).to(
        campaign.actual_device
    )
    model.load_parent_state(parent["model_state"])
    frozen_before = frozen_state(model)
    initial = flattened_trainable(model, arm).copy()
    train_rows = dataset.multiview_rows
    eval_rows = dataset.holdout_rows
    ledger = ConceptExposureLedger(
        [*(row.sample for row in train_rows), *(row.sample for row in eval_rows)],
        gradient_width=5,
        minimum_exposures_per_concept=max(1, campaign.grow_steps),
    )
    steps, loss, trainable = train_feature_steps(
        model=model,
        arm=arm,
        seed=seed,
        rows=train_rows,
        binding=train_binding,
        ledger=ledger,
        stoi=stoi,
        config=_training_config(campaign, baseline_manifest),
        total_steps=campaign.grow_steps,
        checkpoint_dir=directory / "checkpoints",
        config_hash=config_hash,
    )
    core_identical = frozen_state_identical(frozen_before, model)
    if not core_identical:
        raise RuntimeError(f"base parent tensors changed for {arm} seed {seed}")
    predictions = predict_feature_rows(
        model,
        rows=eval_rows,
        binding=holdout_binding,
        stoi=stoi,
        itos=itos,
        device=campaign.actual_device,
    )
    count_score = counting_accuracy(
        model,
        rows=counting_rows(True),
        stoi=stoi,
        itos=itos,
        device=campaign.actual_device,
    )
    final = flattened_trainable(model, arm)
    payload = {
        "schema": f"{SCHEMA}.horse",
        "arm": arm,
        "seed": seed,
        "config_hash": config_hash,
        "parent_sha256": parent_result["parent_sha256"],
        "model_state": model.state_dict(),
        "vocab": vocab,
    }
    atomic_torch(model_path, payload)
    result = {
        "schema": f"{SCHEMA}.horse-result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "arm": arm,
        "seed": seed,
        "config_hash": config_hash,
        "actual_device": campaign.actual_device,
        "train_binding_sha256": train_binding.seal_sha256,
        "holdout_binding_sha256": holdout_binding.seal_sha256,
        "steps": steps,
        "trainable_parameters": trainable,
        "final_loss": loss,
        "metrics": action_metrics(predictions),
        "predictions": predictions,
        "counting_accuracy": count_score,
        "parent_counting_accuracy": parent_result["counting_accuracy"],
        "base_parent_bit_identical": core_identical,
        "input_receipt": model.input_receipt(),
        "weight_effect": weight_effect_receipt(initial, final),
        "exposure_report": ledger.report(),
        "model_sha256": file_sha256(model_path),
        "completed_at_utc": utc_now(),
    }
    atomic_json(result_path, result)
    return result


def sample_blocked_prediction_comparison(
    contender: Sequence[Mapping[str, Any]], control: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Treat held sample IDs, not seed-repeated predictions, as inference blocks."""

    def unpack(horses: Sequence[Mapping[str, Any]]) -> dict[tuple[int, str], bool]:
        result: dict[tuple[int, str], bool] = {}
        for horse in horses:
            seed = int(horse["seed"])
            for prediction in horse["predictions"]:
                key = (seed, str(prediction["sample_id"]))
                if key in result:
                    raise RuntimeError(
                        "duplicate seed/sample prediction in blocked comparison"
                    )
                result[key] = bool(prediction["correct"])
        return result

    left = unpack(contender)
    right = unpack(control)
    if left.keys() != right.keys():
        raise RuntimeError("sample-blocked prediction keys differ")
    seeds = sorted({key[0] for key in left})
    sample_ids = sorted({key[1] for key in left})
    per_seed_deltas = {
        str(seed): sum(
            int(left[seed, sample_id]) - int(right[seed, sample_id])
            for sample_id in sample_ids
        )
        for seed in seeds
    }
    per_seed_direction_3_of_3 = len(seeds) == 3 and all(
        delta > 0 for delta in per_seed_deltas.values()
    )
    block_deltas = {
        sample_id: sum(
            int(left[seed, sample_id]) - int(right[seed, sample_id]) for seed in seeds
        )
        for sample_id in sample_ids
    }
    wins = sum(delta > 0 for delta in block_deltas.values())
    losses = sum(delta < 0 for delta in block_deltas.values())
    ties = len(block_deltas) - wins - losses
    p_value = paired_exact_p(wins, losses)
    return {
        "inference_unit": "held-sample-id-blocked-across-seeds",
        "sample_blocks": len(sample_ids),
        "seeds": seeds,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "two_sided_exact_p": p_value,
        "per_seed_correct_count_deltas": per_seed_deltas,
        "per_seed_direction_3_of_3": per_seed_direction_3_of_3,
        "clears_finite_uncertainty_gate": (
            wins > losses and p_value <= 0.05 and per_seed_direction_3_of_3
        ),
    }


def candidate_has_no_hidden_zero_slices(
    candidate_rows: Sequence[Mapping[str, Any]],
) -> bool:
    """Reject aggregate wins that hide a zero action or sector in any seed."""

    return all(
        float(row["metrics"]["worst_action_accuracy"]) > 0.0
        and bool(row["metrics"]["per_sector_accuracy"])
        and all(
            float(accuracy) > 0.0
            for accuracy in row["metrics"]["per_sector_accuracy"].values()
        )
        for row in candidate_rows
    )


def aggregate(
    rows: Sequence[Mapping[str, Any]], campaign: PrimeScissorCampaignConfig
) -> dict[str, Any]:
    expected = {(arm, seed) for arm in ARMS for seed in campaign.seeds}
    identities = [(str(row["arm"]), int(row["seed"])) for row in rows]
    if len(identities) != len(set(identities)):
        raise RuntimeError("aggregate received duplicate arm/seed horses")
    if set(identities) != expected:
        missing = sorted(expected - set(identities))
        extra = sorted(set(identities) - expected)
        raise RuntimeError(
            f"aggregate horse set differs; missing={missing}, extra={extra}"
        )
    expected_config_hash = stable_hash(asdict(campaign))
    if any(str(row.get("config_hash")) != expected_config_hash for row in rows):
        raise RuntimeError("aggregate received a config-mismatched horse")
    by_arm = {
        arm: sorted(
            (dict(row) for row in rows if row["arm"] == arm),
            key=lambda row: int(row["seed"]),
        )
        for arm in ARMS
    }
    comparisons = {}
    paired = {}
    pooled_diagnostics = {}
    for control in CONTROLS:
        name = f"{PRIMARY}_vs_{control}"
        comparisons[name] = {
            metric: metric_comparison(by_arm[PRIMARY], by_arm[control], metric)
            for metric in ("accuracy", "macro_f1")
        }
        paired[name] = sample_blocked_prediction_comparison(
            by_arm[PRIMARY], by_arm[control]
        )
        pooled_diagnostics[name] = paired_prediction_comparison(
            by_arm[PRIMARY], by_arm[control]
        )
    parameter_counts = {
        int(row["trainable_parameters"]) for values in by_arm.values() for row in values
    }
    retained = all(
        math.isclose(
            float(row["counting_accuracy"]),
            float(row["parent_counting_accuracy"]),
            abs_tol=1e-12,
        )
        and bool(row["base_parent_bit_identical"])
        for values in by_arm.values()
        for row in values
    )
    candidate_used_projection = all(
        int(row["input_receipt"]["projection_nonzero"]) > 0 for row in by_arm[PRIMARY]
    )
    candidate_no_hidden_zeros = candidate_has_no_hidden_zero_slices(by_arm[PRIMARY])
    gate_names = [f"{PRIMARY}_vs_{control}" for control in CONTROLS]
    producer_gate = (
        len(parameter_counts) == 1
        and retained
        and candidate_used_projection
        and candidate_no_hidden_zeros
        and all(
            comparisons[name][metric]["clears_positive_gate"]
            for name in gate_names
            for metric in ("accuracy", "macro_f1")
        )
        and all(paired[name]["clears_finite_uncertainty_gate"] for name in gate_names)
    )
    return {
        "schema": f"{SCHEMA}.result",
        "status": "COMPLETE",
        "authority": AUTHORITY,
        "promotion": "NOT_AUTHORIZED",
        "partial_unfreeze": "NONE",
        "producer_gate": (
            "MET_PENDING_INDEPENDENT_REPLAY" if producer_gate else "NOT_MET"
        ),
        "config": asdict(campaign),
        "learned_parameter_count_matched": len(parameter_counts) == 1,
        "counting_and_base_parent_preserved": retained,
        "candidate_projection_used": candidate_used_projection,
        "candidate_no_hidden_zero_actions_or_sectors": candidate_no_hidden_zeros,
        "comparisons": comparisons,
        "paired_comparisons": paired,
        "seed_prediction_pooled_diagnostics_not_used_for_gate": pooled_diagnostics,
        "per_arm": by_arm,
        "completed_at_utc": utc_now(),
    }


def _status(output: Path, **fields: Any) -> None:
    atomic_json(
        output / "STATUS.json",
        {
            "schema": f"{SCHEMA}.status",
            "status": "RUNNING",
            **fields,
            "updated_at_utc": utc_now(),
        },
    )


def _device_timing_calibration(
    *,
    device: str,
    config_hash: str,
    train_rows: Sequence[ActionTextRow],
    holdout_rows: Sequence[ActionTextRow],
    train_binding: SealedOccurrenceDerangement,
    holdout_binding: SealedOccurrenceDerangement,
) -> dict[str, Any]:
    """Time representative training/evaluation without altering the fixed budget."""

    if len(train_rows) < 128 or len(holdout_rows) < 64:
        raise RuntimeError("device calibration requires representative sealed rows")
    tables = build_feature_tables()
    controls = ["\x00", "\x02", "\x1f", "\x03", "K", " ", ":", "=", ">", *list("01234")]
    vocab = controls + [chr(BYTE_TOKEN_BASE + value) for value in range(256)]
    stoi = {token: index for index, token in enumerate(vocab)}
    configure_determinism(seed=20261118, device=device)
    parent = FrozenActionModel(len(vocab))
    model = ActionGatedPrimeScissorInput(vocab, arm=SHUFFLED, tables=tables).to(device)
    model.load_parent_state(parent.state_dict())
    trainable = set_trainable(model, SHUFFLED)
    optimizer = torch.optim.Adam(trainable, lr=0.002)
    timing_rows = train_rows[:128]
    inputs, labels, masks = make_batch(
        tuple(row.pair() for row in timing_rows), range(128), stoi, device
    )
    owner_mask = feature_owner_mask(
        timing_rows, range(128), input_width=inputs.shape[1], device=device
    )
    timing_kwargs = {
        "feature_owner_mask": owner_mask,
        "sample_ids": [row.sample.sample_id for row in timing_rows],
        "binding": train_binding,
    }
    warmup_steps = 10
    measured_steps = 500
    for _ in range(warmup_steps):
        logits, _ = model(inputs, "action", **timing_kwargs)
        token_loss = nn.functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), labels.reshape(-1), reduction="none"
        ).reshape(labels.shape)
        loss = ((token_loss * masks).sum(dim=1) / masks.sum(dim=1).clamp(min=1)).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    if device == "cuda":
        torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(measured_steps):
        logits, _ = model(inputs, "action", **timing_kwargs)
        token_loss = nn.functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), labels.reshape(-1), reduction="none"
        ).reshape(labels.shape)
        loss = ((token_loss * masks).sum(dim=1) / masks.sum(dim=1).clamp(min=1)).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    if device == "cuda":
        torch.cuda.synchronize()
    train_elapsed = time.perf_counter() - started
    if device == "cuda":
        torch.cuda.synchronize()
    eval_started = time.perf_counter()
    predict_feature_rows(
        model,
        rows=holdout_rows[:64],
        binding=holdout_binding,
        stoi=stoi,
        itos={index: token for token, index in stoi.items()},
        device=device,
    )
    if device == "cuda":
        torch.cuda.synchronize()
    eval_elapsed = time.perf_counter() - eval_started
    seconds_per_step = train_elapsed / measured_steps
    seconds_per_eval_sample = eval_elapsed / 64
    projected_seconds = seconds_per_step * (
        18_000 * len(ARMS) * 3
    ) + seconds_per_eval_sample * (1_500 * len(ARMS) * 3)
    projected_with_margin = projected_seconds * 1.20
    body = {
        "schema": f"{SCHEMA}.device-timing-calibration",
        "status": "PASS",
        "evidence": "MECHANICS_TIMING_ONLY_NO_BUDGET_CHANGE_NO_CAPABILITY_EVIDENCE",
        "config_hash": config_hash,
        "actual_device": device,
        "device_name": (
            torch.cuda.get_device_name(torch.cuda.current_device())
            if device == "cuda"
            else "cpu"
        ),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "timed_arm": SHUFFLED,
        "timing_bound": "shuffled occurrence lookup is the conservative Python-overhead arm",
        "warmup_steps": warmup_steps,
        "measured_steps": measured_steps,
        "representative_batch_size": 128,
        "train_elapsed_seconds": train_elapsed,
        "seconds_per_step": seconds_per_step,
        "measured_eval_samples": 64,
        "eval_elapsed_seconds": eval_elapsed,
        "seconds_per_eval_sample": seconds_per_eval_sample,
        "projected_15_horse_seconds": projected_seconds,
        "projected_15_horse_seconds_with_20_percent_margin": projected_with_margin,
        "maximum_admitted_seconds": 24 * 60 * 60,
        "preregistered_steps_per_horse_unchanged": 18_000,
    }
    receipt = {**body, "receipt_sha256": stable_hash(body)}
    if projected_with_margin > 24 * 60 * 60:
        raise RuntimeError(f"projected campaign exceeds the 24h quota gate: {receipt}")
    return receipt


def _collect_horse_results(
    output: Path,
    campaign: PrimeScissorCampaignConfig,
    *,
    config_hash: str,
    require_complete: bool,
) -> tuple[list[dict[str, Any]], list[tuple[str, int]]]:
    expected = {(arm, seed) for seed in campaign.seeds for arm in ARMS}
    observed: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((output / "horses").glob("*/RESULT.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        identity = (str(result.get("arm")), int(result.get("seed", -1)))
        if identity not in expected:
            raise RuntimeError(f"unexpected horse receipt: {identity} at {path}")
        if identity in observed:
            raise RuntimeError(f"duplicate horse receipt: {identity}")
        if result.get("config_hash") != config_hash:
            raise RuntimeError(f"config-mismatched horse receipt: {identity}")
        model_path = path.with_name("MODEL.pt")
        if not model_path.is_file() or file_sha256(model_path) != result.get(
            "model_sha256"
        ):
            raise RuntimeError(f"horse model receipt mismatch: {identity}")
        observed[identity] = result
    missing = sorted(expected - set(observed))
    if require_complete and missing:
        raise RuntimeError(f"aggregate refuses missing horses: {missing}")
    return [observed[key] for key in sorted(observed)], missing


def run(args: argparse.Namespace) -> dict[str, Any]:
    baseline_run = args.baseline_run.resolve(strict=True)
    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    baseline_result = json.loads(baseline_result_path.read_text(encoding="utf-8"))
    seeds = tuple(int(seed) for seed in baseline_manifest["config"]["seeds"])
    if len(seeds) < 3:
        raise RuntimeError(
            "prime-scissor campaign requires at least three baseline seeds"
        )
    if args.grow_steps != 18_000:
        raise ValueError(
            "the preregistered material budget is exactly 18,000 steps per horse"
        )
    output = args.output_dir.resolve()
    admitted_free_gib = require_storage(output, args.minimum_free_gib)
    preregistration = args.preregistration.resolve(strict=True)
    preflight_receipt_path = args.preflight_receipt.resolve(strict=True)
    preflight_receipt = json.loads(preflight_receipt_path.read_text(encoding="utf-8"))
    provenance = clay_math_provenance(args.clay_math_root)
    actual_device = resolve_device(args.device)
    torch.set_num_threads(args.threads)
    configure_determinism(seed=20261118, device=actual_device)

    runtime_source_dir = args.source_dir.resolve(strict=True)
    provider = ClaySourceAdapter(runtime_source_dir)
    expected_source_hashes = dict(
        sorted(baseline_manifest["config"]["source_hashes"].items())
    )
    actual_source_hashes = dict(sorted(provider.source_hashes.items()))
    if actual_source_hashes != expected_source_hashes:
        raise RuntimeError(
            "hash-verified source-dir remap differs from the sealed baseline source"
        )
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(baseline_manifest["config"]["rows_per_view"]),
        holdout_rows=int(baseline_manifest["config"]["holdout_rows"]),
        seed=int(baseline_manifest["config"]["data_seed"]),
    )
    if not dataset.verify():
        raise RuntimeError(
            "regenerated source-disjoint dataset failed its own verifier"
        )
    dataset_hash = str(dataset.manifest["manifest_sha256"])
    if dataset_hash != baseline_manifest["dataset"]["manifest_sha256"]:
        raise RuntimeError("regenerated dataset differs from the sealed baseline")
    train_binding = build_occurrence_derangement(
        dataset.multiview_rows,
        seed=TRAIN_BINDING_SEED,
        split_name="train",
    )
    holdout_binding = build_occurrence_derangement(
        dataset.holdout_rows,
        seed=HOLDOUT_BINDING_SEED,
        split_name="holdout",
    )
    if set(train_binding.sample_ids) & set(holdout_binding.sample_ids):
        raise RuntimeError("train and holdout occurrence seals overlap sample IDs")
    tables = build_feature_tables()
    conditioning = empirical_conditioning_receipt(tables, dataset)
    feature_receipt_hash = stable_hash(tables.receipt)
    verify_preflight_authority(
        preflight_receipt,
        {
            "dataset_manifest_sha256": dataset_hash,
            "feature_receipt_sha256": feature_receipt_hash,
            "table_sha256": dict(tables.receipt["table_sha256"]),
            "pivot_indices_sha256": tables.receipt["pivot_indices_sha256"],
            "pivot_descriptors_sha256": tables.receipt["pivot_descriptors_sha256"],
            "empirical_conditioning_receipt_sha256": conditioning["receipt_sha256"],
            "train_binding_seal_sha256": train_binding.seal_sha256,
            "train_binding_mapped_sha256": train_binding.mapped_values_sha256,
            "holdout_binding_seal_sha256": holdout_binding.seal_sha256,
            "holdout_binding_mapped_sha256": holdout_binding.mapped_values_sha256,
        },
    )
    runner_path = Path(__file__).resolve(strict=True)
    module_path = runner_path.with_name("clay_prime_scissor_input.py").resolve(
        strict=True
    )
    campaign = PrimeScissorCampaignConfig(
        baseline_run=str(baseline_run),
        baseline_manifest_sha256=file_sha256(baseline_manifest_path),
        baseline_result_sha256=file_sha256(baseline_result_path),
        dataset_manifest_sha256=dataset_hash,
        train_occurrence_binding_sha256=train_binding.seal_sha256,
        holdout_occurrence_binding_sha256=holdout_binding.seal_sha256,
        feature_table_receipt_sha256=feature_receipt_hash,
        runner_sha256=file_sha256(runner_path),
        input_module_sha256=file_sha256(module_path),
        preregistration_sha256=file_sha256(preregistration),
        preflight_receipt_sha256=file_sha256(preflight_receipt_path),
        clay_math_commit=str(provenance["commit"]),
        clay_math_source_hashes=dict(provenance["source_hashes"]),
        seeds=seeds,
        grow_steps=args.grow_steps,
        checkpoint_every=args.checkpoint_every,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        threads=args.threads,
        requested_device=args.device,
        actual_device=actual_device,
        source_dir_authority="cli-remap-verified-by-sealed-source-hashes",
        source_hashes=actual_source_hashes,
    )
    config_hash = stable_hash(asdict(campaign))
    manifest = {
        "schema": f"{SCHEMA}.manifest",
        "config": asdict(campaign),
        "config_hash": config_hash,
        "runner": str(runner_path),
        "runner_sha256": campaign.runner_sha256,
        "input_module": str(module_path),
        "input_module_sha256": campaign.input_module_sha256,
        "preregistration": str(preregistration),
        "preregistration_sha256": campaign.preregistration_sha256,
        "preflight_receipt": str(preflight_receipt_path),
        "preflight_receipt_sha256": campaign.preflight_receipt_sha256,
        "dataset": dict(dataset.manifest),
        "feature_tables": dict(tables.receipt),
        "empirical_conditioning": conditioning,
        "clay_math_provenance": provenance,
        "source_remap": {
            "authority": "cli-remap-verified-by-sealed-source-hashes",
            "source_hashes": actual_source_hashes,
        },
        "train_occurrence_binding": train_binding.metadata(),
        "holdout_occurrence_binding": holdout_binding.metadata(),
        "admitted_free_gib": admitted_free_gib,
        "minimum_free_gib": args.minimum_free_gib,
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "RUN_MANIFEST.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable = dict(existing)
        comparable["admitted_free_gib"] = admitted_free_gib
        if comparable != manifest:
            raise RuntimeError(
                "existing prime-scissor manifest differs; use a new output"
            )
    else:
        atomic_json(manifest_path, manifest)

    calibration_path = output / "TIMING_CALIBRATION.json"
    existing_horse_receipts = list((output / "horses").glob("*/RESULT.json"))
    if not calibration_path.is_file():
        if existing_horse_receipts:
            raise RuntimeError(
                "horse receipts exist without the mandatory device timing calibration"
            )
        atomic_json(
            calibration_path,
            _device_timing_calibration(
                device=actual_device,
                config_hash=config_hash,
                train_rows=dataset.multiview_rows,
                holdout_rows=dataset.holdout_rows,
                train_binding=train_binding,
                holdout_binding=holdout_binding,
            ),
        )
    else:
        calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
        if (
            calibration.get("config_hash") != config_hash
            or calibration.get("actual_device") != actual_device
        ):
            raise RuntimeError("device timing calibration differs from this campaign")

    if args.calibration_only:
        calibration_result = {
            "schema": f"{SCHEMA}.calibration-only-result",
            "status": "CALIBRATION_COMPLETE_NO_HORSES_STARTED",
            "authority": AUTHORITY,
            "config_hash": config_hash,
            "timing_calibration_sha256": file_sha256(calibration_path),
            "horse_artifacts_created_by_this_invocation": False,
            "completed_at_utc": utc_now(),
        }
        atomic_json(output / "STATUS.json", calibration_result)
        return calibration_result

    selected_seeds = tuple(int(seed) for seed in (args.seed or seeds))
    selected_arms = tuple(str(arm) for arm in (args.arm or ARMS))
    if not set(selected_seeds) <= set(seeds):
        raise ValueError("selected seed is not part of the sealed baseline seed set")
    if not set(selected_arms) <= set(ARMS):
        raise ValueError("selected arm is not part of the preregistered arm set")
    jobs = [
        (seed, arm)
        for seed in seeds
        for arm in ARMS
        if seed in selected_seeds and arm in selected_arms
    ]
    if args.max_horses is not None:
        if args.max_horses < 1:
            raise ValueError("max-horses must be positive")
        jobs = jobs[: args.max_horses]
    if args.aggregate_only:
        jobs = []

    parent_results = {
        int(row["seed"]): row for row in baseline_result.get("parents", [])
    }
    for seed in sorted({seed for seed, _arm in jobs}):
        parent_dir = baseline_run / "parents" / f"seed-{seed}"
        parent_path = parent_dir / "PARENT.pt"
        parent_result = parent_results.get(seed)
        if parent_result is None:
            parent_result = json.loads(
                (parent_dir / "RESULT.json").read_text(encoding="utf-8")
            )
        if file_sha256(parent_path) != parent_result["parent_sha256"]:
            raise RuntimeError(f"baseline parent hash differs for seed {seed}")
        parent = torch.load(parent_path, map_location="cpu", weights_only=False)
        for arm in (arm for candidate_seed, arm in jobs if candidate_seed == seed):
            _status(output, seed=seed, stage=arm)
            result = train_arm(
                arm=arm,
                seed=seed,
                output=output,
                campaign=campaign,
                baseline_manifest=baseline_manifest,
                parent=parent,
                parent_result=parent_result,
                dataset=dataset,
                tables=tables,
                train_binding=train_binding,
                holdout_binding=holdout_binding,
                config_hash=config_hash,
            )
            print(
                f"{arm:32s} seed={seed} accuracy={result['metrics']['accuracy']:.6f} "
                f"macro_f1={result['metrics']['macro_f1']:.6f} count={result['counting_accuracy']:.6f}",
                flush=True,
            )
    learned, missing = _collect_horse_results(
        output,
        campaign,
        config_hash=config_hash,
        require_complete=args.aggregate_only,
    )
    if missing:
        partial = {
            "schema": f"{SCHEMA}.staged-result",
            "status": "STAGED_PARTIAL",
            "authority": AUTHORITY,
            "config_hash": config_hash,
            "complete_horses": len(learned),
            "expected_horses": len(ARMS) * len(seeds),
            "missing_horses": [list(identity) for identity in missing],
            "completed_at_utc": utc_now(),
        }
        atomic_json(output / "STATUS.json", partial)
        return partial

    result = aggregate(learned, campaign)
    atomic_json(output / "RESULT.json", result)
    atomic_json(
        output / "STATUS.json",
        {
            "schema": f"{SCHEMA}.status",
            "status": "COMPLETE",
            "result_sha256": file_sha256(output / "RESULT.json"),
            "updated_at_utc": utc_now(),
        },
    )
    return result


def _preflight_rows(split: str) -> tuple[ActionTextRow, ...]:
    rows = []
    for label in range(5):
        torch.manual_seed(900 + label + (100 if split == "holdout" else 0))
        prompt = action_prompt(torch.randn(37, dtype=torch.float32))
        rows.append(
            ActionTextRow(
                sample=ExposureSample(
                    sample_id=f"{split}-sample-{label}",
                    payload_sha256=stable_hash({"split": split, "prompt": prompt}),
                    concept_id=f"sector-{label}",
                    variant_id=f"variant-{split}-{label}",
                    source_family=f"preflight-{split}",
                    split=split,
                    operation_id=f"action-{label}",
                    view_id=f"preflight-{split}",
                ),
                prompt=prompt,
                target=str(label),
                label=label,
                sector=label,
            )
        )
    return tuple(rows)


def run_mechanics_preflight() -> dict[str, Any]:
    """Run 3x5 single-step synthetic mechanics checks; never capability evidence."""

    train_rows = _preflight_rows("train")
    holdout_rows = _preflight_rows("holdout")
    train_binding = build_occurrence_derangement(
        train_rows, seed=TRAIN_BINDING_SEED, split_name="preflight-train"
    )
    holdout_binding = build_occurrence_derangement(
        holdout_rows, seed=HOLDOUT_BINDING_SEED, split_name="preflight-holdout"
    )
    tables = build_feature_tables()
    controls = ["\x00", "\x02", "\x1f", "\x03", "K", " ", ":", "=", ">", *list("01234")]
    vocab = controls + [chr(BYTE_TOKEN_BASE + value) for value in range(256)]
    stoi = {token: index for index, token in enumerate(vocab)}
    pairs = tuple(row.pair() for row in train_rows)
    parameter_counts: set[int] = set()
    records = []
    for seed in (101, 102, 103):
        torch.manual_seed(seed)
        parent = FrozenActionModel(len(vocab))
        parent_state = parent.state_dict()
        for arm in ARMS:
            torch.manual_seed(seed + ARM_SEED_OFFSET)
            model = ActionGatedPrimeScissorInput(vocab, arm=arm, tables=tables)
            model.load_parent_state(parent_state)
            before = frozen_state(model)
            trainable = set_trainable(model, arm)
            parameter_counts.add(sum(parameter.numel() for parameter in trainable))
            inputs, labels, masks = make_batch(
                pairs, range(len(train_rows)), stoi, "cpu"
            )
            kwargs: dict[str, Any] = {
                "feature_owner_mask": feature_owner_mask(
                    train_rows,
                    range(len(train_rows)),
                    input_width=inputs.shape[1],
                    device="cpu",
                )
            }
            if arm == SHUFFLED:
                kwargs.update(
                    {
                        "sample_ids": [row.sample.sample_id for row in train_rows],
                        "binding": train_binding,
                    }
                )
            logits, _ = model(inputs, "action", **kwargs)
            token_loss = nn.functional.cross_entropy(
                logits.reshape(-1, logits.shape[-1]),
                labels.reshape(-1),
                reduction="none",
            ).reshape(labels.shape)
            loss = (
                (token_loss * masks).sum(dim=1) / masks.sum(dim=1).clamp(min=1)
            ).mean()
            optimizer = torch.optim.Adam(trainable, lr=0.002)
            optimizer.zero_grad()
            loss.backward()
            gradient = model.feature_projection.weight.grad
            gradient_nonzero = (
                gradient is not None and int(torch.count_nonzero(gradient).item()) > 0
            )
            optimizer.step()
            records.append(
                {
                    "seed": seed,
                    "arm": arm,
                    "loss": float(loss.detach()),
                    "projection_gradient_nonzero": gradient_nonzero,
                    "projection_nonzero_after_step": int(
                        torch.count_nonzero(model.feature_projection.weight).item()
                    ),
                    "parent_preserved": frozen_state_identical(before, model),
                }
            )
    if len(parameter_counts) != 1:
        raise RuntimeError("preflight learned parameter counts differ")
    if not all(row["parent_preserved"] for row in records):
        raise RuntimeError("preflight changed a frozen parent tensor")
    if not all(
        row["projection_gradient_nonzero"]
        for row in records
        if row["arm"] != "no_intervention_matched"
    ):
        raise RuntimeError(
            "a non-null preflight arm did not reach its pre-GRU projection"
        )
    if any(
        row["projection_gradient_nonzero"]
        for row in records
        if row["arm"] == "no_intervention_matched"
    ):
        raise RuntimeError(
            "no-intervention preflight unexpectedly activated its projection"
        )
    body = {
        "schema": f"{SCHEMA}.mechanics-preflight",
        "status": "PASS",
        "evidence": "SYNTHETIC_MECHANICS_ONLY_NOT_CAPABILITY_EVIDENCE",
        "seeds": [101, 102, 103],
        "arms": list(ARMS),
        "trainable_parameters": parameter_counts.pop(),
        "feature_table_receipt_sha256": stable_hash(tables.receipt),
        "train_binding_seal_sha256": train_binding.seal_sha256,
        "holdout_binding_seal_sha256": holdout_binding.seal_sha256,
        "records": records,
    }
    return {**body, "receipt_sha256": stable_hash(body)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--preflight-receipt", type=Path, required=True)
    parser.add_argument("--clay-math-root", type=Path, required=True)
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Runtime Clay source remap; file hashes must match the sealed baseline.",
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--arm", action="append", choices=ARMS)
    parser.add_argument("--seed", action="append", type=int)
    parser.add_argument("--max-horses", type=int)
    execution = parser.add_mutually_exclusive_group()
    execution.add_argument("--calibration-only", action="store_true")
    execution.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--grow-steps", type=int, default=18_000)
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.002)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument(
        "--minimum-free-gib", type=float, default=DEFAULT_MINIMUM_FREE_GIB
    )
    parser.add_argument("--mechanics-preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mechanics_preflight:
        print(json.dumps(run_mechanics_preflight(), indent=2, sort_keys=True))
        return 0
    result = run(args)
    print(
        json.dumps(
            {
                "status": result["status"],
                "producer_gate": result.get("producer_gate", "NOT_EVALUATED"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
