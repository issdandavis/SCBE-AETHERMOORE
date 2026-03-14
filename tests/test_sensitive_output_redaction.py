from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

src_module = sys.modules.setdefault("src", types.ModuleType("src"))
security_module = sys.modules.setdefault("src.security", types.ModuleType("src.security"))
secret_store_module = types.ModuleType("src.security.secret_store")
secret_store_module.get_secret = lambda key, default="": default
secret_store_module.set_secret = lambda key, value, note="": None
sys.modules["src.security.secret_store"] = secret_store_module
setattr(src_module, "security", security_module)


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


terminal_ai_router = _load_module("test_terminal_ai_router", "scripts/system/terminal_ai_router.py")
sell_from_terminal = _load_module("test_sell_from_terminal", "scripts/system/sell_from_terminal.py")
scbe_system_cli = _load_module("test_scbe_system_cli", "scripts/scbe-system-cli.py")


def test_terminal_ai_router_public_payload_strips_secret_metadata() -> None:
    payload = {
        "generated_at_utc": "2026-03-14T00:00:00Z",
        "config_path": "config.json",
        "checks": ["openai"],
        "alias_sync": {
            "OPENAI_API_KEY": {"status": "synced", "source": "OPENAI_KEY"},
            "ANTHROPIC_API_KEY": {"status": "missing", "source": None},
        },
        "status": {
            "openai": {
                "status": "degraded",
                "detail": {
                    "http_status": 401,
                    "key_name": "OPENAI_API_KEY",
                    "key_source": "env",
                    "accepted_keys": ["OPENAI_API_KEY"],
                    "error": "Authorization: Bearer super-secret-token",
                },
            }
        },
    }

    public_payload = terminal_ai_router._build_public_health_payload(payload)

    assert public_payload["alias_sync_summary"] == {"set": 0, "synced": 1, "missing": 1}
    detail = public_payload["status"]["openai"]["detail"]
    assert "key_name" not in detail
    assert "key_source" not in detail
    assert "accepted_keys" not in detail
    assert "super-secret-token" not in detail["error"]
    assert "[redacted]" in detail["error"]


def test_sell_from_terminal_process_summary_omits_raw_streams() -> None:
    class Proc:
        returncode = 1
        stdout = "OPENAI_API_KEY=abc123"
        stderr = "Authorization: Bearer super-secret-token"

    summary = sell_from_terminal._summarize_process_result(["python", "tool.py"], Proc())

    assert summary["returncode"] == 1
    assert summary["stdout_present"] is True
    assert summary["stderr_present"] is True
    assert "stdout" not in summary
    assert "stderr" not in summary
    assert "[redacted]" in summary["error_excerpt"]


def test_scbe_system_cli_sanitize_agent_result_for_disk_omits_content() -> None:
    result = {
        "ok": True,
        "agent_id": "codex",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "content": "password=hunter2",
        "raw": {"secret": "x"},
        "prompt": "secret prompt",
    }

    sanitized = scbe_system_cli._sanitize_agent_result_for_disk(result)

    assert sanitized["ok"] is True
    assert sanitized["agent_id"] == "codex"
    assert "content" not in sanitized
    assert "raw" not in sanitized
    assert "prompt" not in sanitized
    assert sanitized["content_char_count"] == len("password=hunter2")
    assert len(sanitized["content_sha256"]) == 64
