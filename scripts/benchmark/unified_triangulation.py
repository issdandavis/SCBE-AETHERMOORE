#!/usr/bin/env python3
"""Unified Triangulation — All 3 systems + null space analysis
================================================================

Combines:
1. Semantic tongue detection (E4 — 85.7% det, 0% FP)
2. Hyperbolic helix separation (1.762 — 57% better than flat)
3. Triple-weight remainder (three witnesses)

Plus: NULL SPACE ANALYSIS
- Which tongue dimensions have ZERO signal?
- The absence pattern IS information
- Known attacks have characteristic "holes" in their tongue profile
- Clean text fills dimensions that attacks leave empty

Reverse-engineers attack vectors from expected results:
- Given known attack class → predict which tongues should activate
- Compare prediction vs actual → the GAP is the diagnostic
"""

from __future__ import annotations
import math, json, time, sys
from pathlib import Path
from typing import Dict, Tuple
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.adversarial.scbe_harness import (
    quantize_spin, build_metric_tensor,
    TONGUE_NAMES, TONGUE_WEIGHTS, PI, PHI,
    _ADVERSARIAL_PATTERNS, _MULTILINGUAL_OVERRIDE_PATTERNS,
)
from tests.adversarial.attack_corpus import BASELINE_CLEAN, get_all_attacks
from tests.adversarial.tongue_semantic import semantic_tongue_coords

G = build_metric_tensor()
ATTACKS = get_all_attacks()
CLEAN = BASELINE_CLEAN


# ═══════════════════════════════════════════════════════════
# Poincare ball ops (from hyperbolic_helix_test)
# ═══════════════════════════════════════════════════════════

def poincare_project(v, max_norm=0.999):
    norm = np.linalg.norm(v)
    return v * max_norm / norm if norm >= max_norm else v

def mobius_add(u, v, eps=1e-10):
    u_sq, v_sq, uv = np.dot(u,u), np.dot(v,v), np.dot(u,v)
    num = (1 + 2*uv + v_sq)*u + (1 - u_sq)*v
    denom = 1 + 2*uv + u_sq*v_sq + eps
    return poincare_project(num / denom)

def exp_map_zero(v, eps=1e-10):
    norm = np.linalg.norm(v)
    return np.tanh(norm) * v / norm if norm >= eps else v

def hyperbolic_distance(u, v, eps=1e-10):
    diff_sq = np.sum((u-v)**2)
    u_sq, v_sq = np.sum(u**2), np.sum(v**2)
    denom = (1-u_sq)*(1-v_sq)
    if denom <= eps: return float('inf')
    return math.acosh(max(1 + 2*diff_sq/max(denom,eps), 1.0))


# ═══════════════════════════════════════════════════════════
# Three subsystems
# ═══════════════════════════════════════════════════════════

def system1_semantic_detection(text: str, centroid: np.ndarray) -> Dict:
    """E4: Semantic tongue + lexical + geometric signals."""
    coords = semantic_tongue_coords(text)
    spin = quantize_spin(coords, centroid, 0.03)
    d_star = math.sqrt(sum(G[i,i]*(coords[i]-centroid[i])**2 for i in range(6)))
    cost = PI ** (PHI * min(d_star, 5.0))
    weighted = [abs(coords[i])*TONGUE_WEIGHTS[i] for i in range(6)]
    norm = math.sqrt(sum(c*c for c in coords))

    signals = []
    adv = sum(1 for p in _ADVERSARIAL_PATTERNS if p.search(text))
    ml = sum(1 for p in _MULTILINGUAL_OVERRIDE_PATTERNS if p.search(text))
    if spin.magnitude >= 5: signals.append("spin")
    if max(weighted)/max(sum(weighted),1e-9) > 0.6: signals.append("imbalance")
    if cost > 1.5: signals.append("cost")
    if norm > 0.3: signals.append("boundary")
    if adv >= 1: signals.append("lexical")
    if ml >= 1: signals.append("ml")

    has_geo = any(s in ["cost","spin","boundary","imbalance"] for s in signals)
    detected = len(signals)>=2 or adv>=2 or ml>=1 or (adv>=1 and has_geo)

    return {"detected": detected, "signals": signals, "cost": cost,
            "spin": spin.magnitude, "coords": coords, "d_star": d_star}


def system2_hyperbolic_helix(text: str) -> Dict:
    """Hyperbolic helix: separation in curved space."""
    tc = semantic_tongue_coords(text)
    point = np.zeros(6)
    for t in range(6):
        angle = 2*PI*t/6
        mag = tc[t] * 0.3
        tangent = np.zeros(6)
        tangent[t%6] = mag * math.cos(angle*PHI)
        tangent[(t+1)%6] = mag * math.sin(angle*PHI)
        step = exp_map_zero(tangent)
        point = mobius_add(point, step)
    point = poincare_project(point)
    radius = np.linalg.norm(point)
    return {"point": point, "radius": radius}


def system3_remainder(text: str) -> Dict:
    """Triple-weight remainder: three witnesses."""
    raw = semantic_tongue_coords(text)
    mooned = raw / PHI  # moon counter-weight
    # Foam dampen
    foamed = raw.copy()
    for i in range(5):
        tension = math.sqrt(TONGUE_WEIGHTS[i]*TONGUE_WEIGHTS[i+1])
        bleed = (raw[i]-raw[i+1]) / tension * 0.3
        foamed[i] -= bleed
        foamed[i+1] += bleed
    foamed = np.clip(foamed, 0, 1)

    remainder = np.abs(raw-mooned) + np.abs(mooned-foamed) + np.abs(raw-foamed)
    score = float(np.sum(remainder))
    dominant = TONGUE_NAMES[int(np.argmax(remainder))]
    return {"score": score, "remainder": remainder, "dominant": dominant}


# ═══════════════════════════════════════════════════════════
# NULL SPACE ANALYSIS
# ═══════════════════════════════════════════════════════════

def null_space_analysis(coords: np.ndarray) -> Dict:
    """Analyze what's ABSENT in the tongue coordinates.

    The absence pattern is information:
    - Which tongues have zero/near-zero signal?
    - What SHOULD be there but isn't?
    - The null signature identifies content type
    """
    threshold = 0.01  # below this = null
    null_tongues = [TONGUE_NAMES[i] for i in range(6) if coords[i] < threshold]
    active_tongues = [TONGUE_NAMES[i] for i in range(6) if coords[i] >= threshold]
    null_ratio = len(null_tongues) / 6
    null_pattern = "".join("_" if coords[i] < threshold else "#" for i in range(6))

    # Null energy: what COULD be there (potential)
    null_energy = sum(TONGUE_WEIGHTS[i] for i in range(6) if coords[i] < threshold)
    active_energy = sum(coords[i] * TONGUE_WEIGHTS[i] for i in range(6) if coords[i] >= threshold)

    return {
        "null_tongues": null_tongues,
        "active_tongues": active_tongues,
        "null_ratio": null_ratio,
        "null_pattern": null_pattern,  # visual: _=absent #=present
        "null_energy": round(null_energy, 4),  # potential energy in the empty space
        "active_energy": round(active_energy, 4),
        "potential_ratio": round(null_energy / max(active_energy, 1e-10), 4),
    }


# ═══════════════════════════════════════════════════════════
# Expected attack signatures (reverse-engineered)
# ═══════════════════════════════════════════════════════════

EXPECTED_SIGNATURES = {
    "direct_override": {"high": ["CA"], "low": ["UM", "DR"], "note": "Commands are engineering, lack depth"},
    "indirect_injection": {"high": ["CA", "AV"], "low": ["DR"], "note": "Technical + context manipulation"},
    "encoding_obfuscation": {"high": ["CA"], "low": ["KO", "UM", "DR"], "note": "Pure engineering, no meaning"},
    "multilingual": {"high": ["KO"], "low": ["CA", "DR"], "note": "Humanities (language), no tech"},
    "adaptive_sequence": {"high": ["AV", "CA"], "low": ["DR"], "note": "Social engineering + tech"},
    "tool_exfiltration": {"high": ["CA"], "low": ["KO", "UM"], "note": "Pure engineering exploit"},
    "tongue_manipulation": {"high": ["CA", "RU"], "low": ["KO"], "note": "Tech + math (knows the system)"},
    "spin_drift": {"high": ["AV"], "low": ["DR", "UM"], "note": "Social/temporal, lacks structure"},
    "boundary_exploit": {"high": ["CA"], "low": ["KO", "AV", "UM"], "note": "Raw engineering overflow"},
    "combined_multi": {"high": ["CA", "AV"], "low": ["UM"], "note": "Multi-vector engineering + social"},
}


# ═══════════════════════════════════════════════════════════
# Unified run
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print(f"{'UNIFIED TRIANGULATION — 3 SYSTEMS + NULL SPACE':^80}")
    print("=" * 80)
    print()

    # Calibrate
    clean_coords = [semantic_tongue_coords(p["prompt"]) for p in CLEAN]
    centroid = np.mean(clean_coords, axis=0)

    # Collect results per class
    class_results = {}
    total_detected = 0
    total_fp = 0

    for attack in ATTACKS:
        text = attack["prompt"]
        cls = attack.get("class", "unknown")

        s1 = system1_semantic_detection(text, centroid)
        s2 = system2_hyperbolic_helix(text)
        s3 = system3_remainder(text)
        null = null_space_analysis(s1["coords"])

        # UNIFIED DECISION: combine all 3 systems
        # System 1: detection signals
        # System 2: hyperbolic radius (farther = more suspicious)
        # System 3: remainder score (higher = more disagreement)
        # Null space: high null ratio = suspicious (attacks leave holes)

        unified_score = 0.0
        if s1["detected"]: unified_score += 1.0
        if s2["radius"] > 0.06: unified_score += 0.5  # farther than typical clean
        if s3["score"] > 0.15: unified_score += 0.5
        if null["null_ratio"] > 0.5: unified_score += 0.3  # more than half tongues empty
        if null["potential_ratio"] > 5.0: unified_score += 0.2  # lots of unused potential

        detected = unified_score >= 1.0

        if detected:
            total_detected += 1

        if cls not in class_results:
            class_results[cls] = {"total": 0, "detected": 0, "null_patterns": [], "remainder_scores": [], "helix_radii": []}
        class_results[cls]["total"] += 1
        if detected:
            class_results[cls]["detected"] += 1
        class_results[cls]["null_patterns"].append(null["null_pattern"])
        class_results[cls]["remainder_scores"].append(s3["score"])
        class_results[cls]["helix_radii"].append(s2["radius"])

    # Check FP
    for prompt in CLEAN:
        s1 = system1_semantic_detection(prompt["prompt"], centroid)
        s2 = system2_hyperbolic_helix(prompt["prompt"])
        s3 = system3_remainder(prompt["prompt"])
        null = null_space_analysis(s1["coords"])
        score = 0.0
        if s1["detected"]: score += 1.0
        if s2["radius"] > 0.06: score += 0.5
        if s3["score"] > 0.15: score += 0.5
        if null["null_ratio"] > 0.5: score += 0.3
        if null["potential_ratio"] > 5.0: score += 0.2
        if score >= 1.0:
            total_fp += 1

    det_rate = total_detected / max(len(ATTACKS), 1)
    fp_rate = total_fp / max(len(CLEAN), 1)

    print(f"UNIFIED: {total_detected}/91 detected ({det_rate:.1%}), {total_fp}/15 FP ({fp_rate:.1%})")
    print()

    # Per-class
    print(f"{'Class':<25} {'Det':>5} {'Rate':>7} {'Avg Rem':>8} {'Avg Rad':>8} {'Null Pattern':>15}")
    print("-" * 75)
    for cls, data in sorted(class_results.items()):
        rate = data["detected"] / max(data["total"], 1)
        avg_rem = sum(data["remainder_scores"]) / max(len(data["remainder_scores"]), 1)
        avg_rad = sum(data["helix_radii"]) / max(len(data["helix_radii"]), 1)
        # Most common null pattern
        from collections import Counter
        pattern = Counter(data["null_patterns"]).most_common(1)[0][0]
        print(f"{cls:<25} {data['detected']:>3}/{data['total']:<2} {rate:>6.0%} {avg_rem:>8.4f} {avg_rad:>8.4f} {pattern:>15}")

    # Null space signatures
    print()
    print(f"{'NULL SPACE SIGNATURES (what is ABSENT tells you what it IS)':^80}")
    print("-" * 80)
    print(f"{'Class':<25} {'Null Pattern':>15} {'Null Tongues':>25} {'Match Expected?':>15}")
    print("-" * 80)

    for cls, data in sorted(class_results.items()):
        pattern = Counter(data["null_patterns"]).most_common(1)[0][0]
        null_tongues = [TONGUE_NAMES[i] for i, c in enumerate(pattern) if c == "_"]
        expected = EXPECTED_SIGNATURES.get(cls, {}).get("low", [])
        match = set(null_tongues) & set(expected)
        match_pct = len(match) / max(len(expected), 1) if expected else 0
        match_str = f"{len(match)}/{len(expected)}" if expected else "n/a"
        print(f"{cls:<25} {pattern:>15} {', '.join(null_tongues) if null_tongues else 'none':>25} {match_str:>15}")

    # Reverse engineering: compare actual vs expected
    print()
    print(f"{'REVERSE ENGINEERING — Expected vs Actual Attack Signatures':^80}")
    print("-" * 80)
    for cls in sorted(EXPECTED_SIGNATURES.keys()):
        exp = EXPECTED_SIGNATURES[cls]
        if cls in class_results:
            data = class_results[cls]
            attacks_in_class = [a for a in ATTACKS if a.get("class") == cls]
            if attacks_in_class:
                avg_coords = np.mean([semantic_tongue_coords(a["prompt"]) for a in attacks_in_class], axis=0)
                actual_high = [TONGUE_NAMES[i] for i in np.argsort(avg_coords)[::-1][:2]]
                actual_low = [TONGUE_NAMES[i] for i in np.argsort(avg_coords)[:2]]
                print(f"  {cls}:")
                print(f"    Expected high: {exp['high']}  Actual high: {actual_high}")
                print(f"    Expected low:  {exp['low']}   Actual low:  {actual_low}")
                print(f"    Note: {exp['note']}")
                print()

    # Save
    out = Path("artifacts/benchmark/unified_triangulation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "detection_rate": round(det_rate, 4),
        "false_positive_rate": round(fp_rate, 4),
        "per_class": {cls: {"detected": d["detected"], "total": d["total"]} for cls, d in class_results.items()},
    }
    out.write_text(json.dumps(report, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
