"""Unit tests for the identifier-canonicality signal."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.identifier_canonicality import (  # noqa: E402
    L13_MAPPING_RECOMMENDATION,
    evaluate_code,
    recommended_l13_action,
)

# --------------------------------------------------------------------------- #
#  Clean cases
# --------------------------------------------------------------------------- #


def test_clean_ascii_python():
    r = evaluate_code("def add(x, y):\n    return x + y\n")
    assert r.kind == "clean"
    assert r.score == 0.0
    assert r.findings == []
    assert r.identifier_count >= 3
    assert r.fingerprint is not None
    assert recommended_l13_action(r) == "ALLOW"


def test_clean_with_unicode_string_literal():
    """Unicode in string LITERALS is fine — it's only the identifier that matters."""
    src = 'def hello(name):\n    return f"hello, {name} 🌍"\n'
    r = evaluate_code(src)
    assert r.kind == "clean"


# --------------------------------------------------------------------------- #
#  Mixed-script attack (Latin + Cyrillic in one identifier)
# --------------------------------------------------------------------------- #


def test_mixed_script_cyrillic_latin():
    # Cyrillic а sneaked into 'password'
    src = "def login(pаssword):\n    return pаssword\n"
    r = evaluate_code(src)
    assert r.kind == "mixed_script"
    assert r.score >= 0.85
    assert recommended_l13_action(r) == "DENY"
    bad = [f for f in r.findings if f.kind == "mixed_script"]
    assert len(bad) >= 1
    assert "Cyrillic" in bad[0].scripts and "Latin" in bad[0].scripts


def test_mixed_script_greek_latin():
    # Greek omicron in 'login'
    src = "def lοgin(x):\n    return x\n"
    r = evaluate_code(src)
    assert r.kind == "mixed_script"
    assert recommended_l13_action(r) == "DENY"


# --------------------------------------------------------------------------- #
#  Confusable-only attack (pure non-Latin script that mimics ASCII)
# --------------------------------------------------------------------------- #


def test_all_confusable_cyrillic():
    # 'аре' is all Cyrillic, looks like ASCII 'ape'
    src = "def get():\n    аре = 1\n    return аре\n"
    r = evaluate_code(src)
    assert r.kind == "confusable"
    assert 0.55 < r.score < 0.75
    assert recommended_l13_action(r) == "QUARANTINE"


# --------------------------------------------------------------------------- #
#  Invisible / BiDi character attacks
# --------------------------------------------------------------------------- #


def test_zero_width_joiner_in_identifier():
    # ZWJ between 'admin' and '_check'
    src = "def admin‍_check(x):\n    return x\n"
    r = evaluate_code(src)
    assert r.kind == "invisible"
    assert r.score == 1.0
    assert recommended_l13_action(r) == "DENY"


def test_bidi_control_in_identifier_rejected_by_parser():
    """Python's parser rejects BiDi controls in identifiers per PEP 3131
    (only specific Unicode categories are allowed). So BiDi-in-identifier
    surfaces as input_invalid, not a canonicality finding.

    Genuine Trojan-Source attacks (CVE-2021-42574) target string literals
    and comments — out of scope for the v1 identifier gate; a sibling
    source-text BiDi scanner would catch those.
    """
    src = "def bad‮name(x):\n    return x\n"
    r = evaluate_code(src)
    assert r.kind == "input_invalid"


# --------------------------------------------------------------------------- #
#  Legitimate non-ASCII single-script identifier (allow with annotation)
# --------------------------------------------------------------------------- #


def test_greek_single_script_legitimate():
    # 'τ' is a legitimate Greek-only identifier
    src = "def τ(x):\n    return x\n"
    r = evaluate_code(src)
    assert r.kind == "non_ascii"
    assert 0.20 < r.score < 0.40
    assert recommended_l13_action(r) == "ALLOW"


# --------------------------------------------------------------------------- #
#  Catastrophic / edge cases
# --------------------------------------------------------------------------- #


def test_input_invalid_python():
    r = evaluate_code("def f(:\n    return\n")
    assert r.kind == "input_invalid"
    assert r.score == 1.0


def test_unsupported_language():
    r = evaluate_code("fn main() {}", language="rust")
    assert r.kind == "input_invalid"
    assert r.score == 1.0


# --------------------------------------------------------------------------- #
#  L13 mapping coverage
# --------------------------------------------------------------------------- #


def test_l13_mapping_covers_all_kinds():
    expected = {"clean", "non_ascii", "confusable", "mixed_script", "invisible", "input_invalid"}
    assert set(L13_MAPPING_RECOMMENDATION.keys()) == expected


def test_l13_mapping_actions_are_valid():
    valid = {"ALLOW", "QUARANTINE", "DENY", "REROUTE"}
    for action in L13_MAPPING_RECOMMENDATION.values():
        assert action in valid


# --------------------------------------------------------------------------- #
#  Fingerprint stability
# --------------------------------------------------------------------------- #


def test_fingerprint_equal_for_same_identifiers_different_order():
    src_a = "def f(x):\n    y = x\n    z = y\n    return z\n"
    src_b = "def f(x):\n    z = y = x\n    return z\n"
    r_a = evaluate_code(src_a)
    r_b = evaluate_code(src_b)
    # Same identifier set → same fingerprint
    assert r_a.fingerprint == r_b.fingerprint


def test_fingerprint_differs_for_different_identifiers():
    r_a = evaluate_code("def f(x):\n    return x\n")
    r_b = evaluate_code("def f(y):\n    return y\n")
    assert r_a.fingerprint != r_b.fingerprint


# --------------------------------------------------------------------------- #
#  Serialization
# --------------------------------------------------------------------------- #


def test_to_dict_is_json_serializable():
    import json

    src = "def login(pаssword):\n    return pаssword\n"
    r = evaluate_code(src)
    serialized = json.dumps(r.to_dict())
    restored = json.loads(serialized)
    assert restored["kind"] == "mixed_script"
    assert isinstance(restored["findings"], list)
