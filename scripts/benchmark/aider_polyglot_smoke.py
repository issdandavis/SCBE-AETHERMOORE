#!/usr/bin/env python3
"""Run the smallest useful local smoke for the Aider Polyglot benchmark.

This is not a leaderboard run. It verifies that the public Aider harness and
Polyglot exercise checkout are reachable, then optionally runs Aider's
``--no-aider --no-unit-tests`` path so we can keep a cheap evidence packet
before moving full scoring into a container or remote Docker runner.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_AIDER_ROOT = REPO_ROOT / "external" / "benchmarks" / "aider"
DEFAULT_POLYGLOT_ROOT = DEFAULT_AIDER_ROOT / "tmp.benchmarks" / "polyglot-benchmark"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "public_agentic_benchmark_setup" / "aider_polyglot"
POLYGLOT_REPO_URL = "https://github.com/Aider-AI/polyglot-benchmark.git"
SCHEMA_VERSION = "scbe_aider_polyglot_smoke_v1"

UV_DEPS = [
    "importlib_resources",
    "GitPython",
    "lox",
    "pandas",
    "typer",
    "python-dotenv",
    "rich",
    "matplotlib",
    "imgcat",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(command: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
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
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
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
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "returncode": 124,
            "ok": False,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else f"timeout after {timeout}s",
        }


def _clone_polyglot(polyglot_root: Path) -> dict[str, Any] | None:
    if (polyglot_root / ".git").exists():
        return {"action": "already_present", "path": str(polyglot_root), "ok": True}
    polyglot_root.parent.mkdir(parents=True, exist_ok=True)
    return _run(["git", "clone", "--depth", "1", POLYGLOT_REPO_URL, str(polyglot_root)], cwd=REPO_ROOT, timeout=240)


def _uv_python_command(python_version: str, aider_root: Path, args: list[str]) -> list[str]:
    command = ["uv", "run", "--no-project", "--python", python_version, "--with-editable", "."]
    for dep in UV_DEPS:
        command.extend(["--with", dep])
    command.extend(["python", "benchmark/benchmark.py"])
    command.extend(args)
    return command


def inspect_polyglot(polyglot_root: Path) -> dict[str, Any]:
    expected_languages = ["cpp", "go", "java", "javascript", "python", "rust"]
    languages = []
    file_count = 0
    if polyglot_root.exists():
        for language in expected_languages:
            language_path = polyglot_root / language
            if language_path.is_dir():
                languages.append(language)
        file_count = sum(1 for item in polyglot_root.rglob("*") if item.is_file())
    return {
        "path": str(polyglot_root),
        "present": polyglot_root.exists(),
        "expected_languages": expected_languages,
        "languages_present": languages,
        "language_count": len(languages),
        "file_count": file_count,
        "complete_language_set": set(languages) == set(expected_languages),
    }


def build_geoseal_adapter_preflight(polyglot: dict[str, Any], num_tests: int) -> dict[str, Any]:
    """Build a deterministic SCBE gate packet before any scored Aider run."""
    from src.coding_spine.command_compiler import compile_intent_to_plan

    selected_languages = list(polyglot.get("languages_present") or [])
    intent = (
        "Run a tiny Aider Polyglot coding benchmark slice through a GeoSeal-controlled "
        f"agent adapter; num_tests={num_tests}; languages={','.join(selected_languages) or 'none'}"
    )
    plan = compile_intent_to_plan(
        intent=intent,
        permission_mode="observe",
        preferred_language="python",
        requested_tool="read",
    )
    contract = {
        "benchmark": "aider_polyglot",
        "adapter": "geoseal_agent_adapter_preflight",
        "permission_mode": "observe",
        "selected_languages": selected_languages,
        "num_tests": num_tests,
        "requires_container_for_scored_run": True,
        "must_capture": [
            "model",
            "edit_format",
            "num_tests",
            "exercise_dir",
            "run_dir",
            "stats_file",
            "aider_results_json",
            "chat_history",
        ],
    }
    contract_sha = sha256(json.dumps(contract, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema_version": "scbe_geoseal_aider_adapter_preflight_v1",
        "ok": bool(polyglot.get("complete_language_set") and plan["policy"].get("ok")),
        "contract": contract,
        "policy": plan["policy"],
        "command": plan["command"],
        "plan_sha256": plan["hashes"]["plan_sha256"],
        "contract_sha256": contract_sha,
    }


def build_report(
    aider_root: Path = DEFAULT_AIDER_ROOT,
    polyglot_root: Path = DEFAULT_POLYGLOT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    execute: bool = False,
    download_polyglot: bool = False,
    python_version: str = "3.12",
    num_tests: int = 1,
) -> dict[str, Any]:
    aider_repo_present = (aider_root / "benchmark" / "benchmark.py").exists()
    clone_polyglot_result = None
    if download_polyglot and not polyglot_root.exists():
        clone_polyglot_result = _clone_polyglot(polyglot_root)
    polyglot = inspect_polyglot(polyglot_root)
    geoseal_preflight = build_geoseal_adapter_preflight(polyglot, num_tests)
    uv_present = shutil.which("uv") is not None

    help_result = None
    smoke_result = None
    if execute and aider_repo_present and uv_present:
        help_result = _run(_uv_python_command(python_version, aider_root, ["--help"]), cwd=aider_root, timeout=300)
        smoke_args = [
            "scbe-smoke",
            "--no-aider",
            "--no-unit-tests",
            "--num-tests",
            str(num_tests),
            "--threads",
            "1",
            "--exercises-dir",
            str(Path("tmp.benchmarks") / "polyglot-benchmark"),
        ]
        smoke_result = _run(_uv_python_command(python_version, aider_root, smoke_args), cwd=aider_root, timeout=600)

    blockers = []
    if execute and not uv_present:
        blockers.append("uv is not installed or not on PATH.")
    if not aider_repo_present:
        blockers.append("Aider checkout is missing benchmark/benchmark.py.")
    if not polyglot["present"]:
        blockers.append("Aider Polyglot exercise checkout is missing.")
    elif not polyglot["complete_language_set"]:
        blockers.append("Aider Polyglot checkout is missing one or more expected language directories.")
    if not geoseal_preflight["ok"]:
        blockers.append("GeoSeal adapter preflight did not pass.")
    if help_result is not None and not help_result["ok"]:
        blockers.append("Aider benchmark --help failed in the isolated uv environment.")
    if smoke_result is not None and not smoke_result["ok"]:
        blockers.append("Aider no-model/no-unit-tests smoke failed.")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "ok": not blockers,
        "execute": execute,
        "download_polyglot": download_polyglot,
        "aider_root": str(aider_root),
        "aider_repo_present": aider_repo_present,
        "polyglot_repo_url": POLYGLOT_REPO_URL,
        "clone_polyglot_result": clone_polyglot_result,
        "polyglot": polyglot,
        "geoseal_adapter_preflight": geoseal_preflight,
        "uv_present": uv_present,
        "python_version": python_version,
        "num_tests": num_tests,
        "help_result": help_result,
        "smoke_result": smoke_result,
        "full_scoring_ready": False,
        "claim_allowed": "Local Aider Polyglot command-shape and dataset smoke only; not a public leaderboard score.",
        "limits": [
            "Aider's benchmark README recommends container isolation because generated code is untrusted.",
            "This smoke uses --no-aider and --no-unit-tests, so it does not measure coding quality.",
            "Full scoring needs a selected model/provider, budget, logs, patches, and containerized execution.",
        ],
        "next_steps": [
            "Run scored Aider Polyglot only after this GeoSeal adapter preflight is attached to the artifact packet.",
            "Convert the GeoSeal preflight contract into the scored-run adapter wrapper.",
            "Keep full Aider Polyglot scoring out of the local disk lane unless Docker and space are available.",
        ],
        "blockers": blockers,
    }

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "latest_aider_polyglot_smoke.json"
    md_path = output_root / "latest_aider_polyglot_smoke.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"payload": payload, "json": str(json_path), "markdown": str(md_path)}


def render_markdown(payload: dict[str, Any]) -> str:
    help_ok = None if payload["help_result"] is None else payload["help_result"]["ok"]
    smoke_ok = None if payload["smoke_result"] is None else payload["smoke_result"]["ok"]
    preflight = payload["geoseal_adapter_preflight"]
    lines = [
        "# Aider Polyglot Smoke",
        "",
        f"Generated: `{payload['created_at']}`",
        f"OK: `{payload['ok']}`",
        f"Executed: `{payload['execute']}`",
        f"Aider checkout: `{payload['aider_repo_present']}`",
        f"Polyglot checkout: `{payload['polyglot']['present']}`",
        f"Languages: `{payload['polyglot']['language_count']}/6`",
        f"Help check: `{help_ok}`",
        f"No-model smoke: `{smoke_ok}`",
        f"GeoSeal adapter preflight: `{preflight['ok']}`",
        f"Full scoring ready: `{payload['full_scoring_ready']}`",
        "",
        "## Claim",
        "",
        payload["claim_allowed"],
        "",
        "## Limits",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["limits"])
    lines.extend(
        [
            "",
            "## GeoSeal Adapter Preflight",
            "",
            f"- schema: `{preflight['schema_version']}`",
            f"- policy: `{preflight['policy']['decision']}`",
            f"- command: `{preflight['command']['key']}`",
            f"- contract_sha256: `{preflight['contract_sha256']}`",
        ]
    )
    if payload["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {item}" for item in payload["blockers"])
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in payload["next_steps"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aider-root", type=Path, default=DEFAULT_AIDER_ROOT)
    parser.add_argument("--polyglot-root", type=Path, default=DEFAULT_POLYGLOT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--execute", action="store_true", help="Run help and no-model/no-unit-tests smoke commands.")
    parser.add_argument(
        "--download-polyglot", action="store_true", help="Clone Aider-AI/polyglot-benchmark when missing."
    )
    parser.add_argument("--python", default="3.12", help="Python version passed to uv run.")
    parser.add_argument("--num-tests", type=int, default=1)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_report(
        aider_root=args.aider_root,
        polyglot_root=args.polyglot_root,
        output_root=args.output_root,
        execute=args.execute,
        download_polyglot=args.download_polyglot,
        python_version=args.python,
        num_tests=args.num_tests,
    )
    payload = report["payload"]
    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "execute": payload["execute"],
                "json": report["json"],
                "markdown": report["markdown"],
                "full_scoring_ready": payload["full_scoring_ready"],
                "blockers": payload["blockers"],
                "claim_allowed": payload["claim_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
