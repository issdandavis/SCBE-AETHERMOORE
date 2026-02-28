"""Governed Editor -- PollyPad-based dual-zone editor.

Modes: ENGINEERING/NAVIGATION/SYSTEMS/SCIENCE/COMMS/MISSION
Zones: HOT (exploratory, limited tools) / SAFE (execution, full tools)
Promotion from HOT -> SAFE requires SCBE ALLOW decision.

@layer Layer 8, Layer 12, Layer 13
@component AetherIDE.Editor
"""
from __future__ import annotations

from typing import Dict, Tuple

from src.polly_pads_runtime import (
    PollyPad,
    PAD_TOOL_MATRIX,
    PAD_MODE_TONGUE,
    scbe_decide,
    Thresholds,
)


class GovernedEditor:
    """Dual-zone editor with per-mode tool gating."""

    def __init__(self, mode: str = "ENGINEERING", zone: str = "HOT"):
        self._pad = PollyPad(unit_id="aether-ide", mode=mode, zone=zone)
        self._coherence = 1.0
        self._d_star = 0.0
        self._h_eff = 0.0

    def available_tools(self) -> Tuple[str, ...]:
        """Return currently available tools for mode + zone."""
        return self._pad.tools

    def is_tool_allowed(self, tool: str) -> bool:
        """Check if a specific tool is allowed in current mode + zone."""
        return tool in self._pad.tools

    def switch_mode(self, mode: str) -> None:
        """Switch pad mode. Always demotes to HOT zone for safety."""
        self._pad = PollyPad(unit_id="aether-ide", mode=mode, zone="HOT")

    def try_promote(self, d_star: float, coherence: float, h_eff: float) -> bool:
        """Try to promote HOT -> SAFE. Requires SCBE ALLOW."""
        if self._pad.zone == "SAFE":
            return True
        decision = scbe_decide(d_star, coherence, h_eff)
        if decision == "ALLOW":
            self._pad = PollyPad(
                unit_id="aether-ide",
                mode=self._pad.mode,
                zone="SAFE",
            )
            self._update_state(coherence, d_star, h_eff)
            return True
        return False

    def demote(self) -> None:
        """Demote SAFE -> HOT."""
        if self._pad.zone == "SAFE":
            self._pad = PollyPad(
                unit_id="aether-ide",
                mode=self._pad.mode,
                zone="HOT",
            )

    def _update_state(self, coherence: float, d_star: float, h_eff: float) -> None:
        self._coherence = coherence
        self._d_star = d_star
        self._h_eff = h_eff

    @property
    def mode(self) -> str:
        return self._pad.mode

    @property
    def zone(self) -> str:
        return self._pad.zone

    @property
    def tongue(self) -> str:
        return PAD_MODE_TONGUE[self._pad.mode]
