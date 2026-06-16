"""Tests for cube_faces — one token core, every face a different use."""
from __future__ import annotations

from python.scbe.cube_faces import all_faces


def test_all_faces_present():
    f = all_faces("loop")
    assert set(f["faces"]) == {"chemistry", "roles", "code", "governance", "wolfram"}


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
