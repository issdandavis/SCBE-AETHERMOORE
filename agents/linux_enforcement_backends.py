"""
Hardened Linux enforcement backends for SCBE kernel actions.

These adapters consume structured enforcement actions and avoid executing raw
string commands assembled from untrusted event inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
import json
import logging
import os
import subprocess
import urllib.error
import urllib.request


LOGGER = logging.getLogger("scbe.linux.enforcement")

DEFAULT_BACKEND_NAMES: tuple[str, ...] = ("systemd", "journald")
KNOWN_BACKEND_NAMES: tuple[str, ...] = ("systemd", "journald", "soc")


@dataclass(frozen=True)
class EnforcementAction:
    process_key: str
    kernel_action: str
    host: str
    pid: int
    process_name: str
    operation: str
    target: str
    rationale: str
    quarantine_dir: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_key": self.process_key,
            "kernel_action": self.kernel_action,
            "host": self.host,
            "pid": self.pid,
            "process_name": self.process_name,
            "operation": self.operation,
            "target": self.target,
            "rationale": self.rationale,
            "quarantine_dir": self.quarantine_dir,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class BackendApplyResult:
    backend: str
    applied: bool
    failures: tuple[str, ...] = tuple()
    details: tuple[str, ...] = tuple()


class EnforcementBackend(Protocol):
    name: str

    def apply(self, action: EnforcementAction, *, dry_run: bool) -> BackendApplyResult:
        ...


def parse_backend_names(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return DEFAULT_BACKEND_NAMES
    names = tuple(x.strip().lower() for x in raw.split(",") if x.strip())
    if not names:
        return tuple()
    invalid = [name for name in names if name not in KNOWN_BACKEND_NAMES]
    if invalid:
        raise ValueError(f"unknown enforcement backend(s): {', '.join(invalid)}")
    return names


def _signal_for_action(kernel_action: str) -> str | None:
    action = (kernel_action or "").upper()
    if action == "ALLOW":
        return None
    if action == "KILL":
        return "SIGKILL"
    if action in {"THROTTLE", "QUARANTINE", "HONEYPOT"}:
        return "SIGSTOP"
    return "SIGSTOP"


def _run_systemctl(argv: tuple[str, ...]) -> tuple[int, str]:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    return int(proc.returncode), (proc.stderr or "").strip()


class SystemdEnforcementBackend:
    name = "systemd"

    def __init__(self, *, command_runner: Callable[[tuple[str, ...]], tuple[int, str]] | None = None):
        self._command_runner = command_runner or _run_systemctl

    def apply(self, action: EnforcementAction, *, dry_run: bool) -> BackendApplyResult:
        signal = _signal_for_action(action.kernel_action)
        if signal is None:
            return BackendApplyResult(backend=self.name, applied=False, details=("allow action; no systemd kill",))
        if action.pid <= 0:
            return BackendApplyResult(
                backend=self.name,
                applied=False,
                failures=(f"invalid pid for systemd backend: {action.pid}",),
            )

        argv = ("systemctl", "kill", f"--signal={signal}", f"{action.pid}.scope")
        if dry_run:
            return BackendApplyResult(
                backend=self.name,
                applied=False,
                details=(f"dry-run {' '.join(argv)}",),
            )

        rc, stderr = self._command_runner(argv)
        if rc != 0:
            msg = f"{' '.join(argv)} -> exit {rc}"
            if stderr:
                msg = f"{msg}: {stderr}"
            return BackendApplyResult(backend=self.name, applied=True, failures=(msg,))
        return BackendApplyResult(backend=self.name, applied=True, details=(f"applied {' '.join(argv)}",))


class JournaldEnforcementBackend:
    name = "journald"

    def __init__(self, *, sender: Callable[..., Any] | None = None):
        self._sender = sender
        self._sender_name = "custom"
        if self._sender is None:
            try:
                from systemd import journal  # type: ignore

                self._sender = journal.send
                self._sender_name = "systemd.journal.send"
            except Exception:  # noqa: BLE001
                self._sender = None
                self._sender_name = "python-logger-fallback"

    def apply(self, action: EnforcementAction, *, dry_run: bool) -> BackendApplyResult:
        message = {
            "event": "scbe_linux_enforcement",
            "process_key": action.process_key,
            "kernel_action": action.kernel_action,
            "host": action.host,
            "pid": action.pid,
            "process_name": action.process_name,
            "operation": action.operation,
            "target": action.target,
            "rationale": action.rationale,
            "metadata": action.metadata,
        }
        if dry_run:
            return BackendApplyResult(
                backend=self.name,
                applied=False,
                details=("dry-run journald emit",),
            )

        if self._sender is not None:
            try:
                self._sender(
                    MESSAGE=json.dumps(message, separators=(",", ":")),
                    PRIORITY="4",
                    SYSLOG_IDENTIFIER="scbe-linux-enforcement",
                    SCBE_KERNEL_ACTION=action.kernel_action,
                    SCBE_PROCESS_KEY=action.process_key,
                    SCBE_PID=str(action.pid),
                )
                return BackendApplyResult(
                    backend=self.name,
                    applied=True,
                    details=(f"emitted via {self._sender_name}",),
                )
            except Exception as exc:  # noqa: BLE001
                return BackendApplyResult(
                    backend=self.name,
                    applied=True,
                    failures=(f"journald send failed: {exc}",),
                )

        LOGGER.info("scbe_linux_enforcement %s", json.dumps(message, separators=(",", ":")))
        return BackendApplyResult(
            backend=self.name,
            applied=True,
            details=("emitted via python logger fallback",),
        )


class SocSinkEnforcementBackend:
    name = "soc"

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        bearer_token: str | None = None,
        timeout_seconds: float = 3.0,
        urlopen: Callable[..., Any] | None = None,
    ):
        self.endpoint = (endpoint or "").strip()
        self.bearer_token = (bearer_token or "").strip()
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self._urlopen = urlopen or urllib.request.urlopen

    def apply(self, action: EnforcementAction, *, dry_run: bool) -> BackendApplyResult:
        if not self.endpoint:
            return BackendApplyResult(
                backend=self.name,
                applied=False,
                details=("soc endpoint not configured",),
            )

        payload = {
            "event_type": "scbe_linux_enforcement",
            "action": action.to_dict(),
        }
        if dry_run:
            return BackendApplyResult(
                backend=self.name,
                applied=False,
                details=(f"dry-run POST {self.endpoint}",),
            )

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with self._urlopen(req, timeout=self.timeout_seconds) as response:
                code = int(getattr(response, "status", 0) or 0)
                if code >= 400:
                    return BackendApplyResult(
                        backend=self.name,
                        applied=True,
                        failures=(f"soc sink returned HTTP {code}",),
                    )
        except urllib.error.HTTPError as exc:
            return BackendApplyResult(
                backend=self.name,
                applied=True,
                failures=(f"soc sink returned HTTP {exc.code}",),
            )
        except Exception as exc:  # noqa: BLE001
            return BackendApplyResult(
                backend=self.name,
                applied=True,
                failures=(f"soc sink request failed: {exc}",),
            )

        return BackendApplyResult(
            backend=self.name,
            applied=True,
            details=(f"posted to {self.endpoint}",),
        )


def build_enforcement_backends(
    names: tuple[str, ...],
    *,
    soc_endpoint: str | None = None,
    soc_bearer_token: str | None = None,
    soc_timeout_seconds: float = 3.0,
) -> tuple[EnforcementBackend, ...]:
    backends: list[EnforcementBackend] = []
    for name in names:
        if name == "systemd":
            backends.append(SystemdEnforcementBackend())
        elif name == "journald":
            backends.append(JournaldEnforcementBackend())
        elif name == "soc":
            token = soc_bearer_token or os.getenv("SCBE_SOC_BEARER_TOKEN", "")
            backends.append(
                SocSinkEnforcementBackend(
                    endpoint=soc_endpoint,
                    bearer_token=token,
                    timeout_seconds=soc_timeout_seconds,
                )
            )
        else:
            raise ValueError(f"unknown enforcement backend: {name}")
    return tuple(backends)
