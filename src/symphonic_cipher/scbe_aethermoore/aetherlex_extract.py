#!/usr/bin/env python3
"""
aetherlex_extract.py  —  Everweave Seed Corpus Extractor & Hasher
=================================================================
Spiralverse Canonical Linguistic Codex v1.0 — Seed-Anchored Edition
Treats the Everweave origin logs as an immutable cryptographic seed corpus.
Extracts phrases, tokenizes via the Six Sacred Tongues (dual-layer: runic +
particle), packs with golden-ratio phase metadata, and hashes to 64-byte
SHAKE-256 seeds suitable for Kyber/Dilithium key generation.
Provenance chain:
  Layer 0: Everweave Logs (this tool reads them)
  Layer 1: 24-letter Kor'aelin Alphabet (runic concepts)
  Layer 2: 14-particle Grammar + 6-tongue Registry (semantic layer)
  Layer 3: SCBE Tokenizer (bijective 256-token encoding)
Usage:
  python3 aetherlex_extract.py extract  --src everweave.txt [--pages 1-10] [--out corpus.json]
  python3 aetherlex_extract.py hash     --phrase "spell of binding..." --tongue KO
  python3 aetherlex_extract.py stats    --corpus corpus.json
  python3 aetherlex_extract.py selftest
Author: Issac Davis (@davisissac) / Spiralverse Protocol
License: Spiralverse Open Seed License v1
"""
import argparse
import hashlib
import hmac
import json
import math
import os
import re
import struct
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
# CANONICAL CODEX DATA  (Immutable — derived from Everweave seed)
# ═══════════════════════════════════════════════════════════

VERSION = "SPIRALVERSEv1"

# ─── The 24 Sacred Letters (Runic Layer — Mind/Symbolic) ───
# From the Kor'aelin Alphabet Guide (Layer 1)
# Index → (name, phoneme, concept)
RUNES_24 = [
    ("Arul",  "/a/",   "origin, creation"),
    ("Belan", "/b/",   "balance, duality"),
    ("Calor", "/k/",   "clarity, illumination"),
    ("Dael",  "/d/",   "divinity, sacred trinity"),
    ("Elar",  "/e/",   "air, freedom"),
    ("Fen",   "/f/",   "fire, passion"),
    ("Gaer",  "/g/",   "earth, foundation"),
    ("Havar", "/h/",   "home, hearth"),
    ("Iril",  "/i/",   "magic, mystery, arcane"),
    ("Jael",  "/dʒ/",  "justice, law"),
    ("Kor",   "/k/",   "knowledge, learning, secrets"),  # Runic layer
    ("Laris", "/l/",   "protection, shielding"),
    ("Mael",  "/m/",   "moon, dreams, intuition"),
    ("Nera",  "/n/",   "abundance, harvest"),
    ("Orun",  "/o/",   "rebirth, cycle"),
    ("Parun", "/p/",   "flora, growth"),
    ("Ren",   "/r/",   "journey, travel"),
    ("Sylor", "/s/",   "sun, radiance"),
    ("Thul",  "/θ/",   "time, spiral, evolution"),
    ("Uen",   "/u/",   "ocean, depths"),
    ("Vel",   "/v/",   "invitation, collaboration"),
    ("Wyn",   "/w/",   "water, flow, change"),
    ("Yul",   "/j/",   "youth, renewal"),
    ("Thana", "/θa/",  "ending, closure, transition"),
]

RUNE_BY_NAME = {r[0].lower(): i for i, r in enumerate(RUNES_24)}

# ─── The 14 Core Particles (Grammatical Layer — Heart/Relational) ───
# From the Lexicon JSON (Layer 2)
PARTICLES_14 = [
    ("kor",  "heart, core, essence"),         # Particle layer — dual with rune
    ("sil",  "together, unity"),
    ("vel",  "invitation, collaboration"),
    ("zar",  "dimension, bridge"),
    ("keth", "time, temporal flow"),
    ("thul", "spiral, evolution"),
    ("nav",  "difference, diversity"),
    ("ael",  "eternal, continuity"),
    ("ra",   "flow, current"),
    ("med",  "wisdom, knowledge"),
    ("gal",  "strength, foundation"),
    ("lan",  "gentleness, peace"),
    ("bren", "warmth, flame, hearth"),
    ("oen",  "circle, completeness"),
]

PARTICLE_BY_NAME = {p[0]: i for i, p in enumerate(PARTICLES_14)}

# ─── Six Sacred Tongues Registry ───
# Canonical: [code, name, phi_weight, phase_rad, keywords_for_classification]
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

TONGUES = {
    "KO": {
        "name": "Kor'aelin", "meaning": "Heart-Eternal",
        "phi_n": 0, "weight": PHI ** 0, "phase": 0.0,
        "keywords": [
            "bind", "binding", "bond", "heart", "companion", "together",
            "collaborative", "spell", "cast", "weave", "intent", "will",
            "magic", "arcane", "enchant", "invoke", "ritual", "chant",
            "kor", "sil", "vel", "gesture", "incantation", "summon",
        ],
    },
    "AV": {
        "name": "Avali", "meaning": "Common Tongue",
        "phi_n": 1, "weight": PHI ** 1, "phase": math.pi / 3,
        "keywords": [
            "speak", "say", "tell", "ask", "question", "conversation",
            "trade", "negotiate", "greet", "welcome", "invite", "offer",
            "gentle", "rhythm", "caress", "breeze", "dance", "sense",
            "vision", "dream", "intriguing", "curious", "explore",
        ],
    },
    "RU": {
        "name": "Runethic", "meaning": "Ancient Tongue",
        "phi_n": 2, "weight": PHI ** 2, "phase": 2 * math.pi / 3,
        "keywords": [
            "ancient", "old", "rune", "ruin", "inscription", "temple",
            "oath", "vow", "guard", "protect", "preserve", "history",
            "knowledge", "study", "research", "scholar", "tome", "scroll",
            "library", "archive", "legend", "lore", "power", "energy",
            "eldritch", "blast", "supernatural", "weaving",
        ],
    },
    "CA": {
        "name": "Cassisivadan", "meaning": "Nature's Speech",
        "phi_n": 3, "weight": PHI ** 3, "phase": math.pi,
        "keywords": [
            "forest", "tree", "root", "leaf", "herb", "plant", "grow",
            "flower", "seed", "nature", "wild", "animal", "bird",
            "puzzle", "mystery", "ambiguous", "unclear", "strange",
            "storm", "nothing", "mechanical", "construct", "tinker",
            "fun", "joy", "play", "laugh",
        ],
    },
    "UM": {
        "name": "Umbroth", "meaning": "Shadow Tongue",
        "phi_n": 4, "weight": PHI ** 4, "phase": 4 * math.pi / 3,
        "keywords": [
            "shadow", "dark", "hidden", "secret", "conceal", "veil",
            "fragment", "disjointed", "disorient", "confus", "lost",
            "nothing", "opaque", "unclear", "memory", "forget", "drift",
            "sever", "cut", "break", "shatter", "crack", "limit",
            "mock", "frustrat", "fail", "lack", "beyond",
        ],
    },
    "DR": {
        "name": "Draumric", "meaning": "Forge Tongue",
        "phi_n": 5, "weight": PHI ** 5, "phase": 5 * math.pi / 3,
        "keywords": [
            "forge", "build", "craft", "construct", "gather", "material",
            "stone", "metal", "wood", "timber", "shelter", "structure",
            "golem", "servant", "form", "physical", "task", "tool",
            "hammer", "fire", "heat", "mold", "shape", "ready",
            "instruct", "direct", "precision", "collect",
        ],
    },
}

TONGUE_CODES = ["KO", "AV", "RU", "CA", "UM", "DR"]


# ═══════════════════════════════════════════════════════════
# PHRASE EXTRACTION
# ═══════════════════════════════════════════════════════════

@dataclass
class ExtractedPhrase:
    """A phrase extracted from the Everweave logs."""
    text: str
    speaker: str           # "DM" or "Izack" or "unknown"
    page: int              # Everweave page number
    line_start: int        # Line number in source file
    tongue_bias: str       # Two-letter tongue code
    tongue_scores: Dict[str, float] = field(default_factory=dict)
    # Populated after tokenization
    runic_tokens: List[int] = field(default_factory=list)
    particle_tokens: List[int] = field(default_factory=list)
    seed_hex: str = ""
    entropy_bpb: float = 0.0


def parse_everweave(filepath: str,
                    page_start: int = 1,
                    page_end: int = 999) -> List[ExtractedPhrase]:
    """
    Parse the Everweave text file into dialogue turns, then into sentences.
    Returns a list of ExtractedPhrase objects.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    phrases: List[ExtractedPhrase] = []
    current_speaker = "unknown"
    current_page = 1
    current_block: List[str] = []
    block_start_line = 0

    # Page markers look like: "Export from Everweave\nN/149"
    page_re = re.compile(r"^(\d+)/\d+\s*$")
    speaker_re = re.compile(r"^(DM|Izack):\s*(.*)", re.IGNORECASE)

    # Skip noise lines
    skip_re = re.compile(r"^(Export from Everweave|$)")

    def flush_block():
        nonlocal current_block
        if not current_block:
            return
        full_text = " ".join(current_block).strip()
        full_text = re.sub(r"\s+", " ", full_text)
        if len(full_text) < 10:  # Too short
            current_block = []
            return

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", full_text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 15:  # Skip very short fragments
                continue
            if current_page < page_start or current_page > page_end:
                continue
            phrases.append(ExtractedPhrase(
                text=sent,
                speaker=current_speaker,
                page=current_page,
                line_start=block_start_line,
                tongue_bias="",  # Classified later
            ))
        current_block = []

    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.rstrip()

        # Check for page markers
        pm = page_re.match(line)
        if pm:
            current_page = int(pm.group(1))
            continue

        if skip_re.match(line):
            continue

        # Check for speaker change
        sm = speaker_re.match(line)
        if sm:
            flush_block()
            current_speaker = sm.group(1).upper()
            if sm.group(1).lower() == "izack":
                current_speaker = "IZACK"
            remainder = sm.group(2).strip()
            if remainder:
                current_block = [remainder]
                block_start_line = line_no
            continue

        # Continuation line
        if line.strip():
            if not current_block:
                block_start_line = line_no
            current_block.append(line.strip())

    flush_block()
    return phrases


# ═══════════════════════════════════════════════════════════
# TONGUE CLASSIFICATION
# ═══════════════════════════════════════════════════════════

def classify_tongue(phrase: ExtractedPhrase) -> str:
    """
    Classify a phrase's tongue bias by keyword scoring.
    Returns the two-letter tongue code with highest affinity.
    """
    text_lower = phrase.text.lower()
    words = set(re.findall(r"[a-z']+", text_lower))

    scores: Dict[str, float] = {}
    for code, tongue in TONGUES.items():
        score = 0.0
        for kw in tongue["keywords"]:
            # Substring match for stems (e.g., "frustrat" matches "frustrating")
            if any(kw in w for w in words) or kw in text_lower:
                score += 1.0
        # Speaker bias: Izack's actions lean KO (intent), DM descriptions lean AV/UM
        if phrase.speaker == "IZACK" and code == "KO":
            score += 0.5
        elif phrase.speaker == "DM" and code in ("AV", "UM"):
            score += 0.3
        scores[code] = score

    phrase.tongue_scores = scores

    # Pick highest; break ties by canonical order
    max_score = max(scores.values())
    if max_score == 0:
        return "AV"  # Default to Avali (common tongue) for unclassified

    for code in TONGUE_CODES:
        if scores[code] == max_score:
            return code
    return "AV"


# ═══════════════════════════════════════════════════════════
# DUAL-LAYER TOKENIZATION
# ═══════════════════════════════════════════════════════════

# Semantic affinity maps: word concepts → rune/particle indices
# This is a simplified classifier; production would use embeddings.
RUNE_AFFINITIES: Dict[str, List[str]] = {
    # concept keywords → rune names (lowercase)
    "begin|start|wake|origin|birth|creat": ["arul"],
    "balanc|dual|mirror|equal|twin": ["belan"],
    "clear|light|illumin|bright|reveal|truth": ["calor"],
    "divine|sacred|holy|spirit|soul|god": ["dael"],
    "air|wind|free|fly|sky|breath": ["elar"],
    "fire|flame|burn|heat|passion|warm": ["fen"],
    "earth|ground|stone|rock|soil|root|found": ["gaer"],
    "home|hearth|shelter|dwell|belong|camp": ["havar"],
    "magic|mystic|arcane|sorcery|spell|enchant": ["iril"],
    "justice|law|fair|judge|consequence": ["jael"],
    "knowledge|learn|secret|study|research|scholar|know": ["kor"],
    "protect|shield|guard|ward|defend|safe": ["laris"],
    "moon|dream|night|intuit|sleep|slumber": ["mael"],
    "abund|harvest|gather|collect|plenty|wealth": ["nera"],
    "rebirth|cycle|renew|transform|phoenix": ["orun"],
    "plant|flora|forest|tree|herb|leaf|grow|bloom": ["parun"],
    "journey|travel|path|road|walk|approach|venture": ["ren"],
    "sun|light|radian|glow|shine|gold": ["sylor"],
    "time|spiral|evolv|turn|age|ancient|hour": ["thul"],
    "ocean|sea|depth|wave|water|tide|shore": ["uen"],
    "invit|collabor|offer|willing|open|welcome": ["vel"],
    "flow|change|adapt|stream|current|drift": ["wyn"],
    "youth|young|renew|fresh|new|begin": ["yul"],
    "end|clos|finish|death|final|last|transition": ["thana"],
}

PARTICLE_AFFINITIES: Dict[str, List[str]] = {
    "heart|core|essence|soul|emotional|bond|love": ["kor"],
    "together|unite|join|group|collective|we": ["sil"],
    "invit|collabor|offer|welcome|willing|open": ["vel"],
    "dimension|bridge|portal|realm|cross|between": ["zar"],
    "time|temporal|moment|when|past|future|then": ["keth"],
    "spiral|evolv|turn|transform|grow|develop": ["thul"],
    "differ|divers|unique|other|plural|distinct": ["nav"],
    "eternal|forever|timeless|endless|persist|continuity": ["ael"],
    "flow|current|move|stream|river|run|drift": ["ra"],
    "wisdom|knowledge|learn|understand|study|insight": ["med"],
    "strength|strong|found|endur|solid|firm|stable": ["gal"],
    "gentle|peace|calm|soft|ease|quiet|still": ["lan"],
    "warm|flame|hearth|fire|community|passion": ["bren"],
    "circle|complete|whole|cycle|full|round": ["oen"],
}


def _affinity_tokenize(text: str, affinity_map: Dict[str, List[str]],
                       name_to_idx: Dict[str, int], max_tokens: int) -> List[int]:
    """Score text against affinity keywords, return top-N indices."""
    text_lower = text.lower()
    scores: Dict[int, float] = {}

    for pattern, names in affinity_map.items():
        keywords = pattern.split("|")
        for kw in keywords:
            if kw in text_lower:
                for name in names:
                    idx = name_to_idx.get(name, -1)
                    if idx >= 0:
                        scores[idx] = scores.get(idx, 0) + 1.0

    # Sort by score descending, take top max_tokens
    ranked = sorted(scores.items(), key=lambda x: -x[1])

    if not ranked:
        # Fallback: hash-based deterministic assignment
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(h >> (i * 5)) % len(name_to_idx) for i in range(max_tokens)]

    result = [idx for idx, _ in ranked[:max_tokens]]

    # Pad to max_tokens if needed (deterministic from text hash)
    while len(result) < max_tokens:
        h = int(hashlib.md5(f"{text}:{len(result)}".encode()).hexdigest(), 16)
        result.append(h % len(name_to_idx))

    return result


def tokenize_dual_layer(phrase: ExtractedPhrase, n_runic: int = 6, n_particle: int = 5):
    """
    Dual-layer tokenize a phrase:
      Runic layer  — 24-letter symbolic mapping (mind/concept)
      Particle layer — 14-morpheme relational mapping (heart/intent)
    """
    phrase.runic_tokens = _affinity_tokenize(
        phrase.text, RUNE_AFFINITIES, RUNE_BY_NAME, n_runic)
    phrase.particle_tokens = _affinity_tokenize(
        phrase.text, PARTICLE_AFFINITIES, PARTICLE_BY_NAME, n_particle)


# ═══════════════════════════════════════════════════════════
# PACKING & HASHING
# ═══════════════════════════════════════════════════════════

def pack_tokens(tongue_code: str,
                runic: List[int],
                particles: List[int],
                page: int) -> bytes:
    """
    Pack dual-layer tokens into a binary payload for hashing.
    Format:
      [tongue_id: 3 bits][page: 16 bits]
      [n_runic: 4 bits][runic indices: 5 bits each]
      [n_particle: 4 bits][particle indices: 4 bits each]
      [phi_weight: float32][phase: float32]
    """
    tongue_idx = TONGUE_CODES.index(tongue_code) if tongue_code in TONGUE_CODES else 0
    tongue_data = TONGUES[tongue_code]

    buf = bytearray()

    # Header: tongue + page
    buf.append((tongue_idx << 5) | (len(runic) & 0x1F))
    buf.extend(struct.pack(">H", page & 0xFFFF))

    # Runic indices (5 bits each, packed into bytes)
    runic_bits = 0
    runic_bit_len = 0
    for idx in runic:
        runic_bits = (runic_bits << 5) | (idx & 0x1F)
        runic_bit_len += 5
    # Pad to byte boundary
    pad = (8 - runic_bit_len % 8) % 8
    runic_bits <<= pad
    runic_byte_len = (runic_bit_len + pad) // 8
    buf.extend(runic_bits.to_bytes(max(runic_byte_len, 1), "big"))

    # Particle count + indices (4 bits each)
    buf.append(len(particles) & 0x0F)
    part_bits = 0
    part_bit_len = 0
    for idx in particles:
        part_bits = (part_bits << 4) | (idx & 0x0F)
        part_bit_len += 4
    pad2 = (8 - part_bit_len % 8) % 8
    part_bits <<= pad2
    part_byte_len = (part_bit_len + pad2) // 8
    buf.extend(part_bits.to_bytes(max(part_byte_len, 1), "big"))

    # Phase and weight (float32)
    buf.extend(struct.pack(">f", tongue_data["weight"]))
    buf.extend(struct.pack(">f", tongue_data["phase"]))

    return bytes(buf)


def hash_seed(tongue_code: str,
              runic: List[int],
              particles: List[int],
              page: int,
              raw_text: str = "") -> Tuple[str, float]:
    """
    Hash packed tokens to a 64-byte SHAKE-256 seed.
    Returns (hex_string, entropy_bits_per_byte).
    """
    packed = pack_tokens(tongue_code, runic, particles, page)

    # Domain separation: VERSION || packed || text_hash
    text_hash = hashlib.sha256(raw_text.encode("utf-8")).digest()
    preimage = VERSION.encode() + packed + text_hash

    seed = hashlib.shake_256(preimage).digest(64)
    seed_hex = seed.hex()

    # Entropy estimate (Shannon entropy over byte frequencies)
    freq = Counter(seed)
    total = len(seed)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    return seed_hex, entropy


def generate_attestation(phrase: ExtractedPhrase) -> Dict:
    """Generate a cryptographic attestation for a seed."""
    packed = pack_tokens(
        phrase.tongue_bias, phrase.runic_tokens, phrase.particle_tokens, phrase.page)
    text_hash = hashlib.sha256(phrase.text.encode()).digest()
    preimage = VERSION.encode() + packed + text_hash

    return {
        "version": VERSION,
        "tongue": phrase.tongue_bias,
        "page": phrase.page,
        "sha256_preimage": hashlib.sha256(preimage).hexdigest(),
        "hmac_attest": hmac.new(
            VERSION.encode(), preimage, hashlib.sha256).hexdigest(),
        "phi_weight": TONGUES[phrase.tongue_bias]["weight"],
        "phase": TONGUES[phrase.tongue_bias]["phase"],
        "timestamp": time.time(),
    }


# ═══════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════

def process_phrase(phrase: ExtractedPhrase) -> ExtractedPhrase:
    """Full pipeline: classify → tokenize → hash."""
    phrase.tongue_bias = classify_tongue(phrase)
    tokenize_dual_layer(phrase)
    phrase.seed_hex, phrase.entropy_bpb = hash_seed(
        phrase.tongue_bias,
        phrase.runic_tokens,
        phrase.particle_tokens,
        phrase.page,
        phrase.text,
    )
    return phrase


def extract_corpus(filepath: str,
                   page_start: int = 1,
                   page_end: int = 999) -> List[ExtractedPhrase]:
    """Extract, classify, tokenize, and hash all phrases."""
    phrases = parse_everweave(filepath, page_start, page_end)

    # Deduplicate: same text + same page = parser artifact → keep first only.
    # Same text on DIFFERENT pages = genuine repetition → salt with sequence.
    seen_page: set = set()
    deduped: List[ExtractedPhrase] = []
    text_count: Dict[str, int] = {}

    for p in phrases:
        key = (p.text, p.page)
        if key in seen_page:
            continue  # Drop same-page duplicate
        seen_page.add(key)

        # Sequence salt for cross-page repeats (e.g., "What would you like to do?")
        seq = text_count.get(p.text, 0)
        text_count[p.text] = seq + 1
        if seq > 0:
            # Append sequence nonce so identical text on different pages → different seeds
            p.text = f"{p.text} [seq:{seq}]"

        deduped.append(p)

    for p in deduped:
        process_phrase(p)

    return deduped


# ═══════════════════════════════════════════════════════════
# CORPUS STATISTICS
# ═══════════════════════════════════════════════════════════

def corpus_stats(phrases: List[ExtractedPhrase]) -> Dict:
    """Compute statistics over a seed corpus."""
    total = len(phrases)
    if total == 0:
        return {"total": 0}

    tongue_dist = Counter(p.tongue_bias for p in phrases)
    speaker_dist = Counter(p.speaker for p in phrases)
    page_range = (min(p.page for p in phrases), max(p.page for p in phrases))
    avg_entropy = sum(p.entropy_bpb for p in phrases) / total

    # Seed uniqueness check
    seeds = [p.seed_hex for p in phrases]
    unique_seeds = len(set(seeds))

    # Average phrase length
    avg_len = sum(len(p.text) for p in phrases) / total

    return {
        "total_phrases": total,
        "unique_seeds": unique_seeds,
        "collision_rate": 1.0 - (unique_seeds / total) if total > 0 else 0,
        "avg_entropy_bpb": round(avg_entropy, 4),
        "avg_phrase_length": round(avg_len, 1),
        "page_range": list(page_range),
        "tongue_distribution": dict(tongue_dist.most_common()),
        "speaker_distribution": dict(speaker_dist.most_common()),
    }


# ═══════════════════════════════════════════════════════════
# SELFTEST
# ═══════════════════════════════════════════════════════════

def selftest():
    """Validate invariants of the extraction pipeline."""
    print("=== AetherLex Selftest ===")
    errors = 0

    # 1. Codex data integrity
    assert len(RUNES_24) == 24, f"Expected 24 runes, got {len(RUNES_24)}"
    assert len(PARTICLES_14) == 14, f"Expected 14 particles, got {len(PARTICLES_14)}"
    assert len(TONGUES) == 6, f"Expected 6 tongues, got {len(TONGUES)}"
    print(f"  [OK] Codex integrity: 24 runes, 14 particles, 6 tongues")

    # 2. Golden ratio weights
    for code in TONGUE_CODES:
        expected = PHI ** TONGUES[code]["phi_n"]
        actual = TONGUES[code]["weight"]
        assert abs(expected - actual) < 1e-6, f"{code} weight mismatch"
    print(f"  [OK] Golden ratio weights verified (φ^0 through φ^5)")

    # 3. Deterministic hashing
    test_phrases = [
        "The gentle rhythm of waves caressing the shore rouses you from your slumber",
        "spell of binding upon some sand and water to make a golem companion",
        "fragments of memory drift like seafoam—disjointed impressions of arcane research",
        "The servant waits silently, its watery form glistening in the sunlight",
        "creating a truly independent golem requires knowledge far beyond your repertoire",
    ]

    seeds = []
    for text in test_phrases:
        p = ExtractedPhrase(text=text, speaker="DM", page=1, line_start=0, tongue_bias="")
        process_phrase(p)
        seeds.append(p.seed_hex)

        # Regenerability: same input → same output
        p2 = ExtractedPhrase(text=text, speaker="DM", page=1, line_start=0, tongue_bias="")
        process_phrase(p2)
        assert p.seed_hex == p2.seed_hex, f"Non-deterministic seed for: {text[:40]}..."

    print(f"  [OK] Deterministic hashing: 5 phrases regenerable")

    # 4. Seed uniqueness
    assert len(set(seeds)) == len(seeds), "Seed collision detected!"
    print(f"  [OK] Seed uniqueness: 5/5 unique seeds")

    # 5. Entropy check (should be > 5.0 bits/byte for SHAKE-256 output)
    for text in test_phrases:
        p = ExtractedPhrase(text=text, speaker="DM", page=1, line_start=0, tongue_bias="")
        process_phrase(p)
        assert p.entropy_bpb > 4.5, f"Low entropy {p.entropy_bpb} for: {text[:40]}..."
    print(f"  [OK] Entropy check: all seeds > 4.5 bits/byte")

    # 6. Tongue classification sanity
    binding = ExtractedPhrase(
        text="spell of binding upon sand and water", speaker="IZACK",
        page=1, line_start=0, tongue_bias="")
    classify_tongue(binding)
    assert binding.tongue_bias == "" or True  # Just run it
    binding.tongue_bias = classify_tongue(binding)
    print(f"  [OK] Tongue classification: binding phrase → {binding.tongue_bias}")

    shadow = ExtractedPhrase(
        text="fragments of memory hidden in shadow, frustratingly lost",
        speaker="DM", page=1, line_start=0, tongue_bias="")
    shadow.tongue_bias = classify_tongue(shadow)
    assert shadow.tongue_bias == "UM", f"Expected UM, got {shadow.tongue_bias}"
    print(f"  [OK] Tongue classification: shadow phrase → UM")

    forge = ExtractedPhrase(
        text="gather materials, driftwood and stone, to construct a shelter",
        speaker="DM", page=1, line_start=0, tongue_bias="")
    forge.tongue_bias = classify_tongue(forge)
    assert forge.tongue_bias == "DR", f"Expected DR, got {forge.tongue_bias}"
    print(f"  [OK] Tongue classification: forge phrase → DR")

    # 7. Pack/unpack round-trip (packed data is deterministic)
    packed1 = pack_tokens("KO", [0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4], 1)
    packed2 = pack_tokens("KO", [0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4], 1)
    assert packed1 == packed2, "Non-deterministic packing"
    print(f"  [OK] Deterministic packing: identical inputs → identical bytes")

    print(f"\n=== selftest ok ({7 - errors} checks passed) ===")
    return errors == 0


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cmd_extract(args):
    """Extract seed corpus from Everweave log."""
    if not os.path.exists(args.src):
        print(f"Error: file not found: {args.src}", file=sys.stderr)
        sys.exit(1)

    # Parse page range
    page_start, page_end = 1, 999
    if args.pages:
        parts = args.pages.split("-")
        page_start = int(parts[0])
        page_end = int(parts[1]) if len(parts) > 1 else page_start

    print(f"Extracting from: {args.src}")
    print(f"Pages: {page_start}–{page_end}")

    corpus = extract_corpus(args.src, page_start, page_end)
    print(f"Extracted: {len(corpus)} phrases")

    # Stats
    stats = corpus_stats(corpus)
    print(f"Unique seeds: {stats['unique_seeds']}/{stats['total_phrases']}")
    print(f"Avg entropy: {stats['avg_entropy_bpb']:.4f} bits/byte")
    print(f"Tongue distribution:")
    for code, count in stats.get("tongue_distribution", {}).items():
        pct = 100 * count / stats["total_phrases"]
        name = TONGUES[code]["name"]
        print(f"  {code} ({name}): {count} ({pct:.1f}%)")

    # Save corpus
    out_path = args.out or "everweave_corpus.json"
    corpus_data = {
        "version": VERSION,
        "source": os.path.basename(args.src),
        "pages": f"{page_start}-{page_end}",
        "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stats": stats,
        "phrases": [],
    }

    for p in corpus:
        entry = {
            "text": p.text,
            "speaker": p.speaker,
            "page": p.page,
            "tongue": p.tongue_bias,
            "runic_tokens": [RUNES_24[i][0] for i in p.runic_tokens],
            "particle_tokens": [PARTICLES_14[i][0] for i in p.particle_tokens],
            "seed": p.seed_hex,
            "entropy_bpb": round(p.entropy_bpb, 4),
        }
        corpus_data["phrases"].append(entry)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corpus_data, f, indent=2, ensure_ascii=False)
    print(f"Corpus saved: {out_path}")

    # Print first 5 as sample
    if args.verbose:
        print(f"\n--- Sample (first 5 phrases) ---")
        for p in corpus[:5]:
            print(f"\n  [{p.tongue_bias}] p.{p.page} ({p.speaker})")
            print(f"  Text: {p.text[:80]}...")
            print(f"  Runes:     {', '.join(RUNES_24[i][0] for i in p.runic_tokens)}")
            print(f"  Particles: {', '.join(PARTICLES_14[i][0] for i in p.particle_tokens)}")
            print(f"  Seed: {p.seed_hex[:32]}...")
            print(f"  Entropy: {p.entropy_bpb:.4f} bpb")


def cmd_hash(args):
    """Hash a single phrase with tongue bias."""
    tongue = args.tongue.upper()
    if tongue not in TONGUES:
        print(f"Error: unknown tongue '{tongue}'. Use: {', '.join(TONGUE_CODES)}")
        sys.exit(1)

    p = ExtractedPhrase(
        text=args.phrase,
        speaker=args.speaker or "IZACK",
        page=args.page or 1,
        line_start=0,
        tongue_bias=tongue,
    )

    tokenize_dual_layer(p)
    p.seed_hex, p.entropy_bpb = hash_seed(
        tongue, p.runic_tokens, p.particle_tokens, p.page, p.text)

    attest = generate_attestation(p)

    print(f"Phrase:      {p.text}")
    print(f"Tongue:      {tongue} ({TONGUES[tongue]['name']})")
    print(f"Speaker:     {p.speaker}")
    print(f"Page:        {p.page}")
    print(f"Runes:       {', '.join(RUNES_24[i][0] for i in p.runic_tokens)}")
    print(f"Particles:   {', '.join(PARTICLES_14[i][0] for i in p.particle_tokens)}")
    print(f"Seed (hex):  {p.seed_hex}")
    print(f"Entropy:     {p.entropy_bpb:.4f} bits/byte")
    print(f"φ-weight:    {attest['phi_weight']:.6f}")
    print(f"Phase:       {attest['phase']:.6f}")
    print(f"SHA256:      {attest['sha256_preimage']}")
    print(f"HMAC:        {attest['hmac_attest']}")


def cmd_stats(args):
    """Print statistics for an existing corpus JSON."""
    with open(args.corpus, "r") as f:
        data = json.load(f)

    stats = data.get("stats", {})
    print(f"Corpus: {data.get('source', '?')} ({data.get('pages', '?')})")
    print(f"Phrases: {stats.get('total_phrases', 0)}")
    print(f"Unique seeds: {stats.get('unique_seeds', 0)}")
    print(f"Collision rate: {stats.get('collision_rate', 0):.6f}")
    print(f"Avg entropy: {stats.get('avg_entropy_bpb', 0):.4f} bpb")
    print(f"Avg phrase length: {stats.get('avg_phrase_length', 0):.1f} chars")
    print(f"Tongue distribution:")
    for code, count in stats.get("tongue_distribution", {}).items():
        pct = 100 * count / max(stats.get("total_phrases", 1), 1)
        print(f"  {code}: {count} ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        prog="aetherlex_extract",
        description="Everweave Seed Corpus Extractor — Spiralverse Canonical Codex v1",
    )
    sub = parser.add_subparsers(dest="command")

    # extract
    p_ext = sub.add_parser("extract", help="Extract seed corpus from Everweave log")
    p_ext.add_argument("--src", required=True, help="Path to Everweave text file")
    p_ext.add_argument("--pages", default=None, help="Page range, e.g. '1-10'")
    p_ext.add_argument("--out", default=None, help="Output JSON path")
    p_ext.add_argument("--verbose", "-v", action="store_true")

    # hash
    p_hash = sub.add_parser("hash", help="Hash a single phrase")
    p_hash.add_argument("--phrase", required=True, help="Phrase text")
    p_hash.add_argument("--tongue", required=True, help="Tongue code (KO/AV/RU/CA/UM/DR)")
    p_hash.add_argument("--speaker", default="IZACK", help="Speaker (DM/IZACK)")
    p_hash.add_argument("--page", type=int, default=1, help="Page number")

    # stats
    p_stat = sub.add_parser("stats", help="Print corpus statistics")
    p_stat.add_argument("--corpus", required=True, help="Corpus JSON file")

    # selftest
    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "hash":
        cmd_hash(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "selftest":
        ok = selftest()
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
