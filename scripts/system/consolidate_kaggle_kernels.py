#!/usr/bin/env python3
"""Inventory and consolidate Kaggle kernels without deleting by default.

Kaggle has no folder primitive for notebooks/kernels. This script creates a
repo-local source-of-truth inventory, classifies kernels into active lanes, and
emits reversible pull/delete commands so cleanup is deliberate instead of
terminal-scroll archaeology.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "docs" / "map-room" / "KAGGLE_KERNEL_CONSOLIDATION_2026-04-25.md"
DEFAULT_JSON = REPO_ROOT / "artifacts" / "kaggle_consolidation" / "kaggle_kernel_inventory.json"
DEFAULT_PULL_ROOT = REPO_ROOT / "artifacts" / "kaggle_kernel_archive"


@dataclass(frozen=True)
class KernelRow:
    ref: str
    title: str
    author: str
    last_run_time: str
    total_votes: str
    slug: str
    lane: str
    recommendation: str
    reason: str


def run_cmd(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def fetch_kernel_csv(page_size: int) -> str:
    result = run_cmd(
        [
            "kaggle",
            "kernels",
            "list",
            "--mine",
            "--csv",
            "--page-size",
            str(page_size),
            "--sort-by",
            "dateRun",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout


def parse_rows(raw_csv: str) -> list[dict[str, str]]:
    lines = [line for line in raw_csv.splitlines() if line.strip() and not line.startswith("Warning:")]
    reader = csv.DictReader(lines)
    rows: list[dict[str, str]] = []
    for row in reader:
        if not row.get("ref"):
            continue
        rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def classify(ref: str, title: str) -> tuple[str, str, str]:
    slug = ref.split("/", 1)[-1]
    text = f"{slug} {title}".lower()

    active_slugs = {
        "polly-auto-geoseal-stage6-repair-v7",
        "scbe-coding-agent-qlora-v2",
        "scbe-coding-agent-kaggle",
        "polly-hf-train-kaggle",
    }
    if slug in active_slugs:
        return "active-training", "keep", "current coding/training lane"
    if "polly-auto" in text:
        return "polly-auto-archive", "keep-or-archive", "generated training round; preserve until outputs are checked"
    if "scbe-code" in text or "coder" in text or "coding" in text:
        return "code-experiment-archive", "archive", "older code-model experiment"
    if "governance" in text or "pqc" in text or "lattice" in text or "quasicrystal" in text:
        return "research-archive", "archive", "older research/security experiment"
    if "copy-of" in text or text.startswith("untitled") or re.search(r"\bnotebook[0-9a-f]{6,}\b", text):
        return "junk-or-unnamed", "archive-then-delete-candidate", "copy/untitled/random notebook slug"
    if "training" in text or "qlora" in text or "finetune" in text or "fine-tune" in text:
        return "training-archive", "archive", "older generic training notebook"
    return "uncategorized", "review", "needs manual review"


def build_inventory(raw_rows: Iterable[dict[str, str]]) -> list[KernelRow]:
    inventory: list[KernelRow] = []
    for raw in raw_rows:
        ref = raw["ref"]
        slug = ref.split("/", 1)[-1]
        lane, recommendation, reason = classify(ref, raw.get("title", ""))
        inventory.append(
            KernelRow(
                ref=ref,
                title=raw.get("title", ""),
                author=raw.get("author", ""),
                last_run_time=raw.get("lastRunTime", ""),
                total_votes=raw.get("totalVotes", ""),
                slug=slug,
                lane=lane,
                recommendation=recommendation,
                reason=reason,
            )
        )
    return inventory


def render_markdown(inventory: list[KernelRow], *, json_path: Path, pull_root: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    counts: dict[str, int] = {}
    rec_counts: dict[str, int] = {}
    for item in inventory:
        counts[item.lane] = counts.get(item.lane, 0) + 1
        rec_counts[item.recommendation] = rec_counts.get(item.recommendation, 0) + 1

    lines = [
        "# Kaggle Kernel Consolidation - 2026-04-25",
        "",
        f"- Generated: `{stamp}`",
        f"- Total kernels inventoried: `{len(inventory)}`",
        f"- Machine-readable inventory: `{json_path}`",
        f"- Archive pull root: `{pull_root}`",
        "- Delete policy: no remote delete is performed by the script unless `--apply-delete-candidates` is used.",
        "",
        "## Summary",
        "",
        "| Lane | Count |",
        "|---|---:|",
    ]
    for lane, count in sorted(counts.items()):
        lines.append(f"| `{lane}` | {count} |")
    lines.extend(["", "| Recommendation | Count |", "|---|---:|"])
    for rec, count in sorted(rec_counts.items()):
        lines.append(f"| `{rec}` | {count} |")

    lines.extend(
        [
            "",
            "## Active Keep Set",
            "",
            "| Ref | Title | Last Run | Reason |",
            "|---|---|---|---|",
        ]
    )
    for item in inventory:
        if item.recommendation == "keep":
            lines.append(f"| `{item.ref}` | {item.title} | `{item.last_run_time}` | {item.reason} |")

    lines.extend(
        [
            "",
            "## Archive Or Delete Candidates",
            "",
            "| Ref | Title | Lane | Recommendation | Last Run | Reason |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in inventory:
        if item.recommendation != "keep":
            lines.append(
                f"| `{item.ref}` | {item.title} | `{item.lane}` | `{item.recommendation}` | "
                f"`{item.last_run_time}` | {item.reason} |"
            )

    lines.extend(
        [
            "",
            "## Commands",
            "",
            "Pull every kernel into a local archive:",
            "",
            "```powershell",
            "python scripts\\system\\consolidate_kaggle_kernels.py --pull-archive",
            "```",
            "",
            "After reviewing the archive, delete only generated copy/untitled/random-slug candidates:",
            "",
            "```powershell",
            "python scripts\\system\\consolidate_kaggle_kernels.py --apply-delete-candidates",
            "```",
            "",
            "Check the live Stage 6 Kaggle lane:",
            "",
            "```powershell",
            "kaggle kernels status issacizrealdavis/polly-auto-geoseal-stage6-repair-v7",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, inventory: list[KernelRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "scbe_kaggle_kernel_inventory_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(inventory),
        "kernels": [asdict(item) for item in inventory],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def pull_archive(inventory: list[KernelRow], pull_root: Path) -> None:
    pull_root.mkdir(parents=True, exist_ok=True)
    for item in inventory:
        dest = pull_root / item.lane / item.slug
        dest.mkdir(parents=True, exist_ok=True)
        result = run_cmd(["kaggle", "kernels", "pull", item.ref, "-p", str(dest), "-m"], timeout=180)
        status = "OK" if result.returncode == 0 else "FAIL"
        print(f"{status} pull {item.ref} -> {dest}")
        if result.returncode != 0:
            print((result.stderr or result.stdout).strip()[:600])


def delete_candidates(inventory: list[KernelRow]) -> int:
    deleted = 0
    for item in inventory:
        if item.recommendation != "archive-then-delete-candidate":
            continue
        result = run_cmd(["kaggle", "kernels", "delete", item.ref], timeout=60)
        status = "OK" if result.returncode == 0 else "FAIL"
        print(f"{status} delete {item.ref}")
        if result.returncode == 0:
            deleted += 1
        else:
            print((result.stderr or result.stdout).strip()[:600])
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory and consolidate Kaggle kernels.")
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--pull-root", type=Path, default=DEFAULT_PULL_ROOT)
    parser.add_argument("--pull-archive", action="store_true", help="Pull all kernel source/metadata into local archive.")
    parser.add_argument(
        "--apply-delete-candidates",
        action="store_true",
        help="Delete only kernels classified as archive-then-delete-candidate. Review report first.",
    )
    args = parser.parse_args()

    raw = fetch_kernel_csv(args.page_size)
    inventory = build_inventory(parse_rows(raw))
    write_json(args.json_out, inventory)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(inventory, json_path=args.json_out, pull_root=args.pull_root), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.json_out}")
    print(f"Inventoried {len(inventory)} kernels")

    if args.pull_archive:
        pull_archive(inventory, args.pull_root)
    if args.apply_delete_candidates:
        deleted = delete_candidates(inventory)
        print(f"Deleted {deleted} delete candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
