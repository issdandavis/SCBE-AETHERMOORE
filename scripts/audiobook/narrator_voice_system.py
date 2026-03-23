"""
SCBE Audiobook Narrator Voice System

Architecture:
  1. INTENT ANALYZER — reads each line and classifies emotional register,
     speaker identity, pacing, and inflection cues
  2. VOICE ROUTER — maps speaker + emotion to voice profile parameters
  3. TTS ENGINE — Kokoro ONNX with per-character voice profiles
  4. INTENT INFLECTION — uses SCBE intent-phase encoding to modulate
     pitch, speed, and emphasis based on emotional content

The key innovation: instead of flat TTS, each line gets an intent vector
that tells the voice model HOW to say it, not just WHAT to say.

Usage:
    python scripts/audiobook/narrator_voice_system.py --chapter ch01.md
    python scripts/audiobook/narrator_voice_system.py --chapter all --output artifacts/audiobook/
    python scripts/audiobook/narrator_voice_system.py --test  # Generate sample clips
"""

import re
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
READER_DIR = REPO / "content" / "book" / "reader-edition"
OUTPUT_DIR = REPO / "artifacts" / "audiobook"

# ── Character Voice Profiles ─────────────────────────────────

@dataclass
class VoiceProfile:
    """TTS parameters for a character's voice."""
    name: str
    speed: float          # 0.8 = slow, 1.0 = normal, 1.2 = fast
    pitch_shift: float    # semitones: -3 = deeper, +3 = higher
    warmth: float         # 0.0 = cold/clinical, 1.0 = warm/intimate
    breathiness: float    # 0.0 = clear, 1.0 = breathy/whispered
    cadence: str          # "steady" | "clipped" | "flowing" | "staccato"
    accent_hint: str      # for future multi-voice TTS
    description: str      # human-readable voice notes

VOICES = {
    "narrator": VoiceProfile(
        name="Narrator (Marcus POV)",
        speed=0.95, pitch_shift=0, warmth=0.6, breathiness=0.1,
        cadence="steady",
        accent_hint="American West Coast, educated, slightly tired",
        description="Dry, observational, engineering-brained. The default voice."
    ),
    "marcus_internal": VoiceProfile(
        name="Marcus Internal Thought",
        speed=0.90, pitch_shift=-0.5, warmth=0.4, breathiness=0.2,
        cadence="staccato",
        accent_hint="same as narrator but quieter, more private",
        description="Italicized thoughts. Faster, drier, more compressed."
    ),
    "polly": VoiceProfile(
        name="Polly",
        speed=1.05, pitch_shift=2, warmth=0.3, breathiness=0.0,
        cadence="clipped",
        accent_hint="British academic, centuries-old precision",
        description="Sharp, clear, sarcastic. Warmth leaks through in rare moments."
    ),
    "senna": VoiceProfile(
        name="Senna Thorne",
        speed=0.88, pitch_shift=1, warmth=0.5, breathiness=0.15,
        cadence="steady",
        accent_hint="measured, precise, composure as vocal technique",
        description="Fewer words, more weight per word. Pauses before important lines."
    ),
    "bram": VoiceProfile(
        name="Bram Cortez",
        speed=0.85, pitch_shift=-2, warmth=0.4, breathiness=0.0,
        cadence="clipped",
        accent_hint="gruff, low register, infrastructure worker",
        description="Blunt. Short sentences. Says 'no' like it's a complete philosophy."
    ),
    "alexander": VoiceProfile(
        name="Alexander Thorne",
        speed=0.90, pitch_shift=-1, warmth=0.7, breathiness=0.1,
        cadence="steady",
        accent_hint="unhurried, generous, slightly formal",
        description="Warmth lives in the pace, not the pitch. Leaves space."
    ),
    "dax": VoiceProfile(
        name="Dax",
        speed=1.0, pitch_shift=-0.5, warmth=0.6, breathiness=0.0,
        cadence="flowing",
        accent_hint="Australian, Melbourne, casual warmth",
        description="Direct, warm, says 'mate' and 'drongo' without performing it."
    ),
    "fizzle": VoiceProfile(
        name="Fizzle Brightcog",
        speed=1.15, pitch_shift=3, warmth=0.8, breathiness=0.0,
        cadence="staccato",
        accent_hint="rapid, excited, switches between Draumric weight and gnomish speed",
        description="Chaotic genius energy. Fast when excited, slow when remembering Izack."
    ),
    "aria": VoiceProfile(
        name="Aria Ravencrest Thorne",
        speed=0.88, pitch_shift=1.5, warmth=0.6, breathiness=0.1,
        cadence="steady",
        accent_hint="direct, few words, practical authority",
        description="Every word is chosen. No filler. Sounds like someone who eliminates waste."
    ),
    "izack": VoiceProfile(
        name="Izack Thorne",
        speed=0.82, pitch_shift=-1.5, warmth=0.7, breathiness=0.2,
        cadence="flowing",
        accent_hint="warm, tired, gently self-deprecating",
        description="The voice of a man holding 21 dimensions together by hand. Tired but kind."
    ),
    "lyra": VoiceProfile(
        name="Lyra Thorne",
        speed=1.10, pitch_shift=2, warmth=0.5, breathiness=0.0,
        cadence="staccato",
        accent_hint="fast, sharp, arrives mid-thought",
        description="Teasing, quick, the words arrive before you're ready for them."
    ),
    "tovak": VoiceProfile(
        name="Tovak Rel",
        speed=0.80, pitch_shift=-2, warmth=0.2, breathiness=0.0,
        cadence="clipped",
        accent_hint="minimal, measured, UM specialist stillness",
        description="Three words per sentence average. Every word load-bearing."
    ),
    "jorren": VoiceProfile(
        name="Jorren Hale",
        speed=0.90, pitch_shift=-0.5, warmth=0.3, breathiness=0.0,
        cadence="steady",
        accent_hint="dry, archival, quiet precision",
        description="Sounds like old paper feels. Every sentence is a filed report."
    ),
    "nadia": VoiceProfile(
        name="Nadia Kest",
        speed=1.05, pitch_shift=1, warmth=0.6, breathiness=0.0,
        cadence="flowing",
        accent_hint="energetic, direct, the team's heartbeat",
        description="Says what everyone is thinking. Faster than most characters."
    ),
    "sera": VoiceProfile(
        name="Sera Voss",
        speed=0.88, pitch_shift=0.5, warmth=0.2, breathiness=0.0,
        cadence="steady",
        accent_hint="judicial, measured, one-degree temperature changes",
        description="Every sentence is a ruling. Warmth is rationed precisely."
    ),
    "void_seed": VoiceProfile(
        name="The Void Seed",
        speed=0.75, pitch_shift=-4, warmth=0.0, breathiness=0.3,
        cadence="flowing",
        accent_hint="inhuman, patient, persuasive, wrong",
        description="Speaks in italics. Should sound like it's inside your head, not in the room."
    ),
}

# ── Emotion / Intent Classification ──────────────────────────

@dataclass
class LineIntent:
    """Intent vector for a single line of narration."""
    text: str
    speaker: str            # character name or "narrator"
    emotion: str            # grief | humor | tension | wonder | intimacy | dread | warmth | neutral
    intensity: float        # 0.0 = whisper, 1.0 = full voice
    pause_before: float     # seconds of silence before this line
    pause_after: float      # seconds of silence after this line
    emphasis_words: List[str]  # words to stress
    is_internal: bool       # italicized thought?
    is_caw: bool            # Polly's Caw! — needs special treatment


def classify_speaker(line: str, prev_speaker: str = "narrator") -> str:
    """Identify who is speaking from dialogue attribution."""
    # Direct attribution patterns
    patterns = {
        r'"[^"]*"\s*(Marcus|he)\s+said': "marcus_internal",
        r'"[^"]*"\s*Polly\s+said': "polly",
        r'"[^"]*"\s*Senna\s+said': "senna",
        r'"[^"]*"\s*Bram\s+said': "bram",
        r'"[^"]*"\s*Alexander\s+said': "alexander",
        r'"[^"]*"\s*Dax\s+said': "dax",
        r'"[^"]*"\s*Fizzle\s+said': "fizzle",
        r'"[^"]*"\s*Aria\s+said': "aria",
        r'"[^"]*"\s*Izack\s+said': "izack",
        r'"[^"]*"\s*Lyra\s+said': "lyra",
        r'"[^"]*"\s*Tovak\s+said': "tovak",
        r'"[^"]*"\s*Jorren\s+said': "jorren",
        r'"[^"]*"\s*Nadia\s+said': "nadia",
        r'"[^"]*"\s*Sera\s+said': "sera",
    }

    for pattern, speaker in patterns.items():
        if re.search(pattern, line, re.IGNORECASE):
            return speaker

    # Check for Caw!
    if "Caw!" in line or "CAW" in line:
        return "polly"

    # Check for italicized thought (Marcus internal)
    if line.strip().startswith("*") and line.strip().endswith("*"):
        return "marcus_internal"

    # Check for Void Seed speech (usually italicized without quotes)
    if re.search(r'\*[A-Z][^*]+\*', line) and "one source" in line.lower():
        return "void_seed"

    # Dialogue without clear attribution — use context
    if line.strip().startswith('"'):
        return prev_speaker if prev_speaker != "narrator" else "narrator"

    return "narrator"


def classify_emotion(line: str) -> tuple:
    """Classify the emotional register of a line."""
    text_lower = line.lower()

    # Grief markers
    if any(w in text_lower for w in ["cried", "tears", "grief", "loss", "missing", "gone", "dead"]):
        return "grief", 0.7

    # Humor markers
    if any(w in text_lower for w in ["laughed", "grinned", "snorted", "joke", "funny"]):
        return "humor", 0.6

    # Tension markers
    if any(w in text_lower for w in ["alarm", "breach", "hostile", "warning", "emergency"]):
        return "tension", 0.8

    # Wonder markers
    if any(w in text_lower for w in ["beautiful", "impossible", "extraordinary", "wonder"]):
        return "wonder", 0.6

    # Intimacy markers
    if any(w in text_lower for w in ["kissed", "hand", "shoulder", "touched", "warmth", "close"]):
        return "intimacy", 0.5

    # Dread markers
    if any(w in text_lower for w in ["void", "darkness", "wrong", "copper taste", "whisper"]):
        return "dread", 0.7

    return "neutral", 0.5


def analyze_chapter(filepath: Path) -> List[LineIntent]:
    """Parse a chapter into annotated lines with intent vectors."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    intents = []
    prev_speaker = "narrator"

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Scene breaks get long pauses
        if stripped == '* * *' or stripped == '---':
            intents.append(LineIntent(
                text="", speaker="narrator", emotion="neutral",
                intensity=0.0, pause_before=2.0, pause_after=1.0,
                emphasis_words=[], is_internal=False, is_caw=False
            ))
            continue

        speaker = classify_speaker(stripped, prev_speaker)
        emotion, intensity = classify_emotion(stripped)
        is_internal = stripped.startswith("*") and not stripped.startswith("**")
        is_caw = "Caw!" in stripped or "CAW" in stripped

        # Determine pauses
        pause_before = 0.3 if speaker != prev_speaker else 0.1
        pause_after = 0.5 if stripped.endswith('.') else 0.2
        if emotion == "grief":
            pause_after = 0.8
        if is_caw:
            pause_before = 0.2
            pause_after = 0.5

        # Find emphasis words (capitalized words, words in italics)
        emphasis = re.findall(r'\*(\w+)\*', stripped)
        emphasis += [w for w in stripped.split() if w.isupper() and len(w) > 2]

        intents.append(LineIntent(
            text=stripped,
            speaker=speaker,
            emotion=emotion,
            intensity=intensity,
            pause_before=pause_before,
            pause_after=pause_after,
            emphasis_words=emphasis,
            is_internal=is_internal,
            is_caw=is_caw,
        ))

        if speaker != "narrator":
            prev_speaker = speaker

    return intents


def generate_voice_script(intents: List[LineIntent]) -> List[dict]:
    """Convert intent vectors into a voice script for TTS."""
    script = []

    for intent in intents:
        if not intent.text:
            script.append({"type": "pause", "duration": intent.pause_before + intent.pause_after})
            continue

        profile = VOICES.get(intent.speaker, VOICES["narrator"])

        # Modify voice parameters based on emotion
        speed_mod = 1.0
        pitch_mod = 0.0
        warmth_mod = 0.0

        if intent.emotion == "grief":
            speed_mod = 0.9
            pitch_mod = -1.0
            warmth_mod = 0.2
        elif intent.emotion == "humor":
            speed_mod = 1.05
            pitch_mod = 0.5
        elif intent.emotion == "tension":
            speed_mod = 1.1
            pitch_mod = 0.5
        elif intent.emotion == "wonder":
            speed_mod = 0.9
            warmth_mod = 0.3
        elif intent.emotion == "intimacy":
            speed_mod = 0.85
            warmth_mod = 0.4

        if intent.is_internal:
            speed_mod *= 0.95
            warmth_mod -= 0.1

        if intent.is_caw:
            speed_mod = 1.2
            pitch_mod = 3.0

        script.append({
            "type": "speech",
            "text": intent.text,
            "speaker": intent.speaker,
            "voice_profile": profile.name,
            "speed": profile.speed * speed_mod,
            "pitch": profile.pitch_shift + pitch_mod,
            "warmth": min(1.0, max(0.0, profile.warmth + warmth_mod)),
            "cadence": profile.cadence,
            "emotion": intent.emotion,
            "intensity": intent.intensity,
            "pause_before": intent.pause_before,
            "pause_after": intent.pause_after,
            "emphasis": intent.emphasis_words,
            "is_internal": intent.is_internal,
            "is_caw": intent.is_caw,
        })

    return script


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCBE Audiobook Voice System")
    parser.add_argument("--chapter", default="ch01.md", help="Chapter file or 'all'")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--test", action="store_true", help="Generate test clips")

    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    if args.chapter == "all":
        files = sorted(READER_DIR.glob("*.md"))
    else:
        files = [READER_DIR / args.chapter]

    for filepath in files:
        if not filepath.exists():
            print(f"Not found: {filepath}")
            continue

        print(f"Analyzing: {filepath.name}")
        intents = analyze_chapter(filepath)
        script = generate_voice_script(intents)

        # Save voice script
        script_path = out / f"{filepath.stem}_voice_script.json"
        with open(script_path, 'w', encoding='utf-8') as f:
            json.dump(script, f, indent=2)

        # Stats
        speakers = {}
        emotions = {}
        for entry in script:
            if entry["type"] == "speech":
                s = entry["speaker"]
                e = entry["emotion"]
                speakers[s] = speakers.get(s, 0) + 1
                emotions[e] = emotions.get(e, 0) + 1

        print(f"  Lines: {len(script)}")
        print(f"  Speakers: {dict(sorted(speakers.items(), key=lambda x: -x[1]))}")
        print(f"  Emotions: {dict(sorted(emotions.items(), key=lambda x: -x[1]))}")
        print(f"  Script: {script_path}")
        print()


if __name__ == "__main__":
    main()
