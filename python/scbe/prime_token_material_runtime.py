"""Hash-bound material runtime for the frozen prime-token horse race.

This module is intentionally inert until called by the separately gated runner.
It loads the recovered full-system parent read-only, converts a prepared and
source-disjoint case manifest into typed packets, and owns held evaluation.
It never authorizes training, promotion, unfreezing, serving, or tool dispatch.
"""

from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from .prime_token_input_access import (
    CONTROL_MODES,
    FullSystemPrimeTokenInputAccessLM,
    PrimeTokenRecord,
    build_prime_token_batch,
)
from .prime_token_training import (
    PrimeTrainingExample,
    canonical_sha256,
    module_state_sha256,
    sha256_file,
    validate_training_examples,
)

RUNTIME_SCHEMA = "scbe.prime-token-material-runtime.v1"
CASE_MANIFEST_SCHEMA = "scbe.prime-token-material-cases.v1"
EVALUATOR_RECEIPT_SCHEMA = "scbe.prime-token-evaluator-receipt.v1"
PARENT_CHECKPOINT_SCHEMA = "clay.full-system-pretrain.checkpoint.v1"
HELD_SPLITS = ("validation", "final_test")
CASE_LANES = ("train", *HELD_SPLITS, "ordinary", "retention")


def _object_file(path_value: object, expected_sha256: object, *, label: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(path_value, str) or not Path(path_value).is_absolute():
        raise ValueError(f"{label} path must be absolute")
    path = Path(path_value).resolve(strict=True)
    if not isinstance(expected_sha256, str) or sha256_file(path) != expected_sha256:
        raise RuntimeError(f"{label} hash differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{label} must contain one JSON object")
    return path, value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"{path}:{line_number} must contain a JSON object")
            rows.append(value)
    return rows


def _manifest_lane(root: Path, descriptor: object, *, lane: str) -> list[dict[str, Any]]:
    if not isinstance(descriptor, dict):
        raise ValueError(f"case manifest omitted {lane}")
    relative = descriptor.get("path")
    expected_hash = descriptor.get("sha256")
    expected_count = descriptor.get("count")
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"case manifest {lane} path is invalid")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError(f"case manifest {lane} path escapes its directory")
    if not isinstance(expected_hash, str) or sha256_file(path) != expected_hash:
        raise RuntimeError(f"case manifest {lane} hash differs")
    rows = _load_jsonl(path)
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or len(rows) != expected_count:
        raise RuntimeError(f"case manifest {lane} count differs")
    return rows


def _record(value: object, *, source_family: str) -> PrimeTokenRecord:
    if not isinstance(value, dict):
        raise TypeError("prime-token record must be an object")
    record = PrimeTokenRecord(
        canonical_id=str(value.get("canonical_id") or ""),
        section_id=str(value.get("section_id") or ""),
        source_family=str(value.get("source_family") or ""),
        views=value.get("views") if isinstance(value.get("views"), dict) else {},
    )
    record.validate()
    if record.source_family != source_family:
        raise ValueError("case and prime-token record source families differ")
    return record


def _int_tuple(value: object, *, label: str, nonempty: bool = True) -> tuple[int, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label} must be a{' non-empty' if nonempty else ''} list")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise TypeError(f"{label} must contain integers")
    return tuple(value)


def _case_parts(row: Mapping[str, Any], *, expected_split: str) -> dict[str, Any]:
    split = str(row.get("split") or "")
    if split != expected_split:
        raise ValueError("case split differs from its manifest lane")
    record_id = str(row.get("record_id") or "")
    source_family = str(row.get("source_family") or "")
    if not record_id or not source_family:
        raise ValueError("case requires record and source-family identities")
    token_ids = _int_tuple(row.get("token_ids"), label="token_ids")
    targets = _int_tuple(row.get("targets"), label="targets")
    if len(targets) != len(token_ids):
        raise ValueError("case targets differ from token IDs")
    owner_positions = _int_tuple(row.get("owner_positions"), label="owner_positions")
    output_positions = _int_tuple(row.get("output_positions"), label="output_positions")
    records_raw = row.get("records")
    if not isinstance(records_raw, list) or len(records_raw) != len(owner_positions):
        raise ValueError("case records differ from owner positions")
    records = tuple(_record(value, source_family=source_family) for value in records_raw)
    return {
        "record_id": record_id,
        "source_family": source_family,
        "split": split,
        "token_ids": token_ids,
        "targets": targets,
        "owner_positions": owner_positions,
        "output_positions": output_positions,
        "records": records,
    }


def _load_parent(config: Mapping[str, Any]) -> nn.Module:
    parent = config.get("parent")
    if not isinstance(parent, dict):
        raise ValueError("runtime config omitted its parent descriptor")
    source_root = Path(str(parent.get("source_root") or ""))
    checkpoint = Path(str(parent.get("checkpoint") or ""))
    if not source_root.is_absolute() or not checkpoint.is_absolute():
        raise ValueError("parent source and checkpoint paths must be absolute")
    source_root = source_root.resolve(strict=True)
    checkpoint = checkpoint.resolve(strict=True)
    model_source = (source_root / "full_system_pretrain" / "model.py").resolve(strict=True)
    if sha256_file(model_source) != parent.get("model_source_sha256"):
        raise RuntimeError("full-system model source hash differs")
    if sha256_file(checkpoint) != parent.get("checkpoint_sha256"):
        raise RuntimeError("full-system parent checkpoint hash differs")
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    importlib.invalidate_caches()
    model_module = importlib.import_module("full_system_pretrain.model")
    if Path(str(model_module.__file__)).resolve() != model_source:
        raise RuntimeError("full-system model import resolved to another source tree")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False, mmap=True)
    if payload.get("schema") != PARENT_CHECKPOINT_SCHEMA:
        raise RuntimeError("full-system parent checkpoint schema changed")
    full_config = payload.get("config")
    state = payload.get("model")
    if not isinstance(full_config, dict) or not isinstance(full_config.get("model"), dict):
        raise RuntimeError("full-system parent lacks its model configuration")
    if canonical_sha256(full_config) != payload.get("config_sha256"):
        raise RuntimeError("full-system parent configuration hash differs")
    if not isinstance(state, dict) or "input.feature_table" not in state:
        raise RuntimeError("full-system parent state lacks the STISTA feature table")
    model_config = model_module.FullSystemConfig.from_dict(full_config["model"])
    model = model_module.FullSystemLM(model_config, state["input.feature_table"])
    model.load_state_dict(state, strict=True)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model


def _class_map(value: object, *, allowed: set[int], label: str) -> dict[int, str]:
    if not isinstance(value, dict):
        raise ValueError(f"case manifest omitted {label}")
    result = {int(token): str(group) for token, group in value.items()}
    if set(result) != allowed or any(not group for group in result.values()):
        raise ValueError(f"{label} must classify every allowed output token exactly once")
    return result


def _ordinary_tokens(row: Mapping[str, Any], *, lane: str) -> tuple[str, Tensor]:
    identity = str(row.get("id") or "")
    if not identity:
        raise ValueError(f"{lane} row requires an identity")
    token_ids = _int_tuple(row.get("token_ids"), label=f"{lane}.token_ids")
    return identity, torch.tensor([token_ids], dtype=torch.long)


def _metric_mean(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    return sum(float(row[key]) for row in rows) / len(rows)


def build_runtime(config: Mapping[str, Any]) -> dict[str, object]:
    """Build one deterministic arm/seed runtime after the runner releases it."""

    if config.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("runtime config schema changed")
    arm = str(config.get("arm") or "")
    seed = config.get("seed")
    if arm not in {"no_intervention", *CONTROL_MODES}:
        raise ValueError("runtime config names an unknown arm")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("runtime seed must be an integer")
    source_path, _source_manifest = _object_file(
        config.get("source_manifest"), config.get("source_manifest_sha256"), label="source manifest"
    )
    split_path, _split_manifest = _object_file(
        config.get("split_manifest"), config.get("split_manifest_sha256"), label="split manifest"
    )
    cases_path, cases_manifest = _object_file(
        config.get("cases_manifest"), config.get("cases_manifest_sha256"), label="case manifest"
    )
    if cases_manifest.get("schema") != CASE_MANIFEST_SCHEMA:
        raise ValueError("case manifest schema changed")
    if cases_manifest.get("source_disjoint") is not True:
        raise ValueError("case manifest is not source-disjoint")
    evaluator_receipt = str(cases_manifest.get("exact_evaluator_receipt_sha256") or "")
    if len(evaluator_receipt) != 64 or any(character not in "0123456789abcdef" for character in evaluator_receipt):
        raise ValueError("case manifest evaluator receipt is invalid")
    files = cases_manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(CASE_LANES):
        raise ValueError("case manifest does not contain the exact required lanes")
    lane_rows = {lane: _manifest_lane(cases_path.parent, files[lane], lane=lane) for lane in CASE_LANES}
    if not lane_rows["train"] or not lane_rows["validation"] or not lane_rows["final_test"]:
        raise ValueError("case manifest contains an empty train or held lane")
    allowed = set(_int_tuple(cases_manifest.get("allowed_output_token_ids"), label="allowed output token IDs"))
    if len(allowed) != len(cases_manifest["allowed_output_token_ids"]) or min(allowed) < 0:
        raise ValueError("allowed output token IDs are duplicated or negative")
    relationship_classes = _class_map(
        cases_manifest.get("relationship_class_by_token_id"), allowed=allowed, label="relationship classes"
    )
    function_classes = _class_map(
        cases_manifest.get("function_class_by_token_id"), allowed=allowed, label="function classes"
    )
    evaluator_path, evaluator_spec = _object_file(
        config.get("evaluator_receipt"),
        config.get("evaluator_receipt_sha256"),
        label="evaluator receipt",
    )
    if sha256_file(evaluator_path) != evaluator_receipt:
        raise RuntimeError("case manifest names another evaluator receipt")
    expected_evaluator_spec = {
        "schema": EVALUATOR_RECEIPT_SCHEMA,
        "allowed_output_token_ids": sorted(allowed),
        "relationship_class_by_token_id": {str(key): relationship_classes[key] for key in sorted(allowed)},
        "function_class_by_token_id": {str(key): function_classes[key] for key in sorted(allowed)},
        "scoring": "full-vocabulary-argmax_then_exact_and_class_equivalence",
    }
    if evaluator_spec != expected_evaluator_spec:
        raise RuntimeError("evaluator receipt does not exactly bind the declared scoring map")

    prepared = {
        lane: [_case_parts(row, expected_split=lane) for row in lane_rows[lane]] for lane in ("train", *HELD_SPLITS)
    }
    family_sets = {lane: {case["source_family"] for case in prepared[lane]} for lane in ("train", *HELD_SPLITS)}
    record_sets = {lane: {case["record_id"] for case in prepared[lane]} for lane in ("train", *HELD_SPLITS)}
    for index, left in enumerate(("train", *HELD_SPLITS)):
        for right in ("train", *HELD_SPLITS)[index + 1 :]:
            if family_sets[left] & family_sets[right] or record_sets[left] & record_sets[right]:
                raise ValueError(f"runtime cases overlap source families or record IDs: {left}/{right}")

    packet_mode = "canonical_six_view_reader" if arm == "no_intervention" else arm
    single_frame = str(config.get("single_frame") or "lexical")
    examples: dict[str, list[PrimeTrainingExample]] = {lane: [] for lane in ("train", *HELD_SPLITS)}
    replay_cases: list[dict[str, object]] = []
    for lane in ("train", *HELD_SPLITS):
        binding_pool = [record for case in prepared[lane] for record in case["records"]]
        for case in prepared[lane]:
            token_ids = torch.tensor([case["token_ids"]], dtype=torch.long)
            targets = torch.tensor([case["targets"]], dtype=torch.long)
            packet = build_prime_token_batch(
                [case["records"]],
                [case["owner_positions"]],
                sequence_length=token_ids.shape[1],
                mode=packet_mode,
                frame=single_frame,
                binding_pool=binding_pool if packet_mode == "shuffled_binding_reader" else None,
            )
            weights = torch.zeros_like(token_ids, dtype=torch.float32)
            weights[0, list(case["output_positions"])] = 1.0
            example = PrimeTrainingExample(
                record_ids=(case["record_id"],),
                splits=(lane,),
                source_families=(case["source_family"],),
                token_ids=token_ids,
                targets=targets,
                weights=weights,
                packet=packet,
                output_positions=(case["output_positions"],),
                allowed_output_token_ids=tuple(sorted(allowed)),
                exact_evaluator_receipt_sha256=evaluator_receipt,
            )
            example.validate()
            examples[lane].append(example)
            if lane in HELD_SPLITS:
                replay_cases.append(
                    {
                        "records": [list(case["records"])],
                        "owner_positions": [list(case["owner_positions"])],
                        "sequence_length": token_ids.shape[1],
                        "mode": packet_mode,
                        "frame": single_frame,
                        "binding_pool": binding_pool if packet_mode == "shuffled_binding_reader" else None,
                        "token_ids": token_ids.tolist(),
                        "targets": targets.tolist(),
                        "record_ids": [case["record_id"]],
                        "splits": [lane],
                        "source_families": [case["source_family"]],
                        "output_positions": [list(case["output_positions"])],
                        "allowed_output_token_ids": sorted(allowed),
                        "exact_evaluator_receipt_sha256": evaluator_receipt,
                    }
                )
    validate_training_examples(examples["train"])

    torch.manual_seed(seed)
    core = _load_parent(config)
    model = FullSystemPrimeTokenInputAccessLM(core, reader_rank=int(config.get("reader_rank", 32)))
    parent_sha256 = module_state_sha256(core)
    identity = {
        "arm": arm,
        "seed": str(seed),
        "parent_sha256": parent_sha256,
        "source_manifest_sha256": sha256_file(source_path),
        "split_manifest_sha256": sha256_file(split_path),
        "cases_manifest_sha256": sha256_file(cases_path),
        "evaluator_receipt_sha256": evaluator_receipt,
    }
    ordinary = [_ordinary_tokens(row, lane="ordinary") for row in lane_rows["ordinary"]]
    retention = [_ordinary_tokens(row, lane="retention") for row in lane_rows["retention"]]

    @torch.no_grad()
    def evaluate(current_model: FullSystemPrimeTokenInputAccessLM, current_arm: str) -> dict[str, object]:
        if current_arm != arm or module_state_sha256(current_model.core) != parent_sha256:
            raise RuntimeError("evaluator lineage differs from its runtime")
        device = next(current_model.parameters()).device
        current_model.eval()
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        tracemalloc.start()
        started = time.perf_counter()
        outcomes: list[dict[str, object]] = []
        for lane in HELD_SPLITS:
            for example in examples[lane]:
                token_ids = example.token_ids.to(device)
                packet = example.packet if arm != "no_intervention" else None
                logits = current_model(token_ids, prime_packet=packet)
                if max(allowed) >= logits.shape[-1]:
                    raise ValueError("allowed output token exceeds model vocabulary")
                bounded = logits[..., sorted(allowed)]
                predictions = logits.argmax(dim=-1).cpu()
                for position in example.output_positions[0]:
                    prediction = int(predictions[0, position])
                    target = int(example.targets[0, position])
                    probabilities = torch.softmax(bounded[0, position].float(), dim=-1)
                    top = torch.topk(probabilities, k=min(2, probabilities.numel())).values
                    margin = float(top[0] - top[1]) if top.numel() == 2 else float(top[0])
                    entropy = float((-(probabilities * probabilities.clamp_min(1e-12).log())).sum().item())
                    outcomes.append(
                        {
                            "id": f"{example.record_ids[0]}:{position}",
                            "record_id": example.record_ids[0],
                            "split": lane,
                            "source_family": example.source_families[0],
                            "prediction": prediction,
                            "target": target,
                            "accuracy": float(prediction == target),
                            "relationship": float(relationship_classes.get(prediction) == relationship_classes[target]),
                            "function": float(function_classes.get(prediction) == function_classes[target]),
                            "bounded_margin": margin,
                            "bounded_entropy": entropy,
                        }
                    )
        elapsed = max(time.perf_counter() - started, 1e-12)
        false_activations = 0
        for _identity, token_ids in ordinary:
            result = current_model(token_ids.to(device), return_prime_meta=True)
            meta = result[-1] if isinstance(result, tuple) else {}
            false_activations += int(bool(meta.get("prime_packet_used")) or bool(meta.get("false_activation")))
        retained = 0
        for _identity, token_ids in retention:
            values = token_ids.to(device)
            retained += int(torch.equal(current_model(values), current_model.core(values)))
        _current_bytes, peak_cpu = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_memory = float(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else float(peak_cpu)
        metrics = {
            "accuracy": _metric_mean(outcomes, "accuracy"),
            "relationship": _metric_mean(outcomes, "relationship"),
            "function": _metric_mean(outcomes, "function"),
            "ordinary_false_activation": false_activations / len(ordinary) if ordinary else 0.0,
            "frozen_parent_retention": retained / len(retention) if retention else 1.0,
            "throughput": len(outcomes) / elapsed,
            "peak_memory": peak_memory,
            "bounded_margin": _metric_mean(outcomes, "bounded_margin"),
            "bounded_entropy": _metric_mean(outcomes, "bounded_entropy"),
        }
        if not all(math.isfinite(float(value)) for value in metrics.values()):
            raise RuntimeError("evaluator produced a non-finite metric")
        return {
            "metrics": metrics,
            "per_example": outcomes,
            "evaluator_receipt_sha256": evaluator_receipt,
        }

    return {
        "model": model,
        "train_examples": examples["train"],
        "identity": identity,
        "evaluate": evaluate,
        "replay_cases": replay_cases,
        "runtime_receipt_sha256": canonical_sha256(identity),
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


__all__ = [
    "CASE_MANIFEST_SCHEMA",
    "EVALUATOR_RECEIPT_SCHEMA",
    "RUNTIME_SCHEMA",
    "build_runtime",
]
