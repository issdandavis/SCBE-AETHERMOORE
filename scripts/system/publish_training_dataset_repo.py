#!/usr/bin/env python3
"""Build and restage the training-data repo from repo corpora and export roots."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import claude_export_lore_to_sft as claude_lore
from scripts import draft_corpus_to_sft as draft_corpus
from scripts.system import shard_training_dataset as sharder

DEFAULT_BUILD_ROOT = REPO_ROOT / "_staging" / "training-data-build"
DEFAULT_OUTPUT_REPO = REPO_ROOT / "_staging" / "training-data-repo"
DEFAULT_DATASET_REPO = "issdandavis/scbe-aethermoore-training-data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and optionally publish the SCBE training-data repo")
    parser.add_argument("--include-training-data", action="store_true", help="Include the repo training-data/ tree")
    parser.add_argument("--claude-export-zip", action="append", default=[], help="Claude export zip to convert")
    parser.add_argument("--draft-root", action="append", default=[], help="Draft root directory or file to convert")
    parser.add_argument("--input", action="append", default=[], help="Extra JSONL file or directory to stage")
    parser.add_argument("--build-root", default=str(DEFAULT_BUILD_ROOT), help="Working directory for generated JSONL")
    parser.add_argument("--output-repo", default=str(DEFAULT_OUTPUT_REPO), help="Dataset repo working tree")
    parser.add_argument("--dataset-repo", default=DEFAULT_DATASET_REPO, help="Remote dataset repo identifier")
    parser.add_argument("--max-bytes", type=int, default=sharder.DEFAULT_MAX_BYTES, help="Shard size limit")
    parser.add_argument("--exclude-glob", action="append", default=[], help="Glob for JSONL paths to skip when staging")
    parser.add_argument("--git-commit", action="store_true", help="Commit the restaged dataset repo")
    parser.add_argument("--git-push", action="store_true", help="Push the dataset repo after committing")
    parser.add_argument("--remote-url", default=None, help="Optional git remote URL to set on the output repo")
    parser.add_argument(
        "--commit-message",
        default="feat(dataset): refresh staged training corpus",
        help="Commit message when --git-commit is used",
    )
    return parser.parse_args()


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_generated_inputs(
    *,
    build_root: Path,
    claude_export_zips: Iterable[str],
    draft_roots: Iterable[str],
) -> tuple[list[Path], dict]:
    generated_dir = build_root / "generated"
    _reset_directory(generated_dir)
    build_summary: dict[str, object] = {"generated": []}
    generated_inputs: list[Path] = []

    for idx, raw_zip in enumerate(claude_export_zips, start=1):
        zip_path = _resolve_path(raw_zip)
        if not zip_path.exists():
            continue
        out_path = generated_dir / f"claude_export_lore_{idx:02d}.jsonl"
        summary_path = generated_dir / f"claude_export_lore_{idx:02d}.summary.json"
        _, projects, memory_root = claude_lore.load_export(zip_path)
        doc_rows, doc_stats = claude_lore.project_doc_rows(projects, 6000, 8500, 1200)
        memory_rows, memory_stats = claude_lore.project_memory_rows(projects, memory_root)
        rows = doc_rows + memory_rows
        claude_lore.write_jsonl(out_path, rows)
        summary = {
            "zip_path": str(zip_path),
            "output_path": str(out_path),
            "rows_written": len(rows),
            "doc_rows": len(doc_rows),
            "memory_rows": len(memory_rows),
            **doc_stats,
            **memory_stats,
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
        generated_inputs.append(out_path)
        build_summary["generated"].append({"kind": "claude_export_lore", **summary})

    if draft_roots:
        out_path = generated_dir / "draft_corpus_sft.jsonl"
        summary_path = generated_dir / "draft_corpus_sft.summary.json"
        rows, stats = draft_corpus.collect_rows(
            roots=draft_roots,
            chunk_target=6000,
            chunk_max=8500,
            min_doc_chars=1200,
        )
        draft_corpus.write_jsonl(out_path, rows)
        summary = {
            "roots": [str(_resolve_path(item)) for item in draft_roots],
            "output_path": str(out_path),
            "rows_written": len(rows),
            **stats,
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
        generated_inputs.append(out_path)
        build_summary["generated"].append({"kind": "draft_corpus", **summary})

    return generated_inputs, build_summary


def reset_output_repo(output_repo: Path) -> None:
    output_repo.mkdir(parents=True, exist_ok=True)
    for name in ("data", "manifests"):
        target = output_repo / name
        if target.exists():
            shutil.rmtree(target)
    readme = output_repo / "README.md"
    if readme.exists():
        readme.unlink()


def run_git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def ensure_git_repo(output_repo: Path, remote_url: str | None = None) -> None:
    git_dir = output_repo / ".git"
    if not git_dir.exists():
        run_git(["git", "init", "-b", "main"], output_repo)
    if remote_url:
        remotes = run_git(["git", "remote"], output_repo).splitlines()
        if "origin" in remotes:
            run_git(["git", "remote", "set-url", "origin", remote_url], output_repo)
        else:
            run_git(["git", "remote", "add", "origin", remote_url], output_repo)


def commit_output_repo(output_repo: Path, message: str) -> str | None:
    run_git(["git", "add", "."], output_repo)
    status = run_git(["git", "status", "--short"], output_repo)
    if not status:
        return None
    run_git(["git", "commit", "-m", message], output_repo)
    return run_git(["git", "rev-parse", "HEAD"], output_repo)


def prepare_dataset_repo(
    *,
    include_training_data: bool,
    claude_export_zips: Iterable[str],
    draft_roots: Iterable[str],
    extra_inputs: Iterable[str],
    build_root: Path,
    output_repo: Path,
    dataset_repo: str,
    max_bytes: int,
    exclude_globs: Iterable[str],
) -> dict:
    _reset_directory(build_root)
    generated_inputs, build_summary = build_generated_inputs(
        build_root=build_root,
        claude_export_zips=claude_export_zips,
        draft_roots=draft_roots,
    )
    stage_inputs: list[str] = []
    if include_training_data:
        stage_inputs.append(str(REPO_ROOT / "training-data"))
    stage_inputs.extend(str(path) for path in generated_inputs)
    stage_inputs.extend(str(_resolve_path(item)) for item in extra_inputs)
    if not stage_inputs:
        raise ValueError("No staging inputs were provided")

    reset_output_repo(output_repo)
    manifest = sharder.stage_dataset_repo(
        inputs=stage_inputs,
        output_root=output_repo,
        max_bytes=max_bytes,
        dataset_repo=dataset_repo,
        exclude_globs=exclude_globs,
    )
    build_summary.update(
        {
            "dataset_repo": dataset_repo,
            "stage_inputs": stage_inputs,
            "staged_counts": manifest["counts"],
        }
    )
    summary_path = build_root / "training_dataset_build_summary.json"
    summary_path.write_text(json.dumps(build_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return {"manifest": manifest, "build_summary_path": str(summary_path), "stage_inputs": stage_inputs}


def main() -> int:
    args = parse_args()
    build_root = _resolve_path(args.build_root)
    output_repo = _resolve_path(args.output_repo)
    result = prepare_dataset_repo(
        include_training_data=args.include_training_data,
        claude_export_zips=args.claude_export_zip,
        draft_roots=args.draft_root,
        extra_inputs=args.input,
        build_root=build_root,
        output_repo=output_repo,
        dataset_repo=args.dataset_repo,
        max_bytes=args.max_bytes,
        exclude_globs=args.exclude_glob,
    )

    pushed = False
    commit_sha = None
    if args.git_commit or args.git_push:
        ensure_git_repo(output_repo, remote_url=args.remote_url)
        commit_sha = commit_output_repo(output_repo, args.commit_message)
    if args.git_push:
        run_git(["git", "push", "-u", "origin", "main"], output_repo)
        pushed = True

    payload = {
        "output_repo": str(output_repo),
        "build_summary_path": result["build_summary_path"],
        "manifest_counts": result["manifest"]["counts"],
        "stage_inputs": result["stage_inputs"],
        "commit_sha": commit_sha,
        "pushed": pushed,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
