"""devctl: start/stop/tunnel the SCBE MCP servers without juggling ports/processes.

The load-bearing test here is the SAFETY one: `stop` must only terminate a recorded pid that is ACTUALLY
listening on its port -- a reused pid (some unrelated program) must be left alone. The rest pin the pure
helpers (no process spawn, so deterministic in CI).
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("devctl", ROOT / "tools" / "mcp" / "devctl.py")
D = importlib.util.module_from_spec(_spec)
sys.modules["devctl"] = D  # register BEFORE exec so the frozen @dataclass can introspect its module
_spec.loader.exec_module(D)


def test_registry_and_transport_paths():
    assert "scbe-verify" in D.SERVERS
    spec = D.SERVERS["scbe-verify"]
    assert spec.module == "src/mcp/scbe_verify_mcp.py" and spec.port == 8765 and spec.transport == "sse"
    assert D._TRANSPORT_PATH["sse"] == "/sse" and D._TRANSPORT_PATH["streamable-http"] == "/mcp"


def test_state_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "_STATE", tmp_path / "state.json")
    assert D._load_state() == {}  # nothing yet
    D._save_state({"scbe-verify": {"pid": 123, "port": 8765}})
    assert D._load_state()["scbe-verify"]["pid"] == 123


def test_log_path_sanitizes_name():
    # the safety that matters: separators are stripped so the log can't escape the home dir
    p = D._log_path("evil/../name")
    assert p.parent == Path.home()
    assert "/" not in p.name and "\\" not in p.name and p.name.endswith(".log")


def test_port_owner_of_a_free_port_is_none():
    assert D._port_owner(59321) is None  # an unlikely-bound high port -> nobody owns it


def test_stop_leaves_a_pid_that_does_not_own_the_port_ALONE(tmp_path, monkeypatch):
    # the core safety property: recorded pid 4242, but the port is owned by a DIFFERENT pid (reuse) and
    # 4242 is alive -> stop must NOT terminate it.
    monkeypatch.setattr(D, "_STATE", tmp_path / "state.json")
    D._save_state({"scbe-verify": {"pid": 4242, "port": 8765, "transport": "sse", "module": "x"}})
    monkeypatch.setattr(D, "_port_owner", lambda port: 9999)  # someone ELSE owns the port
    monkeypatch.setattr(D, "_alive", lambda pid: True)
    killed = []
    monkeypatch.setattr(D, "_terminate", lambda pid: killed.append(pid) or True)

    D.cmd_stop(["scbe-verify"])
    assert killed == []  # 4242 was NOT terminated -- it doesn't own the port
    assert D._load_state() == {}  # but it's removed from our state (we no longer track it)


def test_stop_terminates_only_when_pid_owns_the_port(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "_STATE", tmp_path / "state.json")
    D._save_state({"scbe-verify": {"pid": 4242, "port": 8765, "transport": "sse", "module": "x"}})
    monkeypatch.setattr(D, "_port_owner", lambda port: 4242)  # OUR pid owns the port -> safe to stop
    monkeypatch.setattr(D, "_alive", lambda pid: True)
    killed = []
    monkeypatch.setattr(D, "_terminate", lambda pid: killed.append(pid) or True)

    D.cmd_stop(["scbe-verify"])
    assert killed == [4242]
