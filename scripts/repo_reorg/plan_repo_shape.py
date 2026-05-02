"""Inventory + classifier for the repo-shape-2026-04 reorg.

Reads the repo root, classifies every top-level entry into one of:

  keep_root, docs_specs, docs_ops, docs_business, runnables_legacy,
  appstore_demo, ui_graveyard, services_nested, archive_misc, untouched

Writes:
  artifacts/repo_reorg/inventory_2026-04.json
  docs/ops/REPO_REORG_2026-04.md  (human-readable plan)

This script is *non-destructive*. ``apply_phase1_docs.py`` consumes the JSON
and performs the actual ``git mv`` for the docs phase only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

KEEP_ROOT_FILES = {
    "README.md",
    "LICENSE",
    "NOTICE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "START_HERE.md",
    "CITATION.cff",
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    ".gitleaks.toml",
    ".dockerignore",
    ".npmignore",
    ".prettierignore",
    ".prettierrc",
    ".pre-commit-config.yaml",
    ".cursorrules",
    ".env.example",
    ".env.gateway.example",
    ".firebaserc",
    ".vercelignore",
    ".dbxignore",
    ".flake8",
    ".mcp.json",
    ".tmp_hypothesis_paths.txt",
    ".npmrc.tmp",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-lock.txt",
    "MANIFEST.in",
    "ruff.toml",
    "pytest.ini",
    "tsconfig.json",
    "tsconfig.base.json",
    "tsconfig.gateway.json",
    "vitest.config.ts",
    "playwright.config.ts",
    "render.yaml",
    "vercel.json",
    "firebase.json",
    "Procfile",
    "trust-policy.json",
    "Dockerfile",
    "Dockerfile.api",
    "Dockerfile.cloudrun",
    "Dockerfile.gateway",
    "Dockerfile.research",
    "Dockerfile.sovereign",
    "docker-compose.yml",
    "docker-compose.api.yml",
    "docker-compose.gateway.local.yml",
    "docker-compose.hydra-remote.yml",
    "docker-compose.postgres-lite.yml",
    "docker-compose.research.yml",
    "docker-compose.unified.yml",
    "skills-lock.json",
    "llms.txt",
    "ALIASES.md",
    "README_INDEX.md",
    "kokoro-v1.0.onnx",
    "voices-v1.0.bin",
}

KEEP_ROOT_DIRS = {
    ".git",
    ".github",
    ".cursor",
    ".vscode",
    ".devcontainer",
    ".claude",
    ".agents",
    ".codex_tmp",
    ".scbe",
    ".secrets",
    ".roots",
    ".firebase",
    ".grok",
    ".home",
    ".skillhub",
    ".streamlit",
    ".tmp-build",
    ".pytest_tmp_hallpass_review",
    ".pytest_cache",
    ".hypothesis",
    ".cache",
    ".npm-cache",
    ".ruff_cache",
    ".benchmarks",
    ".playwright-cli",
    ".playwright-mcp",
    ".scbe-sandbox",
    ".venv-training",
    "__pycache__",
    "src",
    "api",
    "tests",
    "scripts",
    "docs",
    "training",
    "space",
    "external_repos",
    "training-data",
    "training-runs",
    "config",
    "deploy",
    "k8s",
    "rust",
    "packages",
    "bin",
    "schemas",
    "agents",
    "hydra",
    "skills",
    "spaces",
    "external",
    "_external",
    "mcp",
    "plugins",
    "policies",
    "services",
    "workflows",
    "tools",
    "lexicons",
    "extensions",
    "automation",
    "models",
    "phdm-21d-embedding",
    "my-local-model",
    "scbe_aethermoore.egg-info",
    "kokoro-v1.0.onnx",
    "voices-v1.0.bin",
    "build",
    "logs",
    "data",
    "exports",
    "deliverables",
    "artifacts",
    "backups",
    "notebooks",
    "notes",
    "Notes and Dumps. by me",
    "Microsoft",
    "ok",
    "output",
    "paper",
    "products",
    "proto",
    "public",
    "references",
    "sealed_blobs",
    "shopify",
    "spiralverse-protocol",
    "spiral-word-app",
    "scbe-aethermoore",
    "scbe-visual-system",
    "symphonic_cipher",
    "test-install",
    "ui",
    "physics_sim",
    "unsloth_compiled_cache",
    "AETHERMOORE",
    "ai-ide",
    "aether-browser",
    "aetherbrowse",
    "app",
    "apps",
    "assets",
    "aws",
    "articles",
    "benchmarks",
    "conference-app",
    "content",
    "dashboard",
    "demo",
    "demos",
    "desktop",
    "examples",
    "experimental",
    "experiments",
    "game",
    "kindle-app",
    "prototype",
    "python",
    "archive",
    "_staging",
}

DOCS_SPECS = {
    "ARCHITECTURE.md",
    "SPEC.md",
    "LAYER_INDEX.md",
    "CONCEPTS.md",
    "STRUCTURE.md",
    "SYSTEM_ARCHITECTURE.md",
    "SYSTEM_OVERVIEW.mermaid.md",
    "SCBE_SYSTEM_OVERVIEW.md",
    "CANONICAL_SYSTEM_STATE.md",
    "Spiralverse_Game_Design_Bible.md",
}
DOCS_OPS = {
    "APP_STORE_STRATEGY.md",
    "CLEANUP_NOTES.md",
    "DEPLOYMENT_STRATEGY.md",
    "DEMOS.md",
    "INSTRUCTIONS.md",
    "OVERNIGHT_TASKS.md",
    "PROJECT_COMPLETION_STATUS.md",
    "REPO_AUDIT.md",
    "REPO_BOUNDARY_PLAN.md",
    "REPO_REPORT.md",
    "REPO_SURFACE_MAP.md",
    "RESTRUCTURE_PLAN.md",
    "ROADMAP_90_DAY_TO_PILOT.md",
    "STATE_OF_SYSTEM.md",
    "SYSTEM_IMPROVEMENT_RECOMMENDATIONS.md",
    "SYSTEM_STATUS.md",
    "TEST_AUDIT_REPORT.md",
    "TEST_FAILURE_ANALYSIS.md",
    "SPLIT_NOTICE.md",
}
DOCS_BUSINESS = {
    "COMMERCIAL.md",
    "CUSTOMER_LICENSE_AGREEMENT.md",
    "PACKAGE_SUMMARY.txt",
    "PATENT_CLAIMS_COVERAGE.md",
    "PATENT_DETAILED_DESCRIPTION.md",
    "PATENT_FIGURES.txt",
    "PITCH_EMAIL_BANK_INNOVATION_LAB.md",
    "SCBE_PATENT_PORTFOLIO.md",
    "VIDEO_SCRIPT_90SEC.md",
    "ZENODO_ABSTRACT.md",
}

RUNNABLES_LEGACY = {
    "enhanced_scbe_cli.py",
    "scbe-cli.py",
    "scbe-agent.py",
    "scbe-geo.py",
    "scbe.py",
    "scbe.js",
    "scbe.ps1",
    "RUN_SCBE.bat",
    "build_apk.bat",
    "test_jdk.bat",
    "quick-test.js",
    "six-tongues-cli.py",
    "scbe_inter_lattice_binder.py",
    "index.html",
    "index.js",
    "product-landing.html",
    "test_telemetry_advanced_math.json",
    "triangulated_notion_update.json",
    "scbe_metering.db",
    "The_Six_Tongues_Protocol.txt",
}


def classify_root_entries() -> dict:
    out = {
        "schema_version": "scbe_repo_reorg_inventory_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "branch_recommendation": "chore/repo-shape-2026-04",
        "phases": {
            "phase1_docs_specs": [],
            "phase1_docs_ops": [],
            "phase1_docs_business": [],
            "phase2_runnables_legacy": [],
            "untouched_root_files": [],
            "untouched_root_dirs": [],
            "uncategorized": [],
        },
    }

    for entry in sorted(REPO.iterdir(), key=lambda p: p.name.lower()):
        name = entry.name
        if entry.is_dir():
            if name in KEEP_ROOT_DIRS or name.startswith("."):
                out["phases"]["untouched_root_dirs"].append(name)
            else:
                out["phases"]["uncategorized"].append({"name": name, "kind": "dir"})
            continue
        if name in DOCS_SPECS:
            out["phases"]["phase1_docs_specs"].append(name)
        elif name in DOCS_OPS:
            out["phases"]["phase1_docs_ops"].append(name)
        elif name in DOCS_BUSINESS:
            out["phases"]["phase1_docs_business"].append(name)
        elif name in RUNNABLES_LEGACY:
            out["phases"]["phase2_runnables_legacy"].append(name)
        elif name in KEEP_ROOT_FILES or name.startswith("."):
            out["phases"]["untouched_root_files"].append(name)
        else:
            out["phases"]["uncategorized"].append({"name": name, "kind": "file"})
    return out


def write_outputs(inventory: dict) -> tuple[Path, Path]:
    art_dir = REPO / "artifacts" / "repo_reorg"
    art_dir.mkdir(parents=True, exist_ok=True)
    json_path = art_dir / "inventory_2026-04.json"
    json_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    md_dir = REPO / "docs" / "ops"
    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / "REPO_REORG_2026-04.md"

    lines: list[str] = []
    lines.append("# Repo Shape Reorg \u2014 2026-04")
    lines.append("")
    lines.append(f"Generated: {inventory['generated_at']}")
    lines.append(f"Branch: `{inventory['branch_recommendation']}`")
    lines.append("")
    lines.append("This file is generated by `scripts/repo_reorg/plan_repo_shape.py`.")
    lines.append("It is the source of truth for what moves where.")
    lines.append("")
    lines.append("## Phase 1 \u2014 Docs consolidation")
    lines.append("")
    lines.append("### docs/specs/")
    for n in inventory["phases"]["phase1_docs_specs"]:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("### docs/ops/")
    for n in inventory["phases"]["phase1_docs_ops"]:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("### docs/business/")
    for n in inventory["phases"]["phase1_docs_business"]:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("## Phase 2 \u2014 Runnables to runnables/legacy/")
    for n in inventory["phases"]["phase2_runnables_legacy"]:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("## Kept at root (files)")
    for n in inventory["phases"]["untouched_root_files"]:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("## Kept at root (dirs)")
    for n in inventory["phases"]["untouched_root_dirs"]:
        lines.append(f"- `{n}`")
    lines.append("")
    if inventory["phases"]["uncategorized"]:
        lines.append("## Uncategorized (review before moving)")
        for entry in inventory["phases"]["uncategorized"]:
            kind = entry["kind"] if isinstance(entry, dict) else "?"
            name = entry["name"] if isinstance(entry, dict) else str(entry)
            lines.append(f"- ({kind}) {name}")
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    inventory = classify_root_entries()
    json_path, md_path = write_outputs(inventory)
    print(f"Wrote {json_path.relative_to(REPO)}")
    print(f"Wrote {md_path.relative_to(REPO)}")
    counts = {k: len(v) for k, v in inventory["phases"].items()}
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
