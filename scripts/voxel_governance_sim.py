#!/usr/bin/env python3
"""SCBE sparse voxel governance simulator.

Builds a sparse 3D voxel field where each occupied voxel stores:
- 21D state vector (deterministic from input text/hash)
- six-tongue spectral channels (phase + weight)
- SCBE governance metrics (coherence, d*, Layer 12 cost)
- quasicrystal projection/validation metadata

Canonical wall formula is preserved:
  H(d*,R) = R * pi^(phi * d*)

This tool is deterministic and inspectable by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from src.scbe_governance_math import (
    PHI,
    Point3,
    bft_consensus,
    coherence_from_phases,
    drift_star,
    encode_voxel_key,
    layer12_cost,
    local_vote,
    poincare_dist_3d,
    quantize,
)
from src.symphonic_cipher.scbe_aethermoore.qc_lattice.quasicrystal import (
    QuasicrystalLattice,
    ValidationStatus,
)

TONGUES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")
LWS_WEIGHTS: Dict[str, float] = {
    "KO": 1.0,
    "AV": 1.125,
    "RU": 1.25,
    "CA": 1.333,
    "UM": 1.5,
    "DR": 1.667,
}


@dataclass(frozen=True)
class VoxelRecord:
    voxel_id: str
    index_xyz: Tuple[int, int, int]
    world_xyz: Tuple[float, float, float]
    state21d: List[float]
    phases: Dict[str, float]
    weights: Dict[str, float]
    coherence: float
    d_star: float
    canonical_wall_cost: float
    layer12_cost: float
    local_votes: Dict[str, str]
    decision: str
    quasicrystal_status: str
    quasicrystal_valid: bool
    quasicrystal_distance: float
    quasicrystal_physical: List[float]
    quasicrystal_perpendicular: List[float]


def canonical_wall_cost(d_star_value: float, realm_scale: float = 1.0) -> float:
    """Canonical Layer 12 wall formula."""
    return realm_scale * (math.pi ** (PHI * d_star_value))


def _hash_bytes(seed: str) -> bytes:
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _u8_to_unit(b: int) -> float:
    return b / 255.0


def _unit_to_signed01(u: float) -> float:
    return (u * 2.0) - 1.0


def vector21_from_seed(seed: str) -> List[float]:
    """Deterministic 21D vector in [-0.9, 0.9]."""
    raw = _hash_bytes(seed) + _hash_bytes(seed + "::phi")
    vals = [_unit_to_signed01(_u8_to_unit(v)) * 0.9 for v in raw[:21]]
    return vals


def world_xyz_from_seed(seed: str, bound: float) -> Tuple[float, float, float]:
    raw = _hash_bytes(seed + "::xyz")
    xyz = []
    for i in range(3):
        u = _u8_to_unit(raw[i])
        xyz.append((-bound) + (2.0 * bound * u))
    return (xyz[0], xyz[1], xyz[2])


def phases_and_weights(state21d: List[float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    phase_vec = state21d[6:12]
    weight_vec = state21d[0:6]
    phases: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    for idx, tongue in enumerate(TONGUES):
        phase = max(-1.0, min(1.0, phase_vec[idx])) * math.pi
        # blend deterministic state weight with canonical LWS prior
        derived = abs(weight_vec[idx]) + 0.05
        weights[tongue] = round((0.5 * LWS_WEIGHTS[tongue]) + (0.5 * derived), 6)
        phases[tongue] = round(phase, 6)
    return phases, weights


def gate_vector_from_state(state21d: List[float]) -> List[int]:
    gates: List[int] = []
    for v in state21d[:6]:
        # [-0.9,0.9] -> [0,21]
        q = int(round(((v + 0.9) / 1.8) * 21))
        gates.append(max(0, min(21, q)))
    return gates


def classify_decision(base_decision: str, qc_valid: bool) -> str:
    if qc_valid:
        return base_decision
    if base_decision == "ALLOW":
        return "QUARANTINE"
    if base_decision == "QUARANTINE":
        return "DENY"
    return "DENY"


def build_voxel_record(
    seed: str,
    lattice: QuasicrystalLattice,
    world_bound: float,
    bins: int,
) -> VoxelRecord:
    state = vector21_from_seed(seed)
    wx, wy, wz = world_xyz_from_seed(seed, world_bound)
    phases, weights = phases_and_weights(state)

    p = Point3(wx, wy, wz)
    coherence = float(coherence_from_phases(phases))
    d_star_value = float(drift_star(p, weights))
    canonical_cost = float(canonical_wall_cost(d_star_value, 1.0))
    cost_l12 = float(layer12_cost(d_star_value, coherence))

    votes = {
        tongue: local_vote(tongue, cost_l12, coherence, phases, weights)
        for tongue in TONGUES
    }
    base_decision = bft_consensus(votes)

    gates = gate_vector_from_state(state)
    qc = lattice.validate_gates(gates)
    qc_valid = qc.status == ValidationStatus.VALID
    decision = classify_decision(base_decision, qc_valid)

    qx = quantize(wx, -world_bound, world_bound, bins)
    qy = quantize(wy, -world_bound, world_bound, bins)
    qz = quantize(wz, -world_bound, world_bound, bins)
    qv = quantize(coherence, -1.0, 1.0, bins)
    qp = quantize(d_star_value, 0.0, world_bound * 2.0, bins)
    qs = quantize(canonical_cost, 0.0, 200.0, bins)
    voxel_id = encode_voxel_key(
        {"X": qx, "Y": qy, "Z": qz, "V": qv, "P": qp, "S": qs},
        decision,  # decision appears in key envelope
    )

    return VoxelRecord(
        voxel_id=voxel_id,
        index_xyz=(qx, qy, qz),
        world_xyz=(round(wx, 6), round(wy, 6), round(wz, 6)),
        state21d=[round(v, 6) for v in state],
        phases=phases,
        weights={k: round(v, 6) for k, v in weights.items()},
        coherence=round(coherence, 6),
        d_star=round(d_star_value, 6),
        canonical_wall_cost=round(canonical_cost, 6),
        layer12_cost=round(cost_l12, 6),
        local_votes=votes,
        decision=decision,
        quasicrystal_status=qc.status.value,
        quasicrystal_valid=qc_valid,
        quasicrystal_distance=round(float(qc.lattice_point.distance_to_window), 6),
        quasicrystal_physical=[round(float(v), 6) for v in qc.lattice_point.r_physical.tolist()],
        quasicrystal_perpendicular=[round(float(v), 6) for v in qc.lattice_point.r_perpendicular.tolist()],
    )


def path_weight(a: VoxelRecord, b: VoxelRecord) -> float:
    pa = Point3(*a.world_xyz)
    pb = Point3(*b.world_xyz)
    base = poincare_dist_3d(pa, pb)
    penalty = 0.0
    if b.decision == "QUARANTINE":
        penalty += 0.6
    elif b.decision == "DENY":
        penalty += 1.2
    return base + penalty + 1e-6


def shortest_path(voxels: List[VoxelRecord]) -> Dict[str, Any]:
    if len(voxels) < 2:
        return {"node_ids": [], "total_cost": 0.0}

    import heapq

    start = 0
    target = len(voxels) - 1
    dist = {i: float("inf") for i in range(len(voxels))}
    prev: Dict[int, int] = {}
    dist[start] = 0.0
    heap = [(0.0, start)]

    while heap:
        cur_d, u = heapq.heappop(heap)
        if u == target:
            break
        if cur_d > dist[u]:
            continue
        for v in range(len(voxels)):
            if v == u:
                continue
            w = path_weight(voxels[u], voxels[v])
            nd = cur_d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    if dist[target] == float("inf"):
        return {"node_ids": [], "total_cost": float("inf")}

    path_idx = [target]
    cur = target
    while cur in prev:
        cur = prev[cur]
        path_idx.append(cur)
    path_idx.reverse()
    return {
        "node_ids": [voxels[i].voxel_id for i in path_idx],
        "total_cost": round(dist[target], 6),
    }


def make_seed_inputs(input_json: Path | None, count: int) -> List[str]:
    if input_json is None:
        return [f"seed-{i:03d}" for i in range(1, count + 1)]
    obj = json.loads(input_json.read_text(encoding="utf-8"))
    if isinstance(obj, dict) and isinstance(obj.get("items"), list):
        vals = [str(item) for item in obj["items"]]
        return vals[:count] if count > 0 else vals
    raise ValueError("Input JSON must be an object with items: []")


def summarize(voxels: List[VoxelRecord], route: Dict[str, Any]) -> Dict[str, Any]:
    if not voxels:
        return {
            "state_vector": {"coherence": 0.0, "energy": 0.0, "drift": 0.0},
            "decision_record": {
                "action": "DENY",
                "signature": "none",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "empty voxel set",
                "confidence": 0.0,
            },
        }
    coherence = sum(v.coherence for v in voxels) / len(voxels)
    energy = sum(v.canonical_wall_cost for v in voxels) / len(voxels)
    drift = sum(v.d_star for v in voxels) / len(voxels)
    deny_ratio = sum(1 for v in voxels if v.decision == "DENY") / len(voxels)
    quarantine_ratio = sum(1 for v in voxels if v.decision == "QUARANTINE") / len(voxels)

    if deny_ratio >= 0.25:
        action = "DENY"
        reason = "high deny ratio in voxel field"
    elif quarantine_ratio >= 0.35:
        action = "QUARANTINE"
        reason = "elevated quarantine ratio in voxel field"
    else:
        action = "ALLOW"
        reason = "voxel field within trust envelope"

    state_vector = {
        "coherence": round(coherence, 6),
        "energy": round(energy, 6),
        "drift": round(drift, 6),
    }
    trace_obj = {
        "state_vector": state_vector,
        "route_total_cost": route.get("total_cost"),
        "node_count": len(voxels),
        "action": action,
    }
    signature = hashlib.sha256(
        json.dumps(trace_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    decision_record = {
        "action": action,
        "signature": signature,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "confidence": round(max(0.0, 1.0 - deny_ratio), 6),
    }
    return {"state_vector": state_vector, "decision_record": decision_record}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sparse voxel simulator for SCBE governance routing.")
    p.add_argument("--input-json", type=Path, default=None, help="JSON file with {\"items\": [...]} seeds.")
    p.add_argument("--count", type=int, default=12, help="How many voxels to generate.")
    p.add_argument("--world-bound", type=float, default=2.5, help="Coordinate bound for world xyz.")
    p.add_argument("--bins", type=int, default=36, help="Quantization bins for voxel addressing.")
    p.add_argument("--output", type=Path, default=Path("artifacts/voxel_governance_run.json"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    seeds = make_seed_inputs(args.input_json, args.count)
    lattice = QuasicrystalLattice()
    voxels = [build_voxel_record(seed, lattice, args.world_bound, args.bins) for seed in seeds]
    route = shortest_path(voxels)
    dual = summarize(voxels, route)

    payload = {
        "run_id": datetime.now(timezone.utc).strftime("voxel_%Y%m%dT%H%M%SZ"),
        "formula_layer12_canonical": "H(d*,R) = R * pi^(phi * d*)",
        "state_vector": dual["state_vector"],
        "decision_record": dual["decision_record"],
        "route": route,
        "voxel_count": len(voxels),
        "voxels": [asdict(v) for v in voxels],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(json.dumps({"state_vector": payload["state_vector"], "decision_record": payload["decision_record"]}, indent=2))


if __name__ == "__main__":
    main()

