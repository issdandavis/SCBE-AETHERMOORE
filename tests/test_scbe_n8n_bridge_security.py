from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflows.n8n import scbe_n8n_bridge as bridge  # noqa: E402


def test_send_zapier_event_blocks_non_allowlisted_host(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_ZAPIER_WEBHOOK_URL", "https://evil.example.com/hook")
    result = bridge._send_zapier_event({"event": "llm_dispatch"})
    assert result["status"] == "blocked"
    assert "allowlist" in result["reason"]


def test_send_zapier_event_skips_when_no_env_hook(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_ZAPIER_WEBHOOK_URL", "")
    result = bridge._send_zapier_event({"event": "llm_dispatch"})
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_llm_dispatch_ignores_user_hook_override(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})

    monkeypatch.setattr(
        bridge,
        "_dispatch_openai_compatible",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "ok"}}]},
    )
    monkeypatch.setattr(
        bridge,
        "_extract_openai_style_response",
        lambda _resp: {"text": "ok", "tool_calls": []},
    )
    monkeypatch.setattr(
        bridge,
        "_send_zapier_event",
        lambda payload: {"status": "sent", "event": payload.get("event")},
    )

    req = bridge.LLMDispatchRequest.model_validate(
        {
            "provider": "openai",
            "messages": [{"role": "user", "content": "hello"}],
            "route_to_zapier": True,
            # this key should be ignored because it is not part of the model
            "zapier_hook_url": "https://evil.example.com/hook",
        }
    )
    result = await bridge.llm_dispatch(req, x_api_key="test-key")

    assert result["zapier"]["status"] == "sent"
    assert "zapier_hook_url" not in req.model_dump()
