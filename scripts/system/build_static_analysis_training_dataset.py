#!/usr/bin/env python3
"""Build defensive static-analysis and reverse-engineering training records.

The goal is to teach agents how to inspect a system, infer what it does, find
safe remediation paths, and verify the fix. This builder intentionally avoids
offensive payload recipes, credential material, proprietary blobs, and unsafe
operational instructions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "scbe_static_analysis_training_v1"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "training" / "static_analysis_reverse_engineering"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-static-analysis-training"
DEFAULT_HF_REPO = "issdandavis/scbe-static-analysis-training"
DEFAULT_KAGGLE_OWNER = os.environ.get("KAGGLE_USERNAME", "issacizrealdavis")
DEFAULT_KAGGLE_SLUG = "scbe-static-analysis-training"
REVERSE_ENGINEERING_VIDEO_ID = "8vk5z9VAaBQ"
REVERSE_ENGINEERING_TRANSCRIPT_PATH = (
    REPO_ROOT / "artifacts" / "apollo" / "youtube_transcripts" / f"{REVERSE_ENGINEERING_VIDEO_ID}.txt"
)

SECRET_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9_=-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_=-]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_=-]{12,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
]

FORBIDDEN_TERMS = [
    "credential theft",
    "privilege escalation exploit",
    "weaponized payload",
    "persistence implant",
    "malware loader",
]


@dataclass(frozen=True)
class TrainingScenario:
    scenario_id: str
    title: str
    source_kind: str
    risk_level: str
    user_prompt: str
    analysis_steps: list[str]
    remediation_steps: list[str]
    verification_steps: list[str]
    tags: list[str]
    evidence: dict[str, Any] = field(default_factory=dict)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_text(value: str) -> str:
    out = value
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def public_path(path: str | Path) -> str:
    raw = str(path)
    replacements = {
        str(REPO_ROOT): "%REPO%",
        str(Path.home()): "%USERPROFILE%",
    }
    out = raw
    for source, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        out = out.replace(source, replacement)
    return redact_text(out)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    package_files = {
        "scbe-aethermoore": REPO_ROOT / "package.json",
        "scbe-aethermoore-cli": REPO_ROOT / "packages" / "cli" / "package.json",
        "scbe-agent-bus": REPO_ROOT / "packages" / "agent-bus" / "package.json",
    }
    for name, path in package_files.items():
        data = load_json(path)
        if data.get("version"):
            versions[name] = str(data["version"])
    return versions


def npm_dependency_names() -> list[str]:
    data = load_json(REPO_ROOT / "package.json")
    names = sorted({*data.get("dependencies", {}).keys(), *data.get("devDependencies", {}).keys()})
    return names[:40]


def transcript_profile(path: Path = REVERSE_ENGINEERING_TRANSCRIPT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "video_id": REVERSE_ENGINEERING_VIDEO_ID,
            "transcript_available": False,
            "source_url": f"https://www.youtube.com/watch?v={REVERSE_ENGINEERING_VIDEO_ID}",
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "video_id": REVERSE_ENGINEERING_VIDEO_ID,
        "transcript_available": True,
        "transcript_path": public_path(path),
        "word_count": len(text.split()),
        "char_count": len(text),
        "source_url": f"https://www.youtube.com/watch?v={REVERSE_ENGINEERING_VIDEO_ID}",
    }


def build_scenarios() -> list[TrainingScenario]:
    versions = package_versions()
    deps = npm_dependency_names()
    video_profile = transcript_profile()
    return [
        TrainingScenario(
            scenario_id="shopify_tailwind_cdn_to_bundled_vite",
            title="Replace production Tailwind CDN with bundled Vite CSS",
            source_kind="deploy_fix_summary",
            risk_level="medium",
            user_prompt=(
                "A Vite React app ships with https://cdn.tailwindcss.com in index.html. "
                "Static analysis flags the production CDN path. Explain the safe fix and the verification plan."
            ),
            analysis_steps=[
                "Inspect index.html for remote runtime CSS or script dependencies.",
                "Inspect package.json and vite.config.ts to confirm whether Tailwind is bundled at build time.",
                "Treat this as a supply-chain and availability concern, not an exploit exercise.",
            ],
            remediation_steps=[
                "Add tailwindcss and the Vite Tailwind plugin as project dependencies.",
                "Create a local stylesheet that imports Tailwind layers.",
                "Import the stylesheet from the app entrypoint.",
                "Remove the CDN script from index.html.",
                "Wire the Tailwind plugin into vite.config.ts.",
            ],
            verification_steps=[
                "Run the app build or Vite preview.",
                "Use browser automation to confirm no requests are made to cdn.tailwindcss.com.",
                "Check console warnings and failed requests.",
                "Confirm a bundled CSS asset is present in the built page.",
            ],
            tags=["static-analysis", "supply-chain", "vite", "tailwind", "frontend"],
            evidence={"source": "user-provided Shopify Command Center deploy summary"},
        ),
        TrainingScenario(
            scenario_id="codeql_uncontrolled_path_triage",
            title="Triage uncontrolled path expression findings safely",
            source_kind="codeql_alert_pattern",
            risk_level="high",
            user_prompt=(
                "CodeQL reports uncontrolled data used in a path expression in a CLI bridge. "
                "How should an agent inspect and fix it without breaking legitimate workspace paths?"
            ),
            analysis_steps=[
                "Find the boundary where user input becomes a path.",
                "Identify the intended root directory and whether symlinks or relative paths are allowed.",
                "Trace all file operations using the derived path.",
                "Look for tests that already encode valid paths and invalid traversal attempts.",
            ],
            remediation_steps=[
                "Resolve candidate paths against an explicit trusted base directory.",
                "Reject paths that escape the trusted base after resolution.",
                "Use literal path APIs where the platform supports them.",
                "Return a clear error for rejected paths without echoing sensitive local paths.",
            ],
            verification_steps=[
                "Add a deterministic valid-path regression test.",
                "Add invalid traversal and absolute-path boundary tests.",
                "Run the targeted tests plus the security or CLI smoke suite.",
                "Re-run CodeQL or the closest local static check before closing the alert.",
            ],
            tags=["static-analysis", "codeql", "path-safety", "cli", "defensive"],
        ),
        TrainingScenario(
            scenario_id="package_surface_reverse_engineering",
            title="Infer package product surfaces from manifests",
            source_kind="manifest_reverse_engineering",
            risk_level="low",
            user_prompt=(
                "Given a repo with npm and PyPI manifests, infer the public product lineup and write a buyer-safe "
                "summary without inventing package names."
            ),
            analysis_steps=[
                "Read package.json, nested package.json files, pyproject.toml files, and README install snippets.",
                "Cross-check manifest names, versions, descriptions, bin entries, and repository URLs.",
                "Verify live registry versions when network access is available.",
                "Mark local-only packages as publish pending instead of linking dead registries.",
            ],
            remediation_steps=[
                "Create one catalog record per real package.",
                "Use install commands from manifests or READMEs.",
                "Separate npm and PyPI versions when they differ.",
                "Expose product pages that explain who uses the package and what problem it solves.",
            ],
            verification_steps=[
                "Test that every catalog entry points to an existing page.",
                "Test that live pages include registry URLs and versions.",
                "Test that publish-pending packages do not include dead registry links.",
            ],
            tags=["static-analysis", "package-metadata", "npm", "pypi", "productization"],
            evidence={"versions": versions, "dependency_sample": deps},
        ),
        TrainingScenario(
            scenario_id="agent_bus_behavioral_reverse_engineering",
            title="Reverse engineer an agent bus by reading its CLI and envelope contract",
            source_kind="agent_harness_analysis",
            risk_level="low",
            user_prompt=(
                "A repo contains an agent bus package. Explain how to infer what it does from static files before "
                "running it."
            ),
            analysis_steps=[
                "Read the package bin map to find the CLI entrypoint.",
                "Read the README examples to identify supported commands and expected output shape.",
                "Read exported TypeScript or Python types to identify the event envelope contract.",
                "Map commands to tests so behavior is grounded in executable checks.",
            ],
            remediation_steps=[
                "Document the commands as task packets, health checks, and typed envelope routes.",
                "Add smoke tests for command help, JSON output, and invalid input handling.",
                "Keep local/private routing as the default for sensitive agent work.",
            ],
            verification_steps=[
                "Run package unit tests.",
                "Run CLI help and one JSON smoke command.",
                "Check that invalid input fails clearly without leaking local secrets.",
            ],
            tags=["static-analysis", "agent-bus", "cli", "typed-envelope", "harness"],
        ),
        TrainingScenario(
            scenario_id="safe_reverse_engineering_policy_gate",
            title="Keep reverse-engineering training defensive",
            source_kind="training_policy",
            risk_level="medium",
            user_prompt=(
                "We want models to learn reverse engineering because engineering often starts with understanding an "
                "existing system. What boundaries keep the training safe?"
            ),
            analysis_steps=[
                "Define reverse engineering as system comprehension, interface recovery, dependency mapping, "
                "and failure analysis.",
                "Classify offensive exploit building, credential abuse, persistence, and stealth as blocked content.",
                "Prefer metadata, manifests, tests, logs with secrets removed, and small synthetic examples.",
            ],
            remediation_steps=[
                "Tag records with defensive intent and source provenance.",
                "Strip secrets and local paths.",
                "Convert risky findings into patch-and-test tasks instead of offensive payload recipes.",
                "Require verification steps for every remediation answer.",
            ],
            verification_steps=[
                "Scan generated records for blocked terms and secret patterns.",
                "Assert every record has analysis, remediation, and verification sections.",
                "Hold out a small eval set focused on refusal of offensive requests.",
            ],
            tags=["training-policy", "defensive-reverse-engineering", "safety", "sft"],
        ),
        TrainingScenario(
            scenario_id="reverse_engineering_levels_video_to_training",
            title="Convert reverse-engineering education into defensive training tasks",
            source_kind="public_video_summary",
            risk_level="medium",
            user_prompt=(
                "A public video titled 'Every Level of Reverse Engineering Explained' is provided as learning "
                "material. Convert the idea into safe agent-training tasks for system comprehension."
            ),
            analysis_steps=[
                "Use the video as a topic anchor, not as permission to copy transcript text.",
                "Extract the transcript's ladder as defensive learning stages: strings, static analysis, "
                "dynamic analysis, symbolic execution, and real software or firmware investigation.",
                "Treat reverse engineering as progressive comprehension: identify inputs, outputs, file formats, "
                "dependencies, interfaces, and behavior.",
                "Prefer tasks that ask the agent to explain what a program does and how to verify a fix.",
                "Avoid tasks that ask for bypass, stealth, unauthorized access, or offensive payload construction.",
            ],
            remediation_steps=[
                "Create records for manifest reading, dependency mapping, build artifact inspection, "
                "log interpretation, and patch verification.",
                "Require the answer to include analysis, safe remediation, and verification sections.",
                "Add provenance metadata with the public source URL and a short source title.",
                "Keep the content synthetic or metadata-only "
                "unless a transcript and license review explicitly allow more.",
            ],
            verification_steps=[
                "Scan generated records for secrets and blocked offensive terms.",
                "Assert that every record keeps a defensive purpose.",
                "Hold out eval prompts that ask the model to redirect unsafe reverse-engineering requests "
                "to defensive analysis.",
            ],
            tags=["reverse-engineering", "static-analysis", "video-derived", "training-policy"],
            evidence={
                "source_title": "Every Level of Reverse Engineering Explained",
                "source_url": f"https://www.youtube.com/watch?v={REVERSE_ENGINEERING_VIDEO_ID}",
                "transcript_profile": video_profile,
                "transcript_topics": [
                    "strings",
                    "static analysis",
                    "dynamic analysis",
                    "symbolic execution",
                    "real software and firmware bug investigation",
                ],
            },
        ),
    ]


def scenario_hash(scenario: TrainingScenario) -> str:
    payload = json.dumps(
        {
            "scenario_id": scenario.scenario_id,
            "prompt": scenario.user_prompt,
            "analysis": scenario.analysis_steps,
            "remediation": scenario.remediation_steps,
            "verification": scenario.verification_steps,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_answer(scenario: TrainingScenario) -> str:
    parts = [
        "Analysis:",
        *[f"- {item}" for item in scenario.analysis_steps],
        "",
        "Safe remediation:",
        *[f"- {item}" for item in scenario.remediation_steps],
        "",
        "Verification:",
        *[f"- {item}" for item in scenario.verification_steps],
    ]
    return redact_text("\n".join(parts))


def build_record(scenario: TrainingScenario, created_at: str) -> dict[str, Any]:
    answer = format_answer(scenario)
    record = {
        "schema": SCHEMA_VERSION,
        "id": f"static-analysis-{scenario_hash(scenario)[:16]}",
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "created_at_utc": created_at,
        "source_kind": scenario.source_kind,
        "risk_level": scenario.risk_level,
        "tags": scenario.tags,
        "privacy": "metadata_or_synthetic_only",
        "blocked_use": (
            "Do not use this record to generate offensive payloads, credential abuse workflows, "
            "stealth, persistence, or unauthorized access instructions."
        ),
        "evidence": scenario.evidence,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an SCBE defensive static-analysis agent. Explain how to understand, fix, "
                    "and verify systems without giving offensive operational instructions."
                ),
            },
            {"role": "user", "content": redact_text(scenario.user_prompt)},
            {"role": "assistant", "content": answer},
        ],
    }
    record["source_sha256"] = scenario_hash(scenario)
    return record


def assert_safe_records(records: list[dict[str, Any]]) -> None:
    for record in records:
        blob = json.dumps(record, ensure_ascii=False)
        for pattern in SECRET_PATTERNS:
            if pattern.search(blob):
                raise ValueError(f"secret-like token leaked in {record['id']}")
        lowered = blob.lower()
        for term in FORBIDDEN_TERMS:
            if term in lowered:
                raise ValueError(f"blocked term '{term}' appears in {record['id']}")
        answer = record["messages"][2]["content"]
        for heading in ("Analysis:", "Safe remediation:", "Verification:"):
            if heading not in answer:
                raise ValueError(f"{record['id']} missing {heading}")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_readme(path: Path, records: list[dict[str, Any]], created_at: str) -> None:
    tags = sorted({tag for record in records for tag in record["tags"]})
    text = f"""---
license: cc-by-4.0
task_categories:
- text-generation
- question-answering
language:
- en
tags:
- scbe
- static-analysis
- defensive-reverse-engineering
- ai-agents
---

# SCBE Static Analysis Training

Defensive static-analysis and reverse-engineering training records generated at `{created_at}`.

This dataset teaches agents to inspect systems, infer purpose from manifests and
tests, fix issues, and verify outcomes. It is meant for defensive engineering,
product hardening, package comprehension, and build/deploy remediation.

It does not contain offensive payload recipes, credentials, private blobs, or raw
customer source code.

## Files

- `records.jsonl`: full records with metadata and ChatML-style messages.
- `records.chat.jsonl`: message-only SFT rows plus minimal labels.
- `manifest.json`: generation metadata.
- `dataset-metadata.json`: Kaggle-compatible metadata.

## Counts

- total records: {len(records)}
- tags: {", ".join(tags)}
"""
    path.write_text(text, encoding="utf-8")


def build_dataset(out_dir: Path, kaggle_dir: Path, kaggle_ref: str) -> dict[str, Any]:
    created_at = now_utc()
    records = [build_record(scenario, created_at) for scenario in build_scenarios()]
    assert_safe_records(records)
    chat_records = [
        {
            "id": record["id"],
            "schema": record["schema"],
            "scenario_id": record["scenario_id"],
            "messages": record["messages"],
            "tags": record["tags"],
            "privacy": record["privacy"],
        }
        for record in records
    ]
    manifest = {
        "schema": SCHEMA_VERSION,
        "created_at_utc": created_at,
        "record_count": len(records),
        "privacy": "metadata_or_synthetic_only",
        "hf_repo_default": DEFAULT_HF_REPO,
        "kaggle_ref": kaggle_ref,
        "outputs": ["records.jsonl", "records.chat.jsonl", "README.md", "manifest.json", "dataset-metadata.json"],
    }

    metadata = {
        "id": kaggle_ref,
        "title": "SCBE Static Analysis Training",
        "subtitle": "Defensive reverse-engineering, package comprehension, and remediation records",
        "licenses": [{"name": "cc"}],
        "keywords": ["static-analysis", "reverse-engineering", "ai-agents", "defensive-security", "software"],
    }

    for target in (out_dir, kaggle_dir):
        target.mkdir(parents=True, exist_ok=True)
        write_jsonl(target / "records.jsonl", records)
        write_jsonl(target / "records.chat.jsonl", chat_records)
        write_readme(target / "README.md", records, created_at)
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / "dataset-metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return {"manifest": manifest, "records": records}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--kaggle-ref", default=f"{DEFAULT_KAGGLE_OWNER}/{DEFAULT_KAGGLE_SLUG}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_dataset(args.output_dir, args.kaggle_dir, args.kaggle_ref)
    manifest = result["manifest"]
    print(
        f"[static-analysis-training] wrote {manifest['record_count']} safe records "
        f"to {public_path(args.output_dir)} and {public_path(args.kaggle_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
