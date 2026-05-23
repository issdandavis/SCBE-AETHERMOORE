"""Deploy Condition Packet routes for GitHub and Copilot-assisted work.

These helpers turn common agentic operations into sealed DCPs with:
- approved tool sources,
- exact shell/GitHub commands,
- completion gates,
- watcher receipts written before dispatch,
- Copilot as a proposer route, never as the completion judge.
"""

from __future__ import annotations

import shlex
import math
from dataclasses import dataclass, field

from .dcp import (
    CompletionGate,
    ComputeTarget,
    ContextPolicy,
    DeployConditionPacket,
    DeployTarget,
    DeployTargetKind,
    FailureSemantics,
    FullnessStage,
    GoalSpec,
    KnownFailure,
    ProcessingSpace,
    PushPullRules,
    RecoveryRoute,
    RepoState,
    SecretsBoundary,
    StorageState,
    ToolCombo,
    ToolEntry,
    ToolMove,
    ToolScope,
    TrustLevel,
    TrustState,
    create_dcp,
)

DEFAULT_REPO = "issdandavis/SCBE-AETHERMOORE"


@dataclass(frozen=True)
class CommandRoute:
    """Human-readable command lane that can be attached to docs or a runner."""

    name: str
    description: str
    commands: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OperationPiece:
    """A proposed operation piece.

    This is the Tetris-tree unit: a model, Copilot, or human can propose the
    piece, but it does not execute until a route slot locks it into place.
    geometry_vector is intentionally small and deterministic:
    (context_fit, verification_fit, safety_fit), each in [0, 1].
    """

    name: str
    lane: str
    command: str
    tool_name: str
    requires: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    geometry_vector: tuple[float, float, float] = (0.5, 0.5, 0.5)
    risk_score: float = 0.25


@dataclass(frozen=True)
class RouteSlot:
    """A route slot where an operation piece can lock."""

    name: str
    lane: str
    accepts: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)
    geometry_vector: tuple[float, float, float] = (0.5, 0.5, 0.5)
    risk_capacity: float = 0.5


@dataclass(frozen=True)
class LockDecision:
    """Deterministic decision for a proposed piece and slot."""

    piece: str
    slot: str
    locked: bool
    score: float
    reasons: list[str] = field(default_factory=list)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _geometry_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((_clamp01(x) - _clamp01(y)) ** 2 for x, y in zip(a, b, strict=True)))


def lock_operation_piece(piece: OperationPiece, slot: RouteSlot, tools: list[ToolEntry]) -> LockDecision:
    """Decide whether a proposed piece locks into a route slot.

    The lock is deliberately mechanical. It does not ask whether the proposal
    sounds good; it checks:
    - lane compatibility,
    - required artifacts available in the slot,
    - tool trust/scope,
    - risk capacity,
    - geometry fit.
    """

    reasons: list[str] = []
    tool = next((entry for entry in tools if entry.name == piece.tool_name), None)

    if slot.accepts and piece.lane not in slot.accepts:
        reasons.append(f"lane {piece.lane!r} is not accepted by slot {slot.name!r}")

    missing = [requirement for requirement in piece.requires if requirement not in slot.available]
    if missing:
        reasons.append(f"missing required artifacts: {missing}")

    if tool is None:
        reasons.append(f"tool {piece.tool_name!r} is not in the approved bucket")
    elif tool.trust_state == TrustState.DENY or tool.scope == ToolScope.DENIED:
        reasons.append(f"tool {piece.tool_name!r} is not allowed to execute")

    if piece.risk_score > slot.risk_capacity:
        reasons.append(f"risk {piece.risk_score:.3f} exceeds slot capacity {slot.risk_capacity:.3f}")

    distance = _geometry_distance(piece.geometry_vector, slot.geometry_vector)
    geometry_fit = max(0.0, 1.0 - (distance / math.sqrt(3.0)))
    risk_fit = 1.0 if slot.risk_capacity <= 0 else max(0.0, 1.0 - (piece.risk_score / slot.risk_capacity))
    lane_fit = 1.0 if not slot.accepts or piece.lane in slot.accepts else 0.0
    score = round((0.60 * geometry_fit) + (0.25 * risk_fit) + (0.15 * lane_fit), 6)

    if score < 0.55:
        reasons.append(f"geometry score {score:.3f} below lock threshold 0.550")

    return LockDecision(piece=piece.name, slot=slot.name, locked=not reasons, score=score, reasons=reasons)


def route_tetris_tree(
    pieces: list[OperationPiece],
    slots: list[RouteSlot],
    tools: list[ToolEntry],
) -> list[LockDecision]:
    """Greedily lock operation pieces into a route tree.

    Each slot receives the highest-scoring valid piece. Produced artifacts from
    a locked piece become available to downstream slots.
    """

    decisions: list[LockDecision] = []
    remaining = list(pieces)
    carried_artifacts: set[str] = set()

    for slot in slots:
        live_slot = RouteSlot(
            name=slot.name,
            lane=slot.lane,
            accepts=slot.accepts,
            available=[*slot.available, *sorted(carried_artifacts)],
            geometry_vector=slot.geometry_vector,
            risk_capacity=slot.risk_capacity,
        )
        candidates = [lock_operation_piece(piece, live_slot, tools) for piece in remaining]
        locked = [candidate for candidate in candidates if candidate.locked]
        if not locked:
            decisions.append(
                LockDecision(
                    piece="",
                    slot=slot.name,
                    locked=False,
                    score=0.0,
                    reasons=["no proposed piece fit this slot"],
                )
            )
            continue

        best = max(locked, key=lambda candidate: candidate.score)
        decisions.append(best)
        chosen = next(piece for piece in remaining if piece.name == best.piece)
        carried_artifacts.update(chosen.produces)
        remaining = [piece for piece in remaining if piece.name != chosen.name]

    return decisions


def approved_agentic_tools(*, include_copilot: bool = True) -> list[ToolEntry]:
    """Return the approved tools for a GitHub PR workcell.

    Copilot is deliberately restricted. It can produce candidate text or a
    suggested shell command, but its output must go through review, lint, tests,
    and the GitHub watcher before the DCP can complete.
    """

    tools = [
        ToolEntry(
            name="git",
            scope=ToolScope.ALLOWED,
            trust_level=TrustLevel.VERIFIED_PRIMARY,
            trust_state=TrustState.ALLOW,
            source_roots=["https://git-scm.com/", "local git executable"],
            failure_semantics=FailureSemantics(
                tool_failure="local git command failed or repo state changed",
                source_contract_failure="git behavior or repository policy changed",
                source_integrity_failure="signed commit/ref verification should be inspected",
            ),
        ),
        ToolEntry(
            name="github-cli",
            scope=ToolScope.ALLOWED,
            trust_level=TrustLevel.VERIFIED_PRIMARY,
            trust_state=TrustState.ALLOW,
            source_roots=["https://cli.github.com/", "https://github.com/cli/cli"],
            failure_semantics=FailureSemantics(
                tool_failure="gh CLI auth, network, or local extension failed",
                source_contract_failure="GitHub API or gh JSON shape changed",
                source_integrity_failure="GitHub API identity or repo trust boundary should be rechecked",
            ),
        ),
        ToolEntry(
            name="codex-github-mcp",
            scope=ToolScope.RESTRICTED,
            trust_level=TrustLevel.VERIFIED_PRIMARY,
            trust_state=TrustState.ALLOW,
            source_roots=[
                "C:/Users/issda/.codex/config.toml",
                "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN",
            ],
            failure_semantics=FailureSemantics(
                tool_failure="MCP server failed to start or token env var was not visible",
                source_contract_failure="GitHub MCP API surface changed",
                source_integrity_failure="token must be revoked/replaced if exposed outside env storage",
            ),
        ),
        ToolEntry(
            name="shell",
            scope=ToolScope.RESTRICTED,
            trust_level=TrustLevel.VERIFIED_PRIMARY,
            trust_state=TrustState.ALLOW,
            source_roots=["Windows PowerShell", "repository package scripts"],
            failure_semantics=FailureSemantics(
                tool_failure="command failed in the local shell",
                source_contract_failure="repo script contract changed",
                source_integrity_failure="shell output may include secrets and must be scrubbed before push",
            ),
        ),
    ]

    if include_copilot:
        tools.append(
            ToolEntry(
                name="github-copilot",
                scope=ToolScope.RESTRICTED,
                trust_level=TrustLevel.VERIFIED_SECONDARY,
                trust_state=TrustState.ALLOW,
                source_roots=[
                    "https://github.com/features/copilot",
                    "gh extension install github/gh-copilot",
                ],
                failure_semantics=FailureSemantics(
                    tool_failure="Copilot extension unavailable, unauthenticated, or produced unusable output",
                    source_contract_failure="Copilot CLI command contract changed",
                    source_integrity_failure="Copilot output is untrusted generated code until SCBE gates pass",
                ),
            )
        )

    return tools


def github_command_route(
    *,
    branch: str,
    title: str,
    repo: str = DEFAULT_REPO,
    body_file: str = ".scbe/ops/pr_body.md",
) -> CommandRoute:
    """Return the exact GitHub commands for branch-to-PR operation."""

    quoted_title = shlex.quote(title)
    return CommandRoute(
        name="github_pr_commands",
        description="Create, push, inspect, watch, merge-check, and clean a GitHub PR.",
        required_tools=["git", "github-cli"],
        expected_artifacts=["commit_sha", "remote_ref", "pr_url", "ci_status"],
        commands=[
            "git status --short --branch",
            f"git switch -c {shlex.quote(branch)}",
            "git diff --check HEAD",
            "npm run lint",
            "git add <changed paths>",
            f"git commit -m {quoted_title}",
            f"git push -u origin {shlex.quote(branch)}",
            (
                f"gh pr create --repo {shlex.quote(repo)} --head {shlex.quote(branch)} "
                f"--base main --title {quoted_title} --body-file {shlex.quote(body_file)}"
            ),
            "gh pr view --json number,url,state,statusCheckRollup,mergeCommit",
            "gh run watch <run-id> --interval 10",
            "git fetch origin --prune",
            "git switch main",
            "git reset --hard refs/remotes/origin/main",
            f"git branch -d {shlex.quote(branch)}",
            f"git push origin --delete {shlex.quote(branch)}",
        ],
    )


def copilot_command_route(
    *,
    prompt: str,
    target: str = "shell",
) -> CommandRoute:
    """Return a governed Copilot route.

    The route intentionally ends with SCBE verification commands. Copilot can
    suggest commands or explain failures, but it cannot mark work complete.
    """

    quoted_prompt = shlex.quote(prompt)
    quoted_target = shlex.quote(target)
    return CommandRoute(
        name="copilot_proposer_commands",
        description="Use GitHub Copilot as a restricted proposer/explainer under SCBE verification.",
        required_tools=["github-cli", "github-copilot", "shell"],
        expected_artifacts=["candidate_command_or_patch", "review_notes", "test_evidence"],
        commands=[
            "gh extension list",
            "gh extension install github/gh-copilot",
            f"gh copilot suggest {quoted_prompt} --target {quoted_target}",
            f"gh copilot explain {quoted_prompt}",
            "git diff --check HEAD",
            "npm run lint",
            "python -m pytest tests/agentic/test_dcp.py tests/tokenizer/test_domain_tokenizer.py -q",
        ],
    )


GITHUB_COPILOT_PR_COMBO = ToolCombo(
    name="github_copilot_pr",
    description="GitHub PR lane with Copilot as a candidate proposer and SCBE as the judge.",
    required_tools=["git", "github-cli", "github-copilot", "shell"],
    moves=[
        ToolMove(
            name="inspect_repo",
            produces=["repo_state", "branch_state"],
            frame_advantage=["repo_state"],
            on_success=["optional_copilot_suggest"],
            timeout_seconds=30,
        ),
        ToolMove(
            name="optional_copilot_suggest",
            requires=["repo_state"],
            produces=["candidate_suggestion"],
            on_success=["apply_patch"],
            on_fail=["manual_patch"],
            unsafe_if=["secrets_in_prompt", "copilot_unavailable"],
            timeout_seconds=120,
        ),
        ToolMove(
            name="apply_patch",
            requires=["candidate_suggestion"],
            produces=["working_tree_diff"],
            on_success=["verify_local"],
            on_fail=["manual_patch"],
            timeout_seconds=300,
        ),
        ToolMove(
            name="manual_patch",
            requires=["repo_state"],
            produces=["working_tree_diff"],
            on_success=["verify_local"],
            timeout_seconds=300,
        ),
        ToolMove(
            name="verify_local",
            requires=["working_tree_diff"],
            produces=["local_gate_report"],
            on_success=["commit_push_pr"],
            on_fail=["triage_failure"],
            cancel_condition="unrelated_dirty_tree",
            timeout_seconds=600,
            frame_advantage=["local_gate_report"],
        ),
        ToolMove(
            name="commit_push_pr",
            requires=["local_gate_report"],
            produces=["pr_number", "watcher_receipt"],
            on_success=["watch_ci"],
            unsafe_if=["required_gate_failed", "secrets_in_diff"],
            timeout_seconds=180,
            frame_advantage=["watcher_receipt"],
        ),
        ToolMove(
            name="watch_ci",
            requires=["watcher_receipt"],
            produces=["ci_status"],
            on_success=["sync_and_prune"],
            on_fail=["fetch_failed_job_log"],
            timeout_seconds=1800,
        ),
    ],
)


TETRIS_TREE_PR_SLOTS = [
    RouteSlot(
        name="inspect",
        lane="root",
        accepts=["inspect"],
        available=[],
        geometry_vector=(0.90, 0.65, 0.80),
        risk_capacity=0.20,
    ),
    RouteSlot(
        name="propose",
        lane="candidate",
        accepts=["propose"],
        available=["repo_state"],
        geometry_vector=(0.75, 0.55, 0.55),
        risk_capacity=0.45,
    ),
    RouteSlot(
        name="verify",
        lane="gate",
        accepts=["verify"],
        available=["repo_state", "candidate_patch"],
        geometry_vector=(0.80, 0.95, 0.90),
        risk_capacity=0.25,
    ),
    RouteSlot(
        name="publish",
        lane="github",
        accepts=["publish"],
        available=["repo_state", "candidate_patch", "local_gate_report"],
        geometry_vector=(0.60, 0.85, 0.85),
        risk_capacity=0.30,
    ),
]


TETRIS_TREE_PR_PIECES = [
    OperationPiece(
        name="git_status_piece",
        lane="inspect",
        command="git status --short --branch",
        tool_name="git",
        produces=["repo_state"],
        geometry_vector=(0.92, 0.60, 0.82),
        risk_score=0.05,
    ),
    OperationPiece(
        name="copilot_candidate_piece",
        lane="propose",
        command='gh copilot suggest "propose the smallest safe patch" --target shell',
        tool_name="github-copilot",
        requires=["repo_state"],
        produces=["candidate_patch"],
        geometry_vector=(0.72, 0.55, 0.50),
        risk_score=0.35,
    ),
    OperationPiece(
        name="local_gate_piece",
        lane="verify",
        command="git diff --check HEAD && npm run lint",
        tool_name="shell",
        requires=["candidate_patch"],
        produces=["local_gate_report"],
        geometry_vector=(0.78, 0.97, 0.88),
        risk_score=0.10,
    ),
    OperationPiece(
        name="github_pr_piece",
        lane="publish",
        command="gh pr create --head <branch> --base main --title <title> --body-file .scbe/ops/pr_body.md",
        tool_name="github-cli",
        requires=["local_gate_report"],
        produces=["pr_number", "watcher_receipt"],
        geometry_vector=(0.62, 0.84, 0.88),
        risk_score=0.20,
    ),
]


def create_github_pr_dcp(
    *,
    intent: str,
    branch: str,
    title: str,
    test_commands: list[str],
    repo: str = DEFAULT_REPO,
    include_copilot: bool = True,
) -> DeployConditionPacket:
    """Create a DCP for a governed GitHub issue/PR task."""

    dcp = create_dcp(
        intent,
        GoalSpec(
            description="Branch pushed, PR opened, local gates pass, CI reaches green, and local main is resynced.",
            success_evidence=[
                "git diff --check HEAD",
                "npm run lint",
                *test_commands,
                "gh pr view --json state,statusCheckRollup,mergeCommit",
            ],
            failure_modes=[
                "dirty unrelated files before patch",
                "Copilot unavailable or produces invalid suggestion",
                "lint or format failure",
                "targeted test failure",
                "CI check failure after merge",
            ],
        ),
    )
    dcp.known_failures = [
        KnownFailure(
            id="copilot-not-judge",
            description="Copilot output can be useful but is not trusted until deterministic gates pass.",
            affected_files=["generated patch", "shell command suggestion"],
            workaround="treat Copilot as a proposer; run SCBE gates and inspect diff before push",
        ),
        KnownFailure(
            id="late-ci-after-merge",
            description="Some GitHub checks complete after auto-merge; completion requires late status polling.",
            workaround="watch PR statusCheckRollup after merge, then sync main and prune only when green",
        ),
    ]
    dcp.tools = approved_agentic_tools(include_copilot=include_copilot)
    dcp.processing_space = ProcessingSpace(
        compute=ComputeTarget.LOCAL,
        constraints=[
            "do not expose secrets to Copilot prompts",
            "do not push generated caches",
            "do not let external proposers decide completion",
        ],
    )
    dcp.storage_state = StorageState(
        repo_state=RepoState.CLEAN,
        branch=branch,
        has_uncommitted_changes=False,
        secrets_boundary=SecretsBoundary.LOCAL_ONLY,
        artifact_paths=[".scbe/ops/", "artifacts/"],
    )
    dcp.context_policy = ContextPolicy(
        active_keys=["intent", "goal", "branch", "completion_gates", "watcher_receipt"],
        compactable=["old terminal output", "prior failed candidate patches"],
        pull_on_demand=["full CI logs", "GitHub PR status", "CodeRabbit status", "Vercel status"],
    )
    dcp.deploy_target = DeployTarget(kind=DeployTargetKind.PR, branch=branch, push_url=f"https://github.com/{repo}")
    dcp.push_pull_rules = PushPullRules(
        can_push=["source changes", "tests", "docs", "workflow fixes", "DCP receipts"],
        must_stay_local=[
            "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN",
            ".env",
            "config/connector_oauth/.env.connector.oauth",
            ".home/.codex",
        ],
        evidence_to_pull=["statusCheckRollup", "failed job logs", "merge commit", "local smoke output"],
    )

    dcp.completion_gates = [
        CompletionGate(
            id="diff_check",
            description="No trailing whitespace or conflict markers in staged diff",
            command="git diff --check HEAD",
            timeout_seconds=30,
        ),
        CompletionGate(
            id="lint",
            description="TypeScript formatting/lint check passes",
            command="npm run lint",
            timeout_seconds=180,
        ),
        *[
            CompletionGate(
                id=f"test_{index + 1}",
                description=f"Targeted test command {index + 1} passes",
                command=command,
                timeout_seconds=600,
            )
            for index, command in enumerate(test_commands)
        ],
        CompletionGate(
            id="github_pr_green",
            description="GitHub PR has no failed required checks",
            command=f"gh pr view --repo {repo} --json state,statusCheckRollup,mergeCommit,url",
            timeout_seconds=120,
        ),
    ]
    dcp.recovery_routes = [
        RecoveryRoute(
            on_gate_id="diff_check", action="normalize line endings or remove conflict markers", max_retries=2
        ),
        RecoveryRoute(on_gate_id="lint", action="run formatter/linter, inspect diff, rerun lint", max_retries=2),
        RecoveryRoute(
            on_gate_id="github_pr_green", action="fetch failed job log with gh run view --log", max_retries=3
        ),
    ]
    dcp.stamp_watcher_receipt(
        operation_type="github_pr",
        watch_command=f"gh pr view --repo {repo} --json state,statusCheckRollup,mergeCommit,url",
        on_success="sync_main_and_prune_branch",
        on_failure="fetch_failed_job_log_and_downgrade_failed_tool",
        poll_interval_seconds=45,
        max_wait_minutes=30,
    )
    dcp.advance_fullness(FullnessStage.LOCAL_CHANGE)
    return dcp


def route_packet_for_docs(
    *,
    branch: str = "feat/example-dcp-route",
    title: str = "feat(agentic): example governed GitHub route",
    repo: str = DEFAULT_REPO,
) -> dict[str, object]:
    """Build a compact docs-friendly packet with DCP plus command routes."""

    dcp = create_github_pr_dcp(
        intent="ship a governed GitHub PR through SCBE DCP gates",
        branch=branch,
        title=title,
        repo=repo,
        test_commands=[
            "python -m pytest tests/agentic/test_dcp.py tests/agentic/test_dcp_routes.py -q",
            "npx vitest run tests/cross-language/nsm-primes-parity.test.ts",
        ],
    )
    return {
        "dcp": dcp.to_dict(),
        "github": github_command_route(branch=branch, title=title, repo=repo).__dict__,
        "copilot": copilot_command_route(
            prompt="Explain the failing lint/test output and propose a minimal patch"
        ).__dict__,
        "tetris_tree": [
            decision.__dict__
            for decision in route_tetris_tree(
                TETRIS_TREE_PR_PIECES,
                TETRIS_TREE_PR_SLOTS,
                approved_agentic_tools(include_copilot=True),
            )
        ],
    }


__all__ = [
    "CommandRoute",
    "DEFAULT_REPO",
    "GITHUB_COPILOT_PR_COMBO",
    "LockDecision",
    "OperationPiece",
    "RouteSlot",
    "TETRIS_TREE_PR_PIECES",
    "TETRIS_TREE_PR_SLOTS",
    "approved_agentic_tools",
    "copilot_command_route",
    "create_github_pr_dcp",
    "github_command_route",
    "lock_operation_piece",
    "route_packet_for_docs",
    "route_tetris_tree",
]
