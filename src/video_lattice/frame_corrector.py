"""
Frame corrector — translates hyperbolic drift into generator correction signals.

This is the "error recycling" step:
  1. TemporalTracker detects drift exceeding threshold.
  2. FrameCorrector converts the correction_vector into a format the generator
     (diffusion model, Unreal Engine, neural renderer) can consume.
  3. Correction is injected at the next generation step.

The correction signal has two forms:
  - Latent nudge: a delta vector to add to the diffusion model's latent space.
  - Condition signal: a structured dict describing which semantic axes drifted
    and by how much, for injection as a conditioning signal.

Unreal Engine 5 hook:
  The UE5 Python API (unreal.PythonScriptPlugin or remote execution) can receive
  the condition_signal dict via a TCP socket or file-based IPC.
  The UE5 side applies the correction as camera/lighting/material parameter deltas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .multi_lattice import LatticeAxis
from .temporal_tracker import FrameState, TemporalTracker

_PHI = (1 + math.sqrt(5)) / 2


@dataclass
class CorrectionSignal:
    """Structured correction output for one frame."""
    frame_index: int
    aggregate_drift: float
    cost_signal: float                        # R^(d²) scaling factor
    axis_corrections: Dict[str, float]        # axis → signed correction magnitude
    latent_nudge: Optional[np.ndarray]        # delta for diffusion latent space
    condition_signal: Dict[str, Any]          # structured hint for UE5 / generator
    severity: str                             # "none" | "mild" | "moderate" | "severe"
    # Trijective audit fields (empty/False when no intent anchor is set)
    intent_violated: bool = False
    intent_drift: float = 0.0
    intent_description: str = ""

    def to_ue5_dict(self) -> Dict[str, Any]:
        """Serialize to a flat dict compatible with UE5 Python remote execution."""
        return {
            "frame": self.frame_index,
            "drift": round(self.aggregate_drift, 4),
            "cost": round(self.cost_signal, 4),
            "severity": self.severity,
            "intent_violated": self.intent_violated,
            "intent_drift": round(self.intent_drift, 4),
            **{f"correction_{k}": round(v, 4) for k, v in self.axis_corrections.items()},
        }


class FrameCorrector:
    """Converts temporal tracker output into actionable correction signals.

    Args:
        tracker: TemporalTracker to pull frame states from
        latent_dim: dimension of the diffusion model's latent space
        mild_threshold: drift below this → no correction
        moderate_threshold: drift above this → moderate correction
        severe_threshold: drift above this → severe correction
        cost_base: R in R^(d²), matches tracker's cost_base
    """

    def __init__(
        self,
        tracker: TemporalTracker,
        latent_dim: int = 4096,
        mild_threshold: float = 0.5,
        moderate_threshold: float = 1.5,
        severe_threshold: float = 3.0,
        cost_base: float = _PHI,
    ) -> None:
        self.tracker = tracker
        self.latent_dim = latent_dim
        self.mild_threshold = mild_threshold
        self.moderate_threshold = moderate_threshold
        self.severe_threshold = severe_threshold
        self.cost_base = cost_base
        self._corrections: List[CorrectionSignal] = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def correct(self, state: FrameState) -> CorrectionSignal:
        """Generate a correction signal from a FrameState.

        Args:
            state: FrameState from TemporalTracker.observe()

        Returns:
            CorrectionSignal with latent nudge and condition dict.
        """
        severity = self._classify_severity(state.aggregate_drift)
        d = state.aggregate_drift
        cost = self.cost_base ** (d * d) if d > 0 else 1.0

        # Per-axis correction magnitudes (signed: negative = pull back)
        axis_corrections: Dict[str, float] = {}
        for ax, drift in state.drift_by_axis.items():
            ax_name = ax.value
            if drift > self.mild_threshold:
                axis_corrections[ax_name] = -drift * cost
            else:
                axis_corrections[ax_name] = 0.0

        # Latent nudge from axis corrections
        latent_nudge = None
        if state.correction_triggered and axis_corrections:
            correction_vec = np.array(list(axis_corrections.values()), dtype=np.float64)
            rng = np.random.default_rng(seed=state.frame_index)
            proj = rng.standard_normal((len(correction_vec), self.latent_dim))
            proj /= np.linalg.norm(proj, axis=0, keepdims=True) + 1e-8
            latent_nudge = np.clip(correction_vec @ proj, -5.0, 5.0)

        condition_signal = self._build_condition(state, severity, axis_corrections, cost)

        sig = CorrectionSignal(
            frame_index=state.frame_index,
            aggregate_drift=state.aggregate_drift,
            cost_signal=cost,
            axis_corrections=axis_corrections,
            latent_nudge=latent_nudge,
            condition_signal=condition_signal,
            severity=severity,
            intent_violated=state.intent_violated,
            intent_drift=max(state.intent_drift_by_axis.values()) if state.intent_drift_by_axis else 0.0,
            intent_description=self.tracker.intent_anchor.description if self.tracker.intent_anchor else "",
        )
        self._corrections.append(sig)
        return sig

    # ------------------------------------------------------------------
    # Process a full sequence
    # ------------------------------------------------------------------

    def process_sequence(
        self,
        axis_vector_sequence: List[Dict[LatticeAxis, np.ndarray]],
    ) -> List[CorrectionSignal]:
        """Process a list of frames and return all correction signals."""
        signals = []
        for frame_vectors in axis_vector_sequence:
            state = self.tracker.observe(frame_vectors)
            sig = self.correct(state)
            signals.append(sig)
        return signals

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _classify_severity(self, drift: float) -> str:
        if drift < self.mild_threshold:
            return "none"
        if drift < self.moderate_threshold:
            return "mild"
        if drift < self.severe_threshold:
            return "moderate"
        return "severe"

    def _build_condition(
        self,
        state: FrameState,
        severity: str,
        axis_corrections: Dict[str, float],
        cost: float = 1.0,
    ) -> Dict[str, Any]:
        """Build a structured condition dict for injection into a generator.

        This is the UE5/diffusion bridge — the generator reads this dict
        and applies corresponding corrections to its next-frame generation.
        """
        # Identify which axes need the most correction
        top_drift_axes = sorted(
            ((ax.value, d) for ax, d in state.drift_by_axis.items()),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )[:3]

        anchor = self.tracker.intent_anchor
        return {
            "severity": severity,
            "drift": state.aggregate_drift,
            "cost_multiplier": cost,
            "top_drift_axes": [
                {"axis": name, "drift": round(d, 4)} for name, d in top_drift_axes
            ],
            "axis_corrections": {k: round(v, 4) for k, v in axis_corrections.items()},
            # Trijective audit: human-intent vs machine-representation leg
            "intent": {
                "violated": state.intent_violated,
                "max_drift": round(max(state.intent_drift_by_axis.values()), 4) if state.intent_drift_by_axis else 0.0,
                "by_axis": {ax.value: round(d, 4) for ax, d in state.intent_drift_by_axis.items()},
                "description": anchor.description if anchor else "",
            },
            # UE5-specific hints
            "ue5": {
                "suggest_keyframe": severity in ("moderate", "severe"),
                "apply_motion_blur_correction": "motion" in axis_corrections and axis_corrections.get("motion", 0) != 0,
                "apply_depth_correction": "depth" in axis_corrections and axis_corrections.get("depth", 0) != 0,
                "rerender_priority": {"none": 0, "mild": 1, "moderate": 2, "severe": 3}[severity],
            },
            # Diffusion-model hints
            "diffusion": {
                "inject_latent_nudge": state.correction_triggered,
                "guidance_scale_delta": math.log1p(state.aggregate_drift),
                "denoise_strength": min(0.95, 0.3 + 0.2 * state.aggregate_drift),
            },
        }

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def corrections(self) -> List[CorrectionSignal]:
        return list(self._corrections)

    def summary(self) -> dict:
        if not self._corrections:
            return {"frame_count": 0}
        severities = [c.severity for c in self._corrections]
        intent_violations = sum(1 for c in self._corrections if c.intent_violated)
        return {
            "frame_count": len(self._corrections),
            "severity_counts": {s: severities.count(s) for s in ("none", "mild", "moderate", "severe")},
            "intent_violations": intent_violations,
            "tracker_summary": self.tracker.summary(),
        }
