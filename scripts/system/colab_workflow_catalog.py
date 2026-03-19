#!/usr/bin/env python3
"""Local catalog for SCBE Colab notebooks and training lanes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPO = "issdandavis/SCBE-AETHERMOORE"
CANONICAL_BRANCH = "main"


NOTEBOOKS: list[dict[str, Any]] = [
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
    return str(Path(CANONICAL_REPO)) if CANONICAL_REPO else "issdandavis/SCBE-AETHERMOORE"


def _github_branch() -> str:
    return CANONICAL_BRANCH


def _record_payload(row: dict[str, Any]) -> dict[str, Any]:
    rel_path = row["path"].replace("\\", "/")
    local_path = REPO_ROOT / row["path"]
    return {
        "name": row["name"],
        "aliases": row["aliases"],
        "category": row["category"],
        "summary": row["summary"],
        "path": rel_path,
        "local_path": str(local_path),
        "exists": local_path.exists(),
        "colab_url": f"https://colab.research.google.com/github/{_github_repo()}/blob/{_github_branch()}/{rel_path}",
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
