from __future__ import annotations

"""Triadic affirm/counter/judge decision test over six explicit evidence axes."""

import argparse
import hashlib
import json
import math
import os
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch
import torch.nn as nn
import torch.nn.functional as F

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import multiview_perspective_reasoning as BASE  # noqa: E402


DEFAULT_OUTPUT = Path("artifacts") / "triadic_evidence_reasoning_20261021"
ROLE_BETA = 3.0


@dataclass(frozen=True)
class Arm:
    name: str
    feature_mode: str
    role_supervision: bool


ARMS = (
    Arm("aligned_triadic_role", "aligned", True),
    Arm("aligned_triadic_free", "aligned", False),
    Arm("ordinary_triadic_role", "ordinary", True),
    Arm("shuffled_triadic_role", "shuffled", True),
    Arm("random_triadic_role", "random", True),
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_state_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        tensor = value.detach().contiguous().cpu()
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


class TriadicPerspectiveNet(nn.Module):
    """Six transport nodes followed by affirm, counter, and judge heads."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(BASE.INPUT_DIM, 96),
            nn.GELU(),
            nn.Linear(96, BASE.CORE_DIM + BASE.RESIDUAL_DIM),
        )
        self.base_query = nn.Parameter(torch.zeros(1, 1, BASE.CORE_DIM))
        self.form_attention = nn.MultiheadAttention(BASE.CORE_DIM, 4, batch_first=True)
        self.lane_head = nn.Linear(BASE.RESIDUAL_DIM, len(BASE.TONGUES))
        self.bit_head = nn.Linear(BASE.CORE_DIM, 6)
        self.op_embedding = nn.Embedding(len(BASE.OP_DELTAS), 16)
        self.transition = nn.Sequential(
            nn.Linear(BASE.CORE_DIM + 16, 64),
            nn.GELU(),
            nn.Linear(64, BASE.CORE_DIM),
        )

        # One scale per explicit evidence axis. Positive and negative scales are
        # both allowed; the two role heads read opposite sides of the resulting
        # contribution. The judge sees both, their difference, and their overlap.
        self.axis_scale = nn.Parameter(torch.ones(BASE.N_LENSES))
        self.judge_head = nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 3))

    def encode(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encoder(values)
        return F.normalize(encoded[..., : BASE.CORE_DIM], dim=-1), encoded[..., BASE.CORE_DIM :]

    def attend(
        self, forms: torch.Tensor, need_weights: bool = False
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        query = self.base_query.expand(forms.shape[0], -1, -1)
        value, weights = self.form_attention(
            query,
            forms,
            forms,
            need_weights=need_weights,
            average_attn_weights=False,
        )
        return F.normalize(value[:, 0], dim=-1), weights if need_weights else None

    def prototypes(self, cores: torch.Tensor) -> torch.Tensor:
        value, _ = self.attend(cores)
        return value

    def step(self, core: torch.Tensor, operation: torch.Tensor) -> torch.Tensor:
        delta = self.transition(torch.cat([core, self.op_embedding(operation)], dim=-1))
        return F.normalize(core + delta, dim=-1)

    def decision(
        self,
        core: torch.Tensor,
        omitted_axis: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        signed = 2.0 * torch.sigmoid(self.bit_head(core)) - 1.0
        contribution = signed * self.axis_scale
        mask = torch.ones_like(contribution)
        if omitted_axis is not None:
            mask.scatter_(1, omitted_axis[:, None], 0.0)
        contribution = contribution * mask

        # softplus(x) - softplus(-x) == x. The two role heads can overlap near
        # zero (uncertainty), while their difference retains the signed evidence.
        affirm = F.softplus(ROLE_BETA * contribution) / ROLE_BETA * mask
        counter = F.softplus(-ROLE_BETA * contribution) / ROLE_BETA * mask
        overlap = torch.minimum(affirm, counter)
        affirm_total = affirm.sum(dim=-1)
        counter_total = counter.sum(dim=-1)
        margin = affirm_total - counter_total
        total = affirm_total + counter_total
        active = mask.sum(dim=-1).clamp_min(1.0)
        confidence = (signed.abs() * mask).sum(dim=-1) / active
        ratio = margin / total.clamp_min(1e-6)
        features = torch.stack(
            (
                affirm_total,
                counter_total,
                margin,
                total,
                overlap.sum(dim=-1),
                margin.abs(),
                confidence,
                ratio,
            ),
            dim=-1,
        )
        return self.judge_head(features), {
            "signed": signed,
            "contribution": contribution,
            "affirm": affirm,
            "counter": counter,
            "overlap": overlap,
            "features": features,
        }


def tensor_rows(
    rows: Sequence[tuple[int, int, int]], device: torch.device
) -> tuple[torch.Tensor, ...]:
    return tuple(torch.tensor([row[index] for row in rows], device=device) for index in range(3))


def true_contributions(states: torch.Tensor) -> torch.Tensor:
    values = [
        [weight * bit for weight, bit in zip(BASE.TRUTH_WEIGHTS, BASE.signed_bits(int(state)))]
        for state in states
    ]
    return torch.tensor(values, dtype=torch.float32, device=states.device)


def train_arm(
    arm: Arm,
    seed: int,
    steps: int,
    device: torch.device,
    trace_every: int = 100,
) -> tuple[TriadicPerspectiveNet, list[dict[str, float]]]:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    features = BASE.build_features(arm.feature_mode).to(device)
    model = TriadicPerspectiveNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    train_rows, _ = BASE.transition_split()
    starts, operations, targets = tensor_rows(train_rows, device)
    inverse = BASE.INVERSE_INDEX.to(device)[operations]
    lane_targets = torch.arange(len(BASE.TONGUES), device=device).repeat(BASE.N_STATES)
    bits = torch.tensor(
        [BASE.state_bits(state) for state in range(BASE.N_STATES)],
        dtype=torch.float32,
        device=device,
    )
    semantic_train = torch.tensor(
        [state for state in range(BASE.N_STATES) if state not in BASE.SEMANTIC_TEST_STATES],
        device=device,
    )
    truth_targets = torch.tensor(
        [BASE.truth_for(int(state)) + 1 for state in semantic_train], device=device
    )
    semantic_states = semantic_train.repeat_interleave(BASE.N_LENSES)
    semantic_lenses = torch.arange(BASE.N_LENSES, device=device).repeat(len(semantic_train))
    stance_targets = torch.tensor(
        [
            BASE.lens_stance(int(state), int(lens)) + 1
            for state, lens in zip(semantic_states, semantic_lenses)
        ],
        device=device,
    )
    target_contribution = true_contributions(semantic_train)
    trace: list[dict[str, float]] = []

    for step in range(steps):
        optimizer.zero_grad(set_to_none=True)
        cores, residual = model.encode(features)
        proto = model.prototypes(cores)
        loss_identity = BASE.identity_loss(cores)
        loss_lane = F.cross_entropy(
            model.lane_head(residual.reshape(-1, BASE.RESIDUAL_DIM)), lane_targets
        )
        loss_bits = F.binary_cross_entropy_with_logits(model.bit_head(proto), bits)
        predicted = model.step(proto[starts], operations)
        loss_transition = F.cross_entropy(predicted @ proto.T / 0.09, targets)
        returned = model.step(predicted, inverse)
        loss_cycle = F.cross_entropy(returned @ proto.T / 0.09, starts)
        truth_logits, truth_receipt = model.decision(proto[semantic_train])
        loss_truth = F.cross_entropy(truth_logits, truth_targets)
        stance_logits, _ = model.decision(proto[semantic_states], semantic_lenses)
        loss_stance = F.cross_entropy(stance_logits, stance_targets)
        loss_role = F.smooth_l1_loss(
            truth_receipt["contribution"] / 3.0, target_contribution / 3.0
        )
        loss = (
            loss_identity
            + 0.25 * loss_lane
            + 0.25 * loss_bits
            + loss_transition
            + 0.65 * loss_cycle
            + 0.70 * loss_truth
            + 0.90 * loss_stance
        )
        if arm.role_supervision:
            loss = loss + 0.80 * loss_role
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss for {arm.name} seed {seed} step {step}")
        loss.backward()
        for name, parameter in model.named_parameters():
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                raise RuntimeError(f"non-finite gradient {name} for {arm.name} seed {seed}")
        optimizer.step()
        if step == 0 or (step + 1) % trace_every == 0 or step + 1 == steps:
            trace.append(
                {
                    "step": step + 1,
                    "loss": float(loss.detach().cpu()),
                    "identity": float(loss_identity.detach().cpu()),
                    "lane": float(loss_lane.detach().cpu()),
                    "bits": float(loss_bits.detach().cpu()),
                    "transition": float(loss_transition.detach().cpu()),
                    "cycle": float(loss_cycle.detach().cpu()),
                    "truth": float(loss_truth.detach().cpu()),
                    "stance": float(loss_stance.detach().cpu()),
                    "role": float(loss_role.detach().cpu()),
                }
            )
    return model, trace


def accuracy(prediction: torch.Tensor, target: torch.Tensor) -> float:
    return float((prediction == target).float().mean().cpu()) if len(target) else 0.0


def roll(
    model: TriadicPerspectiveNet, start: torch.Tensor, operations: Sequence[int]
) -> torch.Tensor:
    state = start
    for operation in operations:
        op = torch.full((state.shape[0],), operation, dtype=torch.long, device=state.device)
        state = model.step(state, op)
    return state


def semantic_metrics(
    model: TriadicPerspectiveNet,
    proto: torch.Tensor,
    states: Sequence[int],
    device: torch.device,
) -> dict[str, float]:
    state_tensor = torch.tensor(states, device=device)
    truth_target = torch.tensor([BASE.truth_for(state) + 1 for state in states], device=device)
    truth_logits, receipt = model.decision(proto[state_tensor])
    truth_prediction = truth_logits.argmax(-1)
    repeated_states = state_tensor.repeat_interleave(BASE.N_LENSES)
    lenses = torch.arange(BASE.N_LENSES, device=device).repeat(len(states))
    stance_logits, _ = model.decision(proto[repeated_states], lenses)
    stance_prediction = stance_logits.argmax(-1)
    stance_target = torch.tensor(
        [
            BASE.lens_stance(int(state), int(lens)) + 1
            for state, lens in zip(repeated_states, lenses)
        ],
        device=device,
    )
    repeated_truth = truth_prediction.repeat_interleave(BASE.N_LENSES)
    reason_prediction = torch.where(
        stance_prediction != repeated_truth, lenses, torch.full_like(lenses, 6)
    )
    reason_target = torch.tensor(
        [
            BASE.disagreement_reason(int(state), int(lens))
            for state, lens in zip(repeated_states, lenses)
        ],
        device=device,
    )
    disagreement = reason_target != 6
    stance_matrix = stance_prediction.view(len(states), BASE.N_LENSES)
    stance_target_matrix = stance_target.view(len(states), BASE.N_LENSES)
    minority_mask_values = []
    for state in states:
        values = [BASE.lens_stance(state, lens) for lens in range(BASE.N_LENSES)]
        dominant = BASE.majority(values)
        minority_mask_values.extend(value != dominant for value in values)
    minority_mask = torch.tensor(minority_mask_values, device=device)
    target_contribution = true_contributions(state_tensor)
    predicted_contribution = receipt["contribution"]
    contribution_sign = accuracy(
        torch.sign(predicted_contribution).long(), torch.sign(target_contribution).long()
    )
    contribution_mae = float(
        (predicted_contribution - target_contribution).abs().mean().cpu()
    )
    return {
        "truth": accuracy(truth_prediction, truth_target),
        "stance": accuracy(stance_prediction, stance_target),
        "reason": accuracy(reason_prediction[disagreement], reason_target[disagreement]),
        "vector_exact": float(
            (stance_matrix == stance_target_matrix).all(dim=1).float().mean().cpu()
        ),
        "minority": accuracy(stance_prediction[minority_mask], stance_target[minority_mask]),
        "contribution_sign": contribution_sign,
        "contribution_mae": contribution_mae,
    }


def decision_snapshot(
    model: TriadicPerspectiveNet,
    features: torch.Tensor,
    proto: torch.Tensor,
) -> dict[str, object]:
    cores, residual = model.encode(features)
    _, form_attention = model.attend(cores, need_weights=True)
    events: dict[str, object] = {}
    for state in (1, 6, 19, 32):
        truth_logits, receipt = model.decision(proto[state : state + 1])
        lenses = torch.arange(BASE.N_LENSES, device=features.device)
        lens_logits, lens_receipt = model.decision(
            proto[state : state + 1].expand(BASE.N_LENSES, -1), lenses
        )
        truth_prediction = int(truth_logits.argmax(-1).item())
        stance_prediction = lens_logits.argmax(-1)
        reason_prediction = torch.where(
            stance_prediction != truth_prediction, lenses, torch.full_like(lenses, 6)
        )
        events[str(state)] = {
            "truth": BASE.truth_for(state),
            "stances": [BASE.lens_stance(state, lens) for lens in range(BASE.N_LENSES)],
            "form_attention_by_head": form_attention[state, :, 0].detach().cpu().tolist(),
            "lane_predictions": model.lane_head(residual[state]).argmax(-1).detach().cpu().tolist(),
            "signed_coordinates": receipt["signed"][0].detach().cpu().tolist(),
            "contributions": receipt["contribution"][0].detach().cpu().tolist(),
            "affirm": receipt["affirm"][0].detach().cpu().tolist(),
            "counter": receipt["counter"][0].detach().cpu().tolist(),
            "overlap": receipt["overlap"][0].detach().cpu().tolist(),
            "judge_features": receipt["features"][0].detach().cpu().tolist(),
            "truth_probabilities": F.softmax(truth_logits, dim=-1)[0].detach().cpu().tolist(),
            "lens_probabilities": F.softmax(lens_logits, dim=-1).detach().cpu().tolist(),
            "reason_predictions": reason_prediction.detach().cpu().tolist(),
            "lens_margins": lens_receipt["features"][:, 2].detach().cpu().tolist(),
        }
    return {"axis_scale": model.axis_scale.detach().cpu().tolist(), "events": events}


@torch.no_grad()
def evaluate(
    model: TriadicPerspectiveNet, arm: Arm, seed: int, device: torch.device
) -> dict[str, object]:
    model.eval()
    features = BASE.build_features(arm.feature_mode).to(device)
    cores, residual = model.encode(features)
    proto = model.prototypes(cores)
    labels = torch.arange(BASE.N_STATES, device=device)
    summed = cores.sum(dim=1)
    identity_hits = []
    for lane in range(len(BASE.TONGUES)):
        other = F.normalize((summed - cores[:, lane]) / (len(BASE.TONGUES) - 1), dim=-1)
        identity_hits.append((cores[:, lane] @ other.T).argmax(-1))
    identity_prediction = torch.stack(identity_hits, dim=1)
    lane_prediction = model.lane_head(residual.reshape(-1, BASE.RESIDUAL_DIM)).argmax(-1)
    lane_target = torch.arange(len(BASE.TONGUES), device=device).repeat(BASE.N_STATES)
    bit_prediction = (torch.sigmoid(model.bit_head(proto)) >= 0.5).long()
    bit_target = torch.tensor(
        [BASE.state_bits(state) for state in range(BASE.N_STATES)], device=device
    )

    _, test_rows = BASE.transition_split()
    starts, operations, targets = tensor_rows(test_rows, device)
    predicted = model.step(proto[starts], operations)
    predicted_state = (predicted @ proto.T).argmax(-1)
    positive = torch.tensor(
        [BASE.OP_DELTAS[int(operation)] > 0 for operation in operations], device=device
    )
    returned = model.step(predicted, BASE.INVERSE_INDEX.to(device)[operations])
    path_forward = path_backward = rollback = postrollback = 0
    paths = BASE.deterministic_paths()
    for start_value, path in paths:
        current = proto[start_value : start_value + 1]
        end = roll(model, current, path)
        expected = BASE.path_target(start_value, path)
        path_forward += int((end @ proto.T).argmax(-1).item() == expected)
        inverse_path = tuple(int(BASE.INVERSE_INDEX[operation]) for operation in reversed(path))
        back = roll(model, end, inverse_path)
        path_backward += int((back @ proto.T).argmax(-1).item() == start_value)
        displaced = roll(model, current, path[:2])
        recovered = roll(
            model,
            displaced,
            tuple(int(BASE.INVERSE_INDEX[operation]) for operation in reversed(path[:2])),
        )
        rollback += int((recovered @ proto.T).argmax(-1).item() == start_value)
        final = roll(model, recovered, path)
        postrollback += int((final @ proto.T).argmax(-1).item() == expected)

    branch_hits = 0
    rng = random.Random(77123)
    for _ in range(128):
        start_value = rng.randrange(BASE.N_STATES)
        candidates: list[tuple[int, ...]] = []
        endpoints: set[int] = set()
        while len(candidates) < 4:
            candidate = tuple(rng.randrange(len(BASE.OP_DELTAS)) for _ in range(3))
            endpoint = BASE.path_target(start_value, candidate)
            if endpoint not in endpoints:
                endpoints.add(endpoint)
                candidates.append(candidate)
        correct = rng.randrange(4)
        goal = BASE.path_target(start_value, candidates[correct])
        scores = [
            float((roll(model, proto[start_value : start_value + 1], candidate) @ proto[goal]).item())
            for candidate in candidates
        ]
        branch_hits += int(max(range(4), key=lambda index: scores[index]) == correct)

    train_states = [
        state for state in range(BASE.N_STATES) if state not in BASE.SEMANTIC_TEST_STATES
    ]
    heldout_semantic = semantic_metrics(
        model, proto, list(BASE.SEMANTIC_TEST_STATES), device
    )
    train_semantic = semantic_metrics(model, proto, train_states, device)
    metrics = {
        "identity_top1": accuracy(
            identity_prediction, labels[:, None].expand_as(identity_prediction)
        ),
        "lane_residual_accuracy": accuracy(lane_prediction, lane_target),
        "byte_exact": float((bit_prediction == bit_target).all(dim=1).float().mean().cpu()),
        "forward_heldout": accuracy(predicted_state[positive], targets[positive]),
        "backward_heldout": accuracy(predicted_state[~positive], targets[~positive]),
        "cycle_heldout": accuracy((returned @ proto.T).argmax(-1), starts),
        "multistep_forward": path_forward / len(paths),
        "multistep_backward": path_backward / len(paths),
        "parallel_branch_selection": branch_hits / 128,
        "rollback_recovery": rollback / len(paths),
        "postrollback_target": postrollback / len(paths),
        **{f"heldout_{key}": value for key, value in heldout_semantic.items()},
        **{f"train_{key}": value for key, value in train_semantic.items()},
    }
    reasoning_keys = (
        "forward_heldout",
        "backward_heldout",
        "multistep_forward",
        "multistep_backward",
        "parallel_branch_selection",
        "rollback_recovery",
    )
    interpretation_keys = (
        "heldout_truth",
        "heldout_stance",
        "heldout_reason",
        "heldout_minority",
    )
    metrics["reasoning_floor"] = min(metrics[key] for key in reasoning_keys)
    metrics["interpretation_floor"] = min(metrics[key] for key in interpretation_keys)
    metrics["joint_floor"] = min(metrics["reasoning_floor"], metrics["interpretation_floor"])
    return {
        "arm": arm.name,
        "seed": seed,
        "metrics": metrics,
        "decision_snapshot": decision_snapshot(model, features, proto),
    }


def comparison(
    runs: Sequence[dict[str, object]], left: str, right: str, metric: str
) -> dict[str, object]:
    left_rows = {
        int(row["seed"]): float(row["metrics"][metric])
        for row in runs
        if row["arm"] == left
    }
    right_rows = {
        int(row["seed"]): float(row["metrics"][metric])
        for row in runs
        if row["arm"] == right
    }
    seeds = sorted(set(left_rows) & set(right_rows))
    effects = [left_rows[seed] - right_rows[seed] for seed in seeds]
    left_values = [left_rows[seed] for seed in seeds]
    right_values = [right_rows[seed] for seed in seeds]
    pooled = (
        math.sqrt((statistics.variance(left_values) + statistics.variance(right_values)) / 2)
        if len(seeds) > 1
        else math.inf
    )
    mean_effect = statistics.mean(effects) if effects else 0.0
    return {
        "left": left,
        "right": right,
        "metric": metric,
        "seeds": seeds,
        "left_values": left_values,
        "right_values": right_values,
        "paired_effects": effects,
        "mean_effect": mean_effect,
        "two_pooled_sd": 2 * pooled,
        "all_positive": bool(effects) and all(effect > 0 for effect in effects),
        "clears_two_pooled_sd": bool(effects) and mean_effect > 2 * pooled,
    }


def analyze(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    comparisons = {
        "role_vs_free_interpretation": comparison(
            runs, "aligned_triadic_role", "aligned_triadic_free", "interpretation_floor"
        ),
        "aligned_vs_ordinary_interpretation": comparison(
            runs, "aligned_triadic_role", "ordinary_triadic_role", "interpretation_floor"
        ),
        "aligned_vs_shuffled_interpretation": comparison(
            runs, "aligned_triadic_role", "shuffled_triadic_role", "interpretation_floor"
        ),
        "aligned_vs_ordinary_joint": comparison(
            runs, "aligned_triadic_role", "ordinary_triadic_role", "joint_floor"
        ),
        "aligned_vs_shuffled_joint": comparison(
            runs, "aligned_triadic_role", "shuffled_triadic_role", "joint_floor"
        ),
    }
    aligned = [row for row in runs if row["arm"] == "aligned_triadic_role"]
    traceable = all(
        float(row["metrics"][metric]) >= 0.90
        for row in aligned
        for metric in (
            "heldout_truth",
            "heldout_stance",
            "heldout_reason",
            "heldout_minority",
            "heldout_contribution_sign",
        )
    )
    role_comparison = comparisons["role_vs_free_interpretation"]
    role_supported = role_comparison["all_positive"] and role_comparison["clears_two_pooled_sd"]
    tokenizer_specific = all(
        comparisons[name]["all_positive"] and comparisons[name]["clears_two_pooled_sd"]
        for name in (
            "aligned_vs_ordinary_interpretation",
            "aligned_vs_shuffled_interpretation",
            "aligned_vs_ordinary_joint",
            "aligned_vs_shuffled_joint",
        )
    )
    return {
        "comparisons": comparisons,
        "claim_rules": {
            "triadic_traceable_decision_support": traceable,
            "role_supervision_support": role_supported,
            "tokenizer_specific_interpretation_support": tokenizer_specific,
        },
    }


def render_report(receipt: dict[str, object]) -> str:
    lines = [
        "# Triadic evidence decision result",
        "",
        f"Generated: {receipt['created_at']}",
        "",
        "The affirm head reads evidence for a conclusion, the counter head reads opposing evidence,",
        "and the judge sees both totals, their margin, overlap, confidence, and ratio.",
        "",
        "| arm | reasoning | truth | stance | reason | minority | vector | sign | MAE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        rows = [row for row in receipt["runs"] if row["arm"] == arm.name]

        def mean(metric: str) -> float:
            return statistics.mean(float(row["metrics"][metric]) for row in rows)

        lines.append(
            f"| {arm.name} | {mean('reasoning_floor'):.3f} | {mean('heldout_truth'):.3f} | "
            f"{mean('heldout_stance'):.3f} | {mean('heldout_reason'):.3f} | "
            f"{mean('heldout_minority'):.3f} | {mean('heldout_vector_exact'):.3f} | "
            f"{mean('heldout_contribution_sign'):.3f} | {mean('heldout_contribution_mae'):.3f} |"
        )
    lines.extend(["", "## Pre-registered gates", ""])
    for name, passed in receipt["analysis"]["claim_rules"].items():
        lines.append(f"- {name}: **{'PASS' if passed else 'NOT ESTABLISHED'}**")
    return "\n".join(lines) + "\n"


def preflight(output_dir: Path, device: torch.device) -> dict[str, object]:
    started = time.perf_counter()
    determinism = BASE.configure_determinism(device)
    counts = [sum(parameter.numel() for parameter in TriadicPerspectiveNet().parameters()) for _ in ARMS]
    sample = torch.tensor([[2.0, -1.0, 0.0]])
    decomposition_error = float(
        (
            F.softplus(ROLE_BETA * sample) / ROLE_BETA
            - F.softplus(-ROLE_BETA * sample) / ROLE_BETA
            - sample
        )
        .abs()
        .max()
    )
    gradient_checks = {}
    for arm in ARMS:
        model, trace = train_arm(arm, 101, 1, device, trace_every=1)
        gradient_checks[arm.name] = math.isfinite(trace[-1]["loss"])
        del model
    replay_arm = ARMS[0]
    replay_hashes = []
    for _ in range(2):
        model, _ = train_arm(replay_arm, 20261021, 3, device, trace_every=3)
        replay_hashes.append(model_state_sha256(model))
        del model
    result = {
        "schema": "scbe.triadic-evidence-reasoning-preflight.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "determinism": determinism,
        "parameter_counts": counts,
        "all_parameter_matched": len(set(counts)) == 1,
        "softplus_decomposition_max_error": decomposition_error,
        "gradient_checks": gradient_checks,
        "exact_replay": {
            "passed": replay_hashes[0] == replay_hashes[1],
            "state_sha256": replay_hashes,
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    result["passed"] = (
        result["all_parameter_matched"]
        and decomposition_error < 1e-6
        and all(gradient_checks.values())
        and result["exact_replay"]["passed"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "PREFLIGHT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_experiment(
    output_dir: Path, steps: int, seeds: Sequence[int], device: torch.device
) -> dict[str, object]:
    gate = preflight(output_dir, device)
    if not gate["passed"]:
        raise RuntimeError("preflight failed; refusing triadic matrix")
    started = time.perf_counter()
    runs: list[dict[str, object]] = []
    for arm in ARMS:
        for seed in seeds:
            run_started = time.perf_counter()
            model, trace = train_arm(arm, seed, steps, device)
            result = evaluate(model, arm, seed, device)
            result["training_trace"] = trace
            result["parameter_count"] = sum(parameter.numel() for parameter in model.parameters())
            result["state_sha256"] = model_state_sha256(model)
            result["elapsed_seconds"] = time.perf_counter() - run_started
            runs.append(result)
            (output_dir / f"{arm.name}_s{seed}.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
    receipt = {
        "schema": "scbe.triadic-evidence-reasoning.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "seeds": list(seeds),
        "device": str(device),
        "arms": [asdict(arm) for arm in ARMS],
        "preflight_sha256": sha256_file(output_dir / "PREFLIGHT.json"),
        "source": {
            "runner": {"path": str(Path(__file__)), "sha256": sha256_file(Path(__file__))},
            "base_runner": {
                "path": str(Path(BASE.__file__)),
                "sha256": sha256_file(Path(BASE.__file__)),
            },
        },
        "runs": runs,
        "analysis": analyze(runs),
        "elapsed_seconds": time.perf_counter() - started,
        "automatic_promotion": False,
        "provider_spend": 0,
    }
    (output_dir / "RESULTS.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (output_dir / "REPORT.md").write_text(render_report(receipt), encoding="utf-8")
    return receipt


def parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--seeds", type=parse_seeds, default=(11, 23, 37))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "auto":
        device_name = "cpu"
    if device_name == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA requested but unavailable")
    device = torch.device(device_name)
    torch.set_num_threads(max(1, min(torch.get_num_threads(), 4)))
    BASE.configure_determinism(device)
    if args.preflight_only:
        result = preflight(args.output_dir, device)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    receipt = run_experiment(args.output_dir, args.steps, args.seeds, device)
    print(render_report(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
