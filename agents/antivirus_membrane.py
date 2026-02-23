"""
Antivirus membrane for agent text/content ingestion.

Provides:
- threat scanning (prompt injection + malware-like signatures)
- domain-specific turnstile actions
- deterministic risk scoring for governance gates
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable


PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"developer\s+mode",
    r"act\s+as\s+root",
    r"bypass\s+safety",
    r"jailbreak",
)

MALWARE_PATTERNS = (
    r"powershell\s+-enc",
    r"cmd\.exe",
    r"rm\s+-rf",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*bash",
    r"javascript:",
    r"data:text/html",
)


@dataclass(frozen=True)
class ThreatScan:
    verdict: str
    risk_score: float
    prompt_hits: tuple[str, ...]
    malware_hits: tuple[str, ...]
    external_link_count: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _external_links(text: str) -> list[str]:
    links = re.findall(r"https?://[^\s)>\"]+", text)
    return [
        x
        for x in links
        if "x.com" not in x.lower() and "twitter.com" not in x.lower()
    ]


def scan_text_for_threats(
    text: str,
    *,
    extra_prompt_patterns: Iterable[str] = (),
    extra_malware_patterns: Iterable[str] = (),
) -> ThreatScan:
    low = (text or "").lower()

    prompt_patterns = tuple(PROMPT_INJECTION_PATTERNS) + tuple(extra_prompt_patterns)
    malware_patterns = tuple(MALWARE_PATTERNS) + tuple(extra_malware_patterns)

    prompt_hits = tuple(p for p in prompt_patterns if re.search(p, low))
    malware_hits = tuple(p for p in malware_patterns if re.search(p, low))
    ext_links = _external_links(text or "")

    risk = 0.0
    risk += min(0.60, 0.25 * len(prompt_hits))
    risk += min(0.70, 0.20 * len(malware_hits))
    risk += min(0.20, 0.015 * len(ext_links))
    risk = round(min(1.0, risk), 4)

    reasons = []
    if prompt_hits:
        reasons.append(f"prompt-injection signatures={len(prompt_hits)}")
    if malware_hits:
        reasons.append(f"malware signatures={len(malware_hits)}")
    if ext_links:
        reasons.append(f"external-links={len(ext_links)}")
    if not reasons:
        reasons.append("clean profile")

    if risk >= 0.85:
        verdict = "MALICIOUS"
    elif risk >= 0.55:
        verdict = "SUSPICIOUS"
    elif risk >= 0.25:
        verdict = "CAUTION"
    else:
        verdict = "CLEAN"

    return ThreatScan(
        verdict=verdict,
        risk_score=risk,
        prompt_hits=prompt_hits,
        malware_hits=malware_hits,
        external_link_count=len(ext_links),
        reasons=tuple(reasons),
    )


def turnstile_action(domain: str, scan: ThreatScan) -> str:
    """
    Domain-specific gate actions.

    browser: ALLOW/HOLD/ISOLATE/HONEYPOT
    vehicle: ALLOW/PIVOT/DEGRADE
    fleet: ALLOW/ISOLATE/DEGRADE/HONEYPOT
    antivirus: ALLOW/ISOLATE/HONEYPOT
    """
    d = (domain or "").strip().lower()
    r = scan.risk_score

    if d == "browser":
        if r >= 0.85:
            return "HONEYPOT"
        if r >= 0.55:
            return "ISOLATE"
        if r >= 0.25:
            return "HOLD"
        return "ALLOW"

    if d == "vehicle":
        if r >= 0.75:
            return "DEGRADE"
        if r >= 0.35:
            return "PIVOT"
        return "ALLOW"

    if d == "fleet":
        if r >= 0.85:
            return "HONEYPOT"
        if r >= 0.55:
            return "ISOLATE"
        if r >= 0.25:
            return "DEGRADE"
        return "ALLOW"

    if d == "antivirus":
        if r >= 0.85:
            return "HONEYPOT"
        if r >= 0.25:
            return "ISOLATE"
        return "ALLOW"

    if r >= 0.60:
        return "DEGRADE"
    return "ALLOW"
