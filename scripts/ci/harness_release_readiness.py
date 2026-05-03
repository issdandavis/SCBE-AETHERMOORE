#!/usr/bin/env python3
"""Build a release-readiness manifest for the GeoSeal agentic harness.

The harness is moving quickly, so this script gives the release lane a
repeatable "clean board" check: expected files, Git status, SHA-256 hashes,
package-candidate classification, generated-artifact warnings, and the test
commands that should gate promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HARNESS_RELEASE_PATHS = [
    "src/agent_comms/packet.py",
    "src/agent_comms/ledger.py",
    "src/agent_comms/__init__.py",
    "src/agent_comms/graph_runner.py",
    "src/agent_comms/harness_providers.py",
    "src/agent_comms/lane_grid.py",
    "src/agent_comms/secure_handoff.py",
    "src/agent_comms/triadic_handoff.py",
    "src/geoseal_cli.py",
    "bin/geoseal.cjs",
    "scripts/serve_geoseal_harness.py",
    "scripts/benchmark/harness_provider_matrix.py",
    "scripts/benchmark/harness_research_matrix.py",
    "scripts/benchmark/harness_live_smoke.py",
    "scripts/research/geoseal_research_routes.py",
    "scripts/terminal/geoseal_harness_terminal.py",
    "scripts/terminal/analog_action_primitives.py",
    "scripts/system/geoseal_github_ops.py",
    "scripts/ci/harness_release_readiness.py",
    "spiral-word-app/braid_ledger.py",
    "spiral-word-app/app.py",
    "spiral-word-app/governance.py",
    "spiral-word-app/headless.py",
    "spiral-word-app/requirements.txt",
    "tests/agent_comms/test_graph_runner.py",
    "tests/agent_comms/test_harness_packet.py",
    "tests/agent_comms/test_harness_providers.py",
    "tests/agent_comms/test_lane_grid.py",
    "tests/agent_comms/test_secure_handoff.py",
    "tests/agent_comms/test_triadic_handoff.py",
    "tests/benchmark/test_harness_provider_matrix.py",
    "tests/benchmark/test_harness_research_matrix.py",
    "tests/benchmark/test_harness_live_smoke.py",
    "tests/research/test_geoseal_research_routes.py",
    "tests/terminal/test_geoseal_harness_terminal.py",
    "tests/ci/test_harness_release_readiness.py",
    "tests/spiral_word/test_app_endpoints.py",
    "tests/spiral_word/test_braid_ledger.py",
    "tests/spiral_word/test_headless.py",
    "tests/training/test_generate_ambiguity_action_sft.py",
    "tests/training/test_generate_packet_traces_sft.py",
    "tests/training/test_score_packet_trace_sft.py",
    "scripts/system/verify_docs_publish_surface.py",
    "tests/system/test_verify_docs_publish_surface.py",
    "tests/system/test_geoseal_github_ops.py",
    "docs/ops/RELEASE_AND_REVENUE_PATH_2026-05-02.md",
    "docs/specs/TRIADIC_BRAID_SOURCE_MAP.md",
]

TEST_COMMANDS = [
    "python -m pytest tests/agent_comms tests/benchmark/test_harness_provider_matrix.py "
    "tests/benchmark/test_harness_research_matrix.py tests/benchmark/test_harness_live_smoke.py "
    "tests/research/test_geoseal_research_routes.py tests/terminal/test_geoseal_harness_terminal.py "
    "tests/ci/test_harness_release_readiness.py "
    "tests/system/test_verify_docs_publish_surface.py tests/system/test_geoseal_github_ops.py "
    "tests/spiral_word tests/training/test_generate_ambiguity_action_sft.py "
    "tests/training/test_generate_packet_traces_sft.py tests/training/test_score_packet_trace_sft.py -q",
    "python scripts/benchmark/harness_provider_matrix.py --json",
    "python scripts/benchmark/harness_live_smoke.py --models ollama:a,huggingface:Qwen/Qwen2.5-Coder-7B-Instruct --json",
    "python scripts/system/verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html --require-checkout",
    "python scripts/ci/harness_release_readiness.py --json",
]

GENERATED_PREFIXES = ("artifacts/", "dist/", "training/runs/", ".pytest_cache/", ".hypothesis/")
PACKAGE_PREFIXES = ("src/", "scripts/", "bin/", "spiral-word-app/", "docs/", "tests/")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_status(root: Path, paths: Iterable[str]) -> dict[str, str]:
    path_list = list(paths)
    if not path_list:
        return {}
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", *path_list],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return {path: "git_status_error" for path in path_list}

    statuses: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[:2].strip() or "clean"
        path = line[3:].strip()
        statuses[path] = code
        if path.endswith("/"):
            for requested in path_list:
                if requested.startswith(path):
                    statuses[requested] = code
    return statuses


def _classify_path(path: str) -> dict[str, bool]:
    normalized = path.replace("\\", "/")
    return {
        "generated": normalized.startswith(GENERATED_PREFIXES),
        "package_candidate": normalized.startswith(PACKAGE_PREFIXES) and not normalized.startswith(GENERATED_PREFIXES),
        "test": normalized.startswith("tests/"),
        "documentation": normalized.startswith("docs/"),
    }


def build_release_readiness(
    *,
    root: Path = PROJECT_ROOT,
    paths: Iterable[str] = HARNESS_RELEASE_PATHS,
    git_status_func: Callable[[Path, Iterable[str]], dict[str, str]] = _git_status,
) -> dict[str, Any]:
    path_list = list(dict.fromkeys(paths))
    git_status = git_status_func(root, path_list)
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    uncommitted: list[str] = []
    generated_candidates: list[str] = []

    for rel in path_list:
        full_path = root / rel
        exists = full_path.exists()
        status = git_status.get(rel, "clean")
        classification = _classify_path(rel)
        item = {
            "path": rel,
            "exists": exists,
            "git_status": status,
            "sha256": _sha256_file(full_path) if exists and full_path.is_file() else "",
            **classification,
        }
        files.append(item)
        if not exists:
            missing.append(rel)
        if status != "clean":
            uncommitted.append(rel)
        if classification["generated"] and classification["package_candidate"]:
            generated_candidates.append(rel)

    gates = {
        "all_expected_files_exist": not missing,
        "no_generated_package_candidates": not generated_candidates,
        "has_uncommitted_work": bool(uncommitted),
        "ready_to_publish": (not missing) and (not generated_candidates) and (not uncommitted),
    }
    return {
        "schema_version": "scbe_harness_release_readiness_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "summary": {
            "files": len(files),
            "missing": len(missing),
            "uncommitted": len(uncommitted),
            "generated_candidates": len(generated_candidates),
            "package_candidates": sum(1 for item in files if item["package_candidate"]),
        },
        "gates": gates,
        "files": files,
        "missing": missing,
        "uncommitted": uncommitted,
        "generated_candidates": generated_candidates,
        "test_commands": list(TEST_COMMANDS),
        "release_note": (
            "Publish only after the listed tests pass and uncommitted harness files are intentionally staged."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a compact text summary")
    parser.add_argument("--write", type=Path, default=None, help="Optional path to write the manifest JSON")
    args = parser.parse_args(argv)

    report = build_release_readiness()
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        gates = report["gates"]
        print("GeoSeal Harness Release Readiness")
        print("=" * 37)
        print(
            f"files={summary['files']} missing={summary['missing']} "
            f"uncommitted={summary['uncommitted']} generated={summary['generated_candidates']}"
        )
        print(f"ready_to_publish={gates['ready_to_publish']}")
        if report["missing"]:
            print("missing:")
            for path in report["missing"]:
                print(f"- {path}")
        if report["uncommitted"]:
            print("uncommitted:")
            for path in report["uncommitted"]:
                print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
