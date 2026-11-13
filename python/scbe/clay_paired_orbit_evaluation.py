"""Independent large-holdout diagnostic for a completed paired-orbit run."""

from __future__ import annotations

import json
import os
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import torch

from python.scbe.clay_paired_orbit_training import (
    ACTION_COUNT,
    ARMS,
    PRIMARY_ARM,
    ClaySourceAdapter,
    OrbitBank,
    PairedOrbitError,
    StandardActionMLP,
    _atomic_torch,
    build_evaluation_banks,
    evaluate,
    file_sha256,
    sha256_json,
    utc_now,
)

SCHEMA = "clay.paired-orbit-large-holdout-diagnostic.v1"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _mean_sd(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def _label_counts(bank: OrbitBank) -> list[int]:
    return torch.bincount(bank.labels, minlength=ACTION_COUNT).tolist()


def _paired_delta_receipt(
    rows: Sequence[Mapping[str, Any]], candidate: str, control: str, metric: str
) -> dict[str, Any]:
    index = {
        (int(row["held_sector"]), int(row["seed"]), str(row["arm"])): row
        for row in rows
    }
    keys = sorted(
        (held, seed)
        for held, seed, arm in index
        if arm == candidate and (held, seed, control) in index
    )
    values = [
        float(index[(held, seed, candidate)]["holdout"][metric])
        - float(index[(held, seed, control)]["holdout"][metric])
        for held, seed in keys
    ]
    if not values:
        raise PairedOrbitError("paired comparison has no matched rows")
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    mean = statistics.fmean(values)
    return {
        "candidate": candidate,
        "control": control,
        "metric": metric,
        "matched_pairs": len(values),
        "deltas": values,
        "mean_delta": mean,
        "sd_delta": sd,
        "two_sd_delta": 2.0 * sd,
        "all_positive": all(value > 0 for value in values),
        "positive_pairs": sum(value > 0 for value in values),
        "clears_two_sd_delta": mean > 2.0 * sd,
    }


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        arms[arm] = {
            f"{split}_{metric}": _mean_sd(
                [float(row[split][metric]) for row in selected]
            )
            for split in ("holdout", "anchor")
            for metric in (
                "accuracy",
                "macro_f1",
                "stable_macro_f1",
                "worst_class_accuracy",
                "worst_stable_class_accuracy",
                "cross_entropy",
            )
        }
    comparisons = {
        f"{candidate}_vs_static_unique": {
            metric: _paired_delta_receipt(rows, candidate, "static_unique", metric)
            for metric in (
                "accuracy",
                "macro_f1",
                "stable_macro_f1",
                "worst_class_accuracy",
                "worst_stable_class_accuracy",
            )
        }
        for candidate in ARMS[1:]
    }
    comparisons["paired_grouped_vs_shuffled"] = {
        metric: _paired_delta_receipt(
            rows, PRIMARY_ARM, "paired_orbit_shuffled", metric
        )
        for metric in ("accuracy", "macro_f1", "worst_class_accuracy")
    }
    comparisons["paired_grouped_vs_independent"] = {
        metric: _paired_delta_receipt(
            rows, PRIMARY_ARM, "curriculum_independent", metric
        )
        for metric in ("accuracy", "macro_f1", "worst_class_accuracy")
    }
    return {"arms": arms, "paired_comparisons": comparisons}


def _save_bank(path: Path, bank: OrbitBank) -> None:
    _atomic_torch(
        path,
        {
            "features": bank.features,
            "labels": bank.labels,
            "sectors": bank.sectors,
            "groups": bank.groups,
            "views": bank.views,
            "manifest_sha256": bank.manifest_sha256,
        },
    )


def _load_bank(path: Path, name: str) -> OrbitBank:
    payload = torch.load(path, map_location="cpu", weights_only=True)
    bank = OrbitBank(
        name,
        payload["features"],
        payload["labels"],
        payload["sectors"],
        payload["groups"],
        payload["views"],
        False,
        payload["manifest_sha256"],
    )
    if not bank.verify():
        raise PairedOrbitError(f"saved evaluation bank failed receipt: {path}")
    return bank


def render_diagnostic(report: Mapping[str, Any]) -> str:
    scale = float(report["evaluation_scale_factor"])
    lines = [
        "# Paired-Orbit Large-Holdout Diagnostic",
        "",
        f"Diagnostic SHA-256: `{report['diagnostic_sha256']}`",
        "",
        "This post-hoc evaluation uses new, independently seeded held and anchor",
        f"banks with {report['records_per_split_per_fold']:,} rows per fold "
        f"({scale:.2f}x the original evaluation size). It diagnoses rare-class",
        "stability; it is not a promotion gate.",
        "",
        "| Data arm | Held acc | All-supported F1 | Stable F1 | Worst stable | Anchor acc |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in ARMS:
        row = report["aggregate"]["arms"][arm]
        lines.append(
            f"| {arm} | {row['holdout_accuracy']['mean']:.4f} | "
            f"{row['holdout_macro_f1']['mean']:.4f} | "
            f"{row['holdout_stable_macro_f1']['mean']:.4f} | "
            f"{row['holdout_worst_stable_class_accuracy']['mean']:.4f} | "
            f"{row['anchor_accuracy']['mean']:.4f} |"
        )
    lines.extend(
        (
            "",
            "All checkpoints are unchanged from the completed training campaign.",
            "No evaluation result authorizes promotion or partial unfreeze.",
            "",
        )
    )
    return "\n".join(lines)


def evaluate_saved_campaign(
    run_root: str | Path,
    provider: ClaySourceAdapter,
    *,
    records: int = 10_000,
    seed_offset: int = 500_000,
    device_name: str = "auto",
    min_stable_support: int = 1,
) -> dict[str, Any]:
    root = Path(run_root).resolve(strict=True)
    campaign = json.loads((root / "CAMPAIGN.json").read_text(encoding="utf-8"))
    result = json.loads((root / "RESULT.json").read_text(encoding="utf-8"))
    if result.get("state") != "COMPLETE_MECHANICS_NO_PROMOTION":
        raise PairedOrbitError("source campaign is not complete")
    if records < 1:
        raise PairedOrbitError("diagnostic record count must be positive")
    if min_stable_support < 1:
        raise PairedOrbitError("minimum stable support must be positive")
    configuration = campaign["configuration"]
    held_sectors = [int(value) for value in configuration["held_sectors"]]
    hidden_width = int(configuration["hidden_width"])
    source_records = int(configuration["evaluation_records"])
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)

    output = root / "large-holdout-diagnostic"
    previous_path = output / "RESULT.json"
    previous = (
        json.loads(previous_path.read_text(encoding="utf-8"))
        if previous_path.is_file()
        else None
    )
    can_reuse = bool(
        previous
        and previous.get("source_result_sha256") == result["result_sha256"]
        and int(previous.get("records_per_split_per_fold", -1)) == records
        and int(previous.get("seed_offset", -1)) == seed_offset
    )

    eval_banks: dict[int, tuple[OrbitBank, OrbitBank]] = {}
    fold_receipts: dict[str, Any] = {}
    for held in held_sectors:
        folder = output / "inputs" / f"held-{held}"
        holdout_path = folder / "holdout.pt"
        anchor_path = folder / "anchor.pt"
        if can_reuse and holdout_path.is_file() and anchor_path.is_file():
            holdout = _load_bank(holdout_path, "holdout")
            anchor = _load_bank(anchor_path, "anchor")
            if (
                holdout.features.shape[0] != records
                or anchor.features.shape[0] != records
            ):
                raise PairedOrbitError("reused evaluation bank has the wrong row count")
        else:
            holdout, anchor = build_evaluation_banks(
                provider,
                held_sector=held,
                count=records,
                seed=2026111300 + held + seed_offset,
            )
            _save_bank(holdout_path, holdout)
            _save_bank(anchor_path, anchor)
        eval_banks[held] = (holdout, anchor)
        fold_receipts[str(held)] = {
            "holdout_manifest_sha256": holdout.manifest_sha256,
            "anchor_manifest_sha256": anchor.manifest_sha256,
            "holdout_label_counts": _label_counts(holdout),
            "anchor_label_counts": _label_counts(anchor),
        }

    rows: list[dict[str, Any]] = []
    for source_row in result["horses"]:
        held = int(source_row["held_sector"])
        arm = str(source_row["arm"])
        seed = int(source_row["seed"])
        checkpoint = root / "horses" / f"held-{held}" / f"{arm}-seed-{seed}" / "BEST.pt"
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model = StandardActionMLP(hidden_width).to(device)
        model.load_state_dict(state, strict=True)
        holdout, anchor = eval_banks[held]
        rows.append(
            {
                "held_sector": held,
                "arm": arm,
                "seed": seed,
                "checkpoint_sha256": file_sha256(checkpoint),
                "holdout": evaluate(
                    model,
                    holdout,
                    device,
                    min_stable_support=min_stable_support,
                ),
                "anchor": evaluate(
                    model,
                    anchor,
                    device,
                    min_stable_support=min_stable_support,
                ),
            }
        )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": utc_now(),
        "evidence_class": "posthoc_large_holdout_diagnostic_not_promotion_gate",
        "source_result_sha256": result["result_sha256"],
        "source_campaign_sha256": campaign["campaign_sha256"],
        "implementation_sha256": file_sha256(Path(__file__)),
        "records_per_split_per_fold": records,
        "source_records_per_split_per_fold": source_records,
        "evaluation_scale_factor": records / source_records,
        "seed_offset": seed_offset,
        "min_stable_support": min_stable_support,
        "reused_input_banks": can_reuse,
        "device": str(device),
        "fold_receipts": fold_receipts,
        "rows": rows,
        "aggregate": _aggregate(rows),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    report = {**body, "diagnostic_sha256": sha256_json(body)}
    _atomic_json(output / "RESULT.json", report)
    _atomic_text(output / "MARKET_REPORT.md", render_diagnostic(report))
    _atomic_json(
        output / "STATUS.json",
        {
            "schema": SCHEMA,
            "state": "COMPLETE_DIAGNOSTIC_NO_PROMOTION",
            "diagnostic_sha256": report["diagnostic_sha256"],
            "promotion_authorized": False,
        },
    )
    return report


__all__ = [
    "SCHEMA",
    "evaluate_saved_campaign",
    "render_diagnostic",
]
