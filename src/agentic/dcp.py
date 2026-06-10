"""Deploy Condition Packet (DCP) — sealed operating envelope for agentic tasks.

A DCP converts "make this work" into a governed workcell:
  goal + expectations + known_failures + tools + space + storage +
  context_policy + deploy_target + push_pull_rules + completion_gates +
  recovery_routes + watcher_receipt

The watcher receipt is written on *dispatch*, not on completion.
If the agent crashes mid-operation, the receipt already exists and
a restart knows exactly where to resume without replaying full context.

The DCP is also a training artifact: every executed DCP that reaches
a verified terminal state produces a (packet, action_trace, evidence)
triple suitable for SFT/DPO.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ─── Trust / scope enums ─────────────────────────────────────────────────────


class TrustLevel(str, Enum):
    VERIFIED_PRIMARY = "verified_primary"  # official repo / signed release
    VERIFIED_SECONDARY = "verified_secondary"  # known-good mirror / checksum
    UNVERIFIED = "unverified"  # untested external source
    QUARANTINED = "quarantined"  # failed its own contract once
    DENIED = "denied"  # known-bad; never use


class TrustState(str, Enum):
    """Maps to L13 risk decision tiers."""

    ALLOW = "allow"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"
    DENY = "deny"


class ToolScope(str, Enum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"  # allowed but must log every call
    DENIED = "denied"


# ─── Compute / storage enums ─────────────────────────────────────────────────


class ComputeTarget(str, Enum):
    LOCAL = "local"
    CI = "ci"
    CLOUD_RUNNER = "cloud_runner"
    CONTAINER = "container"
    BROWSER = "browser"


class RepoState(str, Enum):
    CLEAN = "clean"  # no uncommitted changes
    DIRTY = "dirty"  # uncommitted changes present
    DETACHED = "detached"  # detached HEAD


class SecretsBoundary(str, Enum):
    LOCAL_ONLY = "local_only"  # secrets never leave the machine
    VAULT = "vault"  # secrets go through a secrets manager
    NONE = "none"  # no secrets in scope


class DeployTargetKind(str, Enum):
    LOCAL = "local"
    PR = "pr"
    MAIN = "main"
    NPM = "npm"
    PYPI = "pypi"
    HUGGING_FACE = "hugging_face"
    VERCEL = "vercel"
    DOCKER = "docker"
    K8S = "k8s"
    CUSTOM = "custom"


# ─── Operation fullness ───────────────────────────────────────────────────────


class FullnessStage(str, Enum):
    """Downstream pipeline stage — a task is only done when it reaches a terminal."""

    LOCAL_CHANGE = "local_change"
    COMMITTED = "committed"
    PUSHED = "pushed"
    PR_CREATED = "pr_created"
    CI_RUNNING = "ci_running"
    CI_COMPLETE = "ci_complete"
    MERGED = "merged"
    DEPLOYED = "deployed"
    VERIFIED = "verified"  # terminal: post-deploy smoke passed


class GateResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    PENDING = "pending"


# ─── Leaf dataclasses ────────────────────────────────────────────────────────


@dataclass
class GoalSpec:
    """What completion means — concrete, not aspirational."""

    description: str
    success_evidence: list[str] = field(default_factory=list)  # commands/artifacts that prove it
    failure_modes: list[str] = field(default_factory=list)  # known ways it can fail to complete


@dataclass
class Expectation:
    """What the user hopes is true — not yet verified."""

    description: str
    verified: bool = False
    verification_command: str | None = None  # command that would prove it


@dataclass
class KnownFailure:
    """Prior breakpoints, flaky tests, weak lanes documented before action starts."""

    id: str
    description: str
    affected_files: list[str] = field(default_factory=list)
    workaround: str | None = None


@dataclass
class FailureSemantics:
    """What a failure means for a given tool/source."""

    tool_failure: str = "the tool wrapper may be broken"
    source_contract_failure: str = "upstream source behavior changed"
    source_integrity_failure: str = "trusted source may no longer be trusted"


@dataclass
class ToolEntry:
    """A tool the agent may use, with its trust level and allowed scope."""

    name: str
    scope: ToolScope = ToolScope.ALLOWED
    trust_level: TrustLevel = TrustLevel.VERIFIED_PRIMARY
    trust_state: TrustState = TrustState.ALLOW
    source_roots: list[str] = field(default_factory=list)
    failure_semantics: FailureSemantics = field(default_factory=FailureSemantics)

    def downgrade(self, reason: str = "") -> ToolEntry:
        """Return a copy quarantined one level down. Does not mutate in place."""
        next_state = {
            TrustState.ALLOW: TrustState.QUARANTINE,
            TrustState.QUARANTINE: TrustState.ESCALATE,
            TrustState.ESCALATE: TrustState.DENY,
            TrustState.DENY: TrustState.DENY,
        }[self.trust_state]
        return ToolEntry(
            name=self.name,
            scope=self.scope,
            trust_level=self.trust_level,
            trust_state=next_state,
            source_roots=self.source_roots,
            failure_semantics=self.failure_semantics,
        )


@dataclass
class ProcessingSpace:
    compute: ComputeTarget = ComputeTarget.LOCAL
    constraints: list[str] = field(default_factory=list)  # e.g. "no network", "read-only fs"


@dataclass
class StorageState:
    repo_state: RepoState = RepoState.CLEAN
    branch: str = "main"
    has_uncommitted_changes: bool = False
    secrets_boundary: SecretsBoundary = SecretsBoundary.LOCAL_ONLY
    artifact_paths: list[str] = field(default_factory=list)


@dataclass
class ContextPolicy:
    """What the agent keeps hot, what it compacts, what it pulls on demand."""

    active_keys: list[str] = field(default_factory=list)  # stay in live context
    compactable: list[str] = field(default_factory=list)  # can be summarized away
    pull_on_demand: list[str] = field(default_factory=list)  # retrieve only when needed

    def __post_init__(self) -> None:
        overlap = set(self.active_keys) & set(self.compactable)
        if overlap:
            raise ValueError(f"Keys cannot be both active and compactable: {overlap}")


@dataclass
class DeployTarget:
    kind: DeployTargetKind = DeployTargetKind.LOCAL
    branch: str | None = None
    pr_number: int | None = None
    push_url: str | None = None
    environment: str | None = None  # e.g. "staging", "production"


@dataclass
class PushPullRules:
    can_push: list[str] = field(default_factory=list)  # what is allowed to leave
    must_stay_local: list[str] = field(default_factory=list)  # secrets, keys, creds
    evidence_to_pull: list[str] = field(default_factory=list)  # CI logs, test results, deploy status


@dataclass
class CompletionGate:
    """A verification step that must pass before the task counts as done."""

    id: str
    description: str
    command: str  # exact shell command to run
    expected_exit_code: int = 0
    timeout_seconds: int = 120
    required: bool = True  # if False, failure is a warning not a block
    result: GateResult = GateResult.PENDING
    output: str = ""  # captured stdout/stderr from last run


@dataclass
class RecoveryRoute:
    """What happens when a gate fails."""

    on_gate_id: str  # which gate triggers this route
    action: str  # command or strategy description
    max_retries: int = 1
    cancel_condition: str | None = None  # early-abort: cancel if this is true
    cancel_into: str | None = None  # move to cancel into (like a Tekken cancel window)


@dataclass
class WatcherReceipt:
    """Written on dispatch, not on completion.

    A cheap watcher process reads this file and polls until terminal state,
    then writes a result back — without dragging the full conversation along.
    """

    operation_id: str
    operation_type: str  # "github_pr", "npm_publish", "ci_run", etc.
    fullness_stage: FullnessStage = FullnessStage.LOCAL_CHANGE
    terminal_stages: list[str] = field(default_factory=lambda: ["verified", "denied"])
    watch_command: str = ""  # e.g. "gh pr view 1863 --json state,statusCheckRollup"
    poll_interval_seconds: int = 90
    max_wait_minutes: int = 30
    on_success: str = ""  # action when terminal reached green
    on_failure: str = ""  # action when terminal reached red
    resume_without_full_context: bool = True
    written_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    final_stage: FullnessStage | None = None


# ─── Tool chain: Tekken combo system ─────────────────────────────────────────


@dataclass
class ToolMove:
    """A single move in a tool chain combo.

    frame_advantage: artifact(s) this move produces that give the next move
    a head start — e.g. repo_map.json from build_context_map lets all
    downstream tools skip the scan.
    """

    name: str
    requires: list[str] = field(default_factory=list)  # artifacts/states needed to start
    produces: list[str] = field(default_factory=list)  # artifacts/states this creates
    on_success: list[str] = field(default_factory=list)  # legal next moves
    on_fail: list[str] = field(default_factory=list)  # legal recovery moves
    cancel_condition: str | None = None  # abort early if this evaluates true
    cancel_into: str | None = None  # move to enter if cancel fires
    unsafe_if: list[str] = field(default_factory=list)  # guard conditions that block this move
    recovery: list[str] = field(default_factory=list)  # moves to restore state after failure
    timeout_seconds: int = 120
    frame_advantage: list[str] = field(default_factory=list)  # context artifacts passed forward


@dataclass
class ToolCombo:
    """A named sequence of ToolMoves — a reusable agent macro."""

    name: str
    description: str
    moves: list[ToolMove] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)

    def validate_chain(self) -> list[str]:
        """Return a list of broken links in the combo (move requires X but prior move doesn't produce X)."""
        errors: list[str] = []
        available: set[str] = set()
        for move in self.moves:
            missing = [r for r in move.requires if r not in available]
            if missing:
                errors.append(f"{move.name} requires {missing} but they are not yet produced")
            available.update(move.produces)
            available.update(move.frame_advantage)
        return errors


# ─── Top-level packet ─────────────────────────────────────────────────────────


@dataclass
class DeployConditionPacket:
    """Sealed operating envelope for a single agentic task.

    Fields follow the conversation spec:
      intent → goal → expectations → known_failures → tools →
      processing_space → storage_state → context_policy →
      deploy_target → push_pull_rules → completion_gates →
      recovery_routes → [watcher_receipt written on dispatch]
    """

    # Identity
    packet_id: str
    schema_version: str
    created_at: float

    # What and why
    intent: str
    goal: GoalSpec

    # Pre-conditions
    expectations: list[Expectation] = field(default_factory=list)
    known_failures: list[KnownFailure] = field(default_factory=list)

    # Operating environment
    tools: list[ToolEntry] = field(default_factory=list)
    processing_space: ProcessingSpace = field(default_factory=ProcessingSpace)
    storage_state: StorageState = field(default_factory=StorageState)
    context_policy: ContextPolicy = field(default_factory=ContextPolicy)

    # Destination and movement rules
    deploy_target: DeployTarget = field(default_factory=DeployTarget)
    push_pull_rules: PushPullRules = field(default_factory=PushPullRules)

    # Verification
    completion_gates: list[CompletionGate] = field(default_factory=list)
    recovery_routes: list[RecoveryRoute] = field(default_factory=list)

    # Async tracking — stamp before dispatch
    watcher_receipt: WatcherReceipt | None = None

    def stamp_watcher_receipt(
        self,
        operation_type: str,
        watch_command: str,
        *,
        on_success: str = "",
        on_failure: str = "",
        poll_interval_seconds: int = 90,
        max_wait_minutes: int = 30,
    ) -> WatcherReceipt:
        """Create and attach the watcher receipt. Call this BEFORE the push.

        If the agent crashes after this point, the receipt exists and a restart
        can poll to completion without replaying full context.
        """
        receipt = WatcherReceipt(
            operation_id=self.packet_id,
            operation_type=operation_type,
            fullness_stage=FullnessStage.LOCAL_CHANGE,
            watch_command=watch_command,
            on_success=on_success,
            on_failure=on_failure,
            poll_interval_seconds=poll_interval_seconds,
            max_wait_minutes=max_wait_minutes,
        )
        self.watcher_receipt = receipt
        return receipt

    def advance_fullness(self, stage: FullnessStage) -> None:
        """Record downstream progress without full context reload."""
        if self.watcher_receipt is not None:
            self.watcher_receipt.fullness_stage = stage
            if stage in (FullnessStage.VERIFIED,):
                self.watcher_receipt.completed_at = time.time()
                self.watcher_receipt.final_stage = stage

    def required_gates_pending(self) -> list[CompletionGate]:
        return [g for g in self.completion_gates if g.required and g.result == GateResult.PENDING]

    def required_gates_failed(self) -> list[CompletionGate]:
        return [g for g in self.completion_gates if g.required and g.result == GateResult.FAIL]

    def is_complete(self) -> bool:
        """True only when all required gates have passed."""
        return all(g.result == GateResult.PASS for g in self.completion_gates if g.required)

    def recovery_for(self, gate_id: str) -> list[RecoveryRoute]:
        return [r for r in self.recovery_routes if r.on_gate_id == gate_id]

    def tool(self, name: str) -> ToolEntry | None:
        return next((t for t in self.tools if t.name == name), None)

    def downgrade_tool(self, name: str) -> bool:
        """Quarantine a tool one trust level down. Returns True if found."""
        for i, t in enumerate(self.tools):
            if t.name == name:
                self.tools[i] = t.downgrade()
                return True
        return False

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeployConditionPacket:
        return _from_dict(data)

    @classmethod
    def from_json(cls, text: str) -> DeployConditionPacket:
        return cls.from_dict(json.loads(text))


# ─── Factory ─────────────────────────────────────────────────────────────────


def create_dcp(
    intent: str,
    goal: GoalSpec,
    *,
    schema_version: str = "dcp-v1",
) -> DeployConditionPacket:
    """Stamp a new Deploy Condition Packet with a fresh UUID and timestamp."""
    return DeployConditionPacket(
        packet_id=str(uuid.uuid4()),
        schema_version=schema_version,
        created_at=time.time(),
        intent=intent,
        goal=goal,
    )


def validate_dcp(dcp: DeployConditionPacket) -> list[str]:
    """Return a list of validation errors. Empty list = valid."""
    errors: list[str] = []

    if not dcp.intent.strip():
        errors.append("intent must not be empty")

    if not dcp.goal.description.strip():
        errors.append("goal.description must not be empty")

    if not dcp.completion_gates:
        errors.append("at least one completion gate is required")

    gate_ids = {g.id for g in dcp.completion_gates}
    for route in dcp.recovery_routes:
        if route.on_gate_id not in gate_ids:
            errors.append(f"recovery route references unknown gate: {route.on_gate_id!r}")

    for tool in dcp.tools:
        if tool.trust_state == TrustState.DENY and tool.scope == ToolScope.ALLOWED:
            errors.append(f"tool {tool.name!r} is DENY trust but scope is ALLOWED — fix the scope")

    overlap = set(dcp.context_policy.active_keys) & set(dcp.context_policy.compactable)
    if overlap:
        errors.append(f"context_policy: keys in both active and compactable: {overlap}")

    return errors


# ─── Built-in combos ─────────────────────────────────────────────────────────


CLEAN_PR_COMBO = ToolCombo(
    name="clean_pr",
    description="Standard PR flow: format → lint → test → security → commit → push → PR",
    required_tools=["shell", "git", "github"],
    moves=[
        ToolMove(
            name="format",
            produces=["formatted_files"],
            on_success=["lint"],
            on_fail=["triage_format_error"],
            timeout_seconds=60,
        ),
        ToolMove(
            name="lint",
            requires=["formatted_files"],
            produces=["lint_report"],
            on_success=["test"],
            on_fail=["triage_lint_error"],
            cancel_condition="dirty_unrelated_files",
            recovery=["format", "re_lint"],
            timeout_seconds=60,
            frame_advantage=["lint_report"],
        ),
        ToolMove(
            name="test",
            requires=["lint_report"],
            produces=["test_report"],
            on_success=["security_check"],
            on_fail=["triage_test_failure"],
            cancel_condition="lint_failure_detected",
            cancel_into="triage_lint_error",
            timeout_seconds=300,
            frame_advantage=["test_report"],
        ),
        ToolMove(
            name="security_check",
            requires=["test_report"],
            produces=["security_report"],
            on_success=["commit"],
            on_fail=["block_on_security"],
            unsafe_if=["secrets_in_diff"],
            timeout_seconds=120,
        ),
        ToolMove(
            name="commit",
            requires=["security_report"],
            produces=["commit_sha"],
            on_success=["push"],
            on_fail=["triage_commit_error"],
            unsafe_if=["detached_head"],
            timeout_seconds=30,
        ),
        ToolMove(
            name="push",
            requires=["commit_sha"],
            produces=["remote_ref"],
            on_success=["pr_create"],
            on_fail=["triage_push_error"],
            timeout_seconds=60,
        ),
        ToolMove(
            name="pr_create",
            requires=["remote_ref"],
            produces=["pr_number", "watcher_receipt"],
            on_success=["watch_ci"],
            on_fail=["triage_pr_error"],
            frame_advantage=["watcher_receipt"],
            timeout_seconds=30,
        ),
        ToolMove(
            name="watch_ci",
            requires=["watcher_receipt"],
            produces=["ci_result"],
            on_success=["sync_main"],
            on_fail=["fetch_failed_job_log"],
            timeout_seconds=1800,
        ),
    ],
)

BENCHMARK_COMBO = ToolCombo(
    name="benchmark",
    description="Load task → run agent → run harness → score → triage → rerun if needed",
    required_tools=["shell", "benchmark_harness"],
    moves=[
        ToolMove(
            name="load_task",
            produces=["task_packet"],
            on_success=["run_agent"],
            on_fail=["abort_missing_task"],
            timeout_seconds=30,
        ),
        ToolMove(
            name="run_agent",
            requires=["task_packet"],
            produces=["patch"],
            on_success=["run_harness"],
            on_fail=["triage_agent_failure"],
            timeout_seconds=600,
        ),
        ToolMove(
            name="run_harness",
            requires=["patch"],
            produces=["score_packet"],
            on_success=["record_score"],
            on_fail=["triage_harness_failure"],
            frame_advantage=["score_packet"],
            timeout_seconds=300,
        ),
        ToolMove(
            name="record_score",
            requires=["score_packet"],
            produces=["score_record"],
            on_success=[],
            on_fail=["triage_record_error"],
            timeout_seconds=30,
        ),
    ],
)


# ─── Serialization helpers ────────────────────────────────────────────────────


def _to_dict(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
    return obj


def _from_dict(data: dict[str, Any]) -> DeployConditionPacket:
    def parse_goal(d: dict) -> GoalSpec:
        return GoalSpec(**d)

    def parse_expectation(d: dict) -> Expectation:
        return Expectation(**d)

    def parse_known_failure(d: dict) -> KnownFailure:
        return KnownFailure(**d)

    def parse_failure_semantics(d: dict) -> FailureSemantics:
        return FailureSemantics(**d)

    def parse_tool(d: dict) -> ToolEntry:
        return ToolEntry(
            name=d["name"],
            scope=ToolScope(d.get("scope", "allowed")),
            trust_level=TrustLevel(d.get("trust_level", "verified_primary")),
            trust_state=TrustState(d.get("trust_state", "allow")),
            source_roots=d.get("source_roots", []),
            failure_semantics=parse_failure_semantics(d.get("failure_semantics", {})),
        )

    def parse_processing_space(d: dict) -> ProcessingSpace:
        return ProcessingSpace(
            compute=ComputeTarget(d.get("compute", "local")),
            constraints=d.get("constraints", []),
        )

    def parse_storage_state(d: dict) -> StorageState:
        return StorageState(
            repo_state=RepoState(d.get("repo_state", "clean")),
            branch=d.get("branch", "main"),
            has_uncommitted_changes=d.get("has_uncommitted_changes", False),
            secrets_boundary=SecretsBoundary(d.get("secrets_boundary", "local_only")),
            artifact_paths=d.get("artifact_paths", []),
        )

    def parse_context_policy(d: dict) -> ContextPolicy:
        return ContextPolicy(
            active_keys=d.get("active_keys", []),
            compactable=d.get("compactable", []),
            pull_on_demand=d.get("pull_on_demand", []),
        )

    def parse_deploy_target(d: dict) -> DeployTarget:
        return DeployTarget(
            kind=DeployTargetKind(d.get("kind", "local")),
            branch=d.get("branch"),
            pr_number=d.get("pr_number"),
            push_url=d.get("push_url"),
            environment=d.get("environment"),
        )

    def parse_push_pull_rules(d: dict) -> PushPullRules:
        return PushPullRules(**d)

    def parse_gate(d: dict) -> CompletionGate:
        return CompletionGate(
            id=d["id"],
            description=d["description"],
            command=d["command"],
            expected_exit_code=d.get("expected_exit_code", 0),
            timeout_seconds=d.get("timeout_seconds", 120),
            required=d.get("required", True),
            result=GateResult(d.get("result", "pending")),
            output=d.get("output", ""),
        )

    def parse_recovery(d: dict) -> RecoveryRoute:
        return RecoveryRoute(**d)

    def parse_watcher(d: dict | None) -> WatcherReceipt | None:
        if d is None:
            return None
        return WatcherReceipt(
            operation_id=d["operation_id"],
            operation_type=d["operation_type"],
            fullness_stage=FullnessStage(d.get("fullness_stage", "local_change")),
            terminal_stages=d.get("terminal_stages", ["verified", "denied"]),
            watch_command=d.get("watch_command", ""),
            poll_interval_seconds=d.get("poll_interval_seconds", 90),
            max_wait_minutes=d.get("max_wait_minutes", 30),
            on_success=d.get("on_success", ""),
            on_failure=d.get("on_failure", ""),
            resume_without_full_context=d.get("resume_without_full_context", True),
            written_at=d.get("written_at", time.time()),
            completed_at=d.get("completed_at"),
            final_stage=FullnessStage(d["final_stage"]) if d.get("final_stage") else None,
        )

    return DeployConditionPacket(
        packet_id=data["packet_id"],
        schema_version=data["schema_version"],
        created_at=data["created_at"],
        intent=data["intent"],
        goal=parse_goal(data["goal"]),
        expectations=[parse_expectation(e) for e in data.get("expectations", [])],
        known_failures=[parse_known_failure(f) for f in data.get("known_failures", [])],
        tools=[parse_tool(t) for t in data.get("tools", [])],
        processing_space=parse_processing_space(data.get("processing_space", {})),
        storage_state=parse_storage_state(data.get("storage_state", {})),
        context_policy=parse_context_policy(data.get("context_policy", {})),
        deploy_target=parse_deploy_target(data.get("deploy_target", {})),
        push_pull_rules=parse_push_pull_rules(data.get("push_pull_rules", {})),
        completion_gates=[parse_gate(g) for g in data.get("completion_gates", [])],
        recovery_routes=[parse_recovery(r) for r in data.get("recovery_routes", [])],
        watcher_receipt=parse_watcher(data.get("watcher_receipt")),
    )


__all__ = [
    "TrustLevel",
    "TrustState",
    "ToolScope",
    "ComputeTarget",
    "RepoState",
    "SecretsBoundary",
    "DeployTargetKind",
    "FullnessStage",
    "GateResult",
    "GoalSpec",
    "Expectation",
    "KnownFailure",
    "FailureSemantics",
    "ToolEntry",
    "ProcessingSpace",
    "StorageState",
    "ContextPolicy",
    "DeployTarget",
    "PushPullRules",
    "CompletionGate",
    "RecoveryRoute",
    "WatcherReceipt",
    "ToolMove",
    "ToolCombo",
    "DeployConditionPacket",
    "create_dcp",
    "validate_dcp",
    "CLEAN_PR_COMBO",
    "BENCHMARK_COMBO",
]
