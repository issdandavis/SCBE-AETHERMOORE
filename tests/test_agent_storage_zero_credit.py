from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_node(script: str) -> dict:
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_agent_storage_endpoint_requires_commonjs_cleanly() -> None:
    payload = run_node("""
        const mod = require('./api/agent/storage.js');
        console.log(JSON.stringify({
          handlerType: typeof mod,
          hasBuilder: typeof mod._private.buildExportPacket,
          providers: mod._private.PROVIDERS.map((p) => p.id),
          formation: mod._private.WORKSPACE_FORMATION
        }));
        """)
    assert payload["handlerType"] == "function"
    assert payload["hasBuilder"] == "function"
    assert payload["providers"][:2] == ["local_download", "browser_local"]
    assert {"github", "dropbox", "onedrive", "gdrive"}.issubset(set(payload["providers"]))
    assert payload["formation"]["schema_version"] == "aethermoor.bus.workspace_formation.v1"
    assert payload["formation"]["folders"][0]["path"] == "00_inbox"


def test_agent_storage_builds_zero_server_storage_export_packet() -> None:
    payload = run_node("""
        const { buildExportPacket } = require('./api/agent/storage.js')._private;
        const result = buildExportPacket({
          kind: 'agent bus',
          name: 'Customer Smoke Export',
          destination: 'gdrive',
          content: { verdict: 'ALLOW', message: 'saved from bus' },
          metadata: { tenant: 'demo' }
        });
        console.log(JSON.stringify(result));
        """)
    assert payload["ok"] is True
    assert payload["cost"] == "zero-server-storage"
    assert payload["packet"]["destination_hint"] == "gdrive"
    assert payload["packet"]["filename"] == "customer-smoke-export.json"
    assert payload["packet"]["workspace_formation"]["default_root"] == ".aethermoor-bus/workspaces"
    assert payload["download"]["mime"] == "application/json"
    decoded = json.loads(
        subprocess.check_output(
            [
                "node",
                "-e",
                f"console.log(Buffer.from('{payload['download']['base64']}', 'base64').toString('utf8'))",
            ],
            cwd=REPO_ROOT,
            text=True,
        )
    )
    assert decoded["schema_version"] == "aethermoor.agent.storage_export.v1"
    assert "saved from bus" in decoded["content"]


def test_agent_storage_rejects_large_exports() -> None:
    payload = run_node("""
        const { buildExportPacket } = require('./api/agent/storage.js')._private;
        try {
          buildExportPacket({ content: 'x'.repeat(300000) });
          console.log(JSON.stringify({ ok: false }));
        } catch (error) {
          console.log(JSON.stringify({ ok: true, status: error.status, message: error.message }));
        }
        """)
    assert payload["ok"] is True
    assert payload["status"] == 413
