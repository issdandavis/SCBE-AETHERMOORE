import math
import random

import pytest

from python.scbe.atomic_tokenization import (
    TONGUES,
    atomic_drift_scale,
    element_to_tau,
    map_token_to_atomic_state,
    map_token_to_element,
)
from python.scbe.chemical_fusion import FusionParams, fuse_atomic_states, fuse_tokens


def test_atomic_mapping_is_deterministic():
    e1 = map_token_to_element("the")
    e2 = map_token_to_element("the")
    assert e1 == e2


def test_language_aware_mapping_aligns_articles():
    english = map_token_to_atomic_state("the", language="en")
    spanish = map_token_to_atomic_state("el", language="es")
    chinese = map_token_to_atomic_state("的", language="zh")

    assert english.semantic_class == "INERT_WITNESS"
    assert spanish.semantic_class == "INERT_WITNESS"
    assert chinese.semantic_class == "INERT_WITNESS"
    assert english.element == spanish.element == chinese.element


def test_context_class_can_shift_token_role():
    temporal = map_token_to_atomic_state("after", context_class="timeline")
    operator = map_token_to_atomic_state("after", context_class="operator")

    assert temporal.semantic_class == "TEMPORAL"
    assert operator.semantic_class == "RELATION"
    assert temporal.element != operator.element


def test_witness_tokens_are_marked_stable():
    state = map_token_to_atomic_state("the", language="en")

    assert state.element.witness_stable is True
    assert state.witness_state == 0
    assert element_to_tau(state.element)["RU"] >= 0


def test_atomic_tau_stays_within_trit_bounds():
    states = [
        map_token_to_atomic_state(token, language="en")
        for token in ("the", "not", "build", "compiler", "after", "very")
    ]

    for state in states:
        for tongue in TONGUES:
            assert getattr(state.tau, tongue) in (-1, 0, 1)


def test_negative_and_dual_atomic_state_are_exposed():
    negation = map_token_to_atomic_state("not", language="en")
    action = map_token_to_atomic_state("build", language="en")
    witness = map_token_to_atomic_state("the", language="en")

    assert negation.negative_state is True
    assert negation.dual_state == 1
    assert action.dual_state == 0
    assert witness.dual_state is None
    assert 0.0 < negation.resilience < 1.0
    assert 0.0 < action.adaptivity < 1.0


def test_negative_and_shadow_atoms_drift_more_than_primary_atoms():
    negation = map_token_to_atomic_state("not", language="en")
    action = map_token_to_atomic_state("build", language="en")

    neg_drift = atomic_drift_scale(negation, trust_factor=1.0)
    action_drift = atomic_drift_scale(action, trust_factor=1.0)

    assert neg_drift > action_drift


def test_higher_trust_damps_atomic_drift():
    state = map_token_to_atomic_state("without", language="en")

    low_trust = atomic_drift_scale(state, trust_factor=0.5)
    high_trust = atomic_drift_scale(state, trust_factor=1.8)

    assert high_trust < low_trust


def test_negation_changes_fusion_output():
    tau_hat_1, _, _ = fuse_tokens(["go"])
    tau_hat_2, _, _ = fuse_tokens(["not", "go"])

    assert tau_hat_1 != tau_hat_2


def test_valence_pressure_changes_reconstruction_votes():
    action_state = map_token_to_atomic_state("build")
    entity_state = map_token_to_atomic_state("compiler")

    baseline = fuse_atomic_states(
        [action_state, entity_state],
        params=FusionParams(rho_default=0.0),
    )
    pressured = fuse_atomic_states(
        [action_state, entity_state],
        params=FusionParams(rho_default=0.25),
    )

    assert pressured.reconstruction_votes["CA"] > baseline.reconstruction_votes["CA"]
    assert pressured.reconstruction_votes["DR"] > baseline.reconstruction_votes["DR"]


def test_edge_weights_affect_fusion_result():
    _, baseline_votes, _ = fuse_tokens(["not", "build"], edge_weights={(0, 1): 0.0})
    _, weighted_votes, _ = fuse_tokens(["not", "build"], edge_weights={(0, 1): 0.5})

    assert weighted_votes["UM"] != baseline_votes["UM"]


def test_empty_fusion_input_is_rejected():
    with pytest.raises(ValueError, match="at least one atomic state"):
        fuse_atomic_states([])


def test_coherence_penalty_grows_with_divergence():
    witness_a = map_token_to_atomic_state("the", language="en")
    witness_b = map_token_to_atomic_state("and", language="en")
    negation = map_token_to_atomic_state("not", language="en")

    aligned = fuse_atomic_states([witness_a, witness_b], edge_weights={(0, 1): 0.5})
    divergent = fuse_atomic_states([witness_a, negation], edge_weights={(0, 1): 0.5})

    assert aligned.coherence_penalty == 0.0
    assert divergent.coherence_penalty > aligned.coherence_penalty


def test_fusion_result_exposes_diagnostics():
    result = fuse_atomic_states(
        [map_token_to_atomic_state("not"), map_token_to_atomic_state("build")],
        edge_weights={(0, 1): 0.5},
        params=FusionParams(rho_default=0.25),
    )

    assert result.coherence_penalty >= 0.0
    assert result.valence_pressure > 0.0
    assert isinstance(result.signed_edge_tension, float)


def test_randomized_fusion_votes_stay_finite():
    token_pool = ["the", "not", "build", "compiler", "after", "very", "because", "run"]
    rng = random.Random(7)

    for _ in range(25):
        sample = [rng.choice(token_pool) for _ in range(rng.randint(1, 8))]
        _, votes, _ = fuse_tokens(sample)
        assert all(math.isfinite(value) for value in votes.values())
