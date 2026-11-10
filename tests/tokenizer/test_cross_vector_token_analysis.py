from __future__ import annotations

from python.scbe.cross_vector_token_analysis import AXES, analyze, detect_mode, tokenize


def test_math_analysis_is_deterministic_and_receipted() -> None:
    first = analyze("x + 2*y", "x - 2*y", mode="math", seed=17)
    second = analyze("x + 2*y", "x - 2*y", mode="math", seed=17)
    assert first == second
    assert len(first["receipt_sha256"]) == 64
    assert first["analysis"]["relation_counts"]["substituted"] == 1
    assert first["analysis"]["radial"]["relay_count"] == 64 * 4 * 4


def test_math_sign_change_appears_on_declared_polarity_axis() -> None:
    report = analyze("x + 2*y", "x - 2*y", mode="math")
    polarity = AXES.index("math_polarity")
    changed = [row for row in report["analysis"]["alignment"] if row["relation"] == "substituted"]
    assert [(row["input_text"], row["output_text"]) for row in changed] == [("+", "-")]
    assert changed[0]["delta"][polarity] == -2.0
    assert changed[0]["delta_trits"][polarity] == -1


def test_linguistic_negation_changes_trits_and_tongue_membership() -> None:
    report = analyze("allow the action", "do not allow the action", mode="linguistic")
    assert report["analysis"]["relation_counts"]["inserted"] == 2
    assert report["analysis"]["tongue_differential"]["only_b"] == ["KO"]
    not_token = next(token for token in report["output"]["tokens"] if token["text"] == "not")
    assert not_token["semantic_class"] == "NEGATION"
    assert any(value != 0 for value in not_token["tau"])


def test_utf8_spans_and_identity_round_trip_to_source_bytes() -> None:
    source = "café + 3"
    for token in tokenize(source, mode="math"):
        encoded = source.encode("utf-8")[token.byte_start : token.byte_end]
        assert encoded.decode("utf-8") == token.text
        assert token.canonical_id == f"utf8:{encoded.hex()}"
        assert len(token.vector) == len(AXES)


def test_auto_mode_and_radial_flash_are_typed() -> None:
    assert detect_mode("rotate the vector") == "linguistic"
    assert detect_mode("v = r**2") == "math"
    report = analyze("rotate vector", "rotate vector now")
    radial = report["analysis"]["radial"]
    assert len(radial["flashes"]) == 4
    assert set(radial["relay_trit_histogram"]) == {"-1", "0", "1"}
    assert sum(radial["relay_trit_histogram"].values()) == radial["relay_count"]
