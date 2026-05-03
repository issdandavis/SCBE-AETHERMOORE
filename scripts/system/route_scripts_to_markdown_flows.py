#!/usr/bin/env python3
"""Route repo scripts into Markdown task-flow cards for agentic workflows.

Scripts stay executable in place. This exporter creates DR/Markdown-readable
cards grouped by deterministic Sacred Tongue route so agents can browse,
handoff, and train on task flows without loading script bodies into prompts.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "notes" / "agentic_task_flows"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.coding_spine.deterministic_tongue_router import route_prompt


TONGUE_FULL_NAMES: dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


@dataclass(frozen=True)
class ScriptFlowCard:
    script_path: str
    card_path: str
    card_tongue: str
    card_tongue_name: str
    card_language: str
    script_tongue: str
    script_tongue_name: str
    script_language: str
    title: str
    purpose: str
    command: str
    source_sha256: str
    route_reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "script_path": self.script_path,
            "card_path": self.card_path,
            "card_tongue": self.card_tongue,
            "card_tongue_name": self.card_tongue_name,
            "card_language": self.card_language,
            "script_tongue": self.script_tongue,
            "script_tongue_name": self.script_tongue_name,
            "script_language": self.script_language,
            "title": self.title,
            "purpose": self.purpose,
            "command": self.command,
            "source_sha256": self.source_sha256,
            "route_reason": self.route_reason,
        }


def _stable_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "script"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _source_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_paths() -> set[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {(REPO_ROOT / line.strip()).resolve() for line in result.stdout.splitlines() if line.strip()}


def _first_doc_sentence(source: str) -> str:
    try:
        module = ast.parse(source)
    except SyntaxError:
        return ""
    doc = ast.get_docstring(module) or ""
    if not doc:
        return ""
    first = " ".join(doc.strip().splitlines()).strip()
    if "." in first:
        first = first.split(".", 1)[0].strip() + "."
    return first


def _purpose_for(path: Path, source: str) -> str:
    doc = _first_doc_sentence(source)
    if doc:
        return doc
    return f"Agentic task flow wrapper for {path.name}."


def _title_for(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title().strip()


def _route_text(path: Path, purpose: str) -> str:
    return f"Task: {path.name}. Purpose: {purpose}."


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _card_markdown(card: ScriptFlowCard) -> str:
    front_matter = {
        "schema_version": "scbe_script_markdown_flow_v1",
        "card_tongue": card.card_tongue,
        "card_tongue_name": card.card_tongue_name,
        "card_language": card.card_language,
        "script_tongue": card.script_tongue,
        "script_tongue_name": card.script_tongue_name,
        "script_language": card.script_language,
        "script_path": card.script_path,
        "source_sha256": card.source_sha256,
    }
    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=True)}")
    lines.extend(
        [
            "---",
            "",
            f"# {card.title}",
            "",
            "## Purpose",
            "",
            card.purpose,
            "",
            "## Route",
            "",
            f"- Card tongue: `{card.card_tongue}` ({card.card_tongue_name})",
            f"- Card language lane: `{card.card_language}`",
            f"- Script tongue: `{card.script_tongue}` ({card.script_tongue_name})",
            f"- Script language lane: `{card.script_language}`",
            f"- Route reason: `{card.route_reason}`",
            "",
            "## Command",
            "",
            "```powershell",
            card.command,
            "```",
            "",
            "## Agentic Use",
            "",
            "- Read this card before invoking the script.",
            "- Keep script execution evidence as a receipt.",
            "- Do not paste the full script body into model context unless debugging requires it.",
            "- Prefer this Markdown card as the compact DR structure packet for handoff.",
            "",
        ]
    )
    return "\n".join(lines)


def iter_script_paths(patterns: Iterable[str], *, include_untracked: bool = False) -> list[Path]:
    paths: set[Path] = set()
    tracked = _tracked_paths()
    for pattern in patterns:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file() and path.suffix == ".py":
                resolved = path.resolve()
                if include_untracked or not tracked or resolved in tracked:
                    paths.add(resolved)
    return sorted(paths)


def route_script(path: Path, out_root: Path) -> ScriptFlowCard:
    source = _read_text(path)
    purpose = _purpose_for(path, source)
    route = route_prompt(_route_text(path, purpose))
    rel_script = path.resolve().relative_to(REPO_ROOT).as_posix()
    folder = out_root / "DR-Markdown" / f"{route.tongue}-{_stable_slug(route.language)}"
    card_path = folder / f"{_stable_slug(path.stem)}.md"
    command = f"python {rel_script}"
    return ScriptFlowCard(
        script_path=rel_script,
        card_path=_display_path(card_path),
        card_tongue="DR",
        card_tongue_name=TONGUE_FULL_NAMES["DR"],
        card_language="Markdown",
        script_tongue=route.tongue,
        script_tongue_name=TONGUE_FULL_NAMES.get(route.tongue, route.tongue),
        script_language=route.language,
        title=_title_for(path),
        purpose=purpose,
        command=command,
        source_sha256=_source_sha(path),
        route_reason=route.reason,
    )


def _clean_out_root(out_root: Path) -> None:
    if not out_root.exists():
        return
    for path in out_root.rglob("*.md"):
        path.unlink()
    manifest_path = out_root / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()


def build_routes(
    patterns: Iterable[str],
    out_root: Path = DEFAULT_OUT,
    *,
    limit: int | None = None,
    include_untracked: bool = False,
) -> dict:
    out_root = out_root.resolve()
    cards = [route_script(path, out_root) for path in iter_script_paths(patterns, include_untracked=include_untracked)]
    if limit is not None:
        cards = cards[:limit]

    _clean_out_root(out_root)
    for card in cards:
        target = Path(card.card_path)
        if not target.is_absolute():
            target = REPO_ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_card_markdown(card), encoding="utf-8")

    by_script_tongue: dict[str, int] = {}
    for card in cards:
        by_script_tongue[card.script_tongue] = by_script_tongue.get(card.script_tongue, 0) + 1

    manifest = {
        "schema_version": "scbe_script_markdown_flow_manifest_v1",
        "generated_at_utc": "stable",
        "out_root": _display_path(out_root),
        "patterns": list(patterns),
        "include_untracked": include_untracked,
        "card_count": len(cards),
        "card_tongue": "DR",
        "card_tongue_name": TONGUE_FULL_NAMES["DR"],
        "card_language": "Markdown",
        "tongue_full_names": TONGUE_FULL_NAMES,
        "by_script_tongue": dict(sorted(by_script_tongue.items())),
        "cards": [card.to_dict() for card in cards],
    }

    manifest_path = out_root / "manifest.json"
    index_path = out_root / "_index.md"
    out_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    index_path.write_text(_index_markdown(manifest), encoding="utf-8")
    return manifest


def _index_markdown(manifest: dict) -> str:
    lines = [
        "# Agentic Script Task Flows",
        "",
        "This folder is generated by `scripts/system/route_scripts_to_markdown_flows.py`.",
        "Scripts remain executable in their source paths; these files are DR/Markdown structure cards for compact agentic handoff.",
        "",
        "## Counts",
        "",
        f"- Cards: `{manifest['card_count']}`",
        f"- Card tongue: `{manifest['card_tongue']}` ({manifest['card_tongue_name']})",
        f"- Card language: `{manifest['card_language']}`",
    ]
    for tongue, count in manifest["by_script_tongue"].items():
        lines.append(f"- `{tongue}` ({manifest['tongue_full_names'].get(tongue, tongue)}): `{count}`")
    lines.extend(["", "## Sacred Tongue Legend", ""])
    for tongue, name in manifest["tongue_full_names"].items():
        lines.append(f"- `{tongue}` = {name}")
    lines.extend(["", "## Cards", ""])
    for card in manifest["cards"]:
        card_path = Path(card["card_path"])
        out_root = Path(manifest["out_root"])
        try:
            link = card_path.relative_to(out_root).as_posix()
        except ValueError:
            link = card_path.name
        lines.append(
            f"- [{card['title']}]({link}) -> `{card['script_path']}` "
            f"(`{card['script_tongue']}` {card['script_tongue_name']}/`{card['script_language']}`)"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern",
        action="append",
        default=None,
        help="Repo-root glob pattern. May be passed more than once. Defaults to scripts/system/*.py.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output markdown folder.")
    parser.add_argument("--limit", type=int, default=None, help="Optional deterministic card limit for smoke runs.")
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked local scripts. Default only emits cards for git-tracked scripts.",
    )
    parser.add_argument("--json", action="store_true", help="Print full manifest JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patterns = args.pattern or ["scripts/system/*.py"]
    manifest = build_routes(patterns, Path(args.out), limit=args.limit, include_untracked=args.include_untracked)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(
            json.dumps(
                {
                    "schema_version": manifest["schema_version"],
                    "out_root": manifest["out_root"],
                    "card_count": manifest["card_count"],
                    "card_tongue": manifest["card_tongue"],
                    "card_tongue_name": manifest["card_tongue_name"],
                    "card_language": manifest["card_language"],
                    "by_script_tongue": manifest["by_script_tongue"],
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
