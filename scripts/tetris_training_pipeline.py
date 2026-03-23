"""
Tetris Training Pipeline
=========================

Full pre-embedding -> embedding -> training data pipeline.

Fuses:
  1. Spin Conversation Generator (pivot_knowledge.py) — generates diverse NPC dialogues
  2. Tetris Embedder — sacred rotation + phi expansion for optimal packing
  3. Context Grid — octree + memory + RAG storage
  4. Sphere Grid Notes — 121 Obsidian notes as base curriculum
  5. Existing SFT data — merged_sft.jsonl (10,978 pairs)
  6. HF Push — upload Tetris-optimized training data to HuggingFace

Run:
  python scripts/tetris_training_pipeline.py
  python scripts/tetris_training_pipeline.py --push-hf
  python scripts/tetris_training_pipeline.py --benchmark-only
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from src.kernel.tetris_embedder import TetrisEmbedder, augment_text, TONGUE_KEYS
from src.kernel.context_grid import FederatedContextGrid, load_obsidian_vault


def load_hf_token() -> str:
    env_path = ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "HF_TOKEN=" in line or "HUGGINGFACE_TOKEN=" in line:
                token = line.split("=", 1)[1].strip().strip('"')
                if token:
                    return token
    return os.environ.get("HF_TOKEN", "")


def generate_spin_conversations(n_sessions: int = 5) -> list[dict]:
    """
    Generate spin conversations using the radial matrix topic system.

    Traverses 35 topics across 3 concentric rings with Sacred Tongue tagging.
    """
    import random

    TOPICS = {
        "CORE": [
            ("philosophy", "KO"), ("mathematics", "CA"), ("physics", "CA"),
            ("psychology", "RU"), ("history", "DR"), ("culture", "AV"),
        ],
        "INNER": [
            ("programming", "CA"), ("astronomy", "RU"), ("chemistry", "CA"),
            ("music", "AV"), ("cooking", "DR"), ("economics", "KO"),
            ("art", "AV"), ("politics", "KO"), ("technology", "CA"),
            ("emotions", "RU"), ("creativity", "AV"), ("time", "UM"),
        ],
        "OUTER": [
            ("algorithms", "CA"), ("databases", "DR"), ("web_development", "AV"),
            ("AI", "CA"), ("cybersecurity", "UM"), ("nutrition", "DR"),
            ("food_science", "RU"), ("dreams", "RU"), ("linguistics", "AV"),
            ("game_theory", "KO"), ("cryptography", "UM"), ("ecology", "DR"),
        ],
    }
    RING_ORDER = ["CORE", "INNER", "OUTER"]
    MOVES = ["LATERAL", "OUTWARD", "INWARD"]
    NPC_TEMPLATES = {
        "polly": ("KO", "You are Polly, a sarcastic raven familiar who guards the Archive."),
        "eldrin": ("DR", "You are Eldrin Ashveil, a 600-year-old elven scholar of structure."),
        "aria": ("AV", "You are Aria, a spirit navigator who maps the space between tongues."),
        "kael": ("CA", "You are Kael Nightwhisper, a rival mage obsessed with computation."),
        "zara": ("UM", "You are Zara, a shadow agent who speaks in encrypted riddles."),
        "clay": ("RU", "You are Clay, an ancient golem who reasons through entropy."),
    }

    pairs = []
    rng = random.Random(42 + n_sessions)

    for session in range(n_sessions):
        npc_name = rng.choice(list(NPC_TEMPLATES.keys()))
        npc_tongue, npc_prompt = NPC_TEMPLATES[npc_name]
        ring_idx = rng.randint(0, 2)
        ring = RING_ORDER[ring_idx]
        topic, topic_tongue = rng.choice(TOPICS[ring])
        n_pivots = rng.randint(5, 8)
        tongue_seq = [topic_tongue]

        for step in range(n_pivots):
            response = (
                f"In the realm of {topic}, we find deep connections to the "
                f"{npc_tongue} domain. As a keeper of {ring.lower()} knowledge, "
                f"I see how {topic} interweaves with Sacred Tongue {topic_tongue}. "
                f"The {['fundamental', 'intermediate', 'advanced', 'masterful'][min(step, 3)]} "
                f"understanding requires traversing the sphere grid."
            )
            move = rng.choice(MOVES)
            if move == "OUTWARD" and ring_idx < 2:
                ring_idx += 1
            elif move == "INWARD" and ring_idx > 0:
                ring_idx -= 1
            else:
                move = "LATERAL"
            ring = RING_ORDER[ring_idx]
            prev_topic = topic
            topic, topic_tongue = rng.choice(TOPICS[ring])
            tongue_seq.append(topic_tongue)

            pairs.append({
                "instruction": (
                    f"{npc_prompt} The player asks about {topic} in the "
                    f"context of {prev_topic}. Respond in character, connecting "
                    f"these topics through the {topic_tongue} Sacred Tongue domain."
                ),
                "response": response,
                "metadata": {
                    "npc": npc_name, "tongue": topic_tongue,
                    "type": "spin_conversation", "ring": ring,
                    "move": move, "pivot_depth": step, "session": session,
                },
                "encoding_tongue": topic_tongue,
                "timestamp": time.time(),
            })
    return pairs


def load_existing_sft(max_pairs: int = 500) -> list[dict]:
    """Load a sample of existing SFT data for embedding comparison."""
    merged = ROOT / "training-data" / "merged_sft.jsonl"
    pairs = []
    if merged.exists():
        with open(merged, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_pairs:
                    break
                try:
                    rec = json.loads(line)
                    pairs.append(rec)
                except json.JSONDecodeError:
                    continue
    return pairs


def infer_tongue(record: dict) -> str:
    """Infer Sacred Tongue from SFT record metadata or content."""
    # Check metadata
    meta = record.get("metadata", {})
    if isinstance(meta, str):
        meta = {}
    tongue = meta.get("tongue", meta.get("encoding_tongue", ""))
    if tongue in TONGUE_KEYS:
        return tongue

    # Check top-level
    tongue = record.get("encoding_tongue", "")
    if tongue in TONGUE_KEYS:
        return tongue

    # Infer from content keywords
    text = (record.get("instruction", "") + " " + record.get("prompt", "") +
            " " + record.get("response", "")).lower()

    tongue_keywords = {
        "KO": ["command", "orchestrat", "dispatch", "fleet", "coordinat"],
        "AV": ["transport", "navigat", "brows", "search", "web"],
        "RU": ["research", "hypothes", "entropy", "chaos", "explor"],
        "CA": ["code", "compute", "train", "deploy", "test", "implement"],
        "UM": ["secur", "govern", "audit", "threat", "scan", "seal"],
        "DR": ["structur", "architect", "document", "debug", "heal"],
    }

    best_tongue = "KO"
    best_count = 0
    for t, keywords in tongue_keywords.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_tongue = t

    return best_tongue


def benchmark_embeddings(tetris: TetrisEmbedder, texts: list[str],
                         tongues: list[str], tiers: list[int]) -> dict:
    """Compute embedding quality metrics."""
    results = tetris.embed_batch(texts, tongues, tiers)
    embs = np.array([r.rotated_embedding for r in results])

    # Diversity
    cos = embs @ embs.T
    np.fill_diagonal(cos, 0)
    n = len(embs)
    avg_cos = cos.sum() / (n * (n - 1)) if n > 1 else 0

    # Tongue separation
    separations = {}
    for t in TONGUE_KEYS:
        mask = [i for i, x in enumerate(tongues) if x == t]
        other = [i for i, x in enumerate(tongues) if x != t]
        if len(mask) > 1 and len(other) > 0:
            te = embs[mask]
            tc = te @ te.T
            np.fill_diagonal(tc, 0)
            intra = tc.sum() / (len(mask) * (len(mask) - 1))
            inter = np.mean(embs[mask] @ embs[other].T)
            separations[t] = float(intra - inter)

    # Tongue coords range
    tcoords = np.array([r.tongue_coords for r in results])
    coord_spread = float(tcoords.max() - tcoords.min())

    # Spatial buckets
    bucket_size = 0.25
    buckets = set()
    for r in results:
        key = tuple(int((x + 1.0) / bucket_size) for x in r.spatial_coords[:3])
        buckets.add(key)

    return {
        "n_docs": n,
        "avg_cosine": float(avg_cos),
        "diversity_score": max(0, min(100, (1 - avg_cos / 0.5) * 100)),
        "tongue_separation": separations,
        "avg_separation": float(np.mean(list(separations.values()))) if separations else 0,
        "coord_spread": coord_spread,
        "n_buckets": len(buckets),
    }


def export_tetris_sft(records: list[dict], tetris: TetrisEmbedder,
                      output_path: Path) -> int:
    """
    Export SFT records with Tetris embeddings as enriched JSONL.

    Each record gets:
      - tongue (inferred or explicit)
      - augmented_text (tongue-prefixed)
      - tongue_coords (6D expanded)
      - spatial_coords (3D expanded)
      - embedding_hash (for dedup)
    """
    texts = []
    tongues = []
    tiers = []

    for rec in records:
        text = rec.get("instruction", rec.get("prompt", "")) + " " + rec.get("response", "")
        tongue = infer_tongue(rec)
        tier = 1  # Default; could parse from metadata

        texts.append(text[:500])
        tongues.append(tongue)
        tiers.append(tier)

    # Batch embed with Tetris pipeline
    embeddings = tetris.embed_batch(texts, tongues, tiers)

    # Write enriched JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for rec, emb in zip(records, embeddings):
            enriched = {
                **rec,
                "tongue": emb.tongue,
                "tier": emb.tier,
                "tongue_coords": emb.tongue_coords.tolist(),
                "spatial_coords": emb.spatial_coords.tolist(),
                "embedding_hash": hashlib.md5(
                    emb.rotated_embedding.tobytes()
                ).hexdigest()[:16],
            }
            f.write(json.dumps(enriched, ensure_ascii=False, default=str) + "\n")
            written += 1

    return written


def push_to_hf(file_path: Path, repo_id: str, hf_token: str) -> bool:
    """Push enriched JSONL to HuggingFace."""
    try:
        from huggingface_hub import upload_file
        upload_file(
            path_or_fileobj=str(file_path),
            path_in_repo=f"data/{file_path.name}",
            repo_id=repo_id,
            repo_type="dataset",
            token=hf_token,
        )
        return True
    except Exception as e:
        print(f"  HF push error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Tetris Training Pipeline")
    parser.add_argument("--push-hf", action="store_true", help="Push to HuggingFace")
    parser.add_argument("--benchmark-only", action="store_true", help="Only run benchmarks")
    parser.add_argument("--spin-sessions", type=int, default=5, help="Spin conversation sessions")
    parser.add_argument("--sft-sample", type=int, default=200, help="SFT pairs to sample")
    args = parser.parse_args()

    print("=" * 60)
    print("TETRIS TRAINING PIPELINE")
    print("Sacred Geometry Pre-Embedding -> Full Training")
    print("=" * 60)

    hf_token = load_hf_token()
    tetris = TetrisEmbedder("all-MiniLM-L6-v2")

    # ================================================================
    # PHASE 1: Generate Spin Conversations
    # ================================================================
    print("\nPHASE 1: Generating spin conversations...")
    t0 = time.time()
    spin_pairs = generate_spin_conversations(args.spin_sessions)
    spin_time = time.time() - t0
    print(f"  Generated {len(spin_pairs)} SFT pairs in {spin_time:.1f}s")

    tongue_dist = {}
    for p in spin_pairs:
        t = p.get("encoding_tongue", p.get("metadata", {}).get("tongue", "KO"))
        tongue_dist[t] = tongue_dist.get(t, 0) + 1
    print(f"  Tongue distribution: {tongue_dist}")

    # ================================================================
    # PHASE 2: Load Existing Data
    # ================================================================
    print("\nPHASE 2: Loading existing training data...")
    existing_sft = load_existing_sft(args.sft_sample)
    print(f"  Loaded {len(existing_sft)} existing SFT pairs")

    sphere_docs = load_obsidian_vault(ROOT / "notes" / "sphere-grid")
    sphere_sft = [{
        "instruction": f"Explain the {d['title']} concept from the SCBE sphere grid.",
        "response": d["content"][:600],
        "metadata": {"tongue": d["tongue"], "tier": d.get("tier", 1), "source": "sphere-grid"},
    } for d in sphere_docs]
    print(f"  Loaded {len(sphere_sft)} sphere grid curriculum notes")

    # ================================================================
    # PHASE 3: Combine + Deduplicate
    # ================================================================
    print("\nPHASE 3: Combining and deduplicating...")
    all_records = spin_pairs + sphere_sft + existing_sft

    # Deduplicate by content hash
    seen = set()
    deduped = []
    for rec in all_records:
        key = hashlib.md5(
            (rec.get("instruction", rec.get("prompt", "")) +
             rec.get("response", "")).encode()
        ).hexdigest()
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    print(f"  Combined: {len(all_records)} -> {len(deduped)} after dedup")

    # ================================================================
    # PHASE 4: Tetris Embedding + Benchmark
    # ================================================================
    print("\nPHASE 4: Tetris embedding + benchmark...")

    texts = [(r.get("instruction", r.get("prompt", "")) + " " +
              r.get("response", ""))[:500] for r in deduped]
    tongues = [infer_tongue(r) for r in deduped]
    tiers = [r.get("metadata", {}).get("tier", 1) if isinstance(r.get("metadata"), dict) else 1
             for r in deduped]

    t0 = time.time()
    metrics = benchmark_embeddings(tetris, texts, tongues, tiers)
    embed_time = time.time() - t0

    print(f"  Embedded {metrics['n_docs']} docs in {embed_time:.1f}s")
    print(f"  Diversity:     {metrics['diversity_score']:.0f}/100 (cosine={metrics['avg_cosine']:.4f})")
    print(f"  Avg separation: {metrics['avg_separation']:.4f}")
    print(f"  Coord spread:  {metrics['coord_spread']:.4f}")
    print(f"  Octree buckets: {metrics['n_buckets']}")
    print(f"  Tongue separation:")
    for t, sep in sorted(metrics["tongue_separation"].items()):
        grade = "GOOD" if sep > 0.3 else "OK" if sep > 0.1 else "WEAK"
        print(f"    {t}: {sep:+.4f} [{grade}]")

    if args.benchmark_only:
        print("\n  --benchmark-only: stopping here")
        return

    # ================================================================
    # PHASE 5: Export Enriched JSONL
    # ================================================================
    print("\nPHASE 5: Exporting Tetris-enriched JSONL...")
    output_path = ROOT / "training-data" / "tetris_enriched_sft.jsonl"
    t0 = time.time()
    written = export_tetris_sft(deduped, tetris, output_path)
    export_time = time.time() - t0
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"  Wrote {written} records to {output_path.name} ({file_size:.1f}MB) in {export_time:.1f}s")

    # ================================================================
    # PHASE 6: Push to HuggingFace (optional)
    # ================================================================
    if args.push_hf:
        print("\nPHASE 6: Pushing to HuggingFace...")
        repo_id = "issdandavis/scbe-aethermoore-training-data"
        if hf_token:
            ok = push_to_hf(output_path, repo_id, hf_token)
            print(f"  Push {'OK' if ok else 'FAILED'} -> {repo_id}")
        else:
            print("  SKIP: No HF token")
    else:
        print("\nPHASE 6: Skipped (use --push-hf to upload)")

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Spin conversations:   {len(spin_pairs)} pairs ({args.spin_sessions} sessions)")
    print(f"  Sphere grid notes:    {len(sphere_sft)} curriculum notes")
    print(f"  Existing SFT:         {len(existing_sft)} pairs")
    print(f"  Total (deduped):      {len(deduped)} records")
    print(f"  Tetris diversity:     {metrics['diversity_score']:.0f}/100")
    print(f"  Octree buckets:       {metrics['n_buckets']}")
    print(f"  Output:               {output_path}")
    print(f"  File size:            {file_size:.1f}MB")


if __name__ == "__main__":
    main()
