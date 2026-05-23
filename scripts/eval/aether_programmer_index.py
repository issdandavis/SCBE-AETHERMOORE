from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "eval" / "aether_programmer_index.v1.json"


@dataclass(frozen=True)
class TaskScore:
    task_id: str
    track_id: str
    entry_pass: bool
    quality_score: float
    weighted_quality: float


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp01(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _readiness_label(score: float, bands: list[dict[str, Any]]) -> str:
    for band in bands:
        if float(band["min"]) <= score <= float(band["max"]):
            return str(band["label"])
    return "unclassified"


def _trend_status(history: list[dict[str, Any]], trend_control: dict[str, Any]) -> dict[str, Any]:
    if not history:
        return {
            "status": "no_history",
            "above_true_negative_floor": True,
            "requires_recovery": False,
            "exploration_complete": False,
            "message": "No trend history supplied.",
        }

    floor = float(trend_control["true_negative_floor"])
    decline_window = int(trend_control["decline_window_turns"])
    latest = history[-1]
    latest_score = float(latest.get("score", 0.0))
    above_floor = latest_score >= floor

    if len(history) < decline_window:
        return {
            "status": "insufficient_history",
            "above_true_negative_floor": above_floor,
            "requires_recovery": not above_floor,
            "exploration_complete": above_floor,
            "message": "Not enough turns to judge multi-turn decline.",
        }

    window = history[-decline_window:]
    scores = [float(turn.get("score", 0.0)) for turn in window]
    declining = all(scores[i] < scores[i - 1] for i in range(1, len(scores)))
    cause_supplied = any(str(turn.get("cause_note", "")).strip() for turn in window)
    recovery_attempted = any(bool(turn.get("recovery_attempted")) for turn in window)
    requires_recovery = (not above_floor) or (declining and not (cause_supplied and recovery_attempted))

    if requires_recovery:
        status = "recovery_required"
    elif declining:
        status = "controlled_decline"
    else:
        status = "stable_or_recovering"

    return {
        "status": status,
        "above_true_negative_floor": above_floor,
        "requires_recovery": requires_recovery,
        "exploration_complete": above_floor and not requires_recovery,
        "window_scores": scores,
        "message": trend_control["rule"],
    }


def _entry_pass(task: dict[str, Any], required_checks: list[str]) -> bool:
    checks = task.get("checks", {})
    return bool(task.get("passed")) and all(bool(checks.get(check)) for check in required_checks)


def _quality_score(task: dict[str, Any], dimensions: list[dict[str, Any]]) -> float:
    quality = task.get("quality", {})
    total_weight = sum(float(dim["weight"]) for dim in dimensions)
    if total_weight <= 0:
        return 0.0
    weighted = sum(_clamp01(quality.get(dim["id"], 0.0)) * float(dim["weight"]) for dim in dimensions)
    return weighted / total_weight


def score_run(run_packet: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    evidence_level = run_packet.get("evidence_level", "unrun_or_planned")
    evidence_multiplier = float(config["evidence_multipliers"].get(evidence_level, 0.0))
    required_checks = list(config["entry_gate"]["required_checks"])
    dimensions = list(config["quality_dimensions"])
    track_weights = {track["track_id"]: float(track["weight"]) for track in config["tracks"]}
    refinement_loop = config["failure_refinement_loop"]
    refinement_stages = [stage["id"] for stage in refinement_loop["stages"]]

    task_scores: list[TaskScore] = []
    solution_backlog: list[dict[str, Any]] = []

    for task in run_packet.get("tasks", []):
        track_id = str(task.get("track_id", ""))
        task_id = str(task.get("task_id", ""))
        entry_pass = _entry_pass(task, required_checks)
        quality = _quality_score(task, dimensions) if entry_pass else 0.0
        task_scores.append(
            TaskScore(
                task_id=task_id,
                track_id=track_id,
                entry_pass=entry_pass,
                quality_score=quality,
                weighted_quality=quality * track_weights.get(track_id, 0.0),
            )
        )
        if not entry_pass:
            solution_backlog.append(
                {
                    "task_id": task_id,
                    "track_id": track_id,
                    "failure_mode": task.get("failure_mode", "unspecified"),
                    "proposed_solution": task.get("proposed_solution", "add a focused regression and rerun"),
                    "candidate_solution_budget": refinement_loop["candidate_solution_budget"],
                    "rerun_strategy": refinement_loop["name"],
                    "required_stages": refinement_stages,
                }
            )

    track_reports: list[dict[str, Any]] = []
    raw_score = 0.0
    for track in config["tracks"]:
        track_id = track["track_id"]
        scores = [task for task in task_scores if task.track_id == track_id]
        if not scores:
            pass_rate = 0.0
            average_quality = 0.0
        else:
            passed = [task for task in scores if task.entry_pass]
            pass_rate = len(passed) / len(scores)
            average_quality = sum(task.quality_score for task in passed) / len(passed) if passed else 0.0
        track_score = float(track["weight"]) * pass_rate * average_quality * evidence_multiplier
        raw_score += track_score
        track_reports.append(
            {
                "track_id": track_id,
                "weight": track["weight"],
                "task_count": len(scores),
                "pass_rate": round(pass_rate, 4),
                "average_pass_quality": round(average_quality, 4),
                "score": round(track_score, 4),
            }
        )

    final_score = round(raw_score, 4)
    return {
        "schema_version": "aether_programmer_index_report_v1",
        "run_id": run_packet.get("run_id", "unknown"),
        "evidence_level": evidence_level,
        "evidence_multiplier": evidence_multiplier,
        "score": final_score,
        "readiness": _readiness_label(final_score, config["readiness_bands"]),
        "trend": _trend_status(run_packet.get("history", []), config["failure_refinement_loop"]["trend_control"]),
        "tracks": track_reports,
        "solution_backlog": solution_backlog,
        "task_scores": [
            {
                "task_id": task.task_id,
                "track_id": task.track_id,
                "entry_pass": task.entry_pass,
                "quality_score": round(task.quality_score, 4),
            }
            for task in task_scores
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an Aether Programmer Index run packet.")
    parser.add_argument("run_packet", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = score_run(_load_json(args.run_packet), _load_json(args.config))
    output = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
