from __future__ import annotations

"""Discrete lattice-snap repair for long-horizon staircase state drift."""

import argparse
import json
import math
import os
import statistics
import sys
import time
from dataclasses import asdict
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
import spiral_staircase_reasoning as COUPLED  # noqa: E402
import spiral_staircase_sidecar as SIDE  # noqa: E402


DEFAULT_OUTPUT = Path("artifacts") / "spiral_staircase_lattice_snap_20261021"
ARMS = SIDE.ARMS


class LatticeSnapStaircaseNet(SIDE.DecoupledStaircaseNet):
    """Project every proposed transition back onto a conserved token node."""

    def snap(
        self, candidate: torch.Tensor, prototypes: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        logits = candidate @ prototypes.T / 0.09
        probabilities = F.softmax(logits, dim=-1)
        hard = F.one_hot(logits.argmax(-1), BASE.N_STATES).to(probabilities.dtype)
        # Forward is a discrete node. Backward uses the soft projection gradient.
        weights = hard + probabilities - probabilities.detach() if self.training else hard
        return F.normalize(weights @ prototypes, dim=-1), logits

    def route(
        self,
        prototypes: torch.Tensor,
        batch: COUPLED.RouteBatch,
        *,
        receipts: bool,
        capture: bool = False,
    ) -> dict[str, torch.Tensor | None]:
        state = prototypes[batch.starts]
        stack = torch.zeros(batch.starts.shape[0], SIDE.STACK_DIM, device=state.device)
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
            candidate = self.move_with_embedding(state, action_vector)
            state, logits = self.snap(candidate, prototypes)
            state_logits.append(logits)

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


def train_arm(
    arm: SIDE.Arm,
    seed: int,
    steps: int,
    device: torch.device,
    *,
    batch_size: int = 192,
    trace_every: int = 100,
) -> tuple[LatticeSnapStaircaseNet, list[dict[str, float]]]:
    model, trace = SIDE.train_arm(
        arm,
        seed,
        steps,
        device,
        batch_size=batch_size,
        trace_every=trace_every,
        model_type=LatticeSnapStaircaseNet,
    )
    assert isinstance(model, LatticeSnapStaircaseNet)
    return model, trace


def states_snap_to_lattice() -> bool:
    model = LatticeSnapStaircaseNet()
    features = BASE.build_features("aligned")
    cores, _ = model.encode(features)
    prototypes = model.prototypes(cores)
    batch = COUPLED.make_route_batch(
        5,
        16,
        torch.Generator().manual_seed(83),
        torch.device("cpu"),
        receipts=True,
        schedule_mode="phi",
    )
    route = model.route(prototypes, batch, receipts=True, capture=True)
    trace = route["state_trace"]
    assert isinstance(trace, torch.Tensor)
    nearest = (trace @ prototypes.T).argmax(-1)
    expected = prototypes[nearest]
    return bool(torch.allclose(trace, expected, atol=1e-6, rtol=1e-6))


def preflight(output_dir: Path, device: torch.device) -> dict[str, object]:
    started = time.perf_counter()
    determinism = BASE.configure_determinism(device)
    action_check = COUPLED.verify_actions()
    route_check = COUPLED.verify_routes()
    codec_check = BASE.verify_round_trips()
    counts = [sum(parameter.numel() for parameter in LatticeSnapStaircaseNet().parameters()) for _ in ARMS]
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
        "schema": "scbe.spiral-staircase-lattice-snap-preflight.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "determinism": determinism,
        "action_inverse": action_check,
        "nested_route_return": route_check,
        "codec_round_trip": codec_check,
        "states_snap_to_lattice": states_snap_to_lattice(),
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
        and result["states_snap_to_lattice"]
        and result["all_parameter_matched"]
        and all(finite.values())
        and result["exact_replay"]["passed"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "PREFLIGHT.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def analyze(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    return SIDE.analyze(runs)


def render_report(receipt: dict[str, object]) -> str:
    lines = [
        "# Lattice-snap spiral staircase result",
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


def run_experiment(
    output_dir: Path,
    steps: int,
    seeds: Sequence[int],
    device: torch.device,
) -> dict[str, object]:
    gate = preflight(output_dir, device)
    if not gate["passed"]:
        raise RuntimeError("preflight failed; refusing lattice-snap matrix")
    started = time.perf_counter()
    runs: list[dict[str, object]] = []
    for arm in ARMS:
        for seed in seeds:
            run_started = time.perf_counter()
            model, trace = train_arm(arm, seed, steps, device)
            result = SIDE.evaluate(model, arm, seed, device)
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
        "schema": "scbe.spiral-staircase-lattice-snap.v1",
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


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--seeds", type=COUPLED.parse_seeds, default=(11, 23, 37))
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
