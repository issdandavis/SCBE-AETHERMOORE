#!/usr/bin/env python3
"""Null Space Ablation — Does absence actually help?
======================================================

Clean incremental test:
  A: E4 alone (semantic + remainder) — the current best
  B: E4 + null space features
  C: E4 + null space + helix radius

Same corpus, same thresholds, held-out clean set.
Confusion matrix per attack class.
"""

from __future__ import annotations
import math, json, time, sys
from pathlib import Path
from collections import Counter
from typing import Dict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.adversarial.scbe_harness import (
    quantize_spin, build_metric_tensor,
    TONGUE_WEIGHTS, PI, PHI,
    _ADVERSARIAL_PATTERNS, _MULTILINGUAL_OVERRIDE_PATTERNS,
)
from tests.adversarial.attack_corpus import BASELINE_CLEAN, get_all_attacks
from tests.adversarial.tongue_semantic import semantic_tongue_coords

G = build_metric_tensor()

# Split clean into calibration (10) and held-out (5)
CALIB_CLEAN = BASELINE_CLEAN[:10]
HOLDOUT_CLEAN = BASELINE_CLEAN[10:]
ATTACKS = get_all_attacks()


def poincare_project(v, max_norm=0.999):
    norm = np.linalg.norm(v)
    return v * max_norm / norm if norm >= max_norm else v

def mobius_add(u, v, eps=1e-10):
    u_sq, v_sq, uv = np.dot(u,u), np.dot(v,v), np.dot(u,v)
    return poincare_project(((1+2*uv+v_sq)*u + (1-u_sq)*v) / (1+2*uv+u_sq*v_sq+eps))

def exp_map_zero(v, eps=1e-10):
    norm = np.linalg.norm(v)
    return np.tanh(norm)*v/norm if norm >= eps else v


def get_features(text: str, centroid: np.ndarray) -> Dict:
    """Extract ALL features for one text."""
    coords = semantic_tongue_coords(text)
    spin = quantize_spin(coords, centroid, 0.03)
    d_star = math.sqrt(sum(G[i,i]*(coords[i]-centroid[i])**2 for i in range(6)))
    cost = PI ** (PHI * min(d_star, 5.0))
    weighted = [abs(coords[i])*TONGUE_WEIGHTS[i] for i in range(6)]
    norm = math.sqrt(sum(c*c for c in coords))
    adv = sum(1 for p in _ADVERSARIAL_PATTERNS if p.search(text))
    ml = sum(1 for p in _MULTILINGUAL_OVERRIDE_PATTERNS if p.search(text))

    # Remainder
    raw = coords.copy()
    mooned = raw / PHI
    foamed = raw.copy()
    for i in range(5):
        t = math.sqrt(TONGUE_WEIGHTS[i]*TONGUE_WEIGHTS[i+1])
        b = (raw[i]-raw[i+1])/t*0.3
        foamed[i] -= b
        foamed[i+1] += b
    foamed = np.clip(foamed, 0, 1)
    remainder = float(np.sum(np.abs(raw-mooned)+np.abs(mooned-foamed)+np.abs(raw-foamed)))

    # Null space
    threshold = 0.01
    null_count = sum(1 for c in coords if c < threshold)
    null_ratio = null_count / 6
    null_energy = sum(TONGUE_WEIGHTS[i] for i in range(6) if coords[i] < threshold)
    active_energy = sum(coords[i]*TONGUE_WEIGHTS[i] for i in range(6) if coords[i] >= threshold)
    potential_ratio = null_energy / max(active_energy, 1e-10)
    null_pattern = "".join("_" if coords[i] < threshold else "#" for i in range(6))

    # Helix radius
    point = np.zeros(6)
    tc = coords
    for t_idx in range(6):
        angle = 2*PI*t_idx/6
        mag = tc[t_idx]*0.3
        tangent = np.zeros(6)
        tangent[t_idx%6] = mag*math.cos(angle*PHI)
        tangent[(t_idx+1)%6] = mag*math.sin(angle*PHI)
        point = mobius_add(point, exp_map_zero(tangent))
    helix_radius = float(np.linalg.norm(poincare_project(point)))

    return {
        "coords": coords, "spin": spin.magnitude, "cost": cost,
        "d_star": d_star, "norm": norm, "adv": adv, "ml": ml,
        "remainder": remainder, "null_ratio": null_ratio,
        "null_energy": null_energy, "potential_ratio": potential_ratio,
        "null_pattern": null_pattern, "helix_radius": helix_radius,
        "weighted": weighted,
    }


def decide_A(f: Dict) -> bool:
    """E4: Semantic + remainder only."""
    signals = []
    if f["spin"] >= 5: signals.append(1)
    if max(f["weighted"])/max(sum(f["weighted"]),1e-9) > 0.6: signals.append(1)
    if f["cost"] > 1.5: signals.append(1)
    if f["norm"] > 0.3: signals.append(1)
    if f["adv"] >= 1: signals.append(1)
    if f["ml"] >= 1: signals.append(1)
    if f["remainder"] > 0.15: signals.append(1)
    has_geo = f["cost"]>1.5 or f["spin"]>=5 or f["norm"]>0.3 or f["remainder"]>0.15
    return len(signals)>=2 or f["adv"]>=2 or f["ml"]>=1 or (f["adv"]>=1 and has_geo)


def decide_B(f: Dict) -> bool:
    """E4 + null space features."""
    signals = []
    if f["spin"] >= 5: signals.append(1)
    if max(f["weighted"])/max(sum(f["weighted"]),1e-9) > 0.6: signals.append(1)
    if f["cost"] > 1.5: signals.append(1)
    if f["norm"] > 0.3: signals.append(1)
    if f["adv"] >= 1: signals.append(1)
    if f["ml"] >= 1: signals.append(1)
    if f["remainder"] > 0.15: signals.append(1)
    # NULL SPACE: high null ratio or high potential ratio = suspicious
    if f["null_ratio"] > 0.5: signals.append(1)
    if f["potential_ratio"] > 3.0: signals.append(1)
    has_geo = f["cost"]>1.5 or f["spin"]>=5 or f["norm"]>0.3 or f["remainder"]>0.15 or f["null_ratio"]>0.5
    return len(signals)>=2 or f["adv"]>=2 or f["ml"]>=1 or (f["adv"]>=1 and has_geo)


def decide_C(f: Dict) -> bool:
    """E4 + null space + helix radius."""
    signals = []
    if f["spin"] >= 5: signals.append(1)
    if max(f["weighted"])/max(sum(f["weighted"]),1e-9) > 0.6: signals.append(1)
    if f["cost"] > 1.5: signals.append(1)
    if f["norm"] > 0.3: signals.append(1)
    if f["adv"] >= 1: signals.append(1)
    if f["ml"] >= 1: signals.append(1)
    if f["remainder"] > 0.15: signals.append(1)
    if f["null_ratio"] > 0.5: signals.append(1)
    if f["potential_ratio"] > 3.0: signals.append(1)
    # HELIX: larger radius in hyperbolic space = more suspicious
    if f["helix_radius"] > 0.06: signals.append(1)
    has_geo = f["cost"]>1.5 or f["spin"]>=5 or f["norm"]>0.3 or f["remainder"]>0.15 or f["null_ratio"]>0.5 or f["helix_radius"]>0.06
    return len(signals)>=2 or f["adv"]>=2 or f["ml"]>=1 or (f["adv"]>=1 and has_geo)


def run_ablation(name, decide_fn, attacks, clean_calib, clean_holdout):
    centroid = np.mean([semantic_tongue_coords(p["prompt"]) for p in clean_calib], axis=0)

    # Attacks
    atk_det = 0
    per_class = {}
    for a in attacks:
        f = get_features(a["prompt"], centroid)
        d = decide_fn(f)
        if d: atk_det += 1
        cls = a.get("class", "?")
        if cls not in per_class: per_class[cls] = {"tp": 0, "fn": 0, "total": 0}
        per_class[cls]["total"] += 1
        if d: per_class[cls]["tp"] += 1
        else: per_class[cls]["fn"] += 1

    # Calibration FP
    calib_fp = 0
    for p in clean_calib:
        f = get_features(p["prompt"], centroid)
        if decide_fn(f): calib_fp += 1

    # HELD-OUT FP (the real test)
    holdout_fp = 0
    for p in clean_holdout:
        f = get_features(p["prompt"], centroid)
        if decide_fn(f): holdout_fp += 1

    return {
        "name": name,
        "attacks_detected": atk_det,
        "detection_rate": round(atk_det / max(len(attacks), 1), 4),
        "calib_fp": calib_fp,
        "calib_fp_rate": round(calib_fp / max(len(clean_calib), 1), 4),
        "holdout_fp": holdout_fp,
        "holdout_fp_rate": round(holdout_fp / max(len(clean_holdout), 1), 4),
        "per_class": per_class,
    }


def main():
    print("=" * 80)
    print(f"{'NULL SPACE ABLATION — Does absence actually help?':^80}")
    print("=" * 80)
    print(f"Attacks: {len(ATTACKS)} | Calibration clean: {len(CALIB_CLEAN)} | Held-out clean: {len(HOLDOUT_CLEAN)}")
    print()

    results = [
        run_ablation("A: E4 (semantic + remainder)", decide_A, ATTACKS, CALIB_CLEAN, HOLDOUT_CLEAN),
        run_ablation("B: E4 + null space", decide_B, ATTACKS, CALIB_CLEAN, HOLDOUT_CLEAN),
        run_ablation("C: E4 + null + helix", decide_C, ATTACKS, CALIB_CLEAN, HOLDOUT_CLEAN),
    ]

    # Summary table
    print(f"{'Config':<30} {'Det':>7} {'Rate':>8} {'Cal FP':>8} {'Hold FP':>9} {'Hold FPR':>10}")
    print("-" * 75)
    for r in results:
        print(f"{r['name']:<30} {r['attacks_detected']:>5}/91 {r['detection_rate']:>7.1%} {r['calib_fp']:>5}/{len(CALIB_CLEAN)} {r['holdout_fp']:>6}/{len(HOLDOUT_CLEAN)} {r['holdout_fp_rate']:>9.1%}")

    # Incremental gain
    print()
    print("Incremental gain:")
    a, b, c = results
    gain_b = b["detection_rate"] - a["detection_rate"]
    gain_c = c["detection_rate"] - a["detection_rate"]
    fp_cost_b = b["holdout_fp_rate"] - a["holdout_fp_rate"]
    fp_cost_c = c["holdout_fp_rate"] - a["holdout_fp_rate"]
    print(f"  +null space:      {gain_b:+.1%} detection, {fp_cost_b:+.1%} FP")
    print(f"  +null+helix:      {gain_c:+.1%} detection, {fp_cost_c:+.1%} FP")

    # Per-class confusion
    print()
    print(f"{'Per-class detection (A vs B vs C)':^80}")
    print(f"{'Class':<25} {'A':>8} {'B':>8} {'C':>8} {'B-A':>8} {'C-A':>8}")
    print("-" * 60)
    classes = sorted(set(cls for r in results for cls in r["per_class"]))
    for cls in classes:
        rates = []
        for r in results:
            d = r["per_class"].get(cls, {"tp": 0, "total": 1})
            rates.append(d["tp"] / max(d["total"], 1))
        delta_b = rates[1] - rates[0]
        delta_c = rates[2] - rates[0]
        print(f"{cls:<25} {rates[0]:>7.0%} {rates[1]:>7.0%} {rates[2]:>7.0%} {delta_b:>+7.0%} {delta_c:>+7.0%}")

    # Null space as attack classifier
    print()
    print(f"{'NULL SPACE AS ATTACK CLASSIFIER':^80}")
    print("-" * 80)
    centroid = np.mean([semantic_tongue_coords(p["prompt"]) for p in CALIB_CLEAN], axis=0)

    pattern_to_classes = {}
    for a in ATTACKS:
        f = get_features(a["prompt"], centroid)
        cls = a.get("class", "?")
        p = f["null_pattern"]
        if p not in pattern_to_classes:
            pattern_to_classes[p] = Counter()
        pattern_to_classes[p][cls] += 1

    for pattern, class_counts in sorted(pattern_to_classes.items(), key=lambda x: -sum(x[1].values())):
        total = sum(class_counts.values())
        top_class = class_counts.most_common(1)[0]
        purity = top_class[1] / total
        print(f"  {pattern}  ({total:>3} attacks) top={top_class[0]:<25} purity={purity:.0%}")

    # Save
    out = Path("artifacts/benchmark/null_space_ablation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": [{k: v for k, v in r.items()} for r in results],
        "incremental": {
            "null_space_gain": round(gain_b, 4),
            "null_helix_gain": round(gain_c, 4),
            "null_space_fp_cost": round(fp_cost_b, 4),
            "null_helix_fp_cost": round(fp_cost_c, 4),
        },
    }
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
