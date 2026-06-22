import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_mcp_config() -> dict:
    return json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))


def test_mcp_config_json_is_valid_and_has_servers():
    cfg = _load_mcp_config()
    assert isinstance(cfg.get("mcpServers"), dict)
    assert cfg["mcpServers"]


def test_repo_local_python_mcp_entries_point_to_existing_scripts():
    cfg = _load_mcp_config()
    missing = []
    for name, server in cfg["mcpServers"].items():
        command = server.get("command")
        args = server.get("args") or []
        if command != "python":
            continue
        for arg in args:
            if isinstance(arg, str) and arg.endswith(".py") and not (REPO_ROOT / arg).is_file():
                missing.append(f"{name}:{arg}")
    assert missing == []


def test_mcp_config_does_not_reference_known_removed_local_servers():
    cfg_text = (REPO_ROOT / ".mcp.json").read_text(encoding="utf-8")
    assert "mcp/orchestrator.py" not in cfg_text
    assert "mcp/notion_server.py" not in cfg_text
    assert "youtube-studio-mcp" not in cfg_text


def test_mcp_config_uses_available_local_launchers_for_non_remote_commands():
    cfg = _load_mcp_config()
    missing = []
    for name, server in cfg["mcpServers"].items():
        command = server.get("command")
        if command in {"cmd", "python", "npx"}:
            if shutil.which(command) is None:
                missing.append(f"{name}:{command}")
    assert missing == []
