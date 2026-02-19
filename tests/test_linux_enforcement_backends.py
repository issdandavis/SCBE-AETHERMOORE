import json

import pytest

from agents.linux_enforcement_backends import (
    JournaldEnforcementBackend,
    SocSinkEnforcementBackend,
    SystemdEnforcementBackend,
    build_enforcement_backends,
    parse_backend_names,
)


def _action(kernel_action: str = "QUARANTINE"):
    from agents.linux_enforcement_backends import EnforcementAction

    return EnforcementAction(
        process_key="node-a:123:bash",
        kernel_action=kernel_action,
        host="node-a",
        pid=123,
        process_name="bash",
        operation="exec",
        target="/tmp/drop.sh",
        rationale="test rationale",
        quarantine_dir="/var/quarantine/scbe",
        metadata={"decision": "ESCALATE"},
    )


def test_parse_backend_names_defaults_and_custom_values():
    assert parse_backend_names(None) == ("systemd", "journald")
    assert parse_backend_names("soc,journald") == ("soc", "journald")
    assert parse_backend_names("") == tuple()


def test_parse_backend_names_rejects_unknown_names():
    with pytest.raises(ValueError):
        parse_backend_names("systemd,unknown")


def test_build_enforcement_backends_builds_known_backends():
    backends = build_enforcement_backends(("systemd", "journald", "soc"), soc_endpoint="https://soc.example/api")
    names = tuple(getattr(x, "name", x.__class__.__name__) for x in backends)
    assert names == ("systemd", "journald", "soc")


def test_systemd_backend_uses_scope_commands_without_shell():
    calls: list[tuple[str, ...]] = []

    def _runner(argv: tuple[str, ...]) -> tuple[int, str]:
        calls.append(argv)
        return 0, ""

    backend = SystemdEnforcementBackend(command_runner=_runner)
    result = backend.apply(_action("KILL"), dry_run=False)

    assert calls == [("systemctl", "kill", "--signal=SIGKILL", "123.scope")]
    assert result.failures == tuple()


def test_journald_backend_emits_structured_message():
    seen: dict[str, str] = {}

    def _sender(**kwargs):
        seen.update(kwargs)

    backend = JournaldEnforcementBackend(sender=_sender)
    result = backend.apply(_action("THROTTLE"), dry_run=False)

    assert result.failures == tuple()
    assert "MESSAGE" in seen
    payload = json.loads(seen["MESSAGE"])
    assert payload["kernel_action"] == "THROTTLE"
    assert payload["pid"] == 123


def test_soc_backend_posts_json_payload():
    captured: dict[str, object] = {}

    class _Resp:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _urlopen(req, timeout):
        captured["method"] = req.get_method()
        captured["timeout"] = timeout
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        captured["body"] = req.data.decode("utf-8")
        return _Resp()

    backend = SocSinkEnforcementBackend(
        endpoint="https://soc.example/api",
        bearer_token="token-123",
        timeout_seconds=2.5,
        urlopen=_urlopen,
    )
    result = backend.apply(_action("KILL"), dry_run=False)

    assert result.failures == tuple()
    assert captured["method"] == "POST"
    assert captured["timeout"] == 2.5
    assert captured["url"] == "https://soc.example/api"
    payload = json.loads(str(captured["body"]))
    assert payload["action"]["kernel_action"] == "KILL"


def test_soc_backend_no_endpoint_is_safe_noop():
    backend = SocSinkEnforcementBackend(endpoint="")
    result = backend.apply(_action("KILL"), dry_run=False)
    assert result.applied is False
    assert result.failures == tuple()
