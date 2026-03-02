# tests/test_mode_switcher.py
import pytest

def test_simple_read_selects_sightless():
    from src.browser.mode_switcher import compute_phi_weight, select_mode
    weight = compute_phi_weight(
        domain_sensitivity=0.1,  # news site
        action_type="read",
        data_sensitivity=0.1,    # public
        auth_required=False,
    )
    assert weight < 5.0
    assert select_mode(weight) == "sightless"

def test_form_interaction_selects_visual():
    from src.browser.mode_switcher import compute_phi_weight, select_mode
    weight = compute_phi_weight(
        domain_sensitivity=0.3,
        action_type="type",
        data_sensitivity=0.3,
        auth_required=True,
    )
    assert 5.0 <= weight < 10.0
    assert select_mode(weight) == "visual"

def test_transaction_selects_full_octopus():
    from src.browser.mode_switcher import compute_phi_weight, select_mode
    weight = compute_phi_weight(
        domain_sensitivity=0.7,
        action_type="submit",
        data_sensitivity=0.7,
        auth_required=True,
    )
    assert 10.0 <= weight < 20.0
    assert select_mode(weight) == "full_octopus"

def test_banking_selects_governed_critical():
    from src.browser.mode_switcher import compute_phi_weight, select_mode
    weight = compute_phi_weight(
        domain_sensitivity=0.9,
        action_type="submit",
        data_sensitivity=0.9,
        auth_required=True,
    )
    assert weight >= 20.0
    assert select_mode(weight) == "governed_critical"

def test_domain_sensitivity_lookup():
    from src.browser.mode_switcher import domain_sensitivity
    assert domain_sensitivity("google.com") < 0.3
    assert domain_sensitivity("chase.com") > 0.7
    assert domain_sensitivity("unknownsite.xyz") == 0.5  # default

def test_action_type_weights():
    from src.browser.mode_switcher import ACTION_WEIGHTS
    assert ACTION_WEIGHTS["read"] < ACTION_WEIGHTS["click"]
    assert ACTION_WEIGHTS["click"] < ACTION_WEIGHTS["submit"]
