from __future__ import annotations

"""Decoupled state/return-stack repair for the spiral staircase benchmark."""

import argparse
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
import spiral_staircase_reasoning as COUPLED  # noqa: E402


DEFAULT_OUTPUT = Path("artifacts") / "spiral_staircase_sidecar_20261021"
STACK_DIM = 64


@dataclass(frozen=True)
class Arm:
    name: str
    feature_mode: str
    receipts: bool
    schedule_mode: str


ARMS = (
    Arm("aligned_receipt_phi", "aligned", True, "phi"),
    Arm("aligned_no_receipt_phi", "aligned", False, "phi"),
    Arm("aligned_no_receipt_uniform", "aligned", False, "uniform"),
    Arm("aligned_no_receipt_zero", "aligned", False, "zero"),
    Arm("aligned_no_receipt_shuffled_phi", "aligned", False, "shuffled_phi"),
    Arm("ordinary_receipt_phi", "ordinary", True, "phi"),
    Arm("shuffled_codec_receipt_phi", "shuffled", True, "phi"),
)


class DecoupledStaircaseNet(nn.Module):
    """Learn state motion and door-stack memory on separate rails.

    The state rail sees only the current state and an action embedding. The
    stack rail sees event, action/receipt, realm, and schedule. With a receipt,
    route loss cannot flow into the stack rail. Without a receipt, a soft action
    selected by the stack head links the two rails.
    """

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

        self.action_embedding = nn.Embedding(COUPLED.N_ACTIONS, 16)
        self.state_transition = nn.Sequential(
            nn.Linear(BASE.CORE_DIM + 16, 64),
            nn.GELU(),
            nn.Linear(64, BASE.CORE_DIM),
        )

        self.stack_event_embedding = nn.Embedding(2, 8)
        self.stack_input_action = nn.Embedding(COUPLED.N_ACTIONS + 1, 16)
        self.stack_realm_embedding = nn.Embedding(COUPLED.N_REALMS + 1, 8)
        self.schedule_projection = nn.Linear(COUPLED.SCHEDULE_DIM, 16)
        self.stack_encoder = nn.Sequential(
            nn.Linear(8 + 16 + 8 + 16, STACK_DIM),
            nn.GELU(),
            nn.Linear(STACK_DIM, STACK_DIM),
        )
        self.stack_cell = nn.GRUCell(STACK_DIM, STACK_DIM)
        self.stack_action_head = nn.Linear(STACK_DIM, COUPLED.N_ACTIONS)

    def encode(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encoder(values)
        core = F.normalize(encoded[..., : BASE.CORE_DIM], dim=-1)
        return core, encoded[..., BASE.CORE_DIM :]

    def prototypes(self, cores: torch.Tensor) -> torch.Tensor:
        query = self.base_query.expand(cores.shape[0], -1, -1)
        value, _ = self.form_attention(query, cores, cores, need_weights=False)
        return F.normalize(value[:, 0], dim=-1)

    def move_with_embedding(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        delta = self.state_transition(torch.cat((state, action), dim=-1))
        return F.normalize(state + delta, dim=-1)

    def move(self, state: torch.Tensor, action_index: torch.Tensor) -> torch.Tensor:
        return self.move_with_embedding(state, self.action_embedding(action_index))

    def stack_event(
        self,
        event: torch.Tensor,
        action: torch.Tensor,
        realm: torch.Tensor,
        schedule: torch.Tensor,
    ) -> torch.Tensor:
        values = torch.cat(
            (
                self.stack_event_embedding(event),
                self.stack_input_action(action),
                self.stack_realm_embedding(realm),
                self.schedule_projection(schedule),
            ),
            dim=-1,
        )
        return self.stack_encoder(values)

    def route(
        self,
        prototypes: torch.Tensor,
        batch: COUPLED.RouteBatch,
        *,
        receipts: bool,
        capture: bool = False,
    ) -> dict[str, torch.Tensor | None]:
        state = prototypes[batch.starts]
        stack = torch.zeros(batch.starts.shape[0], STACK_DIM, device=state.device)
        state_logits = []
        close_logits = []
        state_trace = []
        stack_trace = []
        for index in range(batch.input_actions.shape[0]):
            count = batch.starts.shape[0]
            event_value = int(batch.events[index])
            if event_value == 1:
                predicted_action = self.stack_action_head(stack)
                close_logits.append(predicted_action)
                if receipts:
                    action_vector = self.action_embedding(batch.target_actions[index])
                else:
                    probabilities = F.softmax(predicted_action / 0.35, dim=-1)
                    action_vector = probabilities @ self.action_embedding.weight
            else:
                action_vector = self.action_embedding(batch.target_actions[index])
            state = self.move_with_embedding(state, action_vector)
            state_logits.append(state @ prototypes.T / 0.09)

            event = batch.events[index].expand(count)
            schedule = batch.schedules[index].expand(count, -1)
            encoded = self.stack_event(
                event,
                batch.input_actions[index],
                batch.realms[index],
                schedule,
            )
            stack = self.stack_cell(encoded, stack)
            if capture:
                state_trace.append(state)
                stack_trace.append(stack)
        return {
            "state_logits": torch.stack(state_logits),
            "close_logits": torch.stack(close_logits),
            "state_trace": torch.stack(state_trace) if capture else None,
            "stack_trace": torch.stack(stack_trace) if capture else None,
            "final_stack": stack,
        }


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
    model_type: type[DecoupledStaircaseNet] = DecoupledStaircaseNet,
) -> tuple[DecoupledStaircaseNet, list[dict[str, float]]]:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    generator = torch.Generator().manual_seed(seed * 1009 + 71)
    features = BASE.build_features(arm.feature_mode).to(device)
    model = model_type().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2.5e-3, weight_decay=1e-4)
    lane_target = torch.arange(len(BASE.TONGUES), device=device).repeat(BASE.N_STATES)
    bit_target = torch.tensor(
        [BASE.state_bits(state) for state in range(BASE.N_STATES)],
        dtype=torch.float32,
        device=device,
    )
    all_states = torch.arange(BASE.N_STATES, device=device).repeat_interleave(COUPLED.N_ACTIONS)
    all_actions = torch.arange(COUPLED.N_ACTIONS, device=device).repeat(BASE.N_STATES)
    all_targets = COUPLED.apply_action(all_states, all_actions)
    trace: list[dict[str, float]] = []

    for step in range(steps):
        depth = COUPLED.TRAIN_DEPTHS[step % len(COUPLED.TRAIN_DEPTHS)]
        batch = COUPLED.make_route_batch(
            depth,
            batch_size,
            generator,
            device,
            receipts=arm.receipts,
            schedule_mode=arm.schedule_mode,
        )
        optimizer.zero_grad(set_to_none=True)
        cores, residual = model.encode(features)
        prototypes = model.prototypes(cores)
        route = model.route(prototypes, batch, receipts=arm.receipts, capture=True)
        state_logits = route["state_logits"]
        close_logits = route["close_logits"]
        state_trace = route["state_trace"]
        assert isinstance(state_logits, torch.Tensor)
        assert isinstance(close_logits, torch.Tensor)
        assert isinstance(state_trace, torch.Tensor)

        one_step = model.move(prototypes[all_states], all_actions)
        inverse = model.move(one_step, COUPLED.INVERSE_ACTION.to(device)[all_actions])
        loss_identity = BASE.identity_loss(cores)
        loss_lane = F.cross_entropy(
            model.lane_head(residual.reshape(-1, BASE.RESIDUAL_DIM)), lane_target
        )
        loss_bits = F.binary_cross_entropy_with_logits(model.bit_head(prototypes), bit_target)
        loss_one_step = F.cross_entropy(one_step @ prototypes.T / 0.09, all_targets)
        loss_inverse = F.cross_entropy(inverse @ prototypes.T / 0.09, all_states)
        loss_route = F.cross_entropy(
            state_logits.reshape(-1, BASE.N_STATES), batch.targets.reshape(-1)
        )
        loss_stack = F.cross_entropy(
            close_logits.reshape(-1, COUPLED.N_ACTIONS), batch.target_actions[depth:].reshape(-1)
        )
        final_stack = route["final_stack"]
        assert isinstance(final_stack, torch.Tensor)
        loss_stack_return = final_stack.pow(2).mean()
        loss = (
            0.30 * loss_identity
            + 0.15 * loss_lane
            + 0.20 * loss_bits
            + loss_one_step
            + 0.50 * loss_inverse
            + loss_route
            + 0.65 * loss_stack
            + 0.10 * loss_stack_return
        )
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss for {arm.name} seed {seed} step {step}")
        loss.backward()
        for name, parameter in model.named_parameters():
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                raise RuntimeError(f"non-finite gradient {name} for {arm.name} seed {seed}")
        if step == 0 or (step + 1) % trace_every == 0 or step + 1 == steps:
            trace.append(
                {
                    "step": step + 1,
                    "depth": depth,
                    "loss": float(loss.detach().cpu()),
                    "identity": float(loss_identity.detach().cpu()),
                    "lane": float(loss_lane.detach().cpu()),
                    "bits": float(loss_bits.detach().cpu()),
                    "one_step": float(loss_one_step.detach().cpu()),
                    "inverse": float(loss_inverse.detach().cpu()),
                    "route": float(loss_route.detach().cpu()),
                    "stack": float(loss_stack.detach().cpu()),
                    "stack_return": float(loss_stack_return.detach().cpu()),
                    "state_gradient": gradient_norm(model.state_transition.parameters()),
                    "stack_gradient": gradient_norm(model.stack_cell.parameters()),
                    "schedule_gradient": gradient_norm(model.schedule_projection.parameters()),
                }
            )
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
    return model, trace


def accuracy(values: torch.Tensor) -> float:
    return float(values.float().mean().cpu())


@torch.no_grad()
def evaluate(
    model: DecoupledStaircaseNet,
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
    bit_prediction = (torch.sigmoid(model.bit_head(prototypes)) >= 0.5).long()
    bit_target = torch.tensor([BASE.state_bits(state) for state in range(BASE.N_STATES)], device=device)

    all_states = torch.arange(BASE.N_STATES, device=device).repeat_interleave(COUPLED.N_ACTIONS)
    all_actions = torch.arange(COUPLED.N_ACTIONS, device=device).repeat(BASE.N_STATES)
    all_targets = COUPLED.apply_action(all_states, all_actions)
    one_step = model.move(prototypes[all_states], all_actions)
    one_step_accuracy = accuracy((one_step @ prototypes.T).argmax(-1).eq(all_targets))

    by_depth: dict[str, dict[str, float]] = {}
    for depth in COUPLED.EVAL_DEPTHS:
        batch = COUPLED.fixed_eval_batch(depth, arm, device)
        route = model.route(prototypes, batch, receipts=arm.receipts, capture=True)
        state_logits = route["state_logits"]
        close_logits = route["close_logits"]
        stack_trace = route["stack_trace"]
        final_stack = route["final_stack"]
        assert isinstance(state_logits, torch.Tensor)
        assert isinstance(close_logits, torch.Tensor)
        assert isinstance(stack_trace, torch.Tensor)
        assert isinstance(final_stack, torch.Tensor)
        prediction = state_logits.argmax(-1)
        correct = prediction.eq(batch.targets)
        close_prediction = close_logits.argmax(-1)
        close_target = batch.target_actions[depth:]
        by_depth[str(depth)] = {
            "step_accuracy": accuracy(correct),
            "open_accuracy": accuracy(correct[:depth]),
            "close_accuracy": accuracy(correct[depth:]),
            "full_route_exact": accuracy(correct.all(dim=0)),
            "final_return": accuracy(prediction[-1].eq(batch.starts)),
            "stack_action_accuracy": accuracy(close_prediction.eq(close_target)),
            "stack_return_norm": float(final_stack.norm(dim=-1).mean().cpu()),
        }

    deep_depths = tuple(d for d in COUPLED.EVAL_DEPTHS if d not in COUPLED.TRAIN_DEPTHS)

    def depth_mean(metric: str, depths: Sequence[int]) -> float:
        return statistics.mean(by_depth[str(depth)][metric] for depth in depths)

    metrics = {
        "identity_top1": accuracy(identity_prediction.eq(labels[:, None])),
        "lane_residual_accuracy": accuracy(lane_prediction.eq(lane_target)),
        "byte_exact": accuracy(bit_prediction.eq(bit_target).all(dim=-1)),
        "one_step_accuracy": one_step_accuracy,
        "short_step_accuracy": depth_mean("step_accuracy", COUPLED.TRAIN_DEPTHS),
        "short_close_accuracy": depth_mean("close_accuracy", COUPLED.TRAIN_DEPTHS),
        "short_final_return": depth_mean("final_return", COUPLED.TRAIN_DEPTHS),
        "short_full_route_exact": depth_mean("full_route_exact", COUPLED.TRAIN_DEPTHS),
        "short_stack_action_accuracy": depth_mean("stack_action_accuracy", COUPLED.TRAIN_DEPTHS),
        "deep_step_accuracy": depth_mean("step_accuracy", deep_depths),
        "deep_close_accuracy": depth_mean("close_accuracy", deep_depths),
        "deep_final_return": depth_mean("final_return", deep_depths),
        "deep_full_route_exact": depth_mean("full_route_exact", deep_depths),
        "deep_stack_action_accuracy": depth_mean("stack_action_accuracy", deep_depths),
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
    snapshot_batch = COUPLED.make_route_batch(
        snapshot_depth,
        1,
        torch.Generator().manual_seed(104_729),
        device,
        receipts=arm.receipts,
        schedule_mode=arm.schedule_mode,
    )
    snapshot = model.route(prototypes, snapshot_batch, receipts=arm.receipts, capture=True)
    state_logits = snapshot["state_logits"]
    stack_trace = snapshot["stack_trace"]
    assert isinstance(state_logits, torch.Tensor)
    assert isinstance(stack_trace, torch.Tensor)
    state_probabilities = F.softmax(state_logits[:, 0], dim=-1)
    state_predictions = state_probabilities.argmax(-1)
    events = []
    for index in range(state_logits.shape[0]):
        before_stack = torch.zeros(STACK_DIM, device=device) if index == 0 else stack_trace[index - 1, 0]
        stack_probabilities = F.softmax(model.stack_action_head(before_stack), dim=-1)
        predicted_action = int(stack_probabilities.argmax())
        events.append(
            {
                "step": index + 1,
                "event": "open" if int(snapshot_batch.events[index]) == 0 else "close",
                "landing_depth": int(snapshot_batch.depths[index]),
                "input_action": COUPLED.action_name(int(snapshot_batch.input_actions[index, 0])),
                "target_action": COUPLED.action_name(int(snapshot_batch.target_actions[index, 0])),
                "stack_predicted_action": COUPLED.action_name(predicted_action),
                "stack_action_probability": float(stack_probabilities[predicted_action].cpu()),
                "target_state": int(snapshot_batch.targets[index, 0]),
                "predicted_state": int(state_predictions[index]),
                "state_probability": float(
                    state_probabilities[index, state_predictions[index]].cpu()
                ),
                "stack_norm": float(stack_trace[index, 0].norm().cpu()),
            }
        )
    return {
        "arm": arm.name,
        "seed": seed,
        "metrics": metrics,
        "by_depth": by_depth,
        "activation_snapshot": {"start_state": int(snapshot_batch.starts[0]), "events": events},
    }


def analyze(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    comparisons = {
        "receipt_vs_no_receipt": COUPLED.comparison(
            runs, "aligned_receipt_phi", "aligned_no_receipt_phi", "deep_route_floor"
        ),
        "phi_vs_uniform": COUPLED.comparison(
            runs, "aligned_no_receipt_phi", "aligned_no_receipt_uniform", "deep_route_floor"
        ),
        "phi_vs_zero": COUPLED.comparison(
            runs, "aligned_no_receipt_phi", "aligned_no_receipt_zero", "deep_route_floor"
        ),
        "phi_vs_shuffled_phi": COUPLED.comparison(
            runs,
            "aligned_no_receipt_phi",
            "aligned_no_receipt_shuffled_phi",
            "deep_route_floor",
        ),
        "aligned_vs_ordinary": COUPLED.comparison(
            runs, "aligned_receipt_phi", "ordinary_receipt_phi", "deep_route_floor"
        ),
        "aligned_vs_shuffled_codec": COUPLED.comparison(
            runs, "aligned_receipt_phi", "shuffled_codec_receipt_phi", "deep_route_floor"
        ),
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
    }


def render_report(receipt: dict[str, object]) -> str:
    lines = [
        "# Decoupled spiral staircase result",
        "",
        f"Generated: {receipt['created_at']}",
        "",
        "| arm | 1-step | short floor | deep floor | deep stack | deep full route |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        rows = [row for row in receipt["runs"] if row["arm"] == arm.name]

        def mean(metric: str) -> float:
            return statistics.mean(float(row["metrics"][metric]) for row in rows)

        lines.append(
            f"| {arm.name} | {mean('one_step_accuracy'):.3f} | "
            f"{mean('short_route_floor'):.3f} | {mean('deep_route_floor'):.3f} | "
            f"{mean('deep_stack_action_accuracy'):.3f} | "
            f"{mean('deep_full_route_exact'):.3f} |"
        )
    lines.extend(("", "## Pre-registered gates", ""))
    for name, passed in receipt["analysis"]["claim_rules"].items():
        lines.append(f"- {name}: **{'PASS' if passed else 'NOT ESTABLISHED'}**")
    return "\n".join(lines) + "\n"


def receipt_route_is_detached() -> bool:
    model = DecoupledStaircaseNet()
    features = BASE.build_features("aligned")
    cores, _ = model.encode(features)
    prototypes = model.prototypes(cores)
    batch = COUPLED.make_route_batch(
        2,
        8,
        torch.Generator().manual_seed(7),
        torch.device("cpu"),
        receipts=True,
        schedule_mode="phi",
    )
    route = model.route(prototypes.detach(), batch, receipts=True)
    state_logits = route["state_logits"]
    assert isinstance(state_logits, torch.Tensor)
    state_logits.sum().backward()
    stack_parameters = (
        list(model.stack_event_embedding.parameters())
        + list(model.stack_input_action.parameters())
        + list(model.stack_realm_embedding.parameters())
        + list(model.schedule_projection.parameters())
        + list(model.stack_encoder.parameters())
        + list(model.stack_cell.parameters())
        + list(model.stack_action_head.parameters())
    )
    return all(parameter.grad is None for parameter in stack_parameters)


def preflight(output_dir: Path, device: torch.device) -> dict[str, object]:
    started = time.perf_counter()
    determinism = BASE.configure_determinism(device)
    action_check = COUPLED.verify_actions()
    route_check = COUPLED.verify_routes()
    codec_check = BASE.verify_round_trips()
    counts = [sum(parameter.numel() for parameter in DecoupledStaircaseNet().parameters()) for _ in ARMS]
    finite = {}
    for arm in ARMS:
        model, trace = train_arm(arm, 101, 1, device, batch_size=32, trace_every=1)
        finite[arm.name] = math.isfinite(trace[-1]["loss"])
        del model
    hashes = []
    for _ in range(2):
        model, _ = train_arm(ARMS[0], 20261021, 3, device, batch_size=48, trace_every=3)
        hashes.append(COUPLED.model_state_sha256(model))
        del model
    result = {
        "schema": "scbe.spiral-staircase-sidecar-preflight.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "determinism": determinism,
        "action_inverse": action_check,
        "nested_route_return": route_check,
        "codec_round_trip": codec_check,
        "receipt_route_detached_from_stack": receipt_route_is_detached(),
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
        and result["receipt_route_detached_from_stack"]
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
        raise RuntimeError("preflight failed; refusing decoupled staircase matrix")
    started = time.perf_counter()
    runs: list[dict[str, object]] = []
    for arm in ARMS:
        for seed in seeds:
            run_started = time.perf_counter()
            model, trace = train_arm(arm, seed, steps, device)
            result = evaluate(model, arm, seed, device)
            result["training_trace"] = trace
            result["parameter_count"] = sum(parameter.numel() for parameter in model.parameters())
            result["state_sha256"] = COUPLED.model_state_sha256(model)
            result["elapsed_seconds"] = time.perf_counter() - run_started
            runs.append(result)
            (output_dir / f"{arm.name}_s{seed}.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
    receipt = {
        "schema": "scbe.spiral-staircase-sidecar.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "seeds": list(seeds),
        "device": str(device),
        "train_depths": list(COUPLED.TRAIN_DEPTHS),
        "evaluation_depths": list(COUPLED.EVAL_DEPTHS),
        "arms": [asdict(arm) for arm in ARMS],
        "preflight_sha256": COUPLED.sha256_file(output_dir / "PREFLIGHT.json"),
        "source": {"path": str(Path(__file__)), "sha256": COUPLED.sha256_file(Path(__file__))},
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
    return COUPLED.parse_seeds(value)


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
