#!/usr/bin/env python3
"""
Generate Quantum Frequency Bundle SFT Dataset
===============================================
Runs the QHO-grounded quantum frequency bundle generator over the
full Claude conversations corpus + collegiate curriculum records,
producing dense, frequency-tagged training data with:

    - QHO excitation levels per tongue
    - Polychromatic visual frequency vectors (6-channel)
    - 3-band acoustic signatures (infra/audible/ultra)
    - Spectral emission lines
    - Governance costs via harmonic wall
    - Trit signals + Monty Hall multipath analysis

Output: training-data/sft/quantum_frequency_bundles_sft.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.quantum_frequency_bundle import (
    generate_quantum_bundle,
    generate_quantum_sft_records,
    quantum_bundle_summary,
)


def main():
    # Input sources
    sources = [
        ROOT / "training-data" / "sft" / "claude_conversations_sft.jsonl",
        ROOT / "training-data" / "sft" / "collegiate_curriculum_sft.jsonl",
    ]

    output_path = ROOT / "training-data" / "sft" / "quantum_frequency_bundles_sft.jsonl"
    summary_path = ROOT / "training-data" / "sft" / "quantum_frequency_summary.json"

    print("=" * 70)
    print("QUANTUM FREQUENCY BUNDLE SFT GENERATOR")
    print("QHO physics -> polychromatic visual + acoustic + governance")
    print("=" * 70)
    print()

    # Collect texts from all sources
    all_texts = []
    source_counts = {}

    for src_path in sources:
        if not src_path.exists():
            print(f"  SKIP: {src_path.name} not found")
            continue

        print(f"  Loading: {src_path.name}")
        count = 0
        with open(src_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                messages = record.get("messages", [])
                combined = " ".join(m.get("content", "") for m in messages).strip()
                if len(combined) >= 50:
                    all_texts.append(combined[:512])  # cap for speed
                    count += 1
        source_counts[src_path.name] = count
        print(f"    -> {count} texts extracted")

    print(f"\n  Total texts: {len(all_texts)}")
    print()

    # Generate quantum bundles
    print("Generating quantum frequency bundles...")
    bundles = []
    sft_records = []

    batch_size = 200
    for i in range(0, len(all_texts), batch_size):
        batch = all_texts[i:i + batch_size]
        batch_bundles = [generate_quantum_bundle(t) for t in batch]
        bundles.extend(batch_bundles)
        batch_sft = generate_quantum_sft_records(batch_bundles)
        sft_records.extend(batch_sft)

        done = min(i + batch_size, len(all_texts))
        if done % 1000 == 0 or done == len(all_texts):
            print(f"  [{done}/{len(all_texts)}] bundles generated...")

    # Write output
    print(f"\nWriting {len(sft_records)} SFT records...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in sft_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Summary
    summary = quantum_bundle_summary(bundles)
    summary["sources"] = source_counts
    summary["total_sft_records"] = len(sft_records)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print("=" * 70)
    print(f"Total bundles: {summary['count']}")
    print(f"SFT records: {len(sft_records)}")
    print(f"Output: {output_path}")
    print()
    print(f"Sources:")
    for name, count in source_counts.items():
        print(f"  {name}: {count}")
    print()
    print(f"Excitation stats:")
    print(f"  Mean max excitation: {summary['excitation']['mean_max']}")
    print(f"  Ground states: {summary['excitation']['ground_state_count']} "
          f"({summary['excitation']['ground_state_pct']}%)")
    print(f"  Max excited: {summary['excitation']['max_excited_count']} "
          f"({summary['excitation']['max_excited_pct']}%)")
    print()
    print("Visual vector means (polychromatic emission):")
    for t, v in summary["visual_vector_means"].items():
        print(f"  {t.upper():>2}: {v:.4f}")
    print()
    print("Acoustic band means:")
    for band, v in summary["acoustic_band_means"].items():
        print(f"  {band:>12}: {v:.4f}")
    print()
    print(f"Mean harmonic cost: {summary['governance']['mean_harmonic_cost']:.4f}")
    print(f"Total spectral lines: {summary['total_spectral_lines']} "
          f"(mean {summary['mean_lines_per_record']:.1f}/record)")
    print()
    print("Dominant tongue distribution:")
    for t, c in summary["dominant_tongue_distribution"].items():
        pct = c / summary["count"] * 100
        print(f"  {t.upper():>2}: {c:>5} ({pct:.1f}%)")
    print()
    print("Musical interval distribution:")
    for iv, c in summary["musical_interval_distribution"].items():
        pct = c / summary["count"] * 100
        print(f"  {iv:>15}: {c:>5} ({pct:.1f}%)")
    print()
    ga = summary.get("gallery_ambient", {})
    if ga:
        print("Gallery Ambient (dead tone detection):")
        print(f"  Autorotation active: {ga.get('autorotation_active_count', 0)} "
              f"({ga.get('autorotation_active_pct', 0.0)}%)")
        print(f"  Mean gallery energy: {ga.get('mean_gallery_energy', 0):.4f}")
        print(f"  Dominant dead tone distribution:")
        for tone, c in ga.get("dominant_dead_tone_distribution", {}).items():
            pct = c / max(1, summary["count"]) * 100
            print(f"    {tone:>15}: {c:>5} ({pct:.1f}%)")
        print(f"  Mean blind spot proximity:")
        for tone, v in ga.get("mean_blind_spot_proximity", {}).items():
            print(f"    {tone:>15}: {v:.4f}")
        print(f"  Mean coupling strength:")
        for tone, v in ga.get("mean_coupling_strength", {}).items():
            print(f"    {tone:>15}: {v:.4f}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
