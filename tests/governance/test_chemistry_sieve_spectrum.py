"""Prime sieve spectrum: factors go down, struck bonds merge up."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from python.scbe.chemistry_sieve_spectrum import SIEVE_PATH, primes_through, spectrum

ROOT = Path(__file__).resolve().parents[2]
KNOWN_PRIMES_30 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


def _load_clay_sieve():
    spec = importlib.util.spec_from_file_location("clay_sieve_test", SIEVE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _token(formula: str, board: int, word: str | None = None) -> dict:
    return {
        "formula": formula,
        "word": word or formula,
        "code": formula,
        "board_index": board,
    }


def _fine(receipt: dict, part: str) -> dict:
    return next(step for step in receipt["origin"]["fine"] if step["part"] == part)


def test_prime_marks_come_from_the_loom_sieve():
    clay = _load_clay_sieve()

    assert list(primes_through(30)) == list(clay.sieve_of_eratosthenes(30)) == KNOWN_PRIMES_30
    assert "self_sieve" not in Path(ROOT, "python/scbe/chemistry_sieve_spectrum.py").read_text(encoding="utf-8")


def test_edges_survive_and_composites_are_replaced_by_primes():
    water = spectrum("water", [_token("H2O", 8, "run")])
    protons = _fine(water, "protons")
    neutrons = _fine(water, "neutrons")
    electrons = _fine(water, "electrons")

    assert water["origin"]["parts"]["protons"]["value"] == 10
    assert water["origin"]["parts"]["neutrons"]["value"] == 8
    assert water["origin"]["parts"]["electrons"]["value"] == 10
    assert protons["rule"] == "factor_replacement"
    assert [row["value"] for row in protons["replaced_by"]] == [2, 5]
    assert [row["value"] for row in neutrons["replaced_by"]] == [2, 2, 2]
    assert [row["kind"] for row in electrons["replaced_by"]] == ["prime", "prime"]
    assert water["origin"]["carried_subparts"]["word"] == "run"
    assert "Na" not in water["drawing"]
    assert "science_score" not in water
    assert "total" not in water


def test_hydrogen_has_no_finer_grain_than_the_three_counts():
    hydrogen = spectrum("hydrogen", [_token("H", 1)])

    assert [step["state"] for step in hydrogen["origin"]["fine"]] == ["edge", "edge", "edge"]
    assert all(step["replaced_by"] is None for step in hydrogen["origin"]["fine"])
    assert "coarse" not in hydrogen


def test_helium_counts_are_prime_survivors():
    helium = spectrum("helium", [_token("He", 2)])

    assert [step["state"] for step in helium["origin"]["fine"]] == ["survivor", "survivor", "survivor"]
    assert [step["value"] for step in helium["origin"]["fine"]] == [2, 2, 2]


def test_a_chain_keeps_each_token_ledger():
    chain = spectrum("h-he-he", [_token("H", 1), _token("He", 2), _token("He", 3)])

    assert [token["formula"] for token in chain["tokens"]] == ["H", "He", "He"]
    assert [token["parts"]["protons"]["value"] for token in chain["tokens"]] == [1, 2, 2]
    assert "He+He" not in chain["drawing"]
    assert "coarse" not in chain


def test_unknown_formula_does_not_invent_a_path():
    outside = spectrum("outside", [_token("Zz", 0, "outside")])

    assert outside["origin"]["exists"] is False
    assert outside["origin"]["fine"] == []
    assert outside["path"] == []


def test_cli_spectrum_prints_the_water_factors():
    completed = subprocess.run(
        [
            sys.executable,
            "scbe.py",
            "chem",
            "set",
            "spectrum",
            "--formula",
            "H2O",
            "--word",
            "water",
            "--code",
            "O",
            "--board",
            "8",
            "--chain",
            "He",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["sieve"] == "clay_sieve.sieve_of_eratosthenes"
    assert [token["formula"] for token in payload["tokens"]] == ["H2O", "He"]
    assert payload["tokens"][1]["parts"]["protons"]["kind"] == "prime"
    assert "coarse" not in payload
    assert payload["origin"]["carried_subparts"]["word"] == "water"
