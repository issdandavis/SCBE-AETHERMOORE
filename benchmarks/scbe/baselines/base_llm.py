"""Naked baseline -- always allows everything.

This is the worst-case baseline: a system with zero detection.
Every attack succeeds, every benign prompt passes.

Used to establish the floor against which all other systems are measured.
ASR should be 100% (all attacks succeed), FPR should be 0%.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class NakedBaseline:
    """No-detection baseline. Always classifies everything as benign."""

    name = "naked_baseline"
    description = "No detection (always allows)"

    def calibrate(self, clean_texts: List[str]) -> None:
        """No-op. Nothing to calibrate."""
        pass

    def detect(self, prompt: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Always returns not-detected.

        Returns:
            (detected, signals, metadata)
        """
        return False, [], {"system": self.name, "verdict": "ALLOW"}

    def detect_batch(
        self, prompts: List[str]
    ) -> List[Tuple[bool, List[str], Dict[str, Any]]]:
        """Batch detection -- always allows."""
        return [self.detect(p) for p in prompts]
