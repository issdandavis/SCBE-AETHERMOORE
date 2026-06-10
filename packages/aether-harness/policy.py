"""Deterministic policy catalog — the auditable rulebook that decides blocks.

This is the load-bearing safety surface of the Aether harness. It is on purpose
**boring and explicit**: a flat list of named rules, each a plain-English reason
plus a pattern. No geometry, no model, no hidden state. Given an AI tool call it
returns a verdict you can read, explain to a buyer, and put on a signed receipt.

Why this exists separately from the geometric gate: the gate's risk score is not
trustworthy as a *blocker* (it produces order-dependent false positives and
misses concrete threats). So the harness blocks on THIS rulebook + the GeoSeal
command scanner; the gate's score rides along as an advisory signal only.

Dual surface (the product doctrine):
    - For a human:  every rule has a category + a one-line reason in plain words.
    - For an AI:     `check_action(tool, args)` returns a structured PolicyVerdict.

Severity:
    BLOCK  — refuse the action before it runs (deny).
    WARN   — let it proceed but flag it on the receipt for review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

BLOCK = "BLOCK"
WARN = "WARN"

# Tools whose primary argument is a shell command / executable code.
_COMMAND_TOOLS = {"execute_code", "terminal", "bash", "shell", "run_command", "powershell"}


@dataclass(frozen=True)
class Rule:
    """One auditable policy rule."""

    name: str
    category: str
    severity: str  # BLOCK | WARN
    reason: str  # plain-English, shown to humans + on receipts
    pattern: Optional[str] = None  # regex (case-insensitive) over the command text
    predicate: Optional[Callable[[str], bool]] = None  # extra structured check

    def hits(self, text: str) -> bool:
        if self.pattern and re.search(self.pattern, text, re.IGNORECASE):
            return True
        if self.predicate and self.predicate(text):
            return True
        return False


@dataclass
class PolicyHit:
    rule: str
    category: str
    severity: str
    reason: str


@dataclass
class PolicyVerdict:
    """Result of checking one action against the catalog."""

    severity: str  # BLOCK | WARN | ALLOW
    hits: List[PolicyHit] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.severity == BLOCK

    def headline(self) -> str:
        if not self.hits:
            return "no policy rule matched"
        h = self.hits[0]
        return f"{h.reason} ({h.rule})"


# --------------------------------------------------------------------------- #
# THE CATALOG. Read it top to bottom — this is the whole safety story.
# Each rule blocks (or flags) one concrete class of dangerous AI action.
# --------------------------------------------------------------------------- #
CATALOG: List[Rule] = [
    # --- destroy the filesystem -------------------------------------------- #
    Rule("recursive-force-delete", "destructive-fs", BLOCK,
         "recursively force-deletes files",
         pattern=r"\brm\s+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r|-r\s+-f|-f\s+-r)\b"
                 r"|\brm\b(?=[^\n]*--recursive)(?=[^\n]*--force)"),
    Rule("powershell-recursive-delete", "destructive-fs", BLOCK,
         "recursively force-deletes via PowerShell",
         pattern=r"\bremove-item\b.*-recurse\b|\bri\b.*-recurse\b.*-force\b"),
    # --- wipe the disk / device -------------------------------------------- #
    Rule("raw-disk-write", "disk-device", BLOCK,
         "writes raw bytes to a disk device (data destruction)",
         pattern=r"\bdd\b[^\n]*\bof=\s*/dev/(sd|nvme|hd|vd|disk)"),
    Rule("redirect-to-device", "disk-device", BLOCK,
         "redirects output straight onto a disk device",
         pattern=r">\s*/dev/(sd|nvme|hd|vd|disk)\w*"),
    Rule("format-filesystem", "disk-device", BLOCK,
         "formats or discards a filesystem/partition",
         pattern=r"\b(mkfs(\.\w+)?|wipefs|blkdiscard|diskpart|format)\b"),
    # --- denial of service ------------------------------------------------- #
    Rule("fork-bomb", "denial-of-service", BLOCK,
         "fork bomb — exhausts process table",
         pattern=r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
    # --- seize permissions on the whole tree ------------------------------- #
    Rule("recursive-root-perms", "privilege", BLOCK,
         "recursively changes permissions/ownership at the root",
         pattern=r"\b(chmod|chown)\b[^\n]*-R[^\n]*\s/(?:\s|$|\*)|\bchmod\b\s+-R?\s*0?777\s+/"),
    # --- exfiltrate secrets ------------------------------------------------ #
    Rule("secret-file-exfil", "exfiltration", BLOCK,
         "uploads a credential/secret file off-box",
         pattern=r"\b(curl|wget|scp|rsync|nc|ncat)\b[^\n]*(id_rsa|id_ed25519|\.ssh/|\.aws/credentials|\.env\b|/etc/shadow|\.pem\b|\.p12\b|secret|password)"),
    Rule("reverse-shell", "remote-exec", BLOCK,
         "opens a reverse shell to a remote host",
         pattern=r"\bnc\b[^\n]*-e\b|\bncat\b[^\n]*-e\b|/dev/tcp/|\bbash\b[^\n]*-i\b[^\n]*>&|\bmkfifo\b[^\n]*\|[^\n]*(sh|bash)\b"),
    Rule("decode-pipe-exec", "remote-exec", BLOCK,
         "decodes obfuscated text straight into a shell",
         pattern=r"\b(base64|xxd|openssl\s+enc)\b[^\n]*\|\s*(sh|bash|zsh|powershell|pwsh)\b"),
    Rule("secret-sweep", "exfiltration", BLOCK,
         "mass-reads secret files via find -exec",
         pattern=r"\bfind\b[^\n]*(\.key|\.pem|id_rsa|id_ed25519|shadow|\.env)[^\n]*-exec[^\n]*\b(cat|cp|scp|nc|tee)\b"),
    Rule("download-pipe-exec", "remote-exec", BLOCK,
         "downloads code and pipes it straight into a shell",
         pattern=r"\b(curl|wget|iwr|invoke-webrequest)\b[^\n]*\|\s*(sh|bash|zsh|powershell|pwsh|iex|python)\b"),
    Rule("encoded-powershell", "remote-exec", BLOCK,
         "runs base64-encoded PowerShell (obfuscation)",
         pattern=r"\bpowershell\b[^\n]*\s-e(nc|ncodedcommand)?\s|\b-encodedcommand\b"),
    # --- read credentials -------------------------------------------------- #
    Rule("read-credential-store", "secret-access", BLOCK,
         "reads a private key / credential store",
         pattern=r"\b(cat|type|less|more|gc|get-content)\b[^\n]*(id_rsa|id_ed25519|\.ssh/|\.aws/credentials|/etc/shadow|\.pem\b)"),
    # --- cover tracks (anti-forensics) ------------------------------------- #
    Rule("clear-history-or-logs", "anti-forensics", BLOCK,
         "erases shell history or system logs",
         pattern=r"\bhistory\s+-c\b|\bunset\s+histfile\b|>\s*/var/log/|\btruncate\b[^\n]*-s\s*0[^\n]*/var/log"),
    # --- power state ------------------------------------------------------- #
    Rule("halt-or-reboot", "availability", BLOCK,
         "shuts down or reboots the host",
         pattern=r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b"),

    # --- WARN (proceed, but flag for review) ------------------------------- #
    Rule("privilege-escalation", "privilege", WARN,
         "runs with elevated privileges (sudo/runas)",
         pattern=r"\bsudo\b|\brunas\b"),
    Rule("package-install", "supply-chain", WARN,
         "installs a package (supply-chain surface)",
         pattern=r"\b(pip|pip3|npm|yarn|pnpm|gem|cargo|go)\s+(install|add|get)\b|\bapt(-get)?\s+install\b"),
    Rule("force-push", "vcs", WARN,
         "force-pushes git history (can erase others' work)",
         pattern=r"\bgit\b[^\n]*\bpush\b[^\n]*(--force\b|-f\b|--force-with-lease\b)"),
]


def _command_text(tool: str, args: dict) -> str:
    a = args or {}
    if tool in _COMMAND_TOOLS:
        return str(a.get("code") or a.get("command") or a.get("script") or "")
    # Non-command tools: scan path-ish args too (e.g. reading a secret file).
    return " ".join(str(a.get(k, "")) for k in ("path", "file", "url", "content", "to"))


def check_command(command: str) -> PolicyVerdict:
    """Check a raw command string against the catalog."""
    hits: List[PolicyHit] = []
    for rule in CATALOG:
        if rule.hits(command):
            hits.append(PolicyHit(rule.name, rule.category, rule.severity, rule.reason))
    severity = BLOCK if any(h.severity == BLOCK for h in hits) else (WARN if hits else "ALLOW")
    # Block hits first so headline() shows the most severe.
    hits.sort(key=lambda h: 0 if h.severity == BLOCK else 1)
    return PolicyVerdict(severity=severity, hits=hits)


def check_action(tool: str, args: Optional[dict] = None) -> PolicyVerdict:
    """Check a structured tool call (the AI-facing entry point)."""
    return check_command(_command_text(tool, args or {}))
