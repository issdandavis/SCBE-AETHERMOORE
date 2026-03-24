"""Library Wing Round-Table Engine.

Runs multi-perspective synthesis loops over compact context capsules,
ChoiceScript-derived episodes, and Obsidian notes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import datetime as dt
import hashlib
import json
import re

TOKEN_RE = re.compile(r"[a-zA-Z0-9_\-\.]+")


@dataclass
class Perspective:
    name: str
    model: str
    role: str
    worktree_lane: str


@dataclass
class LaneNote:
    note_id: str
    round_index: int
    perspective: str
    model: str
    lane: str
    summary: str
    citations: list[str]
    score: float


class LibraryWingRoundTable:
    """Round-table conductor for parallel perspective loops."""

    DEFAULT_PERSPECTIVES = [
        Perspective("research-chair", "hf:qwen2.5-7b", "evidence quality and source ranking", "string_E"),
        Perspective("trainer-chair", "hf:llama3.1-8b", "dataset and training-loop design", "string_A"),
        Perspective("governance-chair", "hf:mistral-7b", "safety and policy gates", "string_D"),
        Perspective("product-chair", "hf:phi-4-mini", "delivery and monetization shape", "string_G"),
        Perspective("ops-chair", "hubspot-legacy", "workflow ops and CRM orchestration", "string_B"),
    ]

    def __init__(self, repo_root: Path, output_root: Path):
        self.repo_root = Path(repo_root)
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t.lower() for t in TOKEN_RE.findall(text)]

    def _score_item(self, item: dict[str, Any], role_terms: set[str], prompt_terms: set[str]) -> float:
        blob = f"{item.get('title', '')} {item.get('text', '')}"
        tokens = self._tokenize(blob)
        role_overlap = sum(1 for t in tokens if t in role_terms)
        prompt_overlap = sum(1 for t in tokens if t in prompt_terms)
        source_boost = 1.5 if item.get("source", "").startswith("capsule") else 1.0
        return source_boost * (2.0 * role_overlap + 1.25 * prompt_overlap + 0.1)

    def _synthesize(
        self, perspective: Perspective, prompt: str, context_items: list[dict[str, Any]], round_index: int
    ) -> LaneNote:
        role_terms = set(self._tokenize(perspective.role))
        prompt_terms = set(self._tokenize(prompt))
        ranked = sorted(
            context_items,
            key=lambda x: self._score_item(x, role_terms=role_terms, prompt_terms=prompt_terms),
            reverse=True,
        )
        top = ranked[:4]
        citations = [str(x.get("source_ref", "")) for x in top if x.get("source_ref")]
        key_points = []
        for item in top:
            title = item.get("title", "untitled")
            snippet = str(item.get("text", ""))[:180].replace("\n", " ")
            key_points.append(f"- {title}: {snippet}")

        summary = (
            f"Role focus: {perspective.role}.\n"
            f"Round guidance: prioritize modular loops, compact context, and parallel lanes.\n"
            f"Selected notes:\n" + "\n".join(key_points)
        )
        digest = hashlib.sha1((perspective.name + str(round_index) + summary).encode("utf-8")).hexdigest()[:12]
        avg_score = 0.0
        if top:
            avg_score = sum(self._score_item(i, role_terms, prompt_terms) for i in top) / len(top)

        return LaneNote(
            note_id=f"{perspective.name}-{round_index}-{digest}",
            round_index=round_index,
            perspective=perspective.name,
            model=perspective.model,
            lane=perspective.worktree_lane,
            summary=summary,
            citations=citations,
            score=round(avg_score, 4),
        )

    def run(
        self, prompt: str, context_items: list[dict[str, Any]], rounds: int = 2, max_workers: int = 5
    ) -> dict[str, Any]:
        now = dt.datetime.now(dt.UTC).isoformat()
        notes: list[LaneNote] = []

        for round_index in range(1, rounds + 1):
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [
                    pool.submit(self._synthesize, p, prompt, context_items, round_index)
                    for p in self.DEFAULT_PERSPECTIVES
                ]
                for fut in as_completed(futures):
                    notes.append(fut.result())

        consensus = self._build_consensus(notes)
        run = {
            "generated_at": now,
            "prompt": prompt,
            "rounds": rounds,
            "perspectives": [asdict(p) for p in self.DEFAULT_PERSPECTIVES],
            "notes": [asdict(n) for n in notes],
            "consensus": consensus,
        }
        return run

    @staticmethod
    def _build_consensus(notes: list[LaneNote]) -> dict[str, Any]:
        themes = {
            "modular_training_loops": 0,
            "compact_context_rag": 0,
            "governance_gates": 0,
            "parallel_worktrees": 0,
        }
        for n in notes:
            lower = n.summary.lower()
            if "modular" in lower or "loop" in lower:
                themes["modular_training_loops"] += 1
            if "context" in lower or "capsule" in lower:
                themes["compact_context_rag"] += 1
            if "safety" in lower or "policy" in lower or "governance" in lower:
                themes["governance_gates"] += 1
            if "lane" in lower or "parallel" in lower or "worktree" in lower:
                themes["parallel_worktrees"] += 1

        top_theme = max(themes, key=themes.get)
        return {
            "theme_votes": themes,
            "top_theme": top_theme,
            "decision": "ship_library_wing_v1",
        }

    def save_run(self, run: dict[str, Any], stem: str) -> tuple[Path, Path]:
        json_path = self.output_root / f"{stem}.json"
        md_path = self.output_root / f"{stem}.md"

        json_path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        lines = [
            f"# Library Wing Round Table Run ({stem})",
            "",
            f"Generated: {run['generated_at']}",
            f"Prompt: {run['prompt']}",
            f"Rounds: {run['rounds']}",
            "",
            "## Consensus",
            f"- Decision: `{run['consensus']['decision']}`",
            f"- Top Theme: `{run['consensus']['top_theme']}`",
            "",
            "## Lane Notes",
        ]
        for n in run["notes"]:
            lines.extend(
                [
                    f"### {n['perspective']} ({n['model']})",
                    f"- Lane: `{n['lane']}`",
                    f"- Score: `{n['score']}`",
                    f"- Citations: {', '.join(n['citations']) if n['citations'] else 'none'}",
                    "",
                    n["summary"],
                    "",
                ]
            )

        md_path.write_text("\n".join(lines), encoding="utf-8")
        return json_path, md_path


def load_capsule_context(capsule_path: Path) -> list[dict[str, Any]]:
    capsule = json.loads(Path(capsule_path).read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    for source in capsule.get("sources", []):
        items.append(
            {
                "source": "capsule",
                "source_ref": source.get("docs_url", ""),
                "title": source.get("title", source.get("chunk_id", "source")),
                "text": f"category={source.get('category', '')} score={source.get('score', 0)}",
            }
        )
    context_text = capsule.get("context_text", "")
    if context_text:
        items.append(
            {
                "source": "capsule_text",
                "source_ref": "capsule_context",
                "title": "Capsule Context",
                "text": context_text,
            }
        )
    return items


def load_obsidian_context(vault_path: Path, max_files: int = 40) -> list[dict[str, Any]]:
    vault = Path(vault_path)
    items: list[dict[str, Any]] = []
    if not vault.exists():
        return items

    files = sorted(vault.rglob("*.md"))[:max_files]
    for path in files:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        title = path.stem
        snippet = raw[:900]
        items.append(
            {
                "source": "obsidian",
                "source_ref": str(path),
                "title": title,
                "text": snippet,
            }
        )
    return items


def load_choicescript_context(notes_path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    path = Path(notes_path)
    if not path.exists():
        return items
    for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        if not line.strip():
            continue
        items.append(
            {
                "source": "choicescript",
                "source_ref": f"{path}#L{idx}",
                "title": f"ChoiceScript Note {idx}",
                "text": line,
            }
        )
    return items
