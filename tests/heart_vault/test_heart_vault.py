"""
Heart Vault — Comprehensive Test Suite
=========================================

Tests the full Heart Vault module:
    1. Graph CRUD (nodes, edges, queries, subgraph extraction)
    2. Emotion taxonomy & Poincaré Ball projection
    3. Literary device detection & metaphor resolution
    4. Heart Credit ledger (contribute, query, validate, penalty)
    5. Integration: literary detection → graph insertion → credit accounting
"""

from __future__ import annotations

import math
import sys
import os

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.concept_blocks.heart_vault import (
    # Graph
    HeartVaultGraph,
    Node,
    Edge,
    NodeType,
    EdgeType,
    TongueAffinity,
    # Emotions
    EMOTION_LIBRARY,
    EmotionFamily,
    EmotionIntensity,
    EmotionSpec,
    classify_emotion,
    emotion_to_poincare,
    emotional_distance,
    poincare_distance,
    valence_arousal_to_poincare,
    # Literary
    METAPHOR_MAP,
    LiteraryDevice,
    LiteraryHit,
    MetaphorMapping,
    detect_literary_devices,
    resolve_metaphor,
    # Heart Credits
    HeartCreditEntry,
    HeartCreditLedger,
    CreditAction,
    TONGUE_WEIGHTS,
    BASE_CONTRIBUTE_REWARD,
    BASE_QUERY_COST,
    VALIDATION_BONUS,
    PENALTY_AMOUNT,
)


# ===================================================================
#  1. Graph CRUD
# ===================================================================

class TestHeartVaultGraph:
    """Tests for the SQLite-backed knowledge graph."""

    def setup_method(self):
        self.vault = HeartVaultGraph(":memory:")

    def teardown_method(self):
        self.vault.close()

    # -- Node operations --

    def test_add_and_get_node(self):
        node = self.vault.add_node(
            NodeType.EMOTION, "joy",
            properties={"valence": 0.8, "arousal": 0.3},
            tongue=TongueAffinity.KO,
            quality_score=0.9,
        )
        assert node.id
        assert node.node_type == NodeType.EMOTION
        assert node.label == "joy"
        assert node.properties["valence"] == 0.8
        assert node.tongue == TongueAffinity.KO
        assert node.quality_score == 0.9

        fetched = self.vault.get_node(node.id)
        assert fetched is not None
        assert fetched.label == "joy"
        assert fetched.properties["arousal"] == 0.3

    def test_add_node_with_custom_id(self):
        node = self.vault.add_node(NodeType.CONCEPT, "time", node_id="time-001")
        assert node.id == "time-001"
        assert self.vault.get_node("time-001") is not None

    def test_get_nonexistent_node_returns_none(self):
        assert self.vault.get_node("nonexistent") is None

    def test_update_node(self):
        node = self.vault.add_node(NodeType.PROVERB, "Original text")
        ok = self.vault.update_node(node.id, label="Updated text", quality_score=0.7)
        assert ok is True

        updated = self.vault.get_node(node.id)
        assert updated is not None
        assert updated.label == "Updated text"
        assert updated.quality_score == 0.7

    def test_update_nonexistent_node_returns_false(self):
        assert self.vault.update_node("nope", label="x") is False

    def test_delete_node(self):
        node = self.vault.add_node(NodeType.CONCEPT, "deletable")
        assert self.vault.delete_node(node.id) is True
        assert self.vault.get_node(node.id) is None

    def test_delete_node_cascades_edges(self):
        n1 = self.vault.add_node(NodeType.CONCEPT, "A")
        n2 = self.vault.add_node(NodeType.CONCEPT, "B")
        self.vault.add_edge(EdgeType.MAPS_TO, n1.id, n2.id)
        assert self.vault.edge_count() == 1

        self.vault.delete_node(n1.id)
        assert self.vault.edge_count() == 0

    def test_node_count(self):
        assert self.vault.node_count() == 0
        self.vault.add_node(NodeType.EMOTION, "joy")
        self.vault.add_node(NodeType.EMOTION, "fear")
        self.vault.add_node(NodeType.LITERARY, "metaphor")
        assert self.vault.node_count() == 3
        assert self.vault.node_count(NodeType.EMOTION) == 2
        assert self.vault.node_count(NodeType.LITERARY) == 1

    def test_find_nodes_by_type(self):
        self.vault.add_node(NodeType.EMOTION, "joy")
        self.vault.add_node(NodeType.EMOTION, "fear")
        self.vault.add_node(NodeType.CONCEPT, "time")

        emotions = self.vault.find_nodes(node_type=NodeType.EMOTION)
        assert len(emotions) == 2
        assert all(n.node_type == NodeType.EMOTION for n in emotions)

    def test_find_nodes_by_tongue(self):
        self.vault.add_node(NodeType.PROVERB, "Proverb 1", tongue=TongueAffinity.RU)
        self.vault.add_node(NodeType.PROVERB, "Proverb 2", tongue=TongueAffinity.DR)
        self.vault.add_node(NodeType.PROVERB, "Proverb 3", tongue=TongueAffinity.RU)

        ru_nodes = self.vault.find_nodes(tongue=TongueAffinity.RU)
        assert len(ru_nodes) == 2

    def test_find_nodes_by_label(self):
        self.vault.add_node(NodeType.CONCEPT, "time flies")
        self.vault.add_node(NodeType.CONCEPT, "time heals")
        self.vault.add_node(NodeType.CONCEPT, "love conquers")

        results = self.vault.find_nodes(label_contains="time")
        assert len(results) == 2

    def test_find_nodes_min_quality(self):
        self.vault.add_node(NodeType.PROVERB, "Low quality", quality_score=0.2)
        self.vault.add_node(NodeType.PROVERB, "High quality", quality_score=0.9)

        results = self.vault.find_nodes(min_quality=0.5)
        assert len(results) == 1
        assert results[0].label == "High quality"

    def test_content_hash_deterministic(self):
        n1 = self.vault.add_node(NodeType.CONCEPT, "test", properties={"k": "v"})
        n2 = Node(id="other", node_type=NodeType.CONCEPT, label="test",
                   properties={"k": "v"})
        assert n1.content_hash() == n2.content_hash()

    # -- Edge operations --

    def test_add_and_get_edges(self):
        n1 = self.vault.add_node(NodeType.LITERARY, "Time is a thief")
        n2 = self.vault.add_node(NodeType.EMOTION, "loss")

        edge = self.vault.add_edge(
            EdgeType.EVOKES, n1.id, n2.id,
            weight=0.9,
            properties={"intensity": "high"},
        )
        assert edge.edge_type == EdgeType.EVOKES
        assert edge.weight == 0.9

        edges = self.vault.get_edges(source_id=n1.id)
        assert len(edges) == 1
        assert edges[0].target_id == n2.id

    def test_get_edges_by_type(self):
        n1 = self.vault.add_node(NodeType.CONCEPT, "A")
        n2 = self.vault.add_node(NodeType.CONCEPT, "B")
        n3 = self.vault.add_node(NodeType.SOURCE, "S")

        self.vault.add_edge(EdgeType.MAPS_TO, n1.id, n2.id)
        self.vault.add_edge(EdgeType.SOURCED_FROM, n1.id, n3.id)

        maps = self.vault.get_edges(edge_type=EdgeType.MAPS_TO)
        assert len(maps) == 1

    def test_neighbors_outgoing(self):
        n1 = self.vault.add_node(NodeType.LITERARY, "metaphor")
        n2 = self.vault.add_node(NodeType.EMOTION, "fear")
        n3 = self.vault.add_node(NodeType.EMOTION, "anger")
        self.vault.add_edge(EdgeType.EVOKES, n1.id, n2.id)
        self.vault.add_edge(EdgeType.EVOKES, n1.id, n3.id)

        neighbors = self.vault.neighbors(n1.id, edge_type=EdgeType.EVOKES)
        assert len(neighbors) == 2
        labels = {n.label for _, n in neighbors}
        assert labels == {"fear", "anger"}

    def test_neighbors_incoming(self):
        n1 = self.vault.add_node(NodeType.LITERARY, "metaphor")
        n2 = self.vault.add_node(NodeType.EMOTION, "fear")
        self.vault.add_edge(EdgeType.EVOKES, n1.id, n2.id)

        incoming = self.vault.neighbors(n2.id, direction="incoming")
        assert len(incoming) == 1
        assert incoming[0][1].label == "metaphor"

    def test_edge_count(self):
        n1 = self.vault.add_node(NodeType.CONCEPT, "A")
        n2 = self.vault.add_node(NodeType.CONCEPT, "B")
        assert self.vault.edge_count() == 0

        self.vault.add_edge(EdgeType.MAPS_TO, n1.id, n2.id)
        assert self.vault.edge_count() == 1

    # -- Graph queries --

    def test_shortest_path(self):
        a = self.vault.add_node(NodeType.CONCEPT, "A")
        b = self.vault.add_node(NodeType.CONCEPT, "B")
        c = self.vault.add_node(NodeType.CONCEPT, "C")
        self.vault.add_edge(EdgeType.MAPS_TO, a.id, b.id)
        self.vault.add_edge(EdgeType.MAPS_TO, b.id, c.id)

        path = self.vault.shortest_path(a.id, c.id)
        assert path is not None
        assert path == [a.id, b.id, c.id]

    def test_shortest_path_direct(self):
        a = self.vault.add_node(NodeType.CONCEPT, "A")
        b = self.vault.add_node(NodeType.CONCEPT, "B")
        self.vault.add_edge(EdgeType.MAPS_TO, a.id, b.id)

        path = self.vault.shortest_path(a.id, b.id)
        assert path == [a.id, b.id]

    def test_shortest_path_same_node(self):
        a = self.vault.add_node(NodeType.CONCEPT, "A")
        assert self.vault.shortest_path(a.id, a.id) == [a.id]

    def test_shortest_path_no_connection(self):
        a = self.vault.add_node(NodeType.CONCEPT, "A")
        b = self.vault.add_node(NodeType.CONCEPT, "B")
        assert self.vault.shortest_path(a.id, b.id) is None

    def test_subgraph(self):
        center = self.vault.add_node(NodeType.CONCEPT, "center")
        n1 = self.vault.add_node(NodeType.EMOTION, "near1")
        n2 = self.vault.add_node(NodeType.EMOTION, "near2")
        far = self.vault.add_node(NodeType.CONCEPT, "far")
        self.vault.add_edge(EdgeType.EVOKES, center.id, n1.id)
        self.vault.add_edge(EdgeType.EVOKES, center.id, n2.id)
        self.vault.add_edge(EdgeType.MAPS_TO, n1.id, far.id)

        nodes, edges = self.vault.subgraph(center.id, depth=1)
        node_ids = {n.id for n in nodes}
        assert center.id in node_ids
        assert n1.id in node_ids
        assert n2.id in node_ids
        # 'far' is 2 hops away, depth=1 should not include it
        assert far.id not in node_ids

    def test_subgraph_depth_2(self):
        center = self.vault.add_node(NodeType.CONCEPT, "center")
        n1 = self.vault.add_node(NodeType.EMOTION, "near")
        far = self.vault.add_node(NodeType.CONCEPT, "far")
        self.vault.add_edge(EdgeType.EVOKES, center.id, n1.id)
        self.vault.add_edge(EdgeType.MAPS_TO, n1.id, far.id)

        nodes, edges = self.vault.subgraph(center.id, depth=2)
        node_ids = {n.id for n in nodes}
        assert far.id in node_ids

    # -- Stats --

    def test_stats(self):
        self.vault.add_node(NodeType.EMOTION, "joy")
        self.vault.add_node(NodeType.LITERARY, "metaphor")
        self.vault.add_node(NodeType.PROVERB, "proverb")
        n1 = self.vault.add_node(NodeType.CONCEPT, "A")
        n2 = self.vault.add_node(NodeType.CONCEPT, "B")
        self.vault.add_edge(EdgeType.MAPS_TO, n1.id, n2.id)

        stats = self.vault.stats()
        assert stats["total_nodes"] == 5
        assert stats["total_edges"] == 1
        assert stats["nodes_by_type"]["EMOTION"] == 1
        assert stats["nodes_by_type"]["CONCEPT"] == 2


# ===================================================================
#  2. Emotion Taxonomy & Poincaré Ball
# ===================================================================

class TestEmotions:
    """Tests for the emotion taxonomy and Poincaré projection."""

    def test_emotion_library_populated(self):
        assert len(EMOTION_LIBRARY) > 20
        assert "joy" in EMOTION_LIBRARY
        assert "fear" in EMOTION_LIBRARY
        assert "rage" in EMOTION_LIBRARY

    def test_emotion_spec_fields(self):
        joy = EMOTION_LIBRARY["joy"]
        assert joy.family == EmotionFamily.JOY
        assert joy.intensity == EmotionIntensity.MEDIUM
        assert joy.valence > 0
        assert isinstance(joy.arousal, float)

    def test_composite_emotions(self):
        assert "love" in EMOTION_LIBRARY
        assert "nostalgia" in EMOTION_LIBRARY
        assert "hope" in EMOTION_LIBRARY
        assert "anxiety" in EMOTION_LIBRARY

    def test_valence_arousal_to_poincare_origin(self):
        x, y = valence_arousal_to_poincare(0.0, 0.0)
        assert x == 0.0
        assert y == 0.0

    def test_valence_arousal_to_poincare_inside_disk(self):
        x, y = valence_arousal_to_poincare(0.8, 0.6)
        r = math.sqrt(x * x + y * y)
        assert r < 1.0, "Point must be inside the unit disk"

    def test_extreme_emotions_near_boundary(self):
        """High valence+arousal should map closer to the disk boundary."""
        x_mild, y_mild = valence_arousal_to_poincare(0.2, 0.1)
        x_extreme, y_extreme = valence_arousal_to_poincare(0.9, 0.9)

        r_mild = math.sqrt(x_mild ** 2 + y_mild ** 2)
        r_extreme = math.sqrt(x_extreme ** 2 + y_extreme ** 2)
        assert r_extreme > r_mild

    def test_poincare_distance_same_point(self):
        p = valence_arousal_to_poincare(0.5, 0.5)
        d = poincare_distance(p, p)
        assert abs(d) < 1e-10

    def test_poincare_distance_positive(self):
        p1 = valence_arousal_to_poincare(0.8, 0.3)  # joy
        p2 = valence_arousal_to_poincare(-0.9, 0.9)  # rage
        d = poincare_distance(p1, p2)
        assert d > 0

    def test_opposing_emotions_far_apart(self):
        """Joy and rage should be farther apart than joy and serenity."""
        d_joy_rage = emotional_distance("joy", "rage")
        d_joy_serenity = emotional_distance("joy", "serenity")
        assert d_joy_rage is not None
        assert d_joy_serenity is not None
        assert d_joy_rage > d_joy_serenity

    def test_emotion_to_poincare_returns_none_for_unknown(self):
        assert emotion_to_poincare("nonexistent_emotion") is None

    def test_emotional_distance_returns_none_for_unknown(self):
        assert emotional_distance("joy", "nonexistent") is None

    def test_classify_emotion_nearest(self):
        """Classify a point near joy."""
        spec = classify_emotion(0.8, 0.3)
        assert spec.name == "joy"

    def test_classify_emotion_negative(self):
        spec = classify_emotion(-0.9, 1.0)
        assert spec.name == "rage"

    def test_all_emotions_project_inside_disk(self):
        """Every emotion in the library must project inside the unit disk."""
        for name, spec in EMOTION_LIBRARY.items():
            x, y = valence_arousal_to_poincare(spec.valence, spec.arousal)
            r = math.sqrt(x * x + y * y)
            assert r < 1.0, f"{name} projected outside disk: r={r}"


# ===================================================================
#  3. Literary Device Detection
# ===================================================================

class TestLiteraryDevices:
    """Tests for literary device detection and metaphor resolution."""

    def test_detect_known_metaphor(self):
        hits = detect_literary_devices("Time is a thief that steals our youth.")
        metaphors = [h for h in hits if h.device == LiteraryDevice.METAPHOR]
        assert len(metaphors) >= 1
        assert metaphors[0].tenor == "time"
        assert metaphors[0].vehicle == "thief"
        assert metaphors[0].confidence >= 0.8
        assert metaphors[0].emotion_hint == "loss"

    def test_detect_unknown_metaphor(self):
        hits = detect_literary_devices("The world is a canvas.")
        metaphors = [h for h in hits if h.device == LiteraryDevice.METAPHOR]
        assert len(metaphors) >= 1
        assert metaphors[0].confidence <= 0.6  # Lower confidence for unknown

    def test_detect_simile(self):
        hits = detect_literary_devices("Life is like a box of chocolates.")
        similes = [h for h in hits if h.device == LiteraryDevice.SIMILE]
        assert len(similes) >= 1

    def test_detect_personification(self):
        hits = detect_literary_devices("The wind whispered through the trees.")
        personifications = [h for h in hits if h.device == LiteraryDevice.PERSONIFICATION]
        assert len(personifications) >= 1
        assert "wind whispered" in personifications[0].text

    def test_detect_hyperbole(self):
        hits = detect_literary_devices("I've told you a million times to stop.")
        hyperboles = [h for h in hits if h.device == LiteraryDevice.HYPERBOLE]
        assert len(hyperboles) >= 1

    def test_detect_oxymoron(self):
        hits = detect_literary_devices("There was a deafening silence in the room.")
        oxymorons = [h for h in hits if h.device == LiteraryDevice.OXYMORON]
        assert len(oxymorons) >= 1
        assert "deafening" in oxymorons[0].text
        assert "silence" in oxymorons[0].text

    def test_detect_alliteration(self):
        hits = detect_literary_devices("Peter Piper picked a peck of pickled peppers.")
        alliterations = [h for h in hits if h.device == LiteraryDevice.ALLITERATION]
        assert len(alliterations) >= 1

    def test_no_false_positives_on_plain_text(self):
        hits = detect_literary_devices("The cat sat on the mat.")
        metaphors = [h for h in hits if h.device == LiteraryDevice.METAPHOR
                     and h.confidence > 0.7]
        assert len(metaphors) == 0

    def test_sorted_by_confidence(self):
        hits = detect_literary_devices(
            "Time is a thief. The deafening silence broke. "
            "She told him a million times."
        )
        if len(hits) >= 2:
            for i in range(len(hits) - 1):
                assert hits[i].confidence >= hits[i + 1].confidence

    def test_resolve_known_metaphor(self):
        result = resolve_metaphor("time", "thief")
        assert result is not None
        mapping, emotion = result
        assert mapping.tenor == "time"
        assert mapping.vehicle == "thief"
        assert emotion.name  # Should resolve to a named emotion

    def test_resolve_unknown_metaphor(self):
        result = resolve_metaphor("banana", "spaceship")
        assert result is None

    def test_metaphor_map_populated(self):
        assert len(METAPHOR_MAP) > 10
        assert "time" in METAPHOR_MAP
        assert "love" in METAPHOR_MAP
        assert "death" in METAPHOR_MAP

    def test_multiple_vehicles_per_tenor(self):
        """Time has multiple vehicles: thief, river, healer."""
        assert len(METAPHOR_MAP["time"]) >= 3


# ===================================================================
#  4. Heart Credit Ledger
# ===================================================================

class TestHeartCredits:
    """Tests for the Heart Credit economy."""

    def setup_method(self):
        self.vault = HeartVaultGraph(":memory:")
        self.ledger = HeartCreditLedger(self.vault)

    def teardown_method(self):
        self.vault.close()

    def test_contribute_earns_credits(self):
        node = self.vault.add_node(NodeType.PROVERB, "Test proverb",
                                   tongue=TongueAffinity.KO, quality_score=0.8)
        entry = self.ledger.contribute("agent-1", node.id, TongueAffinity.KO,
                                       quality_score=0.8)
        assert entry.amount > 0
        assert entry.action == CreditAction.CONTRIBUTE
        expected = BASE_CONTRIBUTE_REWARD * 0.8 * TONGUE_WEIGHTS[TongueAffinity.KO]
        assert abs(entry.amount - expected) < 0.01

    def test_higher_tongue_earns_more(self):
        n1 = self.vault.add_node(NodeType.PROVERB, "KO proverb")
        n2 = self.vault.add_node(NodeType.PROVERB, "DR proverb")

        e1 = self.ledger.contribute("a1", n1.id, TongueAffinity.KO, quality_score=0.5)
        e2 = self.ledger.contribute("a2", n2.id, TongueAffinity.DR, quality_score=0.5)
        assert e2.amount > e1.amount

    def test_query_costs_credits(self):
        entry = self.ledger.query("agent-1")
        assert entry.amount < 0
        assert abs(entry.amount + BASE_QUERY_COST) < 0.01

    def test_validate_earns_bonus(self):
        node = self.vault.add_node(NodeType.PROVERB, "Validated proverb")
        entry = self.ledger.validate("agent-1", node.id, TongueAffinity.RU)
        assert entry.amount > 0
        expected = VALIDATION_BONUS * TONGUE_WEIGHTS[TongueAffinity.RU]
        assert abs(entry.amount - expected) < 0.01

    def test_penalty_deducts_credits(self):
        node = self.vault.add_node(NodeType.PROVERB, "Bad proverb")
        entry = self.ledger.penalize("agent-1", node.id, TongueAffinity.KO)
        assert entry.amount == -PENALTY_AMOUNT

    def test_balance(self):
        node = self.vault.add_node(NodeType.PROVERB, "Good proverb")

        self.ledger.contribute("agent-1", node.id, TongueAffinity.KO, quality_score=1.0)
        self.ledger.query("agent-1")

        balance = self.ledger.balance("agent-1")
        expected = (BASE_CONTRIBUTE_REWARD * 1.0 * TONGUE_WEIGHTS[TongueAffinity.KO]) - BASE_QUERY_COST
        assert abs(balance - expected) < 0.01

    def test_balance_zero_for_unknown_agent(self):
        assert self.ledger.balance("nobody") == 0.0

    def test_history(self):
        node = self.vault.add_node(NodeType.PROVERB, "Proverb")
        self.ledger.contribute("agent-1", node.id, TongueAffinity.KO)
        self.ledger.query("agent-1")
        self.ledger.query("agent-1")

        history = self.ledger.history("agent-1")
        assert len(history) == 3
        # Most recent first
        assert history[0].action == CreditAction.QUERY
        assert history[2].action == CreditAction.CONTRIBUTE

    def test_leaderboard(self):
        n1 = self.vault.add_node(NodeType.PROVERB, "P1")
        n2 = self.vault.add_node(NodeType.PROVERB, "P2")

        self.ledger.contribute("rich-agent", n1.id, TongueAffinity.DR, quality_score=1.0)
        self.ledger.contribute("poor-agent", n2.id, TongueAffinity.KO, quality_score=0.1)

        board = self.ledger.leaderboard()
        assert len(board) == 2
        assert board[0]["agent_id"] == "rich-agent"
        assert board[0]["balance"] > board[1]["balance"]

    def test_stats(self):
        node = self.vault.add_node(NodeType.PROVERB, "P1")
        self.ledger.contribute("a1", node.id, TongueAffinity.KO)
        self.ledger.query("a2")

        stats = self.ledger.stats()
        assert stats["total_transactions"] == 2
        assert stats["total_earned"] > 0
        assert stats["total_spent"] < 0
        assert stats["unique_agents"] == 2


# ===================================================================
#  5. Integration: Literary → Graph → Credits
# ===================================================================

class TestIntegration:
    """End-to-end: detect devices, insert into graph, account credits."""

    def setup_method(self):
        self.vault = HeartVaultGraph(":memory:")
        self.ledger = HeartCreditLedger(self.vault)

    def teardown_method(self):
        self.vault.close()

    def test_metaphor_to_graph_to_credit(self):
        """
        Full pipeline:
        1. Detect "Time is a thief" as a metaphor
        2. Resolve to emotion (loss)
        3. Insert both into the graph
        4. Connect with EVOKES edge
        5. Agent earns Heart Credits for the contribution
        """
        text = "Time is a thief that robs us of precious moments."

        # Step 1: Detect
        hits = detect_literary_devices(text)
        metaphors = [h for h in hits if h.device == LiteraryDevice.METAPHOR]
        assert len(metaphors) >= 1
        hit = metaphors[0]
        assert hit.tenor == "time"
        assert hit.vehicle == "thief"

        # Step 2: Resolve to emotion
        result = resolve_metaphor(hit.tenor, hit.vehicle)
        assert result is not None
        mapping, emotion_spec = result

        # Step 3: Insert literary node
        lit_node = self.vault.add_node(
            NodeType.LITERARY, hit.text,
            properties={
                "device": hit.device.value,
                "tenor": hit.tenor,
                "vehicle": hit.vehicle,
                "confidence": hit.confidence,
            },
            tongue=TongueAffinity.CA,  # Cassisivadan for structural analysis
            quality_score=hit.confidence,
        )

        # Step 3b: Insert emotion node
        emotion_node = self.vault.add_node(
            NodeType.EMOTION, emotion_spec.name,
            properties={
                "valence": emotion_spec.valence,
                "arousal": emotion_spec.arousal,
                "family": emotion_spec.family.value,
            },
            tongue=TongueAffinity.KO,
            quality_score=0.95,
        )

        # Step 4: Connect literary → emotion
        edge = self.vault.add_edge(
            EdgeType.EVOKES, lit_node.id, emotion_node.id,
            weight=hit.confidence,
        )
        assert edge.weight == hit.confidence

        # Step 5: Agent earns credits
        entry = self.ledger.contribute(
            "metaphor-agent", lit_node.id,
            TongueAffinity.CA,
            quality_score=hit.confidence,
        )
        assert entry.amount > 0

        # Verify the graph
        neighbors = self.vault.neighbors(lit_node.id, edge_type=EdgeType.EVOKES)
        assert len(neighbors) == 1
        assert neighbors[0][1].label == emotion_spec.name

        # Verify the balance
        assert self.ledger.balance("metaphor-agent") > 0

    def test_proverb_ingestion_pipeline(self):
        """
        Ingest a proverb with Sacred Tongue categorization and credit accounting.
        """
        # The proverb
        proverb_text = "A stitch in time saves nine"

        # Runethic quality gate (simplified — in production this goes through
        # the semantic antivirus and governance pipeline)
        quality = 0.85

        # Insert as PROVERB node under Draumric (Structure/Order)
        node = self.vault.add_node(
            NodeType.PROVERB, proverb_text,
            properties={
                "source": "English folklore",
                "theme": "prudence",
                "culture": "Western",
            },
            tongue=TongueAffinity.DR,
            quality_score=quality,
        )

        # Link to concept: time
        time_concept = self.vault.add_node(
            NodeType.CONCEPT, "time",
            tongue=TongueAffinity.CA,
        )
        self.vault.add_edge(EdgeType.ILLUSTRATES, node.id, time_concept.id)

        # Credit the contributing agent
        self.ledger.contribute("proverb-collector", node.id,
                               TongueAffinity.DR, quality_score=quality)

        # Query by another agent
        self.ledger.query("wisdom-seeker", TongueAffinity.DR)

        # Verify
        assert self.vault.node_count(NodeType.PROVERB) == 1
        assert self.ledger.balance("proverb-collector") > 0
        assert self.ledger.balance("wisdom-seeker") < 0

    def test_emotion_poincare_integration(self):
        """
        Map emotions to Poincaré Ball and verify geometric properties
        are preserved in the graph context.
        """
        # Add emotions to graph with Poincaré coordinates
        for name in ["joy", "fear", "rage", "serenity"]:
            spec = EMOTION_LIBRARY[name]
            px, py = valence_arousal_to_poincare(spec.valence, spec.arousal)
            self.vault.add_node(
                NodeType.EMOTION, name,
                properties={
                    "valence": spec.valence,
                    "arousal": spec.arousal,
                    "poincare_x": px,
                    "poincare_y": py,
                },
                node_id=f"emotion-{name}",
            )

        # Connect opposing emotions
        self.vault.add_edge(EdgeType.CONTRASTS,
                            "emotion-joy", "emotion-rage")

        # Verify: joy and rage are far in hyperbolic space
        d = emotional_distance("joy", "rage")
        assert d is not None and d > 1.0

        # Verify: joy and serenity are close
        d2 = emotional_distance("joy", "serenity")
        assert d2 is not None and d2 < d

    def test_tongue_categorization(self):
        """All six Sacred Tongues should be usable for categorization."""
        for tongue in TongueAffinity:
            node = self.vault.add_node(
                NodeType.CONCEPT, f"concept-{tongue.value}",
                tongue=tongue,
            )
            fetched = self.vault.get_node(node.id)
            assert fetched is not None
            assert fetched.tongue == tongue

        # Each tongue should have exactly one node
        for tongue in TongueAffinity:
            results = self.vault.find_nodes(tongue=tongue)
            assert len(results) == 1


# ===================================================================
#  6. Edge cases
# ===================================================================

class TestEdgeCases:

    def test_empty_graph_stats(self):
        vault = HeartVaultGraph(":memory:")
        stats = vault.stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        vault.close()

    def test_empty_text_detection(self):
        hits = detect_literary_devices("")
        assert hits == []

    def test_very_long_text(self):
        text = "Time is a thief. " * 1000
        hits = detect_literary_devices(text)
        assert len(hits) > 0

    def test_poincare_clamping(self):
        """Values outside [-1,1] should be clamped."""
        x, y = valence_arousal_to_poincare(5.0, -5.0)
        r = math.sqrt(x * x + y * y)
        assert r < 1.0

    def test_tongue_weights_golden_ratio(self):
        """Tongue weights should follow phi scaling."""
        phi = (1 + math.sqrt(5)) / 2
        assert abs(TONGUE_WEIGHTS[TongueAffinity.AV] - phi) < 0.001
        assert abs(TONGUE_WEIGHTS[TongueAffinity.RU] - phi ** 2) < 0.001
        assert abs(TONGUE_WEIGHTS[TongueAffinity.CA] - phi ** 3) < 0.001
