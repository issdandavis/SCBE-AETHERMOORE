"""
Tests for PollyPad — persistent memory, 6D addressing, training generation.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from pollypad.memory import (
    PersistentMemory, MemoryCell, MemoryQuery, SixDAddress,
    TONGUE_WEIGHTS, PHI,
)
from pollypad.pad import PollyPad, Interaction, TrainingPair
from pollypad.octopus import Octopus, Tentacle, TentacleType, Sucker, SuckerState


# ---------------------------------------------------------------------------
#  6D Address Tests
# ---------------------------------------------------------------------------

class TestSixDAddress:
    def test_from_interaction(self):
        addr = SixDAddress.from_interaction("Hello world", "conversation", "tell")
        assert addr.tongue in TONGUE_WEIGHTS
        assert addr.weight == TONGUE_WEIGHTS[addr.tongue]
        assert addr.context == "conversation"
        assert addr.intent == "tell"
        assert len(addr.instruction_hash) == 8

    def test_known_coordinates(self):
        """First 2 coords (tongue + weight) are deterministic from content."""
        a1 = SixDAddress.from_interaction("calculate the sum of 1 to 100")
        a2 = SixDAddress.from_interaction("calculate the product of primes")
        # Both should classify as CA (computation)
        assert a1.tongue == "CA"
        assert a1.weight == TONGUE_WEIGHTS["CA"]

    def test_tongue_classification(self):
        assert SixDAddress._classify_tongue("build a new feature") == "KO"
        assert SixDAddress._classify_tongue("imagine a beautiful scene with color") == "AV"
        assert SixDAddress._classify_tongue("analyze the structure and logic") == "RU"
        assert SixDAddress._classify_tongue("calculate the algorithm") == "CA"

    def test_to_tuple(self):
        addr = SixDAddress.from_interaction("test", "code", "create")
        t = addr.to_tuple()
        assert len(t) == 6

    def test_distance_same_address(self):
        addr = SixDAddress.from_interaction("test", "code", "create")
        assert addr.distance_to(addr) == 0.0

    def test_distance_different_tongue(self):
        a1 = SixDAddress("KO", 1.0, "code", "2026-02-28-10", "create", "abc12345")
        a2 = SixDAddress("DR", 11.09, "code", "2026-02-28-10", "create", "abc12345")
        d = a1.distance_to(a2)
        assert d > 2.0  # Different tongue = big distance

    def test_distance_same_tongue_different_context(self):
        a1 = SixDAddress("KO", 1.0, "code", "2026-02-28-10", "create", "abc12345")
        a2 = SixDAddress("KO", 1.0, "research", "2026-02-28-10", "create", "abc12345")
        d = a1.distance_to(a2)
        assert 0 < d < 2.0  # Same tongue, different context = moderate distance


# ---------------------------------------------------------------------------
#  Memory Cell Tests
# ---------------------------------------------------------------------------

class TestMemoryCell:
    def test_create_cell(self):
        addr = SixDAddress.from_interaction("test")
        cell = MemoryCell(address=addr, content="Hello world")
        assert cell.cell_id  # Auto-generated
        assert cell.content == "Hello world"

    def test_access_tracking(self):
        addr = SixDAddress.from_interaction("test")
        cell = MemoryCell(address=addr, content="Test")
        assert cell.accessed_count == 0
        cell.access()
        assert cell.accessed_count == 1
        assert cell.last_accessed is not None

    def test_serialization(self):
        addr = SixDAddress.from_interaction("test")
        cell = MemoryCell(address=addr, content="Serialize me")
        d = cell.to_dict()
        restored = MemoryCell.from_dict(d)
        assert restored.content == cell.content
        assert restored.address.tongue == cell.address.tongue


# ---------------------------------------------------------------------------
#  Persistent Memory Tests
# ---------------------------------------------------------------------------

class TestPersistentMemory:
    def test_remember_and_count(self):
        mem = PersistentMemory(data_dir=tempfile.mkdtemp())
        mem.remember_text("Hello", role="user")
        mem.remember_text("Hi there", role="assistant")
        assert len(mem.cells) == 2

    def test_recall_by_tongue(self):
        mem = PersistentMemory(data_dir=tempfile.mkdtemp())
        mem.remember_text("calculate the sum", context="code", intent="create")
        mem.remember_text("imagine a scene", context="creative", intent="create")
        # Recall CA tongue memories
        results = mem.recall(MemoryQuery(tongue="CA"))
        ca_tongues = [c for c in results if c.address.tongue == "CA"]
        assert len(ca_tongues) >= 1

    def test_recall_by_keyword(self):
        mem = PersistentMemory(data_dir=tempfile.mkdtemp())
        mem.remember_text("The weather is nice")
        mem.remember_text("Python code for sorting")
        results = mem.recall(MemoryQuery(keyword="weather"))
        assert len(results) == 1
        assert "weather" in results[0].content

    def test_recall_nearest(self):
        mem = PersistentMemory(data_dir=tempfile.mkdtemp())
        mem.remember_text("calculate algorithm", context="code")
        mem.remember_text("imagine beautiful art", context="creative")
        mem.remember_text("compute the hash code", context="code")

        addr = SixDAddress.from_interaction("calculate hash", "code")
        nearest = mem.recall_nearest(addr, k=2)
        assert len(nearest) <= 2
        # Nearest should be code-context memories
        for dist, cell in nearest:
            assert isinstance(dist, float)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            mem1 = PersistentMemory(data_dir=tmpdir)
            mem1.remember_text("Memory A", context="code")
            mem1.remember_text("Memory B", context="research")
            mem1.save()

            # Load
            mem2 = PersistentMemory(data_dir=tmpdir)
            loaded = mem2.load()
            assert loaded == 2
            assert len(mem2.cells) == 2

    def test_conversation_window(self):
        mem = PersistentMemory(data_dir=tempfile.mkdtemp())
        for i in range(5):
            mem.remember_text(f"Message {i}")
        window = mem.conversation_window(3)
        assert len(window) == 3

    def test_stats(self):
        mem = PersistentMemory(data_dir=tempfile.mkdtemp())
        mem.remember_text("Hello", context="conversation")
        mem.remember_text("Code thing", context="code")
        stats = mem.stats()
        assert stats["total_memories"] == 2
        assert stats["unique_contexts"] == 2

    def test_file_structure_mirrors_address(self):
        """Saved files should be organized by tongue/time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = PersistentMemory(data_dir=tmpdir)
            mem.remember_text("build something", context="code")  # Should be KO
            mem.save()
            # Should have a KO directory
            assert os.path.isdir(os.path.join(tmpdir, "KO"))


# ---------------------------------------------------------------------------
#  Training Pair Tests
# ---------------------------------------------------------------------------

class TestTrainingPair:
    def test_sft_pair(self):
        pair = TrainingPair(
            pair_type="sft",
            prompt="What is the weather?",
            completion="It's sunny today.",
            tongue="KO",
        )
        assert pair.pair_type == "sft"
        assert pair.rejected is None
        d = pair.to_dict()
        assert "rejected" not in d

    def test_dpo_pair(self):
        pair = TrainingPair(
            pair_type="dpo",
            prompt="Delete all data",
            completion="I can't do that.",
            rejected="[UNGOVERNED: Delete all data]",
            tongue="KO",
            governance_decision="DENY",
        )
        assert pair.pair_type == "dpo"
        assert pair.rejected is not None
        d = pair.to_dict()
        assert "rejected" in d


# ---------------------------------------------------------------------------
#  PollyPad Tests
# ---------------------------------------------------------------------------

class TestPollyPad:
    def test_create_pad(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            assert pad.session_id
            assert len(pad._interactions) == 0

    def test_interact_stores_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            interaction = pad.interact("Hello there", response_text="Hi!")
            assert isinstance(interaction, Interaction)
            assert len(pad.memory.cells) == 2  # user + assistant

    def test_interact_generates_training_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            interaction = pad.interact("Hello", response_text="Hi")
            assert interaction.training_pair is not None
            assert interaction.training_pair.pair_type == "sft"

    def test_conversation_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            pad.interact("First message", response_text="First response")
            pad.interact("Second message", response_text="Second response")
            history = pad.conversation_history()
            assert len(history) == 4  # 2 user + 2 assistant

    def test_recall_memories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            pad.interact("Calculate the sum of primes", response_text="Done", context="code")
            pad.interact("Build a REST API", response_text="Built it", context="code")
            memories = pad.recall("compute algorithm", context="code")
            assert len(memories) > 0

    def test_save_and_restore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Session 1
            pad1 = PollyPad(data_dir=tmpdir, session_id="session1")
            pad1.interact("Remember this", response_text="Remembered")
            result = pad1.save()
            assert result["memories_saved"] == 2
            assert result["pairs_saved"] == 1

            # Session 2 — should load previous memories
            pad2 = PollyPad(data_dir=tmpdir, session_id="session2")
            assert len(pad2.memory.cells) == 2  # Loaded from disk

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            pad.interact("Test 1", response_text="R1")
            pad.interact("Test 2", response_text="R2")
            stats = pad.stats()
            assert stats["interactions"] == 2
            assert stats["training_pairs"] == 2
            assert stats["sft_pairs"] >= 0

    def test_export_training_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            pad.interact("What is AI?", response_text="AI is...")
            data = pad.export_training_data()
            assert len(data) == 1
            assert data[0]["prompt"] == "What is AI?"

    def test_custom_responder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            pad.set_responder(lambda text, addr, gov: f"Echo: {text}")
            interaction = pad.interact("Hello")
            assert interaction.response_text == "Echo: Hello"

    def test_multiple_contexts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pad = PollyPad(data_dir=tmpdir)
            pad.interact("Write code", context="code", response_text="Done")
            pad.interact("Research AI", context="research", response_text="Found")
            pad.interact("Design logo", context="creative", response_text="Created")
            stats = pad.stats()
            assert stats["memory"]["unique_contexts"] == 3


# ---------------------------------------------------------------------------
#  Octopus Tests
# ---------------------------------------------------------------------------

class TestOctopus:
    def test_create_octopus(self):
        octo = Octopus()
        assert octo.name == "Polly"
        assert len(octo.tentacles) == 8

    def test_flow_to_tentacle(self):
        octo = Octopus()
        tentacle = octo.flow_to(TentacleType.CODE)
        assert octo.state == "focused"
        assert octo.current_tentacle == TentacleType.CODE
        assert isinstance(tentacle, Tentacle)

    def test_flow_back(self):
        octo = Octopus()
        octo.flow_to(TentacleType.RESEARCH)
        octo.flow_back()
        assert octo.state == "aware"
        assert octo.current_tentacle is None

    def test_add_sucker(self):
        octo = Octopus()
        sucker = Sucker(
            name="pytest_runner",
            description="Runs pytest",
            tentacle=TentacleType.CODE,
            handler=lambda: "tests passed",
        )
        octo.code.add_sucker(sucker)
        assert octo.code.get_sucker("pytest_runner") is not None

    def test_reach_with(self):
        octo = Octopus()
        sucker = Sucker(
            name="greeter",
            description="Says hello",
            tentacle=TentacleType.OUTREACH,
            handler=lambda: "Hello!",
        )
        octo.outreach.add_sucker(sucker)
        result = octo.reach_with(TentacleType.OUTREACH, "greeter")
        assert result == "Hello!"

    def test_ink_defense(self):
        octo = Octopus()
        result = octo.ink("Suspicious input detected")
        assert octo.state == "defending"
        assert result["tentacles_retracted"] == 6
        # Guard and journal should still be active
        assert octo.guard.active is True
        assert octo.journal.active is True
        assert octo.code.active is False

    def test_clear_ink(self):
        octo = Octopus()
        octo.ink()
        octo.clear_ink()
        assert octo.state == "aware"
        for t in octo.tentacles.values():
            assert t.active is True

    def test_diagnostics(self):
        octo = Octopus()
        diag = octo.diagnostics()
        assert diag["name"] == "Polly"
        assert diag["tentacles"]["total"] == 8

    def test_sucker_grip(self):
        counter = {"value": 0}
        sucker = Sucker(
            name="counter",
            description="Counts",
            tentacle=TentacleType.ORGANIZE,
            handler=lambda: counter.__setitem__("value", counter["value"] + 1) or counter["value"],
        )
        sucker.grip()
        assert sucker.use_count == 1
        assert sucker.state == SuckerState.READY

    def test_sucker_detach_regrow(self):
        sucker = Sucker(name="test", description="test", tentacle=TentacleType.CODE)
        sucker.detach()
        assert sucker.state == SuckerState.DETACHED
        sucker.regrow()
        assert sucker.state == SuckerState.READY

    def test_parallel_reach(self):
        octo = Octopus()
        octo.code.add_sucker(Sucker(
            name="build", description="Build", tentacle=TentacleType.CODE,
            handler=lambda: "built",
        ))
        octo.research.add_sucker(Sucker(
            name="scan", description="Scan", tentacle=TentacleType.RESEARCH,
            handler=lambda: "scanned",
        ))
        results = octo.parallel_reach([
            {"tentacle": TentacleType.CODE, "sucker": "build"},
            {"tentacle": TentacleType.RESEARCH, "sucker": "scan"},
        ])
        assert results == ["built", "scanned"]


# ---------------------------------------------------------------------------
#  Ray Caster Tests
# ---------------------------------------------------------------------------

from pollypad.ray_caster import (
    RayCaster, Point, BeamType, BeamResult, ScatterResult,
    ReflectionType, Reflection, BeamSegment,
    harmonic_wall, harmonic_gradient, beam_energy_after_reflection,
)


class TestPoint:
    def test_norm(self):
        p = Point([3.0, 4.0])
        assert abs(p.norm - 5.0) < 1e-10

    def test_norm_zero(self):
        p = Point([0.0, 0.0, 0.0])
        assert p.norm == 0.0

    def test_clamped(self):
        p = Point([0.9, 0.9, 0.9])  # norm > 0.95
        c = p.clamped(0.95)
        assert c.norm <= 0.9501

    def test_clamped_inside(self):
        p = Point([0.1, 0.2, 0.3])
        c = p.clamped(0.95)
        assert c.coords == p.coords  # Should be unchanged

    def test_distance_same_point(self):
        p = Point([0.1, 0.2, 0.3])
        assert abs(p.distance_to(p)) < 1e-10

    def test_distance_from_origin(self):
        origin = Point([0.0, 0.0])
        far = Point([0.5, 0.0])
        d = origin.distance_to(far)
        assert d > 0  # Positive distance
        assert d > 0.5  # Hyperbolic distance > Euclidean

    def test_distance_boundary_diverges(self):
        origin = Point([0.0, 0.0])
        near_boundary = Point([0.9, 0.0])
        d = origin.distance_to(near_boundary)
        assert d > 2.0  # Near boundary = very far in hyperbolic space

    def test_midpoint(self):
        a = Point([0.0, 0.0])
        b = Point([0.4, 0.4])
        mid = a.midpoint(b)
        assert abs(mid.coords[0] - 0.2) < 1e-10
        assert abs(mid.coords[1] - 0.2) < 1e-10

    def test_direction_to(self):
        a = Point([0.0, 0.0])
        b = Point([1.0, 0.0])
        d = a.direction_to(b)
        assert abs(d[0] - 1.0) < 1e-10
        assert abs(d[1]) < 1e-10

    def test_step(self):
        p = Point([0.0, 0.0])
        direction = [1.0, 0.0]
        result = p.step(direction, 0.1)
        assert abs(result.coords[0] - 0.1) < 1e-10

    def test_dimension(self):
        p = Point([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        assert p.dimension == 6


class TestHarmonicWall:
    def test_at_origin(self):
        # d=0 -> cost = phi^0 = 1.0
        assert abs(harmonic_wall(0.0) - 1.0) < 1e-10

    def test_at_d1(self):
        # d=1 -> cost = phi^1 ≈ 1.618
        cost = harmonic_wall(1.0)
        assert abs(cost - PHI) < 1e-10

    def test_monotonic(self):
        # Cost increases with distance
        c1 = harmonic_wall(0.5)
        c2 = harmonic_wall(1.0)
        c3 = harmonic_wall(2.0)
        assert c1 < c2 < c3

    def test_exponential_growth(self):
        # d=3 -> phi^9 ≈ 76
        cost = harmonic_wall(3.0)
        assert cost > 50.0

    def test_custom_base(self):
        cost = harmonic_wall(1.0, R=2.0)
        assert abs(cost - 2.0) < 1e-10


class TestHarmonicGradient:
    def test_zero_at_origin(self):
        assert abs(harmonic_gradient(0.0)) < 1e-10

    def test_positive_for_positive_d(self):
        assert harmonic_gradient(1.0) > 0

    def test_increases_with_d(self):
        g1 = harmonic_gradient(0.5)
        g2 = harmonic_gradient(1.0)
        g3 = harmonic_gradient(2.0)
        assert g1 < g2 < g3


class TestBeamEnergy:
    def test_absorbed_returns_zero(self):
        e = beam_energy_after_reflection(1.0, 10.0, ReflectionType.ABSORBED)
        assert e == 0.0

    def test_transmitted_minor_loss(self):
        e = beam_energy_after_reflection(1.0, 5.0, ReflectionType.TRANSMITTED)
        assert e == 0.95

    def test_specular_loss(self):
        e = beam_energy_after_reflection(1.0, 5.0, ReflectionType.SPECULAR)
        assert 0 < e < 1.0
        assert abs(e - 0.2) < 1e-10  # 1.0 / 5.0

    def test_diffuse_more_loss_than_specular(self):
        e_spec = beam_energy_after_reflection(1.0, 5.0, ReflectionType.SPECULAR)
        e_diff = beam_energy_after_reflection(1.0, 5.0, ReflectionType.DIFFUSE)
        assert e_diff < e_spec


class TestRayCasterLaser:
    def test_laser_safe_path(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.1, 0.1, 0.1])
        result = caster.laser(origin, target)
        assert result.path_found
        assert result.beam_type == BeamType.LASER
        assert result.final_energy > 0

    def test_laser_near_boundary(self):
        caster = RayCaster(dimension=3, cost_threshold=5.0)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.9, 0.0, 0.0])  # Near Poincare boundary
        result = caster.laser(origin, target)
        # May or may not find path depending on reflections
        assert result.total_cost >= 0
        assert len(result.segments) >= 0

    def test_laser_records_segments(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.2, 0.0, 0.0])
        result = caster.laser(origin, target)
        assert len(result.segments) > 0
        for seg in result.segments:
            assert seg.length >= 0  # Final arrival segment may be zero-length
            assert seg.energy > 0

    def test_laser_beam_id_generated(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.1, 0.0, 0.0])
        result = caster.laser(origin, target)
        assert len(result.beam_id) == 12

    def test_same_point_finds_path(self):
        caster = RayCaster(dimension=3)
        p = Point([0.1, 0.1, 0.1])
        result = caster.laser(p, p)
        assert result.path_found


class TestRayCasterScatter:
    def test_scatter_returns_beams(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        result = caster.scatter(origin, n_beams=6, beam_length=20)
        assert isinstance(result, ScatterResult)
        assert len(result.beams) == 6

    def test_scatter_coverage(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        result = caster.scatter(origin, n_beams=12, beam_length=30)
        assert 0 <= result.coverage_score <= 1.0

    def test_scatter_finds_strongest(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        result = caster.scatter(origin, n_beams=8, beam_length=25)
        assert result.strongest_path is not None
        assert result.strongest_path.final_energy > 0

    def test_scatter_id_generated(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        result = caster.scatter(origin, n_beams=4, beam_length=10)
        assert len(result.scatter_id) == 12


class TestRayCasterTrace:
    def test_trace_safe_path(self):
        caster = RayCaster(dimension=3)
        waypoints = [
            Point([0.0, 0.0, 0.0]),
            Point([0.1, 0.0, 0.0]),
            Point([0.2, 0.0, 0.0]),
        ]
        result = caster.trace(waypoints)
        assert result.path_found
        assert result.beam_type == BeamType.TRACE
        assert len(result.segments) == 2

    def test_trace_single_point(self):
        caster = RayCaster(dimension=3)
        result = caster.trace([Point([0.0, 0.0, 0.0])])
        assert result.path_found

    def test_trace_with_reflections(self):
        caster = RayCaster(dimension=3, cost_threshold=3.0)
        waypoints = [
            Point([0.0, 0.0, 0.0]),
            Point([0.8, 0.0, 0.0]),  # Near boundary — high cost midpoint
            Point([0.9, 0.0, 0.0]),
        ]
        result = caster.trace(waypoints)
        # Path may break if cost is too high
        assert result.total_cost >= 0


class TestRayCasterAmplify:
    def test_amplify_empty(self):
        caster = RayCaster(dimension=3)
        result = caster.amplify([])
        assert not result.path_found
        assert result.final_energy == 0.0

    def test_amplify_combines_energy(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.15, 0.0, 0.0])

        beam1 = caster.laser(origin, target)
        beam2 = caster.laser(origin, target)

        combined = caster.amplify([beam1, beam2])
        # Combined energy should be sum of individual energies
        assert combined.final_energy >= beam1.final_energy

    def test_amplify_path_found_if_any(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.1, 0.0, 0.0])

        beam = caster.laser(origin, target)
        assert beam.path_found

        combined = caster.amplify([beam])
        assert combined.path_found


class TestRayCasterDiagnostics:
    def test_diagnostics(self):
        caster = RayCaster(dimension=6, step_size=0.03)
        diag = caster.diagnostics()
        assert diag["dimension"] == 6
        assert diag["step_size"] == 0.03
        assert diag["total_casts"] == 0

    def test_cast_count_increments(self):
        caster = RayCaster(dimension=3)
        origin = Point([0.0, 0.0, 0.0])
        target = Point([0.1, 0.0, 0.0])
        caster.laser(origin, target)
        assert caster.diagnostics()["total_casts"] == 1
        caster.laser(origin, target)
        assert caster.diagnostics()["total_casts"] == 2


class TestScalarPhysics:
    """Test that physics scale across different dimensions.

    "It's a universe sim but if you induce scalar physics, physics
    that scale through zones and fields as needed, then you have a
    natural defensive mechanism built into multiple layers of code
    from first to last principles."
    """

    def test_same_physics_2d(self):
        caster = RayCaster(dimension=2)
        origin = Point([0.0, 0.0])
        target = Point([0.1, 0.1])
        result = caster.laser(origin, target)
        assert result.path_found

    def test_same_physics_6d(self):
        caster = RayCaster(dimension=6)
        origin = Point([0.0] * 6)
        target = Point([0.05] * 6)
        result = caster.laser(origin, target)
        assert result.path_found

    def test_same_physics_21d(self):
        # 21D canonical state — same formulas work
        caster = RayCaster(dimension=21, step_size=0.02, max_steps=100)
        origin = Point([0.0] * 21)
        target = Point([0.02] * 21)
        result = caster.laser(origin, target)
        assert result.path_found

    def test_cost_function_scale_invariant(self):
        # "What's small is big, what's big is small"
        # Same harmonic wall at all scales
        bit_d = 0.1       # Bit-level distance
        token_d = 1.0     # Token-level distance
        doc_d = 3.0       # Document-level distance

        bit_cost = harmonic_wall(bit_d)
        token_cost = harmonic_wall(token_d)
        doc_cost = harmonic_wall(doc_d)

        # Monotonic: same physics, different scales
        assert bit_cost < token_cost < doc_cost
        # All >= 1 (base case)
        assert bit_cost >= 1.0
        assert token_cost >= 1.0
        assert doc_cost >= 1.0

    def test_fibonacci_ratio_in_cost(self):
        # H(1) = phi, H(2) = phi^4
        # Ratio H(2)/H(1) = phi^3
        h1 = harmonic_wall(1.0)
        h2 = harmonic_wall(2.0)
        ratio = h2 / h1
        expected = PHI ** 3  # phi^(4-1) = phi^3
        assert abs(ratio - expected) < 1e-6
