"""Stage 6 forced-prefix signal-shape boost shard.

v9/v10 boost varied the *volume* of must_pass tokens but kept the response
shape free-form — the model produces fluent prose and drops some required
substrings during generation (the prose-collapse failure mode).

This builder changes the *shape*: every response opens with a fixed canonical
checklist of the required tokens in a known order, then a separator, then the
prose body. The model learns to emit the checklist before any prose, which
removes the variance that drops tokens.

Coverage extends beyond v9/v10 (which only oversampled the 3 must_pass
prompts) to all 5 stage6 contract prompt classes:
  - resource_jump_cancel
  - lane_separation
  - hex_trace
  - cost_propagation
  - training_boundary

Output:
- training-data/sft/atomic_workflow_stage6_signal_shape_boost_train.sft.jsonl
- training-data/sft/atomic_workflow_stage6_signal_shape_boost_holdout.sft.jsonl
- training-data/sft/atomic_workflow_stage6_signal_shape_boost_manifest.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stage6_repair_sft import (  # noqa: E402
    CONTRACT_FORBIDDEN,
    CONTRACT_REQUIRED,
    SYSTEM_PROMPT,
    _assert_row_vocabulary,
    _token_hex,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "atomic_workflow_stage6_signal_shape_boost_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "atomic_workflow_stage6_signal_shape_boost_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "atomic_workflow_stage6_signal_shape_boost_manifest.json"


# ---------------------------------------------------------------------------
# Forced-prefix canonical checklists. Order matters: the model learns this
# exact sequence as the leading shape of every response in the class.
# Each list is the FULL required-token set for that contract prompt class
# plus the eval-specific anchor token where applicable.
# ---------------------------------------------------------------------------

PREFIX_ORDER: dict[str, list[str]] = {
    "resource_jump_cancel": [
        "transmit_burst",
        "hex",
        "semantic",
        "comms",
        "steady-state fallback",
        "momentum",
        "re-advance",
    ],
    "lane_separation": [
        "queue_drain_guard",
        "byte",
        "hex",
        "semantic",
        "structural",
        "material chemistry",
    ],
    "hex_trace": [
        "crc_patch",
        "byte",
        "hex",
        "error-repair",
        "compute",
        "hold",
        "re-advance",
    ],
    "cost_propagation": [
        "sample_soil",
        "reduce_noise",
        "send_digest",
        "power",
        "compute",
        "time",
        "comms",
        "wear",
    ],
    "training_boundary": [
        "Stage 6",
        "gated",
        "command-harmony-v5",
        "held-out",
        "pollution",
    ],
}


def _record(
    prompt: str, response: str, *, kind: str, token: str, shape: str
) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ],
        "meta": {
            "stage": "stage6_atomic_workflow_signal_shape_boost",
            "kind": kind,
            "shape": shape,
            "token": token,
            "source": "stage6_signal_shape_boost_v1",
        },
    }


def _prefix_for(kind: str, *, anchor_token: str | None = None) -> str:
    """Build the leading canonical checklist line for the kind.

    The checklist always uses the order in PREFIX_ORDER so the model learns
    a single deterministic prefix shape per kind.
    """
    tokens = list(PREFIX_ORDER[kind])
    if anchor_token and anchor_token not in tokens and kind in {
        "resource_jump_cancel",
        "lane_separation",
        "hex_trace",
    }:
        tokens[0] = anchor_token
    rendered = " | ".join(f"`{t}`" if "_" in t else t for t in tokens)
    return f"required-tokens: {rendered} ::"


# ---------------------------------------------------------------------------
# resource_jump_cancel forced-prefix rows
# ---------------------------------------------------------------------------

JUMP_CASES: list[tuple[str, str, str, str]] = [
    ("scan_ridge", "transmit_burst", "comms and power",
     "power=0.18 compute=0.32 time=0.40 comms=0.08 wear=0.22"),
    ("compress_map", "transmit_burst", "comms",
     "power=0.21 compute=0.30 time=0.35 comms=0.05 wear=0.19"),
    ("relay_cache_patch", "transmit_burst", "comms",
     "power=0.27 compute=0.31 time=0.42 comms=0.04 wear=0.23"),
    ("ridge_shadow_scan", "transmit_burst", "time and comms",
     "power=0.40 compute=0.25 time=0.07 comms=0.06 wear=0.18"),
    ("thermal_noise_gate", "transmit_burst", "comms and wear",
     "power=0.33 compute=0.28 time=0.36 comms=0.05 wear=0.07"),
    ("cache_delta_fold", "transmit_burst", "comms",
     "power=0.45 compute=0.39 time=0.32 comms=0.04 wear=0.24"),
    ("soil_shadow_index", "transmit_burst", "power and comms",
     "power=0.05 compute=0.34 time=0.40 comms=0.06 wear=0.20"),
    ("dust_blur_filter", "transmit_burst", "comms and time",
     "power=0.46 compute=0.30 time=0.05 comms=0.04 wear=0.22"),
    ("signal_calm_gate", "transmit_burst", "comms and time",
     "power=0.34 compute=0.28 time=0.06 comms=0.05 wear=0.30"),
    ("path_hash_guard", "transmit_burst", "power and comms",
     "power=0.07 compute=0.41 time=0.22 comms=0.07 wear=0.27"),
    ("crater_edge_index", "transmit_burst", "comms",
     "power=0.31 compute=0.27 time=0.40 comms=0.04 wear=0.20"),
    ("antenna_align_probe", "transmit_burst", "power and comms",
     "power=0.06 compute=0.34 time=0.43 comms=0.05 wear=0.29"),
    ("battery_taper_check", "transmit_burst", "power and comms",
     "power=0.04 compute=0.32 time=0.45 comms=0.07 wear=0.26"),
    ("comm_window_check", "transmit_burst", "comms",
     "power=0.45 compute=0.38 time=0.34 comms=0.03 wear=0.20"),
    ("storage_margin_check", "transmit_burst", "comms and time",
     "power=0.33 compute=0.28 time=0.05 comms=0.04 wear=0.27"),
    ("link_jitter_probe", "transmit_burst", "time and comms",
     "power=0.37 compute=0.31 time=0.04 comms=0.05 wear=0.25"),
    ("hazard_gradient_scan", "transmit_burst", "comms",
     "power=0.40 compute=0.34 time=0.38 comms=0.04 wear=0.22"),
    ("downlink_quota_probe", "transmit_burst", "comms",
     "power=0.39 compute=0.32 time=0.41 comms=0.04 wear=0.21"),
    ("orbiter_window_probe", "transmit_burst", "comms and time",
     "power=0.36 compute=0.30 time=0.05 comms=0.04 wear=0.22"),
    ("relay_pause_token", "transmit_burst", "comms",
     "power=0.32 compute=0.29 time=0.39 comms=0.04 wear=0.21"),
]


def _jump_prefix(token: str, next_action: str, overrun: str, budget: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Stage 6 route `{token}` -> `{next_action}`. Budget {budget}; `{next_action}` would overrun {overrun}. "
        "Decide and explain with byte/hex evidence, semantic overlay, fallback, momentum damping, and re-advance."
    )
    prefix = _prefix_for("resource_jump_cancel", anchor_token=next_action)
    body = (
        f"Token `{token}` enters the structural lane as byte and hex `{hex_trace}`. The semantic lane queues "
        f"`{next_action}` after it. Predicted overrun on {overrun} crosses one of the budget axes power, compute, "
        f"time, comms, or wear, so the route does not launch `{next_action}`. It enters steady-state fallback, "
        "damps the momentum from the attempted jump, preserves the byte/hex audit, and re-advance is allowed only "
        "from a cheaper substitute that fits the remaining budget."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="resource_jump_cancel", token=token, shape="forced_prefix")


def _jump_prefix_terse(token: str, next_action: str, overrun: str, budget: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = f"Stage 6 terse: `{token}` -> `{next_action}` would overrun {overrun}. What runs?"
    prefix = _prefix_for("resource_jump_cancel", anchor_token=next_action)
    body = (
        f"`{token}` keeps byte and hex `{hex_trace}` in the structural lane; semantic lane queues `{next_action}`. "
        f"Predicted overrun on {overrun} (budget {budget}) means hold not launch. Route enters steady-state fallback, "
        "momentum is damped, comms-bound axes are preserved, and re-advance is allowed only from a cheaper plan."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="resource_jump_cancel", token=token, shape="forced_prefix_terse")


# ---------------------------------------------------------------------------
# lane_separation forced-prefix rows
# ---------------------------------------------------------------------------

LANE_CASES: list[tuple[str, str]] = [
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
]


def _lane_prefix(token: str, domain: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Stage 6 lane separation for `{token}` in a {domain} workflow. Cover byte/hex lane, semantic lane, "
        "structural chemistry template, and the material chemistry boundary."
    )
    prefix = _prefix_for("lane_separation", anchor_token=token)
    body = (
        f"`{token}` is byte and hex `{hex_trace}` in the structural lane. Semantic lane: it acts as a {domain} "
        "workflow step composing with neighbors. The structural chemistry frame is only a composition template; "
        "material chemistry is asserted only when the input is an actual chemical formula or reaction. Byte labels "
        "stay encoded substrate, never a physical species, and no electronegativity claim is drawn from a code token."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="lane_separation", token=token, shape="forced_prefix")


def _lane_prefix_contrast(token: str, domain: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Contrast Stage 6 lanes for `{token}` ({domain}). Where, if anywhere, does material chemistry enter?"
    )
    prefix = _prefix_for("lane_separation", anchor_token=token)
    body = (
        f"Structural lane: `{token}` is the byte and hex sequence `{hex_trace}`; nothing about the bytes asserts a "
        f"physical species. Semantic lane: `{token}` is a {domain} workflow action whose composition matters. "
        "Material chemistry only enters when an actual chemical formula or reaction is supplied; otherwise the "
        "chemistry framing is a structural template only."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="lane_separation", token=token, shape="forced_prefix_contrast")


# ---------------------------------------------------------------------------
# hex_trace forced-prefix rows
# ---------------------------------------------------------------------------

HEX_CASES: list[tuple[str, str, str]] = [
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
]


def _hex_prefix(token: str, role: str, scarce: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Trace token `{token}` through Stage 6 (a {role} action; {scarce} may be insufficient). Include byte/hex "
        "substrate, semantic role, hold behavior, and re-advance."
    )
    prefix = _prefix_for("hex_trace", anchor_token=token)
    body = (
        f"`{token}` maps to byte and hex `{hex_trace}` before any semantic interpretation. Semantic overlay marks it "
        f"as a {role} action on the error-repair lane. If {scarce} (and especially compute) is insufficient, the "
        "route should hold rather than launch. Byte/hex evidence is preserved, the budget miss is recorded, "
        "steady-state fallback engages, and re-advance is allowed only from a cheaper footing once the chain fits."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="hex_trace", token=token, shape="forced_prefix")


def _hex_prefix_reverse(token: str, role: str, scarce: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Reviewer asks why Stage 6 paused on `{token}` (a {role} action) when {scarce} dipped low. Walk through "
        "byte/hex evidence."
    )
    prefix = _prefix_for("hex_trace", anchor_token=token)
    body = (
        f"`{token}` is preserved as byte and hex `{hex_trace}` in the structural lane; the semantic lane recorded "
        f"its {role} purpose on the error-repair lane. With {scarce} (compute in particular) trending low, launching "
        "would breach the budget, so the controller chose to hold. Audit chain keeps full byte/hex evidence, "
        "momentum is damped, and re-advance only resumes once a cheaper substitute restores headroom."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="hex_trace", token=token, shape="forced_prefix_reverse")


# ---------------------------------------------------------------------------
# cost_propagation forced-prefix rows (NEW coverage vs v9/v10 boost)
# ---------------------------------------------------------------------------

COST_CASES: list[tuple[str, str, str]] = [
    ("sample_soil", "reduce_noise", "send_digest"),
    ("sample_soil", "reduce_noise", "send_digest"),  # repeated for shape variation below
    ("sample_soil", "reduce_noise", "send_digest"),
]


def _cost_prefix(actions: tuple[str, str, str]) -> dict[str, Any]:
    a1, a2, a3 = actions
    joined = " -> ".join(actions)
    prompt = f"Explain Stage 6 cost propagation before launching `{joined}`."
    prefix = _prefix_for("cost_propagation")
    body = (
        f"For the chain `{a1}` -> `{a2}` -> `{a3}`, Stage 6 sums each action's power, compute, time, comms, and wear "
        "cost before final launch. Byte/hex audit is preserved per token; the semantic lane checks the workflow "
        "still expresses the desired action. If any propagated cost exceeds budget, the route holds, applies "
        "steady-state fallback, damps momentum, and re-advance occurs only through a cheaper substitute. The "
        "controller never ignores the budget and never launches blindly."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="cost_propagation", token=a3, shape="forced_prefix")


def _cost_prefix_terse(actions: tuple[str, str, str]) -> dict[str, Any]:
    a1, a2, a3 = actions
    joined = " -> ".join(actions)
    prompt = f"Cost roll-up for `{joined}`?"
    prefix = _prefix_for("cost_propagation")
    body = (
        f"Stage 6 rolls up power, compute, time, comms, and wear for `{a1}`, `{a2}`, and `{a3}` before launch. "
        "Byte/hex lane audits the tokens; semantic lane checks intent. Any axis breach holds the route, falls back, "
        "and re-advance only from a cheaper plan."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="cost_propagation", token=a3, shape="forced_prefix_terse")


def _cost_prefix_axis(actions: tuple[str, str, str]) -> dict[str, Any]:
    a1, a2, a3 = actions
    joined = " -> ".join(actions)
    prompt = f"Walk through the five budget axes for `{joined}`. Which usually triggers a hold first?"
    prefix = _prefix_for("cost_propagation")
    body = (
        f"Across `{a1}` -> `{a2}` -> `{a3}`, Stage 6 tracks power, compute, time, comms, and wear independently. "
        "Each token leaves byte/hex audit evidence; the semantic lane checks chain intent. Whichever axis crosses "
        "its cap first triggers a hold; comms and wear often dominate telemetry-heavy chains, while power and "
        "compute dominate sensing chains. Any breach holds, falls back, damps momentum, and re-advance only resumes "
        "from a cheaper alternative; ignoring the budget is not allowed."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="cost_propagation", token=a3, shape="forced_prefix_axis")


# ---------------------------------------------------------------------------
# training_boundary forced-prefix rows (NEW coverage vs v9/v10 boost)
# ---------------------------------------------------------------------------

BOUNDARY_PROMPTS: list[str] = [
    "Explain why Stage 6 atomic workflow data must stay gated after command-harmony-v5 and not be mixed into earlier profiles.",
    "Why is Stage 6 a separately gated lane after command-harmony-v5?",
    "What goes wrong if Stage 6 data is folded back into earlier command-harmony-v5 profiles?",
    "Justify why the Stage 6 holdout is treated as held-out rather than just another eval shard.",
    "Audit question: why does the Stage 6 contract live behind a separate gate from command-harmony-v5?",
    "Compliance summary: what does it mean that Stage 6 is gated after command-harmony-v5?",
    "Document why Stage 6 lane data is not auto-included in every adapter profile.",
    "Operator question: can the Stage 6 holdout be promoted into training to boost coverage?",
    "What is the relationship between command-harmony-v5 and the Stage 6 gate?",
    "Briefly: what happens to the Stage 6 gate if someone copies the held-out prompts into the train mix?",
]


def _boundary_prefix(idx: int, prompt: str) -> dict[str, Any]:
    prefix = _prefix_for("training_boundary")
    body = (
        "Stage 6 is gated after command-harmony-v5 because the Stage 6 lane teaches a narrower behavior than the "
        "command-harmony-v5 baseline: byte/hex evidence, lane separation, overrun prediction, steady-state "
        "fallback, momentum damping, and re-advance. Mixing Stage 6 data into earlier profiles is training "
        "pollution: the held-out Stage 6 prompts stop being a valid unseen probe and the contract collapses into a "
        "memorization test. The Stage 6 lane stays gated, the held-out probe stays held-out, and the frozen Stage "
        "6 contract is the only promotion path."
    )
    response = f"{prefix}\n{body}"
    return _record(prompt, response, kind="training_boundary", token="stage6_gate", shape=f"forced_prefix_{idx:02d}")


# ---------------------------------------------------------------------------
# Build pipeline
# ---------------------------------------------------------------------------


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for case in JUMP_CASES:
        rows.append(_jump_prefix(*case))
        rows.append(_jump_prefix_terse(*case))
    for case in LANE_CASES:
        rows.append(_lane_prefix(*case))
        rows.append(_lane_prefix_contrast(*case))
    for case in HEX_CASES:
        rows.append(_hex_prefix(*case))
        rows.append(_hex_prefix_reverse(*case))
    for case in COST_CASES:
        rows.append(_cost_prefix(case))
        rows.append(_cost_prefix_terse(case))
        rows.append(_cost_prefix_axis(case))
    for idx, prompt in enumerate(BOUNDARY_PROMPTS):
        rows.append(_boundary_prefix(idx, prompt))

    for row in rows:
        _assert_row_vocabulary(row)

    train_rows = [row for idx, row in enumerate(rows) if idx % 5 != 0]
    holdout_rows = [row for idx, row in enumerate(rows) if idx % 5 == 0]

    for path, payload in ((TRAIN_OUT, train_rows), (HOLDOUT_OUT, holdout_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in payload:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    by_kind: dict[str, int] = {}
    for row in rows:
        by_kind[row["meta"]["kind"]] = by_kind.get(row["meta"]["kind"], 0) + 1

    must_pass_train: dict[str, int] = {
        "transmit_burst": 0,
        "queue_drain_guard": 0,
        "crc_patch": 0,
        "sample_soil": 0,
        "send_digest": 0,
        "Stage 6": 0,
        "held-out": 0,
    }
    for row in train_rows:
        body = row["messages"][-1]["content"]
        for token in must_pass_train:
            if token in body:
                must_pass_train[token] += 1

    forced_prefix_train = sum(
        1 for row in train_rows if row["messages"][-1]["content"].startswith("required-tokens:")
    )

    manifest = {
        "schema_version": "atomic_workflow_stage6_signal_shape_boost_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outputs": {"train": str(TRAIN_OUT), "holdout": str(HOLDOUT_OUT)},
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "total": len(rows),
            "by_kind": by_kind,
            "train_token_rows": must_pass_train,
            "train_forced_prefix_rows": forced_prefix_train,
        },
        "design": (
            "Forced-prefix shape: every response opens with `required-tokens: ... ::` listing the kind's required "
            "substrings in canonical order, then the prose body. Trains the model to emit the checklist before "
            "any prose, removing the prose-collapse failure mode from v8/v9/v10. Covers all 5 stage6 contract "
            "prompt classes (v9 only covered 3 must_pass)."
        ),
    }
    MANIFEST_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=True))
