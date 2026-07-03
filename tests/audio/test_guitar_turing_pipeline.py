"""Tests for guitar/tab language surfaces over the Machine Crystal runtime."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "audio"


def _load(name: str):
    sys.path.insert(0, str(SCRIPT_DIR))
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_guitar_tab_examples_execute_on_machine_crystal():
    guitar_turing = _load("guitar_turing")

    demo = guitar_turing.demo_receipts()
    assert demo["verdict"] == "PASS"
    assert demo["receipts"]["add_2_3"]["brainfuck"] == "++>+++[<+>-]"
    assert demo["receipts"]["count_to_4"]["receipt"]["output_hex"] == "04"
    assert guitar_turing.tape_value(demo["receipts"]["double_3"], 1) == 6


def test_mode_language_governs_legal_notes_and_executes_phrase():
    guitar_lang = _load("guitar_lang")

    assert guitar_lang.compile_phrase("E minor", ["E", "F#", "G"]) == "+->"
    assert guitar_lang.run_phrase(
        "E minor",
        ["E", "E", "G", "E", "E", "E", "B", "A", "E", "G", "F#", "C"],
    )["receipt"]["tape_window"][0] == 5

    try:
        guitar_lang.compile_phrase("C major", ["F#"])
    except ValueError as exc:
        assert "not in C major" in str(exc)
    else:
        raise AssertionError("F# should be rejected in C major")

    assert guitar_lang.demo_receipt()["verdict"] == "PASS"
