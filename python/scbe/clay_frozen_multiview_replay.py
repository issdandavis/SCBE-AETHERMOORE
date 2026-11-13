"""Independent inference replay for the frozen multi-view adapter campaign.

This verifier deliberately does not import the campaign producer, its model,
or its metric helpers.  It rebuilds the held action rows from the pinned source,
loads each emitted state dict into a separately declared network, recomputes
predictions and metrics, and compares the resulting gates with RESULT.json.
It is measurement-only and cannot grant promotion, unfreezing, or execution
authority.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from numbers import Integral
import os
from pathlib import Path
import random
import statistics
import struct
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from python.scbe.clay_paired_orbit_training import ClaySourceAdapter

SCHEMA = "clay.frozen-multiview-adapter-independent-replay.v1"
DATA_SCHEMA = "clay.frozen-multiview-action-data.v1"
AUTHORITY = "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_PARTIAL_UNFREEZE"
TRAINED_ARMS = (
    "frozen_adapter_static",
    "frozen_adapter_multiview",
    "frozen_adapter_null",
)
ALL_ARMS = ("no_intervention_adapter",) + TRAINED_ARMS
PRIMARY_ARM = "frozen_adapter_multiview"
CONTROLS = (
    "frozen_adapter_static",
    "frozen_adapter_null",
    "no_intervention_adapter",
)
FROZEN_PREFIXES = ("e.", "g.", "count_head.")
STRUCTURAL_MISMATCH_DELTA = 1e300
PAD, BOS, SEP, EOS = "\x00", "\x02", "\x1f", "\x03"
FEATURE_WIDTH = 37
ACTION_COUNT = 5
BYTE_TOKEN_BASE = 0xE100
STATIC_SOURCE = "clay-action-train-static-v1"
MULTIVIEW_SOURCES = tuple(f"clay-action-train-view-{index}-v1" for index in range(3))
HOLDOUT_SOURCE = "clay-action-held-diagonal-v1"
ACTION_NAMES = (
    "rest",
    "push_x_positive",
    "push_x_negative",
    "push_y_positive",
    "push_y_negative",
)
INFERENCE_PATH = {
    "input": "exact 148-byte encoding of the 37-value float32 state",
    "learned_path": "frozen embedding -> frozen two-layer GRU -> adapter -> action head",
    "decode": "greedy character decode to one integer action ID",
    "target_authority": "DevelopmentalGameSandbox.sieve_actions one-step reward argmax",
    "sector_role": "held-output diagnostic coordinate only",
    "routing_sieve_at_inference": False,
    "triangulation_or_ensemble_at_inference": False,
    "tool_calls_at_inference": False,
}


@dataclass(frozen=True, slots=True)
class ReplaySample:
    """Identity record declared independently from the producer ledger."""

    sample_id: str
    payload_sha256: str
    concept_id: str
    variant_id: str
    source_family: str
    split: str
    operation_id: str
    view_id: str

    def identity_record(self) -> dict[str, str]:
        return {
            "sample_id": self.sample_id,
            "payload_sha256": self.payload_sha256,
            "concept_id": self.concept_id,
            "variant_id": self.variant_id,
            "source_family": self.source_family,
            "split": self.split,
            "operation_id": self.operation_id,
            "view_id": self.view_id,
        }


@dataclass(frozen=True, slots=True)
class ReplayActionRow:
    sample: ReplaySample
    prompt: str
    target: str
    label: int
    sector: int

    def pair(self) -> tuple[str, str]:
        return self.prompt, self.target

    def identity_record(self) -> dict[str, Any]:
        return {
            **self.sample.identity_record(),
            "prompt_sha256": hashlib.sha256(self.prompt.encode("utf-8")).hexdigest(),
            "target": self.target,
            "label": self.label,
            "sector": self.sector,
        }


@dataclass(frozen=True, slots=True)
class ReplayDataset:
    static_rows: tuple[ReplayActionRow, ...]
    multiview_rows: tuple[ReplayActionRow, ...]
    holdout_rows: tuple[ReplayActionRow, ...]
    manifest: Mapping[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _replay_feature_bytes(feature: Tensor) -> bytes:
    """Serialize one state without calling the producer's byte bridge."""

    value = feature.detach().cpu().to(torch.float32).contiguous()
    if value.shape != (FEATURE_WIDTH,) or not bool(torch.isfinite(value).all()):
        raise ValueError("action feature must be one finite 37-value vector")
    return struct.pack(f">{FEATURE_WIDTH}f", *value.tolist())


def _replay_prompt(feature: Tensor) -> str:
    payload = _replay_feature_bytes(feature)
    return "K :" + "".join(chr(BYTE_TOKEN_BASE + item) for item in payload) + " =>"


def _replay_quotas(count: int) -> list[int]:
    if count < ACTION_COUNT:
        raise ValueError("each replay row bank must cover every action")
    base, remainder = divmod(count, ACTION_COUNT)
    return [base + (index < remainder) for index in range(ACTION_COUNT)]


def _collect_replay_rows(
    provider: Any,
    sandbox: Any,
    *,
    count: int,
    seed: int,
    view_id: str,
    source_family: str,
    split: str,
    used_payloads: set[str],
) -> tuple[ReplayActionRow, ...]:
    """Recreate accepted rows through replay-local balancing and serialization."""

    quotas = _replay_quotas(count)
    accepted = [0] * ACTION_COUNT
    rng = random.Random(seed)
    rows: list[ReplayActionRow] = []
    attempts = 0
    while len(rows) < count and attempts < count * 512:
        attempts += 1
        state = provider.sample_state(sandbox, rng)
        feature, raw_label, raw_sector = provider.materialize(sandbox, state)
        label = int(raw_label)
        sector = int(raw_sector)
        if label not in range(ACTION_COUNT) or accepted[label] >= quotas[label]:
            continue
        payload = _replay_feature_bytes(feature)
        payload_sha256 = hashlib.sha256(
            payload + bytes((label, sector & 0xFF))
        ).hexdigest()
        if payload_sha256 in used_payloads:
            continue
        used_payloads.add(payload_sha256)
        sample_id = f"{split}-{view_id}-{len(rows):06d}"
        rows.append(
            ReplayActionRow(
                sample=ReplaySample(
                    sample_id=sample_id,
                    payload_sha256=payload_sha256,
                    concept_id=f"sector-{sector}",
                    variant_id=f"byte-state-{payload_sha256[:24]}",
                    source_family=source_family,
                    split=split,
                    operation_id=f"action-{label}",
                    view_id=view_id,
                ),
                prompt=_replay_prompt(feature),
                target=str(label),
                label=label,
                sector=sector,
            )
        )
        accepted[label] += 1
    if len(rows) != count:
        raise RuntimeError(
            f"could not fill replay view {view_id}: {len(rows)}/{count}; "
            f"action counts={accepted}"
        )
    return tuple(rows)


def _replay_action_counts(rows: Sequence[ReplayActionRow]) -> dict[str, int]:
    return {
        f"action-{action}": sum(row.label == action for row in rows)
        for action in range(ACTION_COUNT)
    }


def build_replay_dataset(
    provider: Any,
    *,
    rows_per_view: int,
    holdout_rows: int,
    seed: int,
) -> ReplayDataset:
    """Independently reconstruct the producer's deterministic dataset deed."""

    if rows_per_view < ACTION_COUNT or holdout_rows < ACTION_COUNT:
        raise ValueError("replay row counts must cover every action")
    sandboxes = provider.training_sandboxes()
    if len(sandboxes) != 3:
        raise ValueError("replay requires exactly three legal train views")
    used_payloads: set[str] = set()
    static_rows = _collect_replay_rows(
        provider,
        sandboxes[0],
        count=rows_per_view * 3,
        seed=seed + 11,
        view_id="static-view-0",
        source_family=STATIC_SOURCE,
        split="train",
        used_payloads=used_payloads,
    )
    multiview_rows = tuple(
        row
        for view, sandbox in enumerate(sandboxes)
        for row in _collect_replay_rows(
            provider,
            sandbox,
            count=rows_per_view,
            seed=seed + 101 + 37 * view,
            view_id=f"train-view-{view}",
            source_family=MULTIVIEW_SOURCES[view],
            split="train",
            used_payloads=used_payloads,
        )
    )
    held_rows = _collect_replay_rows(
        provider,
        provider.holdout_sandbox(),
        count=holdout_rows,
        seed=seed + 1009,
        view_id="held-diagonal",
        source_family=HOLDOUT_SOURCE,
        split="holdout",
        used_payloads=used_payloads,
    )
    body: dict[str, Any] = {
        "schema": DATA_SCHEMA,
        "seed": seed,
        "feature_width": FEATURE_WIDTH,
        "feature_bytes_per_row": FEATURE_WIDTH * 4,
        "byte_token_base": BYTE_TOKEN_BASE,
        "byte_token_count": 256,
        "rows_per_view": rows_per_view,
        "static_rows": len(static_rows),
        "multiview_rows": len(multiview_rows),
        "holdout_rows": len(held_rows),
        "static_sha256": _stable_hash([row.identity_record() for row in static_rows]),
        "multiview_sha256": _stable_hash(
            [row.identity_record() for row in multiview_rows]
        ),
        "holdout_sha256": _stable_hash([row.identity_record() for row in held_rows]),
        "static_action_counts": _replay_action_counts(static_rows),
        "multiview_action_counts": _replay_action_counts(multiview_rows),
        "holdout_action_counts": _replay_action_counts(held_rows),
        "source_hashes": dict(sorted(provider.source_hashes.items())),
        "source_families": {
            "static": [STATIC_SOURCE],
            "multiview": list(MULTIVIEW_SOURCES),
            "holdout": [HOLDOUT_SOURCE],
        },
        "source_disjoint": HOLDOUT_SOURCE not in {STATIC_SOURCE, *MULTIVIEW_SOURCES},
        "authority": {
            "execution": "NONE",
            "compiler": "DETERMINISTIC_LABEL_AUTHORITY_ONLY",
            "promotion": "NOT_AUTHORIZED",
        },
    }
    return ReplayDataset(
        static_rows=static_rows,
        multiview_rows=multiview_rows,
        holdout_rows=held_rows,
        manifest={**body, "manifest_sha256": _stable_hash(body)},
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def _counting_rows(holdout: bool) -> list[tuple[str, str]]:
    rows = []
    for step in range(1, 10):
        for start in range(40):
            terms = [start + step * index for index in range(4)]
            target = start + step * 4
            if target > 400 or (start % 7 == 0) != holdout:
                continue
            rows.append(
                (
                    f"C {step} : " + " ".join(map(str, terms)) + " =>",
                    f" {target}",
                )
            )
    return rows


def _vocab_of(*rowsets: Sequence[tuple[str, str]]) -> tuple[list[str], dict[str, int]]:
    characters = set(PAD + BOS + SEP + EOS)
    for rows in rowsets:
        for prompt, target in rows:
            characters.update(prompt)
            characters.update(target)
    special = (PAD, BOS, SEP, EOS)
    vocab = list(special) + sorted(char for char in characters if char not in special)
    return vocab, {char: index for index, char in enumerate(vocab)}


def byte_token_identity_receipt(vocab: Sequence[str]) -> dict[str, Any]:
    """Prove the logical one-token-per-byte carrier without hiding storage cost."""

    token_to_id = {token: index for index, token in enumerate(vocab)}
    byte_tokens = tuple(chr(BYTE_TOKEN_BASE + value) for value in range(256))
    missing = [
        value for value, token in enumerate(byte_tokens) if token not in token_to_id
    ]
    token_ids = [token_to_id[token] for token in byte_tokens if token in token_to_id]
    contiguous = bool(token_ids) and token_ids == list(
        range(token_ids[0], token_ids[0] + len(token_ids))
    )
    table_rows = [
        {
            "byte": value,
            "code_point": f"U+{ord(token):04X}",
            "model_token_id": token_to_id.get(token),
        }
        for value, token in enumerate(byte_tokens)
    ]
    storage_widths = sorted({len(token.encode("utf-8")) for token in byte_tokens})
    passed = (
        not missing
        and len(set(byte_tokens)) == 256
        and len(set(token_ids)) == 256
        and contiguous
    )
    return {
        "schema": "clay.byte-token-identity-receipt.v1",
        "pass": passed,
        "canonical_identity": "unsigned byte value 0..255",
        "carrier_mapping": "token_code_point = U+E100 + byte_value",
        "canonical_byte_count": 256,
        "present_byte_token_count": len(token_ids),
        "missing_byte_values": missing,
        "distinct_carrier_token_count": len(set(byte_tokens)),
        "distinct_model_token_id_count": len(set(token_ids)),
        "model_token_ids_contiguous": contiguous,
        "first_model_token_id": token_ids[0] if token_ids else None,
        "last_model_token_id": token_ids[-1] if token_ids else None,
        "logical_model_tokens_per_payload_byte": 1,
        "utf8_storage_bytes_per_carrier_token": storage_widths,
        "feature_payload_bytes": FEATURE_WIDTH * 4,
        "feature_payload_model_tokens": FEATURE_WIDTH * 4,
        "table_sha256": _stable_hash(table_rows),
        "view_boundary": (
            "B256 and Six-Tongues spellings are reversible views over the same "
            "byte identity; they are not input arms in this campaign"
        ),
    }


class ReplayAdapter(nn.Module):
    """Separately declared adapter with producer-compatible state keys."""

    def __init__(self, hidden: int = 192, bottleneck: int = 160) -> None:
        super().__init__()
        self.down = nn.Linear(hidden, bottleneck)
        self.mid = nn.Linear(bottleneck, bottleneck)
        self.up = nn.Linear(bottleneck, hidden)
        self.act = nn.GELU()

    def forward(self, hidden: Tensor) -> Tensor:
        return hidden + self.up(self.act(self.mid(self.act(self.down(hidden)))))


class ReplayFrozenActionModel(nn.Module):
    """Independent network declaration used only for artifact replay."""

    def __init__(self, vocab_size: int) -> None:
        super().__init__()
        self.e = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.g = nn.GRU(64, 192, 2, batch_first=True)
        self.adapter = ReplayAdapter()
        self.count_head = nn.Linear(192, vocab_size)
        self.adapter_head = nn.Linear(192, vocab_size)

    def forward(
        self,
        inputs: Tensor,
        *,
        head: str,
        null_carrier: bool,
        state: Any = None,
    ) -> tuple[Tensor, Any]:
        core_state = state[0] if isinstance(state, tuple) else state
        hidden, core_state = self.g(self.e(inputs), core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        carrier = torch.ones_like(hidden) if null_carrier else hidden
        return self.adapter_head(self.adapter(carrier)), (core_state, None)


@torch.inference_mode()
def _generate_integer(
    model: ReplayFrozenActionModel,
    *,
    head: str,
    prompt: str,
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    null_carrier: bool,
    max_length: int,
) -> int | None:
    model.eval()
    ids = [stoi[BOS], *(stoi[char] for char in prompt), stoi[SEP]]
    logits, state = model(torch.tensor([ids]), head=head, null_carrier=null_carrier)
    token = int(logits[0, -1].argmax())
    output = []
    for _ in range(max_length):
        if token == stoi[EOS]:
            break
        output.append(itos[token])
        logits, state = model(
            torch.tensor([[token]]),
            head=head,
            null_carrier=null_carrier,
            state=state,
        )
        token = int(logits[0, -1].argmax())
    text = "".join(output).strip()
    try:
        return int(text.split()[0])
    except (ValueError, IndexError):
        return None


def _predict_actions(
    model: ReplayFrozenActionModel,
    rows: Sequence[ReplayActionRow],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
    *,
    null_carrier: bool,
) -> list[dict[str, Any]]:
    predictions = []
    for index, row in enumerate(rows):
        prediction = _generate_integer(
            model,
            head="action",
            prompt=row.prompt,
            stoi=stoi,
            itos=itos,
            null_carrier=null_carrier,
            max_length=2,
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


def _counting_accuracy(
    model: ReplayFrozenActionModel,
    rows: Sequence[tuple[str, str]],
    stoi: Mapping[str, int],
    itos: Mapping[int, str],
) -> float:
    correct = 0
    for prompt, target in rows:
        prediction = _generate_integer(
            model,
            head="count",
            prompt=prompt,
            stoi=stoi,
            itos=itos,
            null_carrier=False,
            max_length=5,
        )
        correct += prediction == int(target.strip())
    return correct / len(rows)


def replay_action_metrics(predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Recompute all reported action metrics without producer helpers."""

    accuracy = sum(bool(row["correct"]) for row in predictions) / len(predictions)
    recalls = []
    f1s = []
    per_action = {}
    for label in range(5):
        relevant = [row for row in predictions if int(row["target"]) == label]
        true_positive = sum(row["prediction"] == label for row in relevant)
        false_negative = len(relevant) - true_positive
        false_positive = sum(
            row["prediction"] == label and int(row["target"]) != label
            for row in predictions
        )
        recall = true_positive / len(relevant) if relevant else 0.0
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        recalls.append(recall)
        f1s.append(f1)
        per_action[str(label)] = {
            "support": len(relevant),
            "accuracy": recall,
            "f1": f1,
            "false_negative": false_negative,
        }
    sectors = sorted({int(row["sector"]) for row in predictions})
    return {
        "accuracy": accuracy,
        "macro_f1": statistics.fmean(f1s),
        "worst_action_accuracy": min(recalls),
        "per_action": per_action,
        "per_sector_accuracy": {
            str(sector): statistics.fmean(
                bool(row["correct"])
                for row in predictions
                if int(row["sector"]) == sector
            )
            for sector in sectors
        },
    }


def _prediction_bucket(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, Integral):
        return "invalid"
    integer = int(value)
    return str(integer) if integer in range(ACTION_COUNT) else "invalid"


def replay_output_diagnostics(
    predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Expose output flow instead of hiding behavior behind mean accuracy."""

    buckets = tuple(str(index) for index in range(ACTION_COUNT)) + ("invalid",)
    confusion = {
        str(target): {bucket: 0 for bucket in buckets} for target in range(ACTION_COUNT)
    }
    distribution = {bucket: 0 for bucket in buckets}
    per_sector: dict[str, dict[str, Any]] = {}
    correct_count = 0
    for row in predictions:
        target = int(row["target"])
        if target not in range(ACTION_COUNT):
            raise ValueError(f"invalid replay target: {target}")
        bucket = _prediction_bucket(row.get("prediction"))
        correct = bucket == str(target)
        if bool(row["correct"]) != correct:
            raise ValueError("replay correctness flag disagrees with target/prediction")
        confusion[str(target)][bucket] += 1
        distribution[bucket] += 1
        correct_count += int(correct)
        sector = str(int(row["sector"]))
        if sector not in per_sector:
            per_sector[sector] = {
                "support": 0,
                "correct": 0,
                "invalid": 0,
                "prediction_distribution": {name: 0 for name in buckets},
            }
        sector_row = per_sector[sector]
        sector_row["support"] += 1
        sector_row["correct"] += int(correct)
        sector_row["invalid"] += int(bucket == "invalid")
        sector_row["prediction_distribution"][bucket] += 1

    top_error_flows = []
    for target in range(ACTION_COUNT):
        for bucket in buckets:
            if bucket == str(target):
                continue
            count = confusion[str(target)][bucket]
            if count:
                top_error_flows.append(
                    {
                        "target_id": target,
                        "target_action": ACTION_NAMES[target],
                        "prediction": (
                            ACTION_NAMES[int(bucket)]
                            if bucket != "invalid"
                            else "invalid"
                        ),
                        "count": count,
                    }
                )
    top_error_flows.sort(
        key=lambda row: (
            -int(row["count"]),
            int(row["target_id"]),
            str(row["prediction"]),
        )
    )
    total = len(predictions)
    invalid = distribution["invalid"]
    return {
        "example_count": total,
        "correct_count": correct_count,
        "valid_prediction_count": total - invalid,
        "invalid_prediction_count": invalid,
        "valid_prediction_rate": (total - invalid) / total if total else 0.0,
        "prediction_distribution": distribution,
        "confusion": confusion,
        "per_sector": dict(sorted(per_sector.items(), key=lambda item: int(item[0]))),
        "top_error_flows": top_error_flows[:12],
    }


def paired_output_diagnostics(
    contender: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Trace which exact held examples a contender fixes or regresses."""

    def index_rows(
        rows: Sequence[Mapping[str, Any]], *, label: str
    ) -> dict[tuple[int, str], Mapping[str, Any]]:
        indexed: dict[tuple[int, str], Mapping[str, Any]] = {}
        for row in rows:
            key = (int(row["example_index"]), str(row["payload_sha256"]))
            if key in indexed:
                raise RuntimeError(f"duplicate {label} output diagnostic key: {key}")
            indexed[key] = row
        return indexed

    left = index_rows(contender, label="contender")
    right = index_rows(control, label="control")
    if left.keys() != right.keys():
        raise RuntimeError("paired output diagnostic keys differ")
    by_action = {
        str(index): {"wins": 0, "losses": 0, "ties": 0} for index in range(ACTION_COUNT)
    }
    sectors = sorted({int(row["sector"]) for row in contender})
    by_sector = {str(sector): {"wins": 0, "losses": 0, "ties": 0} for sector in sectors}
    wins = losses = both_correct = both_wrong_same = both_wrong_different = 0
    changed = 0
    for key in left:
        contender_row = left[key]
        control_row = right[key]
        if int(contender_row["target"]) != int(control_row["target"]) or int(
            contender_row["sector"]
        ) != int(control_row["sector"]):
            raise RuntimeError("paired output targets or sectors differ")
        contender_correct = _prediction_bucket(contender_row.get("prediction")) == str(
            int(contender_row["target"])
        )
        control_correct = _prediction_bucket(control_row.get("prediction")) == str(
            int(control_row["target"])
        )
        if (
            bool(contender_row["correct"]) != contender_correct
            or bool(control_row["correct"]) != control_correct
        ):
            raise RuntimeError(
                "paired output correctness flag disagrees with target/prediction"
            )
        target = str(int(contender_row["target"]))
        sector = str(int(contender_row["sector"]))
        if contender_correct and not control_correct:
            wins += 1
            outcome = "wins"
        elif control_correct and not contender_correct:
            losses += 1
            outcome = "losses"
        else:
            outcome = "ties"
            if contender_correct:
                both_correct += 1
            elif _prediction_bucket(
                contender_row.get("prediction")
            ) == _prediction_bucket(control_row.get("prediction")):
                both_wrong_same += 1
            else:
                both_wrong_different += 1
        by_action[target][outcome] += 1
        by_sector[sector][outcome] += 1
        changed += _prediction_bucket(
            contender_row.get("prediction")
        ) != _prediction_bucket(control_row.get("prediction"))
    p_value = _paired_exact_p(wins, losses)
    return {
        "examples": len(left),
        "wins": wins,
        "losses": losses,
        "ties": len(left) - wins - losses,
        "both_correct": both_correct,
        "both_wrong_same_output": both_wrong_same,
        "both_wrong_different_output": both_wrong_different,
        "prediction_changed_count": changed,
        "two_sided_exact_p": p_value,
        "clears_finite_uncertainty_gate": wins > losses and p_value <= 0.05,
        "by_action": by_action,
        "by_sector": by_sector,
    }


def _paired_exact_p(wins: int, losses: int) -> float:
    discordant = wins + losses
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(wins, losses) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def _paired_comparison(
    contender: Sequence[Mapping[str, Any]], control: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    left = {
        (int(row["seed"]), int(item["example_index"])): bool(item["correct"])
        for row in contender
        for item in row["predictions"]
    }
    right = {
        (int(row["seed"]), int(item["example_index"])): bool(item["correct"])
        for row in control
        for item in row["predictions"]
    }
    if left.keys() != right.keys():
        raise RuntimeError("replay paired prediction keys differ")
    wins = sum(left[key] and not right[key] for key in left)
    losses = sum(right[key] and not left[key] for key in left)
    p_value = _paired_exact_p(wins, losses)
    return {
        "examples": len(left),
        "wins": wins,
        "losses": losses,
        "ties": len(left) - wins - losses,
        "two_sided_exact_p": p_value,
        "clears_finite_uncertainty_gate": wins > losses and p_value <= 0.05,
    }


def _metric_comparison(
    contender: Sequence[Mapping[str, Any]],
    control: Sequence[Mapping[str, Any]],
    metric: str,
) -> dict[str, Any]:
    left = [float(row["metrics"][metric]) for row in contender]
    right = [float(row["metrics"][metric]) for row in control]
    left_sd = statistics.stdev(left) if len(left) > 1 else 0.0
    right_sd = statistics.stdev(right) if len(right) > 1 else 0.0
    pooled_sd = math.sqrt((left_sd * left_sd + right_sd * right_sd) / 2.0)
    delta = statistics.fmean(left) - statistics.fmean(right)
    threshold = 2.0 * pooled_sd
    return {
        "metric": metric,
        "contender_mean": statistics.fmean(left),
        "control_mean": statistics.fmean(right),
        "mean_delta": delta,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": threshold,
        "clears_positive_gate": delta > threshold,
        "matched_seed_wins": sum(a > b for a, b in zip(left, right, strict=True)),
        "matched_seed_losses": sum(a < b for a, b in zip(left, right, strict=True)),
    }


def _max_numeric_delta(left: Any, right: Any) -> float:
    if isinstance(left, bool) or isinstance(right, bool):
        return 0.0 if left == right else STRUCTURAL_MISMATCH_DELTA
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if left.keys() != right.keys():
            return STRUCTURAL_MISMATCH_DELTA
        return max(
            (_max_numeric_delta(left[key], right[key]) for key in left),
            default=0.0,
        )
    if isinstance(left, Sequence) and not isinstance(left, (str, bytes)):
        if not isinstance(right, Sequence) or isinstance(right, (str, bytes)):
            return STRUCTURAL_MISMATCH_DELTA
        if len(left) != len(right):
            return STRUCTURAL_MISMATCH_DELTA
        return max(
            (_max_numeric_delta(a, b) for a, b in zip(left, right, strict=True)),
            default=0.0,
        )
    return 0.0 if left == right else STRUCTURAL_MISMATCH_DELTA


def _prediction_mismatches(
    replayed: Sequence[Mapping[str, Any]], recorded: Sequence[Mapping[str, Any]]
) -> int:
    fields = (
        "example_index",
        "sample_id",
        "payload_sha256",
        "target",
        "prediction",
        "correct",
        "sector",
        "operation_id",
        "view_id",
        "source_family",
    )
    if len(replayed) != len(recorded):
        return max(len(replayed), len(recorded))
    return sum(
        any(left.get(field) != right.get(field) for field in fields)
        for left, right in zip(replayed, recorded, strict=True)
    )


def _frozen_equal(
    parent_state: Mapping[str, Tensor], candidate_state: Mapping[str, Tensor]
) -> bool:
    keys = {key for key in parent_state if key.startswith(FROZEN_PREFIXES)}
    candidate_keys = {key for key in candidate_state if key.startswith(FROZEN_PREFIXES)}
    if keys != candidate_keys:
        return False
    return all(
        key in candidate_state and torch.equal(parent_state[key], candidate_state[key])
        for key in keys
    )


def _load_payload(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _file_sha256(path) != expected_sha256:
        raise RuntimeError(f"artifact hash mismatch: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise RuntimeError(f"model payload is not a mapping: {path}")
    return payload


def verify_completed_artifacts(
    run_dir: Path, *, tolerance: float = 1e-12
) -> dict[str, Any]:
    """Replay only terminal artifacts without computing a campaign verdict.

    The producer emits each file atomically, but the model/result pair is not a
    transaction. Missing or half-written pairs are therefore reported as
    pending rather than failed. This receipt is deliberately incapable of
    aggregate comparison or promotion.
    """

    run_dir = run_dir.resolve(strict=True)
    manifest = _read_json(run_dir / "RUN_MANIFEST.json")
    config = manifest["config"]
    errors: list[str] = []

    provider = ClaySourceAdapter(Path(config["source_dir"]))
    dataset = build_replay_dataset(
        provider,
        rows_per_view=int(config["rows_per_view"]),
        holdout_rows=int(config["holdout_rows"]),
        seed=int(config["data_seed"]),
    )
    dataset_matches = dict(dataset.manifest) == dict(manifest["dataset"])
    if not dataset_matches:
        errors.append("independently rebuilt dataset manifest mismatch")
    source_hashes_match = dict(sorted(provider.source_hashes.items())) == dict(
        config["source_hashes"]
    )
    if not source_hashes_match:
        errors.append("source hash mismatch")

    count_train = _counting_rows(False)
    count_holdout = _counting_rows(True)
    vocab, stoi = _vocab_of(
        count_train,
        count_holdout,
        tuple(row.pair() for row in dataset.static_rows),
        tuple(row.pair() for row in dataset.multiview_rows),
        tuple(row.pair() for row in dataset.holdout_rows),
    )
    vocab_matches = _stable_hash(vocab) == manifest["vocab_sha256"]
    if not vocab_matches:
        errors.append("vocabulary hash mismatch")
    token_identity = byte_token_identity_receipt(vocab)
    if not token_identity["pass"]:
        errors.append("byte-token identity receipt failed")
    itos = {index: char for char, index in stoi.items()}

    receipts: list[dict[str, Any]] = []
    replayed_predictions: dict[tuple[str, int], list[dict[str, Any]]] = {}
    pending: list[str] = []
    incomplete_pairs: list[str] = []
    expected = len(config["seeds"]) * len(ALL_ARMS)
    for seed in (int(value) for value in config["seeds"]):
        parent_dir = run_dir / "parents" / f"seed-{seed}"
        parent_result_path = parent_dir / "RESULT.json"
        parent_path = parent_dir / "PARENT.pt"
        if parent_result_path.is_file() != parent_path.is_file():
            identity = f"no_intervention_adapter:seed-{seed}"
            pending.append(identity)
            incomplete_pairs.append(identity)
            parent = None
            parent_result = None
        elif not parent_result_path.is_file():
            pending.append(f"no_intervention_adapter:seed-{seed}")
            parent = None
            parent_result = None
        else:
            parent_result = _read_json(parent_result_path)
            parent = _load_payload(parent_path, str(parent_result["parent_sha256"]))
            if parent.get("vocab") != vocab:
                errors.append(f"parent vocabulary mismatch for seed {seed}")

        candidates: list[tuple[str, Path, Path, Mapping[str, Any] | None]] = []
        if parent is not None and parent_result is not None:
            candidates.append(
                ("no_intervention_adapter", parent_path, parent_result_path, parent)
            )
        for arm in TRAINED_ARMS:
            horse_dir = run_dir / "horses" / f"{arm}-seed-{seed}"
            result_path = horse_dir / "RESULT.json"
            artifact = horse_dir / "MODEL.pt"
            if result_path.is_file() != artifact.is_file():
                identity = f"{arm}:seed-{seed}"
                pending.append(identity)
                incomplete_pairs.append(identity)
            elif result_path.is_file():
                candidates.append((arm, artifact, result_path, None))
            else:
                pending.append(f"{arm}:seed-{seed}")

        for arm, artifact, result_path, loaded_parent in candidates:
            recorded = _read_json(result_path)
            if str(recorded.get("status")) != "COMPLETE":
                errors.append(f"{arm} seed {seed}: result is not terminal")
                continue
            if arm == "no_intervention_adapter":
                payload = dict(loaded_parent or {})
                expected_sha = str(recorded["parent_sha256"])
                null_carrier = False
            else:
                expected_sha = str(recorded["model_sha256"])
                payload = _load_payload(artifact, expected_sha)
                null_carrier = arm == "frozen_adapter_null"
            if payload.get("vocab") != vocab:
                errors.append(f"{arm} seed {seed}: artifact vocabulary mismatch")
            model = ReplayFrozenActionModel(len(vocab))
            model.load_state_dict(payload["model_state"], strict=True)
            predictions = _predict_actions(
                model,
                dataset.holdout_rows,
                stoi,
                itos,
                null_carrier=null_carrier,
            )
            replayed_predictions[(arm, seed)] = predictions
            metrics = replay_action_metrics(predictions)
            output_diagnostics = replay_output_diagnostics(predictions)
            count_score = _counting_accuracy(model, count_holdout, stoi, itos)
            mismatch_count = _prediction_mismatches(
                predictions, recorded["predictions"]
            )
            metric_delta = _max_numeric_delta(metrics, recorded["metrics"])
            count_delta = abs(count_score - float(recorded["counting_accuracy"]))
            frozen_exact = bool(
                parent is not None
                and _frozen_equal(parent["model_state"], payload["model_state"])
            )
            if mismatch_count:
                errors.append(
                    f"{arm} seed {seed}: {mismatch_count} prediction mismatches"
                )
            if metric_delta > tolerance:
                errors.append(f"{arm} seed {seed}: metric delta {metric_delta}")
            if count_delta > tolerance:
                errors.append(f"{arm} seed {seed}: counting delta {count_delta}")
            if not frozen_exact:
                errors.append(f"{arm} seed {seed}: frozen core differs")
            receipts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "artifact": str(artifact),
                    "artifact_sha256": _file_sha256(artifact),
                    "expected_artifact_sha256": expected_sha,
                    "recorded_result_sha256": _file_sha256(result_path),
                    "prediction_sha256": _stable_hash(predictions),
                    "prediction_mismatches": mismatch_count,
                    "max_metric_delta": metric_delta,
                    "counting_delta": count_delta,
                    "frozen_core_bit_identical": frozen_exact,
                    "metrics": metrics,
                    "output_diagnostics": output_diagnostics,
                    "counting_accuracy": count_score,
                }
            )

    per_seed_output_comparisons = {}
    for seed in (int(value) for value in config["seeds"]):
        contender = replayed_predictions.get((PRIMARY_ARM, seed))
        if contender is None:
            continue
        for control in CONTROLS:
            control_predictions = replayed_predictions.get((control, seed))
            if control_predictions is None:
                continue
            name = f"{PRIMARY_ARM}_vs_{control}:seed-{seed}"
            per_seed_output_comparisons[name] = paired_output_diagnostics(
                contender, control_predictions
            )

    if errors:
        status = "FAIL_PARTIAL_INDEPENDENT_REPLAY"
    elif receipts:
        status = "PASS_PARTIAL_INDEPENDENT_REPLAY_NO_VERDICT"
    else:
        status = "WAITING_FOR_TERMINAL_ARTIFACTS"
    result = {
        "schema": f"{SCHEMA}.partial",
        "status": status,
        "authority": AUTHORITY,
        "campaign_verdict": "NONE_PARTIAL_REPLAY_ONLY",
        "promotion": "NONE",
        "partial_unfreeze_authorized": False,
        "inference_path": INFERENCE_PATH,
        "run_dir": str(run_dir),
        "independent_dataset_builder": str(Path(__file__).resolve()),
        "independent_dataset_builder_sha256": _file_sha256(Path(__file__).resolve()),
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "dataset_manifest_matches": dataset_matches,
        "source_hashes_match": source_hashes_match,
        "vocabulary_matches": vocab_matches,
        "token_identity": token_identity,
        "completed_terminal_count": len(receipts),
        "expected_terminal_count": expected,
        "pending_terminal_artifacts": sorted(pending),
        "incomplete_terminal_pairs": sorted(incomplete_pairs),
        "model_receipts": receipts,
        "per_seed_output_comparisons": per_seed_output_comparisons,
        "errors": errors,
        "completed_at_utc": _utc_now(),
    }
    result["replay_sha256"] = _stable_hash(result)
    return result


def verify_run(run_dir: Path, *, tolerance: float = 1e-12) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    manifest = _read_json(run_dir / "RUN_MANIFEST.json")
    producer = _read_json(run_dir / "RESULT.json")
    config = manifest["config"]
    errors: list[str] = []

    provider = ClaySourceAdapter(Path(config["source_dir"]))
    dataset = build_replay_dataset(
        provider,
        rows_per_view=int(config["rows_per_view"]),
        holdout_rows=int(config["holdout_rows"]),
        seed=int(config["data_seed"]),
    )
    if dict(dataset.manifest) != dict(manifest["dataset"]):
        errors.append("dataset manifest mismatch")
    if dict(sorted(provider.source_hashes.items())) != dict(config["source_hashes"]):
        errors.append("source hash mismatch")

    count_train = _counting_rows(False)
    count_holdout = _counting_rows(True)
    vocab, stoi = _vocab_of(
        count_train,
        count_holdout,
        tuple(row.pair() for row in dataset.static_rows),
        tuple(row.pair() for row in dataset.multiview_rows),
        tuple(row.pair() for row in dataset.holdout_rows),
    )
    if _stable_hash(vocab) != manifest["vocab_sha256"]:
        errors.append("vocabulary hash mismatch")
    token_identity = byte_token_identity_receipt(vocab)
    if not token_identity["pass"]:
        errors.append("byte-token identity receipt failed")
    itos = {index: char for char, index in stoi.items()}

    recorded_by_arm = {
        arm: {int(row["seed"]): row for row in producer["per_arm"][arm]}
        for arm in ALL_ARMS
    }
    replay_by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ALL_ARMS}
    receipts = []
    for seed in (int(value) for value in config["seeds"]):
        parent_result = _read_json(run_dir / "parents" / f"seed-{seed}" / "RESULT.json")
        parent_path = run_dir / "parents" / f"seed-{seed}" / "PARENT.pt"
        parent = _load_payload(parent_path, str(parent_result["parent_sha256"]))
        if parent.get("vocab") != vocab:
            errors.append(f"parent vocabulary mismatch for seed {seed}")
        parent_state = parent["model_state"]

        for arm in ALL_ARMS:
            recorded = recorded_by_arm[arm][seed]
            if arm == "no_intervention_adapter":
                payload = parent
                artifact = parent_path
                recorded_result_path = (
                    run_dir / "parents" / f"seed-{seed}" / "RESULT.json"
                )
                null_carrier = False
            else:
                result_path = run_dir / "horses" / f"{arm}-seed-{seed}" / "RESULT.json"
                horse_result = _read_json(result_path)
                artifact = run_dir / "horses" / f"{arm}-seed-{seed}" / "MODEL.pt"
                recorded_result_path = result_path
                payload = _load_payload(artifact, str(horse_result["model_sha256"]))
                null_carrier = arm == "frozen_adapter_null"
            model = ReplayFrozenActionModel(len(vocab))
            model.load_state_dict(payload["model_state"], strict=True)
            predictions = _predict_actions(
                model,
                dataset.holdout_rows,
                stoi,
                itos,
                null_carrier=null_carrier,
            )
            metrics = replay_action_metrics(predictions)
            output_diagnostics = replay_output_diagnostics(predictions)
            count_score = _counting_accuracy(model, count_holdout, stoi, itos)
            mismatch_count = _prediction_mismatches(
                predictions, recorded["predictions"]
            )
            metric_delta = _max_numeric_delta(metrics, recorded["metrics"])
            count_delta = abs(count_score - float(recorded["counting_accuracy"]))
            frozen_exact = _frozen_equal(parent_state, payload["model_state"])
            if mismatch_count:
                errors.append(
                    f"{arm} seed {seed}: {mismatch_count} prediction mismatches"
                )
            if metric_delta > tolerance:
                errors.append(f"{arm} seed {seed}: metric delta {metric_delta}")
            if count_delta > tolerance:
                errors.append(f"{arm} seed {seed}: counting delta {count_delta}")
            if not frozen_exact:
                errors.append(f"{arm} seed {seed}: frozen core differs")
            replay_row = {
                "arm": arm,
                "seed": seed,
                "metrics": metrics,
                "predictions": predictions,
                "counting_accuracy": count_score,
            }
            replay_by_arm[arm].append(replay_row)
            receipts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "artifact": str(artifact),
                    "artifact_sha256": _file_sha256(artifact),
                    "recorded_result_sha256": _file_sha256(recorded_result_path),
                    "prediction_sha256": _stable_hash(predictions),
                    "prediction_mismatches": mismatch_count,
                    "max_metric_delta": metric_delta,
                    "counting_delta": count_delta,
                    "frozen_core_bit_identical": frozen_exact,
                    "output_diagnostics": output_diagnostics,
                }
            )

    comparisons = {}
    paired = {}
    for control in CONTROLS:
        name = f"{PRIMARY_ARM}_vs_{control}"
        comparisons[name] = {
            metric: _metric_comparison(
                replay_by_arm[PRIMARY_ARM], replay_by_arm[control], metric
            )
            for metric in ("accuracy", "macro_f1")
        }
        paired[name] = _paired_comparison(
            replay_by_arm[PRIMARY_ARM], replay_by_arm[control]
        )
    per_seed_output_comparisons = {}
    for seed in (int(value) for value in config["seeds"]):
        contender = next(
            row for row in replay_by_arm[PRIMARY_ARM] if int(row["seed"]) == seed
        )
        for control in CONTROLS:
            control_row = next(
                row for row in replay_by_arm[control] if int(row["seed"]) == seed
            )
            name = f"{PRIMARY_ARM}_vs_{control}:seed-{seed}"
            per_seed_output_comparisons[name] = paired_output_diagnostics(
                contender["predictions"], control_row["predictions"]
            )
    comparison_delta = _max_numeric_delta(comparisons, producer["comparisons"])
    paired_delta = _max_numeric_delta(paired, producer["paired_comparisons"])
    if comparison_delta > tolerance:
        errors.append(f"aggregate comparison delta {comparison_delta}")
    if paired_delta > tolerance:
        errors.append(f"aggregate paired delta {paired_delta}")

    max_metric_delta = max(
        (float(row["max_metric_delta"]) for row in receipts), default=0.0
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
        "inference_path": INFERENCE_PATH,
        "run_dir": str(run_dir),
        "independent_dataset_builder": str(Path(__file__).resolve()),
        "independent_dataset_builder_sha256": _file_sha256(Path(__file__).resolve()),
        "producer_result_sha256": _file_sha256(run_dir / "RESULT.json"),
        "dataset_manifest_sha256": dataset.manifest["manifest_sha256"],
        "token_identity": token_identity,
        "model_receipts": receipts,
        "comparisons": comparisons,
        "paired_comparisons": paired,
        "per_seed_output_comparisons": per_seed_output_comparisons,
        "max_metric_delta": max_metric_delta,
        "aggregate_comparison_delta": comparison_delta,
        "aggregate_paired_delta": paired_delta,
        "errors": errors,
        "completed_at_utc": _utc_now(),
    }
    result["replay_sha256"] = _stable_hash(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument(
        "--partial-completed",
        action="store_true",
        help=(
            "replay only completed parent/horse artifacts and emit no campaign "
            "verdict"
        ),
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="print a compact receipt summary while retaining full JSON on disk",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    if args.partial_completed:
        result = verify_completed_artifacts(args.run_dir, tolerance=args.tolerance)
        default_output = args.run_dir / "PARTIAL_INDEPENDENT_REPLAY.json"
    else:
        result = verify_run(args.run_dir, tolerance=args.tolerance)
        default_output = args.run_dir / "INDEPENDENT_REPLAY.json"
    output = args.output or default_output
    _atomic_json(output, result)
    printable = (
        {
            "status": result["status"],
            "completed_terminal_count": result.get("completed_terminal_count"),
            "expected_terminal_count": result.get("expected_terminal_count"),
            "error_count": len(result["errors"]),
            "output": str(output),
            "replay_sha256": result["replay_sha256"],
        }
        if args.summary_only
        else result
    )
    print(json.dumps(printable, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
