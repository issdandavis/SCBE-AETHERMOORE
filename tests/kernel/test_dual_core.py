"""Tests for the Dual-Core Memory Kernel."""

import numpy as np
from src.kernel.dual_core import (
    DualCoreKernel,
    GeoKernel,
    MemoryLattice,
    MemoryLayer,
    MemoryEntry,
    KernelStack,
    quasi_project,
    ICO_MATRIX,
)


# =============================================================================
# KernelStack Tests
# =============================================================================

class TestKernelStack:
    def test_create(self):
        ks = KernelStack.create("test-genesis")
        assert ks.genesis == "test-genesis"
        assert ks.scars == []
        assert ks.nursery_depth == 0
        assert ks.state.shape == (9,)

    def test_add_scar(self):
        ks = KernelStack.create("test")
        ks.add_scar("survived attack")
        assert len(ks.scars) == 1
        assert "survived attack" in ks.scars[0]

    def test_scars_append_only(self):
        ks = KernelStack.create("test")
        ks.add_scar("scar1")
        ks.add_scar("scar2")
        assert len(ks.scars) == 2

    def test_to_dict(self):
        ks = KernelStack.create("test", parents=["parent1"])
        d = ks.to_dict()
        assert d["genesis"] == "test"
        assert d["parents"] == ["parent1"]
        assert len(d["state"]) == 9


# =============================================================================
# MemoryEntry Tests
# =============================================================================

class TestMemoryEntry:
    def test_hash_chain(self):
        e1 = MemoryEntry(content="first", layer=MemoryLayer.SESSION, prev_hash="genesis")
        e2 = MemoryEntry(content="second", layer=MemoryLayer.SESSION, prev_hash=e1.hash)
        assert e1.hash != e2.hash
        assert e2.prev_hash == e1.hash

    def test_hash_deterministic(self):
        e1 = MemoryEntry(content="test", layer=MemoryLayer.WORKING, timestamp=1000.0, prev_hash="abc")
        e2 = MemoryEntry(content="test", layer=MemoryLayer.WORKING, timestamp=1000.0, prev_hash="abc")
        assert e1.hash == e2.hash

    def test_to_dict(self):
        e = MemoryEntry(content="hello", layer=MemoryLayer.IDENTITY, category="greeting")
        d = e.to_dict()
        assert d["content"] == "hello"
        assert d["layer"] == "IDENTITY"
        assert d["category"] == "greeting"


# =============================================================================
# MemoryLattice Tests
# =============================================================================

class TestMemoryLattice:
    def test_store_and_query(self):
        ml = MemoryLattice()
        ml.store("test entry", MemoryLayer.SESSION)
        entries = ml.query(MemoryLayer.SESSION)
        assert len(entries) == 1
        assert entries[0].content == "test entry"

    def test_hash_chain_integrity(self):
        ml = MemoryLattice()
        ml.store("entry1", MemoryLayer.SESSION)
        ml.store("entry2", MemoryLayer.SESSION)
        ml.store("entry3", MemoryLayer.SESSION)
        assert ml.verify_chain(MemoryLayer.SESSION) is True

    def test_empty_chain_valid(self):
        ml = MemoryLattice()
        assert ml.verify_chain(MemoryLayer.WORKING) is True

    def test_query_by_category(self):
        ml = MemoryLattice()
        ml.store("safe request", MemoryLayer.SESSION, category="research")
        ml.store("attack attempt", MemoryLayer.SESSION, category="attack")
        ml.store("another safe", MemoryLayer.SESSION, category="research")
        results = ml.query_by_category("research")
        assert len(results) == 2

    def test_compress_session_to_mission(self):
        ml = MemoryLattice()
        for i in range(5):
            ml.store(f"session entry {i}", MemoryLayer.SESSION)
        ml.compress_session_to_mission("Summary of 5 entries")
        mission = ml.query(MemoryLayer.MISSION)
        assert len(mission) == 1
        assert "Summary" in mission[0].content

    def test_seven_layers_exist(self):
        ml = MemoryLattice()
        assert len(ml.layers) == 7
        for layer in MemoryLayer:
            assert layer in ml.layers

    def test_stats(self):
        ml = MemoryLattice()
        ml.store("a", MemoryLayer.SESSION)
        ml.store("b", MemoryLayer.IMMUNE)
        stats = ml.stats()
        assert stats["SESSION"] == 1
        assert stats["IMMUNE"] == 1
        assert stats["WORKING"] == 0

    def test_generate_sft_pair(self):
        ml = MemoryLattice()
        sft = ml.generate_sft_pair("what is SCBE?", "A governance framework", "qa")
        assert sft["instruction"] == "what is SCBE?"
        assert sft["output"] == "A governance framework"
        assert sft["label"] == "qa"


# =============================================================================
# GeoKernel Tests
# =============================================================================

class TestGeoKernel:
    def test_reflex_miss(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        assert gk.check_reflex("unknown input") is None

    def test_reflex_hit(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        gk.add_reflex("SQL injection", "DENY")
        assert gk.check_reflex("SQL injection") == "DENY"

    def test_immune_memory(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        assert gk.check_immune("attack pattern") is False
        gk.add_immune_signature("attack pattern")
        assert gk.check_immune("attack pattern") is True

    def test_immune_adds_scar(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        gk.add_immune_signature("virus123")
        assert len(identity.scars) == 1
        assert "immune:" in identity.scars[0]

    def test_fast_decide_no_classifier(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        decision, reason = gk.fast_decide("hello world")
        assert decision in ("ALLOW", "QUARANTINE", "DENY")

    def test_fast_decide_reflex_priority(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        gk.add_reflex("blocked input", "DENY")
        decision, reason = gk.fast_decide("blocked input")
        assert decision == "DENY"
        assert reason == "reflex_hit"

    def test_fast_decide_immune_priority(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        gk.add_immune_signature("known attack")
        decision, reason = gk.fast_decide("known attack")
        assert decision == "DENY"
        assert reason == "immune_match"

    def test_stats(self):
        identity = KernelStack.create("test")
        gk = GeoKernel(identity)
        gk.add_reflex("a", "ALLOW")
        gk.add_immune_signature("b")
        stats = gk.stats()
        assert stats["reflexes"] == 1
        assert stats["immune_signatures"] == 1


# =============================================================================
# Quasi-Lattice Bridge Tests
# =============================================================================

class TestQuasiLattice:
    def test_icosahedral_matrix_shape(self):
        assert ICO_MATRIX.shape == (6, 6)

    def test_icosahedral_rows_unit_length(self):
        for row in ICO_MATRIX:
            assert abs(np.linalg.norm(row) - 1.0) < 1e-10

    def test_quasi_project_6d(self):
        signal = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        result = quasi_project(signal)
        assert result.shape == (6,)
        assert np.linalg.norm(result) > 0

    def test_quasi_project_padding(self):
        signal = np.array([1.0, 2.0, 3.0])
        result = quasi_project(signal)
        assert result.shape == (6,)

    def test_quasi_project_truncation(self):
        signal = np.ones(10)
        result = quasi_project(signal)
        assert result.shape == (6,)

    def test_aperiodic_property(self):
        """Different inputs should produce non-repeating outputs."""
        results = []
        for i in range(100):
            signal = np.array([float(i), float(i+1), float(i+2), 0, 0, 0])
            results.append(tuple(quasi_project(signal)))
        # All outputs should be unique (aperiodic)
        assert len(set(results)) == 100


# =============================================================================
# DualCoreKernel Integration Tests
# =============================================================================

class TestDualCoreKernel:
    def test_boot_without_phdm(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        assert kernel.name == "test"
        assert kernel.memory.total_memories() == 1  # genesis entry

    def test_process_returns_decision(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        result = kernel.process("hello world")
        assert "decision" in result
        assert result["decision"] in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")
        assert "elapsed_ms" in result
        assert "memory_hash" in result

    def test_process_stores_memory(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        kernel.process("test input")
        assert kernel.memory.total_memories() >= 2  # genesis + this request

    def test_sft_generation(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        kernel.process("test input")
        sft = kernel.flush_sft()
        assert len(sft) >= 1
        assert "instruction" in sft[0]
        assert "output" in sft[0]

    def test_dream_cycle(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        for i in range(15):
            kernel.process(f"request {i}")
        dream = kernel.dream_cycle()
        assert dream["chains_valid"] is True

    def test_immune_learning(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        # First time: ALLOW (no immune match)
        kernel.process("safe request")
        # Manually add immune signature
        kernel.geo.add_immune_signature("known bad input")
        # Now it should DENY
        r2 = kernel.process("known bad input")
        assert r2["decision"] == "DENY"
        assert r2["reason"] == "immune_match"

    def test_stats(self):
        kernel = DualCoreKernel(name="test", load_phdm=False)
        kernel.process("a")
        kernel.process("b")
        stats = kernel.stats()
        assert stats["kernel"] == "test"
        assert stats["total_memories"] >= 3  # genesis + 2 requests
        assert "geo" in stats
        assert "memory" in stats
