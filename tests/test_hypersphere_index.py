from __future__ import annotations

from src.storage.hypersphere_index import HyperSphereIndex, poincare_distance


def test_poincare_distance_symmetric() -> None:
    a = [0.2, 0.1, 0.0, 0.05, -0.03, 0.01]
    b = [-0.1, 0.05, 0.03, -0.02, 0.08, 0.0]
    assert abs(poincare_distance(a, b) - poincare_distance(b, a)) < 1e-9


def test_layer_assignment_increases_with_radius() -> None:
    index = HyperSphereIndex(dimensions=6, layer_count=8, max_radius=0.95)
    index.add(doc_id="inner", text="inner", vector=[0.05, 0.0, 0.0, 0.0, 0.0, 0.0])
    index.add(doc_id="outer", text="outer", vector=[0.8, 0.0, 0.0, 0.0, 0.0, 0.0])
    hits = index.search(query_vector=[0.05, 0.0, 0.0, 0.0, 0.0, 0.0], top_k=2, layer_window=7)
    by_id = {hit.doc_id: hit for hit in hits}
    assert by_id["inner"].layer <= by_id["outer"].layer


def test_search_prefers_closer_topic() -> None:
    index = HyperSphereIndex(dimensions=6, layer_count=8, max_radius=0.95)
    index.add(doc_id="topic-a-1", text="A one", vector=[0.5, 0.0, 0.0, 0.0, 0.0, 0.0], metadata={"topic": "A"})
    index.add(doc_id="topic-a-2", text="A two", vector=[0.48, 0.02, 0.0, 0.0, 0.0, 0.0], metadata={"topic": "A"})
    index.add(doc_id="topic-b-1", text="B one", vector=[-0.5, 0.0, 0.0, 0.0, 0.0, 0.0], metadata={"topic": "B"})
    index.add(doc_id="topic-b-2", text="B two", vector=[-0.45, -0.03, 0.0, 0.0, 0.0, 0.0], metadata={"topic": "B"})

    hits = index.search(query_vector=[0.52, 0.01, 0.0, 0.0, 0.0, 0.0], top_k=2, layer_window=2)
    assert len(hits) == 2
    assert all(hit.metadata.get("topic") == "A" for hit in hits)
