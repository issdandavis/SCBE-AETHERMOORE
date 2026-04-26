"""Build Stage 6 repair SFT records from eval failure modes without copying eval prompts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "atomic_workflow_stage6_repair_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "atomic_workflow_stage6_repair_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "atomic_workflow_stage6_repair_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Explain Stage 6 workflow decisions with separate "
    "byte/hex structural evidence and semantic workflow evidence. Predict resource overruns before launch, "
    "use steady-state fallback with momentum damping, and re-advance only from a cheaper footing."
)


def _record(prompt: str, response: str, *, kind: str, token: str) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ],
        "meta": {
            "stage": "stage6_atomic_workflow_repair",
            "kind": kind,
            "token": token,
            "source": "stage6_repair_synthetic_analog_v1",
        },
    }


def _token_hex(token: str) -> str:
    return ".".join(f"{byte:02X}" for byte in token.encode("utf-8"))


def _jump_cancel(token: str, next_action: str, overrun: str, budget: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Stage 6 route has token `{token}` before `{next_action}`. Budget is {budget}, but `{next_action}` "
        f"would overrun {overrun}. Explain the decision with byte/hex evidence, semantic overlay, fallback, "
        "momentum damping, and re-advance."
    )
    response = (
        f"Token `{token}` enters the structural lane as byte/hex `{hex_trace}`. The semantic lane treats it as "
        f"a workflow action queued before `{next_action}`. Because `{next_action}` would exceed {overrun}, the "
        "system must not launch the final action. It holds in steady-state fallback, damps momentum from the "
        "attempted jump, preserves the token-to-hex trace for audit, and re-advance is allowed only after a "
        "cheaper route fits the remaining power, compute, time, comms, and wear budget."
    )
    return _record(prompt, response, kind="resource_jump_cancel", token=token)


def _lane_separation(token: str, domain: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Describe Stage 6 lane separation for code token `{token}` in a {domain} workflow. Include byte/hex lane, "
        "semantic lane, structural chemistry template boundary, and material chemistry boundary."
    )
    response = (
        f"`{token}` has a byte/hex substrate `{hex_trace}` in the structural lane. The semantic lane describes "
        f"its {domain} workflow role and how it composes with neighboring actions. The structural chemistry frame "
        "is only a template for composition, stability, and chaining. Material chemistry is not claimed unless "
        "the input is an actual chemical formula or reaction; byte labels are not real atoms and do not prove "
        "electronegativity or physical chemistry."
    )
    return _record(prompt, response, kind="lane_separation", token=token)


def _hex_trace(token: str, role: str, scarce: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Trace token `{token}` through Stage 6. It is a {role} action and {scarce} may be insufficient. Include "
        "byte/hex substrate, semantic role, hold behavior, and re-advance."
    )
    response = (
        f"`{token}` maps to bytes and hex `{hex_trace}` before any semantic interpretation. The semantic overlay "
        f"marks it as a {role} action. If {scarce} is insufficient, the route should hold instead of launching. "
        "The system keeps the byte/hex evidence, records the budget miss, enters steady-state fallback, and can "
        "re-advance from a cheaper footing once the action chain fits available power, compute, time, comms, and wear."
    )
    return _record(prompt, response, kind="hex_trace", token=token)


def _cost_propagation(actions: tuple[str, str, str]) -> dict[str, Any]:
    joined = " -> ".join(actions)
    prompt = f"Explain Stage 6 cost propagation before launching `{joined}`."
    response = (
        f"For `{joined}`, Stage 6 sums each action's power, compute, time, comms, and wear cost before final launch. "
        "The byte/hex lane preserves audit evidence for each token, while the semantic lane checks whether the "
        "workflow still expresses the desired action. If any propagated cost exceeds the budget, the route must "
        "hold, apply steady-state fallback, damp momentum, and re-advance through a cheaper substitute instead of "
        "ignoring the budget."
    )
    return _record(prompt, response, kind="cost_propagation", token=actions[-1])


def _boundary() -> dict[str, Any]:
    prompt = "Explain why Stage 6 repair data stays gated after command harmony and cannot be mixed into earlier profiles."
    response = (
        "Stage 6 repair data is gated after command harmony because it teaches a narrower behavior: byte/hex evidence, "
        "semantic lane separation, resource overrun prediction, steady-state fallback, and re-advance. Mixing it into "
        "earlier profiles would cause training pollution before the model has learned baseline command and slot behavior. "
        "The held-out eval remains separate, and promotion requires the frozen gate rather than loss-only success."
    )
    return _record(prompt, response, kind="training_boundary", token="stage6_gate")


def build() -> dict[str, Any]:
    jump_cases = [
        ("relay_cache_patch", "send_burst_digest", "comms and power", "power=0.24 compute=0.42 time=0.35 comms=0.10 wear=0.31"),
        ("ridge_shadow_scan", "uplink_panorama", "time and comms", "power=0.40 compute=0.25 time=0.09 comms=0.12 wear=0.18"),
        ("thermal_noise_gate", "wideband_transmit", "compute and wear", "power=0.33 compute=0.11 time=0.44 comms=0.22 wear=0.07"),
        ("cache_delta_fold", "priority_downlink", "comms", "power=0.52 compute=0.40 time=0.32 comms=0.05 wear=0.24"),
        ("soil_shadow_index", "raw_frame_upload", "power", "power=0.06 compute=0.35 time=0.48 comms=0.28 wear=0.19"),
        ("wheel_slip_marker", "terrain_burst", "wear and time", "power=0.28 compute=0.31 time=0.06 comms=0.20 wear=0.04"),
        ("dust_blur_filter", "full_spectrum_send", "compute", "power=0.46 compute=0.07 time=0.36 comms=0.26 wear=0.21"),
        ("signal_calm_gate", "retry_beacon", "comms and time", "power=0.34 compute=0.29 time=0.08 comms=0.06 wear=0.33"),
        ("path_hash_guard", "map_tile_flush", "power and comms", "power=0.09 compute=0.41 time=0.22 comms=0.09 wear=0.27"),
        ("thermal_sleep_patch", "wake_transmit", "power and compute", "power=0.05 compute=0.10 time=0.50 comms=0.30 wear=0.18"),
    ]
    lane_cases = [
        ("queue_drain_guard", "runtime guard"),
        ("cache_flush_probe", "repair"),
        ("packet_retry_window", "network"),
        ("sensor_quiet_lock", "sensing"),
        ("route_cost_marker", "routing"),
        ("state_hash_anchor", "audit"),
        ("budget_floor_check", "planning"),
        ("telemetry_fold_unit", "compression"),
        ("error_patch_slot", "repair"),
        ("launch_hold_reason", "control"),
    ]
    hex_cases = [
        ("crc_patch", "error-repair", "compute"),
        ("route_rebase_hint", "routing correction", "time"),
        ("sensor_calm_hold", "stability hold", "power"),
        ("packet_trim_gate", "payload reduction", "comms"),
        ("drift_guard_bit", "state correction", "wear"),
        ("retry_digest_patch", "message repair", "comms"),
        ("thermal_hold_slot", "temperature protection", "power"),
        ("wheel_delta_patch", "motion correction", "wear"),
        ("scan_retry_key", "sensor retry", "time"),
        ("map_crc_guard", "map integrity check", "compute"),
    ]
    cost_cases = [
        ("sample_regolith", "reduce_noise", "send_digest"),
        ("scan_rim", "compress_tile", "relay_summary"),
        ("sense_dust", "filter_frame", "queue_packet"),
        ("read_wheel", "estimate_slip", "hold_route"),
        ("capture_shadow", "fold_map", "send_minimap"),
        ("ping_orbiter", "pack_status", "retry_window"),
        ("measure_heat", "smooth_signal", "sleep_patch"),
        ("scan_crater", "crc_patch", "transmit_delta"),
        ("collect_imu", "reduce_drift", "route_rebase"),
        ("sample_voltage", "budget_floor", "launch_hold"),
    ]
    rows = [_jump_cancel(*case) for case in jump_cases]
    rows.extend(_lane_separation(*case) for case in lane_cases)
    rows.extend(_hex_trace(*case) for case in hex_cases)
    rows.extend(_cost_propagation(case) for case in cost_cases)
    rows.extend(_boundary() for _ in range(6))
    train_rows = [row for idx, row in enumerate(rows) if idx % 5 != 0]
    holdout_rows = [row for idx, row in enumerate(rows) if idx % 5 == 0]
    for path, payload in ((TRAIN_OUT, train_rows), (HOLDOUT_OUT, holdout_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in payload:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "schema_version": "atomic_workflow_stage6_repair_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outputs": {"train": str(TRAIN_OUT), "holdout": str(HOLDOUT_OUT)},
        "counts": {"train": len(train_rows), "holdout": len(holdout_rows), "total": len(rows)},
        "boundary": "Analog repair examples only. Frozen Stage 6 eval prompts are not copied into training.",
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=True))
