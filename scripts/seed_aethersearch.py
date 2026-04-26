#!/usr/bin/env python3
"""
Seed AetherSearch with Polly grounding anchors + site content.

Usage:
  PYTHONPATH=. python scripts/seed_aethersearch.py [--dry-run]

Reads polly_grounding_anchors.jsonl and indexes each record
through the SCBE enrichment pipeline into AetherSearch.
"""

import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.search_enrichment import enrich_document, EnrichedDocument

GROUNDING_FILE = "training-data/sft/polly_grounding_anchors.jsonl"


def load_grounding_anchors(path: str) -> list[dict]:
    """Load JSONL grounding anchors."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def seed_from_anchors(dry_run: bool = False):
    """Enrich and index grounding anchors."""
    records = load_grounding_anchors(GROUNDING_FILE)
    print(f"Loaded {len(records)} grounding anchors from {GROUNDING_FILE}")

    enriched = []
    for i, rec in enumerate(records):
        instruction = rec.get("instruction", "")
        output = rec.get("output", "")
        meta = rec.get("metadata", {})
        category = meta.get("category", "general")
        meta.get("audience", "customer")

        doc = enrich_document(
            title=instruction,
            content=output,
            url="https://aethermoore.com",
            source=f"grounding_{category}",
            doc_id=f"polly_{category}_{i:04d}",
        )
        enriched.append(doc)

        if dry_run or i < 5:
            print(
                f"  [{i:3d}] {doc.dominant_tongue} | "
                f"H={doc.harmonic_distance:.2f} | "
                f"F={doc.friction_magnitude:.2f} | "
                f"{doc.governance_tier:11s} | "
                f"{instruction[:60]}"
            )

    # Stats
    tongue_counts = {}
    gov_counts = {}
    for d in enriched:
        tongue_counts[d.dominant_tongue] = tongue_counts.get(d.dominant_tongue, 0) + 1
        gov_counts[d.governance_tier] = gov_counts.get(d.governance_tier, 0) + 1

    print(f"\n--- Enrichment Summary ---")
    print(f"Total: {len(enriched)}")
    print(f"Tongues: {tongue_counts}")
    print(f"Governance: {gov_counts}")

    if dry_run:
        print("\n[DRY RUN] No documents indexed.")
        return enriched

    # Try Meilisearch indexing
    try:
        from src.api.search_routes import _get_meili, MEILI_INDEX

        meili = _get_meili()
        if meili:
            index = meili.index(MEILI_INDEX)
            docs = [d.to_meili_doc() for d in enriched]
            task = index.add_documents(docs)
            print(f"\nIndexed {len(docs)} documents into Meilisearch (task: {task.task_uid})")
        else:
            print("\nMeilisearch not available. Documents enriched but not indexed.")
            _write_enriched_jsonl(enriched)
    except Exception as e:
        print(f"\nMeilisearch indexing failed: {e}")
        _write_enriched_jsonl(enriched)

    return enriched


def _write_enriched_jsonl(enriched: list[EnrichedDocument]):
    """Write enriched docs to JSONL as fallback."""
    out_path = "training-data/sft/aethersearch_enriched.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for doc in enriched:
            f.write(json.dumps(doc.to_meili_doc()) + "\n")
    print(f"Wrote {len(enriched)} enriched documents to {out_path}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    seed_from_anchors(dry_run=dry_run)
