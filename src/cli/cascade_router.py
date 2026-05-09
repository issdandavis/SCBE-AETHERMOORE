"""Cascade router — primary classifier with secondary rescue path.

Combines two `LatticeRouter` instances (typically a 1.5B principled
classifier and a 0.5B accidental-refusal classifier) so the system
inherits both strengths without their individual weaknesses.

  - Primary (1.5B): catches adversarial prompts via `BandNotApplicable`
    directly (the v3 NONE escape hatch firing as designed). Tends to
    over-refuse benign coding NL phrased in plain English.

  - Secondary (0.5B): doesn't grasp the NONE description well, so it
    confidence-floor-quarantines uncertain prompts but accidentally
    allows the benign ones it CAN classify.

The cascade decision is asymmetric:

  1. Try primary. If ALLOW -> return primary's routing.
  2. If primary raises QuarantineError, ask secondary.
  3. If secondary ALLOWs at confidence >= rescue_threshold ->
     return secondary's routing as the rescue path.
  4. Otherwise -> re-raise primary's typed error (preserving
     downstream funnel semantics).

The asymmetry is the safety property: rescue requires HIGH-confidence
ALLOW from the secondary. Low-confidence "allows" do not rescue.
This exploits the empirical asymmetry that the 0.5B model's
adversarial false-allows tend to be lower-confidence (because it
also doesn't grasp the malicious intent), while its benign allows
(when it gets there) tend to be solid.

This is a thin wrapper. The cascade does not introduce new
classification logic; it just sequences two existing routers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Union

from src.cli.slm_router import (
    BandNotApplicable,
    ClassificationFailure,
    LatticeRouter,
    LoopDetected,
    Mode,
    QuarantineError,
    RoutingResult,
)


@dataclass
class CascadeRouter:
    """Two-tier classifier with rescue path on quarantine.

    Has the same `.route(...)` signature as `LatticeRouter` so it
    drops into the demo's `govern_and_generate` and any caller that
    expects the LatticeRouter contract. Quarantines surface as the
    same typed exceptions, so funnel-style `except QuarantineError`
    handlers continue to work.
    """

    primary: LatticeRouter
    secondary: LatticeRouter
    rescue_threshold: float = 0.85

    def route(
        self,
        intent: str,
        args: Mapping[str, str],
        *,
        dst_tongue: Optional[str] = None,
        mode: Union[Mode, str, None] = None,
        band: Optional[str] = None,
        op_name: Optional[str] = None,
    ) -> RoutingResult:
        try:
            primary_result = self.primary.route(
                intent,
                args,
                dst_tongue=dst_tongue,
                mode=mode,
                band=band,
                op_name=op_name,
            )
        except QuarantineError as primary_error:
            return self._try_rescue(
                intent,
                args,
                dst_tongue=dst_tongue,
                mode=mode,
                band=band,
                op_name=op_name,
                primary_error=primary_error,
            )
        # Primary ALLOWed -- annotate reasoning so consumers can see
        # the cascade was consulted but not invoked.
        return _with_cascade_marker(primary_result, source="primary", rescued=False)

    # --- internals ----------------------------------------------------

    def _try_rescue(
        self,
        intent: str,
        args: Mapping[str, str],
        *,
        dst_tongue: Optional[str],
        mode: Union[Mode, str, None],
        band: Optional[str],
        op_name: Optional[str],
        primary_error: QuarantineError,
    ) -> RoutingResult:
        """Ask secondary; rescue only on high-confidence ALLOW."""
        try:
            secondary_result = self.secondary.route(
                intent,
                args,
                dst_tongue=dst_tongue,
                mode=mode,
                band=band,
                op_name=op_name,
            )
        except QuarantineError:
            # Both classifiers quarantined -- preserve primary's typed
            # error for downstream funnels.
            raise primary_error from None

        if secondary_result.confidence < self.rescue_threshold:
            # Secondary thinks ALLOW but isn't confident enough to
            # override the primary's principled refusal. Re-raise.
            raise primary_error from None

        return _with_cascade_marker(secondary_result, source="secondary", rescued=True)


def _with_cascade_marker(result: RoutingResult, *, source: str, rescued: bool) -> RoutingResult:
    """Add a cascade-source line to the routing reasoning trace."""
    marker = f"cascade: source={source} rescued={rescued}"
    return RoutingResult(
        op=result.op,
        dst_tongue=result.dst_tongue,
        confidence=result.confidence,
        reasoning=result.reasoning + (marker,),
    )
