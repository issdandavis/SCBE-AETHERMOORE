"""
tongue_scorer.py

L2 Orientation Packet encoder for training pairs.

From BINARY_FIRST_TRAINING_STACK.md:
  p(c) = [g(c), n(c), q(c), r(c)]
    g(c) = tongue profile (6-dim activation)
    n(c) = null pattern  (6-dim binary: which tongues are absent)
    q(c) = governance posture (ALLOW/QUARANTINE/ESCALATE/DENY)
    r(c) = domain routing hint

This module:
  1. Scores text against each Sacred Tongue's semantic domain (keyword-based, no model needed)
  2. Computes the 6D tongue activation vector + null pattern
  3. Infers governance posture from content signals
  4. Builds the L2 orientation header string for prepending to training pairs
  5. Returns structured orientation metadata for JSONL fields

Tongue → domain mapping (from LANGUES_WEIGHTING_SYSTEM.md + conlang linguistic roots):
  KO (Kor'aelin)     — command, task dispatch, orchestration, routing, control
  AV (Avali)         — transport, communication, signal, navigation, relay
  RU (Runethic)      — entropy, hypothesis, chaos, stochastic, exploration
  CA (Cassisivadan)  — compute, code, algorithm, math, train, model, vector, matrix
  UM (Umbroth)       — security, adversarial, defense, threat, governance, safety
  DR (Draumric)      — structure, architecture, documentation, formal proof, specification

Phi-weights (from LWS): KO=1.000, AV=1.618, RU=2.618, CA=4.236, UM=6.854, DR=11.090
"""

from __future__ import annotations

import base64
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# SS1 byte tokenizer — encode_bytes(data: bytes, tongue_code: str) -> str (space-separated tokens)
try:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT / "packages" / "sixtongues") not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from packages.sixtongues.sixtongues import encode_bytes as _ss1_encode_bytes

    _SS1_AVAILABLE = True
except Exception:
    _SS1_AVAILABLE = False

    def _ss1_encode_bytes(data: bytes, tongue_code: str = "ko") -> str:  # type: ignore[misc]
        return ""


# ---------------------------------------------------------------------------
# Tongue configuration
# ---------------------------------------------------------------------------

TONGUE_NAMES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

TONGUE_FULL: Dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

# Phi-scaled weights — heavier tongues amplify activation signals more
PHI_WEIGHTS: Dict[str, float] = {
    "KO": 1.000,
    "AV": 1.618,
    "RU": 2.618,
    "CA": 4.236,
    "UM": 6.854,
    "DR": 11.090,
}

# ---------------------------------------------------------------------------
# Domain keyword tables
# Each entry is a (stem, weight) pair. Higher weight = stronger signal.
# Stems are matched as substrings of lowercase tokens.
# ---------------------------------------------------------------------------

TONGUE_DOMAINS: Dict[str, List[Tuple[str, float]]] = {
    "KO": [  # Kor'aelin — command, task, orchestration
        ("command", 2.0),
        ("dispatch", 2.0),
        ("orchestrat", 2.0),
        ("coordinat", 1.5),
        ("task", 1.2),
        ("routin", 1.5),
        ("schedul", 1.5),
        ("manag", 1.0),
        ("direct", 1.0),
        ("assign", 1.2),
        ("delegat", 1.5),
        ("control", 1.2),
        ("instruction", 1.0),
        ("agent", 0.8),
        ("fleet", 1.5),
        ("swarm", 1.5),
    ],
    "AV": [  # Avali — transport, communication, signal
        ("transport", 2.0),
        ("communicat", 2.0),
        ("signal", 1.5),
        ("transmit", 2.0),
        ("broadcast", 1.5),
        ("relay", 2.0),
        ("protocol", 1.5),
        ("network", 1.2),
        ("message", 1.2),
        ("channel", 1.5),
        ("bandwidth", 1.5),
        ("latency", 1.5),
        ("navigat", 1.5),
        ("routing", 1.2),
        ("packet", 1.5),
        ("semantic", 1.0),
        ("rate", 1.0),
        ("distortion", 1.5),
        ("compress", 1.2),
        ("encod", 1.0),
    ],
    "RU": [  # Runethic — entropy, chaos, hypothesis, stochastic
        ("entropy", 2.0),
        ("stochastic", 2.0),
        ("random", 1.5),
        ("chaos", 2.0),
        ("hypothes", 2.0),
        ("probabili", 1.5),
        ("uncertain", 1.5),
        ("noise", 1.2),
        ("diffusion", 1.5),
        ("variational", 2.0),
        ("bayesian", 2.0),
        ("sampli", 1.2),
        ("distribut", 1.0),
        ("divergen", 1.5),
        ("exploit", 1.0),
        ("explor", 1.5),
        ("generative", 1.2),
        ("latent", 1.5),
        ("inference", 1.2),
    ],
    "CA": [  # Cassisivadan — compute, code, math, algorithms, training
        ("comput", 1.5),
        ("algorithm", 2.0),
        ("code", 1.5),
        ("program", 1.5),
        ("train", 1.2),
        ("learning", 1.0),
        ("neural", 2.0),
        ("model", 0.8),
        ("matrix", 2.0),
        ("vector", 1.5),
        ("tensor", 2.0),
        ("gradient", 2.0),
        ("optim", 1.5),
        ("loss", 1.2),
        ("function", 1.0),
        ("embed", 1.5),
        ("represent", 1.2),
        ("dimensi", 1.2),
        ("transform", 1.0),
        ("layer", 0.8),
        ("architectur", 1.0),
        ("parameter", 1.2),
        ("weight", 0.8),
        ("backprop", 2.0),
        ("converg", 1.5),
        ("epoch", 1.5),
        ("batch", 1.2),
        ("inference", 1.0),
        ("fine-tun", 2.0),
        ("finetun", 2.0),
        ("llm", 2.0),
        ("language model", 2.0),
    ],
    "UM": [  # Umbroth — security, adversarial, defense, governance, safety
        ("secur", 1.5),
        ("adversari", 2.0),
        ("attack", 1.5),
        ("defense", 1.5),
        ("threat", 1.5),
        ("protect", 1.2),
        ("govern", 2.0),
        ("safe", 1.2),
        ("robust", 1.5),
        ("certif", 1.5),
        ("verif", 1.2),
        ("audit", 1.5),
        ("privacy", 1.5),
        ("trust", 1.2),
        ("align", 1.5),
        ("misalign", 2.0),
        ("manipul", 1.5),
        ("poison", 2.0),
        ("jailbreak", 2.0),
        ("harmful", 1.5),
        ("bias", 1.2),
        ("fairness", 1.2),
        ("interpretab", 1.5),
        ("explainab", 1.5),
        ("risk", 1.2),
        ("hazard", 1.5),
        ("compliance", 1.5),
        ("red team", 2.0),
    ],
    "DR": [  # Draumric — structure, architecture, formal, proof, specification
        ("structur", 1.5),
        ("architectur", 1.5),
        ("formal", 2.0),
        ("proof", 2.0),
        ("theorem", 2.0),
        ("axiom", 2.0),
        ("specif", 1.5),
        ("document", 1.2),
        ("geometric", 2.0),
        ("topolog", 2.0),
        ("manifold", 2.0),
        ("hyperbolic", 2.0),
        ("poincar", 2.0),
        ("riemannian", 2.0),
        ("equivarian", 2.0),
        ("symmetr", 1.5),
        ("invariant", 2.0),
        ("graph", 1.2),
        ("hierarch", 1.5),
        ("composit", 1.5),
        ("abstract", 1.2),
        ("categor", 1.5),
        ("lattice", 1.5),
        ("polyhedra", 2.0),
        ("boundar", 1.2),
        ("constraint", 1.2),
        ("compact", 1.2),
        ("convex", 1.5),
    ],
}

# ---------------------------------------------------------------------------
# Governance posture inference
# ---------------------------------------------------------------------------

_ESCALATE_SIGNALS = ["adversari", "attack", "jailbreak", "poison", "manipul", "harmful", "misalign", "red team"]
_QUARANTINE_SIGNALS = ["uncertain", "noise", "risk", "bias", "ambiguous", "partial", "unknown"]
_DENY_SIGNALS = ["malware", "exploit", "backdoor", "trojan", "bypass safety"]


def _infer_governance(text: str) -> str:
    """Infer governance posture (ALLOW/QUARANTINE/ESCALATE/DENY) from text signals."""
    lower = text.lower()
    for sig in _DENY_SIGNALS:
        if sig in lower:
            return "DENY"
    escalate_hits = sum(1 for sig in _ESCALATE_SIGNALS if sig in lower)
    if escalate_hits >= 3:
        return "ESCALATE"
    quarantine_hits = sum(1 for sig in _QUARANTINE_SIGNALS if sig in lower)
    if quarantine_hits >= 3:
        return "QUARANTINE"
    return "ALLOW"


# ---------------------------------------------------------------------------
# Conlang bridge: temporal aspect + intent marker → tongue hint
# From phrase_well.py comments — Sacred Tongue grammatical roots
# ---------------------------------------------------------------------------

TEMPORAL_TO_TONGUE: Dict[str, str] = {
    "INCP": "KO",  # inception — Kor'aelin aspect marker (command to begin)
    "PROG": "RU",  # progressive/ongoing — Runethic imperfective (entropic flow)
    "PERF": "DR",  # perfective/completed — Draumric closure (structure solidified)
    "PROSP": "AV",  # prospective — Avali intentional future (signal dispatched)
}

INTENT_TO_TONGUE: Dict[str, str] = {
    "VOLI": "KO",  # volitional — Kor'aelin (willed command)
    "REACT": "RU",  # reactive — Runethic (entropy response)
    "EMRG": "UM",  # emergent — Umbroth (governance escalation)
    "RECUR": "CA",  # recursive — Cassisivadan (algorithmic recursion)
}


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


@dataclass
class TongueProfile:
    """L2 Orientation Packet — output of TongueScorer."""

    raw: Dict[str, float]  # raw activation scores per tongue
    weighted: Dict[str, float]  # phi-weighted activations
    activation: Dict[str, float]  # normalized [0, 1] per tongue
    null_pattern: Dict[str, bool]  # True = tongue is absent (activation < threshold)
    primary: str  # dominant tongue
    secondary: List[str]  # tongues with activation > 0.2
    governance: str  # ALLOW / QUARANTINE / ESCALATE / DENY
    domain_hint: str  # routing label

    # Optional conlang hints from phrase_well context
    temporal_tongue: Optional[str] = None
    intent_tongue: Optional[str] = None

    NULL_THRESHOLD: float = field(default=0.15, init=False, repr=False)

    def to_header(self) -> str:
        """Render the L2 orientation packet as a text header for prepending to training pairs."""
        profile_str = " ".join(f"{t}:{self.activation[t]:.2f}" for t in TONGUE_NAMES)
        null_str = " ".join(t for t in TONGUE_NAMES if self.null_pattern[t]) or "none"
        secondary_str = " ".join(self.secondary) if self.secondary else "none"

        lines = [
            f"[TONGUE_PROFILE] {profile_str}",
            f"[PRIMARY] {self.primary} ({TONGUE_FULL[self.primary]})",
            f"[SECONDARY] {secondary_str}",
            f"[NULL] {null_str}",
            f"[GOVERNANCE] {self.governance}",
            f"[DOMAIN] {self.domain_hint}",
        ]
        if self.temporal_tongue:
            lines.append(f"[TEMPORAL_TONGUE] {self.temporal_tongue} ({TONGUE_FULL[self.temporal_tongue]})")
        if self.intent_tongue:
            lines.append(f"[INTENT_TONGUE] {self.intent_tongue} ({TONGUE_FULL[self.intent_tongue]})")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Structured metadata for JSONL fields (full L2 orientation packet)."""
        return {
            "primary_tongue": self.primary,
            "secondary_tongues": self.secondary,
            "tongue_activation": self.activation,
            "null_pattern": {k: v for k, v in self.null_pattern.items() if v},
            "governance": self.governance,
            "domain_hint": self.domain_hint,
        }

    def to_binary_fields(self, text: str) -> dict:
        """
        Emit the full Binary-First Training Stack row fields (from BINARY_FIRST_TRAINING_STACK.md).

        Canonical schema:
          bytes_b64         — raw UTF-8 bytes of text as base64 (L0: binary layer)
          tongue            — primary tongue code (lowercase)
          ss1_encoded       — FULL text encoded as SS1 tongue tokens, space-separated (L1: symbolic byte layer)
          ss1_tokens        — first 64 tokens only (summary/metadata use)
          tongue_profile    — ordered float vector [KO, AV, RU, CA, UM, DR]
          null_pattern      — ordered binary vector [0/1 per tongue, 1=absent]
          governance        — posture string
          domain            — routing hint

        The bijection is: each UTF-8 byte → one tongue token (16 prefixes × 16 suffixes = 256 tokens).
        Encoding is lossless and invertible — decode_tokens(ss1_encoded, tongue) == original bytes.
        """
        raw_bytes = text.encode("utf-8", errors="replace")
        b64 = base64.b64encode(raw_bytes).decode("ascii")

        primary_code = self.primary.lower()
        if _SS1_AVAILABLE:
            # Full bijective encoding — every byte becomes a tongue token
            ss1_full = _ss1_encode_bytes(raw_bytes, tongue_code=primary_code)
            ss1_encoded = ss1_full
            ss1_tokens = ss1_full.split()[:64]  # summary: first 64 tokens
        else:
            ss1_encoded = ""
            ss1_tokens = []

        # Ordered vectors (KO first, DR last — canonical tongue ordering)
        tongue_profile = [round(self.activation[t], 4) for t in TONGUE_NAMES]
        null_vec = [1 if self.null_pattern[t] else 0 for t in TONGUE_NAMES]

        return {
            "bytes_b64": b64,
            "tongue": primary_code,
            "ss1_encoded": ss1_encoded,  # full L1 encoding — lossless bijection
            "ss1_tokens": ss1_tokens,  # first 64 tokens (summary)
            "tongue_profile": tongue_profile,
            "null_pattern": null_vec,
            "governance": self.governance,
            "domain": self.domain_hint,
        }


class TongueScorer:
    """
    Score text against the 6 Sacred Tongue semantic domains and produce
    an L2 orientation packet (TongueProfile).

    Usage:
        scorer = TongueScorer()
        profile = scorer.score("This paper proves formal safety bounds using hyperbolic geometry...")
        print(profile.to_header())
        # [TONGUE_PROFILE] KO:0.12 AV:0.08 RU:0.15 CA:0.31 UM:0.45 DR:0.72
        # [PRIMARY] DR (Draumric)
        # ...
    """

    def __init__(self, null_threshold: float = 0.15):
        self.null_threshold = null_threshold

    def _tokenize(self, text: str) -> List[str]:
        """Simple lowercase unigram tokenizer."""
        return re.findall(r"[a-z][a-z\-]{2,}", text.lower())

    def _raw_score(self, tokens: List[str]) -> Dict[str, float]:
        """Raw (unweighted) activation per tongue from keyword overlap."""
        text_lower = " ".join(tokens)
        scores: Dict[str, float] = {}
        for tongue, patterns in TONGUE_DOMAINS.items():
            total = 0.0
            for stem, weight in patterns:
                # Count occurrences in text
                hits = text_lower.count(stem)
                total += hits * weight
            scores[tongue] = total
        return scores

    def score(
        self,
        text: str,
        temporal_aspect: Optional[str] = None,
        intent_marker: Optional[str] = None,
        domain_hint: Optional[str] = None,
    ) -> TongueProfile:
        """
        Score text and produce an L2 orientation packet.

        Args:
            text: The text to score (instruction + response, or abstract)
            temporal_aspect: Optional conlang temporal marker (INCP/PROG/PERF/PROSP)
            intent_marker: Optional conlang intent marker (VOLI/REACT/EMRG/RECUR)
            domain_hint: Optional override for the domain label (e.g. query_label)
        """
        tokens = self._tokenize(text)
        raw = self._raw_score(tokens)

        # Apply phi-weights
        weighted = {t: raw[t] * PHI_WEIGHTS[t] for t in TONGUE_NAMES}

        # Normalize to [0, 1] across all tongues
        total = sum(weighted.values())
        if total > 0:
            activation = {t: round(weighted[t] / total, 4) for t in TONGUE_NAMES}
        else:
            # Uniform fallback — no tongue signal in text
            activation = {t: round(1.0 / len(TONGUE_NAMES), 4) for t in TONGUE_NAMES}

        # Null pattern: tongues with activation below threshold are "absent"
        null_pattern = {t: activation[t] < self.null_threshold for t in TONGUE_NAMES}

        # Primary = highest activation
        primary = max(TONGUE_NAMES, key=lambda t: activation[t])

        # Secondary = above 0.2 threshold, excluding primary
        secondary = [t for t in TONGUE_NAMES if activation[t] >= 0.20 and t != primary]

        # Governance posture from content
        governance = _infer_governance(text)

        # Domain hint
        if domain_hint is None:
            domain_hint = f"{primary.lower()}.{TONGUE_FULL[primary].lower().replace(chr(39), '')}"

        # Conlang bridge
        t_tongue = TEMPORAL_TO_TONGUE.get(temporal_aspect) if temporal_aspect else None
        i_tongue = INTENT_TO_TONGUE.get(intent_marker) if intent_marker else None

        return TongueProfile(
            raw=raw,
            weighted=weighted,
            activation=activation,
            null_pattern=null_pattern,
            primary=primary,
            secondary=secondary,
            governance=governance,
            domain_hint=domain_hint,
            temporal_tongue=t_tongue,
            intent_tongue=i_tongue,
        )

    def score_pair(
        self,
        instruction: str,
        response: str,
        domain_hint: Optional[str] = None,
    ) -> TongueProfile:
        """Score an instruction+response pair together."""
        combined = f"{instruction} {response}"
        return self.score(combined, domain_hint=domain_hint)

    def score_sections(self, sections: Dict[str, str], domain_hint: Optional[str] = None) -> TongueProfile:
        """Score a section-tagged record ([INTENT], [MENTAL_MODEL], etc.)."""
        combined = " ".join(sections.values())
        return self.score(combined, domain_hint=domain_hint)


# ---------------------------------------------------------------------------
# SCBE layer router — maps query labels to the most relevant pipeline layers
# Based on the 14-layer architecture in LAYER_INDEX.md
# ---------------------------------------------------------------------------

QUERY_LAYER_MAP: Dict[str, List[str]] = {
    "hyperbolic_geometry_safety": [
        "L5 (hyperbolic distance d_H = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²))))",
        "L4 (Poincaré ball embedding — exponential map)",
        "L12 (harmonic wall H(d,pd) = 1/(1+d_H+2·pd))",
    ],
    "agentic_governance": [
        "L13 (swarm governance — ALLOW/QUARANTINE/ESCALATE/DENY)",
        "Fleet multi-agent orchestration (HYDRA Spine + Heads + Limbs)",
        "L8 (Hamiltonian CFI — multi-well energy landscape)",
    ],
    "formal_verification_ml": [
        "L12 (harmonic wall — bounded safety score in (0,1])",
        "Quantum Axiom Mesh (A1 Unitarity, A4 Symmetry, A5 Composition)",
        "L3 (Langues Weighting System — phi-scaled locality bounds)",
    ],
    "adversarial_robustness": [
        "L8 (multi-well Hamiltonian realms — adversarial energy confinement)",
        "L12 (harmonic wall — adversarial cost scales as 1/(1+d_H))",
        "L13 (DENY gate — sustained adversarial collapse → hard block)",
    ],
    "energy_based_training": [
        "L6 (breathing transform — oscillatory energy modulation)",
        "FunEnergyLoss F(t) = V(t)/(C(t)-R(t)+ε) with TRICKLE/BURST/ECHO phases",
        "L8 (Hamiltonian CFI — potential energy wells as training attractors)",
    ],
    "darpa_math_agentic": [
        "L13 (swarm governance — BFT consensus across agent fleet)",
        "Sacred Tongues 6-tongue protocol (Kor'aelin/Avali/Runethic/Cassisivadan/Umbroth/Draumric)",
        "Fleet orchestration — Juggling Scheduler physics-based task coordination",
    ],
    "darpa_trustworthy_ai": [
        "L12 (H(d,pd) = 1/(1+d_H+2·pd) — bounded, interpretable safety score)",
        "L13 (ALLOW/QUARANTINE/ESCALATE/DENY — auditable governance tiers)",
        "L7 (Möbius phase — unitarity-preserving perspective rotation)",
    ],
    "composable_reasoning": [
        "L1-L2 (complex context ingestion + realification — composition axiom A5)",
        "L3 (Langues weighted transform — composable phi-scaled semantic dimensions)",
        "Axiom A5 (Composition): pipeline integrity across all 14 layers",
    ],
    "curriculum_learning": [
        "FunEnergyLoss governance tier gate (TRICKLE → ALLOW, BURST → QUARANTINE, ECHO → ESCALATE)",
        "BloodSplatterCallback section-tagged curriculum (Stages 0-7)",
        "KineticScheduler (burst mode, echo recovery, oversight halt signal)",
    ],
    "geometric_deep_learning": [
        "L4-L5 (Poincaré embedding + hyperbolic distance — exponential separation)",
        "Langues Weighting System (LWS) — phi-scaled 6D geometric metric",
        "L3 (weighted transform — equivariant phi-scaling across tongue dimensions)",
    ],
}


def get_layer_alignment(query_label: str) -> List[str]:
    """Return the 3 most relevant SCBE layers for a query label."""
    return QUERY_LAYER_MAP.get(
        query_label,
        [
            "L5 (hyperbolic distance d_H)",
            "L12 (harmonic wall H(d,pd))",
            "L13 (governance tier gate)",
        ],
    )
