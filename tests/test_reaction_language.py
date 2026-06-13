"""Locks for the natural-language -> reaction-CLI intent parser.

The parser is pure and stdlib-only, so these run without RDKit. A couple of
end-to-end build_ask checks importorskip the chemistry engines.
"""

from __future__ import annotations

import pytest

from python.scbe.reaction_language import plan_from_text


def test_combustion_template_fills_products():
    plan = plan_from_text("balance propane combustion")
    assert plan.verb == "balance" and plan.confident
    assert plan.args["reactants"] == "C3H8,O2"
    assert plan.args["products"] == "CO2,H2O"


def test_burn_phrasing_is_combustion():
    plan = plan_from_text("burn methane in oxygen")
    assert plan.args == {"reactants": "CH4,O2", "products": "CO2,H2O"}


def test_explicit_equation_keeps_both_reactants():
    """Regression: the verb word must not eat the first reactant token."""
    plan = plan_from_text("balance C3H8 + O2 -> CO2 + H2O")
    assert plan.verb == "balance" and plan.confidence >= 0.9
    assert plan.args["reactants"] == "C3H8,O2"
    assert plan.args["products"] == "CO2,H2O"


def test_equation_without_verb_word_still_balances():
    plan = plan_from_text("H2 + O2 -> H2O")
    assert plan.verb == "balance"
    assert plan.args == {"reactants": "H2,O2", "products": "H2O"}


def test_screen_by_name_resolves_to_smiles():
    plan = plan_from_text("is ethanol controlled?")
    assert plan.verb == "screen" and plan.confident
    assert plan.args["input"] == "CCO"


def test_screen_by_bare_smiles():
    """Regression: a bare uppercase SMILES (CCO) must be picked up as the operand."""
    plan = plan_from_text("screen CCO")
    assert plan.verb == "screen" and plan.confident
    assert plan.args["input"] == "CCO"


def test_screen_by_cas_number():
    plan = plan_from_text("screen 50-78-2")
    assert plan.verb == "screen" and plan.args["input"] == "50-78-2"


def test_geometry_by_name_and_by_smiles():
    by_name = plan_from_text("what shape is carbon dioxide")
    assert by_name.verb == "geometry" and by_name.args["smiles"] == "O=C=O"
    by_smiles = plan_from_text("geometry of CCO")
    assert by_smiles.verb == "geometry" and by_smiles.args["smiles"] == "CCO"


def test_checkpoint_extracts_path():
    plan = plan_from_text("checkpoint artifacts/demo/methalox/signed_chain.json")
    assert plan.verb == "checkpoint" and plan.confident
    assert plan.args["packets"] == "artifacts/demo/methalox/signed_chain.json"


def test_ambiguous_species_asks_instead_of_guessing():
    """Two species, no arrow -> low confidence + a clarification, not an action."""
    plan = plan_from_text("react hydrogen and oxygen and water")
    assert plan.verb == "balance" and not plan.confident
    assert plan.clarification is not None
    assert plan.confidence < 0.6


def test_unknown_verb_offers_the_menu():
    plan = plan_from_text("do something vague")
    assert plan.verb is None and plan.clarification is not None
    assert not plan.confident


def test_help_lists_verbs():
    plan = plan_from_text("what can you do")
    assert plan.verb == "help" and plan.notes


def test_parser_never_fabricates_unknown_species():
    """An unknown molecule must clarify, never invent a wrong formula."""
    plan = plan_from_text("balance unobtainium combustion")
    # No known fuel resolved -> must not emit a confident balance command.
    assert not plan.confident
    assert plan.clarification is not None


def test_empty_input_is_handled():
    plan = plan_from_text("   ")
    assert plan.verb is None and plan.clarification is not None


# --- end-to-end through the CLI builder (needs the chemistry engines) -------- #


def test_build_ask_executes_a_confident_balance():
    pytest.importorskip("python.scbe.reaction_balance")
    from scripts.reaction_cli import build_ask

    payload = build_ask("balance methane combustion")
    assert payload["executed"] is True and payload["ok"] is True
    assert payload["verb"] == "balance"
    assert payload["result"]["equation"] == "CH4 + 2 O2 -> CO2 + 2 H2O"


def test_build_ask_explain_does_not_execute():
    from scripts.reaction_cli import build_ask

    payload = build_ask("balance methane combustion", execute=False)
    assert payload["executed"] is False
    assert payload["canonical_command"].startswith("react balance")


def test_build_ask_clarifies_without_executing():
    from scripts.reaction_cli import build_ask

    payload = build_ask("do something vague")
    assert payload["executed"] is False
    assert payload["clarification"]


def test_build_ask_propagates_screen_flag():
    """A flagged screen via `ask` must carry result.flagged so the CLI can exit
    non-zero like the explicit `screen` verb (no entry identity named in test)."""
    from python.scbe.controlled_substances import _listed_cas_numbers
    from scripts.reaction_cli import build_ask

    listed_cas = next(iter(_listed_cas_numbers()))
    payload = build_ask(f"screen {listed_cas}")
    assert payload["verb"] == "screen" and payload["executed"] is True
    assert payload["result"]["flagged"] is True


# --- missing / invalid input files become data, never tracebacks ------------- #


def test_load_json_raises_input_file_error_for_missing_and_invalid(tmp_path):
    from scripts.reaction_cli import InputFileError, load_json

    with pytest.raises(InputFileError, match="file not found"):
        load_json(str(tmp_path / "does_not_exist.json"))

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(InputFileError, match="not valid JSON"):
        load_json(str(bad))


def test_build_checkpoint_missing_file_is_clean_error():
    from scripts.reaction_cli import build_checkpoint

    payload = build_checkpoint("does_not_exist_xyz.json")
    assert payload["ok"] is False
    assert "file not found" in payload["error"]


def test_audit_and_compare_missing_file_are_clean_errors(tmp_path):
    from scripts.reaction_cli import audit_packet, compare_packets

    audit = audit_packet(str(tmp_path / "nope.json"))
    assert audit["ok"] is False and "file not found" in audit["error"]

    comp = compare_packets(str(tmp_path / "a.json"), str(tmp_path / "b.json"))
    assert comp["ok"] is False and "file not found" in comp["error"]


def test_build_ask_checkpoint_missing_file_does_not_crash():
    """The NL layer must surface a builder failure as data, never a traceback."""
    from scripts.reaction_cli import build_ask

    payload = build_ask("checkpoint artifacts/does_not_exist_xyz.json")
    assert payload["verb"] == "checkpoint" and payload["executed"] is True
    assert payload["ok"] is False
    assert "file not found" in payload["result"]["error"]
