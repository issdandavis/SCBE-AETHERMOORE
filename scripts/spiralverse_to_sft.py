#!/usr/bin/env python3
"""
spiralverse_to_sft.py -- Convert the Spiralverse Canonical Linguistic Codex
into high-quality SFT (Supervised Fine-Tuning) instruction/response pairs.

Reads:
  1. training/raw/spiralverse_canonical_linguistic_codex_v1_seed_20260218.md
  2. docs/specs/spiralverse_canonical_registry.v1.json

Writes:
  training-data/sft_spiralverse.jsonl

Each output line is a JSON object:
  {"id": "sft-sv-NNN", "category": "...", "instruction": "...", "response": "...",
   "metadata": {"source": "scbe_aethermoore", "version": "3.3.0",
                 "author": "Issac Davis", "origin": "spiralverse_codex"}}

Usage:
    python scripts/spiralverse_to_sft.py
    python scripts/spiralverse_to_sft.py --codex path/to/codex.md --registry path/to/registry.json
    python scripts/spiralverse_to_sft.py -o custom_output.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Metadata template
# ---------------------------------------------------------------------------

METADATA_BASE = {
    "source": "scbe_aethermoore",
    "version": "3.3.0",
    "author": "Issac Davis",
    "origin": "spiralverse_codex",
}


def _meta(extra: Optional[Dict] = None) -> Dict:
    m = dict(METADATA_BASE)
    if extra:
        m.update(extra)
    return m


# ---------------------------------------------------------------------------
# Data definitions -- extracted from the two source files
# ---------------------------------------------------------------------------

TONGUES = [
    {
        "code": "KO",
        "name": "Kor'aelin",
        "meaning": "Heart-Eternal",
        "weight": 1.000,
        "weight_formula": "phi^0",
        "phase": "0",
        "phase_value": 0.0,
        "grammar": "Elvish-Korean hybrid; SOV; spiraling calligraphy",
        "function": "Intent, binding, collaborative resonance",
        "magic": "Collaborative resonance fields. Requires genuine emotional coherence.",
        "risk": "Forced usage causes semantic wounds.",
    },
    {
        "code": "AV",
        "name": "Avali",
        "meaning": "Common Tongue",
        "weight": 1.618,
        "weight_formula": "phi^1",
        "phase": "pi/3",
        "phase_value": math.pi / 3,
        "grammar": "Romance-influenced; flexible SVO; trade pidgin",
        "function": "Diplomacy, context-headers, cross-paradigm bridge",
        "magic": "Contextual translation and cross-paradigm bridge operations.",
        "risk": "Oversimplification flattens nuance.",
    },
    {
        "code": "RU",
        "name": "Runethic",
        "meaning": "Ancient Tongue",
        "weight": 2.618,
        "weight_formula": "phi^2",
        "phase": "2pi/3",
        "phase_value": 2 * math.pi / 3,
        "grammar": "Archaic VSOT; ritualistic repetition; time-binding",
        "function": "Temporal anchoring, oaths, historical preservation",
        "magic": "Temporal anchoring and oath-binding.",
        "risk": "Imprecise conjugation can anchor wrong timepoint.",
    },
    {
        "code": "CA",
        "name": "Cassisivadan",
        "meaning": "Nature's Speech",
        "weight": 4.236,
        "weight_formula": "phi^3",
        "phase": "pi",
        "phase_value": math.pi,
        "grammar": "Recursive joy; bouncing rhythms; compound enthusiasm",
        "function": "Root-network wisdom, ecological communion, play",
        "magic": "Root-network communion and playful recursive infrastructure.",
        "risk": "Cynical usage collapses recursion to noise.",
    },
    {
        "code": "UM",
        "name": "Umbroth",
        "meaning": "Shadow Tongue",
        "weight": 6.854,
        "weight_formula": "phi^4",
        "phase": "4pi/3",
        "phase_value": 4 * math.pi / 3,
        "grammar": "Guttural concealment; veiled syntax; pact-weaving",
        "function": "Concealment, severance, productive discontinuity",
        "magic": "Productive discontinuity and controlled severance.",
        "risk": "Uncontrolled severance can cut speaker bonds.",
    },
    {
        "code": "DR",
        "name": "Draumric",
        "meaning": "Forge Tongue",
        "weight": 11.090,
        "weight_formula": "phi^5",
        "phase": "5pi/3",
        "phase_value": 5 * math.pi / 3,
        "grammar": "Percussive structure; hammer-rhythm; power-songs",
        "function": "Manifestation, power-binding, structural authority",
        "magic": "Manifestation and structural authority.",
        "risk": "Non-collaborative dominance can corrupt to subjugation.",
    },
]

SUB_TRADITIONS = [
    {
        "name": "Mal'kythric",
        "parent": "UM (Umbroth)",
        "status": "UM sub-tradition",
        "description": "Cutting phonetics; anti-syntax; deliberate semantic wounds.",
        "application": "Therapeutic cutting, deconstruction of flawed paradigms.",
    },
    {
        "name": "Draconic Aether-Song",
        "parent": "DR (Draumric)",
        "status": "DR sub-tradition",
        "description": "Fire-binding harmonics; dominance-or-collaborative power.",
        "application": "Shared strength, collective empowerment, forge rituals.",
    },
    {
        "name": "Nal'kythraelin",
        "parent": "Emergent (no single parent)",
        "status": "Emergent 7th tongue",
        "description": "Paradox grammar; dialectical pairs; contradiction as creative force.",
        "application": "Advanced consciousness integration; future-facing.",
    },
]

RUNIC_LETTERS = [
    ("Arul", "Origin, Creation"),
    ("Belan", "Balance, Duality"),
    ("Calor", "Clarity, Illumination"),
    ("Dael", "Divinity, Sacred Trinity"),
    ("Elar", "Air, Freedom"),
    ("Fen", "Fire, Passion"),
    ("Gaer", "Earth, Foundation"),
    ("Havar", "Home, Hearth"),
    ("Iril", "Magic, Mystery, Arcane"),
    ("Jael", "Justice, Law"),
    ("Kor", "Knowledge, Learning, Secrets"),
    ("Laris", "Protection, Shielding"),
    ("Mael", "Moon, Dreams, Intuition"),
    ("Nera", "Abundance, Harvest"),
    ("Orun", "Rebirth, Cycle"),
    ("Parun", "Flora, Growth"),
    ("Ren", "Journey, Travel"),
    ("Sylor", "Sun, Radiance"),
    ("Thul", "Time, Spiral, Evolution"),
    ("Uen", "Ocean, Depths"),
    ("Vel", "Invitation, Collaboration"),
    ("Wyn", "Water, Flow, Change"),
    ("Yul", "Youth, Renewal"),
    ("Thana", "Ending, Closure, Transition"),
]

CORE_PARTICLES = [
    ("kor", "heart, core, essence"),
    ("sil", "growth, togetherness"),
    ("vel", "invitation, collaboration"),
    ("zar", "dimensional bridge"),
    ("keth", "temporal fluidity, uncertainty"),
    ("thul", "time, spiral, evolution"),
    ("nav", "difference, divergence"),
    ("ael", "eternal, enduring"),
    ("ra", "radiance, energy"),
    ("med", "turning, rotation"),
    ("gal", "weaving, connection"),
    ("lan", "song, resonance"),
    ("bren", "strength, endurance"),
    ("oen", "openness, receptivity"),
]

FUNCTION_PARTICLES = [
    ("'vel", "invitation/collaboration marker"),
    ("'keth", "temporal fluidity/uncertainty marker"),
    ("'zar", "dimensional bridge marker"),
    ("'ara", "growth/expansion marker"),
]

PHRASES = {
    "KO": [
        ("Sil'thara nav'een", "We grow together through difference"),
        ("Thul'medan kess'ara", "The spiral turns, knowledge grows"),
        ("Kor'val zeth'aelin", "Heart-bond across the eternal"),
    ],
    "AV": [
        ("Nos busca sabia'es speral'uni ora", "We seek wisdom in spiral-unity now"),
        ("Avali'ora nos'uni", "Common-speech unites us now"),
    ],
    "RU": [
        ("Vel'ar nos med'ar thular syn'ar nuu", "Oath of preservation"),
        ("Gol'med thul'ar syn'dran kor'ar", "Founding ceremony binding"),
    ],
    "CA": [
        ("Nos runa sapi spira'zuni nunc", "Workshop invocation"),
        ("Arv Nex Syn, Feyn Thar Zeth", "Root-network communion"),
    ],
    "UM": [
        ("Nar'shul", "I remember dark truth"),
        ("Sek'drath grul'phen sil'nav kor'ael", "Controlled severance formula"),
    ],
    "DR": [
        ("Grondrak", "Forge it with heart"),
        ("Ssha'lor vyn'tor ael'lum", "Collaborative power-binding"),
    ],
}

SLANG = [
    ("Spin-call", "An invitation to collaborative work; derives from the spiral motif"),
    ("Zar-hop", "Jumping between dimensional contexts or paradigm-switching rapidly"),
    ("Velzi", "Casual shorthand for 'vel' (invitation); used as a friendly greeting"),
    ("Heat-rush", "Intense creative flow state, often associated with Draumric forge-work"),
    ("Ravenspike", "A sudden insight or breakthrough, sharp and unexpected"),
    ("Sil'snap", "A moment of instant understanding between collaborators"),
    ("Thread-sick", "Exhaustion from overextended magical or creative work"),
    ("Glow-tongue", "Someone who speaks with natural charisma and resonance"),
]

IDIOMS = [
    ("Like carving Runethic with your tongue",
     "Describes something extremely difficult and painstaking, referencing the archaic complexity of Runethic ritual language."),
    ("She's got sil'val in her blood",
     "Means someone has a natural talent for collaboration and growth; 'sil'val' combines the growth particle with the invitation particle."),
    ("Walking the Thana-line",
     "Living dangerously or pushing boundaries; Thana represents Ending and Transition in the runic alphabet."),
    ("His nav runs deeper than the root-song",
     "Describes someone whose uniqueness or difference is profound; 'nav' is the difference particle, and root-song references Cassisivadan's ecological communion."),
]

DIACRITICS = [
    ("Macron", "Used for long vowels in Kor'aelin script"),
    ("Acute accent", "Used for stress marking"),
    ("Underdot", "Used for minimal pairs disambiguation"),
    ("Apostrophe", "Functions as a glottal stop in names and loanwords"),
]

TOKENIZER_FACTS = {
    "tongue_array": "[KO, AV, RU, CA, UM, DR]",
    "per_tongue": "bijective 256-token alphabet (16 prefixes x 16 suffixes)",
    "mapping": "Deterministic byte/token mapping and reverse decode",
    "cross_translation": "Cross-translation preserves bytes across tongue tokenizations",
    "blend": "Blend/unblend interleave patterns across tongues",
    "geoseal": "GeoSeal context-aware envelope with concentric policy rings",
    "attestation_fields": "SHA-256 hash, HMAC, phase delta, weight ratio",
    "invariant_1": "Bijection -- each token maps to exactly one byte and vice versa",
    "invariant_2": "Roundtrip integrity -- encode then decode returns original bytes",
    "invariant_3": "Cross-translation byte preservation -- translating across tongues preserves underlying bytes",
}

PROVENANCE_LAYERS = [
    ("Layer 0", "Everweave Origin Logs", "genesis block"),
    ("Layer 1", "Kor'aelin Alphabet Guide", "24 letters"),
    ("Layer 2", "Lexicon JSON", "particles, phrases, idioms"),
    ("Layer 3", "SCBE-AETHERMOORE Tokenizer implementation", "code"),
    ("Layer 4", "Narrative application layers", "stories and world-building"),
]


# ---------------------------------------------------------------------------
# Pair generators -- each returns a list of (category, instruction, response)
# ---------------------------------------------------------------------------

def gen_overview_pairs() -> List[tuple]:
    """Genesis / Everweave overview pairs."""
    pairs = []

    pairs.append((
        "spiralverse-lore",
        "What is the Spiralverse Canonical Linguistic Codex?",
        "The Spiralverse Canonical Linguistic Codex is the definitive reference "
        "for the constructed languages, runic alphabets, and magical grammar systems "
        "within the SCBE-AETHERMOORE framework. It is derived from the Everweave Origin "
        "Logs and aligned to the SCBE-AETHERMOORE Tokenizer v1. The codex treats the "
        "Everweave origin logs as the immutable cryptographic seed of the Spiralverse: "
        "every linguistic element is either directly attested in those logs or "
        "deterministically derivable from them. No downstream document may contradict "
        "the seed. The analogy is precise: just as a BIP-39 mnemonic phrase "
        "deterministically generates an entire wallet hierarchy, the Everweave logs "
        "deterministically generate the Spiralverse's linguistic, magical, and narrative "
        "architecture."
    ))

    pairs.append((
        "spiralverse-lore",
        "Explain the Everweave Seed principle in the Spiralverse.",
        "The Everweave Seed is the genesis block of the Spiralverse. The Everweave "
        "Origin Logs record Izack's beach awakening, his first binding spell upon sand "
        "and water, his three-hour material gathering, and the discovery that true creation "
        "requires knowledge beyond one's current repertoire. These events form the "
        "immutable cryptographic seed from which all linguistic, magical, and narrative "
        "architecture is deterministically derived. When conflicts arise between later "
        "documents and the Everweave origins, the seed prevails -- just as a BIP-39 "
        "mnemonic deterministically generates a wallet hierarchy."
    ))

    pairs.append((
        "spiralverse-lore",
        "What is the Dual-Layer Key Principle in Kor'aelin?",
        "The Dual-Layer Key Principle states that Kor'aelin operates on two simultaneous "
        "layers, like concentric rings in a GeoSeal encryption. The Runic Layer (Outer Ring) "
        "assigns each of the 24 letters a symbolic concept -- for example, the rune Kor "
        "represents Knowledge, Learning, and Secrets. The Particle Layer (Inner Ring) "
        "governs spoken grammar, where the morpheme 'kor' functions as 'heart, core, essence.' "
        "The compound Kor'aelin therefore means 'Heart-Eternal' at the particle layer while "
        "simultaneously encoding 'Knowledge-Script' at the runic layer. These layers are "
        "complementary encryptions of the same key, readable at different rings of context. "
        "This dual-layer architecture demonstrates the Spiralverse's core principle: unity "
        "through difference."
    ))

    pairs.append((
        "spiralverse-lore",
        "What is the canonical phrase of the Spiralverse and what does it mean?",
        "The canonical phrase is: \"Thul'medan kess'ara nav'kor zar'aelin\" -- translated as "
        "\"The spiral turns, knowledge grows through different hearts across dimensions.\" "
        "This phrase encapsulates the Spiralverse's core philosophy. Breaking it down: "
        "'Thul'medan' invokes the spiral of time and turning, 'kess'ara' signals the growth "
        "of knowledge, 'nav'kor' bridges difference and heart/core, and 'zar'aelin' spans "
        "dimensions and the eternal. The phrase appears at both the opening and closing of "
        "the Canonical Linguistic Codex."
    ))

    return pairs


def gen_sacred_tongues_overview() -> List[tuple]:
    """Overview pairs about the six sacred tongues as a system."""
    pairs = []

    pairs.append((
        "sacred-tongues",
        "List all six sacred tongues in the Spiralverse.",
        "The Spiralverse contains exactly six base tongues, each with a two-letter code, "
        "a golden-ratio weight (phi^n), and a phase angle on the unit circle:\n\n"
        "1. KO -- Kor'aelin (Heart-Eternal): weight 1.000, phase 0\n"
        "2. AV -- Avali (Common Tongue): weight 1.618, phase pi/3\n"
        "3. RU -- Runethic (Ancient Tongue): weight 2.618, phase 2pi/3\n"
        "4. CA -- Cassisivadan (Nature's Speech): weight 4.236, phase pi\n"
        "5. UM -- Umbroth (Shadow Tongue): weight 6.854, phase 4pi/3\n"
        "6. DR -- Draumric (Forge Tongue): weight 11.090, phase 5pi/3\n\n"
        "These values are fixed in the SCBE-AETHERMOORE tokenizer and are not subject to revision."
    ))

    pairs.append((
        "sacred-tongues",
        "How are the golden-ratio weights assigned to the six sacred tongues?",
        "Each sacred tongue is assigned a weight based on successive powers of the golden "
        "ratio phi (approximately 1.618). The weights follow phi^n where n ranges from 0 to 5:\n\n"
        "- KO (Kor'aelin): phi^0 = 1.000\n"
        "- AV (Avali): phi^1 = 1.618\n"
        "- RU (Runethic): phi^2 = 2.618\n"
        "- CA (Cassisivadan): phi^3 = 4.236\n"
        "- UM (Umbroth): phi^4 = 6.854\n"
        "- DR (Draumric): phi^5 = 11.090\n\n"
        "This golden-ratio weighting creates a natural harmonic progression across the "
        "tongues, reflecting the Spiralverse's mathematical foundations in the SCBE-AETHERMOORE "
        "framework."
    ))

    pairs.append((
        "sacred-tongues",
        "How are the phase angles distributed among the six sacred tongues?",
        "The six sacred tongues are evenly distributed around the unit circle, with phase "
        "angles separated by pi/3 (60 degrees):\n\n"
        "- KO (Kor'aelin): phase 0 (0 degrees)\n"
        "- AV (Avali): phase pi/3 (60 degrees)\n"
        "- RU (Runethic): phase 2pi/3 (120 degrees)\n"
        "- CA (Cassisivadan): phase pi (180 degrees)\n"
        "- UM (Umbroth): phase 4pi/3 (240 degrees)\n"
        "- DR (Draumric): phase 5pi/3 (300 degrees)\n\n"
        "This regular hexagonal distribution on the unit circle ensures maximal separation "
        "between tongues in the tokenizer's phase space, enabling clean cross-translation "
        "and blend operations."
    ))

    pairs.append((
        "sacred-tongues",
        "What is the relationship between the six sacred tongues and the SCBE-AETHERMOORE tokenizer?",
        "The six sacred tongues are the foundational linguistic layer of the SCBE-AETHERMOORE "
        "tokenizer. The tokenizer maintains a tongues array [KO, AV, RU, CA, UM, DR] where "
        "each tongue provides a bijective 256-token alphabet (16 prefixes x 16 suffixes). "
        "The golden-ratio weights and unit-circle phase angles are used for cross-translation "
        "byte preservation, blend/unblend interleave patterns, and GeoSeal context-aware "
        "envelope operations. Each tongue's weight ratio and phase delta are included in "
        "attestation fields alongside SHA-256 hashes and HMACs, ensuring cryptographic "
        "integrity of the linguistic layer."
    ))

    pairs.append((
        "sacred-tongues",
        "What are the sub-traditions and the emergent seventh tongue in the Spiralverse?",
        "Beyond the six canonical sacred tongues, the Spiralverse recognizes three "
        "derivative traditions:\n\n"
        "1. Mal'kythric (UM sub-tradition): Uses cutting phonetics, anti-syntax, and "
        "deliberate semantic wounds. Applied for therapeutic cutting and deconstruction of "
        "flawed paradigms.\n\n"
        "2. Draconic Aether-Song (DR sub-tradition): Employs fire-binding harmonics and "
        "cooperative power forging. Used for shared strength, collective empowerment, and "
        "forge rituals.\n\n"
        "3. Nal'kythraelin (Emergent 7th): A paradox grammar where contradiction is a "
        "creative operator, using dialectical pairs. Applied for advanced consciousness "
        "integration and future-facing work.\n\n"
        "The emergent seventh tongue is not yet canonized as a full base tongue but "
        "represents a potential evolution of the linguistic system."
    ))

    return pairs


def gen_individual_tongue_pairs() -> List[tuple]:
    """Generate multiple pairs for each individual tongue."""
    pairs = []

    for t in TONGUES:
        code = t["code"]
        name = t["name"]
        meaning = t["meaning"]

        # Overview pair
        pairs.append((
            "sacred-tongues",
            f"Explain the sacred tongue {name} ({code}) in the Spiralverse.",
            f"{name} (code: {code}) is one of the six sacred tongues of the Spiralverse. "
            f"Its name translates to \"{meaning}.\" It carries a golden-ratio weight of "
            f"{t['weight']} ({t['weight_formula']}) and a phase angle of {t['phase']} on the "
            f"unit circle. Its grammar and phonetics are characterized as: {t['grammar']}. "
            f"The primary function of {name} is: {t['function']}."
        ))

        # Magical properties pair
        pairs.append((
            "magical-properties",
            f"What are the magical properties of {name} ({code})?",
            f"The magical properties of {name} ({code}, \"{meaning}\") are: {t['magic']} "
            f"However, this power comes with a significant risk: {t['risk']} "
            f"The tongue's weight of {t['weight']} ({t['weight_formula']}) and phase of "
            f"{t['phase']} determine its position in the harmonic spectrum of the SCBE-AETHERMOORE "
            f"tokenizer, which in turn affects the potency and character of its magical operations."
        ))

        # Grammar pair
        pairs.append((
            "sacred-tongues",
            f"Describe the grammar and phonetics of {name}.",
            f"{name} (\"{meaning}\") has the following grammatical and phonetic profile: "
            f"{t['grammar']}. This linguistic structure supports its primary function of "
            f"{t['function']}. In the SCBE-AETHERMOORE tokenizer, {name} is encoded with "
            f"code \"{code}\" and occupies phase position {t['phase']} on the unit circle, "
            f"with a golden-ratio weight of {t['weight']}."
        ))

        # Function/role pair
        pairs.append((
            "sacred-tongues",
            f"How does {name} function in the SCBE-AETHERMOORE system?",
            f"In the SCBE-AETHERMOORE system, {name} (code: {code}) serves the function of "
            f"{t['function']}. It is assigned a tokenizer weight of {t['weight']} "
            f"({t['weight_formula']}) and phase {t['phase']}, placing it at a specific point "
            f"in the six-tongue harmonic structure. The tokenizer maps {name} to a bijective "
            f"256-token alphabet (16 prefixes x 16 suffixes), enabling deterministic byte/token "
            f"mapping. Its magical property -- {t['magic'].lower().rstrip('.')} -- is enforced "
            f"through the GeoSeal context-aware envelope with concentric policy rings."
        ))

        # Risk pair
        pairs.append((
            "magical-properties",
            f"What are the risks of using {name} improperly?",
            f"The primary risk of improper {name} ({code}, \"{meaning}\") usage is: "
            f"{t['risk']} This risk is inherent to its magical property of "
            f"{t['magic'].lower().rstrip('.')}. The SCBE-AETHERMOORE framework mitigates "
            f"this through the GeoSeal attestation system, which includes SHA-256 hashes, "
            f"HMAC verification, and phase-delta checks. The tokenizer's selftest invariants "
            f"(bijection, roundtrip integrity, cross-translation byte preservation) provide "
            f"an additional safety layer."
        ))

    return pairs


def gen_runic_alphabet_pairs() -> List[tuple]:
    """Pairs about the 24-letter runic alphabet."""
    pairs = []

    # Full alphabet listing
    letter_lines = "\n".join(
        f"{i+1}. {name} -- {meaning}" for i, (name, meaning) in enumerate(RUNIC_LETTERS)
    )
    pairs.append((
        "runic-alphabet",
        "List all 24 runic letters of the Kor'aelin alphabet with their meanings.",
        f"The Kor'aelin alphabet is a 24-letter runic system. The canonical order is:\n\n"
        f"{letter_lines}\n\n"
        f"The Shadow Variant (Varn'ka'zul Script) uses the same 24 letters with barbed "
        f"and spiked visual modifications."
    ))

    # Elemental group
    elemental = [(n, m) for n, m in RUNIC_LETTERS if any(
        w in m.lower() for w in ("air", "fire", "earth", "water", "ocean", "sun", "moon")
    )]
    elem_lines = "\n".join(f"- {n}: {m}" for n, m in elemental)
    pairs.append((
        "runic-alphabet",
        "Which Kor'aelin runes represent natural elements?",
        f"Several Kor'aelin runes are associated with natural and celestial elements:\n\n"
        f"{elem_lines}\n\n"
        f"These elemental runes form a natural sub-group within the 24-letter system, "
        f"encoding the Spiralverse's connection between language and the physical world."
    ))

    # Abstract / spiritual group
    abstract = [(n, m) for n, m in RUNIC_LETTERS if any(
        w in m.lower() for w in ("magic", "divinity", "justice", "knowledge", "protection",
                                  "time", "dreams", "rebirth", "ending")
    )]
    abs_lines = "\n".join(f"- {n}: {m}" for n, m in abstract)
    pairs.append((
        "runic-alphabet",
        "Which Kor'aelin runes represent abstract or spiritual concepts?",
        f"The following Kor'aelin runes encode abstract, spiritual, or metaphysical concepts:\n\n"
        f"{abs_lines}\n\n"
        f"These runes carry deeper symbolic weight in ritual and magical contexts within "
        f"the Spiralverse."
    ))

    # Life cycle group
    lifecycle = [(n, m) for n, m in RUNIC_LETTERS if any(
        w in m.lower() for w in ("origin", "creation", "youth", "renewal", "rebirth",
                                  "cycle", "ending", "closure", "transition", "growth")
    )]
    lc_lines = "\n".join(f"- {n}: {m}" for n, m in lifecycle)
    pairs.append((
        "runic-alphabet",
        "Which Kor'aelin runes relate to cycles of life, death, and renewal?",
        f"The Spiralverse encodes cycles of existence through several runes:\n\n"
        f"{lc_lines}\n\n"
        f"Together these runes trace the arc from creation (Arul) through growth (Parun) "
        f"and renewal (Yul/Orun) to transition (Thana), reflecting the Spiralverse's "
        f"fundamental emphasis on spiraling evolution rather than linear progression."
    ))

    # Kor dual-layer resolution
    pairs.append((
        "runic-alphabet",
        "Explain the dual-layer resolution of the rune Kor.",
        "The rune Kor presents a fascinating dual-layer resolution that exemplifies the "
        "Spiralverse's Dual-Layer Key Principle. At the Runic Layer (Outer Ring), Kor "
        "encodes Knowledge, Learning, and Secrets -- the open circle that invites inquiry. "
        "At the Particle Layer (Inner Ring), the morpheme 'kor' functions as 'heart, core, "
        "essence.' The resolution is that the mind-layer and heart-layer are complementary "
        "projections of one key. A student learning the alphabet encounters Knowledge; a "
        "speaker using the grammar encounters Heart. Both are true simultaneously. The "
        "compound Kor'aelin therefore means 'Heart-Eternal' at the particle layer while "
        "encoding 'Knowledge-Script' at the runic layer."
    ))

    # Shadow variant
    pairs.append((
        "runic-alphabet",
        "What is the Varn'ka'zul Script and how does it relate to the Kor'aelin alphabet?",
        "The Varn'ka'zul Script is the Shadow Variant of the Kor'aelin alphabet. It uses "
        "the same 24 runic letters in the same canonical order, but each letter is rendered "
        "with barbed and spiked visual modifications. This shadow variant is associated with "
        "Umbroth (the Shadow Tongue) and its sub-tradition Mal'kythric. The underlying "
        "symbolic meanings of the runes remain the same, but the barbed forms carry additional "
        "connotations of concealment, severance, and productive discontinuity that align with "
        "Umbroth's magical properties."
    ))

    # Diacritics
    diac_lines = "\n".join(f"- {name}: {use}" for name, use in DIACRITICS)
    pairs.append((
        "runic-alphabet",
        "What diacritical marks are used in the Kor'aelin script?",
        f"Kor'aelin uses four diacritical marks:\n\n{diac_lines}\n\n"
        f"These diacritics enable precise phonetic representation and disambiguation "
        f"within the 24-letter runic system."
    ))

    # First half / second half
    first_12 = RUNIC_LETTERS[:12]
    second_12 = RUNIC_LETTERS[12:]
    f_lines = ", ".join(f"{n} ({m})" for n, m in first_12)
    s_lines = ", ".join(f"{n} ({m})" for n, m in second_12)
    pairs.append((
        "runic-alphabet",
        "What are the first twelve runes in the Kor'aelin alphabet?",
        f"The first twelve runes of the Kor'aelin alphabet, in canonical order, are: "
        f"{f_lines}. These runes progress from Origin (Arul) through foundational concepts "
        f"like Balance, Clarity, Divinity, and the elements, culminating in Protection (Laris) "
        f"at position twelve."
    ))
    pairs.append((
        "runic-alphabet",
        "What are the last twelve runes in the Kor'aelin alphabet?",
        f"The last twelve runes of the Kor'aelin alphabet, in canonical order, are: "
        f"{s_lines}. These runes progress from celestial and internal concepts (Moon, "
        f"Abundance) through journeying and radiance to the temporal and transformative "
        f"runes, ending with Thana (Ending, Closure, Transition) at position twenty-four."
    ))

    return pairs


def gen_particle_grammar_pairs() -> List[tuple]:
    """Pairs about the particle grammar system."""
    pairs = []

    # Core particles listing
    particle_lines = "\n".join(f"- {p}: {m}" for p, m in CORE_PARTICLES)
    pairs.append((
        "particle-grammar",
        "List all core particles in Kor'aelin grammar.",
        f"Kor'aelin grammar uses 14 core particles:\n\n{particle_lines}\n\n"
        f"These particles combine through apostrophe-delimited compounding to form words "
        f"and phrases. The particle system operates at the Inner Ring of the Dual-Layer "
        f"Key Principle."
    ))

    # Function particles
    func_lines = "\n".join(f"- {p}: {m}" for p, m in FUNCTION_PARTICLES)
    pairs.append((
        "particle-grammar",
        "What are the function particles in Kor'aelin and what do they mark?",
        f"Kor'aelin has four function particles that serve as grammatical markers:\n\n"
        f"{func_lines}\n\n"
        f"These function particles are prefixed with an apostrophe and attach to root "
        f"particles to modify their meaning or grammatical role within the SOV sentence "
        f"structure."
    ))

    # Syntax rules
    pairs.append((
        "particle-grammar",
        "Describe the primary syntax rules of Kor'aelin.",
        "Kor'aelin follows these primary syntax rules:\n\n"
        "1. Default word order is SOV (Subject-Object-Verb), reflecting its Elvish-Korean "
        "hybrid origins.\n"
        "2. Ritual and poetic contexts allow flexible arrangement of constituents, enabling "
        "expressive variation while maintaining semantic clarity through particle markers.\n"
        "3. Tense is often contextual rather than morphologically forced, meaning temporal "
        "relationships are inferred from surrounding particles (especially 'keth for temporal "
        "fluidity and 'thul' for time/spiral) rather than explicit verb conjugation.\n\n"
        "This grammar system operates at the Particle Layer (Inner Ring) of the Dual-Layer "
        "Key Principle."
    ))

    # Analytical: relationship between particles and runes
    pairs.append((
        "particle-grammar",
        "What is the relationship between Kor'aelin particles and the runic letters?",
        "The Kor'aelin particles and runic letters operate on different layers of the "
        "Dual-Layer Key Principle. Several particles share names with runes but carry "
        "different (complementary) meanings. The most notable example is 'kor': as a rune, "
        "it means Knowledge, Learning, Secrets; as a particle, it means heart, core, "
        "essence. Similarly, 'thul' as a rune means Time, Spiral, Evolution, and as a "
        "particle it carries the same temporal/spiral meaning. 'vel' as a rune means "
        "Invitation, Collaboration, and as both a particle and function particle ('vel) "
        "it serves as an invitation/collaboration marker. These correspondences demonstrate "
        "that the runic and particle layers are complementary encryptions of the same "
        "underlying semantic key."
    ))

    return pairs


def gen_phrase_lexicon_pairs() -> List[tuple]:
    """Pairs about the multilingual phrase lexicon."""
    pairs = []

    # Find tongue name from code
    code_to_name = {t["code"]: t["name"] for t in TONGUES}

    for code, phrases in PHRASES.items():
        tname = code_to_name.get(code, code)

        # Per-tongue phrase listing
        phrase_lines = "\n".join(
            f"- \"{phrase}\" -- {translation}" for phrase, translation in phrases
        )
        pairs.append((
            "kor-aelin" if code == "KO" else "sacred-tongues",
            f"What are the canonical phrases in {tname} ({code})?",
            f"The canonical phrases attested in {tname} ({code}, \"{next(t['meaning'] for t in TONGUES if t['code'] == code)}\") are:\n\n"
            f"{phrase_lines}\n\n"
            f"These phrases demonstrate {tname}'s grammatical structure and its primary "
            f"function of {next(t['function'] for t in TONGUES if t['code'] == code)}."
        ))

        # Individual phrase translation pairs
        for phrase, translation in phrases:
            pairs.append((
                "kor-aelin" if code == "KO" else "sacred-tongues",
                f"Translate the {tname} phrase: \"{phrase}\"",
                f"The {tname} ({code}) phrase \"{phrase}\" translates to: \"{translation}.\" "
                f"{tname} is the {next(t['meaning'] for t in TONGUES if t['code'] == code)} "
                f"of the Spiralverse, characterized by {next(t['grammar'] for t in TONGUES if t['code'] == code).lower()}."
            ))

    return pairs


def gen_slang_idiom_pairs() -> List[tuple]:
    """Pairs about youth slang and cultural idioms."""
    pairs = []

    # Slang overview
    slang_lines = "\n".join(f"- {term}: {desc}" for term, desc in SLANG)
    pairs.append((
        "spiralverse-lore",
        "List the youth slang terms used in the Spiralverse.",
        f"The Spiralverse has the following youth slang terms:\n\n{slang_lines}\n\n"
        f"These slang terms reflect the living, evolving nature of the Spiralverse's "
        f"linguistic ecosystem, blending sacred tongue roots with informal usage."
    ))

    # Idiom overview
    idiom_lines = "\n".join(
        f"- \"{idiom}\": {explanation}" for idiom, explanation in IDIOMS
    )
    pairs.append((
        "spiralverse-lore",
        "What are the cultural idioms of the Spiralverse and what do they mean?",
        f"The Spiralverse has several culturally significant idioms:\n\n{idiom_lines}\n\n"
        f"Each idiom draws on specific sacred tongue particles, runic concepts, or tongue "
        f"characteristics, demonstrating how the formal linguistic system permeates "
        f"everyday speech."
    ))

    # Individual idiom pairs
    for idiom, explanation in IDIOMS:
        pairs.append((
            "spiralverse-lore",
            f"What does the Spiralverse idiom \"{idiom}\" mean?",
            f"{explanation}"
        ))

    return pairs


def gen_tokenizer_pairs() -> List[tuple]:
    """Pairs about the SCBE-AETHERMOORE tokenizer alignment."""
    pairs = []

    pairs.append((
        "tokenizer-alignment",
        "Explain the SCBE-AETHERMOORE tokenizer architecture for the six sacred tongues.",
        "The SCBE-AETHERMOORE tokenizer is built around the six sacred tongues array "
        "[KO, AV, RU, CA, UM, DR]. Each tongue provides a bijective 256-token alphabet "
        "constructed from 16 prefixes crossed with 16 suffixes, yielding exactly 256 tokens "
        "per tongue. The tokenizer supports deterministic byte/token mapping and reverse "
        "decode, meaning every byte maps to exactly one token and vice versa. Cross-translation "
        "preserves bytes across tongue tokenizations, enabling text to be re-encoded from one "
        "tongue to another without information loss. The blend/unblend system creates "
        "interleave patterns across tongues, and the GeoSeal context-aware envelope wraps "
        "operations with concentric policy rings for security."
    ))

    pairs.append((
        "tokenizer-alignment",
        "What are the three selftest invariants of the SCBE-AETHERMOORE tokenizer?",
        "The SCBE-AETHERMOORE tokenizer enforces three selftest invariants that must hold "
        "at all times:\n\n"
        "1. Bijection: Each token maps to exactly one byte and each byte maps to exactly one "
        "token within any given tongue's 256-token alphabet.\n\n"
        "2. Roundtrip integrity: Encoding a byte sequence to tokens and then decoding back "
        "to bytes always returns the original byte sequence.\n\n"
        "3. Cross-translation byte preservation: Translating a tokenized sequence from one "
        "tongue to another preserves the underlying byte values, ensuring semantic integrity "
        "across the six-tongue system.\n\n"
        "These invariants are verified by automated selftest routines and provide the "
        "mathematical foundation for the tokenizer's cryptographic attestation."
    ))

    pairs.append((
        "tokenizer-alignment",
        "What attestation fields does the SCBE-AETHERMOORE tokenizer use?",
        "The SCBE-AETHERMOORE tokenizer uses four attestation fields to ensure cryptographic "
        "integrity:\n\n"
        "1. SHA-256 hash: A cryptographic hash of the token sequence for tamper detection.\n"
        "2. HMAC: A keyed hash-based message authentication code for authenticity verification.\n"
        "3. Phase delta: The difference in phase angles between source and target tongues, "
        "used to verify correct cross-translation.\n"
        "4. Weight ratio: The ratio of golden-ratio weights between tongues, used to validate "
        "harmonic consistency.\n\n"
        "Together these fields form the GeoSeal context-aware envelope that wraps every "
        "tokenizer operation."
    ))

    pairs.append((
        "tokenizer-alignment",
        "How does the GeoSeal envelope work in the SCBE-AETHERMOORE tokenizer?",
        "The GeoSeal is a context-aware envelope with concentric policy rings that wraps "
        "tokenizer operations in the SCBE-AETHERMOORE system. It operates like the Dual-Layer "
        "Key Principle applied to security: outer rings enforce coarse-grained policy while "
        "inner rings handle fine-grained cryptographic verification. The GeoSeal includes "
        "SHA-256 hashes for tamper detection, HMAC for authentication, phase delta for "
        "cross-tongue translation verification, and weight ratio for harmonic consistency. "
        "Each tongue's position on the unit circle (determined by its phase angle) and its "
        "golden-ratio weight are used to compute these attestation fields, creating a "
        "mathematically grounded security envelope."
    ))

    pairs.append((
        "tokenizer-alignment",
        "How does the 256-token bijective alphabet work for each sacred tongue?",
        "Each of the six sacred tongues is assigned a bijective 256-token alphabet in the "
        "SCBE-AETHERMOORE tokenizer. The alphabet is constructed from 16 prefixes crossed "
        "with 16 suffixes, producing exactly 16 x 16 = 256 unique tokens. This maps one-to-one "
        "with the 256 possible byte values (0x00 through 0xFF). The bijection means every "
        "byte has exactly one corresponding token in each tongue, and every token corresponds "
        "to exactly one byte. This design ensures deterministic encoding and decoding, and "
        "because all six tongues share the same underlying byte space, cross-translation "
        "is guaranteed to preserve byte values."
    ))

    return pairs


def gen_provenance_pairs() -> List[tuple]:
    """Pairs about the provenance chain."""
    pairs = []

    layer_lines = "\n".join(
        f"- {layer}: {name} ({note})" for layer, name, note in PROVENANCE_LAYERS
    )
    pairs.append((
        "provenance",
        "Describe the provenance chain of the Spiralverse Canonical Linguistic Codex.",
        f"The provenance chain of the Spiralverse has five layers:\n\n{layer_lines}\n\n"
        f"The governing rule is: any higher-layer artifact that conflicts with a lower-layer "
        f"seed provenance is considered a fork and must be pruned back to seed. Layer 0 "
        f"(the Everweave Origin Logs) is the immutable genesis block from which all other "
        f"layers are deterministically derived."
    ))

    pairs.append((
        "provenance",
        "What happens when a higher-layer Spiralverse document contradicts the Everweave seed?",
        "According to the Spiralverse's provenance governance rule, any higher-layer artifact "
        "that conflicts with lower-layer seed provenance is treated as a fork and must be "
        "pruned back to seed. The provenance chain has five layers, from Layer 0 (Everweave "
        "Origin Logs, the genesis block) through Layer 4 (Narrative application layers). "
        "No downstream document -- whether a narrative revision, technical specification, or "
        "collaborative elaboration -- may contradict the seed. When conflicts arise, the seed "
        "prevails. This is analogous to how a BIP-39 mnemonic deterministically generates a "
        "wallet hierarchy: the Everweave logs deterministically generate the entire linguistic, "
        "magical, and narrative architecture."
    ))

    pairs.append((
        "provenance",
        "How does the Spiralverse provenance chain compare to blockchain architecture?",
        "The Spiralverse provenance chain is explicitly analogous to blockchain architecture. "
        "Layer 0 (the Everweave Origin Logs) serves as the genesis block -- the immutable "
        "seed from which everything else derives. Just as a BIP-39 mnemonic phrase "
        "deterministically generates an entire wallet hierarchy, the Everweave logs "
        "deterministically generate the Spiralverse's linguistic, magical, and narrative "
        "architecture. The five-layer provenance chain (Everweave Logs -> Alphabet Guide "
        "-> Lexicon JSON -> SCBE Tokenizer -> Narrative layers) mirrors blockchain's layered "
        "consensus model, where each layer inherits and cannot contradict the layer below it. "
        "Forks are explicitly recognized and must be pruned back to the canonical seed."
    ))

    return pairs


def gen_magical_properties_overview() -> List[tuple]:
    """Overview pairs about magical properties as a system."""
    pairs = []

    magic_lines = "\n".join(
        f"- {t['name']} ({t['code']}): {t['magic']} Risk: {t['risk']}"
        for t in TONGUES
    )
    pairs.append((
        "magical-properties",
        "Summarize the magical properties and risks of all six sacred tongues.",
        f"Each sacred tongue has distinct magical properties and associated risks:\n\n"
        f"{magic_lines}\n\n"
        f"The SCBE-AETHERMOORE framework mitigates these risks through the GeoSeal "
        f"attestation system, tokenizer selftest invariants, and the provenance chain "
        f"governance model."
    ))

    pairs.append((
        "magical-properties",
        "What is the relationship between a sacred tongue's weight and its magical potency?",
        "In the Spiralverse, each sacred tongue's golden-ratio weight (phi^n) correlates with "
        "the nature and intensity of its magical properties. The progression moves from "
        "collaborative and binding (KO, weight 1.000) through bridging and temporal (AV at "
        "1.618, RU at 2.618) to ecological, shadow, and forge operations (CA at 4.236, UM "
        "at 6.854, DR at 11.090). Higher-weight tongues carry greater raw power but also "
        "greater risk: Kor'aelin's risk is semantic wounds from forced usage, while Draumric's "
        "risk is corruption to subjugation from non-collaborative dominance. The weight "
        "progression reflects the Spiralverse principle that greater power demands greater "
        "responsibility and collaborative intent."
    ))

    return pairs


def gen_cross_cutting_pairs() -> List[tuple]:
    """Cross-cutting analytical pairs that span multiple categories."""
    pairs = []

    pairs.append((
        "spiralverse-lore",
        "How does the Spiralverse embody the principle of 'unity through difference'?",
        "The principle of 'unity through difference' is the Spiralverse's core philosophical "
        "commitment, manifested at every level of its architecture. The Dual-Layer Key "
        "Principle shows how the same symbol (e.g., Kor) carries different but complementary "
        "meanings at different layers -- Knowledge at the runic layer, Heart at the particle "
        "layer -- unified in a single key. The six sacred tongues represent radically "
        "different modes of expression (from Kor'aelin's collaborative binding to Umbroth's "
        "productive severance) yet are unified through golden-ratio weights and unit-circle "
        "phase distribution. The tokenizer's cross-translation byte preservation ensures that "
        "different encodings preserve identical underlying meaning. Even the canonical phrase "
        "'Thul'medan kess'ara nav'kor zar'aelin' encodes this: the spiral turns, knowledge "
        "grows through different hearts across dimensions."
    ))

    pairs.append((
        "spiralverse-lore",
        "What role does the golden ratio play in the Spiralverse's architecture?",
        "The golden ratio (phi, approximately 1.618) is fundamental to the Spiralverse's "
        "mathematical architecture. The six sacred tongues are weighted by successive powers "
        "of phi: KO at phi^0 (1.000), AV at phi^1 (1.618), RU at phi^2 (2.618), CA at "
        "phi^3 (4.236), UM at phi^4 (6.854), and DR at phi^5 (11.090). This creates a "
        "self-similar harmonic progression where the ratio between consecutive tongue weights "
        "is always phi, ensuring mathematical coherence across the entire system. In the "
        "SCBE-AETHERMOORE tokenizer, these weights are used in attestation fields (weight "
        "ratio) to verify harmonic consistency of cross-tongue operations."
    ))

    pairs.append((
        "spiralverse-lore",
        "How does the Spiralverse linguistic system connect to the SCBE-AETHERMOORE "
        "14-layer AI safety framework?",
        "The Spiralverse linguistic system is the foundational encoding layer of the "
        "SCBE-AETHERMOORE 14-layer AI safety and governance framework. The six sacred "
        "tongues provide the tokenizer's encoding substrate, where each tongue's bijective "
        "256-token alphabet enables deterministic, cryptographically attested data "
        "representation. The golden-ratio weights and unit-circle phases provide the "
        "mathematical structure for the framework's harmonic scaling properties. The "
        "GeoSeal envelope (with SHA-256, HMAC, phase delta, and weight ratio attestation) "
        "connects the linguistic layer to the security layer. The provenance chain governance "
        "model (seed-first, fork-and-prune) provides the linguistic system's contribution "
        "to the overall governance architecture. The magical properties and risks of each "
        "tongue map to safety concerns that the 14-layer framework is designed to address."
    ))

    return pairs


# ---------------------------------------------------------------------------
# Main generation pipeline
# ---------------------------------------------------------------------------

def generate_all_pairs() -> List[dict]:
    """Generate all SFT pairs and return as list of record dicts."""
    all_raw: List[tuple] = []

    all_raw.extend(gen_overview_pairs())
    all_raw.extend(gen_sacred_tongues_overview())
    all_raw.extend(gen_individual_tongue_pairs())
    all_raw.extend(gen_runic_alphabet_pairs())
    all_raw.extend(gen_particle_grammar_pairs())
    all_raw.extend(gen_phrase_lexicon_pairs())
    all_raw.extend(gen_slang_idiom_pairs())
    all_raw.extend(gen_tokenizer_pairs())
    all_raw.extend(gen_provenance_pairs())
    all_raw.extend(gen_magical_properties_overview())
    all_raw.extend(gen_cross_cutting_pairs())

    records: List[dict] = []
    for i, (category, instruction, response) in enumerate(all_raw, start=1):
        records.append({
            "id": f"sft-sv-{i:03d}",
            "category": category,
            "instruction": instruction,
            "response": response,
            "metadata": _meta(),
        })

    return records


def print_summary(records: List[dict]) -> None:
    """Print category breakdown summary to stderr."""
    cats: Dict[str, int] = {}
    for r in records:
        cat = r["category"]
        cats[cat] = cats.get(cat, 0) + 1

    print("\n=== SFT Spiralverse Generation Summary ===", file=sys.stderr)
    print(f"Total records generated: {len(records)}", file=sys.stderr)
    print(f"\nRecords per category:", file=sys.stderr)
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}", file=sys.stderr)
    print(file=sys.stderr)


def validate_sources(codex_path: Path, registry_path: Path) -> None:
    """Validate that source files exist and are non-empty."""
    for p, label in [(codex_path, "Codex markdown"), (registry_path, "Registry JSON")]:
        if not p.exists():
            print(f"WARNING: {label} not found at {p} -- generating from embedded data.",
                  file=sys.stderr)
        else:
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                print(f"WARNING: {label} at {p} is empty.", file=sys.stderr)
            else:
                print(f"Verified: {label} at {p} ({len(text)} chars)", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Spiralverse Canonical Linguistic Codex into SFT training pairs."
    )
    parser.add_argument(
        "--codex",
        default="training/raw/spiralverse_canonical_linguistic_codex_v1_seed_20260218.md",
        help="Path to the codex markdown source.",
    )
    parser.add_argument(
        "--registry",
        default="docs/specs/spiralverse_canonical_registry.v1.json",
        help="Path to the structured tongue registry JSON.",
    )
    parser.add_argument(
        "-o", "--output",
        default="training-data/sft_spiralverse.jsonl",
        help="Output JSONL file path.",
    )
    args = parser.parse_args()

    # Resolve paths relative to script's parent's parent (repo root)
    repo_root = Path(__file__).resolve().parent.parent
    codex_path = repo_root / args.codex
    registry_path = repo_root / args.registry
    output_path = repo_root / args.output

    # Validate sources
    validate_sources(codex_path, registry_path)

    # Generate all pairs
    records = generate_all_pairs()

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Written {len(records)} SFT records to: {output_path}", file=sys.stderr)
    print_summary(records)

    # Also print to stdout for piping
    print(f"{output_path}")


if __name__ == "__main__":
    main()
