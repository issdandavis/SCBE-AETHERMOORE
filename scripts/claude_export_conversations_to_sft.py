#!/usr/bin/env python3
"""
Convert Claude export conversations into chronologically-tagged SFT records.
=============================================================================
Processes ALL 608+ conversations from a Claude data export zip, extracting
human/assistant message pairs and tagging them with:

  1. Chronological order (epoch_index — monotonic time dimension)
  2. Era classification (lore / crypto / engineering / research / business)
  3. Sacred Tongue affinity scoring (6D tongue vector per record)
  4. Tri-bundle tokenization (162D encoding per byte position)
  5. Content hashing + deduplication
  6. Conversation-level metadata (name, project, message count)

Output: training-data/sft/claude_conversations_sft.jsonl

Usage:
    python scripts/claude_export_conversations_to_sft.py
    python scripts/claude_export_conversations_to_sft.py --zip path/to/export.zip
    python scripts/claude_export_conversations_to_sft.py --min-chars 200 --max-chars 12000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.tri_bundle import (
    TONGUE_WEIGHTS,
    PHI,
    encode_bytes,
)
from src.crypto.trit_curriculum import compute_trit_signal, trit_distribution
from src.crypto.multipath_generator import compute_multipath, multipath_summary

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_ZIP = Path(r"C:\Users\issda\Downloads\data-2026-04-05-23-23-13-batch-0000.zip")
OUTPUT_DIR = ROOT / "training-data" / "sft"
OUTPUT_FILE = OUTPUT_DIR / "claude_conversations_sft.jsonl"
SUMMARY_FILE = ROOT / "artifacts" / "training" / "claude_conversations_sft.summary.json"

# ---------------------------------------------------------------------------
# Era classification keywords
# ---------------------------------------------------------------------------
ERA_KEYWORDS: dict[str, list[str]] = {
    "lore": [
        "avalon", "spiral", "polly", "izack", "aria", "zara", "kael",
        "eldrin", "ravencrest", "world tree", "academy", "magic",
        "chapter", "draft", "everweave", "codex", "fizzle", "senna",
        "clayborn", "aethermoor", "lexicon", "chronicle", "rune",
        "shore to king", "architect of realms", "collaborative",
        "dimensional", "realm", "fantasy", "story", "novel", "lore",
        "narrative", "character", "guild", "quest", "enchant",
    ],
    "crypto": [
        "cipher", "encrypt", "decrypt", "hash", "quantum", "pqc",
        "dilithium", "kyber", "ml-dsa", "ml-kem", "hmac", "aes",
        "post-quantum", "grover", "lattice", "cryptograph", "entropic",
        "harmonic scaling", "hyperbolic", "poincare", "security gate",
        "adversarial", "rwp", "envelope", "signature", "key exchange",
    ],
    "engineering": [
        "pipeline", "docker", "kubernetes", "deploy", "ci/cd", "github",
        "workflow", "api", "endpoint", "server", "uvicorn", "fastapi",
        "express", "gateway", "n8n", "bridge", "webhook", "npm",
        "build", "compile", "typescript", "vitest", "pytest", "test",
        "refactor", "module", "import", "class", "function", "lint",
        "m4mesh", "m5 mesh", "m6 seed", "bootstrap", "aetherbrowse",
    ],
    "research": [
        "hypothesis", "paper", "arxiv", "theorem", "proof", "lemma",
        "manifold", "topology", "lyapunov", "hamiltonian", "barrier",
        "convergence", "eigenvalue", "spectral", "fourier", "fft",
        "quantization", "embedding", "attention", "transformer",
        "neural", "training data", "sft", "fine-tune", "model",
        "phi-weighted", "sacred tongue", "tri-bundle", "dark energy",
        "mirror problem", "phase tunnel", "mirage", "ferrofluid",
    ],
    "business": [
        "revenue", "customer", "pricing", "subscription", "saas",
        "monetiz", "sell", "product", "launch pack", "enterprise",
        "sam.gov", "darpa", "contract", "proposal", "invoice",
        "marketing", "social media", "growth", "merch", "ko-fi",
        "business", "startup", "pitch", "investor",
    ],
}

# Tongue affinity keywords — which tongues light up for which content
TONGUE_KEYWORDS: dict[str, list[str]] = {
    "ko": [  # Kor'aelin — intent/flow/action
        "action", "flow", "verb", "move", "run", "build", "create",
        "do", "make", "execute", "deploy", "launch", "start", "go",
        "quest", "journey", "adventure", "battle", "fight", "sprint",
    ],
    "av": [  # Avali — wisdom/transport/ancient
        "wisdom", "ancient", "sacred", "divine", "truth", "knowledge",
        "philosophy", "spiritual", "soul", "prophecy", "oracle",
        "scripture", "genesis", "creation", "origin", "elder",
    ],
    "ru": [  # Runethic — witness/governance/law
        "governance", "rule", "law", "policy", "audit", "compliance",
        "witness", "verify", "validate", "enforce", "judge", "court",
        "protocol", "standard", "regulation", "authority", "oath",
    ],
    "ca": [  # Cassisivadan — compute/analysis/logic
        "compute", "calculate", "analyze", "algorithm", "function",
        "formula", "equation", "math", "logic", "proof", "theorem",
        "graph", "matrix", "vector", "tensor", "dimension", "metric",
    ],
    "um": [  # Umbroth — shadow/security/hidden
        "shadow", "dark", "void", "null", "hidden", "secret",
        "encrypt", "cipher", "mask", "stealth", "cloak", "veil",
        "security", "threat", "adversarial", "attack", "defense",
    ],
    "dr": [  # Draumric — structure/forge/rigid
        "structure", "forge", "build", "architect", "framework",
        "scaffold", "skeleton", "foundation", "pillar", "wall",
        "layer", "stack", "pipeline", "schema", "blueprint", "spec",
    ],
}

# Noise filters — skip these conversations
NOISE_PATTERNS = [
    re.compile(pat, re.IGNORECASE)
    for pat in (
        r"^$",  # untitled empties
        r"^skip to content",
        r"^a full log",
        r"^stfud$",
        r"^syffj$",
        r"^louhjkl$",
        r"^dhit$",
        r"^drft$",
        r"^mokols$",
        r"^pl$",
    )
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Claude export conversations to chronologically-tagged SFT"
    )
    parser.add_argument("--zip", default=str(DEFAULT_ZIP), help="Export zip path")
    parser.add_argument("--out", default=str(OUTPUT_FILE), help="Output JSONL path")
    parser.add_argument("--summary", default=str(SUMMARY_FILE), help="Summary JSON path")
    parser.add_argument("--min-chars", type=int, default=100, help="Min message chars to keep")
    parser.add_argument("--max-chars", type=int, default=15000, help="Max message chars (truncate)")
    parser.add_argument("--min-pair-chars", type=int, default=200, help="Min combined pair chars")
    return parser.parse_args()


def extract_message_text(msg: dict[str, Any]) -> str:
    """Extract text from a Claude export message (handles both text and content fields)."""
    # Try top-level 'text' first (assistant messages usually have this)
    text = msg.get("text", "")
    if text and len(str(text).strip()) > 10:
        return str(text).strip()

    # Fall back to content blocks
    content = msg.get("content", [])
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                block_text = block.get("text", "")
                if block_text:
                    parts.append(str(block_text))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()

    return ""


def is_noise_conversation(name: str, messages: list) -> bool:
    """Filter out garbage conversations."""
    if len(messages) < 2:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(name or ""):
            return True
    return False


def classify_era(text: str) -> str:
    """Classify text into an era based on keyword density."""
    sample = text.lower()
    scores: dict[str, int] = {}
    for era, keywords in ERA_KEYWORDS.items():
        scores[era] = sum(1 for kw in keywords if kw in sample)
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "general"
    return best


def compute_tongue_affinity(text: str) -> dict[str, float]:
    """Compute 6D tongue affinity vector from text content."""
    sample = text.lower()
    raw: dict[str, int] = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        raw[tongue] = sum(1 for kw in keywords if kw in sample)

    total = sum(raw.values()) or 1
    # Normalize to [0, 1] and apply phi weighting
    affinity = {}
    for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
        base = raw.get(tongue, 0) / total
        affinity[tongue] = round(base * TONGUE_WEIGHTS[tongue], 4)

    return affinity


def primary_tongue(affinity: dict[str, float]) -> str:
    """Get the dominant tongue from an affinity vector."""
    if not any(v > 0 for v in affinity.values()):
        return "ko"  # default to Kor'aelin (intent/flow)
    return max(affinity, key=lambda k: affinity[k])


def tri_bundle_summary(text: str) -> dict[str, Any]:
    """Compute tri-bundle encoding summary stats for text."""
    text_bytes = text.encode("utf-8")
    if not text_bytes:
        return {"byte_count": 0, "dimensions": 0, "mean_sync": 0.0}

    # Sample first 512 bytes for performance (full encoding on huge texts is slow)
    sample = text_bytes[:512]
    clusters = encode_bytes(sample, tongue_code="ko")
    if len(clusters) < 2:
        return {
            "byte_count": len(text_bytes),
            "dimensions": len(text_bytes) * 162,
            "mean_sync": 0.0,
        }

    # Compute mean synchronization across clusters
    syncs = []
    for cluster in clusters:
        s = cluster.synchronization_score()
        syncs.append(s)
    mean_sync = sum(syncs) / len(syncs) if syncs else 0.0

    return {
        "byte_count": len(text_bytes),
        "dimensions": len(text_bytes) * 162,
        "mean_sync": round(mean_sync, 6),
    }


def content_hash(text: str) -> str:
    """SHA-256 content hash for deduplication."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp from export."""
    if not ts:
        return datetime(2025, 1, 1, tzinfo=timezone.utc)
    # Handle various formats
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return datetime(2025, 1, 1, tzinfo=timezone.utc)


def extract_pairs(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract human/assistant message pairs from a conversation."""
    messages = conversation.get("chat_messages", [])
    convo_name = conversation.get("name", "") or ""
    convo_uuid = conversation.get("uuid", "")
    convo_created = conversation.get("created_at", "")

    pairs = []
    i = 0
    while i < len(messages) - 1:
        msg_h = messages[i]
        msg_a = messages[i + 1]

        if msg_h.get("sender") == "human" and msg_a.get("sender") == "assistant":
            human_text = extract_message_text(msg_h)
            assistant_text = extract_message_text(msg_a)
            msg_timestamp = msg_h.get("created_at", "") or msg_a.get("created_at", "")

            pairs.append({
                "human": human_text,
                "assistant": assistant_text,
                "timestamp": msg_timestamp,
                "conversation_name": convo_name,
                "conversation_uuid": convo_uuid,
                "conversation_created": convo_created,
                "msg_index": i,
            })
            i += 2
        else:
            i += 1

    return pairs


def make_record(
    pair: dict[str, Any],
    epoch_index: int,
    era: str,
    tongue_affinity: dict[str, float],
    tri_summary: dict[str, Any],
    trit_dict: dict[str, Any],
    pair_hash: str,
) -> dict[str, Any]:
    """Build one SFT training record with full SCBE tagging."""
    pt = primary_tongue(tongue_affinity)
    ts = parse_timestamp(pair["timestamp"])

    return {
        "messages": [
            {"role": "user", "content": pair["human"]},
            {"role": "assistant", "content": pair["assistant"]},
        ],
        "metadata": {
            "source": "claude_export_conversations",
            "record_type": "conversation_pair",
            "content_hash": pair_hash,
            "timestamp": pair["timestamp"],
            "epoch_index": epoch_index,
            "epoch_date": ts.strftime("%Y-%m-%d"),
            "epoch_month": ts.strftime("%Y-%m"),
            "epoch_day_of_year": ts.timetuple().tm_yday,
            "epoch_unix": int(ts.timestamp()),
            "era": era,
            "conversation_name": pair["conversation_name"],
            "conversation_uuid": pair["conversation_uuid"],
            "msg_index": pair["msg_index"],
            "tongue_affinity": tongue_affinity,
            "primary_tongue": pt,
            "phi_weight": TONGUE_WEIGHTS[pt],
            "tri_bundle": tri_summary,
            "trit_signal": trit_dict,
            "char_count_human": len(pair["human"]),
            "char_count_assistant": len(pair["assistant"]),
        },
    }


def main() -> int:
    args = parse_args()
    zip_path = Path(args.zip).expanduser()
    out_path = Path(args.out).expanduser()
    summary_path = Path(args.summary).expanduser()

    print("=" * 70)
    print("Claude Export Conversations -> Chronological SFT Pipeline")
    print("=" * 70)
    print(f"Source: {zip_path}")
    print(f"Output: {out_path}")
    print()

    # Load export
    print("Loading export...")
    with zipfile.ZipFile(zip_path) as zf:
        convos = json.loads(zf.read("conversations.json"))
    print(f"  Loaded {len(convos)} conversations")

    # Extract all pairs
    print("Extracting message pairs...")
    all_pairs: list[dict[str, Any]] = []
    skipped_noise = 0
    skipped_short = 0

    for convo in convos:
        name = convo.get("name", "") or ""
        messages = convo.get("chat_messages", [])

        if is_noise_conversation(name, messages):
            skipped_noise += 1
            continue

        pairs = extract_pairs(convo)
        for pair in pairs:
            human_len = len(pair["human"])
            assistant_len = len(pair["assistant"])

            if human_len < 10 or assistant_len < args.min_chars:
                skipped_short += 1
                continue
            if human_len + assistant_len < args.min_pair_chars:
                skipped_short += 1
                continue

            # Truncate overly long messages
            if len(pair["human"]) > args.max_chars:
                pair["human"] = pair["human"][:args.max_chars] + "\n[truncated]"
            if len(pair["assistant"]) > args.max_chars:
                pair["assistant"] = pair["assistant"][:args.max_chars] + "\n[truncated]"

            all_pairs.append(pair)

    print(f"  Extracted {len(all_pairs)} valid pairs")
    print(f"  Skipped {skipped_noise} noise conversations")
    print(f"  Skipped {skipped_short} short/empty messages")

    # Sort chronologically (Dimension 1: time)
    print("Sorting chronologically...")
    all_pairs.sort(key=lambda p: parse_timestamp(p["timestamp"]))

    # Deduplicate
    print("Deduplicating...")
    seen_hashes: set[str] = set()
    unique_pairs: list[tuple[dict[str, Any], str]] = []
    dupes = 0
    for pair in all_pairs:
        combined = pair["human"] + "\n---\n" + pair["assistant"]
        h = content_hash(combined)
        if h in seen_hashes:
            dupes += 1
            continue
        seen_hashes.add(h)
        unique_pairs.append((pair, h))

    print(f"  {len(unique_pairs)} unique pairs ({dupes} duplicates removed)")

    # Build records with full tagging
    print("Tagging records (era + tongue + tri-bundle + trit curriculum)...")
    records: list[dict[str, Any]] = []
    era_counts: dict[str, int] = {}
    tongue_counts: dict[str, int] = {}
    trit_signals_all = []

    for epoch_index, (pair, pair_hash) in enumerate(unique_pairs):
        combined = pair["human"] + "\n" + pair["assistant"]

        # Era classification
        era = classify_era(combined)
        era_counts[era] = era_counts.get(era, 0) + 1

        # Tongue affinity
        affinity = compute_tongue_affinity(combined)
        pt = primary_tongue(affinity)
        tongue_counts[pt] = tongue_counts.get(pt, 0) + 1

        # Tri-bundle summary (sample encoding)
        tri_summary = tri_bundle_summary(combined)

        # 3-trit curriculum signal (27-state training tag)
        # Use first 256 chars for trit computation (performance)
        trit_text = combined[:256] if len(combined) > 256 else combined
        trit_sig = compute_trit_signal(trit_text)
        trit_dict = trit_sig.to_dict()
        trit_signals_all.append(trit_sig)

        # Multi-path analysis (Monty Hall weighting)
        mp = compute_multipath(trit_sig)
        trit_dict["multipath"] = mp.to_dict()

        record = make_record(pair, epoch_index, era, affinity, tri_summary, trit_dict, pair_hash)
        records.append(record)

        if (epoch_index + 1) % 500 == 0:
            print(f"  [{epoch_index + 1}/{len(unique_pairs)}] processed...")

    # Write output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Compute time span
    if records:
        first_ts = records[0]["metadata"]["epoch_date"]
        last_ts = records[-1]["metadata"]["epoch_date"]
        time_span = f"{first_ts} -> {last_ts}"
    else:
        time_span = "none"

    # Trit curriculum distribution
    trit_dist = trit_distribution(trit_signals_all) if trit_signals_all else {}

    # Multi-path summary (Monty Hall)
    all_multipaths = [compute_multipath(t) for t in trit_signals_all]
    mp_summary = multipath_summary(all_multipaths)

    # Summary
    summary = {
        "zip_path": str(zip_path),
        "output_path": str(out_path),
        "total_conversations": len(convos),
        "skipped_noise": skipped_noise,
        "skipped_short": skipped_short,
        "total_pairs_extracted": len(all_pairs),
        "duplicates_removed": dupes,
        "records_written": len(records),
        "time_span": time_span,
        "era_distribution": dict(sorted(era_counts.items(), key=lambda x: -x[1])),
        "tongue_distribution": dict(sorted(tongue_counts.items(), key=lambda x: -x[1])),
        "trit_curriculum_distribution": trit_dist,
        "trit_states_used": len(trit_dist),
        "multipath_analysis": mp_summary,
        "total_tri_bundle_dimensions": sum(
            r["metadata"]["tri_bundle"]["dimensions"] for r in records
        ),
        "mean_sync_overall": round(
            sum(r["metadata"]["tri_bundle"]["mean_sync"] for r in records) / len(records), 6
        ) if records else 0.0,
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("=" * 70)
    print(f"Records written: {len(records)}")
    print(f"Output: {out_path}")
    print(f"Time span: {time_span}")
    print()
    print("Era distribution:")
    for era, count in sorted(era_counts.items(), key=lambda x: -x[1]):
        pct = count / len(records) * 100
        print(f"  {era:>15}: {count:>5} ({pct:.1f}%)")
    print()
    print("Primary tongue distribution:")
    for tongue, count in sorted(tongue_counts.items(), key=lambda x: -x[1]):
        pct = count / len(records) * 100
        weight = TONGUE_WEIGHTS[tongue]
        print(f"  {tongue:>4} (phi={weight:.3f}): {count:>5} ({pct:.1f}%)")
    print()
    print(f"Total tri-bundle dimensions: {summary['total_tri_bundle_dimensions']:,}")
    print(f"Mean synchronization: {summary['mean_sync_overall']:.6f}")
    print()
    print(f"Trit curriculum states used: {summary['trit_states_used']}/27")
    print("Trit curriculum distribution:")
    for label, count in list(trit_dist.items())[:15]:
        pct = count / len(records) * 100
        print(f"  {label:>20}: {count:>5} ({pct:.1f}%)")
    if len(trit_dist) > 15:
        print(f"  ... and {len(trit_dist) - 15} more states")
    print()
    print("Multi-path / Monty Hall analysis:")
    print(f"  Polymorphic records: {mp_summary['multipath_count']}/{mp_summary['count']} "
          f"({mp_summary['multipath_pct']}%)")
    print(f"  Total reachable paths: {mp_summary['total_reachable_paths']}")
    print(f"  Unique reachable states: {mp_summary['unique_reachable_states']}/27")
    mh = mp_summary["monty_hall"]
    print(f"  Mean Monty Hall advantage: {mh['mean_advantage']:.1%}")
    print(f"  Mean mirror weight: {mh['mean_mirror_weight']:.2f}x")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
