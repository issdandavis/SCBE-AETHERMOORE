from python.scbe.atomic_tokenization import (
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
