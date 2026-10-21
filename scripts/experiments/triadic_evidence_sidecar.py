from __future__ import annotations

"""Triadic decision heads fed by a detached exact-byte coordinate sidecar."""

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
import torch.nn.functional as F

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import multiview_perspective_reasoning as BASE  # noqa: E402
import triadic_evidence_reasoning as TRIAD  # noqa: E402


DEFAULT_OUTPUT = Path("artifacts") / "triadic_evidence_sidecar_20261021"


@dataclass(frozen=True)
class Arm:
    name: str
    feature_mode: str
    role_supervision: bool


ARMS = (
    Arm("aligned_sidecar_role", "aligned", True),
    Arm("aligned_sidecar_free", "aligned", False),
    Arm("ordinary_sidecar_role", "ordinary", True),
    Arm("shuffled_sidecar_role", "shuffled", True),
    Arm("random_sidecar_role", "random", True),
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinate_sidecar(features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Read six exact low-bit coordinates per form, then retain cross-form agreement.

    Codec features use zero for an unset bit and a positive normalized value for
    a set bit. A vote is therefore exact for aligned and ordinary codec arms.
    Shuffled or random controls expose disagreement instead of receiving a
    hidden canonical label.
    """
    votes = torch.where(features[..., : BASE.N_LENSES] > 0, 1.0, -1.0)
    consensus = votes.mean(dim=1)
    agreement = votes.eq(votes[:, :1]).all(dim=1).float()
    return consensus.detach(), agreement.detach()


class SidecarTriadicNet(TRIAD.TriadicPerspectiveNet):
    def decide_coordinates(
        self,
        signed: torch.Tensor,
        omitted_axis: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        contribution = signed * self.axis_scale
        mask = torch.ones_like(contribution)
        if omitted_axis is not None:
            mask.scatter_(1, omitted_axis[:, None], 0.0)
        contribution = contribution * mask
        affirm = F.softplus(TRIAD.ROLE_BETA * contribution) / TRIAD.ROLE_BETA * mask
        counter = F.softplus(-TRIAD.ROLE_BETA * contribution) / TRIAD.ROLE_BETA * mask
        overlap = torch.minimum(affirm, counter)
        affirm_total = affirm.sum(dim=-1)
        counter_total = counter.sum(dim=-1)
        margin = affirm_total - counter_total
        total = affirm_total + counter_total
        active = mask.sum(dim=-1).clamp_min(1.0)
        confidence = (signed.abs() * mask).sum(dim=-1) / active
        ratio = margin / total.clamp_min(1e-6)
        judge_features = torch.stack(
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
        return self.judge_head(judge_features), {
            "signed": signed,
            "contribution": contribution,
            "affirm": affirm,
            "counter": counter,
            "overlap": overlap,
            "features": judge_features,
        }


def train_arm(
    arm: Arm,
    seed: int,
    steps: int,
    device: torch.device,
    trace_every: int = 100,
) -> tuple[SidecarTriadicNet, list[dict[str, float]]]:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    features = BASE.build_features(arm.feature_mode).to(device)
    sidecar, _ = coordinate_sidecar(features)
    model = SidecarTriadicNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    train_rows, _ = BASE.transition_split()
    starts, operations, targets = TRIAD.tensor_rows(train_rows, device)
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
    target_contribution = TRIAD.true_contributions(semantic_train)
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
        truth_logits, truth_receipt = model.decide_coordinates(sidecar[semantic_train])
        loss_truth = F.cross_entropy(truth_logits, truth_targets)
        stance_logits, _ = model.decide_coordinates(
            sidecar[semantic_states], semantic_lenses
        )
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


def semantic_metrics(
    model: SidecarTriadicNet,
    sidecar: torch.Tensor,
    states: Sequence[int],
    device: torch.device,
) -> dict[str, float]:
    state_tensor = torch.tensor(states, device=device)
    truth_target = torch.tensor([BASE.truth_for(state) + 1 for state in states], device=device)
    truth_logits, receipt = model.decide_coordinates(sidecar[state_tensor])
    truth_prediction = truth_logits.argmax(-1)
    repeated_states = state_tensor.repeat_interleave(BASE.N_LENSES)
    lenses = torch.arange(BASE.N_LENSES, device=device).repeat(len(states))
    stance_logits, _ = model.decide_coordinates(sidecar[repeated_states], lenses)
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
    target_contribution = TRIAD.true_contributions(state_tensor)
    predicted_contribution = receipt["contribution"]
    return {
        "truth": TRIAD.accuracy(truth_prediction, truth_target),
        "stance": TRIAD.accuracy(stance_prediction, stance_target),
        "reason": TRIAD.accuracy(reason_prediction[disagreement], reason_target[disagreement]),
        "vector_exact": float(
            (stance_matrix == stance_target_matrix).all(dim=1).float().mean().cpu()
        ),
        "minority": TRIAD.accuracy(stance_prediction[minority_mask], stance_target[minority_mask]),
        "contribution_sign": TRIAD.accuracy(
            torch.sign(predicted_contribution).long(), torch.sign(target_contribution).long()
        ),
        "contribution_mae": float(
            (predicted_contribution - target_contribution).abs().mean().cpu()
        ),
    }


def path_metrics(
    model: SidecarTriadicNet, proto: torch.Tensor, device: torch.device
) -> dict[str, float]:
    _, test_rows = BASE.transition_split()
    starts, operations, targets = TRIAD.tensor_rows(test_rows, device)
    predicted = model.step(proto[starts], operations)
    predicted_state = (predicted @ proto.T).argmax(-1)
    positive = torch.tensor(
        [BASE.OP_DELTAS[int(operation)] > 0 for operation in operations], device=device
    )
    returned = model.step(predicted, BASE.INVERSE_INDEX.to(device)[operations])
    paths = BASE.deterministic_paths()
    path_forward = path_backward = rollback = postrollback = 0
    for start_value, path in paths:
        current = proto[start_value : start_value + 1]
        end = TRIAD.roll(model, current, path)
        expected = BASE.path_target(start_value, path)
        path_forward += int((end @ proto.T).argmax(-1).item() == expected)
        inverse_path = tuple(int(BASE.INVERSE_INDEX[operation]) for operation in reversed(path))
        back = TRIAD.roll(model, end, inverse_path)
        path_backward += int((back @ proto.T).argmax(-1).item() == start_value)
        displaced = TRIAD.roll(model, current, path[:2])
        recovered = TRIAD.roll(
            model,
            displaced,
            tuple(int(BASE.INVERSE_INDEX[operation]) for operation in reversed(path[:2])),
        )
        rollback += int((recovered @ proto.T).argmax(-1).item() == start_value)
        final = TRIAD.roll(model, recovered, path)
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
            float(
                (
                    TRIAD.roll(model, proto[start_value : start_value + 1], candidate)
                    @ proto[goal]
                ).item()
            )
            for candidate in candidates
        ]
        branch_hits += int(max(range(4), key=lambda index: scores[index]) == correct)
    metrics = {
        "forward_heldout": TRIAD.accuracy(predicted_state[positive], targets[positive]),
        "backward_heldout": TRIAD.accuracy(predicted_state[~positive], targets[~positive]),
        "cycle_heldout": TRIAD.accuracy((returned @ proto.T).argmax(-1), starts),
        "multistep_forward": path_forward / len(paths),
        "multistep_backward": path_backward / len(paths),
        "parallel_branch_selection": branch_hits / 128,
        "rollback_recovery": rollback / len(paths),
        "postrollback_target": postrollback / len(paths),
    }
    metrics["reasoning_floor"] = min(
        metrics[key]
        for key in (
            "forward_heldout",
            "backward_heldout",
            "multistep_forward",
            "multistep_backward",
            "parallel_branch_selection",
            "rollback_recovery",
        )
    )
    return metrics


@torch.no_grad()
def evaluate(
    model: SidecarTriadicNet, arm: Arm, seed: int, device: torch.device
) -> dict[str, object]:
    model.eval()
    features = BASE.build_features(arm.feature_mode).to(device)
    sidecar, agreement = coordinate_sidecar(features)
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
    train_states = [
        state for state in range(BASE.N_STATES) if state not in BASE.SEMANTIC_TEST_STATES
    ]
    heldout_semantic = semantic_metrics(
        model, sidecar, list(BASE.SEMANTIC_TEST_STATES), device
    )
    train_semantic = semantic_metrics(model, sidecar, train_states, device)
    metrics = {
        "identity_top1": TRIAD.accuracy(
            identity_prediction, labels[:, None].expand_as(identity_prediction)
        ),
        "lane_residual_accuracy": TRIAD.accuracy(lane_prediction, lane_target),
        "byte_exact": float((bit_prediction == bit_target).all(dim=1).float().mean().cpu()),
        "sidecar_axis_agreement": float(agreement.mean().cpu()),
        **path_metrics(model, proto, device),
        **{f"heldout_{key}": value for key, value in heldout_semantic.items()},
        **{f"train_{key}": value for key, value in train_semantic.items()},
    }
    interpretation_keys = (
        "heldout_truth",
        "heldout_stance",
        "heldout_reason",
        "heldout_minority",
    )
    metrics["interpretation_floor"] = min(metrics[key] for key in interpretation_keys)
    metrics["joint_floor"] = min(metrics["reasoning_floor"], metrics["interpretation_floor"])
    snapshots = {}
    for state in (1, 6, 19, 32):
        truth_logits, receipt = model.decide_coordinates(sidecar[state : state + 1])
        lenses = torch.arange(BASE.N_LENSES, device=device)
        stance_logits, lens_receipt = model.decide_coordinates(
            sidecar[state : state + 1].expand(BASE.N_LENSES, -1), lenses
        )
        truth_prediction = int(truth_logits.argmax(-1).item())
        stance_prediction = stance_logits.argmax(-1)
        snapshots[str(state)] = {
            "sidecar": sidecar[state].cpu().tolist(),
            "agreement": agreement[state].cpu().tolist(),
            "contribution": receipt["contribution"][0].cpu().tolist(),
            "affirm": receipt["affirm"][0].cpu().tolist(),
            "counter": receipt["counter"][0].cpu().tolist(),
            "overlap": receipt["overlap"][0].cpu().tolist(),
            "judge_features": receipt["features"][0].cpu().tolist(),
            "truth_probabilities": F.softmax(truth_logits, dim=-1)[0].cpu().tolist(),
            "stance_probabilities": F.softmax(stance_logits, dim=-1).cpu().tolist(),
            "lens_margins": lens_receipt["features"][:, 2].cpu().tolist(),
            "reason_predictions": torch.where(
                stance_prediction != truth_prediction, lenses, torch.full_like(lenses, 6)
            )
            .cpu()
            .tolist(),
        }
    return {
        "arm": arm.name,
        "seed": seed,
        "metrics": metrics,
        "decision_snapshot": {
            "axis_scale": model.axis_scale.cpu().tolist(),
            "events": snapshots,
        },
    }


def analyze(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    comparisons = {
        "role_vs_free_interpretation": TRIAD.comparison(
            runs, "aligned_sidecar_role", "aligned_sidecar_free", "interpretation_floor"
        ),
        "aligned_vs_ordinary_interpretation": TRIAD.comparison(
            runs, "aligned_sidecar_role", "ordinary_sidecar_role", "interpretation_floor"
        ),
        "aligned_vs_shuffled_interpretation": TRIAD.comparison(
            runs, "aligned_sidecar_role", "shuffled_sidecar_role", "interpretation_floor"
        ),
        "aligned_vs_ordinary_joint": TRIAD.comparison(
            runs, "aligned_sidecar_role", "ordinary_sidecar_role", "joint_floor"
        ),
        "aligned_vs_shuffled_joint": TRIAD.comparison(
            runs, "aligned_sidecar_role", "shuffled_sidecar_role", "joint_floor"
        ),
    }
    aligned = [row for row in runs if row["arm"] == "aligned_sidecar_role"]
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
    role = comparisons["role_vs_free_interpretation"]
    role_supported = role["all_positive"] and role["clears_two_pooled_sd"]
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
            "exact_sidecar_triadic_traceability": traceable,
            "role_supervision_support": role_supported,
            "tokenizer_specific_interpretation_support": tokenizer_specific,
        },
    }


def render_report(receipt: dict[str, object]) -> str:
    lines = [
        "# Exact-sidecar triadic decision result",
        "",
        f"Generated: {receipt['created_at']}",
        "",
        "| arm | reason | truth | stance | why | minority | vector | sign | sidecar agreement |",
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
            f"{mean('heldout_contribution_sign'):.3f} | {mean('sidecar_axis_agreement'):.3f} |"
        )
    lines.extend(["", "## Pre-registered gates", ""])
    for name, passed in receipt["analysis"]["claim_rules"].items():
        lines.append(f"- {name}: **{'PASS' if passed else 'NOT ESTABLISHED'}**")
    return "\n".join(lines) + "\n"


def preflight(output_dir: Path, device: torch.device) -> dict[str, object]:
    started = time.perf_counter()
    determinism = BASE.configure_determinism(device)
    aligned_features = BASE.build_features("aligned").to(device)
    ordinary_features = BASE.build_features("ordinary").to(device)
    aligned_sidecar, aligned_agreement = coordinate_sidecar(aligned_features)
    ordinary_sidecar, ordinary_agreement = coordinate_sidecar(ordinary_features)
    expected = torch.tensor(
        [BASE.signed_bits(state) for state in range(BASE.N_STATES)],
        dtype=torch.float32,
        device=device,
    )
    exact_aligned = torch.equal(aligned_sidecar, expected)
    exact_ordinary = torch.equal(ordinary_sidecar, expected)
    counts = [sum(parameter.numel() for parameter in SidecarTriadicNet().parameters()) for _ in ARMS]
    gradient_checks = {}
    for arm in ARMS:
        model, trace = train_arm(arm, 101, 1, device, trace_every=1)
        gradient_checks[arm.name] = math.isfinite(trace[-1]["loss"])
        del model
    hashes = []
    for _ in range(2):
        model, _ = train_arm(ARMS[0], 20261021, 3, device, trace_every=3)
        hashes.append(TRIAD.model_state_sha256(model))
        del model
    result = {
        "schema": "scbe.triadic-evidence-sidecar-preflight.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "determinism": determinism,
        "aligned_sidecar_exact": exact_aligned,
        "ordinary_sidecar_exact": exact_ordinary,
        "aligned_agreement_mean": float(aligned_agreement.mean().cpu()),
        "ordinary_agreement_mean": float(ordinary_agreement.mean().cpu()),
        "parameter_counts": counts,
        "all_parameter_matched": len(set(counts)) == 1,
        "gradient_checks": gradient_checks,
        "exact_replay": {"passed": hashes[0] == hashes[1], "state_sha256": hashes},
        "elapsed_seconds": time.perf_counter() - started,
    }
    result["passed"] = (
        exact_aligned
        and exact_ordinary
        and result["all_parameter_matched"]
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
        raise RuntimeError("preflight failed; refusing exact-sidecar matrix")
    started = time.perf_counter()
    runs: list[dict[str, object]] = []
    for arm in ARMS:
        for seed in seeds:
            run_started = time.perf_counter()
            model, trace = train_arm(arm, seed, steps, device)
            result = evaluate(model, arm, seed, device)
            result["training_trace"] = trace
            result["parameter_count"] = sum(parameter.numel() for parameter in model.parameters())
            result["state_sha256"] = TRIAD.model_state_sha256(model)
            result["elapsed_seconds"] = time.perf_counter() - run_started
            runs.append(result)
            (output_dir / f"{arm.name}_s{seed}.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
    receipt = {
        "schema": "scbe.triadic-evidence-sidecar.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "seeds": list(seeds),
        "device": str(device),
        "arms": [asdict(arm) for arm in ARMS],
        "preflight_sha256": sha256_file(output_dir / "PREFLIGHT.json"),
        "source": {
            "runner": {"path": str(Path(__file__)), "sha256": sha256_file(Path(__file__))},
            "triadic_runner": {
                "path": str(Path(TRIAD.__file__)),
                "sha256": sha256_file(Path(TRIAD.__file__)),
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
