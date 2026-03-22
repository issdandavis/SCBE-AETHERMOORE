#!/usr/bin/env python3
"""Emit a plan-check artifact that blocks code until research + approval."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lines_or_placeholder(items: list[str], placeholder: str) -> list[str]:
    values = [x.strip() for x in items if x and x.strip()]
    if values:
        return [f"- {x}" for x in values]
    return [f"- {placeholder}"]


def build_markdown(args: argparse.Namespace) -> str:
    sections: list[str] = []
    sections.append(f"# Plan Check: {args.task.strip()}")
    sections.append("")
    sections.append("## Metadata")
    sections.append(f"- generated_at_utc: {utc_now()}")
    sections.append("- phase: planning")
    sections.append("- coding_unlocked: no")
    sections.append("")
    sections.append("## Objective")
    sections.append(f"- {args.task.strip()}")
    sections.append("")
    sections.append("## Constraints")
    sections.extend(lines_or_placeholder(args.constraint, "TODO: add constraints"))
    sections.append("")
    sections.append("## Verified Facts (with sources)")
    if args.source:
        sections.extend([f"- source: {src.strip()}" for src in args.source if src.strip()])
    else:
        sections.append("- TODO: add at least one source")
    sections.append("")
    sections.append("## Assumptions")
    sections.extend(lines_or_placeholder(args.assumption, "TODO: list assumptions"))
    sections.append("")
    sections.append("## Plan Steps")
    if args.plan_step:
        sections.extend([f"{idx}. {step.strip()}" for idx, step in enumerate(args.plan_step, start=1) if step.strip()])
    else:
        sections.extend(["1. TODO: define step 1", "2. TODO: define step 2", "3. TODO: define validation"])
    sections.append("")
    sections.append("## Test Strategy")
    sections.extend(lines_or_placeholder(args.test, "TODO: define tests"))
    sections.append("")
    sections.append("## Risks")
    sections.extend(lines_or_placeholder(args.risk, "TODO: define risks"))
    sections.append("")
    sections.append("## Go/No-Go")
    sections.append("- decision: hold")
    sections.append("- reason: awaiting explicit user approval")
    sections.append("- approval_required: yes")
    sections.append("")
    return "\n".join(sections) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a pre-code plan-check markdown artifact.")
    parser.add_argument("--task", required=True, help="Task title/objective")
    parser.add_argument("--out", required=True, help="Output markdown file path")
    parser.add_argument("--requires-research", action="store_true", help="Fail if no --source is provided")
    parser.add_argument("--constraint", action="append", default=[], help="Constraint item (repeatable)")
    parser.add_argument("--source", action="append", default=[], help="Evidence/source URL or path (repeatable)")
    parser.add_argument("--assumption", action="append", default=[], help="Assumption item (repeatable)")
    parser.add_argument("--plan-step", action="append", default=[], help="Plan step (repeatable)")
    parser.add_argument("--test", action="append", default=[], help="Test strategy item (repeatable)")
    parser.add_argument("--risk", action="append", default=[], help="Risk item (repeatable)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.requires_research and not any(x.strip() for x in args.source):
        print("ERROR: --requires-research was set but no --source values were provided.")
        return 2

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_markdown(args), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
