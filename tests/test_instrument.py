"""SCBE Instrument: note songs manifest as executable/disassemblable CA code."""

import pytest

from python.scbe.instrument import modes, notes_to_ops, play, scale


def test_coding_scale_maps_notes_to_ca_ops():
    assert modes() == ["coding"]
    assert scale("coding")["C"] == "add"
    assert scale("coding")["E"] == "mul"
    assert notes_to_ops("C E") == ["add", "mul"]


def test_play_executes_python_face_and_reads_song_back():
    result = play("C E", face="python", args=(10, 3, 2))

    assert result["ops"] == ["add", "mul"]
    assert result["value"] == 50
    assert result["song_back"] == "C E"
    assert result["bijective"] is True
    assert "# add (0x00)" in result["code"]
    assert "# mul (0x02)" in result["code"]


def test_repeated_note_song_is_bijective():
    result = play("C C", face="python", args=(2, 3, 4))

    assert result["value"] == 9
    assert result["song_back"] == "C C"
    assert result["bijective"] is True


def test_non_python_faces_emit_traceable_code_without_execution():
    rust = play("C E", face="rust", args=(10, 3, 2))
    haskell = play("C E", face="haskell", args=(10, 3, 2))

    assert rust["value"] is None
    assert haskell["value"] is None
    assert rust["song_back"] == "C E"
    assert haskell["song_back"] == "C E"
    assert "add (0x00)" in rust["code"]
    assert "caAdd" in haskell["code"]


def test_unknown_note_is_rejected():
    with pytest.raises(ValueError, match="note 'Z'"):
        notes_to_ops("C Z")
