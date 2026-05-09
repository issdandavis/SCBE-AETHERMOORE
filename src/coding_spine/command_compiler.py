"""SCBE command compiler for agent-bus tool plans.

This is the first practical compiler layer: it does not invent a new language.
It lowers a user/agent intent into a typed, policy-checked command plan over the
existing GeoSeal agent harness.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1
from src.coding_spine.agent_tool_policy import evaluate_harness_tool_policy

_TOOL_COMMAND_KEY = {
    "read": "explain_route_json",
    "execute_tests": "testing_cli_json",
    "write_workspace": "code_packet_json",
    "system_ghost_terminal_audit": "ghost_terminal_audit_ps1",
    "system_ghost_terminal_cleanup": "ghost_terminal_cleanup_stale_ps1",
    "network_or_cloud": None,
    "secrets_or_credentials": None,
    "destructive_filesystem": None,
}


@dataclass(frozen=True)
class CompileRequest:
    intent: str
    permission_mode: str = "observe"
    preferred_language: str = "python"
    requested_tool: str | None = None

    def normalized_intent(self) -> str:
        return re.sub(r"\s+", " ", self.intent.strip())


@dataclass(frozen=True)
class CommandPlan:
    schema_version: str
    intent: dict[str, Any]
    tool: dict[str, Any]
    policy: dict[str, Any]
    command: dict[str, Any]
    strands: dict[str, Any]
    hashes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def infer_tool_class(intent: str, requested_tool: str | None = None) -> str:
    """Infer the smallest useful harness tool class for an intent."""

    if requested_tool:
        return requested_tool.strip().lower().replace("_", "-").replace("-", "_")

    text = intent.lower()
    if _contains_any(text, ("ghost", "terminal", "popup", "popping", "window")):
        if _contains_any(text, ("clean", "kill", "stop", "close")):
            return "system_ghost_terminal_cleanup"
        return "system_ghost_terminal_audit"
    if _contains_any(
        text, ("test", "pytest", "vitest", "lint", "verify", "validate", "check")
    ):
        return "execute_tests"
    if _contains_any(
        text, ("write", "edit", "patch", "build", "implement", "create", "fix")
    ):
        return "write_workspace"
    if _contains_any(
        text, ("github", "vercel", "hugging", "hf", "codespace", "cloud", "deploy")
    ):
        return "network_or_cloud"
    if _contains_any(text, ("secret", "token", "password", "credential", "api key")):
        return "secrets_or_credentials"
    if _contains_any(text, ("delete", "reset", "wipe", "uninstall", "remove")):
        return "destructive_filesystem"
    return "read"


def _tool_contract(manifest: dict[str, Any], tool_class: str) -> dict[str, Any] | None:
    for row in manifest.get("tool_contracts", []):
        if str(row.get("tool", "")).lower() == tool_class:
            return row
    return None


def compile_intent_to_plan(
    *,
    intent: str,
    permission_mode: str = "observe",
    preferred_language: str = "python",
    requested_tool: str | None = None,
) -> dict[str, Any]:
    """Compile intent into a policy-checked agent-bus command plan."""

    req = CompileRequest(
        intent=intent,
        permission_mode=permission_mode,
        preferred_language=preferred_language,
        requested_tool=requested_tool,
    )
    normalized = req.normalized_intent()
    manifest = build_agent_harness_manifest_v1(
        inline_goal=normalized,
        preferred_language=preferred_language,
        permission_mode=permission_mode,
    )
    tool_class = infer_tool_class(normalized, requested_tool=requested_tool)
    policy = evaluate_harness_tool_policy(
        permission_mode=permission_mode,
        tool_class=tool_class,
    )
    command_key = _TOOL_COMMAND_KEY.get(tool_class)
    command_template = (
        manifest.get("geoseal_cli", {}).get(command_key) if command_key else None
    )
    contract = _tool_contract(manifest, tool_class)
    intent_hash = sha256(normalized.encode("utf-8")).hexdigest()
    tool_hash = sha256(tool_class.encode("utf-8")).hexdigest()
    command_hash = sha256((command_template or "").encode("utf-8")).hexdigest()
    plan_hash = sha256(
        json.dumps(
            {
                "intent": normalized,
                "permission_mode": permission_mode,
                "preferred_language": preferred_language,
                "tool_class": tool_class,
                "command_key": command_key,
                "policy_decision": policy["decision"],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    plan = CommandPlan(
        schema_version="scbe_command_plan_v1",
        intent={
            "text": normalized,
            "permission_mode": permission_mode,
            "preferred_language": preferred_language,
            "requested_tool": requested_tool,
        },
        tool={
            "class": tool_class,
            "contract": contract,
        },
        policy=policy,
        command={
            "key": command_key,
            "template": command_template,
            "runnable": bool(policy.get("ok") and command_template),
        },
        strands={
            "forward": "intent -> tool_class -> policy -> command_template",
            "reverse": "command_template -> tool_class -> permission_profile -> intent_hash",
            "converged": bool(
                contract and (command_key is not None or not policy.get("ok"))
            ),
        },
        hashes={
            "intent_sha256": intent_hash,
            "tool_sha256": tool_hash,
            "command_sha256": command_hash,
            "plan_sha256": plan_hash,
        },
    )
    return plan.to_dict()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compile intent into an SCBE agent-bus command plan"
    )
    parser.add_argument("intent", nargs="*", help="Intent text to compile")
    parser.add_argument("--permission-mode", default="observe")
    parser.add_argument("--language", default="python")
    parser.add_argument("--tool", default=None, help="Force a harness tool class")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = compile_intent_to_plan(
        intent=" ".join(args.intent),
        permission_mode=args.permission_mode,
        preferred_language=args.language,
        requested_tool=args.tool,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"{payload['schema_version']} tool={payload['tool']['class']} "
            f"decision={payload['policy']['decision']} runnable={payload['command']['runnable']}"
        )
        if payload["command"]["template"]:
            print(payload["command"]["template"])
    return 0 if payload["policy"]["decision"] != "DENY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
