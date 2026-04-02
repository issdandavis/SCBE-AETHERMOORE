#!/usr/bin/env python3
"""Local catalog for SCBE Colab notebooks and training lanes."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPO = "issdandavis/SCBE-AETHERMOORE"
CANONICAL_BRANCH = "main"
COLAB_URL_RE = re.compile(r"https://colab\.research\.google\.com/[^\s\"')>]+")


NOTEBOOKS: list[dict[str, Any]] = [
    {
        "name": "spiralverse-generator",
        "aliases": ["generator", "training-generator", "protocol-generator", "spiralverse-generator"],
        "path": "notebooks/spiralverse_protocol_training_generator.ipynb",
        "category": "data",
        "summary": "Canonical Spiralverse protocol generator for raw synthetic conversation corpora.",
    },
    {
        "name": "canonical-training-lane",
        "aliases": ["canonical", "one-notebook", "ship-train", "canonical-training", "training-lane"],
        "path": "notebooks/scbe_canonical_training_lane_colab.ipynb",
        "category": "training",
        "summary": "One-notebook Colab lane for raw export upload, normalization, and QLoRA fine-tuning.",
    },
    {
        "name": "scbe-pivot-v2",
        "aliases": ["pivot", "pivot-v2", "conversation-pivot"],
        "path": "notebooks/scbe_pivot_training_v2.ipynb",
        "category": "training",
        "summary": "Pivot-conversation notebook for measured SFT and DPO preparation.",
    },
    {
        "name": "scbe-finetune-free",
        "aliases": ["finetune", "sft", "free-colab", "scbe-finetune"],
        "path": "notebooks/scbe_finetune_colab.ipynb",
        "category": "training",
        "summary": "Free T4 LoRA fine-tuning lane for SCBE governance data.",
    },
    {
        "name": "qlora-training",
        "aliases": ["qlora", "colab-qlora", "trainer"],
        "path": "notebooks/colab_qlora_training.ipynb",
        "category": "training",
        "summary": "QLoRA training notebook for compact Colab model adaptation.",
    },
    {
        "name": "aethermoor-finetune",
        "aliases": ["aethermoor", "aethermoor-finetune", "game-finetune"],
        "path": "notebooks/colab_aethermoor_finetune.ipynb",
        "category": "training",
        "summary": "Aethermoor-focused fine-tuning notebook for game and world data.",
    },
    {
        "name": "aethermoor-datagen",
        "aliases": ["datagen", "game-datagen", "aethermoor-datagen"],
        "path": "notebooks/colab_aethermoor_datagen.ipynb",
        "category": "data",
        "summary": "Generate or expand Aethermoor data on free Colab compute.",
    },
    {
        "name": "spiralverse-federated",
        "aliases": ["spiralverse", "federated", "spiralverse-federated"],
        "path": "notebooks/spiralverse_federated_training_colab.ipynb",
        "category": "training",
        "summary": "Spiralverse federated training notebook spanning multiple model lanes.",
    },
    {
        "name": "langues-metric",
        "aliases": ["langues", "metric", "langues-metric"],
        "path": "notebooks/scbe_langues_metric_colab.ipynb",
        "category": "research",
        "summary": "Interactive Langues metric and harmonic math exploration notebook.",
    },
    {
        "name": "webtoon-panel",
        "aliases": ["webtoon", "panel-gen", "manhwa"],
        "path": "notebooks/webtoon_panel_generation_colab.ipynb",
        "category": "generation",
        "summary": "Remote-first panel generation notebook for prompt packs and GPU rendering.",
    },
    {
        "name": "webtoon-panel-embedded",
        "aliases": ["embedded-webtoon", "webtoon-embedded"],
        "path": "notebooks/webtoon_panel_generation_embedded_colab.ipynb",
        "category": "generation",
        "summary": "Embedded Colab lane for webtoon generation with local handoff support.",
    },
    {
        "name": "cloud-workspace",
        "aliases": ["cloud", "workspace", "cloud-workspace"],
        "path": "notebooks/scbe_cloud_workspace.ipynb",
        "category": "ops",
        "summary": "General cloud/Colab workspace notebook for SCBE experiments.",
    },
]


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in "-_")


def _github_repo() -> str:
    return CANONICAL_REPO.replace("\\", "/") if CANONICAL_REPO else "issdandavis/SCBE-AETHERMOORE"


def _github_branch() -> str:
    env_branch = os.environ.get("SCBE_COLAB_BRANCH", "").strip()
    if env_branch:
        return env_branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        branch = result.stdout.strip()
        if branch and branch != "HEAD":
            return branch
    except Exception:
        pass
    return CANONICAL_BRANCH


def extract_embedded_colab_url(notebook_path: Path) -> str:
    """Return an embedded Colab URL from notebook markdown when present."""
    if not notebook_path.exists():
        return ""
    try:
        payload = json.loads(notebook_path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            text = "".join(source)
        else:
            text = str(source)
        match = COLAB_URL_RE.search(text)
        if match:
            return match.group(0)
    return ""


def _record_payload(row: dict[str, Any]) -> dict[str, Any]:
    rel_path = row["path"].replace("\\", "/")
    local_path = REPO_ROOT / row["path"]
    fallback_colab_url = (
        f"https://colab.research.google.com/github/{_github_repo()}/blob/{_github_branch()}/{rel_path}"
    )
    embedded_colab_url = extract_embedded_colab_url(local_path)
    return {
        "name": row["name"],
        "aliases": row["aliases"],
        "category": row["category"],
        "summary": row["summary"],
        "path": rel_path,
        "local_path": str(local_path),
        "exists": local_path.exists(),
        "embedded_colab_url": embedded_colab_url,
        "fallback_colab_url": fallback_colab_url,
        "colab_url": embedded_colab_url or fallback_colab_url,
    }


def _resolve_notebook(query: str) -> dict[str, Any]:
    term = _normalize(query)
    if not term:
        raise KeyError("notebook name required")

    for row in NOTEBOOKS:
        if term == _normalize(row["name"]):
            return row
        if any(term == _normalize(alias) for alias in row["aliases"]):
            return row

    for row in NOTEBOOKS:
        haystack = [_normalize(row["name"]), *[_normalize(alias) for alias in row["aliases"]]]
        if any(term in item for item in haystack):
            return row

    raise KeyError(f"unknown notebook: {query}")


def resolve_notebook_payload(query: str) -> dict[str, Any]:
    """Resolve a notebook name or alias and return its full payload."""
    row = _resolve_notebook(query)
    return _record_payload(row)


def list_notebook_payloads() -> list[dict[str, Any]]:
    """Return payloads for every notebook in the catalog."""
    return [_record_payload(row) for row in NOTEBOOKS]


def _print_text_list() -> int:
    print("# SCBE Colab Notebook Catalog")
    for row in NOTEBOOKS:
        payload = _record_payload(row)
        aliases = ", ".join(row["aliases"])
        exists = "yes" if payload["exists"] else "no"
        print(f"- {payload['name']} [{row['category']}]")
        print(f"  path: {payload['path']}")
        print(f"  aliases: {aliases}")
        print(f"  exists: {exists}")
        print(f"  summary: {row['summary']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Catalog SCBE Colab notebooks and derived Colab URLs")
    parser.add_argument("action", nargs="?", default="list", choices=["list", "show", "url"])
    parser.add_argument("name", nargs="?", default="")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if args.action == "list":
        payload = [_record_payload(row) for row in NOTEBOOKS]
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        return _print_text_list()

    try:
        row = _resolve_notebook(args.name)
    except KeyError as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    payload = _record_payload(row)
    if args.action == "url":
        if args.json:
            print(json.dumps({"name": payload["name"], "colab_url": payload["colab_url"]}, indent=2))
        else:
            print(payload["colab_url"])
        return 0

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
