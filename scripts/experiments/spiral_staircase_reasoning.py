from __future__ import annotations

"""Controlled recursive-realm test for a shared neural "spiral staircase".

An OPEN event applies one reversible operation and enters one landing.  A CLOSE
event returns through the matching door.  Receipt arms receive the exact inverse
operation at CLOSE; the no-receipt control must retain the whole stack in its
recurrent state.  Training uses depths 1..4 and evaluation uses depths 1..12.

The phi schedule is only a bounded routing coordinate.  It does not alter the
target or bypass the learned transition.  Uniform, zero, shuffled-phi, ordinary
byte, and shuffled-codec controls have exactly the same trainable parameters.
"""

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


DEFAULT_OUTPUT = Path("artifacts") / "spiral_staircase_reasoning_20261021"
TRAIN_DEPTHS = (1, 2, 3, 4)
EVAL_DEPTHS = tuple(range(1, 13))
N_ACTIONS = 8
NULL_ACTION = N_ACTIONS
N_REALMS = 3
NULL_REALM = N_REALMS
SCHEDULE_DIM = 6
HIDDEN_DIM = 64

ACTION_NAMES = (
    "add_1",
    "sub_1",
    "add_3",
    "sub_3",
    "xor_1",
    "xor_3",
    "rotate_left",
    "rotate_right",
)
INVERSE_ACTION = torch.tensor((1, 0, 3, 2, 4, 5, 7, 6), dtype=torch.long)
ACTION_REALM = torch.tensor((0, 0, 0, 0, 1, 1, 2, 2), dtype=torch.long)


@dataclass(frozen=True)
class Arm:
    name: str
    feature_mode: str
    receipts: bool
    schedule_mode: str


ARMS = (
    Arm("aligned_receipt_phi", "aligned", True, "phi"),
    Arm("aligned_no_receipt_phi", "aligned", False, "phi"),
    Arm("aligned_receipt_uniform", "aligned", True, "uniform"),
    Arm("aligned_receipt_zero", "aligned", True, "zero"),
    Arm("aligned_receipt_shuffled_phi", "aligned", True, "shuffled_phi"),
    Arm("ordinary_receipt_phi", "ordinary", True, "phi"),
    Arm("shuffled_codec_receipt_phi", "shuffled", True, "phi"),
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


def action_name(action: int) -> str:
    return "receipt_missing" if action == NULL_ACTION else ACTION_NAMES[action]


def apply_action(states: torch.Tensor, actions: torch.Tensor) -> torch.Tensor:
    """Apply one of eight bijections to six-bit states."""
    if states.shape != actions.shape:
        raise ValueError("states and actions must have the same shape")
    if bool(((actions < 0) | (actions >= N_ACTIONS)).any()):
        raise ValueError("a target action must be in 0..7")
    out = states.clone()
    out = torch.where(actions == 0, (states + 1) % BASE.N_STATES, out)
    out = torch.where(actions == 1, (states - 1) % BASE.N_STATES, out)
    out = torch.where(actions == 2, (states + 3) % BASE.N_STATES, out)
    out = torch.where(actions == 3, (states - 3) % BASE.N_STATES, out)
    out = torch.where(actions == 4, states ^ 1, out)
    out = torch.where(actions == 5, states ^ 3, out)
    rotate_left = ((states << 1) & 63) | (states >> 5)
    rotate_right = (states >> 1) | ((states & 1) << 5)
    out = torch.where(actions == 6, rotate_left, out)
    return torch.where(actions == 7, rotate_right, out)


def schedule_features(
    depths: torch.Tensor,
    mode: str,
    *,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Return bounded coordinates for each landing depth."""
    d = depths.to(dtype=dtype)
    if mode == "zero":
        return torch.zeros((*depths.shape, SCHEDULE_DIM), dtype=dtype, device=depths.device)
    if mode == "shuffled_phi":
        # Multiplication by five permutes 1..12 modulo 13.  Matching OPEN and
        # CLOSE events still receive the same coordinate, but depth order is lost.
        d = torch.remainder(d * 5.0, 13.0)
    if mode in {"phi", "shuffled_phi"}:
        phi = (1.0 + math.sqrt(5.0)) / 2.0
        theta = d * (2.0 * math.pi / (phi * phi))
        shell = torch.pow(torch.full_like(d, phi), -d / 8.0)
        height = torch.tanh(d / (phi**3))
    elif mode == "uniform":
        theta = d * (2.0 * math.pi / 13.0)
        shell = 1.0 - d / 13.0
        height = torch.tanh(d / 8.0)
    else:
        raise ValueError(f"unknown schedule mode {mode!r}")
    return torch.stack(
        (torch.sin(theta), torch.cos(theta), torch.sin(2 * theta), torch.cos(2 * theta), shell, height),
        dim=-1,
    )


@dataclass
class RouteBatch:
    starts: torch.Tensor
    input_actions: torch.Tensor
    target_actions: torch.Tensor
    events: torch.Tensor
    realms: torch.Tensor
    depths: torch.Tensor
    schedules: torch.Tensor
    targets: torch.Tensor


def make_route_batch(
    depth: int,
    batch_size: int,
    generator: torch.Generator,
    device: torch.device,
    *,
    receipts: bool,
    schedule_mode: str,
) -> RouteBatch:
    if depth < 1:
        raise ValueError("depth must be positive")
    starts = torch.randint(BASE.N_STATES, (batch_size,), generator=generator)
    opens = torch.randint(N_ACTIONS, (batch_size, depth), generator=generator)
    closes = INVERSE_ACTION[opens.flip(1)]
    target_actions = torch.cat((opens, closes), dim=1).T.contiguous()
    input_actions = target_actions.clone()
    if not receipts:
        input_actions[depth:] = NULL_ACTION
    events = torch.cat((torch.zeros(depth, dtype=torch.long), torch.ones(depth, dtype=torch.long)))
    landing_depths = torch.cat((torch.arange(1, depth + 1), torch.arange(depth, 0, -1)))
    realms = ACTION_REALM[target_actions]
    if not receipts:
        realms[depth:] = NULL_REALM
    current = starts.clone()
    targets = []
    for action in target_actions:
        current = apply_action(current, action)
        targets.append(current)
    target_states = torch.stack(targets)
    schedules = schedule_features(landing_depths, schedule_mode)
    return RouteBatch(
        starts=starts.to(device),
        input_actions=input_actions.to(device),
        target_actions=target_actions.to(device),
        events=events.to(device),
        realms=realms.to(device),
        depths=landing_depths.to(device),
        schedules=schedules.to(device),
        targets=target_states.to(device),
    )


class SpiralStaircaseNet(nn.Module):
    """A shared transition cell wrapped by six exact transport views."""

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
        self.initial_state_head = nn.Linear(BASE.CORE_DIM, BASE.N_STATES)
        self.init_hidden = nn.Linear(BASE.CORE_DIM, HIDDEN_DIM)
        self.event_embedding = nn.Embedding(2, 8)
        self.action_embedding = nn.Embedding(N_ACTIONS + 1, 16)
        self.realm_embedding = nn.Embedding(N_REALMS + 1, 8)
        self.schedule_projection = nn.Linear(SCHEDULE_DIM, 16)
        self.event_encoder = nn.Sequential(
            nn.Linear(8 + 16 + 8 + 16, HIDDEN_DIM),
            nn.GELU(),
            nn.Linear(HIDDEN_DIM, HIDDEN_DIM),
        )
        self.cell = nn.GRUCell(HIDDEN_DIM, HIDDEN_DIM)
        self.state_head = nn.Linear(HIDDEN_DIM, BASE.N_STATES)
        self.bit_head = nn.Linear(HIDDEN_DIM, 6)

    def encode(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encoder(values)
        core = F.normalize(encoded[..., : BASE.CORE_DIM], dim=-1)
        return core, encoded[..., BASE.CORE_DIM :]

    def prototypes(self, cores: torch.Tensor) -> torch.Tensor:
        query = self.base_query.expand(cores.shape[0], -1, -1)
        value, _ = self.form_attention(query, cores, cores, need_weights=False)
        return F.normalize(value[:, 0], dim=-1)

    def initial_hidden(self, prototypes: torch.Tensor, starts: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.init_hidden(prototypes[starts]))

    def route(
        self,
        prototypes: torch.Tensor,
        batch: RouteBatch,
        *,
        capture_hidden: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
        hidden = self.initial_hidden(prototypes, batch.starts)
        initial = hidden
        logits = []
        hidden_trace = []
        for index in range(batch.input_actions.shape[0]):
            count = batch.starts.shape[0]
            event = self.event_embedding(batch.events[index].expand(count))
            action = self.action_embedding(batch.input_actions[index])
            realm = self.realm_embedding(batch.realms[index])
            schedule = self.schedule_projection(batch.schedules[index].expand(count, -1))
            encoded_event = self.event_encoder(torch.cat((event, action, realm, schedule), dim=-1))
            hidden = self.cell(encoded_event, hidden)
            logits.append(self.state_head(hidden))
            if capture_hidden:
                hidden_trace.append(hidden)
        trace = torch.stack(hidden_trace) if capture_hidden else None
        return torch.stack(logits), initial, trace


def gradient_norm(parameters: Iterable[torch.Tensor]) -> float:
    total = 0.0
    for parameter in parameters:
        if parameter.grad is not None:
            total += float(parameter.grad.detach().pow(2).sum().cpu())
    return math.sqrt(total)


def train_arm(
    arm: Arm,
    seed: int,
    steps: int,
    device: torch.device,
    *,
    batch_size: int = 192,
    trace_every: int = 100,
) -> tuple[SpiralStaircaseNet, list[dict[str, float]]]:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    data_generator = torch.Generator().manual_seed(seed * 1009 + 71)
    features = BASE.build_features(arm.feature_mode).to(device)
    model = SpiralStaircaseNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2.5e-3, weight_decay=1e-4)
    labels = torch.arange(BASE.N_STATES, device=device)
    lane_targets = torch.arange(len(BASE.TONGUES), device=device).repeat(BASE.N_STATES)
    bit_table = torch.tensor(
        [BASE.state_bits(state) for state in range(BASE.N_STATES)],
        dtype=torch.float32,
        device=device,
    )
    trace: list[dict[str, float]] = []

    for step in range(steps):
        depth = TRAIN_DEPTHS[step % len(TRAIN_DEPTHS)]
        batch = make_route_batch(
            depth,
            batch_size,
            data_generator,
            device,
            receipts=arm.receipts,
            schedule_mode=arm.schedule_mode,
        )
        optimizer.zero_grad(set_to_none=True)
        cores, residual = model.encode(features)
        prototypes = model.prototypes(cores)
        route_logits, initial_hidden, hidden_trace = model.route(
            prototypes, batch, capture_hidden=True
        )
        assert hidden_trace is not None
        initial_logits = model.initial_state_head(prototypes)
        route_targets = batch.targets.reshape(-1)
        flat_hidden = hidden_trace.reshape(-1, HIDDEN_DIM)
        loss_identity = BASE.identity_loss(cores)
        loss_lane = F.cross_entropy(
            model.lane_head(residual.reshape(-1, BASE.RESIDUAL_DIM)), lane_targets
        )
        loss_initial = F.cross_entropy(initial_logits, labels)
        loss_route = F.cross_entropy(route_logits.reshape(-1, BASE.N_STATES), route_targets)
        loss_bits = F.binary_cross_entropy_with_logits(
            model.bit_head(flat_hidden), bit_table[route_targets]
        )
        loss_return = 1.0 - F.cosine_similarity(hidden_trace[-1], initial_hidden, dim=-1).mean()
        loss = (
            0.30 * loss_identity
            + 0.15 * loss_lane
            + 0.40 * loss_initial
            + loss_route
            + 0.20 * loss_bits
            + 0.30 * loss_return
        )
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss for {arm.name} seed {seed} step {step}")
        loss.backward()
        for name, parameter in model.named_parameters():
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                raise RuntimeError(f"non-finite gradient {name} for {arm.name} seed {seed}")
        should_trace = step == 0 or (step + 1) % trace_every == 0 or step + 1 == steps
        if should_trace:
            trace.append(
                {
                    "step": step + 1,
                    "depth": depth,
                    "loss": float(loss.detach().cpu()),
                    "identity": float(loss_identity.detach().cpu()),
                    "lane": float(loss_lane.detach().cpu()),
                    "initial": float(loss_initial.detach().cpu()),
                    "route": float(loss_route.detach().cpu()),
                    "bits": float(loss_bits.detach().cpu()),
                    "return": float(loss_return.detach().cpu()),
                    "encoder_gradient": gradient_norm(model.encoder.parameters()),
                    "schedule_gradient": gradient_norm(model.schedule_projection.parameters()),
                    "cell_gradient": gradient_norm(model.cell.parameters()),
                }
            )
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
    return model, trace


def fixed_eval_batch(depth: int, arm: Arm, device: torch.device, count: int = 384) -> RouteBatch:
    generator = torch.Generator().manual_seed(820_000 + depth * 97)
    return make_route_batch(
        depth,
        count,
        generator,
        device,
        receipts=arm.receipts,
        schedule_mode=arm.schedule_mode,
    )


def accuracy(values: torch.Tensor) -> float:
    return float(values.float().mean().cpu())


@torch.no_grad()
def evaluate(
    model: SpiralStaircaseNet,
    arm: Arm,
    seed: int,
    device: torch.device,
) -> dict[str, object]:
    model.eval()
    features = BASE.build_features(arm.feature_mode).to(device)
    cores, residual = model.encode(features)
    prototypes = model.prototypes(cores)
    labels = torch.arange(BASE.N_STATES, device=device)
    summed = cores.sum(dim=1)
    identity_predictions = []
    for lane in range(len(BASE.TONGUES)):
        other = F.normalize((summed - cores[:, lane]) / (len(BASE.TONGUES) - 1), dim=-1)
        identity_predictions.append((cores[:, lane] @ other.T).argmax(-1))
    identity_prediction = torch.stack(identity_predictions, dim=1)
    lane_prediction = model.lane_head(residual.reshape(-1, BASE.RESIDUAL_DIM)).argmax(-1)
    lane_target = torch.arange(len(BASE.TONGUES), device=device).repeat(BASE.N_STATES)
    initial_prediction = model.initial_state_head(prototypes).argmax(-1)

    by_depth: dict[str, dict[str, float]] = {}
    noop_steps = []
    noop_full = []
    for depth in EVAL_DEPTHS:
        batch = fixed_eval_batch(depth, arm, device)
        logits, initial_hidden, hidden_trace = model.route(prototypes, batch, capture_hidden=True)
        assert hidden_trace is not None
        predictions = logits.argmax(-1)
        correct = predictions.eq(batch.targets)
        open_correct = correct[:depth]
        close_correct = correct[depth:]
        full_route = correct.all(dim=0)
        final_return = predictions[-1].eq(batch.starts)
        noop = batch.targets.eq(batch.starts.unsqueeze(0))
        noop_steps.append(accuracy(noop))
        noop_full.append(accuracy(noop.all(dim=0)))
        by_depth[str(depth)] = {
            "step_accuracy": accuracy(correct),
            "open_accuracy": accuracy(open_correct),
            "close_accuracy": accuracy(close_correct),
            "full_route_exact": accuracy(full_route),
            "final_return": accuracy(final_return),
            "hidden_return_cosine": float(
                F.cosine_similarity(hidden_trace[-1], initial_hidden, dim=-1).mean().cpu()
            ),
            "hidden_return_l2": float(
                (hidden_trace[-1] - initial_hidden).pow(2).sum(-1).sqrt().mean().cpu()
            ),
        }

    def depth_mean(metric: str, depths: Sequence[int]) -> float:
        return statistics.mean(by_depth[str(depth)][metric] for depth in depths)

    short_depths = TRAIN_DEPTHS
    deep_depths = tuple(depth for depth in EVAL_DEPTHS if depth not in TRAIN_DEPTHS)
    metrics = {
        "identity_top1": accuracy(identity_prediction.eq(labels[:, None])),
        "lane_residual_accuracy": accuracy(lane_prediction.eq(lane_target)),
        "initial_state_accuracy": accuracy(initial_prediction.eq(labels)),
        "short_step_accuracy": depth_mean("step_accuracy", short_depths),
        "short_close_accuracy": depth_mean("close_accuracy", short_depths),
        "short_final_return": depth_mean("final_return", short_depths),
        "short_full_route_exact": depth_mean("full_route_exact", short_depths),
        "deep_step_accuracy": depth_mean("step_accuracy", deep_depths),
        "deep_close_accuracy": depth_mean("close_accuracy", deep_depths),
        "deep_final_return": depth_mean("final_return", deep_depths),
        "deep_full_route_exact": depth_mean("full_route_exact", deep_depths),
        "deep_hidden_return_cosine": depth_mean("hidden_return_cosine", deep_depths),
        "noop_step_accuracy": statistics.mean(noop_steps),
        "noop_full_route_exact": statistics.mean(noop_full),
        "oracle_route_accuracy": 1.0,
    }
    metrics["short_route_floor"] = min(
        metrics["short_step_accuracy"],
        metrics["short_close_accuracy"],
        metrics["short_final_return"],
    )
    metrics["deep_route_floor"] = min(
        metrics["deep_step_accuracy"],
        metrics["deep_close_accuracy"],
        metrics["deep_final_return"],
    )

    snapshot_depth = 12
    generator = torch.Generator().manual_seed(104_729)
    snapshot_batch = make_route_batch(
        snapshot_depth,
        1,
        generator,
        device,
        receipts=arm.receipts,
        schedule_mode=arm.schedule_mode,
    )
    snapshot_logits, initial_hidden, snapshot_hidden = model.route(
        prototypes, snapshot_batch, capture_hidden=True
    )
    assert snapshot_hidden is not None
    probabilities = F.softmax(snapshot_logits[:, 0], dim=-1)
    snapshot_predictions = probabilities.argmax(-1)
    events = []
    for index in range(snapshot_logits.shape[0]):
        events.append(
            {
                "step": index + 1,
                "event": "open" if int(snapshot_batch.events[index]) == 0 else "close",
                "landing_depth": int(snapshot_batch.depths[index]),
                "input_action": action_name(int(snapshot_batch.input_actions[index, 0])),
                "target_action": action_name(int(snapshot_batch.target_actions[index, 0])),
                "realm": int(snapshot_batch.realms[index, 0]),
                "schedule": snapshot_batch.schedules[index].cpu().tolist(),
                "target_state": int(snapshot_batch.targets[index, 0]),
                "predicted_state": int(snapshot_predictions[index]),
                "probability": float(probabilities[index, snapshot_predictions[index]].cpu()),
                "hidden_norm": float(snapshot_hidden[index, 0].norm().cpu()),
                "initial_cosine": float(
                    F.cosine_similarity(snapshot_hidden[index, 0], initial_hidden[0], dim=0).cpu()
                ),
            }
        )
    return {
        "arm": arm.name,
        "seed": seed,
        "metrics": metrics,
        "by_depth": by_depth,
        "activation_snapshot": {
            "start_state": int(snapshot_batch.starts[0]),
            "events": events,
        },
    }


def pooled_sd(candidate: Sequence[float], control: Sequence[float]) -> float:
    left = statistics.stdev(candidate) if len(candidate) > 1 else 0.0
    right = statistics.stdev(control) if len(control) > 1 else 0.0
    return math.sqrt((left * left + right * right) / 2.0)


def comparison(
    runs: Sequence[dict[str, object]], candidate: str, control: str, metric: str
) -> dict[str, object]:
    candidate_rows = {int(row["seed"]): row for row in runs if row["arm"] == candidate}
    control_rows = {int(row["seed"]): row for row in runs if row["arm"] == control}
    seeds = sorted(set(candidate_rows) & set(control_rows))
    candidate_values = [float(candidate_rows[seed]["metrics"][metric]) for seed in seeds]
    control_values = [float(control_rows[seed]["metrics"][metric]) for seed in seeds]
    effects = [left - right for left, right in zip(candidate_values, control_values)]
    noise = pooled_sd(candidate_values, control_values)
    mean_effect = statistics.mean(effects)
    return {
        "candidate": candidate,
        "control": control,
        "metric": metric,
        "seeds": seeds,
        "candidate_values": candidate_values,
        "control_values": control_values,
        "paired_effects": effects,
        "mean_effect": mean_effect,
        "pooled_sd": noise,
        "two_pooled_sd": 2.0 * noise,
        "all_positive": all(effect > 0.0 for effect in effects),
        "clears_two_pooled_sd": mean_effect > 2.0 * noise,
    }


def analyze(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    controls = {
        "receipt_vs_no_receipt": "aligned_no_receipt_phi",
        "phi_vs_uniform": "aligned_receipt_uniform",
        "phi_vs_zero": "aligned_receipt_zero",
        "phi_vs_shuffled_phi": "aligned_receipt_shuffled_phi",
        "aligned_vs_ordinary": "ordinary_receipt_phi",
        "aligned_vs_shuffled_codec": "shuffled_codec_receipt_phi",
    }
    comparisons = {
        name: comparison(runs, "aligned_receipt_phi", control, "deep_route_floor")
        for name, control in controls.items()
    }
    aligned = [row for row in runs if row["arm"] == "aligned_receipt_phi"]
    receipt = comparisons["receipt_vs_no_receipt"]
    phi_names = ("phi_vs_uniform", "phi_vs_zero", "phi_vs_shuffled_phi")
    tokenizer_names = ("aligned_vs_ordinary", "aligned_vs_shuffled_codec")
    return {
        "comparisons": comparisons,
        "claim_rules": {
            "receipt_supports_deep_return": receipt["all_positive"]
            and receipt["clears_two_pooled_sd"],
            "phi_schedule_support": all(
                comparisons[name]["all_positive"]
                and comparisons[name]["clears_two_pooled_sd"]
                for name in phi_names
            ),
            "tokenizer_specific_staircase_support": all(
                comparisons[name]["all_positive"]
                and comparisons[name]["clears_two_pooled_sd"]
                for name in tokenizer_names
            ),
            "deep_nesting_absolute_support": all(
                float(row["metrics"]["deep_route_floor"]) >= 0.90
                and float(row["metrics"]["deep_full_route_exact"]) >= 0.70
                for row in aligned
            ),
        },
        "scope": (
            "Synthetic reversible-state benchmark. It tests reusable recurrent routing, exact "
            "return receipts, and depth extrapolation; it does not establish open-domain reasoning."
        ),
    }


def render_report(receipt: dict[str, object]) -> str:
    lines = [
        "# Spiral staircase reasoning result",
        "",
        f"Generated: {receipt['created_at']}",
        "",
        "| arm | short floor | deep floor | deep close | deep return | deep full route |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        rows = [row for row in receipt["runs"] if row["arm"] == arm.name]

        def mean(metric: str) -> float:
            return statistics.mean(float(row["metrics"][metric]) for row in rows)

        lines.append(
            f"| {arm.name} | {mean('short_route_floor'):.3f} | "
            f"{mean('deep_route_floor'):.3f} | {mean('deep_close_accuracy'):.3f} | "
            f"{mean('deep_final_return'):.3f} | {mean('deep_full_route_exact'):.3f} |"
        )
    lines.extend(("", "## Pre-registered gates", ""))
    for name, passed in receipt["analysis"]["claim_rules"].items():
        lines.append(f"- {name}: **{'PASS' if passed else 'NOT ESTABLISHED'}**")
    return "\n".join(lines) + "\n"


def verify_actions() -> dict[str, object]:
    states = torch.arange(BASE.N_STATES).repeat_interleave(N_ACTIONS)
    actions = torch.arange(N_ACTIONS).repeat(BASE.N_STATES)
    moved = apply_action(states, actions)
    returned = apply_action(moved, INVERSE_ACTION[actions])
    return {
        "checks": int(states.numel()),
        "passed": int(returned.eq(states).sum()),
        "exact": bool(returned.eq(states).all()),
    }


def verify_routes() -> dict[str, object]:
    checks = 0
    passed = 0
    for depth in EVAL_DEPTHS:
        generator = torch.Generator().manual_seed(71_000 + depth)
        batch = make_route_batch(
            depth,
            128,
            generator,
            torch.device("cpu"),
            receipts=True,
            schedule_mode="phi",
        )
        checks += len(batch.starts)
        passed += int(batch.targets[-1].eq(batch.starts).sum())
    return {"checks": checks, "passed": passed, "exact": checks == passed}


def preflight(output_dir: Path, device: torch.device) -> dict[str, object]:
    started = time.perf_counter()
    determinism = BASE.configure_determinism(device)
    action_check = verify_actions()
    route_check = verify_routes()
    codec_check = BASE.verify_round_trips()
    counts = [sum(parameter.numel() for parameter in SpiralStaircaseNet().parameters()) for _ in ARMS]
    finite = {}
    for arm in ARMS:
        model, trace = train_arm(arm, 101, 1, device, batch_size=32, trace_every=1)
        finite[arm.name] = math.isfinite(trace[-1]["loss"])
        del model
    hashes = []
    for _ in range(2):
        model, _ = train_arm(ARMS[0], 20261021, 3, device, batch_size=48, trace_every=3)
        hashes.append(model_state_sha256(model))
        del model
    result = {
        "schema": "scbe.spiral-staircase-preflight.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "determinism": determinism,
        "action_inverse": action_check,
        "nested_route_return": route_check,
        "codec_round_trip": codec_check,
        "parameter_counts": counts,
        "all_parameter_matched": len(set(counts)) == 1,
        "finite_one_step": finite,
        "exact_replay": {"passed": hashes[0] == hashes[1], "state_sha256": hashes},
        "elapsed_seconds": time.perf_counter() - started,
    }
    result["passed"] = (
        action_check["exact"]
        and route_check["exact"]
        and codec_check["passed"] == codec_check["checks"]
        and result["all_parameter_matched"]
        and all(finite.values())
        and result["exact_replay"]["passed"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "PREFLIGHT.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def run_experiment(
    output_dir: Path,
    steps: int,
    seeds: Sequence[int],
    device: torch.device,
) -> dict[str, object]:
    gate = preflight(output_dir, device)
    if not gate["passed"]:
        raise RuntimeError("preflight failed; refusing staircase matrix")
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
        "schema": "scbe.spiral-staircase-reasoning.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "seeds": list(seeds),
        "device": str(device),
        "train_depths": list(TRAIN_DEPTHS),
        "evaluation_depths": list(EVAL_DEPTHS),
        "arms": [asdict(arm) for arm in ARMS],
        "preflight_sha256": sha256_file(output_dir / "PREFLIGHT.json"),
        "source": {"path": str(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "runs": runs,
        "analysis": analyze(runs),
        "elapsed_seconds": time.perf_counter() - started,
        "automatic_promotion": False,
        "provider_spend": 0,
    }
    (output_dir / "RESULTS.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
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
