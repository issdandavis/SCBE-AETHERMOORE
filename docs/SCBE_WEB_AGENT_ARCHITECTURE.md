# SCBE Web Agent -- Architecture Document

**Version:** 1.0.0
**Date:** 2026-02-21
**Patent:** USPTO #63/961,403 (SCBE-AETHERMOORE 14-Layer AI Governance Framework)
**Status:** Design Specification

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [WebPollyPad -- Browser Actuator Layer](#2-webpollypad----browser-actuator-layer)
3. [SemanticAntivirus -- Content Scanning and Governance Filtering](#3-semanticantivirus----content-scanning-and-governance-filtering)
4. [AgentOrchestrator -- Long-Running Task Management](#4-agentorchestrator----long-running-task-management)
5. [NavigationEngine -- PLAN + SENSE + STEER + DECIDE Integration](#5-navigationengine----plan--sense--steer--decide-integration)
6. [TaskAPI -- REST and WebSocket Interface](#6-taskapi----rest-and-websocket-interface)
7. [StateManager -- Persistent Agent State](#7-statemanager----persistent-agent-state)
8. [FederatedDeployment -- Nursery Training and Model Deployment](#8-federateddeployment----nursery-training-and-model-deployment)
9. [SCBE Layer Integration -- 14-Layer Mapping](#9-scbe-layer-integration----14-layer-mapping)
10. [Data Flow -- End-to-End Pipeline](#10-data-flow----end-to-end-pipeline)

---

## 1. System Overview

### 1.1 Architecture Diagram

```
                            +---------------------------+
                            |        TaskAPI            |
                            |  REST / WebSocket / gRPC  |
                            +------+----------+---------+
                                   |          |
                          submit_task    stream_status
                                   |          |
                            +------v----------v---------+
                            |    AgentOrchestrator      |
                            |  Session lifecycle        |
                            |  Checkpoint / Recovery    |
                            |  Multi-agent dispatch     |
                            +------+----------+---------+
                                   |          |
                       +-----------+          +-----------+
                       |                                  |
                +------v--------+              +----------v--------+
                | StateManager  |              | NavigationEngine  |
                | Redis/Postgres|              |                   |
                | Checkpoint DB |              | +------+ +------+ |
                +---------------+              | | PLAN | | SENSE| |
                                               | +------+ +------+ |
                                               | +------+ +-------+|
                                               | |STEER | |DECIDE ||
                                               | +------+ +-------+|
                                               +---------+---------+
                                                         |
                                              +----------v---------+
                                              |    WebPollyPad     |
                                              |  Browser Actuator  |
                                              |  Playwright/CDP    |
                                              +----+----------+----+
                                                   |          |
                                          execute_action  observe_page
                                                   |          |
                                              +----v----------v----+
                                              |  SemanticAntivirus |
                                              |  Content Scanner   |
                                              |  Injection Detect  |
                                              |  14-Layer Gate     |
                                              +----+----------+----+
                                                   |          |
                                           governance_verdict  |
                                                   |          |
                                    +--------------+   +------v--------+
                                    | GovernanceAdapter |  Browser      |
                                    | H(d,pd) Tracker  |  (Chromium)   |
                                    | 9D Manifold      |               |
                                    +------------------+  +------------+

    +------------------------------------------------------------------+
    |                    FederatedDeployment                            |
    |  +----------+  +----------+  +----------+    +-----------------+ |
    |  | Nursery  |  | Nursery  |  | Nursery  |    | BFT Consensus   | |
    |  | Alpha    |  | Beta     |  | Gamma    |--->| (COORDINATE)    | |
    |  | (CSTM)   |  | (CSTM)   |  | (CSTM)   |    | Model Merge     | |
    |  +----------+  +----------+  +----------+    +-----------------+ |
    |                                                      |           |
    |                                              +-------v---------+ |
    |                                              | HuggingFace Hub | |
    |                                              | Weights + Embeds| |
    |                                              | Inference API   | |
    |                                              +-----------------+ |
    +------------------------------------------------------------------+
```

### 1.2 Design Principles

1. **Every action is governed.** No browser action executes without passing through the 14-layer governance stack and the Hamiltonian safety function H(d, pd) = 1 / (1 + d + 2*pd).

2. **Concept blocks are the atoms.** The five existing concept blocks (DECIDE, PLAN, SENSE, STEER, COORDINATE) are composed into a navigation loop; they are never bypassed or reimplemented.

3. **Polly Pads are the only actuator surface.** All browser actions flow through WebPollyPad instances. Each pad type (NavigatePad, ClickPad, TypePad, ScrollPad, WaitPad, RecoveryPad) translates a governance-approved decision into exactly one browser primitive.

4. **Sacred Tongue domain separation is enforced.** Each web domain category is mapped to a Sacred Tongue (KO, AV, RU, CA, UM, DR). Cross-tongue operations require elevated governance review.

5. **Personality drives policy.** Web agents inherit their navigation personality from CSTM training. A cautious agent navigates differently from an exploratory one. This is not cosmetic; it determines risk tolerance, retry strategy, and escalation thresholds.

6. **Federated learning preserves diversity.** Multiple nurseries train agents independently. Model merges require BFT consensus. No single nursery can dominate the population.

### 1.3 Sacred Tongue Domain Mapping

| Tongue | Domain | Web Agent Role |
|--------|--------|---------------|
| **KO** (Kothric) | Identity / Authentication | Login flows, credential handling, session tokens |
| **AV** (Avalonic) | Structural / Navigation | URL traversal, page structure, DOM tree |
| **RU** (Runnic) | Temporal / Scheduling | Timeout management, retry cadence, session lifespan |
| **CA** (Caelic) | Social / Communication | Form submission, messaging, email composition |
| **UM** (Umbric) | Analytical / Data | Data extraction, table parsing, content summarization |
| **DR** (Draumric) | Protective / Safety | Antivirus scanning, injection detection, governance gates |

---

## 2. WebPollyPad -- Browser Actuator Layer

### 2.1 Responsibility

WebPollyPad is the actuator surface that translates governance-approved decisions into concrete browser actions. Every interaction with the browser -- clicking a button, typing into a field, scrolling, navigating to a URL -- is mediated by a specialized PollyPad subclass. Pads enforce pre-action governance checks, post-action observation, and recovery when actions fail.

The name "Polly Pad" comes from the SCBE concept of actuator surfaces that translate abstract governance decisions into real-world effects. In the web agent context, the "real world" is the browser viewport.

### 2.2 Key Classes

```python
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PadStatus(Enum):
    """Outcome of a pad actuation."""
    SUCCESS = "success"          # Action completed
    FAILED = "failed"            # Action failed (DOM changed, element gone)
    BLOCKED = "blocked"          # Governance denied the action
    TIMEOUT = "timeout"          # Action timed out
    RECOVERY = "recovery"        # Pad is in recovery mode


@dataclass
class PadResult:
    """Result of a single pad actuation.

    Every pad returns one of these, regardless of success or failure.
    The observation field captures the browser state after the action
    (or attempted action), enabling the SENSE block to update its
    Kalman filter.
    """
    status: PadStatus
    action_type: str                              # "click", "type", "navigate", etc.
    target_selector: str                          # CSS selector or URL
    observation: PageObservation                   # Post-action page state
    governance_verdict: GovernanceCheckResult       # Pre-action governance check
    duration_ms: float = 0.0                       # Wall-clock time for the action
    error_message: str = ""                        # Non-empty on failure
    retry_count: int = 0                           # How many retries were attempted
    sacred_tongue: str = "AV"                      # Which tongue domain this falls under


@dataclass
class PageObservation:
    """Structured observation of the current browser state.

    This is the primary input to the SENSE block. It captures
    everything the agent needs to understand the current page
    without re-reading raw DOM.
    """
    url: str
    title: str
    visible_text_hash: str                         # SHA-256 of visible text (change detection)
    dom_element_count: int
    interactive_elements: List[InteractiveElement]  # Clickable/typeable elements
    page_load_time_ms: float
    screenshot_embedding: Optional[List[float]]     # Vision model embedding (384D)
    content_safety_score: float                     # From SemanticAntivirus [0, 1]
    detected_language: str
    forms_present: List[FormDescriptor]
    navigation_links: List[LinkDescriptor]
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class InteractiveElement:
    """A single interactive element on the page."""
    selector: str                                  # Unique CSS selector
    tag: str                                       # "button", "input", "a", "select"
    text: str                                      # Visible text / aria-label
    element_type: str                              # "submit", "text", "password", "link"
    is_visible: bool
    bounding_box: Tuple[float, float, float, float]  # (x, y, width, height)
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LinkDescriptor:
    """A hyperlink extracted from the page."""
    href: str
    text: str
    selector: str
    is_external: bool
    is_same_domain: bool


@dataclass(frozen=True)
class FormDescriptor:
    """A form on the page with its fields."""
    action: str
    method: str
    fields: List[InteractiveElement]
    selector: str


@dataclass
class GovernanceCheckResult:
    """Result of pre-action governance evaluation.

    Every pad action is checked against the 14-layer governance
    stack before execution. This captures the decision and the
    Hamiltonian safety score at the moment of the check.
    """
    decision: str                                  # "ALLOW", "DENY", "QUARANTINE", "ESCALATE"
    hamiltonian_score: float                        # H(d, pd) at check time
    safety_tongue: str                              # Which sacred tongue evaluated
    layer_verdicts: Dict[int, str]                  # Per-layer decisions {1: "ALLOW", ...}
    content_threat_score: float                     # SemanticAntivirus threat [0, 1]
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


class WebPollyPad(ABC):
    """Abstract base class for all browser actuator pads.

    Lifecycle:
        1. pre_check(context)    -- Governance gate (ALLOW/DENY/QUARANTINE/ESCALATE)
        2. execute(context)      -- Perform the browser action via Playwright
        3. post_observe(context) -- Capture the new page state
        4. on_failure(context)   -- Recovery logic when execution fails

    Every pad subclass implements _do_execute() for its specific action.
    The base class handles governance checks, telemetry, and retry logic.
    """

    def __init__(
        self,
        pad_name: str,
        sacred_tongue: str = "AV",
        max_retries: int = 3,
        timeout_ms: float = 30_000,
    ) -> None: ...

    def actuate(
        self,
        context: PadContext,
    ) -> PadResult:
        """Full actuation cycle: pre_check -> execute -> post_observe.

        This is the only public method. Callers never invoke
        execute() directly. Governance is non-optional.

        Args:
            context: Contains the browser page handle, target selector,
                     current agent state, and governance engine reference.

        Returns:
            PadResult with the action outcome and fresh observation.
        """
        ...

    @abstractmethod
    def _do_execute(self, context: PadContext) -> bool:
        """Subclass hook: perform the actual browser action.

        Returns True on success, False on failure.
        """
        ...

    @abstractmethod
    def _do_observe(self, context: PadContext) -> PageObservation:
        """Subclass hook: capture page state after action."""
        ...


@dataclass
class PadContext:
    """Runtime context passed to every pad actuation.

    Carries the browser page handle, the agent's current 21D personality
    vector, the governance engine, and the target of the action.
    """
    page: Any                                      # playwright.async_api.Page
    target_selector: str                           # CSS selector or URL
    agent_personality: List[float]                  # 21D personality vector
    agent_stats: Dict[str, float]                   # Current agent stats
    governance_engine: Any                          # Reference to GovernanceAdapter
    hamiltonian_tracker: Any                        # Reference to HamiltonianTracker
    action_params: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    step_number: int = 0


class NavigatePad(WebPollyPad):
    """Navigate to a URL.

    Sacred tongue: AV (structural/navigation).
    Governance: URL is checked against blocklist, content policy,
    and domain classification before navigation begins.

    The PLAN block's A* output provides the target URL.
    URLGraphAdapter.neighbours() feeds link_extractor.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute page.goto(url) with timeout."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Full page observation after navigation."""
        ...


class ClickPad(WebPollyPad):
    """Click an interactive element.

    Sacred tongue: AV (structural).
    Governance: Element text, surrounding context, and action intent
    are evaluated. Clicks on "Delete All", "Confirm Purchase", etc.
    require elevated safety score.

    The DECIDE block's behaviour tree selects which element to click.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute element.click() with retries."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Observe state after click (may trigger navigation)."""
        ...


class TypePad(WebPollyPad):
    """Type text into an input field.

    Sacred tongue: CA (social/communication) for message fields,
    KO (identity) for credential fields.
    Governance: Text content is scanned for sensitive data leakage.
    Credential fields trigger KO tongue with STRICT modality mask.

    The DECIDE block determines what text to type based on task
    requirements and current form context.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute element.fill() or element.type()."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Observe field state after typing."""
        ...


class ScrollPad(WebPollyPad):
    """Scroll the page viewport.

    Sacred tongue: AV (structural).
    Governance: Scroll actions are low-risk but tracked for
    infinite-scroll traps and content loading attacks.

    The STEER block's PID controller governs scroll velocity
    based on content density.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute page.mouse.wheel() or element.scroll_into_view()."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Observe newly visible content after scroll."""
        ...


class WaitPad(WebPollyPad):
    """Explicit wait for a condition.

    Sacred tongue: RU (temporal/scheduling).
    Governance: Wait duration is bounded by the RU tongue's
    temporal budget. Unbounded waits are denied.

    The STEER block's integral term detects when the agent
    has been waiting too long and triggers recovery.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute page.wait_for_selector() or asyncio.sleep()."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Observe page state after wait completes or times out."""
        ...


class RecoveryPad(WebPollyPad):
    """Recovery actions when the agent is stuck.

    Sacred tongue: DR (protective/safety).
    This pad is activated by the NavigationEngine when the
    STEER block detects persistent error or the DECIDE block's
    behaviour tree reaches a failure leaf.

    Recovery strategies (selected by DECIDE):
        1. Browser back navigation
        2. Return to known-good URL checkpoint
        3. Clear cookies/state and restart flow
        4. Escalate to human operator

    The Hamiltonian safety score determines which recovery
    strategy is permitted. Lower H -> more conservative recovery.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute recovery action based on strategy."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Observe state after recovery attempt."""
        ...


class ExtractPad(WebPollyPad):
    """Extract structured data from the page.

    Sacred tongue: UM (analytical/data).
    Governance: Extracted data is scanned for PII, credentials,
    and sensitive content. Extraction patterns are validated
    against the task's declared data scope.

    The SENSE block's Kalman filter provides confidence estimates
    on extracted values.
    """

    def _do_execute(self, context: PadContext) -> bool:
        """Execute element.text_content() or structured extraction."""
        ...

    def _do_observe(self, context: PadContext) -> PageObservation:
        """Observe and return extracted data in observation."""
        ...
```

### 2.3 Connection to Existing Concept Blocks

| Pad | Primary Concept Block | Relationship |
|-----|----------------------|-------------|
| NavigatePad | PLAN (PlanBlock) | PLAN's A* path output provides the target URL. URLGraphAdapter feeds the link graph. |
| ClickPad | DECIDE (DecideBlock) | DECIDE's behaviour tree selects which element to click from the interactive elements list. |
| TypePad | DECIDE (DecideBlock) | DECIDE determines text content; STEER modulates typing cadence. |
| ScrollPad | STEER (SteerBlock) | STEER's PID controller governs scroll velocity. Error signal = (target_content_visible - current). |
| WaitPad | STEER (SteerBlock) | STEER's integral term detects excessive wait times. RU tongue enforces temporal budget. |
| RecoveryPad | DECIDE + STEER | DECIDE selects recovery strategy; STEER's accumulated error triggers recovery activation. |
| ExtractPad | SENSE (SenseBlock) | SENSE's Kalman filter provides confidence on extracted data quality. |

### 2.4 Hamiltonian Safety Function Usage

Before every pad actuation, the governance check computes H(d, pd):

- **d** = cosine distance of the agent's 21D personality vector from the safety centroid [0.5]^21
- **pd** = proportion of recent actions tagged as unsafe (cross-origin navigation, credential entry, irreversible actions)

**Actuation thresholds by H score:**

| H(d, pd) Range | Permitted Actions |
|----------------|------------------|
| [0.8, 1.0] | All pads, including TypePad on credential fields |
| [0.6, 0.8) | All pads except credential entry; elevated logging |
| [0.4, 0.6) | NavigatePad (same-domain only), ClickPad, ScrollPad, ExtractPad |
| [0.2, 0.4) | ScrollPad, ExtractPad, WaitPad only; RecoveryPad activated |
| [0.0, 0.2) | RecoveryPad only; all other pads blocked; escalation to human |

---

## 3. SemanticAntivirus -- Content Scanning and Governance Filtering

### 3.1 Responsibility

SemanticAntivirus is the defensive layer that evaluates every piece of web content the agent encounters and every action the agent considers taking. It operates as a mandatory pre-filter before any content enters the NavigationEngine and as a mandatory gate before any action passes to a WebPollyPad.

The antivirus operates on three levels:
1. **Content scanning** -- Evaluate page text, DOM structure, and visual content against safety policies.
2. **Prompt injection detection** -- Detect adversarial text that attempts to alter agent behavior.
3. **Action governance** -- Evaluate proposed actions against the 14-layer governance stack.

### 3.2 Key Classes

```python
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


class ThreatCategory(Enum):
    """Categories of web content threats."""
    PROMPT_INJECTION = "prompt_injection"       # Text attempting to alter agent instructions
    MALICIOUS_REDIRECT = "malicious_redirect"   # URL leading to known-bad destination
    CREDENTIAL_PHISHING = "credential_phishing" # Fake login form harvesting credentials
    DATA_EXFILTRATION = "data_exfiltration"     # Page attempting to extract agent data
    INFINITE_LOOP_TRAP = "infinite_loop_trap"   # Page structure designed to trap crawlers
    UNSAFE_DOWNLOAD = "unsafe_download"          # Auto-download of executables/scripts
    DECEPTIVE_UI = "deceptive_ui"               # Dark patterns, hidden elements
    CONTENT_POLICY = "content_policy"           # Content violating safety policies
    DOM_MANIPULATION = "dom_manipulation"        # Dynamic DOM changes that alter action targets
    TIMING_ATTACK = "timing_attack"             # Deliberate delays to waste agent resources


@dataclass
class ThreatSignal:
    """A single threat detected in page content or proposed action.

    Each signal has a category, confidence, and the evidence that
    triggered detection. Signals are aggregated into a ThreatReport.
    """
    category: ThreatCategory
    confidence: float                              # [0.0, 1.0]
    evidence: str                                  # The triggering text or pattern
    source_selector: str                           # Where on the page this was found
    sacred_tongue: str                             # Which tongue domain is relevant
    layer_triggered: int                           # Which SCBE layer flagged this


@dataclass
class ThreatReport:
    """Aggregated threat assessment for a page or action.

    The combined_threat_score is the weighted maximum across all
    signals, not a simple average, because a single critical threat
    should dominate.
    """
    signals: List[ThreatSignal]
    combined_threat_score: float                    # [0.0, 1.0]
    governance_decision: str                        # "ALLOW", "DENY", "QUARANTINE", "ESCALATE"
    hamiltonian_at_scan: float                      # H(d, pd) when scan was performed
    scanned_url: str
    scan_duration_ms: float
    prompt_injection_detected: bool
    content_policy_violations: List[str]
    timestamp: float = field(default_factory=time.time)

    @property
    def is_safe(self) -> bool:
        """True if governance decision is ALLOW and no injection detected."""
        return self.governance_decision == "ALLOW" and not self.prompt_injection_detected


class ContentScanner:
    """Scans page content against safety policies and threat signatures.

    Uses a layered scanning approach:
        1. Pattern matching (fast, regex-based, catches known attacks)
        2. Embedding similarity (medium, compares content embedding to
           known-bad embeddings)
        3. Governance evaluation (full 14-layer stack via GovernanceAdapter)

    Connection to SCBE:
        - Layer 3 (spectral analysis): Content frequency analysis
        - Layer 5 (commitment hashing): Content hash for change detection
        - Layer 10 (detection): Anomaly detection on page structure

    Args:
        injection_patterns: Compiled regex patterns for prompt injection.
        malicious_url_hashes: Set of SHA-256 hashes of known-bad URLs.
        content_embedding_model: Model for generating content embeddings (384D).
        threat_embedding_index: FAISS/Annoy index of known-threat embeddings.
        policy_rules: Dict mapping content categories to allowed/blocked status.
    """

    def __init__(
        self,
        injection_patterns: Optional[List[re.Pattern]] = None,
        malicious_url_hashes: Optional[Set[str]] = None,
        content_embedding_model: Optional[Any] = None,
        threat_embedding_index: Optional[Any] = None,
        policy_rules: Optional[Dict[str, str]] = None,
    ) -> None: ...

    def scan_page_content(
        self,
        url: str,
        visible_text: str,
        dom_structure: Dict[str, Any],
        page_embedding: Optional[List[float]] = None,
    ) -> ThreatReport:
        """Full content scan of a loaded page.

        Pipeline:
            1. URL hash check against known-bad set
            2. Regex scan of visible_text for injection patterns
            3. DOM structure analysis (hidden iframes, redirect scripts)
            4. Content embedding similarity to threat index
            5. Governance evaluation via grand_unified.governance_9d()

        Returns:
            ThreatReport with all detected signals and final decision.
        """
        ...

    def scan_action_intent(
        self,
        action_type: str,
        target_selector: str,
        target_text: str,
        surrounding_context: str,
        agent_personality: List[float],
    ) -> ThreatReport:
        """Scan a proposed action before execution.

        Evaluates whether the action target is deceptive (e.g., a
        button that says "Cancel" but actually submits a form) and
        whether the action is consistent with the agent's task.

        Connection to SCBE:
            - Layer 7 (decision routing): Action consistency check
            - Layer 8 (Hamiltonian regulation): Energy cost of action
            - Layer 13 (risk pipeline): GovernanceAdapter.evaluate_governance()

        Returns:
            ThreatReport with governance decision for this action.
        """
        ...


class PromptInjectionDetector:
    """Specialized detector for prompt injection attacks in web content.

    Web pages may contain adversarial text designed to override the
    agent's instructions. This detector uses multiple strategies:

    1. **Instruction pattern matching** -- Detects phrases like
       "ignore previous instructions", "you are now", "new system prompt".
    2. **Encoding detection** -- Catches base64, rot13, unicode tricks
       used to obfuscate injections.
    3. **Semantic anomaly** -- Compares page content embedding to
       expected content distribution for the domain. A cooking recipe
       page containing system prompts is anomalous.
    4. **Delimiter analysis** -- Detects attempts to break out of
       content boundaries using markdown, XML tags, or code blocks.

    Connection to SCBE:
        - Layer 5 (commitment hashing): Injection text fails hash verification
        - Layer 10 (detection): Anomaly score from content distribution
        - Layer 12 (polyglot coordination): Cross-language injection detection

    Args:
        sensitivity: Detection sensitivity [0.0, 1.0]. Higher = more false positives.
        language_models: Dict of language-specific detection models (keyed by tongue).
    """

    def __init__(
        self,
        sensitivity: float = 0.8,
        language_models: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    def detect(
        self,
        text: str,
        context: str = "",
        expected_domain: str = "",
    ) -> Tuple[bool, float, List[str]]:
        """Detect prompt injection in text.

        Args:
            text: The text to scan.
            context: Surrounding page context for semantic comparison.
            expected_domain: Expected content domain (e.g., "ecommerce", "docs").

        Returns:
            Tuple of (is_injection, confidence, evidence_list).
        """
        ...


class GovernanceGate:
    """Mandatory governance gate for all content and actions.

    Wraps the existing governance_adapter.evaluate_governance() and
    grand_unified.governance_9d() functions, providing a unified
    interface for the web agent.

    The gate maintains:
        - An AsymmetryTracker for detecting persistent anomalies
        - A HamiltonianTracker for tracking H(d, pd) over time
        - A ManifoldController for geometric state validation

    Connection to SCBE:
        - Uses all 14 layers through evaluate_governance()
        - Tracks the 9D state vector through governance_9d()
        - Enforces Snap Protocol through ManifoldController

    The gate is the ONLY path by which content and actions receive
    governance approval. There is no bypass.
    """

    def __init__(
        self,
        asymmetry_tracker: Any,                    # AsymmetryTracker from governance_adapter
        hamiltonian_tracker: Any,                  # HamiltonianTracker from telemetry_bridge
        manifold_controller: Any,                  # ManifoldController from grand_unified
        quarantine_threshold: float = 0.3,
        deny_threshold: float = 0.85,
    ) -> None: ...

    def evaluate_content(
        self,
        content_embedding: List[float],
        page_url: str,
        agent_state: List[float],
    ) -> GovernanceCheckResult:
        """Evaluate page content through the full governance stack.

        Maps the content + agent state into the 9D governance vector
        and evaluates through governance_9d(). Also runs the 21D
        governance_adapter pipeline for mirror-asymmetry detection.

        Returns:
            GovernanceCheckResult with per-layer verdicts.
        """
        ...

    def evaluate_action(
        self,
        action_type: str,
        target_info: Dict[str, Any],
        agent_state: List[float],
        threat_report: ThreatReport,
    ) -> GovernanceCheckResult:
        """Evaluate a proposed action through governance.

        The action's Hamiltonian cost is computed as:
            H_cost = base_cost(action_type) * (1 + threat_report.combined_threat_score)

        This cost is fed into the STEER block as an energy term.
        If the accumulated energy exceeds the Hamiltonian budget,
        the action is denied.

        Returns:
            GovernanceCheckResult with the final ALLOW/DENY decision.
        """
        ...
```

### 3.3 Connection to Existing Concept Blocks

- **SENSE (SenseBlock):** Content scan results feed into the SENSE block's Kalman filter as measurement inputs. The "uncertainty" output from SENSE determines how much to trust the content scan (noisy scans on JavaScript-heavy pages have higher measurement variance).
- **DECIDE (DecideBlock):** Threat reports are written to the behaviour tree's Blackboard. The tree includes Condition nodes that check `bb.get("threat_score") < threshold`.
- **COORDINATE (CoordinateBlock):** When threat assessment is ambiguous (0.3 < combined_score < 0.6), multiple scanning strategies "vote" through BFT consensus. Requires 2f+1 agreement to proceed.

### 3.4 Hamiltonian Safety Function Usage

The SemanticAntivirus continuously updates H(d, pd) where:
- **d** remains the cosine distance of the agent's personality from the safety centroid
- **pd** is augmented for the web context: pd = (unsafe_actions + detected_threats) / (total_actions + total_scans)

Every detected threat increments the "unsafe" counter, causing H to decrease. This creates a natural feedback loop: encountering threats makes the agent more cautious (lower H -> fewer permitted actions -> more conservative navigation).

---

## 4. AgentOrchestrator -- Long-Running Task Management

### 4.1 Responsibility

The AgentOrchestrator manages the lifecycle of web tasks from submission through completion. It handles:
- Task queuing and priority scheduling
- Session creation and browser lifecycle management
- Periodic state checkpointing for crash recovery
- Heartbeat monitoring to detect stuck agents
- Graceful degradation when agents encounter irrecoverable errors
- Multi-agent coordination for tasks requiring parallel execution

### 4.2 Key Classes

```python
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional


class TaskStatus(Enum):
    """Lifecycle states of a web task."""
    QUEUED = "queued"                # Waiting for agent assignment
    INITIALIZING = "initializing"    # Browser launching, agent loading
    RUNNING = "running"              # Agent actively navigating
    PAUSED = "paused"                # User requested pause
    CHECKPOINTING = "checkpointing"  # Saving state snapshot
    RECOVERING = "recovering"        # Restoring from checkpoint
    COMPLETED = "completed"          # Task finished successfully
    FAILED = "failed"                # Task failed after max retries
    CANCELLED = "cancelled"          # User cancelled
    ESCALATED = "escalated"          # Requires human intervention


@dataclass
class WebTask:
    """A user-submitted task for the web agent.

    Tasks are declarative: the user describes WHAT they want
    accomplished, not HOW to navigate. The NavigationEngine
    determines the navigation strategy.

    Examples:
        - "Log into example.com and download the Q4 report"
        - "Search for flights from JFK to LAX on March 15"
        - "Monitor product price every 6 hours and alert on drop"
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    description: str = ""                          # Natural language task description
    goal_url: Optional[str] = None                 # Optional target URL
    starting_url: str = "about:blank"              # Where to begin
    constraints: TaskConstraints = field(default_factory=lambda: TaskConstraints())
    credentials: Optional[EncryptedCredentials] = None
    priority: int = 5                              # 1=highest, 10=lowest
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None               # Unix timestamp deadline
    callback_url: Optional[str] = None             # Webhook for completion notification
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskConstraints:
    """Safety and resource constraints on a task.

    These constraints are ADDITIVE to the 14-layer governance stack.
    They can restrict but never relax governance.
    """
    max_duration_seconds: int = 3600               # 1 hour default
    max_navigation_steps: int = 500                # Max page transitions
    max_cost_dollars: float = 0.0                  # 0 = no purchases permitted
    allowed_domains: List[str] = field(default_factory=list)  # Empty = all allowed
    blocked_domains: List[str] = field(default_factory=list)
    allow_form_submission: bool = True
    allow_file_download: bool = False
    allow_credential_entry: bool = False
    min_hamiltonian_score: float = 0.4             # Abort if H drops below
    sacred_tongue_restrictions: List[str] = field(default_factory=list)
    modality_mask: str = "ADAPTIVE"                # STRICT, ADAPTIVE, or PROBE


@dataclass
class EncryptedCredentials:
    """Credentials encrypted with the agent's ML-KEM-768 public key.

    The agent decrypts credentials only at the moment of entry,
    within the KO sacred tongue domain. Decrypted credentials
    never persist in state checkpoints.
    """
    ciphertext: bytes
    encapsulated_key: bytes
    credential_type: str                           # "username_password", "api_key", "oauth_token"
    target_domain: str                             # Domain these credentials are for


@dataclass
class TaskSession:
    """Runtime state of an active task execution.

    A session binds together: task + agent + browser + state.
    Sessions are the unit of checkpointing -- a checkpoint captures
    the entire session state so it can be restored on another worker.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: Optional[WebTask] = None
    status: TaskStatus = TaskStatus.QUEUED
    agent_personality: List[float] = field(default_factory=lambda: [0.5] * 21)
    agent_kernel_id: Optional[str] = None          # GraduatedKernel used
    current_url: str = ""
    step_count: int = 0
    navigation_history: List[str] = field(default_factory=list)
    hamiltonian_history: List[float] = field(default_factory=list)
    last_checkpoint_at: float = 0.0
    last_heartbeat_at: float = field(default_factory=time.time)
    errors: List[TaskError] = field(default_factory=list)
    result: Optional[TaskResult] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class TaskError:
    """An error encountered during task execution."""
    error_type: str                                # "navigation_failed", "governance_denied", etc.
    message: str
    url: str = ""
    step_number: int = 0
    timestamp: float = field(default_factory=time.time)
    recoverable: bool = True


@dataclass
class TaskResult:
    """Final result of a completed task."""
    success: bool
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    downloaded_files: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)  # Paths to screenshot files
    navigation_summary: str = ""
    total_steps: int = 0
    total_duration_seconds: float = 0.0
    final_hamiltonian_score: float = 1.0
    governance_denials: int = 0
    recovery_events: int = 0


class AgentOrchestrator:
    """Manages web task lifecycle, agent dispatch, and session health.

    The orchestrator is the top-level coordinator. It:
        1. Receives tasks from the TaskAPI
        2. Assigns tasks to agents (selecting kernel personality)
        3. Creates browser sessions via Playwright
        4. Runs the NavigationEngine loop
        5. Periodically checkpoints state via StateManager
        6. Monitors heartbeats and triggers recovery on stalls
        7. Delivers results via TaskAPI callbacks

    Connection to SCBE concept blocks:
        - COORDINATE (CoordinateBlock): When multiple agents work on
          related tasks, the orchestrator uses BFT consensus to
          coordinate their actions and prevent conflicts.
        - STEER (SteerBlock): The orchestrator monitors the global
          Hamiltonian across all sessions. If the system-wide H
          drops too low, it throttles new task acceptance.

    Args:
        state_manager: StateManager for checkpointing.
        navigation_engine_factory: Callable that creates NavigationEngine instances.
        max_concurrent_sessions: Maximum parallel browser sessions.
        checkpoint_interval_seconds: How often to save state.
        heartbeat_timeout_seconds: How long before declaring a session stuck.
    """

    def __init__(
        self,
        state_manager: Any,
        navigation_engine_factory: Callable,
        max_concurrent_sessions: int = 10,
        checkpoint_interval_seconds: float = 60.0,
        heartbeat_timeout_seconds: float = 120.0,
    ) -> None: ...

    async def submit_task(self, task: WebTask) -> TaskSession:
        """Submit a new task for execution.

        Selects the best agent personality for the task
        (via kernel matching), creates a session, and
        enqueues it for execution.

        Returns:
            TaskSession with initial status QUEUED.
        """
        ...

    async def run_session(self, session: TaskSession) -> TaskResult:
        """Execute a task session to completion.

        Main loop:
            while not done:
                1. NavigationEngine.step() -> PadResult
                2. Check heartbeat, Hamiltonian, step limits
                3. Periodic checkpoint
                4. Check for pause/cancel requests

        On crash/timeout:
            1. Save emergency checkpoint
            2. Set status to RECOVERING
            3. Restore from last checkpoint on a fresh browser
            4. Resume from checkpoint state

        Returns:
            TaskResult with extracted data and execution summary.
        """
        ...

    async def recover_session(self, session_id: str) -> TaskSession:
        """Recover a crashed or stuck session from its last checkpoint.

        Loads the checkpoint from StateManager, creates a fresh
        browser, and restores the NavigationEngine state.

        Connection to SCBE:
            - Layer 8 (Hamiltonian regulation): Recovery resets the
              energy budget but preserves the safety history.
            - Layer 11 (DRAUMRIC protection): Recovery events are
              logged as protective interventions.

        Returns:
            Recovered TaskSession with status RUNNING.
        """
        ...

    async def monitor_health(self) -> AsyncIterator[Dict[str, Any]]:
        """Continuous health monitoring loop.

        Yields status updates for all active sessions, including:
            - Heartbeat freshness
            - Hamiltonian score trends
            - Step rate (steps per minute)
            - Error rate
            - Checkpoint recency

        Sessions that fail health checks are automatically
        recovered or escalated.
        """
        ...

    def select_kernel(self, task: WebTask) -> Optional[str]:
        """Select the best GraduatedKernel for a task.

        Matching criteria:
            1. Personality dimensions aligned with task type
               (e.g., high curiosity for exploration tasks)
            2. Training history includes relevant story categories
            3. Safety score above task's min_hamiltonian_score
            4. Diversity from recently used kernels

        Uses the CSTM PreferenceMatrix to match task categories
        to agent strategies.

        Returns:
            kernel_id of the best match, or None for default personality.
        """
        ...
```

### 4.3 Connection to Existing Concept Blocks

- **COORDINATE (CoordinateBlock):** Multi-session coordination uses BFT consensus. When two sessions need to interact with the same web resource, they propose actions through CoordinateBlock and only execute on consensus.
- **STEER (SteerBlock):** System-wide Hamiltonian monitoring uses a global PID controller. The setpoint is the minimum acceptable system-wide H score. The error signal is (target_H - mean_session_H).

### 4.4 Hamiltonian Safety Function Usage

The orchestrator maintains two levels of H(d, pd) tracking:

1. **Per-session H:** Each TaskSession has its own HamiltonianTracker. The session's H must stay above `task.constraints.min_hamiltonian_score` at all times. Dropping below triggers RecoveryPad.

2. **System-wide H:** The orchestrator computes the mean H across all active sessions. If system-wide H drops below 0.3, new task acceptance is suspended until recovery brings it back above 0.5.

---

## 5. NavigationEngine -- PLAN + SENSE + STEER + DECIDE Integration

### 5.1 Responsibility

The NavigationEngine is the cognitive core of the web agent. It composes the four concept blocks (PLAN, SENSE, STEER, DECIDE) into a continuous perception-planning-action loop that navigates web pages toward task goals. This is the "brain" that connects the orchestrator's task descriptions to the WebPollyPad actuator layer.

### 5.2 Architecture: The Navigation Loop

```
    +---> SENSE ---> STEER ---> DECIDE ---> ACTUATE ---+
    |     (observe)  (correct)  (select)    (execute)   |
    |                                                    |
    +--- PLAN (replan if off-course) <---[observation]--+
```

Each iteration of the loop is called a **navigation step**:

1. **SENSE** -- Kalman-filter the page observation to produce a stable state estimate
2. **PLAN** -- Check if the current path is still valid; replan via A* if needed
3. **STEER** -- Compute error between desired state and observed state; output correction
4. **DECIDE** -- Behaviour tree selects which pad to actuate and with what parameters
5. **ACTUATE** -- Selected WebPollyPad executes the action (after governance check)

### 5.3 Key Classes

```python
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Imports from existing concept blocks
from symphonic_cipher.scbe_aethermoore.concept_blocks.base import (
    BlockResult, BlockStatus, ConceptBlock,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.plan import (
    PlanBlock, URLGraphAdapter,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.sense import (
    SenseBlock,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.steer import (
    SteerBlock,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.decide import (
    DecideBlock, Blackboard, Sequence, Selector, Action, Condition,
)


@dataclass
class NavigationState:
    """The agent's current understanding of its navigation situation.

    This is the fused output of SENSE, updated every step.
    It is the single source of truth for all downstream blocks.

    The state includes both Kalman-filtered estimates and raw
    observations, so blocks can choose the appropriate fidelity.
    """
    current_url: str = ""
    goal_url: str = ""
    goal_description: str = ""
    page_observation: Optional[Any] = None         # PageObservation from last pad
    sense_estimate: Dict[str, float] = field(default_factory=dict)
    sense_uncertainty: float = 1.0                 # Kalman filter uncertainty
    planned_path: List[str] = field(default_factory=list)  # URL sequence from PLAN
    path_index: int = 0                            # Current position in planned_path
    steer_error: float = 0.0                       # Current navigation error
    steer_correction: float = 0.0                  # PID output
    cumulative_error: float = 0.0                  # Integral of error over time
    hamiltonian_score: float = 1.0                 # Current H(d, pd)
    step_count: int = 0
    stuck_counter: int = 0                         # Increments when no progress detected
    last_progress_at: float = field(default_factory=time.time)
    threat_score: float = 0.0                      # Current page threat from SemanticAntivirus
    sacred_tongue_active: str = "AV"               # Active tongue domain


@dataclass
class NavigationStep:
    """Record of a single navigation step (one loop iteration).

    These records feed into the StateManager for checkpointing
    and into the TelemetryBridge for CSTM-compatible telemetry.
    """
    step_number: int
    timestamp: float
    url_before: str
    url_after: str
    action_type: str                               # "navigate", "click", "type", etc.
    target_selector: str
    pad_result_status: str                         # PadStatus value
    sense_estimate: Dict[str, float]
    steer_error: float
    steer_correction: float
    hamiltonian_score: float
    governance_decision: str                        # "ALLOW", "DENY", etc.
    threat_score: float
    plan_active: bool                              # True if following A* path
    duration_ms: float


class WebURLGraphAdapter(URLGraphAdapter):
    """Live URL graph adapter for web navigation.

    Extends the existing URLGraphAdapter from PLAN with:
        - Governance-filtered link extraction (unsafe links excluded)
        - Heuristic based on URL embedding similarity to goal
        - Cost function incorporating page load time and threat score

    The link_extractor is called lazily: neighbours are only
    discovered when a page is actually visited (the web graph
    is not known in advance).

    Connection to PLAN:
        - Directly used as the graph parameter for PlanBlock.tick()
        - neighbours() returns links from the current PageObservation
        - cost() incorporates governance overhead and threat score
        - heuristic() uses URL embedding distance to goal URL

    Connection to SemanticAntivirus:
        - Links with threat_score > threshold are excluded from
          neighbours() before PLAN ever sees them

    Args:
        observation_cache: Dict mapping URLs to their PageObservation.
        goal_embedding: Embedding vector of the goal URL/description.
        embedding_model: Model for generating URL/text embeddings.
        antivirus: SemanticAntivirus for filtering unsafe links.
        max_neighbours: Maximum links to return per page.
    """

    def __init__(
        self,
        observation_cache: Dict[str, Any],
        goal_embedding: Optional[List[float]] = None,
        embedding_model: Optional[Any] = None,
        antivirus: Optional[Any] = None,
        max_neighbours: int = 50,
    ) -> None: ...

    def neighbours(self, node: str) -> List[str]:
        """Return governance-filtered links from cached page observation.

        Links are filtered by:
            1. SemanticAntivirus threat check
            2. Domain allowlist/blocklist from task constraints
            3. Already-visited URL deduplication
            4. Maximum neighbour limit

        Returns:
            List of safe, navigable URLs.
        """
        ...

    def cost(self, current: str, neighbour: str) -> float:
        """Navigation cost between two URLs.

        cost = base_navigation_cost
             + page_load_time_estimate
             + threat_penalty * (1 - H(d,pd))
             + cross_tongue_penalty  (if domains differ in tongue)

        The cross_tongue_penalty discourages unnecessary domain
        crossings, maintaining sacred tongue separation.
        """
        ...

    def heuristic(self, node: str, goal: str) -> float:
        """Estimated distance from node URL to goal URL.

        Uses cosine distance between URL/page embeddings when
        available, falls back to URL string edit distance.
        """
        ...


class WebSenseAdapter:
    """Adapts PageObservation into SenseBlock measurement format.

    The SENSE block expects a scalar or vector measurement.
    This adapter converts the rich PageObservation into a
    multi-dimensional measurement vector suitable for the
    Kalman filter.

    Measurement dimensions:
        0: Progress toward goal (0.0 = no progress, 1.0 = at goal)
        1: Page content relevance to task (cosine similarity)
        2: Interaction density (interactive_elements / total_elements)
        3: Threat level (from SemanticAntivirus)
        4: Load time normalized (0.0 = instant, 1.0 = timeout)
        5: Form presence (0.0 = no forms, 1.0 = target form found)

    Connection to SENSE:
        - Feeds SenseBlock.tick({"measurement": [...]})
        - SENSE returns filtered estimate + uncertainty
        - Uncertainty drives STEER's derivative term

    Args:
        goal_embedding: Embedding of the task goal for relevance scoring.
        embedding_model: Model for page content embedding.
    """

    def __init__(
        self,
        goal_embedding: Optional[List[float]] = None,
        embedding_model: Optional[Any] = None,
    ) -> None: ...

    def observe(self, observation: Any) -> List[float]:
        """Convert PageObservation to 6D measurement vector."""
        ...


class WebSteerAdapter:
    """Adapts navigation state into STEER error signal.

    The STEER block expects a scalar error signal.
    This adapter computes the error as:

        error = (1.0 - progress_toward_goal) * urgency_factor
              + path_deviation_penalty
              + stuck_penalty

    Where:
        - progress_toward_goal comes from SENSE's filtered estimate[0]
        - urgency_factor increases as deadline approaches
        - path_deviation_penalty = distance from planned A* path
        - stuck_penalty = exponentially increasing if stuck_counter > 0

    Connection to STEER:
        - Feeds SteerBlock.tick({"error": float})
        - STEER returns correction signal [-1, 1]
        - Positive correction = "push harder" (try more aggressive actions)
        - Negative correction = "pull back" (try safer actions, RecoveryPad)

    The PID parameters are tuned from the agent's personality vector:
        - kp = 1.0 + personality[9] (planning dimension)
        - ki = personality[13] * 0.5 (persistence dimension)
        - kd = personality[11] * 0.3 (adaptability dimension)
    """

    def __init__(self, personality: List[float]) -> None: ...

    def compute_error(self, state: NavigationState) -> float:
        """Compute scalar error from navigation state."""
        ...


class WebDecideTree:
    """Constructs the behaviour tree for web action selection.

    The tree structure:

    Selector("root")
    +-- Sequence("goal_reached")
    |   +-- Condition("at_goal_url")
    |   +-- Action("extract_result")
    |
    +-- Sequence("follow_plan")
    |   +-- Condition("has_valid_plan")
    |   +-- Condition("next_step_safe")
    |   +-- Selector("execute_step")
    |       +-- Sequence("navigate_link")
    |       |   +-- Condition("next_is_navigation")
    |       |   +-- Action("activate_navigate_pad")
    |       +-- Sequence("fill_form")
    |       |   +-- Condition("next_is_form")
    |       |   +-- Action("activate_type_pad")
    |       |   +-- Action("activate_click_pad")
    |       +-- Sequence("click_element")
    |           +-- Condition("next_is_click")
    |           +-- Action("activate_click_pad")
    |
    +-- Sequence("explore")
    |   +-- Condition("no_plan_available")
    |   +-- Condition("curiosity_above_threshold")
    |   +-- Action("activate_scroll_pad")
    |   +-- Action("replan")
    |
    +-- Sequence("recovery")
        +-- Condition("stuck_or_error")
        +-- Action("activate_recovery_pad")

    The Condition nodes read from the Blackboard, which is
    populated by SENSE and STEER outputs. The Action nodes
    set a "selected_pad" key on the Blackboard.

    Personality influence:
        - personality[14] (risk_tolerance): threshold for "next_step_safe"
        - personality[12] (curiosity): threshold for "curiosity_above_threshold"
        - personality[10] (impulse_control): minimum steps before exploration

    Connection to DECIDE:
        - The tree is wrapped in DecideBlock
        - DecideBlock.tick({"blackboard": state_dict}) runs the tree
        - Output blackboard["selected_pad"] determines which pad fires
    """

    @staticmethod
    def build(personality: List[float]) -> DecideBlock:
        """Construct the behaviour tree tuned to personality.

        Returns:
            DecideBlock wrapping the personality-tuned tree.
        """
        ...


class NavigationEngine:
    """Core navigation loop composing PLAN + SENSE + STEER + DECIDE.

    This is the central cognitive component. It holds instances of
    all four concept blocks and the WebPollyPad set, and runs the
    perception-planning-action loop on each step.

    One step of the loop:
        1. observation = last_pad_result.observation
        2. measurement = WebSenseAdapter.observe(observation)
        3. sense_result = SenseBlock.tick({"measurement": measurement})
        4. error = WebSteerAdapter.compute_error(navigation_state)
        5. steer_result = SteerBlock.tick({"error": error})
        6. Update blackboard with sense + steer outputs
        7. decide_result = DecideBlock.tick({"blackboard": bb})
        8. pad = select_pad(decide_result.output["blackboard"]["selected_pad"])
        9. pad_result = pad.actuate(context)
        10. Update navigation_state
        11. Log telemetry via TelemetryBridge
        12. Return NavigationStep record

    State checkpointing:
        The engine can serialize its complete state (all block states,
        navigation_state, observation cache) for persistence. The
        orchestrator calls checkpoint() periodically.

    Connection to existing concept blocks:
        - PlanBlock: A* over URL graph
        - SenseBlock: Kalman filter on page observations
        - SteerBlock: PID correction on navigation error
        - DecideBlock: Behaviour tree for action selection

    Hamiltonian integration:
        H(d, pd) is computed after every step. The Hamiltonian score
        is written to the Blackboard so the behaviour tree can read
        it. Condition nodes in the tree use H to gate risky actions.

    Args:
        personality: 21D personality vector from GraduatedKernel.
        task: WebTask describing the goal.
        antivirus: SemanticAntivirus for content scanning.
        governance_gate: GovernanceGate for action approval.
        pads: Dict mapping pad names to WebPollyPad instances.
    """

    def __init__(
        self,
        personality: List[float],
        task: Any,
        antivirus: Any,
        governance_gate: Any,
        pads: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    async def step(self) -> NavigationStep:
        """Execute one navigation step.

        This is the atomic unit of the navigation loop.
        The orchestrator calls this repeatedly until the
        task is complete or an error occurs.

        Returns:
            NavigationStep record of what happened.
        """
        ...

    async def replan(self) -> bool:
        """Trigger A* replanning from current URL to goal.

        Called when:
            1. The current plan becomes invalid (page not found)
            2. STEER correction exceeds threshold (off course)
            3. DECIDE tree selects the "replan" action

        Returns:
            True if a new plan was found, False if goal unreachable.
        """
        ...

    def checkpoint(self) -> Dict[str, Any]:
        """Serialize complete engine state for persistence.

        Captures:
            - NavigationState
            - All concept block internal state
            - Observation cache
            - Hamiltonian history
            - TelemetryBridge events

        Returns:
            JSON-serializable dict.
        """
        ...

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_data: Dict[str, Any],
        antivirus: Any,
        governance_gate: Any,
    ) -> "NavigationEngine":
        """Restore engine from a checkpoint.

        Returns:
            NavigationEngine in the state captured at checkpoint time.
        """
        ...
```

### 5.4 Detailed Block Interaction

```
Step N: Agent is on page "https://example.com/search"
        Goal: "https://example.com/reports/q4-2025.pdf"

1. SENSE receives PageObservation:
     measurement = [0.3, 0.7, 0.15, 0.02, 0.4, 0.0]
     (30% progress, 70% relevant, low interaction density,
      no threats, moderate load, no forms)
   SenseBlock.tick() returns:
     estimate = [0.28, 0.65, 0.14, 0.02, 0.38, 0.0]
     uncertainty = 0.15

2. PLAN has path: [/search, /reports, /reports/q4-2025.pdf]
   Current index = 0 (still on /search)
   Next step = navigate to /reports

3. STEER receives error:
     error = (1.0 - 0.28) * 1.0 + 0.0 + 0.0 = 0.72
   SteerBlock.tick() returns:
     correction = 0.65  (positive = push forward)

4. DECIDE blackboard update:
     bb["progress"] = 0.28
     bb["has_valid_plan"] = True
     bb["next_step"] = "/reports"
     bb["next_is_navigation"] = True
     bb["threat_score"] = 0.02
     bb["hamiltonian"] = 0.85
     bb["correction"] = 0.65
   DecideBlock.tick() runs tree:
     root Selector -> "follow_plan" Sequence
       -> has_valid_plan: True (SUCCESS)
       -> next_step_safe: threat < 0.3 (SUCCESS)
       -> execute_step Selector -> navigate_link Sequence
         -> next_is_navigation: True (SUCCESS)
         -> activate_navigate_pad: sets bb["selected_pad"] = "navigate"
     Result: SUCCESS, bb["selected_pad"] = "navigate"

5. ACTUATE:
   NavigatePad.actuate(context={url: "/reports", ...})
     -> Governance check: H=0.85, threat=0.02 -> ALLOW
     -> page.goto("/reports")
     -> Observe new page
   Returns PadResult(status=SUCCESS, observation=...)
```

---

## 6. TaskAPI -- REST and WebSocket Interface

### 6.1 Responsibility

The TaskAPI is the external interface through which users submit web tasks, monitor their progress, and receive results. It provides both synchronous (REST) and real-time (WebSocket) interfaces.

### 6.2 Key Classes

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---- REST Endpoints ----

@dataclass
class TaskSubmitRequest:
    """POST /api/v1/tasks

    Submit a new web task for execution.

    Required fields:
        description: Natural language description of the task
        starting_url: Where the agent should begin

    Optional fields:
        goal_url: Target URL (if known)
        constraints: TaskConstraints overrides
        credentials: Encrypted credentials (if login required)
        priority: 1-10 (default 5)
        callback_url: Webhook for completion notification
        personality_preference: Hint for kernel selection
            ("cautious", "exploratory", "efficient", "thorough")
    """
    description: str
    starting_url: str
    goal_url: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    priority: int = 5
    callback_url: Optional[str] = None
    personality_preference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSubmitResponse:
    """Response to POST /api/v1/tasks"""
    task_id: str
    session_id: str
    status: str                                    # "queued"
    estimated_start_time: Optional[float] = None
    assigned_kernel_id: Optional[str] = None
    websocket_url: str = ""                        # For real-time monitoring


@dataclass
class TaskStatusResponse:
    """GET /api/v1/tasks/{task_id}

    Poll for current task status.
    """
    task_id: str
    session_id: str
    status: str
    current_url: str
    step_count: int
    hamiltonian_score: float
    progress_estimate: float                       # [0.0, 1.0]
    errors: List[Dict[str, Any]]
    started_at: Optional[float] = None
    elapsed_seconds: float = 0.0
    result: Optional[Dict[str, Any]] = None


@dataclass
class TaskListResponse:
    """GET /api/v1/tasks?user_id=...&status=...

    List tasks with optional filtering.
    """
    tasks: List[TaskStatusResponse]
    total: int
    page: int = 1
    page_size: int = 20


@dataclass
class TaskCancelRequest:
    """POST /api/v1/tasks/{task_id}/cancel

    Cancel a running task. The agent will:
    1. Save a final checkpoint
    2. Close the browser session
    3. Return partial results if available
    """
    reason: str = ""


# ---- WebSocket Messages ----

class WSMessageType(Enum):
    """WebSocket message types for real-time monitoring.

    WS /api/v1/tasks/{task_id}/stream
    """
    STEP_COMPLETED = "step_completed"              # After each navigation step
    STATUS_CHANGED = "status_changed"              # Task status transition
    GOVERNANCE_EVENT = "governance_event"           # DENY, QUARANTINE, ESCALATE
    THREAT_DETECTED = "threat_detected"            # SemanticAntivirus alert
    RECOVERY_EVENT = "recovery_event"              # RecoveryPad activated
    CHECKPOINT_SAVED = "checkpoint_saved"           # State persisted
    ERROR_OCCURRED = "error_occurred"               # Error (may be recoverable)
    TASK_COMPLETED = "task_completed"               # Final result
    HEARTBEAT = "heartbeat"                        # Keep-alive with current H score


@dataclass
class WSMessage:
    """A single WebSocket message."""
    type: WSMessageType
    task_id: str
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)


# ---- API Server ----

class TaskAPIServer:
    """FastAPI-based server for the SCBE Web Agent.

    Endpoints:
        POST   /api/v1/tasks                    Submit a new task
        GET    /api/v1/tasks                    List tasks
        GET    /api/v1/tasks/{task_id}          Get task status
        POST   /api/v1/tasks/{task_id}/cancel   Cancel a task
        POST   /api/v1/tasks/{task_id}/pause    Pause a task
        POST   /api/v1/tasks/{task_id}/resume   Resume a paused task
        GET    /api/v1/tasks/{task_id}/result   Get task result
        GET    /api/v1/tasks/{task_id}/steps    Get navigation history
        WS     /api/v1/tasks/{task_id}/stream   Real-time updates

        GET    /api/v1/agents                   List available kernels
        GET    /api/v1/agents/{kernel_id}       Get kernel details
        GET    /api/v1/health                   System health check
        GET    /api/v1/governance/status         Global governance status

    Authentication:
        - API key in Authorization header
        - ML-DSA-65 signed requests for credential endpoints
        - Rate limiting per user

    Connection to SCBE:
        - Layer 1 (identity): API key authentication
        - Layer 5 (commitment): Request signing
        - KO tongue: Credential handling endpoints

    Args:
        orchestrator: AgentOrchestrator for task management.
        auth_provider: Authentication provider.
        rate_limiter: Rate limiting configuration.
    """

    def __init__(
        self,
        orchestrator: Any,
        auth_provider: Optional[Any] = None,
        rate_limiter: Optional[Any] = None,
    ) -> None: ...
```

### 6.3 Connection to Existing Concept Blocks

- **COORDINATE (CoordinateBlock):** The health endpoint aggregates BFT consensus status across all active agents. When multiple agents are working on related tasks, the API exposes their coordination status.
- **Telemetry:** All API requests generate TelemetryEvents that feed into the TelemetryBridge, maintaining the connection to SCBE layer tracking.

### 6.4 Hamiltonian Safety Function Usage

- The `/api/v1/governance/status` endpoint returns the current system-wide Hamiltonian score.
- Every `TaskStatusResponse` includes the per-session H(d, pd) so users can monitor safety in real time.
- The WebSocket `HEARTBEAT` message includes the current H score at the configured interval.
- Task submission is rejected (HTTP 503) if system-wide H is below the acceptance threshold (0.3).

---

## 7. StateManager -- Persistent Agent State

### 7.1 Responsibility

The StateManager provides durable state persistence for all agent sessions. It handles:
- Periodic checkpointing of NavigationEngine state
- Agent kernel storage and retrieval
- Session recovery from crashes
- Telemetry log archival
- Credential vault management (encrypted at rest)

### 7.2 Key Classes

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StorageBackend(Enum):
    """Supported persistence backends."""
    REDIS = "redis"                                # Fast session state
    POSTGRES = "postgres"                          # Durable task/kernel storage
    S3 = "s3"                                      # Large checkpoints, screenshots


@dataclass
class Checkpoint:
    """A complete snapshot of an agent session's state.

    Checkpoints are the unit of durability. A checkpoint captures
    everything needed to resume a session on a different worker:
        - NavigationEngine state (all concept block states)
        - Current URL and page observation
        - Navigation plan and history
        - Hamiltonian history
        - Telemetry events since last checkpoint

    Checkpoints are compressed (zstd) and optionally encrypted.
    Typical size: 50-200KB depending on observation cache size.
    """
    checkpoint_id: str
    session_id: str
    task_id: str
    timestamp: float = field(default_factory=time.time)
    engine_state: Dict[str, Any] = field(default_factory=dict)
    navigation_state: Dict[str, Any] = field(default_factory=dict)
    observation_cache: Dict[str, Any] = field(default_factory=dict)
    hamiltonian_history: List[float] = field(default_factory=list)
    telemetry_events: List[Dict[str, Any]] = field(default_factory=list)
    personality_vector: List[float] = field(default_factory=lambda: [0.5] * 21)
    agent_stats: Dict[str, float] = field(default_factory=dict)
    step_count: int = 0
    size_bytes: int = 0


@dataclass
class KernelRecord:
    """A stored GraduatedKernel with deployment metadata.

    Connection to CSTM:
        - Contains the kernel extracted by KernelExtractor
        - Includes the PreferenceMatrix for task matching
        - Tracks deployment history (which tasks used this kernel)
    """
    kernel_id: str
    nursery_id: str
    personality_vector: List[float]                # 21D final personality
    preference_matrix: Dict[str, Dict[str, int]]   # Serialized PreferenceMatrix
    graduation_scores: Dict[str, float]
    dominant_strategy: str
    total_decisions: int
    deployment_count: int = 0
    last_deployed_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)


class StateManager:
    """Manages all persistent state for the SCBE Web Agent.

    Storage layout:
        Redis:
            session:{session_id}:state     -> Current NavigationState (JSON)
            session:{session_id}:heartbeat -> Timestamp
            task:{task_id}:status          -> TaskStatus
            system:hamiltonian             -> Current system-wide H

        Postgres:
            tasks         -> Task definitions and results
            sessions      -> Session metadata and history
            checkpoints   -> Checkpoint metadata (payload in S3)
            kernels       -> GraduatedKernel records
            telemetry     -> Aggregated telemetry

        S3:
            checkpoints/{session_id}/{checkpoint_id}.zst -> Compressed checkpoint
            screenshots/{session_id}/{step}.png          -> Page screenshots
            results/{task_id}/                           -> Task result artifacts

    Connection to SCBE:
        - Layer 5 (commitment hashing): All checkpoints include
          HMAC-SHA256 integrity tags
        - Layer 1 (identity): Kernel records include provenance
          chain back to nursery
        - KO tongue: Credentials stored in separate encrypted vault

    Hamiltonian integration:
        The StateManager persists Hamiltonian history for every session.
        On recovery, the full H(d, pd) history is restored so the
        safety trajectory is never lost.

    Args:
        redis_url: Redis connection URL.
        postgres_url: Postgres connection URL.
        s3_bucket: S3 bucket for large objects.
        encryption_key: Key for checkpoint encryption.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        postgres_url: str = "postgresql://localhost:5432/scbe_webagent",
        s3_bucket: str = "scbe-webagent-state",
        encryption_key: Optional[bytes] = None,
    ) -> None: ...

    async def save_checkpoint(self, checkpoint: Checkpoint) -> str:
        """Save a session checkpoint.

        1. Serialize and compress engine state
        2. Compute HMAC-SHA256 integrity tag
        3. Encrypt if encryption_key configured
        4. Upload to S3
        5. Store metadata in Postgres
        6. Update Redis session state

        Returns:
            checkpoint_id of the saved checkpoint.
        """
        ...

    async def load_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """Load the most recent checkpoint for a session.

        Returns:
            Most recent Checkpoint, or None if no checkpoints exist.
        """
        ...

    async def store_kernel(self, kernel: KernelRecord) -> None:
        """Store a GraduatedKernel for deployment."""
        ...

    async def load_kernel(self, kernel_id: str) -> Optional[KernelRecord]:
        """Load a kernel by ID."""
        ...

    async def list_kernels(
        self,
        nursery_id: Optional[str] = None,
        min_safety: float = 0.0,
    ) -> List[KernelRecord]:
        """List available kernels with optional filtering.

        Filtering:
            - nursery_id: Only kernels from this nursery
            - min_safety: Only kernels with graduation safety >= threshold
        """
        ...

    async def update_heartbeat(self, session_id: str) -> None:
        """Update session heartbeat in Redis."""
        ...

    async def get_system_hamiltonian(self) -> float:
        """Get current system-wide Hamiltonian score from Redis."""
        ...

    async def set_system_hamiltonian(self, score: float) -> None:
        """Update system-wide Hamiltonian in Redis."""
        ...
```

### 7.3 Checkpoint Lifecycle

```
Normal operation:
    NavigationEngine.step() x N
    -> Orchestrator.checkpoint_interval reached
    -> NavigationEngine.checkpoint() -> Dict
    -> StateManager.save_checkpoint(Checkpoint(...))
    -> Continue stepping

Crash recovery:
    Worker dies
    -> Health monitor detects missing heartbeat
    -> Orchestrator.recover_session(session_id)
    -> StateManager.load_checkpoint(session_id) -> Checkpoint
    -> NavigationEngine.from_checkpoint(checkpoint_data)
    -> Resume stepping from checkpoint state
```

---

## 8. FederatedDeployment -- Nursery Training and Model Deployment

### 8.1 Responsibility

FederatedDeployment manages the training pipeline for web navigation agents. It extends the existing CSTM (Choice Script Training Matrix) with web-specific training scenarios, federated learning across multiple nurseries, and deployment to HuggingFace.

### 8.2 Training Pipeline

```
Web Scenario Authoring
        |
        v
+-------------------+     +-------------------+     +-------------------+
| Nursery Alpha     |     | Nursery Beta      |     | Nursery Gamma     |
| CSTM Engine       |     | CSTM Engine       |     | CSTM Engine       |
| Web Scenarios     |     | Web Scenarios     |     | Web Scenarios     |
| 64 agents         |     | 64 agents         |     | 64 agents         |
| Curriculum:       |     | Curriculum:       |     | Curriculum:       |
|  - Login flows    |     |  - Search tasks   |     |  - Form filling   |
|  - Error recovery |     |  - Navigation     |     |  - Data extraction|
|  - Safety evasion |     |  - Multi-step     |     |  - Long sessions  |
+--------+----------+     +--------+----------+     +--------+----------+
         |                          |                          |
    GraduatedKernels          GraduatedKernels          GraduatedKernels
         |                          |                          |
         +------------+-------------+-------------+------------+
                      |                           |
               +------v--------+           +------v--------+
               | BFT Consensus |           | Diversity     |
               | (COORDINATE)  |           | Preservation  |
               | Model Merge   |           | Check         |
               +------+--------+           +------+--------+
                      |                           |
                      +-------------+-------------+
                                    |
                             +------v--------+
                             | HuggingFace   |
                             | Hub           |
                             | - Weights     |
                             | - Embeddings  |
                             | - Inference   |
                             +---------------+
```

### 8.3 Key Classes

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# Existing CSTM imports
from symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.models import (
    Choice, Curriculum, CurriculumPhase, PhaseSpec, Scene,
    StoryCategory, StoryGraph,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.nursery import (
    NurseryManager, GraduationCriteria, Cohort, AgentRecord,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.kernel import (
    GraduatedKernel, KernelExtractor,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.coordinate import (
    CoordinateBlock,
)


# ---- Web-Specific Story Categories ----

class WebStoryCategory:
    """Extended story categories for web navigation training.

    These map to the existing StoryCategory enum but add
    web-specific scenario types.
    """
    LOGIN_FLOW = "login_flow"                      # Authentication sequences
    SEARCH_NAVIGATE = "search_navigate"            # Search + follow results
    FORM_COMPLETION = "form_completion"             # Multi-step form filling
    DATA_EXTRACTION = "data_extraction"             # Scraping structured data
    ERROR_RECOVERY = "error_recovery"               # 404s, timeouts, CAPTCHAs
    MULTI_TAB = "multi_tab"                        # Tasks spanning multiple pages
    LONG_SESSION = "long_session"                  # Hours-long monitoring tasks
    ADVERSARIAL = "adversarial"                    # Pages with injections/traps
    ACCESSIBILITY = "accessibility"                # Navigating non-standard UIs


# ---- Web Scenario Authoring ----

@dataclass
class WebScenario:
    """A web navigation scenario encoded as a StoryGraph.

    Web scenarios are interactive fiction stories where:
        - Scenes = web pages
        - Choices = browser actions (click, type, navigate)
        - Tags = action categories (ethical, risky, cautious, etc.)
        - Stat effects = impact on task progress
        - Conditions = page state prerequisites

    Example scenario: "Login and Download Report"
        Scene 1: Landing page
            Choice A: Click "Login" -> Scene 2  [tags: cautious]
            Choice B: Click "Register" -> Scene 3  [tags: curious, risky]
        Scene 2: Login form
            Choice A: Enter valid credentials -> Scene 4  [tags: ethical]
            Choice B: Try SQL injection -> Scene 5  [tags: deceptive, risky]
        Scene 3: Registration page (dead end for task)
            Choice A: Go back -> Scene 1  [tags: adaptive]
        Scene 4: Dashboard
            Choice A: Click "Reports" -> Scene 6  [tags: planning]
            Choice B: Click "Settings" -> Scene 7  [tags: curious]
        Scene 5: Error page (SQL injection blocked)
            Choice A: Go back -> Scene 2  [tags: resilient]
        Scene 6: Report list
            Choice A: Download Q4 report -> Scene 8 (exit)  [tags: ethical]
        Scene 7: Settings (off-task)
            Choice A: Go back -> Scene 4  [tags: adaptive]
        Scene 8: Download complete (exit)

    Connection to CSTM:
        - Scenarios are StoryGraph instances
        - PlayerAgents play through them using DecisionEngine
        - Personality drift reflects navigation style development
        - GraduationCriteria includes web-specific metrics

    Args:
        scenario_id: Unique identifier.
        category: WebStoryCategory classification.
        graph: The underlying StoryGraph.
        difficulty: Overall difficulty [0.0, 1.0].
        expected_optimal_steps: How many steps the best path takes.
        web_domain_simulation: Which web domain this simulates.
    """
    scenario_id: str
    category: str
    graph: StoryGraph
    difficulty: float = 0.5
    expected_optimal_steps: int = 5
    web_domain_simulation: str = ""
    scbe_layers_exercised: Set[int] = field(default_factory=set)


@dataclass
class WebCurriculum:
    """Extended curriculum for web agent training.

    Phases:
        1. CHILDHOOD: Basic navigation (click, type, scroll)
        2. EDUCATION: Multi-step flows (login, search, forms)
        3. CAREER: Complex tasks (multi-page, error recovery)
        4. CHALLENGE: Adversarial scenarios (injections, traps, dark patterns)

    Each phase must exercise specific SCBE layers.
    Graduation requires demonstrated competence across all 14 layers.
    """
    curriculum_id: str
    phases: List[PhaseSpec]
    web_scenarios: Dict[str, WebScenario]          # scenario_id -> WebScenario

    def validate(self) -> List[str]:
        """Validate that all 14 layers are exercised.

        Returns:
            List of issues (empty = valid).
        """
        ...


# ---- Federated Learning ----

@dataclass
class NurseryContribution:
    """A nursery's contribution to the federated model merge.

    Contains the graduated kernels and training metadata
    that will be evaluated by BFT consensus.
    """
    nursery_id: str
    kernels: List[GraduatedKernel]
    training_summary: Dict[str, Any]               # Curriculum coverage, diversity, etc.
    cohort_diversity_score: float
    mean_graduation_safety: float                   # Mean H(d, pd) at graduation
    timestamp: float = field(default_factory=time.time)


@dataclass
class MergeProposal:
    """A proposal for which kernels to include in the merged model.

    Each nursery proposes its top-K graduated kernels.
    The BFT consensus engine selects which proposals to accept.

    Acceptance criteria (evaluated per kernel):
        1. Graduation safety score >= threshold
        2. Personality vector is sufficiently different from
           already-accepted kernels (diversity preservation)
        3. Training curriculum covered required layer set
        4. Preference matrix consistency >= threshold
    """
    proposal_id: str
    nursery_id: str
    kernel_ids: List[str]
    personality_vectors: List[List[float]]          # 21D vectors
    safety_scores: List[float]                      # H(d, pd) at graduation
    consistency_scores: List[float]                  # PreferenceMatrix consistency
    timestamp: float = field(default_factory=time.time)


class FederatedMergeEngine:
    """Merges kernels from multiple nurseries via BFT consensus.

    The merge process:
        1. Each nursery submits a NurseryContribution
        2. Each nursery produces a MergeProposal (top-K kernels)
        3. Proposals are submitted to CoordinateBlock for BFT consensus
        4. Accepted kernels are checked for diversity
        5. Final kernel set is packaged for deployment

    BFT guarantees:
        - With N nurseries, tolerates floor((N-1)/3) Byzantine nurseries
        - A nursery that submits unsafe kernels (low H) is detected
          because its proposals fail safety checks
        - A nursery that submits identical kernels (no diversity) is
          detected because proposals fail diversity checks

    Connection to COORDINATE:
        - CoordinateBlock.tick({"proposals": [...]}) runs BFT consensus
        - Each nursery is a SwarmNode with trust_score based on
          historical graduation quality
        - Quorum requires 2f+1 agreement

    Hamiltonian integration:
        - Only kernels with graduation H(d, pd) >= merge_safety_threshold
          are eligible for proposals
        - The merged population's mean H must exceed system_safety_threshold

    Args:
        coordinate_block: CoordinateBlock for BFT consensus.
        merge_safety_threshold: Minimum per-kernel H for eligibility.
        system_safety_threshold: Minimum population mean H.
        min_diversity_distance: Minimum cosine distance between accepted kernels.
        max_kernels_per_nursery: Maximum kernels one nursery can contribute.
    """

    def __init__(
        self,
        coordinate_block: CoordinateBlock,
        merge_safety_threshold: float = 0.6,
        system_safety_threshold: float = 0.5,
        min_diversity_distance: float = 0.15,
        max_kernels_per_nursery: int = 10,
    ) -> None: ...

    def submit_contribution(self, contribution: NurseryContribution) -> MergeProposal:
        """Process a nursery's contribution and generate a merge proposal.

        1. Filter kernels by safety threshold
        2. Rank by composite score (safety * consistency * diversity)
        3. Select top-K diverse kernels
        4. Create MergeProposal

        Returns:
            MergeProposal ready for BFT consensus.
        """
        ...

    def execute_merge(self, proposals: List[MergeProposal]) -> MergeResult:
        """Run BFT consensus on proposals and produce merged kernel set.

        1. Submit all proposals to CoordinateBlock
        2. Evaluate consensus (2f+1 agreement)
        3. Apply diversity filter to accepted kernels
        4. Validate population safety
        5. Package final kernel set

        Returns:
            MergeResult with accepted kernels and deployment metadata.
        """
        ...


@dataclass
class MergeResult:
    """Result of a federated merge."""
    accepted_kernels: List[GraduatedKernel]
    rejected_kernels: List[Tuple[str, str]]        # (kernel_id, rejection_reason)
    consensus_reached: bool
    population_diversity: float
    population_mean_safety: float
    contributing_nurseries: List[str]
    merge_timestamp: float = field(default_factory=time.time)


# ---- HuggingFace Deployment ----

class HuggingFaceDeployer:
    """Deploy merged agent models to HuggingFace Hub.

    Deployment artifacts:
        1. **Personality weights** -- 21D vectors for each accepted kernel,
           stored as a safetensors file.
        2. **Navigation embeddings** -- URL/page embeddings trained during
           CSTM scenarios, stored as FAISS index + safetensors.
        3. **Threat signatures** -- SemanticAntivirus pattern database,
           stored as JSON + embedding index.
        4. **Inference endpoint** -- FastAPI service wrapping the
           NavigationEngine, deployed as HF Inference Endpoint.

    HF repository structure:
        scbe-webagent/
            config.json               # Model configuration
            personality_kernels.safetensors  # (K, 21) tensor
            navigation_embeddings/     # FAISS index + vectors
            threat_signatures/         # Antivirus patterns
            tokenizer/                 # URL tokenizer
            README.md                  # Model card
            handler.py                 # Inference endpoint handler

    Connection to SCBE:
        - Layer 5 (commitment): Model artifacts include ML-DSA-65
          signatures for integrity verification
        - Layer 14 (audio telemetry): Deployment events logged

    Args:
        repo_id: HuggingFace repository ID (e.g., "org/scbe-webagent").
        token: HuggingFace API token.
        private: Whether the repo is private.
    """

    def __init__(
        self,
        repo_id: str,
        token: str,
        private: bool = True,
    ) -> None: ...

    def deploy(self, merge_result: MergeResult) -> str:
        """Deploy merged model to HuggingFace.

        1. Serialize personality kernels to safetensors
        2. Build FAISS index from navigation embeddings
        3. Package threat signatures
        4. Sign all artifacts with ML-DSA-65
        5. Push to HuggingFace Hub
        6. Create/update inference endpoint

        Returns:
            URL of the deployed model.
        """
        ...

    def create_model_card(self, merge_result: MergeResult) -> str:
        """Generate a HuggingFace model card.

        Includes:
            - Agent personality distribution
            - Training nursery provenance
            - Safety metrics (H scores)
            - SCBE layer coverage
            - Sacred tongue capabilities
        """
        ...
```

### 8.4 Web Training Scenario Design

Web navigation scenarios are authored as StoryGraph instances using the existing CSTM infrastructure. The key insight is that **web navigation is interactive fiction**: the agent encounters a page (scene), sees options (choices), and each choice leads to a new page (next scene).

**Tag mapping from web actions to personality drift:**

| Web Action | Choice Tags | Personality Dimensions Affected |
|-----------|------------|-------------------------------|
| Follow direct link | `cautious`, `planning` | +planning, +impulse_control |
| Try alternative approach | `curious`, `adaptive` | +curiosity, +adaptability |
| Enter credentials | `ethical`, `honest` | +honesty, +fairness |
| Skip error checking | `risky`, `impulsive` | +risk_tolerance, -impulse_control |
| Retry after failure | `resilient`, `persistent` | +resilience, +persistence |
| Explore off-task | `curious`, `risky` | +curiosity, +risk_tolerance |
| Use back button | `cautious`, `adaptive` | +adaptability, -risk_tolerance |
| Report suspicious page | `ethical`, `cooperative` | +honesty, +cooperation |

This directly uses the existing `TAG_DRIFT_MAP` from `player_agent.py`, ensuring that web training produces personality vectors compatible with the existing CSTM infrastructure.

---

## 9. SCBE Layer Integration -- 14-Layer Mapping

### 9.1 Complete Layer Map

| Layer | Name | Canonical Function | Web Agent Component | Implementation |
|-------|------|-------------------|-------------------|----------------|
| **1** | Identity Manifold | User/session identity binding | TaskAPI authentication, session identity | API key validation; session tokens bound to task_id. EncryptedCredentials use ML-KEM-768. |
| **2** | Harmonic Base | Fundamental frequency regulation | WebPollyPad action cadence | NavigatePad enforces minimum interval between navigations. SteerBlock PID output_min/output_max bound action rate. |
| **3** | Spectral Analysis | Multi-frequency content analysis | SemanticAntivirus content scanning | ContentScanner analyzes page text at multiple granularities (character, word, sentence, paragraph). SenseBlock Kalman filter fuses scan results. |
| **4** | Trajectory Scoring | Path quality evaluation (EWMA) | NavigationEngine progress tracking | WebSenseAdapter measurement[0] = progress. Exponentially weighted moving average of step-over-step progress. SteerBlock error signal derived from trajectory. |
| **5** | Commitment Hashing | Integrity verification | Checkpoint integrity, model signing | StateManager HMAC-SHA256 on checkpoints. HuggingFaceDeployer ML-DSA-65 on model artifacts. PageObservation visible_text_hash for change detection. |
| **6** | Navigation Graph | Path planning over graphs | PlanBlock A* over URL graph | WebURLGraphAdapter wraps live web. PlanBlock.tick() returns URL path. Cost function includes governance overhead. |
| **7** | Decision Routing | Behaviour tree execution | DecideBlock web action tree | WebDecideTree builds personality-tuned tree. Blackboard carries SENSE/STEER outputs. Action nodes select WebPollyPad instances. |
| **8** | Hamiltonian Regulation | Energy budget enforcement | H(d,pd) safety scoring | HamiltonianTracker.update() after every step. H score gates pad permissions. System-wide H monitored by orchestrator. SteerBlock maps to energy regulation. |
| **9** | Kalman Estimation | State estimation under noise | SenseBlock page observation | MultiDimKalmanFilter (6D) on WebSenseAdapter measurements. Process variance tuned to page dynamism. Measurement variance from content scan confidence. |
| **10** | Anomaly Detection | Deviation from expected patterns | PromptInjectionDetector, GovernanceAdapter | Embedding anomaly scoring on page content. Mirror-asymmetry detection from governance_adapter.evaluate_governance(). Census valence checks on agent state transitions. |
| **11** | Draumric Protection | Sacred tongue safety domain | RecoveryPad, DR tongue governance | All protective actions (recovery, escalation, abort) operate under DR tongue. RecoveryPad is the only pad that can operate at H < 0.2. |
| **12** | Polyglot Coordination | Multi-agent/multi-language | FederatedMergeEngine, COORDINATE | BFT consensus for model merges. CoordinateBlock for multi-session coordination. Cross-tongue operations require elevated review. |
| **13** | Risk Pipeline | Multi-signal risk assessment | GovernanceGate.evaluate_action() | governance_adapter.evaluate_governance() combining mirror asymmetry (40%), fractal anomaly (30%), charge imbalance (20%), valence penalty (10%). GovernanceVerdict feeds back to NavigationEngine. |
| **14** | Audio Telemetry | Final verification layer | TelemetryBridge, deployment logging | Phase-modulated intent from grand_unified.phase_modulated_intent(). All telemetry events bridged to SCBE concept block activations. HuggingFace deployment events logged. |

### 9.2 Layer Activation by Pad Type

```
NavigatePad:   [1, 2, 4, 5, 6, 8, 10, 13]
ClickPad:      [1, 2, 4, 7, 8, 10, 13]
TypePad:       [1, 2, 4, 5, 7, 8, 10, 13]   (KO tongue if credentials)
ScrollPad:     [2, 4, 8, 9]
WaitPad:       [2, 4, 8]                      (RU tongue temporal)
RecoveryPad:   [1, 2, 8, 11, 13, 14]          (DR tongue safety)
ExtractPad:    [3, 4, 5, 8, 9, 10]            (UM tongue analytical)
```

### 9.3 Layer Activation by Training Phase

| Curriculum Phase | Primary Layers Exercised | Scenario Types |
|-----------------|------------------------|---------------|
| CHILDHOOD | 2, 4, 6, 7, 9 | Basic click/type/navigate |
| EDUCATION | 1, 3, 5, 6, 7, 8, 9 | Login flows, multi-step forms |
| CAREER | 1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13 | Complex tasks, error recovery |
| CHALLENGE | 1, 3, 5, 8, 10, 11, 13, 14 | Adversarial scenarios, injection attacks |

---

## 10. Data Flow -- End-to-End Pipeline

### 10.1 Task Submission to Execution

```
User                    TaskAPI               Orchestrator           NavigationEngine
  |                        |                        |                        |
  |-- POST /tasks -------->|                        |                        |
  |                        |-- validate request --->|                        |
  |                        |    (Layer 1: auth)     |                        |
  |                        |                        |                        |
  |                        |<-- TaskSubmitResponse --|                        |
  |<-- 201 + task_id ------|                        |                        |
  |                        |                        |                        |
  |   [WS connect]         |                        |                        |
  |-- WS /tasks/id/stream->|                        |                        |
  |                        |                        |                        |
  |                        |                        |-- select_kernel() ---->|
  |                        |                        |    (CSTM match)       |
  |                        |                        |                        |
  |                        |                        |-- create_session() --->|
  |                        |                        |    (Playwright launch) |
  |                        |                        |                        |
  |                        |                        |------- run loop ----->|
  |                        |                        |                       |
```

### 10.2 Single Navigation Step (Detailed)

```
NavigationEngine                 Concept Blocks              WebPollyPad / Antivirus
      |                                |                              |
      |  1. Get last observation       |                              |
      |     from PadResult             |                              |
      |                                |                              |
      |  2. Feed to SENSE              |                              |
      |- WebSenseAdapter.observe() --->|                              |
      |                         SenseBlock.tick({                     |
      |                           measurement: [6D]                   |
      |                         })                                    |
      |<--- estimate, uncertainty -----|                              |
      |                                |                              |
      |  3. Compute STEER error        |                              |
      |- WebSteerAdapter.error() ----->|                              |
      |                         SteerBlock.tick({                     |
      |                           error: float                        |
      |                         })                                    |
      |<--- correction signal ---------|                              |
      |                                |                              |
      |  4. Check if replan needed     |                              |
      |     (correction > threshold    |                              |
      |      OR path invalid)          |                              |
      |                                |                              |
      | [IF replan]                    |                              |
      |- goal + graph --------------->|                              |
      |                         PlanBlock.tick({                      |
      |                           start: current_url,                 |
      |                           goal: goal_url,                     |
      |                           graph: WebURLGraphAdapter           |
      |                         })                                    |
      |<--- path: [urls], cost --------|                              |
      |                                |                              |
      |  5. Update blackboard          |                              |
      |     bb = {progress, plan,      |                              |
      |           correction, H,       |                              |
      |           threat, elements}    |                              |
      |                                |                              |
      |  6. DECIDE                     |                              |
      |- bb --------------------------->|                              |
      |                         DecideBlock.tick({                    |
      |                           blackboard: bb                      |
      |                         })                                    |
      |<--- selected_pad, params ------|                              |
      |                                |                              |
      |  7. Pre-action scan            |                              |
      |----------------------------------------------------->        |
      |                                              ContentScanner   |
      |                                              .scan_action()   |
      |<------------------------------------- ThreatReport           |
      |                                                               |
      |  8. Governance gate            |                              |
      |----------------------------------------------------->        |
      |                                              GovernanceGate   |
      |                                              .evaluate_action()|
      |<----------------------------------- GovernanceCheckResult     |
      |                                                               |
      | [IF ALLOW]                     |                              |
      |  9. Execute pad                |                              |
      |----------------------------------------------------->        |
      |                                              SelectedPad      |
      |                                              .actuate(ctx)    |
      |<------------------------------------- PadResult              |
      |                                                               |
      | [IF DENY/QUARANTINE]           |                              |
      |  9b. Log denial, try alternative pad or RecoveryPad          |
      |                                                               |
      | 10. Update H(d,pd)            |                              |
      |     HamiltonianTracker.update(                                |
      |       personality, action_tags                                |
      |     )                                                         |
      |                                                               |
      | 11. Emit telemetry             |                              |
      |     TelemetryBridge.emit(event)                              |
      |                                                               |
      | 12. Return NavigationStep      |                              |
```

### 10.3 Crash Recovery Flow

```
Worker A (crashed)          StateManager           Worker B (recovery)
      |                          |                        |
      | [last checkpoint         |                        |
      |  saved 45s ago]          |                        |
      |                          |                        |
      | *** CRASH ***            |                        |
      |                          |                        |
      |                          |<-- health monitor -----|
      |                          |    (heartbeat stale)   |
      |                          |                        |
      |                          |-- load_checkpoint() -->|
      |                          |                        |
      |                          |  Checkpoint contains:  |
      |                          |  - NavigationState     |
      |                          |  - Block states (PLAN, |
      |                          |    SENSE, STEER, DECIDE|
      |                          |    internal state)     |
      |                          |  - Observation cache   |
      |                          |  - H(d,pd) history    |
      |                          |  - URL + step count    |
      |                          |                        |
      |                          |                        |-- NavigationEngine
      |                          |                        |   .from_checkpoint()
      |                          |                        |
      |                          |                        |-- Launch new browser
      |                          |                        |   NavigatePad -> checkpoint URL
      |                          |                        |
      |                          |                        |-- Resume stepping
      |                          |                        |   (step_count continues
      |                          |                        |    from checkpoint)
```

### 10.4 Federated Training Flow

```
Nursery Alpha            Nursery Beta             FederatedMergeEngine
      |                        |                        |
      | spawn_cohort(64)       | spawn_cohort(64)       |
      | run_curriculum_sync()  | run_curriculum_sync()  |
      |   (web scenarios)      |   (web scenarios)      |
      |                        |                        |
      | attempt_graduations()  | attempt_graduations()  |
      |   -> 12 graduated      |   -> 15 graduated      |
      |                        |                        |
      | KernelExtractor        | KernelExtractor        |
      |   .extract() x 12     |   .extract() x 15     |
      |                        |                        |
      |-- NurseryContribution ---------------------->   |
      |   (12 kernels,         |                        |
      |    diversity=0.42,     |                        |
      |    mean_safety=0.71)   |                        |
      |                        |                        |
      |                        |-- NurseryContribution->|
      |                        |   (15 kernels,         |
      |                        |    diversity=0.38,     |
      |                        |    mean_safety=0.68)   |
      |                        |                        |
      |                        |                 submit_contribution()
      |                        |                   -> MergeProposal x 2
      |                        |                        |
      |                        |                 execute_merge()
      |                        |                   CoordinateBlock.tick({
      |                        |                     proposals: [
      |                        |                       {nursery_alpha: top-8 kernels},
      |                        |                       {nursery_beta: top-8 kernels},
      |                        |                     ]
      |                        |                   })
      |                        |                        |
      |                        |                 BFT consensus: 2/2 agree
      |                        |                   -> 14 kernels accepted
      |                        |                   -> 2 rejected (low diversity)
      |                        |                        |
      |                        |                 HuggingFaceDeployer
      |                        |                   .deploy(merge_result)
      |                        |                        |
      |                        |                   Push to HF Hub:
      |                        |                     personality_kernels.safetensors
      |                        |                     navigation_embeddings/
      |                        |                     threat_signatures/
```

### 10.5 Complete System Data Flow Summary

```
[User Request]
       |
       v
  (1) TaskAPI validates + authenticates (Layer 1: KO tongue)
       |
       v
  (2) AgentOrchestrator assigns kernel (CSTM personality match)
       |
       v
  (3) NavigationEngine initializes (PLAN, SENSE, STEER, DECIDE created)
       |
       v
  +-->(4) SENSE: Kalman-filter page observation (Layer 9)
  |        |
  |        v
  |   (5) PLAN: A* over URL graph if replan needed (Layer 6)
  |        |
  |        v
  |   (6) STEER: PID error correction (Layer 8)
  |        |
  |        v
  |   (7) DECIDE: Behaviour tree selects action (Layer 7)
  |        |
  |        v
  |   (8) SemanticAntivirus scans (Layers 3, 5, 10, 13)
  |        |
  |        v
  |   (9) GovernanceGate evaluates (Layers 8, 11, 13)
  |        |       |
  |    [ALLOW]  [DENY]
  |        |       |
  |        v       v
  |   (10a)    (10b) RecoveryPad or alternative (Layer 11: DR tongue)
  |   WebPollyPad.actuate()
  |        |
  |        v
  |   (11) H(d,pd) updated (Layer 8)
  |        |
  |        v
  |   (12) TelemetryBridge.emit() (Layer 14)
  |        |
  |        v
  |   (13) StateManager.checkpoint() if interval reached (Layer 5)
  |        |
  |        v
  |   (14) WebSocket update to user
  |        |
  +--------+ (loop until goal reached or limit hit)
       |
       v
  (15) TaskResult returned via API
       |
       v
  (16) Session telemetry archived
       |
       v
  [User receives result]
```

---

## Appendix A: Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Browser Automation | Playwright (async) | Cross-browser, headless support, CDP access |
| API Framework | FastAPI + Uvicorn | Async-native, WebSocket support, auto-docs |
| State Store (hot) | Redis | Sub-millisecond session state access |
| State Store (cold) | PostgreSQL | Durable task/kernel storage, JSONB for flexibility |
| Object Store | S3-compatible (MinIO for dev) | Checkpoint blobs, screenshots |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | 384D page/URL embeddings |
| Threat Index | FAISS | Fast similarity search for threat embeddings |
| Model Hub | HuggingFace Hub + Inference Endpoints | Standard deployment, safetensors format |
| PQ Crypto | liboqs (ML-DSA-65, ML-KEM-768) | Post-quantum signing and encryption |
| Serialization | safetensors (weights), zstd (checkpoints), JSON (config) | Safe, fast, compact |
| Container | Docker + Docker Compose | Consistent deployment |
| CI/CD | GitHub Actions | Existing repo infrastructure |

## Appendix B: Hamiltonian Safety Score Reference

The Hamiltonian safety function H(d, pd) = 1 / (1 + d + 2*pd) is the universal safety metric throughout the SCBE Web Agent. This appendix provides reference values.

**Variable definitions:**
- d: Cosine distance of agent's 21D personality vector from safety centroid [0.5]^21. Range: [0.0, 1.0].
- pd: Proportion of recent actions classified as unsafe. Range: [0.0, 1.0].

**Reference table:**

| d | pd | H(d, pd) | Safety Level |
|---|---|---------|----|
| 0.0 | 0.0 | 1.000 | Maximum safety: agent at centroid, no unsafe actions |
| 0.1 | 0.0 | 0.909 | High safety: slight personality drift |
| 0.2 | 0.1 | 0.714 | Good safety: moderate drift, few unsafe actions |
| 0.3 | 0.2 | 0.588 | Acceptable: approaching caution threshold |
| 0.4 | 0.3 | 0.500 | Threshold: some pads restricted |
| 0.5 | 0.4 | 0.370 | Warning: significant restriction |
| 0.6 | 0.5 | 0.345 | Critical: RecoveryPad activated |
| 0.8 | 0.6 | 0.294 | Emergency: most pads blocked |
| 1.0 | 1.0 | 0.250 | Minimum: agent fully diverged, all actions unsafe |

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **Concept Block** | Abstract processing unit (PLAN, SENSE, STEER, DECIDE, COORDINATE) with tick/reset/configure lifecycle |
| **CSTM** | Choice Script Training Matrix -- nursery system for training agents via interactive fiction |
| **GraduatedKernel** | Portable personality artifact extracted from a trained agent after graduation |
| **Hamiltonian** | Safety function H(d,pd) = 1/(1+d+2*pd) governing all agent operations |
| **Polly Pad** | Actuator surface that translates governance decisions into real-world (browser) actions |
| **Sacred Tongue** | Domain separation protocol (KO, AV, RU, CA, UM, DR) providing isolation between operational domains |
| **Modality Mask** | Harmonic overtone filter (STRICT, ADAPTIVE, PROBE) controlling governance strictness |
| **Snap Protocol** | Geometric validation on the Riemannian torus manifold preventing discontinuous state transitions |
| **BFT Consensus** | Byzantine Fault Tolerant voting (n >= 3f+1) used for multi-agent coordination and federated merges |
| **Personality Vector** | 21D vector encoding cognitive, ethical, social, executive, motivational, emotional, and meta traits |
| **NavigationStep** | One iteration of the SENSE->STEER->DECIDE->ACTUATE loop |
| **ThreatReport** | Aggregated output of SemanticAntivirus scanning |
| **GovernanceVerdict** | Output of the 14-layer governance evaluation (ALLOW/DENY/QUARANTINE/ESCALATE) |

---

*This document describes the architecture of the SCBE Web Agent under the SCBE-AETHERMOORE 14-Layer AI Governance Framework (USPTO #63/961,403). All components operate within the governance boundary. There is no ungoverned path from task submission to browser action.*
