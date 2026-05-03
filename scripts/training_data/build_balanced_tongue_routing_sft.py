"""Build balanced Sacred Tongue routing SFT records.

The local coder currently writes simple code reasonably well, but it is biased
toward CA/KO when asked to choose a tongue. This generator creates a clean,
balanced routing corpus that teaches the model to output only the lane JSON.
It writes to artifacts by default so it does not disturb canonical training
data while other agents are working.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.coding_spine.deterministic_tongue_router import TONGUE_CANONICAL_LANG, route_prompt

DEFAULT_OUT = REPO_ROOT / "artifacts" / "training" / "balanced_tongue_routing_sft.jsonl"

SEEDS: dict[str, list[str]] = {
    "KO": [
        "write a Python helper that loads JSON from disk",
        "build a FastAPI endpoint with Pydantic validation",
        "create a pytest fixture for a temporary database",
        "use pandas to aggregate a dataframe by customer",
    ],
    "AV": [
        "write a TypeScript React component with useState",
        "create a browser snippet that toggles a DOM class on click",
        "build a Node.js route handler with typed request data",
        "write a TSX component that renders API results",
    ],
    "RU": [
        "implement a Rust ring buffer using ownership-safe code",
        "write a Tokio async worker pool with bounded channels",
        "create a Cargo crate for a zero-cost parser",
        "explain lifetimes in a Rust borrowing example",
    ],
    "CA": [
        "write a C function compiled with gcc",
        "implement a C memory allocator sketch with pointer checks",
        "build a CMake target for a small C library",
        "write a symbolic Mathematica expression for eigenvalues",
    ],
    "UM": [
        "solve a stiff differential equation in Julia",
        "build a Julia DataFrames pipeline for spectral anomaly detection",
        "train a small Flux model in Julia",
        "write a Julia multiple-dispatch function for security scoring",
    ],
    "DR": [
        "create a project README with architecture sections",
        "draft Markdown documentation with headings and bullet lists",
        "write a Markdown task-flow card for an agentic script",
        "create structured Markdown release notes with verification commands",
    ],
}

MAPPING_TEXT = "KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Markdown"


def record_for(tongue: str, task: str, variant: str) -> dict:
    if variant == "task_clause":
        prompt = (
            f"Task: {task}. Choose the best Sacred Tongue ({MAPPING_TEXT}). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}.'
        )
    elif variant == "plain":
        prompt = f"Route this coding task to one Sacred Tongue and reply JSON only: {task}"
    else:
        prompt = f"Classify lane for agent harness control. Task={task}. JSON only."

    expected = {"tongue": tongue, "lang": TONGUE_CANONICAL_LANG[tongue]}
    route = route_prompt(prompt)
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a Sacred Tongue routing classifier. Reply only with compact JSON.",
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(expected, sort_keys=True)},
        ],
        "metadata": {
            "track": "balanced_tongue_routing",
            "tongue": tongue,
            "language": TONGUE_CANONICAL_LANG[tongue],
            "variant": variant,
            "deterministic_route": route.as_json(),
            "deterministic_route_matches_expected": route.tongue == tongue,
        },
    }


def build_records() -> list[dict]:
    records: list[dict] = []
    for tongue, tasks in SEEDS.items():
        for task in tasks:
            for variant in ("task_clause", "plain", "agent_harness"):
                records.append(record_for(tongue, task, variant))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    records = build_records()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n", encoding="utf-8")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records": len(records),
        "per_tongue": {tongue: sum(1 for r in records if r["metadata"]["tongue"] == tongue) for tongue in SEEDS},
        "output": str(args.out),
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
