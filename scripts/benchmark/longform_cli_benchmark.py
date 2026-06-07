#!/usr/bin/env python3
"""Benchmark the SCBE Longform Bridge CLI surface.

This is intentionally local-only. It exercises the public `scbe` CLI wrapper,
then scores the result on evidence-bearing behavior:

- command surface availability
- hash-chain validity
- landing and resume pack creation
- tamper detection
- practical execution depth
- headed/headless CLI parity

Execution depth requires real local/offline agent-bus dispatch receipts; it
must not pass on recorded stubs. Headed/headless parity requires human output
to expose the same key state that JSON automation reads.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "packages" / "cli" / "bin" / "scbe.js"
ARTIFACT_DIR = ROOT / "artifacts" / "benchmarks"


@dataclass
class CommandResult:
    command: list[str]
    cwd: str
    ok: bool
    status: int
    elapsed_ms: float
    stdout: str
    stderr: str

    def json_body(self) -> dict[str, Any]:
        return json.loads(self.stdout)

    def preview(self, limit: int = 600) -> dict[str, Any]:
        return {
            "command": self.command,
            "cwd": self.cwd,
            "ok": self.ok,
            "status": self.status,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "stdout_preview": self.stdout[:limit],
            "stderr_preview": self.stderr[:limit],
        }


def run_scbe(workspace: Path, *args: str, timeout: int = 30) -> CommandResult:
    started = time.perf_counter()
    proc = subprocess.run(
        ["node", str(CLI), *args],
        cwd=workspace,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env={**os.environ, "NO_COLOR": "1"},
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return CommandResult(
        command=["scbe", *args],
        cwd=str(workspace),
        ok=proc.returncode == 0,
        status=proc.returncode,
        elapsed_ms=elapsed_ms,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def mutate_second_ledger_event(workspace: Path) -> bool:
    ledger_path = workspace / ".scbe-longform" / "ledger.jsonl"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        return False
    event = json.loads(lines[1])
    event.setdefault("payload", {})["tamper_probe"] = "mutated by benchmark"
    lines[1] = json.dumps(event)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def mutate_latest_landing(workspace: Path) -> bool:
    landing_dir = workspace / ".scbe-longform" / "landings"
    files = sorted(landing_dir.glob("*.json"))
    if not files:
        return False
    target = files[-1]
    landing = json.loads(target.read_text(encoding="utf-8"))
    landing["principles"]["mission"] = "tampered mission"
    target.write_text(json.dumps(landing, indent=2), encoding="utf-8")
    return True


def score(report: dict[str, Any]) -> dict[str, Any]:
    checks = report["checks"]
    weights = {
        "command_surface": 15,
        "chain_integrity": 20,
        "landing_resume": 20,
        "tamper_detection": 20,
        "latency": 10,
        "execution_depth": 15,
        "headed_headless_parity": 10,
    }
    earned = {
        "command_surface": (
            weights["command_surface"] if checks["command_surface"]["ok"] else 0
        ),
        "chain_integrity": (
            weights["chain_integrity"] if checks["chain_integrity"]["ok"] else 0
        ),
        "landing_resume": (
            weights["landing_resume"] if checks["landing_resume"]["ok"] else 0
        ),
        "tamper_detection": (
            weights["tamper_detection"] if checks["tamper_detection"]["ok"] else 0
        ),
        "latency": (
            weights["latency"]
            if checks["latency"]["p95_ms"] < 1000
            else 5 if checks["latency"]["p95_ms"] < 3000 else 0
        ),
        "execution_depth": (
            weights["execution_depth"]
            if checks["execution_depth"]["actual_tool_or_bus_dispatch"]
            else 0
        ),
        "headed_headless_parity": (
            weights["headed_headless_parity"]
            if checks["headed_headless_parity"]["ok"]
            else 0
        ),
    }
    total = sum(weights.values())
    got = sum(earned.values())
    blockers = []
    if earned["execution_depth"] == 0:
        blockers.append(
            "Squad/task execution did not produce enabled local/offline dispatch receipts."
        )
    if earned["headed_headless_parity"] == 0:
        blockers.append(
            "Headed CLI output does not expose the same key workflow state as headless JSON."
        )
    if not checks["tamper_detection"]["ok"]:
        blockers.append("Tamper detection did not trip as expected.")
    return {
        "earned": earned,
        "weights": weights,
        "score": got / total,
        "score_percent": round((got / total) * 100, 2),
        "blockers": blockers,
    }


def run_benchmark(keep_workspace: bool = False) -> dict[str, Any]:
    tmp_root = Path(tempfile.mkdtemp(prefix="scbe-longform-bench-"))
    workspace = tmp_root / "workspace"
    workspace.mkdir()

    commands: list[dict[str, Any]] = []

    init = run_scbe(
        workspace,
        "work",
        "init",
        "--mission",
        "Benchmark durable agentic CLI",
        "--invariant",
        "hash chain remains valid",
        "--claim",
        "benchmark reports only observed behavior",
        "--json",
    )
    commands.append(init.preview())

    spawn = run_scbe(
        workspace,
        "agent",
        "spawn",
        "tester",
        "--mandate",
        "verify longform bridge receipts",
        "--tools",
        "read,test,verify",
        "--budget",
        "4",
        "--json",
    )
    commands.append(spawn.preview())

    do = run_scbe(
        workspace,
        "do",
        "build a benchmark adapter and prove it",
        "--loops",
        "3",
        "--land-every-stage",
        "--squad",
        "--json",
    )
    commands.append(do.preview())
    status_runs = [run_scbe(workspace, "work", "status", "--json") for _ in range(7)]
    commands.extend(item.preview() for item in status_runs)
    status_body = status_runs[-1].json_body() if status_runs[-1].ok else {}

    land_list = run_scbe(workspace, "land", "list", "--json")
    commands.append(land_list.preview())
    land_body = land_list.json_body() if land_list.ok else {}
    first_hash = ""
    if land_body.get("landings"):
        first_hash = land_body["landings"][0]["hash"][:12]

    resume = run_scbe(workspace, "work", "resume", "--hash", first_hash, "--json")
    commands.append(resume.preview())
    resume_body = resume.json_body() if resume.ok else {}

    parity_status = run_scbe(workspace, "work", "status", "--json")
    commands.append(parity_status.preview())
    parity_status_body = parity_status.json_body() if parity_status.ok else {}
    headed_status = run_scbe(workspace, "work", "status")
    commands.append(headed_status.preview())
    headed_land_list = run_scbe(workspace, "land", "list")
    commands.append(headed_land_list.preview())

    tamper_workspace = tmp_root / "tamper-workspace"
    shutil.copytree(workspace, tamper_workspace)
    ledger_mutated = mutate_second_ledger_event(tamper_workspace)
    tamper_status = run_scbe(tamper_workspace, "work", "status", "--json")
    commands.append(tamper_status.preview())
    tamper_status_body = (
        tamper_status.json_body() if tamper_status.stdout.startswith("{") else {}
    )

    landing_tamper_workspace = tmp_root / "landing-tamper-workspace"
    shutil.copytree(workspace, landing_tamper_workspace)
    landing_mutated = mutate_latest_landing(landing_tamper_workspace)
    landing_tamper_list = run_scbe(landing_tamper_workspace, "land", "list", "--json")
    commands.append(landing_tamper_list.preview())
    landing_tamper_body = (
        landing_tamper_list.json_body() if landing_tamper_list.ok else {}
    )

    status_latencies = [item.elapsed_ms for item in status_runs]
    ledger_lines = (
        (workspace / ".scbe-longform" / "ledger.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    ledger_events = [json.loads(line) for line in ledger_lines if line.strip()]
    stage_events = [
        event for event in ledger_events if event.get("kind") == "stage_complete"
    ]
    dispatch_events = [
        event for event in ledger_events if event.get("kind") == "agentbus_dispatch"
    ]
    stubbed_stage_count = sum(
        event.get("payload", {}).get("status") == "stub" for event in stage_events
    )
    dispatched_stage_count = sum(
        event.get("payload", {}).get("status") == "dispatched" for event in stage_events
    )
    dispatch_enabled_count = sum(
        event.get("payload", {}).get("dispatch", {}).get("enabled") is True
        for event in dispatch_events
    )

    checks = {
        "command_surface": {
            "ok": all(item.ok for item in [init, spawn, do, land_list, resume])
            and bool(first_hash),
            "commands_checked": [
                "work init",
                "agent spawn",
                "do",
                "land list",
                "work resume",
            ],
        },
        "chain_integrity": {
            "ok": bool(status_body.get("chain_valid")),
            "brick_count": status_body.get("brick_count"),
            "event_count": status_body.get("event_count"),
        },
        "landing_resume": {
            "ok": bool(
                land_body.get("count", 0) >= 1 and resume_body.get("resume_pack_path")
            ),
            "landing_count": land_body.get("count", 0),
            "resume_pack_path": resume_body.get("resume_pack_path"),
        },
        "tamper_detection": {
            "ok": bool(
                ledger_mutated
                and tamper_status_body.get("chain_valid") is False
                and landing_mutated
                and any(
                    item.get("verified") is False
                    for item in landing_tamper_body.get("landings", [])
                )
            ),
            "ledger_mutated": ledger_mutated,
            "chain_valid_after_ledger_mutation": tamper_status_body.get("chain_valid"),
            "landing_mutated": landing_mutated,
            "landing_verified_values": [
                item.get("verified") for item in landing_tamper_body.get("landings", [])
            ],
        },
        "latency": {
            "status_runs": len(status_runs),
            "median_ms": round(median(status_latencies), 3),
            "p95_ms": round(percentile(status_latencies, 95), 3),
            "max_ms": round(max(status_latencies), 3),
        },
        "execution_depth": {
            "stage_complete_count": len(stage_events),
            "agentbus_dispatch_count": len(dispatch_events),
            "stubbed_stage_count": stubbed_stage_count,
            "dispatched_stage_count": dispatched_stage_count,
            "dispatch_enabled_count": dispatch_enabled_count,
            "actual_tool_or_bus_dispatch": dispatched_stage_count == len(stage_events)
            and dispatch_enabled_count == len(stage_events)
            and len(stage_events) > 0,
        },
        "headed_headless_parity": {
            "ok": bool(
                headed_status.ok
                and headed_land_list.ok
                and "SCBE Longform Workspace Status" in headed_status.stdout
                and "chain valid:" in headed_status.stdout
                and str(parity_status_body.get("event_count")) in headed_status.stdout
                and str(parity_status_body.get("brick_count")) in headed_status.stdout
                and str(land_body.get("count", 0)) not in ("0", "")
                and first_hash in headed_land_list.stdout
                and "Bricks" in headed_land_list.stdout
            ),
            "headless_status_keys": (
                sorted(parity_status_body.keys())
                if isinstance(parity_status_body, dict)
                else []
            ),
            "headed_status_has_chain": "chain valid:" in headed_status.stdout,
            "headed_status_has_counts": bool(
                str(parity_status_body.get("event_count")) in headed_status.stdout
                and str(parity_status_body.get("brick_count")) in headed_status.stdout
            ),
            "headed_land_has_landing_hash": first_hash in headed_land_list.stdout,
        },
    }

    report = {
        "schema_version": "scbe.longform_cli_benchmark.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repo": str(ROOT),
        "cli": str(CLI),
        "workspace": str(workspace) if keep_workspace else None,
        "checks": checks,
        "commands": commands,
    }
    report["score"] = score(report)

    if not keep_workspace:
        shutil.rmtree(tmp_root, ignore_errors=True)

    return report


def render_markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    command_surface = checks["command_surface"]
    chain = checks["chain_integrity"]
    landing = checks["landing_resume"]
    tamper = checks["tamper_detection"]
    latency = checks["latency"]
    execution = checks["execution_depth"]
    parity = checks["headed_headless_parity"]
    lines = [
        "# SCBE Longform CLI Benchmark",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Score: **{report['score']['score_percent']}%**",
        "",
        "| Gate | Result | Evidence |",
        "|---|---:|---|",
        (
            f"| Command surface | {command_surface['ok']} | "
            f"{', '.join(command_surface['commands_checked'])} |"
        ),
        (
            f"| Chain integrity | {chain['ok']} | "
            f"events={chain['event_count']}, bricks={chain['brick_count']} |"
        ),
        f"| Landing/resume | {landing['ok']} | landings={landing['landing_count']} |",
        (
            f"| Tamper detection | {tamper['ok']} | "
            f"chain_after_tamper={tamper['chain_valid_after_ledger_mutation']}, "
            f"landing_verified={tamper['landing_verified_values']} |"
        ),
        (
            f"| Latency | p95 {latency['p95_ms']} ms | "
            f"median={latency['median_ms']} ms, max={latency['max_ms']} ms |"
        ),
        (
            f"| Execution depth | {execution['actual_tool_or_bus_dispatch']} | "
            f"dispatched={execution['dispatched_stage_count']}, "
            f"dispatch_receipts={execution['agentbus_dispatch_count']}, "
            f"stubbed={execution['stubbed_stage_count']} |"
        ),
        (
            f"| Headed/headless parity | {parity['ok']} | "
            f"headed_status_chain={parity['headed_status_has_chain']}, "
            f"headed_counts={parity['headed_status_has_counts']}, "
            f"headed_landing_hash={parity['headed_land_has_landing_hash']} |"
        ),
        "",
        "## Blockers",
        "",
    ]
    if report["score"]["blockers"]:
        lines.extend(f"- {item}" for item in report["score"]["blockers"])
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(ARTIFACT_DIR))
    parser.add_argument("--keep-workspace", action="store_true")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Accepted for scbe bench compatibility; output is JSON by default",
    )
    args = parser.parse_args()

    report = run_benchmark(keep_workspace=args.keep_workspace)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"longform_cli_benchmark_{stamp}.json"
    md_path = out_dir / f"longform_cli_benchmark_{stamp}.md"
    latest_json = out_dir / "longform_cli_benchmark_latest.json"
    latest_md = out_dir / "longform_cli_benchmark_latest.md"

    json_text = json.dumps(report, indent=2)
    md_text = render_markdown(report)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(md_text + "\n", encoding="utf-8")
    latest_json.write_text(json_text + "\n", encoding="utf-8")
    latest_md.write_text(md_text + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": not report["score"]["blockers"],
                "score_percent": report["score"]["score_percent"],
                "json": str(json_path),
                "markdown": str(md_path),
                "latest_json": str(latest_json),
                "latest_markdown": str(latest_md),
                "blockers": report["score"]["blockers"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
