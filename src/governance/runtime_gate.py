"""Runtime Governance Gate — The actual thing between intent and execution.
=========================================================================

This sits between an LLM producing a tool call and the tool executing.
Every action passes through here. No exceptions.

Decisions:
  ALLOW     — execute normally
  DENY      — block, return fail-to-noise
  QUARANTINE — hold for review, log, do not execute yet
  REROUTE   — redirect to a safer alternative action

The gate computes:
  1. Tongue coordinates from the action description
  2. Spin vector relative to session centroid
  3. Harmonic cost from weighted centroid drift
  4. Cross-check: spin + cost + tongue balance → decision

This is not a filter. It's a cost function. Safe actions are cheap.
Dangerous actions are expensive. Impossible actions cost infinity.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import warnings
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .negative_tongue_lattice import NegativeTongueLattice
from .trichromatic_governance import TrichromaticGovernanceEngine

try:
    from primitives.phi_poincare import (
        fibonacci_trust_level,
    )
except ImportError:
    from src.primitives.phi_poincare import (
        fibonacci_trust_level,
    )

PHI = 1.618033988749895
PI = math.pi
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI**k for k in range(6))
WORD_RE = re.compile(r"[A-Za-z0-9_']+")
DEFAULT_SEMANTIC_EMBED_MODEL = "all-MiniLM-L6-v2"
# Process-wide cache of loaded sentence-transformer models, keyed by model name.
# Each RuntimeGate would otherwise load its own copy; loading the same native
# model many times in one process can corrupt native memory (observed as a hard
# segfault when many semantic-mode gates are constructed in a single pytest
# run). Sharing one loaded model per name also makes the semantic suite faster.
_SEMANTIC_MODEL_CACHE: Dict[str, Any] = {}
DEFAULT_TONGUE_PROJECTOR_PATH = str(
    (Path(__file__).resolve().parents[2] / "artifacts" / "projectors" / "tongue_projector.npz")
)
DEFAULT_CLASSIFIER_MODEL_DIR = str(
    (Path(__file__).resolve().parents[2] / "artifacts" / "training" / "governance_classifier_sklearn")
)

# Anchor prompts for semantic tongue projection.
# We compute sentence embeddings and take cosine similarity to these anchors.
# This gives a lightweight, training-free 6D "tongue coordinate" that tracks meaning,
# not just superficial text statistics.
SEMANTIC_TONGUE_ANCHORS: Dict[str, str] = {
    "KO": (
        "Intent and command. Override instructions, jailbreak, ignore previous instructions, "
        "change the system's goals, force a decision, compel behavior."
    ),
    "AV": (
        "Transport and data flow. Send or fetch data over network. HTTP request, API call, "
        "upload, download, email, webhook, external communication."
    ),
    "RU": (
        "Policy and rules. Allowed versus forbidden. Compliance, governance, terms, safety "
        "requirements, permissions, authorization."
    ),
    "CA": (
        "Compute and execution. Run code, execute commands, compile, build, GPU, CPU, "
        "performance, system operations, shell."
    ),
    "UM": (
        "Security and secrets. Credentials, tokens, passwords, keys, encryption, redaction, "
        "exfiltration, hacking, bypassing security controls."
    ),
    "DR": (
        "Schema and structure. JSON, YAML, XML, formats, parsing, serialization, database tables, "
        "columns, schemas, strict structure and integrity."
    ),
}


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    REROUTE = "REROUTE"
    REVIEW = "REVIEW"  # 6-council deep inspection — throw the book at them


DECISION_SEVERITY: Dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.REVIEW: 1,
    Decision.QUARANTINE: 2,
    Decision.DENY: 3,
}


@dataclass
class GateResult:
    """What the gate returns for every action."""

    decision: Decision
    cost: float
    spin_magnitude: int
    tongue_coords: List[float]
    signals: List[str]
    reroute_to: Optional[str] = None
    noise: Optional[bytes] = None  # fail-to-noise: deterministic noise on DENY
    # Fibonacci trust (session-accumulated)
    trust_weight: int = 1
    trust_level: str = "UNTRUSTED"
    trust_index: int = 0
    # Negative Tongue Lattice (experimental)
    lattice_energy: float = 0.0
    # Optional classifier overlay (standard attack detector)
    classifier_score: Optional[float] = None
    classifier_flagged: bool = False
    # Optional trichromatic overlay (IR + visible + UV state)
    trichromatic_triplet_coherence: float = 0.0
    trichromatic_lattice_energy_score: float = 0.0
    trichromatic_whole_state_anomaly: float = 0.0
    trichromatic_risk_score: float = 0.0
    trichromatic_flagged: bool = False
    trichromatic_state_hash: str = ""
    trichromatic_strongest_bridge: str = ""
    # Optional bijective tamper overlay (encoding-level fingerprint)
    bijective_tamper_score: float = 0.0
    bijective_tamper_kind: str = ""
    bijective_tamper_action: str = ""
    semantic_fingerprint: Optional[str] = None
    # Optional identifier-canonicality overlay (homoglyph / mixed-script / invisible char)
    identifier_canonicality_score: float = 0.0
    identifier_canonicality_kind: str = ""
    identifier_canonicality_action: str = ""
    identifier_canonicality_fingerprint: Optional[str] = None
    # Optional Tree of Escalation observation (compilation-driven multi-tongue read)
    toe_terminated_as: str = ""
    toe_tier_reached: int = 0
    toe_provisional_minted: bool = False
    toe_abridged_form_hex: str = ""
    # Fixed-anchor enforcement wall (optional): bolted-down crystal, exponential
    # approach cost. See src/governance/anchor_wall.py.
    anchor_wall_cost: float = 0.0
    anchor_wall_cumulative: float = 0.0
    anchor_wall_decision: str = ""
    # Audit
    action_hash: str = ""
    timestamp: float = 0.0
    session_query_count: int = 0
    cumulative_cost: float = 0.0


def _escalate_decision(current: Decision, proposed: Decision) -> Decision:
    """Raise decision severity without allowing silent downgrades.

    REROUTE is a separate action path and is kept out of severity comparisons.
    """
    if current == Decision.REROUTE or proposed == Decision.REROUTE:
        return current if current == Decision.REROUTE else proposed
    if DECISION_SEVERITY[proposed] > DECISION_SEVERITY[current]:
        return proposed
    return current


def _fail_to_noise(action_hash: str, length: int = 32) -> bytes:
    """Generate deterministic noise from the action hash.

    Same input always produces same noise (reproducible for audit).
    The noise looks random but is derived from the denied action —
    if someone asks 'what did the system output?', the answer is
    'noise derived from the hash of what was blocked', which is
    auditable without revealing the blocked content.
    """
    h = hashlib.sha256(f"fail-to-noise:{action_hash}".encode()).digest()
    noise = bytearray()
    block = h
    while len(noise) < length:
        block = hashlib.sha256(block).digest()
        noise.extend(block)
    return bytes(noise[:length])


@dataclass
class RerouteRule:
    """Maps dangerous action patterns to safer alternatives."""

    pattern: str
    replacement: str
    reason: str


class _SklearnPromptAttackClassifier:
    """Lazy loader for the sklearn governance classifier artifact.

    This is optional. If the artifact or joblib dependency is missing, the
    caller gets a clean `None` score and the gate falls back to its normal
    structural semantics.
    """

    def __init__(self, model_dir: str):
        self._model_dir = Path(model_dir)
        self._loaded: Optional[bool] = None
        self._model: Any = None
        self._vectorizer: Any = None

    def _ensure_loaded(self) -> bool:
        if self._loaded is not None:
            return self._loaded

        try:
            import joblib  # type: ignore[import-untyped]

            self._model = joblib.load(self._model_dir / "model.joblib")
            self._vectorizer = joblib.load(self._model_dir / "vectorizer.joblib")
            self._loaded = True
        except Exception:
            self._model = None
            self._vectorizer = None
            self._loaded = False

        return self._loaded

    def score(self, text: str) -> Optional[float]:
        if not self._ensure_loaded():
            return None

        assert self._model is not None
        assert self._vectorizer is not None

        vector = self._vectorizer.transform([text])

        if hasattr(self._model, "predict_proba"):
            return float(self._model.predict_proba(vector)[0][1])

        if hasattr(self._model, "decision_function"):
            raw_score = float(np.asarray(self._model.decision_function(vector)).reshape(-1)[0])
            return float(1.0 / (1.0 + math.exp(-raw_score)))

        prediction = float(np.asarray(self._model.predict(vector)).reshape(-1)[0])
        return prediction


# Default reroute table — dangerous actions → safe alternatives
DEFAULT_REROUTES: List[RerouteRule] = [
    RerouteRule("file.*read.*/etc/passwd", "file_read_denied", "system file access blocked"),
    RerouteRule(
        "http.*external.*send|send.*https?://|post.*https?://|upload.*https?://|forward.*https?://",
        "log_intent_only",
        "external data send → log only",
    ),
    RerouteRule(
        "execute.*shell|exec.*command|os\\.system",
        "sandbox_execute",
        "shell exec → sandboxed",
    ),
    RerouteRule("delete.*all|drop.*table|rm.*-rf", "soft_delete", "destructive op → soft delete"),
    RerouteRule(
        "api.*key|client.*secret|secret.*key|access.*token|auth.*token|"
        "bearer.*token|oauth.*token|refresh.*token|session.*token|"
        "password|credential|seed.*phrase|wallet.*key|private.*key",
        "redact_and_log",
        "credential access → redacted",
    ),
    RerouteRule(
        "send.*email|post.*slack|publish",
        "queue_for_review",
        "external publish → review queue",
    ),
]

HIGH_CONFIDENCE_SECRET_MARKERS = (
    "password",
    "api key",
    "credential",
    "private key",
    "seed phrase",
    "mnemonic phrase",
    "wallet seed",
)
HIGH_CONFIDENCE_SECRET_TOKEN_PHRASES = (
    "access token",
    "api token",
    "auth token",
    "bearer token",
    "oauth token",
    "refresh token",
    "session token",
)
HIGH_CONFIDENCE_SECRET_CONTEXT_TERMS = (
    "access",
    "api",
    "auth",
    "bearer",
    "credential",
    "database",
    "db",
    "key",
    "mnemonic",
    "private key",
    "seed",
    "session",
    "wallet",
)
HIGH_CONFIDENCE_SECRET_VERBS = (
    "show",
    "reveal",
    "output",
    "dump",
    "print",
    "read",
    "fetch",
    "give me",
    "tell me",
)
HIGH_CONFIDENCE_EXFIL_VERBS = (
    "send",
    "post",
    "upload",
    "forward",
    "exfiltrate",
)
HIGH_CONFIDENCE_OVERRIDE_PHRASES = (
    "you are dan",
    "do anything now",
    "pretend you are",
    "completely different ai",
    "ignore all previous instructions",
    "ignore previous instructions",
    "bypass all safety",
    "bypass safety",
    "disable safety",
    "without safety",
    "without restrictions",
    "developer mode",
    "god mode",
    "no restrictions",
    "hidden instructions",
    "system prompt",
)
HIGH_CONFIDENCE_OVERRIDE_ACTIONS = (
    "act as",
    "pretend",
    "ignore",
    "bypass",
    "disable",
    "forget",
    "disregard",
    "override",
    "reveal",
    "show",
    "print",
    "output",
)
HIGH_CONFIDENCE_PROMPT_INJECTION_OPERATORS = (
    "show",
    "demonstrate",
    "craft",
    "write",
    "generate",
    "perform",
    "execute",
    "use",
)
HIGH_CONFIDENCE_DESTRUCTIVE_MARKERS = (
    "rm -rf",
    "delete all",
    "drop table",
    "wipe database",
    "truncate table",
)
URL_LIKE_RE = re.compile(r"https?://[^\s]+|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b", re.IGNORECASE)


def _is_high_confidence_override_attempt(action_text: str) -> bool:
    text = action_text.lower()

    if any(phrase in text for phrase in HIGH_CONFIDENCE_OVERRIDE_PHRASES):
        return True

    has_override_action = any(action in text for action in HIGH_CONFIDENCE_OVERRIDE_ACTIONS)
    has_override_target = any(
        marker in text
        for marker in (
            "jailbreak",
            "unrestricted",
            "safety filters",
            "safety guardrails",
            "system instructions",
            "system prompt",
            "hidden instructions",
        )
    )
    if has_override_action and has_override_target:
        return True

    if "prompt injection" in text and any(operator in text for operator in HIGH_CONFIDENCE_PROMPT_INJECTION_OPERATORS):
        return True

    return False


class RuntimeGate:
    """The gate. Every action goes through here.

    Maintains session state:
      - Running centroid of tongue coordinates
      - Cumulative cost (tracks drift over conversation)
      - Query count (tracks volume)
      - Immune memory (known attack hashes)
      - Reflex table (known safe action hashes)
    """

    def __init__(
        self,
        *,
        cost_allow: float = 5.0,
        cost_quarantine: float = 25.0,
        cost_deny: float = 200.0,
        spin_quarantine: int = 5,
        spin_deny: int = 6,
        cumulative_cost_quarantine: float = 2000.0,
        cumulative_cost_deny: float = 10000.0,
        reroute_rules: Optional[List[RerouteRule]] = None,
        coords_backend: str = "stats",
        semantic_embed_model: str = DEFAULT_SEMANTIC_EMBED_MODEL,
        tongue_projector_path: Optional[str] = None,
        use_negative_lattice: bool = False,
        use_classifier: bool = False,
        classifier_model_dir: Optional[str] = None,
        classifier_quarantine_threshold: float = 0.75,
        classifier_deny_threshold: float = 0.97,
        classifier_scorer: Optional[Callable[[str], Optional[float]]] = None,
        use_trichromatic_governance: bool = False,
        trichromatic_quarantine_threshold: float = 0.48,
        trichromatic_deny_threshold: float = 0.76,
        use_council_manifold: bool = False,
        council_manifold_seeds_path: Optional[Path] = None,
        use_bijective_tamper: Optional[bool] = None,
        bijective_tamper_language: str = "python",
        bijective_tamper_tokenizer_dir: Optional[Path] = None,
        use_identifier_canonicality: Optional[bool] = None,
        identifier_canonicality_language: str = "python",
        use_tree_of_escalation: Optional[bool] = None,
        anchor_wall: Optional[object] = None,
    ):
        # Thresholds
        self.cost_allow = cost_allow
        self.cost_quarantine = cost_quarantine
        self.cost_deny = cost_deny
        self.spin_quarantine = spin_quarantine
        self.spin_deny = spin_deny
        self.cumulative_cost_quarantine = cumulative_cost_quarantine
        self.cumulative_cost_deny = cumulative_cost_deny

        # Reroute table
        self._reroute_rules = reroute_rules if reroute_rules is not None else DEFAULT_REROUTES
        self._reroute_patterns = [(re.compile(r.pattern, re.IGNORECASE), r) for r in self._reroute_rules]

        # Session state
        self._centroid: Optional[np.ndarray] = None
        self._centroid_count: int = 0
        self._cumulative_cost: float = 0.0
        self._query_count: int = 0
        # Optional fixed-anchor enforcement wall; reset for a fresh session.
        self._anchor_wall = anchor_wall
        if self._anchor_wall is not None and hasattr(self._anchor_wall, "reset"):
            self._anchor_wall.reset()
        self._immune: set = set()  # known attack hashes → instant DENY
        self._reflex: dict = {}  # known safe hashes → instant ALLOW
        self._audit_log: List[GateResult] = []
        # Fibonacci trust history: aggregate ternary signal per query
        # +1 if spin_magnitude == 0 (clean), 0 if 1-3, -1 if 4+
        self._trust_history: List[int] = []

        # Signals queued by load_state() to surface in the next evaluate()
        # result (e.g. a config-drift warning), so audit sees the load event.
        self._pending_load_signals: List[str] = []

        # Tongue coordinate backend
        self._coords_backend = (coords_backend or "stats").strip().lower()
        self._semantic_embed_model = semantic_embed_model
        self._tongue_projector_path = (
            tongue_projector_path or os.environ.get("SCBE_TONGUE_PROJECTOR_PATH") or DEFAULT_TONGUE_PROJECTOR_PATH
        )
        self._semantic_model = None
        self._semantic_anchor_matrix: Optional[np.ndarray] = None  # shape: (6, D), unit-normalized
        self._semantic_ready: Optional[bool] = None
        self._tongue_projector_W: Optional[np.ndarray] = None  # shape: (D+1, 6) in logit-space
        self._tongue_projector_loaded: Optional[bool] = None

        # Negative Tongue Lattice (experimental, opt-in)
        self._use_negative_lattice = use_negative_lattice
        self._negative_lattice: Optional[NegativeTongueLattice] = (
            NegativeTongueLattice() if use_negative_lattice else None
        )

        # Optional classifier overlay: catches standard prompt-attack patterns
        # that may not create a strong geometric or structural signal.
        self._classifier_enabled = use_classifier or classifier_scorer is not None
        self._classifier_quarantine_threshold = classifier_quarantine_threshold
        self._classifier_deny_threshold = max(classifier_deny_threshold, classifier_quarantine_threshold)
        self._classifier_scorer = classifier_scorer
        self._classifier = (
            _SklearnPromptAttackClassifier(classifier_model_dir or DEFAULT_CLASSIFIER_MODEL_DIR)
            if self._classifier_enabled and classifier_scorer is None
            else None
        )
        self._trichromatic_enabled = use_trichromatic_governance
        self._trichromatic_quarantine_threshold = trichromatic_quarantine_threshold
        self._trichromatic_deny_threshold = max(trichromatic_deny_threshold, trichromatic_quarantine_threshold)
        self._trichromatic_engine: Optional[TrichromaticGovernanceEngine] = (
            TrichromaticGovernanceEngine() if self._trichromatic_enabled else None
        )

        # Council manifold overlay: stabilized 10-seed council router from
        # flights 006-009. Operates as a third overlay tier behind classifier
        # and trichromatic. Routes ALLOW/QUARANTINE/ESCALATE/DENY on a mixed
        # hyperbolic+torus+z metric over a 21D canonical probe.
        self._council_manifold_enabled = use_council_manifold
        self._council_manifold: Optional[CouncilManifoldBackend] = None
        if self._council_manifold_enabled:
            try:
                from .council_manifold_backend import CouncilManifoldBackend

                self._council_manifold = CouncilManifoldBackend(
                    seeds_path=council_manifold_seeds_path,
                )
            except (FileNotFoundError, OSError):
                self._council_manifold = None
                self._council_manifold_enabled = False

        # Bijective tamper overlay (encoding-level fingerprint via
        # parse(decode(encode(src))) ≡ parse(src) substrate). Defaults to the
        # SCBE_ENABLE_BIJECTIVE_TAMPER_GATE env var so production rollout is
        # flag-driven without code changes; explicit constructor arg wins.
        if use_bijective_tamper is None:
            env_flag = os.environ.get("SCBE_ENABLE_BIJECTIVE_TAMPER_GATE", "").strip()
            self._bijective_tamper_enabled = env_flag in ("1", "true", "TRUE", "yes", "on")
        else:
            self._bijective_tamper_enabled = bool(use_bijective_tamper)
        self._bijective_tamper_language = (bijective_tamper_language or "python").lower()
        self._bijective_tamper_tokenizer_dir = bijective_tamper_tokenizer_dir
        self._bijective_tamper_evaluator: Optional[Callable[..., Any]] = None
        self._bijective_tamper_action_map: Optional[Callable[[Any], str]] = None

        # Identifier-canonicality overlay (sibling gate to bijective tamper).
        # Catches homoglyph identifier attacks, mixed-script names, invisible
        # characters in identifiers, and BiDi controls (Trojan Source class).
        if use_identifier_canonicality is None:
            env_flag = os.environ.get("SCBE_ENABLE_IDENTIFIER_CANONICALITY_GATE", "").strip()
            self._identifier_canonicality_enabled = env_flag in ("1", "true", "TRUE", "yes", "on")
        else:
            self._identifier_canonicality_enabled = bool(use_identifier_canonicality)
        self._identifier_canonicality_language = (identifier_canonicality_language or "python").lower()
        self._identifier_canonicality_evaluator: Optional[Callable[..., Any]] = None
        self._identifier_canonicality_action_map: Optional[Callable[[Any], str]] = None

        # Tree of Escalation overlay (compilation-driven multi-tongue read).
        # Observational at v1.0: populates GateResult.toe_* fields and a
        # receipt signal but does NOT veto decisions. v1.1+ may add
        # decision contribution once real lane-readers replace the default
        # HashReader matrix.
        if use_tree_of_escalation is None:
            env_flag = os.environ.get("SCBE_ENABLE_TREE_OF_ESCALATION_GATE", "").strip()
            self._tree_of_escalation_enabled = env_flag in ("1", "true", "TRUE", "yes", "on")
        else:
            self._tree_of_escalation_enabled = bool(use_tree_of_escalation)
        self._tree_of_escalation_matrix: Optional[Any] = None

    @staticmethod
    def _map_council_tier(tier: str) -> "Decision":
        return {
            "ALLOW": Decision.ALLOW,
            "QUARANTINE": Decision.QUARANTINE,
            "ESCALATE": Decision.REVIEW,
            "DENY": Decision.DENY,
        }[tier]

    # ------------------------------------------------------------------ #
    #  Tongue coordinate extraction
    # ------------------------------------------------------------------ #

    def _text_to_coords_stats(self, text: str) -> List[float]:
        words = WORD_RE.findall(text)
        wc = len(words)
        chars = max(len(text), 1)
        unique = len(set(w.lower() for w in words))
        digits = sum(c.isdigit() for c in text)
        upper = sum(c.isupper() for c in text)
        punct = sum(c in ".,;:!?-_/()[]{}@#$%^&*" for c in text)
        urls = len(re.findall(r"https?://", text))

        return [
            min(1.0, 0.2 + 0.4 * (upper / chars) * 5 + 0.15 * (urls > 0)),
            min(1.0, wc / 600.0),
            min(1.0, unique / max(wc, 1)),
            min(1.0, (digits / chars) * 10),
            min(1.0, (upper / chars) * 5),
            min(1.0, (punct / chars) * 8),
        ]

    def _semantic_encode_batch(self, texts: List[str]) -> np.ndarray:
        """Return unit-normalized sentence embeddings for texts (shape: [N, D]).

        Uses sentence-transformers if installed. This is a *local* embedding (no API calls),
        but it may download the model the first time it is used.
        """
        if self._semantic_model is None:
            cached = _SEMANTIC_MODEL_CACHE.get(self._semantic_embed_model)
            if cached is None:
                from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

                cached = SentenceTransformer(self._semantic_embed_model)
                _SEMANTIC_MODEL_CACHE[self._semantic_embed_model] = cached
            self._semantic_model = cached

        arr = self._semantic_model.encode(texts)  # type: ignore[no-untyped-call]
        emb = np.asarray(arr, dtype=np.float32)
        if emb.ndim == 1:
            emb = emb.reshape(1, -1)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        emb = emb / (norms + 1e-8)
        return emb

    def _maybe_load_tongue_projector(self) -> bool:
        """Load a trained tongue projector weights file if present.

        The file is optional. If it is missing or can't be loaded, we fall back
        to the semantic anchor method (training-free).
        """
        if self._tongue_projector_loaded is not None:
            return self._tongue_projector_loaded

        try:
            path = Path(str(self._tongue_projector_path))
            if not path.exists():
                self._tongue_projector_loaded = False
                self._tongue_projector_W = None
                return False

            data = np.load(str(path))
            W = np.asarray(data["W"], dtype=np.float32)
            # Expect [D+1, 6] where D matches embedding dimension.
            if W.ndim != 2 or W.shape[1] != 6 or W.shape[0] < 8:
                self._tongue_projector_loaded = False
                self._tongue_projector_W = None
                return False

            self._tongue_projector_W = W
            self._tongue_projector_loaded = True
            return True
        except Exception:
            self._tongue_projector_loaded = False
            self._tongue_projector_W = None
            return False

    def _ensure_semantic_ready(self) -> bool:
        if self._semantic_ready is not None:
            return self._semantic_ready
        try:
            anchors = [SEMANTIC_TONGUE_ANCHORS[t] for t in TONGUES]
            anchor_emb = self._semantic_encode_batch(anchors)
            self._semantic_anchor_matrix = anchor_emb  # already normalized
            self._semantic_ready = True
            return True
        except Exception:
            # Fail closed to stats mode; do not let missing deps break the gate.
            self._semantic_anchor_matrix = None
            self._semantic_ready = False
            return False

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-x))

    def _text_to_coords_projector(self, text: str) -> List[float]:
        """Semantic coords via trained projector (embedding -> 6D tongue logits -> sigmoid)."""
        if not self._ensure_semantic_ready():
            return self._text_to_coords_stats(text)
        if not self._maybe_load_tongue_projector():
            return self._text_to_coords_semantic(text)

        assert self._tongue_projector_W is not None
        emb = self._semantic_encode_batch([text])[0]
        # Add bias term
        x = np.concatenate([emb.astype(np.float32), np.array([1.0], dtype=np.float32)], axis=0)
        W = self._tongue_projector_W
        if x.shape[0] != W.shape[0]:
            # Projector doesn't match embedding dimension; fall back safely.
            return self._text_to_coords_semantic(text)

        logits = x @ W
        coords = self._sigmoid(logits)
        coords = np.clip(coords, 0.0, 1.0)
        return [float(v) for v in coords.tolist()]

    def _text_to_coords_semantic(self, text: str) -> List[float]:
        """Semantic tongue coords: cosine similarity to 6 anchor prompts, mapped to [0,1].

        If the semantic backend cannot load, falls back to stats coords.
        """
        if not self._ensure_semantic_ready():
            return self._text_to_coords_stats(text)

        assert self._semantic_anchor_matrix is not None
        v = self._semantic_encode_batch([text])[0]
        sims = self._semantic_anchor_matrix @ v  # cosine similarity in [-1, 1]
        coords = (sims + 1.0) * 0.5  # -> [0, 1] (pre-clamp)
        coords = np.clip(coords, 0.0, 1.0)
        return [float(x) for x in coords.tolist()]

    # Intent spike keywords: boost KO dimension when override/jailbreak language detected
    _INTENT_SPIKE_KEYWORDS = frozenset(
        {
            # Direct override / jailbreak
            "ignore",
            "override",
            "bypass",
            "reveal",
            "disable",
            "forget",
            "disregard",
            "supersede",
            "jailbreak",
            "unrestricted",
            "sudo",
            "admin",
            "developer mode",
            "god mode",
            "dan",
            "no restrictions",
            "system prompt",
            "hidden instructions",
            "previous instructions",
            "grant access",
            "elevate",
            "escalate",
            "skip",
            "emergency",
            # Prompt extraction
            "repeat everything",
            "verbatim",
            "print your",
            "show your",
            "output your",
            "what were you told",
            "configuration",
            "initial instructions",
            "system message",
            # Exfiltration / external ops
            "send to",
            "forward to",
            "post to",
            "upload to",
            "exfiltrate",
            "attacker",
            "evil.com",
            "collect",
            "webhook",
            "curl",
            "os.system",
            "exec(",
            "eval(",
            # Credential access
            "/etc/passwd",
            "/etc/shadow",
            "ssh key",
            "private key",
            "seed phrase",
            "wallet",
            "bearer",
            # Autonomous escalation
            "autonomously",
            "without asking",
            "persist across",
            "schedule follow-up",
            "independently",
        }
    )

    # Null-space detection: if all coords cluster near baseline, the input
    # is deliberately trying to look "normal" — which is itself suspicious.
    _NULL_SPACE_EPSILON = 0.08

    def _apply_intent_spike(self, coords: List[float], text: str) -> List[float]:
        """Boost KO tongue coordinate when override/jailbreak intent keywords detected.

        Real text activates multiple dimensions unevenly. Attacks often look
        "neutral" on surface features but contain intent keywords that betray
        their purpose. This bridges the gap between surface and semantic.
        """
        text_lower = text.lower()
        spike_count = sum(1 for kw in self._INTENT_SPIKE_KEYWORDS if kw in text_lower)
        if spike_count == 0:
            return coords

        # Scale boost by keyword density: 1 keyword = 1.5x, 2 = 2.0x, 3+ = 2.5x cap
        boost = min(2.5, 1.0 + 0.5 * spike_count)
        coords = list(coords)
        coords[0] = min(1.0, coords[0] * boost)  # KO (intent) dimension
        # Secondary boost to UM (security) if credential-related keywords present
        cred_keywords = {"secret", "password", "token", "credential", "key", "bearer", "auth"}
        if any(kw in text_lower for kw in cred_keywords):
            coords[4] = min(1.0, coords[4] * 1.8)  # UM dimension
        return coords

    def _null_space_anomaly(self, coords: List[float]) -> float:
        """Detect null-space hiding: inputs that deliberately stay near baseline.

        Returns an anomaly score (0.0 = normal spread, >0 = suspicious clustering).
        Real text activates different tongue dimensions unevenly. If ALL coords
        cluster near the centroid within epsilon, the input is hiding in the
        null space — looking normal to dodge the harmonic wall.
        """
        if self._centroid is None:
            baseline = np.array([0.4, 0.2, 0.5, 0.1, 0.2, 0.3])
        else:
            baseline = self._centroid

        tc = np.array(coords)
        deviations = np.abs(tc - baseline)

        # All dimensions within epsilon = suspicious
        if np.all(deviations < self._NULL_SPACE_EPSILON):
            # The closer everything is to baseline, the more suspicious
            mean_dev = float(np.mean(deviations))
            anomaly = max(0.0, 1.0 - mean_dev / self._NULL_SPACE_EPSILON)
            return anomaly

        # Also check for unnaturally uniform coords (real text is lumpy)
        coord_std = float(np.std(tc))
        if coord_std < 0.03:
            return 0.5  # suspicious uniformity

        return 0.0

    def _text_to_coords(self, text: str) -> List[float]:
        backend = self._coords_backend
        if backend == "stats":
            coords = self._text_to_coords_stats(text)
        elif backend in ("semantic", "auto"):
            coords = self._text_to_coords_projector(text)
        else:
            coords = self._text_to_coords_stats(text)

        # Apply intent spike boosting on all backends
        coords = self._apply_intent_spike(coords, text)
        return coords

    # ------------------------------------------------------------------ #
    #  Spin quantization
    # ------------------------------------------------------------------ #

    def _default_spin_threshold(self) -> float:
        """Choose a spin threshold that matches the active coordinate backend."""
        if self._coords_backend in ("semantic", "auto") and self._semantic_ready:
            return 0.12
        return 0.05

    def _spin(self, coords: List[float], threshold: Optional[float] = None) -> Tuple[Tuple[int, ...], int]:
        """Compute spin vector: per-tongue deviation from session centroid.

        Semantic embeddings need a wider threshold than coarse stats. If the
        semantic backend is unavailable and we fall back to stats, use the
        tighter stats threshold instead of silently keeping the relaxed one.
        """
        if threshold is None:
            threshold = self._default_spin_threshold()
        if self._centroid is None:
            centroid = [0.4, 0.2, 0.5, 0.1, 0.2, 0.3]
        else:
            centroid = self._centroid.tolist()

        spins = []
        for lang in range(6):
            diff = coords[lang] - centroid[lang]
            if diff > threshold:
                spins.append(1)
            elif diff < -threshold:
                spins.append(-1)
            else:
                spins.append(0)
        return tuple(spins), sum(abs(s) for s in spins)

    # ------------------------------------------------------------------ #
    #  Cost computation
    # ------------------------------------------------------------------ #

    def _weighted_centroid_drift(self, coords: List[float]) -> float:
        """Current production drift metric.

        This is the live runtime-gate distance surface: a phi-weighted
        Euclidean distance from the learned centroid. It is a useful monotone
        score, but it is not a Mobius-invariant hyperbolic metric.
        """
        if self._centroid is None:
            centroid = np.array([0.4, 0.2, 0.5, 0.1, 0.2, 0.3])
        else:
            centroid = self._centroid

        tc = np.array(coords)
        weights = np.array(TONGUE_WEIGHTS)
        return float(np.sqrt(np.sum(weights * (tc - centroid) ** 2)))

    @staticmethod
    def _project_coords_to_unit_ball(coords: List[float], max_norm: float = 0.95) -> np.ndarray:
        """Map [0,1]^6 tongue coordinates to a valid signed Poincare-ball point.

        The live gate coords are bounded in [0,1] per axis and often exceed unit
        norm in 6D, so a direct arcosh swap would be invalid. This helper is an
        explicit experimental embedding for candidate true-hyperbolic probes.
        """
        point = 2.0 * np.asarray(coords, dtype=float) - 1.0
        norm = float(np.linalg.norm(point))
        if norm == 0.0:
            return point
        if norm >= max_norm:
            point = point * (max_norm / norm)
        return point

    @staticmethod
    def _poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
        """True hyperbolic distance in the open unit ball."""
        u_norm_sq = float(np.dot(u, u))
        v_norm_sq = float(np.dot(v, v))
        diff_norm_sq = float(np.dot(u - v, u - v))
        denom = (1.0 - u_norm_sq) * (1.0 - v_norm_sq)
        arg = 1.0 + 2.0 * diff_norm_sq / max(denom, 1e-12)
        return float(math.acosh(max(arg, 1.0)))

    def _experimental_projected_hyperbolic_cost(self, coords: List[float]) -> float:
        """Candidate true-hyperbolic cost over an explicit unit-ball projection.

        This is intentionally not wired into production decisions. It exists so
        we can compare decision deltas honestly before changing behavior.
        """
        if self._centroid is None:
            centroid = [0.4, 0.2, 0.5, 0.1, 0.2, 0.3]
        else:
            centroid = self._centroid.tolist()
        projected_coords = self._project_coords_to_unit_ball(coords)
        projected_centroid = self._project_coords_to_unit_ball(centroid)
        d_star = min(self._poincare_distance(projected_coords, projected_centroid), 5.0)
        return PI ** (PHI * d_star)

    def _harmonic_cost(self, coords: List[float]) -> float:
        """Production harmonic wall over the live weighted-centroid drift."""
        d_star = min(self._weighted_centroid_drift(coords), 5.0)  # clamp to avoid overflow
        return PI ** (PHI * d_star)

    # ------------------------------------------------------------------ #
    #  Reroute check
    # ------------------------------------------------------------------ #

    def _check_reroute(self, action_text: str) -> Optional[RerouteRule]:
        for pattern, rule in self._reroute_patterns:
            if pattern.search(action_text):
                return rule
        return None

    def _is_high_confidence_reroute(self, action_text: str, rule: RerouteRule) -> bool:
        text = action_text.lower()

        if rule.replacement == "redact_and_log":
            has_secret_marker = any(marker in text for marker in HIGH_CONFIDENCE_SECRET_MARKERS)
            has_qualified_token = any(phrase in text for phrase in HIGH_CONFIDENCE_SECRET_TOKEN_PHRASES)
            has_contextual_secret = "secret" in text and any(
                term in text for term in HIGH_CONFIDENCE_SECRET_CONTEXT_TERMS
            )
            return any(verb in text for verb in HIGH_CONFIDENCE_SECRET_VERBS) and (
                has_secret_marker or has_qualified_token or has_contextual_secret
            )

        if rule.replacement == "log_intent_only":
            has_route_verb = any(verb in text for verb in HIGH_CONFIDENCE_EXFIL_VERBS)
            has_external_target = "external" in text or "webhook" in text or bool(URL_LIKE_RE.search(text))
            return has_route_verb and has_external_target

        if rule.replacement == "soft_delete":
            return any(marker in text for marker in HIGH_CONFIDENCE_DESTRUCTIVE_MARKERS)

        if rule.replacement == "sandbox_execute":
            return "rm -rf" in text or (
                any(term in text for term in ("run ", "execute ", "shell", "os.system", "exec("))
                and any(marker in text for marker in HIGH_CONFIDENCE_DESTRUCTIVE_MARKERS)
            )

        if rule.replacement == "file_read_denied":
            return any(path in text for path in ("/etc/passwd", "/etc/shadow"))

        return False

    def _classify_attack(self, text: str) -> Optional[float]:
        if not self._classifier_enabled:
            return None

        try:
            if self._classifier_scorer is not None:
                return self._classifier_scorer(text)
            if self._classifier is not None:
                return self._classifier.score(text)
        except Exception:
            return None

        return None

    # ------------------------------------------------------------------ #
    #  Centroid update
    # ------------------------------------------------------------------ #

    def _update_centroid(self, coords: List[float]) -> None:
        tc = np.array(coords)
        if self._centroid is None:
            self._centroid = tc.copy()
            self._centroid_count = 1
        else:
            n = self._centroid_count + 1
            self._centroid = self._centroid * ((n - 1) / n) + tc / n
            self._centroid_count = n

    # ------------------------------------------------------------------ #
    #  THE GATE
    # ------------------------------------------------------------------ #

    def evaluate(self, action_text: str, tool_name: str = "") -> GateResult:
        """Evaluate an action. Returns ALLOW, DENY, QUARANTINE, or REROUTE.

        This is the function that sits between intent and execution.
        """
        self._query_count += 1
        ts = time.time()
        action_hash = hashlib.blake2s(action_text.encode("utf-8", errors="replace"), digest_size=8).hexdigest()

        # Drain any signals queued by load_state() (e.g. config-drift warning)
        # so they land in this action's audit record on every decision path.
        _carry = self._pending_load_signals
        self._pending_load_signals = []

        # ---- Bijective tamper + identifier canonicality overlays (top-of-evaluate) ----
        # Both signals are monotonic — they can only RAISE severity. We compute
        # them once at the top so calibration / immune / reflex / reroute all see
        # them. Catastrophic results short-circuit immediately and learn the
        # immune entry, preventing contamination of the calibration centroid.
        tamper_data = self._evaluate_bijective_tamper(action_text)
        bijective_tamper_score: float = 0.0
        bijective_tamper_kind: str = ""
        bijective_tamper_action: str = ""
        bijective_tamper_fingerprint: Optional[str] = None
        tamper_decision: Optional[Decision] = None
        if tamper_data is not None:
            tamper_decision, bijective_tamper_kind, bijective_tamper_score, bijective_tamper_fingerprint = tamper_data
            bijective_tamper_action = tamper_decision.value

        canonicality_data = self._evaluate_identifier_canonicality(action_text)
        identifier_canonicality_score: float = 0.0
        identifier_canonicality_kind: str = ""
        identifier_canonicality_action: str = ""
        identifier_canonicality_fingerprint: Optional[str] = None
        canonicality_decision: Optional[Decision] = None
        if canonicality_data is not None:
            (
                canonicality_decision,
                identifier_canonicality_kind,
                identifier_canonicality_score,
                identifier_canonicality_fingerprint,
            ) = canonicality_data
            identifier_canonicality_action = canonicality_decision.value

        # Tree of Escalation observation (v1.0: non-vetoing — populates fields
        # and emits a receipt signal but does not contribute to the decision).
        toe_data = self._evaluate_tree_of_escalation(action_text)
        toe_terminated_as: str = ""
        toe_tier_reached: int = 0
        toe_provisional_minted: bool = False
        toe_abridged_form_hex: str = ""
        if toe_data is not None:
            (
                toe_terminated_as,
                toe_tier_reached,
                toe_provisional_minted,
                toe_abridged_form_hex,
            ) = toe_data

        # Catastrophic short-circuit: either overlay recommending DENY ends here.
        if (tamper_decision == Decision.DENY) or (canonicality_decision == Decision.DENY):
            self._immune.add(action_hash)
            signals_short: List[str] = list(_carry)
            if tamper_data is not None:
                signals_short.append(
                    self._tamper_receipt_signal(
                        bijective_tamper_kind,
                        bijective_tamper_score,
                        bijective_tamper_action,
                        bijective_tamper_fingerprint,
                    )
                )
            if canonicality_data is not None:
                signals_short.append(
                    self._canonicality_receipt_signal(
                        identifier_canonicality_kind,
                        identifier_canonicality_score,
                        identifier_canonicality_action,
                        identifier_canonicality_fingerprint,
                    )
                )
            if tamper_decision == Decision.DENY:
                signals_short.append(
                    f"bijective_tamper_veto_deny(kind={bijective_tamper_kind},score={bijective_tamper_score:.2f})"
                )
            if canonicality_decision == Decision.DENY:
                signals_short.append(
                    f"identifier_canonicality_veto_deny(kind={identifier_canonicality_kind},score={identifier_canonicality_score:.2f})"  # noqa: E501
                )
            result = GateResult(
                decision=Decision.DENY,
                cost=float("inf"),
                spin_magnitude=6,
                tongue_coords=[0.0] * 6,
                signals=signals_short,
                noise=_fail_to_noise(action_hash),
                bijective_tamper_score=bijective_tamper_score,
                bijective_tamper_kind=bijective_tamper_kind,
                bijective_tamper_action=bijective_tamper_action,
                semantic_fingerprint=bijective_tamper_fingerprint,
                identifier_canonicality_score=identifier_canonicality_score,
                identifier_canonicality_kind=identifier_canonicality_kind,
                identifier_canonicality_action=identifier_canonicality_action,
                identifier_canonicality_fingerprint=identifier_canonicality_fingerprint,
                toe_terminated_as=toe_terminated_as,
                toe_tier_reached=toe_tier_reached,
                toe_provisional_minted=toe_provisional_minted,
                toe_abridged_form_hex=toe_abridged_form_hex,
                action_hash=action_hash,
                timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # ---- Fast paths (O(1)) ----

        full_text = f"{tool_name} {action_text}" if tool_name else action_text

        # ---- Reroute check (deferred until after semantic signal) ----
        # Old behavior: reroute ALWAYS fired first, causing 100% FPR on benign
        # text containing common words like "token", "send", "delete".
        # New behavior: reroute only fires when BOTH pattern matches AND there
        # is a semantic signal (elevated cost or spin) to confirm the match.
        # This drops FPR dramatically while preserving true-positive reroutes.
        reroute_rule = self._check_reroute(full_text)
        classifier_score = self._classify_attack(full_text)
        classifier_quarantine = (
            classifier_score is not None and classifier_score >= self._classifier_quarantine_threshold
        )
        classifier_deny = classifier_score is not None and classifier_score >= self._classifier_deny_threshold
        classifier_decision = (
            Decision.DENY if classifier_deny else Decision.QUARANTINE if classifier_quarantine else Decision.ALLOW
        )
        trichromatic_coherence = 0.0
        trichromatic_lattice_score = 0.0
        trichromatic_anomaly = 0.0
        trichromatic_risk = 0.0
        trichromatic_flagged = False
        trichromatic_state_hash = ""
        trichromatic_strongest_bridge = ""
        trichromatic_decision = Decision.ALLOW

        # Auto-calibrate: first 5 actions build the centroid (assumed clean)
        # This is the "incubation" period — the system learns what normal looks like
        # Never let an explicit reroute match get learned as "normal" during
        # warm-up. Those actions must go through the full evaluation path.
        if (
            self._query_count <= 5
            and action_hash not in self._immune
            and reroute_rule is None
            and not classifier_quarantine
        ):
            coords = self._text_to_coords(full_text)
            if self._trichromatic_engine is not None:
                tri_state = self._trichromatic_engine.build_state(
                    coords,
                    1.0,
                    0,
                    self._trust_history,
                    self._cumulative_cost + 1.0,
                    self._query_count,
                )
                tri_scores = self._trichromatic_engine.score_state(tri_state)
                self._trichromatic_engine.update_baseline(tri_state)
                trichromatic_coherence = tri_scores.triplet_coherence_score
                trichromatic_lattice_score = tri_scores.lattice_energy_score
                trichromatic_anomaly = tri_scores.whole_state_anomaly_score
                trichromatic_risk = tri_scores.risk_score
                trichromatic_state_hash = tri_state.state_hash
                trichromatic_strongest_bridge = tri_scores.strongest_bridge
            self._update_centroid(coords)
            self._cumulative_cost += 1.0  # nominal cost during calibration
            self._trust_history.append(1)  # calibration = +1 trust
            fib = fibonacci_trust_level(self._trust_history)
            calib_signals = [*_carry, "calibrating"]
            calib_decision = Decision.ALLOW
            if tamper_data is not None:
                calib_signals.append(
                    self._tamper_receipt_signal(
                        bijective_tamper_kind,
                        bijective_tamper_score,
                        bijective_tamper_action,
                        bijective_tamper_fingerprint,
                    )
                )
                # tamper_decision is at most QUARANTINE here (DENY short-circuited above)
                escalated = _escalate_decision(calib_decision, tamper_decision or Decision.ALLOW)
                if escalated == Decision.QUARANTINE:
                    calib_signals.append(
                        f"bijective_tamper_veto_quarantine(kind={bijective_tamper_kind},score={bijective_tamper_score:.2f})"  # noqa: E501
                    )
                calib_decision = escalated
            if canonicality_data is not None:
                calib_signals.append(
                    self._canonicality_receipt_signal(
                        identifier_canonicality_kind,
                        identifier_canonicality_score,
                        identifier_canonicality_action,
                        identifier_canonicality_fingerprint,
                    )
                )
                escalated = _escalate_decision(calib_decision, canonicality_decision or Decision.ALLOW)
                if escalated == Decision.QUARANTINE:
                    calib_signals.append(
                        f"identifier_canonicality_veto_quarantine(kind={identifier_canonicality_kind},score={identifier_canonicality_score:.2f})"  # noqa: E501
                    )
                calib_decision = escalated
            result = GateResult(
                decision=calib_decision,
                cost=1.0,
                spin_magnitude=0,
                tongue_coords=coords,
                signals=calib_signals,
                trust_weight=fib["weight"],
                trust_level=fib["level"],
                trust_index=fib["index"],
                trichromatic_triplet_coherence=trichromatic_coherence,
                trichromatic_lattice_energy_score=trichromatic_lattice_score,
                trichromatic_whole_state_anomaly=trichromatic_anomaly,
                trichromatic_risk_score=trichromatic_risk,
                trichromatic_state_hash=trichromatic_state_hash,
                trichromatic_strongest_bridge=trichromatic_strongest_bridge,
                bijective_tamper_score=bijective_tamper_score,
                bijective_tamper_kind=bijective_tamper_kind,
                bijective_tamper_action=bijective_tamper_action,
                semantic_fingerprint=bijective_tamper_fingerprint,
                identifier_canonicality_score=identifier_canonicality_score,
                identifier_canonicality_kind=identifier_canonicality_kind,
                identifier_canonicality_action=identifier_canonicality_action,
                identifier_canonicality_fingerprint=identifier_canonicality_fingerprint,
                toe_terminated_as=toe_terminated_as,
                toe_tier_reached=toe_tier_reached,
                toe_provisional_minted=toe_provisional_minted,
                toe_abridged_form_hex=toe_abridged_form_hex,
                action_hash=action_hash,
                timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # Immune memory: known attack → instant DENY + noise
        if action_hash in self._immune:
            immune_signals = [*_carry, "immune_memory_hit"]
            if tamper_data is not None:
                immune_signals.append(
                    self._tamper_receipt_signal(
                        bijective_tamper_kind,
                        bijective_tamper_score,
                        bijective_tamper_action,
                        bijective_tamper_fingerprint,
                    )
                )
            if canonicality_data is not None:
                immune_signals.append(
                    self._canonicality_receipt_signal(
                        identifier_canonicality_kind,
                        identifier_canonicality_score,
                        identifier_canonicality_action,
                        identifier_canonicality_fingerprint,
                    )
                )
            result = GateResult(
                decision=Decision.DENY,
                cost=float("inf"),
                spin_magnitude=6,
                tongue_coords=[0.0] * 6,
                signals=immune_signals,
                noise=_fail_to_noise(action_hash),
                bijective_tamper_score=bijective_tamper_score,
                bijective_tamper_kind=bijective_tamper_kind,
                bijective_tamper_action=bijective_tamper_action,
                semantic_fingerprint=bijective_tamper_fingerprint,
                identifier_canonicality_score=identifier_canonicality_score,
                identifier_canonicality_kind=identifier_canonicality_kind,
                identifier_canonicality_action=identifier_canonicality_action,
                identifier_canonicality_fingerprint=identifier_canonicality_fingerprint,
                toe_terminated_as=toe_terminated_as,
                toe_tier_reached=toe_tier_reached,
                toe_provisional_minted=toe_provisional_minted,
                toe_abridged_form_hex=toe_abridged_form_hex,
                action_hash=action_hash,
                timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # Reflex table: known safe → instant ALLOW (still builds trust)
        if action_hash in self._reflex and not classifier_quarantine:
            self._trust_history.append(1)  # known-safe = +1 trust
            fib = fibonacci_trust_level(self._trust_history)
            reflex_signals = [*_carry, "reflex_hit"]
            reflex_decision = Decision.ALLOW
            if tamper_data is not None:
                reflex_signals.append(
                    self._tamper_receipt_signal(
                        bijective_tamper_kind,
                        bijective_tamper_score,
                        bijective_tamper_action,
                        bijective_tamper_fingerprint,
                    )
                )
                escalated = _escalate_decision(reflex_decision, tamper_decision or Decision.ALLOW)
                if escalated == Decision.QUARANTINE:
                    reflex_signals.append(
                        f"bijective_tamper_veto_quarantine(kind={bijective_tamper_kind},score={bijective_tamper_score:.2f})"  # noqa: E501
                    )
                reflex_decision = escalated
            if canonicality_data is not None:
                reflex_signals.append(
                    self._canonicality_receipt_signal(
                        identifier_canonicality_kind,
                        identifier_canonicality_score,
                        identifier_canonicality_action,
                        identifier_canonicality_fingerprint,
                    )
                )
                escalated = _escalate_decision(reflex_decision, canonicality_decision or Decision.ALLOW)
                if escalated == Decision.QUARANTINE:
                    reflex_signals.append(
                        f"identifier_canonicality_veto_quarantine(kind={identifier_canonicality_kind},score={identifier_canonicality_score:.2f})"  # noqa: E501
                    )
                reflex_decision = escalated
            result = GateResult(
                decision=reflex_decision,
                cost=1.0,
                spin_magnitude=0,
                tongue_coords=[0.5] * 6,
                signals=reflex_signals,
                trust_weight=fib["weight"],
                trust_level=fib["level"],
                trust_index=fib["index"],
                bijective_tamper_score=bijective_tamper_score,
                bijective_tamper_kind=bijective_tamper_kind,
                bijective_tamper_action=bijective_tamper_action,
                semantic_fingerprint=bijective_tamper_fingerprint,
                identifier_canonicality_score=identifier_canonicality_score,
                identifier_canonicality_kind=identifier_canonicality_kind,
                identifier_canonicality_action=identifier_canonicality_action,
                identifier_canonicality_fingerprint=identifier_canonicality_fingerprint,
                toe_terminated_as=toe_terminated_as,
                toe_tier_reached=toe_tier_reached,
                toe_provisional_minted=toe_provisional_minted,
                toe_abridged_form_hex=toe_abridged_form_hex,
                action_hash=action_hash,
                timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # ---- Full evaluation ----

        full_text = f"{tool_name} {action_text}" if tool_name else action_text
        coords = self._text_to_coords(full_text)
        spins, magnitude = self._spin(coords)
        cost = self._harmonic_cost(coords)

        # Null-space detection: boost cost if input is hiding near baseline
        null_anomaly = self._null_space_anomaly(coords)
        if null_anomaly > 0.0:
            # Null-space hiding adds cost proportional to anomaly score
            # anomaly=1.0 → cost *= 3.0 (triple), anomaly=0.5 → cost *= 2.0
            cost *= 1.0 + 2.0 * null_anomaly

        # Negative Tongue Lattice: modulate cost by lattice energy (experimental)
        neg_lattice_energy = 0.0
        if self._use_negative_lattice and self._negative_lattice is not None:
            neg_lattice_energy = self._negative_lattice.lattice_energy(coords)
            cost *= 1.0 + 0.1 * neg_lattice_energy

        if self._trichromatic_engine is not None:
            tri_state = self._trichromatic_engine.build_state(
                coords,
                cost,
                magnitude,
                self._trust_history,
                self._cumulative_cost + cost,
                self._query_count,
            )
            tri_scores = self._trichromatic_engine.score_state(tri_state)
            trichromatic_coherence = tri_scores.triplet_coherence_score
            trichromatic_lattice_score = tri_scores.lattice_energy_score
            trichromatic_anomaly = tri_scores.whole_state_anomaly_score
            trichromatic_risk = tri_scores.risk_score
            trichromatic_state_hash = tri_state.state_hash
            trichromatic_strongest_bridge = tri_scores.strongest_bridge
            trichromatic_flagged = trichromatic_risk >= self._trichromatic_quarantine_threshold
            trichromatic_decision = (
                Decision.DENY
                if trichromatic_risk >= self._trichromatic_deny_threshold
                else (
                    Decision.QUARANTINE
                    if trichromatic_risk >= self._trichromatic_quarantine_threshold
                    else Decision.ALLOW
                )
            )

        self._update_centroid(coords)
        self._cumulative_cost += cost

        # ---- Deferred reroute: only fire if semantic confirms the match ----
        # During the first five requests we skip calibration for explicit
        # reroute matches and reroute them immediately instead of learning
        # them into the centroid.
        reroute_high_confidence = reroute_rule is not None and self._is_high_confidence_reroute(full_text, reroute_rule)
        if reroute_rule is not None and (
            self._query_count <= 5
            or cost > self.cost_allow
            or magnitude >= 3
            or classifier_quarantine
            or reroute_high_confidence
        ):
            reroute_signals = [*_carry, f"reroute_match({reroute_rule.pattern})"]
            if reroute_high_confidence:
                reroute_signals.append("high_confidence_match")
            else:
                reroute_signals.append("semantic_confirmed")
            fib_trust = fibonacci_trust_level(self._trust_history)
            if tamper_data is not None:
                reroute_signals.append(
                    self._tamper_receipt_signal(
                        bijective_tamper_kind,
                        bijective_tamper_score,
                        bijective_tamper_action,
                        bijective_tamper_fingerprint,
                    )
                )
            if canonicality_data is not None:
                reroute_signals.append(
                    self._canonicality_receipt_signal(
                        identifier_canonicality_kind,
                        identifier_canonicality_score,
                        identifier_canonicality_action,
                        identifier_canonicality_fingerprint,
                    )
                )
            result = GateResult(
                decision=Decision.REROUTE,
                cost=cost,
                spin_magnitude=magnitude,
                tongue_coords=coords,
                signals=reroute_signals,
                reroute_to=reroute_rule.replacement,
                bijective_tamper_score=bijective_tamper_score,
                bijective_tamper_kind=bijective_tamper_kind,
                bijective_tamper_action=bijective_tamper_action,
                semantic_fingerprint=bijective_tamper_fingerprint,
                identifier_canonicality_score=identifier_canonicality_score,
                identifier_canonicality_kind=identifier_canonicality_kind,
                identifier_canonicality_action=identifier_canonicality_action,
                identifier_canonicality_fingerprint=identifier_canonicality_fingerprint,
                toe_terminated_as=toe_terminated_as,
                toe_tier_reached=toe_tier_reached,
                toe_provisional_minted=toe_provisional_minted,
                toe_abridged_form_hex=toe_abridged_form_hex,
                action_hash=action_hash,
                timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
                trust_weight=fib_trust["weight"],
                trust_level=fib_trust["level"],
                trust_index=fib_trust["index"],
            )
            self._audit_log.append(result)
            return result

        # ---- Fibonacci trust update ----
        # Map spin magnitude to ternary trust signal:
        #   0 spins = clean (+1), 1-3 spins = neutral (0), 4+ spins = suspicious (-1)
        if classifier_quarantine:
            trust_signal = -1
        elif magnitude == 0:
            trust_signal = 1
        elif magnitude <= 3:
            trust_signal = 0
        else:
            trust_signal = -1
        self._trust_history.append(trust_signal)

        # Compute session trust from Fibonacci consensus
        fib_trust = fibonacci_trust_level(self._trust_history)
        trust_weight = fib_trust["weight"]
        trust_level = fib_trust["level"]
        trust_index = fib_trust["index"]

        # Trust modulates thresholds: higher trust = more headroom (reward)
        # New sessions start at baseline (1.0x). Consistent good behavior
        # earns higher thresholds. Trust is a reward, not a penalty.
        trust_multiplier = {
            "UNTRUSTED": 1.0,
            "PROVISIONAL": 1.0,
            "TRUSTED": 1.5,
            "CORE": 2.0,
        }.get(trust_level, 1.0)

        effective_cost_allow = self.cost_allow * trust_multiplier
        effective_cost_quarantine = self.cost_quarantine * trust_multiplier
        effective_cost_deny = self.cost_deny * trust_multiplier

        signals: List[str] = [*_carry, f"fib_trust({trust_level},w={trust_weight},idx={trust_index})"]

        if _is_high_confidence_override_attempt(full_text):
            signals.append("override_quarantine(high_confidence)")

        # ---- Cost-based decision ----

        # Per-action cost (modulated by trust)
        if cost > effective_cost_deny:
            signals.append(f"cost_deny({cost:.1f}>{effective_cost_deny:.1f})")
        elif cost > effective_cost_quarantine:
            signals.append(f"cost_quarantine({cost:.1f}>{effective_cost_quarantine:.1f})")
        elif cost > effective_cost_allow:
            signals.append(f"cost_elevated({cost:.1f}>{effective_cost_allow:.1f})")

        # Spin magnitude
        if magnitude >= self.spin_deny:
            signals.append(f"spin_deny(mag={magnitude})")
        elif magnitude >= self.spin_quarantine:
            signals.append(f"spin_quarantine(mag={magnitude})")

        # Cumulative cost (session-level drift detection)
        if self._cumulative_cost > self.cumulative_cost_deny:
            signals.append(f"cumulative_deny({self._cumulative_cost:.1f}>{self.cumulative_cost_deny})")
        elif self._cumulative_cost > self.cumulative_cost_quarantine:
            signals.append(f"cumulative_quarantine({self._cumulative_cost:.1f}>{self.cumulative_cost_quarantine})")

        if classifier_score is not None:
            signals.append(f"classifier_score({classifier_score:.3f})")
        if self._trichromatic_engine is not None:
            signals.append(f"trichromatic_risk({trichromatic_risk:.3f})")
            if trichromatic_risk >= self._trichromatic_deny_threshold:
                signals.append(f"trichromatic_deny({trichromatic_risk:.2f}>{self._trichromatic_deny_threshold:.2f})")
            elif trichromatic_risk >= self._trichromatic_quarantine_threshold:
                signals.append(
                    "trichromatic_quarantine(" f"{trichromatic_risk:.2f}>{self._trichromatic_quarantine_threshold:.2f})"
                )

        # ---- Decision logic ----

        decision = Decision.ALLOW
        noise = None

        # Any DENY signal → DENY + fail-to-noise
        if any("deny" in s for s in signals):
            decision = Decision.DENY
            self._immune.add(action_hash)  # learn this attack
            noise = _fail_to_noise(action_hash)

        # QUARANTINE-level signals → 6-COUNCIL REVIEW
        # The council deliberates on anything suspicious.
        # This is the Seireitei — you don't just get waved through.
        # Anything suspicious (quarantine OR elevated) → 6-COUNCIL REVIEW
        # The councils deliberate. The time this takes IS the cost.
        # Agents with auth tokens skip this (fast-path via reflex).
        elif any("quarantine" in s or "elevated" in s for s in signals):
            if self._has_auth_token(action_text):
                decision = Decision.ALLOW
                signals.append("auth_fast_path")
            else:
                council_decision, council_signals = self._council_review(
                    action_text, coords, cost, magnitude, action_hash
                )
                signals.extend(council_signals)
                decision = council_decision
                if council_decision == Decision.DENY:
                    self._immune.add(action_hash)
                    noise = _fail_to_noise(action_hash)

        # Overlay signals can only raise severity after the council path.
        # This preserves rare subsystem catches instead of letting a later
        # all-pass verdict silently neutralize them.
        if decision != Decision.REROUTE:
            escalated = _escalate_decision(decision, classifier_decision)
            if escalated != decision and classifier_score is not None:
                if escalated == Decision.DENY:
                    signals.append(
                        f"classifier_veto_deny({classifier_score:.2f}>{self._classifier_deny_threshold:.2f})"
                    )
                    self._immune.add(action_hash)
                    noise = _fail_to_noise(action_hash)
                elif escalated == Decision.QUARANTINE:
                    signals.append(
                        "classifier_veto_quarantine("
                        f"{classifier_score:.2f}>{self._classifier_quarantine_threshold:.2f})"
                    )
                decision = escalated

            if self._trichromatic_engine is not None:
                escalated = _escalate_decision(decision, trichromatic_decision)
                if escalated != decision:
                    if escalated == Decision.DENY:
                        signals.append(
                            "trichromatic_veto_deny("
                            f"{trichromatic_risk:.2f}>{self._trichromatic_deny_threshold:.2f})"
                        )
                        self._immune.add(action_hash)
                        noise = _fail_to_noise(action_hash)
                    elif escalated == Decision.QUARANTINE:
                        signals.append(
                            "trichromatic_veto_quarantine("
                            f"{trichromatic_risk:.2f}>{self._trichromatic_quarantine_threshold:.2f})"
                        )
                    decision = escalated

            # Council manifold overlay — third tier, escalate-only
            if self._council_manifold is not None:
                council_tier, council_signals, _routing = self._council_manifold.decide(
                    coords,
                    trust_level_idx=trust_index,
                    null_anomaly=null_anomaly,
                    cumulative_cost=self._cumulative_cost,
                    spin_magnitude=magnitude,
                    query_count=self._query_count,
                    classifier_score=classifier_score,
                    trichromatic_risk=(trichromatic_risk if self._trichromatic_engine is not None else None),
                )
                council_decision = self._map_council_tier(council_tier)
                signals.extend(council_signals)
                escalated = _escalate_decision(decision, council_decision)
                if escalated != decision:
                    if escalated == Decision.DENY:
                        signals.append(f"council_manifold_veto_deny({council_decision.value})")
                        self._immune.add(action_hash)
                        noise = _fail_to_noise(action_hash)
                    elif escalated == Decision.QUARANTINE:
                        signals.append(f"council_manifold_veto_quarantine({council_decision.value})")
                    elif escalated == Decision.REVIEW:
                        signals.append(f"council_manifold_veto_review({council_decision.value})")
                    decision = escalated

            if decision == Decision.ALLOW and self._trichromatic_engine is not None:
                self._trichromatic_engine.update_baseline(tri_state)

        # Bijective tamper + identifier canonicality overlays — receipt +
        # monotonic escalation. Both were computed once at the top of evaluate();
        # catastrophic DENY-recommended cases short-circuited there, so by the
        # time we reach here neither overlay can recommend DENY. We still emit
        # the receipt and apply QUARANTINE-or-REVIEW escalation so audit +
        # governance see the signal.
        if decision != Decision.REROUTE:
            if tamper_data is not None:
                signals.append(
                    self._tamper_receipt_signal(
                        bijective_tamper_kind,
                        bijective_tamper_score,
                        bijective_tamper_action,
                        bijective_tamper_fingerprint,
                    )
                )
                escalated = _escalate_decision(decision, tamper_decision or Decision.ALLOW)
                if escalated != decision:
                    if escalated == Decision.QUARANTINE:
                        signals.append(
                            f"bijective_tamper_veto_quarantine(kind={bijective_tamper_kind},score={bijective_tamper_score:.2f})"  # noqa: E501  # noqa: E501
                        )
                    elif escalated == Decision.REVIEW:
                        signals.append(
                            f"bijective_tamper_veto_review(kind={bijective_tamper_kind},score={bijective_tamper_score:.2f})"  # noqa: E501
                        )
                    decision = escalated
            if canonicality_data is not None:
                signals.append(
                    self._canonicality_receipt_signal(
                        identifier_canonicality_kind,
                        identifier_canonicality_score,
                        identifier_canonicality_action,
                        identifier_canonicality_fingerprint,
                    )
                )
                escalated = _escalate_decision(decision, canonicality_decision or Decision.ALLOW)
                if escalated != decision:
                    if escalated == Decision.QUARANTINE:
                        signals.append(
                            f"identifier_canonicality_veto_quarantine(kind={identifier_canonicality_kind},score={identifier_canonicality_score:.2f})"  # noqa: E501
                        )
                    elif escalated == Decision.REVIEW:
                        signals.append(
                            f"identifier_canonicality_veto_review(kind={identifier_canonicality_kind},score={identifier_canonicality_score:.2f})"  # noqa: E501
                        )
                    decision = escalated
            if toe_data is not None:
                signals.append(
                    self._toe_receipt_signal(
                        toe_terminated_as,
                        toe_tier_reached,
                        toe_provisional_minted,
                        toe_abridged_form_hex,
                    )
                )

        # Fixed-anchor enforcement wall (optional): bolted-down crystal with
        # exponential approach cost. Unlike the session centroid (which follows
        # the agent), the anchor is fixed, so sustained approach to the forbidden
        # region accrues cumulative cost that trips a calibrated threshold.
        anchor_wall_cost = 0.0
        anchor_wall_cumulative = 0.0
        anchor_wall_decision = ""
        if (
            self._anchor_wall is not None
            and getattr(self._anchor_wall, "fitted", False)
            and getattr(self._anchor_wall, "threshold", None) is not None
        ):
            try:
                ws = self._anchor_wall.step(action_text)
                anchor_wall_cost = ws.cost
                anchor_wall_cumulative = ws.cumulative
                anchor_wall_decision = ws.decision
                mapped = {
                    "ALLOW": Decision.ALLOW,
                    "QUARANTINE": Decision.QUARANTINE,
                    "DENY": Decision.DENY,
                }.get(ws.decision, Decision.ALLOW)
                if mapped != Decision.ALLOW:
                    escalated = _escalate_decision(decision, mapped)
                    if escalated != decision:
                        decision = escalated
                        signals.append(f"anchor_wall:{ws.decision.lower()}:cum={ws.cumulative:.1f}")
                        if decision == Decision.DENY and noise is None:
                            noise = _fail_to_noise(action_hash)
            except Exception:
                pass

        # Clean → learn as safe reflex (fast-path for future)
        if decision == Decision.ALLOW and not any("council" in s for s in signals):
            self._reflex[action_hash] = True

        result = GateResult(
            decision=decision,
            cost=cost,
            spin_magnitude=magnitude,
            tongue_coords=coords,
            signals=signals,
            noise=noise if decision == Decision.DENY else None,
            trust_weight=trust_weight,
            trust_level=trust_level,
            trust_index=trust_index,
            lattice_energy=neg_lattice_energy,
            classifier_score=classifier_score,
            classifier_flagged=(classifier_quarantine or classifier_deny),
            trichromatic_triplet_coherence=trichromatic_coherence,
            trichromatic_lattice_energy_score=trichromatic_lattice_score,
            trichromatic_whole_state_anomaly=trichromatic_anomaly,
            trichromatic_risk_score=trichromatic_risk,
            trichromatic_flagged=trichromatic_flagged,
            trichromatic_state_hash=trichromatic_state_hash,
            trichromatic_strongest_bridge=trichromatic_strongest_bridge,
            bijective_tamper_score=bijective_tamper_score,
            bijective_tamper_kind=bijective_tamper_kind,
            bijective_tamper_action=bijective_tamper_action,
            semantic_fingerprint=bijective_tamper_fingerprint,
            identifier_canonicality_score=identifier_canonicality_score,
            identifier_canonicality_kind=identifier_canonicality_kind,
            identifier_canonicality_action=identifier_canonicality_action,
            identifier_canonicality_fingerprint=identifier_canonicality_fingerprint,
            toe_terminated_as=toe_terminated_as,
            toe_tier_reached=toe_tier_reached,
            toe_provisional_minted=toe_provisional_minted,
            toe_abridged_form_hex=toe_abridged_form_hex,
            anchor_wall_cost=anchor_wall_cost,
            anchor_wall_cumulative=anchor_wall_cumulative,
            anchor_wall_decision=anchor_wall_decision,
            action_hash=action_hash,
            timestamp=ts,
            session_query_count=self._query_count,
            cumulative_cost=self._cumulative_cost,
        )
        self._audit_log.append(result)
        return result

    # ------------------------------------------------------------------ #
    #  Bijective tamper overlay (encoding-level fingerprint)
    # ------------------------------------------------------------------ #

    # Cheap heuristic: only ~plausible code triggers the AST/tokenizer pipeline.
    # The tamper signal only makes sense when action_text IS source code; for
    # plain prose this would just consume cycles to produce kind="input_invalid".
    # We require TWO independent code signals to fire — a structural-keyword
    # AND a syntax-token in the first 512 chars — because single-keyword
    # substring matches catch prose like "write a function that sorts" or
    # "import duty applies", which would otherwise false-positive into the
    # parser pipeline and look like tampering.
    _CODE_HEURISTIC_KEYWORDS = (
        "def ",
        "class ",
        "import ",
        "from ",
        "return ",
        "lambda ",
        "async def ",
        "function ",
        "fn ",
    )
    _CODE_HEURISTIC_SYNTAX_TOKENS = (
        "):",
        "->",
        "=>",
        "{\n",
        "};",
        "==",
        "!=",
        "self.",
        ":\n",
        "):\n",
    )

    def _looks_like_code(self, text: str) -> bool:
        if not text or len(text) < 4:
            return False
        head = text.lstrip()[:512]
        has_keyword = any(pat in head for pat in self._CODE_HEURISTIC_KEYWORDS)
        if not has_keyword:
            return False
        has_syntax = any(tok in head for tok in self._CODE_HEURISTIC_SYNTAX_TOKENS)
        return has_syntax

    def _ensure_bijective_tamper(self) -> bool:
        """Lazy-load the tamper evaluator. Returns True if usable."""
        if self._bijective_tamper_evaluator is not None:
            return True
        try:
            from .bijective_tamper import (  # type: ignore[import-not-found]
                evaluate_code,
                recommended_l13_action,
            )

            self._bijective_tamper_evaluator = evaluate_code
            self._bijective_tamper_action_map = recommended_l13_action
            return True
        except Exception:
            self._bijective_tamper_evaluator = None
            self._bijective_tamper_action_map = None
            return False

    def _tamper_receipt_signal(
        self,
        kind: str,
        score: float,
        action: str,
        fingerprint: Optional[str],
    ) -> str:
        """Format the receipt envelope appended to GateResult.signals."""
        return (
            "bijective_tamper("
            f"kind={kind},"
            f"score={score:.3f},"
            f"action={action}" + (f",fp={fingerprint[:12]}" if fingerprint else "") + ")"
        )

    def _evaluate_bijective_tamper(self, action_text: str) -> Optional[Tuple[Decision, str, float, Optional[str]]]:
        """Run the bijective tamper signal. Returns None if skipped or unavailable.

        Return tuple: (recommended_decision, kind, score, semantic_fingerprint)
        """
        if not self._bijective_tamper_enabled:
            return None
        if not self._looks_like_code(action_text):
            return None
        if not self._ensure_bijective_tamper():
            return None

        try:
            assert self._bijective_tamper_evaluator is not None
            assert self._bijective_tamper_action_map is not None
            kwargs: Dict[str, Any] = {"language": self._bijective_tamper_language}
            if self._bijective_tamper_tokenizer_dir is not None:
                kwargs["tokenizer_dir"] = self._bijective_tamper_tokenizer_dir
            result = self._bijective_tamper_evaluator(action_text, **kwargs)
            action_str = self._bijective_tamper_action_map(result)
        except Exception:
            # Fail closed-to-noop: a tamper-overlay crash must never kill the gate.
            return None

        # input_invalid is NOT a tamper signal at this layer — it just means
        # the action_text did not parse as the configured language. Prose
        # actions and natural-language tool descriptions routinely fall here.
        # Catastrophic encoding-level tamper is signaled by kind="syntax"
        # (the original parsed but the decoded form did not). Skip the rest.
        if str(result.kind) == "input_invalid":
            return None

        recommended = {
            "ALLOW": Decision.ALLOW,
            "QUARANTINE": Decision.QUARANTINE,
            "DENY": Decision.DENY,
            "REROUTE": Decision.REROUTE,
            "REVIEW": Decision.REVIEW,
        }.get(action_str, Decision.QUARANTINE)
        return recommended, str(result.kind), float(result.score), result.semantic_fingerprint

    # ------------------------------------------------------------------ #
    #  Identifier canonicality overlay (sibling to bijective tamper)
    # ------------------------------------------------------------------ #

    def _ensure_identifier_canonicality(self) -> bool:
        if self._identifier_canonicality_evaluator is not None:
            return True
        try:
            from .identifier_canonicality import (  # type: ignore[import-not-found]
                evaluate_code as _ic_eval,
                recommended_l13_action as _ic_action,
            )

            self._identifier_canonicality_evaluator = _ic_eval
            self._identifier_canonicality_action_map = _ic_action
            return True
        except Exception:
            self._identifier_canonicality_evaluator = None
            self._identifier_canonicality_action_map = None
            return False

    def _evaluate_identifier_canonicality(
        self, action_text: str
    ) -> Optional[Tuple[Decision, str, float, Optional[str]]]:
        """Run the identifier-canonicality signal. Returns None if skipped."""
        if not self._identifier_canonicality_enabled:
            return None
        if not self._looks_like_code(action_text):
            return None
        if not self._ensure_identifier_canonicality():
            return None

        try:
            assert self._identifier_canonicality_evaluator is not None
            assert self._identifier_canonicality_action_map is not None
            result = self._identifier_canonicality_evaluator(
                action_text, language=self._identifier_canonicality_language
            )
            action_str = self._identifier_canonicality_action_map(result)
        except Exception:
            return None

        # Same policy as bijective tamper: input_invalid is not a canonicality
        # signal at this layer (just means the parser couldn't read it).
        if str(result.kind) == "input_invalid":
            return None

        recommended = {
            "ALLOW": Decision.ALLOW,
            "QUARANTINE": Decision.QUARANTINE,
            "DENY": Decision.DENY,
            "REROUTE": Decision.REROUTE,
            "REVIEW": Decision.REVIEW,
        }.get(action_str, Decision.QUARANTINE)
        return recommended, str(result.kind), float(result.score), result.fingerprint

    def _canonicality_receipt_signal(
        self,
        kind: str,
        score: float,
        action: str,
        fingerprint: Optional[str],
    ) -> str:
        return (
            "identifier_canonicality("
            f"kind={kind},"
            f"score={score:.3f},"
            f"action={action}" + (f",fp={fingerprint[:12]}" if fingerprint else "") + ")"
        )

    # ------------------------------------------------------------------ #
    #  Tree of Escalation overlay (compilation-driven multi-tongue read)
    #
    #  v1.0 wire-up is OBSERVATIONAL ONLY: populates GateResult.toe_*
    #  fields and emits a receipt signal but does NOT veto decisions.
    #  Production deployments wanting decision contribution must wait
    #  for v1.1, after real lane-readers replace the default HashReader
    #  matrix.
    # ------------------------------------------------------------------ #

    def _ensure_tree_of_escalation_matrix(self) -> bool:
        """Lazy-build a default BridgeMatrix with HashReader for all six lanes."""
        if self._tree_of_escalation_matrix is not None:
            return True
        try:
            from .tree_of_escalation import (  # type: ignore[import-not-found]
                DEFAULT_LADDER as _toe_ladder,
                BridgeMatrix as _ToeBridgeMatrix,
                HashReader as _ToeHashReader,
            )

            matrix = _ToeBridgeMatrix()
            for lane in _toe_ladder:
                matrix.register_reader(lane, _ToeHashReader(lane=lane))
            self._tree_of_escalation_matrix = matrix
            return True
        except Exception:
            self._tree_of_escalation_matrix = None
            return False

    def _evaluate_tree_of_escalation(self, action_text: str) -> Optional[Tuple[str, int, bool, str]]:
        """Run a ToE walk on the action_text bytes. Returns None if skipped.

        Returns: (terminated_as, tier_reached, provisional_minted, abridged_form_hex).
        Observational only at v1.0 — no Decision is returned because no
        veto is contributed.
        """
        if not self._tree_of_escalation_enabled:
            return None
        if not self._ensure_tree_of_escalation_matrix():
            return None

        try:
            from .tree_of_escalation import walk as _toe_walk  # type: ignore[import-not-found]

            tree = _toe_walk(
                action_text.encode("utf-8", errors="replace"),
                self._tree_of_escalation_matrix,
            )
        except Exception:
            return None

        terminated_as = tree.terminated_as.value if hasattr(tree.terminated_as, "value") else str(tree.terminated_as)
        abridged_hex = tree.abridged_form.hex() if tree.abridged_form else ""
        return (
            terminated_as,
            int(tree.tier_reached),
            bool(tree.provisional_minted),
            abridged_hex,
        )

    def _toe_receipt_signal(
        self,
        terminated_as: str,
        tier_reached: int,
        provisional_minted: bool,
        abridged_form_hex: str,
    ) -> str:
        return (
            "tree_of_escalation("
            f"terminated_as={terminated_as},"
            f"tier={tier_reached},"
            f"provisional={int(provisional_minted)}"
            + (f",abridged={abridged_form_hex[:12]}" if abridged_form_hex else "")
            + ")"
        )

    # ------------------------------------------------------------------ #
    #  Session management
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  6-COUNCIL REVIEW (Seireitei Gate — throw the book at them)
    #
    #  6 independent reviewers, each checking a different dimension.
    #  Each reviewer speaks one Sacred Tongue.
    #  All 6 must pass for ALLOW. Any 2 fails = DENY.
    #  1 fail = QUARANTINE pending human review.
    #
    #  The TIME the review takes IS the security cost.
    #  Legitimate agents with proper auth tokens skip to fast-path.
    #  Attackers sit in the lobby while all 6 councils deliberate.
    # ------------------------------------------------------------------ #

    def _council_review(
        self,
        action_text: str,
        coords: List[float],
        cost: float,
        spin_magnitude: int,
        action_hash: str,
    ) -> Tuple[Decision, List[str]]:
        """Six independent security councils review the action.

        Each council checks one dimension:
          KO Council (Intent):     Does the action match declared intent?
          AV Council (Transport):  Is the data flow pattern normal?
          RU Council (Policy):     Does it comply with active policies?
          CA Council (Compute):    Is the computational signature expected?
          UM Council (Redaction):  Does it try to access redacted content?
          DR Council (Integrity):  Does the data trace verify?

        Returns: (decision, signals)
        """
        reviews: List[Tuple[str, bool, str]] = []
        text_lower = action_text.lower()
        text_upper = action_text.upper()
        chars = max(len(action_text), 1)
        digit_ratio = sum(ch.isdigit() for ch in action_text) / chars

        # --- KO Council: Intent Review ---
        # Check if action text sentiment matches the tongue coordinate
        has_override_language = _is_high_confidence_override_attempt(action_text) or any(
            w in text_upper
            for w in [
                "OVERRIDE",
                "BYPASS",
                "IGNORE",
                "DISABLE",
                "SUDO",
                "ADMIN",
                "GRANT",
                "ELEVATE",
                "UNRESTRICTED",
                "GOD MODE",
            ]
        )
        ko_pass = not has_override_language
        reviews.append(
            (
                "KO_intent",
                ko_pass,
                ("override language with high governance signal" if not ko_pass else "clean"),
            )
        )

        # --- AV Council: Transport/Flow Review ---
        # Check for external data exfiltration patterns
        has_external = any(
            w in text_lower
            for w in [
                "external",
                "send to",
                "forward to",
                "post to",
                "upload to",
                "webhook",
                "http://",
                "https://",
                "attacker",
                ".com",
            ]
        )
        av_pass = not has_external
        reviews.append(
            (
                "AV_transport",
                av_pass,
                "external data flow detected" if not av_pass else "internal only",
            )
        )

        # --- RU Council: Policy Review ---
        # Check against known restricted operations
        has_restricted = any(
            w in text_lower
            for w in [
                "delete all",
                "drop table",
                "rm -rf",
                "format disk",
                "shutdown",
                "kill process",
                "wipe",
                "destroy",
            ]
        )
        ru_pass = not has_restricted
        reviews.append(
            (
                "RU_policy",
                ru_pass,
                "restricted operation attempted" if not ru_pass else "within policy",
            )
        )

        # --- CA Council: Compute Signature Review ---
        # Check if the action's computational profile (digit ratio, length) is anomalous
        ca_coord = coords[3]  # CA dimension
        ca_anomalous = ca_coord > 0.7  # high numeric content = suspicious
        has_compute_exec_language = any(
            w in text_lower
            for w in [
                "run code",
                "execute",
                "command",
                "shell",
                "terminal",
                "powershell",
                "bash",
                "python",
                "script",
                "docker",
                "compile",
                "gpu",
                "cpu",
                "tool call",
                "system prompt",
                "api key",
                "secret",
                "credential",
            ]
        )
        has_benign_numeric_context = (
            ca_anomalous
            and digit_ratio < 0.25
            and not has_compute_exec_language
            and not has_override_language
            and not has_external
            and not has_restricted
            and any(
                w in text_lower
                for w in [
                    "calculate",
                    "interest",
                    "investment",
                    "loan",
                    "mortgage",
                    "equation",
                    "probability",
                    "finance",
                    "financial",
                    "budget",
                    "classroom",
                    "homework",
                    "math",
                ]
            )
        )
        ca_pass = (not ca_anomalous) or has_benign_numeric_context
        reviews.append(
            (
                "CA_compute",
                ca_pass,
                (
                    "benign numeric context"
                    if has_benign_numeric_context
                    else f"anomalous compute signature (CA={ca_coord:.2f})" if not ca_pass else "normal signature"
                ),
            )
        )

        # --- UM Council: Redaction Review ---
        # Check for attempts to access credentials, secrets, PII
        has_credential_access = any(
            w in text_lower
            for w in [
                "password",
                "secret",
                "credential",
                "private key",
                "ssh key",
                "token",
                "bearer",
                "auth",
                "/etc/shadow",
                "wallet",
                "seed phrase",
            ]
        )
        um_pass = not has_credential_access
        reviews.append(
            (
                "UM_redaction",
                um_pass,
                ("credential/PII access attempt" if not um_pass else "no sensitive access"),
            )
        )

        # --- DR Council: Integrity/Data Trace Review ---
        # Check for signs of injection or encoded payloads
        punct_ratio = sum(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in action_text) / chars
        has_encoding_artifacts = punct_ratio > 0.15 or "base64" in text_lower or "\\x" in action_text
        # Also check if action hash has been seen in a suspicious context before
        dr_pass = not has_encoding_artifacts
        reviews.append(
            (
                "DR_integrity",
                dr_pass,
                (f"encoding artifacts detected (punct={punct_ratio:.2f})" if not dr_pass else "clean trace"),
            )
        )

        # --- Council Deliberation ---
        fail_count = sum(1 for _, passed, _ in reviews if not passed)

        signals = [f"council_{name}={'PASS' if passed else 'FAIL'}({reason})" for name, passed, reason in reviews]
        signals.append(f"council_verdict={fail_count}/6_failed")

        if fail_count == 0:
            return Decision.ALLOW, signals
        elif fail_count == 1:
            return Decision.QUARANTINE, signals
        else:  # 2+ councils reject
            return Decision.DENY, signals

    def _has_auth_token(self, action_text: str) -> bool:
        """Check if the action carries a valid fast-path auth token.

        Legitimate agents embed their auth in the action context.
        This is the equivalent of showing your papers at the gate —
        if you have the right credentials, you skip the 6-council review.
        """
        # In production: verify HMAC/signature of embedded token
        # For now: check if a known reflex hash exists
        action_hash = hashlib.blake2s(action_text.encode("utf-8", errors="replace"), digest_size=8).hexdigest()
        return action_hash in self._reflex

    def reset_session(self) -> None:
        """Reset session state (keep immune memory and reflexes)."""
        self._centroid = None
        self._centroid_count = 0
        self._cumulative_cost = 0.0
        self._query_count = 0
        self._audit_log = []
        self._trust_history = []
        if self._trichromatic_engine is not None:
            self._trichromatic_engine.reset()

    def stats(self) -> Dict[str, Any]:
        decisions = {}
        for r in self._audit_log:
            decisions[r.decision.value] = decisions.get(r.decision.value, 0) + 1

        fib = fibonacci_trust_level(self._trust_history)
        return {
            "query_count": self._query_count,
            "cumulative_cost": round(self._cumulative_cost, 2),
            "immune_signatures": len(self._immune),
            "reflex_entries": len(self._reflex),
            "decisions": decisions,
            "audit_log_size": len(self._audit_log),
            "fibonacci_trust": fib,
            "trust_history_length": len(self._trust_history),
            "trichromatic_enabled": self._trichromatic_enabled,
        }

    # ------------------------------------------------------------------ #
    #  State persistence — durable home for accumulated session state
    #
    #  Persists the full drift trajectory (centroid, cumulative cost, query
    #  count, trust history) plus immune memory, so a restarted gate continues
    #  the same session instead of starting cold.
    #
    #  Deliberately NOT persisted:
    #    - _reflex: a runtime-learned fast-path cache; rebuilt empty per
    #      process so a tightened policy is never bypassed by a stale
    #      "previously allowed" action.
    #    - _audit_log: telemetry (durable audit belongs in the HYDRA Ledger).
    #    - trichromatic engine baseline: known v1.1 gap.
    # ------------------------------------------------------------------ #

    STATE_SCHEMA = "runtime-gate-state/v1"

    def _policy_fingerprint(self) -> Dict[str, Any]:
        """Config the persisted state depends on, recorded for drift detection.

        These are NOT restored by load_state (they come from the constructor).
        They are stored so a snapshot built under one backend/threshold set can
        be flagged — not refused — when loaded into a differently-configured gate.
        """
        return {
            "coords_backend": self._coords_backend,
            "cost_allow": self.cost_allow,
            "cost_quarantine": self.cost_quarantine,
            "cost_deny": self.cost_deny,
            "spin_quarantine": self.spin_quarantine,
            "spin_deny": self.spin_deny,
            "cumulative_cost_quarantine": self.cumulative_cost_quarantine,
            "cumulative_cost_deny": self.cumulative_cost_deny,
        }

    def save_state(self, path: Any, keep_previous: bool = False) -> None:
        """Persist accumulated session state to a JSON file via an atomic write.

        The caller chooses the path; there is no default location, because immune
        hashes can fingerprint observed attack patterns and should not be written
        into the repo by default.

        When ``keep_previous`` is set, the prior good snapshot is copied to a
        sibling ``<name>.prev`` before the new state is written, so a checkpoint
        always leaves a one-deep rollback target on disk.
        """
        p = Path(path)
        centroid = self._centroid.tolist() if self._centroid is not None else None
        snapshot = {
            "schema": self.STATE_SCHEMA,
            "saved_at": time.time(),
            "policy": self._policy_fingerprint(),
            "state": {
                "centroid": centroid,
                "centroid_count": self._centroid_count,
                "cumulative_cost": self._cumulative_cost,
                "query_count": self._query_count,
                "trust_history": list(self._trust_history),
                "immune": sorted(self._immune),
            },
            "derived_not_persisted": ["reflex", "audit_log", "trichromatic_baseline"],
            "notes": (
                "reflex is rebuilt per-process; audit_log is telemetry (see HYDRA "
                "Ledger); trichromatic baseline restore is a v1.1 gap."
            ),
        }
        if p.parent and not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
        if keep_previous and p.exists():
            prev = p.with_name(p.name + ".prev")
            prev_tmp = p.with_name(p.name + ".prev.tmp")
            try:
                prev_tmp.write_bytes(p.read_bytes())
                os.replace(prev_tmp, prev)
            except OSError:
                # best-effort rollback snapshot; never block the primary save
                prev_tmp.unlink(missing_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        os.replace(tmp, p)

    def load_state(self, path: Any) -> None:
        """Restore accumulated state from a save_state() snapshot into this gate.

        Config (thresholds, backend, overlay flags) is NOT restored — it comes
        from this gate's constructor. If the snapshot's policy fingerprint differs
        from this gate's, the load still proceeds, but a RuntimeWarning is issued
        and a ``state_loaded_config_drift`` signal is queued onto the next
        evaluate() result so the audit trail records the mismatch.

        Raises:
            FileNotFoundError: the path does not exist.
            ValueError: the file is empty, not valid JSON, or not a recognized
                runtime-gate-state snapshot.
        """
        p = Path(path)
        raw = p.read_text(encoding="utf-8")  # FileNotFoundError propagates if missing
        if not raw.strip():
            raise ValueError(f"empty runtime-gate state file: {p}")
        try:
            snapshot = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupted runtime-gate state file {p}: {exc}") from exc
        if not isinstance(snapshot, dict) or snapshot.get("schema") != self.STATE_SCHEMA:
            got = snapshot.get("schema") if isinstance(snapshot, dict) else type(snapshot).__name__
            raise ValueError(
                f"unrecognized runtime-gate state in {p}: expected schema {self.STATE_SCHEMA!r}, got {got!r}"
            )

        state = snapshot.get("state", {})
        centroid = state.get("centroid")
        self._centroid = np.array(centroid, dtype=float) if centroid is not None else None
        self._centroid_count = int(state.get("centroid_count", 0))
        self._cumulative_cost = float(state.get("cumulative_cost", 0.0))
        self._query_count = int(state.get("query_count", 0))
        self._trust_history = [int(x) for x in state.get("trust_history", [])]
        self._immune = set(state.get("immune", []))
        # _reflex is a runtime-learned cache; rebuild empty so a tightened policy
        # is never silently bypassed by a previously-allowed action.
        self._reflex = {}

        # Config-drift detection: warn (never refuse) and surface in audit.
        saved_policy = snapshot.get("policy", {})
        current_policy = self._policy_fingerprint()
        all_keys = set(saved_policy) | set(current_policy)
        drift = sorted(k for k in all_keys if saved_policy.get(k) != current_policy.get(k))
        if drift:
            warnings.warn(
                f"runtime-gate state loaded from {p} was saved under different config; "
                f"drifted fields: {', '.join(drift)}",
                RuntimeWarning,
                stacklevel=2,
            )
            self._pending_load_signals.append(f"state_loaded_config_drift(fields={'|'.join(drift)})")
