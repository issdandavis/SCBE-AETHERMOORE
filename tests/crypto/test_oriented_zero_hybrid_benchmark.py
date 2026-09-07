from __future__ import annotations

from fractions import Fraction
import hashlib
import json

import pytest

from scripts.benchmark import oriented_zero_hybrid_benchmark as B
from src.crypto import oriented_zero_hybrid as H
from src.crypto import toy_lwe_box_field as BOX


def test_paired_effect_uses_exact_two_sd_gate() -> None:
    strong = B._paired_effect([1, 1, 1, 1], [9, 10, 11, 12])
    tie = B._paired_effect([4, 4, 4], [4, 4, 4])
    assert strong["improvement_exceeds_two_population_sd"] is True
    assert strong["mean_control_minus_preferred"] == {"numerator": 38, "denominator": 4}
    assert tie["effect_exceeds_two_population_sd"] is False


def test_boundary_panel_suppresses_repeated_threshold_events() -> None:
    graph = B._control_graph(episodes=5)
    trace = B._boundary_trace(7, episodes=5, jitter_steps=12)
    start = H.HybridState("root", Fraction(1), side=1)
    result = H.run_trace(graph, start, trace)
    jumps = sum(receipt.outcome == "JUMP" for receipt in result.receipts)
    assert jumps == 5
    assert B._naive_boundary_events(graph, trace) > jumps
    assert H.replay_matches(graph, start, trace, result.receipts)


def test_graph_compilation_matches_direct_schedule_exactly() -> None:
    for seed in range(8):
        instance = BOX.generate_toy_lwe(seed, dimension=3, samples=6, secret_radius=2)
        graph_result = B._multiscale_search(instance, through_graph=True)
        direct_result = B._multiscale_search(instance, through_graph=False)
        assert graph_result.candidate == direct_result.candidate
        assert graph_result.score == direct_result.score
        assert graph_result.objective_evaluations == direct_result.objective_evaluations
        assert graph_result.route == direct_result.route
        assert graph_result.receipt_head_sha256 is not None
        assert direct_result.receipt_head_sha256 is None


def test_random_control_has_same_objective_budget() -> None:
    instance = BOX.generate_toy_lwe(19, dimension=4, samples=8, secret_radius=2)
    preferred = B._multiscale_search(instance, through_graph=True)
    control = B._random_search(instance, budget=preferred.objective_evaluations, seed=99)
    assert control.objective_evaluations == preferred.objective_evaluations


def test_finite_model_check_exhausts_all_traces() -> None:
    result = B._finite_model_check(depth=4)
    assert result == {"depth": 4, "alphabet": 5, "traces": 625, "steps": 2500, "invariant_failures": 0}


def test_full_benchmark_writes_hash_verified_evidence(tmp_path) -> None:
    output = tmp_path / "result.json"
    report = B.run(
        seed_start=100,
        seeds=5,
        dimension=3,
        samples=6,
        secret_radius=2,
        chatter_episodes=4,
        jitter_steps=4,
        finite_depth=3,
        output=output,
    )
    assert report["status"] == "ORIENTED_ZERO_CONTROL_VALIDATED_NO_INDEPENDENT_SEARCH_GAIN"
    assert report["finite_model_check"]["invariant_failures"] == 0
    assert report["toy_search"]["graph_direct_exact_parity"] is True
    assert report["toy_search"]["graph_vs_direct"]["ties"] == 5
    receipt_path = tmp_path / "result_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["report"]["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert receipt["plot"] is None
    for source in receipt["sources"].values():
        assert hashlib.sha256(B.Path(source["path"]).read_bytes()).hexdigest() == source["sha256"]


@pytest.mark.parametrize(
    "change",
    [
        {"seeds": 2},
        {"seed_start": -1},
        {"dimension": 0},
        {"samples": 0},
        {"secret_radius": 0},
        {"chatter_episodes": 0},
        {"jitter_steps": 0},
        {"finite_depth": 0},
        {"finite_depth": 8},
    ],
)
def test_invalid_benchmark_panels_are_refused(tmp_path, change: dict[str, int]) -> None:
    arguments = {
        "seed_start": 0,
        "seeds": 3,
        "dimension": 2,
        "samples": 4,
        "secret_radius": 1,
        "chatter_episodes": 2,
        "jitter_steps": 2,
        "finite_depth": 2,
        "output": tmp_path / "unused.json",
    }
    arguments.update(change)
    with pytest.raises(ValueError):
        B.run(**arguments)
