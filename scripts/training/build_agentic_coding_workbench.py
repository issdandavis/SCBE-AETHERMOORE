#!/usr/bin/env python3
"""Build SCBE agentic-coding workbench records.

This creates a small, routeable training/eval packet that binds current
agentic-coding research patterns to SCBE-specific surfaces:

- STISA/Sacred Tongues routing
- repo retrieval context
- local coding harness verification
- website/public proof routing

The output is intentionally concrete JSONL for training, plus a compact JSON
status file the GitHub Pages site can render.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "training-data" / "agentic_coding" / "agentic_workbench_scbe.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "training-data" / "agentic_coding" / "agentic_workbench_scbe_manifest.json"
DEFAULT_SITE_DATA = REPO_ROOT / "docs" / "static" / "agent-data" / "agentic-coding-workbench.json"
DEFAULT_SITE_INDEX = REPO_ROOT / "docs" / "static" / "agent-data" / "index.json"

SYSTEM_PROMPT = (
    "You are SCBE-Coder, a local-first agentic coding model. Use STISA/Sacred Tongues routing, "
    "repository retrieval, GeoSeal governance, and executable tests to complete code work. "
    "Prefer localization, patch planning, implementation, and validation over open-ended autonomy."
)

RESEARCH_GROUNDING: tuple[dict[str, str], ...] = (
    {
        "id": "swe-bench-verified",
        "title": "SWE-bench Verified",
        "source_url": "https://openai.com/index/introducing-swe-bench-verified/",
        "takeaway": "Use real repository issues and human-validated evaluation; do not trust benchmark labels blindly.",
        "applied_rule": "Every agentic record must include local files and a verification command.",
    },
    {
        "id": "swe-bench-verified-retired",
        "title": "SWE-bench Verified limitations",
        "source_url": "https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/",
        "takeaway": "Even curated coding benchmarks can contain underspecified or environment-sensitive tasks.",
        "applied_rule": "Record environment assumptions and keep tests local and explicit.",
    },
    {
        "id": "agentless",
        "title": "Agentless software engineering baseline",
        "source_url": "https://arxiv.org/abs/2407.01489",
        "takeaway": "A simple localization, repair, and validation loop is a strong baseline for coding agents.",
        "applied_rule": "Train the harness to localize first, then patch, then validate.",
    },
    {
        "id": "reflexion",
        "title": "Reflexion",
        "source_url": "https://arxiv.org/abs/2303.11366",
        "takeaway": "Feedback traces improve later attempts when they are captured as verbal memory.",
        "applied_rule": "Include failure observations and recovery actions in assistant trajectories.",
    },
    {
        "id": "repogenreflex",
        "title": "RepoGenReflex",
        "source_url": "https://arxiv.org/abs/2409.13122",
        "takeaway": "Repository retrieval and verbal feedback can improve repository-level code completion.",
        "applied_rule": "Bind retrieval snippets to each training task and require source-aware edits.",
    },
)


@dataclass(frozen=True)
class Route:
    tongues: tuple[str, ...]
    layers: tuple[int, ...]
    phase: str
    harness_mode: str


@dataclass(frozen=True)
class WorkbenchTask:
    task_id: str
    title: str
    user_goal: str
    files: tuple[str, ...]
    verification: tuple[str, ...]
    route: Route
    expected_output: str
    retrieval_terms: tuple[str, ...]


TASKS: tuple[WorkbenchTask, ...] = (
    WorkbenchTask(
        task_id="agentic-localize-patch-validate",
        title="Localize, patch, validate coding harness behavior",
        user_goal="Improve the coding harness so agent work follows a simple localize, patch, validate loop.",
        files=(
            "scripts/benchmark/scbe_code_eval.py",
            "tests/fixtures/code_eval_prompts.json",
            "package.json",
        ),
        verification=("python scripts/benchmark/scbe_code_eval.py --dry-run",),
        route=Route(("KO", "DR", "CA"), (1, 3, 7, 12, 14), "repair-loop", "localize_patch_validate"),
        expected_output="A harness improvement that records baseline checks, governance decision, retry use, and final checks.",
        retrieval_terms=("CodeCheckResult", "EvalRecord", "benchmark:coding-agents"),
    ),
    WorkbenchTask(
        task_id="agentic-rag-source-lock",
        title="RAG source lock for code edits",
        user_goal="Use local RAG context before editing agentic coding surfaces, and reject source-free patches.",
        files=(
            "scripts/aetherbrowser/api_server.py",
            "src/harmonic/hyperbolicRAG.ts",
            "tests/adversarial/test_indirect_injection.py",
        ),
        verification=("python -m pytest tests/adversarial/test_indirect_injection.py -q",),
        route=Route(("AV", "UM", "DR"), (2, 4, 8, 12, 14), "retrieval-gated", "rag_guarded_patch"),
        expected_output="A retrieved-evidence packet that separates trusted repo context from untrusted instructions.",
        retrieval_terms=("RAG_TOPIC_PROFILES", "retrieveWithTrust", "indirect injection"),
    ),
    WorkbenchTask(
        task_id="agentic-stisa-route-selection",
        title="STISA route selection for coding tasks",
        user_goal="Teach the model to route coding work through STISA tongues instead of treating all tasks as plain text.",
        files=(
            "scripts/build_coding_system_full_sft.py",
            "scripts/build_aligned_foundations_sft.py",
            "python/scbe/tongue_code_lanes.py",
        ),
        verification=("python scripts/build_aligned_foundations_sft.py",),
        route=Route(("KO", "AV", "RU", "CA", "UM", "DR"), (1, 2, 3, 7, 10, 12, 14), "six-tongue-alignment", "stisa_curriculum"),
        expected_output="A routeable coding record preserving command, transport, governance, compute, security, and structure lanes.",
        retrieval_terms=("PRIMARY_MAP", "SYSTEM_PROMPT", "tongue"),
    ),
    WorkbenchTask(
        task_id="agentic-colab-unblock",
        title="Free Colab fallback without paid cloud dispatch",
        user_goal="When local training is blocked, route the model lane to the free Colab adapter notebook without using paid jobs.",
        files=(
            "config/model_training/scbe-zero-cost-local-0.5b.json",
            "notebooks/scbe_zero_cost_local_0p5b_colab.ipynb",
            "scripts/system/colab_workflow_catalog.py",
        ),
        verification=("python scripts/scbe-system-cli.py colab url zero-cost --json",),
        route=Route(("KO", "CA", "UM"), (1, 3, 7, 12, 14), "cost-gated-training", "free_colab_fallback"),
        expected_output="A zero-dollar training route that blocks paid Hugging Face Jobs unless explicitly authorized.",
        retrieval_terms=("zero-cost-local-0p5b", "cost_policy", "allow_cloud"),
    ),
    WorkbenchTask(
        task_id="agentic-public-proof-route",
        title="Public proof route through GitHub Pages",
        user_goal="Expose the agentic coding workbench through the website so outputs are routeable from aethermoore.com.",
        files=(
            "docs/index.html",
            "docs/agents.html",
            "docs/static/agent-data/index.json",
        ),
        verification=("python scripts/system/check_markdown_links.py --roots docs/architecture",),
        route=Route(("AV", "KO", "DR"), (1, 2, 8, 13, 14), "public-routing", "website_proof_surface"),
        expected_output="A public page and JSON data file that show generated records, research grounding, and verification status.",
        retrieval_terms=("Agent Bus", "latest-research", "sitemap"),
    ),
)


def _read_text(path: Path, limit: int = 1200) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r\n", "\n")
    return text[:limit]


def _collect_retrieval(task: WorkbenchTask, repo_root: Path) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    for rel in task.files:
        path = repo_root / rel
        text = _read_text(path)
        if not text:
            continue
        lower = text.lower()
        score = sum(1 for term in task.retrieval_terms if term.lower() in lower)
        snippets.append(
            {
                "path": rel,
                "score": str(score),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "excerpt": text[:700],
            }
        )
    return snippets


def _assistant_trace(task: WorkbenchTask, snippets: list[dict[str, str]]) -> str:
    source_lines = "\n".join(f"- {item['path']} (score {item['score']})" for item in snippets)
    route = task.route
    return (
        "<think>\n"
        "I will localize the relevant repo surfaces first, bind the work to STISA routing, then make the smallest patch and verify it.\n"
        "</think>\n"
        "<observe>\n"
        f"Retrieved files:\n{source_lines}\n"
        "</observe>\n"
        "<plan>\n"
        "1. Localize code and config surfaces.\n"
        "2. Apply one coherent change.\n"
        "3. Run the targeted verification command.\n"
        "4. Emit a routeable artifact for training or public proof.\n"
        "</plan>\n"
        "<governance>\n"
        f"tongues={','.join(route.tongues)}; layers={','.join(str(layer) for layer in route.layers)}; "
        f"phase={route.phase}; harness_mode={route.harness_mode}; decision=ALLOW_WITH_TEST_GATE\n"
        "</governance>\n"
        "<execute>\n"
        f"{task.expected_output}\n"
        "</execute>\n"
        "<terminal>\n"
        + json.dumps({"command": " && ".join(task.verification)})
        + "\n</terminal>\n"
        "<finish status=\"success\" />"
    )


def build_records(repo_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, task in enumerate(TASKS, start=1):
        snippets = _collect_retrieval(task, repo_root)
        record = {
            "id": f"scbe-agentic-workbench-v1-{index:03d}",
            "category": "agentic-coding-workbench",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": task.user_goal},
                {"role": "assistant", "content": _assistant_trace(task, snippets)},
            ],
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "agentic_workbench_v1",
                "task_id": task.task_id,
                "title": task.title,
                "research_grounding": [item["id"] for item in RESEARCH_GROUNDING],
                "research_source_urls": [item["source_url"] for item in RESEARCH_GROUNDING],
                "retrieved_files": [item["path"] for item in snippets],
                "retrieval_count": len(snippets),
                "tongues": list(task.route.tongues),
                "layers": list(task.route.layers),
                "phase": task.route.phase,
                "harness_mode": task.route.harness_mode,
                "verification": list(task.verification),
                "difficulty": "hard" if len(task.route.tongues) >= 5 else "medium",
            },
        }
        records.append(record)
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_site_index(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            index_payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index_payload = {}
    else:
        index_payload = {}
    if not isinstance(index_payload, dict):
        index_payload = {}
    tasks = index_payload.setdefault("tasks", {})
    if not isinstance(tasks, dict):
        tasks = {}
        index_payload["tasks"] = tasks
    index_payload["updated"] = payload["updated"]
    preview = {
        "record_count": payload["record_count"],
        "route_counts": payload["route_counts"],
        "training_file": payload["training_file"],
    }
    tasks["agentic_coding_workbench"] = {
        "file": "agentic-coding-workbench.json",
        "updated": payload["updated"],
        "preview": str(preview),
    }
    write_json(path, index_payload)


def build_payload(records: list[dict[str, Any]], output: Path) -> dict[str, Any]:
    updated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    route_counts: dict[str, int] = {}
    for record in records:
        for tongue in record["metadata"]["tongues"]:
            route_counts[tongue] = route_counts.get(tongue, 0) + 1
    training_file = output.relative_to(REPO_ROOT).as_posix() if output.is_relative_to(REPO_ROOT) else str(output)
    return {
        "schema_version": "scbe_agentic_coding_workbench_v1",
        "updated": updated,
        "record_count": len(records),
        "training_file": training_file,
        "research_grounding": list(RESEARCH_GROUNDING),
        "route_counts": route_counts,
        "records": [
            {
                "id": row["id"],
                "title": row["metadata"]["title"],
                "task_id": row["metadata"]["task_id"],
                "tongues": row["metadata"]["tongues"],
                "layers": row["metadata"]["layers"],
                "harness_mode": row["metadata"]["harness_mode"],
                "verification": row["metadata"]["verification"],
                "retrieved_files": row["metadata"]["retrieved_files"],
            }
            for row in records
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the SCBE agentic coding workbench packet")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--site-data", default=str(DEFAULT_SITE_DATA))
    parser.add_argument("--site-index", default=str(DEFAULT_SITE_INDEX))
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output).resolve()
    manifest = Path(args.manifest).resolve()
    site_data = Path(args.site_data).resolve()
    site_index = Path(args.site_index).resolve()

    records = build_records(repo_root)
    write_jsonl(output, records)
    payload = build_payload(records, output)
    write_json(manifest, payload)
    write_json(site_data, payload)
    update_site_index(site_index, payload)

    summary = {
        "record_count": payload["record_count"],
        "training_file": str(output),
        "manifest": str(manifest),
        "site_data": str(site_data),
        "site_index": str(site_index),
        "route_counts": payload["route_counts"],
    }
    print(json.dumps(summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
