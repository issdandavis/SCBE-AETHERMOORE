"""Authenticated neural evidence gate for Sacred Egg hatching.

Reuses the 21D embedding, five trajectory sensors, and six-state dual-ternary
valence adapter. Geometry measures deviation; it never replaces a signature or
the GeoSeal decrypt. Reports are review evidence, not automatic training labels.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Mapping

import numpy as np

from .detection import CombinedAssessment, run_combined_detection
from .governance_adapter import AsymmetryTracker, GovernanceVerdict, evaluate_governance
from .unified_state import BRAIN_DIMENSIONS, TrajectoryPoint, hyperbolic_distance_safe, safe_poincare_embed

_TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
_SEVERITY = {"ALLOW": 0, "QUARANTINE": 1, "ESCALATE": 2, "DENY": 3}


def _canonical(value: object) -> bytes:
    """Protocol v1 uses sorted compact UTF-8 JSON; reject NaN and infinity."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _verify_mldsa(public_key: bytes, message: bytes, signature: bytes) -> bool:
    # Existing public-key-only verifier refuses simulated PQC, even with the
    # repository's insecure-demo opt-in set. Import lazily for optional backends.
    from crypto.pqc_liboqs import MLDSA65

    return MLDSA65.verify_with_public_key(public_key, message, signature)


@dataclass(frozen=True)
class NeuralGatePolicy:
    """Trusted deployment configuration, never read from an Egg's mutable shell.

    Bounds need calibration against the deployment's benign and adversarial
    traces. The reference is a raw 21D state, not a claimed 'safe' scalar score.
    """

    audience: str
    reference_state: tuple[float, ...]
    max_hyperbolic_distance: float
    min_witnesses: int = 3
    min_samples: int = 8
    max_samples: int = 128
    max_age_seconds: float = 30.0
    max_clock_skew_seconds: float = 2.0
    max_raw_norm: float = 10.0
    ternary_epsilon: float = 0.01

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_state", tuple(self.reference_state))
        if not self.audience or not 1 <= self.min_witnesses <= 32:
            raise ValueError("Require an audience and 1..32 witnesses")
        if not 8 <= self.min_samples <= self.max_samples <= 256:
            raise ValueError("Require 8..256 bounded trajectory samples")
        positive = (self.max_hyperbolic_distance, self.max_age_seconds, self.max_raw_norm, self.ternary_epsilon)
        if not all(math.isfinite(x) and x > 0 for x in positive):
            raise ValueError("Distance, age, raw norm, and epsilon must be finite and positive")
        if not math.isfinite(self.max_clock_skew_seconds) or self.max_clock_skew_seconds < 0:
            raise ValueError("Clock skew must be finite and nonnegative")
        if len(self.reference_state) != BRAIN_DIMENSIONS or not all(map(math.isfinite, self.reference_state)):
            raise ValueError("Reference must be a finite 21D state")
        if math.hypot(*self.reference_state) > self.max_raw_norm or self.max_raw_norm > 10:
            raise ValueError("Raw norm bound must contain the reference and be <= 10 to avoid saturation")


@dataclass(frozen=True)
class NeuralEvidence:
    """Independent trusted witnesses sign the same complete measurement window.

    States and timestamps are copied into immutable tuples. Distances, embedded
    points, sensor scores and valences are recomputed by the verifier.
    """

    nonce: str
    issued_at: float
    states: tuple[tuple[float, ...], ...]
    timestamps: tuple[float, ...]
    signatures: Mapping[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "states", tuple(tuple(row) for row in self.states))
        object.__setattr__(self, "timestamps", tuple(self.timestamps))
        object.__setattr__(self, "signatures", dict(self.signatures))


@dataclass(frozen=True)
class NeuralGateReport:
    """For a trusted local audit sink; never returned as a decryption oracle."""

    decision: str
    reasons: tuple[str, ...]
    max_distance: float | None = None
    sensors: CombinedAssessment | None = None
    transitions: tuple[GovernanceVerdict, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.decision == "ALLOW"


class NeuralEggGate:
    """Authenticate, validate, and assess a hatch request before key use.

    ``claim_nonce(audience, nonce, expires_at)`` must atomically consume a fresh
    challenge in a shared replay store and reject duplicates across workers.
    Witness keys and the signature verifier are trusted server configuration.
    The default verifier uses the existing real ML-DSA-65 implementation.
    A missing backend, verifier failure, or replay-store failure denies access.

    Signers must authorize the request and attest the measurements themselves;
    blindly signing agent-supplied claims provides no measurement provenance.
    """

    def __init__(
        self,
        policy: NeuralGatePolicy,
        witness_keys: Mapping[str, bytes],
        claim_nonce: Callable[[str, str, float], bool],
        *,
        verify_signature: Callable[[bytes, bytes, bytes], bool] = _verify_mldsa,
        clock: Callable[[], float] = time.time,
        audit: Callable[[NeuralGateReport], None] | None = None,
    ):
        keys = dict(witness_keys)
        if not policy.min_witnesses <= len(keys) <= 32:
            raise ValueError("Insufficient or excessive configured witness keys")
        if any(not key or not isinstance(key, bytes) or not name for name, key in keys.items()):
            raise ValueError("Witness names and public keys must be nonempty")
        if len(set(keys.values())) != len(keys):
            raise ValueError("Witnesses must have distinct public keys")
        self.policy = policy
        self._keys = keys
        self._claim_nonce = claim_nonce
        self._verify = verify_signature
        self._clock = clock
        self._audit = audit
        self._reference = safe_poincare_embed(list(policy.reference_state))
        # Bind thresholds, baseline, audience and key set to every signature.
        self._policy_hash = hashlib.sha256(
            _canonical({"policy": asdict(policy), "witness_keys": {k: v.hex() for k, v in keys.items()}})
        ).hexdigest()

    def signing_message(self, request: dict, evidence: NeuralEvidence) -> bytes:
        """Bytes for independent witnesses to sign; no signature covers itself.

        ``request`` includes the entire Egg (shell and envelope), current context,
        tongue, ritual and history. No secret key is included in this transcript.
        """
        return _canonical(
            {
                "protocol": "SCBE/neural-egg-evidence/v1",
                "policy_hash": self._policy_hash,
                "request": request,
                "nonce": evidence.nonce,
                "issued_at": evidence.issued_at,
                "states": evidence.states,
                "timestamps": evidence.timestamps,
            }
        )

    def evaluate(self, request: dict, evidence: NeuralEvidence | None) -> NeuralGateReport:
        """Fail closed and retain per-sensor/per-transition evidence for review."""
        try:
            report = self._evaluate(request, evidence)
        except Exception:
            # Includes unavailable PQC, replay-store outage and numerical errors.
            # An unavailable check must never turn into an ALLOW.
            report = NeuralGateReport("DENY", ("verification_unavailable_or_invalid",))
        if self._audit is not None:
            try:
                self._audit(report)
            except Exception:
                return NeuralGateReport("DENY", ("audit_unavailable",))
        return report

    def _evaluate(self, request: dict, evidence: NeuralEvidence | None) -> NeuralGateReport:
        p = self.policy
        if evidence is None or not p.min_samples <= len(evidence.states) <= p.max_samples:
            return NeuralGateReport("QUARANTINE", ("insufficient_or_excessive_evidence",))
        if not isinstance(evidence.nonce, str) or not 16 <= len(evidence.nonce) <= 128:
            return NeuralGateReport("DENY", ("invalid_nonce",))
        now = self._clock()
        times = evidence.timestamps
        if (
            len(times) != len(evidence.states)
            or not all(math.isfinite(t) for t in (*times, evidence.issued_at, now))
            or any(a >= b for a, b in zip(times, times[1:]))
            or times[0] < now - p.max_age_seconds
            or not times[-1] <= evidence.issued_at <= now + p.max_clock_skew_seconds
        ):
            return NeuralGateReport("DENY", ("stale_or_unordered_evidence",))
        for state in evidence.states:
            if len(state) != BRAIN_DIMENSIONS or not all(map(math.isfinite, state)):
                return NeuralGateReport("DENY", ("invalid_state",))
            if math.hypot(*state) > p.max_raw_norm:
                return NeuralGateReport("DENY", ("embedding_saturation",))
        tongue = _TONGUES.index(request["agent_tongue"])
        context = request["current_context"]
        if len(context) != 6 or not all(map(math.isfinite, context)):
            return NeuralGateReport("DENY", ("invalid_context",))
        if len(evidence.signatures) > len(self._keys) or any(k not in self._keys for k in evidence.signatures):
            return NeuralGateReport("DENY", ("unknown_witness",))
        message = self.signing_message(request, evidence)
        verified = sum(
            self._verify(self._keys[name], message, signature) is True
            for name, signature in evidence.signatures.items()
        )
        if verified < p.min_witnesses:
            return NeuralGateReport("DENY", ("witness_quorum",))
        if self._claim_nonce(p.audience, evidence.nonce, evidence.issued_at + p.max_age_seconds) is not True:
            return NeuralGateReport("DENY", ("replayed_or_unknown_challenge",))

        points = []
        distances = []
        for i, (state, timestamp) in enumerate(zip(evidence.states, times)):
            embedded = safe_poincare_embed(list(state))
            distances.append(hyperbolic_distance_safe(embedded, self._reference))
            # The phase-distance sensor's published baseline uses distance from
            # ball origin. The separate policy bound uses the trusted reference.
            distance = hyperbolic_distance_safe(embedded, [0.0] * BRAIN_DIMENSIONS)
            points.append(TrajectoryPoint(i, list(state), embedded, distance, timestamp=timestamp))
        sensors = run_combined_detection(points, tongue)
        trajectory = np.asarray(evidence.states)
        tracker = AsymmetryTracker()
        transitions = tuple(
            evaluate_governance(
                trajectory[i],
                trajectory[i - 1],
                trajectory=trajectory[: i + 1],
                tracker=tracker,
                epsilon=p.ternary_epsilon,
                align=False,
                contraction_strength=0.0,
            )
            for i in range(1, len(trajectory))
        )
        # Never repair/contract evidence before evaluating it, average away an
        # individual flag, or treat static/missing activity as proof of safety.
        reasons = []
        decisions = [sensors.decision, *(v.decision for v in transitions)]
        if max(distances) > p.max_hyperbolic_distance:
            reasons.append("reference_distance")
            decisions.append("QUARANTINE")
        for sensor in sensors.detections:
            if sensor.flagged:
                reasons.append(f"sensor:{sensor.mechanism}")
                decisions.append("QUARANTINE")
        for violation in sorted({r for v in transitions for r in v.valence_violations}):
            reasons.append(f"valence:{violation}")
            decisions.append("QUARANTINE")
        decision = max(decisions, key=_SEVERITY.__getitem__)
        if decision != "ALLOW" and not reasons:
            reasons.append("combined_anomaly")
        return NeuralGateReport(decision, tuple(reasons), max(distances), sensors, transitions)
