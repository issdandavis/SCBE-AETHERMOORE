#!/usr/bin/env python3
"""Build the Pump Aquifer — populate the dantian with real bundles.

Reads the merged training data, computes tongue profiles for each record,
clusters them by canon/null-pattern, and saves representative bundles
as the aquifer that the BundleRetriever queries at inference time.

The aquifer is the dantian — the shaped reserve built by circulation,
separate from the model's parameters.

Output: artifacts/pump_aquifer.jsonl
Each row is a RetrievedBundle-compatible record with tongue_profile,
null_pattern, canon, and text.

Usage:
    python scripts/build_pump_aquifer.py
    python scripts/build_pump_aquifer.py --max-bundles 500
"""

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'src'))

from polly_pump.packet import sense, TONGUE_CODES, TONGUE_NAMES

# ── Config ─────────────────────────────────────────────────────────

DEFAULT_INPUT = REPO / 'training-data' / 'polly_training_merged.jsonl'
DEFAULT_OUTPUT = REPO / 'artifacts' / 'pump_aquifer.jsonl'
MAX_BUNDLES = 1000  # target number of aquifer bundles
TEXT_MAX = 500      # max chars per bundle text
SAMPLE_PER_BUCKET = 5  # bundles per (canon, null_pattern) bucket


def extract_text(record):
    """Extract meaningful text from a record."""
    msgs = record.get('messages', [])
    parts = []
    for m in msgs:
        role = m.get('role', '')
        content = m.get('content', '')
        if role in ('user', 'assistant') and content:
            parts.append(content)
    return ' '.join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=str(DEFAULT_INPUT))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--max-bundles', type=int, default=MAX_BUNDLES)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f'Input:  {input_path}')
    print(f'Output: {output_path}')
    print(f'Target: {args.max_bundles} bundles')

    # ── Pass 1: compute packets and bucket by (canon, null_pattern) ──

    buckets = defaultdict(list)  # (canon, null_pattern) -> list of (idx, packet, text)
    total = 0
    skipped = 0

    print('\nPass 1: computing tongue profiles...')
    with open(input_path, encoding='utf-8', errors='replace') as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            text = extract_text(record)
            if len(text) < 30:
                skipped += 1
                continue

            packet = sense(text[:500])
            key = (packet.canon, packet.null_pattern)
            buckets[key].append({
                'idx': idx,
                'text': text[:TEXT_MAX],
                'packet': packet,
            })
            total += 1

            if (idx + 1) % 20000 == 0:
                print(f'  {idx + 1:,} records → {len(buckets)} buckets')

    print(f'\nPass 1 complete: {total:,} records → {len(buckets)} unique (canon, null_pattern) buckets')
    print(f'Skipped: {skipped:,}')

    # ── Pass 2: sample representative bundles from each bucket ──

    print('\nPass 2: sampling representative bundles...')

    # Sort buckets by size (largest first)
    sorted_buckets = sorted(buckets.items(), key=lambda x: -len(x[1]))

    # Compute samples per bucket to hit target
    remaining = args.max_bundles
    bundle_list = []

    for (canon, null_pattern), items in sorted_buckets:
        if remaining <= 0:
            break

        # Take up to SAMPLE_PER_BUCKET from each, or fewer if bucket is small
        n = min(SAMPLE_PER_BUCKET, len(items), remaining)

        # Sample evenly spaced items (not random, for reproducibility)
        step = max(1, len(items) // n)
        samples = [items[i * step] for i in range(n)]

        for s in samples:
            pkt = s['packet']
            bundle = {
                'bundle_id': f'{canon}-{null_pattern}-{len(bundle_list):04d}',
                'text': s['text'],
                'tongue_profile': pkt.tongue_profile,
                'null_pattern': pkt.null_pattern,
                'canon': pkt.canon,
                'emotion': pkt.emotion,
                'governance': pkt.governance,
                'source_root': '',
                'tags': [],
            }
            bundle_list.append(bundle)
            remaining -= 1

    print(f'Sampled {len(bundle_list)} bundles from {len(sorted_buckets)} buckets')

    # ── Stats ──────────────────────────────────────────────────────

    canon_counts = defaultdict(int)
    pattern_counts = defaultdict(int)
    gov_counts = defaultdict(int)

    for b in bundle_list:
        canon_counts[b['canon']] += 1
        pattern_counts[b['null_pattern']] += 1
        gov_counts[b['governance']] += 1

    print(f'\nAquifer composition:')
    print(f'  By canon:')
    for canon, ct in sorted(canon_counts.items(), key=lambda x: -x[1]):
        print(f'    {canon:20s}: {ct:4d}')

    print(f'  By null pattern (top 10):')
    for pattern, ct in sorted(pattern_counts.items(), key=lambda x: -x[1])[:10]:
        print(f'    {pattern}: {ct:4d}')

    print(f'  By governance:')
    for gov, ct in sorted(gov_counts.items(), key=lambda x: -x[1]):
        print(f'    {gov:12s}: {ct:4d}')

    # ── Write ──────────────────────────────────────────────────────

    with open(output_path, 'w', encoding='utf-8') as f:
        for b in bundle_list:
            f.write(json.dumps(b, ensure_ascii=False) + '\n')

    size_kb = os.path.getsize(output_path) / 1024
    print(f'\nAquifer written: {len(bundle_list)} bundles, {size_kb:.0f} KB')
    print(f'Output: {output_path}')


if __name__ == '__main__':
    main()
