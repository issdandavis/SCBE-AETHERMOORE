#!/usr/bin/env python3
"""
Lightweight 24/7-compatible Ops Pulse (free/local-cost path).

Default behavior:
1) Run repo scanner
2) Run scan_postprocess
3) Optionally run a tiny local Hugging Face smoke training
4) Emit an AI-to-AI communication packet
5) Optionally post a context note to Obsidian
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
AUTOPILOT_DIR = ROOT / "artifacts" / "ops-autopilot"
COMM_SCRIPT = ROOT / "skills" / "scbe-ai-to-ai-communication" / "scripts" / "emit_ai_comm_packet.py"
REPO_SCANNER = ROOT / "scripts" / "repo_scanner.py"
POSTPROCESS = ROOT / "scripts" / "scan_postprocess.py"
SMOKE_SCRIPT = ROOT / "training" / "hf_smoke_sft_uv.py"
OBSIDIAN_TOOL = ROOT / "scripts" / "obsidian_ai_hub.py"


def run(cmd: List[str], *, cwd: Path | None = None, env: Dict[str, str] | None = None) -> subprocess.CompletedProcess:
    print(f"[run] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd or ROOT), text=True, capture_output=True, env=env, check=False)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_scan(scan_name: str) -> Dict[str, Any]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scan_dir = ROOT / "artifacts" / "repo_scans" / f"{ts}-{scan_name}"
    scan_dir.mkdir(parents=True, exist_ok=True)

    scan_res = run(
        [
            "python",
            str(REPO_SCANNER),
            "--root",
            ".",
            "--name",
            scan_name,
            "--max-size-mb",
            "5000",
            "--format",
            "all",
            "--out-dir",
            str(scan_dir),
            "--compute-hash",
        ],
        cwd=ROOT,
    )
    if scan_res.returncode != 0:
        return {
            "ok": False,
            "error": scan_res.stderr or scan_res.stdout,
            "scan_dir": str(scan_dir),
        }

    # repo_scanner has historically emitted outputs either directly into `out-dir`
    # or into `<out-dir>/<timestamp>-<name>`. Support both forms for compatibility.
    nested_scan_results_dir = scan_dir / scan_dir.name
    scan_results_dir = nested_scan_results_dir if nested_scan_results_dir.exists() else scan_dir
    if not scan_results_dir.exists():
        return {
            "ok": False,
            "error": f"scanner output folder missing: {scan_results_dir}",
            "scan_dir": str(scan_dir),
        }

    post_dir = scan_results_dir / "postprocess"
    post_res = run(
        [
            "python",
            str(POSTPROCESS),
            "--scan-dir",
            str(scan_results_dir),
            "--out-dir",
            str(post_dir),
            "--format",
            "all",
        ],
        cwd=ROOT,
    )

    manifest: Dict[str, Any] = {}
    tasks: List[Dict[str, Any]] = []
    scan_summary_file = scan_results_dir / "scan_summary.json"
    tasks_file = post_dir / "tasks.json"

    if scan_summary_file.exists():
        manifest = read_json(scan_summary_file)
    if tasks_file.exists():
        tasks = read_json(tasks_file).get("tasks", [])

    return {
        "ok": True,
        "scan_dir": str(scan_dir),
        "scan_results_dir": str(scan_results_dir),
        "scan_postprocess_dir": str(post_dir),
        "scan_stdout": scan_res.stdout[:2048],
        "scan_stderr": scan_res.stderr,
        "scan_postprocess": post_res.returncode == 0,
        "scan_postprocess_stderr": post_res.stderr,
        "scan_postprocess_stdout": post_res.stdout[:2048],
        "scan_summary": manifest,
        "top_tasks": tasks[:3],
    }


def run_smoke() -> Dict[str, Any]:
    smoke_env = os.environ.copy()
    smoke_env.setdefault("SCBE_SMOKE_USE_CPU", "1")
    smoke_env.setdefault("SCBE_SMOKE_MAX_STEPS", "2")

    sm_res = run(["python", str(SMOKE_SCRIPT)], cwd=ROOT, env=smoke_env)
    return {
        "ok": sm_res.returncode == 0,
        "returncode": sm_res.returncode,
        "stdout": sm_res.stdout[-3000:],
        "stderr": sm_res.stderr[-2000:],
    }


def emit_packet(scan_payload: Dict[str, Any], smoke_payload: Dict[str, Any] | None, status: str, task_id: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    packet_name = f"autopilot-{ts}"
    summary_lines = [
        f"scan_ok={scan_payload.get('ok')}",
        f"smoke_ok={smoke_payload.get('ok') if smoke_payload else None}",
    ]
    if scan_payload.get("scan_summary"):
        totals = scan_payload["scan_summary"].get("totals") or {}
        summary_lines.append(f"scan_files={totals.get('total_files', 'n/a')}")
    if smoke_payload:
        if smoke_payload.get("status"):
            summary_lines.append(f"smoke_status={smoke_payload['status']}")

    cmd = [
        "python",
        str(COMM_SCRIPT),
        "--sender",
        "agent.codex",
        "--recipient",
        "agent.aicoop",
        "--intent",
        "free-ops-pulse",
        "--status",
        status,
        "--task-id",
        task_id,
        "--summary",
        " | ".join(summary_lines),
        "--risk",
        "low",
        "--packet-id",
        packet_name,
    ]
    scan_results_dir = scan_payload.get("scan_results_dir") or scan_payload.get("scan_dir", "")
    for p in [
        scan_payload.get("scan_dir"),
        scan_payload.get("scan_results_dir"),
        scan_payload.get("scan_postprocess_dir"),
        str(Path(scan_results_dir) / "postprocess" / "folder_map.json"),
        str(Path(scan_results_dir) / "postprocess" / "tasks.json"),
        "artifacts/autopilot/latest.json",
    ]:
        if p:
            cmd.extend(["--proof", str(p)])

    res = run(cmd, cwd=ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"AI communication packet emission failed: {res.stderr or res.stdout}")
    return Path((res.stdout or "").strip().splitlines()[-1])


def post_obsidian(vault_path: str, title: str, payload: Dict[str, Any]) -> str | None:
    lines = [
        "# Ops Pulse",
        "",
        f"- timestamp: {datetime.now(timezone.utc).isoformat()}Z",
        f"- status: {payload.get('status')}",
        f"- scan_ok: {payload.get('scan', {}).get('ok')}",
        f"- smoke_ok: {payload.get('smoke', {}).get('ok')}",
        "",
        "## Proof",
    ]
    for proof in payload.get("proof", []):
        lines.append(f"- `{proof}`")

    body = "\n".join(lines)
    res = run(
        [
            "python",
            str(OBSIDIAN_TOOL),
            "post-context",
            "--vault",
            vault_path,
            "--folder",
            "Sessions",
            "--title",
            title,
            "--body",
            body,
        ],
        cwd=ROOT,
    )
    if res.returncode != 0:
        return None
    return (res.stdout or "").strip().splitlines()[-1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a free-cost SCBE ops pulse")
    p.add_argument("--scan-name", default="full_codebase", help="Scan label")
    p.add_argument("--skip-smoke", action="store_true", help="Skip local HF smoke run")
    p.add_argument("--obsidian-vault", default="", help="Optional Obsidian vault path")
    p.add_argument("--task-id", default="OPPULSE", help="Task identifier for handoff packet")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    AUTOPILOT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result: Dict[str, Any] = {"run_id": run_id, "status": "in_progress"}

    scan_payload = run_scan(args.scan_name)
    result["scan"] = scan_payload
    if not scan_payload.get("ok"):
        result["status"] = "blocked"
    elif not scan_payload.get("scan_postprocess"):
        result["status"] = "blocked"

    smoke_payload = None
    if not args.skip_smoke:
        smoke_payload = run_smoke()
        result["smoke"] = smoke_payload
        if not smoke_payload.get("ok"):
            result["status"] = "blocked"
    else:
        result["smoke"] = {
            "ok": None,
            "status": "skipped",
            "returncode": 0,
            "stdout": "skipped",
            "stderr": "",
        }

    result["proof"] = [scan_payload.get("scan_dir")]
    scan_results_dir = scan_payload.get("scan_results_dir") or scan_payload.get("scan_dir", "")
    folder_map = str(Path(scan_results_dir) / "postprocess" / "folder_map.json")
    tasks_json = str(Path(scan_results_dir) / "postprocess" / "tasks.json")
    if Path(folder_map).exists():
        result["proof"].append(folder_map)
    if Path(tasks_json).exists():
        result["proof"].append(tasks_json)

    # finalize status for final report and packet contract
    if result["status"] == "in_progress":
        result["status"] = "done"

    try:
        result["packet"] = str(emit_packet(scan_payload, smoke_payload, result["status"], args.task_id))
        result["proof"].append(result["packet"])
    except Exception as exc:
        result["status"] = "blocked"
        result["packet_error"] = str(exc)

    # Keep proof list compact and valid only.
    result["proof"] = [p for p in result.get("proof", []) if p]

    if args.obsidian_vault:
        result["obsidian"] = post_obsidian(
            args.obsidian_vault,
            f"SCBE Ops Pulse {run_id}",
            result,
        ) or "failed"
    if args.obsidian_vault and result.get("obsidian") == "failed":
        result["status"] = "blocked"

    report = AUTOPILOT_DIR / f"{run_id}.json"
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    latest = AUTOPILOT_DIR / "latest.json"
    latest.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"status={result['status']}")
    print(f"report={report}")
    if packet := result.get("packet"):
        print(f"packet={packet}")
    return 0 if result["status"] == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
