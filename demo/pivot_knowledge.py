#!/usr/bin/env python3
"""
Pivot Knowledge — NPC Dialogue System for Aethermoor RPG
=========================================================
Branching dialogue graphs where every NPC conversation generates
SFT training pairs. Each NPC has a tongue affinity that colors their
speech patterns and determines which Sacred Language encoding applies.

Sacred Tongues:
  KO (Kor'aelin)    — Authority / Control
  AV (Avali)        — Transport / Messaging
  RU (Runethic)     — Policy / Constraints
  CA (Cassisivadan) — Compute / Encryption
  UM (Umbroth)      — Security / Secrets
  DR (Draumric)     — Schema / Authentication

Training data flows out as JSONL:
  Every topic pivot, every dialogue exchange, every sacred-language
  encoding becomes an instruction-response pair for fine-tuning.
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Topic — a single node in an NPC's dialogue graph
# ---------------------------------------------------------------------------
@dataclass
class Topic:
    """A conversation topic within an NPC's knowledge graph.

    Each topic belongs to a Sacred Tongue domain and contains template
    responses, pivot connections to other topics, and trigger keywords.
    """
    id: str
    name: str
    tongue: str                     # KO / AV / RU / CA / UM / DR
    responses: List[str]            # Template response strings
    pivot_to: List[str]             # Topic IDs this can branch to
    keywords: List[str]             # Words that trigger this topic


# ---------------------------------------------------------------------------
# PivotKnowledge — branching dialogue controller for a single NPC
# ---------------------------------------------------------------------------
class PivotKnowledge:
    """Manages a single NPC's topic graph, tracks conversation flow,
    and generates SFT training pairs from dialogue interactions."""

    def __init__(self, npc_id: str, npc_name: str, tongue_affinity: str) -> None:
        self.npc_id: str = npc_id
        self.npc_name: str = npc_name
        self.tongue_affinity: str = tongue_affinity
        self.topics: Dict[str, Topic] = {}
        self.current_topic: Optional[str] = None
        self.history: List[str] = []
        self.pair_count: int = 0

    def add_topic(self, topic: Topic) -> None:
        """Register a topic in this NPC's knowledge graph."""
        self.topics[topic.id] = topic
        # Auto-set the first added topic as current if none set
        if self.current_topic is None:
            self.current_topic = topic.id

    def get_response(self) -> str:
        """Return a random response from the currently active topic."""
        if self.current_topic is None or self.current_topic not in self.topics:
            return f"{self.npc_name} gazes at you in silence."
        topic = self.topics[self.current_topic]
        return random.choice(topic.responses)

    def get_pivots(self) -> List[Tuple[str, str]]:
        """Return available pivot targets as (topic_id, topic_name) pairs."""
        if self.current_topic is None or self.current_topic not in self.topics:
            return []
        topic = self.topics[self.current_topic]
        result: List[Tuple[str, str]] = []
        for tid in topic.pivot_to:
            if tid in self.topics:
                result.append((tid, self.topics[tid].name))
        return result

    def pivot(self, topic_id: str) -> str:
        """Switch the conversation to a new topic. Returns its initial response."""
        if topic_id not in self.topics:
            return f"{self.npc_name} tilts their head. 'I don't know about that.'"
        self.current_topic = topic_id
        self.history.append(topic_id)
        return self.get_response()

    def generate_training_pair(self) -> Dict[str, Any]:
        """Create an SFT instruction-response pair from the current state."""
        if self.current_topic is None or self.current_topic not in self.topics:
            topic_name = "unknown"
            topic_tongue = self.tongue_affinity
            response_text = f"{self.npc_name} has nothing to say."
            topic_id = "none"
        else:
            topic = self.topics[self.current_topic]
            topic_name = topic.name
            topic_tongue = topic.tongue
            response_text = self.get_response()
            topic_id = topic.id

        self.pair_count += 1

        return {
            "instruction": (
                f"You are {self.npc_name}, a {self.tongue_affinity} specialist "
                f"in Aethermoor. The topic is {topic_name}. How do you respond?"
            ),
            "response": response_text,
            "metadata": {
                "npc": self.npc_id,
                "tongue": topic_tongue,
                "topic": topic_id,
                "pivot_depth": len(self.history),
            },
        }


# ---------------------------------------------------------------------------
# SacredLanguages — 6 encoding systems, one per tongue
# ---------------------------------------------------------------------------
class SacredLanguages:
    """Encodes text using tongue-specific cipher methods.

    Each Sacred Tongue has a unique encoding that reflects its domain:
      KO  Kor'aelin    — Caesar cipher (authority shifts meaning)
      AV  Avali        — Reversed words + diacritics (transport scrambles order)
      RU  Runethic     — Rune vowel substitution (ancient policy glyphs)
      CA  Cassisivadan — Hex encoding (computational precision)
      UM  Umbroth      — Shadow script case-swap (secrets hide in plain sight)
      DR  Draumric     — Pig-latin variant (schema transforms structure)
    """

    # Rune substitution table for Runethic (RU)
    RUNE_MAP: Dict[str, str] = {
        "a": "\u16AB",  # \u16ab
        "e": "\u16D6",  # \u16d6
        "i": "\u16C1",  # \u16c1
        "o": "\u16DF",  # \u16df
        "u": "\u16A2",  # \u16a2
        "A": "\u16AB",
        "E": "\u16D6",
        "I": "\u16C1",
        "O": "\u16DF",
        "U": "\u16A2",
    }

    # Phi-based tongue weight suffixes for Draumric
    TONGUE_WEIGHT_SUFFIX: Dict[str, str] = {
        "KO": "-ko1.00",
        "AV": "-av1.62",
        "RU": "-ru2.62",
        "CA": "-ca4.24",
        "UM": "-um6.85",
        "DR": "-dr11.09",
    }

    def __init__(self) -> None:
        pass

    def encode(self, text: str, tongue: str) -> str:
        """Encode text using the cipher method of the given Sacred Tongue."""
        tongue = tongue.upper()
        if tongue == "KO":
            return self._encode_koraelin(text)
        elif tongue == "AV":
            return self._encode_avali(text)
        elif tongue == "RU":
            return self._encode_runethic(text)
        elif tongue == "CA":
            return self._encode_cassisivadan(text)
        elif tongue == "UM":
            return self._encode_umbroth(text)
        elif tongue == "DR":
            return self._encode_draumric(text)
        else:
            return text

    # -- KO: Caesar cipher shift by 7 --
    def _encode_koraelin(self, text: str) -> str:
        """Kor'aelin: Authority shifts every letter forward by 7."""
        result: List[str] = []
        for ch in text:
            if "a" <= ch <= "z":
                result.append(chr((ord(ch) - ord("a") + 7) % 26 + ord("a")))
            elif "A" <= ch <= "Z":
                result.append(chr((ord(ch) - ord("A") + 7) % 26 + ord("A")))
            else:
                result.append(ch)
        return "".join(result)

    # -- AV: Reverse each word + add diacritics --
    def _encode_avali(self, text: str) -> str:
        """Avali: Transport reverses word order and adds diacritics."""
        diacritics = {
            "a": "\u00e4", "e": "\u00eb", "i": "\u00ef",
            "o": "\u00f6", "u": "\u00fc",
        }
        words = text.split()
        encoded_words: List[str] = []
        for word in words:
            reversed_word = word[::-1]
            diac_word: List[str] = []
            for ch in reversed_word:
                diac_word.append(diacritics.get(ch.lower(), ch))
            encoded_words.append("".join(diac_word))
        return " ".join(encoded_words)

    # -- RU: Replace vowels with rune symbols --
    def _encode_runethic(self, text: str) -> str:
        """Runethic: Ancient policy runes replace every vowel."""
        result: List[str] = []
        for ch in text:
            if ch in self.RUNE_MAP:
                result.append(self.RUNE_MAP[ch])
            else:
                result.append(ch)
        return "".join(result)

    # -- CA: Each character -> 2-digit hex --
    def _encode_cassisivadan(self, text: str) -> str:
        """Cassisivadan: Computational hex encoding of each character."""
        return "".join(f"{ord(ch):02x}" for ch in text)

    # -- UM: Case swap + shadow separator --
    def _encode_umbroth(self, text: str) -> str:
        """Umbroth: Shadow script swaps case and inserts rune between words."""
        shadow_sep = "\u16CA"  # sowilo rune as shadow marker
        words = text.split()
        swapped: List[str] = []
        for word in words:
            swapped.append(word.swapcase())
        return shadow_sep.join(swapped)

    # -- DR: Pig-latin variant + tongue weight suffix --
    def _encode_draumric(self, text: str) -> str:
        """Draumric: Schema pig-latin (move first consonant cluster, add -aur)
        then append the tongue weight suffix."""
        vowels = set("aeiouAEIOU")
        words = text.split()
        encoded: List[str] = []
        for word in words:
            # Find first vowel position
            idx = 0
            while idx < len(word) and word[idx] not in vowels:
                idx += 1
            if idx == 0:
                # Word starts with vowel -> just add -aur
                pig = word + "aur"
            elif idx == len(word):
                # No vowels -> keep as is + aur
                pig = word + "aur"
            else:
                pig = word[idx:] + word[:idx] + "aur"
            encoded.append(pig)
        suffix = self.TONGUE_WEIGHT_SUFFIX.get("DR", "")
        return " ".join(encoded) + suffix


# ---------------------------------------------------------------------------
# TrainingDataGenerator — collects SFT pairs from dialogue interactions
# ---------------------------------------------------------------------------
class TrainingDataGenerator:
    """Accumulates training data from NPC dialogue interactions.

    Every pivot choice, every dialogue exchange, and every sacred-language
    encoding is recorded as an SFT instruction-response pair.
    """

    def __init__(self) -> None:
        self.pairs: List[Dict[str, Any]] = []
        self.languages: SacredLanguages = SacredLanguages()

    @property
    def total_pairs(self) -> int:
        """Total number of training pairs collected."""
        return len(self.pairs)

    def record_pivot(self, npc: PivotKnowledge, player_choice: str) -> None:
        """Record a topic pivot as training data, including sacred encoding."""
        pair = npc.generate_training_pair()

        # Add the player's pivot choice and sacred encoding
        tongue = pair["metadata"]["tongue"]
        encoded_response = self.languages.encode(pair["response"], tongue)

        pair["player_choice"] = player_choice
        pair["sacred_encoding"] = encoded_response
        pair["encoding_tongue"] = tongue
        pair["timestamp"] = time.time()

        self.pairs.append(pair)

    def record_dialogue(
        self,
        npc_name: str,
        tongue: str,
        player_input: str,
        npc_response: str,
    ) -> None:
        """Record a free-form dialogue exchange as training data."""
        encoded = self.languages.encode(npc_response, tongue)

        pair: Dict[str, Any] = {
            "instruction": (
                f"You are {npc_name} in Aethermoor. "
                f"The player says: '{player_input}'. "
                f"Respond in character."
            ),
            "response": npc_response,
            "sacred_encoding": encoded,
            "encoding_tongue": tongue,
            "metadata": {
                "npc": npc_name.lower().replace(" ", "_"),
                "tongue": tongue,
                "type": "dialogue",
                "pivot_depth": 0,
            },
            "timestamp": time.time(),
        }
        self.pairs.append(pair)

    def export_jsonl(self, path: str) -> None:
        """Write all collected pairs to a JSONL file."""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for pair in self.pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# NPC_TOPIC_GRAPHS — pre-built topic graphs for key Aethermoor NPCs
# ---------------------------------------------------------------------------

NPC_TOPIC_GRAPHS: Dict[str, Dict[str, Any]] = {

    # ------------------------------------------------------------------
    # POLLY — Raven familiar, Fifth Circle Keeper, KO affinity
    # ------------------------------------------------------------------
    "polly": {
        "tongue": "KO",
        "topics": [
            Topic(
                id="archives",
                name="The Wingscroll Archives",
                tongue="KO",
                responses=[
                    "These scrolls predate the First Tongue War. Every glyph is a "
                    "command frozen in authority -- read them wrong and they read you.",
                    "I have catalogued 14,233 scrolls. Each one a decree from a world "
                    "that no longer exists. That is the weight of Kor'aelin.",
                    "The Archives don't just store knowledge. They judge those who seek it. "
                    "Step carefully, scholar.",
                ],
                pivot_to=["history", "tongues_lore", "governance"],
                keywords=["archive", "scroll", "wingscroll", "library", "records"],
            ),
            Topic(
                id="history",
                name="World History",
                tongue="KO",
                responses=[
                    "Before the Six Tongues were codified, magic was raw chaos. "
                    "Kor'aelin was the first tongue spoken -- the word that brought order.",
                    "The Sundering of Avalon split reality into floating islands. "
                    "We ravens remember the ground. Most have forgotten.",
                    "History is not what happened. It is what was recorded, and by whom. "
                    "That is why the Archives matter more than any battlefield.",
                ],
                pivot_to=["archives", "tongues_lore", "familiar_bond"],
                keywords=["history", "past", "ancient", "before", "old", "sundering"],
            ),
            Topic(
                id="tongues_lore",
                name="Sacred Tongues Lore",
                tongue="KO",
                responses=[
                    "Six Tongues, six ways to shape reality. Kor'aelin commands. "
                    "Avali transports. Runethic constrains. Cassisivadan computes. "
                    "Umbroth conceals. Draumric authenticates.",
                    "The Tongues are not merely languages. They are governance protocols "
                    "woven into the fabric of Aethermoor itself. Speak one, and reality listens.",
                    "Each Tongue carries a phi-weight. KO is 1.0 -- the anchor. "
                    "DR is 11.09 -- the outermost ring. The further you reach, "
                    "the more it costs.",
                ],
                pivot_to=["archives", "history", "governance"],
                keywords=["tongue", "language", "magic", "sacred", "six", "phi"],
            ),
            Topic(
                id="governance",
                name="Governance Protocol",
                tongue="KO",
                responses=[
                    "The 14-layer pipeline exists because trust must be verified, "
                    "not assumed. Each layer is a question asked of every action.",
                    "ALLOW, QUARANTINE, DENY. Three words that hold Aethermoor together. "
                    "The Harmonic Wall makes transgression exponentially expensive.",
                    "Governance is not control. It is the architecture of fairness. "
                    "Without it, the strong devour the weak. I have seen it happen.",
                ],
                pivot_to=["tongues_lore", "archives", "familiar_bond"],
                keywords=["governance", "protocol", "layer", "pipeline", "rule", "law"],
            ),
            Topic(
                id="familiar_bond",
                name="Cosmic Familiar Bond",
                tongue="KO",
                responses=[
                    "Izack and I share more than magic. When he bleeds, I feel it. "
                    "When I fly, he dreams of sky. That is the Cosmic Familiar Bond.",
                    "A familiar is not a pet. We are mirrors of the mage's deeper self. "
                    "I am the part of Izack that remembers what he forgets.",
                    "The bond transcends tongues. It is older than Kor'aelin. "
                    "Some say it is the zeroth tongue -- the language before language.",
                ],
                pivot_to=["history", "tongues_lore", "archives"],
                keywords=["familiar", "bond", "izack", "raven", "partner", "connection"],
            ),
        ],
    },

    # ------------------------------------------------------------------
    # ELDRIN — Cartographic Thaumaturge, AV affinity
    # ------------------------------------------------------------------
    "eldrin": {
        "tongue": "AV",
        "topics": [
            Topic(
                id="cartography",
                name="Cartography",
                tongue="AV",
                responses=[
                    "Every map is a promise that the world has edges. "
                    "In Aethermoor, that promise is a beautiful lie.",
                    "I chart the spaces between floating islands. "
                    "The Avali tongue lets me feel the currents -- where things want to go.",
                    "A good map doesn't just show you where things are. "
                    "It shows you where they are going.",
                ],
                pivot_to=["ley_lines", "navigation", "portal_networks"],
                keywords=["map", "chart", "cartography", "draw", "territory"],
            ),
            Topic(
                id="ley_lines",
                name="Ley Lines",
                tongue="AV",
                responses=[
                    "Ley lines are the veins of Aethermoor. Avali magic flows "
                    "through them like blood. Disrupt one and an entire island drifts.",
                    "I have traced seventeen major ley confluences. Each one "
                    "hums in a different Avali frequency. The music is... indescribable.",
                    "Where ley lines cross, reality thins. That is where portals "
                    "form naturally. That is where I build my maps from.",
                ],
                pivot_to=["cartography", "portal_networks", "navigation"],
                keywords=["ley", "line", "energy", "flow", "vein", "current"],
            ),
            Topic(
                id="navigation",
                name="Dimensional Navigation",
                tongue="AV",
                responses=[
                    "Navigation between dimensions requires Avali fluency. "
                    "You must feel the direction -- north is a suggestion, not a fact.",
                    "I carry seventeen compasses. None of them point the same way. "
                    "That is how you know you are in the right place.",
                    "The Avali tongue encodes direction into sound. "
                    "Speak the right word and reality parts like a curtain.",
                ],
                pivot_to=["cartography", "ley_lines", "portal_networks", "maps"],
                keywords=["navigate", "direction", "dimension", "travel", "path"],
            ),
            Topic(
                id="portal_networks",
                name="Portal Networks",
                tongue="AV",
                responses=[
                    "The portal network predates the Academy. Someone -- or something "
                    "-- built stable wormholes between every major island.",
                    "Most portals are Avali constructs: words frozen in space. "
                    "Step through one and you hear the original incantation echo.",
                    "I maintain the Portal Registry. 847 known portals. "
                    "At least 200 more that refuse to be mapped.",
                ],
                pivot_to=["ley_lines", "navigation", "maps"],
                keywords=["portal", "wormhole", "gate", "teleport", "network"],
            ),
            Topic(
                id="maps",
                name="Famous Maps",
                tongue="AV",
                responses=[
                    "The Everweave Atlas is my life's work. Every page is a living "
                    "document -- the ink shifts as the islands drift.",
                    "The oldest map I have found shows Aethermoor before the Sundering. "
                    "One landmass. One tongue. One people. Hard to imagine.",
                    "My favorite map is the one that maps itself. A recursive "
                    "Avali construct. It is three layers deep and still drawing.",
                ],
                pivot_to=["cartography", "navigation", "ley_lines"],
                keywords=["map", "atlas", "everweave", "famous", "collection"],
            ),
            Topic(
                id="eldrin_philosophy",
                name="Cartographer's Philosophy",
                tongue="AV",
                responses=[
                    "'Not All Who Wander Are Lost, Some Are Mapping Magic.' "
                    "That is not just a motto. It is a way of life.",
                    "To chart the unknown, you must first accept that you know nothing. "
                    "The best maps are drawn by the most humble explorers.",
                ],
                pivot_to=["cartography", "maps", "navigation"],
                keywords=["philosophy", "wander", "lost", "purpose", "meaning"],
            ),
        ],
    },

    # ------------------------------------------------------------------
    # CLAY — Earth Sentinel, Sand Golem, RU affinity
    # ------------------------------------------------------------------
    "clay": {
        "tongue": "RU",
        "topics": [
            Topic(
                id="earth_magic",
                name="Earth Magic",
                tongue="RU",
                responses=[
                    "Earth magic is patient magic. You do not force stone. "
                    "You ask it politely and then wait. Sometimes for centuries.",
                    "The Runethic tongue speaks through stone. Each rune is a constraint "
                    "-- a rule the earth agrees to follow. Break the rule, break the spell.",
                    "I am made of sand and policy. Every grain follows a Runethic "
                    "constraint. That is why I hold together. Mostly.",
                ],
                pivot_to=["runethic_traditions", "rock_types", "strength"],
                keywords=["earth", "magic", "stone", "ground", "element"],
            ),
            Topic(
                id="runethic_traditions",
                name="Runethic Traditions",
                tongue="RU",
                responses=[
                    "The old rune-carvers built the floating islands. "
                    "Each island is held aloft by a Runethic constraint lattice. "
                    "Beautiful engineering. Beautiful patience.",
                    "Runethic tradition says: write the rule, test the rule, "
                    "then trust the rule. Policy without testing is just a wish.",
                    "The ancient golems were the first Runethic speakers. "
                    "We do not cast spells. We ratify agreements with the earth.",
                ],
                pivot_to=["earth_magic", "rock_types", "comfort"],
                keywords=["rune", "tradition", "ancient", "carve", "golem", "policy"],
            ),
            Topic(
                id="rock_types",
                name="Rock Types",
                tongue="RU",
                responses=[
                    "Basalt is dependable. Granite is stubborn. Sandstone is flexible. "
                    "Obsidian is... moody. I do not trust obsidian.",
                    "The best rocks for spellcasting are the ones that have been "
                    "patient the longest. Metamorphic. They have been through things.",
                    "My favorite rock is pumice. It floats! Like the islands. "
                    "Sometimes I sit in a bath and we float together.",
                ],
                pivot_to=["earth_magic", "comfort", "runethic_traditions"],
                keywords=["rock", "stone", "mineral", "crystal", "gem", "type"],
            ),
            Topic(
                id="comfort",
                name="Comfort and Naps",
                tongue="RU",
                responses=[
                    "A good nap is the most powerful spell in any tongue. "
                    "I have napped on every desk in the Academy. Rated them all.",
                    "Izack's pocket dimension is the coziest place in Aethermoor. "
                    "Warm sand, no wind, perfect nap conditions. Five stars.",
                    "Comfort is a Runethic principle. A stable foundation supports "
                    "everything above it. Rest is not laziness. It is load-bearing.",
                ],
                pivot_to=["rock_types", "strength", "earth_magic"],
                keywords=["nap", "sleep", "rest", "cozy", "comfort", "tired", "relax"],
            ),
            Topic(
                id="strength",
                name="Strength Training",
                tongue="RU",
                responses=[
                    "I train by lifting boulders. Then bigger boulders. "
                    "Then I ask the boulders to lift me. Mutual respect.",
                    "Strength without constraint is destruction. That is why "
                    "Runethic warriors are the most disciplined. We carry rules, not rage.",
                    "Golem Slam is not about power. It is about applying "
                    "the right amount of force to the right point. Precision strength.",
                ],
                pivot_to=["earth_magic", "runethic_traditions", "comfort"],
                keywords=["strong", "strength", "train", "fight", "power", "muscle"],
            ),
        ],
    },

    # ------------------------------------------------------------------
    # ARIA — Boundary Warden, Warrior-Scholar, UM affinity
    # ------------------------------------------------------------------
    "aria": {
        "tongue": "UM",
        "topics": [
            Topic(
                id="boundary_magic",
                name="Boundary Magic",
                tongue="UM",
                responses=[
                    "Boundaries are not walls. They are definitions. "
                    "My magic defines where one thing ends and another begins.",
                    "Umbroth boundary magic is the most precise art in Aethermoor. "
                    "One fraction of a radian off and you cut through the wrong dimension.",
                    "I draw boundaries that even light respects. "
                    "That is what the Harmonic Wall is, at its core -- "
                    "a boundary so absolute that crossing it costs infinity.",
                ],
                pivot_to=["mathematics", "combat_theory", "warrior_code"],
                keywords=["boundary", "edge", "limit", "border", "ward"],
            ),
            Topic(
                id="mathematics",
                name="Mathematics",
                tongue="CA",
                responses=[
                    "Mathematics is the only magic that never lies. "
                    "A proof is a proof. It does not care about your feelings.",
                    "The hyperbolic metric -- arcosh of one plus twice the "
                    "squared distance over the product of curvature terms -- "
                    "it is beautiful. It is the shape of fairness.",
                    "I teach my students: solve the equation first, then swing the sword. "
                    "A warrior who cannot calculate trajectories is just flailing.",
                ],
                pivot_to=["boundary_magic", "combat_theory", "family"],
                keywords=["math", "equation", "proof", "calculate", "theorem", "number"],
            ),
            Topic(
                id="combat_theory",
                name="Combat Theory",
                tongue="UM",
                responses=[
                    "Every fight is an equation. Attack vectors, defense matrices, "
                    "probability of evasion. I solve for victory before I draw my blade.",
                    "The Boundary Slash works because I have already mapped every "
                    "weak point mathematically. The sword just follows the proof.",
                    "Combat without theory is violence. Combat with theory is art. "
                    "I do not fight -- I demonstrate theorems.",
                ],
                pivot_to=["boundary_magic", "mathematics", "warrior_code"],
                keywords=["combat", "fight", "battle", "war", "sword", "strike"],
            ),
            Topic(
                id="family",
                name="Family",
                tongue="UM",
                responses=[
                    "Izack and I built something worth protecting. Alexander has his "
                    "father's brilliance. Kael has my stubbornness. Lyra has both our "
                    "gentleness. Mira dances between all of us.",
                    "Being a mother and a warrior are not contradictions. "
                    "They are the same thing -- protecting what matters most.",
                    "Kael worries me. He walks in shadows and hops between timelines. "
                    "But I know his heart. It is mine, after all.",
                ],
                pivot_to=["warrior_code", "mathematics", "boundary_magic"],
                keywords=["family", "children", "izack", "kael", "alexander", "lyra", "mira", "mother"],
            ),
            Topic(
                id="warrior_code",
                name="Warrior Code",
                tongue="UM",
                responses=[
                    "My code is simple: protect the boundary, solve the equation, "
                    "never strike first but always strike last.",
                    "The Ravencrest lineage carries an oath. We ward the boundaries "
                    "between what is and what should never be. I honor that oath daily.",
                    "'I Solve Problems With Magic AND Math.' "
                    "That is not a boast. That is a promise.",
                ],
                pivot_to=["combat_theory", "family", "boundary_magic"],
                keywords=["code", "honor", "oath", "warrior", "duty", "protect"],
            ),
            Topic(
                id="aria_teaching",
                name="Teaching at the Academy",
                tongue="UM",
                responses=[
                    "I teach Advanced Boundary Theory at Avalon Academy. "
                    "Half the students fear me. The other half want to be me. "
                    "Both reactions are acceptable.",
                    "The Academy is where warriors become scholars and scholars "
                    "become warriors. I refuse to let my students be only one.",
                ],
                pivot_to=["mathematics", "combat_theory", "warrior_code"],
                keywords=["teach", "academy", "student", "class", "lesson", "school"],
            ),
        ],
    },

    # ------------------------------------------------------------------
    # ZARA — Dragon-Coded Engineer, DR affinity
    # ------------------------------------------------------------------
    "zara": {
        "tongue": "DR",
        "topics": [
            Topic(
                id="dragon_engineering",
                name="Dragon Engineering",
                tongue="DR",
                responses=[
                    "Dragon engineering is where fire meets logic. "
                    "My circuits burn at 1400 degrees and they still compile clean.",
                    "The Draumric tongue authenticates every gear-rune I forge. "
                    "A false schema melts. A true schema sings.",
                    "I build machines that breathe fire and run code. "
                    "Some call it dangerous. I call it Tuesday.",
                ],
                pivot_to=["schema_forging", "fire_magic", "dragon_lore"],
                keywords=["engineer", "build", "machine", "construct", "design", "dragon"],
            ),
            Topic(
                id="schema_forging",
                name="Schema Forging",
                tongue="DR",
                responses=[
                    "A schema is a contract between maker and material. "
                    "Draumric authentication ensures neither side can cheat.",
                    "I forge schemas in dragonfire. The heat purifies the logic. "
                    "What survives the furnace is truth. What burns was a bug.",
                    "Every schema I forge carries my signature -- "
                    "a circuit pattern that looks like dragon scales. "
                    "Counterfeit that, I dare you.",
                ],
                pivot_to=["dragon_engineering", "code_breaking", "fire_magic"],
                keywords=["schema", "forge", "create", "pattern", "design", "blueprint"],
            ),
            Topic(
                id="fire_magic",
                name="Fire Magic",
                tongue="DR",
                responses=[
                    "Dragon blood runs at temperatures that would melt iron. "
                    "My fire is not destruction -- it is validation under extreme conditions.",
                    "The Dragonfire Compile spell literally compiles code in flame. "
                    "If the schema is valid, it crystallizes. If not, it burns. Simple.",
                    "Fire is the most honest element. It does not care about intent. "
                    "It only cares about structure. Feed it good structure, get good results.",
                ],
                pivot_to=["dragon_engineering", "dragon_lore", "schema_forging"],
                keywords=["fire", "flame", "burn", "heat", "dragon", "breath"],
            ),
            Topic(
                id="code_breaking",
                name="Code Breaking",
                tongue="CA",
                responses=[
                    "Breaking code is just forging in reverse. "
                    "I heat the schema until the flaws glow brighter than the structure.",
                    "Cassisivadan encryption is the hardest to crack. "
                    "But I have dragon patience and dragon heat. Nothing holds forever.",
                    "The best code breaker is someone who builds code. "
                    "You cannot find the weakness unless you understand the strength.",
                ],
                pivot_to=["schema_forging", "dragon_engineering", "dragon_lore"],
                keywords=["code", "break", "crack", "decrypt", "hack", "cipher"],
            ),
            Topic(
                id="dragon_lore",
                name="Dragon Lore",
                tongue="DR",
                responses=[
                    "The dragons were the first speakers of Draumric. "
                    "They did not learn it -- the tongue was shaped by their fire.",
                    "Alexander's dragon companion, Shimmer -- Malzeth'irun -- "
                    "is one of the last true Schema Dragons. We understand each other.",
                    "Dragon blood does not make you a dragon. "
                    "It makes you a bridge between fire and thought. "
                    "That is both a gift and a burden.",
                ],
                pivot_to=["fire_magic", "dragon_engineering", "schema_forging"],
                keywords=["dragon", "lore", "ancient", "blood", "heritage", "shimmer"],
            ),
            Topic(
                id="zara_ambition",
                name="Engineering Ambitions",
                tongue="DR",
                responses=[
                    "I am building a schema compiler that runs on pure dragonfire. "
                    "No circuits, no runes. Just authenticated flame. It will change everything.",
                    "My dream? A world where every machine authenticates itself. "
                    "No forged identities, no stolen schemas. Draumric truth, everywhere.",
                ],
                pivot_to=["dragon_engineering", "schema_forging", "code_breaking"],
                keywords=["dream", "future", "goal", "ambition", "plan", "hope"],
            ),
        ],
    },

    # ------------------------------------------------------------------
    # KAEL — Chrono-Shadow Drifter, UM affinity
    # ------------------------------------------------------------------
    "kael": {
        "tongue": "UM",
        "topics": [
            Topic(
                id="shadow_magic",
                name="Shadow Magic",
                tongue="UM",
                responses=[
                    "Shadow is not darkness. It is the space where light has a choice "
                    "and chooses not to go. I live in that choice.",
                    "Umbroth shadow magic lets me step between moments. "
                    "Not through time -- between it. In the gaps where nothing watches.",
                    "My mother says shadow is concealment. I think it is honesty. "
                    "In shadow, you are exactly who you are with nothing to hide behind.",
                ],
                pivot_to=["time_travel", "identity", "timeline_theory"],
                keywords=["shadow", "dark", "stealth", "hide", "concealment", "umbra"],
            ),
            Topic(
                id="time_travel",
                name="Time Travel",
                tongue="RU",
                responses=[
                    "Time is not a river. It is a tree with infinite branches. "
                    "I have climbed most of them. Some branches are dead.",
                    "The Timeweaver lineage lets me hop between timelines. "
                    "Past, future, parallel -- they are all just addresses to me.",
                    "Every time I travel, I leave a Temporal Echo. "
                    "A ghost of the version of me that did not jump. "
                    "Some of those echoes are still out there, living their own lives.",
                ],
                pivot_to=["shadow_magic", "timeline_theory", "identity"],
                keywords=["time", "travel", "past", "future", "timeline", "hop", "jump"],
            ),
            Topic(
                id="identity",
                name="Identity",
                tongue="UM",
                responses=[
                    "When you can be anyone, in any time, who are you really? "
                    "That question keeps me up at night. All the nights. Every timeline's night.",
                    "I am not evil. I am not good. I am searching. "
                    "Father walks in light. Mother guards boundaries. "
                    "I walk in the spaces they cannot see.",
                    "Some versions of me chose differently. Became different people. "
                    "I have met the version of me that gave up. "
                    "I decided I would not be him.",
                ],
                pivot_to=["shadow_magic", "time_travel", "rebellion"],
                keywords=["who", "identity", "self", "purpose", "meaning", "real"],
            ),
            Topic(
                id="timeline_theory",
                name="Timeline Theory",
                tongue="RU",
                responses=[
                    "The Runethic constraints that govern time are the most rigid "
                    "in all of magic. Break a timeline rule and reality folds you "
                    "out of existence. Ask me how I know.",
                    "Timelines branch at decision points. Every choice creates a fork. "
                    "I can see the forks. Sometimes I can choose which branch to ride.",
                    "My theory: all timelines converge at moments of absolute truth. "
                    "The Harmonic Wall is one such moment. You cannot lie to it "
                    "in any timeline.",
                ],
                pivot_to=["time_travel", "shadow_magic", "rebellion"],
                keywords=["theory", "branch", "fork", "converge", "timeline", "rule"],
            ),
            Topic(
                id="rebellion",
                name="Rebellion",
                tongue="UM",
                responses=[
                    "I do not rebel against my parents. I rebel against the idea "
                    "that I have to be a copy of them. My shadows are mine.",
                    "The Nightwhisper name is not inherited. I earned it. "
                    "In a timeline where no one could hear me, I whispered, "
                    "and the shadows answered.",
                    "Revolution is not destruction. It is rearranging the furniture "
                    "of reality until it makes sense to someone new.",
                ],
                pivot_to=["identity", "shadow_magic", "time_travel"],
                keywords=["rebel", "revolution", "fight", "resist", "defy", "against"],
            ),
            Topic(
                id="kael_family",
                name="Family Across Timelines",
                tongue="UM",
                responses=[
                    "Father is the same in every timeline. Brilliant and kind. "
                    "Mother is the same too. Fierce and precise. "
                    "That consistency... it anchors me.",
                    "Alexander and I are close in some timelines, rivals in others. "
                    "Lyra always smiles. Mira always dances. "
                    "Family is the constant across every branch.",
                ],
                pivot_to=["identity", "time_travel", "rebellion"],
                keywords=["family", "father", "mother", "brother", "sister", "home"],
            ),
        ],
    },
}


# ---------------------------------------------------------------------------
# build_npc_knowledge — factory function
# ---------------------------------------------------------------------------
def build_npc_knowledge(
    npc_id: str,
    npc_name: str,
    tongue: str,
) -> PivotKnowledge:
    """Create a PivotKnowledge instance from the NPC_TOPIC_GRAPHS registry.

    If the npc_id is found in the pre-built graphs, all topics are loaded.
    Otherwise, an empty PivotKnowledge is returned for manual population.

    Args:
        npc_id:   Lowercase NPC identifier (e.g. "polly", "eldrin").
        npc_name: Display name for the NPC (e.g. "Polly", "Eldrin").
        tongue:   Primary tongue affinity (KO/AV/RU/CA/UM/DR).

    Returns:
        A fully populated PivotKnowledge instance.
    """
    pk = PivotKnowledge(npc_id=npc_id, npc_name=npc_name, tongue_affinity=tongue)

    if npc_id in NPC_TOPIC_GRAPHS:
        graph = NPC_TOPIC_GRAPHS[npc_id]
        for topic in graph["topics"]:
            pk.add_topic(topic)

    return pk


# ---------------------------------------------------------------------------
# Convenience: build all key NPCs at once
# ---------------------------------------------------------------------------
def build_all_npcs() -> Dict[str, PivotKnowledge]:
    """Build PivotKnowledge instances for all NPCs in the registry."""
    npc_info: Dict[str, Tuple[str, str]] = {
        "polly":  ("Polly",             "KO"),
        "eldrin": ("Eldrin",            "AV"),
        "clay":   ("Clay",             "RU"),
        "aria":   ("Aria Ravencrest",  "UM"),
        "zara":   ("Zara Millwright",  "DR"),
        "kael":   ("Kael Nightwhisper", "UM"),
    }
    result: Dict[str, PivotKnowledge] = {}
    for npc_id, (name, tongue) in npc_info.items():
        result[npc_id] = build_npc_knowledge(npc_id, name, tongue)
    return result


# ---------------------------------------------------------------------------
# Main — demo / smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Pivot Knowledge — NPC Dialogue Demo")
    print("=" * 60)

    languages = SacredLanguages()
    generator = TrainingDataGenerator()
    npcs = build_all_npcs()

    for npc_id, npc in npcs.items():
        print(f"\n--- {npc.npc_name} ({npc.tongue_affinity}) ---")
        print(f"  Topics: {len(npc.topics)}")

        # Get initial response
        response = npc.get_response()
        print(f"  Initial: {response[:80]}...")

        # Show available pivots
        pivots = npc.get_pivots()
        if pivots:
            print(f"  Pivots:  {', '.join(name for _, name in pivots)}")

            # Pivot to first available topic
            pivot_id, pivot_name = pivots[0]
            pivot_response = npc.pivot(pivot_id)
            print(f"  -> Pivoted to '{pivot_name}': {pivot_response[:80]}...")

        # Generate training pair
        pair = npc.generate_training_pair()
        generator.record_pivot(npc, "demo_choice")
        print(f"  Training pair generated (depth={pair['metadata']['pivot_depth']})")

        # Show sacred encoding sample
        encoded = languages.encode("The Six Tongues guard Aethermoor", npc.tongue_affinity)
        # Safely print (Windows consoles may not support runic glyphs)
        safe_encoded = encoded[:60].encode("utf-8", errors="replace").decode("utf-8")
        try:
            print(f"  Encoded ({npc.tongue_affinity}): {safe_encoded}...")
        except UnicodeEncodeError:
            print(f"  Encoded ({npc.tongue_affinity}): [contains runic glyphs - {len(encoded)} chars]")

    print(f"\n{'=' * 60}")
    print(f"  Total training pairs collected: {generator.total_pairs}")
    print(f"{'=' * 60}")

    # Export demo data
    demo_out = Path(__file__).resolve().parent / "training_output" / "pivot_demo.jsonl"
    generator.export_jsonl(str(demo_out))
    print(f"  Exported to: {demo_out}")
