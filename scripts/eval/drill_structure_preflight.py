from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval.drill_map_eval import load_drill_rows, summarize_structural_rows, verifier_for_row

EXPECTED_MAPS = {
    "transport_atomic",
    "atomic_semantic",
    "convergence_action",
    "cartography_state",
    "cross_braid_code",
    "runtime_emission",
    "spirit_narrative",
    "paradigm_isomorphism",
    "opcode_runtime",
    "qa_invariance",
}

FIELD_RE = re.compile(r"([a-zA-Z_]+)=([^\s]+)")
PYTHAGOREAN_COMMA = 531441 / 524288
ALIGNMENT_GEARS = {"seed", "couple", "transfer", "stabilize", "braid", "witness"}

QA_SIGNATURES = {
    "hyperbolic_distance": "d_H(u,v) = arcosh(1 + 2*||u-v||^2/((1-||u||^2)(1-||v||^2)))",
    "harmonic_wall": "H(d, pd) = 1/(1 + d + 2*pd)",
    "comma_drift": "decimal_drift = (531441/524288)^n",
    "phi_ladder": "phi^n where phi = (1 + sqrt(5))/2",
    "phase_delta": "phase_delta = (PHASE[witness] - PHASE[anchor]) mod 2*pi",
}
NUMERIC_RE = re.compile(r"-?\d+\.?\d*")


def _field_map(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in FIELD_RE.finditer(text)}


def _validate_transport(row: dict) -> list[str]:
    fields = _field_map(row["text"])
    errors: list[str] = []
    if "sha" not in fields:
        errors.append("missing sha")
    elif len(fields["sha"]) < 8:
        errors.append("sha too short")
    if "tokens" not in fields:
        errors.append("missing tokens")
    return errors


def _validate_chemistry_capsule(row: dict) -> list[str]:
    text = row.get("text", "")
    errors: list[str] = []
    for needle in (
        "equation:",
        "stability:",
        "class:",
        "mol_intent:",
        "obs_intent:",
        "path_6d:",
        "t_axis:",
        "atoms_conserved:",
        "surface:",
    ):
        if needle not in text:
            errors.append(f"missing {needle[:-1]}")
    mol_match = re.search(
        r"mol_intent:\s*donor=([0-9.]+)\s+acceptor=([0-9.]+)\s+strain=([0-9.]+)\s+delta=([0-9.]+)",
        text,
    )
    if not mol_match:
        errors.append("mol_intent malformed")
    else:
        for value in mol_match.groups():
            numeric = float(value)
            if not 0.0 <= numeric <= 1.0:
                errors.append("mol_intent value out of range")
                break
    obs_match = re.search(r"obs_intent:\s*lens=([a-z_]+)\s+focus=([a-z_]+)\s+gear=([a-z_]+)", text)
    if not obs_match:
        errors.append("obs_intent malformed")
    path_match = re.search(r"path_6d:\s*\[([^\]]+)\]", text)
    if not path_match:
        errors.append("path_6d malformed")
    else:
        try:
            values = [float(chunk.strip()) for chunk in path_match.group(1).split(",")]
            if len(values) != 6:
                errors.append("path_6d must have 6 values")
            elif any(not 0.0 <= value <= 1.0 for value in values):
                errors.append("path_6d value out of range")
        except Exception:
            errors.append("path_6d not numeric")
    t_axis_match = re.search(r"t_axis:\s*([0-9.]+)", text)
    if not t_axis_match:
        errors.append("t_axis malformed")
    else:
        t_axis = float(t_axis_match.group(1))
        if not 0.0 <= t_axis <= 1.0:
            errors.append("t_axis out of range")
    return errors


def _validate_atomic(row: dict) -> list[str]:
    text = row["text"]
    errors: list[str] = []
    for needle in ("class=", "element=", "tau=", "res=", "adapt=", "trust="):
        if needle not in text:
            errors.append(f"missing {needle[:-1]}")
    return errors


def _validate_convergence(row: dict) -> list[str]:
    text = row["text"]
    errors: list[str] = []
    for needle in ("voice=", "motif=", "cadence=", "phase_deltas=", "harmonic=", "transport=", "atomic="):
        if needle not in text:
            errors.append(f"missing {needle[:-1]}")
    fields = _field_map(text)
    harmonic = fields.get("harmonic")
    if harmonic is None:
        errors.append("missing harmonic numeric field")
    else:
        try:
            if not math.isfinite(float(harmonic)):
                errors.append("harmonic not finite")
        except ValueError:
            errors.append("harmonic not numeric")
    return errors


def _validate_cartography(row: dict) -> list[str]:
    fields = _field_map(row["text"])
    errors: list[str] = []
    for name in ("region", "anchor", "witness", "boundary_distance", "trajectory", "phase_delta", "weight_ratio"):
        if name not in fields:
            errors.append(f"missing {name}")
    try:
        boundary_distance = float(fields["boundary_distance"])
        if not 0.0 <= boundary_distance <= 0.5:
            errors.append("boundary_distance out of range")
    except Exception:
        errors.append("boundary_distance not numeric")
    try:
        phase_delta = float(fields["phase_delta"])
        if not 0.0 <= phase_delta < 2 * math.pi + 1e-6:
            errors.append("phase_delta out of range")
    except Exception:
        errors.append("phase_delta not numeric")
        phase_delta = None
    try:
        weight_ratio = float(fields["weight_ratio"])
        if weight_ratio <= 0:
            errors.append("weight_ratio not positive")
    except Exception:
        errors.append("weight_ratio not numeric")
    trajectory = fields.get("trajectory")
    if trajectory not in {"inbound", "outbound"}:
        errors.append("trajectory invalid")
    elif phase_delta is not None:
        expected = "inbound" if phase_delta <= math.pi + 1e-3 else "outbound"
        if trajectory != expected:
            errors.append("trajectory does not match phase_delta")
    return errors


def _validate_cartography_route(row: dict) -> list[str]:
    text = row["text"]
    fields = _field_map(text)
    errors: list[str] = []
    if "witness" not in text.lower():
        errors.append("missing witness reference")
    for name in ("corridor", "gear", "invariant_null_axes", "wormhole_axes", "free_axes", "slope"):
        if name not in fields:
            errors.append(f"missing {name}")
    try:
        phase_delta = float(fields["phase_delta"])
        if not 0.0 <= phase_delta < 2 * math.pi + 1e-6:
            errors.append("phase_delta out of range")
    except Exception:
        errors.append("phase_delta not numeric")
    try:
        weight_ratio = float(fields["weight_ratio"])
        if weight_ratio <= 0:
            errors.append("weight_ratio not positive")
    except Exception:
        errors.append("weight_ratio not numeric")
    try:
        slope = float(fields["slope"])
        if slope < 0:
            errors.append("slope negative")
    except Exception:
        errors.append("slope not numeric")
    if fields.get("corridor") not in {"wormhole", "surface"}:
        errors.append("corridor invalid")
    if fields.get("gear") not in {"idle", "couple", "transfer", "stabilize"}:
        errors.append("gear invalid")
    invariant = fields.get("invariant_null_axes", "none")
    wormhole = fields.get("wormhole_axes", "none")
    free = fields.get("free_axes", "none")
    axis_sets = []
    for label, value in (("invariant_null_axes", invariant), ("wormhole_axes", wormhole), ("free_axes", free)):
        if value == "none":
            axis_sets.append((label, set()))
            continue
        axis_set = set(value.split("/"))
        axis_sets.append((label, axis_set))
    axis_union = set()
    for _, axis_set in axis_sets:
        if axis_union & axis_set:
            errors.append("null-space axes overlap")
            break
        axis_union |= axis_set
    return errors


def _validate_convergence_anchor(row: dict) -> list[str]:
    text = row["text"]
    errors: list[str] = []
    for needle in ("voice=", "motif=", "cadence=", "runtime=", "spirit="):
        if needle not in text:
            errors.append(f"missing {needle[:-1]}")
    return errors


def _validate_cross_braid(row: dict) -> list[str]:
    kind = row.get("kind", "")
    text = row["text"]
    errors: list[str] = []
    if kind == "pair":
        if "phase_delta=" not in text:
            errors.append("missing phase_delta")
        if "weight_ratio=" not in text:
            errors.append("missing weight_ratio")
    else:
        if not text.strip():
            errors.append("empty code surface")
    return errors


def _validate_lane_alignment(row: dict) -> list[str]:
    fields = _field_map(row["text"])
    errors: list[str] = []
    required = {
        "tongue",
        "binary_lane",
        "comma_step",
        "decimal_drift",
        "gear",
        "lane_value",
        "family",
        "anchor_runtime",
        "anchor_spirit",
        "opcode_anchor",
        "surface",
    }
    for name in sorted(required):
        if name not in fields:
            errors.append(f"missing {name}")

    binary_lane = fields.get("binary_lane")
    if binary_lane is not None and not re.fullmatch(r"[01]{3}", binary_lane):
        errors.append("binary_lane invalid")

    comma_step: int | None = None
    if "comma_step" in fields:
        try:
            comma_step = int(fields["comma_step"])
            if comma_step < 0:
                errors.append("comma_step negative")
        except Exception:
            errors.append("comma_step not integer")

    if "decimal_drift" in fields:
        try:
            decimal_drift = float(fields["decimal_drift"])
            if decimal_drift <= 0:
                errors.append("decimal_drift not positive")
            elif comma_step is not None:
                expected = PYTHAGOREAN_COMMA**comma_step
                if not math.isclose(decimal_drift, expected, rel_tol=1e-6, abs_tol=1e-9):
                    errors.append("decimal_drift does not match comma_step")
        except Exception:
            errors.append("decimal_drift not numeric")

    if fields.get("gear") not in ALIGNMENT_GEARS:
        errors.append("gear invalid")
    family = fields.get("family", "")
    if not family or not re.fullmatch(r"[a-z_]+", family):
        errors.append("family invalid")
    if fields.get("lane_value", "").strip() == "":
        errors.append("lane_value empty")
    if fields.get("surface", "").strip() == "":
        errors.append("surface empty")
    if fields.get("anchor_runtime", "").strip() == "":
        errors.append("anchor_runtime empty")
    if fields.get("anchor_spirit", "").strip() == "":
        errors.append("anchor_spirit empty")

    return errors


def _validate_qa_invariance(row: dict) -> list[str]:
    text = row.get("text", "")
    kind = row.get("kind", "")
    errors: list[str] = []
    if "Q:" not in text:
        errors.append("missing Q: marker")
    if "A:" not in text:
        errors.append("missing A: marker")
    signature = QA_SIGNATURES.get(kind)
    if signature is None:
        errors.append("unknown qa_invariance kind")
    elif signature not in text:
        errors.append("canonical signature missing from answer")
    _, _, answer = text.partition("A:")
    numerics = NUMERIC_RE.findall(answer)
    if len(numerics) < 2:
        errors.append("answer has fewer than 2 numeric values")
    return errors


def validate_row(row: dict) -> list[str]:
    verifier = verifier_for_row(row)
    if verifier == "ss2_transport_fields":
        return _validate_transport(row)
    if verifier == "chemistry_capsule_fields":
        return _validate_chemistry_capsule(row)
    if verifier == "atomic_state_fields":
        return _validate_atomic(row)
    if verifier == "convergence_packet_fields":
        return _validate_convergence(row)
    if verifier == "cartography_packet_fields":
        return _validate_cartography(row)
    if verifier == "cartography_route_fields":
        return _validate_cartography_route(row)
    if verifier == "convergence_anchor_fields":
        return _validate_convergence_anchor(row)
    if verifier == "cross_braid_surface":
        return _validate_cross_braid(row)
    if verifier == "lane_alignment_fields":
        return _validate_lane_alignment(row)
    if verifier == "qa_invariance_fields":
        return _validate_qa_invariance(row)
    return []


def validate_rows(rows: Iterable[dict]) -> dict:
    counts_by_map = Counter()
    counts_by_map_kind = Counter()
    tongues_by_map = defaultdict(set)
    failures: list[dict[str, str]] = []

    for row in rows:
        map_name = row.get("map", "unknown")
        kind = row.get("kind", "unknown")
        counts_by_map[map_name] += 1
        counts_by_map_kind[f"{map_name}:{kind}"] += 1
        tongue = row.get("tongue")
        if tongue:
            tongues_by_map[map_name].add(tongue)

        errors = validate_row(row)

        if errors:
            failures.append(
                {
                    "map": map_name,
                    "kind": kind,
                    "tongue": row.get("tongue", ""),
                    "errors": ", ".join(errors),
                    "text_preview": row.get("text", "")[:160],
                }
            )

    structural = summarize_structural_rows(rows)
    missing_maps = sorted(EXPECTED_MAPS - set(counts_by_map))

    return {
        "counts_by_map": dict(sorted(counts_by_map.items())),
        "counts_by_map_kind": dict(sorted(counts_by_map_kind.items())),
        "tongues_by_map": {k: sorted(v) for k, v in sorted(tongues_by_map.items())},
        "structural": structural,
        "missing_maps": missing_maps,
        "failures": failures,
        "ok": not missing_maps and not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to drill JSONL")
    parser.add_argument("--output", default=None, help="Optional JSON report path")
    args = parser.parse_args(argv)

    rows = load_drill_rows(args.data)
    report = validate_rows(rows)

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")

    structural = report["structural"]["_summary"]
    print(
        f"DRILL PREFLIGHT: structural {structural['structural_count']}/{structural['count']} "
        f"= {structural['structural_ratio']:.1%}"
    )
    if report["missing_maps"]:
        print(f"MISSING MAPS: {', '.join(report['missing_maps'])}")
    if report["failures"]:
        print(f"FAILURES: {len(report['failures'])}")
        for item in report["failures"][:10]:
            print(f"  - {item['map']}:{item['kind']}:{item['tongue']} -> {item['errors']}")
    else:
        print("FAILURES: 0")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
