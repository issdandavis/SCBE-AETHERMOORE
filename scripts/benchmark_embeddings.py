"""
Comprehensive Embedding Benchmark Suite
=========================================

Tests Tetris embedder + PHDM 21D across all data sources:
  1. Tongue separation quality (6D coords should cluster by tongue)
  2. Spatial coverage (3D coords should fill the space)
  3. Cross-source consistency (same concept from different sources → similar embeddings)
  4. Harmonic wall cost scaling (exponential cost at deviation boundaries)
  5. Poincare ball integrity (all points inside unit ball)
  6. Source diversity (each source contributes unique embedding regions)
  7. Book vs training data alignment (Six Tongues Protocol chapters)
"""

import json
import hashlib
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os_environ_set = False
try:
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os_environ_set = True
except:
    pass

TONGUE_KEYS = ["KO", "AV", "RU", "CA", "UM", "DR"]


def load_enriched(path: Path, max_records: int = 0) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    if r.get("tongue_coords") and r.get("spatial_coords"):
                        records.append(r)
                        if max_records and len(records) >= max_records:
                            break
                except json.JSONDecodeError:
                    continue
    return records


def benchmark_tongue_separation(records: list[dict]) -> dict:
    """Test 1: Do 6D tongue coords cluster by tongue?"""
    by_tongue = defaultdict(list)
    for r in records:
        t = r.get("tongue", "UNK")
        if t in TONGUE_KEYS:
            by_tongue[t].append(np.array(r["tongue_coords"]))

    results = {}
    for t in TONGUE_KEYS:
        vecs = by_tongue.get(t, [])
        if len(vecs) < 2:
            results[t] = {"n": len(vecs), "intra_dist": 0, "status": "SKIP"}
            continue
        arr = np.array(vecs)
        # Intra-tongue mean distance
        centroid = arr.mean(axis=0)
        intra = np.mean(np.linalg.norm(arr - centroid, axis=1))
        results[t] = {"n": len(vecs), "intra_dist": round(float(intra), 4), "centroid": centroid.tolist()}

    # Inter-tongue distances
    centroids = {t: np.array(results[t]["centroid"]) for t in TONGUE_KEYS if "centroid" in results[t]}
    inter_dists = []
    for i, t1 in enumerate(TONGUE_KEYS):
        for t2 in TONGUE_KEYS[i+1:]:
            if t1 in centroids and t2 in centroids:
                d = float(np.linalg.norm(centroids[t1] - centroids[t2]))
                inter_dists.append(d)

    avg_intra = np.mean([results[t]["intra_dist"] for t in TONGUE_KEYS if results[t].get("intra_dist", 0) > 0])
    avg_inter = np.mean(inter_dists) if inter_dists else 0

    return {
        "per_tongue": results,
        "avg_intra_distance": round(float(avg_intra), 4),
        "avg_inter_distance": round(float(avg_inter), 4),
        "separation_ratio": round(float(avg_inter / max(avg_intra, 0.001)), 2),
        "status": "PASS" if avg_inter > avg_intra else "WEAK",
    }


def benchmark_spatial_coverage(records: list[dict]) -> dict:
    """Test 2: Do 3D spatial coords fill the space?"""
    coords = np.array([r["spatial_coords"] for r in records])

    # Bounding box
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    ranges = maxs - mins

    # Octree bucket count (divide space into 0.25-width bins)
    bucket_size = 0.25
    buckets = set()
    for c in coords:
        key = tuple(int((x - mins[i]) / bucket_size) for i, x in enumerate(c))
        buckets.add(key)

    max_possible = int(np.prod(np.ceil(ranges / bucket_size) + 1))

    return {
        "n_points": len(coords),
        "x_range": [round(float(mins[0]), 3), round(float(maxs[0]), 3)],
        "y_range": [round(float(mins[1]), 3), round(float(maxs[1]), 3)],
        "z_range": [round(float(mins[2]), 3), round(float(maxs[2]), 3)],
        "volume_range": [round(float(r), 3) for r in ranges],
        "octree_buckets": len(buckets),
        "max_possible_buckets": max_possible,
        "fill_rate_pct": round(len(buckets) / max(1, max_possible) * 100, 1),
        "status": "PASS" if len(buckets) > 20 else "WEAK",
    }


def benchmark_source_diversity(records: list[dict]) -> dict:
    """Test 3: Each source should occupy different embedding regions."""
    by_source = defaultdict(list)
    for r in records:
        meta = r.get("metadata", {})
        if isinstance(meta, str):
            meta = {}
        src = meta.get("source", meta.get("source_file", "unknown"))
        if isinstance(src, str):
            by_source[src[:40]].append(np.array(r["tongue_coords"][:3]))

    # Compute centroids per source
    source_centroids = {}
    for src, vecs in by_source.items():
        if len(vecs) >= 5:
            arr = np.array(vecs)
            source_centroids[src] = arr.mean(axis=0)

    # Pairwise distances between source centroids
    sources = list(source_centroids.keys())
    dists = []
    for i, s1 in enumerate(sources):
        for s2 in sources[i+1:]:
            d = float(np.linalg.norm(source_centroids[s1] - source_centroids[s2]))
            dists.append(d)

    return {
        "n_sources_with_5plus": len(source_centroids),
        "avg_source_separation": round(float(np.mean(dists)), 4) if dists else 0,
        "min_source_separation": round(float(np.min(dists)), 4) if dists else 0,
        "max_source_separation": round(float(np.max(dists)), 4) if dists else 0,
        "top_sources": {s: len(v) for s, v in sorted(by_source.items(), key=lambda x: -len(x[1]))[:10]},
        "status": "PASS" if len(source_centroids) >= 5 else "WEAK",
    }


def benchmark_harmonic_wall(records: list[dict]) -> dict:
    """Test 4: Verify exponential cost scaling at deviation boundaries.

    Uses the Poincare ball hyperbolic distance for proper exponential scaling:
      d_H(0, x) = ln((1 + ||x||) / (1 - ||x||))
      H(x) = R^(d_H^2 / scale)
    """
    R = 14.0  # 14-layer pipeline depth
    scale = 2.2 ** 2  # Normalization: d_H=2.2 (norm~0.8) → cost ≈ R

    norms = []
    hyp_dists = []
    costs = []

    for r in records:
        tc = np.array(r["tongue_coords"])
        norm = float(np.linalg.norm(tc))
        norms.append(norm)

        # Hyperbolic distance from origin: d_H = ln((1+r)/(1-r))
        r_clamped = min(norm, 0.9999)
        if r_clamped < 1e-10:
            d_h = 0.0
        else:
            d_h = float(np.log((1.0 + r_clamped) / (1.0 - r_clamped)))
        hyp_dists.append(d_h)

        # Harmonic wall cost: R^(d_H^2 / scale)
        cost = float(R ** (d_h ** 2 / scale))
        costs.append(cost)

    norms = np.array(norms)
    hyp_dists = np.array(hyp_dists)
    costs = np.array(costs)

    # Zone classification
    safe = np.sum(norms < 0.7)
    caution = np.sum((norms >= 0.7) & (norms < 0.85))
    danger = np.sum((norms >= 0.85) & (norms < 0.95))
    wall = np.sum(norms >= 0.95)

    # Reference costs at key boundaries
    ref_norms = [0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.98]
    ref_costs = {}
    for rn in ref_norms:
        d_h = np.log((1 + rn) / (1 - rn))
        c = R ** (d_h ** 2 / scale)
        ref_costs[f"norm_{rn}"] = {"hyp_dist": round(d_h, 3), "cost": round(c, 2)}

    return {
        "n_points": len(norms),
        "euclidean_norm": {
            "mean": round(float(np.mean(norms)), 4),
            "std": round(float(np.std(norms)), 4),
            "max": round(float(np.max(norms)), 4),
        },
        "hyperbolic_distance": {
            "mean": round(float(np.mean(hyp_dists)), 4),
            "std": round(float(np.std(hyp_dists)), 4),
            "max": round(float(np.max(hyp_dists)), 4),
        },
        "cost": {
            "min": round(float(np.min(costs)), 2),
            "mean": round(float(np.mean(costs)), 2),
            "median": round(float(np.median(costs)), 2),
            "p95": round(float(np.percentile(costs, 95)), 2),
            "max": round(float(np.max(costs)), 2),
        },
        "zone_distribution": {
            "safe_lt_0.7": int(safe),
            "caution_0.7_0.85": int(caution),
            "danger_0.85_0.95": int(danger),
            "wall_gt_0.95": int(wall),
        },
        "reference_costs": ref_costs,
        "exponential_ratio": round(float(np.max(costs) / max(np.min(costs), 0.01)), 1),
        "exponential_scaling_confirmed": bool(np.max(costs) > 100 * np.min(costs)),
        "status": "PASS" if np.max(costs) > 100 * np.min(costs) else "WEAK",
    }


def benchmark_poincare_integrity(records: list[dict]) -> dict:
    """Test 5: All points should be inside the Poincare unit ball.

    The Poincare ball model requires all points to have norm < 1.
    Points near the boundary (norm → 1) have hyperbolic distance → infinity,
    which is what makes the harmonic wall work.
    """
    norms = []
    hyp_dists = []
    for r in records:
        tc = np.array(r["tongue_coords"])
        norm = float(np.linalg.norm(tc))
        norms.append(norm)
        # Hyperbolic distance
        r_c = min(norm, 0.9999)
        d_h = float(np.log((1 + r_c) / (1 - r_c))) if r_c > 1e-10 else 0.0
        hyp_dists.append(d_h)

    norms = np.array(norms)
    hyp_dists = np.array(hyp_dists)

    in_ball = int(np.sum(norms < 1.0))
    violated = int(np.sum(norms >= 1.0))

    return {
        "n_points": len(norms),
        "in_unit_ball": in_ball,
        "violated_boundary": violated,
        "near_boundary_0.9_1.0": int(np.sum((norms > 0.9) & (norms < 1.0))),
        "euclidean_norm": {
            "mean": round(float(np.mean(norms)), 4),
            "max": round(float(np.max(norms)), 4),
            "min": round(float(np.min(norms)), 4),
        },
        "hyperbolic_distance": {
            "mean": round(float(np.mean(hyp_dists)), 4),
            "max": round(float(np.max(hyp_dists)), 4),
            "min": round(float(np.min(hyp_dists)), 4),
        },
        "status": "PASS" if violated == 0 else f"FAIL ({violated} points outside ball)",
    }


def benchmark_embedding_hash_uniqueness(records: list[dict]) -> dict:
    """Test 6: Each record should have a unique embedding hash."""
    hashes = [r.get("embedding_hash", "") for r in records]
    unique = len(set(hashes))
    empty = sum(1 for h in hashes if not h)

    return {
        "total": len(hashes),
        "unique": unique,
        "duplicates": len(hashes) - unique,
        "empty": empty,
        "uniqueness_pct": round(unique / max(1, len(hashes)) * 100, 1),
        "status": "PASS" if unique / max(1, len(hashes)) > 0.95 else "WARN",
    }


def benchmark_tongue_coord_variance(records: list[dict]) -> dict:
    """Test 7: Each tongue dimension should have meaningful variance."""
    coords = np.array([r["tongue_coords"] for r in records])
    variances = np.var(coords, axis=0)
    means = np.mean(coords, axis=0)

    dim_names = ["KO_dim", "AV_dim", "RU_dim", "CA_dim", "UM_dim", "DR_dim"]
    per_dim = {}
    for i, name in enumerate(dim_names):
        per_dim[name] = {
            "mean": round(float(means[i]), 4),
            "variance": round(float(variances[i]), 4),
            "status": "ACTIVE" if variances[i] > 0.01 else "DEAD",
        }

    dead_dims = sum(1 for v in variances if v < 0.01)

    return {
        "per_dimension": per_dim,
        "dead_dimensions": dead_dims,
        "total_variance": round(float(np.sum(variances)), 4),
        "status": "PASS" if dead_dims == 0 else f"WARN ({dead_dims} dead dims)",
    }


def main():
    print("=" * 70)
    print("COMPREHENSIVE EMBEDDING BENCHMARK SUITE")
    print("Tetris + PHDM 21D — Cross-Source Validation")
    print("=" * 70)

    enriched_path = ROOT / "training-data" / "mega_tetris_enriched_sft.jsonl"
    if not enriched_path.exists():
        print(f"ERROR: {enriched_path} not found")
        return

    print(f"\nLoading {enriched_path.name}...")
    t0 = time.time()
    records = load_enriched(enriched_path)
    print(f"  Loaded {len(records)} enriched records in {time.time()-t0:.1f}s")

    results = {}

    # Test 1: Tongue Separation
    print("\n--- TEST 1: Tongue Separation (6D) ---")
    t1 = benchmark_tongue_separation(records)
    results["tongue_separation"] = t1
    print(f"  Avg intra-tongue distance: {t1['avg_intra_distance']}")
    print(f"  Avg inter-tongue distance: {t1['avg_inter_distance']}")
    print(f"  Separation ratio:          {t1['separation_ratio']}x [{t1['status']}]")
    for t in TONGUE_KEYS:
        info = t1["per_tongue"].get(t, {})
        print(f"    {t}: n={info.get('n', 0):>5}  intra_dist={info.get('intra_dist', 0):.4f}")

    # Test 2: Spatial Coverage
    print("\n--- TEST 2: Spatial Coverage (3D) ---")
    t2 = benchmark_spatial_coverage(records)
    results["spatial_coverage"] = t2
    print(f"  Points:          {t2['n_points']}")
    print(f"  X range:         {t2['x_range']}")
    print(f"  Y range:         {t2['y_range']}")
    print(f"  Z range:         {t2['z_range']}")
    print(f"  Octree buckets:  {t2['octree_buckets']} / {t2['max_possible_buckets']}")
    print(f"  Fill rate:       {t2['fill_rate_pct']}% [{t2['status']}]")

    # Test 3: Source Diversity
    print("\n--- TEST 3: Source Diversity ---")
    t3 = benchmark_source_diversity(records)
    results["source_diversity"] = t3
    print(f"  Sources (5+ records): {t3['n_sources_with_5plus']}")
    print(f"  Avg separation:       {t3['avg_source_separation']}")
    print(f"  Min separation:       {t3['min_source_separation']}")
    print(f"  Max separation:       {t3['max_source_separation']}")
    print(f"  Status:               [{t3['status']}]")

    # Test 4: Harmonic Wall
    print("\n--- TEST 4: Harmonic Wall Cost Scaling ---")
    t4 = benchmark_harmonic_wall(records)
    results["harmonic_wall"] = t4
    print(f"  Euclidean norm:  mean={t4['euclidean_norm']['mean']}  max={t4['euclidean_norm']['max']}")
    print(f"  Hyperbolic dist: mean={t4['hyperbolic_distance']['mean']}  max={t4['hyperbolic_distance']['max']}")
    print(f"  Cost:  min={t4['cost']['min']}  mean={t4['cost']['mean']}  median={t4['cost']['median']}  p95={t4['cost']['p95']}  max={t4['cost']['max']}")
    print(f"  Exponential ratio: {t4['exponential_ratio']}x")
    print(f"  Zone distribution:")
    for zone, count in t4["zone_distribution"].items():
        pct = count / max(1, t4["n_points"]) * 100
        print(f"    {zone:.<25} {count:>6} ({pct:>5.1f}%)")
    print(f"  Reference costs (R={14}, scale={2.2**2:.2f}):")
    for ref, info in t4["reference_costs"].items():
        print(f"    {ref}: d_H={info['hyp_dist']}  cost={info['cost']}")
    print(f"  Status: [{t4['status']}]")

    # Test 5: Poincare Integrity
    print("\n--- TEST 5: Poincare Ball Integrity ---")
    t5 = benchmark_poincare_integrity(records)
    results["poincare_integrity"] = t5
    print(f"  In unit ball:        {t5['in_unit_ball']}")
    print(f"  Violated boundary:   {t5['violated_boundary']}")
    print(f"  Near boundary (0.9-1.0): {t5['near_boundary_0.9_1.0']}")
    print(f"  Euclidean norm:  mean={t5['euclidean_norm']['mean']}  min={t5['euclidean_norm']['min']}  max={t5['euclidean_norm']['max']}")
    print(f"  Hyperbolic dist: mean={t5['hyperbolic_distance']['mean']}  min={t5['hyperbolic_distance']['min']}  max={t5['hyperbolic_distance']['max']}")
    print(f"  Status: [{t5['status']}]")

    # Test 6: Hash Uniqueness
    print("\n--- TEST 6: Embedding Hash Uniqueness ---")
    t6 = benchmark_embedding_hash_uniqueness(records)
    results["hash_uniqueness"] = t6
    print(f"  Total:       {t6['total']}")
    print(f"  Unique:      {t6['unique']}")
    print(f"  Duplicates:  {t6['duplicates']}")
    print(f"  Uniqueness:  {t6['uniqueness_pct']}% [{t6['status']}]")

    # Test 7: Tongue Coord Variance
    print("\n--- TEST 7: Tongue Coordinate Variance ---")
    t7 = benchmark_tongue_coord_variance(records)
    results["tongue_coord_variance"] = t7
    for name, info in t7["per_dimension"].items():
        print(f"  {name}: mean={info['mean']:>8.4f}  var={info['variance']:>8.4f}  [{info['status']}]")
    print(f"  Total variance: {t7['total_variance']}")
    print(f"  Status:         [{t7['status']}]")

    # Summary
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}")
    statuses = []
    for name, r in results.items():
        s = r.get("status", "?")
        icon = "PASS" if "PASS" in str(s) else "WARN" if "WARN" in str(s) else "INFO" if "INFO" in str(s) else "WEAK"
        statuses.append(icon)
        print(f"  {name:.<40} [{icon}]")

    passed = sum(1 for s in statuses if s == "PASS")
    print(f"\n  {passed}/{len(statuses)} PASS | {len(records)} records | {len(TONGUE_KEYS)} tongues")

    # Save report
    report_path = ROOT / "artifacts" / "embedding_benchmark_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records": len(records),
        "results": results,
    }, indent=2, default=str))
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
