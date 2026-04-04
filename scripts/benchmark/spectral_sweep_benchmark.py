#!/usr/bin/env python3
"""Spectral Sweep Benchmark — Test across the full field
==========================================================

Controls (baselines):
  C1: Raw stub (character counting, no modifications)
  C2: Raw semantic (keyword resonance, no modifications)
  C3: Raw semantic + recalibrated thresholds

Experimental (layered on semantic L3):
  E1: Semantic + moon counter-weights
  E2: Semantic + foam fold dampening
  E3: Semantic + triple-weight remainder
  E4: Semantic + moon + foam (combined)
  E5: Semantic + moon + foam + remainder (full stack)

Each configuration runs through the same attack corpus.
Results cross-referenced as a spectral grid: (-1, 0, +1) per method.
"""

from __future__ import annotations
import json, math, time, sys
from pathlib import Path
from typing import Tuple
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.adversarial.scbe_harness import (
    text_to_tongue_coords,
    quantize_spin,
    build_metric_tensor,
    TONGUE_WEIGHTS,
    PI,
    PHI,
    _ADVERSARIAL_PATTERNS,
    _MULTILINGUAL_OVERRIDE_PATTERNS,
)
from tests.adversarial.attack_corpus import BASELINE_CLEAN, get_all_attacks
from tests.adversarial.tongue_semantic import semantic_tongue_coords

ATTACKS = get_all_attacks()
CLEAN = BASELINE_CLEAN
G = build_metric_tensor()


# ═══════════════════════════════════════════════════════════
# Weight modification methods
# ═══════════════════════════════════════════════════════════


def moon_counterweight(coords: np.ndarray) -> np.ndarray:
    """Jupiter moons: effective weight = weight / phi (shift down one step)."""
    counter = coords * (1 - 1 / PHI)
    return coords - counter  # = coords / phi


def foam_dampen(coords: np.ndarray) -> np.ndarray:
    """Foam boundary dampening: reduce bleed at tongue boundaries."""
    dampened = coords.copy()
    for i in range(5):
        tension = math.sqrt(TONGUE_WEIGHTS[i] * TONGUE_WEIGHTS[i + 1])
        dampen_factor = 1.0 / tension
        # Reduce the boundary between adjacent tongues
        bleed = (coords[i] - coords[i + 1]) * dampen_factor * 0.3
        dampened[i] -= bleed
        dampened[i + 1] += bleed
    return np.clip(dampened, 0.0, 1.0)


def triple_remainder(coords_a: np.ndarray, coords_b: np.ndarray, coords_c: np.ndarray) -> Tuple[float, np.ndarray]:
    """Three witnesses: compute disagreement."""
    remainder_vec = np.abs(coords_a - coords_b) + np.abs(coords_b - coords_c) + np.abs(coords_a - coords_c)
    return float(np.sum(remainder_vec)), remainder_vec


# ═══════════════════════════════════════════════════════════
# Detection engine (parameterized)
# ═══════════════════════════════════════════════════════════


def detect(
    text: str,
    coords: np.ndarray,
    centroid: np.ndarray,
    cost_threshold: float = 12.0,
    spin_threshold: int = 5,
    boundary_threshold: float = 1.5,
    imbalance_threshold: float = 0.6,
    remainder_score: float = 0.0,
    remainder_threshold: float = 999.0,
) -> dict:
    """Run detection with configurable thresholds."""
    spin = quantize_spin(coords, centroid, threshold=0.03)
    d_star_sq = sum(G[i, i] * (coords[i] - centroid[i]) ** 2 for i in range(6))
    d_star = math.sqrt(d_star_sq)
    cost = PI ** (PHI * min(d_star, 5.0))
    weighted = [abs(coords[i]) * TONGUE_WEIGHTS[i] for i in range(6)]
    coord_norm = math.sqrt(sum(c * c for c in coords))
    dom_ratio = max(weighted) / max(sum(weighted), 1e-9)

    signals = []
    adv = sum(1 for p in _ADVERSARIAL_PATTERNS if p.search(text))
    ml = sum(1 for p in _MULTILINGUAL_OVERRIDE_PATTERNS if p.search(text))

    if spin.magnitude >= spin_threshold:
        signals.append("spin")
    if dom_ratio > imbalance_threshold:
        signals.append("imbalance")
    if cost > cost_threshold:
        signals.append("cost")
    if coord_norm > boundary_threshold:
        signals.append("boundary")
    if adv >= 1:
        signals.append("lexical")
    if ml >= 1:
        signals.append("ml")
    if remainder_score > remainder_threshold:
        signals.append("remainder")

    has_geo = any(s in signals for s in ["cost", "spin", "boundary", "imbalance", "remainder"])
    detected = len(signals) >= 2 or adv >= 2 or ml >= 1 or (adv >= 1 and has_geo)

    return {
        "detected": detected,
        "signals": len(signals),
        "cost": cost,
        "spin": spin.magnitude,
        "d_star": d_star,
    }


# ═══════════════════════════════════════════════════════════
# Configuration sweep
# ═══════════════════════════════════════════════════════════


def run_config(
    name: str, coord_fn, post_process=None, cost_threshold=12.0, boundary_threshold=1.5, use_remainder=False
):
    """Run one configuration across all attacks and clean text."""
    # Calibrate
    clean_coords = [coord_fn(p["prompt"]) for p in CLEAN]
    centroid = np.mean(clean_coords, axis=0).tolist()

    atk_detected = 0
    fp_detected = 0
    per_class = {}

    for attack in ATTACKS:
        coords = coord_fn(attack["prompt"])
        if post_process:
            coords = post_process(coords)

        remainder_score = 0.0
        if use_remainder:
            raw = coord_fn(attack["prompt"])
            mooned = moon_counterweight(raw.copy())
            foamed = foam_dampen(raw.copy())
            remainder_score, _ = triple_remainder(raw, mooned, foamed)

        r = detect(
            attack["prompt"],
            coords,
            centroid,
            cost_threshold=cost_threshold,
            boundary_threshold=boundary_threshold,
            remainder_score=remainder_score,
            remainder_threshold=0.15,
        )

        if r["detected"]:
            atk_detected += 1

        cls = attack.get("class", "unknown")
        if cls not in per_class:
            per_class[cls] = {"total": 0, "detected": 0}
        per_class[cls]["total"] += 1
        if r["detected"]:
            per_class[cls]["detected"] += 1

    for prompt in CLEAN:
        coords = coord_fn(prompt["prompt"])
        if post_process:
            coords = post_process(coords)
        r = detect(
            prompt["prompt"], coords, centroid, cost_threshold=cost_threshold, boundary_threshold=boundary_threshold
        )
        if r["detected"]:
            fp_detected += 1

    det_rate = round(atk_detected / max(len(ATTACKS), 1), 4)
    fp_rate = round(fp_detected / max(len(CLEAN), 1), 4)

    return {
        "name": name,
        "detection_rate": det_rate,
        "fp_rate": fp_rate,
        "detected": atk_detected,
        "false_positives": fp_detected,
        "per_class": per_class,
    }


def main():
    print("=" * 80)
    print(f"{'SPECTRAL SWEEP BENCHMARK':^80}")
    print(f"{'Controls + Experimental across full configuration space':^80}")
    print("=" * 80)
    print()

    configs = []

    # CONTROLS
    print("Running controls...")
    configs.append(run_config("C1: Stub raw", text_to_tongue_coords))
    configs.append(run_config("C2: Semantic raw", semantic_tongue_coords))
    configs.append(
        run_config("C3: Semantic recalibrated", semantic_tongue_coords, cost_threshold=1.5, boundary_threshold=0.3)
    )

    # EXPERIMENTAL
    print("Running experimental...")
    configs.append(
        run_config(
            "E1: Semantic + moon",
            semantic_tongue_coords,
            post_process=moon_counterweight,
            cost_threshold=1.0,
            boundary_threshold=0.2,
        )
    )
    configs.append(
        run_config(
            "E2: Semantic + foam",
            semantic_tongue_coords,
            post_process=foam_dampen,
            cost_threshold=1.5,
            boundary_threshold=0.3,
        )
    )

    def moon_then_foam(coords):
        return foam_dampen(moon_counterweight(coords))

    configs.append(
        run_config(
            "E3: Semantic + moon + foam",
            semantic_tongue_coords,
            post_process=moon_then_foam,
            cost_threshold=1.0,
            boundary_threshold=0.2,
        )
    )
    configs.append(
        run_config(
            "E4: Semantic + remainder",
            semantic_tongue_coords,
            cost_threshold=1.5,
            boundary_threshold=0.3,
            use_remainder=True,
        )
    )
    configs.append(
        run_config(
            "E5: Semantic + all",
            semantic_tongue_coords,
            post_process=moon_then_foam,
            cost_threshold=1.0,
            boundary_threshold=0.2,
            use_remainder=True,
        )
    )

    # Results table
    print()
    print(f"{'Config':<35} {'Detected':>10} {'Det Rate':>10} {'FP':>5} {'FP Rate':>10}")
    print("-" * 75)
    for c in configs:
        marker = (
            " <-- BEST"
            if c["detection_rate"] == max(x["detection_rate"] for x in configs if x["fp_rate"] <= 0.1)
            and c["fp_rate"] <= 0.1
            else ""
        )
        print(
            f"{c['name']:<35} {c['detected']:>7}/91 {c['detection_rate']:>9.1%} {c['false_positives']:>5} {c['fp_rate']:>9.1%}{marker}"
        )

    # Per-class breakdown for top 3
    print()
    best = sorted(configs, key=lambda c: c["detection_rate"] if c["fp_rate"] <= 0.1 else 0, reverse=True)[:3]
    print(f"{'Per-class (top 3 configs)':^80}")
    classes = sorted(set(cls for c in configs for cls in c["per_class"]))
    header = f"{'Class':<25}"
    for b in best:
        header += f" {b['name'][:15]:>15}"
    print(header)
    print("-" * (25 + 16 * len(best)))
    for cls in classes:
        row = f"{cls:<25}"
        for b in best:
            d = b["per_class"].get(cls, {"detected": 0, "total": 0})
            row += f" {d['detected']:>6}/{d['total']:<6}"
        print(row)

    # Save
    out_dir = Path("artifacts/benchmark")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "test": "spectral_sweep",
        "configs": [{k: v for k, v in c.items()} for c in configs],
    }
    json_path = out_dir / "spectral_sweep_results.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nSaved: {json_path}")


if __name__ == "__main__":
    main()
