#!/usr/bin/env python3
"""Stage arXiv evidence and markdown notes into Hugging Face-ready training bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from scripts import list_obsidian_vaults as vaults


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "artifacts" / "page_evidence"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "training-data" / "research_bridge"
DEFAULT_NOTE_INPUTS = [
    REPO_ROOT / "docs" / "research",
    REPO_ROOT / "notes" / "round-table",
]
ARXIV_EVIDENCE_PATTERN = "playwriter-arxiv.org-*.json"
SYSTEM_PROMPT = "You are building a source-grounded research memory. " "Preserve only details present in the source."


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip().lower()).strip("-")
    return value or "bundle"


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_text(text: str, *, collapse_newlines: bool = False) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if collapse_newlines:
        normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _shorten(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _extract_arxiv_id(url: str) -> str:
    match = re.search(r"/abs/([^?#]+)", url)
    return match.group(1).strip() if match else ""


def _safe_relative(path: Path, root: Path | None = None) -> str:
    base = root or REPO_ROOT
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path.resolve())


def _iter_arxiv_evidence(evidence_dir: Path) -> list[Path]:
    if not evidence_dir.exists():
        return []
    return sorted(p for p in evidence_dir.glob(ARXIV_EVIDENCE_PATTERN) if p.is_file())


def _iter_note_paths(note_inputs: Sequence[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for raw in note_inputs:
        path = raw.expanduser()
        if not path.exists():
            continue
        candidates: Iterable[Path]
        if path.is_file():
            candidates = [path] if path.suffix.lower() == ".md" else []
        else:
            candidates = (
                candidate
                for candidate in path.rglob("*.md")
                if ".obsidian" not in candidate.parts and not any(part.startswith(".") for part in candidate.parts)
            )
        for candidate in candidates:
            key = str(candidate.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
    return sorted(out)


def _resolve_note_inputs(
    *,
    note_inputs: Sequence[Path],
    use_active_vault: bool,
    vault_subdirs: Sequence[str],
) -> tuple[list[Path], dict[str, Any]]:
    resolved = [path.expanduser() for path in note_inputs]
    active_vault: Path | None = None
    added_vault_paths: list[Path] = []
    if use_active_vault:
        active_vault = vaults.active_vault_path()
        if active_vault and active_vault.exists():
            if vault_subdirs:
                for raw in vault_subdirs:
                    candidate = active_vault / raw
                    if candidate.exists():
                        added_vault_paths.append(candidate)
            else:
                added_vault_paths.append(active_vault)
        resolved.extend(added_vault_paths)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in resolved:
        key = str(path.resolve()).lower() if path.exists() else str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)

    return unique, {
        "use_active_vault": use_active_vault,
        "active_vault_path": str(active_vault.resolve()) if active_vault and active_vault.exists() else "",
        "vault_subdirs": list(vault_subdirs),
        "added_vault_paths": [str(path.resolve()) for path in added_vault_paths],
    }


def _stage_source_copy(source_path: Path, destination_dir: Path, label: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = _text_hash(str(source_path.resolve()))[:10]
    target_name = f"{fingerprint}_{_slug(label)}{source_path.suffix.lower()}"
    target_path = destination_dir / target_name
    shutil.copy2(source_path, target_path)
    return target_path


def _parse_markdown_note(path: Path, max_chars: int) -> dict[str, Any]:
    raw = _clean_text(path.read_text(encoding="utf-8", errors="replace"))
    body = raw
    frontmatter_title = ""
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 4)
        if end != -1:
            frontmatter = raw[4:end]
            body = raw[end + 5 :].strip()
            for line in frontmatter.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                if key.strip().lower() == "title":
                    frontmatter_title = value.strip().strip('"').strip("'")
                    break

    headings = [match.group(1).strip() for match in re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", body)]
    title = frontmatter_title or (headings[0] if headings else path.stem.replace("-", " ").replace("_", " "))
    tasks = [match.group(1).strip() for match in re.finditer(r"(?m)^\s*[-*]\s+\[(?: |x|X)\]\s+(.+?)\s*$", body)]
    summary_seed = re.sub(r"(?m)^#{1,6}\s+.+?$", "", body).strip()
    summary_seed = _shorten(summary_seed, max_chars)
    return {
        "title": title.strip(),
        "headings": headings[:12],
        "tasks": tasks[:10],
        "summary_seed": summary_seed,
        "char_count": len(body),
        "body_excerpt": _shorten(body, max_chars),
    }


def _build_arxiv_record(
    *,
    payload: dict[str, Any],
    source_path: Path,
    staged_path: Path,
    max_excerpt_chars: int,
) -> dict[str, Any]:
    title = _clean_text(str(payload.get("title", "")), collapse_newlines=True)
    url = str(payload.get("url", "")).strip()
    excerpt = _shorten(_clean_text(str(payload.get("excerpt", "")), collapse_newlines=True), max_excerpt_chars)
    arxiv_id = _extract_arxiv_id(url)
    captured_at = str(payload.get("timestamp", "")).strip()
    response_lines = [
        f"Title: {title or 'Unknown'}",
        f"arXiv ID: {arxiv_id or 'unknown'}",
        f"URL: {url or 'unknown'}",
        f"Captured At: {captured_at or 'unknown'}",
        "Excerpt:",
        excerpt or "(empty excerpt)",
    ]
    user_context = "\n".join(
        [
            "Evidence snapshot from arXiv.",
            f"Title: {title or 'Unknown'}",
            f"URL: {url or 'unknown'}",
            f"Captured At: {captured_at or 'unknown'}",
            "Excerpt:",
            excerpt or "(empty excerpt)",
        ]
    )
    response = "\n".join(response_lines)
    return {
        "instruction": "Capture the citable metadata and abstract signal from this arXiv evidence snapshot without inventing claims.",
        "response": response,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_context},
            {"role": "assistant", "content": response},
        ],
        "category": "research_bridge_arxiv",
        "metadata": {
            "source": "arxiv",
            "source_type": "page_evidence",
            "title": title,
            "url": url,
            "arxiv_id": arxiv_id,
            "captured_at": captured_at,
            "source_file": str(source_path.resolve()),
            "staged_source_file": str(staged_path.resolve()),
            "source_hash": _text_hash(user_context),
        },
    }


def _build_note_record(
    *,
    note_path: Path,
    staged_path: Path,
    note: dict[str, Any],
    max_excerpt_chars: int,
) -> dict[str, Any]:
    headings = note["headings"]
    tasks = note["tasks"]
    headings_text = ", ".join(headings[:6]) if headings else "(none)"
    tasks_text = "\n".join(f"- {task}" for task in tasks[:6]) if tasks else "- none"
    summary_seed = _shorten(note["summary_seed"], max_excerpt_chars)
    response = "\n".join(
        [
            f"Title: {note['title']}",
            f"Source Path: {note_path.resolve()}",
            f"Headings: {headings_text}",
            "Key Extract:",
            summary_seed or "(empty note)",
            "Open Tasks:",
            tasks_text,
        ]
    )
    user_context = "\n".join(
        [
            "Research note from markdown.",
            f"Title: {note['title']}",
            f"Source Path: {note_path.resolve()}",
            "Body Excerpt:",
            note["body_excerpt"] or "(empty note)",
        ]
    )
    return {
        "instruction": "Preserve the note's research claims, evidence hooks, and follow-up actions in a source-grounded memory record.",
        "response": response,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_context},
            {"role": "assistant", "content": response},
        ],
        "category": "research_bridge_obsidian",
        "metadata": {
            "source": "obsidian",
            "source_type": "obsidian_markdown",
            "title": note["title"],
            "headings": headings,
            "task_count": len(tasks),
            "char_count": note["char_count"],
            "source_file": str(note_path.resolve()),
            "staged_source_file": str(staged_path.resolve()),
            "source_hash": _text_hash(user_context),
        },
    }


def build_research_training_bundle(
    *,
    evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
    note_inputs: Sequence[Path] = DEFAULT_NOTE_INPUTS,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    bundle_name: str = "research-bridge",
    bundle_stamp: str | None = None,
    dataset_repo: str = "issdandavis/scbe-aethermoore-training-data",
    model_repo: str = "issdandavis/scbe-research-bridge-qwen-0.5b",
    max_excerpt_chars: int = 1400,
    use_active_vault: bool = False,
    vault_subdirs: Sequence[str] = (),
) -> dict[str, Any]:
    created_at = _utc_now_iso()
    stamp = bundle_stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_id = f"{_slug(bundle_name)}-{stamp}"
    bundle_dir = output_root / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    resolved_note_inputs, vault_info = _resolve_note_inputs(
        note_inputs=note_inputs,
        use_active_vault=use_active_vault,
        vault_subdirs=vault_subdirs,
    )

    staged_arxiv_dir = bundle_dir / "sources" / "page_evidence"
    staged_notes_dir = bundle_dir / "sources" / "obsidian"
    corpus_path = bundle_dir / "research_corpus.jsonl"
    manifest_path = bundle_dir / "source_manifest.json"
    hf_manifest_path = bundle_dir / "hf_training_manifest.json"
    report_path = bundle_dir / "bundle_report.md"

    sources: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    dedupe: set[str] = set()

    for evidence_path in _iter_arxiv_evidence(evidence_dir):
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        url = str(payload.get("url", ""))
        if "arxiv.org/abs/" not in url:
            continue
        staged_path = _stage_source_copy(evidence_path, staged_arxiv_dir, evidence_path.stem)
        record = _build_arxiv_record(
            payload=payload,
            source_path=evidence_path,
            staged_path=staged_path,
            max_excerpt_chars=max_excerpt_chars,
        )
        dedupe_key = _text_hash(json.dumps(record["metadata"], sort_keys=True))
        if dedupe_key in dedupe:
            continue
        dedupe.add(dedupe_key)
        records.append(record)
        sources.append(
            {
                "kind": "arxiv_evidence",
                "title": record["metadata"].get("title", ""),
                "source_file": str(evidence_path.resolve()),
                "staged_source_file": str(staged_path.resolve()),
                "arxiv_id": record["metadata"].get("arxiv_id", ""),
                "url": record["metadata"].get("url", ""),
            }
        )

    for note_path in _iter_note_paths(resolved_note_inputs):
        note = _parse_markdown_note(note_path, max_excerpt_chars)
        if not note["summary_seed"] and not note["headings"]:
            continue
        staged_path = _stage_source_copy(note_path, staged_notes_dir, note_path.stem)
        record = _build_note_record(
            note_path=note_path,
            staged_path=staged_path,
            note=note,
            max_excerpt_chars=max_excerpt_chars,
        )
        dedupe_key = _text_hash(json.dumps(record["metadata"], sort_keys=True))
        if dedupe_key in dedupe:
            continue
        dedupe.add(dedupe_key)
        records.append(record)
        sources.append(
            {
                "kind": "obsidian_markdown",
                "title": record["metadata"].get("title", ""),
                "source_file": str(note_path.resolve()),
                "staged_source_file": str(staged_path.resolve()),
                "char_count": record["metadata"].get("char_count", 0),
            }
        )

    if not records:
        raise ValueError("No research sources were found. Provide arXiv evidence files or markdown notes.")

    with corpus_path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts = {
        "records": len(records),
        "arxiv_evidence": sum(1 for row in records if row["category"] == "research_bridge_arxiv"),
        "obsidian_notes": sum(1 for row in records if row["category"] == "research_bridge_obsidian"),
    }

    manifest = {
        "bundle_id": bundle_id,
        "created_at_utc": created_at,
        "bundle_dir": str(bundle_dir.resolve()),
        "counts": counts,
        "inputs": {
            "evidence_dir": str(evidence_dir.resolve()),
            "note_inputs": [str(path.resolve()) for path in resolved_note_inputs if path.exists()],
            "vault": vault_info,
        },
        "outputs": {
            "corpus": str(corpus_path.resolve()),
            "hf_training_manifest": str(hf_manifest_path.resolve()),
            "report": str(report_path.resolve()),
        },
        "sources": sources,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    relative_corpus = _safe_relative(corpus_path)
    hf_manifest = {
        "bundle_id": bundle_id,
        "created_at_utc": created_at,
        "recommended_skill": "$hugging-face-model-trainer",
        "source_strategy": {
            "use_active_vault": use_active_vault,
            "vault_subdirs": list(vault_subdirs),
        },
        "dataset_repo": dataset_repo,
        "model_repo": model_repo,
        "training_method": "sft",
        "suggested_base_model": "Qwen/Qwen2.5-0.5B",
        "local_globs": [relative_corpus],
        "suggested_local_command": (
            "python scripts/train_hf_longrun_placeholder.py "
            f"--dataset-repo {dataset_repo} --model-repo {model_repo} "
            f"--local-glob {relative_corpus} --run-dir training/runs/huggingface/{bundle_id} --no-push-to-hub"
        ),
        "notes": [
            "Use the generated research_corpus.jsonl as a source-grounded SFT seed.",
            "Prefer HF Jobs or the hugging-face-model-trainer skill for real GPU training.",
            "Review bundle_report.md before publishing any model or dataset card.",
        ],
    }
    hf_manifest_path.write_text(json.dumps(hf_manifest, indent=2), encoding="utf-8")

    report_lines = [
        "# Research Training Bridge Bundle",
        "",
        f"- bundle_id: `{bundle_id}`",
        f"- created_at_utc: `{created_at}`",
        f"- records: `{counts['records']}`",
        f"- arxiv_evidence: `{counts['arxiv_evidence']}`",
        f"- obsidian_notes: `{counts['obsidian_notes']}`",
        f"- active_vault: `{vault_info['active_vault_path'] or 'disabled'}`",
        f"- corpus: `{_safe_relative(corpus_path)}`",
        f"- hf_training_manifest: `{_safe_relative(hf_manifest_path)}`",
        "",
        "## Source Inputs",
    ]
    for source in sources:
        report_lines.append(f"- `{source['kind']}` :: `{source.get('title', '')}` :: `{source['source_file']}`")
    report_lines += [
        "",
        "## Training Guidance",
        f"- Dataset repo target: `{dataset_repo}`",
        f"- Model repo target: `{model_repo}`",
        "- Review the staged sources before merging this bundle into broader corpora.",
        "- Keep this bridge source-grounded; do not invent synthetic claims before evidence review.",
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return {
        "ok": True,
        "bundle_id": bundle_id,
        "bundle_dir": str(bundle_dir.resolve()),
        "counts": counts,
        "corpus_path": str(corpus_path.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "hf_training_manifest_path": str(hf_manifest_path.resolve()),
        "report_path": str(report_path.resolve()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a source-grounded research training bundle.")
    parser.add_argument(
        "--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR), help="Directory containing page-evidence JSON files."
    )
    parser.add_argument(
        "--note-input",
        action="append",
        default=[],
        help="Markdown file or directory to ingest (repeatable). Defaults to docs/research + notes/round-table.",
    )
    parser.add_argument(
        "--use-active-vault", action="store_true", help="Also ingest the active Obsidian vault from desktop config."
    )
    parser.add_argument(
        "--vault-subdir",
        action="append",
        default=[],
        help="Subdirectory inside the active Obsidian vault to ingest (repeatable). Only used with --use-active-vault.",
    )
    parser.add_argument(
        "--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Directory where bundle folders are written."
    )
    parser.add_argument("--bundle-name", default="research-bridge", help="Bundle name prefix.")
    parser.add_argument("--bundle-stamp", default=None, help="Optional deterministic timestamp suffix.")
    parser.add_argument(
        "--dataset-repo", default="issdandavis/scbe-aethermoore-training-data", help="Suggested HF dataset repo."
    )
    parser.add_argument(
        "--model-repo", default="issdandavis/scbe-research-bridge-qwen-0.5b", help="Suggested HF model repo."
    )
    parser.add_argument(
        "--max-excerpt-chars", type=int, default=1400, help="Max source chars copied into each training row."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    note_inputs = [Path(path) for path in args.note_input] if args.note_input else list(DEFAULT_NOTE_INPUTS)
    result = build_research_training_bundle(
        evidence_dir=Path(args.evidence_dir),
        note_inputs=note_inputs,
        output_root=Path(args.output_root),
        bundle_name=args.bundle_name,
        bundle_stamp=args.bundle_stamp,
        dataset_repo=args.dataset_repo,
        model_repo=args.model_repo,
        max_excerpt_chars=args.max_excerpt_chars,
        use_active_vault=args.use_active_vault,
        vault_subdirs=args.vault_subdir,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[research-training-bridge] bundle={result['bundle_id']} records={result['counts']['records']}")
        print(f"  corpus: {result['corpus_path']}")
        print(f"  manifest: {result['manifest_path']}")
        print(f"  hf_manifest: {result['hf_training_manifest_path']}")
        print(f"  report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
