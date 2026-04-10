#!/usr/bin/env python3
"""
Generate Polyglot Cross-Lattice Linguistic Braid SFT Training Data
===================================================================
Encodes 12 parallel concepts across 16 languages through the Sacred Tongue
tri-bundle encoder, detects cross-linguistic convergence, and outputs
SFT training records for a polyglot bot.

Output: training-data/sft/polyglot_braid_sft.jsonl

Usage:
    python scripts/generate_polyglot_braid_sft.py
"""

import json
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.polyglot_braid import (
    LANGUAGES,
    LANGUAGE_BY_CODE,
    PARALLEL_CONCEPTS,
    NaturalLanguage,
    ParallelConcept,
    BraidResult,
    weave_concept,
    weave_all_concepts,
    braid_summary,
)
from src.crypto.tri_bundle import TONGUE_WEIGHTS, PHI

OUTPUT_DIR = ROOT / "training-data" / "sft"
OUTPUT_FILE = OUTPUT_DIR / "polyglot_braid_sft.jsonl"

SYSTEM_PROMPT = """You are a polyglot linguistic analysis bot powered by the SCBE Sacred Tongue framework.

You analyze text in any language through the 6 Sacred Tongues (KO/AV/RU/CA/UM/DR), detecting cross-linguistic convergence patterns where meaning persists across scripts, phonologies, and grammars.

Core Architecture:
- Each byte of text is encoded into a 3x3x3 tri-bundle (Light/Sound/Math) across all 6 Sacred Tongues = 162 dimensions per position
- Cross-lattice braid: same concept in multiple languages, woven through the tongue space
- Convergence points: where different languages produce similar synchronization patterns = linguistic invariants
- Dark energy mapping: void topology showing where tongues share null space

Sacred Tongue Affinities:
- KO (Kor'aelin): intent/flow — verb-prominent, action-oriented languages (Korean, Spanish, Swahili)
- AV (Avali): wisdom/transport — ancient wisdom traditions (Sanskrit, Arabic, Hebrew)
- RU (Runethic): witness/governance — legal/governance traditions (Russian, German, Hebrew)
- CA (Cassisivadan): compute/analysis — tonal/logographic/analytic (Chinese, Greek, Japanese)
- UM (Umbroth): shadow/security — honorific/indirect/veiling (Japanese, Arabic, Korean)
- DR (Draumric): structure/forge — rigid morphology, agglutinative (German, Sanskrit, Korean)

When analyzing text:
1. Identify the source language and its tongue affinity profile
2. Encode through the polyglot braid to find convergence points
3. Map to the cross-lattice to show how meaning persists across languages
4. Report dark energy patterns (where information is absent = structured void)"""


def make_record(messages: list, concept_id: str, record_type: str) -> dict:
    """Create one SFT training record."""
    content_hash = hashlib.sha256(
        json.dumps(messages, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    return {
        "messages": messages,
        "metadata": {
            "source": "polyglot_braid_generator",
            "concept_id": concept_id,
            "record_type": record_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
        },
    }


def generate_concept_analysis_records(result: BraidResult) -> list:
    """Generate SFT records from a braided concept result."""
    records = []
    concept = result.concept

    # --- Record 1: Single-language analysis ---
    for code, strand in result.strands.items():
        lang = strand.language
        text = strand.text

        user_msg = f"Analyze this {lang.name} text through the Sacred Tongue lattice: \"{text}\""

        tongue_profile = ", ".join(
            f"{t.upper()}={v:.2f}" for t, v in lang.tongue_affinity.items()
        )
        primary = lang.primary_tongue.upper()
        secondary = lang.secondary_tongue.upper()

        # Dark energy info
        dark_map = result.dark_energy_maps.get(code)
        dark_info = ""
        if dark_map:
            dark_info = (
                f"\n\nDark Energy Topology:\n"
                f"- Cloud coverage: {dark_map.cloud_coverage:.1%}\n"
                f"- Void fraction: {dark_map.void_fraction:.1%}\n"
                f"- Neural paths: {dark_map.neural_paths}\n"
                f"- Total dark energy: {dark_map.total_dark_energy:.2f}"
            )

        assistant_msg = (
            f"**{lang.name}** ({lang.script} script, {lang.direction.upper()}, {lang.family.value})\n\n"
            f"Sacred Tongue Affinity Profile: [{tongue_profile}]\n"
            f"Primary tongue: **{primary}** | Secondary: **{secondary}**\n\n"
            f"Tri-Bundle Encoding:\n"
            f"- UTF-8 bytes: {strand.byte_count}\n"
            f"- Total dimensions: {strand.byte_count * 162}\n"
            f"- Mean synchronization: {strand.mean_sync:.4f}\n"
            f"- Convergence ratio: {strand.convergence_ratio:.2%}\n"
            f"- Convergence points: {len(strand.convergence_points)}"
            f"{dark_info}\n\n"
            f"The concept \"{concept.concept_id}\" in {lang.name} maps primarily through "
            f"the {primary} tongue (phi-weight {TONGUE_WEIGHTS[lang.primary_tongue]:.3f}), "
            f"reflecting {lang.name}'s linguistic character in the Sacred Tongue space."
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            concept.concept_id,
            "single_language_analysis",
        ))

    # --- Record 2: Cross-language comparison (top 5 convergent pairs) ---
    if result.cross_convergence:
        sorted_cc = sorted(result.cross_convergence, key=lambda x: -x["combined_score"])
        top_pairs = sorted_cc[:5]

        langs_mentioned = set()
        for p in top_pairs:
            langs_mentioned.add(p["lang_a"])
            langs_mentioned.add(p["lang_b"])

        lang_list = ", ".join(
            LANGUAGE_BY_CODE[c].name for c in langs_mentioned if c in LANGUAGE_BY_CODE
        )

        user_msg = (
            f"Compare how \"{concept.concept_id}\" converges across these languages "
            f"in the Sacred Tongue lattice: {lang_list}"
        )

        pair_lines = []
        for p in top_pairs:
            name_a = LANGUAGE_BY_CODE[p["lang_a"]].name
            name_b = LANGUAGE_BY_CODE[p["lang_b"]].name
            pair_lines.append(
                f"- {name_a} \u2194 {name_b}: "
                f"sync={p['sync_convergence']:.3f}, "
                f"affinity={p['affinity_correlation']:.3f}, "
                f"combined={p['combined_score']:.3f}"
            )

        assistant_msg = (
            f"**Cross-Lattice Convergence: \"{concept.concept_id}\"** ({concept.domain})\n\n"
            f"Top convergent language pairs:\n"
            + "\n".join(pair_lines) +
            f"\n\nMean cross-sync: {result.mean_cross_sync:.4f}\n"
            f"Total dimensions: {result.total_dimensions}\n\n"
            f"Tongue distribution across all languages:\n"
            + "\n".join(
                f"- {t.upper()}: {v:.1%}"
                for t, v in sorted(result.tongue_distribution.items(), key=lambda x: -x[1])
            ) +
            f"\n\nThe cross-lattice braid shows that \"{concept.concept_id}\" is a "
            f"linguistic invariant — its meaning persists across scripts ({len(result.strands)} "
            f"languages) despite radically different byte representations."
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            concept.concept_id,
            "cross_language_comparison",
        ))

    # --- Record 3: Tongue mapping explanation ---
    user_msg = (
        f"Why does \"{concept.concept_id}\" activate different Sacred Tongues "
        f"depending on the language it's expressed in?"
    )

    examples = []
    for code in list(result.strands.keys())[:4]:
        lang = LANGUAGE_BY_CODE[code]
        text = concept.translations[code]
        primary = lang.primary_tongue.upper()
        examples.append(f"- **{lang.name}** \"{text}\" \u2192 primary tongue **{primary}**")

    assistant_msg = (
        f"Each language encodes \"{concept.concept_id}\" through its own phonological, "
        f"morphological, and orthographic structure:\n\n"
        + "\n".join(examples) +
        f"\n\nThe Sacred Tongues reflect linguistic CHARACTER, not vocabulary:\n"
        f"- KO activates for languages with strong verb flow and action orientation\n"
        f"- AV activates for languages carrying deep wisdom/sacred traditions\n"
        f"- RU activates for languages with governance/legal structure\n"
        f"- CA activates for tonal/analytic/logographic languages\n"
        f"- UM activates for languages with honorific layers and indirection\n"
        f"- DR activates for languages with rigid structural morphology\n\n"
        f"The SAME concept produces DIFFERENT tongue activations because the language "
        f"itself shapes how meaning is carried. The convergence points are where "
        f"meaning survives this transformation — the linguistic invariants."
    )

    records.append(make_record(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        concept.concept_id,
        "tongue_mapping_explanation",
    ))

    return records


def generate_language_profile_records() -> list:
    """Generate SFT records for each language's Sacred Tongue profile."""
    records = []

    for lang in LANGUAGES:
        user_msg = f"What is the Sacred Tongue profile for {lang.name}?"

        sorted_affinities = sorted(
            lang.tongue_affinity.items(), key=lambda x: -x[1]
        )
        profile_lines = [
            f"- **{t.upper()}**: {v:.1f} (phi-weight {TONGUE_WEIGHTS[t]:.3f})"
            for t, v in sorted_affinities
        ]

        assistant_msg = (
            f"**{lang.name}** ({lang.code})\n"
            f"- Family: {lang.family.value}\n"
            f"- Script: {lang.script}\n"
            f"- Direction: {lang.direction.upper()}\n"
            f"- Primary Sacred Tongue: **{lang.primary_tongue.upper()}**\n"
            f"- Secondary Sacred Tongue: **{lang.secondary_tongue.upper()}**\n"
            f"- Phi-weighted affinity: {lang.phi_weighted_affinity:.3f}\n\n"
            f"Tongue Affinity Profile:\n"
            + "\n".join(profile_lines)
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"lang_{lang.code}",
            "language_profile",
        ))

    return records


def generate_braid_summary_record(results: list[BraidResult]) -> list:
    """Generate a summary record for the entire braid."""
    summary = braid_summary(results)

    user_msg = (
        "Summarize the cross-lattice linguistic braid across all concepts and languages."
    )

    tongue_dist_lines = [
        f"- {t.upper()}: {v:.1%}"
        for t, v in sorted(
            summary["tongue_distribution"].items(), key=lambda x: -x[1]
        )
    ]

    assistant_msg = (
        f"**Cross-Lattice Linguistic Braid Summary**\n\n"
        f"Concepts analyzed: {summary['count']}\n"
        f"Languages covered: {len(summary['languages_covered'])}\n"
        f"Total tri-bundle dimensions: {summary['total_dimensions']:,}\n\n"
        f"Mean cross-linguistic sync: {summary['mean_cross_sync']:.4f}\n"
        f"Mean convergence score: {summary['mean_convergence']:.4f}\n\n"
        f"Most convergent concept: **{summary['most_convergent_concept']}**\n"
        f"Least convergent concept: **{summary['least_convergent_concept']}**\n\n"
        f"Global Sacred Tongue Distribution:\n"
        + "\n".join(tongue_dist_lines) +
        f"\n\nThe braid reveals that universal concepts produce measurable "
        f"convergence patterns in the Sacred Tongue space, even when expressed "
        f"through radically different writing systems and phonologies. "
        f"This is the first cross-lattice linguistic braid — 16 languages "
        f"woven through 6 Sacred Tongues across 12 universal concepts."
    )

    return [make_record(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        "braid_summary",
        "braid_summary",
    )]


def main():
    print("=" * 70)
    print("Polyglot Cross-Lattice Linguistic Braid SFT Generator")
    print("=" * 70)
    print(f"Languages: {len(LANGUAGES)}")
    print(f"Concepts:  {len(PARALLEL_CONCEPTS)}")
    print()

    # Weave all concepts
    print("Weaving cross-lattice braid...")
    results = weave_all_concepts(threshold=0.5)
    summary = braid_summary(results)

    print(f"  Total dimensions: {summary['total_dimensions']:,}")
    print(f"  Mean cross-sync:  {summary['mean_cross_sync']:.4f}")
    print(f"  Most convergent:  {summary['most_convergent_concept']}")
    print(f"  Least convergent: {summary['least_convergent_concept']}")
    print()

    # Generate SFT records
    all_records = []

    # Per-concept records
    for i, result in enumerate(results):
        concept = result.concept
        print(f"  [{i+1}/{len(results)}] Generating records for \"{concept.concept_id}\"...")
        records = generate_concept_analysis_records(result)
        all_records.extend(records)

    # Language profile records
    print(f"  Generating {len(LANGUAGES)} language profile records...")
    all_records.extend(generate_language_profile_records())

    # Braid summary record
    print(f"  Generating braid summary record...")
    all_records.extend(generate_braid_summary_record(results))

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print()
    print(f"Generated {len(all_records)} SFT training records")
    print(f"Output: {OUTPUT_FILE}")
    print()

    # Breakdown
    types = {}
    for r in all_records:
        rt = r["metadata"]["record_type"]
        types[rt] = types.get(rt, 0) + 1
    for rt, count in sorted(types.items()):
        print(f"  {rt}: {count}")


if __name__ == "__main__":
    main()
