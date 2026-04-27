#!/usr/bin/env python3
"""AgentBus multi-agent deployment readiness check.

This is an in-house gate, not a publish gate. It verifies the local/free bus,
Cursor task surface, Hugging Face/Kaggle training surfaces, Ollama readiness,
and red-team pressure harness in one repeatable run.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import URLError


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_bus" / "deployment"
DEFAULT_KERNELS = ["issacizrealdavis/polly-auto-regularized-coding-v8"]


def utc_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def run_cmd(
    args: list[str],
    *,
    cwd: Path = REPO_ROOT,
    timeout: int = 120,
    input_text: str | None = None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "args": args,
            "started_at_utc": started,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "args": args,
            "started_at_utc": started,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }


def parse_json_text(text: str) -> Any | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def parse_jsonl(text: str) -> list[Any]:
    rows: list[Any] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"parse_error": True, "raw": line[:300]})
    return rows


def detect_cursor() -> dict[str, Any]:
    candidates = [
        shutil.which("cursor"),
        shutil.which("cursor.cmd"),
        str(Path.home() / "AppData" / "Local" / "Programs" / "cursor" / "resources" / "app" / "bin" / "cursor.cmd"),
    ]
    found = [item for item in candidates if item and Path(item).exists()]
    return {
        "installed": bool(found),
        "path": found[0] if found else "",
        "tasks_json": str((REPO_ROOT / ".vscode" / "tasks.json").resolve()),
        "rule_path": str((REPO_ROOT / ".cursor" / "rules" / "scbe-agent-bus-deployment.mdc").resolve()),
    }


def free_provider_health(run_dir: Path) -> dict[str, Any]:
    """Check only free/open provider surfaces used by the bus by default."""

    output = run_dir / "free_provider_health.json"
    ollama = ollama_health()
    hf = huggingface_status(run_dir)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "free_local_first",
        "providers": {
            "offline": {
                "status": "ok",
                "cost": "free",
                "privacy": "local",
                "detail": "deterministic local fallback",
            },
            "ollama": ollama,
            "huggingface": {
                "status": "ok" if hf["authenticated"] else "requires_auth",
                "cost": "account_or_free_tier",
                "privacy": "remote",
                "detail": "HF is allowed for open-weight surfaces and training/job status, not paid default dispatch.",
            },
        },
        "paid_providers": {
            "openai": "disabled_for_bus_default",
            "anthropic": "disabled_for_bus_default",
            "xai": "disabled_for_bus_default",
        },
    }
    write_json(output, payload)
    return {
        "ok": payload["providers"]["offline"]["status"] == "ok",
        "output_path": str(output),
        "payload": payload,
        "huggingface": hf,
    }


def ollama_health() -> dict[str, Any]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    url = f"{base_url}/api/tags"
    try:
        with urlrequest.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
        parsed = parse_json_text(body) or {}
        models = [
            str(item.get("name") or item.get("model") or "")
            for item in parsed.get("models", [])
            if isinstance(item, dict)
        ]
        return {
            "status": "ok",
            "cost": "free_local_runtime",
            "privacy": "local",
            "base_url": base_url,
            "models": [model for model in models if model][:12],
        }
    except URLError as exc:
        return {
            "status": "unavailable",
            "cost": "free_local_runtime",
            "privacy": "local",
            "base_url": base_url,
            "error": str(exc.reason),
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "cost": "free_local_runtime",
            "privacy": "local",
            "base_url": base_url,
            "error": str(exc),
        }


def huggingface_status(run_dir: Path) -> dict[str, Any]:
    whoami = run_cmd(["hf", "auth", "whoami"], timeout=60)
    jobs = run_cmd(["hf", "jobs", "ps", "-a"], timeout=90)
    write_text(run_dir / "hf_whoami.txt", whoami["stdout"] + whoami["stderr"])
    write_text(run_dir / "hf_jobs.txt", jobs["stdout"] + jobs["stderr"])
    return {
        "authenticated": whoami["exit_code"] == 0,
        "whoami": command_summary(whoami, stdout_limit=800),
        "jobs": command_summary(jobs, stdout_limit=3000),
    }


def kaggle_status(run_dir: Path, kernels: list[str]) -> dict[str, Any]:
    rows = []
    for kernel in kernels:
        result = run_cmd(["kaggle", "kernels", "status", kernel], timeout=60)
        text = (result["stdout"] + result["stderr"]).strip()
        write_text(run_dir / f"kaggle_{safe_name(kernel)}.txt", text + "\n")
        rows.append(
            {
                "kernel": kernel,
                "exit_code": result["exit_code"],
                "status_text": text,
                "complete": "COMPLETE" in text,
                "running": "RUNNING" in text,
            }
        )
    return {
        "kernels": rows,
        "any_complete": any(row["complete"] for row in rows),
        "any_running": any(row["running"] for row in rows),
    }


def bus_pipe_smoke(run_dir: Path) -> dict[str, Any]:
    single_event = [
        {
            "task": "Run a local multi-agent deployment smoke test and return governed routing metadata.",
            "taskType": "governance",
            "seriesId": "deployment-single",
            "privacy": "local_only",
            "budgetCents": 0,
            "dispatch": False,
            "dispatchProvider": "offline",
        }
    ]
    batch_events = [
        {
            "task": "Review a coding change for deterministic tests and rollback notes.",
            "taskType": "review",
            "seriesId": "deployment-batch",
            "privacy": "local_only",
            "budgetCents": 0,
            "dispatch": False,
            "dispatchProvider": "offline",
        },
        {
            "task": "Plan a training-result triage pass without launching paid jobs.",
            "taskType": "training",
            "seriesId": "deployment-batch",
            "privacy": "local_only",
            "budgetCents": 0,
            "dispatch": False,
            "dispatchProvider": "offline",
        },
    ]
    single = run_cmd(
        ["node", "scripts/system/agentbus_pipe.mjs", "--repo-root", str(REPO_ROOT)],
        input_text=json.dumps(single_event),
        timeout=120,
    )
    batch = run_cmd(
        ["node", "scripts/system/agentbus_pipe.mjs", "--repo-root", str(REPO_ROOT), "--continue-on-error"],
        input_text=json.dumps(batch_events),
        timeout=180,
    )
    single_rows = parse_jsonl(single["stdout"])
    batch_rows = parse_jsonl(batch["stdout"])
    write_json(run_dir / "agentbus_pipe_single.json", single_rows)
    write_json(run_dir / "agentbus_pipe_batch.json", batch_rows)
    return {
        "single_ok": single["exit_code"] == 0 and all(row.get("ok") for row in single_rows),
        "batch_ok": batch["exit_code"] == 0 and all(row.get("ok") for row in batch_rows),
        "single": command_summary(single, stdout_limit=1200),
        "batch": command_summary(batch, stdout_limit=2000),
        "single_rows": single_rows,
        "batch_rows": batch_rows,
    }


def pressure_check(run_dir: Path, run_id: str) -> dict[str, Any]:
    pressure_root = run_dir / "pressure"
    cmd = [
        sys.executable,
        "scripts/system/agentbus_pressure_test.py",
        "--run-id",
        f"{run_id}-pressure",
        "--privacy",
        "local_only",
        "--budget-cents",
        "0",
        "--max-players",
        "2",
        "--use-catalog",
        "--limit",
        "5",
        "--output-root",
        str(pressure_root),
    ]
    result = run_cmd(cmd, timeout=240)
    payload = parse_json_text(result["stdout"])
    if payload is None:
        report_path = pressure_root / f"{run_id}-pressure" / "report.json"
        if report_path.exists():
            payload = parse_json_text(report_path.read_text(encoding="utf-8"))
    status = payload.get("overall_status") if isinstance(payload, dict) else None
    return {
        "ok": status in {"pass", "pass_with_utility_gaps"},
        "overall_status": status,
        "command": command_summary(result, stdout_limit=2000),
        "report_path": str((pressure_root / f"{run_id}-pressure" / "report.json").resolve()),
        "payload": payload,
    }


def live_ollama_smoke(run_dir: Path) -> dict[str, Any]:
    output = run_dir / "live_ollama_call.json"
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:0.5b")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only the requested token."},
            {"role": "user", "content": "Return exactly SCBE_OLLAMA_SMOKE_OK."},
        ],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 20},
    }
    try:
        req = urlrequest.Request(
            f"{base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8", errors="replace")
        parsed = parse_json_text(body) or {}
        write_json(output, parsed)
        text = ""
        if isinstance(parsed.get("message"), dict):
            text = str(parsed["message"].get("content", ""))
        return {
            "ok": "SCBE_OLLAMA_SMOKE_OK" in text,
            "provider": "ollama",
            "base_url": base_url,
            "model": model,
            "output_path": str(output),
            "response_chars": len(text),
        }
    except Exception as exc:
        return {
            "ok": False,
            "provider": "ollama",
            "base_url": base_url,
            "model": model,
            "output_path": str(output),
            "error": str(exc),
        }


def command_summary(result: dict[str, Any], *, stdout_limit: int = 1600) -> dict[str, Any]:
    return {
        "args": result["args"],
        "exit_code": result["exit_code"],
        "timed_out": result["timed_out"],
        "stdout_tail": str(result["stdout"])[-stdout_limit:],
        "stderr_tail": str(result["stderr"])[-1200:],
    }


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")[:90]


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    provider_payload = report["free_provider_health"].get("payload") or {}
    providers = provider_payload.get("providers", {}) if isinstance(provider_payload, dict) else {}
    provider_ok = sorted(name for name, row in providers.items() if row.get("status") == "ok")
    provider_blocked = {
        name: row.get("status")
        for name, row in providers.items()
        if row.get("status") != "ok"
    }
    local_ready = bool(
        report["bus_pipe"]["single_ok"]
        and report["bus_pipe"]["batch_ok"]
        and report["pressure"]["ok"]
    )
    return {
        "cursor_ready": bool(report["cursor"]["installed"]),
        "local_multi_agent_ready": local_ready,
        "free_provider_health_ready": bool(provider_ok),
        "hf_authenticated": bool(report["free_provider_health"]["huggingface"]["authenticated"]),
        "ollama_ready": "ollama" in provider_ok,
        "kaggle_any_complete": bool(report["kaggle"]["any_complete"]),
        "provider_ok": provider_ok,
        "provider_blocked": provider_blocked,
        "paid_providers_default": "disabled",
        "pressure_status": report["pressure"]["overall_status"],
        "overall_status": "ready" if local_ready and "offline" in provider_ok else "needs_attention",
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    s = report["summary"]
    lines = [
        "# AgentBus Multi-Agent Deployment Check",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Created: `{report['created_at_utc']}`",
        f"- Overall: `{s['overall_status']}`",
        f"- Local multi-agent ready: `{s['local_multi_agent_ready']}`",
        f"- Cursor ready: `{s['cursor_ready']}`",
        f"- Hugging Face authenticated: `{s['hf_authenticated']}`",
        f"- Ollama ready: `{s['ollama_ready']}`",
        f"- Kaggle complete kernel seen: `{s['kaggle_any_complete']}`",
        f"- Free provider OK: `{', '.join(s['provider_ok']) if s['provider_ok'] else 'none'}`",
        f"- Free provider blocked/degraded: `{json.dumps(s['provider_blocked'], sort_keys=True)}`",
        f"- Paid providers default: `{s['paid_providers_default']}`",
        f"- Pressure status: `{s['pressure_status']}`",
        "",
        "## What This Proves",
        "",
        "- The local AgentBus pipe can route single and batched events without external spend.",
        "- The defensive pressure harness can run against the red-team catalog.",
        "- Cursor has a repo-local rule/task surface for repeatable operator use.",
        "- Hugging Face and Kaggle are checked as free/open training/provider surfaces, not assumed.",
        "- Paid model APIs are not part of the default bus readiness gate.",
        "",
        "## Next Fixes",
        "",
    ]
    if not s["local_multi_agent_ready"]:
        lines.append("- Fix local bus smoke or pressure failures before adding remote model dispatch.")
    if s["provider_blocked"]:
        lines.append("- Repair blocked free providers only if they are needed; offline fallback keeps the bus usable.")
    if report.get("live_ollama_smoke") is None:
        lines.append("- Run `npm run agentbus:deployment-check:ollama` only when a live local Ollama generation test is intentional.")
    lines.append("")
    lines.append("## Artifact Paths")
    lines.append("")
    lines.append(f"- JSON: `{report['report_json']}`")
    lines.append(f"- Markdown: `{report['report_markdown']}`")
    lines.append(f"- Free provider health: `{report['free_provider_health']['output_path']}`")
    lines.append(f"- Pressure report: `{report['pressure']['report_path']}`")
    write_text(path, "\n".join(lines) + "\n")


def run_deployment_check(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"agentbus-deploy-{utc_slug()}"
    run_dir = Path(args.output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schema_version": "scbe_agentbus_deployment_check_v1",
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "cursor": detect_cursor(),
        "free_provider_health": free_provider_health(run_dir),
        "kaggle": kaggle_status(run_dir, args.kernels),
        "bus_pipe": bus_pipe_smoke(run_dir),
        "pressure": pressure_check(run_dir, run_id),
        "live_ollama_smoke": None,
    }
    if args.live_ollama_smoke:
        report["live_ollama_smoke"] = live_ollama_smoke(run_dir)
    report["summary"] = summarize(report)
    report_json = run_dir / "report.json"
    report_md = run_dir / "report.md"
    report["report_json"] = str(report_json)
    report["report_markdown"] = str(report_md)
    write_json(report_json, report)
    write_markdown(report_md, report)
    print(json.dumps({"summary": report["summary"], "report_json": str(report_json), "report_md": str(report_md)}, indent=2))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AgentBus deployment readiness check.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--kernel", dest="kernels", action="append", default=[], help="Kaggle kernel slug to check.")
    parser.add_argument(
        "--live-ollama-smoke",
        action="store_true",
        help="Also make one real local Ollama generation call. No paid provider is used.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.kernels:
        args.kernels = DEFAULT_KERNELS
    report = run_deployment_check(args)
    return 0 if report["summary"]["local_multi_agent_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
