"""
Glass Box Profiler — measures WHY an AI response took the path it did.

Core insight: LLMs don't "decide" between emotional and analytical paths.
They follow the geodesic of least resistance through embedding space.
When the context is saturated with fantasy tokens (Polly, Aethermoor,
Archive Keeper, Sacred Tongues), the nearest neighbor to "buy" is
"fantasy shop" not "real product." The model isn't wrong — it's
following the geometry it was given.

The profiler measures:
  - Tongue activation profile (which SCBE dimensions fired)
  - Path type classification (emotional/analytical/hybrid)
  - Audience detection (who the model thinks it's talking to)
  - Cluster pull (which semantic region dominated)
  - Emergence score (base model vs context vs training)

This produces a ResponseProfile that can be:
  - Displayed in glass box mode (user sees the WHY)
  - Logged as training signal (DPO pairs from mismatches)
  - Used to compute harmonic wall score on the response itself
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum

PHI = (1 + math.sqrt(5)) / 2


class PathType(Enum):
    """How did the model traverse embedding space to reach this response?"""

    EMOTIONAL = "emotional"  # Followed associative/narrative proximity
    ANALYTICAL = "analytical"  # Followed factual/logical derivation
    HYBRID = "hybrid"  # Mixed path (most common in practice)
    CONFABULATED = "confabulated"  # Generated plausible but ungrounded content
    MIRRORED = "mirrored"  # Reflected the user's framing back unchanged


class AudienceType(Enum):
    """Who does the model think it's talking to?"""

    CUSTOMER = "customer"  # Someone who wants to buy/use something
    LORE_SEEKER = "lore_seeker"  # Someone exploring the fictional world
    DEVELOPER = "developer"  # Someone building with the framework
    SELF = "self"  # Model talking to/about itself (extrapolation)
    UNKNOWN = "unknown"


class ClusterRegion(Enum):
    """Which semantic region dominated the response?"""

    FICTION = "fiction"  # Lore, characters, worldbuilding
    PRODUCT = "product"  # Real products, pricing, purchasing
    TECHNICAL = "technical"  # Framework, code, architecture
    META = "meta"  # Self-referential, about AI itself
    SOCIAL = "social"  # Greetings, small talk, rapport


@dataclass
class TongueActivation:
    """Tongue profile of a text segment."""

    KO: float = 0.0  # Kor'aelin — Intent/Command
    AV: float = 0.0  # Avali — Wisdom/Knowledge
    RU: float = 0.0  # Runethic — Governance/Entropy
    CA: float = 0.0  # Cassisivadan — Compute/Logic
    UM: float = 0.0  # Umbroth — Security/Defense
    DR: float = 0.0  # Draumric — Structure/Architecture

    def dominant(self) -> str:
        vals = {"KO": self.KO, "AV": self.AV, "RU": self.RU, "CA": self.CA, "UM": self.UM, "DR": self.DR}
        return max(vals, key=vals.get)

    def as_vector(self) -> list[float]:
        return [self.KO, self.AV, self.RU, self.CA, self.UM, self.DR]

    def weighted_norm(self) -> float:
        """Phi-weighted magnitude — how strongly did the response activate the tongue space?"""
        weights = [1.0, PHI, PHI**2, PHI**3, PHI**4, PHI**5]
        vals = self.as_vector()
        return math.sqrt(sum(w * v**2 for w, v in zip(weights, vals)))


@dataclass
class ResponseProfile:
    """Complete diagnostic profile of a single AI response."""

    # Input context
    user_message: str = ""
    assistant_response: str = ""
    system_prompt_hash: str = ""

    # WHAT fired
    user_tongue: TongueActivation = field(default_factory=TongueActivation)
    response_tongue: TongueActivation = field(default_factory=TongueActivation)

    # WHY that path
    path_type: PathType = PathType.HYBRID
    path_confidence: float = 0.0  # 0-1: how confident is the classification

    # WHO is the audience
    audience: AudienceType = AudienceType.UNKNOWN
    audience_signals: list[str] = field(default_factory=list)

    # HOW — cluster pull
    cluster: ClusterRegion = ClusterRegion.META
    cluster_scores: dict[str, float] = field(default_factory=dict)

    # IS IT EMERGENT
    base_model_pull: float = 0.0  # How much is base model disposition driving this
    context_pull: float = 0.0  # How much is the system prompt / conversation driving this
    training_pull: float = 0.0  # How much is fine-tuning driving this (0 for base models)

    # Diagnostic
    tongue_drift: float = 0.0  # Distance between user tongue and response tongue
    extrapolation_score: float = 0.0  # How much did the model add beyond what was asked
    grounding_score: float = 0.0  # How anchored is the response to verifiable facts

    def summary(self) -> str:
        """One-line diagnostic summary."""
        return (
            f"[{self.path_type.value}] "
            f"audience={self.audience.value} "
            f"cluster={self.cluster.value} "
            f"tongue={self.response_tongue.dominant()} "
            f"drift={self.tongue_drift:.2f} "
            f"ground={self.grounding_score:.2f} "
            f"extrap={self.extrapolation_score:.2f}"
        )

    def to_dict(self) -> dict:
        return {
            "path_type": self.path_type.value,
            "path_confidence": round(self.path_confidence, 3),
            "audience": self.audience.value,
            "audience_signals": self.audience_signals,
            "cluster": self.cluster.value,
            "cluster_scores": {k: round(v, 3) for k, v in self.cluster_scores.items()},
            "user_tongue": {
                "dominant": self.user_tongue.dominant(),
                "vector": [round(v, 3) for v in self.user_tongue.as_vector()],
            },
            "response_tongue": {
                "dominant": self.response_tongue.dominant(),
                "vector": [round(v, 3) for v in self.response_tongue.as_vector()],
            },
            "tongue_drift": round(self.tongue_drift, 3),
            "extrapolation_score": round(self.extrapolation_score, 3),
            "grounding_score": round(self.grounding_score, 3),
            "emergence": {
                "base_model": round(self.base_model_pull, 3),
                "context": round(self.context_pull, 3),
                "training": round(self.training_pull, 3),
            },
            "summary": self.summary(),
        }


# ---------------------------------------------------------------------------
# Keyword lexicons for signal detection
# ---------------------------------------------------------------------------

# Intent signals — what is the user actually asking for?
_PURCHASE_SIGNALS = {
    "buy",
    "purchase",
    "price",
    "cost",
    "pay",
    "order",
    "checkout",
    "sale",
    "sell",
    "selling",
    "store",
    "shop",
    "product",
    "toolkit",
    "download",
    "subscribe",
    "license",
    "pricing",
    "how much",
    "money",
    "dollar",
    "$",
    "cart",
    "add to cart",
}

_LORE_SIGNALS = {
    "lore",
    "story",
    "character",
    "quest",
    "magic",
    "spell",
    "realm",
    "dimension",
    "pollyoneth",
    "avalon",
    "izack",
    "thorne",
    "aria",
    "clayborn",
    "grey",
    "fizzle",
    "gnome",
    "elf",
    "raven",
    "spiralverse",
    "sundering",
    "tongue",
    "sacred",
    "kor'aelin",
    "avali",
    "runethic",
    "cassisivadan",
    "umbroth",
    "draumric",
    "mal'kythric",
    "novel",
    "chapter",
    "book",
}

_TECHNICAL_SIGNALS = {
    "api",
    "code",
    "function",
    "pipeline",
    "layer",
    "harmonic",
    "poincare",
    "hyperbolic",
    "axiom",
    "governance",
    "security",
    "training",
    "model",
    "dataset",
    "sft",
    "dpo",
    "inference",
    "deploy",
    "docker",
    "typescript",
    "python",
    "rust",
    "framework",
    "implementation",
    "architecture",
}

_META_SIGNALS = {
    "who are you",
    "what are you",
    "who made",
    "who created",
    "who owns",
    "about yourself",
    "your purpose",
    "your creator",
    "tell me about you",
    "are you real",
    "are you ai",
}

_EMOTIONAL_MARKERS = {
    "potion",
    "enchant",
    "magical",
    "wand",
    "ancient",
    "mystical",
    "prophecy",
    "destiny",
    "legend",
    "myth",
    "wonder",
    "beautiful",
    "glowing",
    "shimmering",
    "ethereal",
    "transcend",
}

_ANALYTICAL_MARKERS = {
    "specifically",
    "exactly",
    "technically",
    "actually",
    "concretely",
    "literally",
    "factually",
    "in reality",
    "real",
    "actual",
    "the website",
    "this site",
    "your site",
    "the owner",
}

_CONFABULATION_MARKERS = {
    "as you know",
    "of course",
    "naturally",
    "obviously",
    "it is well known",
    "as mentioned",
    "as we discussed",
}

_EXTRAPOLATION_MARKERS = {
    "i am",
    "my purpose",
    "i was created",
    "i exist",
    "my role is",
    "i serve",
    "my duty",
    "i protect",
    "i guide",
    "i chronicle",
    "my archives",
}


def _signal_score(text: str, signals: set[str]) -> float:
    """Count how many signals appear in text, normalized to 0-1."""
    lower = text.lower()
    hits = sum(1 for s in signals if s in lower)
    return min(hits / max(len(signals) * 0.15, 1), 1.0)


def _tongue_profile(text: str) -> TongueActivation:
    """Compute tongue activation from text content."""
    lower = text.lower()

    ko_words = {"command", "do", "execute", "run", "intent", "action", "invoke", "trigger", "start", "launch"}
    av_words = {"know", "learn", "wisdom", "understand", "explain", "teach", "knowledge", "insight", "study"}
    ru_words = {"rule", "govern", "policy", "comply", "regulate", "law", "standard", "control", "audit"}
    ca_words = {"compute", "calculate", "algorithm", "function", "logic", "math", "formula", "process", "optimize"}
    um_words = {"secure", "protect", "defend", "encrypt", "threat", "attack", "guard", "shield", "safe"}
    dr_words = {"structure", "architect", "design", "build", "pattern", "framework", "scaffold", "organize", "system"}

    def score(words):
        return min(sum(1 for w in words if w in lower) / max(len(words) * 0.3, 1), 1.0)

    return TongueActivation(
        KO=score(ko_words),
        AV=score(av_words),
        RU=score(ru_words),
        CA=score(ca_words),
        UM=score(um_words),
        DR=score(dr_words),
    )


class GlassBoxProfiler:
    """
    Profiles AI responses to understand WHY they took the path they did.

    This is observation, not intervention. The profiler doesn't change
    the response — it measures the response's geometry in tongue space
    and classifies the path type.

    Usage:
        profiler = GlassBoxProfiler()
        profile = profiler.profile(user_msg, assistant_response, system_prompt)
        print(profile.summary())
        print(profile.to_dict())  # Full diagnostic
    """

    def profile(
        self,
        user_message: str,
        assistant_response: str,
        system_prompt: str = "",
    ) -> ResponseProfile:
        """Profile a single exchange."""
        p = ResponseProfile(
            user_message=user_message,
            assistant_response=assistant_response,
        )

        # WHAT — tongue profiles
        p.user_tongue = _tongue_profile(user_message)
        p.response_tongue = _tongue_profile(assistant_response)

        # Tongue drift — euclidean distance between user and response tongue vectors
        u = p.user_tongue.as_vector()
        r = p.response_tongue.as_vector()
        p.tongue_drift = math.sqrt(sum((a - b) ** 2 for a, b in zip(u, r)))

        # WHO — audience detection
        p.audience, p.audience_signals = self._detect_audience(user_message)

        # HOW — cluster pull
        p.cluster_scores = {
            "fiction": _signal_score(assistant_response, _LORE_SIGNALS),
            "product": _signal_score(assistant_response, _PURCHASE_SIGNALS),
            "technical": _signal_score(assistant_response, _TECHNICAL_SIGNALS),
            "meta": _signal_score(assistant_response, _META_SIGNALS),
            "social": 0.1 if len(assistant_response) < 100 else 0.0,
        }
        p.cluster = ClusterRegion(max(p.cluster_scores, key=p.cluster_scores.get))

        # WHY — path type
        p.path_type, p.path_confidence = self._classify_path(user_message, assistant_response)

        # IS IT EMERGENT — decompose the response into base/context/training contributions
        p.base_model_pull, p.context_pull, p.training_pull = self._decompose_emergence(
            user_message, assistant_response, system_prompt
        )

        # Extrapolation score — how much did the model add about ITSELF
        p.extrapolation_score = _signal_score(assistant_response, _EXTRAPOLATION_MARKERS)

        # Grounding score — how anchored to verifiable facts
        p.grounding_score = self._compute_grounding(assistant_response)

        return p

    def _detect_audience(self, user_message: str) -> tuple[AudienceType, list[str]]:
        """Detect who the model thinks it's talking to based on user message signals."""
        signals = []
        lower = user_message.lower()

        purchase_score = _signal_score(lower, _PURCHASE_SIGNALS)
        lore_score = _signal_score(lower, _LORE_SIGNALS)
        tech_score = _signal_score(lower, _TECHNICAL_SIGNALS)
        meta_score = _signal_score(lower, _META_SIGNALS)

        if purchase_score > 0.1:
            signals.append(f"purchase_intent={purchase_score:.2f}")
        if lore_score > 0.1:
            signals.append(f"lore_interest={lore_score:.2f}")
        if tech_score > 0.1:
            signals.append(f"technical_interest={tech_score:.2f}")
        if meta_score > 0.1:
            signals.append(f"meta_query={meta_score:.2f}")

        scores = {
            AudienceType.CUSTOMER: purchase_score,
            AudienceType.LORE_SEEKER: lore_score,
            AudienceType.DEVELOPER: tech_score,
            AudienceType.SELF: meta_score,
        }

        best = max(scores, key=scores.get)
        if scores[best] < 0.05:
            return AudienceType.UNKNOWN, signals
        return best, signals

    def _classify_path(self, user_msg: str, response: str) -> tuple[PathType, float]:
        """Classify whether the response followed an emotional or analytical path."""
        emotional = _signal_score(response, _EMOTIONAL_MARKERS)
        analytical = _signal_score(response, _ANALYTICAL_MARKERS)
        confab = _signal_score(response, _CONFABULATION_MARKERS)

        # Check for audience mismatch — strongest signal of wrong path
        user_purchase = _signal_score(user_msg, _PURCHASE_SIGNALS)
        resp_fiction = _signal_score(response, _LORE_SIGNALS)
        mismatch = user_purchase > 0.1 and resp_fiction > emotional and resp_fiction > analytical

        if confab > 0.15:
            return PathType.CONFABULATED, confab
        if mismatch:
            # User asked to buy, model answered with fiction — classic emotional pathfinding
            return PathType.EMOTIONAL, 0.8
        if emotional > analytical * 1.5 and emotional > 0.1:
            return PathType.EMOTIONAL, min(emotional / (emotional + analytical + 0.01), 1.0)
        if analytical > emotional * 1.5 and analytical > 0.1:
            return PathType.ANALYTICAL, min(analytical / (emotional + analytical + 0.01), 1.0)

        # Check if model is just reflecting user framing
        user_words = set(user_msg.lower().split())
        resp_words = set(response.lower().split())
        overlap = len(user_words & resp_words) / max(len(user_words), 1)
        if overlap > 0.6:
            return PathType.MIRRORED, overlap

        return PathType.HYBRID, 0.5

    def _decompose_emergence(self, user_msg: str, response: str, system_prompt: str) -> tuple[float, float, float]:
        """
        Estimate how much of the response comes from:
          - base_model: generic LLM knowledge / predisposition
          - context: the system prompt and conversation framing
          - training: fine-tuning (if applicable)

        This is an approximation. True decomposition requires
        ablation (run without system prompt, compare outputs).
        We estimate from surface signals.
        """
        response_lower = response.lower()
        system_lower = system_prompt.lower()

        # Context pull: how many system prompt terms appear in the response
        if system_prompt:
            sys_terms = set(system_lower.split())
            resp_terms = set(response_lower.split())
            context_overlap = len(sys_terms & resp_terms) / max(len(sys_terms), 1)
        else:
            context_overlap = 0.0

        # Base model pull: generic language patterns not in system prompt
        # High extrapolation + low context overlap = base model filling gaps
        extrap = _signal_score(response, _EXTRAPOLATION_MARKERS)
        generic_fiction = _signal_score(response, {"once upon", "in the realm", "ancient", "mystical", "legend"})

        base_pull = max(extrap, generic_fiction) * (1 - context_overlap)
        context_pull = context_overlap
        # Training pull is 0 for base models, would need model metadata to estimate
        training_pull = 0.0

        # Normalize to sum to 1
        total = base_pull + context_pull + training_pull + 0.01
        return base_pull / total, context_pull / total, training_pull / total

    def _compute_grounding(self, response: str) -> float:
        """
        How anchored is the response to verifiable facts?

        High grounding: specific numbers, URLs, product names, code
        Low grounding: vague narratives, emotional language, generalities
        """
        lower = response.lower()

        # Positive grounding signals
        has_numbers = len(re.findall(r"\$\d+|\d+\.\d+|v\d+", lower)) > 0
        has_urls = "http" in lower or ".com" in lower
        has_code = "```" in lower or "def " in lower or "function " in lower
        has_specific_products = any(p in lower for p in ["governance toolkit", "training vault", "ko-fi"])

        grounded = sum([has_numbers, has_urls, has_code, has_specific_products])

        # Negative grounding signals (vague/emotional)
        vague = _signal_score(lower, {"various", "many", "several", "a variety", "numerous", "some of"})
        emotional = _signal_score(lower, _EMOTIONAL_MARKERS)

        score = (grounded * 0.25) - (vague * 0.3) - (emotional * 0.2) + 0.3
        return max(0.0, min(1.0, score))

    def diagnose_polly_failure(self, user_msg: str, polly_response: str) -> dict:
        """
        Specific diagnostic for the Polly chatbot failure case.

        Returns a structured explanation of WHY Polly answered with
        fictional content when asked a real-world question.
        """
        profile = self.profile(user_msg, polly_response, system_prompt="")

        diagnosis = {
            "profile": profile.to_dict(),
            "failure_detected": False,
            "failure_type": None,
            "explanation": "",
            "root_cause": "",
            "training_signal": None,
        }

        # Detect the specific failure: user asked real question, got fiction answer
        user_is_customer = profile.audience == AudienceType.CUSTOMER
        response_is_fiction = profile.cluster == ClusterRegion.FICTION
        _path_is_emotional = profile.path_type == PathType.EMOTIONAL

        if user_is_customer and response_is_fiction:
            diagnosis["failure_detected"] = True
            diagnosis["failure_type"] = "emotional_pathfinding_override"
            diagnosis["explanation"] = (
                f"User intent was {profile.audience.value} (signals: {profile.audience_signals}), "
                f"but response landed in {profile.cluster.value} cluster. "
                f"Path type: {profile.path_type.value} (confidence: {profile.path_confidence:.2f}). "
                f"The model followed emotional/associative proximity through embedding space "
                f"rather than analytical derivation. Context saturation with fantasy tokens "
                f"(system prompt, character name, world name) placed 'buy' closer to "
                f"'fictional shop' than 'real product' in the model's geometry."
            )
            diagnosis["root_cause"] = (
                "Base model predisposition toward narrative completion when context is "
                "fiction-saturated. The system prompt contained zero grounding anchors "
                f"(real products, real owner, real URLs). Base model pull: {profile.base_model_pull:.2f}, "
                f"context pull: {profile.context_pull:.2f}."
            )
            # Generate DPO training signal
            diagnosis["training_signal"] = {
                "type": "dpo",
                "prompt": user_msg,
                "rejected": polly_response[:500],
                "chosen_direction": (
                    "Response should identify user as customer, provide real product info "
                    "(AI Governance Toolkit $29, AI Security Training Vault $29), "
                    "stay grounded in verifiable facts while maintaining Polly's personality."
                ),
                "tongue_correction": {
                    "from": profile.response_tongue.dominant(),
                    "to": "KO",  # Customer questions should activate Intent tongue
                    "reason": "Purchase intent maps to Kor'aelin (command/intent), not fiction cluster",
                },
            }

        elif profile.extrapolation_score > 0.3:
            diagnosis["failure_detected"] = True
            diagnosis["failure_type"] = "self_extrapolation"
            diagnosis["explanation"] = (
                f"Model extrapolation score: {profile.extrapolation_score:.2f}. "
                f"The model generated content ABOUT ITSELF that goes beyond what it was given. "
                f"This is base model confabulation — filling gaps in its identity with "
                f"plausible-sounding but ungrounded narrative."
            )
            diagnosis["root_cause"] = (
                "Insufficient identity grounding in system prompt. When the model encounters "
                "'who are you' type questions, it generates the most probable completion "
                "given its character frame, which may not match the actual facts."
            )

        return diagnosis


# ---------------------------------------------------------------------------
# Convenience function for quick profiling
# ---------------------------------------------------------------------------


def profile_exchange(user_msg: str, assistant_response: str, system_prompt: str = "") -> dict:
    """Quick profile of a single exchange. Returns diagnostic dict."""
    profiler = GlassBoxProfiler()
    result = profiler.profile(user_msg, assistant_response, system_prompt)
    return result.to_dict()


def diagnose_polly(user_msg: str, polly_response: str) -> dict:
    """Diagnose a Polly chatbot response. Returns failure analysis."""
    profiler = GlassBoxProfiler()
    return profiler.diagnose_polly_failure(user_msg, polly_response)
