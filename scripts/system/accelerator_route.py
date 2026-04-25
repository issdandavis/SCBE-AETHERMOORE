from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from src.tokenizer.accelerator_routing import (
    AcceleratorProviderProfile,
    AcceleratorTaskPacket,
    route_accelerator_task,
)


def _json_object(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _pick(args: argparse.Namespace, payload: dict[str, Any], name: str, default: Any) -> Any:
    value = getattr(args, name)
    return value if value is not None else payload.get(name, default)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route a task through the provider-neutral accelerator simulator")
    parser.add_argument("--task-json", default=None, help="Optional JSON file containing task packet fields")
    parser.add_argument("--provider-json", default=None, help="Optional JSON file containing provider profile fields")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--workload", default=None)
    parser.add_argument("--matmul-fraction", type=float, default=None)
    parser.add_argument("--nonlinear-op-fraction", type=float, default=None)
    parser.add_argument("--precision-required-bits", type=int, default=None)
    parser.add_argument("--input-is-optical-signal", action="store_true")
    parser.add_argument("--branching-density", type=float, default=None)
    parser.add_argument("--memory-access-density", type=float, default=None)
    parser.add_argument("--latency-budget-ms", type=float, default=None)
    parser.add_argument("--energy-budget-j", type=float, default=None)
    parser.add_argument("--fallback", default=None)
    parser.add_argument("--provider-id", default=None)
    parser.add_argument("--provider-precision-bits", type=int, default=None)
    parser.add_argument("--provider-matmul-score", type=float, default=None)
    parser.add_argument("--provider-nonlinear-score", type=float, default=None)
    parser.add_argument("--provider-optical-input-native", action="store_true")
    parser.add_argument("--provider-branching-score", type=float, default=None)
    parser.add_argument("--provider-memory-score", type=float, default=None)
    parser.add_argument("--provider-energy-score", type=float, default=None)
    parser.add_argument("--provider-latency-score", type=float, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_payload = _json_object(args.task_json)
    provider_payload = _json_object(args.provider_json)
    packet = AcceleratorTaskPacket(
        task_id=_pick(args, task_payload, "task_id", "accelerator_task"),
        workload=_pick(args, task_payload, "workload", "unknown"),
        matmul_fraction=_pick(args, task_payload, "matmul_fraction", 0.0),
        nonlinear_op_fraction=_pick(args, task_payload, "nonlinear_op_fraction", 0.0),
        precision_required_bits=_pick(args, task_payload, "precision_required_bits", 16),
        input_is_optical_signal=bool(args.input_is_optical_signal or task_payload.get("input_is_optical_signal", False)),
        branching_density=_pick(args, task_payload, "branching_density", 0.0),
        memory_access_density=_pick(args, task_payload, "memory_access_density", 0.0),
        latency_budget_ms=_pick(args, task_payload, "latency_budget_ms", 100.0),
        energy_budget_j=_pick(args, task_payload, "energy_budget_j", 1.0),
        fallback=_pick(args, task_payload, "fallback", "gpu"),
    )
    provider = AcceleratorProviderProfile(
        provider_id=args.provider_id or provider_payload.get("provider_id", "photonic_npu_simulator_v1"),
        precision_native_bits=args.provider_precision_bits or provider_payload.get("precision_native_bits", 16),
        matmul_throughput_score=args.provider_matmul_score
        if args.provider_matmul_score is not None
        else provider_payload.get("matmul_throughput_score", 0.88),
        nonlinear_supported_score=args.provider_nonlinear_score
        if args.provider_nonlinear_score is not None
        else provider_payload.get("nonlinear_supported_score", 0.92),
        optical_input_native=bool(args.provider_optical_input_native or provider_payload.get("optical_input_native", False)),
        branching_supported_score=args.provider_branching_score
        if args.provider_branching_score is not None
        else provider_payload.get("branching_supported_score", 0.12),
        memory_access_score=args.provider_memory_score
        if args.provider_memory_score is not None
        else provider_payload.get("memory_access_score", 0.22),
        energy_efficiency_score=args.provider_energy_score
        if args.provider_energy_score is not None
        else provider_payload.get("energy_efficiency_score", 0.82),
        latency_score=args.provider_latency_score if args.provider_latency_score is not None else provider_payload.get("latency_score", 0.65),
    )
    print(json.dumps(route_accelerator_task(packet, provider), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
