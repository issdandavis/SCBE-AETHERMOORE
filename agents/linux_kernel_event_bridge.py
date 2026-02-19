"""
Linux kernel event bridge for SCBE antivirus policy.

Consumes Falco/eBPF-style JSON events and maps them into KernelEvent so the
SCBE kernel gate can apply immune-style containment decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import json

from agents.kernel_antivirus_gate import KernelEvent, KernelGateResult, evaluate_kernel_event


def _to_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _to_int(x: Any, default: int = 0) -> int:
    try:
        return int(str(x).strip())
    except Exception:  # noqa: BLE001
        return default


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(str(x).strip())
    except Exception:  # noqa: BLE001
        return default


def _to_bool(x: Any, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return default
    raw = str(x).strip().lower()
    if raw in {"1", "true", "t", "yes", "y"}:
        return True
    if raw in {"0", "false", "f", "no", "n"}:
        return False
    return default


def _pick(d: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _map_evt_type_to_operation(evt_type: str) -> str:
    e = (evt_type or "").strip().lower()
    if e in {"execve", "execveat"}:
        return "exec"
    if e in {"open", "openat", "openat2"}:
        return "open"
    if e in {"write", "writev", "pwrite64"}:
        return "write"
    if e in {"unlink", "unlinkat", "rmdir"}:
        return "delete"
    if e in {"rename", "renameat", "renameat2"}:
        return "rename"
    if e in {"connect", "sendto", "accept", "accept4"}:
        return "network_connect"
    if e in {"init_module", "finit_module", "delete_module"}:
        return "module_load"
    if e in {"ptrace", "process_vm_writev"}:
        return "process_inject"
    return e or "open"


def _network_target(fields: dict[str, Any]) -> str:
    sip = _to_str(_pick(fields, "fd.sip", "evt.arg.sip"))
    sport = _to_str(_pick(fields, "fd.sport", "evt.arg.sport"))
    dip = _to_str(_pick(fields, "fd.dip", "evt.arg.dip"))
    dport = _to_str(_pick(fields, "fd.dport", "evt.arg.dport"))
    if sip or dip:
        src = f"{sip}:{sport}" if sport else sip
        dst = f"{dip}:{dport}" if dport else dip
        return f"{src}->{dst}".strip("->")
    return ""


def map_falco_event_to_kernel_event(event: dict[str, Any], *, host_default: str = "linux-node") -> KernelEvent:
    """
    Map one Falco/eBPF event payload to SCBE KernelEvent.
    """
    fields = event.get("output_fields")
    if not isinstance(fields, dict):
        fields = {}

    evt_type = _to_str(_pick(fields, "evt.type", "event.type", default=event.get("evt_type", ""))).lower()
    operation = _map_evt_type_to_operation(evt_type)

    host = _to_str(
        _pick(
            fields,
            "host.name",
            "k8s.node.name",
            default=event.get("hostname", host_default),
        )
    ) or host_default
    pid = _to_int(_pick(fields, "proc.pid", "process.pid", "evt.pid", default=event.get("pid", 0)))
    process_name = _to_str(
        _pick(
            fields,
            "proc.name",
            "process.name",
            "evt.arg.procname",
            default=event.get("process_name", "unknown"),
        )
    ).lower() or "unknown"
    parent_process = _to_str(
        _pick(fields, "proc.pname", "process.parent.name", "proc.aname[1]", default=event.get("parent_process", ""))
    ).lower()
    command_line = _to_str(
        _pick(
            fields,
            "proc.cmdline",
            "process.command_line",
            "evt.arg.cmdline",
            default=event.get("command_line", ""),
        )
    )

    if operation == "network_connect":
        target = _network_target(fields)
    else:
        target = _to_str(
            _pick(
                fields,
                "fd.name",
                "proc.exepath",
                "evt.arg.filename",
                "evt.arg.path",
                default=event.get("target", ""),
            )
        )

    signer_trusted = _to_bool(
        _pick(
            fields,
            "scbe.signer_trusted",
            "proc.is_signed",
            "file.trusted",
            default=event.get("signer_trusted", False),
        ),
        default=False,
    )

    hash_sha256 = _to_str(
        _pick(
            fields,
            "file.sha256",
            "proc.hash.sha256",
            "scbe.sha256",
            default=event.get("hash_sha256", ""),
        )
    ) or None

    geometry_norm = _to_float(
        _pick(
            fields,
            "scbe.geometry_norm",
            default=event.get("geometry_norm", 0.0),
        ),
        default=0.0,
    )

    metadata = {
        "rule": event.get("rule"),
        "priority": event.get("priority"),
        "output": event.get("output"),
        "evt_type": evt_type,
        "container_id": _pick(fields, "container.id", "container.image.id", default=""),
        "container_name": _pick(fields, "container.name", default=""),
        "k8s_pod": _pick(fields, "k8s.pod.name", default=""),
        "k8s_ns": _pick(fields, "k8s.ns.name", default=""),
    }

    return KernelEvent(
        host=host,
        pid=pid,
        process_name=process_name,
        operation=operation,
        target=target,
        command_line=command_line,
        parent_process=parent_process,
        signer_trusted=signer_trusted,
        hash_sha256=hash_sha256,
        geometry_norm=geometry_norm,
        metadata=metadata,
    )


@dataclass(frozen=True)
class LinuxBridgeDecision:
    kernel_event: KernelEvent
    result: KernelGateResult
    previous_antibody_load: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "kernel_event": asdict(self.kernel_event),
            "previous_antibody_load": self.previous_antibody_load,
            "decision": self.result.to_dict(),
        }


class LinuxKernelAntivirusBridge:
    """
    Stateful bridge maintaining antibody load continuity per process key.
    """

    def __init__(self, *, max_state_entries: int = 50000):
        self.max_state_entries = max(1000, int(max_state_entries))
        self._antibody_load_by_key: dict[str, float] = {}

    @staticmethod
    def process_key(event: KernelEvent) -> str:
        return f"{event.host}:{event.pid}:{event.process_name}"

    def _store_antibody(self, key: str, value: float) -> None:
        if len(self._antibody_load_by_key) >= self.max_state_entries and key not in self._antibody_load_by_key:
            # Drop oldest inserted key deterministically (Python dict insertion order).
            oldest = next(iter(self._antibody_load_by_key.keys()))
            self._antibody_load_by_key.pop(oldest, None)
        self._antibody_load_by_key[key] = float(value)

    def evaluate_falco_event(self, event: dict[str, Any], *, host_default: str = "linux-node") -> LinuxBridgeDecision:
        kernel_event = map_falco_event_to_kernel_event(event, host_default=host_default)
        key = self.process_key(kernel_event)
        prev = float(self._antibody_load_by_key.get(key, 0.0))
        result = evaluate_kernel_event(kernel_event, previous_antibody_load=prev)
        self._store_antibody(key, result.turnstile.antibody_load)
        return LinuxBridgeDecision(kernel_event=kernel_event, result=result, previous_antibody_load=prev)

    def evaluate_json_line(self, line: str, *, host_default: str = "linux-node") -> LinuxBridgeDecision:
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError("falco line must be a JSON object")
        return self.evaluate_falco_event(payload, host_default=host_default)

