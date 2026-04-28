#!/usr/bin/env python3
"""Centralized path contracts for restructure-safe tooling."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN_ROOTS = (
    "src",
    "python",
    "api",
    "tests",
    "packages",
    ".github",
    "package.json",
    "pyproject.toml",
    "pytest.ini",
    "vitest.config.ts",
)

SCANNED_ROOT_REFERENCES = (
    "artifacts/",
    "deploy/",
    "k8s/",
    "training-data/",
    "scripts/",
    "docs/",
    ".github/workflows/",
)

ABSOLUTE_WINDOWS_PREFIX = r"C:\Users\issda\\"

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "output",
    "external",
    "external_repos",
    "docs-build-smoke",
    "docs-build-local",
    "training-data",
    "artifacts",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".hypothesis",
}

TEXT_EXTENSIONS = {
    ".py",
    ".ps1",
    ".mjs",
    ".js",
    ".ts",
    ".tsx",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".md",
    ".txt",
    ".sh",
    ".cjs",
    ".xml",
}

