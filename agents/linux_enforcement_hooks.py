"""
Linux enforcement hooks for SCBE kernel antivirus decisions.

This module turns a Linux bridge decision into deterministic command emitters
and structured backend actions. Host-specific execution is delegated to
hardened adapters (systemd/journald/SOC) instead of running raw shell strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import shlex
import time

from agents.linux_enforcement_backends import (
    DEFAULT_BACKEND_NAMES,
    EnforcementAction,
    EnforcementBackend,
    build_enforcement_backends,
)
from agents.linux_kernel_event_bridge import LinuxBridgeDecision


@dataclass(frozen=True)
class LinuxEnforcementPlan:
    process_key: str
    kernel_action: str
    commands: tuple[str, ...]
    rationale: str
    dry_run: bool
    applied: bool
    failures: tuple[str, ...]
    cooldown_skipped: bool
    backend_names: tuple[str, ...]
    backend_details: tuple[str, ...]
    action: EnforcementAction | None

    def to_dict(self) -> dict[str, object]:
        return {
            "process_key": self.process_key,
            "kernel_action": self.kernel_action,
            "commands": list(self.commands),
            "rationale": self.rationale,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "failures": list(self.failures),
            "cooldown_skipped": self.cooldown_skipped,
            "backend_names": list(self.backend_names),
            "backend_details": list(self.backend_details),
            "action": (self.action.to_dict() if self.action is not None else None),
        }


def _render(argv: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(x) for x in argv)


def _is_probable_path(target: str) -> bool:
    return target.startswith("/") and "->" not in target


class LinuxEnforcementHooks:
    """
    Build and optionally apply Linux enforcement actions from bridge decisions.
    """

    def __init__(
        self,
        *,
        apply_enforcement: bool = False,
        quarantine_dir: str = "/var/quarantine/scbe",
        cooldown_seconds: float = 15.0,
        backends: tuple[EnforcementBackend, ...] | None = None,
        now_fn: Callable[[], float] | None = None,
    ):
        self.apply_enforcement = bool(apply_enforcement)
        self.quarantine_dir = quarantine_dir
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self.backends = tuple(backends or build_enforcement_backends(DEFAULT_BACKEND_NAMES))
        self._now_fn = now_fn or time.time
        self._last_action_at: dict[str, float] = {}

    def _process_key(self, decision: LinuxBridgeDecision) -> str:
        evt = decision.kernel_event
        return f"{evt.host}:{evt.pid}:{evt.process_name}"

    def _commands_for_action(self, decision: LinuxBridgeDecision) -> tuple[tuple[str, ...], ...]:
        evt = decision.kernel_event
        pid = str(evt.pid)
        target = (evt.target or "").strip()
        action = decision.result.kernel_action

        commands: list[tuple[str, ...]] = []
        if action == "ALLOW":
            return tuple(commands)

        if action == "THROTTLE":
            commands.append(("renice", "+10", "-p", pid))
            return tuple(commands)

        if action == "KILL":
            commands.append(("kill", "-KILL", pid))
            return tuple(commands)

        if action in {"QUARANTINE", "HONEYPOT"}:
            # Freeze process first, then isolate artifacts where possible.
            commands.append(("kill", "-STOP", pid))
            commands.append(("mkdir", "-p", self.quarantine_dir))
            if _is_probable_path(target):
                src = Path(target)
                quarantined_name = f"{evt.process_name}-{evt.pid}-{src.name}"
                dest = str(Path(self.quarantine_dir) / quarantined_name)
                commands.append(("cp", "--", target, dest))
                commands.append(("chmod", "000", target))
            return tuple(commands)

        # Fallback for unknown action classes.
        commands.append(("kill", "-STOP", pid))
        return tuple(commands)

    def _cooldown_hit(self, key: str) -> bool:
        if self.cooldown_seconds <= 0.0:
            return False
        now = float(self._now_fn())
        prev = self._last_action_at.get(key)
        if prev is not None and (now - prev) < self.cooldown_seconds:
            return True
        self._last_action_at[key] = now
        return False

    def _build_action(self, decision: LinuxBridgeDecision, rationale: str) -> EnforcementAction:
        evt = decision.kernel_event
        result = decision.result
        return EnforcementAction(
            process_key=self._process_key(decision),
            kernel_action=result.kernel_action,
            host=evt.host,
            pid=int(evt.pid),
            process_name=evt.process_name,
            operation=evt.operation,
            target=evt.target,
            rationale=rationale,
            quarantine_dir=self.quarantine_dir,
            metadata={
                "decision": result.decision,
                "cell_state": result.cell_state,
                "suspicion": round(float(result.suspicion), 6),
                "block_execution": bool(result.block_execution),
                "isolate_process": bool(result.isolate_process),
                "quarantine_target": bool(result.quarantine_target),
            },
        )

    def plan(self, decision: LinuxBridgeDecision) -> LinuxEnforcementPlan:
        key = self._process_key(decision)
        action = decision.result.kernel_action
        backend_names = tuple(getattr(backend, "name", backend.__class__.__name__) for backend in self.backends)
        if action == "ALLOW":
            return LinuxEnforcementPlan(
                process_key=key,
                kernel_action=action,
                commands=tuple(),
                rationale="no enforcement needed for ALLOW",
                dry_run=not self.apply_enforcement,
                applied=False,
                failures=tuple(),
                cooldown_skipped=False,
                backend_names=backend_names,
                backend_details=tuple(),
                action=None,
            )

        if self._cooldown_hit(key):
            return LinuxEnforcementPlan(
                process_key=key,
                kernel_action=action,
                commands=tuple(),
                rationale="cooldown active; duplicate enforcement suppressed",
                dry_run=not self.apply_enforcement,
                applied=False,
                failures=tuple(),
                cooldown_skipped=True,
                backend_names=backend_names,
                backend_details=tuple(),
                action=None,
            )

        argv_list = self._commands_for_action(decision)
        commands = tuple(_render(argv) for argv in argv_list)
        rationale = f"enforcement mapped from kernel_action={action}"
        return LinuxEnforcementPlan(
            process_key=key,
            kernel_action=action,
            commands=commands,
            rationale=rationale,
            dry_run=not self.apply_enforcement,
            applied=False,
            failures=tuple(),
            cooldown_skipped=False,
            backend_names=backend_names,
            backend_details=tuple(),
            action=self._build_action(decision, rationale),
        )

    def apply(self, plan: LinuxEnforcementPlan) -> LinuxEnforcementPlan:
        if not self.apply_enforcement:
            return plan
        if plan.cooldown_skipped:
            return plan
        if plan.action is None:
            return plan
        if not self.backends:
            return LinuxEnforcementPlan(
                process_key=plan.process_key,
                kernel_action=plan.kernel_action,
                commands=plan.commands,
                rationale=plan.rationale,
                dry_run=False,
                applied=False,
                failures=("no enforcement backends configured",),
                cooldown_skipped=plan.cooldown_skipped,
                backend_names=plan.backend_names,
                backend_details=plan.backend_details,
                action=plan.action,
            )

        failures: list[str] = []
        details: list[str] = []
        any_applied = False
        for backend in self.backends:
            result = backend.apply(plan.action, dry_run=False)
            any_applied = any_applied or bool(result.applied)
            failures.extend(result.failures)
            details.extend(result.details)

        return LinuxEnforcementPlan(
            process_key=plan.process_key,
            kernel_action=plan.kernel_action,
            commands=plan.commands,
            rationale=plan.rationale,
            dry_run=False,
            applied=any_applied,
            failures=tuple(failures),
            cooldown_skipped=plan.cooldown_skipped,
            backend_names=plan.backend_names,
            backend_details=tuple(details),
            action=plan.action,
        )

    def handle(self, decision: LinuxBridgeDecision) -> LinuxEnforcementPlan:
        plan = self.plan(decision)
        return self.apply(plan)
