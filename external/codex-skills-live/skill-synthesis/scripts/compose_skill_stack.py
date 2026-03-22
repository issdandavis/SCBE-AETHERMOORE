#!/usr/bin/env python3
"""Compose an ordered multi-skill stack from a task description."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

SKILLS_ROOT = Path(r"C:\Users\issda\.codex\skills")
TOKEN_RE = re.compile(r"[a-zA-Z0-9_\-]+")


@dataclass
class SkillScore:
    skill: str
    score: float
    reasons: list[str]


KEYWORD_MAP = {
    "arxiv": ["aetherbrowser-arxiv-nav", "hydra-clawbot-synthesis"],
    "github": ["aetherbrowser-github-nav", "scbe-github-systems"],
    "huggingface": ["hugging-face-model-trainer", "hugging-face-cli", "hf-publish-workflow"],
    "notion": ["notion", "notion-research-documentation"],
    "obsidian": ["obsidian-vault-ops", "obsidian"],
    "shopify": ["scbe-shopify-money-flow", "aetherbrowser-shopify-nav", "shopify-management-ops"],
    "gamma": ["living-codex-browser-builder", "article-posting-ops"],
    "vercel": ["vercel-deploy"],
    "deploy": ["vercel-deploy", "development-flow-loop"],
    "browser": ["living-codex-browser-builder", "playwright"],
    "research": ["hydra-clawbot-synthesis", "scbe-research-publishing-autopilot", "video-source-verification"],
    "multi": ["multi-agent-orchestrator", "hydra-clawbot-synthesis"],
    "agent": ["multi-agent-orchestrator", "hydra-clawbot-synthesis"],
    "skill": ["skill-synthesis", "skill-creator"],
    "pipeline": ["development-flow-loop", "scbe-internet-workflow-synthesis"],
    "money": ["scbe-monetization-thought-to-cash", "scbe-shopify-money-flow"],
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def list_skills(root: Path) -> set[str]:
    out = set()
    for p in root.iterdir():
        if p.is_dir() and (p / "SKILL.md").exists():
            out.add(p.name)
    return out


def score_skills(task: str, available: set[str]) -> list[SkillScore]:
    tokens = tokenize(task)
    scores: dict[str, SkillScore] = {}

    for tok in tokens:
        if tok not in KEYWORD_MAP:
            continue
        for candidate in KEYWORD_MAP[tok]:
            if candidate not in available:
                continue
            entry = scores.get(candidate)
            if not entry:
                entry = SkillScore(skill=candidate, score=0.0, reasons=[])
                scores[candidate] = entry
            entry.score += 2.5
            entry.reasons.append(f"keyword:{tok}")

    # Baseline orchestration skills when no strong hits.
    if not scores:
        for fallback in ["development-flow-loop", "multi-agent-orchestrator", "scbe-connector-health-check"]:
            if fallback in available:
                scores[fallback] = SkillScore(skill=fallback, score=1.0, reasons=["fallback"])

    return sorted(scores.values(), key=lambda x: x.score, reverse=True)


def make_packets(selected: list[str]) -> list[dict]:
    packets = []
    packets.append({"packet": "A-discovery", "skills": [s for s in selected if "research" in s or "browser" in s or "video" in s]})
    packets.append({"packet": "B-build", "skills": [s for s in selected if s in {"development-flow-loop", "living-codex-browser-builder", "skill-creator", "skill-synthesis"}]})
    packets.append({"packet": "C-validate", "skills": [s for s in selected if s in {"playwright", "scbe-connector-health-check", "hydra-clawbot-synthesis"}]})
    packets.append({"packet": "D-publish", "skills": [s for s in selected if s in {"vercel-deploy", "article-posting-ops", "hf-publish-workflow", "scbe-shopify-money-flow"}]})
    packets.append({"packet": "E-log", "skills": [s for s in selected if s in {"obsidian-vault-ops", "notion", "notion-knowledge-capture"}]})
    # Keep only non-empty packets.
    return [p for p in packets if p["skills"]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose a multi-skill execution stack")
    parser.add_argument("--task", required=True)
    parser.add_argument("--top", type=int, default=6)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    available = list_skills(SKILLS_ROOT)
    ranked = score_skills(args.task, available)
    selected = [x.skill for x in ranked[: max(1, args.top)]]

    result = {
        "task": args.task,
        "selected_skills": selected,
        "ranked": [asdict(x) for x in ranked],
        "packets": make_packets(selected),
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
