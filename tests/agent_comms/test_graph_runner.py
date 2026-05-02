from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src.agent_comms import (
    AgentPacketV1,
    Budget,
    ContextRef,
    GraphEdge,
    GraphNode,
    MergeReport,
    PacketGraphRunner,
    Route,
    build_default_packet_graph,
    hash_state,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _packet(**overrides) -> AgentPacketV1:
    base = dict(
        task_id="graph-test",
        phase="plan",
        route=Route(tongue="KO", domain="code", permission="read"),
        context_refs=[ContextRef(kind="path", value="README.md")],
        state_hash=hash_state("graph-test"),
        budget=Budget(max_input_tokens=1024, max_output_tokens=256),
        request="Run packet graph.",
        expected_output="delta",
    )
    base.update(overrides)
    return AgentPacketV1(**base)


def test_default_packet_graph_runs_plan_verify_merge_and_writes_checkpoints(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoints.jsonl"
    runner = build_default_packet_graph(route_tongue="RU", checkpoint_path=checkpoint)

    result = runner.run(_packet())

    assert result.path == ["plan", "verify", "merge"]
    assert result.final_decision == "promote"
    assert result.halted_reason == "terminal_decision"
    assert len(result.checkpoints) == 3
    rows = [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()]
    assert [row["node_id"] for row in rows] == ["plan", "verify", "merge"]
    assert all(row["packet_fingerprint"].startswith("pkt:") for row in rows)
    assert [row["merge_report"]["delta"]["route"] for row in rows] == ["RU", "RU", "RU"]


def test_packet_graph_stops_on_reject_without_following_promote_edge() -> None:
    def reject(_packet: AgentPacketV1) -> MergeReport:
        return MergeReport(
            claim="reject at plan",
            delta={},
            evidence=["test:forced"],
            contact_points=["hard:unit"],
            decision="reject",
            task_id="graph-test",
        )

    runner = PacketGraphRunner(
        graph_id="reject-graph",
        nodes=[
            GraphNode(
                node_id="plan",
                phase="plan",
                route=Route(tongue="KO", domain="code", permission="read"),
                expected_output="delta",
                handler_id="reject",
            ),
            GraphNode(
                node_id="verify",
                phase="verify",
                route=Route(tongue="KO", domain="code", permission="read"),
                expected_output="verdict",
            ),
        ],
        edges=[GraphEdge(from_node="plan", to_node="verify", on_decision="promote")],
        start_node="plan",
        handlers={"reject": reject},
    )

    result = runner.run(_packet())

    assert result.path == ["plan"]
    assert result.final_decision == "reject"
    assert result.final_node == "plan"


def test_packet_graph_cli_json(tmp_path: Path) -> None:
    checkpoint = tmp_path / "graph.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "packet-graph-run",
            "--intent",
            "plan a Python packet validator",
            "--language",
            "python",
            "--checkpoint",
            str(checkpoint),
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
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_packet_graph_runner_v1"
    assert payload["path"] == ["plan", "verify", "merge"]
    assert checkpoint.is_file()


def test_packet_graph_service_route() -> None:
    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/packet-graph-run",
        json={"intent": "plan a Rust router gate", "language": "rust", "content": "fn main() {}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["path"] == ["plan", "verify", "merge"]
    assert body["data"]["base_route"]["tongue"] == "RU"
    assert body["data"]["checkpoints"][0]["merge_report"]["delta"]["route"] == "RU"
