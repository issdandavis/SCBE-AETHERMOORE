#!/usr/bin/env python3
"""
NPC Brain — Optional LLM-Powered NPC Responses for Aethermoor RPG
==================================================================
Provides conversational AI responses for NPCs using Google Gemini when
available, with full offline fallback using character-appropriate templates.

Every AI response is validated through an L9 sanitization gate and recorded
as an SFT training pair for downstream fine-tuning.

Characters from Issac Davis's lore (Everweave, Notion, SCBE):
  - Polly       : Raven familiar, cautious wisdom, KO affinity
  - Clay        : Sand golem, loyal protector, RU affinity
  - Eldrin      : Cartographer, curious explorer, AV affinity
  - Aria        : Warrior-scholar, strategic balance, UM affinity
  - Zara        : Dragon-blooded engineer, bold innovator, DR affinity
  - Kael        : Shadow drifter, mysterious loner, UM affinity

Works fully without google-generativeai installed (graceful fallback).
"""

from __future__ import annotations

import logging
import os
import random
import re
import time
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sacred Tongue Descriptions
# ---------------------------------------------------------------------------
TONGUE_DESCRIPTIONS: Dict[str, str] = {
    "KO": "Authority and Command - governs intent and routing",
    "AV": "Transport and Navigation - governs context and memory",
    "RU": "Policy and Law - governs constraints and structure",
    "CA": "Compute and Encryption - governs processing and ciphers",
    "UM": "Security and Secrets - governs spectral and quantum domains",
    "DR": "Schema and Authentication - governs data structure and identity",
}

# ---------------------------------------------------------------------------
# NPC Fallback Responses (per character)
# ---------------------------------------------------------------------------
NPC_FALLBACKS: Dict[str, List[str]] = {
    "polly": [
        "The Protocol demands we consider this carefully before acting.",
        "I have seen this pattern before, in the archives of the First Tongues.",
        "Wisdom favours the measured step. Let us not rush headlong.",
        "The ancestors encoded warnings about paths like this one.",
        "Every choice ripples through all fourteen layers. Choose wisely.",
        "Consult the archives before you decide. Knowledge is armour.",
        "The Protocol has endured because it adapts. So must we.",
        "I sense a disturbance in the spectral frequencies. Tread lightly.",
    ],
    "eldrin": [
        "There might be something beyond what the maps show us here.",
        "My charts indicate an unexplored route just past this point.",
        "The ley lines converge ahead. Something remarkable awaits.",
        "I have never seen this configuration on any known chart.",
        "Every uncharted route yields the best discoveries, in my experience.",
        "Let me consult my cartographic notes on this region.",
        "The compass of tongues spins wildly here. Fascinating!",
        "Beyond every horizon lies another horizon. Shall we see?",
    ],
    "clay": [
        "Clay stands between you and harm. Always.",
        "Safe is good. I like safe.",
        "Whatever keeps everyone safe. That is what Clay chooses.",
        "New dirt here. Good dirt. Strong dirt.",
        "Clay does not understand the words, but Clay understands the danger.",
        "Together is safe. Clay stays together.",
        "Building is good. I like building things.",
    ],
    "aria": [
        "The boundary math suggests we approach this systematically.",
        "Consider the implications before crossing that threshold.",
        "By my theorem, the optimal path requires balance.",
        "The equation does not balance if we ignore the constraints.",
        "Every variable matters. Do not discard what seems trivial.",
        "The defensive integral converges only with patience.",
        "I have computed the risk. Proceed, but with full awareness.",
        "The boundary conditions here are unlike anything in my proofs.",
    ],
    "zara": [
        "I can build a workaround for that. Give me a moment.",
        "The schema compiles clean. We are good to proceed.",
        "Prototype fast, iterate faster. That is how I work.",
        "I see the engineering challenge here. Let me sketch a solution.",
        "Dragon-fire and ingenuity solve most problems, in my experience.",
        "Data persists when towers fall. Always keep records.",
        "I can build a workaround if the weave frays.",
        "Connection is infrastructure. Never underestimate the network.",
    ],
    "kael": [
        "There is always another way. Shadows remember what the light forgets.",
        "The dark is not the enemy. Ignorance is.",
        "Time folds for those who dare step sideways.",
        "I have walked paths you cannot see. Trust the shadow.",
        "Not everything hidden is dangerous. Some things hide to survive.",
        "Silence speaks louder than any tongue, if you learn to listen.",
        "The shadow between worlds holds more answers than either side.",
    ],
}

# ---------------------------------------------------------------------------
# L9 Sanitization Patterns (compiled once)
# ---------------------------------------------------------------------------
_RE_CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_RE_INLINE_CODE = re.compile(r"`[^`]+`")
_RE_MARKDOWN_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_MARKDOWN_ITALIC = re.compile(r"\*(.+?)\*")
_RE_MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_RE_URL = re.compile(r"https?://\S+")
_RE_EVAL = re.compile(r"eval\s*\(", re.IGNORECASE)
_RE_IMPORT = re.compile(r"\bimport\s+")

_MAX_RESPONSE_LENGTH = 200


class _VisibleTextExtractor(HTMLParser):
    """Extract visible text while discarding script/style blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignore_depth = 0
        self._parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignore_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignore_depth:
            self._ignore_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignore_depth and data:
            self._parts.append(data)

    def to_text(self) -> str:
        return " ".join(self._parts)


def _strip_html_markup(raw: str) -> str:
    parser = _VisibleTextExtractor()
    parser.feed(raw)
    parser.close()
    return parser.to_text()


# ---------------------------------------------------------------------------
# NPCBrain
# ---------------------------------------------------------------------------
class NPCBrain:
    """LLM-powered NPC conversational engine with offline fallback.

    Lazy-loads google.generativeai on first use. If the library is not
    installed or GOOGLE_AI_KEY is not set, falls back to deterministic
    template responses. Every response passes through an L9 sanitization
    gate before being returned.

    Attributes:
        npc_name:             Display name of the NPC.
        tongue_affinity:      Two-letter Sacred Tongue code (KO, AV, etc.).
        backstory:            Character backstory for system prompt context.
        conversation_history: Rolling conversation log (role/content dicts).
        api_available:        Whether Gemini API is usable.
        model:                The genai model instance, or None.
        training_pairs:       Accumulated SFT pairs from AI responses.
        fallback_responses:   Template responses used when offline.
    """

    def __init__(self, npc_name: str, tongue_affinity: str, backstory: str) -> None:
        self.npc_name: str = npc_name
        self.tongue_affinity: str = tongue_affinity
        self.backstory: str = backstory
        self.conversation_history: List[Dict[str, str]] = []
        self.api_available: bool = False
        self.model: Any = None
        self.training_pairs: List[Dict] = []

        # Resolve fallback responses for this NPC
        key = npc_name.lower().strip()
        self.fallback_responses: List[str] = list(
            NPC_FALLBACKS.get(key, [
                "Hmm, let me think about that for a moment.",
                "The tongues whisper, but I cannot quite make out the words.",
                "That is a question worthy of deeper contemplation.",
                "The Protocol guides, but the choice remains yours.",
                "I sense more to this than meets the eye.",
            ])
        )

        self._api_initialized: bool = False

    # -- Lazy API initialization -------------------------------------------

    def _init_api(self) -> None:
        """Lazy-load google.generativeai and configure with GOOGLE_AI_KEY.

        Sets ``self.api_available`` to True only if the library can be
        imported AND the environment variable is present.
        """
        if self._api_initialized:
            return
        self._api_initialized = True

        try:
            import google.generativeai as genai  # type: ignore[import-untyped]

            key = os.environ.get("GOOGLE_AI_KEY", "")
            if not key:
                logger.debug("GOOGLE_AI_KEY not set; NPC %s using fallback.", self.npc_name)
                self.api_available = False
                return

            genai.configure(api_key=key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.api_available = True
            logger.info("Gemini API initialized for NPC %s.", self.npc_name)

        except ImportError:
            logger.debug("google-generativeai not installed; NPC %s using fallback.", self.npc_name)
            self.api_available = False

    # -- System prompt generation ------------------------------------------

    def generate_system_prompt(self) -> str:
        """Build a character-appropriate system prompt for the LLM.

        Incorporates the NPC's name, tongue affinity and its meaning,
        backstory, and instructions for staying in character within the
        world of Aethermoor.
        """
        tongue_desc = TONGUE_DESCRIPTIONS.get(
            self.tongue_affinity, "an ancient and mysterious domain"
        )
        return (
            f"You are {self.npc_name}, a character in the world of Aethermoor.\n"
            f"Your Sacred Tongue affinity is {self.tongue_affinity} — "
            f"{tongue_desc}.\n\n"
            f"Backstory: {self.backstory}\n\n"
            f"Instructions:\n"
            f"- Stay in character at all times. You are {self.npc_name}, not an AI assistant.\n"
            f"- Speak concisely in 1-3 sentences. Be evocative but brief.\n"
            f"- Reference Aethermoor lore naturally: the Six Sacred Tongues, the 14-layer "
            f"Protocol, the World Tree Pollyoneth, floating islands, and tongue-encoded magic.\n"
            f"- Let your {self.tongue_affinity} affinity colour your perspective and vocabulary.\n"
            f"- Never break character or acknowledge being an AI."
        )

    # -- L9 Sanitization Gate ----------------------------------------------

    @staticmethod
    def _sanitize_response(raw: str) -> str:
        """L9 validation gate: sanitize an LLM response before delivery.

        Strips code blocks, markdown formatting, URLs, HTML tags, and
        dangerous patterns (script tags, eval calls, import statements).
        Truncates to 200 characters at a word boundary.

        Args:
            raw: The raw LLM response string.

        Returns:
            Cleaned, safe text suitable for in-game display.
        """
        text = raw

        # Strip code blocks and inline code
        text = _RE_CODE_BLOCK.sub("", text)
        text = _RE_INLINE_CODE.sub("", text)

        # Strip markdown formatting (preserve inner text)
        text = _RE_MARKDOWN_BOLD.sub(r"\1", text)
        text = _RE_MARKDOWN_ITALIC.sub(r"\1", text)
        text = _RE_MARKDOWN_HEADER.sub("", text)

        # Remove dangerous HTML/script payloads before token cleanup.
        text = _strip_html_markup(text)
        text = _RE_EVAL.sub("", text)
        text = _RE_IMPORT.sub("", text)

        # Remove URLs
        text = _RE_URL.sub("", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate to 200 chars at word boundary
        if len(text) > _MAX_RESPONSE_LENGTH:
            truncated = text[:_MAX_RESPONSE_LENGTH]
            # Find last space to avoid cutting mid-word
            last_space = truncated.rfind(" ")
            if last_space > _MAX_RESPONSE_LENGTH // 2:
                text = truncated[:last_space].rstrip()
            else:
                text = truncated.rstrip()

        return text

    # -- Training pair generation ------------------------------------------

    def _generate_training_pair(
        self, player_input: str, npc_response: str, topic: str
    ) -> Dict:
        """Create an SFT training pair from a player-NPC exchange.

        Args:
            player_input:  What the player said.
            npc_response:  The NPC's (sanitized) reply.
            topic:         Current conversation topic / scene context.

        Returns:
            A dict with instruction, response, and metadata suitable for
            supervised fine-tuning.
        """
        tongue_desc = TONGUE_DESCRIPTIONS.get(self.tongue_affinity, "unknown")
        return {
            "instruction": (
                f"You are {self.npc_name} in Aethermoor, aligned with the "
                f"{self.tongue_affinity} tongue ({tongue_desc}). "
                f"A player says: \"{player_input}\""
            ),
            "response": npc_response,
            "metadata": {
                "source": "npc_brain_sft",
                "npc_name": self.npc_name,
                "tongue_affinity": self.tongue_affinity,
                "topic": topic,
                "timestamp": time.time(),
                "api_generated": self.api_available,
            },
        }

    # -- Core response method ----------------------------------------------

    def get_response(self, player_input: str, current_topic: str = "") -> str:
        """Get an NPC response to the player's input.

        If the Gemini API is available, sends a contextual prompt including
        the NPC's system prompt, recent conversation history, and current
        topic. Otherwise, returns a random fallback response.

        Every response (AI or fallback) is recorded as a training pair and
        appended to conversation history.

        Args:
            player_input:  The player's dialogue text.
            current_topic: Optional scene or topic context string.

        Returns:
            A sanitized, in-character NPC response string.
        """
        # Lazy-init on first call
        self._init_api()

        response_text: str

        if self.api_available and self.model is not None:
            response_text = self._get_ai_response(player_input, current_topic)
        else:
            response_text = random.choice(self.fallback_responses)

        # L9 sanitization gate
        response_text = self._sanitize_response(response_text)

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": player_input})
        self.conversation_history.append({"role": "assistant", "content": response_text})

        # Record training pair
        pair = self._generate_training_pair(player_input, response_text, current_topic)
        self.training_pairs.append(pair)

        return response_text

    def _get_ai_response(self, player_input: str, current_topic: str) -> str:
        """Send a prompt to Gemini and return the raw response text.

        Constructs a full prompt with system context, recent conversation
        history (last 4 turns), and the player's current input.

        Args:
            player_input:  The player's dialogue text.
            current_topic: Optional topic/scene context.

        Returns:
            Raw response string from the model, or a fallback on error.
        """
        system_prompt = self.generate_system_prompt()

        # Build conversation context from last 4 turns (8 messages)
        recent_history = self.conversation_history[-8:]
        history_text = ""
        if recent_history:
            history_lines = []
            for msg in recent_history:
                role_label = "Player" if msg["role"] == "user" else self.npc_name
                history_lines.append(f"{role_label}: {msg['content']}")
            history_text = "\nRecent conversation:\n" + "\n".join(history_lines) + "\n"

        topic_text = ""
        if current_topic:
            topic_text = f"\nCurrent scene/topic: {current_topic}\n"

        full_prompt = (
            f"{system_prompt}\n"
            f"{history_text}"
            f"{topic_text}\n"
            f"Player: {player_input}\n"
            f"{self.npc_name}:"
        )

        try:
            result = self.model.generate_content(full_prompt)
            return result.text or random.choice(self.fallback_responses)
        except Exception as exc:
            logger.warning(
                "Gemini API call failed for NPC %s: %s", self.npc_name, exc
            )
            return random.choice(self.fallback_responses)


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------
def create_npc_brain(
    npc_id: str, npc_name: str, tongue: str, backstory: str
) -> NPCBrain:
    """Create an NPCBrain instance for a named character.

    Args:
        npc_id:   Unique identifier for the NPC (used for logging/tracking).
        npc_name: Display name of the NPC.
        tongue:   Two-letter Sacred Tongue affinity code.
        backstory: Character backstory text.

    Returns:
        A configured NPCBrain instance.
    """
    logger.debug("Creating NPC brain: id=%s, name=%s, tongue=%s", npc_id, npc_name, tongue)
    return NPCBrain(npc_name=npc_name, tongue_affinity=tongue, backstory=backstory)


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------
def selftest() -> None:
    """Run self-test exercising all public methods without requiring API."""
    print(f"\n{'=' * 60}")
    print("  NPC Brain -- Self-Test (offline mode)")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # --- 1. Tongue descriptions ---
    check("All 6 tongue descriptions", len(TONGUE_DESCRIPTIONS) == 6)
    for code in ("KO", "AV", "RU", "CA", "UM", "DR"):
        check(f"  Tongue {code} has description", code in TONGUE_DESCRIPTIONS)

    # --- 2. Fallback responses ---
    check("All 6 NPC fallback sets", len(NPC_FALLBACKS) == 6)
    for npc_key in ("polly", "eldrin", "clay", "aria", "zara", "kael"):
        responses = NPC_FALLBACKS.get(npc_key, [])
        check(f"  {npc_key} has 5+ fallbacks", len(responses) >= 5,
              f"got {len(responses)}")

    # --- 3. NPCBrain creation ---
    polly = create_npc_brain(
        npc_id="polly_01",
        npc_name="Polly",
        tongue="KO",
        backstory="An ancient raven familiar who serves as the keeper of the Protocol.",
    )
    check("NPCBrain created", polly is not None)
    check("  npc_name set", polly.npc_name == "Polly")
    check("  tongue_affinity set", polly.tongue_affinity == "KO")
    check("  backstory set", "raven" in polly.backstory)
    check("  conversation_history empty", len(polly.conversation_history) == 0)
    check("  api_available is False (no key)", not polly.api_available)
    check("  training_pairs empty", len(polly.training_pairs) == 0)
    check("  fallback_responses loaded", len(polly.fallback_responses) >= 5)

    # --- 4. System prompt ---
    prompt = polly.generate_system_prompt()
    check("System prompt contains NPC name", "Polly" in prompt)
    check("System prompt contains tongue", "KO" in prompt)
    check("System prompt contains tongue desc", "Authority" in prompt)
    check("System prompt contains Aethermoor", "Aethermoor" in prompt)
    check("System prompt contains backstory ref", "raven" in prompt.lower() or "Protocol" in prompt)
    check("System prompt has conciseness instruction", "1-3 sentences" in prompt)

    # --- 5. Get response (fallback mode) ---
    response = polly.get_response("What is this place?", current_topic="academy_arrival")
    check("Response is non-empty", len(response) > 0)
    check("Response <= 200 chars", len(response) <= _MAX_RESPONSE_LENGTH)
    check("Conversation history updated (2 entries)", len(polly.conversation_history) == 2)
    check("  User entry recorded", polly.conversation_history[0]["role"] == "user")
    check("  Assistant entry recorded", polly.conversation_history[1]["role"] == "assistant")
    check("Training pair recorded", len(polly.training_pairs) == 1)

    # --- 6. Training pair structure ---
    pair = polly.training_pairs[0]
    check("Training pair has instruction", "instruction" in pair)
    check("Training pair has response", "response" in pair)
    check("Training pair has metadata", "metadata" in pair)
    check("  metadata.source", pair["metadata"]["source"] == "npc_brain_sft")
    check("  metadata.npc_name", pair["metadata"]["npc_name"] == "Polly")
    check("  metadata.tongue_affinity", pair["metadata"]["tongue_affinity"] == "KO")
    check("  metadata.topic", pair["metadata"]["topic"] == "academy_arrival")
    check("  metadata.timestamp is numeric", isinstance(pair["metadata"]["timestamp"], float))

    # --- 7. L9 Sanitization ---
    sanitize = NPCBrain._sanitize_response

    # Code blocks
    check("Strips code blocks",
          "hello" not in sanitize("Before ```python\nprint('hello')\n``` After"))
    check("Strips inline code", "`code`" not in sanitize("Some `code` here"))

    # URLs
    check("Strips URLs", "http" not in sanitize("Visit https://evil.com now"))

    # Script tags
    check("Strips script tags",
          "script" not in sanitize("<script>alert('xss')</script>safe text").lower())
    check("Strips malformed script end tags",
          "alert" not in sanitize("<script>alert('xss')</script >safe text").lower())

    # eval
    check("Strips eval(", "eval" not in sanitize("Try eval(something) here"))

    # import
    check("Strips import ", "import" not in sanitize("Now import os and run"))

    # Markdown
    check("Strips markdown bold", "**" not in sanitize("This is **bold** text"))
    check("Preserves bold inner text", "bold" in sanitize("This is **bold** text"))

    # Truncation
    long_text = "word " * 100  # 500 chars
    sanitized_long = sanitize(long_text)
    check("Truncates long text to <= 200", len(sanitized_long) <= _MAX_RESPONSE_LENGTH)
    check("Truncation at word boundary", not sanitized_long.endswith("wor"))

    # Clean passthrough
    clean = "The Protocol guides us forward with ancient wisdom."
    check("Clean text passes through", sanitize(clean) == clean)

    # --- 8. Multiple responses accumulate ---
    polly.get_response("Tell me about the tongues.", current_topic="academy_lesson")
    polly.get_response("What should I do next?")
    check("3 training pairs after 3 calls", len(polly.training_pairs) == 3)
    check("6 conversation entries after 3 calls", len(polly.conversation_history) == 6)

    # --- 9. Different NPCs ---
    clay = create_npc_brain("clay_01", "Clay", "RU",
                            "A sand golem formed from the earth of Aethermoor.")
    clay_resp = clay.get_response("Are we safe here?")
    check("Clay responds", len(clay_resp) > 0)
    check("Clay fallbacks are clay-specific",
          any("Clay" in r for r in clay.fallback_responses))

    kael = create_npc_brain("kael_01", "Kael", "UM",
                            "A shadow drifter walking between timelines.")
    kael_resp = kael.get_response("What lurks in the shadows?")
    check("Kael responds", len(kael_resp) > 0)

    # --- 10. Unknown NPC gets default fallbacks ---
    unknown = create_npc_brain("mystery_01", "Mystery NPC", "CA",
                               "A stranger with no known history.")
    check("Unknown NPC has default fallbacks", len(unknown.fallback_responses) >= 5)
    unknown_resp = unknown.get_response("Who are you?")
    check("Unknown NPC responds", len(unknown_resp) > 0)

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")
    if failed == 0:
        print("  All NPC brain systems operational.\n")
    else:
        print(f"  WARNING: {failed} check(s) failed.\n")


if __name__ == "__main__":
    selftest()
