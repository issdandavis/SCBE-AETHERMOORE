#!/usr/bin/env python3
"""
merge_and_upload.py — Merge all SCBE SFT training data and upload to HuggingFace.

The Ouroboros Pipeline: The snake eats its own tail.
- Raw Notion exports → SFT pairs
- Spiralverse Codex → SFT pairs
- Codebase docs/tests/specs → SFT pairs (self-referential)
- All merged → uploaded to HF → fine-tune model → model governs codebase → repeat

Usage:
    python scripts/merge_and_upload.py                    # merge only
    python scripts/merge_and_upload.py --upload           # merge + upload to HF
    python scripts/merge_and_upload.py --upload --repo-id issdandavis/scbe-aethermoore-training-data
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# System prompt for chat-style output
SYSTEM_PROMPT = (
    "You are SCBE-AETHERMOORE, a 14-layer AI safety and governance framework "
    "built on hyperbolic geometry, post-quantum cryptography, and sacred tongue "
    "neurotransmitter mappings. You implement the ouroboros principle: learning "
    "from your own architecture to strengthen governance decisions. Answer questions "
    "about the architecture, governance, mathematical foundations, sacred tongues, "
    "Spiralverse lore, and security properties accurately and precisely."
)

TRAINING_DATA_DIR = Path(__file__).parent.parent / "training-data"

# All SFT source files to merge (order matters — earlier files get priority for dedup)
SFT_SOURCES = [
    "instruction-tuning/scbe_instructions.jsonl",
    "knowledge-base/system_knowledge.jsonl",
    "knowledge-base/crypto_knowledge.jsonl",
    "sft_notion.jsonl",
    "sft_spiralverse.jsonl",
    "sft_iseki.jsonl",
    "sft_kernel_manifest.jsonl",
    "sft_codebase.jsonl",
    "sft_ouroboros.jsonl",
    "sft_hydra_arch.jsonl",
]

DEFAULT_LEGACY_MAX_RATIO = 0.15

GOVERNANCE_CATEGORIES = {
    "governance",
    "fsgs",
    "trust-tubes",
    "trust-rings",
    "safety",
    "ouroboros-governance",
}

FUNCTION_CATEGORIES = {
    "post-quantum-crypto",
    "spiral-seal",
    "ml-kem",
    "ml-dsa",
    "hamiltonian-routing",
}


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def infer_track(record: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    explicit = metadata.get("track")
    if explicit in {"system", "governance", "functions"}:
        return explicit

    category = record.get("category", "")
    if category in GOVERNANCE_CATEGORIES:
        return "governance"
    if category in FUNCTION_CATEGORIES:
        return "functions"

    source_file = _normalize_path(metadata.get("source_file", ""))
    if source_file.endswith((".py", ".ts", ".js", ".mjs", ".tsx")):
        return "functions"
    return "system"


def infer_source_type(record: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    explicit = metadata.get("source_type")
    if isinstance(explicit, str) and explicit:
        return explicit

    source_file = _normalize_path(metadata.get("source_file", ""))
    origin = metadata.get("origin", "")
    if source_file.startswith("src/symphonic_cipher/") and origin == "codebase_docs":
        return "legacy_docstring"
    if metadata.get("notion_id"):
        return "notion_page"
    if source_file:
        return "code_doc"
    return "unknown"


def infer_validated(source_type: str) -> bool:
    return source_type not in {"legacy_docstring", "notion_page", "unknown"}


def enrich_metadata(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        metadata = record.setdefault("metadata", {})
        source_type = infer_source_type(record)
        metadata["track"] = infer_track(record)
        metadata["source_type"] = source_type
        quality = metadata.get("quality")
        if not isinstance(quality, dict):
            quality = {}
            metadata["quality"] = quality
        quality.setdefault("dedup", True)
        quality.setdefault("validated", infer_validated(source_type))
    return records


def is_legacy_record(record: dict[str, Any]) -> bool:
    metadata = record.get("metadata", {})
    if metadata.get("source_type") == "legacy_docstring":
        return True
    source_file = _normalize_path(metadata.get("source_file", ""))
    origin = metadata.get("origin", "")
    return source_file.startswith("src/symphonic_cipher/") and origin == "codebase_docs"


def apply_legacy_quota(records: list[dict[str, Any]], max_ratio: float) -> list[dict[str, Any]]:
    if max_ratio <= 0:
        return [r for r in records if not is_legacy_record(r)]
    if max_ratio >= 1:
        return records

    legacy = [r for r in records if is_legacy_record(r)]
    non_legacy_count = len(records) - len(legacy)
    if not legacy:
        return records

    max_legacy = int((max_ratio / (1.0 - max_ratio)) * non_legacy_count)
    if non_legacy_count == 0:
        max_legacy = max(1, int(len(records) * max_ratio))

    if len(legacy) <= max_legacy:
        return records

    keep_ids = {id(r) for r in legacy[:max_legacy]}
    filtered: list[dict[str, Any]] = []
    for record in records:
        if not is_legacy_record(record):
            filtered.append(record)
            continue
        if id(record) in keep_ids:
            filtered.append(record)
    return filtered


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file, skipping bad lines."""
    records = []
    if not path.exists():
        print(f"  SKIP (not found): {path.name}", file=sys.stderr)
        return records
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"  WARN: Bad JSON at {path.name}:{i+1}", file=sys.stderr)
    print(f"  Loaded {len(records):>5} from {path.name}", file=sys.stderr)
    return records


def dedup_by_instruction(records: list[dict]) -> list[dict]:
    """Remove duplicates based on instruction text (keep first occurrence)."""
    seen = set()
    unique = []
    for r in records:
        key = r.get("instruction", "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def reassign_ids(records: list[dict]) -> list[dict]:
    """Reassign sequential IDs to all records."""
    for i, r in enumerate(records):
        r["id"] = f"sft-{i+1:05d}"
    return records


def to_chat_format(record: dict) -> dict:
    """Convert SFT record to chat-messages format."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": record["instruction"]},
            {"role": "assistant", "content": record["response"]},
        ]
    }


def write_jsonl(records: list[dict], path: Path) -> None:
    """Write records as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def merge_all(legacy_max_ratio: float = DEFAULT_LEGACY_MAX_RATIO) -> list[dict]:
    """Merge all SFT sources into a single deduplicated list."""
    all_records = []

    print("\n--- Loading SFT Sources ---", file=sys.stderr)
    for source_file in SFT_SOURCES:
        path = TRAINING_DATA_DIR / source_file
        all_records.extend(load_jsonl(path))

    print(f"\nTotal raw records: {len(all_records)}", file=sys.stderr)

    # Deduplicate
    unique = dedup_by_instruction(all_records)
    print(f"After dedup:       {len(unique)}", file=sys.stderr)

    # Enrich metadata for track/source typing before downstream filtering.
    tagged = enrich_metadata(unique)

    # Cap legacy material share to keep training corpus grounded in verified code/docs.
    quota_applied = apply_legacy_quota(tagged, legacy_max_ratio)
    print(
        f"After legacy quota ({legacy_max_ratio:.0%}): {len(quota_applied)}",
        file=sys.stderr,
    )

    # Filter out very short responses
    filtered = [r for r in quota_applied if len(r.get("response", "")) >= 50]
    print(f"After min-length:  {len(filtered)}", file=sys.stderr)

    # Reassign sequential IDs
    final = reassign_ids(filtered)

    return final


def print_summary(records: list[dict]) -> None:
    """Print category breakdown and stats."""
    cats = Counter(r.get("category", "unknown") for r in records)
    origins = Counter(r.get("metadata", {}).get("origin", "unknown") for r in records)
    tracks = Counter(r.get("metadata", {}).get("track", "system") for r in records)

    total_chars = sum(len(r.get("response", "")) for r in records)
    avg_response = total_chars // max(len(records), 1)
    legacy_count = sum(1 for r in records if is_legacy_record(r))
    legacy_ratio = legacy_count / max(len(records), 1)

    print(f"\n--- Merge Summary ---", file=sys.stderr)
    print(f"Total records:     {len(records)}", file=sys.stderr)
    print(f"Avg response len:  {avg_response} chars", file=sys.stderr)

    print(f"\nBy category:", file=sys.stderr)
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}", file=sys.stderr)

    print(f"\nBy track:", file=sys.stderr)
    for track, count in sorted(tracks.items(), key=lambda x: -x[1]):
        print(f"  {track}: {count}", file=sys.stderr)

    print(f"\nBy origin:", file=sys.stderr)
    for origin, count in sorted(origins.items(), key=lambda x: -x[1]):
        print(f"  {origin}: {count}", file=sys.stderr)

    print(f"\nLegacy share: {legacy_count}/{len(records)} ({legacy_ratio:.2%})", file=sys.stderr)


def split_by_track(records: list[dict]) -> dict[str, list[dict]]:
    split: dict[str, list[dict]] = {
        "system": [],
        "governance": [],
        "functions": [],
    }
    for record in records:
        track = record.get("metadata", {}).get("track", "system")
        if track not in split:
            track = "system"
        split[track].append(record)
    return split


def upload_to_hf(repo_id: str, sft_path: Path, chat_path: Path) -> None:
    """Upload training data to HuggingFace Hub."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub", file=sys.stderr)
        sys.exit(1)

    api = HfApi()

    # Create or get repo
    try:
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=False)
        print(f"Repo ready: https://huggingface.co/datasets/{repo_id}", file=sys.stderr)
    except Exception as e:
        print(f"Repo creation: {e}", file=sys.stderr)

    # Upload files
    files_to_upload = [
        (str(sft_path), "data/sft_combined.jsonl"),
        (str(chat_path), "data/sft_combined_chat.jsonl"),
    ]

    for track in ("system", "governance", "functions"):
        track_path = TRAINING_DATA_DIR / f"sft_{track}.jsonl"
        if track_path.exists():
            files_to_upload.append((str(track_path), f"data/sft_{track}.jsonl"))

    # Also upload individual source files if they exist
    for source_file in SFT_SOURCES:
        source_path = TRAINING_DATA_DIR / source_file
        if source_path.exists():
            files_to_upload.append(
                (str(source_path), f"data/sources/{source_path.name}")
            )

    for local_path, remote_path in files_to_upload:
        if Path(local_path).exists():
            print(f"  Uploading {remote_path}...", file=sys.stderr)
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=remote_path,
                repo_id=repo_id,
                repo_type="dataset",
            )

    # Create dataset card
    card = f"""---
license: mit
language:
- en
tags:
- ai-safety
- governance
- cryptography
- hyperbolic-geometry
- post-quantum
- sacred-tongues
- spiralverse
size_categories:
- n<1K
task_categories:
- text-generation
- question-answering
---

# SCBE-AETHERMOORE Training Data

Training data for the SCBE-AETHERMOORE 14-layer AI safety and governance framework.

## The Ouroboros Principle

This dataset is self-referential: the model learns from its own codebase,
governance decisions, test assertions, and architectural documentation.
Like the ouroboros snake eating its own tail, the system strengthens itself
by learning from itself.

## Dataset Structure

- `data/sft_combined.jsonl` — Instruction/response pairs (SFT format)
- `data/sft_combined_chat.jsonl` — Chat-messages format (for AutoTrain)
- `data/sft_system.jsonl` — System architecture/math/narrative records
- `data/sft_governance.jsonl` — Governance/policy/risk records
- `data/sft_functions.jsonl` — Function and implementation records
- `data/sources/` — Individual source files

## Categories

Architecture, post-quantum cryptography, governance (FSGS), sacred tongues
(Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric), Poincare ball
geometry, harmonic scaling, trust tubes, topology, Spiralverse lore, and more.

## Format

### SFT Format
```json
{{"id": "sft-00001", "category": "architecture", "instruction": "...", "response": "...", "metadata": {{...}}}}
```

### Chat Format
```json
{{"messages": [{{"role": "system", "content": "..."}}, {{"role": "user", "content": "..."}}, {{"role": "assistant", "content": "..."}}]}}
```

## License

MIT — Part of the SCBE-AETHERMOORE project (USPTO Patent #63/961,403)

## Author

Issac Daniel Davis — [GitHub](https://github.com/issdandavis/SCBE-AETHERMOORE)
"""

    api.upload_file(
        path_or_fileobj=card.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
    )
    print(f"\nDataset uploaded: https://huggingface.co/datasets/{repo_id}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Merge all SCBE SFT training data and optionally upload to HuggingFace"
    )
    parser.add_argument(
        "--upload", action="store_true", help="Upload to HuggingFace after merging"
    )
    parser.add_argument(
        "--repo-id",
        default="issdandavis/scbe-aethermoore-training-data",
        help="HuggingFace dataset repo ID",
    )
    parser.add_argument(
        "--legacy-max-ratio",
        type=float,
        default=DEFAULT_LEGACY_MAX_RATIO,
        help="Maximum ratio of legacy_docstring records in merged corpus (default: 0.15)",
    )
    args = parser.parse_args()

    # Merge
    records = merge_all(legacy_max_ratio=args.legacy_max_ratio)
    print_summary(records)

    # Write combined SFT
    sft_path = TRAINING_DATA_DIR / "sft_combined.jsonl"
    write_jsonl(records, sft_path)
    print(f"\nWritten: {sft_path} ({sft_path.stat().st_size:,} bytes)", file=sys.stderr)

    # Write chat format
    chat_records = [to_chat_format(r) for r in records]
    chat_path = TRAINING_DATA_DIR / "sft_combined_chat.jsonl"
    write_jsonl(chat_records, chat_path)
    print(f"Written: {chat_path} ({chat_path.stat().st_size:,} bytes)", file=sys.stderr)

    # Write split tracks for modular training workflows.
    split = split_by_track(records)
    for track in ("system", "governance", "functions"):
        track_path = TRAINING_DATA_DIR / f"sft_{track}.jsonl"
        write_jsonl(split[track], track_path)
        print(
            f"Written: {track_path} ({track_path.stat().st_size:,} bytes, {len(split[track])} records)",
            file=sys.stderr,
        )

    # Upload
    if args.upload:
        print(f"\n--- Uploading to HuggingFace ---", file=sys.stderr)
        upload_to_hf(args.repo_id, sft_path, chat_path)


if __name__ == "__main__":
    main()
