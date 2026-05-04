from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src.coding_spine.bijective_reasoning_code_packet import build_bijective_reasoning_code_packet

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_precode_packet_routes_rust_ring_buffer_without_source() -> None:
    packet = build_bijective_reasoning_code_packet(
        intent="write a Rust ring buffer with zero-cost ownership checks",
        language="rust",
        tile_row=2,
        tile_col=4,
    )
    assert packet["schema_version"] == "scbe-bijective-reasoning-code-packet-v1"
    assert packet["intent"]["source_state"] == "precode_intent"
    assert packet["route"]["tongue"] == "RU"
    assert packet["route"]["language"] == "rust"
    assert packet["route"]["tile"] == "tile:2:4"
    assert packet["route"]["voxel6"] == [2, 4, 0, 0, 0, 0]
    assert packet["transport"]["intent"]["roundtrip_ok"] is True
    assert packet["reconstruction"]["roundtrip_ok"] is True
    assert "code_view_not_materialized" in packet["reconstruction"]["known_losses"]
    assert packet["compact_agent_packet"]["phase"] == "precode"
    assert packet["merge_geometry"]["promote_ready"] is True
    assert "compact_agent_packet_trace" in packet["training_hooks"]["use_as"]
    assert packet["identity"]["packet_id"].startswith("brc1-")


def test_source_packet_preserves_python_code_view_and_semantic_quarks() -> None:
    source = "def add(a, b):\n    return a + b\n"
    packet = build_bijective_reasoning_code_packet(
        intent="add two values",
        source=source,
        language="python",
        source_name="sample.py",
    )
    assert packet["intent"]["source_state"] == "source_code"
    assert packet["route"]["tongue"] == "KO"
    assert packet["code_views"]["python"]["status"] == "source"
    assert packet["code_views"]["python"]["content"] == source
    assert "function_shape" in packet["semantic_ir"]["quarks"]
    assert "return_flow" in packet["semantic_ir"]["quarks"]
    assert packet["transport"]["code"]["roundtrip_ok"] is True
    assert packet["compact_agent_packet"]["phase"] == "packetize"
    assert packet["verification"]["contact_points"][0] == {
        "kind": "hard",
        "name": "transport_roundtrip",
        "ok": True,
    }


def test_reasoning_code_packet_cli_json(tmp_path: Path) -> None:
    source_file = tmp_path / "lib.rs"
    source_file.write_text("fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "reasoning-code-packet",
            "--intent",
            "compile this Rust helper",
            "--source-file",
            str(source_file),
            "--language",
            "rust",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    packet = json.loads(proc.stdout)
    assert packet["route"]["tongue"] == "RU"
    assert packet["identity"]["source_name"] == "lib.rs"
    assert packet["reconstruction"]["roundtrip_ok"] is True


def test_reasoning_code_packet_service_route() -> None:
    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/reasoning-code-packet",
        json={
            "intent": "write a TypeScript browser helper",
            "language": "typescript",
            "permission_mode": "observe",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["route"]["tongue"] == "AV"
    assert body["data"]["intent"]["source_state"] == "precode_intent"


def test_geoseal_harness_packet_endpoint_build_only() -> None:
    from scripts.serve_geoseal_harness import app

    client = TestClient(app)
    response = client.post(
        "/harness/reasoning-code-packet",
        json={
            "intent": "write a Julia spectral anomaly detector",
            "language": "julia",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["packet"]["route"]["tongue"] == "UM"
    assert body["packet"]["compact_agent_packet"]["budget"]["max_output_tokens"] == 300
