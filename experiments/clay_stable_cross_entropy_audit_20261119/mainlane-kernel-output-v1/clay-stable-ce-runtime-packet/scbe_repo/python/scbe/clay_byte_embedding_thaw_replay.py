"""Independent final inference replay for the byte-embedding thaw campaign.

This verifier intentionally does not import the thaw producer or its model. It
rebuilds the source-disjoint dataset through the already independent frozen
replay path, declares the shadow-byte model again, opens only terminal model
artifacts, and recomputes the producer's measurements. The resulting evidence
cannot authorize execution, promotion, merging, or partial unfreezing.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn

from python.scbe import clay_frozen_multiview_replay as frozen_replay
from python.scbe.clay_paired_orbit_training import ClaySourceAdapter


SCHEMA = "clay.byte-embedding-thaw-independent-replay.v1"
LEDGER_SCHEMA = "clay.byte-embedding-thaw-independent-prediction-ledger.v1"
AUTHORITY = {
    "training": "NONE",
    "execution": "NONE",
    "merge": "NONE",
    "promotion": "NONE",
    "partial_unfreeze": "NONE",
}
THAW_ARMS = (
    "byte_thaw_multiview",
    "byte_thaw_static",
    "byte_thaw_sample_shuffled",
)
IMPORTED_CONTROLS = (
    "frozen_adapter_multiview",
    "no_intervention_adapter",
)
ALL_ARMS = THAW_ARMS + IMPORTED_CONTROLS
PRIMARY = "byte_thaw_multiview"
SHUFFLED = "byte_thaw_sample_shuffled"
STATIC = "byte_thaw_static"
GATE_CONTROLS = ("frozen_adapter_multiview", SHUFFLED)
BYTE_COUNT = 256
BYTE_TOKEN_BASE = 0xE100
FROZEN_PREFIXES = ("e.", "g.", "count_head.")
TRAINABLE_KEYS = (
    "adapter.down.weight",
    "adapter.down.bias",
    "adapter.mid.weight",
    "adapter.mid.bias",
    "adapter.up.weight",
    "adapter.up.bias",
    "adapter_head.weight",
    "adapter_head.bias",
)
WEIGHT_EFFECT_SCHEMA = "scbe.weight-effect-receipt.v1"
WEIGHT_EFFECT_TOLERANCE = 1e-4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def sample_local_byte_shuffle(
    row: frozen_replay.ReplayActionRow, *, seed: int
) -> frozen_replay.ReplayActionRow:
    """Rebuild the producer's per-sample byte bijection without importing it."""

    if not row.prompt.startswith("K :") or not row.prompt.endswith(" =>"):
        raise ValueError("unexpected action prompt frame")
    body = row.prompt[3:-3]
    values = [ord(token) - BYTE_TOKEN_BASE for token in body]
    if any(value not in range(BYTE_COUNT) for value in values):
        raise ValueError("action prompt contains a non-byte carrier token")
    digest = hashlib.sha256(
        f"{seed}:{row.sample.sample_id}".encode("utf-8")
    ).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    permutation = list(range(BYTE_COUNT))
    rng.shuffle(permutation)
    if sorted(permutation) != list(range(BYTE_COUNT)):
        raise AssertionError("shuffle is not bijective")
    remapped = "".join(
        chr(BYTE_TOKEN_BASE + permutation[value]) for value in values
    )
    return replace(row, prompt=f"K :{remapped} =>")


def sample_local_byte_shuffle_rows(
    rows: Sequence[frozen_replay.ReplayActionRow], *, seed: int
) -> tuple[frozen_replay.ReplayActionRow, ...]:
    return tuple(sample_local_byte_shuffle(row, seed=seed) for row in rows)


class ReplayByteThawModel(nn.Module):
    """Separate declaration of the action-gated byte-shadow network."""

    def __init__(self, vocab: Sequence[str]) -> None:
        super().__init__()
        self.e = nn.Embedding(len(vocab), 64, padding_idx=0)
        self.g = nn.GRU(64, 192, 2, batch_first=True)
        self.adapter = frozen_replay.ReplayAdapter()
        self.count_head = nn.Linear(192, len(vocab))
        self.adapter_head = nn.Linear(192, len(vocab))
        token_to_id = {token: index for index, token in enumerate(vocab)}
        ids = []
        for value in range(BYTE_COUNT):
            token = chr(BYTE_TOKEN_BASE + value)
            if token not in token_to_id:
                raise ValueError(f"vocabulary is missing byte token {value}")
            ids.append(token_to_id[token])
        byte_token_ids = torch.tensor(ids, dtype=torch.long)
        byte_lookup = torch.full((len(vocab),), -1, dtype=torch.long)
        byte_lookup[byte_token_ids] = torch.arange(BYTE_COUNT, dtype=torch.long)
        self.register_buffer("byte_token_ids", byte_token_ids, persistent=False)
        self.register_buffer("byte_lookup", byte_lookup, persistent=False)
        self.thawed_byte_rows = nn.Parameter(torch.empty(BYTE_COUNT, 64))

    def _embed(self, inputs: Tensor, *, head: str) -> Tensor:
        embedded = self.e(inputs)
        if head != "action":
            return embedded
        byte_indices = self.byte_lookup[inputs]
        active = byte_indices >= 0
        replacements = self.thawed_byte_rows[byte_indices.clamp(min=0)]
        return torch.where(active.unsqueeze(-1), replacements, embedded)

    def forward(
        self,
        inputs: Tensor,
        *,
        head: str,
        null_carrier: bool,
        state: Any = None,
    ) -> tuple[Tensor, Any]:
        core_state = state[0] if isinstance(state, tuple) else state
        hidden, core_state = self.g(self._embed(inputs, head=head), core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        carrier = torch.ones_like(hidden) if null_carrier else hidden
        return self.adapter_head(self.adapter(carrier)), (core_state, None)


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _weight_effect_receipt(initial: np.ndarray, final: np.ndarray) -> dict[str, Any]:
    before = np.asarray(initial)
    after = np.asarray(final)
    if before.shape != after.shape or before.dtype != after.dtype:
        raise ValueError("weight arrays must have identical shape and dtype")
    if not np.all(np.isfinite(before)) or not np.all(np.isfinite(after)):
        raise ValueError("weight arrays must be finite")
    delta = np.asarray(after - before)
    receipt: dict[str, Any] = {
        "schema": WEIGHT_EFFECT_SCHEMA,
        "shape": list(before.shape),
        "dtype": str(before.dtype),
        "initial_sha256": _array_sha256(before),
        "final_sha256": _array_sha256(after),
        "delta_l2": float(np.linalg.norm(delta)),
        "delta_linf": float(np.max(np.abs(delta))) if delta.size else 0.0,
        "changed_scalars": int(np.count_nonzero(delta)),
        "scalar_count": int(delta.size),
    }
    receipt["receipt_sha256"] = hashlib.sha256(
        json.dumps(
            receipt,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return receipt


def _flatten(values: Sequence[Tensor]) -> np.ndarray:
    return np.concatenate(
        [value.detach().cpu().numpy().reshape(-1) for value in values]
    ).astype(np.float32, copy=False)


def audit_thaw_state(
    parent_state: Mapping[str, Tensor],
    candidate_state: Mapping[str, Tensor],
    vocab: Sequence[str],
) -> dict[str, Any]:
    """Check the exact thaw surface and independently recompute its receipts."""

    parent_keys = set(parent_state)
    candidate_keys = set(candidate_state)
    expected_keys = parent_keys | {"thawed_byte_rows"}
    state_keys_exact = candidate_keys == expected_keys
    frozen_keys = sorted(
        key for key in parent_keys if key.startswith(FROZEN_PREFIXES)
    )
    frozen_bit_identical = state_keys_exact and all(
        torch.equal(parent_state[key], candidate_state[key]) for key in frozen_keys
    )
    token_to_id = {token: index for index, token in enumerate(vocab)}
    byte_ids = [token_to_id[chr(BYTE_TOKEN_BASE + value)] for value in range(BYTE_COUNT)]
    original_rows = parent_state["e.weight"][byte_ids].detach().cpu()
    thawed_rows = candidate_state.get("thawed_byte_rows")
    thaw_shape_valid = isinstance(thawed_rows, Tensor) and tuple(thawed_rows.shape) == (
        BYTE_COUNT,
        64,
    )
    if not thaw_shape_valid:
        changed_rows = -1
    else:
        changed_rows = int(
            torch.ne(original_rows, thawed_rows.detach().cpu()).any(dim=1).sum()
        )
    trainable_keys_present = all(
        key in parent_state and key in candidate_state for key in TRAINABLE_KEYS
    )
    weight_effect = None
    if trainable_keys_present and thaw_shape_valid:
        initial = _flatten(
            [*(parent_state[key] for key in TRAINABLE_KEYS), original_rows]
        )
        final = _flatten(
            [
                *(candidate_state[key] for key in TRAINABLE_KEYS),
                candidate_state["thawed_byte_rows"],
            ]
        )
        weight_effect = _weight_effect_receipt(initial, final)
    thaw_receipt = {
        "schema": "clay.action-gated-byte-embedding-thaw.v1",
        "action_gated": True,
        "byte_rows": BYTE_COUNT,
        "embedding_width": 64,
        "trainable_byte_scalars": BYTE_COUNT * 64,
        "changed_byte_rows": changed_rows,
        "count_path_uses_parent_embedding": True,
    }
    return {
        "state_keys_exact": state_keys_exact,
        "unexpected_state_keys": sorted(candidate_keys - expected_keys),
        "missing_state_keys": sorted(expected_keys - candidate_keys),
        "frozen_tensor_keys": frozen_keys,
        "frozen_tensors_bit_identical": frozen_bit_identical,
        "thaw_shape_valid": thaw_shape_valid,
        "changed_byte_rows": changed_rows,
        "thaw_receipt": thaw_receipt,
        "weight_effect": weight_effect,
        "trainable_parameters": int(weight_effect["scalar_count"])
        if weight_effect is not None
        else None,
    }


def compare_weight_effect(
    independent: Mapping[str, Any] | None,
    recorded: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if independent is None or recorded is None:
        return {"pass": False, "reason": "missing weight-effect receipt"}
    exact_fields = (
        "schema",
        "shape",
        "dtype",
        "initial_sha256",
        "final_sha256",
        "changed_scalars",
        "scalar_count",
        "receipt_sha256",
    )
    exact = all(independent.get(key) == recorded.get(key) for key in exact_fields)
    l2_delta = abs(float(independent["delta_l2"]) - float(recorded["delta_l2"]))
    linf_delta = abs(
        float(independent["delta_linf"]) - float(recorded["delta_linf"])
    )
    return {
        "pass": exact
        and l2_delta <= WEIGHT_EFFECT_TOLERANCE
        and linf_delta <= WEIGHT_EFFECT_TOLERANCE,
        "exact_fields_match": exact,
        "delta_l2_abs_difference": l2_delta,
        "delta_linf_abs_difference": linf_delta,
        "tolerance": WEIGHT_EFFECT_TOLERANCE,
    }


def canonical_ledger_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [dict(row) for row in rows]
    keys = [
        (str(row["arm"]), int(row["seed"]), str(row["sample_id"]))
        for row in normalized
    ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("independent replay ledger contains duplicate keys")
    normalized.sort(
        key=lambda row: (str(row["arm"]), int(row["seed"]), str(row["sample_id"]))
    )
    return normalized


def atomic_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite replay ledger: {path}")
    ordered = canonical_ledger_rows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    with pending.open("w", encoding="utf-8", newline="\n") as stream:
        for row in ordered:
            stream.write(canonical_json(row).decode("utf-8") + "\n")
    os.replace(pending, path)
    key_rows = [
        [str(row["arm"]), int(row["seed"]), str(row["sample_id"])]
        for row in ordered
    ]
    return {
        "schema": LEDGER_SCHEMA,
        "path": str(path),
        "sha256": file_sha256(path),
        "rows": len(ordered),
        "unique_keys": len(key_rows),
        "key_sha256": stable_hash(key_rows),
    }


def _ledger_records(
    *,
    arm: str,
    seed: int,
    rows: Sequence[frozen_replay.ReplayActionRow],
    predictions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(rows) != len(predictions):
        raise RuntimeError("prediction and evaluator row counts differ")
    records = []
    for row, prediction in zip(rows, predictions, strict=True):
        records.append(
            {
                "schema": LEDGER_SCHEMA,
                "arm": arm,
                "seed": seed,
                "example_index": int(prediction["example_index"]),
                "sample_id": row.sample.sample_id,
                "prompt_sha256": hashlib.sha256(
                    row.prompt.encode("utf-8")
                ).hexdigest(),
                "payload_sha256": row.sample.payload_sha256,
                "target": int(prediction["target"]),
                "prediction": prediction["prediction"],
                "correct": bool(prediction["correct"]),
                "sector": int(prediction["sector"]),
                "operation_id": str(prediction["operation_id"]),
                "view_id": str(prediction["view_id"]),
                "source_family": str(prediction["source_family"]),
            }
        )
    return records


def replayed_gate(
    *,
    comparisons: Mapping[str, Any],
    paired: Mapping[str, Any],
    parameter_counts: set[int],
    retained: bool,
    rows_changed: bool,
) -> bool:
    names = [f"{PRIMARY}_vs_{control}" for control in GATE_CONTROLS]
    return (
        len(parameter_counts) == 1
        and retained
        and rows_changed
        and all(
            bool(comparisons[name][metric]["clears_positive_gate"])
            for name in names
            for metric in ("accuracy", "macro_f1")
        )
        and all(bool(paired[name]["clears_finite_uncertainty_gate"]) for name in names)
    )


def _baseline_replay_errors(
    baseline_result_path: Path,
    baseline_replay: Mapping[str, Any],
) -> list[str]:
    errors = []
    if baseline_replay.get("status") != "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION":
        errors.append("baseline independent replay did not pass")
    if baseline_replay.get("errors"):
        errors.append("baseline independent replay contains errors")
    if baseline_replay.get("producer_result_sha256") != file_sha256(
        baseline_result_path
    ):
        errors.append("baseline independent replay is not bound to baseline result")
    if baseline_replay.get("independent_dataset_builder_sha256") != file_sha256(
        Path(frozen_replay.__file__).resolve(strict=True)
    ):
        errors.append("baseline independent replay verifier binding is stale")
    if baseline_replay.get("promotion") != "NONE":
        errors.append("baseline independent replay exceeds promotion authority")
    if baseline_replay.get("partial_unfreeze_authorized") is not False:
        errors.append("baseline replay partial-unfreeze boundary differs")
    return errors


def _baseline_watch_errors(
    replay_path: Path,
    replay_receipt: Mapping[str, Any],
    watch_receipt: Mapping[str, Any],
) -> list[str]:
    errors = []
    if watch_receipt.get("status") != "COMPLETE_INDEPENDENT_REPLAY_NO_PROMOTION":
        errors.append("baseline replay watcher is not complete")
    if watch_receipt.get("replay_receipt_sha256") != file_sha256(replay_path):
        errors.append("baseline replay watcher is not bound to replay receipt")
    if watch_receipt.get("producer_result_sha256") != replay_receipt.get(
        "producer_result_sha256"
    ):
        errors.append("baseline replay watcher is not bound to producer result")
    if watch_receipt.get("replay_status") != replay_receipt.get("status"):
        errors.append("baseline replay watcher status differs from replay receipt")
    replay_errors = replay_receipt.get("errors")
    if not isinstance(replay_errors, list) or watch_receipt.get(
        "replay_error_count"
    ) != len(replay_errors):
        errors.append("baseline replay watcher error count differs")
    if watch_receipt.get("verifier_sha256") != replay_receipt.get(
        "independent_dataset_builder_sha256"
    ):
        errors.append("baseline replay watcher verifier hash differs")
    if watch_receipt.get("verifier_contract_sha256") != replay_receipt.get(
        "verifier_contract_sha256"
    ):
        errors.append("baseline replay watcher verifier contract differs")
    contract = replay_receipt.get("verifier_contract")
    contract_files = contract.get("files") if isinstance(contract, Mapping) else None
    source_adapter = (
        contract_files.get("source_adapter")
        if isinstance(contract_files, Mapping)
        else None
    )
    if not isinstance(source_adapter, Mapping) or watch_receipt.get(
        "source_adapter_sha256"
    ) != source_adapter.get("sha256"):
        errors.append("baseline replay watcher source-adapter hash differs")
    if watch_receipt.get("verifier_contract_binding_matches") is not True:
        errors.append("baseline replay watcher verifier contract binding failed")
    if watch_receipt.get("verifier_contract_stable_during_replay") is not True:
        errors.append("baseline replay watcher verifier contract changed")
    if watch_receipt.get("authority_boundary_passed") is not True:
        errors.append("baseline replay watcher authority boundary failed")
    return errors


def _load_terminal_payload(
    artifact: Path, recorded: Mapping[str, Any], *, hash_field: str
) -> dict[str, Any]:
    expected = str(recorded[hash_field])
    if file_sha256(artifact) != expected:
        raise RuntimeError(f"terminal model hash mismatch: {artifact}")
    payload = torch.load(artifact, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise RuntimeError(f"terminal model is not a mapping: {artifact}")
    return payload


def _recorded_rows(
    producer: Mapping[str, Any], arm: str
) -> dict[int, dict[str, Any]]:
    rows = [dict(row) for row in producer["per_arm"][arm]]
    if len(rows) != 3:
        raise RuntimeError(f"producer arm {arm} must contain three seeds")
    result = {int(row["seed"]): row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError(f"producer arm {arm} contains duplicate seeds")
    return result


def verify_run(
    run_dir: Path,
    *,
    tolerance: float = 1e-12,
    ledger_output: Path | None = None,
) -> dict[str, Any]:
    run = run_dir.resolve(strict=True)
    manifest_path = run / "RUN_MANIFEST.json"
    producer_path = run / "RESULT.json"
    manifest = read_json(manifest_path)
    producer = read_json(producer_path)
    config = manifest["config"]
    errors: list[str] = []

    if tuple(config.get("arms", ())) != THAW_ARMS:
        errors.append("thaw arm contract differs")
    seeds = tuple(int(seed) for seed in config.get("seeds", ()))
    if len(seeds) != 3 or len(set(seeds)) != 3:
        errors.append("thaw seed contract differs")
    if stable_hash(config) != manifest.get("config_hash"):
        errors.append("thaw config hash mismatch")
    if producer.get("status") != "COMPLETE":
        errors.append("thaw producer result is not complete")
    if producer.get("config") != config:
        errors.append("producer and manifest configs differ")

    baseline_run = Path(str(config["baseline_run"])).resolve(strict=True)
    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    baseline_replay_path = baseline_run / "INDEPENDENT_REPLAY.json"
    baseline_watch_path = baseline_run / "INDEPENDENT_REPLAY_WATCH_STATUS.json"
    baseline_manifest = read_json(baseline_manifest_path)
    baseline_result = read_json(baseline_result_path)
    baseline_replay = read_json(baseline_replay_path)
    baseline_watch = read_json(baseline_watch_path)
    if file_sha256(baseline_manifest_path) != config.get("baseline_manifest_sha256"):
        errors.append("baseline manifest hash mismatch")
    if file_sha256(baseline_result_path) != config.get("baseline_result_sha256"):
        errors.append("baseline result hash mismatch")
    errors.extend(_baseline_replay_errors(baseline_result_path, baseline_replay))
    errors.extend(
        _baseline_watch_errors(
            baseline_replay_path,
            baseline_replay,
            baseline_watch,
        )
    )

    baseline_config = baseline_manifest["config"]
    provider = ClaySourceAdapter(Path(str(config["source_dir"])))
    dataset = frozen_replay.build_replay_dataset(
        provider,
        rows_per_view=int(baseline_config["rows_per_view"]),
        holdout_rows=int(baseline_config["holdout_rows"]),
        seed=int(baseline_config["data_seed"]),
    )
    if dict(dataset.manifest) != dict(manifest["dataset"]):
        errors.append("independently rebuilt thaw dataset mismatch")
    if dict(dataset.manifest) != dict(baseline_manifest["dataset"]):
        errors.append("thaw and baseline dataset manifests differ")
    if dict(sorted(provider.source_hashes.items())) != dict(config["source_hashes"]):
        errors.append("source hash mismatch")

    count_train = frozen_replay._counting_rows(False)
    count_holdout = frozen_replay._counting_rows(True)
    vocab, stoi = frozen_replay._vocab_of(
        count_train,
        count_holdout,
        tuple(row.pair() for row in dataset.static_rows),
        tuple(row.pair() for row in dataset.multiview_rows),
        tuple(row.pair() for row in dataset.holdout_rows),
    )
    if stable_hash(vocab) != baseline_manifest.get("vocab_sha256"):
        errors.append("vocabulary hash mismatch")
    token_identity = frozen_replay.byte_token_identity_receipt(vocab)
    if not token_identity["pass"]:
        errors.append("byte-token identity receipt failed")
    itos = {index: token for token, index in stoi.items()}
    shuffled_holdout = sample_local_byte_shuffle_rows(
        dataset.holdout_rows, seed=int(config["control_shuffle_seed"])
    )
    shuffle_receipt = {
        "seed": int(config["control_shuffle_seed"]),
        "rows": len(shuffled_holdout),
        "prompt_sha256": stable_hash(
            [hashlib.sha256(row.prompt.encode("utf-8")).hexdigest() for row in shuffled_holdout]
        ),
    }

    recorded_by_arm = {arm: _recorded_rows(producer, arm) for arm in ALL_ARMS}
    baseline_by_arm = {
        arm: _recorded_rows(baseline_result, arm) for arm in IMPORTED_CONTROLS
    }
    replay_by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ALL_ARMS}
    model_receipts: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    learned_audits: list[dict[str, Any]] = []

    for seed in seeds:
        parent_dir = baseline_run / "parents" / f"seed-{seed}"
        parent_result_path = parent_dir / "RESULT.json"
        parent_path = parent_dir / "PARENT.pt"
        parent_result = read_json(parent_result_path)
        parent = _load_terminal_payload(parent_path, parent_result, hash_field="parent_sha256")
        if parent.get("vocab") != vocab:
            errors.append(f"parent vocabulary mismatch for seed {seed}")
        parent_state = parent["model_state"]

        for arm in THAW_ARMS:
            horse_dir = run / "horses" / f"{arm}-seed-{seed}"
            horse_result_path = horse_dir / "RESULT.json"
            artifact = horse_dir / "MODEL.pt"
            horse_result = read_json(horse_result_path)
            recorded = recorded_by_arm[arm][seed]
            if horse_result != recorded:
                errors.append(f"{arm} seed {seed}: aggregate row differs from horse result")
            payload = _load_terminal_payload(
                artifact, horse_result, hash_field="model_sha256"
            )
            identity = {
                "schema": "clay.byte-embedding-thaw-campaign.v1.horse",
                "arm": arm,
                "seed": seed,
                "config_hash": manifest["config_hash"],
                "parent_sha256": parent_result["parent_sha256"],
            }
            if any(payload.get(key) != value for key, value in identity.items()):
                errors.append(f"{arm} seed {seed}: terminal payload identity differs")
            if payload.get("vocab") != vocab:
                errors.append(f"{arm} seed {seed}: artifact vocabulary mismatch")
            state_audit = audit_thaw_state(parent_state, payload["model_state"], vocab)
            if not state_audit["state_keys_exact"]:
                errors.append(f"{arm} seed {seed}: state key set differs")
            if not state_audit["frozen_tensors_bit_identical"]:
                errors.append(f"{arm} seed {seed}: frozen tensors differ")
            if int(state_audit["changed_byte_rows"]) < 1:
                errors.append(f"{arm} seed {seed}: no thawed byte row changed")
            if state_audit["thaw_receipt"] != horse_result.get("thaw_receipt"):
                errors.append(f"{arm} seed {seed}: thaw receipt differs")
            weight_comparison = compare_weight_effect(
                state_audit["weight_effect"], horse_result.get("weight_effect")
            )
            if not weight_comparison["pass"]:
                errors.append(f"{arm} seed {seed}: weight-effect receipt differs")
            model = ReplayByteThawModel(vocab)
            model.load_state_dict(payload["model_state"], strict=True)
            eval_rows = shuffled_holdout if arm == SHUFFLED else dataset.holdout_rows
            predictions = frozen_replay._predict_actions(
                model, eval_rows, stoi, itos, null_carrier=False
            )
            metrics = frozen_replay.replay_action_metrics(predictions)
            count_score = frozen_replay._counting_accuracy(
                model, count_holdout, stoi, itos
            )
            mismatch_count = frozen_replay._prediction_mismatches(
                predictions, recorded["predictions"]
            )
            metric_delta = frozen_replay._max_numeric_delta(
                metrics, recorded["metrics"]
            )
            count_delta = abs(count_score - float(recorded["counting_accuracy"]))
            if mismatch_count:
                errors.append(f"{arm} seed {seed}: {mismatch_count} prediction mismatches")
            if metric_delta > tolerance:
                errors.append(f"{arm} seed {seed}: metric delta {metric_delta}")
            if count_delta > tolerance:
                errors.append(f"{arm} seed {seed}: counting delta {count_delta}")
            replay_row = {
                "arm": arm,
                "seed": seed,
                "metrics": metrics,
                "predictions": predictions,
                "counting_accuracy": count_score,
            }
            replay_by_arm[arm].append(replay_row)
            ledger_rows.extend(
                _ledger_records(
                    arm=arm, seed=seed, rows=eval_rows, predictions=predictions
                )
            )
            learned_audits.append(state_audit)
            model_receipts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "artifact": str(artifact),
                    "artifact_sha256": file_sha256(artifact),
                    "recorded_result_sha256": file_sha256(horse_result_path),
                    "prediction_sha256": stable_hash(predictions),
                    "prediction_mismatches": mismatch_count,
                    "max_metric_delta": metric_delta,
                    "counting_delta": count_delta,
                    "state_audit": state_audit,
                    "producer_weight_effect_comparison": weight_comparison,
                    "output_diagnostics": frozen_replay.replay_output_diagnostics(
                        predictions
                    ),
                }
            )

        for arm in IMPORTED_CONTROLS:
            recorded = recorded_by_arm[arm][seed]
            baseline_recorded = baseline_by_arm[arm][seed]
            if recorded != baseline_recorded:
                errors.append(f"{arm} seed {seed}: imported baseline row differs")
            if arm == "no_intervention_adapter":
                artifact = parent_path
                source_result_path = parent_result_path
                source_result = parent_result
                payload = parent
            else:
                control_dir = baseline_run / "horses" / f"{arm}-seed-{seed}"
                source_result_path = control_dir / "RESULT.json"
                source_result = read_json(source_result_path)
                artifact = control_dir / "MODEL.pt"
                payload = _load_terminal_payload(
                    artifact, source_result, hash_field="model_sha256"
                )
            if source_result != baseline_recorded:
                errors.append(f"{arm} seed {seed}: terminal baseline result differs")
            if payload.get("vocab") != vocab:
                errors.append(f"{arm} seed {seed}: artifact vocabulary mismatch")
            model = frozen_replay.ReplayFrozenActionModel(len(vocab))
            model.load_state_dict(payload["model_state"], strict=True)
            predictions = frozen_replay._predict_actions(
                model,
                dataset.holdout_rows,
                stoi,
                itos,
                null_carrier=False,
            )
            metrics = frozen_replay.replay_action_metrics(predictions)
            count_score = frozen_replay._counting_accuracy(
                model, count_holdout, stoi, itos
            )
            mismatch_count = frozen_replay._prediction_mismatches(
                predictions, recorded["predictions"]
            )
            metric_delta = frozen_replay._max_numeric_delta(
                metrics, recorded["metrics"]
            )
            count_delta = abs(count_score - float(recorded["counting_accuracy"]))
            frozen_exact = frozen_replay._frozen_equal(
                parent_state, payload["model_state"]
            )
            if mismatch_count:
                errors.append(f"{arm} seed {seed}: {mismatch_count} prediction mismatches")
            if metric_delta > tolerance:
                errors.append(f"{arm} seed {seed}: metric delta {metric_delta}")
            if count_delta > tolerance:
                errors.append(f"{arm} seed {seed}: counting delta {count_delta}")
            if not frozen_exact:
                errors.append(f"{arm} seed {seed}: frozen tensors differ")
            replay_by_arm[arm].append(
                {
                    "arm": arm,
                    "seed": seed,
                    "metrics": metrics,
                    "predictions": predictions,
                    "counting_accuracy": count_score,
                }
            )
            ledger_rows.extend(
                _ledger_records(
                    arm=arm,
                    seed=seed,
                    rows=dataset.holdout_rows,
                    predictions=predictions,
                )
            )
            model_receipts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "artifact": str(artifact),
                    "artifact_sha256": file_sha256(artifact),
                    "recorded_result_sha256": file_sha256(source_result_path),
                    "prediction_sha256": stable_hash(predictions),
                    "prediction_mismatches": mismatch_count,
                    "max_metric_delta": metric_delta,
                    "counting_delta": count_delta,
                    "frozen_tensors_bit_identical": frozen_exact,
                    "output_diagnostics": frozen_replay.replay_output_diagnostics(
                        predictions
                    ),
                }
            )

    comparisons: dict[str, Any] = {}
    paired: dict[str, Any] = {}
    for control in (*GATE_CONTROLS, STATIC):
        name = f"{PRIMARY}_vs_{control}"
        comparisons[name] = {
            metric: frozen_replay._metric_comparison(
                replay_by_arm[PRIMARY], replay_by_arm[control], metric
            )
            for metric in ("accuracy", "macro_f1")
        }
        paired[name] = frozen_replay._paired_comparison(
            replay_by_arm[PRIMARY], replay_by_arm[control]
        )
    comparison_delta = frozen_replay._max_numeric_delta(
        comparisons, producer["comparisons"]
    )
    paired_delta = frozen_replay._max_numeric_delta(
        paired, producer["paired_comparisons"]
    )
    if comparison_delta > tolerance:
        errors.append(f"aggregate comparison delta {comparison_delta}")
    if paired_delta > tolerance:
        errors.append(f"aggregate paired delta {paired_delta}")

    parameter_counts = {
        int(audit["trainable_parameters"])
        for audit in learned_audits
        if audit["trainable_parameters"] is not None
    }
    retained = all(
        bool(audit["frozen_tensors_bit_identical"])
        for audit in learned_audits
    ) and all(
        math.isclose(
            float(row["counting_accuracy"]),
            float(recorded_by_arm[row["arm"]][int(row["seed"])]["parent_counting_accuracy"]),
            abs_tol=tolerance,
        )
        for arm in THAW_ARMS
        for row in replay_by_arm[arm]
    )
    rows_changed = all(int(audit["changed_byte_rows"]) > 0 for audit in learned_audits)
    gate = replayed_gate(
        comparisons=comparisons,
        paired=paired,
        parameter_counts=parameter_counts,
        retained=retained,
        rows_changed=rows_changed,
    )
    expected_gate = "MET_PENDING_INDEPENDENT_REPLAY" if gate else "NOT_MET"
    if producer.get("producer_gate") != expected_gate:
        errors.append("producer gate differs from independent replay")

    ledger_path = (ledger_output or run / "INDEPENDENT_REPLAY_LEDGER.jsonl").resolve()
    ledger_receipt = atomic_jsonl(ledger_path, ledger_rows)
    max_metric_delta = max(
        (float(row["max_metric_delta"]) for row in model_receipts), default=0.0
    )
    result = {
        "schema": SCHEMA,
        "status": (
            "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
            if not errors
            else "FAIL_INDEPENDENT_INFERENCE_REPLAY"
        ),
        "authority": AUTHORITY,
        "promotion": "NONE",
        "partial_unfreeze_authorized": False,
        "run_dir": str(run),
        "independent_verifier": str(Path(__file__).resolve()),
        "independent_verifier_sha256": file_sha256(Path(__file__).resolve()),
        "producer_result_sha256": file_sha256(producer_path),
        "manifest_sha256": file_sha256(manifest_path),
        "baseline_manifest_sha256": file_sha256(baseline_manifest_path),
        "baseline_result_sha256": file_sha256(baseline_result_path),
        "baseline_replay_sha256": file_sha256(baseline_replay_path),
        "baseline_replay_watch_sha256": file_sha256(baseline_watch_path),
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "token_identity": token_identity,
        "shuffle_receipt": shuffle_receipt,
        "ledger": ledger_receipt,
        "model_receipts": model_receipts,
        "comparisons": comparisons,
        "paired_comparisons": paired,
        "producer_gate_replayed": expected_gate,
        "learned_parameter_count_matched": len(parameter_counts) == 1,
        "counting_and_base_parent_preserved": retained,
        "thawed_rows_changed": rows_changed,
        "max_metric_delta": max_metric_delta,
        "aggregate_comparison_delta": comparison_delta,
        "aggregate_paired_delta": paired_delta,
        "errors": errors,
        "claim_boundary": (
            "Independent measurement only; execution, merge, promotion, and "
            "partial-unfreeze authority remain NONE."
        ),
        "completed_at_utc": utc_now(),
    }
    result["replay_sha256"] = stable_hash(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ledger-output", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--summary-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.threads < 1:
        raise ValueError("threads must be positive")
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    result = verify_run(
        args.run_dir,
        tolerance=args.tolerance,
        ledger_output=args.ledger_output,
    )
    output = args.output or args.run_dir / "INDEPENDENT_REPLAY.json"
    atomic_json(output, result)
    printable: Mapping[str, Any] = result
    if args.summary_only:
        printable = {
            "status": result["status"],
            "producer_gate_replayed": result["producer_gate_replayed"],
            "ledger_sha256": result["ledger"]["sha256"],
            "model_count": len(result["model_receipts"]),
            "error_count": len(result["errors"]),
        }
    print(json.dumps(printable, sort_keys=True))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
