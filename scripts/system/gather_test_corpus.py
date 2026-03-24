"""Gather Test Corpus — Pull records from all data sources into one corpus
=========================================================================

Scans: training-data JSONL, Notion export, lore sessions, game sessions,
OneDrive lore files, Obsidian vault, and HF funnel data.

Outputs a single JSONL at artifacts/test_corpus/gathered_corpus.jsonl
with a uniform schema:

  {
    "id": "...",
    "text": "...",
    "source": "mega_ingest|lore|game|notion|onedrive|obsidian|funnel",
    "category": "...",
    "tongue": "KO|AV|RU|CA|UM|DR|unknown",
    "char_count": 123,
    "word_count": 45
  }

Usage:
  python scripts/system/gather_test_corpus.py
  python scripts/system/gather_test_corpus.py --max-per-source 100 --sample-seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "artifacts" / "test_corpus"

WORD_RE = re.compile(r"[A-Za-z0-9_']+")


def _record(text: str, source: str, category: str = "", tongue: str = "unknown") -> Optional[Dict[str, Any]]:
    """Build a uniform record, skip empties."""
    text = (text or "").strip()
    if len(text) < 20:
        return None
    words = WORD_RE.findall(text)
    rid = hashlib.blake2s(text.encode("utf-8", errors="replace"), digest_size=8).hexdigest()
    return {
        "id": f"{source}-{rid}",
        "text": text[:8000],  # cap at 8K chars
        "source": source,
        "category": category,
        "tongue": tongue,
        "char_count": len(text),
        "word_count": len(words),
    }


def _load_jsonl(path: Path, source: str, max_records: int) -> List[Dict[str, Any]]:
    """Load JSONL, extract text from common field names."""
    records = []
    if not path.exists():
        return records
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if len(records) >= max_records:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract text from common fields
                text_parts = []
                for key in ("prompt", "instruction", "input", "question"):
                    if key in obj and isinstance(obj[key], str):
                        text_parts.append(obj[key])
                for key in ("response", "output", "answer", "completion", "text", "content"):
                    if key in obj and isinstance(obj[key], str):
                        text_parts.append(obj[key])

                text = "\n".join(text_parts)
                tongue = obj.get("encoding_tongue", obj.get("tongue", "unknown"))
                category = obj.get("event_type", obj.get("category", ""))
                meta = obj.get("metadata", {})
                if isinstance(meta, dict):
                    category = category or meta.get("topic", "")

                rec = _record(text, source, category, tongue)
                if rec:
                    records.append(rec)
    except Exception:
        pass
    return records


def _load_text_files(directory: Path, source: str, max_files: int, extensions: set) -> List[Dict[str, Any]]:
    """Load plain text / docx-as-text files."""
    records = []
    if not directory.exists():
        return records
    files = sorted(directory.rglob("*"))
    count = 0
    for f in files:
        if count >= max_files:
            break
        if f.suffix.lower() not in extensions:
            continue
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rec = _record(text, source, category=f.stem[:50])
        if rec:
            records.append(rec)
            count += 1
    return records


def _load_obsidian(vault_path: Path, source: str, max_files: int) -> List[Dict[str, Any]]:
    """Load markdown notes from Obsidian vault."""
    return _load_text_files(vault_path, source, max_files, {".md"})


def gather(max_per_source: int = 200, sample_seed: int = 42) -> Dict[str, Any]:
    """Gather records from all sources."""
    rng = random.Random(sample_seed)
    all_records: List[Dict[str, Any]] = []
    source_counts: Dict[str, int] = {}

    def _add(records: List[Dict[str, Any]], source: str):
        if len(records) > max_per_source:
            records = rng.sample(records, max_per_source)
        all_records.extend(records)
        source_counts[source] = len(records)

    # 1. Mega ingest SFT (largest curated set)
    _add(
        _load_jsonl(REPO_ROOT / "training-data" / "mega_ingest_sft.jsonl", "mega_ingest", max_per_source), "mega_ingest"
    )

    # 2. Merged SFT
    _add(_load_jsonl(REPO_ROOT / "training-data" / "merged_sft.jsonl", "merged_sft", max_per_source), "merged_sft")

    # 3. Governance SFT
    _add(_load_jsonl(REPO_ROOT / "training-data" / "sft_governance.jsonl", "governance", max_per_source), "governance")

    # 4. Codebase SFT
    _add(_load_jsonl(REPO_ROOT / "training-data" / "sft_codebase.jsonl", "codebase", max_per_source), "codebase")

    # 5. Lore sessions
    lore_dir = REPO_ROOT / "training-data" / "lore_sessions"
    lore_recs = []
    if lore_dir.exists():
        for f in sorted(lore_dir.glob("*.jsonl")):
            lore_recs.extend(_load_jsonl(f, "lore", max_per_source))
    _add(lore_recs, "lore")

    # 6. Game sessions
    game_dir = REPO_ROOT / "training-data" / "game_sessions"
    game_recs = []
    if game_dir.exists():
        for f in sorted(game_dir.glob("*.jsonl")):
            game_recs.extend(_load_jsonl(f, "game", max_per_source))
    _add(game_recs, "game")

    # 7. Math sessions
    _add(
        _load_jsonl(REPO_ROOT / "training-data" / "math_sessions" / "math_patterns.jsonl", "math", max_per_source),
        "math",
    )

    # 8. Architecture sessions
    arch_dir = REPO_ROOT / "training-data" / "architecture_sessions"
    arch_recs = []
    if arch_dir.exists():
        for f in sorted(arch_dir.glob("*.jsonl")):
            arch_recs.extend(_load_jsonl(f, "architecture", max_per_source))
    _add(arch_recs, "architecture")

    # 9. Notion clean export
    _add(_load_jsonl(REPO_ROOT / "training-data" / "notion_raw_clean.jsonl", "notion", max_per_source), "notion")

    # 10. HF funnel cross-model
    _add(
        _load_jsonl(REPO_ROOT / "training-data" / "funnel_cross_model" / "sft_pairs.jsonl", "funnel", max_per_source),
        "funnel",
    )

    # 11. Knowledge base
    kb_dir = REPO_ROOT / "training-data" / "knowledge-base"
    kb_recs = []
    if kb_dir.exists():
        for f in sorted(kb_dir.glob("*.jsonl")):
            kb_recs.extend(_load_jsonl(f, "knowledge", max_per_source))
    _add(kb_recs, "knowledge")

    # 12. OneDrive lore text files
    onedrive_lore = Path("C:/Users/issda/OneDrive/Lore_Drafts_and_Chat_Exports")
    _add(_load_text_files(onedrive_lore, "onedrive_lore", max_per_source, {".txt"}), "onedrive_lore")

    # 13. OneDrive writing
    onedrive_writing = Path("C:/Users/issda/OneDrive/Lore_and_Writing")
    _add(
        _load_text_files(onedrive_writing, "onedrive_writing", max_per_source, {".txt", ".docx", ".pdf"}),
        "onedrive_writing",
    )

    # 14. Obsidian vault
    obsidian = Path("C:/Users/issda/OneDrive/Dropbox/Izack Realmforge/AI Workspace")
    _add(_load_obsidian(obsidian, "obsidian", max_per_source), "obsidian")

    # 15. Repo docs (markdown)
    _add(_load_text_files(REPO_ROOT / "docs", "repo_docs", max_per_source, {".md"}), "repo_docs")

    # Deduplicate by id
    seen = set()
    deduped = []
    for rec in all_records:
        if rec["id"] not in seen:
            seen.add(rec["id"])
            deduped.append(rec)

    return {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "max_per_source": max_per_source,
        "sample_seed": sample_seed,
        "total_records": len(deduped),
        "source_counts": source_counts,
        "records": deduped,
    }


def main():
    ap = argparse.ArgumentParser(description="Gather test corpus from all data sources.")
    ap.add_argument("--max-per-source", type=int, default=200, help="Max records per source")
    ap.add_argument("--sample-seed", type=int, default=42)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    result = gather(max_per_source=args.max_per_source, sample_seed=args.sample_seed)

    if args.output:
        out_path = Path(args.output)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "gathered_corpus.jsonl"

    # Write records as JSONL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in result["records"]:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Write manifest
    manifest = {k: v for k, v in result.items() if k != "records"}
    manifest_path = out_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Gathered {result['total_records']} records from {len(result['source_counts'])} sources")
    print(f"Output: {out_path}")
    print(f"Manifest: {manifest_path}")
    print()
    for source, count in sorted(result["source_counts"].items(), key=lambda x: -x[1]):
        print(f"  {source:<20} {count:>5} records")


if __name__ == "__main__":
    main()
