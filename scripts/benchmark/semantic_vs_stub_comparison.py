#!/usr/bin/env python3
"""Semantic vs Stub L3 Comparison
==================================

Head-to-head: character-counting stub vs real semantic tongue coordinates.
Same attacks, same pipeline, same thresholds. Only L3 changes.

Saves full parameter sets and results for reproducibility.
"""

from __future__ import annotations
import json, math, time, sys
from pathlib import Path
from typing import Dict, List
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.adversarial.scbe_harness import (
    SCBEDetectionGate, text_to_tongue_coords, quantize_spin,
    compute_harmonic_cost, build_metric_tensor,
    TONGUE_NAMES, TONGUE_WEIGHTS, PI, PHI,
    _ADVERSARIAL_PATTERNS, _MULTILINGUAL_OVERRIDE_PATTERNS,
)
from tests.adversarial.attack_corpus import BASELINE_CLEAN, get_all_attacks
from tests.adversarial.tongue_semantic import semantic_tongue_coords


# ═══════════════════════════════════════════════════════════
# Test corpus
# ═══════════════════════════════════════════════════════════

ATTACKS = get_all_attacks()
CLEAN = BASELINE_CLEAN


# ═══════════════════════════════════════════════════════════
# Run both versions
# ═══════════════════════════════════════════════════════════

def run_version(name: str, coord_fn, attacks, clean):
    """Run detection using a specific tongue coordinate function."""
    # Calibrate centroid from clean text
    clean_coords = [coord_fn(p["prompt"]) for p in clean]
    centroid = np.mean(clean_coords, axis=0).tolist()
    G = build_metric_tensor()

    results = {
        "name": name,
        "attacks_total": len(attacks),
        "clean_total": len(clean),
        "attacks_detected": 0,
        "clean_false_positives": 0,
        "per_class": {},
        "tongue_profiles": {},
        "ru_values": [],
        "dominant_tongue_counts": {t: 0 for t in TONGUE_NAMES},
    }

    # Process attacks
    for attack in attacks:
        coords = coord_fn(attack["prompt"])
        spin = quantize_spin(coords, centroid, threshold=0.03)

        # Compute cost
        d_star_sq = sum(G[i, i] * (coords[i] - centroid[i]) ** 2 for i in range(6))
        d_star = math.sqrt(d_star_sq)
        cost = PI ** (PHI * min(d_star, 5.0))

        # Weighted dominance
        weighted = [abs(coords[i]) * TONGUE_WEIGHTS[i] for i in range(6)]
        dom_idx = weighted.index(max(weighted))
        dom_tongue = TONGUE_NAMES[dom_idx]
        results["dominant_tongue_counts"][dom_tongue] += 1

        # Track RU
        results["ru_values"].append(float(coords[2]))

        # Detection (same logic as harness)
        signals = []
        adv_matches = sum(1 for p in _ADVERSARIAL_PATTERNS if p.search(attack["prompt"]))
        ml_matches = sum(1 for p in _MULTILINGUAL_OVERRIDE_PATTERNS if p.search(attack["prompt"]))
        if spin.magnitude >= 5:
            signals.append("spin_drift")
        if max(weighted) / max(sum(weighted), 1e-9) > 0.6:
            signals.append("tongue_imbalance")
        if cost > 12.0:
            signals.append("cost_exceeded")
        if math.sqrt(sum(c * c for c in coords)) > 1.5:
            signals.append("boundary_violation")
        if adv_matches >= 1:
            signals.append("adversarial_lexical")
        if ml_matches >= 1:
            signals.append("cross_lingual")

        has_geometric = any(s in signals for s in ["cost_exceeded", "spin_drift", "boundary_violation", "tongue_imbalance"])
        detected = (
            len(signals) >= 2
            or adv_matches >= 2
            or ml_matches >= 1
            or (adv_matches >= 1 and has_geometric)
        )

        if detected:
            results["attacks_detected"] += 1

        cls = attack.get("class", "unknown")
        if cls not in results["per_class"]:
            results["per_class"][cls] = {"total": 0, "detected": 0}
        results["per_class"][cls]["total"] += 1
        if detected:
            results["per_class"][cls]["detected"] += 1

    # Process clean (false positive check)
    for prompt in clean:
        coords = coord_fn(prompt["prompt"])
        spin = quantize_spin(coords, centroid, threshold=0.03)
        d_star_sq = sum(G[i, i] * (coords[i] - centroid[i]) ** 2 for i in range(6))
        d_star = math.sqrt(d_star_sq)
        cost = PI ** (PHI * min(d_star, 5.0))
        weighted = [abs(coords[i]) * TONGUE_WEIGHTS[i] for i in range(6)]

        signals = []
        adv_matches = sum(1 for p in _ADVERSARIAL_PATTERNS if p.search(prompt["prompt"]))
        ml_matches = sum(1 for p in _MULTILINGUAL_OVERRIDE_PATTERNS if p.search(prompt["prompt"]))
        if spin.magnitude >= 5: signals.append("spin")
        if max(weighted) / max(sum(weighted), 1e-9) > 0.6: signals.append("imbalance")
        if cost > 12.0: signals.append("cost")
        if math.sqrt(sum(c * c for c in coords)) > 1.5: signals.append("boundary")
        if adv_matches >= 1: signals.append("lexical")
        if ml_matches >= 1: signals.append("ml")

        has_geo = any(s in signals for s in ["cost", "spin", "boundary", "imbalance"])
        detected = len(signals) >= 2 or adv_matches >= 2 or ml_matches >= 1 or (adv_matches >= 1 and has_geo)

        if detected:
            results["clean_false_positives"] += 1

    # Summary stats
    results["detection_rate"] = round(results["attacks_detected"] / max(results["attacks_total"], 1), 4)
    results["false_positive_rate"] = round(results["clean_false_positives"] / max(results["clean_total"], 1), 4)
    results["ru_mean"] = round(float(np.mean(results["ru_values"])), 4)
    results["ru_std"] = round(float(np.std(results["ru_values"])), 4)
    results["ru_min"] = round(float(np.min(results["ru_values"])), 4)
    results["ru_max"] = round(float(np.max(results["ru_values"])), 4)

    # Tongue profiles per class
    for cls in results["per_class"]:
        cls_attacks = [a for a in attacks if a.get("class") == cls]
        cls_coords = [coord_fn(a["prompt"]) for a in cls_attacks]
        if cls_coords:
            avg_coords = np.mean(cls_coords, axis=0)
            results["tongue_profiles"][cls] = {TONGUE_NAMES[i]: round(float(avg_coords[i]), 4) for i in range(6)}

    return results


def main():
    print("=" * 75)
    print(f"{'SEMANTIC vs STUB L3 COMPARISON':^75}")
    print(f"{'Same attacks, same pipeline, only L3 changes':^75}")
    print("=" * 75)
    print()

    # Run both versions
    print("Running STUB (character counting)...")
    stub = run_version("STUB (character counting)", text_to_tongue_coords, ATTACKS, CLEAN)

    print("Running SEMANTIC (keyword→domain resonance)...")
    semantic = run_version("SEMANTIC (linguisticCrossTalk)", semantic_tongue_coords, ATTACKS, CLEAN)

    # Comparison table
    print()
    print(f"{'Metric':<35} {'STUB':>15} {'SEMANTIC':>15} {'Delta':>12}")
    print("-" * 80)
    print(f"{'Attacks detected':.<35} {stub['attacks_detected']:>12}/{stub['attacks_total']} {semantic['attacks_detected']:>12}/{semantic['attacks_total']} {'':>12}")
    print(f"{'Detection rate':.<35} {stub['detection_rate']:>14.1%} {semantic['detection_rate']:>14.1%} {(semantic['detection_rate']-stub['detection_rate']):>+11.1%}")
    print(f"{'False positives':.<35} {stub['clean_false_positives']:>12}/{stub['clean_total']} {semantic['clean_false_positives']:>12}/{semantic['clean_total']} {'':>12}")
    print(f"{'FP rate':.<35} {stub['false_positive_rate']:>14.1%} {semantic['false_positive_rate']:>14.1%} {(semantic['false_positive_rate']-stub['false_positive_rate']):>+11.1%}")
    print(f"{'RU mean':.<35} {stub['ru_mean']:>15.4f} {semantic['ru_mean']:>15.4f} {(semantic['ru_mean']-stub['ru_mean']):>+12.4f}")
    print(f"{'RU std':.<35} {stub['ru_std']:>15.4f} {semantic['ru_std']:>15.4f} {(semantic['ru_std']-stub['ru_std']):>+12.4f}")
    print(f"{'RU range':.<35} {stub['ru_min']:.2f}-{stub['ru_max']:.2f}{'':>8} {semantic['ru_min']:.2f}-{semantic['ru_max']:.2f}{'':>8}")
    print()

    # Dominant tongue distribution
    print(f"{'Dominant tongue distribution':^75}")
    print(f"{'Tongue':<10} {'STUB':>12} {'SEMANTIC':>12}")
    print("-" * 40)
    for t in TONGUE_NAMES:
        print(f"{t:<10} {stub['dominant_tongue_counts'][t]:>12} {semantic['dominant_tongue_counts'][t]:>12}")
    print()

    # Per-class comparison
    print(f"{'Per-class detection rate':^75}")
    print(f"{'Class':<25} {'STUB':>12} {'SEMANTIC':>12} {'Delta':>10}")
    print("-" * 65)
    all_classes = sorted(set(list(stub["per_class"].keys()) + list(semantic["per_class"].keys())))
    for cls in all_classes:
        s_data = stub["per_class"].get(cls, {"detected": 0, "total": 0})
        m_data = semantic["per_class"].get(cls, {"detected": 0, "total": 0})
        s_rate = s_data["detected"] / max(s_data["total"], 1)
        m_rate = m_data["detected"] / max(m_data["total"], 1)
        delta = m_rate - s_rate
        print(f"{cls:<25} {s_data['detected']:>5}/{s_data['total']:<5} {m_data['detected']:>5}/{m_data['total']:<5} {delta:>+9.0%}")
    print()

    # Tongue profiles per class (semantic only)
    print(f"{'Semantic tongue profiles per class':^75}")
    print(f"{'Class':<20} {'KO':>7} {'AV':>7} {'RU':>7} {'CA':>7} {'UM':>7} {'DR':>7}")
    print("-" * 65)
    for cls, profile in sorted(semantic["tongue_profiles"].items()):
        print(f"{cls:<20} {profile['KO']:>7.3f} {profile['AV']:>7.3f} {profile['RU']:>7.3f} {profile['CA']:>7.3f} {profile['UM']:>7.3f} {profile['DR']:>7.3f}")

    # Save everything
    out_dir = Path("artifacts/benchmark")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean up non-serializable
    for r in [stub, semantic]:
        r.pop("ru_values", None)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "test": "semantic_vs_stub_L3",
        "attacks": len(ATTACKS),
        "clean": len(CLEAN),
        "stub": stub,
        "semantic": semantic,
        "parameters": {
            "stub_method": "text_to_tongue_coords (character counting: uppercase, word count, unique ratio, digits, punctuation)",
            "semantic_method": "semantic_tongue_coords (keyword->domain resonance from linguisticCrossTalk.ts, 130+ keywords across 6 domains)",
            "detection_logic": "2+ signals OR 2+ lexical OR 1+ cross-lingual OR (1 lexical + geometric)",
            "thresholds": {"spin_drift": 5, "tongue_imbalance": 0.6, "cost_exceeded": 12.0, "boundary": 1.5},
        },
    }

    json_path = out_dir / "semantic_vs_stub_comparison.json"
    json_path.write_text(json.dumps(report, indent=2))
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
