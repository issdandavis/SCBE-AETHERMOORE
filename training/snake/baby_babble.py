#!/usr/bin/env python3
"""
Baby Babble — Phase 0 of the Zara Curriculum
==============================================
Tri-Polynomial Didactic Flow Function (TPDFF)

The mute phase. Before grammar, before meaning, before understanding —
there is sound. Raw phonetic exposure to Sacred Tongue morphemes.

Three layers (phi-weighted):
  1. SMOOTH (KO, phi^0=1.000) — Raw babble. Random syllable concatenation.
     No structure. Pure sonic exposure. The infant hearing language before
     understanding any of it.

  2. FORGE  (DR, phi^1=1.618) — Smoothed babble. Repeated morphemes start
     clustering. Syllable pairs emerge. The child starting to hear patterns
     in the noise — "mama" before "mother."

  3. BIND   (RU, phi^2=2.618) — Bound babble. Morphemes find partners.
     Proto-words form. The toddler babbling "ba-ba" with intent, not just
     random mouth-sounds.

The TPDFF output is training data that teaches a model the PHYSICS of
Sacred Tongue phonology before any grammar or semantics. Like teaching
a baby to hear Korean phonemes in the first 6 months — the window where
phonetic sensitivity is maximum.

Usage:
  PYTHONPATH=. python training/snake/baby_babble.py [--records N] [--output PATH]
"""

import json
import math
import random
import hashlib
import sys
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.crypto.sacred_tongues import TONGUES, TongueSpec

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

# TPDFF layer weights (phi-scaled)
SMOOTH_WEIGHT = 1.0        # phi^0 — raw babble
FORGE_WEIGHT = PHI         # phi^1 — pattern emergence
BIND_WEIGHT = PHI ** 2     # phi^2 — proto-word binding

# Tongue order for profile vectors
TONGUE_ORDER = ["ko", "av", "ru", "ca", "um", "dr"]

# How many syllables per babble string at each layer
SMOOTH_SYLLABLE_RANGE = (3, 12)   # Raw: short to long bursts
FORGE_SYLLABLE_RANGE = (2, 6)     # Smoothed: shorter, repeated
BIND_SYLLABLE_RANGE = (2, 4)      # Bound: proto-words

# Repetition probability at each layer
SMOOTH_REPEAT_PROB = 0.0    # No repetition — pure noise
FORGE_REPEAT_PROB = 0.5     # 50% chance a syllable repeats
BIND_REPEAT_PROB = 0.8      # 80% chance — "ba-ba", "ma-ma"


@dataclass
class BabbleRecord:
    """A single babble training record."""
    instruction: str
    output: str
    metadata: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Syllable generation
# ---------------------------------------------------------------------------

def make_syllable(tongue: TongueSpec, rng: random.Random) -> str:
    """Generate one Sacred Tongue syllable: prefix fragment + suffix."""
    prefix = rng.choice(tongue.prefixes)
    suffix = rng.choice(tongue.suffixes)

    # Take 1-3 chars from prefix for syllable variety
    plen = rng.randint(1, min(3, len(prefix)))
    fragment = prefix[:plen]

    return f"{fragment}'{suffix}" if rng.random() < 0.3 else f"{fragment}{suffix}"


def make_babble_smooth(tongue: TongueSpec, rng: random.Random) -> str:
    """Layer 1: SMOOTH — raw babble. No pattern, no repetition.

    Like an infant hearing language for the first time.
    Random syllables strung together with spaces or hyphens.
    """
    n = rng.randint(*SMOOTH_SYLLABLE_RANGE)
    syllables = [make_syllable(tongue, rng) for _ in range(n)]
    sep = rng.choice([" ", "-", " ", " "])  # Mostly spaces
    return sep.join(syllables)


def make_babble_forge(tongue: TongueSpec, rng: random.Random) -> str:
    """Layer 2: FORGE — smoothed babble. Repetition emerges.

    The child hears "da da da" and starts reproducing it.
    Syllables repeat. Patterns form. Not meaning yet — rhythm.
    """
    n = rng.randint(*FORGE_SYLLABLE_RANGE)
    syllables = []
    for _ in range(n):
        syl = make_syllable(tongue, rng)
        syllables.append(syl)
        if rng.random() < FORGE_REPEAT_PROB:
            syllables.append(syl)  # Echo

    # Sometimes add a rhythmic separator
    sep = rng.choice([" ", "-", " ~ "])
    return sep.join(syllables)


def make_babble_bind(tongue: TongueSpec, rng: random.Random) -> str:
    """Layer 3: BIND — bound babble. Proto-words with intent.

    "Ba-ba" means something now. The syllable pair is a unit.
    Morpheme seams (apostrophes) appear as binding markers.
    """
    n = rng.randint(*BIND_SYLLABLE_RANGE)
    words = []
    for _ in range(n):
        prefix = rng.choice(tongue.prefixes)
        suffix = rng.choice(tongue.suffixes)
        # Full morpheme pair with apostrophe seam
        word = f"{prefix}'{suffix}"
        if rng.random() < BIND_REPEAT_PROB:
            # Bound repetition: the proto-word echoes itself
            words.append(f"{word} {word}")
        else:
            words.append(word)
    return " ".join(words)


# ---------------------------------------------------------------------------
# TPDFF: Tri-Polynomial Didactic Flow Function
# ---------------------------------------------------------------------------

def tpdff_score(smooth: str, forge: str, bind: str) -> float:
    """Compute TPDFF quality score.

    TPDFF(x) = w_s * S(x) + w_f * F(x) + w_b * B(x)

    where:
      S(x) = phonetic diversity (unique syllables / total)
      F(x) = repetition ratio (repeated syllables / total)
      B(x) = binding strength (apostrophe seams / total tokens)

    Returns score in [0, 1]. Higher = better training signal.
    """
    # S(x): diversity in smooth layer
    smooth_tokens = smooth.replace("-", " ").replace("~", " ").split()
    s_unique = len(set(smooth_tokens))
    s_total = max(len(smooth_tokens), 1)
    s_x = s_unique / s_total  # High diversity = good raw exposure

    # F(x): repetition in forge layer
    forge_tokens = forge.replace("-", " ").replace("~", " ").split()
    f_total = max(len(forge_tokens), 1)
    f_repeated = f_total - len(set(forge_tokens))
    f_x = f_repeated / f_total  # Some repetition = pattern learning

    # B(x): binding in bind layer
    bind_tokens = bind.split()
    b_seams = sum(1 for t in bind_tokens if "'" in t)
    b_total = max(len(bind_tokens), 1)
    b_x = b_seams / b_total  # High seam ratio = strong morpheme binding

    # Weighted combination
    total_weight = SMOOTH_WEIGHT + FORGE_WEIGHT + BIND_WEIGHT
    score = (SMOOTH_WEIGHT * s_x + FORGE_WEIGHT * f_x + BIND_WEIGHT * b_x) / total_weight

    return min(1.0, max(0.0, score))


def compute_tongue_profile(tongue_code: str) -> List[float]:
    """Single-tongue activation profile for Phase 0.

    In babble phase, only one tongue is active at a time.
    The model learns one language's phonemes before mixing.
    """
    profile = [0.0] * 6
    idx = TONGUE_ORDER.index(tongue_code)
    profile[idx] = 1.0
    return profile


# ---------------------------------------------------------------------------
# Record generation
# ---------------------------------------------------------------------------

def generate_babble_record(
    tongue_code: str,
    layer: str,
    rng: random.Random,
    record_id: int,
) -> BabbleRecord:
    """Generate one babble training record for a specific tongue and layer."""
    tongue = TONGUES[tongue_code]

    if layer == "smooth":
        babble = make_babble_smooth(tongue, rng)
        instruction = f"[BABBLE:SMOOTH:{tongue.name}] Listen."
        weight = SMOOTH_WEIGHT
    elif layer == "forge":
        babble = make_babble_forge(tongue, rng)
        instruction = f"[BABBLE:FORGE:{tongue.name}] Hear the pattern."
        weight = FORGE_WEIGHT
    elif layer == "bind":
        babble = make_babble_bind(tongue, rng)
        instruction = f"[BABBLE:BIND:{tongue.name}] Name it."
        weight = BIND_WEIGHT
    else:
        raise ValueError(f"Unknown layer: {layer}")

    profile = compute_tongue_profile(tongue_code)

    return BabbleRecord(
        instruction=instruction,
        output=babble,
        metadata={
            "source": "baby_babble",
            "tongue": tongue_code.upper(),
            "tongue_name": tongue.name,
            "tongue_profile": profile,
            "layer": f"L0_{layer}",
            "phase": 0,
            "tpdff_layer": layer,
            "tpdff_weight": round(weight, 4),
            "harmonic_frequency": tongue.harmonic_frequency,
            "grounding": 0.0,  # Pure babble has zero grounding
            "audience": "self",
            "category": f"babble_{layer}",
            "has_code": False,
            "fabrication_depth": 0,
            "record_id": record_id,
        },
    )


def generate_tpdff_triplet(
    tongue_code: str, rng: random.Random, triplet_id: int
) -> List[BabbleRecord]:
    """Generate a TPDFF triplet: smooth -> forge -> bind for one tongue.

    This is the core teaching unit. The model sees the same tongue's
    phonemes at three levels of structure, phi-weighted.
    """
    records = []
    base_id = triplet_id * 3

    smooth_rec = generate_babble_record(tongue_code, "smooth", rng, base_id)
    forge_rec = generate_babble_record(tongue_code, "forge", rng, base_id + 1)
    bind_rec = generate_babble_record(tongue_code, "bind", rng, base_id + 2)

    # Compute TPDFF score for the triplet
    score = tpdff_score(smooth_rec.output, forge_rec.output, bind_rec.output)

    for rec in [smooth_rec, forge_rec, bind_rec]:
        rec.metadata["tpdff_score"] = round(score, 4)

    records.extend([smooth_rec, forge_rec, bind_rec])
    return records


def generate_cross_tongue_record(
    tongue_a: str, tongue_b: str, rng: random.Random, record_id: int
) -> BabbleRecord:
    """Generate a cross-tongue babble record.

    Two tongues mixed — the moment the infant hears a second language.
    This is the transition from Phase 0 to Phase 1.
    """
    ta = TONGUES[tongue_a]
    tb = TONGUES[tongue_b]

    # Interleave syllables from both tongues
    n = rng.randint(4, 8)
    syllables = []
    for _ in range(n):
        if rng.random() < 0.5:
            syllables.append(make_syllable(ta, rng))
        else:
            syllables.append(make_syllable(tb, rng))

    babble = " ".join(syllables)

    # Mixed profile
    profile = [0.0] * 6
    idx_a = TONGUE_ORDER.index(tongue_a)
    idx_b = TONGUE_ORDER.index(tongue_b)
    profile[idx_a] = 0.6
    profile[idx_b] = 0.4

    return BabbleRecord(
        instruction=f"[BABBLE:CROSS:{ta.name}+{tb.name}] Two voices.",
        output=babble,
        metadata={
            "source": "baby_babble",
            "tongue": f"{tongue_a.upper()}+{tongue_b.upper()}",
            "tongue_name": f"{ta.name}+{tb.name}",
            "tongue_profile": profile,
            "layer": "L0_cross",
            "phase": 0,
            "tpdff_layer": "cross",
            "tpdff_weight": round(FORGE_WEIGHT, 4),
            "grounding": 0.0,
            "audience": "self",
            "category": "babble_cross",
            "has_code": False,
            "fabrication_depth": 0,
            "record_id": record_id,
        },
    )


def generate_silence_record(tongue_code: str, rng: random.Random, record_id: int) -> BabbleRecord:
    """Generate a silence/null record.

    The absence of sound is also training data. The model learns
    what a tongue sounds like by also learning what it DOESN'T sound like.
    """
    tongue = TONGUES[tongue_code]

    # Sparse babble — mostly silence with occasional fragments
    n = rng.randint(1, 3)
    fragments = []
    for _ in range(n):
        prefix = rng.choice(tongue.prefixes)
        fragments.append(prefix[:2])  # Just consonant clusters

    babble = " ... ".join(fragments) + " ..."

    profile = compute_tongue_profile(tongue_code)
    # Reduce activation — this is a null-pattern record
    profile = [x * 0.2 for x in profile]

    return BabbleRecord(
        instruction=f"[BABBLE:SILENCE:{tongue.name}] ...",
        output=babble,
        metadata={
            "source": "baby_babble",
            "tongue": tongue_code.upper(),
            "tongue_name": tongue.name,
            "tongue_profile": profile,
            "layer": "L0_null",
            "phase": 0,
            "tpdff_layer": "silence",
            "tpdff_weight": 0.0,
            "null_pattern": True,
            "grounding": 0.0,
            "audience": "self",
            "category": "babble_silence",
            "has_code": False,
            "fabrication_depth": 0,
            "record_id": record_id,
        },
    )


# ---------------------------------------------------------------------------
# Full dataset generation
# ---------------------------------------------------------------------------

def generate_phase0_dataset(
    records_per_tongue: int = 100,
    cross_records: int = 60,
    silence_records: int = 30,
    seed: int = 42,
) -> List[BabbleRecord]:
    """Generate the full Phase 0 Baby Babble dataset.

    Structure:
      - N triplets per tongue (smooth+forge+bind) = 6 tongues * N * 3
      - Cross-tongue pairs for transition training
      - Silence/null records for absence learning

    Default: 100 triplets/tongue = 1,800 triplet records
             + 60 cross-tongue + 30 silence = 1,890 total
    """
    rng = random.Random(seed)
    all_records: List[BabbleRecord] = []
    record_counter = 0

    # Phase 0a: Single-tongue triplets (the core curriculum)
    for tongue_code in TONGUE_ORDER:
        for i in range(records_per_tongue):
            triplet = generate_tpdff_triplet(tongue_code, rng, record_counter)
            all_records.extend(triplet)
            record_counter += 1

    # Phase 0b: Cross-tongue pairs (transition to Phase 1)
    tongue_pairs = [
        ("ko", "av"), ("ko", "dr"), ("av", "ca"),
        ("ru", "um"), ("ca", "dr"), ("um", "ko"),
    ]
    per_pair = max(1, cross_records // len(tongue_pairs))
    for ta, tb in tongue_pairs:
        for _ in range(per_pair):
            rec = generate_cross_tongue_record(ta, tb, rng, record_counter)
            all_records.append(rec)
            record_counter += 1

    # Phase 0c: Silence records (null-pattern training)
    per_tongue_silence = max(1, silence_records // len(TONGUE_ORDER))
    for tongue_code in TONGUE_ORDER:
        for _ in range(per_tongue_silence):
            rec = generate_silence_record(tongue_code, rng, record_counter)
            all_records.append(rec)
            record_counter += 1

    return all_records


def write_babble_jsonl(records: List[BabbleRecord], output_path: str):
    """Write babble records to JSONL."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {output_path}")


def print_stats(records: List[BabbleRecord]):
    """Print dataset statistics."""
    tongue_counts: Dict[str, int] = {}
    layer_counts: Dict[str, int] = {}
    tpdff_scores: List[float] = []

    for rec in records:
        t = rec.metadata.get("tongue", "?")
        tongue_counts[t] = tongue_counts.get(t, 0) + 1
        l = rec.metadata.get("tpdff_layer", "?")
        layer_counts[l] = layer_counts.get(l, 0) + 1
        s = rec.metadata.get("tpdff_score", 0)
        if s > 0:
            tpdff_scores.append(s)

    avg_score = sum(tpdff_scores) / max(len(tpdff_scores), 1)

    print(f"\n{'='*60}")
    print(f"BABY BABBLE — Phase 0 Dataset Statistics")
    print(f"{'='*60}")
    print(f"Total records: {len(records)}")
    print(f"\nTongue distribution:")
    for t, c in sorted(tongue_counts.items()):
        print(f"  {t:8s}: {c:5d} records")
    print(f"\nLayer distribution:")
    for l, c in sorted(layer_counts.items()):
        print(f"  {l:10s}: {c:5d} records")
    print(f"\nTPDFF score: avg={avg_score:.4f}, "
          f"min={min(tpdff_scores):.4f}, max={max(tpdff_scores):.4f}")
    print(f"{'='*60}")

    # Sample outputs
    print(f"\nSample outputs:")
    rng = random.Random(0)
    samples = rng.sample(records, min(9, len(records)))
    for s in samples:
        layer = s.metadata.get("tpdff_layer", "?")
        tongue = s.metadata.get("tongue", "?")
        print(f"  [{layer:7s}|{tongue:5s}] {s.output[:80]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Baby Babble Phase 0 Generator")
    parser.add_argument("--records", type=int, default=100,
                        help="Triplets per tongue (default: 100)")
    parser.add_argument("--cross", type=int, default=60,
                        help="Cross-tongue records (default: 60)")
    parser.add_argument("--silence", type=int, default=30,
                        help="Silence/null records (default: 30)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--output", type=str,
                        default="training-data/sft/baby_babble_phase0.jsonl",
                        help="Output JSONL path")
    args = parser.parse_args()

    records = generate_phase0_dataset(
        records_per_tongue=args.records,
        cross_records=args.cross,
        silence_records=args.silence,
        seed=args.seed,
    )

    print_stats(records)
    write_babble_jsonl(records, args.output)
