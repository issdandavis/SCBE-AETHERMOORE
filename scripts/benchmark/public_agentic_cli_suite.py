#!/usr/bin/env python3
"""Build a public-evidence benchmark packet for GeoSeal as an agentic CLI.

This runner is intentionally conservative. It can prove the local GeoSeal CLI
surface today, and it records Terminal-Bench, SWE-bench, and Aider Polyglot as
public tracks that must use official adapters before any all-around claim.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "eval" / "public_agentic_cli_suite.v1.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "public_agentic_cli_suite"
SCHEMA_VERSION = "scbe_public_agentic_cli_suite_report_v1"


@dataclass(frozen=True)
class Track:
    track_id: str
    family: str
    official_url: str
    description: str
    claim_level: str
    adapter_status: str
    required_for_public_all_around_claim: bool
    run_command: list[str]
    expected_artifacts: list[str]
    primary_metric: str
    pass_threshold: float | None
    cost_tier: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if payload.get("schema_version") != "scbe_public_agentic_cli_suite_config_v1":
        raise ValueError(f"unsupported public suite config schema: {payload.get('schema_version')}")
    return payload


def load_tracks(config: dict[str, Any]) -> list[Track]:
    tracks: list[Track] = []
    seen: set[str] = set()
    for row in config.get("tracks", []):
        track_id = str(row["track_id"])
        if track_id in seen:
            raise ValueError(f"duplicate track_id: {track_id}")
        seen.add(track_id)
        command = row.get("run_command", [])
        if not isinstance(command, list) or not all(isinstance(part, str) and part for part in command):
            raise ValueError(f"{track_id}: run_command must be non-empty list[str]")
        tracks.append(
            Track(
                track_id=track_id,
                family=str(row["family"]),
                official_url=str(row["official_url"]),
                description=str(row["description"]),
                claim_level=str(row["claim_level"]),
                adapter_status=str(row["adapter_status"]),
                required_for_public_all_around_claim=bool(row.get("required_for_public_all_around_claim", False)),
                run_command=command,
                expected_artifacts=[str(item) for item in row.get("expected_artifacts", [])],
                primary_metric=str(row["primary_metric"]),
                pass_threshold=(None if row.get("pass_threshold") is None else float(row["pass_threshold"])),
                cost_tier=str(row["cost_tier"]),
            )
        )
    if not tracks:
        raise ValueError("public suite config must define at least one track")
    return tracks


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def dirty_worktree() -> bool:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return bool(proc.stdout.strip()) if proc.returncode == 0 else True


def _run(command: list[str], execute: bool, timeout: int) -> dict[str, Any]:
    if not execute:
        return {
            "executed": False,
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
        }
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
    return {
        "executed": True,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def _score_geoseal_cli_competitive() -> dict[str, Any]:
    path = REPO_ROOT / "artifacts" / "benchmarks" / "cli_competitive" / "cli_competitive_benchmark_latest.json"
    if not path.exists():
        return {"score": None, "passed": None, "total": None, "source": str(path)}
    payload = _load_json(path)
    score = payload.get("scbe", {}).get("score", {})
    return {
        "score": score.get("score"),
        "passed": score.get("passed"),
        "total": score.get("total"),
        "source": str(path),
    }


def _artifact_state(paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for item in paths:
        path = REPO_ROOT / item
        rows.append(
            {
                "path": item,
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    return rows


def _external_smoke_state(track_id: str) -> dict[str, Any]:
    if track_id == "aider_polyglot":
        path = (
            REPO_ROOT
            / "artifacts"
            / "public_agentic_benchmark_setup"
            / "aider_polyglot"
            / "latest_aider_polyglot_smoke.json"
        )
        if not path.exists():
            return {"available": False, "source": str(path)}
        payload = _load_json(path)
        return {
            "available": True,
            "source": str(path),
            "ok": bool(payload.get("ok")),
            "execute": bool(payload.get("execute")),
            "full_scoring_ready": bool(payload.get("full_scoring_ready")),
            "claim_allowed": payload.get("claim_allowed"),
        }
    if track_id in {"terminal_bench", "swe_bench_verified_or_lite"}:
        path = REPO_ROOT / "artifacts" / "public_agentic_benchmark_setup" / "latest_setup.json"
        if not path.exists():
            return {"available": False, "source": str(path)}
        payload = _load_json(path)
        setup_id = "swe_bench" if track_id == "swe_bench_verified_or_lite" else track_id
        row = next((item for item in payload.get("results", []) if item.get("benchmark_id") == setup_id), None)
        return {
            "available": row is not None,
            "source": str(path),
            "repo_present": bool(row.get("repo_present")) if row else False,
            "ready_for_full_run": bool(row.get("ready_for_full_run")) if row else False,
            "blockers": row.get("blockers", []) if row else ["setup row missing"],
        }
    return {"available": False, "source": None}


def run_track(track: Track, execute: bool, timeout: int) -> dict[str, Any]:
    command_result = _run(track.run_command, execute=execute, timeout=timeout)
    artifacts = _artifact_state(track.expected_artifacts)
    score: dict[str, Any] = {"score": None}
    if track.track_id == "geoseal_cli_competitive" and command_result["executed"]:
        score = _score_geoseal_cli_competitive()
    adapter_wired = track.adapter_status == "wired"
    public_claim_ready = adapter_wired and track.claim_level in {"official_public_result", "local_public_evidence"}
    if track.pass_threshold is not None and score.get("score") is not None:
        passed_gate = float(score["score"]) >= track.pass_threshold
    else:
        passed_gate = command_result["returncode"] == 0 if command_result["executed"] else adapter_wired
    return {
        "track_id": track.track_id,
        "family": track.family,
        "official_url": track.official_url,
        "description": track.description,
        "adapter_status": track.adapter_status,
        "claim_level": track.claim_level,
        "required_for_public_all_around_claim": track.required_for_public_all_around_claim,
        "run_command": track.run_command,
        "command": command_result,
        "artifacts": artifacts,
        "primary_metric": track.primary_metric,
        "score": score,
        "external_smoke": _external_smoke_state(track.track_id),
        "pass_threshold": track.pass_threshold,
        "passed_gate": bool(passed_gate),
        "public_claim_ready": public_claim_ready,
        "cost_tier": track.cost_tier,
        "limits": _track_limits(track),
    }


def _track_limits(track: Track) -> list[str]:
    if track.adapter_status != "wired":
        return [
            "Official benchmark adapter is not wired yet.",
            "This track can prove readiness shape only; it cannot support a leaderboard or all-around claim.",
        ]
    if track.claim_level == "local_public_evidence":
        return [
            "This is repo-local public evidence, not an official external leaderboard result.",
            "Use it to prove CLI governance/control-plane coverage only.",
        ]
    return []


def build_report(config_path: Path, output_root: Path, execute: bool, timeout: int) -> dict[str, Any]:
    config = load_config(config_path)
    tracks = load_tracks(config)
    results = [run_track(track, execute=execute, timeout=timeout) for track in tracks]
    required = [row for row in results if row["required_for_public_all_around_claim"]]
    external_required = [row for row in required if row["track_id"] != "geoseal_cli_competitive"]
    all_required_public_ready = all(row["public_claim_ready"] for row in required)
    local_ready = all(row["passed_gate"] for row in results if row["adapter_status"] == "wired")
    adapter_readiness_ok = all(row["command"]["returncode"] in {0, None} for row in results)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "suite_id": config["suite_id"],
        "git_commit": git_commit(),
        "dirty_worktree": dirty_worktree(),
        "execute": execute,
        "ok": bool(local_ready and adapter_readiness_ok),
        "claim_policy": config["claim_policy"],
        "summary": {
            "tracks": len(results),
            "wired_tracks": sum(1 for row in results if row["adapter_status"] == "wired"),
            "planned_tracks": sum(1 for row in results if row["adapter_status"] != "wired"),
            "local_ready": local_ready,
            "all_required_public_ready": all_required_public_ready,
            "external_required_not_ready": [
                row["track_id"] for row in external_required if not row["public_claim_ready"]
            ],
            "external_setup_evidence": [
                row["track_id"]
                for row in external_required
                if row["external_smoke"].get("ok") or row["external_smoke"].get("repo_present")
            ],
            "publishable_claim": _publishable_claim(results, all_required_public_ready),
        },
        "results": results,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "latest_report.json"
    md_path = output_root / "latest_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"payload": payload, "json": str(json_path), "markdown": str(md_path)}


def _publishable_claim(results: list[dict[str, Any]], all_required_public_ready: bool) -> str:
    geoseal = next((row for row in results if row["track_id"] == "geoseal_cli_competitive"), None)
    if all_required_public_ready:
        return "All required public tracks are ready; all-around claim may be considered with official scores."
    if geoseal and geoseal["score"].get("score") == 1.0:
        return (
            "GeoSeal currently has publishable local evidence for CLI governance/control-plane coverage; "
            "all-around agentic coding superiority is not claimed."
        )
    return "No public superiority claim is ready."


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SCBE Public Agentic CLI Benchmark Packet",
        "",
        f"Generated: `{payload['created_at']}`",
        f"Commit: `{payload['git_commit']}`",
        f"Dirty worktree: `{payload['dirty_worktree']}`",
        "",
        "## Publishable Claim",
        "",
        payload["summary"]["publishable_claim"],
        "",
        "## Track Status",
        "",
        "| Track | Family | Adapter | Claim Level | Gate | Score |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["results"]:
        score = row["score"].get("score")
        score_text = "" if score is None else str(score)
        gate = "pass" if row["passed_gate"] else "hold"
        lines.append(
            f"| `{row['track_id']}` | `{row['family']}` | `{row['adapter_status']}` | "
            f"`{row['claim_level']}` | `{gate}` | `{score_text}` |"
        )
    lines.extend(
        [
            "",
            "## Required External Tracks Not Ready",
            "",
        ]
    )
    missing = payload["summary"]["external_required_not_ready"]
    if missing:
        lines.extend(f"- `{track_id}`" for track_id in missing)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## External Smoke Evidence",
            "",
        ]
    )
    setup_evidence = payload["summary"]["external_setup_evidence"]
    if setup_evidence:
        lines.extend(f"- `{track_id}`" for track_id in setup_evidence)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Claim Guardrails",
            "",
        ]
    )
    for item in payload["claim_policy"]["forbidden_now"]:
        lines.append(f"- Do not claim: {item}")
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    for row in payload["results"]:
        lines.append(f"- `{row['track_id']}`: {row['official_url']}")
    return "\n".join(lines) + "\n"


def validate_config(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    tracks = load_tracks(config)
    required_ids = {track.track_id for track in tracks if track.required_for_public_all_around_claim}
    problems: list[str] = []
    for required in {
        "geoseal_cli_competitive",
        "terminal_bench",
        "swe_bench_verified_or_lite",
        "aider_polyglot",
    }:
        if required not in {track.track_id for track in tracks}:
            problems.append(f"missing required public track: {required}")
        if required not in required_ids:
            problems.append(f"track is not marked required for all-around claim: {required}")
    forbidden = set(config.get("claim_policy", {}).get("forbidden_now", []))
    if not any("all-around best coding agent" in item for item in forbidden):
        problems.append(
            "claim_policy must explicitly forbid all-around best coding agent claims until official runs exist"
        )
    return {"ok": not problems, "track_count": len(tracks), "problems": problems}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--execute", action="store_true", help="Run wired local commands and adapter-readiness commands."
    )
    parser.add_argument("--timeout", type=int, default=180)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    validation = validate_config(args.config)
    if args.validate_only:
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 0 if validation["ok"] else 1
    if not validation["ok"]:
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 1
    report = build_report(args.config, args.output_root, execute=args.execute, timeout=args.timeout)
    print(
        json.dumps(
            {
                "ok": report["payload"]["ok"],
                "json": report["json"],
                "markdown": report["markdown"],
                "publishable_claim": report["payload"]["summary"]["publishable_claim"],
                "external_required_not_ready": report["payload"]["summary"]["external_required_not_ready"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["payload"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
