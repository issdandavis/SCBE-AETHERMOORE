from dataclasses import replace

import pytest

from src.tokenizer.masked_byte_benchmark import (
    ArmRun,
    BenchmarkArm,
    BenchmarkContractError,
    CaseObservation,
    RoutingStep,
    compare_three_arms,
    evaluate_run,
    generate_structured_cases,
    report_json,
)


def _observation(case, *, exact: bool = True, extra_work: int = 0) -> CaseObservation:
    reconstruction = bytearray(case.target)
    if not exact:
        reconstruction[case.masked_positions[0]] ^= 1
    trace = tuple(
        RoutingStep(
            step=step,
            position=position,
            score=1.0 / (step + 1),
            candidate_evaluations=1 + (extra_work if step == 0 else 0),
            predicted_byte=reconstruction[position],
            reason="declared uncertainty order",
        )
        for step, position in enumerate(case.masked_positions)
    )
    return CaseObservation(
        case_id=case.case_id,
        reconstruction=bytes(reconstruction),
        target_probabilities=tuple(0.9 if exact else 0.2 for _ in case.masked_positions),
        trace=trace,
        forward_passes=len(trace),
    )


def _run(cases, arm: BenchmarkArm, seed: int, *, exact: bool = True) -> ArmRun:
    return ArmRun(
        arm=arm,
        seed=seed,
        model_parameters=10_000,
        training_updates=100,
        max_candidate_evaluations=32,
        observations=tuple(_observation(case, exact=exact) for case in cases),
    )


def test_structured_cases_are_replayable_and_split_disjoint() -> None:
    first = generate_structured_cases(split="test", seed=7, count=9)
    second = generate_structured_cases(split="test", seed=7, count=9)
    train = generate_structured_cases(split="train", seed=7, count=9)

    assert first == second
    assert {case.case_id for case in first}.isdisjoint(case.case_id for case in train)
    assert {case.mask_kind.value for case in first} == {"single", "span", "structure"}


def test_evaluate_run_recomputes_exactness_and_work() -> None:
    cases = generate_structured_cases(split="test", seed=11, count=3)
    run = _run(cases, BenchmarkArm.BYTE_BASELINE, 1, exact=True)

    report = evaluate_run(cases, run)

    assert report["exact_recovery"] == 1.0
    assert report["mean_candidate_evaluations"] >= 1.0
    assert report["mean_work_to_exact_recovery"] == report["mean_candidate_evaluations"]
    assert report["mean_target_nll"] > 0.0
    assert '"schema": "scbe.masked-byte-routing-benchmark.v1"' in report_json(report)


def test_evaluator_rejects_unreported_budget_overrun() -> None:
    cases = generate_structured_cases(split="test", seed=13, count=1)
    observation = _observation(cases[0], extra_work=100)
    run = ArmRun(
        arm=BenchmarkArm.SIX_VIEW_ADAPTIVE,
        seed=1,
        model_parameters=100,
        training_updates=10,
        max_candidate_evaluations=4,
        observations=(observation,),
    )

    with pytest.raises(BenchmarkContractError, match="candidate budget"):
        evaluate_run(cases, run)


def test_evaluator_rejects_trace_that_disagrees_with_reconstruction() -> None:
    cases = generate_structured_cases(split="test", seed=17, count=1)
    observation = _observation(cases[0])
    bad_step = replace(observation.trace[0], predicted_byte=observation.trace[0].predicted_byte ^ 1)
    bad = replace(observation, trace=(bad_step, *observation.trace[1:]))
    run = _run(cases, BenchmarkArm.SIX_VIEW_FIXED, 1)
    run = replace(run, observations=(bad,))

    with pytest.raises(BenchmarkContractError, match="trace prediction"):
        evaluate_run(cases, run)


def test_comparison_separates_representation_and_routing_gains() -> None:
    cases = generate_structured_cases(split="test", seed=19, count=3)
    runs = []
    for seed in (1, 2, 3):
        runs.extend(
            [
                _run(cases, BenchmarkArm.BYTE_BASELINE, seed, exact=False),
                _run(cases, BenchmarkArm.SIX_VIEW_FIXED, seed, exact=True),
                _run(cases, BenchmarkArm.SIX_VIEW_ADAPTIVE, seed, exact=True),
            ]
        )

    report = compare_three_arms(cases, runs)

    assert report["representation_gain"]["exact_recovery_delta"] == 1.0
    assert report["representation_gain"]["powered_positive_result"] is True
    assert report["routing_gain"]["exact_recovery_delta"] == 0.0
    assert report["routing_gain"]["powered_positive_result"] is False


def test_comparison_rejects_parameter_mismatch() -> None:
    cases = generate_structured_cases(split="test", seed=23, count=1)
    runs = []
    for seed in (1, 2, 3):
        baseline = _run(cases, BenchmarkArm.BYTE_BASELINE, seed)
        fixed = replace(_run(cases, BenchmarkArm.SIX_VIEW_FIXED, seed), model_parameters=20_000)
        adaptive = _run(cases, BenchmarkArm.SIX_VIEW_ADAPTIVE, seed)
        runs.extend((baseline, fixed, adaptive))

    with pytest.raises(BenchmarkContractError, match="parameter counts"):
        compare_three_arms(cases, runs)
