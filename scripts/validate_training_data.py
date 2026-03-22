"""
Training Data Validation Suite
================================

Validates the mega ingest + Tetris enriched training data:
  1. Schema validation — required fields, types
  2. Content quality — empty/short/duplicate detection
  3. Tongue distribution — balance analysis
  4. Embedding integrity — Tetris coords present and valid
  5. Source coverage — all expected sources represented
  6. Trainability check — SFT format compatibility
  7. Sample inspection — random samples per tongue

Run:
  python scripts/validate_training_data.py
"""

import json
import hashlib
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TONGUE_KEYS = ["KO", "AV", "RU", "CA", "UM", "DR"]


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    records.append({"_parse_error": True})
    return records


def validate_schema(records: list[dict]) -> dict:
    """Check that records have required SFT fields."""
    results = {
        "total": len(records),
        "has_instruction": 0,
        "has_response": 0,
        "has_prompt": 0,
        "has_text": 0,
        "has_metadata": 0,
        "has_tongue": 0,
        "has_encoding_tongue": 0,
        "parse_errors": 0,
        "trainable": 0,  # Has at least instruction+response OR prompt+response OR text
    }

    for r in records:
        if r.get("_parse_error"):
            results["parse_errors"] += 1
            continue
        if r.get("instruction"): results["has_instruction"] += 1
        if r.get("response"): results["has_response"] += 1
        if r.get("prompt"): results["has_prompt"] += 1
        if r.get("text"): results["has_text"] += 1
        if r.get("metadata"): results["has_metadata"] += 1
        if r.get("tongue"): results["has_tongue"] += 1
        if r.get("encoding_tongue"): results["has_encoding_tongue"] += 1

        # Trainable if it has some input + output
        has_input = bool(r.get("instruction") or r.get("prompt") or r.get("text"))
        has_output = bool(r.get("response") or r.get("text"))
        if has_input and has_output:
            results["trainable"] += 1

    results["trainable_pct"] = round(results["trainable"] / max(1, results["total"]) * 100, 1)
    return results


def validate_content_quality(records: list[dict]) -> dict:
    """Check for empty, short, and duplicate content."""
    empty = 0
    short = 0
    very_long = 0
    duplicates = 0
    seen_hashes = set()
    lengths = []

    for r in records:
        if r.get("_parse_error"):
            continue
        resp = r.get("response", r.get("text", ""))
        inst = r.get("instruction", r.get("prompt", ""))
        content = str(inst) + str(resp)

        if not resp:
            empty += 1
        elif len(str(resp)) < 50:
            short += 1
        if len(str(resp)) > 10000:
            very_long += 1

        lengths.append(len(content))

        h = hashlib.md5(content.encode(errors="replace")).hexdigest()
        if h in seen_hashes:
            duplicates += 1
        seen_hashes.add(h)

    avg_len = sum(lengths) / max(1, len(lengths))
    median_len = sorted(lengths)[len(lengths) // 2] if lengths else 0

    return {
        "empty_responses": empty,
        "short_responses_lt50": short,
        "very_long_gt10k": very_long,
        "duplicates_found": duplicates,
        "avg_content_length": round(avg_len),
        "median_content_length": median_len,
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
        "quality_rate_pct": round((len(records) - empty - short) / max(1, len(records)) * 100, 1),
    }


def validate_tongue_distribution(records: list[dict]) -> dict:
    """Analyze tongue balance."""
    counts = Counter()
    for r in records:
        if r.get("_parse_error"):
            continue
        meta = r.get("metadata", {})
        if isinstance(meta, str):
            meta = {}
        tongue = (r.get("tongue") or meta.get("tongue") or
                  r.get("encoding_tongue") or "UNK")
        counts[tongue] += 1

    total = sum(counts.values())
    target = total / 6 if total else 0
    distribution = {}
    for t in TONGUE_KEYS + (["UNK"] if counts.get("UNK") else []):
        c = counts.get(t, 0)
        distribution[t] = {
            "count": c,
            "pct": round(c / max(1, total) * 100, 1),
            "delta_from_target": round(c - target),
            "status": "OK" if abs(c - target) < target * 0.3 else "SKEW",
        }

    return {
        "total_tagged": total,
        "unique_tongues": len(counts),
        "distribution": distribution,
        "most_common": counts.most_common(3),
        "least_common": counts.most_common()[-3:] if len(counts) >= 3 else counts.most_common(),
        "balance_score": round(min(counts.get(t, 0) for t in TONGUE_KEYS) /
                               max(1, max(counts.get(t, 0) for t in TONGUE_KEYS)) * 100),
    }


def validate_tetris_embeddings(records: list[dict]) -> dict:
    """Validate Tetris enrichment fields."""
    has_tongue_coords = 0
    has_spatial_coords = 0
    has_embedding_hash = 0
    valid_coords = 0
    coord_dims = Counter()

    for r in records:
        tc = r.get("tongue_coords")
        sc = r.get("spatial_coords")
        eh = r.get("embedding_hash")

        if tc: has_tongue_coords += 1
        if sc: has_spatial_coords += 1
        if eh: has_embedding_hash += 1

        if tc and sc:
            coord_dims[f"{len(tc)}D+{len(sc)}D"] += 1
            # Check coords are finite numbers
            try:
                if all(isinstance(x, (int, float)) and abs(x) < 100 for x in tc + sc):
                    valid_coords += 1
            except (TypeError, ValueError):
                pass

    total = len(records)
    return {
        "has_tongue_coords": has_tongue_coords,
        "has_spatial_coords": has_spatial_coords,
        "has_embedding_hash": has_embedding_hash,
        "valid_coords": valid_coords,
        "enrichment_rate_pct": round(has_tongue_coords / max(1, total) * 100, 1),
        "coord_dimensions": dict(coord_dims.most_common(5)),
    }


def validate_source_coverage(records: list[dict]) -> dict:
    """Check which sources are represented."""
    sources = Counter()
    for r in records:
        meta = r.get("metadata", {})
        if isinstance(meta, str):
            meta = {}
        src = meta.get("source", meta.get("source_file", "unknown"))
        if isinstance(src, str):
            sources[src[:50]] += 1

    return {
        "unique_sources": len(sources),
        "top_20_sources": dict(sources.most_common(20)),
        "single_record_sources": sum(1 for c in sources.values() if c == 1),
    }


def sample_records(records: list[dict], n_per_tongue: int = 2) -> dict:
    """Pull random samples per tongue for human review."""
    by_tongue = defaultdict(list)
    for r in records:
        if r.get("_parse_error"):
            continue
        meta = r.get("metadata", {})
        if isinstance(meta, str):
            meta = {}
        tongue = (r.get("tongue") or meta.get("tongue") or
                  r.get("encoding_tongue") or "UNK")
        by_tongue[tongue].append(r)

    samples = {}
    rng = random.Random(42)
    for tongue in TONGUE_KEYS:
        pool = by_tongue.get(tongue, [])
        picked = rng.sample(pool, min(n_per_tongue, len(pool)))
        samples[tongue] = []
        for p in picked:
            inst = str(p.get("instruction", p.get("prompt", "")))[:150]
            resp = str(p.get("response", p.get("text", "")))[:200]
            meta = p.get("metadata", {})
            if isinstance(meta, str):
                meta = {}
            samples[tongue].append({
                "instruction_preview": inst,
                "response_preview": resp,
                "source": meta.get("source", "unknown"),
            })
    return samples


def main():
    print("=" * 70)
    print("TRAINING DATA VALIDATION SUITE")
    print("=" * 70)

    # Validate both files
    files = {
        "mega_ingest_sft.jsonl": ROOT / "training-data" / "mega_ingest_sft.jsonl",
        "mega_tetris_enriched_sft.jsonl": ROOT / "training-data" / "mega_tetris_enriched_sft.jsonl",
    }

    for name, path in files.items():
        if not path.exists():
            print(f"\n  SKIP: {name} not found")
            continue

        print(f"\n{'='*70}")
        print(f"FILE: {name}")
        print(f"  Size: {path.stat().st_size / (1024*1024):.1f}MB")
        print(f"{'='*70}")

        t0 = time.time()
        records = load_jsonl(path)
        print(f"  Loaded {len(records)} records in {time.time()-t0:.1f}s")

        # 1. Schema
        print("\n--- SCHEMA VALIDATION ---")
        schema = validate_schema(records)
        print(f"  Total:          {schema['total']}")
        print(f"  Parse errors:   {schema['parse_errors']}")
        print(f"  Has instruction: {schema['has_instruction']}")
        print(f"  Has response:   {schema['has_response']}")
        print(f"  Has prompt:     {schema['has_prompt']}")
        print(f"  Has text:       {schema['has_text']}")
        print(f"  Has tongue:     {schema['has_tongue']}")
        print(f"  TRAINABLE:      {schema['trainable']} ({schema['trainable_pct']}%)")
        status = "PASS" if schema["trainable_pct"] > 80 else "WARN" if schema["trainable_pct"] > 50 else "FAIL"
        print(f"  Status:         [{status}]")

        # 2. Content quality
        print("\n--- CONTENT QUALITY ---")
        quality = validate_content_quality(records)
        print(f"  Empty responses:  {quality['empty_responses']}")
        print(f"  Short (<50ch):    {quality['short_responses_lt50']}")
        print(f"  Very long (>10k): {quality['very_long_gt10k']}")
        print(f"  Duplicates:       {quality['duplicates_found']}")
        print(f"  Avg length:       {quality['avg_content_length']} chars")
        print(f"  Median length:    {quality['median_content_length']} chars")
        print(f"  Quality rate:     {quality['quality_rate_pct']}%")
        status = "PASS" if quality["quality_rate_pct"] > 90 else "WARN" if quality["quality_rate_pct"] > 70 else "FAIL"
        print(f"  Status:           [{status}]")

        # 3. Tongue distribution
        print("\n--- TONGUE DISTRIBUTION ---")
        tongues = validate_tongue_distribution(records)
        print(f"  Balance score:  {tongues['balance_score']}/100 (100=perfect)")
        for t in TONGUE_KEYS + (["UNK"] if "UNK" in tongues["distribution"] else []):
            info = tongues["distribution"].get(t, {"count": 0, "pct": 0, "status": "N/A"})
            bar = "#" * max(1, int(info["pct"] / 2))
            print(f"    {t}: {info['count']:>6} ({info['pct']:>5.1f}%) {bar} [{info['status']}]")

        # 4. Tetris embeddings (only for enriched file)
        if "tetris" in name:
            print("\n--- TETRIS EMBEDDING INTEGRITY ---")
            tetris = validate_tetris_embeddings(records)
            print(f"  Has tongue coords:    {tetris['has_tongue_coords']}")
            print(f"  Has spatial coords:   {tetris['has_spatial_coords']}")
            print(f"  Has embedding hash:   {tetris['has_embedding_hash']}")
            print(f"  Valid coords:         {tetris['valid_coords']}")
            print(f"  Enrichment rate:      {tetris['enrichment_rate_pct']}%")
            print(f"  Coord dimensions:     {tetris['coord_dimensions']}")
            status = "PASS" if tetris["enrichment_rate_pct"] > 95 else "WARN"
            print(f"  Status:               [{status}]")

        # 5. Source coverage
        print("\n--- SOURCE COVERAGE ---")
        sources = validate_source_coverage(records)
        print(f"  Unique sources:       {sources['unique_sources']}")
        print(f"  Single-record sources: {sources['single_record_sources']}")
        print(f"  Top sources:")
        for src, count in list(sources["top_20_sources"].items())[:15]:
            print(f"    {src:.<45} {count:>5}")

        # 6. Samples
        print("\n--- SAMPLE RECORDS (per tongue) ---")
        samples = sample_records(records, n_per_tongue=1)
        for tongue, recs in samples.items():
            for s in recs:
                print(f"\n  [{tongue}] Source: {s['source']}")
                q = s['instruction_preview'].encode('ascii', 'replace').decode()
                a = s['response_preview'][:120].encode('ascii', 'replace').decode()
                print(f"    Q: {q}")
                print(f"    A: {a}...")

    # Save validation report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files_validated": list(files.keys()),
        "records_total": len(records) if records else 0,
    }
    report_path = ROOT / "artifacts" / "training_validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))

    print(f"\n{'='*70}")
    print(f"VALIDATION COMPLETE")
    print(f"  Report: {report_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
