from __future__ import annotations

from scripts.research.mobius_magic_operator_probe import (
    dirichlet_convolution,
    mobius,
    run_probe,
    smallest_prime_factor,
    von_mangoldt,
)


def test_mobius_is_dirichlet_inverse_of_one() -> None:
    limit = 60
    mu, _spf = mobius(limit)
    one = [0.0] + [1.0] * limit
    delta = [0.0] * (limit + 1)
    delta[1] = 1.0

    assert dirichlet_convolution(one, [float(value) for value in mu], limit) == delta


def test_von_mangoldt_marks_prime_powers_only() -> None:
    spf = smallest_prime_factor(40)
    values = von_mangoldt(40, spf)

    assert values[2] > 0.0
    assert values[4] == values[2]
    assert values[8] == values[2]
    assert values[9] == values[3]
    assert values[6] == 0.0
    assert values[12] == 0.0


def test_run_probe_recovers_lambda_and_rejects_perturbed_inverse() -> None:
    result = run_probe(limit=120, seed=11)
    metrics = result["metrics"]

    assert metrics["inverse_error"] == 0.0
    assert metrics["lambda_error"] < 1e-12
    assert metrics["forward_log_error"] < 1e-12
    assert metrics["matrix_lambda_error"] < 1e-12
    assert metrics["true_leakage"] < 1e-12
    assert metrics["perturbed_leakage"] > 0.0
    assert metrics["random_leakage"] > metrics["perturbed_leakage"]
    assert metrics["fog_bright_count"] == metrics["fog_hidden_prime_count"]
    assert metrics["fog_bright_precision"] == 1.0
    assert metrics["fog_prime_recall"] == 1.0
    assert metrics["fog_prime_power_lit_count"] >= metrics["fog_hidden_prime_count"]


def test_run_probe_reports_quarantine_boundary() -> None:
    result = run_probe(limit=80, seed=3)

    assert result["decision_record"]["promotion"] == "QUARANTINE_RESEARCH_ONLY"
    assert result["decision_record"]["verdict"] == "MOBIUS_OPERATOR_LOAD_BEARING"
    assert len(result["sample_lambda"]) == 40
