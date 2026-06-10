from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_node(script: str) -> dict:
    env = os.environ.copy()
    env["AGENT_CHAT_PROVIDER_ORDER"] = "offline"
    env.pop("HF_TOKEN", None)
    env.pop("HUGGINGFACE_TOKEN", None)
    env.pop("HUGGING_FACE_HUB_TOKEN", None)
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


def test_local_bridge_exports_create_server() -> None:
    payload = run_node("""
        const bridge = require('./scripts/system/local_ollama_agent_bridge.cjs');
        console.log(JSON.stringify({
          createBridgeServer: typeof bridge.createBridgeServer,
          configureDefaults: typeof bridge.configureDefaults
        }));
        """)
    assert payload == {"createBridgeServer": "function", "configureDefaults": "function"}


def test_local_bridge_serves_health_and_chat_without_customer_key() -> None:
    payload = run_node("""
        const { createBridgeServer } = require('./scripts/system/local_ollama_agent_bridge.cjs');
        const server = createBridgeServer();
        server.listen(0, '127.0.0.1', async () => {
          const port = server.address().port;
          const base = `http://127.0.0.1:${port}`;
          const health = await fetch(`${base}/api/agent/health`).then((r) => r.json());
          const chat = await fetch(`${base}/api/agent/chat`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ message: 'local bridge smoke' })
          }).then((r) => r.json());
          server.close(() => {
            console.log(JSON.stringify({
              healthOk: health.ok,
              storageEndpoint: health.storage.endpoint,
              chatOk: chat.ok,
              provider: chat.provider,
              text: chat.text
            }));
          });
        });
        """)
    assert payload["healthOk"] is True
    assert payload["storageEndpoint"] == "/api/agent/storage"
    assert payload["chatOk"] is True
    assert payload["provider"] == "offline"
    assert "local bridge smoke" in payload["text"]
