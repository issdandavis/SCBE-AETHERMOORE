"""Tests for the consolidated instrument-computer package."""

from __future__ import annotations

from pathlib import Path

from python.scbe import instrument_computer as ic


def test_holophonor_emits_faces_and_executes_python_receipt():
    receipt = ic.holophonor_receipt("C E", args=(2, 3, 4), speak=False)

    assert receipt["schema"] == "scbe_holophonor_receipt_v1"
    assert receipt["ops"] == ["add", "mul"]
    assert receipt["ca_words"] == ["bip'a", "bip'i"]
    assert receipt["value"] == 14
    assert receipt["bijective"] is True
    assert receipt["primary_face_count"] == 8
    assert set(receipt["primary_faces"]) == set(ic.SUPPORTED_TARGETS)
    assert "haskell" in receipt["primary_sources"]
    assert "song :: Double -> Double -> Double -> Maybe Double" in receipt["primary_sources"]["haskell"]
    assert "-- add (0x00)" in receipt["primary_sources"]["haskell"]
    assert receipt["coding_systems"]["haskell_primary"]["status"] == "primary_face"
    assert receipt["broad_face_count"] >= 18
    assert "python" in receipt["coding_systems"]["broad_faces"]
    assert receipt["stista_atoms"][0]["op"] == "add"
    assert receipt["stista_atoms"][0]["ca_word"] == "bip'a"
    assert receipt["colors"][0]["color"].startswith("#")


def test_music_theory_roles_and_key_bijection():
    assert ic.note_role("E", "C", "major")["triad"]["roman"] == "iii"
    assert ic.note_role("E", "E", "minor")["degree"] == 1
    assert ic.consonance_report(["E", "G", "B"])["verdict"] == "consonant_in_key"

    proof = ic.key_bijection_proof()
    assert proof["verdict"] == "PASS"
    assert {row["cell0"] for row in proof["renders"]} == {5}


def test_any_instrument_alphabet_proof_and_shell_ram():
    proof = ic.prove_any_instrument()
    assert proof["verdict"] == "PASS"
    whistle = next(row for row in proof["rows"] if row["instrument"] == "two_tone_whistle")
    assert whistle["notes_per_op"] == 3
    assert whistle["cell0"] == 5

    shell = ic.shell_demo()
    assert shell["verdict"] == "PASS"
    assert shell["checks"] == {"loaded_5": True, "doubled_to_10": True, "emitted_10": True}

    reel = ic.reel_tape_demo()
    assert reel["verdict"] == "PASS"
    assert reel["receipt"]["mechanism"] == "old_movie_player_reels"
    assert reel["receipt"]["reel_changes"]
    assert reel["receipt"]["output_hex"] == "05"


def test_cli_and_package_do_not_depend_on_dev_scratch_paths():
    root = Path(__file__).resolve().parents[2]
    package = (root / "python" / "scbe" / "instrument_computer.py").read_text(encoding="utf-8")
    cli = (root / "scripts" / "audio" / "instrument_computer.py").read_text(encoding="utf-8")

    assert "C:\\dev" not in package
    assert "C:\\dev" not in cli
