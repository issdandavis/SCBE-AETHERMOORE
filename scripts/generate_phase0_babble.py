#!/usr/bin/env python3
"""
Phase 0: Baby Babble Generator — Tri-Polynomial Didactic Flow Function (TPDFF)
===============================================================================

Generates the first training data for the Zara Curriculum.

Like Zara before Izack found her: mute, raw, pre-verbal. The model encounters
Sacred Tongue tokens for the first time. No grammar, no rules — just exposure
to the FEEL of each tongue.

Three phi-weighted polynomial layers:
  P1 (Kor'aelin, φ^0=1.00): Phoneme smoothing — raw tokens → softened sequences
  P2 (Avali,     φ^1=1.62): Pattern forging — repeated motifs emerge from noise
  P3 (Runethic,  φ^2=2.62): Binding sparks — occasional flashes of structure

The teaching signal is NOT correction. It's exposure + gentle nudging.
Each record is a conversation between the "world" (raw noise) and the
"baby model" (attempting to echo, repeat, or respond).

Output: training-data/sft/phase0_baby_babble_sft.jsonl

Difficulty curve:
  - 0.00-0.10: Pure noise (random tokens from one tongue)
  - 0.10-0.25: Echo tasks (repeat what you heard)
  - 0.25-0.40: Pattern tasks (find the repeating token)
  - 0.40-0.55: Sorting tasks (group tokens by tongue)
  - 0.55-0.70: Completion tasks (finish the sequence)
  - 0.70-0.85: Translation tasks (same sound, different tongue)
  - 0.85-1.00: Naming tasks (what tongue is this?)
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.crypto.sacred_tongues import TONGUES, SacredTongueTokenizer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
SEED = 42

# Phi-weighted polynomial coefficients for the three teaching layers
P1_WEIGHT = 1.0  # Kor'aelin layer — phoneme smoothing
P2_WEIGHT = PHI  # Avali layer — pattern forging
P3_WEIGHT = PHI**2  # Runethic layer — binding sparks

# Tongue codes in compass order (matching GeoSeal Compass)
TONGUE_CODES = ["ko", "av", "ru", "ca", "um", "dr"]
TONGUE_FULL_NAMES = {
    "ko": "Kor'aelin",
    "av": "Avali",
    "ru": "Runethic",
    "ca": "Cassisivadan",
    "um": "Umbroth",
    "dr": "Draumric",
}

# Tongue phi weights (from L3 Langues Weighting System)
TONGUE_PHI_WEIGHTS = {
    "ko": PHI**0,
    "av": PHI**1,
    "ru": PHI**2,
    "ca": PHI**3,
    "um": PHI**4,
    "dr": PHI**5,
}

# How many records per difficulty tier
RECORDS_PER_TIER = {
    "pure_noise": 2000,
    "echo": 2500,
    "pattern": 2500,
    "sorting": 2000,
    "completion": 2000,
    "translation": 1500,
    "naming": 1500,
}


# ---------------------------------------------------------------------------
# Tokenizer setup
# ---------------------------------------------------------------------------


def build_tokenizer() -> SacredTongueTokenizer:
    """Build the Sacred Tongue tokenizer."""
    return SacredTongueTokenizer(TONGUES)


def random_tokens(tokenizer: SacredTongueTokenizer, tongue: str, count: int) -> List[str]:
    """Generate random Sacred Tongue tokens."""
    table = tokenizer.byte_to_token[tongue]
    return [table[random.randint(0, 255)] for _ in range(count)]


def all_tokens(tokenizer: SacredTongueTokenizer, tongue: str) -> List[str]:
    """Get all 256 tokens for a tongue."""
    return list(tokenizer.byte_to_token[tongue])


# ---------------------------------------------------------------------------
# TPDFF: Tri-Polynomial Didactic Flow Function
# ---------------------------------------------------------------------------


def tpdff_smooth(tokens: List[str], weight: float) -> List[str]:
    """P1: Phoneme smoothing — remove harsh transitions.

    Scans for repeated consonant clusters and softens them by
    occasionally inserting a vowel-heavy token from the same tongue.
    Weight controls how aggressively we smooth (higher = more smoothing).
    """
    if weight < 0.3 or len(tokens) < 3:
        return tokens

    result = list(tokens)
    # Every N tokens, repeat the previous one (creates rhythm)
    interval = max(2, int(6 / weight))
    for i in range(interval, len(result), interval):
        if random.random() < weight * 0.3:
            result[i] = result[i - 1]  # Echo creates smoothing
    return result


def tpdff_pattern(tokens: List[str], weight: float) -> Tuple[List[str], Optional[str]]:
    """P2: Pattern forging — introduce repeating motifs.

    Selects a random token and weaves it through the sequence at
    phi-spaced intervals. Returns the pattern token for answer generation.
    Weight controls pattern density (higher = more prominent pattern).
    """
    if weight < 0.5 or len(tokens) < 5:
        return tokens, None

    result = list(tokens)
    pattern_token = random.choice(tokens)
    # Insert pattern at phi-spaced positions
    phi_step = max(2, int(len(tokens) / (weight * 2)))
    for i in range(0, len(result), phi_step):
        if random.random() < weight * 0.4:
            result[i] = pattern_token
    return result, pattern_token


def tpdff_bind(tokens: List[str], weight: float) -> Tuple[List[str], Optional[List[str]]]:
    """P3: Binding sparks — occasional flashes of structure.

    Groups tokens into pairs or triples that form proto-words.
    Weight controls how often binding occurs (higher = more structure).
    Returns the bound groups for answer generation.
    """
    if weight < 1.0 or len(tokens) < 6:
        return tokens, None

    result = list(tokens)
    groups: List[List[str]] = []
    group_size = random.choice([2, 3])
    # Create groups at random positions
    positions = sorted(random.sample(range(len(result) - group_size), min(3, len(result) // group_size)))
    for pos in positions:
        group = result[pos : pos + group_size]
        groups.append(group)
        # Mark the group by repeating it (reinforcement)
        if pos + group_size * 2 <= len(result) and random.random() < weight * 0.2:
            for j in range(group_size):
                result[pos + group_size + j] = group[j]
    return result, groups if groups else None


# ---------------------------------------------------------------------------
# Record generators (one per difficulty tier)
# ---------------------------------------------------------------------------


@dataclass
class BabbleRecord:
    """A single Phase 0 training record."""

    system: str
    user: str
    assistant: str
    tongue: str
    difficulty: float
    tier: str
    tags: List[str]


def _system_prompt(tongue: str, difficulty: float) -> str:
    """Generate system prompt for babble records."""
    name = TONGUE_FULL_NAMES[tongue]
    weight = TONGUE_PHI_WEIGHTS[tongue]
    return (
        f"[PHASE-0: BABY-BABBLE] [TONGUE: {tongue.upper()} ({name})] "
        f"[PHI-WEIGHT: {weight:.3f}] [DIFFICULTY: {difficulty:.2f}]\n"
        f"You are learning to recognize the sounds of {name}. "
        f"Listen carefully and respond with what you hear."
    )


def gen_pure_noise(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.00-0.10: Pure random token exposure.

    User sends random tokens. Assistant echoes a subset.
    Teaching: mere exposure to the phoneme inventory.
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        tongue = random.choice(TONGUE_CODES)
        n_tokens = random.randint(3, 12)
        tokens = random_tokens(tokenizer, tongue, n_tokens)
        difficulty = random.uniform(0.0, 0.10)

        # Apply P1 smoothing only
        smoothed = tpdff_smooth(tokens, P1_WEIGHT * difficulty * 10)

        # Assistant echoes 1-3 tokens (the loudest sounds)
        echo_count = random.randint(1, min(3, len(smoothed)))
        echo = random.sample(smoothed, echo_count)

        records.append(
            BabbleRecord(
                system=_system_prompt(tongue, difficulty),
                user=" ".join(smoothed),
                assistant=" ".join(echo),
                tongue=tongue,
                difficulty=difficulty,
                tier="pure_noise",
                tags=["phase0", "noise", f"tongue-{tongue.upper()}"],
            )
        )
    return records


def gen_echo(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.10-0.25: Echo tasks.

    User sends a short sequence. Assistant repeats it exactly.
    Teaching: exact reproduction — the first step of language.
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        tongue = random.choice(TONGUE_CODES)
        n_tokens = random.randint(2, 8)
        tokens = random_tokens(tokenizer, tongue, n_tokens)
        difficulty = random.uniform(0.10, 0.25)

        smoothed = tpdff_smooth(tokens, P1_WEIGHT)

        records.append(
            BabbleRecord(
                system=_system_prompt(tongue, difficulty),
                user=f"Echo: {' '.join(smoothed)}",
                assistant=" ".join(smoothed),
                tongue=tongue,
                difficulty=difficulty,
                tier="echo",
                tags=["phase0", "echo", f"tongue-{tongue.upper()}"],
            )
        )
    return records


def gen_pattern(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.25-0.40: Pattern recognition.

    A sequence with a repeating token woven in. Assistant identifies it.
    Teaching: pattern detection — noticing what repeats.
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        tongue = random.choice(TONGUE_CODES)
        n_tokens = random.randint(6, 15)
        tokens = random_tokens(tokenizer, tongue, n_tokens)
        difficulty = random.uniform(0.25, 0.40)

        patterned, pattern_token = tpdff_pattern(tokens, P2_WEIGHT)
        if pattern_token is None:
            # Fallback: manually insert pattern
            pattern_token = tokens[0]
            for i in range(0, len(tokens), 3):
                patterned[i] = pattern_token

        records.append(
            BabbleRecord(
                system=_system_prompt(tongue, difficulty),
                user=f"What repeats? {' '.join(patterned)}",
                assistant=pattern_token,
                tongue=tongue,
                difficulty=difficulty,
                tier="pattern",
                tags=["phase0", "pattern", f"tongue-{tongue.upper()}"],
            )
        )
    return records


def gen_sorting(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.40-0.55: Sorting by tongue.

    Mixed tokens from 2-3 tongues. Assistant groups them.
    Teaching: categorical perception — these sounds belong together.
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        n_tongues = random.randint(2, 3)
        chosen = random.sample(TONGUE_CODES, n_tongues)
        difficulty = random.uniform(0.40, 0.55)

        mixed: List[Tuple[str, str]] = []  # (tongue_code, token)
        for t in chosen:
            n = random.randint(2, 5)
            for tok in random_tokens(tokenizer, t, n):
                mixed.append((t, tok))
        random.shuffle(mixed)

        user_tokens = " ".join(tok for _, tok in mixed)

        # Answer: grouped by tongue
        groups: Dict[str, List[str]] = {}
        for t, tok in mixed:
            groups.setdefault(t, []).append(tok)
        answer_parts = []
        for t in chosen:
            if t in groups:
                answer_parts.append(f"[{t.upper()}] {' '.join(groups[t])}")

        records.append(
            BabbleRecord(
                system=_system_prompt(chosen[0], difficulty),
                user=f"Sort by tongue: {user_tokens}",
                assistant=" | ".join(answer_parts),
                tongue=chosen[0],
                difficulty=difficulty,
                tier="sorting",
                tags=["phase0", "sorting", "multi-tongue"] + [f"tongue-{t.upper()}" for t in chosen],
            )
        )
    return records


def gen_completion(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.55-0.70: Sequence completion.

    A sequence with the last 1-2 tokens missing. Assistant fills in.
    Teaching: prediction — what comes next in this tongue?
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        tongue = random.choice(TONGUE_CODES)
        n_tokens = random.randint(5, 10)
        tokens = random_tokens(tokenizer, tongue, n_tokens)
        difficulty = random.uniform(0.55, 0.70)

        # Apply pattern forging so there IS something to predict
        patterned, pattern_tok = tpdff_pattern(tokens, P2_WEIGHT * 1.5)

        # Remove last 1-2 tokens
        hide_count = random.randint(1, 2)
        visible = patterned[:-hide_count]
        hidden = patterned[-hide_count:]

        records.append(
            BabbleRecord(
                system=_system_prompt(tongue, difficulty),
                user=f"Complete: {' '.join(visible)} ___",
                assistant=" ".join(hidden),
                tongue=tongue,
                difficulty=difficulty,
                tier="completion",
                tags=["phase0", "completion", f"tongue-{tongue.upper()}"],
            )
        )
    return records


def gen_translation(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.70-0.85: Cross-tongue echo.

    A byte sequence encoded in one tongue; assistant re-encodes in another.
    Teaching: same meaning, different sound — the first cross-tongue leap.
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        source_tongue = random.choice(TONGUE_CODES)
        target_tongue = random.choice([t for t in TONGUE_CODES if t != source_tongue])
        difficulty = random.uniform(0.70, 0.85)

        # Generate random bytes and encode in both tongues
        n_bytes = random.randint(3, 8)
        raw_bytes = bytes(random.randint(0, 255) for _ in range(n_bytes))

        source_tokens = tokenizer.encode_bytes(source_tongue, raw_bytes)
        target_tokens = tokenizer.encode_bytes(target_tongue, raw_bytes)

        TONGUE_FULL_NAMES[source_tongue]
        tgt_name = TONGUE_FULL_NAMES[target_tongue]

        records.append(
            BabbleRecord(
                system=_system_prompt(source_tongue, difficulty),
                user=f"Say in {tgt_name}: {' '.join(source_tokens)}",
                assistant=" ".join(target_tokens),
                tongue=source_tongue,
                difficulty=difficulty,
                tier="translation",
                tags=["phase0", "translation", f"tongue-{source_tongue.upper()}", f"tongue-{target_tongue.upper()}"],
            )
        )
    return records


def gen_naming(tokenizer: SacredTongueTokenizer, count: int) -> List[BabbleRecord]:
    """Tier 0.85-1.00: Tongue identification.

    A sequence of tokens. Assistant names the tongue.
    Teaching: metalinguistic awareness — knowing WHICH language you hear.
    """
    records: List[BabbleRecord] = []
    for _ in range(count):
        tongue = random.choice(TONGUE_CODES)
        n_tokens = random.randint(3, 8)
        tokens = random_tokens(tokenizer, tongue, n_tokens)
        difficulty = random.uniform(0.85, 1.00)

        name = TONGUE_FULL_NAMES[tongue]

        records.append(
            BabbleRecord(
                system=_system_prompt(tongue, difficulty),
                user=f"What tongue? {' '.join(tokens)}",
                assistant=f"{tongue.upper()} ({name})",
                tongue=tongue,
                difficulty=difficulty,
                tier="naming",
                tags=["phase0", "naming", f"tongue-{tongue.upper()}"],
            )
        )
    return records


# ---------------------------------------------------------------------------
# Tier → Layer/Axiom mapping
# ---------------------------------------------------------------------------

# Phase 0 progressively activates more layers and axioms as difficulty rises.
# Early tiers: just L1 (input) + A5 (composition).
# Later tiers: L1-L3 (weighted transform) + A1 (unitarity) + A2 (locality).

TIER_LAYERS = {
    "pure_noise": [1],
    "echo": [1, 2],
    "pattern": [1, 2, 3],
    "sorting": [1, 2, 3],
    "completion": [1, 2, 3, 4],
    "translation": [1, 2, 3, 4],
    "naming": [1, 2, 3, 4, 5],
}

TIER_AXIOMS = {
    "pure_noise": ["A5_composition"],
    "echo": ["A5_composition"],
    "pattern": ["A5_composition", "A4_symmetry"],
    "sorting": ["A5_composition", "A2_locality"],
    "completion": ["A5_composition", "A3_causality"],
    "translation": ["A5_composition", "A4_symmetry", "A2_locality"],
    "naming": ["A5_composition", "A4_symmetry", "A2_locality", "A1_unitarity"],
}


def _tier_layers(tier: str) -> list:
    return TIER_LAYERS.get(tier, [1, 2, 3])


def _tier_axioms(tier: str) -> list:
    return TIER_AXIOMS.get(tier, ["A5_composition"])


# ---------------------------------------------------------------------------
# SFT record formatting
# ---------------------------------------------------------------------------


def to_sft_record(rec: BabbleRecord) -> dict:
    """Convert a BabbleRecord to SFT JSONL format (matching Phase 1 schema)."""
    messages = [
        {"role": "system", "content": rec.system},
        {"role": "user", "content": rec.user},
        {"role": "assistant", "content": rec.assistant},
    ]

    # Compute tongue weights (dominant tongue gets 1.0, others get distance-based weight)
    tongue_weights = {}
    for t in TONGUE_CODES:
        if t == rec.tongue:
            tongue_weights[t.upper()] = 1.0
        else:
            # Distance in compass bearings (0-3 steps away)
            idx_a = TONGUE_CODES.index(rec.tongue)
            idx_b = TONGUE_CODES.index(t)
            dist = min(abs(idx_a - idx_b), 6 - abs(idx_a - idx_b))
            tongue_weights[t.upper()] = round(max(0, 1.0 - dist * 0.25), 3)

    # Source hash for dedup
    content = rec.user + rec.assistant
    source_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

    return {
        "messages": messages,
        "tongue_weights": tongue_weights,
        "dominant_tongue": rec.tongue.upper(),
        "layers": _tier_layers(rec.tier),
        "axioms": _tier_axioms(rec.tier),
        "difficulty": round(rec.difficulty, 3),
        "augmentation": f"tpdff-{rec.tier}",
        "tags": rec.tags,
        "source_hash": source_hash,
        "curriculum_phase": 0,
        "tpdff_weights": {
            "P1_smooth": round(P1_WEIGHT, 3),
            "P2_pattern": round(P2_WEIGHT, 3),
            "P3_bind": round(P3_WEIGHT, 3),
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    random.seed(SEED)
    tokenizer = build_tokenizer()

    output_dir = Path("training-data/sft")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "phase0_baby_babble_sft.jsonl"

    print("=" * 70)
    print("Phase 0: Baby Babble Generator — TPDFF")
    print("=" * 70)
    print(f"Phi weights: P1={P1_WEIGHT:.3f}, P2={P2_WEIGHT:.3f}, P3={P3_WEIGHT:.3f}")
    print(f"Tongues: {', '.join(TONGUE_FULL_NAMES.values())}")
    print()

    all_records: List[BabbleRecord] = []

    generators = [
        ("pure_noise", gen_pure_noise),
        ("echo", gen_echo),
        ("pattern", gen_pattern),
        ("sorting", gen_sorting),
        ("completion", gen_completion),
        ("translation", gen_translation),
        ("naming", gen_naming),
    ]

    for tier_name, gen_fn in generators:
        count = RECORDS_PER_TIER[tier_name]
        print(f"  Generating {tier_name:.<20s} {count:>6,d} records ... ", end="", flush=True)
        records = gen_fn(tokenizer, count)
        all_records.extend(records)
        print(f"done ({len(records):,d})")

    # Shuffle all records (curriculum mixing)
    random.shuffle(all_records)

    # Write JSONL
    print(f"\nWriting {len(all_records):,d} records to {output_path} ... ", end="", flush=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(to_sft_record(rec), ensure_ascii=False) + "\n")
    print("done")

    # Stats
    file_size = output_path.stat().st_size
    tongue_dist = {}
    tier_dist = {}
    for rec in all_records:
        tongue_dist[rec.tongue] = tongue_dist.get(rec.tongue, 0) + 1
        tier_dist[rec.tier] = tier_dist.get(rec.tier, 0) + 1

    print(f"\n{'=' * 70}")
    print(f"PHASE 0 COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Total records:  {len(all_records):>10,d}")
    print(f"  File size:      {file_size:>10,d} bytes ({file_size / 1024 / 1024:.1f} MB)")
    print(f"\n  Tongue distribution:")
    for t in TONGUE_CODES:
        name = TONGUE_FULL_NAMES[t]
        ct = tongue_dist.get(t, 0)
        pct = ct / len(all_records) * 100
        bar = "#" * int(pct / 2)
        print(f"    {t.upper()} ({name:.<15s}) {ct:>5,d} ({pct:5.1f}%) {bar}")
    print(f"\n  Tier distribution:")
    for tier_name, _ in generators:
        ct = tier_dist.get(tier_name, 0)
        pct = ct / len(all_records) * 100
        print(f"    {tier_name:.<20s} {ct:>5,d} ({pct:5.1f}%)")
    print(f"\n  Difficulty range: {min(r.difficulty for r in all_records):.3f} — {max(r.difficulty for r in all_records):.3f}")
    print(f"  TPDFF weights:   P1={P1_WEIGHT:.3f} (smooth), P2={P2_WEIGHT:.3f} (pattern), P3={P3_WEIGHT:.3f} (bind)")


if __name__ == "__main__":
    main()
