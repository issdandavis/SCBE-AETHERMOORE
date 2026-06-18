"""SCBE Instrument: note songs manifest as executable/disassemblable CA code."""

import pytest

from python.scbe.instrument import (
    ca_word_for_opcode,
    chemistry,
    emit_all,
    faces,
    keyspace,
    melody_for_ops,
    modes,
    notes_to_ops,
    play,
    scale,
    semantic_choices,
    semantic_coverage,
)


def test_coding_scale_maps_notes_to_ca_ops():
    assert modes() == ["ca", "coding"]
    assert scale("coding")["C"] == "add"
    assert scale("coding")["E"] == "mul"
    assert notes_to_ops("C E") == ["add", "mul"]


def test_ca_mode_uses_canonical_cassisivadan_words():
    assert ca_word_for_opcode(0x00) == "bip'a"
    assert ca_word_for_opcode(0x02) == "bip'i"
    assert scale("ca")["bip'a"] == "add"
    assert scale("ca")["bip'i"] == "mul"
    assert notes_to_ops("bip'a bip'i", mode="ca") == ["add", "mul"]


def test_ca_mode_executes_and_round_trips_native_keys():
    result = play("bip'a bip'i", mode="ca", face="python", args=(10, 3, 2))

    assert result["ops"] == ["add", "mul"]
    assert result["value"] == 50
    assert result["song_back"] == "bip'a bip'i"
    assert result["bijective"] is True
    assert [key["op_id"] for key in result["melody"]] == [0, 2]


def test_keyspace_uses_wavelength_and_instrument_axes():
    first = keyspace(0)
    wrapped = keyspace(12)

    assert first["note"] == "C3"
    assert first["instrument"] == "piano"
    assert first["light_nm"] == 380.0
    assert first["color"].startswith("#")
    assert wrapped["note"] == "C4"
    assert wrapped["instrument"] == "strings"
    assert wrapped["light_nm"] > first["light_nm"]
    assert melody_for_ops(["add", "mul"]) == [keyspace(0), keyspace(2)]


def test_instrument_surfaces_semantic_template_choices():
    assert semantic_coverage()["covered"] == 64
    choices = semantic_choices("xor")
    assert choices[0]["name"] == "bitwise_i64"
    assert choices[0]["family"] == "bitwise"
    assert choices[0]["portable"] is True


def test_instrument_has_first_class_chemistry_action():
    row = chemistry("C6H12O6")

    assert row["totals"]["protons"] == 96
    assert row["totals"]["electrons"] == 96
    assert row["totals"]["neutrons_common_isotope"] == 84


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


def test_emit_all_covers_registered_language_faces_for_scalar_song():
    emitted = emit_all("C E")

    assert set(emitted) == set(faces())
    assert len(emitted) >= 18
    assert all(not source.startswith("ERROR:") for source in emitted.values())
    assert "add (0x00)" in emitted["python"]
    assert "mul (0x02)" in emitted["rust"]


def test_unknown_note_is_rejected():
    with pytest.raises(ValueError, match="note 'Z'"):
        notes_to_ops("C Z")
