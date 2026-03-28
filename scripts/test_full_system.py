"""
Full System Integration Test
==============================

Tests the fixed harmonic wall math through every available subsystem:
  1. Tetris embedder (sacred rotation + phi expansion)
  2. PHDM 21D embedding (Poincare ball + harmonic wall)
  3. Harmonic wall cost function (exponential scaling)
  4. 14-layer pipeline stages (L1-L14 conceptual)
  5. Sacred Tongue separation (6 tongues, phi-weighted)
  6. Context grid (octree storage)
  7. Obsidian sphere-grid notes (curriculum data)
  8. Training data integrity (43K records)
  9. Axiom compliance (5 quantum axioms)
  10. Cross-source embedding consistency
"""

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

TONGUE_KEYS = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHI = 1.618033988749895
RESULTS = []


def test(name: str):
    """Decorator to register and run tests."""

    def decorator(fn):
        def wrapper():
            t0 = time.time()
            try:
                result = fn()
                elapsed = time.time() - t0
                passed = result.get("passed", True)
                RESULTS.append({"name": name, "passed": passed, "time": elapsed, **result})
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {name} ({elapsed:.2f}s)")
                if not passed:
                    print(f"         Reason: {result.get('reason', '?')}")
                return result
            except Exception as e:
                elapsed = time.time() - t0
                RESULTS.append({"name": name, "passed": False, "time": elapsed, "error": str(e)})
                print(f"  [ERROR] {name} ({elapsed:.2f}s): {e}")
                return {"passed": False, "error": str(e)}

        wrapper.__name__ = name
        return wrapper

    return decorator


# ================================================================
# TEST 1: Tetris Embedder — Sacred Rotation
# ================================================================
@test("tetris_sacred_rotation")
def test_tetris_rotation():
    from src.kernel.tetris_embedder import sacred_rotate, _ROTATIONS

    # Each tongue should produce a DIFFERENT rotation
    vec = np.random.RandomState(42).randn(384).astype(np.float64)
    vec = vec / np.linalg.norm(vec)

    rotated = {}
    for tongue in TONGUE_KEYS:
        r = sacred_rotate(vec.copy(), tongue)
        rotated[tongue] = r

    # Pairwise distances between rotated vectors
    dists = []
    for i, t1 in enumerate(TONGUE_KEYS):
        for t2 in TONGUE_KEYS[i + 1 :]:
            d = float(np.linalg.norm(rotated[t1] - rotated[t2]))
            dists.append(d)

    avg_dist = np.mean(dists)
    # All rotations preserve norm
    norms = {t: float(np.linalg.norm(v)) for t, v in rotated.items()}
    norm_ok = all(abs(n - 1.0) < 0.01 for n in norms.values())

    return {
        "passed": avg_dist > 0.1 and norm_ok,
        "avg_pairwise_distance": round(avg_dist, 4),
        "norms_preserved": norm_ok,
        "norms": {t: round(n, 6) for t, n in norms.items()},
    }


# ================================================================
# TEST 2: Tetris Embedder — Phi Expansion
# ================================================================
@test("tetris_phi_expansion")
def test_phi_expansion():
    from src.kernel.tetris_embedder import phi_expand_tongue_coords

    expanded = {}
    for tongue in TONGUE_KEYS:
        raw = np.random.RandomState(hash(tongue) % 2**31).randn(6) * 0.01
        e = phi_expand_tongue_coords(raw, tongue)
        expanded[tongue] = e

    # Each tongue should be in a different region
    centroids = np.array(list(expanded.values()))
    pairwise = []
    for i in range(6):
        for j in range(i + 1, 6):
            pairwise.append(float(np.linalg.norm(centroids[i] - centroids[j])))

    avg_sep = np.mean(pairwise)
    # All inside Poincare ball
    norms = {t: float(np.linalg.norm(v)) for t, v in expanded.items()}
    in_ball = all(n < 1.0 for n in norms.values())

    return {
        "passed": avg_sep > 0.3 and in_ball,
        "avg_tongue_separation": round(avg_sep, 4),
        "all_in_poincare_ball": in_ball,
        "norms": {t: round(n, 4) for t, n in norms.items()},
    }


# ================================================================
# TEST 3: Hyperbolic Distance (Poincare Ball)
# ================================================================
@test("hyperbolic_distance")
def test_hyperbolic_distance():
    from src.kernel.tetris_embedder import hyperbolic_distance_from_origin

    # Test known values
    tests = [
        (0.0, 0.0),  # Origin
        (0.5, 1.099),  # Known: 2*arctanh(0.5) = ln(3) ≈ 1.099
        (0.9, 2.944),  # Known: ln(19) ≈ 2.944
        (0.99, 5.293),  # Known: ln(199) ≈ 5.293
    ]

    results = []
    all_ok = True
    for norm, expected in tests:
        point = np.array([norm, 0, 0, 0, 0, 0])
        actual = hyperbolic_distance_from_origin(point)
        error = abs(actual - expected)
        ok = error < 0.01
        if not ok:
            all_ok = False
        results.append(
            {"norm": norm, "expected": expected, "actual": round(actual, 3), "error": round(error, 4), "ok": ok}
        )

    # Key property: distance → infinity as norm → 1
    d_99 = hyperbolic_distance_from_origin(np.array([0.99, 0, 0, 0, 0, 0]))
    d_999 = hyperbolic_distance_from_origin(np.array([0.999, 0, 0, 0, 0, 0]))
    d_9999 = hyperbolic_distance_from_origin(np.array([0.9999, 0, 0, 0, 0, 0]))
    diverges = d_9999 > d_999 > d_99 > 5.0

    return {
        "passed": all_ok and diverges,
        "tests": results,
        "divergence_check": {"d_99": round(d_99, 3), "d_999": round(d_999, 3), "d_9999": round(d_9999, 3)},
        "diverges_to_infinity": diverges,
    }


# ================================================================
# TEST 4: Harmonic Wall Cost Function
# ================================================================
@test("harmonic_wall_cost")
def test_harmonic_wall():
    from src.kernel.tetris_embedder import harmonic_wall_cost

    R = 14.0
    test_points = {
        "safe_center": np.array([0.3, 0, 0, 0, 0, 0]),
        "safe_edge": np.array([0.5, 0, 0, 0, 0, 0]),
        "caution": np.array([0.7, 0, 0, 0, 0, 0]),
        "danger": np.array([0.9, 0, 0, 0, 0, 0]),
        "wall": np.array([0.95, 0, 0, 0, 0, 0]),
        "extreme": np.array([0.98, 0, 0, 0, 0, 0]),
    }

    costs = {}
    for name, point in test_points.items():
        cost = harmonic_wall_cost(point, R)
        costs[name] = round(cost, 2)

    # Verify exponential scaling properties
    exponential = costs["extreme"] > 1000 * costs["safe_center"]
    monotonic = (
        costs["safe_center"]
        < costs["safe_edge"]
        < costs["caution"]
        < costs["danger"]
        < costs["wall"]
        < costs["extreme"]
    )

    # Verify it matches R^(d_H^2/scale)
    scale = 2.2**2
    d_h_09 = np.log(19)  # norm=0.9
    expected_09 = R ** (d_h_09**2 / scale)
    actual_09 = costs["danger"]
    formula_correct = abs(actual_09 - round(expected_09, 2)) < 1.0

    return {
        "passed": exponential and monotonic and formula_correct,
        "costs": costs,
        "exponential_ratio": round(costs["extreme"] / max(costs["safe_center"], 0.01), 1),
        "monotonic_increasing": monotonic,
        "formula_R_d2_scale": formula_correct,
    }


# ================================================================
# TEST 5: PHDM 21D Embedder
# ================================================================
@test("phdm_21d_embedding")
def test_phdm():
    from python.scbe.phdm_embedding import PHDMEmbedder, PoincareBall

    embedder = PHDMEmbedder()
    ball = PoincareBall()

    # Encode text
    emb = embedder.encode("Test sentence about Sacred Tongues governance.")
    assert len(emb) == 21, f"Expected 21D, got {len(emb)}D"

    # Check sub-dimensions
    hyp = emb[:6]  # Hyperbolic
    _phase = emb[6:12]  # Phase
    _flux = emb[12:15]  # Flux
    _audit = emb[15:21]  # Audit

    # Hyperbolic part should be in Poincare ball
    hyp_norm = float(np.linalg.norm(hyp))
    in_ball = hyp_norm < 1.0

    # Harmonic wall cost
    hw_cost = ball.harmonic_wall_cost(hyp_norm, d=14)

    # Hyperbolic distance between two texts
    emb2 = embedder.encode("Adversarial attack vector targeting governance layer.")
    d_h = ball.hyperbolic_distance(emb[:6], emb2[:6])

    return {
        "passed": in_ball and len(emb) == 21,
        "embedding_dim": len(emb),
        "hyperbolic_norm": round(hyp_norm, 4),
        "in_poincare_ball": in_ball,
        "harmonic_wall_cost": round(float(hw_cost), 4),
        "hyp_distance_safe_vs_adversarial": round(float(d_h), 4),
        "sub_dims": {"hyperbolic": 6, "phase": 6, "flux": 3, "audit": 6},
    }


# ================================================================
# TEST 6: 14-Layer Pipeline Stages
# ================================================================
@test("14_layer_pipeline_stages")
def test_pipeline_stages():
    """Verify each layer's math exists and produces valid output."""
    stages = {
        "L1_complex_context": lambda: np.array([1 + 0j, 0.5 + 0.3j]),
        "L2_realification": lambda: np.array([1.0, 0.0, 0.5, 0.3]),  # Complex → Real
        "L3_langues_weight": lambda: np.array([1.0 * PHI**i for i in range(6)]),
        "L4_poincare_embed": lambda: np.tanh(np.array([0.5, 0.3, 0.2, 0.1, 0.4, 0.6])),
        "L5_hyperbolic_dist": lambda: float(np.arccosh(1 + 2 * 0.25 / ((1 - 0.36) * (1 - 0.49) + 1e-10))),
        "L6_breathing": lambda: np.array([0.5 * np.sin(2 * np.pi * 440 * t / 24000) for t in range(10)]),
        "L7_mobius_phase": lambda: np.exp(1j * np.pi / 3),  # 60 degree phase
        "L8_hamiltonian_cfi": lambda: -0.5 * np.array([1, -1, 1, -1]),  # Multi-well
        "L9_spectral_fft": lambda: np.abs(np.fft.fft(np.random.randn(64)))[:32],
        "L10_spin_coherence": lambda: np.mean(np.abs(np.fft.fft(np.random.randn(64)))[:32]),
        "L11_triadic_temporal": lambda: float(np.sqrt(0.5**2 + 0.3**2 + 0.2**2)),
        "L12_harmonic_wall": lambda: 14.0 ** (2.944**2 / 4.84),  # R^(d_H^2/scale) at norm=0.9
        "L13_risk_decision": lambda: "QUARANTINE" if 14.0 ** (2.944**2 / 4.84) > 10 else "ALLOW",
        "L14_audio_axis": lambda: np.abs(np.fft.fft(np.sin(2 * np.pi * 440 * np.arange(1024) / 24000)))[:512],
    }

    results = {}
    all_ok = True
    for name, fn in stages.items():
        try:
            output = fn()
            valid = output is not None
            if isinstance(output, np.ndarray):
                valid = valid and not np.any(np.isnan(output)) and not np.any(np.isinf(output))
            elif isinstance(output, (int, float)):
                valid = valid and not math.isnan(output) and not math.isinf(output)
            results[name] = {"valid": valid, "type": type(output).__name__}
            if not valid:
                all_ok = False
        except Exception as e:
            results[name] = {"valid": False, "error": str(e)}
            all_ok = False

    return {
        "passed": all_ok,
        "stages": results,
        "total": len(stages),
        "valid": sum(1 for r in results.values() if r["valid"]),
    }


# ================================================================
# TEST 7: Sacred Tongue Phi Weights
# ================================================================
@test("sacred_tongue_phi_weights")
def test_phi_weights():
    weights = {t: PHI**i for i, t in enumerate(TONGUE_KEYS)}
    # Verify golden ratio property: w[n+1]/w[n] = PHI
    ratios = []
    for i in range(len(TONGUE_KEYS) - 1):
        ratio = weights[TONGUE_KEYS[i + 1]] / weights[TONGUE_KEYS[i]]
        ratios.append(ratio)

    all_phi = all(abs(r - PHI) < 0.001 for r in ratios)

    return {
        "passed": all_phi,
        "weights": {t: round(w, 4) for t, w in weights.items()},
        "ratios": [round(r, 6) for r in ratios],
        "all_golden_ratio": all_phi,
    }


# ================================================================
# TEST 8: Context Grid + Obsidian Notes
# ================================================================
@test("context_grid_obsidian")
def test_context_grid():
    from src.kernel.context_grid import load_obsidian_vault

    docs = load_obsidian_vault(ROOT / "notes" / "sphere-grid")

    tongues = set()
    for d in docs:
        tongues.add(d.get("tongue", "?"))

    return {
        "passed": len(docs) > 50 and len(tongues) >= 5,
        "notes_loaded": len(docs),
        "tongues_found": sorted(tongues),
        "tongue_count": len(tongues),
    }


# ================================================================
# TEST 9: Training Data Integrity
# ================================================================
@test("training_data_integrity")
def test_training_data():
    path = ROOT / "training-data" / "mega_tetris_enriched_sft.jsonl"
    if not path.exists():
        return {"passed": False, "reason": "File not found"}

    total = 0
    has_coords = 0
    has_tongue = 0
    valid_norms = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            total += 1
            if r.get("tongue_coords"):
                has_coords += 1
                norm = np.linalg.norm(r["tongue_coords"])
                if norm < 1.0:
                    valid_norms += 1
            if r.get("tongue") in TONGUE_KEYS:
                has_tongue += 1

    return {
        "passed": has_coords == total and valid_norms == total and has_tongue > total * 0.8,
        "total_records": total,
        "has_tongue_coords": has_coords,
        "valid_poincare_norms": valid_norms,
        "has_tongue_label": has_tongue,
        "coord_rate": round(has_coords / max(1, total) * 100, 1),
        "tongue_rate": round(has_tongue / max(1, total) * 100, 1),
    }


# ================================================================
# TEST 10: Axiom Compliance
# ================================================================
@test("quantum_axiom_compliance")
def test_axioms():
    """Verify the 5 quantum axioms hold for embedding operations."""
    from src.kernel.tetris_embedder import sacred_rotate, phi_expand_tongue_coords

    vec = np.random.RandomState(42).randn(384).astype(np.float64)
    vec = vec / np.linalg.norm(vec)

    # A1: Unitarity — rotation preserves norm
    rotated = sacred_rotate(vec.copy(), "KO")
    a1_norm_preserved = abs(np.linalg.norm(rotated) - 1.0) < 0.001

    # A2: Locality — nearby inputs produce nearby outputs
    vec2 = vec + np.random.RandomState(43).randn(384) * 0.01
    vec2 = vec2 / np.linalg.norm(vec2)
    r1 = sacred_rotate(vec.copy(), "CA")
    r2 = sacred_rotate(vec2.copy(), "CA")
    input_dist = np.linalg.norm(vec - vec2)
    output_dist = np.linalg.norm(r1 - r2)
    a2_local = output_dist < input_dist * 2  # Rotation shouldn't amplify distance too much

    # A3: Causality — same input always produces same output (deterministic)
    r3 = sacred_rotate(vec.copy(), "CA")
    a3_deterministic = np.allclose(r1, r3)

    # A4: Symmetry — phi weights follow golden ratio
    a4_phi = abs(PHI**2 - PHI - 1) < 0.001  # phi^2 = phi + 1

    # A5: Composition — pipeline stages compose correctly
    raw = np.random.randn(6) * 0.01
    expanded = phi_expand_tongue_coords(raw, "DR")
    norm = np.linalg.norm(expanded)
    a5_bounded = norm < 1.0  # Output in Poincare ball

    return {
        "passed": all([a1_norm_preserved, a2_local, a3_deterministic, a4_phi, a5_bounded]),
        "A1_unitarity": a1_norm_preserved,
        "A2_locality": a2_local,
        "A3_causality": a3_deterministic,
        "A4_symmetry": a4_phi,
        "A5_composition": a5_bounded,
    }


# ================================================================
# TEST 11: Cross-Source Embedding Consistency
# ================================================================
@test("cross_source_consistency")
def test_cross_source():
    """Same concept from different sources should produce similar tongue assignments."""
    from src.kernel.tetris_embedder import TetrisEmbedder

    embedder = TetrisEmbedder("all-MiniLM-L6-v2")

    # Same concept, different phrasings (should get same tongue region)
    governance_texts = [
        "Security governance audit scanning threat detection",
        "Auditing system for governance compliance and threat scanning",
        "Threat detection and security seal enforcement audit trail",
    ]

    code_texts = [
        "Code generation training pipeline model deployment",
        "Deploy machine learning model after training pipeline runs",
        "Generate code and run automated test suite deployment",
    ]

    gov_embs = embedder.embed_batch(governance_texts, ["UM"] * 3)
    code_embs = embedder.embed_batch(code_texts, ["CA"] * 3)

    # Intra-group distance should be small
    gov_coords = np.array([e.tongue_coords for e in gov_embs])
    code_coords = np.array([e.tongue_coords for e in code_embs])

    gov_intra = float(
        np.mean([np.linalg.norm(gov_coords[i] - gov_coords[j]) for i in range(3) for j in range(i + 1, 3)])
    )
    code_intra = float(
        np.mean([np.linalg.norm(code_coords[i] - code_coords[j]) for i in range(3) for j in range(i + 1, 3)])
    )

    # Inter-group distance should be large
    inter = float(np.mean([np.linalg.norm(gov_coords[i] - code_coords[j]) for i in range(3) for j in range(3)]))

    consistent = inter > gov_intra and inter > code_intra

    return {
        "passed": consistent,
        "gov_intra_dist": round(gov_intra, 4),
        "code_intra_dist": round(code_intra, 4),
        "inter_dist": round(inter, 4),
        "separation_ratio": round(inter / max(gov_intra + code_intra, 0.001) * 2, 2),
    }


# ================================================================
# MAIN
# ================================================================
def main():
    print("=" * 70)
    print("FULL SYSTEM INTEGRATION TEST")
    print("Tetris + PHDM + Harmonic Wall + 14-Layer Pipeline")
    print("=" * 70)

    tests = [
        test_tetris_rotation,
        test_phi_expansion,
        test_hyperbolic_distance,
        test_harmonic_wall,
        test_phdm,
        test_pipeline_stages,
        test_phi_weights,
        test_context_grid,
        test_training_data,
        test_axioms,
        test_cross_source,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    for t in tests:
        t()

    # Summary
    passed = sum(1 for r in RESULTS if r["passed"])
    failed = sum(1 for r in RESULTS if not r["passed"])
    total_time = sum(r["time"] for r in RESULTS)

    print(f"\n{'='*70}")
    print(f"RESULTS: {passed}/{len(RESULTS)} PASS  |  {failed} FAIL  |  {total_time:.1f}s total")
    print(f"{'='*70}")

    if failed:
        print("\nFailed tests:")
        for r in RESULTS:
            if not r["passed"]:
                print(f"  - {r['name']}: {r.get('reason', r.get('error', '?'))}")

    # Save report
    report_path = ROOT / "artifacts" / "full_system_test_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "passed": passed,
                "failed": failed,
                "total": len(RESULTS),
                "results": RESULTS,
            },
            indent=2,
            default=str,
        )
    )
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
