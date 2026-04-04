#!/usr/bin/env python3
"""
merge_training_data.py — Merge and deduplicate all SCBE-AETHERMOORE JSONL training files.

Reads all .jsonl files from training-data/ recursively, normalizes the prompt/response
fields, deduplicates by (prompt, response) content hash, and outputs a single merged file.

Usage:
    python scripts/merge_training_data.py
    python scripts/merge_training_data.py --output training-data/merged_sft.jsonl
    python scripts/merge_training_data.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DATA_DIR = REPO_ROOT / "training-data"
DEFAULT_OUTPUT = TRAINING_DATA_DIR / "merged_sft.jsonl"

# Fields that may hold the "prompt" content depending on the file convention
PROMPT_FIELDS = ("prompt", "instruction")
RESPONSE_FIELD = "response"


def compute_hash(prompt: str, response: str) -> str:
    """Compute a SHA-256 hash of the (prompt, response) pair for deduplication."""
    content = f"{prompt}\x00{response}"
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def extract_prompt(record: dict) -> str | None:
    """Extract the prompt/instruction text from a record, trying known field names."""
    for field in PROMPT_FIELDS:
        if field in record and record[field]:
            return str(record[field])
    return None


def extract_response(record: dict) -> str | None:
    """Extract the response text from a record."""
    if RESPONSE_FIELD in record and record[RESPONSE_FIELD]:
        return str(record[RESPONSE_FIELD])
    return None


def infer_category(filepath: Path) -> str:
    """Infer the category from the file's parent directory or filename."""
    rel = filepath.relative_to(TRAINING_DATA_DIR)
    parts = rel.parts

    if len(parts) > 1:
        # File is in a subdirectory: use the directory name
        return parts[0]
    else:
        # File is at the root of training-data/
        stem = filepath.stem
        # Strip common prefixes
        for prefix in ("sft_", "notion_"):
            if stem.startswith(prefix):
                return stem
        return stem


def normalize_record(record: dict, source_file: Path) -> dict | None:
    """
    Normalize a JSONL record to a canonical {prompt, response, metadata, source_file, category} shape.
    Returns None if the record lacks required fields.
    """
    prompt = extract_prompt(record)
    response = extract_response(record)

    if not prompt or not response:
        return None

    # Build metadata: preserve original metadata if present, add source info
    metadata = record.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {"raw": metadata}

    category = infer_category(source_file)

    # Merge in any extra top-level fields as metadata (exclude prompt/response/metadata)
    extra_keys = set(record.keys()) - {
        "prompt",
        "instruction",
        "response",
        "metadata",
    }
    extras = {k: record[k] for k in extra_keys}
    if extras:
        metadata["_extra"] = extras

    return {
        "prompt": prompt,
        "response": response,
        "metadata": json.dumps(metadata, ensure_ascii=False) if isinstance(metadata, dict) else str(metadata),
        "source_file": str(source_file.relative_to(TRAINING_DATA_DIR)),
        "category": category,
    }


def collect_jsonl_files(root: Path) -> list[Path]:
    """Recursively find all .jsonl files under root."""
    files = sorted(root.rglob("*.jsonl"))
    return files


def merge_and_deduplicate(
    input_dir: Path,
    output_path: Path,
    dry_run: bool = False,
) -> dict:
    """
    Main merge pipeline.

    Returns a stats dict with total_files, total_pairs, unique_pairs,
    duplicates_removed, skipped_malformed, and per-category counts.
    """
    jsonl_files = collect_jsonl_files(input_dir)

    # Skip the output file itself if it already exists in the directory
    output_resolved = output_path.resolve()
    jsonl_files = [f for f in jsonl_files if f.resolve() != output_resolved]

    seen_hashes: set[str] = set()
    unique_records: list[dict] = []
    stats = {
        "total_files": len(jsonl_files),
        "total_pairs": 0,
        "unique_pairs": 0,
        "duplicates_removed": 0,
        "skipped_malformed": 0,
        "skipped_empty_lines": 0,
        "per_file": {},
        "per_category": defaultdict(lambda: {"total": 0, "unique": 0, "duplicates": 0}),
    }

    for filepath in jsonl_files:
        file_stats = {"total": 0, "unique": 0, "duplicates": 0, "malformed": 0}
        rel_path = str(filepath.relative_to(input_dir))

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for _line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        stats["skipped_empty_lines"] += 1
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        file_stats["malformed"] += 1
                        stats["skipped_malformed"] += 1
                        continue

                    normalized = normalize_record(record, filepath)
                    if normalized is None:
                        file_stats["malformed"] += 1
                        stats["skipped_malformed"] += 1
                        continue

                    file_stats["total"] += 1
                    stats["total_pairs"] += 1

                    content_hash = compute_hash(normalized["prompt"], normalized["response"])
                    category = normalized["category"]

                    stats["per_category"][category]["total"] += 1

                    if content_hash in seen_hashes:
                        file_stats["duplicates"] += 1
                        stats["duplicates_removed"] += 1
                        stats["per_category"][category]["duplicates"] += 1
                        continue

                    seen_hashes.add(content_hash)
                    file_stats["unique"] += 1
                    stats["unique_pairs"] += 1
                    stats["per_category"][category]["unique"] += 1
                    unique_records.append(normalized)

        except Exception as e:
            print(f"  ERROR reading {rel_path}: {e}", file=sys.stderr)
            file_stats["malformed"] += 1

        stats["per_file"][rel_path] = file_stats

    # Write output
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as out:
            for rec in unique_records:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Convert defaultdict to regular dict for clean output
    stats["per_category"] = dict(stats["per_category"])

    return stats


def print_report(stats: dict, output_path: Path, dry_run: bool) -> None:
    """Print a human-readable merge report."""
    print("=" * 68)
    print("  SCBE-AETHERMOORE Training Data Merge Report")
    print("=" * 68)
    print()

    if dry_run:
        print("  ** DRY RUN -- no files written **")
        print()

    print(f"  Input directory:    {TRAINING_DATA_DIR}")
    print(f"  Output file:        {output_path}")
    print()
    print(f"  Total JSONL files:  {stats['total_files']}")
    print(f"  Total pairs read:   {stats['total_pairs']}")
    print(f"  Unique pairs:       {stats['unique_pairs']}")
    print(f"  Duplicates removed: {stats['duplicates_removed']}")
    print(f"  Skipped malformed:  {stats['skipped_malformed']}")
    print(f"  Skipped empty:      {stats['skipped_empty_lines']}")
    print()

    # Category breakdown
    print("  Category Breakdown:")
    print("  " + "-" * 60)
    print(f"  {'Category':<30} {'Total':>7} {'Unique':>7} {'Dupes':>7}")
    print("  " + "-" * 60)

    for cat in sorted(stats["per_category"].keys()):
        c = stats["per_category"][cat]
        print(f"  {cat:<30} {c['total']:>7} {c['unique']:>7} {c['duplicates']:>7}")

    print("  " + "-" * 60)
    print(f"  {'TOTAL':<30} {stats['total_pairs']:>7} {stats['unique_pairs']:>7} {stats['duplicates_removed']:>7}")
    print()

    if not dry_run:
        # Show file size
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  Output file size:   {size_mb:.2f} MB")
            print()

    print("=" * 68)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge and deduplicate SCBE-AETHERMOORE training JSONL files.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path for merged JSONL (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        default=TRAINING_DATA_DIR,
        help=f"Input directory to scan (default: {TRAINING_DATA_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing any files, just print stats.",
    )
    parser.add_argument(
        "--stats-json",
        type=Path,
        default=None,
        help="Optional path to write stats as JSON.",
    )

    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"ERROR: Input directory does not exist: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {args.input_dir} for JSONL files...")
    stats = merge_and_deduplicate(args.input_dir, args.output, dry_run=args.dry_run)
    print_report(stats, args.output, args.dry_run)

    if args.stats_json and not args.dry_run:
        with open(args.stats_json, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"  Stats written to: {args.stats_json}")

    # Exit with error code if zero unique pairs found
    if stats["unique_pairs"] == 0:
        print("WARNING: No valid training pairs found!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
