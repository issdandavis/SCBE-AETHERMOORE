#!/usr/bin/env python3
"""Prepare public agentic coding benchmark harnesses without heavy runs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "eval" / "public_agentic_benchmark_sources.v1.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "public_agentic_benchmark_setup"
SCHEMA_VERSION = "scbe_public_agentic_benchmark_setup_v1"


@dataclass(frozen=True)
class BenchmarkSource:
    benchmark_id: str
    display_name: str
    official_url: str
    repo_url: str
    local_dir: str
    tool_checks: list[list[str]]
    install_notes: list[str]
    dry_run_command: list[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_sources(path: Path) -> tuple[Path, list[BenchmarkSource]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "scbe_public_agentic_benchmark_sources_v1":
        raise ValueError(f"unsupported source config schema: {payload.get('schema_version')}")
    source_root = REPO_ROOT / str(payload.get("source_root", "external/benchmarks"))
    sources = []
    for row in payload.get("benchmarks", []):
        sources.append(
            BenchmarkSource(
                benchmark_id=str(row["benchmark_id"]),
                display_name=str(row["display_name"]),
                official_url=str(row["official_url"]),
                repo_url=str(row["repo_url"]),
                local_dir=str(row["local_dir"]),
                tool_checks=[[str(part) for part in item] for item in row.get("tool_checks", [])],
                install_notes=[str(item) for item in row.get("install_notes", [])],
                dry_run_command=[str(item) for item in row.get("dry_run_command", [])],
            )
        )
    if not sources:
        raise ValueError("benchmark source config must contain benchmarks")
    return source_root, sources


def _run(command: list[str], cwd: Path, timeout: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "cwd": str(cwd),
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout_tail": proc.stdout[-1200:],
            "stderr_tail": proc.stderr[-1200:],
        }
    except FileNotFoundError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "returncode": 127,
            "ok": False,
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "command": command,
            "cwd": str(cwd),
            "returncode": 126,
            "ok": False,
            "stdout_tail": "",
            "stderr_tail": f"{type(exc).__name__}: {exc}",
        }


def _tool_available(command: str) -> bool:
    return command == "python" or shutil.which(command) is not None


def _clone_or_status(source: BenchmarkSource, source_root: Path) -> dict[str, Any]:
    source_root.mkdir(parents=True, exist_ok=True)
    target = source_root / source.local_dir
    if (target / ".git").exists():
        result = _run(["git", "rev-parse", "HEAD"], cwd=target)
        return {"action": "already_present", "path": str(target), "ok": result["ok"], "head": result["stdout_tail"].strip()}
    return {"action": "clone", "path": str(target), **_run(["git", "clone", "--depth", "1", source.repo_url, str(target)], cwd=REPO_ROOT, timeout=240)}


def _check_cwd(source: BenchmarkSource, source_root: Path, command: list[str]) -> Path:
    local_path = source_root / source.local_dir
    if source.benchmark_id == "aider_polyglot" and local_path.exists() and command[:2] == ["python", "benchmark/benchmark.py"]:
        return local_path
    return REPO_ROOT


def inspect_source(source: BenchmarkSource, source_root: Path, download: bool, run_dry: bool) -> dict[str, Any]:
    local_path = source_root / source.local_dir
    clone_result = _clone_or_status(source, source_root) if download else None
    repo_present = local_path.exists()
    tool_results = []
    for check in source.tool_checks:
        if not check:
            continue
        if not _tool_available(check[0]):
            tool_results.append(
                {
                    "command": check,
                    "cwd": str(_check_cwd(source, source_root, check)),
                    "returncode": 127,
                    "ok": False,
                    "stdout_tail": "",
                    "stderr_tail": f"{check[0]} not found on PATH",
                }
            )
        else:
            tool_results.append(_run(check, cwd=_check_cwd(source, source_root, check)))
    dry_run = None
    if run_dry:
        if source.dry_run_command and _tool_available(source.dry_run_command[0]):
            dry_run = _run(source.dry_run_command, cwd=_check_cwd(source, source_root, source.dry_run_command))
        else:
            dry_run = {
                "command": source.dry_run_command,
                "returncode": 127,
                "ok": False,
                "stdout_tail": "",
                "stderr_tail": "dry-run command unavailable on PATH",
            }
    blockers = []
    if source.benchmark_id in {"terminal_bench", "swe_bench"} and shutil.which("docker") is None:
        blockers.append("Docker is not installed or not on PATH.")
    if source.benchmark_id == "terminal_bench" and shutil.which("tb") is None:
        blockers.append("Terminal-Bench CLI `tb` is not installed.")
    if source.benchmark_id == "swe_bench" and not any(item["ok"] and item["command"][:3] == ["python", "-m", "swebench.harness.run_evaluation"] for item in tool_results):
        blockers.append("SWE-bench Python package is not installed in the active Python environment.")
    if source.benchmark_id == "aider_polyglot" and not repo_present:
        blockers.append("Aider repository is not downloaded; benchmark/benchmark.py is unavailable.")
    if source.benchmark_id == "aider_polyglot" and repo_present and any(not item["ok"] for item in tool_results):
        blockers.append("Aider benchmark Python dependencies are not installed in the active environment.")
    return {
        "benchmark_id": source.benchmark_id,
        "display_name": source.display_name,
        "official_url": source.official_url,
        "repo_url": source.repo_url,
        "local_path": str(local_path),
        "repo_present": repo_present,
        "clone_result": clone_result,
        "tool_checks": tool_results,
        "dry_run": dry_run,
        "install_notes": source.install_notes,
        "blockers": blockers,
        "ready_for_full_run": not blockers and all(item["ok"] for item in tool_results),
    }


def next_steps(results: list[dict[str, Any]]) -> list[str]:
    steps = []
    if any("Docker is not installed or not on PATH." in row["blockers"] for row in results):
        steps.append("Install or enable Docker before full Terminal-Bench or SWE-bench runs.")
    if any(row["benchmark_id"] == "terminal_bench" and "Terminal-Bench CLI `tb` is not installed." in row["blockers"] for row in results):
        steps.append("Install Terminal-Bench CLI in an isolated environment, then rerun this setup dry-run.")
    if any(row["benchmark_id"] == "swe_bench" and "SWE-bench Python package is not installed in the active Python environment." in row["blockers"] for row in results):
        steps.append("Install SWE-bench from its checkout with pip install -e . after Docker is available.")
    if any(row["benchmark_id"] == "aider_polyglot" and not row["repo_present"] for row in results):
        steps.append("Run with --download to shallow-clone Aider before checking benchmark/benchmark.py.")
    if any(row["benchmark_id"] == "aider_polyglot" and "Aider benchmark Python dependencies are not installed in the active environment." in row["blockers"] for row in results):
        steps.append("Install Aider benchmark dependencies in an isolated environment before running Aider Polyglot.")
    if not steps:
        steps.append("All public harness repos/tools are dry-run ready; wire GeoSeal as the agent runtime next.")
    return steps


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Public Agentic Benchmark Setup",
        "",
        f"Generated: `{payload['created_at']}`",
        f"Source root: `{payload['source_root']}`",
        f"Full-run ready: `{payload['full_run_ready']}`",
        "",
        "| Benchmark | Repo Present | Tool Checks | Full Run Ready | Blockers |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["results"]:
        tool_ok = f"{sum(1 for item in row['tool_checks'] if item['ok'])}/{len(row['tool_checks'])}"
        blockers = "; ".join(row["blockers"]) if row["blockers"] else "none"
        lines.append(f"| {row['display_name']} | `{row['repo_present']}` | `{tool_ok}` | `{row['ready_for_full_run']}` | {blockers} |")
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {step}" for step in payload["next_steps"])
    lines.extend(["", "## Sources", ""])
    for row in payload["results"]:
        lines.append(f"- {row['display_name']}: {row['official_url']}")
    return "\n".join(lines) + "\n"


def build_report(config: Path, output_root: Path, download: bool, run_dry: bool) -> dict[str, Any]:
    source_root, sources = load_sources(config)
    results = [inspect_source(source, source_root, download=download, run_dry=run_dry) for source in sources]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "source_root": str(source_root),
        "download": download,
        "run_dry": run_dry,
        "ok": all(row["repo_present"] or not download for row in results),
        "full_run_ready": all(row["ready_for_full_run"] for row in results),
        "results": results,
        "next_steps": next_steps(results),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "latest_setup.json"
    md_path = output_root / "latest_setup.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"payload": payload, "json": str(json_path), "markdown": str(md_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--download", action="store_true", help="Shallow-clone public harness repos into external/benchmarks.")
    parser.add_argument("--dry-run", action="store_true", help="Run available non-mutating help/list commands.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_report(args.config, args.output_root, download=args.download, run_dry=args.dry_run)
    print(json.dumps({"ok": report["payload"]["ok"], "full_run_ready": report["payload"]["full_run_ready"], "json": report["json"], "markdown": report["markdown"], "next_steps": report["payload"]["next_steps"]}, indent=2, sort_keys=True))
    return 0 if report["payload"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
