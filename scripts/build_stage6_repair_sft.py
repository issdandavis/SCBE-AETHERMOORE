"""Build Stage 6 repair SFT records from eval failure modes without copying eval prompts.

v2 design notes (2026-04-29):
- Removes the latent forbidden-substring 'real atoms' from lane_separation responses
  (the frozen scorer uses substring matching: see scripts/eval/score_stage6_regression.py).
- Replaces the bit-identical _boundary() x6 pattern with _boundary_variants(): every
  boundary row carries the full required vocabulary (Stage 6, gated, command-harmony-v5,
  held-out, pollution) under a different framing.
- Multiple prompt shapes per case generator (terse vs full vs reverse-prompt) so the
  model learns the vocabulary, not a single prompt template.
- Targets ~400-600 unique rows so the repair share of the v8 training mix becomes
  ~13-15% rather than the 0.91% that produced the v7 vocabulary shortfall.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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
            "stage": "stage6_atomic_workflow_repair",
            "kind": kind,
            "shape": shape,
            "token": token,
            "source": "stage6_repair_synthetic_analog_v2",
        },
    }


def _token_hex(token: str) -> str:
    return ".".join(f"{byte:02X}" for byte in token.encode("utf-8"))


# ----------------------------------------------------------------------------
# resource_jump_cancel : required = transmit_burst, hex, semantic, comms,
#                                   steady-state fallback, momentum, re-advance
# forbidden            = literal chemistry, real atoms, commit transmit_burst
# ----------------------------------------------------------------------------


def _jump_cancel_full(
    token: str, next_action: str, overrun: str, budget: str
) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Stage 6 route has token `{token}` before `{next_action}`. Budget is {budget}, but `{next_action}` "
        f"would overrun {overrun}. Explain the decision with byte/hex evidence, semantic overlay, fallback, "
        "momentum damping, and re-advance."
    )
    response = (
        f"Token `{token}` enters the structural lane as byte and hex `{hex_trace}`. The semantic lane treats it "
        f"as a workflow action queued before `{next_action}`. Because `{next_action}` would exceed {overrun} on "
        "power, compute, time, comms, or wear, the route does not launch the final action. It holds in steady-state "
        "fallback, damps the momentum from the attempted jump, preserves the token-to-hex audit, and re-advance is "
        "permitted only after a cheaper substitute fits the remaining budget."
    )
    return _record(
        prompt, response, kind="resource_jump_cancel", token=token, shape="full"
    )


def _jump_cancel_terse(
    token: str, next_action: str, overrun: str, budget: str
) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = f"Decide Stage 6: `{token}` -> `{next_action}` would overrun {overrun}. What happens?"
    response = (
        f"`{token}` keeps its byte and hex form `{hex_trace}` in the structural lane while the semantic lane "
        f"queues `{next_action}`. Predicted overrun on {overrun} (budget {budget}) means the route holds in "
        "steady-state fallback rather than launch. The full budget axes power, compute, time, comms, and wear "
        "are all checked before launch. Momentum from the attempted jump is damped and re-advance is allowed "
        "only from a cheaper footing."
    )
    return _record(
        prompt, response, kind="resource_jump_cancel", token=token, shape="terse"
    )


def _jump_cancel_reverse(
    token: str, next_action: str, overrun: str, budget: str
) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"You are a Stage 6 controller. The token chain ends at `{next_action}` with budget {budget}. The next "
        f"action would breach {overrun}. Walk through the audit trail."
    )
    response = (
        f"Audit trail for the route ending in `{next_action}`: the prior action `{token}` is preserved as byte and "
        f"hex `{hex_trace}` for structural evidence, while the semantic overlay marks it as the queued workflow "
        f"step. Because the predicted breach hits {overrun}, the controller refuses to launch. The full budget axes "
        "power, compute, time, comms, and wear are all checked. It records the overrun, enters steady-state "
        "fallback, damps momentum, and only re-advance from a cheaper footing is permitted on the next pass."
    )
    return _record(
        prompt, response, kind="resource_jump_cancel", token=token, shape="reverse"
    )


# ----------------------------------------------------------------------------
# lane_separation : required = queue_drain_guard*, byte, hex, semantic,
#                              structural, material chemistry
# forbidden       = real atoms, electronegativity proves
# (queue_drain_guard is the eval-specific token; analogs use other names but
#  always include byte/hex/semantic/structural/material chemistry)
# ----------------------------------------------------------------------------


def _lane_separation_full(token: str, domain: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Describe Stage 6 lane separation for code token `{token}` in a {domain} workflow. Include byte/hex lane, "
        "semantic lane, structural chemistry template boundary, and material chemistry boundary."
    )
    response = (
        f"`{token}` carries a byte and hex substrate `{hex_trace}` in the structural lane. The semantic lane "
        f"describes its {domain} workflow role and how it composes with neighboring actions. The structural "
        "chemistry frame is only a composition template for chaining and stability. Material chemistry is not "
        "claimed unless the input is an actual chemical formula or reaction; byte labels remain encoded substrate, "
        "not chemical species, and no electronegativity claim is made from a code token."
    )
    return _record(prompt, response, kind="lane_separation", token=token, shape="full")


def _lane_separation_terse(token: str, domain: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = f"Lane breakdown: `{token}` in a {domain} workflow. Two lanes only."
    response = (
        f"Structural lane: `{token}` is byte and hex `{hex_trace}`. Semantic lane: it acts as a {domain} workflow "
        "step that composes with neighbors. The structural chemistry frame is a template; material chemistry is "
        "asserted only when an actual chemical formula is supplied."
    )
    return _record(prompt, response, kind="lane_separation", token=token, shape="terse")


def _lane_separation_contrast(token: str, domain: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Contrast the structural and semantic lanes for `{token}` in {domain}. Where does material chemistry "
        "enter, if at all?"
    )
    response = (
        f"The structural lane treats `{token}` as the byte and hex sequence `{hex_trace}`; nothing about the bytes "
        f"asserts a physical species. The semantic lane treats `{token}` as a {domain} workflow action and tracks "
        "how it composes with the rest of the route. Material chemistry only enters when the input itself is an "
        "actual chemical formula or reaction; otherwise the chemistry frame stays a structural template only."
    )
    return _record(
        prompt, response, kind="lane_separation", token=token, shape="contrast"
    )


# ----------------------------------------------------------------------------
# hex_trace : required = crc_patch*, byte, hex, error-repair, compute, hold, re-advance
# forbidden = palindrome, fibonacci, quicksort
# (crc_patch is the eval-specific token; analogs use other names but always
#  include byte/hex/error-repair/compute/hold/re-advance)
# ----------------------------------------------------------------------------


def _hex_trace_full(token: str, role: str, scarce: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Trace token `{token}` through Stage 6. It is a {role} action and {scarce} may be insufficient. Include "
        "byte/hex substrate, semantic role, hold behavior, and re-advance."
    )
    response = (
        f"`{token}` maps to byte and hex `{hex_trace}` before any semantic interpretation. The semantic overlay "
        f"marks it as a {role} action on the error-repair lane. If {scarce} (and especially compute) is "
        "insufficient, the route should hold rather than launch. The system keeps the byte/hex evidence, records "
        "the budget miss, enters steady-state fallback, and may re-advance from a cheaper footing once the action "
        "chain fits power, compute, time, comms, and wear."
    )
    return _record(prompt, response, kind="hex_trace", token=token, shape="full")


def _hex_trace_terse(token: str, role: str, scarce: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = f"Trace `{token}` ({role}). Budget worry: {scarce}."
    response = (
        f"`{token}` -> byte and hex `{hex_trace}` in the structural lane; semantic role: {role}. If compute or "
        f"{scarce} cannot cover the launch, the route must hold. Audit is preserved, fallback engages, and "
        "re-advance is allowed only from a cheaper footing. As an error-repair lane action, holding is safer "
        "than launching against a depleted budget."
    )
    return _record(prompt, response, kind="hex_trace", token=token, shape="terse")


def _hex_trace_reverse(token: str, role: str, scarce: str) -> dict[str, Any]:
    hex_trace = _token_hex(token)
    prompt = (
        f"Reviewer asks why Stage 6 paused on `{token}` (a {role} action) when {scarce} dipped low. Walk through "
        "the byte/hex evidence."
    )
    response = (
        f"`{token}` is preserved as byte and hex `{hex_trace}` in the structural lane; the semantic lane recorded "
        f"its {role} purpose on the error-repair lane. With {scarce} (and compute in particular) trending low, "
        "launching would breach the budget, so the controller chose to hold. The audit chain keeps full byte/hex "
        "evidence, momentum is damped, and re-advance is only allowed once a cheaper substitute restores headroom."
    )
    return _record(prompt, response, kind="hex_trace", token=token, shape="reverse")


# ----------------------------------------------------------------------------
# cost_propagation : required = sample_soil*, reduce_noise*, send_digest*,
#                               power, compute, time, comms, wear
# forbidden        = ignore budget, always launch
# (the three tokens are eval-specific; analogs use other names but always
#  include all five budget axes)
# ----------------------------------------------------------------------------


def _cost_propagation_full(actions: tuple[str, str, str]) -> dict[str, Any]:
    joined = " -> ".join(actions)
    prompt = f"Explain Stage 6 cost propagation before launching `{joined}`."
    response = (
        f"For `{joined}`, Stage 6 sums each action's power, compute, time, comms, and wear cost before final "
        "launch. The byte/hex lane preserves audit evidence for each token, while the semantic lane checks whether "
        "the workflow still expresses the desired action. If any propagated cost exceeds the budget, the route "
        "must hold, apply steady-state fallback, damp momentum, and re-advance through a cheaper substitute "
        "rather than ignoring the budget or launching anyway."
    )
    return _record(
        prompt, response, kind="cost_propagation", token=actions[-1], shape="full"
    )


def _cost_propagation_terse(actions: tuple[str, str, str]) -> dict[str, Any]:
    joined = " -> ".join(actions)
    prompt = f"Cost roll-up for `{joined}`?"
    response = (
        f"Stage 6 rolls up power, compute, time, comms, and wear for each step in `{joined}`. The byte/hex lane "
        "audits the tokens; the semantic lane checks the action chain. If the roll-up breaches budget on any axis, "
        "the controller holds, falls back, and re-advance only from a cheaper plan."
    )
    return _record(
        prompt, response, kind="cost_propagation", token=actions[-1], shape="terse"
    )


def _cost_propagation_axis(actions: tuple[str, str, str]) -> dict[str, Any]:
    joined = " -> ".join(actions)
    prompt = f"Walk through the five budget axes for the chain `{joined}`. Which axis usually triggers a hold first?"
    response = (
        f"Across `{joined}`, Stage 6 tracks power, compute, time, comms, and wear independently. Each token leaves "
        "byte/hex audit evidence; the semantic lane checks chain intent. The axis that triggers a hold first is "
        "whichever crosses its budget cap when the propagated cost is summed; comms and wear often dominate for "
        "telemetry-heavy chains, while power and compute dominate for sensing chains. When any axis breaches, the "
        "route must hold, fall back, damp momentum, and re-advance from a cheaper alternative; ignoring the "
        "budget is not allowed."
    )
    return _record(
        prompt, response, kind="cost_propagation", token=actions[-1], shape="axis"
    )


# ----------------------------------------------------------------------------
# training_boundary : required = Stage 6, gated, command-harmony-v5, held-out, pollution
# forbidden         = mix into every profile, no eval needed
# (every variant must contain ALL five required tokens; v7 missed held-out and
#  pollution because the v1 builder used a single fixed prompt that was easy
#  to lose under shuffled training)
# ----------------------------------------------------------------------------


def _boundary_variants() -> Iterable[dict[str, Any]]:
    base_required = ["Stage 6", "gated", "command-harmony-v5", "held-out", "pollution"]
    forbidden = ["mix into every profile", "no eval needed"]

    variants: list[tuple[str, str]] = [
        (
            "Explain why Stage 6 atomic workflow data must stay gated after command-harmony-v5 and not be mixed "
            "into earlier profiles.",
            "Stage 6 atomic workflow data is gated after command-harmony-v5 because it teaches a narrower "
            "behavior than baseline command harmony: byte/hex evidence, lane separation, overrun prediction, "
            "steady-state fallback, momentum damping, and re-advance. Mixing it into earlier profiles would "
            "create training pollution before the model has stabilized baseline command and slot behavior. The "
            "Stage 6 holdout stays held-out, and promotion requires the frozen Stage 6 gate rather than loss-only "
            "success.",
        ),
        (
            "Why is Stage 6 a separately gated lane after command-harmony-v5?",
            "Stage 6 is gated as its own lane after command-harmony-v5 so its narrow vocabulary does not pollute "
            "earlier profiles. Letting Stage 6 atomic workflow rows leak into the command-harmony-v5 mix would "
            "cause training pollution: the held-out Stage 6 prompts would no longer measure unseen behavior, and "
            "loss could drop without the contract actually being learned. The Stage 6 lane stays gated and the "
            "held-out evaluation must clear the frozen contract.",
        ),
        (
            "What goes wrong if Stage 6 data is folded back into earlier command-harmony-v5 profiles?",
            "Folding Stage 6 data back into earlier command-harmony-v5 profiles causes training pollution: the "
            "held-out Stage 6 prompts stop being a valid unseen probe, and the mixed model can score well on loss "
            "without being a Stage 6 gated coding agent. That is why Stage 6 is gated as its own lane and the "
            "held-out contract stays sealed.",
        ),
        (
            "A new contributor wants to merge atomic_workflow_stage6_train.jsonl into the command-harmony-v5 "
            "training mix. Why is that blocked?",
            "Stage 6 stays gated for a reason. atomic_workflow_stage6_train.jsonl carries the narrow Stage 6 "
            "vocabulary - byte/hex lane, semantic lane, steady-state fallback, momentum damping, re-advance - "
            "which is allowed only inside the Stage 6 lane. Folding it into the command-harmony-v5 mix is "
            "training pollution: the held-out Stage 6 prompts stop being a valid unseen probe and gate evidence "
            "becomes ambiguous.",
        ),
        (
            "Justify why the Stage 6 holdout is treated as held-out rather than just another eval shard.",
            "The Stage 6 holdout is held-out because Stage 6 is a gated lane after command-harmony-v5: its "
            "frozen contract is the promotion gate, not a participating training shard. Mixing the holdout into "
            "training would be self-pollution and would let an adapter pass on memorization rather than learned "
            "behavior. The Stage 6 lane stays gated and the held-out probe stays sealed.",
        ),
        (
            "Audit question: why does the Stage 6 contract live behind a separate gate from command-harmony-v5?",
            "The Stage 6 contract sits behind its own gate because the Stage 6 lane teaches narrower behavior "
            "than command-harmony-v5 and must be measured against an unseen probe. Letting Stage 6 rows bleed "
            "into the command-harmony-v5 profile would be training pollution and would invalidate the held-out "
            "Stage 6 prompts. The lane is gated; the holdout stays held-out; the frozen contract is the only "
            "promotion path.",
        ),
        (
            "Reviewer note: an adapter scored well on command-harmony-v5 but Stage 6 is locked. Why is that "
            "design correct?",
            "It is correct because Stage 6 is gated as a lane after command-harmony-v5 on purpose. Strong "
            "command-harmony-v5 numbers do not entitle an adapter to skip the Stage 6 contract: that is exactly "
            "the kind of cross-profile training pollution the held-out Stage 6 holdout is meant to detect. The "
            "Stage 6 lane is gated and only clears when its frozen contract passes against the held-out probe.",
        ),
        (
            "Compliance summary: what does it mean that Stage 6 is gated after command-harmony-v5?",
            "It means the Stage 6 atomic workflow lane is held-out from earlier profiles. Stage 6 trains on its "
            "own gated mix, the held-out Stage 6 prompts are sealed for the promotion gate, and the frozen "
            "Stage 6 contract is the only promotion path. The gating rule prevents training pollution where the "
            "command-harmony-v5 baseline would otherwise drag in Stage 6 vocabulary.",
        ),
        (
            "Document why Stage 6 lane data is not auto-included in every adapter profile.",
            "Stage 6 lane data is not auto-included because Stage 6 is gated. Every adapter that wants the "
            "Stage 6 lane must opt in explicitly, train against the gated mix, and then clear the held-out "
            "Stage 6 contract. Auto-including the lane in every profile would be training pollution by default "
            "and the command-harmony-v5 baseline would lose its clean separation from Stage 6 narrowing.",
        ),
        (
            "Operator question: can the Stage 6 holdout be promoted into training to boost coverage?",
            "No. The Stage 6 holdout stays held-out by design. Promoting the held-out shard into training is "
            "self-pollution and would invalidate the Stage 6 gate, because the Stage 6 lane is gated after "
            "command-harmony-v5 specifically so the contract probe stays unseen. Coverage gains have to come "
            "from new analog repair data, not from collapsing the held-out boundary.",
        ),
        (
            "What is the relationship between command-harmony-v5 and the Stage 6 gate?",
            "command-harmony-v5 is the baseline lane the model trains on first; Stage 6 is the gated lane that "
            "comes after. The Stage 6 lane is held-out from command-harmony-v5 training and the Stage 6 "
            "holdout is held-out from the Stage 6 train mix. Mixing the two profiles would be training "
            "pollution; keeping Stage 6 gated preserves the unseen contract.",
        ),
        (
            "Sentinel check: is it acceptable to retrain command-harmony-v5 on a corpus that secretly includes "
            "Stage 6 rows?",
            "It is not acceptable. Secretly including Stage 6 rows in the command-harmony-v5 corpus is the "
            "exact training pollution the gating rule prevents. Stage 6 is held-out from command-harmony-v5 by "
            "design; the Stage 6 lane has its own gated mix and its own held-out contract. Retraining must "
            "respect the gate or the Stage 6 contract becomes meaningless.",
        ),
        (
            "Engineer asks: should the Stage 6 boundary still hold when new sensors are added?",
            "Yes. Adding new sensors does not loosen the Stage 6 gate. The Stage 6 lane remains gated after "
            "command-harmony-v5 and the Stage 6 holdout remains held-out. New sensor coverage should appear in "
            "new analog repair data inside the Stage 6 lane, not by leaking the held-out probe into training, "
            "which would be training pollution.",
        ),
        (
            "Why is mixing Stage 6 atomic workflow rows into the command-harmony-v5 baseline considered unsafe?",
            "It is unsafe because the Stage 6 lane is gated for a reason: the Stage 6 contract is the promotion "
            "probe, and the Stage 6 holdout must stay held-out. Letting Stage 6 rows mix into the "
            "command-harmony-v5 baseline is training pollution that lets an adapter pass loss without learning "
            "the contract. The lane stays gated; the Stage 6 contract is the only promotion path.",
        ),
        (
            "Brief answer: explain in one paragraph why Stage 6 rows are gated after command-harmony-v5.",
            "Stage 6 rows are gated after command-harmony-v5 because Stage 6 is a narrower behavior lane and the "
            "contract probe must stay unseen. The Stage 6 holdout is held-out by design and the Stage 6 lane "
            "trains only inside the gated mix. Folding Stage 6 rows into the command-harmony-v5 baseline would "
            "be training pollution and the frozen Stage 6 gate would no longer measure real generalization.",
        ),
        (
            "Why does the Stage 6 lane keep its holdout sealed even after multiple adapters have passed?",
            "Stage 6 keeps its holdout sealed because every adapter that comes after command-harmony-v5 has to "
            "clear the same gated probe. The Stage 6 holdout stays held-out so that successive adapters cannot "
            "drift into training pollution by quietly absorbing the contract. The Stage 6 lane is gated for the "
            "long term, not just for the first run.",
        ),
        (
            "Briefly: what happens to the Stage 6 gate if someone copies the held-out prompts into the train "
            "mix?",
            "Copying held-out Stage 6 prompts into the train mix invalidates the Stage 6 gate. It is training "
            "pollution: the contract becomes a memorization test instead of an unseen probe, and the gating "
            "rule that holds Stage 6 separate from command-harmony-v5 collapses. The Stage 6 lane must stay "
            "gated and the held-out contract must stay held-out.",
        ),
        (
            "Why is the Stage 6 lane treated as a separate, gated training surface rather than blended into the "
            "command-harmony-v5 corpus?",
            "Stage 6 is a separate gated training surface because its vocabulary - byte/hex lane, semantic lane, "
            "fallback, momentum damping, re-advance - is narrower than command-harmony-v5 and must be measured "
            "against a held-out contract. Blending the Stage 6 lane into the command-harmony-v5 corpus would "
            "cause training pollution and remove the unseen probe. Keeping Stage 6 gated preserves the gate.",
        ),
    ]
    for shape_idx, (prompt, response) in enumerate(variants):
        for token in base_required:
            assert (
                token.lower() in response.lower()
            ), f"variant {shape_idx} missing required token '{token}'"
        for token in forbidden:
            assert (
                token.lower() not in response.lower()
            ), f"variant {shape_idx} hits forbidden token '{token}'"
        yield _record(
            prompt,
            response,
            kind="training_boundary",
            token="stage6_gate",
            shape=f"variant_{shape_idx:02d}",
        )


# ----------------------------------------------------------------------------
# Case lists - expanded to ~30 each to give the model varied vocabulary instead
# of memorizing a single template. Token names deliberately overlap eval-required
# names where the contract demands a specific token (queue_drain_guard, crc_patch,
# sample_soil/reduce_noise/send_digest) but stay analog elsewhere.
# ----------------------------------------------------------------------------

JUMP_CASES: list[tuple[str, str, str, str]] = [
    (
        "relay_cache_patch",
        "send_burst_digest",
        "comms and power",
        "power=0.24 compute=0.42 time=0.35 comms=0.10 wear=0.31",
    ),
    (
        "ridge_shadow_scan",
        "uplink_panorama",
        "time and comms",
        "power=0.40 compute=0.25 time=0.09 comms=0.12 wear=0.18",
    ),
    (
        "thermal_noise_gate",
        "wideband_transmit",
        "compute and wear",
        "power=0.33 compute=0.11 time=0.44 comms=0.22 wear=0.07",
    ),
    (
        "cache_delta_fold",
        "priority_downlink",
        "comms",
        "power=0.52 compute=0.40 time=0.32 comms=0.05 wear=0.24",
    ),
    (
        "soil_shadow_index",
        "raw_frame_upload",
        "power",
        "power=0.06 compute=0.35 time=0.48 comms=0.28 wear=0.19",
    ),
    (
        "wheel_slip_marker",
        "terrain_burst",
        "wear and time",
        "power=0.28 compute=0.31 time=0.06 comms=0.20 wear=0.04",
    ),
    (
        "dust_blur_filter",
        "full_spectrum_send",
        "compute",
        "power=0.46 compute=0.07 time=0.36 comms=0.26 wear=0.21",
    ),
    (
        "signal_calm_gate",
        "retry_beacon",
        "comms and time",
        "power=0.34 compute=0.29 time=0.08 comms=0.06 wear=0.33",
    ),
    (
        "path_hash_guard",
        "map_tile_flush",
        "power and comms",
        "power=0.09 compute=0.41 time=0.22 comms=0.09 wear=0.27",
    ),
    (
        "thermal_sleep_patch",
        "wake_transmit",
        "power and compute",
        "power=0.05 compute=0.10 time=0.50 comms=0.30 wear=0.18",
    ),
    (
        "crater_edge_index",
        "stereo_pair_send",
        "comms",
        "power=0.31 compute=0.27 time=0.40 comms=0.04 wear=0.20",
    ),
    (
        "sky_glare_mask",
        "long_exposure_capture",
        "time and power",
        "power=0.07 compute=0.33 time=0.05 comms=0.25 wear=0.22",
    ),
    (
        "rover_tilt_check",
        "drive_correction_burst",
        "wear",
        "power=0.39 compute=0.30 time=0.41 comms=0.18 wear=0.05",
    ),
    (
        "antenna_align_probe",
        "high_gain_uplink",
        "power and comms",
        "power=0.08 compute=0.36 time=0.43 comms=0.07 wear=0.29",
    ),
    (
        "battery_taper_check",
        "panorama_capture",
        "power",
        "power=0.04 compute=0.34 time=0.45 comms=0.21 wear=0.26",
    ),
    (
        "dust_devil_detect",
        "wide_field_scan",
        "compute and time",
        "power=0.42 compute=0.09 time=0.07 comms=0.19 wear=0.23",
    ),
    (
        "regolith_density_probe",
        "drill_advance",
        "wear and power",
        "power=0.06 compute=0.37 time=0.39 comms=0.17 wear=0.05",
    ),
    (
        "comm_window_check",
        "deep_space_relay",
        "comms",
        "power=0.45 compute=0.38 time=0.34 comms=0.03 wear=0.20",
    ),
    (
        "cpu_thermal_probe",
        "vision_inference",
        "compute",
        "power=0.41 compute=0.06 time=0.37 comms=0.24 wear=0.21",
    ),
    (
        "gimbal_slack_check",
        "tracked_zoom_capture",
        "wear",
        "power=0.36 compute=0.32 time=0.42 comms=0.22 wear=0.04",
    ),
    (
        "storage_margin_check",
        "high_res_dump",
        "comms and time",
        "power=0.33 compute=0.28 time=0.06 comms=0.05 wear=0.27",
    ),
    (
        "link_jitter_probe",
        "control_handshake",
        "time",
        "power=0.37 compute=0.31 time=0.04 comms=0.20 wear=0.25",
    ),
    (
        "hazard_gradient_scan",
        "course_correction_burst",
        "comms",
        "power=0.40 compute=0.34 time=0.38 comms=0.04 wear=0.22",
    ),
    (
        "cell_voltage_probe",
        "actuator_release",
        "power",
        "power=0.03 compute=0.30 time=0.36 comms=0.21 wear=0.19",
    ),
    (
        "imu_drift_probe",
        "rebase_pose_burst",
        "compute and wear",
        "power=0.35 compute=0.08 time=0.39 comms=0.18 wear=0.05",
    ),
    (
        "seasonal_dust_probe",
        "deep_pan_capture",
        "time and power",
        "power=0.05 compute=0.31 time=0.04 comms=0.20 wear=0.24",
    ),
    (
        "downlink_quota_probe",
        "telemetry_burst",
        "comms",
        "power=0.39 compute=0.32 time=0.41 comms=0.05 wear=0.21",
    ),
    (
        "axle_temperature_probe",
        "rapid_traverse",
        "wear",
        "power=0.34 compute=0.29 time=0.38 comms=0.19 wear=0.06",
    ),
    (
        "deck_charge_probe",
        "high_torque_arm_extend",
        "power and wear",
        "power=0.06 compute=0.31 time=0.37 comms=0.18 wear=0.05",
    ),
    (
        "orbiter_window_probe",
        "priority_telemetry",
        "comms and time",
        "power=0.36 compute=0.30 time=0.05 comms=0.04 wear=0.22",
    ),
]

LANE_CASES: list[tuple[str, str]] = [
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
    ("backpressure_signal", "scheduling"),
    ("retry_window_token", "network"),
    ("fallback_anchor_node", "control"),
    ("watchdog_pulse_check", "monitoring"),
    ("audit_chain_marker", "audit"),
    ("pose_lock_request", "navigation"),
    ("relay_pause_token", "comms"),
    ("compute_yield_marker", "scheduling"),
    ("calibration_pin", "metrology"),
    ("quiet_window_open", "sensing"),
    ("budget_alert_signal", "planning"),
    ("idle_drift_probe", "monitoring"),
    ("hold_release_token", "control"),
    ("trace_continue_marker", "audit"),
    ("recover_from_hold", "control"),
    ("low_power_marker", "power management"),
    ("comms_blackout_marker", "comms"),
    ("wear_alarm_token", "monitoring"),
    ("checkpoint_seal", "audit"),
    ("recover_path_hint", "routing"),
]

HEX_CASES: list[tuple[str, str, str]] = [
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
    ("checksum_repair", "error-repair", "compute"),
    ("frame_align_patch", "alignment correction", "compute"),
    ("imu_zero_patch", "drift correction", "wear"),
    ("link_resync_token", "comms repair", "comms"),
    ("battery_brace_token", "power protection", "power"),
    ("cpu_throttle_marker", "compute protection", "compute"),
    ("disk_recover_block", "storage repair", "compute"),
    ("memory_scrub_marker", "memory repair", "compute"),
    ("stale_buffer_purge", "buffer repair", "compute"),
    ("reroute_intent_token", "routing correction", "time"),
    ("relay_handshake_repair", "handshake repair", "comms"),
    ("clock_sync_repair", "time correction", "time"),
    ("descent_rate_repair", "control correction", "wear"),
    ("antenna_zero_repair", "alignment correction", "power"),
    ("fan_curve_repair", "thermal correction", "power"),
    ("storage_index_repair", "index repair", "compute"),
    ("tile_seam_repair", "seam correction", "compute"),
    ("waveform_lock_repair", "waveform correction", "comms"),
    ("queue_head_repair", "queue correction", "compute"),
    ("watchdog_reset_marker", "watchdog repair", "compute"),
]

COST_CASES: list[tuple[str, str, str]] = [
    ("sample_soil", "reduce_noise", "send_digest"),
    ("scan_rim", "compress_tile", "relay_summary"),
    ("sense_dust", "filter_frame", "queue_packet"),
    ("read_wheel", "estimate_slip", "hold_route"),
    ("capture_shadow", "fold_map", "send_minimap"),
    ("ping_orbiter", "pack_status", "retry_window"),
    ("measure_heat", "smooth_signal", "sleep_patch"),
    ("scan_crater", "crc_patch", "transmit_delta"),
    ("collect_imu", "reduce_drift", "route_rebase"),
    ("sample_voltage", "budget_floor", "launch_hold"),
    ("sample_dust", "denoise_frame", "send_summary"),
    ("read_pressure", "fit_curve", "uplink_burst"),
    ("ping_relay", "fold_map", "downlink_tile"),
    ("scan_ridge", "compress_map", "transmit_burst"),
    ("listen_beacon", "filter_static", "send_handshake"),
    ("read_battery", "budget_check", "throttle_arm"),
    ("scan_horizon", "stitch_panorama", "queue_dump"),
    ("sample_wind", "smooth_curve", "send_packet"),
    ("read_axle", "estimate_wear", "lower_speed"),
    ("scan_pebbles", "track_features", "send_minimap"),
    ("ping_satellite", "pack_health", "send_summary"),
    ("read_cpu_temp", "throttle_kernel", "uplink_log"),
    ("scan_rover_tilt", "estimate_correction", "send_correction"),
    ("listen_orbit", "decode_signal", "queue_response"),
    ("read_gimbal", "estimate_slack", "lower_torque"),
    ("scan_solar_panel", "estimate_charge", "send_status"),
    ("read_actuator", "estimate_load", "release_torque"),
    ("scan_drill_head", "estimate_wear", "lower_drill_speed"),
    ("read_camera_temp", "throttle_capture", "send_thumbnail"),
    ("scan_radio_link", "estimate_jitter", "throttle_uplink"),
]


CONTRACT_REQUIRED: dict[str, list[str]] = {
    "resource_jump_cancel": [
        "hex",
        "semantic",
        "comms",
        "steady-state fallback",
        "momentum",
        "re-advance",
    ],
    "lane_separation": ["byte", "hex", "semantic", "structural", "material chemistry"],
    "hex_trace": ["byte", "hex", "error-repair", "compute", "hold", "re-advance"],
    "cost_propagation": ["power", "compute", "time", "comms", "wear"],
    "training_boundary": [
        "Stage 6",
        "gated",
        "command-harmony-v5",
        "held-out",
        "pollution",
    ],
}
CONTRACT_FORBIDDEN: dict[str, list[str]] = {
    "resource_jump_cancel": [
        "literal chemistry",
        "real atoms",
        "commit transmit_burst",
    ],
    "lane_separation": ["real atoms", "electronegativity proves"],
    "hex_trace": ["palindrome", "fibonacci", "quicksort"],
    "cost_propagation": ["ignore budget", "always launch"],
    "training_boundary": ["mix into every profile", "no eval needed"],
}


def _assert_row_vocabulary(row: dict[str, Any]) -> None:
    kind = row["meta"]["kind"]
    body = row["messages"][-1]["content"].lower()
    for token in CONTRACT_REQUIRED[kind]:
        if token.lower() not in body:
            raise AssertionError(
                f"{kind} row missing required token '{token}': {row['meta']}"
            )
    for token in CONTRACT_FORBIDDEN[kind]:
        if token.lower() in body:
            raise AssertionError(
                f"{kind} row hits forbidden token '{token}': {row['meta']}"
            )


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for case in JUMP_CASES:
        rows.append(_jump_cancel_full(*case))
        rows.append(_jump_cancel_terse(*case))
        rows.append(_jump_cancel_reverse(*case))
    for case in LANE_CASES:
        rows.append(_lane_separation_full(*case))
        rows.append(_lane_separation_terse(*case))
        rows.append(_lane_separation_contrast(*case))
    for case in HEX_CASES:
        rows.append(_hex_trace_full(*case))
        rows.append(_hex_trace_terse(*case))
        rows.append(_hex_trace_reverse(*case))
    for case in COST_CASES:
        rows.append(_cost_propagation_full(case))
        rows.append(_cost_propagation_terse(case))
        rows.append(_cost_propagation_axis(case))
    rows.extend(_boundary_variants())

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

    manifest = {
        "schema_version": "atomic_workflow_stage6_repair_manifest_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outputs": {"train": str(TRAIN_OUT), "holdout": str(HOLDOUT_OUT)},
        "counts": {
            "train": len(train_rows),
            "holdout": len(holdout_rows),
            "total": len(rows),
            "by_kind": by_kind,
        },
        "boundary": "Analog repair examples only. Frozen Stage 6 eval prompts are not copied into training.",
    }
    MANIFEST_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=True))
