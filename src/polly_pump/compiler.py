"""Canonical Event Compiler — normalize any record into multi-view format.

Takes raw source material (text, chat, lore, code, docs) and compiles it
into a single normalized event record with all views:

- raw_bytes (L0 substrate)
- ss1_tokens (L1 tongue encoding)
- pump_packet (L2 orientation)
- natural_text (L3 expression)
- task_type assignment

This is the "before training" setup that shapes the geometry the AI
trains inside. Every record passes through the same compiler so the
model gets a consistent multi-view representation.

Usage:
    from polly_pump.compiler import compile_event, compile_batch
    event = compile_event("Who is Polly?", "Polly is Polymnia Aetheris...")
    events = compile_batch(jsonl_records)
"""

from __future__ import annotations

import base64
import json
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .packet import sense, PumpPacket, TONGUE_CODES, TONGUE_NAMES

# ── Tongue encoding (inline for compiler independence) ─────────────

PHI = (1 + math.sqrt(5)) / 2

_TONGUES = {
    "KO": {
        'prefixes': ['sil', 'ra', 'vel', 'zar', 'joy', 'thul', 'keth', 'ael',
                     'vor', 'med', 'fir', 'gal', 'nav', 'nex', 'dun', 'pyr'],
        'suffixes': ['an', 'il', 'ar', 'ia', 'or', 'is', 'ur', 'oth',
                     'ak', 'ol', 'ir', 'eth', 'un', 'ek', 'en', 'esh'],
    },
    "AV": {
        'prefixes': ['saina', 'talan', 'vessa', 'maren', 'oriel', 'serin',
                     'nurel', 'lirea', 'kiva', 'lumen', 'calma', 'ponte',
                     'verin', 'nava', 'sela', 'tide'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
                     'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'],
    },
    "RU": {
        'prefixes': ['khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak',
                     'tharn', 'groth', 'basalt', 'rune', 'sear', 'oath',
                     'gnarl', 'rift', 'iron'],
        'suffixes': ['ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
                     'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'],
    },
    "CA": {
        'prefixes': ['bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa',
                     'spira', 'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip',
                     'mix', 'chass'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
                     'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'],
    },
    "UM": {
        'prefixes': ['veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush',
                     'thorn', 'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache',
                     'null', 'shade'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
                     'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'],
    },
    "DR": {
        'prefixes': ['anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal',
                     'temper', 'forge', 'stone', 'steam', 'oath', 'seal',
                     'frame', 'pillar', 'rivet', 'ember'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
                     'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'],
    },
}


def _encode_byte(tongue_code: str, b: int) -> str:
    t = _TONGUES[tongue_code]
    return f"{t['prefixes'][b >> 4]}'{t['suffixes'][b & 0x0F]}"


def _encode_text(tongue_code: str, text: str, max_bytes: int = 32) -> str:
    raw = text.encode('utf-8', errors='replace')[:max_bytes]
    return ' '.join(f"{tongue_code}:{_encode_byte(tongue_code, b)}" for b in raw)


# ── Compiled Event ─────────────────────────────────────────────────

@dataclass
class CompiledEvent:
    """A single normalized multi-view event record."""

    # Identity
    event_id: str = ""
    source: str = ""

    # L0: raw bytes
    raw_bytes_b64: str = ""  # base64-encoded raw bytes of user text
    byte_count: int = 0

    # L1: tongue tokens (one random tongue per event)
    tongue_code: str = "KO"
    ss1_tokens: str = ""

    # L2: pump packet
    tongue_profile: List[float] = field(default_factory=lambda: [0.0] * 6)
    null_pattern: str = "______"
    null_ratio: float = 0.0
    dominant_tongue: str = "KO"
    canon: str = "general"
    emotion: str = "neutral"
    governance: str = "ALLOW"

    # L3: natural text
    user_text: str = ""
    assistant_text: str = ""
    system_text: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "raw_bytes_b64": self.raw_bytes_b64,
            "byte_count": self.byte_count,
            "tongue_code": self.tongue_code,
            "ss1_tokens": self.ss1_tokens,
            "tongue_profile": self.tongue_profile,
            "null_pattern": self.null_pattern,
            "null_ratio": self.null_ratio,
            "dominant_tongue": self.dominant_tongue,
            "canon": self.canon,
            "emotion": self.emotion,
            "governance": self.governance,
            "user_text": self.user_text,
            "assistant_text": self.assistant_text,
            "system_text": self.system_text,
        }

    def to_sft_row(self, task_type: str = "l3") -> dict:
        """Convert to an SFT training row for the specified task type."""
        return {
            "messages": self._make_messages(task_type),
            "task_type": task_type,
        }

    def _make_messages(self, task_type: str) -> list:
        if task_type == "l0":
            return [
                {"role": "system", "content": "You are a byte-level encoder."},
                {"role": "user", "content": f"What are the raw bytes of: \"{self.user_text[:60]}\""},
                {"role": "assistant", "content": self._l0_response()},
            ]
        elif task_type == "l1":
            return [
                {"role": "system", "content": f"You encode text in {TONGUE_NAMES[TONGUE_CODES.index(self.tongue_code)]}."},
                {"role": "user", "content": f"Encode: \"{self.user_text[:40]}\""},
                {"role": "assistant", "content": f"In {self.tongue_code}: {self.ss1_tokens}"},
            ]
        elif task_type == "l2":
            return [
                {"role": "system", "content": "You compute pump orientation packets."},
                {"role": "user", "content": f"Pump packet for: \"{self.user_text[:100]}\""},
                {"role": "assistant", "content": self._l2_response()},
            ]
        else:  # l3
            msgs = []
            if self.system_text:
                msgs.append({"role": "system", "content": self.system_text})
            msgs.append({"role": "user", "content": self.user_text})
            msgs.append({"role": "assistant", "content": self.assistant_text})
            return msgs

    def _l0_response(self) -> str:
        raw = self.user_text[:32].encode('utf-8', errors='replace')
        hex_str = ' '.join(f'0x{b:02X}' for b in raw[:16])
        return f"Bytes: {hex_str} ({len(raw)} total)"

    def _l2_response(self) -> str:
        profile = ', '.join(f'{TONGUE_CODES[i]}={v:.3f}' for i, v in enumerate(self.tongue_profile))
        return (
            f"Tongue: [{profile}]\n"
            f"Null: {self.null_pattern} (ratio: {self.null_ratio:.2f})\n"
            f"Dom: {self.dominant_tongue} | Canon: {self.canon} | Gov: {self.governance}"
        )


# ── Compiler ───────────────────────────────────────────────────────

def compile_event(
    user_text: str,
    assistant_text: str = "",
    system_text: str = "",
    source: str = "",
    event_id: str = "",
    tongue_code: Optional[str] = None,
) -> CompiledEvent:
    """Compile a single text exchange into a multi-view event."""

    # Choose tongue (rotate across records for coverage)
    if tongue_code is None:
        tongue_code = random.choice(TONGUE_CODES)

    # L0: raw bytes
    raw = user_text.encode('utf-8', errors='replace')
    raw_b64 = base64.b64encode(raw).decode('ascii')

    # L1: tongue tokens
    ss1_tokens = _encode_text(tongue_code, user_text, max_bytes=32)

    # L2: pump packet
    pkt = sense(user_text)

    return CompiledEvent(
        event_id=event_id,
        source=source,
        raw_bytes_b64=raw_b64,
        byte_count=len(raw),
        tongue_code=tongue_code,
        ss1_tokens=ss1_tokens,
        tongue_profile=pkt.tongue_profile,
        null_pattern=pkt.null_pattern,
        null_ratio=pkt.null_ratio,
        dominant_tongue=pkt.dominant_tongue,
        canon=pkt.canon,
        emotion=pkt.emotion,
        governance=pkt.governance,
        user_text=user_text,
        assistant_text=assistant_text,
        system_text=system_text,
    )


def compile_messages(messages: list, **kwargs) -> Optional[CompiledEvent]:
    """Compile a messages-format record into a multi-view event."""
    user_text = ""
    assistant_text = ""
    system_text = ""

    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user":
            user_text = content
        elif role == "assistant":
            assistant_text = content
        elif role == "system":
            system_text = content

    if not user_text or not assistant_text:
        return None

    return compile_event(user_text, assistant_text, system_text, **kwargs)


def compile_batch(records: list, source: str = "") -> List[CompiledEvent]:
    """Compile a batch of records into multi-view events."""
    events = []
    for i, rec in enumerate(records):
        msgs = rec.get("messages", [])
        if not msgs:
            continue

        # Rotate tongues across batch
        tongue_code = TONGUE_CODES[i % 6]

        event = compile_messages(
            msgs,
            source=source,
            event_id=f"{source}-{i:06d}",
            tongue_code=tongue_code,
        )
        if event:
            events.append(event)

    return events
