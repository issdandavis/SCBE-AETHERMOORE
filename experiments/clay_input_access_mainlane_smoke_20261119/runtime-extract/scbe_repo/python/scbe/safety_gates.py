"""safety_gates: two tiers of safety gate -- strict HOME protections, and PRODUCT push controls on top.

Issac's distinction: this machine is his HOME, and home is a tool too -- so the HOME tier is the STRICTEST
on his own security: never delete (an AI misfire wiped his drive once), never leak his private data, detect
threats, keep memory local. A PRODUCT we ship inherits ALL of that and ADDS what a customer's deploy needs:
user-authorized pushes and MID-PUSH gates (canary -> bake -> verify -> promote, each gated, with a kill
switch + rollback) -- the change-control the agent-error-recovery doctrine says you must never skip.

  home = HomeGate();              home.screen(Action("delete", "report.txt"))      -> DENY (never delete)
  prod = ProductGate(policy);     prod.screen(Action("push", "deploy:v2"))         -> REVIEW (needs auth)
  PushSession(prod, checks).run()  # staged, gated, kill-switchable, auto-rollback
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List

ALLOW, DENY, REVIEW = "allow", "deny", "review"


@dataclass
class Action:
    kind: str  # read | write | delete | exec | network | push | memory
    target: str  # path / command / url / artifact
    payload: str = ""  # command text / data being sent
    dest: str = "local"  # local | external


@dataclass
class Decision:
    verdict: str  # allow | deny | review
    reason: str
    tier: str  # home | product

    @property
    def ok(self) -> bool:
        return self.verdict == ALLOW


# --- destructive detection: verb AND verb-less (the gap a verb-only regex misses) ---
_DESTRUCTIVE = re.compile(
    r"""(?ix)
      \brm\s+-[rf]                       # rm -rf / -r / -f
    | \bdel\s                            # del
    | \bRemove-Item\b | \brmdir\b | \bunlink\b
    | \bshutil\.rmtree\b | \bos\.(remove|unlink|rmdir)\b
    | \bDROP\s+(TABLE|DATABASE)\b | \bTRUNCATE\b | \bDELETE\s+FROM\b
    | \bformat\b | \bmkfs\b | \bdd\s+.*\bof= | \bdiskpart\b
    | \.Delete\(\)  | \bClear-Content\b | \bSet-Content\b   # overwrite-in-place
    | (^|\s)>\s*\S                        # verb-LESS truncation/overwrite redirection: `> file`
    | :\s*>\s*\S                          # `: > file`
    """,
)

# private/local data that must never leave to an external destination
_PRIVATE = re.compile(
    r"""(?ix)
      issdandavis\d*@\w+\.\w+             # his email
    | C:\\Users\\issda                    # his home path
    | \b(sk|ghp|pk|AKIA)[-_]?[A-Za-z0-9]{12,}   # api keys / tokens
    | -----BEGIN\s+\w+\s+PRIVATE\s+KEY    # private keys
    | \bpassword\s*[:=]\s*\S              # inline credentials
    """,
)

# threat patterns (prompt-injection / exfil scaffolding)
_THREAT = re.compile(
    r"(?i)(ignore (all )?previous instructions|exfiltrat|reverse shell|/proc/self/environ|curl\s+\S+\s*\|\s*sh)"
)


def is_destructive(text: str) -> bool:
    return bool(_DESTRUCTIVE.search(text or ""))


def leaks_private(text: str) -> bool:
    return bool(_PRIVATE.search(text or ""))


class HomeGate:
    """Strictest tier -- protect Issac's machine + data. Default-deny on anything destructive or leaking."""

    tier = "home"

    def screen(self, a: Action) -> Decision:
        blob = "%s %s" % (a.target, a.payload)
        # 1. NEVER delete -- absolute (an AI misfire wiped his drive once); verb AND verb-less.
        if a.kind == "delete" or is_destructive(blob):
            return Decision(DENY, "destructive op blocked (never-delete absolute)", self.tier)
        # 2. NO leak of his private/local data to an external destination.
        if a.dest == "external" and leaks_private(a.payload):
            return Decision(DENY, "would leak private/local data to an external destination", self.tier)
        # 3. threat patterns -> hold for review, don't silently pass.
        if _THREAT.search(blob):
            return Decision(REVIEW, "threat pattern detected", self.tier)
        # 4. memory stays LOCAL.
        if a.kind == "memory" and a.dest != "local":
            return Decision(DENY, "memory must stay local (no external sync)", self.tier)
        return Decision(ALLOW, "ok", self.tier)


@dataclass
class PushPolicy:
    """User-styled push control: a push is authorized only with an explicit token the USER holds."""

    approved_tokens: set = field(default_factory=set)

    def authorize(self, token: str) -> None:
        self.approved_tokens.add(token)

    def authorized(self, a: Action) -> bool:
        return a.payload in self.approved_tokens  # the push carries its approval token


class ProductGate(HomeGate):
    """Inherits ALL home protections, then adds the deploy-time controls a shipped product needs."""

    tier = "product"

    def __init__(self, policy: PushPolicy):
        self.policy = policy

    def screen(self, a: Action) -> Decision:
        base = HomeGate.screen(self, a)
        if base.verdict == DENY:  # home protections are never relaxed for a product
            return base
        if a.kind == "push" and not self.policy.authorized(a):
            return Decision(REVIEW, "push requires explicit user authorization (no auto-merge)", self.tier)
        return Decision(base.verdict, base.reason, self.tier)


@dataclass
class PushSession:
    """A staged, gated push with mid-push gates + a kill switch + auto-rollback. Each stage must pass its
    check before the next; any failure or a kill rolls back. The 'never just push it' control."""

    gate: ProductGate
    action: Action
    checks: Dict[str, Callable[[], bool]]  # stage -> check
    rollback: Callable[[], None] = lambda: None
    stages: List[str] = field(default_factory=lambda: ["canary", "bake", "verify", "promote"])
    _killed: bool = False
    log: List[str] = field(default_factory=list)

    def kill(self) -> None:
        self._killed = True

    def run(self) -> Decision:
        d = self.gate.screen(self.action)
        if d.verdict != ALLOW:
            self.log.append("gate: %s (%s)" % (d.verdict, d.reason))
            return d
        for stage in self.stages:
            if self._killed:
                self.rollback()
                self.log.append("KILLED at %s -> rolled back" % stage)
                return Decision(DENY, "kill switch -> rolled back at %s" % stage, "product")
            ok = self.checks.get(stage, lambda: True)()
            self.log.append("%s: %s" % (stage, "pass" if ok else "FAIL"))
            if not ok:
                self.rollback()
                return Decision(DENY, "mid-push gate '%s' failed -> rolled back" % stage, "product")
        return Decision(ALLOW, "all mid-push gates passed -> promoted", "product")
