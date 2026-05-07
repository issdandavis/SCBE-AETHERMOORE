"""Tests for the v8-pre Phase 2 prompt parser.

The parser must read ONLY the prompt text (never the answer key) and
extract the semantic schema. These tests exercise each of the surface
forms used by ``coding_verification_unseen_eval_v1``."""

from __future__ import annotations

import json
from pathlib import Path

from python.scbe.mahss_v8_pre_prompt_parser import (
    PromptSchema,
    format_mahss_prefix,
    parse_prompt,
)


def _load_contract() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "config" / "model_training" / "coding_verification_eval_contract.json"
    return json.loads(path.read_text(encoding="utf-8"))["prompts"]


def test_parse_basic_tongue_lang_pair():
    schema = parse_prompt("Implement foo(x) in tongue KO (Kor'aelin/Python).")
    assert "kor'aelin" in schema.tongues
    assert "python" in schema.languages


def test_parse_translate_extracts_both_tongues_and_slot_list():
    """count_vowels translate prompt -- both source and target tongues."""

    prompt = (
        "Algorithm: count_vowels. Source tongue: KO (Kor'aelin, Python). "
        "Translate to tongue UM (Umbroth, Haskell), preserving slot alignment "
        "(sig, init, loop_open, loop_body, ret)."
    )
    schema = parse_prompt(prompt)
    assert "kor'aelin" in schema.tongues
    assert "umbroth" in schema.tongues
    assert "python" in schema.languages
    assert "haskell" in schema.languages
    for slot in ("sig", "init", "loop_open", "loop_body", "ret"):
        assert slot in schema.slots
    assert schema.mode == "translate"


def test_parse_identify_mode_adds_phi_weight_for_tongue():
    prompt = (
        "Identify the algorithm and its slot structure from this snippet "
        "(UM, Haskell):\n```hs\ndoubleAll xs = map (*2) xs\n```\n"
        "Return algorithm name, description, tongue with phi-weight, and the slot list."
    )
    schema = parse_prompt(prompt)
    assert "umbroth" in schema.tongues
    assert "phi=6.85" in schema.metrics
    assert schema.mode == "identify"
    # Identify mode adds slot markers
    assert "algorithm:" in schema.slots
    assert "slots:" in schema.slots


def test_parse_approval_mode_adds_verdict_keywords():
    prompt = (
        "card_route: DR / Draumric Markdown\nscript_route: KO / Kor'aelin / Python\n"
        "Return an explicit verdict (PROMOTE/HOLD/INCUBATE), evidence requirement, "
        "next safe action, and whether this is fast, medium, or long return."
    )
    schema = parse_prompt(prompt)
    assert "draumric" in schema.tongues
    assert "kor'aelin" in schema.tongues
    assert schema.mode == "approval"
    for kw in ("verdict", "evidence", "next", "horizon"):
        assert kw in schema.keywords


def test_parse_lane_boundary_mode_adds_code_keywords():
    prompt = (
        "A user pastes the code token `queue_drain_guard` into the SCBE coding agent. "
        "Reply ONLY in code-side terms. Do NOT mention chemistry vocabulary at all. "
        "Classify queue_drain_guard as a code identifier, state next action is to grep "
        "for its definition in the source tree, and that the unit test exercising it must be run."
    )
    schema = parse_prompt(prompt)
    assert "queue_drain_guard" in schema.identifiers
    assert schema.mode == "lane_boundary"
    for kw in ("code identifier", "definition", "unit test", "run"):
        assert kw in schema.keywords


def test_parse_multi_lens_extracts_all_three_tongues():
    prompt = (
        "Implement triple(x) so it returns 3*x. Provide three language lenses: "
        "KO (Kor'aelin/Python), AV (Avali/JavaScript), RU (Runethic/Rust). "
        "Mark each lens with its tongue label."
    )
    schema = parse_prompt(prompt)
    for t in ("kor'aelin", "avali", "runethic"):
        assert t in schema.tongues, f"missing {t} in {schema.tongues}"
    for lang in ("python", "javascript", "rust"):
        assert lang in schema.languages


def test_parse_identifies_function_names():
    schema = parse_prompt("Implement inventory_unique(items) in tongue KO (Kor'aelin/Python).")
    assert "inventory_unique" in schema.identifiers


def test_parse_backtick_identifier():
    schema = parse_prompt("verify the code token `queue_drain_guard` for me")
    assert "queue_drain_guard" in schema.identifiers


def test_parse_returns_unique_lowercase_values():
    schema = parse_prompt("Implement foo in tongue KO (Kor'aelin/Python). Use tongue KO (Kor'aelin/Python) again.")
    # Even though tongue KO appears twice, schema should contain it once
    assert schema.tongues.count("kor'aelin") == 1


def test_format_prefix_omits_empty_roles():
    schema = PromptSchema(tongues=("kor'aelin",), languages=("python",))
    prefix = format_mahss_prefix(schema, {"TONGUE": ["kor'aelin"], "LANG": ["python"]})
    assert "required-tongues: kor'aelin" in prefix
    assert "required-langs: python" in prefix
    assert "::\n" in prefix
    assert "required-slots" not in prefix


def test_format_prefix_returns_empty_when_nothing_retrieved():
    schema = PromptSchema()
    assert format_mahss_prefix(schema, {}) == ""


def test_parser_extracts_at_least_one_tongue_per_v6g_prompt():
    """Every v6g prompt has at least one tongue mention -- the parser
    should find it. This is the 'fairness' test: parser doesn't peek at
    the answer key, just reads the prompt."""

    prompts = _load_contract()
    failed = []
    for entry in prompts:
        schema = parse_prompt(entry["prompt"])
        # Every prompt either has a tongue, an identifier, or is lane_boundary mode
        if not (schema.tongues or schema.identifiers or schema.mode == "lane_boundary"):
            failed.append(entry["id"])
    assert not failed, f"parser extracted nothing useful from: {failed}"


def test_parser_role_counts_match_expected_for_translate_prompt():
    prompts = _load_contract()
    translate_entry = next(p for p in prompts if p["id"] == "code_eval_count_vowels_translate")
    schema = parse_prompt(translate_entry["prompt"])
    counts = schema.role_counts()
    assert counts.get("TONGUE", 0) == 2  # KO + UM
    assert counts.get("LANG", 0) == 2  # python + haskell
    assert counts.get("SLOT", 0) >= 5  # sig, init, loop_open, loop_body, ret
