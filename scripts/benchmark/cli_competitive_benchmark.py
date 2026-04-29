#!/usr/bin/env python3
"""Benchmark SCBE CLI surfaces against common agentic CLI expectations.

This is a local, evidence-first comparison. Peer CLI capabilities are recorded
from official documentation/source notes, while SCBE scores are backed by local
commands and generated artifacts.
"""

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
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "cli_competitive"

CRITERIA = [
    "help",
    "version",
    "doctor",
    "machine_json",
    "local_repo_actions",
    "workflow_runner",
    "permission_model",
    "custom_commands",
    "mcp_or_tool_extensibility",
    "session_state",
    "benchmark_artifacts",
]

PEER_BASELINES: dict[str, dict[str, Any]] = {
    "codex": {
        "source": "https://help.openai.com/en/articles/11096431-openai-codex-ci-getting-started",
        "capabilities": {
            "help": True,
            "version": True,
            "doctor": False,
            "machine_json": True,
            "local_repo_actions": True,
            "workflow_runner": True,
            "permission_model": True,
            "custom_commands": False,
            "mcp_or_tool_extensibility": True,
            "session_state": True,
            "benchmark_artifacts": False,
        },
        "notes": "Official docs emphasize local code reading/editing/running and approval modes.",
    },
    "claude": {
        "source": "https://docs.claude.com/en/docs/claude-code/slash-commands",
        "capabilities": {
            "help": True,
            "version": True,
            "doctor": True,
            "machine_json": True,
            "local_repo_actions": True,
            "workflow_runner": True,
            "permission_model": True,
            "custom_commands": True,
            "mcp_or_tool_extensibility": True,
            "session_state": True,
            "benchmark_artifacts": False,
        },
        "notes": "Slash commands include /doctor, /permissions, /mcp, /agents, /memory, /review, and custom commands.",
    },
    "gemini": {
        "source": "https://geminicli.com/docs/reference/commands",
        "capabilities": {
            "help": True,
            "version": True,
            "doctor": False,
            "machine_json": True,
            "local_repo_actions": True,
            "workflow_runner": True,
            "permission_model": True,
            "custom_commands": True,
            "mcp_or_tool_extensibility": True,
            "session_state": True,
            "benchmark_artifacts": False,
        },
        "notes": "Command reference emphasizes session commands, settings, shell mode, and tool-oriented operation.",
    },
    "aider": {
        "source": "https://aider.chat/docs/usage/commands.html",
        "capabilities": {
            "help": True,
            "version": True,
            "doctor": False,
            "machine_json": False,
            "local_repo_actions": True,
            "workflow_runner": True,
            "permission_model": True,
            "custom_commands": True,
            "mcp_or_tool_extensibility": False,
            "session_state": True,
            "benchmark_artifacts": False,
        },
        "notes": "In-chat slash commands and git-centered code editing are the main comparison points.",
    },
}


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "ok": self.ok,
            "stdout_preview": self.stdout[:1200],
            "stderr_preview": self.stderr[:1200],
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(command: list[str], timeout: int = 30) -> CommandResult:
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return CommandResult(command, proc.returncode, proc.stdout, proc.stderr)
    except Exception as exc:  # pragma: no cover - defensive artifact capture
        return CommandResult(command, 127, "", f"{type(exc).__name__}: {exc}")


def _json_from_stdout(result: CommandResult) -> dict[str, Any]:
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _score(capabilities: dict[str, bool]) -> dict[str, Any]:
    passed = sum(1 for name in CRITERIA if capabilities.get(name) is True)
    return {
        "passed": passed,
        "total": len(CRITERIA),
        "score": round(passed / len(CRITERIA), 3),
    }


def benchmark_scbe() -> dict[str, Any]:
    geoseal = REPO_ROOT / "bin" / "geoseal.cjs"
    commands = {
        "geoseal_help": _run(["node", str(geoseal), "--help"]),
        "geoseal_version": _run(["node", str(geoseal), "version"]),
        "geoseal_doctor": _run(["node", str(geoseal), "doctor", "--json"]),
        "geoseal_status_without_service": _run(
            ["node", str(geoseal), "status", "--json"]
        ),
        "scbe_cli_help": _run(["python", "scbe-cli.py", "--help"]),
    }
    doctor = _json_from_stdout(commands["geoseal_doctor"])
    status_error = _json_from_stdout(commands["geoseal_status_without_service"])
    command_help = commands["geoseal_help"].stdout

    capabilities = {
        "help": commands["geoseal_help"].ok and commands["scbe_cli_help"].ok,
        "version": commands["geoseal_version"].ok
        and bool(commands["geoseal_version"].stdout.strip()),
        "doctor": commands["geoseal_doctor"].ok and doctor.get("ok") is True,
        "machine_json": doctor.get("ok") is True
        and status_error.get("error") == "api_command_requires_service",
        "local_repo_actions": "agent" in commands["scbe_cli_help"].stdout
        or "cursor" in doctor.get("python_modules", [{}])[0].get("stdout_preview", ""),
        "workflow_runner": "workflow"
        in doctor.get("python_modules", [{}])[0].get("stdout_preview", ""),
        "permission_model": "max-tier"
        in doctor.get("python_modules", [{}])[0].get("stdout_preview", ""),
        "custom_commands": False,
        "mcp_or_tool_extensibility": "nexus-dispatch" in command_help
        or "orchestrator-dispatch" in command_help,
        "session_state": "service-output-dir" in command_help
        or "active_service" in doctor,
        "benchmark_artifacts": True,
    }
    gaps = [name for name in CRITERIA if not capabilities.get(name)]
    improvements = [
        {
            "gap": "custom_commands",
            "recommendation": "Add a repo-local .geoseal/commands/*.md prompt-command loader similar to slash-command CLIs.",
        },
        {
            "gap": "permission_model",
            "recommendation": "Promote max-tier/forbid-provider into a visible geoseal permissions command and persisted profile.",
        },
        {
            "gap": "help_accuracy",
            "recommendation": "Separate API-only examples from local passthrough commands and add tests for advertised commands.",
        },
    ]
    return {
        "name": "scbe-geoseal",
        "score": _score(capabilities),
        "capabilities": capabilities,
        "gaps": gaps,
        "improvements": improvements,
        "commands": {name: result.to_dict() for name, result in commands.items()},
    }


def benchmark_peers() -> list[dict[str, Any]]:
    peers = []
    for name, baseline in PEER_BASELINES.items():
        version_cmd = (
            _run([name, "--version"])
            if shutil.which(name)
            else CommandResult([name, "--version"], 127, "", "not installed")
        )
        peers.append(
            {
                "name": name,
                "installed": version_cmd.returncode != 127,
                "local_version_probe": version_cmd.to_dict(),
                "score": _score(baseline["capabilities"]),
                "capabilities": baseline["capabilities"],
                "source": baseline["source"],
                "notes": baseline["notes"],
            }
        )
    return peers


def build_report() -> dict[str, Any]:
    scbe = benchmark_scbe()
    peers = benchmark_peers()
    ranking = sorted(
        [scbe, *peers], key=lambda item: item["score"]["score"], reverse=True
    )
    return {
        "schema_version": "scbe_cli_competitive_benchmark_v1",
        "created_at": _utc_now(),
        "criteria": CRITERIA,
        "scbe": scbe,
        "peers": peers,
        "ranking": [{"name": item["name"], **item["score"]} for item in ranking],
        "highest_value_next_steps": [
            "Add command accuracy tests so help examples cannot drift away from implemented commands.",
            "Add a visible permissions profile command.",
            "Add repo-local custom commands for repeatable SCBE workflows.",
        ],
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE CLI Competitive Benchmark",
        "",
        f"Generated: `{report['created_at']}`",
        "",
        "## Ranking",
        "",
        "| CLI | Score | Passed | Total |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in report["ranking"]:
        lines.append(
            f"| {row['name']} | {row['score']} | {row['passed']} | {row['total']} |"
        )
    lines.extend(["", "## SCBE Gaps", ""])
    for gap in report["scbe"]["gaps"]:
        lines.append(f"- `{gap}`")
    lines.extend(["", "## Recommended Improvements", ""])
    for item in report["scbe"]["improvements"]:
        lines.append(f"- `{item['gap']}`: {item['recommendation']}")
    lines.extend(["", "## Sources", ""])
    for peer in report["peers"]:
        lines.append(f"- {peer['name']}: {peer['source']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark SCBE CLI against peer CLI patterns."
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report = build_report()
    json_path = out_dir / "cli_competitive_benchmark_latest.json"
    md_path = out_dir / "cli_competitive_benchmark_latest.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(
        json.dumps(
            {
                "ok": True,
                "json": str(json_path),
                "markdown": str(md_path),
                "ranking": report["ranking"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
