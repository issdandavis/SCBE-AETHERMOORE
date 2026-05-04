#!/usr/bin/env python3
"""Inspect GeoSeal harness provider lanes and lane-switch costs.

This is the offline half of the competitive harness benchmark. It does not call
models. It reports which providers are configured, how model refs resolve, and
which cross-provider pairs require an explicit lane-change signal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent_comms import evaluate_lane_switch, provider_registry, resolve_provider_model  # noqa: E402

KEY_MIRROR = Path.home() / ".codex" / "skills" / "scbe-api-key-local-mirror" / "scripts" / "key_mirror.py"
MIRROR_SERVICE_BY_PROVIDER = {
    "kimi": "kimi",
    "kimi_code": "kimi",
    "moonshot": "moonshot",
}

DEFAULT_MODEL_REFS = [
    "ollama:scbe-geoseal-coder:q8",
    "ollama:qwen2.5-coder:7b",
    "lmstudio:local-coder",
    "vllm:qwen-coder",
    "llamacpp:local-model",
    "deepseek:deepseek-chat",
    "groq:llama-3.3-70b-versatile",
    "gemini:gemini-2.5-flash",
    "together:zai-org/GLM-5",
    "mistral:codestral-latest",
    "cerebras:qwen-3-coder-480b",
    "kimi:kimi-for-coding",
    "moonshot:kimi-k2.6",
    "nvidia:qwen/qwen3-coder-480b-a35b-instruct",
    "openrouter:qwen/qwen3-coder",
    "huggingface:Qwen/Qwen2.5-Coder-7B-Instruct",
]


def build_provider_matrix(model_refs: list[str]) -> dict[str, Any]:
    providers = provider_registry()
    provider_statuses = {name: _provider_status_with_mirror(name, provider) for name, provider in providers.items()}
    resolved: list[dict[str, Any]] = []
    for ref in model_refs:
        provider, model = resolve_provider_model(ref)
        status = provider_statuses[provider.provider]
        resolved.append(
            {
                "ref": ref,
                "provider": provider.provider,
                "model": model,
                "family": provider.family,
                "tool_adapter": provider.tool_adapter,
                "local": provider.local,
                "pricing_tier": provider.pricing_tier,
                "capabilities": list(provider.capabilities),
                "docs_url": provider.docs_url,
                "available": status["available"],
                "available_via": status.get("available_via", "env" if status["available"] else "none"),
            }
        )

    pairs: list[dict[str, Any]] = []
    for left, right in combinations(model_refs, 2):
        verdict = evaluate_lane_switch([left, right])
        signal = f"provider-pair:{verdict.lane_path[0]}->{verdict.lane_path[-1]}:benchmark"
        signaled = evaluate_lane_switch([left, right], signal=signal)
        pairs.append(
            {
                "models": [left, right],
                "lane_path": list(verdict.lane_path),
                "cost": verdict.cost,
                "signal_required": verdict.signal_required,
                "ok_without_signal": verdict.ok,
                "recommended_signal": signal if verdict.signal_required else "",
                "ok_with_recommended_signal": signaled.ok,
            }
        )

    return {
        "schema_version": "scbe_harness_provider_matrix_v1",
        "provider_count": len(providers),
        "model_count": len(model_refs),
        "providers": provider_statuses,
        "models": resolved,
        "pairs": pairs,
    }


def build_software_factory_envelope(
    model_refs: list[str],
    *,
    task_id: str = "harness-provider-matrix",
    prompt: str = "Compare configured GeoSeal harness providers and lane-switch costs.",
    provider: str = "no_sandbox",
    branch_strategy: str = "scratch",
) -> dict[str, Any]:
    """Return a Sandcastle-inspired run envelope for GeoSeal harness planning.

    This is intentionally an offline contract: it does not launch containers or
    call models. It makes the run shape testable before provider adapters are
    allowed to mutate worktrees or spend credits.
    """

    matrix = build_provider_matrix(model_refs)
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    available_models = [model for model in matrix["models"] if model["available"]]
    blocked_pairs = [pair for pair in matrix["pairs"] if pair["signal_required"] and not pair["ok_without_signal"]]
    free_or_local = [
        model
        for model in matrix["models"]
        if model["local"] or str(model.get("pricing_tier", "")).startswith("free")
    ]

    return {
        "schema_version": "scbe_software_factory_run_v1",
        "task_id": task_id,
        "provider": provider,
        "agent_refs": model_refs,
        "branch_strategy": branch_strategy,
        "prompt_packet": {
            "prompt_file": None,
            "prompt_sha256": prompt_sha256,
            "context_receipt": f"provider_matrix:{matrix['model_count']}:{matrix['provider_count']}",
        },
        "signals": {
            "start": "SOFTWARE_FACTORY_START",
            "completion": "HOLD",
            "allowed_completion_values": ["COMPLETE", "HOLD", "BLOCKED", "NEEDS_REVIEW"],
        },
        "outputs": {
            "log_path": None,
            "commits": [],
            "changed_paths": [],
            "test_evidence": [],
            "gate_report": None,
        },
        "governance": {
            "lane_signal_required_pairs": len(blocked_pairs),
            "available_model_count": len(available_models),
            "free_or_local_model_count": len(free_or_local),
            "promotion_decision": "HOLD",
            "hold_reason": "offline envelope only; run adapters and gates before merge or publish",
        },
        "benchmark_target": {
            "name": "Sandcastle",
            "repository": "https://github.com/mattpocock/sandcastle",
            "borrowed_contracts": [
                "provider-neutral sandbox abstraction",
                "branch/worktree strategy metadata",
                "prompt packet",
                "completion signal",
                "run outputs with logs and commits",
            ],
            "geoSeal_extensions": [
                "lane-switch signaling",
                "multi-provider matrix",
                "local-key-mirror availability",
                "promotion gate placeholder",
                "training-data capture hook",
            ],
        },
        "matrix": matrix,
    }


def _provider_status_with_mirror(provider_id: str, provider: Any) -> dict[str, Any]:
    status = provider.status()
    if status["available"]:
        status["available_via"] = "env-or-local"
        return status
    service = MIRROR_SERVICE_BY_PROVIDER.get(provider_id)
    if not service or not _mirror_has_service(service):
        status["available_via"] = "none"
        return status
    status["available"] = True
    status["token_present"] = True
    status["available_via"] = f"local-key-mirror:{service}"
    return status


def _mirror_has_service(service: str) -> bool:
    if not KEY_MIRROR.exists():
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(KEY_MIRROR), "resolve", "--service", service],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    return bool(payload.get("ok"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODEL_REFS), help="Comma-separated provider:model refs")
    parser.add_argument(
        "--software-factory",
        action="store_true",
        help="Emit the Sandcastle-inspired GeoSeal software-factory run envelope instead of the raw matrix.",
    )
    parser.add_argument("--task-id", default="harness-provider-matrix", help="Task id for --software-factory output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    refs = [item.strip() for item in str(args.models).split(",") if item.strip()]
    if args.software_factory:
        report = build_software_factory_envelope(refs, task_id=args.task_id)
    else:
        report = build_provider_matrix(refs)
    print(json.dumps(report, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
