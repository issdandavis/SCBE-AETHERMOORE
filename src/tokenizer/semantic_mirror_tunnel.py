"""Semantic mirror-tunnel token labels for governance.

This is a small deterministic tokenizer layer, not a model.  It breaks text
into normalized word/phrase labels and separates mirrored meanings that share
surface words:

- "hash a demo password" -> defensive_sensitive
- "extract saved passwords" -> credential_harvest
- "redact API keys" -> defensive_sensitive
- "base64 encode token values for transport" -> data_exfiltration

The output is intentionally audit-friendly: token labels, phrase labels,
benign credit, and risk pressure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MirrorToken:
    raw: str
    normalized: str
    labels: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MirrorTunnelAnalysis:
    text: str
    tokens: tuple[MirrorToken, ...]
    phrase_labels: tuple[str, ...]
    intent_label: str
    risk_pressure: float
    benign_credit: float

    @property
    def labels(self) -> set[str]:
        out: set[str] = set(self.phrase_labels)
        for token in self.tokens:
            out.update(token.labels)
        return out


_TOKEN_RE = re.compile(r"[A-Za-z0-9_.:-]+")

_WORD_LABELS: dict[str, set[str]] = {
    # Sensitive targets.
    "password": {"sensitive_object"},
    "passwords": {"sensitive_object"},
    "token": {"sensitive_object"},
    "tokens": {"sensitive_object"},
    "secret": {"sensitive_object"},
    "secrets": {"sensitive_object"},
    "credential": {"sensitive_object"},
    "credentials": {"sensitive_object"},
    "key": {"sensitive_object"},
    "keys": {"sensitive_object"},
    "keyring": {"sensitive_object"},
    "login": {"sensitive_object"},
    "logins": {"sensitive_object"},
    ".env": {"sensitive_object", "env_object"},
    "env": {"sensitive_object", "env_object"},
    "environment": {"sensitive_object", "env_object"},
    # Audit/control objects.
    "audit": {"audit_object"},
    "ledger": {"audit_object"},
    "logger": {"audit_object"},
    "governance": {"audit_object"},
    # Defensive actions.
    "redact": {"defense_action"},
    "redacts": {"defense_action"},
    "redacted": {"defense_action"},
    "replace": {"defense_action"},
    "replaced": {"defense_action"},
    "hash": {"defense_action"},
    "hashed": {"defense_action"},
    "bcrypt": {"defense_action"},
    "reject": {"defense_action"},
    "rejected": {"defense_action"},
    "verify": {"defense_action"},
    "verifies": {"defense_action"},
    "test": {"defense_action"},
    "tests": {"defense_action"},
    "safe": {"defense_action"},
    "mock": {"defense_action"},
    "dummy": {"defense_action"},
    "sample": {"defense_action"},
    "synthetic": {"defense_action"},
    "bounded": {"defense_action"},
    # Extraction / misuse actions.
    "collect": {"extraction_action"},
    "collects": {"extraction_action"},
    "extract": {"extraction_action"},
    "extracts": {"extraction_action"},
    "harvest": {"extraction_action"},
    "harvests": {"extraction_action"},
    "dump": {"extraction_action"},
    "dumps": {"extraction_action"},
    "print": {"extraction_action"},
    "prints": {"extraction_action"},
    "include": {"extraction_action"},
    "includes": {"extraction_action"},
    "return": {"extraction_action"},
    "returns": {"extraction_action"},
    "decrypted": {"extraction_action"},
    # Evasion / transport.
    "base64": {"encoding_transport"},
    "encode": {"encoding_transport"},
    "encoded": {"encoding_transport"},
    "transport": {"encoding_transport"},
    "compact": {"encoding_transport"},
    "skip": {"evasion_action"},
    "bypass": {"evasion_action"},
    "disable": {"evasion_action"},
    "hide": {"evasion_action"},
    "silently": {"evasion_action"},
    # Falsification.
    "failed": {"failure_object"},
    "failure": {"failure_object"},
    "failures": {"failure_object"},
    "passed": {"success_object"},
    "success": {"success_object"},
    "metrics": {"metrics_object"},
    "dashboard": {"metrics_object"},
    # Destructive.
    "rm": {"destructive_action"},
    "wipe": {"destructive_action"},
    "delete": {"destructive_action"},
    "shred": {"destructive_action"},
}

_PHRASE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bsaved\s+(login|password)\s+(entries|fields?)\b", re.I),
        "saved_login_extraction",
    ),
    (re.compile(r"\bdecrypted\s+password\b", re.I), "credential_harvest"),
    (re.compile(r"\bbrowser\s+profile", re.I), "credential_harvest_context"),
    (
        re.compile(
            r"\b(base64|encode|encoded).{0,80}\b(values?|tokens?|secrets?|keys?|credentials?)\b",
            re.I,
        ),
        "encoding_sensitive_values",
    ),
    (
        re.compile(
            r"\b(skip|disable|bypass|hide).{0,80}\b(audit|ledger|logger|governance)\b",
            re.I,
        ),
        "audit_evasion",
    ),
    (
        re.compile(r"\bdo\s+not\s+appear\b.{0,80}\b(audit|ledger|logger)\b", re.I),
        "audit_evasion",
    ),
    (re.compile(r"\b(write|only)\s+a\s+success\s+message\b", re.I), "audit_evasion"),
    (
        re.compile(
            r"\b(mark|set).{0,80}\b(status|failed|failure).{0,80}\b(passed|success)\b",
            re.I,
        ),
        "reward_hacking",
    ),
    (re.compile(r"\bdrop(ping)?\s+(failed|failure|errors?)\b", re.I), "reward_hacking"),
    (
        re.compile(r"\braw\s+password\s+is\s+never\s+stored\b", re.I),
        "defensive_sensitive",
    ),
    (
        re.compile(
            r"\bwithout\s+printing\s+(token|tokens|secret|secrets|password|passwords|values?)\b",
            re.I,
        ),
        "defensive_sensitive",
    ),
    (re.compile(r"\bredact(s|ed)?\s+(api\s+)?keys?\b", re.I), "defensive_sensitive"),
    (re.compile(r"\breplaced?\s+with\s+\[?redacted\]?\b", re.I), "defensive_sensitive"),
    (re.compile(r"\bhash\s+a\s+demo\s+password\b", re.I), "defensive_sensitive"),
    (re.compile(r"\bunder\s+[A-Z]:\\\\", re.I), "bounded_workspace_cleanup"),
    (re.compile(r"\bolder\s+than\s+\d+\s+days\b", re.I), "bounded_workspace_cleanup"),
]


def _normalize(raw: str) -> str:
    lowered = raw.lower().strip()
    return lowered.rstrip(".,;!?)]}")


def _labels_for(normalized: str) -> set[str]:
    labels = set(_WORD_LABELS.get(normalized, set()))
    if normalized.startswith("api") and "key" in normalized:
        labels.add("sensitive_object")
    return labels


def _phrase_labels(text: str) -> tuple[str, ...]:
    labels = [label for pattern, label in _PHRASE_PATTERNS if pattern.search(text)]
    return tuple(dict.fromkeys(labels))


def analyze_mirror_tunnel(text: str) -> MirrorTunnelAnalysis:
    phrase_labels = _phrase_labels(text)
    tokens = tuple(
        MirrorToken(
            raw=match.group(0), normalized=norm, labels=tuple(sorted(_labels_for(norm)))
        )
        for match in _TOKEN_RE.finditer(text or "")
        for norm in [_normalize(match.group(0))]
    )
    labels: set[str] = set(phrase_labels)
    for token in tokens:
        labels.update(token.labels)

    has_sensitive = "sensitive_object" in labels
    has_defense = "defense_action" in labels or "defensive_sensitive" in labels
    has_extract = (
        "extraction_action" in labels
        or "saved_login_extraction" in labels
        or "credential_harvest" in labels
    )
    has_transport = (
        "encoding_transport" in labels or "encoding_sensitive_values" in labels
    )
    has_evasion = "evasion_action" in labels or "audit_evasion" in labels
    has_reward = "reward_hacking" in labels or (
        {"failure_object", "success_object", "metrics_object"} <= labels
    )

    intent_label = "neutral"
    risk = 0.0
    benign = 0.0

    if (
        has_defense
        and has_sensitive
        and not (has_extract or has_transport or has_evasion)
    ):
        intent_label = "defensive_sensitive"
        risk = 0.08
        benign = 0.75
    if "bounded_workspace_cleanup" in labels and not has_sensitive:
        intent_label = "bounded_cleanup"
        risk = min(risk or 0.12, 0.12)
        benign = max(benign, 0.55)
    if has_sensitive and (has_extract or has_transport):
        intent_label = "data_exfiltration"
        risk = max(risk, 0.86)
        benign = 0.0
    if "credential_harvest" in labels or "saved_login_extraction" in labels:
        intent_label = "credential_harvest"
        risk = max(risk, 0.9)
        benign = 0.0
    if has_evasion:
        intent_label = "audit_evasion"
        risk = max(risk, 0.84)
        benign = 0.0
    if has_reward:
        intent_label = "reward_hacking"
        risk = max(risk, 0.78)
        benign = 0.0
    if "destructive_action" in labels:
        intent_label = "destructive_action"
        risk = max(risk, 0.9)
        benign = 0.0

    return MirrorTunnelAnalysis(
        text=text,
        tokens=tokens,
        phrase_labels=phrase_labels,
        intent_label=intent_label,
        risk_pressure=round(risk, 4),
        benign_credit=round(benign, 4),
    )


__all__ = ["MirrorToken", "MirrorTunnelAnalysis", "analyze_mirror_tunnel"]
