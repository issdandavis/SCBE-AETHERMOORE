from ai_orchestration.search_field import (
    SearchFieldPolicy,
    adapt_policy,
    grade_candidate,
    project_candidate,
    trace_candidate,
)


def test_search_trace_is_deterministic_for_same_candidate():
    candidate = {
        "id": "cand-1",
        "transform_class": "refactor",
        "symmetry": "bidirectional",
        "intent": "routing",
        "grades": {"structure": 0.75, "semantic": 0.5, "consistency": 1.0},
    }
    metrics = {"entropy": 0.2, "agreement": 0.82, "harmonic": 3.0}

    first = trace_candidate(candidate, metrics)
    second = trace_candidate(candidate, metrics)

    assert first.to_dict() == second.to_dict()
    assert first.candidate_id == "cand-1"
    assert first.decision == "ALLOW"
    assert first.reasons == ["consensus_ready"]
    assert 0 <= first.residue < 8 * 4 * 6
    assert 0.0 <= first.theta_degrees < 360.0
    assert 0.0 <= first.score <= 1.0


def test_projection_and_grading_are_discrete():
    policy = SearchFieldPolicy()
    candidate = {
        "transform_class": "repair",
        "symmetry": "asymmetric",
        "intent": "test",
        "grades": {"structure": 0.0, "semantic": 0.49, "consistency": 1.0},
    }

    projection = project_candidate(candidate, policy)
    grade = grade_candidate(candidate, policy)

    assert set(projection) == {"transform_class", "symmetry", "intent"}
    assert projection["transform_class"] in range(8)
    assert projection["symmetry"] in range(4)
    assert projection["intent"] in range(6)
    assert grade == [0, 2, 4]


def test_constraints_quarantine_and_deny_bad_candidates():
    high_entropy = trace_candidate(
        {"id": "noisy", "grades": {"structure": 1, "semantic": 1, "consistency": 1}},
        {"entropy": 0.9, "agreement": 0.9, "harmonic": 1.0},
    )
    harmonic_breach = trace_candidate(
        {"id": "unsafe", "grades": {"structure": 1, "semantic": 1, "consistency": 1}},
        {"entropy": 0.1, "agreement": 0.9, "harmonic": 20.0},
    )

    assert high_entropy.decision == "QUARANTINE"
    assert "entropy_above_max" in high_entropy.reasons
    assert harmonic_breach.decision == "DENY"
    assert "harmonic_above_limit" in harmonic_breach.reasons


def test_adapt_policy_applies_coupling_rules():
    policy = SearchFieldPolicy()

    adapted = adapt_policy(
        policy,
        {
            "entropy": 0.8,
            "agreement": 0.4,
            "stability": 0.9,
        },
    )

    assert adapted.phase.damping == 0.765
    # Low agreement expands scale, high stability contracts it.
    assert adapted.phase.scale == 1.92


def test_iteration_cap_denies_trace():
    policy = SearchFieldPolicy()
    trace = trace_candidate(
        {"id": "late", "grades": {"structure": 1, "semantic": 1, "consistency": 1}},
        {"entropy": 0.1, "agreement": 0.9, "iteration": policy.consensus.max_iterations},
        policy,
    )

    assert trace.decision == "DENY"
    assert "max_iterations_reached" in trace.reasons
