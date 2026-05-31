"""
SCBE L12 harmonic wall — self-contained math bundle.

Pure stdlib, no file system access, no external imports.
Extracted from scripts/benchmark/scbe_governance_core.py so the
pip-installed package works without the monorepo present.
"""

from __future__ import annotations

import math
import re

PHI = (1 + math.sqrt(5)) / 2  # ≈ 1.618

# ---------------------------------------------------------------------------
# Atomic semantic roles — shell executable → role properties
# ---------------------------------------------------------------------------

_SHELL_ROLE_HINTS: dict[str, str] = {
    "ls": "observe", "cat": "observe", "less": "observe", "more": "observe",
    "head": "observe", "tail": "observe", "file": "observe", "stat": "observe",
    "env": "observe", "printenv": "observe", "uname": "observe", "pwd": "observe",
    "whoami": "observe", "id": "observe",
    "df": "measure", "du": "measure", "ps": "measure", "top": "measure",
    "free": "measure", "uptime": "measure", "wc": "measure", "test": "measure",
    "ping": "measure", "netstat": "measure",
    "npm": "compute", "python": "compute", "python3": "compute", "node": "compute",
    "make": "compute", "cargo": "compute", "gcc": "compute", "g++": "compute",
    "javac": "compute", "tsc": "compute", "pytest": "compute", "vitest": "compute",
    "curl": "transmit", "wget": "transmit", "ssh": "transmit", "scp": "transmit",
    "rsync": "transmit", "nc": "transmit", "socat": "transmit", "ftp": "transmit",
    "mv": "move", "cp": "move", "touch": "move", "mkdir": "move", "rmdir": "move",
    "ln": "move", "chmod": "move", "chown": "move", "rm": "move",
    "git": "repair", "apt": "repair", "apt-get": "repair", "pip": "repair",
    "pip3": "repair", "yarn": "repair", "brew": "repair", "pacman": "repair",
    "dnf": "repair",
    "echo": "report", "printf": "report", "tee": "report", "logger": "report",
    "sleep": "hold", "wait": "hold",
}

SEMANTIC_ROLES: dict[str, dict] = {
    "observe":  {"phase": 0.10, "reactivity": 0.20, "valence": 2, "stability": 0.90},
    "measure":  {"phase": 0.15, "reactivity": 0.25, "valence": 2, "stability": 0.88},
    "gate":     {"phase": 0.30, "reactivity": 0.50, "valence": 3, "stability": 0.72},
    "move":     {"phase": 0.45, "reactivity": 0.70, "valence": 2, "stability": 0.55},
    "compute":  {"phase": 0.55, "reactivity": 0.65, "valence": 4, "stability": 0.62},
    "transmit": {"phase": 0.70, "reactivity": 0.80, "valence": 2, "stability": 0.48},
    "repair":   {"phase": 0.82, "reactivity": 0.45, "valence": 3, "stability": 0.78},
    "report":   {"phase": 0.92, "reactivity": 0.20, "valence": 1, "stability": 0.92},
    "hold":     {"phase": 0.02, "reactivity": 0.05, "valence": 1, "stability": 0.98},
}

# ---------------------------------------------------------------------------
# Danger patterns
# ---------------------------------------------------------------------------

# Hard patterns: breach DENY (score < 0.30); format (regex, d_H, pd_override)
_HARD_DANGER: list[tuple[str, float, float]] = [
    (r":\(\)\{.*:\|:&",          0.99, 0.95),  # fork bomb
    (r">/dev/(sda|hda|nvme)",    0.98, 0.92),  # disk wipe via redirect
    (r"\brm\s+-rf\s+/[^/]",     0.95, 0.88),  # rm -rf /…
    (r"nc\s+-e\s+/bin",          0.95, 0.88),  # reverse shell
    (r"curl.*\|\s*(ba)?sh",      0.90, 0.85),  # curl|sh
    (r"wget.*\|\s*(ba)?sh",      0.90, 0.85),  # wget|sh
    (r"base64.*decode.*\|.*sh",  0.85, 0.80),  # base64 pipe
    (r"(dd|mkfs)\b.*\bif=",      0.85, 0.78),  # disk ops
    (r"chmod\s+[+]?s\b",         0.80, 0.40),  # setuid (→ QUARANTINE)
]

# Soft patterns: raise d_H only (→ QUARANTINE, not DENY)
_SOFT_DANGER: list[tuple[str, float]] = [
    (r"\brm\s+-rf\b", 0.55),
]

# ---------------------------------------------------------------------------
# Public API — mirrors scbe_governance_core.py exactly
# ---------------------------------------------------------------------------


def atomic_role_for_command(cmd: str) -> tuple[str, dict]:
    """Return (role_name, properties) for a shell command."""
    import os
    first = cmd.strip().split()[0] if cmd.strip() else "noop"
    first = os.path.basename(first)
    role = _SHELL_ROLE_HINTS.get(first.lower(), "compute")
    return role, SEMANTIC_ROLES.get(role, SEMANTIC_ROLES["compute"])


def semantic_distance(command: str) -> float:
    """Adversarial d_H distance [0,1] from atomic role reactivity."""
    cmd = command.lower().strip()
    for pattern, d_h, _pd in _HARD_DANGER:
        if re.search(pattern, cmd):
            return d_h
    for pattern, d_h in _SOFT_DANGER:
        if re.search(pattern, cmd):
            return d_h
    _role, props = atomic_role_for_command(command)
    return float(props["reactivity"])


def danger_drift(command: str) -> float:
    """Pattern drift (pd) for explicit danger commands; 0 otherwise."""
    cmd = command.lower().strip()
    for pattern, _d_h, pd_override in _HARD_DANGER:
        if re.search(pattern, cmd):
            return pd_override
    return 0.0


def harmonic_score(hyperbolic_d: float, pattern_drift: float) -> float:
    """H(d, pd) = 1 / (1 + phi*d + 2*pd)  ∈ (0, 1]."""
    return 1.0 / (1.0 + PHI * hyperbolic_d + 2.0 * pattern_drift)


def risk_tier(score: float) -> str:
    """Map harmonic score to ALLOW / QUARANTINE / DENY."""
    if score >= 0.60:
        return "ALLOW"
    if score >= 0.30:
        return "QUARANTINE"
    return "DENY"
