"""
Full integration test for the Federated Context Grid.

Tests:
  1. RAG retrieval — semantic search with Poincare distance
  2. Octree spatial retrieval — O(1) neighborhood lookup
  3. Multi-method fused retrieval — RAG + octree merged
  4. Memory layer tests — store/retrieve across 7 tiers
  5. Hierarchy traversal — tongue -> tier -> skill -> content
  6. Multi-agent simulation — 3 agents with different archetypes
  7. HF generation — Llama 3.1 8B answers from retrieved context
  8. Chain verification — hash chain tamper detection
"""

import os
import sys
import time

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load HF token
env_path = os.path.join(os.path.dirname(__file__), "..", "config", "connector_oauth", ".env.connector.oauth")
hf_token = ""
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "HF_TOKEN=" in line or "HUGGINGFACE_TOKEN=" in line:
                hf_token = line.split("=", 1)[1].strip().strip('"')
                if hf_token:
                    break
os.environ["HF_TOKEN"] = hf_token

from src.kernel.context_grid import FederatedContextGrid, load_obsidian_vault
from src.kernel.agentic_sphere_grid import AgenticSphereGrid

SEP = "=" * 70
SUBSEP = "-" * 50

def header(text):
    print(f"\n{SEP}\n{text}\n{SEP}")

def subheader(text):
    print(f"\n{SUBSEP}\n{text}\n{SUBSEP}")


def main():
    header("FEDERATED CONTEXT GRID — FULL TEST SUITE")

    # =====================================================================
    # SETUP: Load vault and embed
    # =====================================================================
    subheader("SETUP: Loading vault + embedding")
    t0 = time.time()
    docs = load_obsidian_vault("notes/sphere-grid")
    grid = FederatedContextGrid(embedding_model="all-MiniLM-L6-v2")
    stored = grid.store_batch(docs)
    setup_time = time.time() - t0
    print(f"  {len(stored)} documents embedded in {setup_time:.1f}s")
    print(f"  Embedding dim: {len(stored[0].embedding)}")

    passed = 0
    failed = 0
    total = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  PASS: {name}" + (f" — {detail}" if detail else ""))
        else:
            failed += 1
            print(f"  FAIL: {name}" + (f" — {detail}" if detail else ""))

    # =====================================================================
    # TEST 1: RAG Retrieval
    # =====================================================================
    subheader("TEST 1: RAG Retrieval (Cosine + Poincare)")

    queries = [
        ("How does an agent learn new skills?", ["teach", "computational", "activation", "skill"]),
        ("What is the governance scan process?", ["governance", "scan", "9D", "risk"]),
        ("How do Sacred Tongues organize the grid?", ["tongue", "phi", "weight", "domain"]),
        ("What are Hodge dual combos?", ["hodge", "combo", "dual", "tongue"]),
        ("How does the fleet grow cooperatively?", ["fleet", "coverage", "cooperative", "teach"]),
    ]

    for query, expected_keywords in queries:
        t0 = time.time()
        results = grid.query_rag(query, top_k=3)
        elapsed = (time.time() - t0) * 1000

        has_relevant = any(
            any(kw.lower() in r.title.lower() or kw.lower() in r.content[:300].lower()
                for kw in expected_keywords)
            for r in results
        )

        top_title = results[0].title if results else "NONE"
        top_trust = results[0].trust_score if results else 0.0
        check(
            f"RAG: '{query[:50]}...'",
            has_relevant and len(results) > 0,
            f"top='{top_title}' trust={top_trust:.3f} ({elapsed:.1f}ms)"
        )

    # =====================================================================
    # TEST 2: Octree Spatial Retrieval
    # =====================================================================
    subheader("TEST 2: Octree Spatial Retrieval")

    t0 = time.time()
    octree_results = grid.query_octree("code generation and testing", top_k=5)
    elapsed = (time.time() - t0) * 1000

    check(
        "Octree returns results",
        len(octree_results) > 0,
        f"{len(octree_results)} results in {elapsed:.1f}ms"
    )
    if octree_results:
        for r in octree_results[:3]:
            print(f"    [{r.tongue}] {r.title} (trust={r.trust_score:.3f}, dist={r.distance:.4f})")

    # =====================================================================
    # TEST 3: Multi-Method Fused Retrieval
    # =====================================================================
    subheader("TEST 3: Multi-Method Fused Retrieval (RAG + Octree)")

    t0 = time.time()
    fused = grid.query_multi_method("How do agents grow through computational necessity?", top_k=5)
    elapsed = (time.time() - t0) * 1000

    check(
        "Fused retrieval returns results",
        len(fused) > 0,
        f"{len(fused)} results in {elapsed:.1f}ms"
    )
    check(
        "Fused results are deduplicated",
        len(set(r.doc_id for r in fused)) == len(fused),
        f"{len(fused)} unique doc IDs"
    )

    print("  Top 5 fused results:")
    for i, r in enumerate(fused[:5]):
        print(f"    {i+1}. [{r.tongue}] {r.title} (trust={r.trust_score:.3f}, via={r.retrieval_method})")

    # =====================================================================
    # TEST 4: Tongue-Filtered Retrieval
    # =====================================================================
    subheader("TEST 4: Tongue-Filtered Retrieval")

    for tongue in ["CA", "UM", "DR"]:
        results = grid.query_rag("skill patterns and training", top_k=3, tongue_filter=tongue)
        all_match = all(r.tongue == tongue for r in results)
        check(
            f"Tongue filter {tongue}",
            all_match and len(results) > 0,
            f"{len(results)} results, all tongue={tongue}"
        )

    # =====================================================================
    # TEST 5: Memory Layer Tests
    # =====================================================================
    subheader("TEST 5: Memory Layer Store/Retrieve")

    # Check session memory (most docs should be here)
    session_docs = grid.query_memory("session", limit=5)
    check(
        "Session memory populated",
        len(session_docs) > 0,
        f"{len(session_docs)} docs in session layer"
    )

    # Check identity memory (concepts + MOC)
    identity_docs = grid.query_memory("identity")
    check(
        "Identity memory has concepts",
        len(identity_docs) > 0,
        f"{len(identity_docs)} permanent docs"
    )

    # Store and retrieve a custom memory
    grid.store(
        "test_reflex_1", "Attack Pattern: SQL Injection",
        "DROP TABLE; --; SELECT * FROM users WHERE 1=1",
        tongue="UM", tier=2, doc_type="immune",
        memory_layer="immune"
    )
    immune_docs = grid.query_memory("immune")
    check(
        "Immune memory stores attack patterns",
        len(immune_docs) == 1 and "SQL" in immune_docs[0].title,
        f"stored: '{immune_docs[0].title}'"
    )

    # =====================================================================
    # TEST 6: Hierarchy Traversal
    # =====================================================================
    subheader("TEST 6: Hierarchy Traversal (Tongue -> Tier -> Type)")

    # All CA skills
    ca_skills = grid.query_hierarchy(tongue="CA", doc_type="skill-sphere")
    check(
        "CA skill spheres",
        len(ca_skills) == 4,
        f"found {len(ca_skills)} (expected 4: T1-T4)"
    )

    # All tier 1 skills across all tongues
    t1_skills = grid.query_hierarchy(tier=1, doc_type="skill-sphere")
    check(
        "Tier 1 skills across all tongues",
        len(t1_skills) == 6,
        f"found {len(t1_skills)} (expected 6: one per tongue)"
    )

    # Training data notes
    training_notes = grid.query_hierarchy(doc_type="training-data")
    check(
        "Training data notes",
        len(training_notes) == 24,
        f"found {len(training_notes)} (expected 24: one per skill sphere)"
    )

    # =====================================================================
    # TEST 7: Multi-Agent Simulation
    # =====================================================================
    subheader("TEST 7: Multi-Agent Simulation")

    # Create sphere grid with agents
    sphere = AgenticSphereGrid()
    sphere.register_agent("agent_researcher", "researcher")
    sphere.register_agent("agent_builder", "builder")
    sphere.register_agent("agent_guardian", "guardian")

    # Each agent queries the context grid from their specialization perspective
    agent_queries = {
        "agent_researcher": ("What research methods are available?", "RU"),
        "agent_builder": ("How do I write and test code?", "CA"),
        "agent_guardian": ("What security scanning capabilities exist?", "UM"),
    }

    for agent_id, (query, expected_tongue) in agent_queries.items():
        results = grid.query_rag(query, top_k=3, tongue_filter=expected_tongue)
        check(
            f"Agent {agent_id} retrieves {expected_tongue} content",
            len(results) > 0 and all(r.tongue == expected_tongue for r in results),
            f"top='{results[0].title}'" if results else "no results"
        )

        # Agent earns AP from the query (simulating work)
        if results:
            sphere.earn_ap(agent_id, 5.0, f"retrieved {len(results)} docs", results[0].title)

    # Check agent growth
    for agent_id in agent_queries:
        state = sphere.agents[agent_id]
        check(
            f"Agent {agent_id} earned AP",
            state.ap_lifetime > 0,
            f"AP={state.ap_lifetime:.1f}"
        )

    # =====================================================================
    # TEST 8: Hash Chain Verification
    # =====================================================================
    subheader("TEST 8: Hash Chain Verification")

    chain_ok = grid.verify_chain()
    check(
        "Hash chain intact",
        chain_ok,
        f"{len(grid.documents)} documents, all hashes unique"
    )

    # =====================================================================
    # TEST 9: Grid Statistics
    # =====================================================================
    subheader("TEST 9: Grid Statistics")

    stats = grid.stats()
    print(f"  Total documents: {stats.total_documents}")
    print(f"  Tongue distribution: {stats.tongue_distribution}")
    print(f"  Memory layers: {stats.memory_layers}")
    print(f"  Embedding dim: {stats.embedding_dim}")
    print(f"  Octree buckets: {stats.octree_nodes}")
    print(f"  Avg retrieval: {stats.avg_retrieval_ms:.1f}ms")

    check("Stats populated", stats.total_documents == len(stored) + 1)  # +1 for immune test

    # =====================================================================
    # TEST 10: HF Llama 3.1 8B Generation
    # =====================================================================
    subheader("TEST 10: HF Llama 3.1 8B RAG Generation")

    gen_query = "How does the Agentic Sphere Grid help AI agents grow and learn new capabilities?"
    context = grid.query_multi_method(gen_query, top_k=3)

    print(f"  Query: {gen_query}")
    print(f"  Context docs: {len(context)}")
    for r in context[:3]:
        print(f"    [{r.tongue}] {r.title} (trust={r.trust_score:.3f})")

    if hf_token:
        print("\n  Generating answer with Llama 3.1 8B...")
        t0 = time.time()
        answer = grid.generate_answer(gen_query, context, hf_token=hf_token)
        gen_time = time.time() - t0
        check(
            "HF generation produced output",
            len(answer) > 20 and "[" not in answer[:5],  # Not an error message
            f"{len(answer)} chars in {gen_time:.1f}s"
        )
        print(f"\n  GENERATED ANSWER:\n  {answer[:500]}")
    else:
        print("  SKIP: No HF token available for generation test")

    # =====================================================================
    # RESULTS
    # =====================================================================
    header(f"TEST RESULTS: {passed}/{total} PASSED, {failed} FAILED")

    if failed == 0:
        print("\nFEDERATED CONTEXT GRID: ALL TESTS PASSED")
    else:
        print(f"\n{failed} tests need attention")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
