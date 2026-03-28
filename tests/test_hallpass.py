"""Tests for Hall Pass: Hamiltonian Corridor Pathfinding."""

import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.fleet.skill_card_forge import SkillCard  # noqa: F401
except (ImportError, ModuleNotFoundError):
    pytest.skip(
        "skill_card_forge module not available (removed or not yet built)",
        allow_module_level=True,
    )

from src.fleet.hallpass import (
    PHI,
    POLYHEDRA,
    POLYHEDRA_BY_ID,
    EDGE_PENALTIES,
    TONGUE_PHASES,
    TUBE_RADIUS,
    HallPass,
    HallPassCompiler,
    HallPassDispatcher,
    DispatchResult,
    map_card_to_polyhedron,
    get_edge_penalty,
    find_hamiltonian_path,
    compute_path_cost,
    classify_tongue_phase,
    project_to_face,
    harmonic_wall_cost,
    hyperbolic_distance_approx,
)
from src.fleet.skill_card_forge import Deck  # SkillCard already imported above

_CARD_TEMPLATES = [
    (
        "web-scraper",
        "Skill",
        "Offensive",
        300,
        3,
        2,
        "browse navigate search web scrape urls",
        ["browser"],
    ),
    (
        "data-processor",
        "Skill",
        "Support",
        250,
        4,
        1,
        "process transform data analyze compute",
        ["data"],
    ),
    (
        "governance-gate",
        "Defense",
        "Defensive",
        400,
        5,
        3,
        "governance safety quarantine deny audit gate",
        ["governance"],
    ),
    (
        "fleet-deployer",
        "Agent",
        "Orchestrator",
        500,
        6,
        4,
        "deploy orchestrate fleet coordinate multi-agent dispatch",
        ["deploy"],
    ),
    (
        "hf-publisher",
        "Workflow",
        "Offensive",
        350,
        3,
        2,
        "publish deploy huggingface push dataset model",
        ["publish"],
    ),
    (
        "entropy-monitor",
        "Skill",
        "Arcane",
        600,
        7,
        3,
        "entropy quantum geometry manifold sacred tongue",
        ["entropy"],
    ),
]


def _make_cards(n: int = 6) -> list:
    """Create n test skill cards."""
    cards = []
    for i in range(min(n, len(_CARD_TEMPLATES))):
        name, ctype, syn, power, comp, scope, desc, tags = _CARD_TEMPLATES[i]
        cards.append(
            SkillCard(
                name=name,
                card_id=f"t{i}",
                card_type=ctype,
                synergy=syn,
                power=power,
                complexity=comp,
                scope=scope,
                description=desc,
                tags=tags,
            )
        )
    return cards


# ============================================================
# PHDM Polyhedra Tests
# ============================================================


class TestPolyhedra:
    """Test the 16 PHDM polyhedra are correctly defined."""

    def test_exactly_16_polyhedra(self):
        assert len(POLYHEDRA) == 16

    def test_ids_sequential(self):
        for i, p in enumerate(POLYHEDRA):
            assert p.id == i, f"Polyhedron {p.name} has id {p.id}, expected {i}"

    def test_all_have_6d_positions(self):
        for p in POLYHEDRA:
            assert len(p.position_6d) == 6, f"{p.name} has {len(p.position_6d)}D position"

    def test_platonic_five_cheap(self):
        """Platonic solids should have energy E0 = 1.0-2.5 (safe core)."""
        platonic = [p for p in POLYHEDRA if p.category == "platonic"]
        assert len(platonic) == 5
        for p in platonic:
            assert 1.0 <= p.energy_base <= 2.5, f"{p.name} energy={p.energy_base}"

    def test_archimedean_three_medium(self):
        """Archimedean should have energy E1 = 4.0-7.0."""
        arch = [p for p in POLYHEDRA if p.category == "archimedean"]
        assert len(arch) == 3
        for p in arch:
            assert 4.0 <= p.energy_base <= 7.0, f"{p.name} energy={p.energy_base}"

    def test_kepler_two_expensive(self):
        """Kepler-Poinsot should have energy E2 = 12.0-15.0 (adversarial)."""
        kepler = [p for p in POLYHEDRA if p.category == "kepler"]
        assert len(kepler) == 2
        for p in kepler:
            assert 12.0 <= p.energy_base <= 15.0, f"{p.name} energy={p.energy_base}"

    def test_polyhedra_by_id_lookup(self):
        for p in POLYHEDRA:
            assert POLYHEDRA_BY_ID[p.id] is p

    def test_categories_complete(self):
        categories = {p.category for p in POLYHEDRA}
        assert categories == {
            "platonic",
            "archimedean",
            "kepler",
            "toroidal",
            "rhombic",
            "johnson",
        }


# ============================================================
# Edge Penalty Tests
# ============================================================


class TestEdgePenalties:
    """Test edge transition penalties match PHDM spec."""

    def test_platonic_to_platonic_cheap(self):
        assert EDGE_PENALTIES[("platonic", "platonic")] == 0.5

    def test_kepler_to_kepler_expensive(self):
        assert EDGE_PENALTIES[("kepler", "kepler")] == 12.0

    def test_archimedean_to_kepler_high(self):
        assert EDGE_PENALTIES[("archimedean", "kepler")] == 8.0

    def test_symmetric_lookup(self):
        """get_edge_penalty should work regardless of order."""
        p0 = POLYHEDRA[0]  # Tetrahedron (platonic)
        p5 = POLYHEDRA[5]  # Truncated Icosahedron (archimedean)
        assert get_edge_penalty(p0, p5) == get_edge_penalty(p5, p0)

    def test_platonic_to_toroidal(self):
        assert EDGE_PENALTIES[("platonic", "toroidal")] == 4.0


# ============================================================
# Card → Polyhedron Mapping Tests
# ============================================================


class TestCardMapping:
    """Test that SkillCards map to correct polyhedra."""

    def _make_card(self, synergy: str, card_type: str, power: int) -> SkillCard:
        return SkillCard(
            name="test-card",
            card_id="abc123",
            card_type=card_type,
            synergy=synergy,
            power=power,
        )

    def test_agent_maps_to_toroidal(self):
        card = self._make_card("Offensive", "Agent", 300)
        poly = map_card_to_polyhedron(card)
        assert poly.category == "toroidal"

    def test_workflow_maps_to_rhombic(self):
        card = self._make_card("Offensive", "Workflow", 300)
        poly = map_card_to_polyhedron(card)
        assert poly.category == "rhombic"

    def test_defense_maps_to_archimedean(self):
        card = self._make_card("Defensive", "Defense", 300)
        poly = map_card_to_polyhedron(card)
        assert poly.category == "archimedean"

    def test_research_maps_to_johnson(self):
        card = self._make_card("Offensive", "Research", 300)
        poly = map_card_to_polyhedron(card)
        assert poly.category == "johnson"

    def test_arcane_maps_to_kepler(self):
        card = self._make_card("Arcane", "Skill", 600)
        poly = map_card_to_polyhedron(card)
        assert poly.category == "kepler"

    def test_low_power_offensive_maps_to_tetrahedron(self):
        card = self._make_card("Offensive", "Skill", 100)
        poly = map_card_to_polyhedron(card)
        assert poly.id == 0  # Tetrahedron

    def test_high_power_offensive_maps_to_icosahedron(self):
        card = self._make_card("Offensive", "Skill", 600)
        poly = map_card_to_polyhedron(card)
        assert poly.id == 4  # Icosahedron

    def test_orchestrator_maps_to_snub_dodecahedron(self):
        card = self._make_card("Orchestrator", "Skill", 400)
        poly = map_card_to_polyhedron(card)
        assert poly.id == 7  # Snub Dodecahedron


# ============================================================
# Hamiltonian Path Tests
# ============================================================


class TestHamiltonianPath:
    """Test Hamiltonian path finding."""

    def test_empty_input(self):
        assert find_hamiltonian_path([]) == []

    def test_single_node(self):
        path = find_hamiltonian_path([POLYHEDRA[0]])
        assert len(path) == 1
        assert path[0] is POLYHEDRA[0]

    def test_visits_each_node_exactly_once(self):
        nodes = POLYHEDRA[:5]  # Platonic five
        path = find_hamiltonian_path(nodes)
        assert len(path) == 5
        ids = [p.id for p in path]
        assert len(set(ids)) == 5, "Path must visit each node exactly once"

    def test_all_nodes_present(self):
        nodes = POLYHEDRA[:5]
        path = find_hamiltonian_path(nodes)
        path_ids = set(p.id for p in path)
        node_ids = set(p.id for p in nodes)
        assert path_ids == node_ids

    def test_path_starts_with_cheapest(self):
        nodes = [POLYHEDRA[0], POLYHEDRA[4], POLYHEDRA[9]]
        path = find_hamiltonian_path(nodes)
        # Should start with Tetrahedron (energy 1.0)
        assert path[0].id == 0

    def test_custom_start(self):
        nodes = POLYHEDRA[:3]
        path = find_hamiltonian_path(nodes, start=POLYHEDRA[2])
        assert path[0].id == 2

    def test_path_cost_correct(self):
        path = [POLYHEDRA[0], POLYHEDRA[1]]  # Tetra→Cube
        cost = compute_path_cost(path)
        expected = 1.0 + 1.2 + 0.5  # node0 + node1 + edge(platonic→platonic)
        assert abs(cost - expected) < 0.001

    def test_platonic_path_cheaper_than_mixed(self):
        """Platonic-only path should cost less than one with Kepler nodes."""
        platonic_path = POLYHEDRA[:3]
        mixed_path = [
            POLYHEDRA[0],
            POLYHEDRA[9],
            POLYHEDRA[1],
        ]  # inject Great Stellated
        assert compute_path_cost(platonic_path) < compute_path_cost(mixed_path)


# ============================================================
# Face Projection Tests
# ============================================================


class TestFaceProjection:
    """Test face projection reduces context cost."""

    def _make_card(self, power: int = 500, complexity: int = 5) -> SkillCard:
        return SkillCard(
            name="test-card",
            card_id="abc123",
            card_type="Skill",
            synergy="Offensive",
            power=power,
            complexity=complexity,
            description="publish deploy run process",
        )

    def test_projection_reduces_tokens(self):
        card = self._make_card()
        face = project_to_face(card, 0)
        assert face.projected_token_cost < face.full_token_cost

    def test_savings_roughly_five_sixths(self):
        """Projection should save ~60-85% of variable context."""
        card = self._make_card(power=800, complexity=8)
        face = project_to_face(card, 0)
        assert face.savings_pct > 0.5, f"Only saved {face.savings_pct:.0%}"
        assert face.savings_pct < 0.95, f"Saved too much: {face.savings_pct:.0%}"

    def test_face_code_matches_tongue(self):
        card = self._make_card()
        for phase in range(6):
            face = project_to_face(card, phase)
            assert face.face_code == TONGUE_PHASES[phase]["code"]

    def test_face_index_matches_phase(self):
        card = self._make_card()
        face = project_to_face(card, 3)
        assert face.face_index == 3
        assert face.face_code == "CA"

    def test_minimum_projected_cost(self):
        """Projected cost should never be below 200 (base floor)."""
        card = self._make_card(power=50, complexity=1)
        face = project_to_face(card, 0)
        assert face.projected_token_cost >= 200


# ============================================================
# Tongue Phase Classification Tests
# ============================================================


class TestTongueClassification:
    def test_publish_is_flow(self):
        assert classify_tongue_phase("publish content to all platforms") == 0  # KO=Flow

    def test_research_is_context(self):
        assert classify_tongue_phase("research academic papers and learn") == 1  # AV=Context

    def test_api_is_binding(self):
        assert classify_tongue_phase("integrate with API and connect services") == 2  # RU=Binding

    def test_code_is_bitcraft(self):
        assert classify_tongue_phase("build and implement new code") == 3  # CA=Bitcraft

    def test_security_is_veil(self):
        assert classify_tongue_phase("security audit and governance gate") == 4  # UM=Veil

    def test_deploy_is_structure(self):
        assert classify_tongue_phase("deploy and architect the system") == 5  # DR=Structure


# ============================================================
# Trust Tube + Harmonic Wall Tests
# ============================================================


class TestHarmonicWall:
    """Test the phi^(d^2) barrier function."""

    def test_inside_tube_zero_cost(self):
        assert harmonic_wall_cost(0.0) == 0.0
        assert harmonic_wall_cost(0.10) == 0.0
        assert harmonic_wall_cost(TUBE_RADIUS) == 0.0

    def test_just_outside_tube_small_cost(self):
        cost = harmonic_wall_cost(0.20)
        assert cost > 0.0
        assert cost < 2.0  # Should be mild

    def test_far_outside_exponential(self):
        cost_1 = harmonic_wall_cost(1.0)
        cost_2 = harmonic_wall_cost(2.0)
        cost_3 = harmonic_wall_cost(3.0)
        # Each step should be dramatically more expensive
        assert cost_2 > cost_1 * 3
        assert cost_3 > cost_2 * 10

    def test_phi_at_distance_1(self):
        """At d=1.0, cost should be phi^1 = phi."""
        cost = harmonic_wall_cost(1.0)
        assert abs(cost - PHI) < 0.01

    def test_phi_squared_at_distance_sqrt2(self):
        """At d=sqrt(2), cost should be phi^2."""
        cost = harmonic_wall_cost(math.sqrt(2))
        expected = PHI**2
        assert abs(cost - expected) < 0.01

    def test_distance_3_blocks(self):
        """At d=3.0, cost should be phi^(3^2) = phi^9 ~ 76 (effectively blocked)."""
        cost = harmonic_wall_cost(3.0)
        assert cost > 50  # 76x normal cost = blocked


class TestHyperbolicDistance:
    def test_same_point_zero(self):
        p = (0.1, 0.1, 0.1, 0.0, 0.0, 0.0)
        d = hyperbolic_distance_approx(p, p)
        assert abs(d) < 0.001

    def test_origin_to_point(self):
        origin = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        point = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
        d = hyperbolic_distance_approx(origin, point)
        assert d > 0.5  # Hyperbolic distance > Euclidean distance

    def test_symmetric(self):
        a = (0.1, 0.2, 0.0, 0.0, 0.0, 0.0)
        b = (0.3, 0.1, 0.0, 0.0, 0.0, 0.0)
        assert abs(hyperbolic_distance_approx(a, b) - hyperbolic_distance_approx(b, a)) < 0.001


# ============================================================
# HallPass Compiler Tests
# ============================================================


class TestHallPassCompiler:
    """End-to-end tests for the HallPass system."""

    @pytest.fixture
    def sample_cards(self) -> list:
        """Create a diverse set of test cards."""
        return [
            SkillCard(
                name="web-scraper",
                card_id="a1",
                card_type="Skill",
                synergy="Offensive",
                power=300,
                complexity=3,
                scope=2,
                description="browse navigate search web scrape urls",
                tags=["browser", "scrape"],
            ),
            SkillCard(
                name="data-processor",
                card_id="a2",
                card_type="Skill",
                synergy="Support",
                power=250,
                complexity=4,
                scope=1,
                description="process transform data analyze compute",
                tags=["data", "transform"],
            ),
            SkillCard(
                name="governance-gate",
                card_id="a3",
                card_type="Defense",
                synergy="Defensive",
                power=400,
                complexity=5,
                scope=3,
                description="governance safety quarantine deny audit gate",
                tags=["governance", "security"],
            ),
            SkillCard(
                name="fleet-deployer",
                card_id="a4",
                card_type="Agent",
                synergy="Orchestrator",
                power=500,
                complexity=6,
                scope=4,
                description="deploy orchestrate fleet coordinate multi-agent dispatch",
                tags=["deploy", "fleet"],
            ),
            SkillCard(
                name="hf-publisher",
                card_id="a5",
                card_type="Workflow",
                synergy="Offensive",
                power=350,
                complexity=3,
                scope=2,
                description="publish deploy huggingface push dataset model",
                tags=["publish", "huggingface"],
            ),
            SkillCard(
                name="entropy-monitor",
                card_id="a6",
                card_type="Skill",
                synergy="Arcane",
                power=600,
                complexity=7,
                scope=3,
                description="entropy quantum geometry manifold sacred tongue",
                tags=["entropy", "geometry"],
            ),
        ]

    def test_compile_produces_hallpass(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("publish data to HuggingFace", sample_cards, max_cards=4)
        assert isinstance(hp, HallPass)

    def test_hallpass_has_corridor(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("browse and publish content", sample_cards, max_cards=4)
        assert len(hp.corridor) > 0
        assert len(hp.corridor) <= 4

    def test_corridor_visits_each_once(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("full pipeline run", sample_cards, max_cards=6)
        card_ids = [n.card_id for n in hp.corridor]
        assert len(card_ids) == len(set(card_ids)), "Corridor must not revisit cards"

    def test_permissions_are_union(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("deploy and audit", sample_cards, max_cards=4)
        # Legacy permissions field is retained as non-authoritative capability hints.
        all_perms = set()
        for node in hp.corridor:
            all_perms.update(node.permissions)
        assert set(hp.permissions) == all_perms
        assert set(hp.capability_hints) == all_perms

    def test_guidance_metadata_present(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("split and publish across lanes", sample_cards, max_cards=4)
        assert hp.guidance_only is True
        assert hp.grants_access is False
        assert hp.branch_policy == "split"
        assert hp.lane_id
        assert hp.corridor_graph_id
        assert len(hp.expected_step_order) == hp.node_count

    def test_reservation_windows_monotonic(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("process data", sample_cards, max_cards=4)
        previous_end = 0
        for node in hp.corridor:
            assert node.slot_start_ms >= previous_end
            assert node.slot_end_ms > node.slot_start_ms
            previous_end = node.slot_end_ms
        assert hp.ttl_ms >= previous_end

    def test_context_savings_positive(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("research and publish", sample_cards, max_cards=4)
        assert hp.context_savings_pct > 0.0, "Face projection should save context"
        assert hp.total_projected_tokens < hp.total_full_tokens

    def test_energy_cumulative(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("process data", sample_cards, max_cards=3)
        # Last node's cumulative energy should equal total
        if hp.corridor:
            assert abs(hp.corridor[-1].cumulative_energy - hp.total_energy) < 0.01

    def test_tongue_override(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("do something", sample_cards, tongue_override=4)
        assert hp.tongue_phase == 4
        assert hp.tongue_code == "UM"
        for node in hp.corridor:
            assert node.face.face_code == "UM"

    def test_display_not_empty(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("publish", sample_cards, max_cards=3)
        text = hp.display()
        assert "HALL PASS" in text
        assert hp.tongue_code in text

    def test_to_json_valid(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("publish", sample_cards, max_cards=3)
        data = json.loads(hp.to_json())
        assert "corridor" in data
        assert "pass_id" in data
        assert len(data["corridor"]) == hp.node_count

    def test_pass_id_deterministic(self, sample_cards):
        """Same task + same cards → same pass ID."""
        compiler = HallPassCompiler()
        hp1 = compiler.compile("publish data", sample_cards, max_cards=3, workflow_name="test-pass")
        hp2 = compiler.compile("publish data", sample_cards, max_cards=3, workflow_name="test-pass")
        assert hp1.pass_id == hp2.pass_id

    def test_ten_agents_same_pass(self, sample_cards):
        """10 agents with the same HallPass get identical corridors."""
        compiler = HallPassCompiler()
        hp = compiler.compile("deploy fleet", sample_cards, max_cards=4, workflow_name="fleet-deploy")
        # Simulate 10 agents reading the same pass
        for _agent_num in range(10):
            corridor_ids = [n.card_id for n in hp.corridor]
            corridor_polys = [n.polyhedron_name for n in hp.corridor]
            # All agents see the same path
            assert corridor_ids == [n.card_id for n in hp.corridor]
            assert corridor_polys == [n.polyhedron_name for n in hp.corridor]
            assert hp.expected_step_order == [n.card_id for n in hp.corridor]

    def test_trust_tube_in_pass(self, sample_cards):
        compiler = HallPassCompiler()
        hp = compiler.compile("test", sample_cards, max_cards=2)
        assert hp.trust_tube_radius == TUBE_RADIUS
        assert hp.max_barrier_cost > 0


# ============================================================
# Integration: Real Deck Tests
# ============================================================


class TestRealDeck:
    """Test with the actual master deck if available."""

    @pytest.fixture
    def real_deck(self):
        deck_path = os.path.join(os.path.dirname(__file__), "..", "artifacts", "cards", "master_deck.json")
        if not os.path.exists(deck_path):
            pytest.skip("Master deck not found — run forge_cards.py --refresh --save first")
        return Deck.load(deck_path)

    def test_revenue_pipeline_hallpass(self, real_deck):
        compiler = HallPassCompiler()
        hp = compiler.compile(
            "monetization: publish content, sell on Shopify, post to YouTube, grow Twitter",
            real_deck.cards,
            max_cards=8,
            workflow_name="revenue-pipeline",
        )
        assert hp.node_count >= 3
        assert hp.context_savings_pct > 0.3
        print(hp.display())

    def test_research_governance_hallpass(self, real_deck):
        compiler = HallPassCompiler()
        hp = compiler.compile(
            "web research, academic paper search, governance validation, entropy monitoring",
            real_deck.cards,
            max_cards=6,
            workflow_name="research-governance",
        )
        assert hp.node_count >= 3
        assert hp.total_energy > 0
        print(hp.display())

    def test_agent_fleet_hallpass(self, real_deck):
        compiler = HallPassCompiler()
        hp = compiler.compile(
            "multi-agent coordination, cross-talk handoffs, flock management",
            real_deck.cards,
            max_cards=6,
            workflow_name="agent-fleet-ops",
        )
        assert hp.node_count >= 3
        print(hp.display())

    def test_browser_lore_hallpass(self, real_deck):
        compiler = HallPassCompiler()
        hp = compiler.compile(
            "browser automation, lore writing, story canon, game development",
            real_deck.cards,
            max_cards=6,
            workflow_name="browser-lore-game",
        )
        assert hp.node_count >= 3
        print(hp.display())


# ============================================================
# Switchboard Dispatch Tests
# ============================================================


class TestHallPassDispatcher:
    """Test dispatching hall passes to the HYDRA Switchboard."""

    @pytest.fixture
    def tmp_switchboard(self, tmp_path):
        """Create a temporary switchboard backed by a temp SQLite DB."""
        from hydra.switchboard import Switchboard

        db_path = str(tmp_path / "test_switchboard.db")
        return Switchboard(db_path=db_path)

    @pytest.fixture
    def sample_hallpass(self):
        """Compile a small hall pass from mock cards."""
        cards = _make_cards(4)
        compiler = HallPassCompiler()
        return compiler.compile("test deployment task", cards, max_cards=4)

    def test_dispatch_returns_result(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        result = dispatcher.dispatch(sample_hallpass)
        assert isinstance(result, DispatchResult)
        assert result.pass_id == sample_hallpass.pass_id
        assert result.dispatched == sample_hallpass.node_count

    def test_dispatch_creates_switchboard_tasks(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        result = dispatcher.dispatch(sample_hallpass)
        assert len(result.task_ids) == sample_hallpass.node_count
        # Verify all tasks are in the switchboard
        stats = tmp_switchboard.stats()
        total = sum(stats["by_status"].values())
        assert total == sample_hallpass.node_count

    def test_dispatch_tasks_are_queued(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        dispatcher.dispatch(sample_hallpass)
        stats = tmp_switchboard.stats()
        assert stats["by_status"].get("queued", 0) == sample_hallpass.node_count

    def test_dispatch_corridor_order_matches(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        result = dispatcher.dispatch(sample_hallpass)
        expected_names = [node.card_name for node in sample_hallpass.corridor]
        assert result.corridor_order == expected_names

    def test_dispatch_dedup_prevents_double(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        result1 = dispatcher.dispatch(sample_hallpass)
        result2 = dispatcher.dispatch(sample_hallpass)
        # Second dispatch should return same task count (deduped)
        assert result2.dispatched == result1.dispatched
        # Total tasks should still be the same (not doubled)
        stats = tmp_switchboard.stats()
        total = sum(stats["by_status"].values())
        assert total == sample_hallpass.node_count

    def test_dispatch_posts_channel_message(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        result = dispatcher.dispatch(sample_hallpass)
        msgs = tmp_switchboard.get_role_messages(result.role_channel)
        assert len(msgs) >= 1
        msg = msgs[0]["message"]
        assert msg["event"] == "corridor_dispatched"
        assert msg["pass_id"] == sample_hallpass.pass_id

    def test_dispatch_task_payload_has_hallpass_metadata(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        dispatcher.dispatch(sample_hallpass)
        # Claim the first task and inspect its payload
        claimed = tmp_switchboard.claim_task("test-worker", ["skill", "agent", "workflow", "tool", "defense"])
        assert claimed is not None
        payload = claimed["payload"]
        assert "hallpass" in payload
        assert payload["hallpass"]["pass_id"] == sample_hallpass.pass_id
        assert "node" in payload
        assert "energy" in payload
        assert "guidance" in payload
        assert payload["authorization"]["mode"] == "external"
        assert payload["hallpass"]["guidance_only"] is True
        assert "capability_hints" in payload
        assert "permissions" in payload

    def test_dispatch_worker_can_claim_and_complete(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        dispatcher.dispatch(sample_hallpass)
        # Claim all tasks and complete them
        completed = 0
        for _ in range(sample_hallpass.node_count + 1):
            claimed = tmp_switchboard.claim_task("worker-1", ["skill", "agent", "workflow", "tool", "defense"])
            if claimed is None:
                break
            ok = tmp_switchboard.complete_task(claimed["task_id"], "worker-1", {"status": "ok"})
            assert ok
            completed += 1
        assert completed == sample_hallpass.node_count
        stats = tmp_switchboard.stats()
        assert stats["by_status"].get("done", 0) == sample_hallpass.node_count

    def test_dispatch_result_to_dict(self, tmp_switchboard, sample_hallpass):
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        result = dispatcher.dispatch(sample_hallpass)
        d = result.to_dict()
        assert d["pass_id"] == sample_hallpass.pass_id
        assert d["dispatched"] == sample_hallpass.node_count
        assert isinstance(d["task_ids"], list)
        assert isinstance(d["corridor_order"], list)

    def test_dispatch_role_channel_unique_per_pass(self, tmp_switchboard):
        cards = _make_cards(3)
        compiler = HallPassCompiler()
        hp1 = compiler.compile("task alpha", cards, max_cards=3)
        hp2 = compiler.compile("task beta", cards, max_cards=3)
        dispatcher = HallPassDispatcher(switchboard=tmp_switchboard)
        r1 = dispatcher.dispatch(hp1)
        r2 = dispatcher.dispatch(hp2)
        assert r1.role_channel != r2.role_channel
        assert hp1.pass_id in r1.role_channel
        assert hp2.pass_id in r2.role_channel
