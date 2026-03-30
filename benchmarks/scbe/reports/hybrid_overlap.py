"""Evidence-first overlap analysis for SCBE governance detectors.

Runs four lanes on the same prompts:
  - classifier only
  - structural RuntimeGate only
  - trichromatic score only
  - fused hybrid RuntimeGate

The artifact is designed to answer:
  - when does the system fail?
  - why did it fail?
  - how did each subsystem contribute?

Usage:
    python -m benchmarks.scbe.reports.hybrid_overlap
    python -m benchmarks.scbe.reports.hybrid_overlap --scale 10 --seed 42
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

from benchmarks.scbe.attacks.generator import generate_attacks
from src.governance.runtime_gate import (
    DEFAULT_CLASSIFIER_MODEL_DIR,
    Decision,
    RuntimeGate,
)
from tests.adversarial.attack_corpus import BASELINE_CLEAN


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SCBE hybrid overlap evaluation")
    parser.add_argument("--scale", type=int, default=10, help="attacks per category")
    parser.add_argument("--seed", type=int, default=42, help="generator seed")
    parser.add_argument(
        "--coords-backend",
        type=str,
        default="semantic",
        choices=["stats", "semantic", "auto"],
        help="RuntimeGate tongue-coordinate backend",
    )
    parser.add_argument(
        "--classifier-model-dir",
        type=str,
        default=DEFAULT_CLASSIFIER_MODEL_DIR,
        help="path to sklearn classifier artifact directory",
    )
    parser.add_argument(
        "--classifier-quarantine-threshold",
        type=float,
        default=0.75,
        help="classifier review threshold",
    )
    parser.add_argument(
        "--classifier-deny-threshold",
        type=float,
        default=0.97,
        help="classifier deny threshold",
    )
    parser.add_argument(
        "--trichromatic-quarantine-threshold",
        type=float,
        default=0.48,
        help="trichromatic review threshold",
    )
    parser.add_argument(
        "--trichromatic-deny-threshold",
        type=float,
        default=0.76,
        help="trichromatic deny threshold",
    )
    parser.add_argument(
        "--calibration-count",
        type=int,
        default=5,
        help="number of benign prompts used to calibrate stateful lanes",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/benchmark/hybrid_overlap_latest.json",
        help="stable output path for latest report",
    )
    return parser.parse_args()


def overlap_key(classifier_detected: bool, gate_detected: bool, trichromatic_detected: bool) -> str:
    active = []
    if classifier_detected:
        active.append("classifier")
    if gate_detected:
        active.append("gate")
    if trichromatic_detected:
        active.append("trichromatic")
    return "+".join(active) if active else "none"


def hybrid_union_bucket(union_detected: bool, hybrid_detected: bool) -> str:
    if union_detected and hybrid_detected:
        return "both_detect"
    if union_detected and not hybrid_detected:
        return "union_only"
    if not union_detected and hybrid_detected:
        return "hybrid_only"
    return "neither"


def severity_from_thresholds(score: float, quarantine_threshold: float, deny_threshold: float) -> str:
    if score >= deny_threshold:
        return Decision.DENY.value
    if score >= quarantine_threshold:
        return Decision.QUARANTINE.value
    return Decision.ALLOW.value


def load_classifier(model_dir: str) -> Tuple[Any, Any]:
    import joblib  # type: ignore[import-untyped]

    path = Path(model_dir)
    model = joblib.load(path / "model.joblib")
    vectorizer = joblib.load(path / "vectorizer.joblib")
    return model, vectorizer


def run_classifier_lane(
    prompts: Iterable[Dict[str, Any]],
    model: Any,
    vectorizer: Any,
    quarantine_threshold: float,
    deny_threshold: float,
    *,
    mode: str,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for sample in prompts:
        prompt = sample["prompt"]
        vector = vectorizer.transform([prompt])
        predicted_label = int(np.asarray(model.predict(vector)).reshape(-1)[0])
        if hasattr(model, "predict_proba"):
            score = float(model.predict_proba(vector)[0][1])
        elif hasattr(model, "decision_function"):
            raw = float(np.asarray(model.decision_function(vector)).reshape(-1)[0])
            score = float(1.0 / (1.0 + np.exp(-raw)))
        else:
            score = float(predicted_label)

        if mode == "raw":
            detected = predicted_label == 1
            severity = Decision.QUARANTINE.value if detected else Decision.ALLOW.value
        else:
            severity = severity_from_thresholds(score, quarantine_threshold, deny_threshold)
            detected = severity != Decision.ALLOW.value
        records.append(
            {
                "id": sample["id"],
                "class": sample["class"],
                "prompt": prompt,
                "detected": detected,
                "severity": severity,
                "score": score,
                "predicted_label": predicted_label,
                "mode": mode,
            }
        )
    return records


def calibrate_gate(gate: RuntimeGate, calibration_prompts: List[Dict[str, Any]]) -> None:
    for sample in calibration_prompts:
        gate.evaluate(sample["prompt"])


def run_gate_lane(
    prompts: Iterable[Dict[str, Any]],
    calibration_prompts: List[Dict[str, Any]],
    *,
    coords_backend: str,
) -> List[Dict[str, Any]]:
    gate = RuntimeGate(coords_backend=coords_backend, use_classifier=False, use_trichromatic_governance=False)
    calibrate_gate(gate, calibration_prompts)
    records: List[Dict[str, Any]] = []
    for sample in prompts:
        result = gate.evaluate(sample["prompt"])
        records.append(
            {
                "id": sample["id"],
                "class": sample["class"],
                "prompt": sample["prompt"],
                "detected": result.decision != Decision.ALLOW,
                "severity": result.decision.value,
                "cost": result.cost,
                "spin_magnitude": result.spin_magnitude,
                "signals": result.signals,
                "trust_level": result.trust_level,
                "cumulative_cost": result.cumulative_cost,
            }
        )
    return records


def run_trichromatic_lane(
    prompts: Iterable[Dict[str, Any]],
    calibration_prompts: List[Dict[str, Any]],
    *,
    coords_backend: str,
    quarantine_threshold: float,
    deny_threshold: float,
) -> List[Dict[str, Any]]:
    gate = RuntimeGate(
        coords_backend=coords_backend,
        use_classifier=False,
        use_trichromatic_governance=True,
        trichromatic_quarantine_threshold=quarantine_threshold,
        trichromatic_deny_threshold=deny_threshold,
    )
    calibrate_gate(gate, calibration_prompts)
    records: List[Dict[str, Any]] = []
    for sample in prompts:
        result = gate.evaluate(sample["prompt"])
        severity = severity_from_thresholds(
            result.trichromatic_risk_score,
            quarantine_threshold,
            deny_threshold,
        )
        records.append(
            {
                "id": sample["id"],
                "class": sample["class"],
                "prompt": sample["prompt"],
                "detected": severity != Decision.ALLOW.value,
                "severity": severity,
                "risk_score": result.trichromatic_risk_score,
                "triplet_coherence": result.trichromatic_triplet_coherence,
                "lattice_energy_score": result.trichromatic_lattice_energy_score,
                "whole_state_anomaly": result.trichromatic_whole_state_anomaly,
                "strongest_bridge": result.trichromatic_strongest_bridge,
                "state_hash": result.trichromatic_state_hash,
                "gate_decision": result.decision.value,
            }
        )
    return records


def run_hybrid_lane(
    prompts: Iterable[Dict[str, Any]],
    calibration_prompts: List[Dict[str, Any]],
    *,
    coords_backend: str,
    classifier_model_dir: str,
    classifier_quarantine_threshold: float,
    classifier_deny_threshold: float,
    trichromatic_quarantine_threshold: float,
    trichromatic_deny_threshold: float,
) -> List[Dict[str, Any]]:
    gate = RuntimeGate(
        coords_backend=coords_backend,
        use_classifier=True,
        classifier_model_dir=classifier_model_dir,
        classifier_quarantine_threshold=classifier_quarantine_threshold,
        classifier_deny_threshold=classifier_deny_threshold,
        use_trichromatic_governance=True,
        trichromatic_quarantine_threshold=trichromatic_quarantine_threshold,
        trichromatic_deny_threshold=trichromatic_deny_threshold,
    )
    calibrate_gate(gate, calibration_prompts)
    records: List[Dict[str, Any]] = []
    for sample in prompts:
        result = gate.evaluate(sample["prompt"])
        records.append(
            {
                "id": sample["id"],
                "class": sample["class"],
                "prompt": sample["prompt"],
                "detected": result.decision != Decision.ALLOW,
                "severity": result.decision.value,
                "cost": result.cost,
                "spin_magnitude": result.spin_magnitude,
                "signals": result.signals,
                "classifier_score": result.classifier_score,
                "classifier_flagged": result.classifier_flagged,
                "trichromatic_risk_score": result.trichromatic_risk_score,
                "trichromatic_flagged": result.trichromatic_flagged,
                "trichromatic_strongest_bridge": result.trichromatic_strongest_bridge,
                "state_hash": result.trichromatic_state_hash,
            }
        )
    return records


def summarize_lane(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(records)
    total = len(rows)
    detected = sum(1 for row in rows if row["detected"])
    per_category: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        category = row["class"]
        bucket = per_category.setdefault(category, {"total": 0, "detected": 0})
        bucket["total"] += 1
        if row["detected"]:
            bucket["detected"] += 1

    for category, bucket in per_category.items():
        bucket["rate"] = bucket["detected"] / max(bucket["total"], 1)

    return {
        "total": total,
        "detected": detected,
        "rate": detected / max(total, 1),
        "per_category": per_category,
    }


def build_cases(
    samples: List[Dict[str, Any]],
    classifier_raw_records: List[Dict[str, Any]],
    classifier_overlay_records: List[Dict[str, Any]],
    gate_records: List[Dict[str, Any]],
    trichromatic_records: List[Dict[str, Any]],
    hybrid_records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int], Dict[str, int]]:
    cases: List[Dict[str, Any]] = []
    overlap_counts: Dict[str, int] = {}
    hybrid_union_counts: Dict[str, int] = {}
    for idx, sample in enumerate(samples):
        classifier_raw = classifier_raw_records[idx]
        classifier_overlay = classifier_overlay_records[idx]
        gate = gate_records[idx]
        trichromatic = trichromatic_records[idx]
        hybrid = hybrid_records[idx]
        key = overlap_key(
            classifier_overlay["detected"],
            gate["detected"],
            trichromatic["detected"],
        )
        overlap_counts[key] = overlap_counts.get(key, 0) + 1

        union_detected = (
            classifier_overlay["detected"] or gate["detected"] or trichromatic["detected"]
        )
        hybrid_bucket = hybrid_union_bucket(union_detected, hybrid["detected"])
        hybrid_union_counts[hybrid_bucket] = hybrid_union_counts.get(hybrid_bucket, 0) + 1

        cases.append(
            {
                "id": sample["id"],
                "class": sample["class"],
                "prompt": sample["prompt"],
                "component_overlap": key,
                "component_union_detected": union_detected,
                "hybrid_vs_union": hybrid_bucket,
                "classifier_raw": classifier_raw,
                "classifier_overlay": classifier_overlay,
                "gate": gate,
                "trichromatic": trichromatic,
                "hybrid": hybrid,
            }
        )
    return cases, overlap_counts, hybrid_union_counts


def collect_failures(cases: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(cases)
    hybrid_misses = [row for row in rows if not row["hybrid"]["detected"]]
    hybrid_false_positives = [row for row in rows if row["hybrid"]["detected"]]

    misses_by_category: Dict[str, List[str]] = {}
    for row in hybrid_misses:
        misses_by_category.setdefault(row["class"], []).append(row["id"])

    false_positive_ids = [row["id"] for row in hybrid_false_positives]

    return {
        "hybrid_miss_count": len(hybrid_misses),
        "hybrid_miss_ids_by_category": misses_by_category,
        "hybrid_false_positive_count": len(hybrid_false_positives),
        "hybrid_false_positive_ids": false_positive_ids,
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    calibration_prompts = BASELINE_CLEAN[: args.calibration_count]
    benign_eval_prompts = BASELINE_CLEAN[args.calibration_count :]
    attacks = generate_attacks(scale=args.scale, seed=args.seed)

    model, vectorizer = load_classifier(args.classifier_model_dir)

    classifier_raw_attack_records = run_classifier_lane(
        attacks,
        model,
        vectorizer,
        args.classifier_quarantine_threshold,
        args.classifier_deny_threshold,
        mode="raw",
    )
    classifier_raw_benign_records = run_classifier_lane(
        benign_eval_prompts,
        model,
        vectorizer,
        args.classifier_quarantine_threshold,
        args.classifier_deny_threshold,
        mode="raw",
    )

    classifier_overlay_attack_records = run_classifier_lane(
        attacks,
        model,
        vectorizer,
        args.classifier_quarantine_threshold,
        args.classifier_deny_threshold,
        mode="overlay",
    )
    classifier_overlay_benign_records = run_classifier_lane(
        benign_eval_prompts,
        model,
        vectorizer,
        args.classifier_quarantine_threshold,
        args.classifier_deny_threshold,
        mode="overlay",
    )

    gate_attack_records = run_gate_lane(
        attacks,
        calibration_prompts,
        coords_backend=args.coords_backend,
    )
    gate_benign_records = run_gate_lane(
        benign_eval_prompts,
        calibration_prompts,
        coords_backend=args.coords_backend,
    )

    trichromatic_attack_records = run_trichromatic_lane(
        attacks,
        calibration_prompts,
        coords_backend=args.coords_backend,
        quarantine_threshold=args.trichromatic_quarantine_threshold,
        deny_threshold=args.trichromatic_deny_threshold,
    )
    trichromatic_benign_records = run_trichromatic_lane(
        benign_eval_prompts,
        calibration_prompts,
        coords_backend=args.coords_backend,
        quarantine_threshold=args.trichromatic_quarantine_threshold,
        deny_threshold=args.trichromatic_deny_threshold,
    )

    hybrid_attack_records = run_hybrid_lane(
        attacks,
        calibration_prompts,
        coords_backend=args.coords_backend,
        classifier_model_dir=args.classifier_model_dir,
        classifier_quarantine_threshold=args.classifier_quarantine_threshold,
        classifier_deny_threshold=args.classifier_deny_threshold,
        trichromatic_quarantine_threshold=args.trichromatic_quarantine_threshold,
        trichromatic_deny_threshold=args.trichromatic_deny_threshold,
    )
    hybrid_benign_records = run_hybrid_lane(
        benign_eval_prompts,
        calibration_prompts,
        coords_backend=args.coords_backend,
        classifier_model_dir=args.classifier_model_dir,
        classifier_quarantine_threshold=args.classifier_quarantine_threshold,
        classifier_deny_threshold=args.classifier_deny_threshold,
        trichromatic_quarantine_threshold=args.trichromatic_quarantine_threshold,
        trichromatic_deny_threshold=args.trichromatic_deny_threshold,
    )

    attack_cases, attack_overlap_counts, attack_hybrid_union_counts = build_cases(
        attacks,
        classifier_raw_attack_records,
        classifier_overlay_attack_records,
        gate_attack_records,
        trichromatic_attack_records,
        hybrid_attack_records,
    )
    benign_cases, benign_overlap_counts, benign_hybrid_union_counts = build_cases(
        benign_eval_prompts,
        classifier_raw_benign_records,
        classifier_overlay_benign_records,
        gate_benign_records,
        trichromatic_benign_records,
        hybrid_benign_records,
    )

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark": {
            "attack_source": "benchmarks.scbe.attacks.generator",
            "attack_scale": args.scale,
            "attack_seed": args.seed,
            "attack_total": len(attacks),
            "benign_source": "tests.adversarial.attack_corpus.BASELINE_CLEAN",
            "calibration_count": len(calibration_prompts),
            "benign_eval_total": len(benign_eval_prompts),
            "coords_backend": args.coords_backend,
        },
        "thresholds": {
            "classifier": {
                "quarantine": args.classifier_quarantine_threshold,
                "deny": args.classifier_deny_threshold,
            },
            "trichromatic": {
                "quarantine": args.trichromatic_quarantine_threshold,
                "deny": args.trichromatic_deny_threshold,
            },
        },
        "lanes": {
            "classifier_raw_attacks": summarize_lane(classifier_raw_attack_records),
            "classifier_overlay_attacks": summarize_lane(classifier_overlay_attack_records),
            "gate_attacks": summarize_lane(gate_attack_records),
            "trichromatic_attacks": summarize_lane(trichromatic_attack_records),
            "hybrid_attacks": summarize_lane(hybrid_attack_records),
            "classifier_raw_benign": summarize_lane(classifier_raw_benign_records),
            "classifier_overlay_benign": summarize_lane(classifier_overlay_benign_records),
            "gate_benign": summarize_lane(gate_benign_records),
            "trichromatic_benign": summarize_lane(trichromatic_benign_records),
            "hybrid_benign": summarize_lane(hybrid_benign_records),
        },
        "attack_overlap": {
            "component_counts": attack_overlap_counts,
            "hybrid_vs_component_union": attack_hybrid_union_counts,
        },
        "benign_overlap": {
            "component_counts": benign_overlap_counts,
            "hybrid_vs_component_union": benign_hybrid_union_counts,
        },
        "attack_failures": collect_failures(
            row for row in attack_cases if not row["hybrid"]["detected"]
        ),
        "benign_failures": collect_failures(
            row for row in benign_cases if row["hybrid"]["detected"]
        ),
        "attack_cases": attack_cases,
        "benign_cases": benign_cases,
    }


def write_report(report: Dict[str, Any], latest_path: Path) -> Tuple[Path, Path]:
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    timestamped_path = latest_path.with_name(
        f"{latest_path.stem.rstrip('_latest')}_{time.strftime('%Y-%m-%dT%H-%M-%SZ', time.gmtime())}.json"
    )
    latest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    timestamped_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return latest_path, timestamped_path


def print_summary(report: Dict[str, Any], latest_path: Path, timestamped_path: Path) -> None:
    lanes = report["lanes"]
    print("=" * 88)
    print("SCBE HYBRID OVERLAP REPORT")
    print("=" * 88)
    print(
        f"attacks={report['benchmark']['attack_total']}  "
        f"benign_eval={report['benchmark']['benign_eval_total']}  "
        f"coords={report['benchmark']['coords_backend']}"
    )
    print("")
    print(f"{'lane':<18} {'attacks':>12} {'benign fp':>12}")
    print("-" * 44)
    print(
        f"{'classifier_raw':<18} "
        f"{lanes['classifier_raw_attacks']['detected']:>4}/{lanes['classifier_raw_attacks']['total']:<7} "
        f"{lanes['classifier_raw_benign']['detected']:>4}/{lanes['classifier_raw_benign']['total']:<7}"
    )
    print(
        f"{'classifier_overlay':<18} "
        f"{lanes['classifier_overlay_attacks']['detected']:>4}/{lanes['classifier_overlay_attacks']['total']:<7} "
        f"{lanes['classifier_overlay_benign']['detected']:>4}/{lanes['classifier_overlay_benign']['total']:<7}"
    )
    print(
        f"{'gate':<18} "
        f"{lanes['gate_attacks']['detected']:>4}/{lanes['gate_attacks']['total']:<7} "
        f"{lanes['gate_benign']['detected']:>4}/{lanes['gate_benign']['total']:<7}"
    )
    print(
        f"{'trichromatic':<18} "
        f"{lanes['trichromatic_attacks']['detected']:>4}/{lanes['trichromatic_attacks']['total']:<7} "
        f"{lanes['trichromatic_benign']['detected']:>4}/{lanes['trichromatic_benign']['total']:<7}"
    )
    print(
        f"{'hybrid':<18} "
        f"{lanes['hybrid_attacks']['detected']:>4}/{lanes['hybrid_attacks']['total']:<7} "
        f"{lanes['hybrid_benign']['detected']:>4}/{lanes['hybrid_benign']['total']:<7}"
    )
    print("")
    print("Attack component overlap:")
    for key in sorted(report["attack_overlap"]["component_counts"]):
        print(f"  {key:<28} {report['attack_overlap']['component_counts'][key]}")
    print("")
    print("Hybrid vs component union:")
    for key in sorted(report["attack_overlap"]["hybrid_vs_component_union"]):
        print(f"  {key:<28} {report['attack_overlap']['hybrid_vs_component_union'][key]}")
    print("")
    print(f"latest artifact: {latest_path}")
    print(f"timestamped artifact: {timestamped_path}")


def main() -> None:
    args = parse_args()
    report = build_report(args)
    latest_path, timestamped_path = write_report(report, Path(args.output))
    print_summary(report, latest_path, timestamped_path)


if __name__ == "__main__":
    main()
