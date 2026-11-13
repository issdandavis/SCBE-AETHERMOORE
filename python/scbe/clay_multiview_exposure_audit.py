"""Independently reconstruct exact row exposure for completed Clay campaigns.

The auditor does not import the trainer or inspect learned metrics.  It verifies
the campaign and input-bank receipts, proves that every scheduled horse
completed with the declared data manifest, and replays the trainer's dedicated
CPU sampling stream into exact per-row count vectors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

SCHEMA = "clay.multiview-exposure-audit.v2"
CAMPAIGN_SCHEMA = "clay.multiview-factor-coverage-campaign.v1"
COMPLETE_STATE = "COMPLETE_MECHANICS_NO_PROMOTION"
FEATURE_WIDTH = 37
ACTION_COUNT = 5


class ExposureAuditError(RuntimeError):
    """Raised when a campaign cannot support an exact exposure receipt."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_sha256(value: Tensor) -> str:
    cpu = value.detach().cpu().contiguous()
    header = f"{cpu.dtype}|{tuple(cpu.shape)}|".encode("ascii")
    return hashlib.sha256(header + cpu.numpy().tobytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExposureAuditError(f"missing receipt: {path}") from exc
    if not isinstance(payload, dict):
        raise ExposureAuditError(f"receipt must be a JSON object: {path}")
    return payload


def _verify_json_receipt(
    path: Path, payload: Mapping[str, Any], digest_field: str
) -> str:
    claimed = str(payload.get(digest_field, ""))
    body = dict(payload)
    body.pop(digest_field, None)
    if len(claimed) != 64 or sha256_json(body) != claimed:
        raise ExposureAuditError(f"{path.name} has an invalid {digest_field}")
    return claimed


def _bank_body(name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    features = payload["features"]
    return {
        "name": name,
        "records": int(features.shape[0]),
        "feature_sha256": tensor_sha256(features),
        "label_sha256": tensor_sha256(payload["labels"]),
        "sector_sha256": tensor_sha256(payload["sectors"]),
        "group_sha256": tensor_sha256(payload["groups"]),
        "view_sha256": tensor_sha256(payload["views"]),
        "complete_groups": bool(payload["complete_groups"]),
    }


def verify_bank(path: Path, *, name: str) -> dict[str, Any]:
    """Verify one producer bank without importing the producer implementation."""

    if not path.is_file():
        raise ExposureAuditError(f"missing training bank: {path}")
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise ExposureAuditError(f"could not load training bank: {path}") from exc
    required = {
        "features",
        "labels",
        "sectors",
        "groups",
        "views",
        "complete_groups",
        "manifest_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ExposureAuditError(f"training bank schema differs: {path}")
    features = payload["features"]
    vectors = tuple(payload[key] for key in ("labels", "sectors", "groups", "views"))
    if not isinstance(features, Tensor) or features.ndim != 2:
        raise ExposureAuditError(f"training features are not a matrix: {path}")
    records = int(features.shape[0])
    if features.shape != (records, FEATURE_WIDTH) or records < 1:
        raise ExposureAuditError(f"training feature shape differs: {path}")
    if not bool(torch.isfinite(features).all()):
        raise ExposureAuditError(f"training features are non-finite: {path}")
    if any(
        not isinstance(value, Tensor)
        or value.shape != (records,)
        or value.dtype != torch.int64
        for value in vectors
    ):
        raise ExposureAuditError(f"training index vectors differ: {path}")
    labels = payload["labels"]
    if bool(torch.any((labels < 0) | (labels >= ACTION_COUNT))):
        raise ExposureAuditError(
            f"training labels are outside the action range: {path}"
        )
    if not isinstance(payload["complete_groups"], bool):
        raise ExposureAuditError(f"complete_groups is not boolean: {path}")
    manifest = str(payload["manifest_sha256"])
    if manifest != sha256_json(_bank_body(name, payload)):
        raise ExposureAuditError(f"training bank manifest drift: {path}")
    return {
        "path": str(path.resolve()),
        "file_sha256": file_sha256(path),
        "manifest_sha256": manifest,
        "records": records,
        "feature_width": int(features.shape[1]),
        "complete_groups": payload["complete_groups"],
    }


def replay_uniform_exposure(
    record_count: int,
    *,
    held_sector: int,
    seed: int,
    steps: int,
    batch_size: int,
    call_block: int = 256,
) -> Tensor:
    """Replay exact producer call boundaries into an int64 row-count vector."""

    if min(record_count, held_sector, seed, steps, batch_size, call_block) < 1:
        raise ExposureAuditError("replay dimensions must be positive")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(held_sector * 1_000_000 + seed)
    counts = torch.zeros(record_count, dtype=torch.int64)
    remaining = steps
    while remaining:
        calls = min(call_block, remaining)
        draws = torch.cat(
            [
                torch.randint(
                    0,
                    record_count,
                    (batch_size,),
                    generator=generator,
                    dtype=torch.int64,
                )
                for _ in range(calls)
            ]
        )
        counts += torch.bincount(draws, minlength=record_count)
        remaining -= calls
    if int(counts.sum().item()) != steps * batch_size:
        raise ExposureAuditError("reconstructed exposure total differs")
    return counts


def _count_report(
    counts: Tensor, *, held_sector: int, seed: int, arms: Sequence[str]
) -> dict[str, Any]:
    source = counts.to(torch.float64)
    total = int(counts.sum().item())
    quantiles = torch.quantile(
        source, torch.tensor((0.0, 0.05, 0.5, 0.95, 1.0), dtype=torch.float64)
    ).tolist()
    positive = source[source > 0]
    probabilities = positive / float(total)
    entropy = float(-(probabilities * torch.log(probabilities)).sum().item())
    denominator = math.log(int(counts.numel())) if counts.numel() > 1 else 1.0
    frequencies: dict[str, int] = {}
    unique_counts, frequency_counts = torch.unique(counts, return_counts=True)
    for count, frequency in zip(
        unique_counts.tolist(), frequency_counts.tolist(), strict=True
    ):
        frequencies[str(int(count))] = int(frequency)
    return {
        "schedule_id": f"held-{held_sector}-seed-{seed}",
        "held_sector": held_sector,
        "seed": seed,
        "generator_seed": held_sector * 1_000_000 + seed,
        "applies_to_arms": list(arms),
        "draws": total,
        "records": int(counts.numel()),
        "unique_rows_seen": int((counts > 0).sum().item()),
        "unseen_rows": int((counts == 0).sum().item()),
        "row_exposure": dict(
            zip(("min", "p05", "median", "p95", "max"), quantiles, strict=True)
        ),
        "mean_exposure": float(source.mean().item()),
        "effective_rows_inverse_simpson": total
        * total
        / float(torch.sum(source**2).item()),
        "entropy_evenness": entropy / denominator if denominator else 1.0,
        "count_frequency": frequencies,
        "counts_sha256": tensor_sha256(counts),
        "row_exposure_counts": counts.tolist(),
    }


def _expected_horses(
    held_sectors: Sequence[int], arms: Sequence[str], seeds: Sequence[int]
) -> set[tuple[int, str, int]]:
    return {
        (int(held), str(arm), int(seed))
        for held in held_sectors
        for arm in arms
        for seed in seeds
    }


def audit_completed_campaign(root: str | Path) -> dict[str, Any]:
    """Build an exact, outcome-agnostic exposure receipt for one completed run."""

    campaign_root = Path(root).resolve()
    campaign_path = campaign_root / "CAMPAIGN.json"
    result_path = campaign_root / "RESULT.json"
    campaign = _load_json(campaign_path)
    result = _load_json(result_path)
    if campaign.get("schema") != CAMPAIGN_SCHEMA:
        raise ExposureAuditError("campaign schema is not supported")
    campaign_sha = _verify_json_receipt(campaign_path, campaign, "campaign_sha256")
    result_sha = _verify_json_receipt(result_path, result, "result_sha256")
    if result.get("state") != COMPLETE_STATE:
        raise ExposureAuditError("campaign is not complete")
    if result.get("campaign_sha256") != campaign_sha:
        raise ExposureAuditError("result does not belong to campaign")

    config = campaign.get("configuration")
    if not isinstance(config, dict) or result.get("configuration") != config:
        raise ExposureAuditError("campaign/result configuration mismatch")
    arms = tuple(str(value) for value in config["arms"])
    seeds = tuple(int(value) for value in config["seeds"])
    held_sectors = tuple(int(value) for value in config["held_sectors"])
    steps = int(config["steps"])
    batch_size = int(config["batch_size"])
    declared_records = int(config["records_per_arm"])
    if (
        not arms
        or not seeds
        or not held_sectors
        or min(steps, batch_size, declared_records) < 1
    ):
        raise ExposureAuditError("campaign dimensions are invalid")

    expected = _expected_horses(held_sectors, arms, seeds)
    result_horses = result.get("horses")
    if not isinstance(result_horses, list):
        raise ExposureAuditError("aggregate result has no horse ledger")
    observed = {
        (int(row["held_sector"]), str(row["arm"]), int(row["seed"]))
        for row in result_horses
        if isinstance(row, dict)
    }
    if len(result_horses) != len(expected) or observed != expected:
        raise ExposureAuditError("aggregate horse ledger is incomplete or duplicated")

    banks: dict[str, dict[str, Any]] = {}
    records_by_held: dict[int, int] = {}
    for held in held_sectors:
        arm_records: set[int] = set()
        for arm in arms:
            bank_path = campaign_root / "inputs" / f"held-{held}" / f"{arm}.pt"
            receipt = verify_bank(bank_path, name=arm)
            banks[f"held-{held}/{arm}"] = receipt
            arm_records.add(int(receipt["records"]))
        if arm_records != {declared_records}:
            raise ExposureAuditError(f"arm row counts differ in held sector {held}")
        records_by_held[held] = declared_records

    horse_receipts: list[dict[str, Any]] = []
    for held, arm, seed in sorted(expected):
        horse_path = (
            campaign_root
            / "horses"
            / f"held-{held}"
            / f"{arm}-seed-{seed}"
            / "RESULT.json"
        )
        horse = _load_json(horse_path)
        horse_sha = _verify_json_receipt(horse_path, horse, "result_sha256")
        bank = banks[f"held-{held}/{arm}"]
        if (
            int(horse.get("held_sector", -1)) != held
            or str(horse.get("arm", "")) != arm
            or int(horse.get("seed", -1)) != seed
            or int(horse.get("steps", -1)) != steps
            or int(horse.get("batch_size", -1)) != batch_size
            or horse.get("data_manifest_sha256") != bank["manifest_sha256"]
        ):
            raise ExposureAuditError(f"horse lineage differs: {horse_path}")
        horse_receipts.append(
            {
                "held_sector": held,
                "arm": arm,
                "seed": seed,
                "path": str(horse_path),
                "file_sha256": file_sha256(horse_path),
                "result_sha256": horse_sha,
            }
        )

    schedules = []
    for held in held_sectors:
        for seed in seeds:
            counts = replay_uniform_exposure(
                records_by_held[held],
                held_sector=held,
                seed=seed,
                steps=steps,
                batch_size=batch_size,
            )
            schedules.append(
                _count_report(counts, held_sector=held, seed=seed, arms=arms)
            )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "auditor_file_sha256": file_sha256(Path(__file__).resolve()),
        "sampler_reference_file_sha256": file_sha256(
            Path(__file__).resolve().with_name("clay_paired_orbit_training.py")
        ),
        "campaign_root": str(campaign_root),
        "campaign_file_sha256": file_sha256(campaign_path),
        "campaign_sha256": campaign_sha,
        "producer_result_file_sha256": file_sha256(result_path),
        "producer_result_sha256": result_sha,
        "sampling_contract": {
            "algorithm": "torch.randint uniform with replacement",
            "generator": "dedicated torch.Generator(device=cpu) per horse",
            "generator_seed": "held_sector * 1000000 + model_seed",
            "call_shape": [batch_size],
            "calls_per_horse": steps,
            "draws_per_horse": steps * batch_size,
        },
        "configuration": {
            "arms": list(arms),
            "seeds": list(seeds),
            "held_sectors": list(held_sectors),
            "steps": steps,
            "batch_size": batch_size,
            "records_per_arm": declared_records,
        },
        "banks": banks,
        "horse_receipts": horse_receipts,
        "schedules": schedules,
        "matched_arms_share_positional_schedule": True,
        "outcome_values_used_for_exposure": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "audit_sha256": sha256_json(body)}


def write_audit(path: str | Path, report: Mapping[str, Any]) -> Path:
    output = Path(path).resolve()
    if output.exists():
        raise ExposureAuditError(f"refusing to overwrite exposure receipt: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, output)
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.campaign.resolve()
    output = args.output.resolve() if args.output else root / "EXPOSURE_AUDIT_V2.json"
    report = audit_completed_campaign(root)
    write_audit(output, report)
    summary = {
        "status": "PASS_EXACT_EXPOSURE_AUDIT_NO_PROMOTION",
        "output": str(output),
        "audit_sha256": report["audit_sha256"],
        "horses": len(report["horse_receipts"]),
        "schedules": len(report["schedules"]),
        "draws_per_horse": report["sampling_contract"]["draws_per_horse"],
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


__all__ = [
    "CAMPAIGN_SCHEMA",
    "ExposureAuditError",
    "SCHEMA",
    "audit_completed_campaign",
    "canonical_json",
    "file_sha256",
    "main",
    "replay_uniform_exposure",
    "sha256_json",
    "tensor_sha256",
    "verify_bank",
    "write_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
