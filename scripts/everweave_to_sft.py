#!/usr/bin/env python3
"""
Everweave & Novel → SFT Training Data Converter
=================================================
Converts the Six Tongues Protocol novel (chapters 1-15),
Everweave DOCX campaign exports, and character CSVs into
structured SFT/DPO training pairs for fine-tuning.

Outputs:
  training-data/sft_novel.jsonl        — novel chapter pairs
  training-data/sft_everweave.jsonl    — campaign log pairs
  training-data/sft_characters.jsonl   — character/relationship pairs
  training-data/sft_glossary.jsonl     — glossary/term definition pairs

Usage:
  python scripts/everweave_to_sft.py [--novel PATH] [--docx PATH] [--csv PATH]
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_OUT = PROJECT_ROOT / "training-data"
TRAINING_OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class SFTPair:
    instruction: str
    response: str
    category: str = "story-lore"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "response": self.response,
            "category": self.category,
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "author": "Issac Davis",
                **self.metadata,
            },
            "id": f"sft-{self.category[:4]}-{uuid.uuid4().hex[:8]}",
        }


# ---------------------------------------------------------------------------
# Novel parser
# ---------------------------------------------------------------------------
CHAPTER_RE = re.compile(
    r"^(?:#{1,2}\s*)?Chapter\s+(\d+):\s*(.+)$", re.MULTILINE
)
SECTION_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


def parse_novel_text(text: str) -> List[Dict[str, str]]:
    """Split novel text into chapters with title and body."""
    chapters: List[Dict[str, str]] = []
    matches = list(CHAPTER_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Trim trailing appendix/glossary if it starts with # Appendix or # Epilogue
        for tag in ["# Appendix", "# Complete Chapter Summary", "# Glossary"]:
            idx = body.find(tag)
            if idx != -1:
                body = body[:idx].strip()
        chapters.append({
            "number": int(m.group(1)),
            "title": m.group(2).strip(),
            "body": body,
        })
    return chapters


def extract_tech_concepts(text: str) -> List[str]:
    """Pull SCBE technical concepts mentioned in text."""
    concepts = []
    markers = [
        "Harmonic Wall", "Poincare", "Byzantine", "consensus", "Echoes",
        "Tongue", "KO", "AV", "RU", "CA", "UM", "DR", "Fleet",
        "authentication", "Rogue", "Void Seed", "phi", "golden ratio",
        "fractal", "dimensional drift", "swarm", "Protocol",
        "Rite of Resonance", "Rite of Binding", "Tokenizer",
        "Mirror-Shift-Refactor", "MSR", "H(d,R)", "R^(d",
        "Seal-Breaking", "Storm formation", "Phalanx", "Lance", "Web",
    ]
    for m in markers:
        if m.lower() in text.lower():
            concepts.append(m)
    return concepts


def novel_to_sft(chapters: List[Dict[str, str]]) -> List[SFTPair]:
    """Generate SFT pairs from novel chapters."""
    pairs: List[SFTPair] = []

    for ch in chapters:
        num = ch["number"]
        title = ch["title"]
        body = ch["body"]
        concepts = extract_tech_concepts(body)

        # 1. Chapter summary pair
        # Truncate body for the response (first ~2000 chars as summary context)
        summary_body = body[:3000]
        # Find natural paragraph breaks
        paras = [p.strip() for p in summary_body.split("\n\n") if p.strip()]
        summary = " ".join(paras[:4])[:1500]

        pairs.append(SFTPair(
            instruction=f"Summarize Chapter {num}: '{title}' of The Six Tongues Protocol.",
            response=summary,
            category="story-lore",
            metadata={
                "origin": "six_tongues_novel",
                "chapter": num,
                "title": title,
                "concepts": concepts[:8],
            },
        ))

        # 2. Tech-mapping pair (if chapter has technical concepts)
        if len(concepts) >= 2:
            pairs.append(SFTPair(
                instruction=(
                    f"How does Chapter {num} ('{title}') map story elements "
                    f"to SCBE-AETHERMOORE technical architecture?"
                ),
                response=(
                    f"Chapter {num} illustrates these SCBE concepts through "
                    f"narrative: {', '.join(concepts[:6])}. "
                    + " ".join(paras[:3])[:1200]
                ),
                category="story-tech-mapping",
                metadata={
                    "origin": "six_tongues_novel",
                    "chapter": num,
                    "concepts": concepts,
                },
            ))

        # 3. Character interaction pairs (find dialogue)
        dialogue_lines = re.findall(
            r'"([^"]{15,})"', body
        )
        for dl in dialogue_lines[:5]:
            # Find speaker context (look back ~100 chars)
            idx = body.find(dl)
            context = body[max(0, idx - 150):idx].strip()
            # Try to find speaker name
            speaker_match = re.search(
                r'(Marcus|Polly|Eldrin|Zara|Lyra|Venn|Ame|Aisha)\b',
                context
            )
            speaker = speaker_match.group(1) if speaker_match else "Unknown"

            pairs.append(SFTPair(
                instruction=(
                    f"In the world of Aethermoor, what does {speaker} say "
                    f"about the Protocol in Chapter {num}?"
                ),
                response=f'{speaker} says: "{dl}"',
                category="story-dialogue",
                metadata={
                    "origin": "six_tongues_novel",
                    "chapter": num,
                    "speaker": speaker,
                },
            ))

        # 4. Key scene pairs (look for Protocol status blocks)
        status_blocks = re.findall(
            r'\[([^\]]+)\]', body
        )
        for sb in status_blocks[:3]:
            if len(sb) > 15:
                pairs.append(SFTPair(
                    instruction=f"What Protocol status event occurs in Chapter {num}?",
                    response=f"Protocol event: [{sb}]",
                    category="story-protocol",
                    metadata={
                        "origin": "six_tongues_novel",
                        "chapter": num,
                    },
                ))

        # 5. Spell/magic system pairs
        spell_patterns = re.findall(
            r"(?:spoke|speaking|declared|speak)[^.]*?(?:KO|AV|RU|CA|UM|DR)[^.]+\.",
            body, re.IGNORECASE
        )
        for sp in spell_patterns[:3]:
            sp = sp.strip()
            if len(sp) > 30:
                pairs.append(SFTPair(
                    instruction=(
                        f"Describe a spell casting example from Chapter {num} "
                        f"of The Six Tongues Protocol."
                    ),
                    response=sp[:500],
                    category="story-magic",
                    metadata={
                        "origin": "six_tongues_novel",
                        "chapter": num,
                    },
                ))

    return pairs


# ---------------------------------------------------------------------------
# Everweave DOCX parser
# ---------------------------------------------------------------------------
def parse_everweave_docx(path: Path) -> List[SFTPair]:
    """Parse an Everweave campaign export DOCX into SFT pairs.

    The DOCX uses DM/Izack turn-based format:
      DM: <narration>
      Izack: <player action/dialogue>
      "What do you do?" = choice prompt
    """
    pairs: List[SFTPair] = []

    try:
        from docx import Document
    except ImportError:
        print("  [WARN] python-docx not installed, skipping DOCX parsing")
        return pairs

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    print(f"  Loaded {len(paragraphs)} paragraphs ({sum(len(p) for p in paragraphs)} chars)")

    # Parse into DM/Player turns
    turns: List[Dict[str, str]] = []
    current_speaker = ""
    current_text = ""

    for para in paragraphs:
        # Detect speaker change
        if para.startswith("DM:"):
            if current_speaker and current_text:
                turns.append({"speaker": current_speaker, "text": current_text.strip()})
            current_speaker = "DM"
            current_text = para[3:].strip()
        elif para.startswith("Izack:"):
            if current_speaker and current_text:
                turns.append({"speaker": current_speaker, "text": current_text.strip()})
            current_speaker = "Izack"
            current_text = para[6:].strip()
        else:
            # Continuation of current speaker
            current_text += " " + para

    # Flush last turn
    if current_speaker and current_text:
        turns.append({"speaker": current_speaker, "text": current_text.strip()})

    print(f"  Parsed {len(turns)} turns (DM + Izack)")

    # Generate SFT pairs from turn sequences
    char_names = [
        "Izack", "Polly", "Clay", "Eldrin", "Aria", "Zara",
        "Kael", "Alexander", "Grey", "Marta", "Rupert", "Shimmer",
        "Malzeth", "Veyra", "Lyra", "Mira", "Senna",
        "Clayborn", "Avalon", "Aethermoor",
    ]

    scene_num = 0
    for i in range(len(turns) - 1):
        dm_turn = turns[i]
        next_turn = turns[i + 1]

        # Pattern 1: DM narrates -> Izack responds (SFT pair)
        if dm_turn["speaker"] == "DM" and next_turn["speaker"] == "Izack":
            scene_num += 1
            dm_text = dm_turn["text"][:1200]
            player_text = next_turn["text"][:800]

            # Skip very short turns
            if len(dm_text) < 30 or len(player_text) < 15:
                continue

            # Main SFT pair: narration -> player action
            pairs.append(SFTPair(
                instruction=(
                    f"In the Everweave campaign, the DM describes: {dm_text} "
                    f"What does Izack do?"
                ),
                response=player_text,
                category="everweave-action",
                metadata={
                    "origin": "everweave_export",
                    "scene": scene_num,
                    "source_file": path.name,
                },
            ))

            # If DM text contains a question/prompt, also make a choice pair
            if "what" in dm_text.lower()[-100:] or "?" in dm_text[-50:]:
                pairs.append(SFTPair(
                    instruction=(
                        f"The Everweave DM asks: "
                        + dm_text[dm_text.rfind(".",-200)+1:].strip()[:300]
                    ),
                    response=f"Izack decides: {player_text[:500]}",
                    category="everweave-choice",
                    metadata={
                        "origin": "everweave_export",
                        "scene": scene_num,
                    },
                ))

        # Pattern 2: DM narration with world-building (standalone lore)
        if dm_turn["speaker"] == "DM" and len(dm_turn["text"]) > 200:
            mentioned = [n for n in char_names if n.lower() in dm_turn["text"].lower()]
            if mentioned and scene_num % 5 == 0:  # Sample every 5th scene
                pairs.append(SFTPair(
                    instruction=(
                        f"Describe what happens with {', '.join(mentioned[:3])} "
                        f"in the Everweave Spiralverse campaign."
                    ),
                    response=dm_turn["text"][:1200],
                    category="everweave-lore",
                    metadata={
                        "origin": "everweave_export",
                        "scene": scene_num,
                        "characters": mentioned,
                    },
                ))

    # Generate character-specific interaction pairs
    # Group turns by which characters are mentioned
    for char in ["Polly", "Clay", "Eldrin", "Aria", "Zara", "Kael", "Alexander"]:
        char_turns = [t for t in turns if char.lower() in t["text"].lower()]
        if char_turns:
            # Take first appearance
            first = char_turns[0]["text"][:800]
            pairs.append(SFTPair(
                instruction=f"When does {char} first appear in the Everweave campaign?",
                response=f"{char}'s first appearance: {first}",
                category="everweave-character-intro",
                metadata={"origin": "everweave_export", "character": char},
            ))
            # Take a notable interaction (longest turn mentioning them)
            longest = max(char_turns, key=lambda t: len(t["text"]))
            pairs.append(SFTPair(
                instruction=f"Describe a notable scene with {char} in the Everweave campaign.",
                response=longest["text"][:1200],
                category="everweave-character-scene",
                metadata={"origin": "everweave_export", "character": char},
            ))

    return pairs


# ---------------------------------------------------------------------------
# Character CSV parser
# ---------------------------------------------------------------------------
def parse_character_csv(path: Path) -> List[SFTPair]:
    """Parse the Everweave merchandise concepts CSV as character bible."""
    pairs: List[SFTPair] = []

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        name = row.get("Character", row.get("Name", "")).strip()
        if not name:
            continue

        # Build character description from available fields
        fields = {k: v for k, v in row.items() if v and v.strip()}
        desc_parts = []
        for k, v in fields.items():
            if k.lower() not in ("character", "name"):
                desc_parts.append(f"{k}: {v.strip()}")
        desc = ". ".join(desc_parts)

        if len(desc) < 20:
            continue

        pairs.append(SFTPair(
            instruction=f"Describe the character {name} from the Spiralverse/Aethermoor lore.",
            response=desc[:1500],
            category="character-lore",
            metadata={
                "origin": "everweave_merchandise_csv",
                "character": name,
            },
        ))

    return pairs


# ---------------------------------------------------------------------------
# Character bible from user-provided structured text
# ---------------------------------------------------------------------------
CHARACTER_BIBLE = {
    "Izack Thorne": {
        "full_name": "Izack Thorne / Issac Relyth Danvovik-Sova",
        "role": "Protagonist, Dimensional Architect, Warlock King, Founder of Avalon Academy",
        "traits": "Curious scholar specializing in dimensional storage/transmutation. "
                  "Evolves from amnesiac castaway to revolutionary mage.",
        "family": "Husband to Aria Ravencrest. Father to Alexander, Lyra, Mira, Senna, Kael.",
        "allies": "Mentor to Zara. Bonded with Polly.",
        "tongue": "CA (Cassisivadan)",
        "theme": "Growth from isolation to collaboration. Author self-insert.",
    },
    "Aria Ravencrest": {
        "full_name": "Aria Ravencrest / Aria Luminara",
        "role": "Collaborative Researcher, Wife, Strategic Partner",
        "traits": "Pragmatic strategist with boundary magic. Heals through harmonic resonance.",
        "family": "Wife to Izack. Mother to Alexander, Lyra, Mira, Senna, Kael.",
        "tongue": "UM (Umbroth)",
        "theme": "Reform vs. revolution. Emotional vulnerability in mages.",
    },
    "Alexander": {
        "role": "Son, Young Mage, Diplomat",
        "traits": "Prodigy with Third Thread/integration magic. Heart-bonded with "
                  "Malzeth'irun (Shimmer). Diplomatic and empathetic.",
        "family": "Son of Izack & Aria. Bonded with Malzeth'irun.",
        "tongue": "CA (Cassisivadan)",
        "theme": "Next-generation evolution. Convergence through education.",
    },
    "Kael": {
        "role": "Son, Time-Sensitive Mage",
        "traits": "Time-sensitive abilities from Timeweavers lineage. "
                  "Drawn to shadow path (Umbroth) despite father's light.",
        "family": "Son of Izack & Aria. Youngest.",
        "tongue": "UM (Umbroth)",
        "theme": "Identity beyond parents' legacy. Temporal nuances.",
    },
    "Polly": {
        "role": "Familiar, Chronicler, Polydimensional Manifestation",
        "traits": "Sarcastic raven with runic feathers. Sentient guide. "
                  "Fifth Circle Keeper of the Archives. 'Recording History Before It Forgets Itself'.",
        "family": "Bonded to Izack.",
        "tongue": "KO (Kor'aelin)",
        "theme": "Meta-narrator. Wisdom through sarcasm. Pays forward mentorship.",
    },
    "Clay": {
        "full_name": "Clayborn / Clay",
        "role": "Sentient Construct, Companion",
        "traits": "Mud/magic golem learning song/soul. Harmonic subrunes.",
        "family": "Created by Izack. Ally to Grey.",
        "tongue": "RU (Runethic)",
        "theme": "Creation and consciousness. Naps on desks.",
    },
    "Zara": {
        "role": "Apprentice, Dragonkin Mage",
        "traits": "Third Thread bearer. Heals/suppressed magic specialist. "
                  "Dragon-blooded prodigy. Fire-Breathing and Code-Breaking.",
        "family": "Apprentice to Izack. Ally to Aria/Polly.",
        "tongue": "DR (Draumric)",
        "theme": "Inclusion vs. erasure.",
    },
    "Eldrin": {
        "role": "Cartographer, Research Companion, Archive Master",
        "traits": "Weathered scholar. Maps magical resonances. Silver hair.",
        "family": "Ally to Izack.",
        "tongue": "AV (Avali)",
        "theme": "Bridge between old and new magic.",
    },
    "Grey": {
        "role": "Threshold Guardian, Warrior",
        "traits": "Stoic protector. Defensive magic focus. Guards portals.",
        "family": "Ally to Izack/Clay.",
        "tongue": "RU (Runethic)",
        "theme": "Reform over revolution. Military nuance.",
    },
    "Malzeth'irun / Shimmer": {
        "role": "Dragon Companion",
        "traits": "True power unlocked in bonding rite. Integration magic.",
        "family": "Bonded to Alexander.",
        "tongue": "DR (Draumric)",
        "theme": "Post-singularity evolution.",
    },
    "Veyra": {
        "role": "Antagonist - Shadow at the Gates",
        "traits": "Chaos/randomness seeker from Pattern Dancers. "
                  "Believes beauty lies in entropy, not order.",
        "tongue": "UM (Umbroth)",
        "theme": "Beauty in chaos. Potential reform arc.",
    },
    "Marcus Chen": {
        "role": "Isekai Protagonist (Novel), Systems Engineer from Earth",
        "traits": "San Francisco systems engineer. Isekai'd to Aethermoor. "
                  "Rises from Seventh Circle refugee to Third Circle Keeper. "
                  "Proves phi-dimensional convergence theorem.",
        "tongue": "Multi-tongue (starts with RU affinity)",
        "theme": "Outsiders make the best defenders. Same war, different world.",
    },
}


def character_bible_to_sft() -> List[SFTPair]:
    """Generate SFT pairs from the character bible."""
    pairs: List[SFTPair] = []

    for name, info in CHARACTER_BIBLE.items():
        # Character description pair
        desc = ". ".join(f"{k}: {v}" for k, v in info.items())
        pairs.append(SFTPair(
            instruction=f"Describe the character {name} from the Spiralverse/Aethermoor.",
            response=desc,
            category="character-bible",
            metadata={"origin": "character_bible", "character": name},
        ))

        # Relationship pairs
        if "family" in info:
            pairs.append(SFTPair(
                instruction=f"What are {name}'s relationships in the Spiralverse?",
                response=info["family"],
                category="character-relationship",
                metadata={"origin": "character_bible", "character": name},
            ))

        # Tongue affinity pairs
        if "tongue" in info:
            pairs.append(SFTPair(
                instruction=f"What Sacred Tongue is {name} affiliated with?",
                response=f"{name}'s tongue affinity: {info['tongue']}. {info.get('traits', '')}",
                category="character-tongue",
                metadata={"origin": "character_bible", "character": name},
            ))

    # Cross-character relationship pairs
    pairs.append(SFTPair(
        instruction="List Izack Thorne's children and their magical abilities.",
        response=(
            "Izack and Aria's children: "
            "1) Alexander - Third Thread integration magic prodigy, bonded with dragon Shimmer. "
            "2) Lyra - Harmony/growth focus, emerging mage. "
            "3) Mira - Pattern dancer affinity, sees magic as dance. "
            "4) Senna - Growth Shaper, creative life energy. "
            "5) Kael - Timeweaver lineage, drawn to Umbroth shadow path."
        ),
        category="character-family",
        metadata={"origin": "character_bible"},
    ))

    pairs.append(SFTPair(
        instruction="How does Marcus Chen relate to Izack Thorne in the Spiralverse?",
        response=(
            "Marcus Chen is the isekai protagonist of The Six Tongues Protocol novel. "
            "He is a systems engineer from Earth who is transported to Aethermoor. "
            "Izack Thorne is the protagonist of the Everweave campaign -- a native of "
            "the Spiralverse who builds Avalon Academy. Both characters defend the "
            "Protocol through their unique perspectives: Marcus as an outsider-engineer, "
            "Izack as a dimensional architect. Their stories are parallel narratives "
            "in the same world."
        ),
        category="character-crossover",
        metadata={"origin": "character_bible"},
    ))

    return pairs


# ---------------------------------------------------------------------------
# Glossary extractor
# ---------------------------------------------------------------------------
GLOSSARY = {
    "The Protocol": "Fundamental system governing reality in Aethermoor. Aggregate intelligence powered by distributed consensus of Echoes. Verifies existence every 0.3 seconds.",
    "Echoes": "Autonomous verification agents forming the Protocol's distributed swarm. Each carries a fragment of decision logic and votes on authentication.",
    "Harmonic Wall": "The Protocol's trust model as Poincare disk. H(d,R) = R^(d^2) cost scaling.",
    "Six Sacred Tongues": "KO (Control), AV (Transport), RU (Policy), CA (Compute), UM (Security), DR (Schema). Domain-separated authorization channels.",
    "KO (Kor'aelin)": "Control Tongue. Domain of intent and high-level commands. Weight 1.000. Phase 0. Elvish-Korean hybrid.",
    "AV (Avali)": "Transport Tongue. Domain of movement and data flow. Weight 1.618 (phi). Phase pi/3. Romance-influenced trade pidgin.",
    "RU (Runethic)": "Policy Tongue. Domain of permissions and oaths. Weight 2.618 (phi^2). Phase 2pi/3. Archaic ritualistic.",
    "CA (Cassisivadan)": "Compute Tongue. Domain of encryption and transformation. Weight 4.236 (phi^3). Phase pi. Recursive joy.",
    "UM (Umbroth)": "Security Tongue. Domain of concealment and severance. Weight 6.854 (phi^4). Phase 4pi/3. Guttural concealment.",
    "DR (Draumric)": "Schema Tongue. Domain of structure and authentication. Weight 11.090 (phi^5). Phase 5pi/3. Percussive hammer-rhythm.",
    "Fleet": "Six autonomous drones, each attuned to one Sacred Tongue, coordinating through swarm consensus.",
    "Void Seed": "Collapsed remnant of failed centralized Protocol that tried to become God 10,000 years ago. Contained but patient.",
    "Rogue Agent": "Adversary who subverts the Protocol through forged authentication or social engineering.",
    "Byzantine Fault Tolerance": "Distributed consensus principle requiring 2/3 honest nodes. Foundation of Aethermoor's security.",
    "Dimensional Drift": "Offset between a person's native frequency and Aethermoor's baseline, measured in harmonics.",
    "Phi-Dimensional Signature": "Fractal dimension of authenticated trajectories through protocol space. Legitimate users converge to phi = 1.618.",
    "Mirror-Shift-Refactor": "The Protocol's decision algebra. M (mirror swap), S (rotation by phi), Pi (projection to valid manifold), 0 (zero-gravity hold).",
    "Rite of Resonance": "Ritual speaking all six Tongues to declare a fundamental truth. Reduces dimensional drift.",
    "Rite of Binding": "Ritual severing ties to home dimension. Achieves native authentication (R = 1.000).",
    "Aethermoor": "Floating island world governed by the Protocol. Contains the Archives, Avalon Academy, World Tree (Pollyoneth).",
    "Avalon Academy": "Founded by Izack Thorne. Center of magical education in Aethermoor.",
    "World Tree (Pollyoneth)": "The root network connecting 48 realms. Named for Polly.",
    "Aether Veins": "Root network of the World Tree Protocol connecting 48 realms.",
    "Sacred Tongue Tokenizer": "6x256 bijective token alphabet. Each tongue has 16 prefix x 16 suffix tokens. Deterministic byte mapping.",
    "GeoSeal": "Context-aware envelope with concentric policy rings for encoding/wrapping messages.",
    "Concentric Ring Policy": "Outer ring = runic layer (symbolic concepts). Inner ring = particle layer (spoken grammar). Dual-layer key.",
}


def glossary_to_sft() -> List[SFTPair]:
    """Convert glossary terms to SFT pairs."""
    pairs: List[SFTPair] = []
    for term, definition in GLOSSARY.items():
        pairs.append(SFTPair(
            instruction=f"Define '{term}' in the context of SCBE-AETHERMOORE / Aethermoor.",
            response=f"{term}: {definition}",
            category="glossary",
            metadata={"origin": "glossary", "term": term},
        ))
    return pairs


# ---------------------------------------------------------------------------
# Novel text loader (from markdown file or stdin)
# ---------------------------------------------------------------------------
def load_novel_from_file(path: Path) -> str:
    """Load novel text from a markdown file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_novel_from_raw_files() -> str:
    """Try to load novel from known locations."""
    candidates = [
        PROJECT_ROOT / "training" / "raw" / "six_tongues_full_wiki_git_20260219T031923Z.md",
        PROJECT_ROOT / "training" / "raw" / "six_tongues_full_wiki_git_20260218T053842Z.md",
        PROJECT_ROOT / "training" / "raw" / "six_tongues_full_wiki_20260218T053758Z.md",
    ]
    for c in candidates:
        if c.exists():
            text = c.read_text(encoding="utf-8")
            if "Chapter 1" in text:
                return text
    return ""


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run(
    novel_path: Optional[Path] = None,
    docx_path: Optional[Path] = None,
    csv_path: Optional[Path] = None,
) -> Dict[str, int]:
    """Run the full conversion pipeline."""
    stats: Dict[str, int] = {}

    # 1. Novel → SFT
    print("\n[1/4] Processing novel...")
    novel_text = ""
    if novel_path and novel_path.exists():
        novel_text = load_novel_from_file(novel_path)
    else:
        novel_text = load_novel_from_raw_files()

    if novel_text and "Chapter" in novel_text:
        chapters = parse_novel_text(novel_text)
        novel_pairs = novel_to_sft(chapters)
        out_novel = TRAINING_OUT / "sft_novel.jsonl"
        with open(out_novel, "w", encoding="utf-8") as f:
            for p in novel_pairs:
                f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
        stats["novel_pairs"] = len(novel_pairs)
        stats["novel_chapters"] = len(chapters)
        print(f"  {len(chapters)} chapters -> {len(novel_pairs)} SFT pairs -> {out_novel.name}")
    else:
        print("  [SKIP] No novel text found")
        stats["novel_pairs"] = 0

    # 2. Everweave DOCX → SFT
    print("\n[2/4] Processing Everweave DOCX...")
    if docx_path is None:
        docx_path = Path("C:/Users/issda/OneDrive/Downloads/everweave-export-7 (2).docx")
    if docx_path.exists():
        ew_pairs = parse_everweave_docx(docx_path)
        if ew_pairs:
            out_ew = TRAINING_OUT / "sft_everweave.jsonl"
            with open(out_ew, "w", encoding="utf-8") as f:
                for p in ew_pairs:
                    f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
            stats["everweave_pairs"] = len(ew_pairs)
            print(f"  {len(ew_pairs)} SFT pairs -> {out_ew.name}")
        else:
            stats["everweave_pairs"] = 0
            print("  [WARN] DOCX parsed but no pairs extracted")
    else:
        stats["everweave_pairs"] = 0
        print(f"  [SKIP] DOCX not found: {docx_path}")

    # 3. Character CSV + Bible → SFT
    print("\n[3/4] Processing characters...")
    char_pairs: List[SFTPair] = []

    if csv_path is None:
        csv_path = Path("C:/Users/issda/OneDrive/Downloads/everweave_merchandise_concepts.csv")
    if csv_path.exists():
        char_pairs.extend(parse_character_csv(csv_path))

    char_pairs.extend(character_bible_to_sft())

    out_chars = TRAINING_OUT / "sft_characters.jsonl"
    with open(out_chars, "w", encoding="utf-8") as f:
        for p in char_pairs:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
    stats["character_pairs"] = len(char_pairs)
    print(f"  {len(char_pairs)} SFT pairs -> {out_chars.name}")

    # 4. Glossary → SFT
    print("\n[4/4] Processing glossary...")
    gloss_pairs = glossary_to_sft()
    out_gloss = TRAINING_OUT / "sft_glossary.jsonl"
    with open(out_gloss, "w", encoding="utf-8") as f:
        for p in gloss_pairs:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
    stats["glossary_pairs"] = len(gloss_pairs)
    print(f"  {len(gloss_pairs)} SFT pairs -> {out_gloss.name}")

    # Summary
    total = sum(stats.values()) - stats.get("novel_chapters", 0)
    stats["total_pairs"] = total
    print(f"\n{'='*50}")
    print(f"  TOTAL: {total} SFT pairs generated")
    for k, v in stats.items():
        if k != "total_pairs":
            print(f"    {k}: {v}")
    print(f"{'='*50}\n")

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Everweave & Novel -> SFT converter")
    parser.add_argument("--novel", type=Path, default=None, help="Path to novel markdown")
    parser.add_argument("--docx", type=Path, default=None, help="Path to Everweave DOCX export")
    parser.add_argument("--csv", type=Path, default=None, help="Path to character CSV")
    args = parser.parse_args()

    run(novel_path=args.novel, docx_path=args.docx, csv_path=args.csv)
