#!/usr/bin/env python3
"""Book-to-SFT: Convert 'The Six Tongues Protocol' into training records.

The book IS the curriculum. Marcus Chen's journey through Aethermoor teaches
the Sacred Tongues through narrative — every scene demonstrates a concept.

This generator:
  1. Splits the book into scene-level passages
  2. Detects which tongues/layers/axioms each passage teaches
  3. Creates multiple Q&A pair types per passage:
     - Narrative comprehension (what happens)
     - Tongue extraction (what concept is demonstrated)
     - Technical bridge (how does the lore map to the code)
     - Character perspective (experience the tongue through Marcus/Polly)
  4. Tags every record with full dimensional metadata
"""

from __future__ import annotations

import json
import math
import random
import hashlib
import re
import sys
import io
from pathlib import Path
from typing import Any

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
BOOK_PATH = ROOT / "content" / "book" / "reader-edition" / "the-six-tongues-protocol-full.md"
OUT_DIR = ROOT / "training-data" / "sft"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHI = (1 + math.sqrt(5)) / 2

# Canonical tongue definitions from the book (Chapter 2, lines 414-424)
TONGUES = {
    "KO": {
        "full": "Kor'aelin",
        "color": "red-gold",
        "domain": "Intent",
        "essence": "what should be true",
        "weight": 1.00,
    },
    "AV": {
        "full": "Avali",
        "color": "blue-silver",
        "domain": "Context/Transport",
        "essence": "how to get there",
        "weight": round(PHI ** 1, 3),
    },
    "RU": {
        "full": "Runethic",
        "color": "deep purple",
        "domain": "Binding/Permissions",
        "essence": "who is allowed",
        "weight": round(PHI ** 2, 3),
    },
    "CA": {
        "full": "Cassisivadan",
        "color": "white-gold",
        "domain": "Implementation/Compute",
        "essence": "how to make it true",
        "weight": round(PHI ** 3, 3),
    },
    "UM": {
        "full": "Umbroth",
        "color": "shadow-black",
        "domain": "Security/Privacy",
        "essence": "what must stay hidden",
        "weight": round(PHI ** 4, 3),
    },
    "DR": {
        "full": "Draumric",
        "color": "earth-brown",
        "domain": "Structure/Authentication",
        "essence": "proof that it is true",
        "weight": round(PHI ** 5, 3),
    },
}

# Keywords that signal tongue presence in narrative text
TONGUE_SIGNALS = {
    "KO": [
        "intent", "purpose", "goal", "want", "what should be true", "kor'aelin",
        "red-gold", "authority", "foundation", "motivation", "desire", "aim",
        "what do you intend", "tuning fork", "reference point",
    ],
    "AV": [
        "context", "route", "path", "transport", "avali", "blue-silver",
        "messenger", "channel", "tcp", "handshake", "connection", "metadata",
        "how to get there", "routing", "packet", "stream",
    ],
    "RU": [
        "permission", "allowed", "policy", "binding", "runethic", "deep purple",
        "gavel", "access control", "who is allowed", "inscript", "rule",
        "authorize", "grant", "deny", "permission", "contract",
    ],
    "CA": [
        "compute", "algorithm", "encrypt", "math", "cassisivadan", "white-gold",
        "interference", "transform", "calculate", "implement", "execute",
        "how to make it true", "computation", "engineering", "code",
    ],
    "UM": [
        "security", "hidden", "shadow", "steganograph", "umbroth", "shadow-black",
        "spy", "veil", "secret", "privacy", "anti-light", "invisible",
        "what must stay hidden", "threat", "attack", "guard",
    ],
    "DR": [
        "structure", "schema", "authentication", "foundation", "draumric",
        "earth-brown", "signature", "receipt", "proof", "document", "identity",
        "proof that it is true", "data integrity", "architect", "layer",
    ],
}

# Layer signals in narrative
LAYER_SIGNALS = {
    1: ["context", "input", "arrival", "entry", "beginning", "first"],
    2: ["realif", "transform", "convert", "translate"],
    3: ["weight", "tongue", "langues", "phi", "golden"],
    4: ["poincare", "hyperbolic", "ball", "embedding", "project"],
    5: ["distance", "arcosh", "metric", "far", "near", "diverge"],
    6: ["breath", "oscillat", "pulse", "heartbeat", "rhythm"],
    7: ["mobius", "phase", "rotation", "navigate"],
    8: ["hamiltonian", "well", "realm", "energy", "potential"],
    9: ["spectral", "frequency", "fft", "fourier", "harmonic"],
    10: ["spin", "coherence", "alignment", "decoherence"],
    11: ["temporal", "time", "history", "accumulate", "memory"],
    12: ["harmonic wall", "safety score", "H(d", "governance score"],
    13: ["allow", "deny", "quarantine", "escalate", "decision", "governance"],
    14: ["audio", "telemetry", "signal", "output", "final"],
}


def load_book() -> str:
    """Load the full book text."""
    return BOOK_PATH.read_text(encoding="utf-8")


def split_chapters(text: str) -> list[dict]:
    """Split book into chapters with metadata."""
    chapter_pattern = re.compile(r"^# (Chapter \d+: .+)$", re.MULTILINE)
    matches = list(chapter_pattern.finditer(text))

    chapters = []
    for i, match in enumerate(matches):
        title = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        chapters.append({"title": title, "number": i + 1, "body": body})

    return chapters


def split_passages(chapter_body: str, target_words: int = 300) -> list[str]:
    """Split a chapter into passage-level chunks.

    Uses paragraph boundaries and scene breaks (---) to find natural split points.
    Target ~300 words per passage for rich but focused training records.
    """
    # Split on scene breaks first
    scenes = re.split(r"\n---\n", chapter_body)

    passages = []
    for scene in scenes:
        paragraphs = [p.strip() for p in scene.split("\n\n") if p.strip()]
        current = []
        current_words = 0

        for para in paragraphs:
            word_count = len(para.split())
            current.append(para)
            current_words += word_count

            if current_words >= target_words:
                passages.append("\n\n".join(current))
                current = []
                current_words = 0

        if current:
            passages.append("\n\n".join(current))

    return [p for p in passages if len(p.split()) >= 50]  # Skip tiny fragments


def detect_tongues(text: str) -> dict[str, float]:
    """Score tongue presence in a passage."""
    text_lower = text.lower()
    scores = {}
    for code, signals in TONGUE_SIGNALS.items():
        hits = sum(1 for s in signals if s in text_lower)
        scores[code] = round(min(hits / max(len(signals) * 0.3, 1), 1.0), 3)
    # Normalize so at least something registers
    total = sum(scores.values())
    if total == 0:
        scores = {k: 0.1 for k in scores}
    return scores


def detect_layers(text: str) -> list[int]:
    """Detect which pipeline layers a passage touches."""
    text_lower = text.lower()
    layers = []
    for layer, signals in LAYER_SIGNALS.items():
        if any(s in text_lower for s in signals):
            layers.append(layer)
    return sorted(layers) if layers else [0]


def detect_axioms(text: str) -> list[str]:
    """Detect axiom references."""
    text_lower = text.lower()
    axioms = []
    if any(w in text_lower for w in ["norm", "preserv", "unitar", "conserv"]):
        axioms.append("A1_unitarity")
    if any(w in text_lower for w in ["local", "spatial", "bound", "contain"]):
        axioms.append("A2_locality")
    if any(w in text_lower for w in ["causal", "time", "order", "before", "after", "sequence"]):
        axioms.append("A3_causality")
    if any(w in text_lower for w in ["symmetr", "invarian", "gauge", "balance"]):
        axioms.append("A4_symmetry")
    if any(w in text_lower for w in ["compos", "pipeline", "chain", "end-to-end"]):
        axioms.append("A5_composition")
    return axioms if axioms else ["general"]


def make_record(system: str, user: str, assistant: str, tongues: dict, layers: list,
                axioms: list, difficulty: float, augmentation: str, tags: list) -> dict:
    """Build a dimensionally-tagged SFT record."""
    dominant = max(tongues, key=tongues.get)
    tongue_str = " ".join(f"{t}={v}" for t, v in tongues.items())
    layer_str = ",".join(f"L{l}" for l in layers)
    axiom_str = ",".join(axioms)

    dim_header = (
        f"[TONGUES: {tongue_str}]\n"
        f"[LAYERS: {layer_str}]\n"
        f"[AXIOMS: {axiom_str}]\n"
        f"[DIFFICULTY: {difficulty}]"
    )
    enriched_system = f"{dim_header}\n{system}"

    return {
        "messages": [
            {"role": "system", "content": enriched_system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tongue_weights": tongues,
        "dominant_tongue": dominant,
        "layers": layers,
        "axioms": axioms,
        "difficulty": difficulty,
        "augmentation": augmentation,
        "tags": tags,
        "source_hash": hashlib.md5(user.encode()).hexdigest()[:8],
    }


SYS_BASE = (
    "You are Polly, an AI assistant trained on the SCBE-AETHERMOORE governance framework. "
    "You teach the Sacred Tongues through the lore of Aethermoor and Marcus Chen's journey. "
    "Every scene in the Six Tongues Protocol demonstrates real concepts from the 14-layer pipeline."
)

SYS_LORE = (
    "You are Polly, the corvid keeper of Aethermoor. You teach the Sacred Tongues "
    "by telling stories from the world itself -- every event in Aethermoor demonstrates "
    "a governance concept, because the world RUNS on the Six Tongues."
)

SYS_TECHNICAL = (
    "You are Polly, an AI assistant that bridges the lore of Aethermoor with the technical "
    "reality of the SCBE-AETHERMOORE codebase. When asked about a scene from the Six Tongues "
    "Protocol, you explain both what happens in the story AND what it means in the code."
)


def summarize_passage(passage: str, max_words: int = 150) -> str:
    """Create a concise summary of a passage for training answers.

    We don't want to dump raw book text as the answer -- we want
    teaching summaries that extract the concept.
    """
    sentences = re.split(r"(?<=[.!?])\s+", passage)
    # Take key sentences that aren't pure dialogue
    summary_sentences = []
    words = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Prefer sentences with tongue/concept keywords
        summary_sentences.append(s)
        words += len(s.split())
        if words >= max_words:
            break
    return " ".join(summary_sentences)


def extract_tongue_teaching(passage: str, tongues: dict) -> str | None:
    """If the passage explicitly teaches a tongue, extract that teaching."""
    dominant = max(tongues, key=tongues.get)
    if tongues[dominant] < 0.3:
        return None

    t = TONGUES[dominant]
    return (
        f"This passage demonstrates **{t['full']} ({dominant})** -- the {t['color']} tongue of "
        f"{t['domain']}. {t['full']} encodes '{t['essence']}' and carries a phi-weight of "
        f"{t['weight']} (phi^{list(TONGUES.keys()).index(dominant)}).\n\n"
        f"In the narrative, you can see {t['full']} at work: the characters are engaging with "
        f"the {t['domain'].lower()} dimension of the system. Every time the story touches "
        f"'{t['essence']}', that's {t['full']} speaking."
    )


def generate_records_for_passage(
    passage: str, chapter_title: str, chapter_num: int, passage_idx: int
) -> list[dict]:
    """Generate multiple SFT records from a single passage."""
    records = []
    tongues = detect_tongues(passage)
    layers = detect_layers(passage)
    axioms = detect_axioms(passage)
    dominant = max(tongues, key=tongues.get)
    dom_tongue = TONGUES[dominant]

    # Difficulty scales with chapter (later chapters = harder concepts)
    base_difficulty = round(min(0.2 + chapter_num * 0.025, 0.8), 2)

    # Record type 1: Narrative comprehension
    summary = summarize_passage(passage, max_words=120)
    records.append(make_record(
        SYS_BASE,
        f"What happens in {chapter_title} in the passage about "
        f"{dom_tongue['full']} ({dom_tongue['domain'].lower()})?",
        summary,
        tongues, layers, axioms,
        difficulty=base_difficulty,
        augmentation="book-narrative",
        tags=["book", "narrative", f"chapter-{chapter_num}", f"tongue-{dominant}"],
    ))

    # Record type 2: Tongue extraction (only if a tongue is clearly present)
    teaching = extract_tongue_teaching(passage, tongues)
    if teaching:
        records.append(make_record(
            SYS_LORE,
            f"What Sacred Tongue concept is being demonstrated in this scene from {chapter_title}?",
            teaching,
            tongues, layers, axioms,
            difficulty=round(base_difficulty + 0.1, 2),
            augmentation="book-tongue-extraction",
            tags=["book", "tongue-extraction", f"chapter-{chapter_num}", f"tongue-{dominant}"],
        ))

    # Record type 3: Technical bridge (every 2nd passage to avoid over-generation)
    if passage_idx % 2 == 0 and layers != [0]:
        layer_list = ", ".join(f"Layer {l}" for l in layers)
        records.append(make_record(
            SYS_TECHNICAL,
            f"How does this scene from {chapter_title} relate to the SCBE pipeline?",
            f"This scene touches {layer_list} in the 14-layer pipeline.\n\n"
            f"The dominant tongue is {dom_tongue['full']} ({dominant} -- {dom_tongue['domain']}), "
            f"which maps to the '{dom_tongue['essence']}' dimension of governance.\n\n"
            f"In the codebase, this corresponds to the tongue weight phi^"
            f"{list(TONGUES.keys()).index(dominant)} = {dom_tongue['weight']}, applied during "
            f"Layer 3 (Weighted Transform) before Poincare embedding in Layer 4.\n\n"
            f"The axioms in play are: {', '.join(axioms)}. "
            f"{'These axioms constrain how the pipeline processes this type of input.' if axioms != ['general'] else 'No specific axiom is directly demonstrated -- this is general pipeline flow.'}",
            tongues, layers, axioms,
            difficulty=round(base_difficulty + 0.15, 2),
            augmentation="book-technical-bridge",
            tags=["book", "technical-bridge", f"chapter-{chapter_num}", f"tongue-{dominant}"] + [f"layer-{l}" for l in layers],
        ))

    # Record type 4: Character perspective (Polly's view, every 3rd passage)
    if passage_idx % 3 == 0:
        records.append(make_record(
            SYS_LORE,
            f"Polly, tell me about what Marcus is learning in {chapter_title}.",
            f"In this part of the story, Marcus is encountering {dom_tongue['full']} -- "
            f"the {dom_tongue['color']} tongue. "
            f"That's the '{dom_tongue['essence']}' dimension.\n\n"
            f"Most newcomers to Aethermoor struggle with {dom_tongue['full']} because it requires "
            f"understanding not just WHAT something is, but {dom_tongue['essence']}. "
            f"Marcus the engineer approaches it through pattern recognition -- he sees the "
            f"architecture before he sees the magic, which is exactly how {dom_tongue['full']} "
            f"is meant to be learned.\n\n"
            f"The phi-weight of {dom_tongue['full']} is {dom_tongue['weight']}. "
            f"In the governance system, that means this tongue carries "
            f"{'foundational' if dominant == 'KO' else 'significant' if dominant in ('AV', 'RU') else 'substantial' if dominant == 'CA' else 'critical' if dominant == 'UM' else 'supreme'} "
            f"weight in any decision.",
            tongues, layers, axioms,
            difficulty=round(base_difficulty + 0.05, 2),
            augmentation="book-character-perspective",
            tags=["book", "character", "polly", f"chapter-{chapter_num}", f"tongue-{dominant}"],
        ))

    return records


def main():
    print("Loading The Six Tongues Protocol...")
    book_text = load_book()
    chapters = split_chapters(book_text)
    print(f"Found {len(chapters)} chapters")

    all_records = []

    for chapter in chapters:
        passages = split_passages(chapter["body"], target_words=300)
        print(f"  {chapter['title']}: {len(passages)} passages")

        for idx, passage in enumerate(passages):
            records = generate_records_for_passage(
                passage, chapter["title"], chapter["number"], idx
            )
            all_records.extend(records)

    # Write output
    out_path = OUT_DIR / "book_six_tongues_sft.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nBook SFT: {len(all_records)} records -> {out_path}")

    # Stats breakdown
    from collections import Counter
    aug_counts = Counter(r["augmentation"] for r in all_records)
    tongue_counts = Counter(r["dominant_tongue"] for r in all_records)
    chapter_counts = Counter()
    for r in all_records:
        for tag in r["tags"]:
            if tag.startswith("chapter-"):
                chapter_counts[tag] += 1

    print(f"\nRecord types:")
    for aug, count in aug_counts.most_common():
        print(f"  {aug:35s} {count}")

    print(f"\nDominant tongue distribution:")
    for tongue, count in tongue_counts.most_common():
        t = TONGUES[tongue]
        print(f"  {t['full']:20s} ({tongue}) {count}")

    print(f"\nChapter coverage:")
    for ch in sorted(chapter_counts.keys(), key=lambda x: int(x.split("-")[1])):
        print(f"  {ch:15s} {chapter_counts[ch]}")


if __name__ == "__main__":
    main()
