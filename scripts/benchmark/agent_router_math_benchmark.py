#!/usr/bin/env python3
"""Run the SCBE math-reasoning benchmark from the existing agent-router workflow.

This wrapper exists so the workflow can use repository secrets on GitHub Actions
without embedding long Python heredocs in YAML.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _parse_query(query: str) -> dict[str, Any]:
    text = str(query or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"model": text}
    return payload if isinstance(payload, dict) else {}


def _cost_guard(provider: str, model: str, cost_mode: str) -> None:
    if cost_mode != "low_cost":
        return
    low_cost_allowed = (
        (provider == "openai" and model in {"gpt-4o-mini", "gpt-4.1-mini"})
        or provider in {"cerebras", "groq", "huggingface"}
    )
    if not low_cost_allowed:
        raise SystemExit(f"cost guard blocked {provider}:{model}; set cost_mode=paid_allowed if intended")


def _build_router_config(provider: str, model: str, artifact_root: Path) -> Path:
    cfg_path = Path("config/governance/terminal_ai_router_profiles.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["provider_order"] = [provider]
    cfg["complexity_tiers"] = {"easy": ["cheap"], "medium": ["cheap"], "hard": ["cheap"]}
    for name, provider_cfg in cfg.get("providers", {}).items():
        provider_cfg["enabled"] = name == provider
    selected = cfg["providers"][provider]
    selected["daily_cap_usd"] = max(float(selected.get("daily_cap_usd", 0.0)), 20.0)
    selected["tiers"] = {"cheap": {"model": model, "estimated_cents": 0.0}}

    config_path = artifact_root / "router-config.generated.json"
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return config_path


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def run_benchmark(query: str) -> dict[str, Any]:
    payload = _parse_query(query)
    provider = str(payload.get("provider", "openai"))
    model = str(payload.get("model", "gpt-4o-mini"))
    mode = str(payload.get("mode", "both"))
    limit = int(payload.get("limit", 8))
    cost_mode = str(payload.get("cost_mode", "low_cost"))

    _cost_guard(provider, model, cost_mode)

    artifact_root = Path("artifacts/benchmarks/math-reasoning")
    artifact_root.mkdir(parents=True, exist_ok=True)
    config_path = _build_router_config(provider, model, artifact_root)

    health_cmd = [
        "python",
        "scripts/system/terminal_ai_router.py",
        "--config",
        str(config_path),
        "health",
        "--checks",
        provider,
        "--output",
        str(artifact_root / "router-health.json"),
        "--strict",
    ]
    health = _run(health_cmd)

    modes = ["raw", "gated-tool-choice"] if mode == "both" else [mode]
    runs: list[dict[str, Any]] = []
    for selected_mode in modes:
        cmd = [
            "node",
            "packages/cli/scripts/bench_math_reasoning.cjs",
            "--mode",
            selected_mode,
            "--provider",
            "router",
            "--router-provider",
            provider,
            "--router-config",
            str(config_path),
            "--limit",
            str(limit),
            "--json",
        ]
        proc = _run(cmd)
        record: dict[str, Any] = {
            "mode": selected_mode,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
        try:
            report = json.loads(proc.stdout)
            record["score"] = report.get("score", {})
            record["model"] = report.get("model")
            record["artifact"] = report.get("artifact")
        except Exception:
            record["score"] = {}
        runs.append(record)

    result = {
        "schema_version": "agent-router-math-benchmark-v1",
        "ok": health.returncode == 0 and all(run["exit_code"] == 0 for run in runs),
        "provider": provider,
        "model": model,
        "mode": mode,
        "limit": limit,
        "cost_mode": cost_mode,
        "health": {
            "exit_code": health.returncode,
            "stdout_tail": health.stdout[-1000:],
            "stderr_tail": health.stderr[-1000:],
        },
        "runs": runs,
    }
    Path("artifacts/agent-router").mkdir(parents=True, exist_ok=True)
    Path("artifacts/agent-router/result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-router wrapper for the SCBE math reasoning benchmark.")
    parser.add_argument("--query", default=os.environ.get("QUERY", ""), help="JSON query payload or model name.")
    args = parser.parse_args()
    result = run_benchmark(args.query)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
