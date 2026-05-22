"""Custom-encounter JSON loader: round-trips the demo and rejects director footguns clearly."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from src.narrative_combat.director import Director
from src.narrative_combat.fixtures import boss_duel_demo
from src.narrative_combat.loader import (
    EncounterSpecError,
    encounter_from_dict,
    encounter_to_dict,
    load_encounter,
)


def test_dump_then_load_round_trips_the_demo():
    original = boss_duel_demo(seed=1337)
    rebuilt = encounter_from_dict(encounter_to_dict(original))
    assert rebuilt == original


def test_round_tripped_encounter_produces_identical_fight():
    original = boss_duel_demo(seed=1337)
    rebuilt = encounter_from_dict(encounter_to_dict(original))
    assert Director(original).run() == Director(rebuilt).run()


def test_load_encounter_reads_a_json_file(tmp_path):
    path = tmp_path / "encounter.json"
    path.write_text(json.dumps(encounter_to_dict(boss_duel_demo(seed=1337))), encoding="utf-8")
    loaded = load_encounter(path)
    assert loaded == boss_duel_demo(seed=1337)


def test_seed_override_replaces_file_seed():
    spec = encounter_to_dict(boss_duel_demo(seed=1337))
    loaded = encounter_from_dict(spec, seed_override=42)
    assert loaded.seed == 42


def test_missing_required_field_points_at_the_path():
    spec = encounter_to_dict(boss_duel_demo())
    del spec["fighters"][0]["techniques"]
    with pytest.raises(EncounterSpecError, match=r"encounter\.fighters\[0\]\.techniques"):
        encounter_from_dict(spec)


def test_fewer_than_two_fighters_is_rejected():
    spec = encounter_to_dict(boss_duel_demo())
    spec["fighters"] = spec["fighters"][:1]
    with pytest.raises(EncounterSpecError, match=r"at least 2 fighters"):
        encounter_from_dict(spec)


def test_empty_concealed_is_rejected_before_director_crashes():
    spec = encounter_to_dict(boss_duel_demo())
    spec["fighters"][0]["concealed"] = []
    with pytest.raises(EncounterSpecError, match=r"concealed"):
        encounter_from_dict(spec)


def test_concealed_pointing_at_unknown_technique_is_rejected():
    spec = encounter_to_dict(boss_duel_demo())
    spec["fighters"][0]["concealed"] = ["no_such_art"]
    with pytest.raises(EncounterSpecError, match=r"unknown technique id"):
        encounter_from_dict(spec)


def test_missing_required_feature_kind_is_rejected():
    spec = encounter_to_dict(boss_duel_demo())
    spec["features"] = [f for f in spec["features"] if f["kind"] != "monster"]
    with pytest.raises(EncounterSpecError, match=r"missing \['monster'\]"):
        encounter_from_dict(spec)


def test_wrong_type_is_rejected_with_type_name():
    spec = encounter_to_dict(boss_duel_demo())
    spec["fighters"][0]["stats"]["body"] = "strong"
    with pytest.raises(EncounterSpecError, match=r"expected an integer, got str"):
        encounter_from_dict(spec)


def test_duplicate_required_feature_kind_is_rejected():
    spec = encounter_to_dict(boss_duel_demo())
    duplicate = dict(spec["features"][0])  # a second safe_zone
    duplicate["feature_id"] = "second_safe_zone"
    spec["features"].append(duplicate)
    with pytest.raises(EncounterSpecError, match=r"appear more than once"):
        encounter_from_dict(spec)


def test_cli_reports_bad_encounter_to_stderr_with_exit_code_2(tmp_path):
    bad = tmp_path / "bad.json"
    spec = encounter_to_dict(boss_duel_demo())
    spec["fighters"][0]["concealed"] = []  # director footgun the loader must catch
    bad.write_text(json.dumps(spec), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "src.narrative_combat.cli", "--encounter", str(bad)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "concealed" in result.stderr
    assert result.stdout.strip() == ""
