#!/usr/bin/env python3
"""
ingest_open_datasets.py - Download and reformat leading open agentic coding
datasets into the SCBE training schema.

Supported datasets:
  - R2E-Gym SFT trajectories (HuggingFace)
  - CodeActInstruct (HuggingFace)
  - SWE-smith (HuggingFace)
  - AgentInstruct (HuggingFace)

Each dataset is normalized to SCBE schema v3.0.0 with tongue weights,
layers, and difficulty annotations inferred from content.

Usage:
    python scripts/training/ingest_open_datasets.py --dataset r2e-gym
    python scripts/training/ingest_open_datasets.py --dataset codeactinstruct
    python scripts/training/ingest_open_datasets.py --all

Requires: datasets, huggingface_hub
    pip install datasets huggingface_hub

Author: Issac Davis
Date: 2026-04-23
"""

import argparse
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "training-data" / "agentic_coding"

# ---------------------------------------------------------------------------
#  Dataset configurations
# ---------------------------------------------------------------------------

DATASET_CONFIGS = {
    "r2e-gym": {
        "repo": "r2e-gym/r2e-gym-trajectories",
        "subset": None,
        "split": "train",
        "format": "chat",
        "category": "agentic-repository-task",
        "tongues": ["KO", "CA", "DR"],
        "layers": [1, 3, 7, 12, 14],
        "description": "Real repository environments with synthetic tasks from commits",
    },
    "codeactinstruct": {
        "repo": "xingyaoww/codeactinstruct",
        "subset": None,
        "split": "train",
        "format": "chat",
        "category": "agentic-tool-use",
        "tongues": ["KO", "AV", "CA"],
        "layers": [1, 3, 5, 10, 14],
        "description": "Synthetic code + tool use with execution feedback",
    },
    "swe-smith": {
        "repo": "SWE-bench/SWE-smith",
        "subset": None,
        "split": "train",
        "format": "trajectory",
        "category": "agentic-bug-fix",
        "tongues": ["RU", "CA", "UM"],
        "layers": [1, 3, 7, 9, 12, 14],
        "description": "Automated bug synthesis from real GitHub repos",
    },
    "agentinstruct": {
        "repo": "THUDM/AgentInstruct",
        "subset": None,
        "split": "train",
        "format": "chat",
        "category": "agentic-general",
        "tongues": ["KO", "AV", "RU", "CA"],
        "layers": [1, 3, 5, 7, 14],
        "description": "Mixed OS/DB/web agent instructions",
    },
}


# ---------------------------------------------------------------------------
#  Format converters
# ---------------------------------------------------------------------------

def infer_difficulty(text: str) -> str:
    """Infer difficulty from task description length and complexity."""
    length = len(text)
    complexity_markers = sum(1 for w in ["multiple", "complex", "refactor", "architecture", "cross-file", "debug", "fix"] if w in text.lower())
    
    if length < 200 and complexity_markers == 0:
        return "easy"
    elif length > 800 or complexity_markers >= 3:
        return "hard"
    return "medium"


def infer_tongues(text: str) -> List[str]:
    """Infer dominant Sacred Tongues from task content."""
    text_lower = text.lower()
    scores = {
        "KO": len([w for w in ["implement", "create", "add", "build", "function", "call", "api"] if w in text_lower]),
        "AV": len([w for w in ["explain", "document", "describe", "understand", "knowledge", "read"] if w in text_lower]),
        "RU": len([w for w in ["test", "verify", "validate", "check", "governance", "audit", "security"] if w in text_lower]),
        "CA": len([w for w in ["compute", "calculate", "logic", "algorithm", "math", "performance"] if w in text_lower]),
        "UM": len([w for w in ["secure", "protect", "encrypt", "defense", "vulnerability", "exploit"] if w in text_lower]),
        "DR": len([w for w in ["architecture", "structure", "design", "pattern", "refactor", "organize"] if w in text_lower]),
    }
    # Return top 2-3 tongues
    sorted_tongues = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [t for t, s in sorted_tongues[:3] if s > 0] or ["KO"]


def convert_chat_to_scbe(example: Dict, config: Dict, idx: int) -> Optional[Dict]:
    """Convert a chat-format dataset example to SCBE schema."""
    messages = example.get("messages") or example.get("conversations") or example.get("chat")
    if not messages:
        return None
    
    # Extract text for inference
    all_text = " ".join(str(m.get("content", "")) for m in messages)
    
    return {
        "id": f"ag-{config['category'][:3]}-{hashlib.sha1(all_text[:200].encode()).hexdigest()[:8]}-{idx:05d}",
        "category": config["category"],
        "messages": [
            {
                "role": m.get("role", "user"),
                "content": m.get("content", m.get("value", "")),
            }
            for m in messages
        ],
        "metadata": {
            "source": "open_dataset",
            "version": "3.3.0",
            "original_dataset": config["repo"],
            "generator": "ingest_open_datasets.py",
            "tongues": infer_tongues(all_text),
            "layers": config["layers"],
            "difficulty": infer_difficulty(all_text),
            "description": config["description"],
        }
    }


def convert_trajectory_to_scbe(example: Dict, config: Dict, idx: int) -> Optional[Dict]:
    """Convert a trajectory-format dataset example to SCBE schema."""
    trajectory = example.get("trajectory") or example.get("history") or example
    if not trajectory:
        return None
    
    all_text = json.dumps(trajectory)[:500]
    
    return {
        "id": f"ag-{config['category'][:3]}-{hashlib.sha1(all_text.encode()).hexdigest()[:8]}-{idx:05d}",
        "category": config["category"],
        "trajectory": trajectory,
        "metadata": {
            "source": "open_dataset",
            "version": "3.3.0",
            "original_dataset": config["repo"],
            "generator": "ingest_open_datasets.py",
            "tongues": infer_tongues(all_text),
            "layers": config["layers"],
            "difficulty": infer_difficulty(all_text),
            "description": config["description"],
        }
    }


# ---------------------------------------------------------------------------
#  Downloader
# ---------------------------------------------------------------------------

def download_dataset(name: str, config: Dict, max_samples: Optional[int] = None) -> List[Dict]:
    """Download and convert a dataset."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' library not installed. Run: pip install datasets")
        return []
    
    print(f"\nDownloading {name} from {config['repo']}...")
    
    try:
        ds = load_dataset(
            config["repo"],
            config.get("subset"),
            split=config["split"],
            trust_remote_code=True,
        )
    except Exception as e:
        print(f"  FAILED: {e}")
        return []
    
    if max_samples:
        ds = ds.select(range(min(max_samples, len(ds))))
    
    print(f"  Loaded {len(ds)} examples")
    
    converter = convert_chat_to_scbe if config["format"] == "chat" else convert_trajectory_to_scbe
    results = []
    
    for idx, example in enumerate(ds):
        converted = converter(example, config, idx)
        if converted:
            results.append(converted)
    
    print(f"  Converted {len(results)} examples to SCBE schema")
    return results


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest open agentic coding datasets")
    parser.add_argument("--dataset", choices=list(DATASET_CONFIGS.keys()) + ["all"],
                        default="all", help="Dataset to ingest")
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Max samples per dataset")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without downloading")
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    datasets_to_fetch = list(DATASET_CONFIGS.keys()) if args.dataset == "all" else [args.dataset]
    
    if args.dry_run:
        print("DRY RUN — Would download:")
        for name in datasets_to_fetch:
            cfg = DATASET_CONFIGS[name]
            print(f"  {name}: {cfg['repo']} → {args.output_dir / f'{name}_scbe.jsonl'}")
        return
    
    total = 0
    for name in datasets_to_fetch:
        cfg = DATASET_CONFIGS[name]
        examples = download_dataset(name, cfg, args.max_samples)
        
        if examples:
            output_file = args.output_dir / f"{name}_scbe.jsonl"
            with open(output_file, 'w', encoding='utf-8') as f:
                for ex in examples:
                    f.write(json.dumps(ex, ensure_ascii=False) + '\n')
            print(f"  Saved to {output_file}")
            total += len(examples)
    
    print(f"\nTotal ingested: {total} examples")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
