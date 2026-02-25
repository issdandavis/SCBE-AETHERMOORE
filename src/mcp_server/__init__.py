"""SCBE Semantic Mesh — MCP Knowledge Graph Server.

A cross-platform context extension for LLMs built on interconnected
linguistic variations and quasi-meanings.

The mesh encodes concepts not as flat entities but as positions in a
6D Sacred Tongue space (KO/AV/RU/CA/UM/DR), embedded in a Poincare
ball where semantic drift has exponential cost. Binary input is
converted to balanced ternary at intake — the "embryonic gastrulation"
moment where raw data differentiates into three manifold layers
(M+/M0/M-) before becoming a governed node in the graph.

Architecture:
    HeartVaultGraph   — SQLite property graph (nodes, edges, queries)
    PolyAINodalNetwork — Governed graph writes (L6/L11/L12/L14 pipeline)
    TriManifoldPersonality — Ternary meaning-space classification
    MCP Server        — JSON-RPC over stdio, compatible with any MCP client
"""
