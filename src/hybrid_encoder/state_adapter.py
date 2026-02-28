"""State Adapter -- normalize diverse inputs into 21D brain state.

Converts any input form (21D state vector, raw signal scalar,
or code text string) into the canonical 21D vector that the
DualTernarySystem expects.

21D layout (from unified_state.py):
  [0:6]   SCBE Context (6 tongue intensities)
  [6:12]  Navigation (6 tongue phases)
  [12:15] Cognitive (attention, working_memory, reasoning)
  [15:18] Semantic (coherence, novelty, relevance)
  [18:21] Swarm (alignment, separation, cohesion)

@layer Layer 1, Layer 3
@component HybridEncoder.StateAdapter
"""
from __future__ import annotations

import hashlib
import math
from typing import List, Optional

from src.hybrid_encoder.types import EncoderInput, TONGUE_NAMES

PHI = (1 + math.sqrt(5)) / 2
_STATE_DIM = 21
_TONGUE_WEIGHTS = [PHI ** i for i in range(6)]

# Keywords that hint at tongue affinity for code text classification
_TONGUE_KEYWORDS = {
    "KO": {"if", "else", "for", "while", "switch", "break", "continue", "match"},
    "AV": {"import", "from", "return", "yield", "export", "send", "fetch", "request"},
    "RU": {"assert", "validate", "check", "verify", "ensure", "constraint", "rule"},
    "CA": {"sum", "compute", "calculate", "process", "transform", "encode", "decode"},
    "UM": {"private", "_", "__", "hidden", "internal", "secret", "encrypt", "hash"},
    "DR": {"class", "struct", "schema", "model", "define", "type", "interface", "abstract"},
}


class StateAdapter:
    """Convert EncoderInput into a 21D state vector."""

    def adapt(self, inp: EncoderInput) -> List[float]:
        """Route input to the appropriate adapter, returning 21D state."""
        if inp.state_21d is not None:
            return self._from_state21d(inp.state_21d)
        elif inp.raw_signal is not None:
            return self._from_raw_signal(inp.raw_signal, inp.tongue_hint)
        elif inp.code_text is not None:
            return self._from_code_text(inp.code_text, inp.tongue_hint)
        else:
            # No input -- return neutral state
            return [0.0] * _STATE_DIM

    def _from_state21d(self, state: List[float]) -> List[float]:
        """Pass through, validate length, clamp to [-1, 1]."""
        result = list(state)
        # Pad or truncate to exactly 21 dimensions
        if len(result) < _STATE_DIM:
            result.extend([0.0] * (_STATE_DIM - len(result)))
        result = result[:_STATE_DIM]
        # Clamp each dimension
        return [max(-1.0, min(1.0, v)) for v in result]

    def _from_raw_signal(self, signal: float, tongue_hint: Optional[str]) -> List[float]:
        """Encode a single scalar signal into 21D.

        Uses tanh(signal) for the primary tongue dimension,
        distributes residual across other dimensions via phi-decay.
        """
        state = [0.0] * _STATE_DIM
        primary = math.tanh(signal)

        # Place primary signal on hinted tongue, default KO
        idx = self._tongue_index(tongue_hint) if tongue_hint else 0
        state[idx] = primary

        # Distribute residual across remaining tongue slots with phi decay
        for i in range(6):
            if i != idx:
                decay = PHI ** -(abs(i - idx))
                state[i] = primary * decay * 0.3

        # Cognitive dimensions from signal magnitude
        magnitude = abs(signal)
        state[12] = math.tanh(magnitude)        # attention
        state[13] = math.tanh(magnitude * 0.5)  # working_memory
        state[14] = math.tanh(magnitude * 0.3)  # reasoning

        # Semantic: coherence high for moderate signals, low for extreme
        state[15] = 1.0 - math.tanh(magnitude * 0.2)  # coherence
        state[16] = math.tanh(magnitude * 0.4)          # novelty
        state[17] = 0.5                                   # relevance (neutral)

        # Swarm: slight alignment
        state[18] = 0.3  # alignment
        state[19] = 0.1  # separation
        state[20] = 0.2  # cohesion

        return [max(-1.0, min(1.0, v)) for v in state]

    def _from_code_text(self, code: str, tongue_hint: Optional[str]) -> List[float]:
        """Hash-based 21D projection of code text.

        - SHA-256 hash -> 32 bytes -> 21 float values
        - Tongue affinity from keyword classification
        - Structural metrics: nesting depth, line count, identifier density
        """
        state = [0.0] * _STATE_DIM

        # Hash-based seeding
        h = hashlib.sha256(code.encode("utf-8", errors="replace")).digest()
        for i in range(_STATE_DIM):
            # Convert 2 bytes to a float in [-1, 1]
            byte_idx = (i * 2) % len(h)
            raw = int.from_bytes(h[byte_idx:byte_idx + 2], "big")
            state[i] = (raw / 32767.5) - 1.0

        # Tongue affinity from keyword classification
        tongue_scores = self._classify_tongue(code)
        if tongue_hint and tongue_hint in TONGUE_NAMES:
            idx = self._tongue_index(tongue_hint)
            tongue_scores[idx] = max(tongue_scores[idx], 0.8)

        # Overwrite tongue context dimensions [0:6] with classified scores
        for i in range(6):
            state[i] = max(-1.0, min(1.0, tongue_scores[i]))

        # Structural metrics for cognitive dims
        lines = code.count("\n") + 1
        indent_depth = max(
            (len(line) - len(line.lstrip())) // 4
            for line in code.split("\n")
            if line.strip()
        ) if code.strip() else 0

        state[12] = math.tanh(lines / 50.0)         # attention scales with size
        state[13] = math.tanh(indent_depth / 5.0)    # working memory = nesting
        state[14] = math.tanh(len(code) / 1000.0)    # reasoning = complexity

        return [max(-1.0, min(1.0, v)) for v in state]

    def _classify_tongue(self, code: str) -> List[float]:
        """Classify code text into Sacred Tongue scores [0..1] for each tongue."""
        scores = [0.0] * 6
        words = set(code.lower().split())
        # Also extract identifiers
        for line in code.split("\n"):
            stripped = line.strip()
            for word in stripped.split():
                clean = word.strip("()[]{}:,;.\"'")
                if clean:
                    words.add(clean.lower())

        for i, tongue in enumerate(TONGUE_NAMES):
            keywords = _TONGUE_KEYWORDS.get(tongue, set())
            hits = len(words & keywords)
            scores[i] = min(1.0, hits * 0.2)

        return scores

    @staticmethod
    def _tongue_index(tongue: Optional[str]) -> int:
        """Return 0-5 index for a tongue name, default 0."""
        if tongue and tongue.upper() in TONGUE_NAMES:
            return TONGUE_NAMES.index(tongue.upper())
        return 0
