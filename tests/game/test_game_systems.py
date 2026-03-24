"""
Tests for Spiral Forge RPG — Python reference implementation.

Covers: types, companion, combat, sacred eggs, symbiotic network, regions.
pytest markers: unit, game
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from symphonic_cipher.scbe_aethermoore.game.types import (
    TONGUE_CODES,
    TONGUE_WEIGHTS,
    HODGE_DUAL_PAIRS,
    PHI,
    CanonicalState,
    default_canonical_state,
    state_to_array,
    array_to_state,
    tongue_distance,
    tongue_norm,
    dominant_tongue,
    zero_tongue_vector,
    EVOLUTION_THRESHOLDS,
    OVER_EVOLUTION_THRESHOLD,
)
from symphonic_cipher.scbe_aethermoore.game.companion import (
    Companion,
    create_companion,
    derive_combat_stats,
    apply_tongue_experience,
    apply_combat_result,
    current_evolution_stage,
    is_over_evolved,
)
from symphonic_cipher.scbe_aethermoore.game.combat import (
    compute_type_advantage,
    calculate_damage,
)
from symphonic_cipher.scbe_aethermoore.game.sacred_eggs import (
    check_hatchable_eggs,
    can_hatch_egg,
    egg_starting_tongue,
)
from symphonic_cipher.scbe_aethermoore.game.symbiotic_network import SymbioticNetwork
from symphonic_cipher.scbe_aethermoore.game.regions import (
    REGIONS,
    get_tower_floor,
    get_rank,
    get_region_by_tongue,
)


# ===========================================================================
#  Types & Tongue System
# ===========================================================================


class TestTongueSystem:
    def test_six_tongues_in_order(self):
        assert TONGUE_CODES == ("KO", "AV", "RU", "CA", "UM", "DR")
        assert len(TONGUE_CODES) == 6

    def test_golden_ratio_weights(self):
        assert TONGUE_WEIGHTS["KO"] == 1.0
        assert abs(TONGUE_WEIGHTS["AV"] - PHI) < 1e-6
        assert abs(TONGUE_WEIGHTS["RU"] - PHI**2) < 1e-6
        assert abs(TONGUE_WEIGHTS["DR"] - PHI**5) < 1e-4

    def test_hodge_dual_pairs(self):
        assert HODGE_DUAL_PAIRS == (("KO", "DR"), ("AV", "UM"), ("RU", "CA"))

    def test_tongue_distance_symmetric(self):
        a = (0.5, 0.3, 0.2, 0.1, 0.4, 0.6)
        b = (0.1, 0.7, 0.3, 0.5, 0.2, 0.1)
        assert abs(tongue_distance(a, b) - tongue_distance(b, a)) < 1e-12
        assert tongue_distance(a, a) < 1e-12

    def test_dominant_tongue(self):
        assert dominant_tongue((0.1, 0.2, 0.9, 0.1, 0.1, 0.1)) == "RU"
        assert dominant_tongue((0.1, 0.1, 0.1, 0.1, 0.1, 0.8)) == "DR"


# ===========================================================================
#  21D Canonical State
# ===========================================================================


class TestCanonicalState:
    def test_default_has_21_dims(self):
        state = default_canonical_state()
        arr = state_to_array(state)
        assert len(arr) == 21

    def test_roundtrip(self):
        state = default_canonical_state()
        arr = state_to_array(state)
        restored = array_to_state(arr)
        assert state_to_array(restored) == arr

    def test_rejects_wrong_length(self):
        with pytest.raises(ValueError, match="Expected 21"):
            array_to_state([1, 2, 3])


# ===========================================================================
#  Companion System
# ===========================================================================


class TestCompanionSystem:
    def test_create_companion(self):
        comp = create_companion(
            "test-1",
            "crysling",
            "Crysling",
            "mono_CA",
            "processor",
            (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        )
        assert comp.id == "test-1"
        assert comp.species_id == "crysling"
        assert comp.evolution_stage == "spark"
        assert comp.bond_level == 1
        assert comp.seal_integrity == 100.0

    def test_derived_stats(self):
        comp = create_companion(
            "t",
            "crysling",
            "C",
            "mono_CA",
            "processor",
            (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        )
        stats = comp.derived_stats
        assert 0 <= stats.speed <= 100
        assert 0 <= stats.proof_power <= 100

    def test_tongue_experience(self):
        comp = create_companion(
            "t",
            "crysling",
            "C",
            "mono_CA",
            "processor",
            (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        )
        old_norm = tongue_norm(comp.state.tongue_position)
        apply_tongue_experience(comp, "CA", 0.5)
        new_norm = tongue_norm(comp.state.tongue_position)
        assert new_norm >= old_norm * 0.9
        assert new_norm <= 1.1

    def test_combat_result_win(self):
        comp = create_companion(
            "t",
            "crysling",
            "C",
            "mono_CA",
            "processor",
            (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        )
        old_radius = comp.state.radius
        apply_combat_result(comp, True, 5)
        assert comp.state.radius > old_radius
        # bond_xp may be 0 if level-up consumed it
        assert comp.bond_xp >= 0 or comp.bond_level > 1

    def test_combat_result_loss(self):
        comp = create_companion(
            "t",
            "crysling",
            "C",
            "mono_CA",
            "processor",
            (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        )
        apply_combat_result(comp, False, 5)
        assert comp.scar_count == 1
        assert comp.seal_integrity < 100

    def test_evolution_stages(self):
        assert current_evolution_stage(0.1) == "spark"
        assert current_evolution_stage(0.35) == "form"
        assert current_evolution_stage(0.55) == "prime"
        assert current_evolution_stage(0.75) == "apex"
        assert current_evolution_stage(0.9) == "transcendent"

    def test_over_evolution(self):
        comp = create_companion(
            "t",
            "crysling",
            "C",
            "mono_CA",
            "processor",
            (0.1, 0.1, 0.1, 0.6, 0.1, 0.1),
        )
        assert not is_over_evolved(comp)
        comp.state = CanonicalState(
            tongue_position=comp.state.tongue_position,
            radius=0.96,
        )
        assert is_over_evolved(comp)


# ===========================================================================
#  Combat — Cl(4,0) Bivector
# ===========================================================================


class TestCombatSystem:
    def test_antisymmetry(self):
        a = (0.8, 0.1, 0.1, 0.0, 0.0, 0.0)
        b = (0.0, 0.0, 0.0, 0.0, 0.0, 0.8)
        ab = compute_type_advantage(a, b)
        ba = compute_type_advantage(b, a)
        assert abs(ab + ba) < 1e-8

    def test_same_vector_zero_advantage(self):
        v = (0.5, 0.3, 0.2, 0.1, 0.4, 0.6)
        assert abs(compute_type_advantage(v, v)) < 1e-8

    def test_advantage_bounded(self):
        a = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        b = (0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
        adv = compute_type_advantage(a, b)
        assert -1.0 <= adv <= 1.0

    def test_damage_at_least_one(self):
        assert calculate_damage(10, 0, 50, 50) >= 1
        assert calculate_damage(1, -1, 0, 100) >= 1

    def test_advantage_affects_damage(self):
        positive = calculate_damage(100, 0.5, 50, 50)
        negative = calculate_damage(100, -0.5, 50, 50)
        assert positive > negative


# ===========================================================================
#  Sacred Eggs
# ===========================================================================


class TestSacredEggs:
    def test_high_ko_triggers_ember(self):
        tongue = (0.7, 0.1, 0.1, 0.1, 0.1, 0.1)
        results = check_hatchable_eggs(tongue)
        assert any(r.egg_type == "mono_KO" for r in results)

    def test_balanced_ko_dr_triggers_eclipse(self):
        tongue = (0.45, 0.1, 0.1, 0.1, 0.1, 0.45)
        results = check_hatchable_eggs(tongue)
        assert any(r.egg_type == "hodge_eclipse" for r in results)

    def test_all_high_triggers_prism(self):
        tongue = (0.4, 0.4, 0.4, 0.4, 0.4, 0.4)
        results = check_hatchable_eggs(tongue)
        assert any(r.egg_type == "omni_prism" for r in results)

    def test_low_tongues_hatch_nothing(self):
        tongue = (0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
        assert check_hatchable_eggs(tongue) == []

    def test_starting_tongues_are_valid(self):
        for egg_type in [
            "mono_KO",
            "mono_AV",
            "mono_RU",
            "mono_CA",
            "mono_UM",
            "mono_DR",
            "hodge_eclipse",
            "hodge_storm",
            "hodge_paradox",
            "omni_prism",
        ]:
            start = egg_starting_tongue(egg_type)  # type: ignore[arg-type]
            assert len(start) == 6
            assert all(0 <= v <= 1 for v in start)


# ===========================================================================
#  Symbiotic Network
# ===========================================================================


class TestSymbioticNetwork:
    def test_algebraic_connectivity(self):
        net = SymbioticNetwork()
        net.add_companion("a", (0.6, 0.1, 0.1, 0.1, 0.1, 0.1))
        net.add_companion("b", (0.1, 0.1, 0.1, 0.1, 0.1, 0.6))
        net.add_bond("a", "b", 5)
        assert net.get_algebraic_connectivity() > 0

    def test_network_bonuses(self):
        net = SymbioticNetwork()
        net.add_companion("a", (0.6, 0.1, 0.1, 0.1, 0.1, 0.1))
        net.add_companion("b", (0.1, 0.1, 0.1, 0.6, 0.1, 0.1))
        net.add_companion("c", (0.1, 0.1, 0.1, 0.1, 0.1, 0.6))
        net.add_bond("a", "b", 3)
        net.add_bond("b", "c", 2)
        net.add_bond("a", "c", 1)
        bonuses = net.compute_network_bonuses()
        assert bonuses.xp_multiplier > 1
        assert bonuses.diversity_bonus == 3 / 6
        assert abs(bonuses.density - 1.0) < 0.01

    def test_artifact_governance(self):
        net = SymbioticNetwork()
        net.add_companion("a", (0.5, 0.5, 0.5, 0.5, 0.5, 0.5))
        assert net.submit_artifact((0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) == "approved"
        assert net.submit_artifact((5.0, 5.0, 5.0, 5.0, 5.0, 5.0)) == "quarantined"


# ===========================================================================
#  Regions & Tower
# ===========================================================================


class TestRegions:
    def test_six_regions(self):
        assert len(REGIONS) == 6
        for code in TONGUE_CODES:
            assert get_region_by_tongue(code) is not None

    def test_tower_floors_1_to_100(self):
        for f in range(1, 101):
            floor = get_tower_floor(f)
            assert floor.floor == f
            assert floor.encounters == 5
            assert floor.rank
            assert floor.math_domain

    def test_invalid_floors(self):
        with pytest.raises(ValueError):
            get_tower_floor(0)
        with pytest.raises(ValueError):
            get_tower_floor(101)

    def test_rank_progression(self):
        assert get_rank(1) == "F"
        assert get_rank(50) == "B"
        assert get_rank(100) == "Millennium"

    def test_boss_every_10th(self):
        for f in range(1, 101):
            assert get_tower_floor(f).boss == (f % 10 == 0)
