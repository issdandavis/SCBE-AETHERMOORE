"""Pump Guards — KAIROS-style CPU budget + Undercover Mode output filter.

Two production safety features for the pump:

1. CycleBudget: bounds compute per pump cycle (sense→retrieve→stabilize).
   Prevents runaway processing. Default 15-second wall-clock budget per cycle,
   configurable. If a cycle exceeds budget, it returns a safe fallback state
   instead of hanging.

2. UndercoverFilter: scrubs internal pump state from model outputs before
   they reach the user. Tongue profiles, null patterns, governance posture,
   bundle IDs, and prestate blocks are stripped so the model's proprioception
   stays internal -- like how the brainstem doesn't narrate its own activity.

Usage:
    from polly_pump.guards import CycleBudget, UndercoverFilter

    # Budget
    with CycleBudget(max_seconds=15) as budget:
        packet = sense(text)
        bundles = retriever.retrieve(packet)
        output = stabilize(packet, bundles)
    # If budget exceeded, budget.exceeded is True and budget.fallback is returned

    # Undercover
    uc = UndercoverFilter()
    clean_output = uc.scrub(model_response)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional


# ── KAIROS-style Cycle Budget ──────────────────────────────────────

@dataclass
class CycleBudget:
    """Bounds wall-clock time for a pump cycle.

    Use as a context manager. If the block exceeds max_seconds,
    the exceeded flag is set and downstream code can use fallback.

    Example:
        with CycleBudget(max_seconds=15) as budget:
            do_expensive_work()
        if budget.exceeded:
            return budget.fallback_response
    """
    max_seconds: float = 15.0
    exceeded: bool = False
    elapsed: float = 0.0
    _start: float = 0.0

    # Fallback response when budget is exceeded
    fallback_response: str = (
        "I need a moment to gather my thoughts. "
        "Could you rephrase or try a simpler question?"
    )

    def __enter__(self):
        self._start = time.monotonic()
        self.exceeded = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.monotonic() - self._start
        if self.elapsed > self.max_seconds:
            self.exceeded = True
        return False  # don't suppress exceptions

    def check(self) -> bool:
        """Check budget mid-cycle. Returns True if still within budget."""
        elapsed = time.monotonic() - self._start
        if elapsed > self.max_seconds:
            self.exceeded = True
            return False
        return True

    def remaining(self) -> float:
        """Seconds remaining in budget."""
        return max(0.0, self.max_seconds - (time.monotonic() - self._start))


# ── Undercover Mode Output Filter ─────────────────────────────────

# Patterns that indicate internal pump state leaking into output
_INTERNAL_PATTERNS = [
    # Pump prestate block
    re.compile(r'\[POLLY_PUMP_PRESTATE\].*?\[BUNDLES\].*?(?=\n\n|\Z)', re.DOTALL),
    re.compile(r'\[POLLY_PUMP_PRESTATE\].*?(?=\n\n|\Z)', re.DOTALL),

    # Tongue profile values
    re.compile(r'tongue_profile\s*[:=]\s*\[[\d.,\s]+\]', re.IGNORECASE),
    re.compile(r'(?:KO|AV|RU|CA|UM|DR)\s*=\s*\d+\.\d+', re.IGNORECASE),

    # Null pattern notation
    re.compile(r'null_pattern\s*[:=]\s*[#_]{6}', re.IGNORECASE),
    re.compile(r'\[([#_]{6})\]'),

    # Governance posture labels (when leaked as metadata, not content)
    re.compile(r'governance\s*[:=]\s*(?:ALLOW|QUARANTINE|ESCALATE|DENY)', re.IGNORECASE),
    re.compile(r'governance_posture\s*[:=]', re.IGNORECASE),

    # Bundle IDs and scores
    re.compile(r'bundle_id\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'score\s*[:=]\s*\d+\.\d+'),

    # Source root references
    re.compile(r'source_root\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'source_roots\s*[:=].*', re.IGNORECASE),

    # Dominant tongue metadata
    re.compile(r'dominant_tongue\s*[:=]\s*(?:KO|AV|RU|CA|UM|DR)', re.IGNORECASE),

    # Canon/emotion metadata labels
    re.compile(r'canon\s*[:=]\s*(?:lore|architecture|tokenizer|game|security|meta|general)', re.IGNORECASE),
    re.compile(r'emotion\s*[:=]\s*(?:curious|playful|urgent|reflective|creative|technical|adversarial|neutral)', re.IGNORECASE),

    # Null ratio
    re.compile(r'null_ratio\s*[:=]\s*\d+\.\d+', re.IGNORECASE),

    # Internal system references
    re.compile(r'polly_pump', re.IGNORECASE),
    re.compile(r'pump_packet', re.IGNORECASE),
    re.compile(r'aquifer', re.IGNORECASE),
]

# Feature flag / codename patterns to scrub
_CODENAME_PATTERNS = [
    re.compile(r'\bKAIROS\b'),
    re.compile(r'\bULTRAPLAN\b'),
    re.compile(r'\bBRIDGE_MODE\b'),
    re.compile(r'\bUNDERCOVER\b'),
    re.compile(r'\bYOLO classifier\b', re.IGNORECASE),
]


class UndercoverFilter:
    """Scrubs internal pump state from model outputs.

    The model receives pump state as part of its system prompt
    (that's how orientation works). But the model should NOT
    echo that state back to the user. This filter catches
    any leakage and strips it.

    Think of it as the brainstem not narrating its own activity.
    The cortex speaks. The brainstem stays quiet.
    """

    def __init__(
        self,
        extra_patterns: Optional[list] = None,
        scrub_codenames: bool = True,
    ):
        self.patterns = list(_INTERNAL_PATTERNS)
        if extra_patterns:
            self.patterns.extend(extra_patterns)
        self.scrub_codenames = scrub_codenames
        if scrub_codenames:
            self.patterns.extend(_CODENAME_PATTERNS)

    def scrub(self, text: str) -> str:
        """Remove internal state from output text.

        Returns cleaned text with internal patterns removed.
        Preserves the rest of the content intact.
        """
        result = text
        for pattern in self.patterns:
            result = pattern.sub('', result)

        # Clean up orphaned sentence fragments after scrubbing
        # "By the way, the  and  for this query." → remove
        result = re.sub(r'(?:By the way|Also|Note that|Additionally),?\s*(?:the\s+)?\s*(?:and\s+)?\s*(?:for\s+)?(?:this\s+)?(?:query|input|request)?\.?\s*', '', result)

        # Clean up resulting whitespace (multiple blank lines → one)
        result = re.sub(r'\n{3,}', '\n\n', result)
        # Remove lines that are only whitespace
        result = '\n'.join(line for line in result.split('\n') if line.strip())
        result = result.strip()

        return result

    def has_leakage(self, text: str) -> bool:
        """Check if text contains internal state leakage."""
        for pattern in self.patterns:
            if pattern.search(text):
                return True
        return False

    def detect_leaks(self, text: str) -> list:
        """Return list of detected leak patterns with matches."""
        leaks = []
        for pattern in self.patterns:
            matches = pattern.findall(text)
            if matches:
                leaks.append({
                    'pattern': pattern.pattern,
                    'matches': matches[:3],  # limit to 3 examples
                })
        return leaks
