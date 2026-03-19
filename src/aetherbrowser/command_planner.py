"""Deterministic command planning for AetherBrowser orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.aetherbrowser.agents import AgentSquad
from src.aetherbrowser.router import ModelProvider, OctoArmorRouter, TaskComplexity


_BROWSER_ACTION_KEYWORDS = {
    "browser",
    "click",
    "fill",
    "form",
    "login",
    "navigate",
    "open",
    "page",
    "scroll",
    "search",
    "site",
    "submit",
    "tab",
    "upload",
}

_READ_ONLY_KEYWORDS = {
    "analyze",
    "browse",
    "extract",
    "inspect",
    "read",
    "research",
    "review",
    "search",
    "snapshot",
    "summarize",
    "title",
}

_AUTH_KEYWORDS = {
    "auth",
    "credential",
    "login",
    "logout",
    "mfa",
    "oauth",
    "otp",
    "password",
    "signin",
    "token",
    "username",
}

_SIDE_EFFECT_KEYWORDS = {
    "approve",
    "buy",
    "checkout",
    "comment",
    "commit",
    "create",
    "delete",
    "deploy",
    "download",
    "fill",
    "grant",
    "install",
    "merge",
    "pay",
    "post",
    "publish",
    "push",
    "register",
    "send",
    "submit",
    "transfer",
    "type",
    "update",
    "upload",
    "write",
}

_HIGH_RISK_KEYWORDS = {
    "bank",
    "billing",
    "buy",
    "checkout",
    "credential",
    "delete",
    "deploy",
    "password",
    "payment",
    "publish",
    "push",
    "submit",
    "transfer",
    "wallet",
}

_SERVICE_HINTS = {
    "github": "github.com",
    "huggingface": "huggingface.co",
    "notion": "notion.so",
    "arxiv": "arxiv.org",
}


@dataclass
class RankedAction:
    label: str
    reason: str
    risk_tier: str
    requires_approval: bool = False
    command_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "reason": self.reason,
            "risk_tier": self.risk_tier,
            "requires_approval": self.requires_approval,
            "command_hint": self.command_hint,
        }


@dataclass
class CommandPlan:
    text: str
    task_type: str
    intent: str
    complexity: TaskComplexity
    provider: str
    selection_reason: str
    fallback_chain: list[str]
    browser_action_required: bool
    escalation_ready: bool
    preferred_engine: str
    targets: list[str]
    risk_tier: str
    review_zone: str | None
    approval_required: bool
    required_approvals: list[str]
    auto_cascade: bool
    next_actions: list[RankedAction]
    assignments: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "task_type": self.task_type,
            "intent": self.intent,
            "complexity": self.complexity.value,
            "provider": self.provider,
            "selection_reason": self.selection_reason,
            "fallback_chain": self.fallback_chain,
            "browser_action_required": self.browser_action_required,
            "escalation_ready": self.escalation_ready,
            "preferred_engine": self.preferred_engine,
            "targets": self.targets,
            "risk_tier": self.risk_tier,
            "review_zone": self.review_zone,
            "approval_required": self.approval_required,
            "required_approvals": self.required_approvals,
            "auto_cascade": self.auto_cascade,
            "next_actions": [action.to_dict() for action in self.next_actions],
            "assignments": [
                {
                    **assignment,
                    "role": assignment["role"].value if hasattr(assignment["role"], "value") else assignment["role"],
                }
                for assignment in self.assignments
            ],
        }

def build_command_plan(
    *,
    text: str,
    squad: AgentSquad,
    router: OctoArmorRouter,
    routing_preferences: dict[str, str | ModelProvider] | None = None,
    auto_cascade: bool = True,
) -> CommandPlan:
    lowered = text.lower()
    tokens = set(_tokenize(text))
    task_type = squad.infer_task_type(text)
    complexity = router.score_complexity(text)
    assignments = squad.decompose(text, task_type=task_type)
    browser_action_required = bool(tokens & _BROWSER_ACTION_KEYWORDS) or task_type == "page"
    intent = _infer_intent(task_type=task_type, lowered=lowered, tokens=tokens)
    targets = _infer_targets(lowered)
    risk_tier, required_approvals = _infer_risk(
        lowered=lowered,
        tokens=tokens,
        browser_action_required=browser_action_required,
    )
    preferred_engine = _select_engine(
        intent=intent,
        browser_action_required=browser_action_required,
        risk_tier=risk_tier,
    )
    routing_complexity = complexity
    if browser_action_required and risk_tier == "low":
        routing_complexity = TaskComplexity.LOW
    elif browser_action_required and risk_tier == "medium" and complexity == TaskComplexity.HIGH:
        routing_complexity = TaskComplexity.MEDIUM
    selection = router.select_model(
        routing_complexity,
        role="KO",
        preference_overrides=routing_preferences,
        allow_fallback=auto_cascade,
    )
    provider_status = router.provider_status_snapshot()
    escalation_ready = any(
        meta["available"] is True and name != "local" for name, meta in provider_status.items()
    )
    approval_required = bool(required_approvals)
    review_zone = _review_zone_for_risk(risk_tier) if approval_required else None
    next_actions = _build_next_actions(
        task_type=task_type,
        intent=intent,
        preferred_engine=preferred_engine,
        targets=targets,
        risk_tier=risk_tier,
        approval_required=approval_required,
    )
    return CommandPlan(
        text=text,
        task_type=task_type,
        intent=intent,
        complexity=complexity,
        provider=selection.provider.value,
        selection_reason=selection.selection_reason,
        fallback_chain=[provider.value for provider in selection.fallback_chain],
        browser_action_required=browser_action_required,
        escalation_ready=escalation_ready,
        preferred_engine=preferred_engine,
        targets=targets,
        risk_tier=risk_tier,
        review_zone=review_zone,
        approval_required=approval_required,
        required_approvals=required_approvals,
        auto_cascade=auto_cascade,
        next_actions=next_actions,
        assignments=assignments,
    )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _infer_intent(*, task_type: str, lowered: str, tokens: set[str]) -> str:
    if tokens & {"login", "signin", "auth"} or "sign in" in lowered:
        return "authenticate"
    if tokens & {"checkout", "payment", "pay", "buy"}:
        return "checkout"
    if tokens & {"publish", "post", "submit", "upload"}:
        return "submit_changes"
    if tokens & {"fill", "type", "update", "write", "create"}:
        return "edit_page"
    if task_type == "research":
        return "research"
    if task_type == "page":
        return "analyze_page"
    if tokens & {"open", "navigate", "browse"}:
        return "navigate"
    return "general_assist"


def _infer_targets(lowered: str) -> list[str]:
    targets: list[str] = []
    for hint, domain in _SERVICE_HINTS.items():
        if hint in lowered and domain not in targets:
            targets.append(domain)
    for match in re.findall(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", lowered):
        if match not in targets:
            targets.append(match)
    return targets


def _infer_risk(*, lowered: str, tokens: set[str], browser_action_required: bool) -> tuple[str, list[str]]:
    approvals: list[str] = []
    if tokens & _AUTH_KEYWORDS or "sign in" in lowered or "log in" in lowered:
        approvals.append("Uses authentication or credentials")
    if tokens & _SIDE_EFFECT_KEYWORDS:
        approvals.append("Performs a state-changing browser action")
    if tokens & _HIGH_RISK_KEYWORDS:
        approvals.append("Touches a high-impact flow such as payment, publish, deploy, push, or delete")

    if not approvals and browser_action_required and not (tokens & _READ_ONLY_KEYWORDS):
        approvals.append("Browser action is not clearly read-only")

    unique_approvals = list(dict.fromkeys(approvals))
    if any(token in _HIGH_RISK_KEYWORDS for token in tokens):
        return "high", unique_approvals
    if unique_approvals:
        return "medium", unique_approvals
    return "low", []


def _select_engine(*, intent: str, browser_action_required: bool, risk_tier: str) -> str:
    if intent in {"authenticate", "checkout", "submit_changes"}:
        return "playwright"
    if browser_action_required and risk_tier == "low":
        return "playwright"
    return "playwright"


def _review_zone_for_risk(risk_tier: str) -> str | None:
    if risk_tier == "high":
        return "RED"
    if risk_tier == "medium":
        return "YELLOW"
    return None


def _build_next_actions(
    *,
    task_type: str,
    intent: str,
    preferred_engine: str,
    targets: list[str],
    risk_tier: str,
    approval_required: bool,
) -> list[RankedAction]:
    target_text = targets[0] if targets else "the target surface"
    route_hint = (
        f"python scripts/system/browser_chain_dispatcher.py --domain {target_text} --task {intent} --engine {preferred_engine}"
        if targets
        else f"Route the task through the dispatcher with {preferred_engine}"
    )
    actions = [
        RankedAction(
            label="Route through the browser dispatcher",
            reason=f"Start from the governed {preferred_engine} lane before touching a live page.",
            risk_tier="low",
            command_hint=route_hint,
        ),
        RankedAction(
            label="Capture title and snapshot evidence",
            reason="Preserve proof before deeper movement or extraction.",
            risk_tier="low",
        ),
    ]

    if task_type == "research":
        actions.append(
            RankedAction(
                label="Use site-native search and gather approved sources",
                reason="Research flows should start from the target service instead of unmanaged generic browsing.",
                risk_tier="low",
            )
        )
    elif approval_required:
        actions.append(
            RankedAction(
                label="Hold state-changing action for review",
                reason="The requested action changes state or touches credentials, so it should stay in the deliberate lane.",
                risk_tier=risk_tier,
                requires_approval=True,
            )
        )
    else:
        actions.append(
            RankedAction(
                label=f"Proceed with {intent.replace('_', ' ')}",
                reason="The request appears read-only and can stay in the fast lane.",
                risk_tier=risk_tier,
            )
        )

    return actions
