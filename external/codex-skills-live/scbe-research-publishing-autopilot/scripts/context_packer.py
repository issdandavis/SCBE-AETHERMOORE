#!/usr/bin/env python3
"""
Build a "context-of-self" artifact from prior posts and dataset manifests.

This gives downstream drafting a grounded voice:
- what already worked
- what offers convert
- what datasets are available as source truth
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create self context pack from prior posts and datasets.")
    parser.add_argument("--posts-history", required=True, help="JSONL file with prior post performance")
    parser.add_argument("--dataset-manifest", required=True, help="JSON manifest of available datasets")
    parser.add_argument("--out", required=True, help="Output path for self_context_pack.json")
    parser.add_argument("--top-n", type=int, default=20, help="Top posts to keep")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def score_post(row: Dict[str, Any]) -> float:
    impressions = float(row.get("impressions", 0) or 0)
    clicks = float(row.get("clicks", 0) or 0)
    conversions = float(row.get("conversions", row.get("leads", 0)) or 0)
    saves = float(row.get("saves", 0) or 0)
    # Weighted for business impact first, then attention quality.
    return conversions * 100.0 + clicks * 2.0 + saves * 1.5 + (impressions * 0.01)


def normalize_datasets(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("datasets", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def extract_terms(text: str) -> List[str]:
    words = [w.strip(".,:;!?()[]{}\"'").lower() for w in text.split()]
    words = [w for w in words if len(w) >= 5 and w.isascii()]
    # Keep deterministic order but deduplicate.
    seen = set()
    out: List[str] = []
    for w in words:
        if w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def main() -> int:
    args = parse_args()
    posts = read_jsonl(Path(args.posts_history))
    datasets = normalize_datasets(read_json(Path(args.dataset_manifest)))

    for row in posts:
        row["_score"] = score_post(row)

    ranked_posts = sorted(posts, key=lambda r: float(r.get("_score", 0.0)), reverse=True)[: max(1, args.top_n)]

    top_terms: Dict[str, int] = {}
    for row in ranked_posts:
        text = str(row.get("text", row.get("body", "")))
        for term in extract_terms(text):
            top_terms[term] = top_terms.get(term, 0) + 1

    term_rank = sorted(top_terms.items(), key=lambda kv: (-kv[1], kv[0]))[:50]
    canonical_vocab = [t for t, _ in term_rank]

    pack = {
        "summary": {
            "posts_seen": len(posts),
            "top_posts_kept": len(ranked_posts),
            "datasets_seen": len(datasets),
        },
        "top_posts": [
            {
                "post_id": r.get("post_id", ""),
                "channel": r.get("channel", ""),
                "score": r.get("_score", 0.0),
                "text": r.get("text", r.get("body", "")),
                "cta": r.get("cta", ""),
                "offer_path": r.get("offer_path", ""),
            }
            for r in ranked_posts
        ],
        "datasets": [
            {
                "name": d.get("name", ""),
                "path": d.get("path", ""),
                "topic": d.get("topic", ""),
                "notes": d.get("notes", ""),
            }
            for d in datasets
        ],
        "canonical_vocab": canonical_vocab,
        "policy": {
            "context_of_self_is_king": True,
            "use_only_verified_dataset_claims": True,
            "no_unmapped_marketing_claims": True,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    print(f"Saved context pack: {out_path}")
    print(
        f"posts={pack['summary']['posts_seen']} top={pack['summary']['top_posts_kept']} datasets={pack['summary']['datasets_seen']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
