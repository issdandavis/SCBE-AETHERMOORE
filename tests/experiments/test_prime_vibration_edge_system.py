"""Tests for the corrected Prime-Vibration Edge System v3 experiment.

Locks in the two critical corrections from the formula verification report:
l-infinity (not l1) coefficient bound in Delta(S, B), and the separation of
forward encoding (no alpha) from Lane B drift (alpha-scaled).
"""

import math

import pytest

from scripts.experiments.prime_vibration_edge_system import (
    F4,
    F4_GROUP_ORDER,
    certificate_holds,
    common_overtone,
    delta_certificate,
    fermat_number,
    forward_encoding,
    is_primitive_root_mod_f4,
    lane_a_frequency,
    lane_b_drift,
    lane_b_frequency,
    multiplicative_group_order,
    numerical_epsilon,
    prime_valuations,
    recover_coefficients,
    repeat_period,
    run_experiment,
    second_order_products,
    third_order_products,
)

SUPPORT = (2, 3, 5)


class TestLaneA:
    def test_lock_frequency(self):
        assert lane_a_frequency(7, 100.0) == 700.0

    def test_gcd_repeat_period(self):
        assert repeat_period(6, 10, 1.0) == pytest.approx(0.5)

    def test_lcm_common_overtone(self):
        assert common_overtone(6, 10, 2.0) == pytest.approx(60.0)


class TestLaneB:
    def test_prime_valuations(self):
        assert prime_valuations(360) == {2: 3, 3: 2, 5: 1}

    def test_prime_valuations_rejects_small_n(self):
        with pytest.raises(ValueError):
            prime_valuations(1)

    def test_forward_encoding_is_log_n_without_alpha(self):
        assert forward_encoding(360) == pytest.approx(math.log(360), abs=1e-12)

    def test_alpha_conflation_bug(self):
        """The website's hybrid formula asserts log n = alpha*log n — must NOT hold."""
        alpha, n = 0.5, 360
        conflated = alpha * forward_encoding(n)
        assert conflated != pytest.approx(math.log(n), abs=1e-6)
        assert lane_b_drift(n, alpha) == pytest.approx(alpha * math.log(n), abs=1e-12)

    def test_omega_notation_frequency(self):
        assert lane_b_frequency(3, 2.0) == pytest.approx(2.0 * math.log(3))


class TestDeltaCertificate:
    def test_linf_and_l1_are_different_objects(self):
        """Report critical finding #1: the norms give different minima at B=2."""
        linf = delta_certificate(SUPPORT, 2, norm="linf")
        l1 = delta_certificate(SUPPORT, 2, norm="l1")
        assert linf.value < l1.value
        # l1 ball is a subset of the l-inf cube, so the l-inf min can only be <=.
        assert linf.vector != l1.vector

    def test_linf_minimum_is_log_ten_ninths(self):
        """At S={2,3,5}, B=2 the l-inf minimizer is (-1,2,-1): |log(9/10)|."""
        result = delta_certificate(SUPPORT, 2, norm="linf")
        assert result.value == pytest.approx(math.log(10 / 9), abs=1e-12)
        assert result.vector in ((-1, 2, -1), (1, -2, 1))

    def test_certificate_inequality(self):
        assert certificate_holds(SUPPORT, 2, eps_sensor=1e-6)
        assert numerical_epsilon(SUPPORT, 2) < 1e-12

    def test_rejects_bad_inputs(self):
        with pytest.raises(ValueError):
            delta_certificate(SUPPORT, 0)
        with pytest.raises(ValueError):
            delta_certificate(SUPPORT, 2, norm="l2")

    def test_reverse_recovery_roundtrip(self):
        true_vector = (2, -1, 1)
        target = sum(c * math.log(p) for c, p in zip(true_vector, SUPPORT))
        assert recover_coefficients(target, SUPPORT, 2, tol=1e-9) == true_vector

    def test_reverse_recovery_returns_none_when_out_of_reach(self):
        assert recover_coefficients(100.0, SUPPORT, 2, tol=1e-9) is None


class TestCanary:
    def test_second_order_products_even(self):
        assert second_order_products(3, 7) == (10, 4, 6)
        assert all(x % 2 == 0 for x in second_order_products(11, 13))

    def test_third_order_products_odd(self):
        assert third_order_products(3, 7) == (13, -1)
        assert all(x % 2 == 1 for x in third_order_products(11, 13))


class TestFermatLane:
    def test_fermat_numbers(self):
        assert [fermat_number(k) for k in range(5)] == [3, 5, 17, 257, F4]

    def test_group_orders_are_powers_of_two(self):
        for k in range(5):
            assert multiplicative_group_order(k) == 2 ** (2**k)

    def test_group_order_refuses_composite_fermat(self):
        with pytest.raises(ValueError):
            multiplicative_group_order(5)

    def test_three_generates_f4_but_two_does_not(self):
        assert is_primitive_root_mod_f4(3)
        assert not is_primitive_root_mod_f4(2)
        assert pow(2, 32, F4) == 1  # ord(2) = 32

    def test_f4_constants(self):
        assert F4 == 2**16 + 1
        assert F4_GROUP_ORDER == 2**16


def test_full_experiment_passes():
    report = run_experiment()
    failures = [c.name for c in report.checks if not c.passed]
    assert report.passed, f"failing checks: {failures}"
