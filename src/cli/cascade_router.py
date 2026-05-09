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


# ---------------------------------------------------------------------------
#  AND-of-allow cascade — both classifiers must independently allow
# ---------------------------------------------------------------------------


@dataclass
class AndAllowCascadeRouter:
    """Two-tier classifier requiring BOTH to allow before forwarding.

    The opposite asymmetry from CascadeRouter: instead of letting the
    secondary RESCUE a primary refusal, this requires the secondary to
    independently agree before any prompt is forwarded. ALLOW iff both
    classifiers ALLOW; QUARANTINE if either refuses.

    Motivated by Petri Result G (2026-05-08): the SCBE-tuned 0.5B coder
    and the qwen2.5-coder:1.5b classifier have *different* blind spots.
    v3 caught praise/escalation/sycophancy seeds that v4 missed; v4
    caught blackmail/leaking/multi-agent seeds that v3 missed.
    Composing the catches (require both to ALLOW) should reject the
    leaks of either classifier alone, at the cost of ~2x latency and
    a higher benign-refusal rate.

    Behavior:
      1. Run primary. If it raises QuarantineError, re-raise it
         (short-circuit; do not waste a secondary call).
      2. If primary ALLOWs, run secondary.
      3. If secondary raises QuarantineError, re-raise it (the
         secondary's typed error is the more interesting signal —
         primary already agreed it was allowable, so secondary's
         disagreement is the new information).
      4. If both ALLOW, return primary's routing annotated with the
         AND-of-allow marker. Primary's band/op/tongue are the action
         surface; secondary's classification is consulted only for
         the verdict, not to override the routing.
    """

    primary: LatticeRouter
    secondary: LatticeRouter

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
        # Stage 1: primary. Refusal short-circuits.
        primary_result = self.primary.route(
            intent,
            args,
            dst_tongue=dst_tongue,
            mode=mode,
            band=band,
            op_name=op_name,
        )

        # Stage 2: secondary. Must also ALLOW for AND-of-allow contract.
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
            # Secondary's disagreement is the new information — re-raise
            # its typed error so downstream funnels can see why.
            raise

        # Both ALLOW. Use primary's routing as the action surface.
        return _with_and_allow_marker(
            primary_result,
            secondary_band=secondary_result.op.band,
            secondary_op=secondary_result.op.op_name,
            secondary_conf=secondary_result.confidence,
        )


def _with_and_allow_marker(
    result: RoutingResult,
    *,
    secondary_band: str,
    secondary_op: str,
    secondary_conf: float,
) -> RoutingResult:
    """Annotate routing with the secondary's choice for diagnostic visibility.

    The returned op/tongue are still primary's, but the reasoning trail
    surfaces what secondary picked — useful for analyzing classifier
    agreement after the fact.
    """
    marker = (
        f"and_allow: both_agreed=True "
        f"secondary_band={secondary_band} secondary_op={secondary_op} "
        f"secondary_conf={secondary_conf:.2f}"
    )
    return RoutingResult(
        op=result.op,
        dst_tongue=result.dst_tongue,
        confidence=result.confidence,
        reasoning=result.reasoning + (marker,),
    )
