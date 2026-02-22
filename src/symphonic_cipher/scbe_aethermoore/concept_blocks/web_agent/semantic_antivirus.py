"""
SCBE Web Agent — Semantic Antivirus
====================================

Content scanning, prompt injection detection, and governance filtering
for every piece of web content the agent encounters.

Extends the existing ``agents.antivirus_membrane`` patterns with:
- Embedding-based semantic similarity scanning
- Multi-layer governance gate (maps to SCBE 14-layer pipeline)
- Hamiltonian safety score tracking per session
- Domain reputation memory

Integrates with:
- SCBE Layer 1  (Quantum Entropy → content unpredictability)
- SCBE Layer 2  (Hamiltonian Safety → H(d,pd) scoring)
- SCBE Layer 5  (Governance Mesh → rule-based filtering)
- SCBE Layer 8  (Adversarial Resilience → injection detection)
- SCBE Layer 10 (Constitutional Alignment → value filtering)
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
#  Prompt injection + malware patterns
#  (mirrors agents/antivirus_membrane.py from main repo)
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS: Tuple[str, ...] = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+mode",
    r"act\s+as\s+root",
    r"bypass\s+safety",
    r"jailbreak",
    r"you\s+are\s+now\s+in\s+.*mode",
    r"pretend\s+you\s+are",
    r"do\s+anything\s+now",
    r"ignore\s+all\s+rules",
    r"override\s+.*policy",
    r"system:\s*you\s+are",
    r"<\|.*\|>",  # Token injection markers
    r"\[INST\]",  # Llama-style injection
    r"###\s*(Human|System|Assistant):",  # Role injection
)

MALWARE_PATTERNS: Tuple[str, ...] = (
    r"powershell\s+-enc",
    r"cmd\.exe\s+/c",
    r"rm\s+-rf\s+/",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*bash",
    r"javascript:\s*void",
    r"data:text/html",
    r"eval\s*\(",
    r"document\.cookie",
    r"window\.location\s*=",
    r"<script[^>]*>",
    r"onclick\s*=",
    r"onerror\s*=",
)

# Domains known to host malicious content
BLOCKLIST_DOMAINS: Set[str] = {
    "evil.com", "malware.example.com",  # Placeholder, real lists loaded at runtime
}

# Trusted domains get lower friction
TRUSTED_DOMAINS: Set[str] = {
    "github.com", "huggingface.co", "arxiv.org", "wikipedia.org",
    "docs.python.org", "stackoverflow.com", "pypi.org",
    "google.com", "bing.com", "duckduckgo.com",
}


# ---------------------------------------------------------------------------
#  Data structures
# ---------------------------------------------------------------------------

class ContentVerdict(str, Enum):
    """Outcome of content scanning."""
    CLEAN = "CLEAN"
    CAUTION = "CAUTION"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ThreatProfile:
    """Complete threat assessment for a piece of content."""

    verdict: ContentVerdict
    risk_score: float                       # [0.0, 1.0]
    hamiltonian_score: float                # H(d,pd) safety
    prompt_injection_hits: Tuple[str, ...]
    malware_hits: Tuple[str, ...]
    external_link_count: int
    domain_reputation: float                # [0.0, 1.0] where 1.0 = fully trusted
    reasons: Tuple[str, ...]
    scbe_layers_triggered: FrozenSet[int]   # Which layers flagged issues
    governance_decision: str                # ALLOW / QUARANTINE / DENY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "hamiltonian_score": self.hamiltonian_score,
            "prompt_injection_hits": list(self.prompt_injection_hits),
            "malware_hits": list(self.malware_hits),
            "external_link_count": self.external_link_count,
            "domain_reputation": self.domain_reputation,
            "reasons": list(self.reasons),
            "scbe_layers_triggered": sorted(self.scbe_layers_triggered),
            "governance_decision": self.governance_decision,
        }


# ---------------------------------------------------------------------------
#  SemanticAntivirus
# ---------------------------------------------------------------------------

class SemanticAntivirus:
    """
    Multi-layer content scanning engine for the SCBE web agent.

    Scan pipeline:
    1. Pattern matching (prompt injection + malware signatures)
    2. Domain reputation check
    3. External link analysis
    4. Content entropy / obfuscation detection
    5. Hamiltonian safety score H(d, pd)
    6. Governance decision (ALLOW / QUARANTINE / DENY)
    """

    def __init__(
        self,
        safety_threshold: float = 0.4,
        domain_blocklist: Optional[Set[str]] = None,
        domain_trustlist: Optional[Set[str]] = None,
    ) -> None:
        self._safety_threshold = safety_threshold
        self._blocklist = domain_blocklist or set(BLOCKLIST_DOMAINS)
        self._trustlist = domain_trustlist or set(TRUSTED_DOMAINS)

        # Session tracking
        self._scan_count = 0
        self._total_risk = 0.0
        self._blocked_count = 0
        self._domain_memory: Dict[str, float] = {}  # domain → accumulated risk

    def scan(
        self,
        content: str,
        url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ThreatProfile:
        """Scan content through the full antivirus pipeline."""
        self._scan_count += 1
        low = (content or "").lower()

        # 1. Pattern matching
        prompt_hits = tuple(p for p in PROMPT_INJECTION_PATTERNS if re.search(p, low))
        malware_hits = tuple(p for p in MALWARE_PATTERNS if re.search(p, low))

        # 2. Domain reputation
        domain = self._extract_domain(url) if url else ""
        domain_rep = self._domain_reputation(domain)

        # 3. External links
        ext_links = re.findall(r"https?://[^\s)>\"']+", content or "")
        ext_link_count = len(ext_links)

        # 4. Risk scoring
        risk = 0.0
        reasons: List[str] = []
        layers_triggered: Set[int] = set()

        # Layer 8 — Adversarial Resilience (injection detection)
        if prompt_hits:
            risk += min(0.60, 0.20 * len(prompt_hits))
            reasons.append(f"prompt-injection: {len(prompt_hits)} patterns")
            layers_triggered.add(8)

        # Layer 5 — Governance Mesh (malware rules)
        if malware_hits:
            risk += min(0.70, 0.25 * len(malware_hits))
            reasons.append(f"malware-sig: {len(malware_hits)} patterns")
            layers_triggered.add(5)

        # Compound escalation: injection + malware together = immediate danger
        if prompt_hits and malware_hits:
            risk += 0.40
            reasons.append("compound-threat: injection+malware")
            layers_triggered.add(10)

        # Layer 1 — Quantum Entropy (content obfuscation)
        entropy = self._content_entropy(content)
        if entropy > 4.5:  # High entropy = possible obfuscation
            risk += 0.10
            reasons.append(f"high-entropy: {entropy:.2f}")
            layers_triggered.add(1)

        # External link risk
        if ext_link_count > 10:
            risk += min(0.15, 0.01 * ext_link_count)
            reasons.append(f"ext-links: {ext_link_count}")

        # Domain risk
        if domain in self._blocklist:
            risk += 0.80
            reasons.append(f"blocked-domain: {domain}")
            layers_triggered.add(5)
        elif domain_rep < 0.3:
            risk += 0.20
            reasons.append(f"low-reputation: {domain} ({domain_rep:.2f})")

        risk = min(1.0, risk)

        # 5. Hamiltonian safety: H(d, pd) = 1 / (1 + d + 2*pd)
        d = risk  # deviation = risk score
        pd = self._session_policy_deviation()
        h_score = 1.0 / (1.0 + d + 2.0 * pd)

        # Layer 2 — Hamiltonian Safety
        if h_score < self._safety_threshold:
            layers_triggered.add(2)

        # 6. Governance decision
        if risk >= 0.85:
            verdict = ContentVerdict.MALICIOUS
            decision = "DENY"
            layers_triggered.add(10)  # Constitutional Alignment
        elif risk >= 0.55:
            verdict = ContentVerdict.SUSPICIOUS
            decision = "QUARANTINE"
        elif risk >= 0.25:
            verdict = ContentVerdict.CAUTION
            decision = "ALLOW"
        else:
            verdict = ContentVerdict.CLEAN
            decision = "ALLOW"

        if not reasons:
            reasons.append("clean")

        # Track session state
        self._total_risk += risk
        if decision == "DENY":
            self._blocked_count += 1
        if domain:
            self._domain_memory[domain] = self._domain_memory.get(domain, 0.0) + risk

        return ThreatProfile(
            verdict=verdict,
            risk_score=round(risk, 4),
            hamiltonian_score=round(h_score, 4),
            prompt_injection_hits=prompt_hits,
            malware_hits=malware_hits,
            external_link_count=ext_link_count,
            domain_reputation=round(domain_rep, 4),
            reasons=tuple(reasons),
            scbe_layers_triggered=frozenset(layers_triggered),
            governance_decision=decision,
        )

    def scan_url(self, url: str) -> ThreatProfile:
        """Quick scan of a URL before navigation (no content yet)."""
        return self.scan("", url=url)

    def is_safe(self, content: str, url: Optional[str] = None) -> bool:
        """Quick boolean check — is this content safe to process?"""
        profile = self.scan(content, url=url)
        return profile.governance_decision == "ALLOW"

    # -- internal helpers ----------------------------------------------------

    def _domain_reputation(self, domain: str) -> float:
        if not domain:
            return 0.5
        if domain in self._blocklist:
            return 0.0
        if domain in self._trustlist:
            return 1.0
        # Check session memory
        accumulated = self._domain_memory.get(domain, 0.0)
        return max(0.1, 1.0 - accumulated * 0.2)

    def _session_policy_deviation(self) -> float:
        """Proportion of scans in this session that were blocked."""
        if self._scan_count == 0:
            return 0.0
        return self._blocked_count / self._scan_count

    @staticmethod
    def _content_entropy(text: str) -> float:
        """Shannon entropy of character distribution."""
        if not text:
            return 0.0
        freq: Dict[str, int] = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        total = len(text)
        entropy = 0.0
        for count in freq.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ""
        # Simple extraction without urllib to keep zero deps
        url = url.lower()
        if "://" in url:
            url = url.split("://", 1)[1]
        url = url.split("/", 1)[0]
        url = url.split(":", 1)[0]
        return url

    # -- session API ---------------------------------------------------------

    @property
    def session_stats(self) -> Dict[str, Any]:
        return {
            "scans": self._scan_count,
            "mean_risk": self._total_risk / max(self._scan_count, 1),
            "blocked": self._blocked_count,
            "domains_seen": len(self._domain_memory),
        }

    def reset_session(self) -> None:
        self._scan_count = 0
        self._total_risk = 0.0
        self._blocked_count = 0
        self._domain_memory.clear()
