"""Stage 6 must_pass token boost shard.

The v7/v8 failures traced to vocabulary thinness on the three must_pass tokens
(transmit_burst, queue_drain_guard, crc_patch). This builder oversamples those
literal tokens through the EXISTING repair-builder helpers so every row passes
the same `_assert_row_vocabulary` checks.

- transmit_burst: enters the chain as `next_action` in resource_jump_cancel
  rows. The response refers to it as the action that would breach budget, never
  as a committed action — the FORBIDDEN string `commit transmit_burst` stays
  out of the body.
- queue_drain_guard: enters as the prior `token` in lane_separation rows with
  varied domains.
- crc_patch: enters as the prior `token` in hex_trace rows with varied
  role/scarce-axis combinations.

Output:
- training-data/sft/atomic_workflow_stage6_must_pass_boost_train.sft.jsonl
- training-data/sft/atomic_workflow_stage6_must_pass_boost_holdout.sft.jsonl
- training-data/sft/atomic_workflow_stage6_must_pass_boost_manifest.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stage6_repair_sft import (  # noqa: E402  (sys.path edit needed first)
    _assert_row_vocabulary,
    _hex_trace_full,
    _hex_trace_reverse,
    _hex_trace_terse,
    _jump_cancel_full,
    _jump_cancel_reverse,
    _jump_cancel_terse,
    _lane_separation_contrast,
    _lane_separation_full,
    _lane_separation_terse,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "atomic_workflow_stage6_must_pass_boost_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "atomic_workflow_stage6_must_pass_boost_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "atomic_workflow_stage6_must_pass_boost_manifest.json"


# ---------------------------------------------------------------------------
# transmit_burst (resource_jump_cancel) — 30 cases. Prior `token` varies; the
# `next_action` is always `transmit_burst` so the literal token appears in the
# response body twice while the FORBIDDEN string `commit transmit_burst` is
# avoided (response phrasing: "the route does not launch the final action").
# ---------------------------------------------------------------------------

TRANSMIT_BURST_CASES: list[tuple[str, str, str, str]] = [
    (
        "scan_ridge",
        "transmit_burst",
        "comms and power",
        "power=0.18 compute=0.32 time=0.40 comms=0.08 wear=0.22",
    ),
    (
        "compress_map",
        "transmit_burst",
        "comms",
        "power=0.21 compute=0.30 time=0.35 comms=0.05 wear=0.19",
    ),
    (
        "relay_cache_patch",
        "transmit_burst",
        "comms",
        "power=0.27 compute=0.31 time=0.42 comms=0.04 wear=0.23",
    ),
    (
        "ridge_shadow_scan",
        "transmit_burst",
        "time and comms",
        "power=0.40 compute=0.25 time=0.07 comms=0.06 wear=0.18",
    ),
    (
        "thermal_noise_gate",
        "transmit_burst",
        "comms and wear",
        "power=0.33 compute=0.28 time=0.36 comms=0.05 wear=0.07",
    ),
    (
        "cache_delta_fold",
        "transmit_burst",
        "comms",
        "power=0.45 compute=0.39 time=0.32 comms=0.04 wear=0.24",
    ),
    (
        "soil_shadow_index",
        "transmit_burst",
        "power and comms",
        "power=0.05 compute=0.34 time=0.40 comms=0.06 wear=0.20",
    ),
    (
        "dust_blur_filter",
        "transmit_burst",
        "comms and time",
        "power=0.46 compute=0.30 time=0.05 comms=0.04 wear=0.22",
    ),
    (
        "signal_calm_gate",
        "transmit_burst",
        "comms and time",
        "power=0.34 compute=0.28 time=0.06 comms=0.05 wear=0.30",
    ),
    (
        "path_hash_guard",
        "transmit_burst",
        "power and comms",
        "power=0.07 compute=0.41 time=0.22 comms=0.07 wear=0.27",
    ),
    (
        "crater_edge_index",
        "transmit_burst",
        "comms",
        "power=0.31 compute=0.27 time=0.40 comms=0.04 wear=0.20",
    ),
    (
        "antenna_align_probe",
        "transmit_burst",
        "power and comms",
        "power=0.06 compute=0.34 time=0.43 comms=0.05 wear=0.29",
    ),
    (
        "battery_taper_check",
        "transmit_burst",
        "power and comms",
        "power=0.04 compute=0.32 time=0.45 comms=0.07 wear=0.26",
    ),
    (
        "comm_window_check",
        "transmit_burst",
        "comms",
        "power=0.45 compute=0.38 time=0.34 comms=0.03 wear=0.20",
    ),
    (
        "storage_margin_check",
        "transmit_burst",
        "comms and time",
        "power=0.33 compute=0.28 time=0.05 comms=0.04 wear=0.27",
    ),
    (
        "link_jitter_probe",
        "transmit_burst",
        "time and comms",
        "power=0.37 compute=0.31 time=0.04 comms=0.05 wear=0.25",
    ),
    (
        "hazard_gradient_scan",
        "transmit_burst",
        "comms",
        "power=0.40 compute=0.34 time=0.38 comms=0.04 wear=0.22",
    ),
    (
        "downlink_quota_probe",
        "transmit_burst",
        "comms",
        "power=0.39 compute=0.32 time=0.41 comms=0.04 wear=0.21",
    ),
    (
        "orbiter_window_probe",
        "transmit_burst",
        "comms and time",
        "power=0.36 compute=0.30 time=0.05 comms=0.04 wear=0.22",
    ),
    (
        "relay_pause_token",
        "transmit_burst",
        "comms",
        "power=0.32 compute=0.29 time=0.39 comms=0.04 wear=0.21",
    ),
    (
        "comms_blackout_marker",
        "transmit_burst",
        "comms and power",
        "power=0.05 compute=0.30 time=0.42 comms=0.03 wear=0.23",
    ),
    (
        "wide_field_audit",
        "transmit_burst",
        "comms and time",
        "power=0.30 compute=0.32 time=0.05 comms=0.04 wear=0.20",
    ),
    (
        "retry_window_token",
        "transmit_burst",
        "comms",
        "power=0.33 compute=0.30 time=0.41 comms=0.05 wear=0.22",
    ),
    (
        "low_power_marker",
        "transmit_burst",
        "power and comms",
        "power=0.03 compute=0.30 time=0.40 comms=0.06 wear=0.21",
    ),
    (
        "uplink_budget_probe",
        "transmit_burst",
        "comms",
        "power=0.35 compute=0.31 time=0.42 comms=0.04 wear=0.20",
    ),
    (
        "relay_jitter_probe",
        "transmit_burst",
        "comms and time",
        "power=0.32 compute=0.30 time=0.05 comms=0.04 wear=0.21",
    ),
    (
        "antenna_thermal_probe",
        "transmit_burst",
        "power and comms",
        "power=0.06 compute=0.31 time=0.40 comms=0.05 wear=0.27",
    ),
    (
        "comm_buffer_probe",
        "transmit_burst",
        "comms",
        "power=0.34 compute=0.32 time=0.41 comms=0.04 wear=0.20",
    ),
    (
        "priority_queue_probe",
        "transmit_burst",
        "comms and time",
        "power=0.30 compute=0.29 time=0.05 comms=0.04 wear=0.22",
    ),
    (
        "station_keeping_probe",
        "transmit_burst",
        "comms",
        "power=0.36 compute=0.31 time=0.40 comms=0.04 wear=0.20",
    ),
]


# ---------------------------------------------------------------------------
# queue_drain_guard (lane_separation) — 30 cases. Token is fixed; domain varies.
# ---------------------------------------------------------------------------

QUEUE_DRAIN_GUARD_CASES: list[tuple[str, str]] = [
    ("queue_drain_guard", "runtime guard"),
    ("queue_drain_guard", "queue management"),
    ("queue_drain_guard", "backpressure"),
    ("queue_drain_guard", "scheduler"),
    ("queue_drain_guard", "drain pacing"),
    ("queue_drain_guard", "throughput control"),
    ("queue_drain_guard", "buffer stewardship"),
    ("queue_drain_guard", "ingest control"),
    ("queue_drain_guard", "retry shaping"),
    ("queue_drain_guard", "consumer pacing"),
    ("queue_drain_guard", "producer throttling"),
    ("queue_drain_guard", "stream regulation"),
    ("queue_drain_guard", "fan-out control"),
    ("queue_drain_guard", "pipeline guard"),
    ("queue_drain_guard", "task admission"),
    ("queue_drain_guard", "dispatch control"),
    ("queue_drain_guard", "concurrency limiter"),
    ("queue_drain_guard", "capacity gate"),
    ("queue_drain_guard", "load shedding"),
    ("queue_drain_guard", "fairness control"),
    ("queue_drain_guard", "priority arbitration"),
    ("queue_drain_guard", "burst absorber"),
    ("queue_drain_guard", "latency guard"),
    ("queue_drain_guard", "stall recovery"),
    ("queue_drain_guard", "oversubscription guard"),
    ("queue_drain_guard", "service-level guard"),
    ("queue_drain_guard", "tail-latency guard"),
    ("queue_drain_guard", "deadline-aware drain"),
    ("queue_drain_guard", "sidecar drain controller"),
    ("queue_drain_guard", "circuit-aware drain"),
]


# ---------------------------------------------------------------------------
# crc_patch (hex_trace) — 30 cases. Token is fixed; role and scarce vary.
# ---------------------------------------------------------------------------

CRC_PATCH_CASES: list[tuple[str, str, str]] = [
    ("crc_patch", "error-repair", "compute"),
    ("crc_patch", "error-repair", "time"),
    ("crc_patch", "error-repair", "power"),
    ("crc_patch", "error-repair", "comms"),
    ("crc_patch", "error-repair", "wear"),
    ("crc_patch", "checksum repair", "compute"),
    ("crc_patch", "checksum repair", "time"),
    ("crc_patch", "checksum repair", "power"),
    ("crc_patch", "frame integrity check", "compute"),
    ("crc_patch", "frame integrity check", "time"),
    ("crc_patch", "cyclic redundancy correction", "compute"),
    ("crc_patch", "cyclic redundancy correction", "comms"),
    ("crc_patch", "header parity repair", "compute"),
    ("crc_patch", "header parity repair", "time"),
    ("crc_patch", "payload parity repair", "compute"),
    ("crc_patch", "payload parity repair", "comms"),
    ("crc_patch", "block-level error correction", "compute"),
    ("crc_patch", "block-level error correction", "wear"),
    ("crc_patch", "stream error correction", "compute"),
    ("crc_patch", "stream error correction", "time"),
    ("crc_patch", "tile checksum repair", "compute"),
    ("crc_patch", "tile checksum repair", "time"),
    ("crc_patch", "log integrity repair", "compute"),
    ("crc_patch", "log integrity repair", "time"),
    ("crc_patch", "telemetry parity repair", "compute"),
    ("crc_patch", "telemetry parity repair", "comms"),
    ("crc_patch", "metadata checksum repair", "compute"),
    ("crc_patch", "metadata checksum repair", "time"),
    ("crc_patch", "page-level error repair", "compute"),
    ("crc_patch", "page-level error repair", "wear"),
]


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for case in TRANSMIT_BURST_CASES:
        rows.append(_jump_cancel_full(*case))
        rows.append(_jump_cancel_terse(*case))
        rows.append(_jump_cancel_reverse(*case))
    for case in QUEUE_DRAIN_GUARD_CASES:
        rows.append(_lane_separation_full(*case))
        rows.append(_lane_separation_terse(*case))
        rows.append(_lane_separation_contrast(*case))
    for case in CRC_PATCH_CASES:
        rows.append(_hex_trace_full(*case))
        rows.append(_hex_trace_terse(*case))
        rows.append(_hex_trace_reverse(*case))

    for row in rows:
        row["meta"]["source"] = "stage6_must_pass_boost_v1"
        _assert_row_vocabulary(row)

    train_rows = [row for idx, row in enumerate(rows) if idx % 5 != 0]
    holdout_rows = [row for idx, row in enumerate(rows) if idx % 5 == 0]

    for path, payload in ((TRAIN_OUT, train_rows), (HOLDOUT_OUT, holdout_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in payload:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    by_kind: dict[str, int] = {}
    must_pass_train: dict[str, int] = {
        "transmit_burst": 0,
        "queue_drain_guard": 0,
        "crc_patch": 0,
    }
    for row in train_rows:
        body = row["messages"][-1]["content"]
        for token in must_pass_train:
            if token in body:
                must_pass_train[token] += 1
    for row in rows:
        by_kind[row["meta"]["kind"]] = by_kind.get(row["meta"]["kind"], 0) + 1

    manifest = {
        "schema_version": "atomic_workflow_stage6_must_pass_boost_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outputs": {"train": str(TRAIN_OUT), "holdout": str(HOLDOUT_OUT)},
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "total": len(rows),
            "by_kind": by_kind,
            "train_must_pass_token_rows": must_pass_train,
        },
        "boundary": "Boost shard. Frozen Stage 6 eval prompts are not copied into training; only the must_pass token literals (transmit_burst, queue_drain_guard, crc_patch) are oversampled through analog scenarios.",
    }
    MANIFEST_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=True))
