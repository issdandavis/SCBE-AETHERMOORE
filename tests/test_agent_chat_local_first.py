from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_node(script: str) -> dict:
    env = os.environ.copy()
    env.pop("HF_TOKEN", None)
    env.pop("HUGGINGFACE_TOKEN", None)
    env.pop("HUGGING_FACE_HUB_TOKEN", None)
    env.pop("OLLAMA_URL", None)
    env.pop("AGENT_OLLAMA_URL", None)
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_agent_chat_endpoint_requires_commonjs_cleanly() -> None:
    payload = run_node("""
        const mod = require('./api/agent/chat.js');
        console.log(JSON.stringify({
          handlerType: typeof mod,
          hasRouteChat: typeof mod._private.routeChat
        }));
        """)
    assert payload == {"handlerType": "function", "hasRouteChat": "function"}


def test_agent_chat_offline_fallback_is_zero_cost_without_tokens() -> None:
    payload = run_node("""
        const { routeChat, chatConfig } = require('./api/agent/chat.js')._private;
        routeChat(chatConfig(), 'hello from local first test', [])
          .then((result) => console.log(JSON.stringify(result)))
          .catch((error) => {
            console.error(error);
            process.exit(1);
          });
        """)
    assert payload["ok"] is True
    assert payload["provider"] == "offline"
    assert payload["model"] == "none"
    assert "hello from local first test" in payload["text"]
