"""Pre-tool policy enforcement aligned with ``tool_contracts`` + ``permission_profiles``.

Callers (GeoSeal CLI, HTTP bridge) classify a surface into a harness *tool class*
then evaluate whether the active ``permission_mode`` permits it. This mirrors
the manifest fields emitted by ``build_agent_harness_manifest_v1`` without
requiring agents to re-derive rules from prose.
"""

from __future__ import annotations

import os
from typing import Any

from src.coding_spine.agent_tool_bridge import _permission_profiles, _tool_contracts


def tool_contracts_public() -> list[dict[str, Any]]:
    """Stable copy for tests and diagnostics."""

    return list(_tool_contracts())


def permission_profiles_public() -> list[dict[str, Any]]:
    return list(_permission_profiles())


def geoseal_command_to_tool_class(command: str, *, execute: bool = False) -> str:
    """Map a GeoSeal HTTP/CLI subcommand to a harness tool class."""

    c = (command or "").strip().lower().replace("_", "-")
    if c == "loop-dispatch":
        return "network_or_cloud" if execute else "read"
    if c == "testing-cli":
        return "execute_tests" if execute else "read"
    if c in (
        "code-packet",
        "explain-route",
        "backend-registry",
        "agent-harness",
        "compile",
        "skill-tools",
        "hydra-bridge",
        "call-switchboard",
        "lightning-indexer",
        "agentic-training-loop",
        "history",
    ):
        return "read"
    if c == "replay":
        return "execute_tests"
    if c == "project-scaffold":
        return "write_workspace"
    if c == "code-roundtrip":
        return "execute_tests" if execute else "read"
    return "read"


def evaluate_harness_tool_policy(
    *,
    permission_mode: str,
    tool_class: str,
    cloud_dispatch_approval: str | None = None,
) -> dict[str, Any]:
    """Return whether the tool class is allowed for this permission profile.

    Rules (derived from ``_permission_profiles``):
    - If the tool class is in ``blocks``, decision is DENY.
    - If it is in ``allows``, decision is ALLOW.
    - If it appears only under ``requires_approval``, ALLOW only when
      ``SCBE_POLICY_APPROVE_CLOUD_DISPATCH`` is truthy (1/true/yes/on).

    Args:
        cloud_dispatch_approval: When not ``None``, used instead of
            ``os.environ["SCBE_POLICY_APPROVE_CLOUD_DISPATCH"]`` for the
            requires_approval branch (deterministic tests / MC/DC). Production
            callers should omit this and set the env var when needed.
    """

    mode = (permission_mode or "observe").strip().lower()
    tc = (tool_class or "read").strip().lower()
    profiles = {str(p["mode"]).strip().lower(): p for p in _permission_profiles()}
    profile = profiles.get(mode)
    base: dict[str, Any] = {
        "schema_version": "scbe_agent_tool_policy_v1",
        "permission_mode": mode,
        "tool_class": tc,
    }
    if not profile:
        return {
            **base,
            "ok": False,
            "decision": "DENY",
            "reason": f"unknown permission_mode {mode!r}",
        }

    blocks = {str(x).strip().lower() for x in profile.get("blocks", [])}
    allows = {str(x).strip().lower() for x in profile.get("allows", [])}
    requires = {str(x).strip().lower() for x in profile.get("requires_approval", [])}

    if tc in blocks:
        return {
            **base,
            "ok": False,
            "decision": "DENY",
            "reason": f"{tc!r} is blocked in permission_mode={mode!r}",
        }

    if tc in allows:
        return {**base, "ok": True, "decision": "ALLOW", "reason": "profile_allows"}

    if tc in requires:
        if cloud_dispatch_approval is not None:
            env = str(cloud_dispatch_approval).strip().lower()
        else:
            env = (
                os.environ.get("SCBE_POLICY_APPROVE_CLOUD_DISPATCH", "").strip().lower()
            )
        if env in ("1", "true", "yes", "on"):
            return {
                **base,
                "ok": True,
                "decision": "ALLOW",
                "reason": "requires_approval_satisfied_via_SCBE_POLICY_APPROVE_CLOUD_DISPATCH",
            }
        return {
            **base,
            "ok": False,
            "decision": "QUARANTINE",
            "reason": (
                f"{tc!r} requires explicit approval in permission_mode={mode!r}; "
                "set SCBE_POLICY_APPROVE_CLOUD_DISPATCH=1"
            ),
        }

    return {
        **base,
        "ok": False,
        "decision": "DENY",
        "reason": f"{tc!r} is not listed as allowed for permission_mode={mode!r}",
    }
