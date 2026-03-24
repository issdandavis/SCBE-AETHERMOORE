"""Convert SCBE training data to Qwen2.5 ChatML format.

Reads all JSONL files from training-data/, applies the dual-manifold
personality system prompt, and outputs a single HF-ready dataset.

Usage:
    python scripts/convert_to_chat_format.py
    python scripts/convert_to_chat_format.py --push-to-hf
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.gacha_isekai.personality_manifold import PersonalityManifold

TRAINING_DATA_DIR = PROJECT_ROOT / "training-data"
OUTPUT_FILE = TRAINING_DATA_DIR / "chat_format_combined.jsonl"

# Category -> personality activation hints
CATEGORY_PERSONALITY = {
    "architecture_sessions": {"facet": "wisdom", "intensity": 0.9},
    "tongues_sessions": {"facet": "wisdom", "intensity": 0.8},
    "math_sessions": {"facet": "curiosity", "intensity": 0.8},
    "game_design_sessions": {"facet": "curiosity", "intensity": 0.7},
    "game_sessions": {"facet": "curiosity", "intensity": 0.6},
    "gacha_sessions": {"facet": "wit", "intensity": 0.7},
    "lore_sessions": {"facet": "empathy", "intensity": 0.8},
    "music_sessions": {"facet": "empathy", "intensity": 0.7},
    "sidekick": {"facet": "resolve", "intensity": 0.8},
    "knowledge-base": {"facet": "wisdom", "intensity": 0.9},
    "instruction-tuning": {"facet": "resolve", "intensity": 0.7},
    "evals": {"facet": "vigilance", "intensity": 0.8},
    "hf-digimon-egg": {"facet": "wit", "intensity": 0.6},
}


def detect_category(file_path: Path) -> str:
    """Detect training data category from file path."""
    parts = file_path.relative_to(TRAINING_DATA_DIR).parts
    if len(parts) > 1:
        return parts[0]
    # Root-level files
    name = file_path.stem.lower()
    if "sft_" in name:
        return "instruction-tuning"
    if "notion" in name:
        return "knowledge-base"
    if "merged" in name:
        return "instruction-tuning"
    return "general"


def load_all_jsonl() -> List[Dict[str, Any]]:
    """Load all JSONL files from training-data/."""
    all_records = []
    jsonl_files = sorted(TRAINING_DATA_DIR.rglob("*.jsonl"))

    print(f"Found {len(jsonl_files)} JSONL files")

    for fpath in jsonl_files:
        # Skip the output file itself
        if fpath.name == OUTPUT_FILE.name:
            continue

        category = detect_category(fpath)
        count = 0

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        record["_source_file"] = str(fpath.relative_to(TRAINING_DATA_DIR))
                        record["_category"] = category
                        all_records.append(record)
                        count += 1
                    except json.JSONDecodeError:
                        print(f"  Skipped bad JSON in {fpath.name}:{line_num}")
        except Exception as e:
            print(f"  Error reading {fpath}: {e}")

        if count > 0:
            print(f"  {fpath.relative_to(TRAINING_DATA_DIR)}: {count} records [{category}]")

    return all_records


def record_to_chat(
    record: Dict[str, Any],
    manifold: PersonalityManifold,
) -> Dict[str, Any] | None:
    """Convert a single training record to ChatML conversation format.

    Returns a dict with 'messages' key in OpenAI/Qwen chat format.
    """
    prompt = record.get("prompt", "").strip()
    response = record.get("response", "").strip()

    if not prompt or not response:
        return None

    # Skip very short pairs (noise)
    if len(prompt) < 10 or len(response) < 20:
        return None

    # Activate personality from context
    category = record.get("_category", "general")
    personality_hint = CATEGORY_PERSONALITY.get(category, {"facet": "curiosity", "intensity": 0.5})
    manifold.activate(personality_hint["facet"], personality_hint["intensity"], context=prompt)

    # Also activate from prompt content
    manifold.activate_from_context(prompt)

    # Generate dynamic system prompt
    system_prompt = manifold.generate_system_prompt(context=prompt)

    # Build ChatML messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response},
    ]

    return {
        "messages": messages,
        "category": category,
        "source_file": record.get("_source_file", ""),
        "personality_tag": manifold.get_personality_tag(),
    }


def convert_all(push_to_hf: bool = False) -> None:
    """Main conversion pipeline."""
    print("=" * 60)
    print("SCBE Training Data -> ChatML Converter")
    print("=" * 60)

    # Load all records
    records = load_all_jsonl()
    print(f"\nTotal raw records: {len(records)}")

    # Initialize personality manifold
    manifold = PersonalityManifold()

    # Convert to chat format
    chat_records = []
    skipped = 0

    for record in records:
        chat = record_to_chat(record, manifold)
        if chat is not None:
            chat_records.append(chat)
        else:
            skipped += 1

    print(f"\nConverted: {len(chat_records)} chat pairs")
    print(f"Skipped: {skipped} (empty or too short)")

    # Category breakdown
    from collections import Counter

    cats = Counter(r["category"] for r in chat_records)
    print("\nBy category:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")

    # Personality tag distribution
    tags = Counter(r["personality_tag"] for r in chat_records)
    print(f"\nUnique personality states: {len(tags)}")
    for tag, count in tags.most_common(5):
        print(f"  {tag}: {count}")

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in chat_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\nWrote: {OUTPUT_FILE}")
    print(f"Size: {file_size_mb:.2f} MB")
    print(f"Records: {len(chat_records)}")

    # Also write a messages-only version (what the trainer actually uses)
    messages_file = TRAINING_DATA_DIR / "chat_messages_only.jsonl"
    with open(messages_file, "w", encoding="utf-8") as f:
        for record in chat_records:
            f.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")
    print(f"Wrote messages-only: {messages_file}")

    # Push to HuggingFace
    if push_to_hf:
        push_dataset_to_hf(chat_records)

    # Personality depth report
    report = manifold.get_depth_report()
    print("\nFinal personality manifold state:")
    for name, info in report["facets"].items():
        print(f"  {name}: activation={info['activation']}, bridge={info['bridge_strength']}, depth={info['depth']}")


def push_dataset_to_hf(records: List[Dict[str, Any]]) -> None:
    """Push converted dataset to HuggingFace."""
    try:
        from datasets import Dataset
        from huggingface_hub import HfApi

        # Build dataset from messages
        messages_list = [r["messages"] for r in records]
        categories = [r["category"] for r in records]
        tags = [r["personality_tag"] for r in records]

        ds = Dataset.from_dict(
            {
                "messages": [json.dumps(m) for m in messages_list],
                "category": categories,
                "personality_tag": tags,
            }
        )

        repo_id = "issdandavis/aethermoor-chat-sft"
        print(f"\nPushing to HuggingFace: {repo_id}")
        ds.push_to_hub(repo_id, private=False)
        print(f"Pushed {len(ds)} records to {repo_id}")

    except ImportError:
        print("\nInstall 'datasets' and 'huggingface_hub' to push to HF:")
        print("  pip install datasets huggingface_hub")
    except Exception as e:
        print(f"\nHF push failed: {e}")
        print("You can manually upload chat_format_combined.jsonl to HuggingFace.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert training data to chat format")
    parser.add_argument("--push-to-hf", action="store_true", help="Push to HuggingFace after conversion")
    args = parser.parse_args()

    convert_all(push_to_hf=args.push_to_hf)
