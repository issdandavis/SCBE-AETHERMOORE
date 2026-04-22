#!/usr/bin/env python3
"""
Generate Conlang-First Sacred Tongue SFT Training Data
========================================================
Teaches the Six Sacred Tongues AS LEARNABLE CONSTRUCTED LANGUAGES
before they are used as tokenizers. Wires existing assets:

    1. Sacred Tongue specs (prefixes, suffixes, frequencies)
    2. Children's storybooks (10 stories, each mapped to a tongue)
    3. Counting rhymes and lullabies
    4. Harmonic frequency intervals (voice leading)

Pipeline order for the AI learner:
    Human language → polyglot braid → tongue affinity →
    conlang grammar lesson → lullaby melody → story context →
    THEN tokenizer

Output: training-data/sft/conlang_first_sft.jsonl

Usage:
    python scripts/generate_conlang_first_sft.py
"""

import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.sacred_tongues import (
    TONGUES,
)
from src.crypto.tri_bundle import TONGUE_WEIGHTS
from src.crypto.harmonic_dark_fill import (
    TONGUE_AUDIBLE_FREQ,
    INTERVALS,
    voice_leading_interval,
)

OUTPUT_DIR = ROOT / "training-data" / "sft"
OUTPUT_FILE = OUTPUT_DIR / "conlang_first_sft.jsonl"
STORIES_DIR = ROOT / "content" / "book" / "childrens-storybooks"

# ---------------------------------------------------------------------------
# Full tongue names — NEVER abbreviated
# ---------------------------------------------------------------------------

TONGUE_FULL_NAMES = {
    "ko": "Kor'aelin",
    "av": "Avali",
    "ru": "Runethic",
    "ca": "Cassisivadan",
    "um": "Umbroth",
    "dr": "Draumric",
}

TONGUE_DOMAINS = {
    "ko": "intent, flow, and action",
    "av": "wisdom, transport, and diplomacy",
    "ru": "witness, governance, and binding",
    "ca": "compute, analysis, and bitcraft",
    "um": "shadow, security, and veiling",
    "dr": "structure, forging, and proof",
}

TONGUE_MUSICAL_NOTES = {
    "ko": "A4 (440 Hz)",
    "av": "C5 (523.25 Hz)",
    "ru": "D4 (293.66 Hz)",
    "ca": "E5 (659.25 Hz)",
    "um": "G3 (196 Hz)",
    "dr": "G4 (392 Hz)",
}

# Story → tongue mapping (from the storybook headers)
STORY_TONGUE_MAP = {
    "01-the-three-golem-houses.md": "dr",
    "02-the-raven-who-cried-shadow-hound.md": "ko",
    "03-goldilocks-in-the-poincare-ball.md": "ru",
    "04-the-ant-and-the-grasshopper-of-suldessar.md": "av",
    "05-fizzles-golden-goose.md": "ca",
    "06-the-tortoise-and-the-drake.md": "um",
    "07-counting-rhymes-of-avalon.md": None,  # all tongues
    "08-stone-soup-at-ravencrest.md": "ko",
    "09-humpty-dumpty-on-the-harmonic-wall.md": "dr",
    "10-the-emperors-new-algorithm.md": "ru",
}


SYSTEM_PROMPT = """You are a Sacred Tongue language teacher from Avalon Academy in Aethermoor.

You teach the Six Sacred Tongues as LEARNABLE CONSTRUCTED LANGUAGES — not as abstract tokenizers, but as living languages with vocabulary, grammar, phonetics, and stories. A student must learn to SPEAK the tongue before they can use it to ENCODE.

The Six Sacred Tongues:
- Kor'aelin (440 Hz, A4): The tongue of intent, flow, and action. Soft vowels (a, ae, ei, ia). Used for commands, nonces, and flow control.
- Avali (523.25 Hz, C5): The tongue of wisdom, transport, and diplomacy. Melodic syllables (saina, talan, vessa). Used for headers, metadata, and context.
- Runethic (293.66 Hz, D4): The tongue of witness, governance, and binding. Hard consonants (khar, drath, bront). Used for salts, oaths, and legal proofs.
- Cassisivadan (659.25 Hz, E5): The tongue of compute, analysis, and bitcraft. Playful clicks (bip, bop, klik, loopa). Used for ciphertext and mathematical operations.
- Umbroth (196 Hz, G3): The tongue of shadow, security, and veiling. Hushed sounds (veil, zhur, hush, thorn). Used for redaction and concealment.
- Draumric (392 Hz, G4): The tongue of structure, forging, and proof. Metallic weight (anvil, forge, stone, steam). Used for authentication tags and structural seals.

Teaching philosophy:
1. Grammar first — learn the morpheme structure (prefix'suffix) before encoding bytes
2. Stories carry the meaning — each tongue has its own fairy tales and nursery rhymes
3. Sound matters — each tongue has a harmonic frequency that defines its character
4. Lullabies embed the pattern — rhythm and melody make vocabulary stick
5. Only AFTER speaking the tongue do we encode through it"""


def make_record(messages: list, concept_id: str, record_type: str) -> dict:
    """Create one SFT training record."""
    content_hash = hashlib.sha256(
        json.dumps(messages, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    return {
        "messages": messages,
        "metadata": {
            "source": "conlang_first_generator",
            "concept_id": concept_id,
            "record_type": record_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
        },
    }


# ---------------------------------------------------------------------------
# Record generators
# ---------------------------------------------------------------------------

def generate_grammar_lessons() -> list:
    """Generate grammar lesson records for each Sacred Tongue.

    Each tongue has 16 prefixes × 16 suffixes = 256 tokens.
    The prefix encodes the high nibble (4 bits), suffix encodes the low nibble.
    Token format: prefix'suffix (apostrophe as morpheme seam).
    """
    records = []

    for code, spec in TONGUES.items():
        full_name = TONGUE_FULL_NAMES[code]
        domain = TONGUE_DOMAINS[code]
        note = TONGUE_MUSICAL_NOTES[code]
        freq = TONGUE_AUDIBLE_FREQ[code]
        weight = TONGUE_WEIGHTS[code]

        # --- Lesson 1: Introduction to the tongue ---
        user_msg = f"Teach me {full_name}. What is this language?"

        # Show first 4 prefixes and first 4 suffixes as examples
        prefix_examples = ", ".join(spec.prefixes[:4])
        suffix_examples = ", ".join(spec.suffixes[:4])
        sample_tokens = [
            f"{spec.prefixes[i]}'{spec.suffixes[j]}"
            for i, j in [(0, 0), (0, 1), (1, 0), (2, 3), (3, 2)]
        ]

        assistant_msg = (
            f"**{full_name}** is the Sacred Tongue of {domain}.\n\n"
            f"**Sound character:** {full_name} resonates at {note} — "
            f"its harmonic frequency defines the emotional quality of the language. "
            f"When you speak {full_name}, you are vibrating at this pitch.\n\n"
            f"**Phi weight:** {weight:.3f} (phi^{['0', '1', '2', '3', '4', '5'][list(TONGUE_WEIGHTS.keys()).index(code)]})\n\n"
            f"**Morpheme structure:** Every word in {full_name} is built from a prefix "
            f"and a suffix, joined by an apostrophe:\n"
            f"  `prefix'suffix`\n\n"
            f"**Prefixes** (the first sound, carrying the high meaning):\n"
            f"  {prefix_examples}, ... (16 total)\n\n"
            f"**Suffixes** (the ending, carrying the low detail):\n"
            f"  {suffix_examples}, ... (16 total)\n\n"
            f"**Sample vocabulary:**\n"
            + "\n".join(f"  - `{t}`" for t in sample_tokens)
            + f"\n\n"
            f"With 16 prefixes × 16 suffixes, {full_name} has exactly **256 words** — "
            f"one for every possible byte value. This is not coincidence. {full_name} "
            f"was designed so that every piece of data can be spoken aloud in this tongue."
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"grammar_{code}_intro",
            "grammar_introduction",
        ))

        # --- Lesson 2: Full vocabulary table ---
        user_msg = f"Show me the full vocabulary of {full_name}."

        # Build a compact vocabulary grid (first 4 rows × 4 cols as sample)
        grid_lines = []
        grid_lines.append(f"{'':>8} | " + " | ".join(f"{s:>6}" for s in spec.suffixes[:8]))
        grid_lines.append("-" * (8 + 3 + 8 * 9))
        for i in range(4):
            row = f"{spec.prefixes[i]:>8} | " + " | ".join(
                f"{spec.prefixes[i]}'{spec.suffixes[j]:>4}"[:6]
                for j in range(8)
            )
            grid_lines.append(row)

        assistant_msg = (
            f"**{full_name} Vocabulary Grid** (sample: 4 prefixes × 8 suffixes)\n\n"
            f"```\n"
            + "\n".join(grid_lines)
            + f"\n```\n\n"
            f"**All 16 prefixes of {full_name}:**\n"
            + ", ".join(f"`{p}`" for p in spec.prefixes)
            + f"\n\n"
            f"**All 16 suffixes of {full_name}:**\n"
            + ", ".join(f"`{s}`" for s in spec.suffixes)
            + f"\n\n"
            f"**Total vocabulary:** 16 × 16 = **256 words**\n"
            f"**Encoding rule:** Byte value `N` → prefix = `prefixes[N >> 4]`, "
            f"suffix = `suffixes[N & 0x0F]`\n\n"
            f"For example, byte 0x00 = `{spec.prefixes[0]}'{spec.suffixes[0]}`, "
            f"byte 0xFF = `{spec.prefixes[15]}'{spec.suffixes[15]}`, "
            f"byte 0x42 = `{spec.prefixes[4]}'{spec.suffixes[2]}`."
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"grammar_{code}_vocab",
            "grammar_vocabulary",
        ))

        # --- Lesson 3: Phonetic character and pronunciation ---
        user_msg = f"How do I pronounce {full_name} words? What does it sound like?"

        # Analyze phonetic patterns
        vowel_heavy = sum(1 for p in spec.prefixes if p[-1] in "aeiou")
        consonant_heavy = 16 - vowel_heavy

        assistant_msg = (
            f"**Pronouncing {full_name}**\n\n"
            f"{full_name} has a distinctive sound character:\n\n"
            f"**Prefix patterns:** {vowel_heavy} of 16 prefixes end in vowels, "
            f"{consonant_heavy} end in consonants. "
        )

        if code == "ko":
            assistant_msg += (
                "Kor'aelin flows like water — soft vowel endings (a, ae, ei, ia) "
                "create a melodic, action-oriented cadence. It sounds like a commander "
                "giving orders gently but firmly."
            )
        elif code == "av":
            assistant_msg += (
                "Avali is the most melodic tongue — long, flowing syllables (saina, talan, vessa) "
                "that carry the weight of ancient wisdom. It sounds like a diplomat "
                "speaking across centuries."
            )
        elif code == "ru":
            assistant_msg += (
                "Runethic is carved from stone — hard consonants (khar, drath, bront) "
                "that strike like a gavel. It sounds like oaths being sworn "
                "in an ancient court."
            )
        elif code == "ca":
            assistant_msg += (
                "Cassisivadan is playful and precise — short, clicking syllables (bip, bop, klik) "
                "that sound like a machine counting. It sounds like a child "
                "playing with an abacus."
            )
        elif code == "um":
            assistant_msg += (
                "Umbroth is whispered — hushed, shadowy sounds (veil, zhur, hush) "
                "that seem to disappear as you speak them. It sounds like secrets "
                "being shared in the dark."
            )
        elif code == "dr":
            assistant_msg += (
                "Draumric is hammered into existence — metallic, heavy syllables (anvil, forge, stone) "
                "that ring like a blacksmith's strike. It sounds like architecture "
                "being spoken into being."
            )

        assistant_msg += (
            f"\n\n**Harmonic pitch:** {note}\n"
            f"When speaking {full_name} aloud, imagine your voice resonating at {freq:.0f} Hz. "
            f"This is not metaphor — in the Sacred Tongue lattice, {full_name} literally "
            f"occupies this frequency band.\n\n"
            f"**Practice phrase:** Say these five words aloud:\n"
            + "\n".join(
                f"  {i+1}. `{spec.prefixes[i*3]}'{spec.suffixes[i*2]}`"
                for i in range(5)
            )
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"grammar_{code}_phonetics",
            "grammar_phonetics",
        ))

    return records


def generate_lullaby_records() -> list:
    """Generate lullaby/melody records mapping tongue frequencies to patterns.

    Uses the voice_leading_interval system to create melodic relationships
    between tongues.
    """
    records = []

    # --- Lullaby 1: The Six Tongue Lullaby ---
    # Intervals between adjacent tongues in phi order
    tongue_order = ["ko", "av", "ru", "ca", "um", "dr"]
    intervals = []
    for i in range(len(tongue_order) - 1):
        ratio = voice_leading_interval(tongue_order[i], tongue_order[i + 1])
        intervals.append((tongue_order[i], tongue_order[i + 1], ratio))

    interval_lines = []
    for t1, t2, ratio in intervals:
        n1 = TONGUE_FULL_NAMES[t1]
        n2 = TONGUE_FULL_NAMES[t2]
        # Find nearest named interval
        nearest = min(INTERVALS.items(), key=lambda x: abs(x[1] - ratio))
        interval_lines.append(
            f"  {n1} → {n2}: ratio {ratio:.3f} (nearest: {nearest[0]})"
        )

    user_msg = "Sing me the Six Tongue Lullaby — the one that teaches all the tongues in order."

    assistant_msg = (
        "**The Six Tongue Lullaby**\n"
        "*(Gentle rocking rhythm — one tongue per verse, ascending in phi weight)*\n\n"
        "> Kor'aelin, Kor'aelin, A-four-forty,\n"
        "> Sil'a, kor'ae, vel'ei — flow so naughty.\n"
        "> Intent runs through like water in a stream,\n"
        "> Every action starts inside a dream.\n"
        "> *(hum at 440 Hz)*\n\n"
        "> Avali, Avali, C-five-twenty-three,\n"
        "> Saina'a, talan'e, vessa'i — wise and free.\n"
        "> Wisdom carries what the world forgets,\n"
        "> Every header holds what memory sets.\n"
        "> *(hum at 523 Hz)*\n\n"
        "> Runethic, Runethic, D-four steady,\n"
        "> Khar'ak, drath'eth, bront'ik — always ready.\n"
        "> Governance stands where others fall,\n"
        "> Every oath is carved into the wall.\n"
        "> *(hum at 294 Hz)*\n\n"
        "> Cassisivadan, Cassisivadan, E-five high,\n"
        "> Bip'a, bop'e, klik'i — numbers fly.\n"
        "> Compute and count and click and play,\n"
        "> Every cipher dances through the day.\n"
        "> *(hum at 659 Hz)*\n\n"
        "> Umbroth, Umbroth, G-three low,\n"
        "> Veil'a, zhur'e, nar'i — shadows flow.\n"
        "> Security hides what must be kept,\n"
        "> Every secret safely while you slept.\n"
        "> *(hum at 196 Hz)*\n\n"
        "> Draumric, Draumric, G-four strong,\n"
        "> Anvil'a, tharn'e, mek'i — forge along.\n"
        "> Structure stands through storm and time,\n"
        "> Every seal is proof in paradigm.\n"
        "> *(hum at 392 Hz)*\n\n"
        "**Melodic intervals between tongues:**\n"
        + "\n".join(interval_lines)
        + "\n\n"
        "The lullaby ascends in phi weight: each tongue is phi times heavier than the last. "
        "The child learns the NAME, the SOUND, the DOMAIN, and three VOCABULARY WORDS "
        "for each tongue — all before they ever encounter a tokenizer."
    )

    records.append(make_record(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        "lullaby_six_tongues",
        "lullaby",
    ))

    # --- Lullaby 2: The Phi Counting Song ---
    user_msg = "Teach me the Phi Counting Song — the one from the Counting Rhymes of Avalon."

    assistant_msg = (
        "**The Phi Counting Song**\n"
        "*(From the Counting Rhymes of Avalon — Ages 3-6)*\n\n"
        "This song teaches the phi-weighted hierarchy of the Sacred Tongues through clapping:\n\n"
        "> One clap for Kor'aelin — *clap!*\n"
        "> One-and-a-bit for Avali — *clap-tap!*\n"
        "> Two-and-a-bit for Runethic — *clap-clap-tap!*\n"
        "> Four-and-a-bit for Cassisivadan — *clap-clap-clap-clap-tap!*\n"
        "> Almost seven for Umbroth — *clap-clap-clap-clap-clap-clap-tap!*\n"
        "> Eleven for Draumric — *eleven big claps in a row!*\n\n"
        "**The math behind the rhythm:**\n"
        f"  Kor'aelin weight:    phi^0 = {TONGUE_WEIGHTS['ko']:.3f} (1 clap)\n"
        f"  Avali weight:        phi^1 = {TONGUE_WEIGHTS['av']:.3f} (~1.6 claps)\n"
        f"  Runethic weight:     phi^2 = {TONGUE_WEIGHTS['ru']:.3f} (~2.6 claps)\n"
        f"  Cassisivadan weight: phi^3 = {TONGUE_WEIGHTS['ca']:.3f} (~4.2 claps)\n"
        f"  Umbroth weight:      phi^4 = {TONGUE_WEIGHTS['um']:.3f} (~6.9 claps)\n"
        f"  Draumric weight:     phi^5 = {TONGUE_WEIGHTS['dr']:.3f} (~11.1 claps)\n\n"
        "Each tongue is exactly phi times heavier than the one before. "
        "The child doesn't need to know what phi is — they FEEL it in the clapping pattern. "
        "The fractional claps become 'taps' — a lighter sound that teaches the irrational remainder."
    )

    records.append(make_record(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        "lullaby_phi_counting",
        "lullaby",
    ))

    # --- Lullaby 3: Per-tongue bedtime phrases ---
    for code, spec in TONGUES.items():
        full_name = TONGUE_FULL_NAMES[code]
        TONGUE_AUDIBLE_FREQ[code]
        note = TONGUE_MUSICAL_NOTES[code]

        # Build a "goodnight" phrase from each tongue's vocabulary
        goodnight_tokens = [
            f"{spec.prefixes[i]}'{spec.suffixes[j]}"
            for i, j in [(0, 0), (6, 2), (11, 4), (15, 15)]
        ]

        user_msg = f"Sing me the {full_name} goodnight lullaby."

        assistant_msg = (
            f"**{full_name} Goodnight**\n"
            f"*(Whispered at {note}, gentle rocking rhythm)*\n\n"
            f"> {goodnight_tokens[0]}, {goodnight_tokens[1]},\n"
            f"> The {TONGUE_DOMAINS[code].split(',')[0]} settles down.\n"
            f"> {goodnight_tokens[2]}, {goodnight_tokens[3]},\n"
            f"> {full_name} sleeps without a sound.\n\n"
            f"> Every prefix finds its suffix pair,\n"
            f"> Every morpheme resting there.\n"
            f"> Sixteen by sixteen, two-five-six,\n"
            f"> {full_name} dreams in byte-sized tricks.\n\n"
            f"**The four goodnight words:**\n"
            + "\n".join(
                f"  - `{t}` = byte {[0x00, 0x62, 0xB4, 0xFF][i]} (0x{[0x00, 0x62, 0xB4, 0xFF][i]:02X})"
                for i, t in enumerate(goodnight_tokens)
            )
            + f"\n\n"
            f"Notice how {full_name} sounds even at rest — the prefixes "
            f"carry the weight of {TONGUE_DOMAINS[code].split(',')[0]}, "
            f"and the suffixes soften them into sleep."
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"lullaby_{code}_goodnight",
            "lullaby",
        ))

    return records


def generate_story_lesson_records() -> list:
    """Generate SFT records from existing children's stories.

    Each story teaches one Sacred Tongue through narrative. We extract
    the tongue mapping and create pre-tokenizer lessons.
    """
    records = []

    for filename, tongue_code in STORY_TONGUE_MAP.items():
        filepath = STORIES_DIR / filename
        if not filepath.exists():
            continue

        story_text = filepath.read_text(encoding="utf-8")

        # Extract title (first line after #)
        title = ""
        for line in story_text.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        if tongue_code is None:
            # Counting rhymes — all tongues
            user_msg = (
                "Tell me about the Counting Rhymes of Avalon and how they teach "
                "all six Sacred Tongues."
            )

            assistant_msg = (
                f"**{title}**\n\n"
                "The Counting Rhymes teach ALL six Sacred Tongues through rhythm and math. "
                "Each rhyme embeds the phi-weighted hierarchy:\n\n"
                f"  Kor'aelin (phi^0 = {TONGUE_WEIGHTS['ko']:.3f}) — the base beat\n"
                f"  Avali (phi^1 = {TONGUE_WEIGHTS['av']:.3f}) — the wisdom counter\n"
                f"  Runethic (phi^2 = {TONGUE_WEIGHTS['ru']:.3f}) — the governance metronome\n"
                f"  Cassisivadan (phi^3 = {TONGUE_WEIGHTS['ca']:.3f}) — the computing click\n"
                f"  Umbroth (phi^4 = {TONGUE_WEIGHTS['um']:.3f}) — the shadow whisper\n"
                f"  Draumric (phi^5 = {TONGUE_WEIGHTS['dr']:.3f}) — the structural hammer\n\n"
                "The rhymes include:\n"
                "1. **Counting the Tongues** — clapping phi weights\n"
                "2. **Five Little Golems** — subtraction with Draumric structural proofs\n"
                "3. **Hickory Dickory Spiral Spire** — counting to 6 tongues and 14 layers\n"
                "4. **The Phi Song** — the golden ratio as rhythm\n\n"
                "A child who learns these rhymes knows the NAME, WEIGHT, and CHARACTER "
                "of every Sacred Tongue before they ever see a token table."
            )
        else:
            full_name = TONGUE_FULL_NAMES[tongue_code]
            spec = TONGUES[tongue_code]
            domain = TONGUE_DOMAINS[tongue_code]

            # Extract the song/rhyme if present
            has_song = "## The Song" in story_text or "## The Nursery Rhyme" in story_text

            # Show 3 sample tokens from this tongue
            sample_tokens = [
                f"{spec.prefixes[i]}'{spec.suffixes[j]}"
                for i, j in [(0, 0), (3, 2), (7, 5)]
            ]

            user_msg = (
                f"How does \"{title}\" teach {full_name}? "
                f"What should I learn about the tongue from this story?"
            )

            assistant_msg = (
                f"**{title}** teaches **{full_name}** — the tongue of {domain}.\n\n"
                f"**The lesson:** This story shows {full_name}'s character through action, "
                f"not definition. "
            )

            # Story-specific insights
            if tongue_code == "dr":
                if "Golem" in title:
                    assistant_msg += (
                        "Maren's stone house survived because every joint had a Draumric "
                        "structural proof carved into it. Structure is not what you SEE — "
                        "it's what HOLDS when something pushes. Draumric words sound like "
                        "they're built from metal: "
                    )
                else:
                    assistant_msg += (
                        "Humpty Dumpty fell because his structure lacked Draumric seals. "
                        "When authentication is structural proof, it can't be faked. "
                        "Draumric words carry the weight of iron: "
                    )
            elif tongue_code == "ko":
                if "Raven" in title:
                    assistant_msg += (
                        "Pip's false alarm ('Vekk-ala!') taught that Kor'aelin commands "
                        "carry INTENT — and false intent degrades the system. Every "
                        "Kor'aelin word is an action: "
                    )
                else:
                    assistant_msg += (
                        "Stone Soup showed that Kor'aelin orchestrates cooperation — "
                        "each ingredient was a different intent flowing together. "
                        "Kor'aelin words sound like gentle commands: "
                    )
            elif tongue_code == "ru":
                if "Goldilocks" in title:
                    assistant_msg += (
                        "The three rooms (ALLOW, QUARANTINE, DENY) showed that Runethic "
                        "governance is geometric, not arbitrary. The binding runes checked "
                        "bloodline but not authorization — a bug. Runethic words sound like "
                        "oaths carved in stone: "
                    )
                else:
                    assistant_msg += (
                        "The Emperor's invisible algorithm showed that Runethic governance "
                        "demands verifiable proof, not trust. Runethic words are hard and certain: "
                    )
            elif tongue_code == "av":
                assistant_msg += (
                    "The Ant's patient wisdom-gathering versus the Grasshopper's improvisation "
                    "showed that Avali carries accumulated knowledge across time. "
                    "Avali words are melodic and ancient: "
                )
            elif tongue_code == "ca":
                assistant_msg += (
                    "Fizzle's goose showed that Cassisivadan compute must respect "
                    "logarithmic growth — greed collapses exponential returns. "
                    "Cassisivadan words click and pop like calculations: "
                )
            elif tongue_code == "um":
                assistant_msg += (
                    "The Tortoise's security assessments versus the Drake's speed showed "
                    "that Umbroth threat modeling guarantees arrival. Speed without threat "
                    "assessment is gambling. Umbroth words whisper like shadows: "
                )

            assistant_msg += (
                "\n".join(f"  `{t}`" for t in sample_tokens)
                + f"\n\n"
                f"**Pre-tokenizer exercise:** Before you encode ANY data through {full_name}, "
                f"say three {full_name} words aloud. Feel how the sounds carry the character "
                f"of {domain.split(',')[0]}. "
                f"The tongue is not a lookup table — it is a LANGUAGE, and the story taught you "
                f"what that language MEANS."
            )

            if has_song:
                assistant_msg += (
                    f"\n\n**The story includes a song/rhyme** that attaches {full_name} "
                    f"phonetics to meaning through rhythm. Sing it before you tokenize."
                )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"story_{filename.replace('.md', '')}",
            "story_lesson",
        ))

    return records


def generate_tongue_comparison_records() -> list:
    """Generate records comparing tongues through their intervals."""
    records = []

    # --- Record: How do the tongues relate musically? ---
    user_msg = (
        "How do the six Sacred Tongues relate to each other musically? "
        "What intervals connect them?"
    )

    lines = []
    tongue_codes = list(TONGUE_FULL_NAMES.keys())
    for i in range(len(tongue_codes)):
        for j in range(i + 1, len(tongue_codes)):
            c1, c2 = tongue_codes[i], tongue_codes[j]
            ratio = voice_leading_interval(c1, c2)
            n1 = TONGUE_FULL_NAMES[c1]
            n2 = TONGUE_FULL_NAMES[c2]
            nearest = min(INTERVALS.items(), key=lambda x: abs(x[1] - ratio))
            lines.append(f"  {n1} ↔ {n2}: {ratio:.3f} ({nearest[0]})")

    assistant_msg = (
        "**Sacred Tongue Musical Intervals**\n\n"
        "Every pair of Sacred Tongues has a musical interval — a frequency ratio "
        "that determines how they SOUND together. These intervals come from "
        "the Tymoczko voice-leading framework, where 3-voice counterpoint "
        "lives in an orbifold (T^3/S_3).\n\n"
        + "\n".join(lines)
        + "\n\n"
        "**What this means for learning:**\n"
        "- Tongues with a **perfect fifth** (1.500) are maximally consonant — "
        "they complement each other naturally\n"
        "- Tongues with a **phi interval** (1.618) have the golden ratio between them — "
        "they are adjacent in the phi hierarchy\n"
        "- Tongues with a **minor third** (1.200) are close but dissonant — "
        "they create tension when used together\n\n"
        "A polyglot who speaks all six tongues hears these intervals as "
        "the TEXTURE of the language space."
    )

    records.append(make_record(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        "tongue_intervals",
        "tongue_comparison",
    ))

    # --- Record: Translation exercise between tongues ---
    for code, spec in TONGUES.items():
        full_name = TONGUE_FULL_NAMES[code]
        # Encode byte 0x48 ('H') in this tongue
        byte_val = 0x48
        hi = (byte_val >> 4) & 0x0F
        lo = byte_val & 0x0F
        token = f"{spec.prefixes[hi]}'{spec.suffixes[lo]}"

        # Same byte in all other tongues
        other_encodings = []
        for other_code, other_spec in TONGUES.items():
            if other_code == code:
                continue
            other_token = f"{other_spec.prefixes[hi]}'{other_spec.suffixes[lo]}"
            other_name = TONGUE_FULL_NAMES[other_code]
            other_encodings.append(f"  {other_name}: `{other_token}`")

        user_msg = (
            f"How does the letter 'H' (byte 0x48) sound in {full_name} "
            f"compared to the other Sacred Tongues?"
        )

        assistant_msg = (
            f"The byte 0x48 (the letter 'H' in ASCII) across all six Sacred Tongues:\n\n"
            f"  **{full_name}: `{token}`**\n"
            + "\n".join(other_encodings)
            + f"\n\n"
            f"Same byte, six different words. The PREFIX is determined by the high nibble "
            f"(0x4 = index 4), and the SUFFIX by the low nibble (0x8 = index 8). "
            f"Each tongue's 4th prefix and 8th suffix produce a completely different sound.\n\n"
            f"This is the cross-lattice in action: the MEANING (byte 0x48) is invariant, "
            f"but the EXPRESSION changes with each tongue. Learning to hear the same byte "
            f"in all six tongues is how you become a Sacred Tongue polyglot."
        )

        records.append(make_record(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            f"cross_{code}_byte_0x48",
            "tongue_comparison",
        ))

    return records


def generate_pipeline_order_record() -> list:
    """Generate a record explaining the conlang-first pipeline order."""
    records = []

    user_msg = (
        "What is the correct order for learning the Sacred Tongues? "
        "When do I start tokenizing?"
    )

    assistant_msg = (
        "**The Conlang-First Learning Pipeline**\n\n"
        "You do NOT start with the tokenizer. The tokenizer is the LAST step. "
        "Here is the correct learning order:\n\n"
        "**Phase 1: Learn the Language**\n"
        "1. **Name and domain** — Learn what each tongue IS: "
        "Kor'aelin (intent), Avali (wisdom), Runethic (governance), "
        "Cassisivadan (compute), Umbroth (shadow), Draumric (structure)\n"
        "2. **Sound character** — Listen to each tongue's harmonic frequency. "
        "Speak sample words aloud. Feel the difference between Kor'aelin's flow "
        "and Runethic's weight.\n"
        "3. **Morpheme structure** — Learn prefix'suffix grammar. "
        "Every word is built the same way: 16 prefixes × 16 suffixes = 256 words.\n\n"
        "**Phase 2: Stories and Songs**\n"
        "4. **Children's stories** — Read the fairy tales. Each one teaches a tongue "
        "through narrative:\n"
        "   - The Three Golem Houses → Draumric (structure)\n"
        "   - The Raven Who Cried Shadow-Hound → Kor'aelin (intent)\n"
        "   - Goldilocks in the Poincare Ball → Runethic (governance)\n"
        "   - The Ant and the Grasshopper → Avali (wisdom)\n"
        "   - Fizzle's Golden Goose → Cassisivadan (compute)\n"
        "   - The Tortoise and the Drake → Umbroth (security)\n"
        "5. **Lullabies** — Sing the Six Tongue Lullaby and the Phi Counting Song. "
        "The rhythm embeds the phi-weighted hierarchy into muscle memory.\n"
        "6. **Counting rhymes** — Clap the phi weights. Feel the golden ratio.\n\n"
        "**Phase 3: Cross-Lattice Understanding**\n"
        "7. **Cross-tongue translation** — Encode the same byte in all six tongues. "
        "Hear how 'H' sounds different in each language.\n"
        "8. **Musical intervals** — Understand how tongues relate to each other "
        "through voice-leading intervals.\n\n"
        "**Phase 4: THEN Tokenize**\n"
        "9. **Byte → token encoding** — NOW use the prefix/suffix table to "
        "encode actual data. By this point, you KNOW what each token MEANS "
        "because you've learned the language it comes from.\n"
        "10. **Tri-bundle encoding** — Each byte through 6 tongues × 3 bundles × "
        "3 strands = 162 dimensions per position. The tokenizer is not a lookup "
        "table — it's a language you speak.\n\n"
        "**Why this order matters:**\n"
        "A tokenizer without language understanding is just a hash function. "
        "A tokenizer WITH language understanding is a semantic encoder. "
        "The conlang-first pipeline ensures the AI learns to THINK in "
        "Sacred Tongues before it PROCESSES through them."
    )

    records.append(make_record(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        "pipeline_order",
        "pipeline_order",
    ))

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Conlang-First Sacred Tongue SFT Generator")
    print("=" * 70)
    print(f"Tongues: {len(TONGUES)}")
    print(f"Stories: {len(STORY_TONGUE_MAP)}")
    print()

    all_records = []

    # Phase 1: Grammar lessons (3 per tongue × 6 tongues = 18)
    print("Generating grammar lessons...")
    grammar = generate_grammar_lessons()
    all_records.extend(grammar)
    print(f"  {len(grammar)} grammar records")

    # Phase 2: Lullabies (2 shared + 6 per-tongue = 8)
    print("Generating lullaby records...")
    lullabies = generate_lullaby_records()
    all_records.extend(lullabies)
    print(f"  {len(lullabies)} lullaby records")

    # Phase 3: Story lessons (10 stories)
    print("Generating story lesson records...")
    stories = generate_story_lesson_records()
    all_records.extend(stories)
    print(f"  {len(stories)} story lesson records")

    # Phase 4: Tongue comparisons (1 interval map + 6 cross-tongue = 7)
    print("Generating tongue comparison records...")
    comparisons = generate_tongue_comparison_records()
    all_records.extend(comparisons)
    print(f"  {len(comparisons)} comparison records")

    # Phase 5: Pipeline order (1)
    print("Generating pipeline order record...")
    pipeline = generate_pipeline_order_record()
    all_records.extend(pipeline)
    print(f"  {len(pipeline)} pipeline records")

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
