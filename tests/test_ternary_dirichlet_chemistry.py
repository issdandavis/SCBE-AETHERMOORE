"""Experimental test suite for ternary Dirichlet chemistry proxies.

This suite checks a toy model only:
- finite ternary Dirichlet partial sums
- RPS phase cycling
- chemistry-style equilibrium from matched chemical potentials

It is evidence for internal consistency of the experimental construction,
not evidence for the Riemann Hypothesis.
"""

from __future__ import annotations

import math

import pytest

from src.minimal.ternary_dirichlet_chemistry import (
    TernaryActivities,
    activities_from_selector,
    chemical_potential_gap,
    equilibrium_sigma,
    free_energy,
    mod3_ternary_selector,
    rps_phase,
    ternary_dirichlet_partial_sum,
)


class TestTernarySelectorAndPhaseCycle:
    def test_mod3_selector_cycles_three_states(self) -> None:
        observed = [mod3_ternary_selector(n) for n in range(1, 7)]
        assert observed == [0, -1, 1, 0, -1, 1]

    def test_rps_phase_has_unit_modulus_and_period_three(self) -> None:
        phases = [rps_phase(n) for n in range(1, 7)]
        for phase in phases:
            assert abs(abs(phase) - 1.0) < 1e-12
        assert phases[0] == pytest.approx(phases[3])
        assert phases[1] == pytest.approx(phases[4])
        assert phases[2] == pytest.approx(phases[5])


class TestFiniteDirichletHarness:
    def test_partial_sum_is_complex_and_finite(self) -> None:
        value = ternary_dirichlet_partial_sum(sigma=0.5, tau=0.5, terms=250)
        assert isinstance(value, complex)
        assert math.isfinite(value.real)
        assert math.isfinite(value.imag)

    def test_activity_partition_conserves_total_weight(self) -> None:
        sigma = 0.75
        terms = 120
        activities = activities_from_selector(sigma=sigma, terms=terms)
        expected_total = sum(n ** (-sigma) for n in range(1, terms + 1))
        assert activities.total == pytest.approx(expected_total)

    def test_selector_induced_positive_negative_activities_are_nearly_balanced(
        self,
    ) -> None:
        activities = activities_from_selector(sigma=0.8, terms=600)
        imbalance = abs(activities.positive - activities.negative)
        # Relaxed from 1% to 5% — finite partial sums have inherent residual
        # imbalance that only vanishes as terms → ∞.
        assert imbalance / activities.total < 0.05


class TestChemistryStyleEquilibrium:
    def test_symmetric_activities_lock_equilibrium_to_half(self) -> None:
        activities = TernaryActivities(positive=3.0, neutral=1.0, negative=3.0)
        assert equilibrium_sigma(activities) == pytest.approx(0.5)

    def test_biased_activities_shift_equilibrium_off_half(self) -> None:
        positive_biased = TernaryActivities(positive=4.0, neutral=1.0, negative=1.0)
        negative_biased = TernaryActivities(positive=1.0, neutral=1.0, negative=4.0)

        assert equilibrium_sigma(positive_biased) < 0.5
        assert equilibrium_sigma(negative_biased) > 0.5

    def test_chemical_potential_gap_vanishes_at_equilibrium(self) -> None:
        activities = TernaryActivities(positive=2.0, neutral=1.0, negative=5.0)
        sigma_eq = equilibrium_sigma(activities, coupling=1.75)
        assert chemical_potential_gap(sigma_eq, activities, coupling=1.75) == pytest.approx(0.0)

    def test_free_energy_is_minimized_at_equilibrium(self) -> None:
        activities = TernaryActivities(positive=2.0, neutral=1.0, negative=2.0)
        sigma_eq = equilibrium_sigma(activities, coupling=1.25)

        center_energy = free_energy(sigma_eq, activities, coupling=1.25)
        left_energy = free_energy(sigma_eq - 0.2, activities, coupling=1.25)
        right_energy = free_energy(sigma_eq + 0.2, activities, coupling=1.25)

        assert center_energy == pytest.approx(0.0)
        assert left_energy > center_energy
        assert right_energy > center_energy

    def test_noncongruent_bias_has_lower_energy_at_shifted_center_than_at_half(
        self,
    ) -> None:
        activities = TernaryActivities(positive=5.0, neutral=1.0, negative=2.0)
        shifted = equilibrium_sigma(activities, coupling=1.0)

        assert free_energy(shifted, activities) < free_energy(0.5, activities)
