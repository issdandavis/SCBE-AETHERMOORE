"""Tests for the Rubik's-cube token (python/scbe/cube_token.py)."""
from python.scbe.cube_token import CubeToken, CubeRegistry, TONGUES, TONGUE_LANGUAGE


class TestCubeFaces:
    def test_six_coding_language_faces(self):
        c = CubeToken("bind")
        faces = c.code_faces()
        assert set(faces) == set(TONGUES)
        assert faces["KO"]["language"] == "python"
        assert faces["RU"]["language"] == "rust"
        assert all(f["tokens"] for f in faces.values())

    def test_chem_face(self):
        chem = CubeToken("bind").chem_face()
        assert "element" in chem and "trit_vector" in chem
        assert set(chem["trit_vector"]) == set(TONGUES)

    def test_gov_face(self):
        assert CubeToken("bind").gov_face()["tier"] in ("ALLOW", "QUARANTINE")


class TestBijective:
    def test_recover_from_any_face(self):
        for tok in ["bind", "parse", "release", "compile", "hello world"]:
            c = CubeToken(tok)
            assert c.is_bijective()
            for t in TONGUES:
                assert CubeToken.from_face(t, c.face(t)).token == tok

    def test_distinct_tokens_distinct_faces(self):
        a = CubeToken("bind").face("KO")
        b = CubeToken("parse").face("KO")
        assert a != b


class TestRegistry:
    def test_store_and_retrieve(self):
        reg = CubeRegistry(bits=10)
        for w in ["bind", "parse", "release", "compile", "seal"]:
            reg.add(w)
        assert len(reg) == 5
        got = reg.get("release")
        assert got is not None and got.token == "release"
        assert reg.get("missing") is None


class TestFaceFormations:
    def test_six_formations_cover_many_languages(self):
        from python.scbe.cube_token import LANGUAGE_FORMATIONS, LANGUAGE_TO_TONGUE
        assert set(LANGUAGE_FORMATIONS) == set(TONGUES)
        assert len(LANGUAGE_TO_TONGUE) >= 60  # all code languages as faces
        for spec in LANGUAGE_FORMATIONS.values():
            assert spec["paradigm"] and spec["languages"]

    def test_speak_token_as_specific_language(self):
        c = CubeToken("bind")
        # a language routes to its formation's tongue and encodes there
        assert c.as_language("rust")["tongue"] == "RU"
        assert c.as_language("julia")["tongue"] == "CA"
        assert c.as_language("rust")["encoding"] == c.face("RU")
        assert "error" in c.as_language("not-a-language")

    def test_language_reverse_lookup(self):
        from python.scbe.cube_token import tongue_for_language
        assert tongue_for_language("elixir") == "UM"
        assert tongue_for_language("SQL") == "DR"
        assert tongue_for_language("nonsense") is None

    def test_formations_preserve_bijection(self):
        c = CubeToken("compile")
        for tongue, spec in CubeToken("compile").all_formations().items():
            assert CubeToken.from_face(tongue, spec["encoding"]).token == "compile"
