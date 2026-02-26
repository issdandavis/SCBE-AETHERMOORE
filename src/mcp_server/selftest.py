"""Self-test for the SCBE Semantic Mesh."""

from __future__ import annotations

import sys
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.mcp_server.semantic_mesh import (
    SemanticMesh,
    classify_tongue,
    text_to_tongue_embedding,
    embryonic_intake,
    TOOL_DEFINITIONS,
    MCPServer,
)


def selftest():
    print(f"\n{'='*60}")
    print("  SCBE Semantic Mesh — Self-Test")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    def check(name: str, cond: bool, detail: str = ""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # ── Tongue Classification ──────────────────────────────────────
    check("KO tongue", classify_tongue("The king commands authority") == "KO")
    check("AV tongue", classify_tongue("Navigate the path to discovery") == "AV")
    check("RU tongue", classify_tongue("The policy requires compliance") == "RU")
    check("CA tongue", classify_tongue("Optimize the algorithm pattern") == "CA")
    check("UM tongue", classify_tongue("Hidden secrets in the shadow") == "UM")
    check("DR tongue", classify_tongue("Forge the framework structure") == "DR")
    check("Default tongue", classify_tongue("hello world") == "CA")

    # ── Tongue Embedding ──────────────────────────────────────────
    emb = text_to_tongue_embedding("The leader commands authority over the kingdom")
    check("Embedding is 6D", len(emb) == 6)
    norm = sum(v * v for v in emb) ** 0.5
    check("Embedding inside Poincare ball", norm < 1.0, f"norm={norm}")

    # ── Embryonic Intake ──────────────────────────────────────────
    intake = embryonic_intake("Navigate the hidden path through shadows")
    check("Intake has tongue", "tongue" in intake)
    check("Intake has embedding", len(intake["embedding"]) == 6)
    check("Intake has ternary_state", len(intake["ternary_state"]) == 6)
    check("Intake has manifold", intake["manifold"] in ("M+", "M0", "M-"))
    check("Intake has breath_phase", 0.0 <= intake["breath_phase"] < 1.0)
    check("Intake ternary values valid",
          all(t in (-1, 0, 1) for t in intake["ternary_state"]))
    print(f"    Tongue: {intake['tongue']}")
    print(f"    Manifold: {intake['manifold']}")
    print(f"    Ternary: {intake['ternary_state']}")
    print(f"    Breath: phase={intake['breath_phase']:.3f}, amp={intake['breath_amplitude']:.3f}")

    # ── Semantic Mesh (in-memory) ──────────────────────────────────
    mesh = SemanticMesh(":memory:")

    # Ingest some concepts
    r1 = mesh.ingest("The harmonic wall creates exponential cost for adversarial drift",
                      label="Harmonic Wall", node_type="CONCEPT")
    check("Ingest returns node_id", bool(r1["node_id"]))
    check("Ingest has tongue", bool(r1["tongue"]))
    check("Ingest has manifold", r1["manifold"] in ("M+", "M0", "M-"))
    print(f"    Node: {r1['node_id']}, tongue={r1['tongue']}, manifold={r1['manifold']}")

    r2 = mesh.ingest("Navigate through the Poincare ball using hyperbolic geodesics",
                      label="Poincare Navigation", connect_to=[r1["node_id"]])
    check("Second ingest OK", bool(r2["node_id"]))
    check("Edge created", len(r2["edges_created"]) == 1)

    r3 = mesh.ingest("The secret encryption protocol hides data in shadows",
                      label="Shadow Encryption")
    check("Third ingest OK", bool(r3["node_id"]))

    r4 = mesh.ingest("Forge a new framework for AI governance structure",
                      label="AI Governance Framework",
                      connect_to=[r1["node_id"], r3["node_id"]])
    check("Fourth ingest with 2 edges", len(r4["edges_created"]) == 2)

    # ── Query ──────────────────────────────────────────────────────
    results = mesh.query("exponential cost security")
    check("Query returns results", len(results) > 0)
    if results:
        check("Top result is Harmonic Wall", "Harmonic" in results[0]["label"])
        print(f"    Top result: {results[0]['label']} (sim={results[0]['similarity']})")

    # Tongue-filtered query
    um_results = mesh.query("hidden", tongue_filter="UM")
    check("Tongue-filtered query works", isinstance(um_results, list))

    # ── Context Subgraph ──────────────────────────────────────────
    ctx = mesh.get_context(r1["node_id"], depth=2)
    check("Context has nodes", len(ctx["nodes"]) > 0)
    check("Context has edges", len(ctx["edges"]) > 0)
    print(f"    Subgraph: {ctx['stats']['node_count']} nodes, {ctx['stats']['edge_count']} edges")

    # ── Path Finding ──────────────────────────────────────────────
    path_result = mesh.path(r2["node_id"], r1["node_id"])
    check("Path found", path_result["found"])
    if path_result["found"]:
        check("Path length 1 (direct)", path_result["length"] == 1)
        print(f"    Path: {' -> '.join(n['label'] for n in path_result['path'])}")

    # ── Connect ───────────────────────────────────────────────────
    conn = mesh.connect(r3["node_id"], r2["node_id"], edge_type="CONTRASTS")
    check("Connect returns edge_id", bool(conn["edge_id"]))
    check("Edge type is CONTRASTS", conn["type"] == "CONTRASTS")

    # ── Stats ─────────────────────────────────────────────────────
    stats = mesh.stats()
    check("Stats has total_nodes", stats["total_nodes"] == 4)
    check("Stats has total_edges", stats["total_edges"] >= 3)
    print(f"    Nodes: {stats['total_nodes']}, Edges: {stats['total_edges']}")

    # ── MCP Tool Definitions ──────────────────────────────────────
    check("6 tools defined", len(TOOL_DEFINITIONS) == 6)
    tool_names = {t["name"] for t in TOOL_DEFINITIONS}
    for expected in ["mesh_ingest", "mesh_query", "mesh_context",
                     "mesh_connect", "mesh_path", "mesh_stats"]:
        check(f"  Tool {expected} exists", expected in tool_names)

    # ── MCP Server construction ───────────────────────────────────
    server = MCPServer(":memory:")
    check("MCP server created", server is not None)

    # Test initialize
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
    })
    check("Initialize response OK", resp["result"]["serverInfo"]["name"] == "scbe-semantic-mesh")

    # Test tools/list
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
    })
    check("Tools list returns 6", len(resp["result"]["tools"]) == 6)

    # Test tools/call — mesh_ingest
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "mesh_ingest",
            "arguments": {"content": "Test concept for MCP", "label": "MCP Test"},
        },
    })
    check("MCP ingest succeeds", "content" in resp["result"])

    # Test tools/call — mesh_stats
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "mesh_stats", "arguments": {}},
    })
    check("MCP stats succeeds", "content" in resp["result"])

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = selftest()
    sys.exit(0 if success else 1)
