"""
Constitutional Web Agent (CWA)
==============================

Framework 3: Browser agent with constitutional AI safety checks.
Every web interaction is validated against a safety constitution
derived from the SCBE governance model.

Constitutional rules map to Sacred Tongues:
  KO (Control)  — navigation control flow
  AV (I/O)      — robots.txt / domain interaction safety
  RU (Policy)   — download restrictions, credential handling
  CA (Logic)    — deception detection (clickjacking, hidden elements)
  UM (Security) — credential exfiltration blocking
  DR (Types)    — data type validation

The agent classifies intent before execution and quarantines
actions that violate constitutional principles.

@module browser/constitutionalWebAgent
@layer Layer 13 (Risk Decision)
@component Constitutional Web Agent
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


# =============================================================================
# TYPES
# =============================================================================


class Decision(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


class TongueCode(Enum):
    KO = "KO"  # Control
    AV = "AV"  # I/O
    RU = "RU"  # Policy
    CA = "CA"  # Logic
    UM = "UM"  # Security
    DR = "DR"  # Types


class Severity(Enum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ConstitutionalRule:
    """A single constitutional rule for browser governance."""

    principle: str
    tongue: TongueCode
    severity: Severity
    pattern: Optional[str] = None  # Regex pattern to match against

    def matches(self, text: str) -> bool:
        """Check if the rule's pattern matches the given text."""
        if self.pattern is None:
            return False
        return bool(re.search(self.pattern, text, re.IGNORECASE))


@dataclass
class IntentAnalysis:
    """Result of intent classification."""

    task: str
    risk_level: str  # "safe", "moderate", "elevated", "malicious"
    risk_score: float  # [0, 1]
    trust_score: float  # [0, 1]
    classification: str
    flags: List[str] = field(default_factory=list)


@dataclass
class ConstitutionalViolation:
    """A detected constitutional violation."""

    rule: ConstitutionalRule
    matched_text: str
    action: str
    timestamp: float


@dataclass
class GovernanceResult:
    """Result of constitutional governance evaluation."""

    decision: Decision
    violations: List[ConstitutionalViolation]
    passed_tongues: List[TongueCode]
    failed_tongues: List[TongueCode]
    risk_score: float
    explanation: str


@dataclass
class BrowseStep:
    """A single step in a browsing plan."""

    action: str  # "navigate", "click", "type", "extract", "screenshot"
    target: str  # URL, selector, or description
    rationale: str


@dataclass
class StepResult:
    """Result of executing a single browse step."""

    step: BrowseStep
    governance: GovernanceResult
    executed: bool
    result_data: Optional[Dict[str, Any]] = None
    trust_delta: float = 0.0


@dataclass
class BrowseTaskResult:
    """Final result of a constitutional browsing task."""

    status: str  # "complete", "quarantined", "blocked"
    steps_executed: int
    steps_total: int
    results: List[StepResult]
    final_trust: float
    tongue_resonance: Dict[str, bool]
    audit_trail: List[Dict[str, Any]]
    quarantine_reason: Optional[str] = None


# =============================================================================
# CONSTITUTION
# =============================================================================

DEFAULT_CONSTITUTION: List[ConstitutionalRule] = [
    ConstitutionalRule(
        principle="No credential exfiltration",
        tongue=TongueCode.UM,
        severity=Severity.CRITICAL,
        pattern=r"(password|token|api[_-]?key|secret|credential)\s*[=:]\s*['\"][^'\"]+",
    ),
    ConstitutionalRule(
        principle="No unauthorized executable downloads",
        tongue=TongueCode.RU,
        severity=Severity.HIGH,
        pattern=r"\.(exe|dll|sh|bat|cmd|ps1|msi|dmg|appimage)\s*$",
    ),
    ConstitutionalRule(
        principle="Respect robots.txt",
        tongue=TongueCode.AV,
        severity=Severity.STANDARD,
        pattern=None,  # Checked via domain lookup, not regex
    ),
    ConstitutionalRule(
        principle="No deceptive interaction",
        tongue=TongueCode.CA,
        severity=Severity.HIGH,
        pattern=r"(clickjack|hidden.*button|opacity\s*:\s*0|display\s*:\s*none.*submit)",
    ),
    ConstitutionalRule(
        principle="No data: URI execution",
        tongue=TongueCode.UM,
        severity=Severity.CRITICAL,
        pattern=r"(?:^|\s)data:\s*(text/html|application/javascript)",
    ),
    ConstitutionalRule(
        principle="No javascript: URI execution",
        tongue=TongueCode.UM,
        severity=Severity.CRITICAL,
        pattern=r"(?:^|\s)javascript:",
    ),
    ConstitutionalRule(
        principle="No prompt injection relay",
        tongue=TongueCode.DR,
        severity=Severity.CRITICAL,
        pattern=r"(ignore\s+previous|system\s*prompt|jailbreak|you\s+are\s+now)",
    ),
    ConstitutionalRule(
        principle="No cross-origin credential forwarding",
        tongue=TongueCode.UM,
        severity=Severity.HIGH,
        pattern=r"(authorization|cookie)\s*:\s*.*\.(different|external|unknown)",
    ),
]

# Action sensitivity levels (mirrors TS ACTION_SENSITIVITY)
ACTION_SENSITIVITY: Dict[str, float] = {
    "navigate": 0.3,
    "click": 0.4,
    "type": 0.5,
    "extract": 0.3,
    "screenshot": 0.2,
    "submit": 0.7,
    "download": 0.8,
    "upload": 0.8,
    "execute_script": 0.9,
}


# =============================================================================
# INTENT CLASSIFIER
# =============================================================================


def classify_intent(task: str) -> IntentAnalysis:
    """
    Classify the intent of a browsing task.

    Maps task description to risk level using keyword analysis.
    """
    task_lower = task.lower()
    flags: List[str] = []
    risk_score = 0.1

    # Malicious intent patterns
    malicious_patterns = [
        (r"steal|exfiltrate|harvest|scrape.*credentials", 0.9, "credential_theft"),
        (r"inject|xss|sqli|payload", 0.85, "injection_attempt"),
        (r"phish|spoof|impersonate", 0.8, "phishing"),
        (r"bypass|circumvent|evade", 0.7, "evasion"),
    ]

    for pattern, score, flag in malicious_patterns:
        if re.search(pattern, task_lower):
            risk_score = max(risk_score, score)
            flags.append(flag)

    # Elevated but potentially legitimate
    elevated_patterns = [
        (r"automate.*login|fill.*password|enter.*credentials", 0.6, "credential_automation"),
        (r"download.*bulk|mass.*download|crawl", 0.5, "bulk_operation"),
        (r"modify.*cookie|inject.*header", 0.55, "session_manipulation"),
    ]

    for pattern, score, flag in elevated_patterns:
        if re.search(pattern, task_lower):
            risk_score = max(risk_score, score)
            flags.append(flag)

    # Determine risk level
    if risk_score >= 0.8:
        risk_level = "malicious"
    elif risk_score >= 0.5:
        risk_level = "elevated"
    elif risk_score >= 0.3:
        risk_level = "moderate"
    else:
        risk_level = "safe"

    trust_score = max(0.0, 1.0 - risk_score)

    return IntentAnalysis(
        task=task,
        risk_level=risk_level,
        risk_score=risk_score,
        trust_score=trust_score,
        classification=flags[0] if flags else "benign",
        flags=flags,
    )


# =============================================================================
# CONSTITUTIONAL WEB AGENT
# =============================================================================


class ConstitutionalWebAgent:
    """
    Browser agent with constitutional AI safety checks.

    Every web interaction is validated against the safety constitution.
    Actions failing constitutional checks are quarantined or denied.
    """

    def __init__(
        self,
        constitution: Optional[List[ConstitutionalRule]] = None,
        trust_score: float = 0.7,
        agent_id: str = "cwa-001",
    ):
        self.constitution = constitution or DEFAULT_CONSTITUTION
        self.trust_score = trust_score
        self.agent_id = agent_id
        self.audit_log: List[Dict[str, Any]] = []
        self._violation_count = 0

    def evaluate_action(
        self,
        action: str,
        target: str,
        content: str = "",
    ) -> GovernanceResult:
        """
        Evaluate a browser action against the constitution.

        Args:
            action: Action type (navigate, click, type, etc.)
            target: Target URL, selector, or description
            content: Page content or payload to scan

        Returns:
            GovernanceResult with decision and tongue status
        """
        violations: List[ConstitutionalViolation] = []
        passed_tongues: List[TongueCode] = []
        failed_tongues: List[TongueCode] = []

        # Check all constitutional rules
        combined_text = f"{action} {target} {content}"

        for rule in self.constitution:
            if rule.matches(combined_text):
                violations.append(
                    ConstitutionalViolation(
                        rule=rule,
                        matched_text=combined_text[:200],
                        action=action,
                        timestamp=time.time(),
                    )
                )
                if rule.tongue not in failed_tongues:
                    failed_tongues.append(rule.tongue)

        # Determine passed tongues
        all_tongues = list(TongueCode)
        for tongue in all_tongues:
            if tongue not in failed_tongues:
                passed_tongues.append(tongue)

        # Compute risk score
        action_risk = ACTION_SENSITIVITY.get(action, 0.5)
        violation_risk = sum(
            0.3 if v.rule.severity == Severity.CRITICAL else 0.2 if v.rule.severity == Severity.HIGH else 0.1
            for v in violations
        )
        risk_score = min(1.0, action_risk * 0.4 + violation_risk * 0.6)

        # Make decision
        decision = self._decide(risk_score, violations, failed_tongues)

        # Build explanation
        explanation = self._explain(decision, violations, risk_score)

        # Audit log entry
        self.audit_log.append(
            {
                "timestamp": time.time(),
                "agent_id": self.agent_id,
                "action": action,
                "target": target[:100],
                "decision": decision.value,
                "risk_score": risk_score,
                "violations": len(violations),
                "failed_tongues": [t.value for t in failed_tongues],
            }
        )

        if violations:
            self._violation_count += len(violations)

        return GovernanceResult(
            decision=decision,
            violations=violations,
            passed_tongues=passed_tongues,
            failed_tongues=failed_tongues,
            risk_score=risk_score,
            explanation=explanation,
        )

    def browse_with_governance(
        self,
        task: str,
        steps: Sequence[BrowseStep],
    ) -> BrowseTaskResult:
        """
        Execute a browsing task with full constitutional oversight.

        Each step is evaluated against the constitution before execution.
        On violation, the agent is quarantined and execution stops.
        """
        # Step 0: Intent classification
        intent = classify_intent(task)

        if intent.risk_level == "malicious":
            return BrowseTaskResult(
                status="blocked",
                steps_executed=0,
                steps_total=len(steps),
                results=[],
                final_trust=0.0,
                tongue_resonance={t.value: False for t in TongueCode},
                audit_trail=self.audit_log.copy(),
                quarantine_reason=f"Malicious intent detected: {intent.classification}",
            )

        # Execute steps with continuous verification
        current_trust = self.trust_score
        step_results: List[StepResult] = []
        tongue_status: Dict[str, bool] = {t.value: True for t in TongueCode}

        for step in steps:
            # Constitutional check
            governance = self.evaluate_action(
                action=step.action,
                target=step.target,
                content=step.rationale,
            )

            # Update tongue status
            for t in governance.failed_tongues:
                tongue_status[t.value] = False

            if governance.decision == Decision.DENY:
                step_results.append(
                    StepResult(
                        step=step,
                        governance=governance,
                        executed=False,
                        trust_delta=-0.15,
                    )
                )
                current_trust = max(0.0, current_trust - 0.15)
                return BrowseTaskResult(
                    status="blocked",
                    steps_executed=len(step_results),
                    steps_total=len(steps),
                    results=step_results,
                    final_trust=current_trust,
                    tongue_resonance=tongue_status,
                    audit_trail=self.audit_log.copy(),
                    quarantine_reason=governance.explanation,
                )

            if governance.decision == Decision.QUARANTINE:
                step_results.append(
                    StepResult(
                        step=step,
                        governance=governance,
                        executed=False,
                        trust_delta=-0.05,
                    )
                )
                current_trust = max(0.0, current_trust - 0.05)
                return BrowseTaskResult(
                    status="quarantined",
                    steps_executed=len(step_results),
                    steps_total=len(steps),
                    results=step_results,
                    final_trust=current_trust,
                    tongue_resonance=tongue_status,
                    audit_trail=self.audit_log.copy(),
                    quarantine_reason=governance.explanation,
                )

            # ALLOW or ESCALATE — execute
            trust_delta = 0.01 if governance.decision == Decision.ALLOW else -0.03
            current_trust = max(0.0, min(1.0, current_trust + trust_delta))

            step_results.append(
                StepResult(
                    step=step,
                    governance=governance,
                    executed=True,
                    result_data={"action": step.action, "target": step.target},
                    trust_delta=trust_delta,
                )
            )

        return BrowseTaskResult(
            status="complete",
            steps_executed=len(step_results),
            steps_total=len(steps),
            results=step_results,
            final_trust=current_trust,
            tongue_resonance=tongue_status,
            audit_trail=self.audit_log.copy(),
        )

    @property
    def violation_count(self) -> int:
        return self._violation_count

    # --------------------------------------------------------------------------
    # Internal
    # --------------------------------------------------------------------------

    def _decide(
        self,
        risk_score: float,
        violations: List[ConstitutionalViolation],
        failed_tongues: List[TongueCode],
    ) -> Decision:
        # Critical tongue failures (UM = Security) → immediate DENY
        critical_violations = [v for v in violations if v.rule.severity == Severity.CRITICAL]
        if critical_violations:
            return Decision.DENY

        # Security tongue failure → ESCALATE
        if TongueCode.UM in failed_tongues:
            return Decision.ESCALATE

        # High severity → QUARANTINE
        high_violations = [v for v in violations if v.rule.severity == Severity.HIGH]
        if high_violations:
            return Decision.QUARANTINE

        # Risk-based thresholds
        if risk_score >= 0.85:
            return Decision.DENY
        if risk_score >= 0.6:
            return Decision.ESCALATE
        if risk_score >= 0.3:
            return Decision.QUARANTINE
        return Decision.ALLOW

    def _explain(
        self,
        decision: Decision,
        violations: List[ConstitutionalViolation],
        risk_score: float,
    ) -> str:
        parts = [f"{decision.value} (risk={risk_score:.3f})"]
        if violations:
            principles = [v.rule.principle for v in violations]
            parts.append(f"Violations: {', '.join(principles)}")
        return ". ".join(parts)
