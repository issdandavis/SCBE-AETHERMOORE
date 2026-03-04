#!/usr/bin/env python3
"""
Push normalized Perplexity JSONL dataset to Hugging Face Hub.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATA_PATH = "data/perplexity/normalized/perplexity_normalized.jsonl"
DEFAULT_HF_REPO = "your-username/aethermore-perplexity"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_repo_id(repo_id: str) -> bool:
    repo_id = (repo_id or "").strip()
    return bool(re.match(r"^[^/\s]+/[^/\s]+$", repo_id))


def build_readme(repo_id: str, data_path: Path, row_count: int, columns: list[str]) -> str:
    cols = "\n".join(f"- `{c}`" for c in columns)
    return (
        f"# {repo_id}\n\n"
        "Normalized Perplexity thread turns.\n\n"
        f"- Generated at: {utc_now()}\n"
        f"- Source file: `{data_path}`\n"
        f"- Rows: `{row_count}`\n\n"
        "## Columns\n"
        f"{cols}\n"
    )


def render_card_template(
    template_path: Path,
    *,
    repo_id: str,
    row_count: int,
    train_rows: int,
    test_rows: int,
    data_path: Path,
) -> str:
    text = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{REPO_ID}}": repo_id,
        "{{ROW_COUNT}}": str(row_count),
        "{{TRAIN_ROWS}}": str(train_rows),
        "{{TEST_ROWS}}": str(test_rows),
        "{{DATA_PATH}}": str(data_path),
        "{{GENERATED_AT}}": utc_now(),
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def load_hf_libs() -> tuple[Any, Any]:
    try:
        from datasets import load_dataset
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "datasets package is required. Install with: pip install datasets"
        ) from exc
    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "huggingface_hub package is required. Install with: pip install huggingface_hub"
        ) from exc
    return load_dataset, HfApi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push normalized Perplexity dataset JSONL to Hugging Face."
    )
    parser.add_argument("--data-path", default=DEFAULT_DATA_PATH)
    parser.add_argument("--repo-id", default=os.getenv("HF_REPO", DEFAULT_HF_REPO))
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    parser.add_argument("--card-path", default="docs/datasets/perplexity_dataset_card.md")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.05)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def push_to_hf(
    *,
    data_path: Path,
    repo_id: str,
    token: str | None,
    card_path: Path | None,
    private: bool,
    seed: int,
    test_size: float,
    max_rows: int,
    dry_run: bool,
) -> dict[str, Any]:
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {data_path}")
    if not validate_repo_id(repo_id):
        raise ValueError(f"Invalid --repo-id: {repo_id} (expected 'namespace/name').")

    load_dataset, HfApi = load_hf_libs()
    dataset = load_dataset("json", data_files=str(data_path), split="train")
    if max_rows > 0:
        dataset = dataset.select(range(min(max_rows, len(dataset))))
    dataset = dataset.shuffle(seed=seed)
    ds = dataset.train_test_split(test_size=test_size, seed=seed)

    columns = list(ds["train"].column_names)
    train_rows = len(ds["train"])
    test_rows = len(ds["test"])
    row_count = train_rows + test_rows

    summary = {
        "generated_at": utc_now(),
        "repo_id": repo_id,
        "data_path": str(data_path),
        "rows_total": row_count,
        "rows_train": train_rows,
        "rows_test": test_rows,
        "columns": columns,
        "seed": seed,
        "test_size": test_size,
        "dry_run": dry_run,
    }

    if dry_run:
        return summary

    if not token:
        raise RuntimeError("HF token required. Pass --token or set HF_TOKEN.")

    api = HfApi(token=token)
    api.create_repo(
        repo_id=repo_id,
        repo_type="dataset",
        private=private,
        exist_ok=True,
    )

    ds.push_to_hub(
        repo_id=repo_id,
        token=token,
        private=private,
    )

    if card_path and card_path.exists():
        readme = render_card_template(
            card_path,
            repo_id=repo_id,
            row_count=row_count,
            train_rows=train_rows,
            test_rows=test_rows,
            data_path=data_path,
        )
    else:
        readme = build_readme(repo_id, data_path, row_count, columns)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(readme)
        tmp_path = tmp.name

    api.upload_file(
        repo_id=repo_id,
        repo_type="dataset",
        path_or_fileobj=tmp_path,
        path_in_repo="README.md",
        token=token,
    )

    return summary


def main() -> int:
    args = parse_args()
    try:
        summary = push_to_hf(
            data_path=Path(args.data_path),
            repo_id=str(args.repo_id),
            token=(args.token or None),
            card_path=Path(args.card_path) if args.card_path else None,
            private=bool(args.private),
            seed=int(args.seed),
            test_size=float(args.test_size),
            max_rows=int(args.max_rows),
            dry_run=bool(args.dry_run),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[push_to_hf] ERROR: {exc}", file=sys.stderr)
        return 1

    import json

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    main()
