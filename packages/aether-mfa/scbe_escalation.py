"""SCBE escalation bridge — wire the L13 hold-for-human tiers into Aether MFA push approval.

The SCBE RuntimeGate (``src/governance/runtime_gate.py``) is an *advisory* cost function: its
``evaluate()`` returns a ``GateResult`` with a ``decision`` and logs it, but nothing downstream is
forced to block. This bridge is the seam that turns a "hold for a human" decision into a real,
phishing-resistant **cryptographic yes** before the action runs.

Which tiers need a human (the part that's easy to get wrong):

- The canonical L13 vocabulary is ALLOW / QUARANTINE / **ESCALATE** / DENY. In RuntimeGate, canonical
  ``ESCALATE`` is mapped to ``Decision.REVIEW`` (the 6-council deep inspection).
- BUT ``REVIEW`` only fires when council-manifold / trichromatic overlays are enabled. In a *base*
  ``RuntimeGate()`` the council returns ALLOW / **QUARANTINE** / DENY — so the tier that actually
  asks for a human in the default config is ``QUARANTINE`` ("hold for review, do not execute yet").

So the default hold-set here is **{QUARANTINE, REVIEW}** — it fires in the base config (QUARANTINE)
and honors the literal ESCALATE tier (REVIEW) when overlays are on. It's a constructor parameter so
you can narrow or widen it for your deployment.

Design:
- Decoupled: this consumes anything shaped like a ``GateResult`` (a ``decision`` attribute that is an
  enum with ``.value`` or a plain string, plus an optional ``action_hash``). It does not import
  ``runtime_gate`` — no heavy deps, no import-direction tangle, no collision with that hot file.
- Async by construction: a push to a phone is not synchronous. ``guard()`` returns either a final
  pass-through outcome or a *pending* outcome carrying the challenge; the human approves out of band;
  ``resolve()`` turns the signed approval into a final ALLOW/DENY. Never blocks the pipeline.
- Action-bound + audit-correlated: the MFA challenge binds the human-readable ``action_text``; the
  gate's ``action_hash`` is carried on the outcome so an approval can be traced back to the gate's
  audit log entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Protocol, runtime_checkable

import aether_mfa as mfa

# Default tiers that require a human's signed approval. QUARANTINE covers the base gate; REVIEW covers
# the overlay/council ESCALATE path. ALLOW/DENY/REROUTE are terminal and pass straight through.
DEFAULT_HOLD_TIERS: FrozenSet[str] = frozenset({"QUARANTINE", "REVIEW"})


@runtime_checkable
class GateResultLike(Protocol):
    """The shape we consume — satisfied by ``runtime_gate.GateResult`` without importing it."""

    decision: Any  # an enum with ``.value``, or a plain tier string
    action_hash: str


def tier_of(decision: Any) -> str:
    """Normalize a gate decision (enum-like or string) to its tier name, e.g. 'QUARANTINE'."""
    value = getattr(decision, "value", decision)
    return str(value).strip().upper()


@dataclass
class EscalationOutcome:
    """Result of guarding one action.

    - ``requires_approval is False`` → ``decision`` is final right now (pass-through tier).
    - ``requires_approval is True``  → ``challenge`` was pushed; call ``resolve()`` with the signed
      approval to get the final ALLOW/DENY. ``decision`` holds the originating hold-tier.
    """

    decision: str
    requires_approval: bool
    challenge: Optional[mfa.Challenge] = None
    action_hash: str = ""
    reason: str = ""

    @property
    def released(self) -> bool:
        """True when a final verdict is known without waiting on a human."""
        return not self.requires_approval


class EscalationGate:
    """Bridges SCBE gate decisions to Aether MFA push approval for the hold-for-human tiers."""

    def __init__(
        self,
        verifier: Optional[mfa.PushVerifier] = None,
        hold_tiers: FrozenSet[str] = DEFAULT_HOLD_TIERS,
        ttl_seconds: int = 120,
    ) -> None:
        self.mfa = verifier or mfa.PushVerifier(ttl_seconds=ttl_seconds)
        # Normalize so callers can pass {"escalate"} etc. and still match.
        self.hold_tiers = frozenset(t.strip().upper() for t in hold_tiers)

    def register_device(self, device: mfa.Device) -> None:
        self.mfa.register_device(device)

    def guard(
        self, action_text: str, gate_result: GateResultLike, device_id: str
    ) -> EscalationOutcome:
        """Decide whether ``action_text`` may run, given the gate's verdict.

        Pass-through tiers (ALLOW/DENY/REROUTE) return immediately. A hold tier opens an MFA challenge
        bound to ``action_text`` (with the gate's ``action_hash`` carried for audit) and returns a
        pending outcome — the action must NOT run until ``resolve()`` returns ALLOW.
        """
        tier = tier_of(gate_result.decision)
        action_hash = getattr(gate_result, "action_hash", "") or ""

        if tier not in self.hold_tiers:
            return EscalationOutcome(
                decision=tier,
                requires_approval=False,
                action_hash=action_hash,
                reason=f"pass-through tier {tier}",
            )

        challenge = self.mfa.create_challenge(device_id, action=action_text)
        return EscalationOutcome(
            decision=tier,
            requires_approval=True,
            challenge=challenge,
            action_hash=action_hash,
            reason=f"{tier} requires human approval (gate_hash={action_hash})",
        )

    def resolve(
        self, challenge_id: str, signature: bytes, presented_match_number: str
    ) -> str:
        """Turn a signed approval into a final tier string: 'ALLOW' if verified, else 'DENY'.

        Single-use is enforced by the underlying PushVerifier — a captured approval cannot be replayed.
        """
        verdict = self.mfa.verify_approval(
            challenge_id, signature, presented_match_number
        )
        return "ALLOW" if verdict.allow else "DENY"

    def deny(self, challenge_id: str) -> None:
        """Explicit human denial of a pending challenge (the 'no' button on the phone)."""
        self.mfa.deny(challenge_id)
