"""Quasi-vector field analysis — production-safe interpretation.

Salvage note (2026-05-22): spin voxel = **vector-field coherence probe**,
NOT magnetic material / spintronic security / quantum-resistance.

Metrics (from src/storage/spin_voxel.py):
  C_field  = ||sum v_i|| / (sum ||v_i|| + eps)     # alignment (1=parallel, 0=cancel)
  D_field  = mean_edges (1 - hat{v}_i · hat{v}_j)  # boundary / local disagreement
  phason   = phi-step z-rotation (invariance probe; norms preserved)

Plus:
  polar vs axial check on ROGII path: tangent is polar; optional "curl-like"
  residual from neighbor mismatch flags quasi/axial boundary energy.

Usage:
  python scripts/analysis/quasi_vector_analysis.py
  python scripts/analysis/quasi_vector_analysis.py --rogii C:\\dev\\rogii\\fulldata\\extracted\\train
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from storage.spin_voxel import (  # noqa: E402
    SpinVoxelConfig,
    apply_phason,
    harmonic_scaling_spin_voxel,
    spin_coherence,
    spin_disorder,
    spin_hamiltonian,
)


def _rand_unit(rng: random.Random) -> tuple[float, float, float]:
    x, y, z = rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x / n, y / n, z / n)


def synthetic_suite(n: int = 64, seed: int = 0) -> dict:
    rng = random.Random(seed)
    axis = (0.0, 0.0, 1.0)
    aligned = [axis for _ in range(n)]
    disordered = [_rand_unit(rng) for _ in range(n)]
    # domain wall: two halves anti-aligned → high boundary energy
    wall = [axis if i < n // 2 else (-axis[0], -axis[1], -axis[2]) for i in range(n)]
    # quasi-periodic: rotate each step by phi angle (phason walk)
    phi = (1 + math.sqrt(5)) / 2
    theta = 2 * math.pi / phi
    c, s = math.cos(theta), math.sin(theta)
    qv = []
    v = (1.0, 0.0, 0.0)
    for _ in range(n):
        qv.append(v)
        v = (c * v[0] - s * v[1], s * v[0] + c * v[1], v[2])

    def pack(name, spins):
        ph = apply_phason(spins, n=1)
        return {
            "name": name,
            "n": len(spins),
            "C_field": round(spin_coherence(spins), 6),
            "D_field": round(spin_disorder(spins), 6),
            "H_spin": round(spin_hamiltonian(spins), 6),
            "H_mod_fast": round(
                harmonic_scaling_spin_voxel(
                    d=2.0, r=1.2, intent_norm=1.0, spins=spins, phase="fast"
                ),
                4,
            ),
            "phason_norm_drift": round(
                max(
                    abs(math.sqrt(sum(a * a for a in u)) - math.sqrt(sum(b * b for b in v)))
                    for u, v in zip(spins, ph)
                ),
                12,
            ),
        }

    return {
        "aligned": pack("aligned", aligned),
        "disordered": pack("disordered", disordered),
        "domain_wall": pack("domain_wall", wall),
        "phi_walk_quasi": pack("phi_walk_quasi", qv),
    }


def path_tangents(xyz: np.ndarray) -> list[tuple[float, float, float]]:
    """Polar direction field along a well path (quasi-vector analysis input)."""
    d = np.diff(xyz, axis=0)
    out = []
    for row in d:
        n = float(np.linalg.norm(row))
        if n < 1e-12:
            out.append((0.0, 0.0, 0.0))
        else:
            out.append((float(row[0] / n), float(row[1] / n), float(row[2] / n)))
    return out


def analyze_field(spins: list[tuple[float, float, float]], label: str = "field") -> dict:
    if len(spins) < 2:
        return {"label": label, "error": "need >=2 vectors"}
    # sliding window coherence (local quasi-periodicity probe)
    win = min(32, len(spins))
    local_c = []
    for i in range(0, len(spins) - win + 1, max(1, win // 2)):
        local_c.append(spin_coherence(spins[i : i + win]))
    return {
        "label": label,
        "n": len(spins),
        "C_field": round(spin_coherence(spins), 6),
        "D_field": round(spin_disorder(spins), 6),
        "H_spin": round(spin_hamiltonian(spins), 6),
        "local_C_mean": round(float(np.mean(local_c)), 6) if local_c else None,
        "local_C_std": round(float(np.std(local_c)), 6) if local_c else None,
        "local_C_min": round(float(np.min(local_c)), 6) if local_c else None,
        "interpretation": (
            "aligned / smooth path"
            if spin_coherence(spins) > 0.85
            else (
                "mixed / curved"
                if spin_coherence(spins) > 0.4
                else "disordered / high curvature or reversal"
            )
        ),
    }


def rogii_analysis(train_dir: Path, max_wells: int = 12) -> list[dict]:
    wells = sorted({p.name.split("__")[0] for p in train_dir.glob("*__horizontal_well.csv")})
    rows = []
    for wid in wells[:max_wells]:
        h = __import__("pandas").read_csv(train_dir / f"{wid}__horizontal_well.csv")
        xyz = h[["X", "Y", "Z"]].to_numpy(float)
        known = h["TVT_input"].notna().to_numpy() if "TVT_input" in h.columns else np.ones(len(h), bool)
        # full path + lateral-only
        full = path_tangents(xyz)
        lat_xyz = xyz[~known] if (~known).sum() > 5 else xyz
        lat = path_tangents(lat_xyz)
        a_full = analyze_field(full, f"{wid}/full")
        a_lat = analyze_field(lat, f"{wid}/lateral")
        rows.append(
            {
                "well": wid,
                "full": a_full,
                "lateral": a_lat,
                "C_drop_to_lateral": round(a_full["C_field"] - a_lat["C_field"], 6),
                "D_rise_to_lateral": round(a_lat["D_field"] - a_full["D_field"], 6),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Quasi-vector field coherence analysis")
    ap.add_argument(
        "--rogii",
        type=Path,
        default=None,
        help="Optional path to ROGII train dir for wellbore tangent analysis",
    )
    ap.add_argument("--out", type=Path, default=None, help="JSON report path")
    args = ap.parse_args()

    report = {
        "schema": "quasi_vector_analysis_v1",
        "claim_boundary": (
            "spin voxel = vector-field coherence probe; "
            "NOT spintronic crypto / quantum resistance"
        ),
        "synthetic": synthetic_suite(),
        "rogii": None,
    }

    print("=== QUASI-VECTOR ANALYSIS (salvage-honest) ===\n")
    print("C_field → alignment | D_field → boundary energy | phason → norm-preserving rotate\n")
    print("Synthetic fields:")
    for k, v in report["synthetic"].items():
        print(
            f"  {v['name']:16s}  C={v['C_field']:.4f}  D={v['D_field']:.4f}  "
            f"H={v['H_spin']:.3f}  H_mod={v['H_mod_fast']:.1f}  "
            f"phason_drift={v['phason_norm_drift']}"
        )

    # expected inequalities (honest self-check)
    s = report["synthetic"]
    ok = (
        s["aligned"]["C_field"] > 0.99
        and s["disordered"]["C_field"] < 0.3
        and s["domain_wall"]["D_field"] > s["aligned"]["D_field"]
        and s["aligned"]["phason_norm_drift"] == 0.0
    )
    print(f"\n  self-check inequalities: {'PASS' if ok else 'FAIL'}")

    default_rogii = Path(r"C:\dev\rogii\fulldata\extracted\train")
    rogii_path = args.rogii or (default_rogii if default_rogii.is_dir() else None)
    if rogii_path and rogii_path.is_dir():
        print(f"\nROGII wellbore tangent fields ({rogii_path}):")
        rows = rogii_analysis(rogii_path, max_wells=10)
        report["rogii"] = rows
        for r in rows:
            print(
                f"  {r['well']}: full C={r['full']['C_field']:.4f} D={r['full']['D_field']:.4f} | "
                f"lat C={r['lateral']['C_field']:.4f} D={r['lateral']['D_field']:.4f} | "
                f"ΔC={r['C_drop_to_lateral']:+.4f} ΔD={r['D_rise_to_lateral']:+.4f}  "
                f"[{r['lateral']['interpretation']}]"
            )
        # summary
        c_full = np.mean([r["full"]["C_field"] for r in rows])
        c_lat = np.mean([r["lateral"]["C_field"] for r in rows])
        print(f"\n  mean C_field full={c_full:.4f} lateral={c_lat:.4f}")
        print(
            "  read: high lateral C = smooth azimuth hold (good for const TVT prior); "
            "low C / high D = doglegs & turn rate → residual transfer harder"
        )

    out = args.out or (ROOT / "artifacts" / "quasi_vector_analysis_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport → {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
