"""Tests for cube_faces — one token core, every face a different use."""

from __future__ import annotations

from python.scbe.cube_faces import all_faces


def test_all_faces_present():
    f = all_faces("loop")
    assert set(f["faces"]) == {"bits", "chemistry", "roles", "audio", "code", "governance", "wolfram"}


def test_bits_and_audio_faces():
    f = all_faces("loop")
    bits = f["faces"]["bits"]
    assert bits["hex"] == b"loop".hex()
    assert set(bits["binary"]) <= {"0", "1"} and len(bits["binary"]) == len(b"loop") * 8
    audio = f["faces"]["audio"]
    assert audio["note"] in {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}
    assert audio["phi_frequency_hz"] >= 440.0


def test_core_is_the_token_bytes():
    f = all_faces("loop")
    assert f["core"]["hex"] == b"loop".hex()
    assert f["core"]["bytes"] == list(b"loop")
    assert f["bijective"] is True  # every face round-trips to the token


def test_code_face_has_all_six_tongues():
    f = all_faces("ward")
    assert set(f["faces"]["code"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    for face in f["faces"]["code"].values():
        assert "language" in face and "tokens" in face


def test_wolfram_face_is_per_byte_with_class():
    f = all_faces("loop")
    rules = f["faces"]["wolfram"]["per_byte_rules"]
    assert len(rules) == len(b"loop")
    for r in rules:
        assert r["class"] in {"I", "II", "III", "IV"}
        assert r["rule"] == r["byte"]  # byte value IS the CA rule


def test_roles_come_from_chemistry_trit():
    f = all_faces("loop")
    trit = f["faces"]["chemistry"]["trit_vector"]
    active = [t for t in ("KO", "AV", "RU", "CA", "UM", "DR") if trit.get(t, 0) > 0]
    # one role label per positively-lit tongue channel
    assert len(f["faces"]["roles"]) == len(active)


def test_real_chemistry_recognized():
    from python.scbe.atomic_tokenization import chemical_element, parse_formula

    assert chemical_element("H").symbol == "H"
    assert chemical_element("O").Z == 8
    assert chemical_element("loop") is None  # plain word -> not an element
    assert parse_formula("H2O") == {"H": 2, "O": 1}
    assert parse_formula("C3H8") == {"C": 3, "H": 8}
    assert parse_formula("loop") is None  # not a false compound


def test_chem_face_differentiates_chemistry():
    assert all_faces("H")["faces"]["chemistry"]["real_element"]["symbol"] == "H"
    assert all_faces("Na")["faces"]["chemistry"]["real_element"]["Z"] == 11
    assert all_faces("H2O")["faces"]["chemistry"]["composition"] == {"H": 2, "O": 1}
    # a non-chemical word gets neither enrichment (back-compatible)
    chem = all_faces("loop")["faces"]["chemistry"]
    assert "real_element" not in chem and "composition" not in chem


def test_linguistic_classifier_untouched():
    # the chemistry layer is additive — the encoder/parity path is unchanged
    from python.scbe.atomic_tokenization import classify_token_semantic

    assert classify_token_semantic("loop") == "ENTITY"
    assert classify_token_semantic("the") == "INERT_WITNESS"
