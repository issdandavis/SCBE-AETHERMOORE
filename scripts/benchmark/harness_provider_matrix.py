#!/usr/bin/env python3
"""Inspect GeoSeal harness provider lanes and lane-switch costs.

This is the offline half of the competitive harness benchmark. It does not call
models. It reports which providers are configured, how model refs resolve, and
which cross-provider pairs require an explicit lane-change signal.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent_comms import evaluate_lane_switch, provider_registry, resolve_provider_model  # noqa: E402

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
    "nvidia:qwen/qwen3-coder-480b-a35b-instruct",
    "openrouter:qwen/qwen3-coder",
    "huggingface:Qwen/Qwen2.5-Coder-7B-Instruct",
]


def build_provider_matrix(model_refs: list[str]) -> dict[str, Any]:
    providers = provider_registry()
    resolved: list[dict[str, Any]] = []
    for ref in model_refs:
        provider, model = resolve_provider_model(ref)
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
                "available": provider.status()["available"],
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
        "providers": {name: provider.status() for name, provider in providers.items()},
        "models": resolved,
        "pairs": pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODEL_REFS), help="Comma-separated provider:model refs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    refs = [item.strip() for item in str(args.models).split(",") if item.strip()]
    report = build_provider_matrix(refs)
    print(json.dumps(report, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
