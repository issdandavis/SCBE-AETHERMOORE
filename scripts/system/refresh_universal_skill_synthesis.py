#!/usr/bin/env python3
"""Build an auto-updating skill synthesis matrix + Sacred Tongues lexicon.

This script scans installed Codex skills and emits machine-readable references
for a meta-skill that orchestrates all skills with intent/emotion routing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILLS_ROOT = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"

TONGUE_CANON: Dict[str, Dict[str, str]] = {
    "KO": {"role": "architect", "emotion": "clarity", "intent": "system_design"},
    "AV": {"role": "coder", "emotion": "creative_flow", "intent": "implementation"},
    "RU": {"role": "reviewer", "emotion": "discernment", "intent": "quality_review"},
    "CA": {"role": "tester", "emotion": "assurance", "intent": "validation"},
    "UM": {"role": "security", "emotion": "vigilance", "intent": "protection"},
    "DR": {"role": "deployer", "emotion": "resolve", "intent": "release_execution"},
}

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "browser": ["browser", "playwright", "web", "navigate", "scrape", "selenium"],
    "research": ["research", "analy", "verify", "source", "evidence"],
    "ops": ["ops", "workflow", "orches", "autom", "pipeline", "bridge"],
    "dev": ["code", "build", "debug", "implement", "dev", "feature"],
    "security": ["security", "governance", "safe", "threat", "auth", "risk"],
    "deployment": ["deploy", "release", "docker", "vercel", "k8s", "infra", "ci"],
    "monetization": ["monet", "sales", "outreach", "market", "pricing", "shopify", "gumroad"],
    "knowledge": ["notion", "obsidian", "document", "wiki", "capture", "meeting"],
}

CATEGORY_TONGUES: Dict[str, List[str]] = {
    "browser": ["AV", "CA"],
    "research": ["KO", "RU"],
    "ops": ["KO", "DR"],
    "dev": ["AV", "RU"],
    "security": ["UM", "RU"],
    "deployment": ["DR", "UM"],
    "monetization": ["KO", "AV", "DR"],
    "knowledge": ["KO", "RU"],
}

TONGUE_PREFIX = {"KO": "ko", "AV": "av", "RU": "ru", "CA": "ca", "UM": "um", "DR": "dr"}


@dataclass
class SkillMeta:
    slug: str
    name: str
    description: str
    path: str
    categories: List[str]
    tongues: List[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_frontmatter(markdown: str) -> Dict[str, Any]:
    match = re.match(r"^---\n(.*?)\n---\n", markdown, re.S)
    if not match:
        return {}

    raw = match.group(1)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    data: Dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _collect_categories(text: str) -> List[str]:
    hay = text.lower()
    out: List[str] = []
    for category, keys in CATEGORY_KEYWORDS.items():
        if any(k in hay for k in keys):
            out.append(category)
    return sorted(out)


def _collect_tongues(categories: List[str]) -> List[str]:
    ordered: List[str] = []
    for category in categories:
        for tongue in CATEGORY_TONGUES.get(category, []):
            if tongue not in ordered:
                ordered.append(tongue)
    if not ordered:
        ordered = ["KO", "AV", "RU"]
    return ordered


def scan_skills(skills_root: Path) -> List[SkillMeta]:
    rows: List[SkillMeta] = []
    if not skills_root.exists():
        return rows

    for path in sorted(skills_root.glob("*/SKILL.md")):
        text = _read_text(path)
        fm = _extract_frontmatter(text)
        slug = path.parent.name
        name = str(fm.get("name", slug)).strip() or slug
        description = str(fm.get("description", "")).strip()
        classifier_text = " ".join([slug, name, description])
        categories = _collect_categories(classifier_text)
        tongues = _collect_tongues(categories)
        rows.append(
            SkillMeta(
                slug=slug,
                name=name,
                description=description,
                path=str(path.parent),
                categories=categories,
                tongues=tongues,
            )
        )
    return rows


def _extract_agentic_characters() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    agent_file = REPO_ROOT / "src" / "agentic" / "agents.ts"
    if not agent_file.exists():
        return out
    text = _read_text(agent_file)
    pattern = re.compile(r"You are the ([A-Za-z]+) Agent \(([^/]+)/([A-Z]{2})\)")
    for role, character, tongue in pattern.findall(text):
        out[tongue] = {"role": role.lower(), "character": character}
    return out


def _extract_runtime_characters() -> Dict[str, str]:
    out: Dict[str, str] = {}
    server_file = REPO_ROOT / "aetherbrowse" / "runtime" / "server.py"
    if not server_file.exists():
        return out
    text = _read_text(server_file)
    pattern = re.compile(r'"([a-zA-Z0-9_]+)": \{"role": "[^"]+", "tongue": "([A-Z]{2})"')
    for name, tongue in pattern.findall(text):
        if tongue not in out:
            out[tongue] = name
    return out


def build_sacred_lexicon() -> Dict[str, Any]:
    agentic = _extract_agentic_characters()
    runtime = _extract_runtime_characters()

    tongues: Dict[str, Any] = {}
    for code, base in TONGUE_CANON.items():
        entry = dict(base)
        entry["prefix"] = TONGUE_PREFIX[code]
        entry["agentic_character"] = agentic.get(code, {}).get("character", "")
        entry["runtime_character"] = runtime.get(code, "")
        tongues[code] = entry

    morph_seeds = [
        ("anchor", "scope_lock"),
        ("pulse", "momentum"),
        ("guard", "risk_control"),
        ("forge", "creation"),
        ("verify", "evidence_check"),
        ("release", "ship"),
    ]
    tokens = []
    for code, info in tongues.items():
        for stem, intent in morph_seeds:
            tokens.append(
                {
                    "token": f"{info['prefix']}:{stem}",
                    "tongue": code,
                    "emotion": info["emotion"],
                    "intent": intent,
                    "decode": f"{code}::{stem}",
                }
            )

    return {
        "generated_at": _utc_now_iso(),
        "format": "prefix:stem",
        "decode_rule": "Lookup token prefix -> tongue metadata; stem carries action semantics.",
        "tongues": tongues,
        "tokens": tokens,
    }


def build_matrix(skills: List[SkillMeta]) -> Dict[str, Any]:
    rows = []
    for skill in skills:
        rows.append(
            {
                "slug": skill.slug,
                "name": skill.name,
                "description": skill.description,
                "path": skill.path,
                "categories": skill.categories,
                "recommended_tongues": skill.tongues,
            }
        )
    return {
        "generated_at": _utc_now_iso(),
        "count": len(rows),
        "rows": rows,
    }


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_outputs(
    *,
    output_dir: Path,
    skills: List[SkillMeta],
    matrix: Dict[str, Any],
    lexicon: Dict[str, Any],
) -> Dict[str, str]:
    _ensure_dir(output_dir)

    inventory_path = output_dir / "skill_inventory.json"
    matrix_path = output_dir / "synthesis_matrix.json"
    lexicon_path = output_dir / "sacred_lexicon.json"
    summary_path = output_dir / "summary.md"

    inventory = {
        "generated_at": _utc_now_iso(),
        "count": len(skills),
        "skills": [
            {
                "slug": s.slug,
                "name": s.name,
                "description": s.description,
                "path": s.path,
            }
            for s in skills
        ],
    }
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    matrix_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    lexicon_path.write_text(json.dumps(lexicon, indent=2), encoding="utf-8")

    summary_lines = [
        "# Universal Skill Synthesis Snapshot",
        "",
        f"- generated_at: {inventory['generated_at']}",
        f"- skill_count: {inventory['count']}",
        "",
        "## Tongues",
    ]
    for code, meta in lexicon["tongues"].items():
        summary_lines.append(
            f"- {code} ({meta.get('prefix')}): role={meta.get('role')}, emotion={meta.get('emotion')}, intent={meta.get('intent')}, "
            f"agentic_character={meta.get('agentic_character')}, runtime_character={meta.get('runtime_character')}"
        )
    summary_lines += ["", "## Top Skills"]
    for row in matrix["rows"][:20]:
        summary_lines.append(
            f"- {row['slug']} -> tongues={','.join(row['recommended_tongues'])} categories={','.join(row['categories'])}"
        )
    summary_lines.append("")
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    return {
        "inventory": str(inventory_path),
        "matrix": str(matrix_path),
        "lexicon": str(lexicon_path),
        "summary": str(summary_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh universal skill synthesis references.")
    parser.add_argument(
        "--skills-root", default=str(DEFAULT_SKILLS_ROOT), help="Root directory that contains installed skill folders"
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_SKILLS_ROOT / "scbe-universal-synthesis" / "references"),
        help="Output directory for synthesis artifacts",
    )
    parser.add_argument(
        "--watch-seconds",
        type=float,
        default=0.0,
        help="If > 0, rerun refresh on this interval (seconds).",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="Optional cap on watch iterations. 0 means run forever while watch mode is enabled.",
    )
    return parser.parse_args()


def _run_once(skills_root: Path, output_dir: Path) -> Dict[str, Any]:
    skills = scan_skills(skills_root)
    matrix = build_matrix(skills)
    lexicon = build_sacred_lexicon()
    outputs = write_outputs(output_dir=output_dir, skills=skills, matrix=matrix, lexicon=lexicon)
    return {
        "ok": True,
        "skills_root": str(skills_root),
        "output_dir": str(output_dir),
        "skill_count": len(skills),
        "outputs": outputs,
    }


def main() -> int:
    args = parse_args()
    skills_root = Path(args.skills_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    watch_seconds = max(0.0, float(args.watch_seconds))
    max_runs = max(0, int(args.max_runs))

    if watch_seconds <= 0.0:
        result = _run_once(skills_root, output_dir)
        print(json.dumps(result, indent=2))
        return 0

    run_index = 0
    try:
        while True:
            run_index += 1
            result = _run_once(skills_root, output_dir)
            result["watch"] = {
                "enabled": True,
                "interval_seconds": watch_seconds,
                "run_index": run_index,
                "max_runs": max_runs,
            }
            print(json.dumps(result, indent=2))

            if max_runs and run_index >= max_runs:
                break
            time.sleep(watch_seconds)
    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
