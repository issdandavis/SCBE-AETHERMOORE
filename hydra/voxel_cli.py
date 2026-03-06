"""HYDRA voxel6d CLI — 6D Voxel Storage query and demo interface.

Usage:
    python -m hydra.voxel_cli demo
    python -m hydra.voxel_cli store --x 0.3 --y 0.5 --wl 540 --tongue RU --authority agent.claude --intent "0.8,0.1,0.1"
    python -m hydra.voxel_cli query-intent --intent "0.9,0.1,0.0" --top-k 3
    python -m hydra.voxel_cli layout --flows 8 --mode default --json
    python -m hydra.voxel_cli lattice25d --bundles 12 --cell-size 0.4 --json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time

import numpy as np

from hydra.voxel_storage import VoxelGrid, Voxel, chladni_amplitude, generate_chladni_grid
from hydra.color_dimension import TONGUE_WAVELENGTHS, TONGUE_WEIGHTS, ColorBand
from hydra.octree_sphere_grid import HyperbolicLattice25D


def _build_layout(flow_count: int = 8, mode: str = "default", at_unix_ms: float | None = None, window_ms: float = 60000) -> dict:
    """Build a layout result compatible with the TypeScript spectralGraph output."""
    grid = VoxelGrid(resolution=16, chladni_mode=(3, 2))

    tongues = list(TONGUE_WEIGHTS.keys())
    intent_presets = {
        "observe": [0.1, 0.1, 0.8],
        "route": [0.5, 0.5, 0.0],
        "govern": [0.9, 0.0, 0.1],
        "archive": [0.0, 0.2, 0.8],
        "publish": [0.3, 0.7, 0.0],
        "contain": [0.8, 0.1, 0.1],
        "research": [0.0, 0.1, 0.9],
    }
    intent_tags = list(intent_presets.keys())
    authority_levels = ["public", "internal", "restricted", "sealed"]

    bands = [400, 455, 500, 540, 580, 617, 700]

    flows = []
    for i in range(flow_count):
        wl = bands[i % len(bands)] + ((i * 13) % 17) - 8
        wl = max(380, min(780, wl))
        tongue = tongues[i % len(tongues)]
        intent_tag = intent_tags[i % len(intent_tags)]
        authority = authority_levels[i % len(authority_levels)]
        intent_vec = intent_presets[intent_tag]

        x = 0.1 + (i * 0.12) % 0.8
        y = 0.15 + (i * 0.17) % 0.7

        v = grid.store(
            x=x, y=y, z=float(i % 4) * 0.1,
            wavelength_nm=float(wl),
            tongue=tongue,
            authority=f"agent.{authority}",
            intent_vector=intent_vec,
            intent_label=intent_tag,
            payload={"flow_id": f"flow_{i+1}", "mode": mode},
            voxel_id=f"flow_{i+1}_voxel",
        )

        flows.append({
            "id": f"flow_{i+1}",
            "sequence": i,
            "wavelengthNm": wl,
            "authority": authority,
            "intentTag": intent_tag,
            "intentVector": list(v.intent_vector[:3]),
            "tongue": tongue,
            "chladniAddress": v.chladni_address,
        })

    now_ms = at_unix_ms or (time.time() * 1000)
    half = window_ms / 2

    voxels_out = []
    for v in grid.voxels.values():
        voxels_out.append({
            "id": v.voxel_id,
            "x": v.x, "y": v.y, "z": v.z,
            "wavelengthNm": v.wavelength_nm,
            "authority": v.authority_agent.replace("agent.", ""),
            "authorityHash": v.authority_hash,
            "intentTag": v.intent_label,
            "intentVector": list(v.intent_vector[:3]),
            "modeN": grid.chladni_n,
            "modeM": grid.chladni_m,
            "chladniValue": v.chladni_address,
            "createdAtUnixMs": v.created_at * 1000,
            "updatedAtUnixMs": v.updated_at * 1000,
        })

    auth_dist = {}
    intent_dist = {}
    for v in grid.voxels.values():
        auth = v.authority_agent.replace("agent.", "")
        auth_dist[auth] = auth_dist.get(auth, 0) + 1
        intent_dist[v.intent_label] = intent_dist.get(v.intent_label, 0) + 1

    stats = grid.stats()

    return {
        "mode": mode,
        "dimensions": {
            "explicit": ["x", "y", "z", "spectral", "authority", "intent"],
            "implied": ["timestamp"],
        },
        "flows": flows,
        "voxels": voxels_out,
        "temporal": {
            "atUnixMs": now_ms,
            "windowMs": window_ms,
            "activeVoxelCount": len(voxels_out),
            "authorityDistribution": auth_dist,
            "intentDistribution": intent_dist,
        },
        "metrics": {
            "voxelCount": stats["count"],
            "uniqueAgents": stats.get("unique_agents", 0),
            "wavelengthRange": list(stats.get("wavelength_range", (0, 0))),
            "chladniMode": list(stats.get("chladni_mode", (3, 2))),
            "chladniMean": stats.get("chladni_mean", 0),
            "temporalEvents": stats.get("temporal_events", 0),
        },
    }


def cmd_demo(_args):
    from hydra.voxel_storage import _demo
    _demo()


def cmd_layout(args):
    result = _build_layout(
        flow_count=args.flows,
        mode=args.mode,
        at_unix_ms=args.at_unix_ms,
        window_ms=args.window_ms,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Mode: {result['mode']}")
        print(f"Flows: {len(result['flows'])}")
        print(f"Voxels: {len(result['voxels'])}")
        print(f"Dimensions: {result['dimensions']}")
        print(f"Metrics: {json.dumps(result['metrics'], indent=2)}")
        print(f"Temporal: {json.dumps(result['temporal'], indent=2, default=str)}")


def cmd_store(args):
    grid = VoxelGrid(resolution=16)
    intent = [float(x) for x in args.intent.split(",")]
    v = grid.store(
        x=args.x, y=args.y, z=args.z,
        wavelength_nm=args.wl,
        tongue=args.tongue,
        authority=args.authority,
        intent_vector=intent,
        intent_label=args.label or "",
    )
    print(json.dumps({
        "voxel_id": v.voxel_id,
        "position": [v.x, v.y, v.z],
        "wavelength_nm": v.wavelength_nm,
        "tongue": v.tongue,
        "authority": v.authority_agent,
        "authority_hash": v.authority_hash,
        "intent_vector": list(v.intent_vector),
        "chladni_address": v.chladni_address,
        "created_at": v.created_at,
    }, indent=2, default=str))


def cmd_chladni(args):
    pattern = generate_chladni_grid(args.resolution, args.mode_n, args.mode_m)
    if args.json:
        print(json.dumps(pattern.tolist()))
    else:
        for row in range(0, args.resolution, max(1, args.resolution // 16)):
            line = ""
            for col in range(args.resolution):
                val = pattern[row, col]
                if abs(val) < 0.3:
                    line += "."
                elif val > 0:
                    line += "#"
                else:
                    line += "o"
            print(f"  {line}")


def cmd_lattice25d(args):
    lat = HyperbolicLattice25D(
        cell_size=args.cell_size,
        max_depth=args.max_depth,
        phase_weight=args.phase_weight,
    )

    tongues = list(TONGUE_WEIGHTS.keys())
    presets = [
        ("govern", [0.9, 0.0, 0.1]),
        ("research", [0.0, 0.1, 0.9]),
        ("route", [0.5, 0.5, 0.0]),
        ("contain", [0.8, 0.1, 0.1]),
    ]

    for i in range(args.bundles):
        # Intentionally force partial overlap by reusing coarse lattice points
        x = math.cos(i * 0.73) * args.radius + (0.06 if i % 3 == 0 else 0.0)
        y = math.sin(i * 0.91) * args.radius + (0.06 if i % 4 == 0 else 0.0)
        phase = (i * args.phase_step) % (2 * math.pi)
        label, vec = presets[i % len(presets)]
        tongue = tongues[i % len(tongues)]
        lat.insert_bundle(
            x=x,
            y=y,
            phase_rad=phase,
            tongue=tongue,
            authority=["public", "internal", "sealed"][i % 3],
            intent_vector=vec,
            intent_label=f"{label}_{i}",
            payload={"flow_index": i},
            wavelength_nm=float(TONGUE_WAVELENGTHS.get(tongue, 550.0)),
        )

    q = lat.query_nearest(
        x=args.query_x,
        y=args.query_y,
        phase_rad=args.query_phase,
        intent_vector=[0.9, 0.0, 0.1],
        tongue="DR",
        top_k=min(5, args.bundles),
    )

    result = {
        "stats": lat.stats(),
        "overlap_cells": [
            {"cell": list(cell), "count": len(items)}
            for cell, items in lat.overlapping_cells().items()
        ],
        "lace_edge_count": len(lat.lace_edges()),
        "nearest": [
            {
                "bundle_id": b.bundle_id,
                "label": b.intent_label,
                "tongue": b.tongue,
                "phase_rad": b.phase_rad,
                "distance": dist,
            }
            for b, dist in q
        ],
    }

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        s = result["stats"]
        print("2.5D Hyperbolic Lattice")
        print(f"  bundles: {s['bundle_count']}")
        print(f"  occupied cells: {s['occupied_cells']}")
        print(f"  overlap cells: {s['overlap_cells']} (max overlap: {s['max_overlap']})")
        print(f"  lace edges: {result['lace_edge_count']}")
        print(f"  semantic weight avg: {s['semantic_weight_avg']:.3f}")
        print("  nearest:")
        for n in result["nearest"]:
            print(
                f"    - {n['label']:14s} tongue={n['tongue']:2s} "
                f"phase={n['phase_rad']:.3f} d={n['distance']:.4f}"
            )


def main():
    parser = argparse.ArgumentParser(prog="hydra-voxel6d", description="6D Voxel Storage CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("demo", help="Run interactive demo")

    p_layout = sub.add_parser("layout", help="Generate voxel layout")
    p_layout.add_argument("--flows", type=int, default=8)
    p_layout.add_argument("--mode", choices=["default", "quasi", "dense"], default="default")
    p_layout.add_argument("--at-unix-ms", type=float, default=None)
    p_layout.add_argument("--window-ms", type=float, default=60000)
    p_layout.add_argument("--json", action="store_true")

    p_store = sub.add_parser("store", help="Store a single voxel")
    p_store.add_argument("--x", type=float, default=0.5)
    p_store.add_argument("--y", type=float, default=0.5)
    p_store.add_argument("--z", type=float, default=0.0)
    p_store.add_argument("--wl", type=float, default=550.0)
    p_store.add_argument("--tongue", default="KO")
    p_store.add_argument("--authority", default="agent.claude")
    p_store.add_argument("--intent", default="0.5,0.5,0.0")
    p_store.add_argument("--label", default="")

    p_chladni = sub.add_parser("chladni", help="Show Chladni pattern")
    p_chladni.add_argument("--resolution", type=int, default=16)
    p_chladni.add_argument("--mode-n", type=int, default=3)
    p_chladni.add_argument("--mode-m", type=int, default=2)
    p_chladni.add_argument("--json", action="store_true")

    p_lattice = sub.add_parser("lattice25d", help="2.5D cyclic lattice + hyperbolic octree projection")
    p_lattice.add_argument("--bundles", type=int, default=12)
    p_lattice.add_argument("--cell-size", type=float, default=0.4)
    p_lattice.add_argument("--max-depth", type=int, default=6)
    p_lattice.add_argument("--phase-weight", type=float, default=0.35)
    p_lattice.add_argument("--phase-step", type=float, default=0.7)
    p_lattice.add_argument("--radius", type=float, default=0.7)
    p_lattice.add_argument("--query-x", type=float, default=0.1)
    p_lattice.add_argument("--query-y", type=float, default=0.1)
    p_lattice.add_argument("--query-phase", type=float, default=0.0)
    p_lattice.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "demo":
        cmd_demo(args)
    elif args.command == "layout":
        cmd_layout(args)
    elif args.command == "store":
        cmd_store(args)
    elif args.command == "chladni":
        cmd_chladni(args)
    elif args.command == "lattice25d":
        cmd_lattice25d(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
