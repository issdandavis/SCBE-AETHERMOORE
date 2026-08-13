"""Cars and roads: adding a face must never break the road system.

Issac's frame, 2026-08-06: a token is a car, bijectivity is the road system. A ROAD is
two-way — drive out to the face, drive back, the same car arrives. A DESTINATION is
one-way — many cars park in the same spot and the spot cannot say which car it was.

That distinction was already true in `cube_faces` and was never written down, which made
`bijective` easy to misread as a claim about all nine faces. It is not:

    CubeToken.is_bijective() == all(from_face(t, face(t)).token == token for t in TONGUES)

It quantifies over TONGUES only. `chemistry` collapses a token to one element, `audio` to
`sum(raw) % 12`, `color` to one of sixteen palette names — all one-way, none under the
proof, correctly so.

WHAT THIS FILE ACTUALLY GUARDS. Adding `color` and `affect` could not break bijectivity,
because destinations never could. The real hazard had no guard at all: a future face pushed
into TONGUES, after which `is_bijective()` starts returning False and says nothing about
which face did it. These tests fail loudly and name the road.

And one of them is here because it already happened. Wiring the affect face broke every
tongue face on the first run — `emotional_syntax_tree._load_heart_vault()` does
`sys.path.insert(0, ...)` at position ZERO with a path under the SCBE tree so it can read
the Heart Vault emotion taxonomy, after which `from scbe import encode_bytes` inside
`cube_token._tongue_encode` resolved to the python/scbe PACKAGE instead of the root CLI
module and every road died with ImportError. A face's engine perturbed its host's import
resolution, by a route with nothing to do with the face. `test_engine_load_does_not_disturb_sys_path`
is that bug, kept as a test.
"""

from __future__ import annotations

import sys

import pytest

from python.scbe.cube_faces import all_faces
from python.scbe.cube_token import TONGUES, CubeToken

TOKENS = ["loop", "ward", "calc", "bind", "sort"]


@pytest.mark.parametrize("token", TOKENS)
def test_every_road_is_two_way(token: str) -> None:
    """Drive out to each tongue and back; the same car must arrive."""
    rm = all_faces(token)["road_map"]
    assert rm["all_roads_two_way"], "broken roads: %s" % rm["broken_roads"]
    for tongue, road in rm["roads"].items():
        assert road["two_way"], "road %r is ONE-WAY: %r left as %r and came back as %r" % (
            tongue,
            token,
            road["surface"],
            road["returns"],
        )


@pytest.mark.parametrize("token", TOKENS)
def test_bijective_still_holds_with_the_new_faces(token: str) -> None:
    """color and affect are destinations, so wiring them cannot move this."""
    f = all_faces(token)
    assert f["bijective"] is True
    assert "color" in f["faces"] and "affect" in f["faces"]


def test_road_map_and_is_bijective_agree() -> None:
    """Two independent statements of the same invariant must not drift apart.

    `is_bijective()` is one bool over all tongues; `road_map` checks them one at a time.
    If these ever disagree, one of them is lying and the per-road view says which.
    """
    for token in TOKENS:
        f = all_faces(token)
        assert f["bijective"] == f["road_map"]["all_roads_two_way"]


def test_no_destination_is_declared_a_road() -> None:
    """The lossy faces must stay out of the road network. This is the guard that was missing."""
    rm = all_faces("loop")["road_map"]
    for d in rm["destinations"]:
        assert d not in rm["roads"], (
            "%r is a DESTINATION but appears in the road network. If it really round-trips, "
            "prove it with from_face(); if it does not, bijective() will now be False and "
            "will not say why." % d
        )
    assert set(rm["roads"]) == set(TONGUES)


def test_engine_load_does_not_disturb_sys_path() -> None:
    """A face's engine must not rewrite its host's import resolution.

    Regression: loading the affect engine inserted an SCBE path at sys.path[0] and killed
    every tongue face. The loader now snapshots and restores sys.path around the import.
    """
    before = list(sys.path)
    f = all_faces("ward", "I let go and he is alive")
    assert sys.path == before, "engine load mutated sys.path: %r" % ([p for p in sys.path if p not in before],)
    # and the roads still work AFTER the engine has been loaded
    assert f["road_map"]["all_roads_two_way"]
    assert CubeToken("ward").is_bijective() is True


def test_affect_is_a_property_of_the_trip_not_the_car() -> None:
    """A bare token carries no emotion; the utterance it rode in on does.

    Skips rather than fails when the loom engine is absent, because an unavailable face is
    a deployment fact, not a defect in the cube.
    """
    bare = all_faces("ward")["faces"]["affect"]
    if not bare.get("available"):
        pytest.skip("affect engine unavailable: %s" % bare.get("reason"))

    assert bare["context_is_token"] is True, (
        "a reading taken with no passenger must say so, or neutral gets mistaken for a " "measurement of neutrality"
    )
    assert bare["evidence"] == []

    rode = all_faces("ward", "I let go and he is alive")["faces"]["affect"]
    assert rode["context_is_token"] is False
    assert rode["force_relation"] == "restraint_preserved_life"
    assert rode["evidence"], "the passenger produced no evidence phrases"


def test_color_channels_are_not_interchangeable() -> None:
    """`spread_label` discriminates and carries no meaning; `byte_fold` is degenerate.

    The channel this test calls `address` was RENAMED to `spread_label` in the face,
    and the rename is the point rather than cosmetic: it discriminates well (14/16
    swatches, largest bin 28.6%) but it is a crc32 of the token, so it carries
    `is_an_address: False`. Calling it an address implied a placement it never
    performed. Real placement is the `address` FACE, which is a byte<->(cell,
    orientation) bijection. This test kept the old name and so broke on the rename.
    """
    co = all_faces("loop")["faces"]["color"]
    if not co.get("available"):
        pytest.skip("color engine unavailable: %s" % co.get("reason"))

    assert co["spread_label"]["discriminates"] is True
    assert (
        co["spread_label"]["is_an_address"] is False
    ), "a crc32 label spreads well but places nothing -- the address FACE places"
    assert co["byte_fold"]["discriminates"] is False, (
        "byte_fold sent 84% of a 49-token vocabulary to gray. It is retained as a record "
        "that it was checked, never as an address."
    )
    # the degenerate fold really is more concentrated than the crc32 address
    from collections import Counter

    vocab = [
        "loop",
        "ward",
        "calc",
        "bind",
        "sort",
        "hash",
        "read",
        "write",
        "open",
        "close",
        "push",
        "pull",
        "send",
        "recv",
        "make",
        "free",
        "lock",
        "wait",
    ]
    faces = [all_faces(t)["faces"]["color"] for t in vocab]
    addr = Counter(c["spread_label"]["swatch"] for c in faces)
    fold = Counter(c["byte_fold"]["swatch"] for c in faces)
    assert len(addr) > len(fold), "crc32 address (%d swatches) should spread wider than the byte fold (%d)" % (
        len(addr),
        len(fold),
    )
