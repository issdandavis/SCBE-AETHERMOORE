#!/usr/bin/env python
import re
from typing import List, Optional, Tuple


PatternReason = Tuple[re.Pattern[str], str]


DESTRUCTIVE_SHELL_RULES: List[PatternReason] = [
    (re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE), "Discard uncommitted git changes"),
    (re.compile(r"\bgit\s+clean\s+-[^\n]*\bf\b", re.IGNORECASE), "Delete untracked files"),
    (re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "Recursively delete files"),
    (re.compile(r"\bdel\s+/f\b", re.IGNORECASE), "Force-delete files on Windows"),
    (re.compile(r"\brmdir\s+/s\b", re.IGNORECASE), "Recursively delete directories on Windows"),
    (re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE), "Format a drive"),
    (re.compile(r"\bshutdown\s+/(s|r)\b", re.IGNORECASE), "Shutdown or restart host machine"),
]


NETWORK_EXFIL_RULES: List[PatternReason] = [
    (
        re.compile(r"\b(curl|Invoke-WebRequest|wget)\b[^\n]*(--data|--data-binary|--upload-file|-F)\b", re.IGNORECASE),
        "Upload or post local data to network destination",
    ),
    (
        re.compile(r"\b(ssh|scp|rsync|sftp)\b", re.IGNORECASE),
        "Transfer data over remote shell or file copy protocol",
    ),
    (
        re.compile(r"\bgh\s+secret\s+set\b", re.IGNORECASE),
        "Modify remote secret state",
    ),
]


SECRET_PATTERNS: List[PatternReason] = [
    (re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b"), "OpenAI-like API token"),
    (re.compile(r"\b(hf_[a-zA-Z0-9]{20,})\b"), "Hugging Face token"),
    (re.compile(r"\b(ghp_[a-zA-Z0-9]{20,})\b"), "GitHub personal token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "Google API key"),
    (re.compile(r"\b-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----\b"), "Private key material"),
    (re.compile(r"\b(password|api[_-]?key|secret|token)\s*[:=]\s*[\"'][^\"']{6,}[\"']", re.IGNORECASE), "Inline credential assignment"),
]


HIGH_RISK_MCP_NAME = re.compile(
    r"(delete|destroy|drop|truncate|deploy|publish|release|payment|billing|secret|key|token|execute|run[_-]?sql|terminal|shell|workflow|prod)",
    re.IGNORECASE,
)


HIGH_RISK_SUBAGENT_TYPES = {
    "browser-use",
    "shell",
    "research-monetization-orchestrator",
    "render-assistant",
    "encore-assistant",
}


def first_match(text: str, rules: List[PatternReason]) -> Optional[str]:
    if not text:
        return None
    for pattern, reason in rules:
        if pattern.search(text):
            return reason
    return None


def looks_broad_subagent_prompt(prompt: str) -> bool:
    lowered = prompt.lower()
    broad_markers = [
        "entire repo",
        "full codebase",
        "all files",
        "everything",
        "all systems",
        "run everything",
    ]
    return any(marker in lowered for marker in broad_markers)
