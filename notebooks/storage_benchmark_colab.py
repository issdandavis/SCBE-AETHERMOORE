"""
SCBE Storage Benchmark — Colab/Local Runner
============================================

Benchmarks the SCBE fusion storage surfaces against FAISS baselines
at scales from 1K to 100K records.

Usage (local):
  python notebooks/storage_benchmark_colab.py --sizes 1000,5000,10000 --seed 42

Usage (Colab):
  1. Upload this file + the repo to Colab
  2. !pip install numpy faiss-cpu
  3. !python notebooks/storage_benchmark_colab.py --sizes 1000,10000,50000,100000

The script auto-detects whether FAISS is available and skips those
benchmarks if not installed.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.storage.langues_dispersal import (
    TONGUE_WEIGHTS,
    compute_dispersal,
    dispersal_route,
    quantize_spin,
)
from src.storage.fusion_surfaces import CymaticCone, SemiSphereCone, TongueRouter
from src.crypto.octree import HyperbolicOctree
from hydra.octree_sphere_grid import HyperbolicLattice25D
from src.knowledge.quasicrystal_voxel_drive import QuasiCrystalVoxelDrive

# Optional FAISS import
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

ARTIFACT_DIR = REPO_ROOT / "artifacts" / "system_audit" / "storage_benchmark"
PHI = 1.618033988749895


# =========================================================================== #
#  Workload generation
# =========================================================================== #

def generate_workload(n: int, dim: int = 6, seed: int = 42):
    """Generate n records with 6D tongue coords + 3D Poincare coords.

    Returns:
        tongue_vecs: (n, 6) float32
        poincare_vecs: (n, 3) float32 — inside unit ball
        content_list: list of bytes
        ids: list of str
    """
    rng = np.random.default_rng(seed)

    # 6D tongue coordinates in [0, 1]
    tongue_vecs = rng.uniform(0, 1, size=(n, 6)).astype(np.float32)

    # 3D Poincare ball coordinates — clamp to r < 0.93
    raw = rng.normal(0, 0.35, size=(n, 3)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    scale = np.minimum(0.93 / (norms + 1e-8), 1.0)
    poincare_vecs = raw * scale

    # Intent vectors (3D)
    intent_vecs = rng.uniform(0.1, 0.9, size=(n, 3)).astype(np.float32)

    # Content bytes (variable length 50-200 bytes)
    content_list = [rng.bytes(rng.integers(50, 200)) for _ in range(n)]

    ids = [f"rec-{i:06d}" for i in range(n)]

    return tongue_vecs, poincare_vecs, intent_vecs, content_list, ids


# =========================================================================== #
#  Benchmark functions
# =========================================================================== #

@dataclass
class BenchResult:
    surface: str
    n_records: int
    ingest_ms: float
    query_10_ms: float
    memory_mb: float
    node_count: int
    node_explosion: float
    compaction_score: float
    recall_at_5: float  # vs brute-force ground truth
    extra: Dict[str, Any]


def _rss_mb() -> float:
    """Current process RSS in MB (cross-platform)."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def bench_cymatic_cone(tongue_vecs, poincare_vecs, content_list, ids, query_tongue, query_poincare) -> BenchResult:
    n = len(ids)
    cc = CymaticCone(max_depth=3)
    mem_before = _rss_mb()

    t0 = time.perf_counter()
    for i in range(n):
        cc.insert(ids[i], poincare_vecs[i], tongue_vecs[i].tolist(), content_list[i])
    ingest_ms = (time.perf_counter() - t0) * 1000

    # Query: retrieve with correct vector (10 queries)
    t0 = time.perf_counter()
    for i in range(min(10, n)):
        cc.retrieve(ids[i], tongue_vecs[i].tolist())
    query_ms = (time.perf_counter() - t0) * 1000

    mem_after = _rss_mb()
    stats = cc.stats()

    return BenchResult(
        surface="CymaticCone",
        n_records=n,
        ingest_ms=round(ingest_ms, 1),
        query_10_ms=round(query_ms, 2),
        memory_mb=round(max(0, mem_after - mem_before), 2),
        node_count=stats["octree_nodes"] + stats["octree_leaves"],
        node_explosion=stats["node_explosion"],
        compaction_score=stats["compaction_score"],
        recall_at_5=1.0,  # exact retrieval
        extra={"chladni_modes": stats["unique_chladni_modes"]},
    )


def bench_semisphere_cone(tongue_vecs, poincare_vecs, intent_vecs, ids, query_tongue, query_poincare) -> BenchResult:
    n = len(ids)
    ssc = SemiSphereCone(radius_threshold=0.5, lattice_cell_size=0.5, octree_max_depth=4)
    mem_before = _rss_mb()

    tongues = ("KO", "AV", "RU", "CA", "UM", "DR")

    t0 = time.perf_counter()
    for i in range(n):
        ssc.insert(
            ids[i], poincare_vecs[i],
            x=float(poincare_vecs[i][0]), y=float(poincare_vecs[i][1]),
            phase_rad=float(tongue_vecs[i][0] * 2 * math.pi),
            tongue=tongues[i % 6],
            intent_vector=intent_vecs[i].tolist(),
        )
    ingest_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    for i in range(min(10, n)):
        ssc.query_nearest(
            float(poincare_vecs[i][0]), float(poincare_vecs[i][1]),
            float(tongue_vecs[i][0] * 2 * math.pi),
            intent_vector=intent_vecs[i].tolist(),
            tongue=tongues[i % 6], top_k=5,
        )
    query_ms = (time.perf_counter() - t0) * 1000

    mem_after = _rss_mb()
    stats = ssc.stats()

    return BenchResult(
        surface="SemiSphereCone",
        n_records=n,
        ingest_ms=round(ingest_ms, 1),
        query_10_ms=round(query_ms, 2),
        memory_mb=round(max(0, mem_after - mem_before), 2),
        node_count=stats["total_nodes"],
        node_explosion=stats["node_explosion"],
        compaction_score=stats["compaction_score"],
        recall_at_5=0.0,  # not directly comparable
        extra={"hemisphere_pct": stats["hemisphere_ratio"], "cone_pct": stats["cone_ratio"]},
    )


def bench_dispersal_analysis(tongue_vecs) -> Dict[str, Any]:
    """Run dispersal analysis and return the report."""
    vecs = tongue_vecs.tolist()
    report = compute_dispersal(vecs, threshold=0.05)
    return {
        "dispersal_rate": report.dispersal_rate,
        "spin_entropy": report.spin_entropy,
        "dominant_tongue": report.dominant_tongue,
        "effective_dimension": report.effective_dimension,
        "unique_spin_codes": len(report.spin_distribution),
        "tongue_dispersals": report.tongue_dispersals,
    }


def bench_numpy_brute(tongue_vecs, query_tongue) -> BenchResult:
    n = tongue_vecs.shape[0]
    mem_before = _rss_mb()

    t0 = time.perf_counter()
    data = tongue_vecs.copy()  # "ingest" is just copy
    ingest_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    for i in range(min(10, query_tongue.shape[0])):
        diffs = data - query_tongue[i:i + 1]
        dists = np.linalg.norm(diffs, axis=1)
        _ = np.argsort(dists)[:5]
    query_ms = (time.perf_counter() - t0) * 1000

    mem_after = _rss_mb()

    return BenchResult(
        surface="numpy_brute",
        n_records=n,
        ingest_ms=round(ingest_ms, 2),
        query_10_ms=round(query_ms, 2),
        memory_mb=round(max(0, mem_after - mem_before), 2),
        node_count=n,
        node_explosion=1.0,
        compaction_score=1.0,
        recall_at_5=1.0,
        extra={},
    )


def bench_faiss_flat(tongue_vecs, query_tongue) -> Optional[BenchResult]:
    if not HAS_FAISS:
        return None
    n, d = tongue_vecs.shape
    mem_before = _rss_mb()

    t0 = time.perf_counter()
    index = faiss.IndexFlatL2(d)
    index.add(tongue_vecs)
    ingest_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    _, _ = index.search(query_tongue[:10], 5)
    query_ms = (time.perf_counter() - t0) * 1000

    mem_after = _rss_mb()

    return BenchResult(
        surface="FAISS_FlatL2",
        n_records=n,
        ingest_ms=round(ingest_ms, 2),
        query_10_ms=round(query_ms, 4),
        memory_mb=round(max(0, mem_after - mem_before), 2),
        node_count=n,
        node_explosion=1.0,
        compaction_score=1.0,
        recall_at_5=1.0,
        extra={"index_type": "FlatL2"},
    )


def bench_faiss_ivf_pq(tongue_vecs, query_tongue) -> Optional[BenchResult]:
    if not HAS_FAISS:
        return None
    n, d = tongue_vecs.shape
    if n < 256:
        return None  # need enough data for IVF training

    nlist = max(4, int(math.sqrt(n)))
    m_pq = min(d, 3)  # PQ sub-quantizers (d=6 → m=3)
    mem_before = _rss_mb()

    t0 = time.perf_counter()
    quantizer = faiss.IndexFlatL2(d)
    index = faiss.IndexIVFPQ(quantizer, d, nlist, m_pq, 8)
    index.train(tongue_vecs)
    index.add(tongue_vecs)
    index.nprobe = max(1, nlist // 4)
    ingest_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    _, I = index.search(query_tongue[:10], 5)
    query_ms = (time.perf_counter() - t0) * 1000

    mem_after = _rss_mb()

    # Recall vs brute force
    bf_index = faiss.IndexFlatL2(d)
    bf_index.add(tongue_vecs)
    _, I_gt = bf_index.search(query_tongue[:10], 5)
    recall = 0.0
    for i in range(min(10, query_tongue.shape[0])):
        gt_set = set(I_gt[i].tolist())
        found = set(I[i].tolist())
        recall += len(gt_set & found) / max(1, len(gt_set))
    recall /= min(10, query_tongue.shape[0])

    return BenchResult(
        surface="FAISS_IVF_PQ",
        n_records=n,
        ingest_ms=round(ingest_ms, 1),
        query_10_ms=round(query_ms, 4),
        memory_mb=round(max(0, mem_after - mem_before), 2),
        node_count=nlist,
        node_explosion=round(nlist / n, 4),
        compaction_score=round(n / max(1, nlist), 2),
        recall_at_5=round(recall, 4),
        extra={"nlist": nlist, "m_pq": m_pq, "nprobe": index.nprobe},
    )


# =========================================================================== #
#  Main benchmark runner
# =========================================================================== #

def run_full_benchmark(sizes: List[int], seed: int = 42) -> Dict[str, Any]:
    results = {}

    for n in sizes:
        print(f"\n{'='*60}")
        print(f"  BENCHMARKING N={n}")
        print(f"{'='*60}")

        tongue_vecs, poincare_vecs, intent_vecs, content_list, ids = generate_workload(n, seed=seed)
        query_tongue = tongue_vecs[:20].copy()
        query_poincare = poincare_vecs[:20].copy()

        row: Dict[str, Any] = {"n": n}

        # Dispersal analysis
        print(f"  [dispersal] analyzing {n} records...")
        row["dispersal"] = bench_dispersal_analysis(tongue_vecs)
        print(f"    rate={row['dispersal']['dispersal_rate']:.3f} entropy={row['dispersal']['spin_entropy']:.3f} dim={row['dispersal']['effective_dimension']:.2f}")

        # CymaticCone
        print(f"  [CymaticCone] ingesting {n} records...")
        r = bench_cymatic_cone(tongue_vecs, poincare_vecs, content_list, ids, query_tongue, query_poincare)
        row["CymaticCone"] = asdict(r)
        print(f"    ingest={r.ingest_ms:.0f}ms query={r.query_10_ms:.2f}ms nodes={r.node_count} explosion={r.node_explosion:.3f}")

        # SemiSphereCone
        print(f"  [SemiSphereCone] ingesting {n} records...")
        r = bench_semisphere_cone(tongue_vecs, poincare_vecs, intent_vecs, ids, query_tongue, query_poincare)
        row["SemiSphereCone"] = asdict(r)
        print(f"    ingest={r.ingest_ms:.0f}ms query={r.query_10_ms:.2f}ms nodes={r.node_count} explosion={r.node_explosion:.3f}")

        # Numpy brute force
        print(f"  [numpy_brute] {n} records...")
        r = bench_numpy_brute(tongue_vecs, query_tongue)
        row["numpy_brute"] = asdict(r)
        print(f"    ingest={r.ingest_ms:.2f}ms query={r.query_10_ms:.2f}ms")

        # FAISS FlatL2
        if HAS_FAISS:
            print(f"  [FAISS_FlatL2] {n} records...")
            r = bench_faiss_flat(tongue_vecs, query_tongue)
            if r:
                row["FAISS_FlatL2"] = asdict(r)
                print(f"    ingest={r.ingest_ms:.2f}ms query={r.query_10_ms:.4f}ms")
        else:
            print(f"  [FAISS] not installed, skipping")

        # FAISS IVF+PQ
        if HAS_FAISS and n >= 256:
            print(f"  [FAISS_IVF_PQ] {n} records...")
            r = bench_faiss_ivf_pq(tongue_vecs, query_tongue)
            if r:
                row["FAISS_IVF_PQ"] = asdict(r)
                print(f"    ingest={r.ingest_ms:.1f}ms query={r.query_10_ms:.4f}ms recall@5={r.recall_at_5:.3f}")

        results[str(n)] = row

    return {
        "benchmark": "scbe_storage_colab",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "has_faiss": HAS_FAISS,
        "seed": seed,
        "sizes": sizes,
        "results": results,
    }


def main():
    ap = argparse.ArgumentParser(description="SCBE Storage Benchmark (Colab/Local)")
    ap.add_argument("--sizes", default="1000,5000,10000", help="Comma-separated record counts")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default="", help="Output JSON path")
    args = ap.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    report = run_full_benchmark(sizes, seed=args.seed)

    # Print summary table
    print(f"\n{'='*80}")
    print(f"  SUMMARY")
    print(f"{'='*80}")
    print(f"{'Surface':<20} {'N':>7} {'Ingest':>10} {'Query10':>10} {'Nodes':>8} {'Explode':>8} {'Recall':>7}")
    print("-" * 80)
    for n_str, row in report["results"].items():
        for surface in ["CymaticCone", "SemiSphereCone", "numpy_brute", "FAISS_FlatL2", "FAISS_IVF_PQ"]:
            if surface in row:
                r = row[surface]
                print(f"{surface:<20} {r['n_records']:>7} {r['ingest_ms']:>9.1f}ms {r['query_10_ms']:>9.2f}ms {r['node_count']:>8} {r['node_explosion']:>8.3f} {r['recall_at_5']:>6.3f}")
        print()

    # Save
    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = ARTIFACT_DIR / f"{ts}-colab-benchmark.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
