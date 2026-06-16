"""Origami — flat cube -> paper -> fan/crane and the number-folding game."""

import pytest

from python.scbe import origami as Origami


def test_unfold_has_six_faces():
    net = Origami.unfold()
    faces = [c for row in net for c in row if c.strip()]
    assert sorted(faces) == ["B", "D", "F", "L", "R", "U"]  # the six cube faces


def test_accordion_alternates_and_renders():
    assert Origami.accordion(5) == ["M", "V", "M", "V", "M"]
    pat = Origami.crease_pattern(Origami.accordion(4))
    assert "│" in pat and "┊" in pat  # mountain + valley glyphs


def test_crane_has_steps():
    steps = Origami.crane()
    assert len(steps) >= 5 and any("base" in s for s in steps)


def test_fortune_teller_requires_eight_cells():
    with pytest.raises(ValueError):
        Origami.FortuneTeller(list("ABC"))
    Origami.FortuneTeller(list("ABCDEFGH"))  # ok


def test_fortune_teller_is_deterministic_and_parity_sensitive():
    ft = Origami.FortuneTeller(list("ABCDEFGH"))
    assert ft.play([4, 3, 2]) == "D"  # orient=1, visible[1]=cell3
    assert ft.play([4, 3, 2]) == "D"  # deterministic
    assert ft.play([2, 1]) == "A"  # even opens -> orientation 0
    assert ft.play([1, 1]) == "B"  # odd opens -> orientation 1


def test_fortune_teller_from_program_cycles_to_eight():
    ft = Origami.FortuneTeller.from_program(["add", "mul", "sqrt", "inc"])
    assert ft.flaps() == ["add", "mul", "sqrt", "inc", "add", "mul", "sqrt", "inc"]
    landed = ft.play([4, 3, 2])  # -> cell 3 -> inc
    assert landed == "inc" and Origami._run_op("inc") == 5.0


def test_empty_picks_rejected():
    with pytest.raises(ValueError):
        Origami.FortuneTeller(list("ABCDEFGH")).play([])
