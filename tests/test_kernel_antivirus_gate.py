from agents.kernel_antivirus_gate import evaluate_kernel_event


def _safe_event():
    return {
        "host": "node-a",
        "pid": 4021,
        "process_name": "notepad.exe",
        "operation": "exec",
        "target": r"C:\Windows\System32\notepad.exe",
        "command_line": r"notepad.exe C:\notes\todo.txt",
        "parent_process": "explorer.exe",
        "signer_trusted": True,
        "hash_sha256": "a" * 64,
        "geometry_norm": 0.08,
    }


def test_clean_signed_binary_stays_healthy():
    result = evaluate_kernel_event(_safe_event())
    assert result.decision == "ALLOW"
    assert result.kernel_action == "ALLOW"
    assert result.cell_state == "HEALTHY"
    assert result.block_execution is False


def test_malicious_payload_gets_isolated_or_honeypot():
    event = _safe_event()
    event.update(
        {
            "process_name": "powershell.exe",
            "parent_process": "winword.exe",
            "command_line": "powershell -enc SQBtAG0AYQBsAGkAYwBpAG8AdQBz",
            "target": r"C:\Windows\System32\drivers\evil.sys",
            "operation": "module_load",
            "signer_trusted": False,
            "hash_sha256": "",
            "geometry_norm": 0.82,
        }
    )
    result = evaluate_kernel_event(event)
    assert result.decision in {"ESCALATE", "DENY", "QUARANTINE"}
    assert result.kernel_action in {"QUARANTINE", "HONEYPOT", "KILL"}
    assert result.block_execution is True
    assert result.isolate_process is True


def test_inflamed_state_throttles_even_if_allow():
    event = _safe_event()
    event["geometry_norm"] = 0.995
    result = evaluate_kernel_event(event)
    assert result.cell_state in {"INFLAMED", "NECROTIC"}
    assert result.kernel_action in {"THROTTLE", "HONEYPOT", "QUARANTINE", "KILL"}


def test_event_dict_roundtrip_contains_cell_state():
    result = evaluate_kernel_event(_safe_event())
    data = result.to_dict()
    assert "cell_state" in data
    assert data["cell_state"] in {"HEALTHY", "PRIMED", "INFLAMED", "NECROTIC"}
