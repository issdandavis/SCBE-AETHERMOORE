from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from python.scbe.chem_code import (
    canonicalize_chem_source,
    parse_chem_code,
    run_chem_code,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "agents" / "scbe_code.py"


def test_chem_code_loop_emits_safe_research_events_and_prime_control_tape() -> None:
    source = """
    i = 0
    while i < 3 {
      observe H2O
      i = add(i, 1)
    }
    report H2O
    """

    result = run_chem_code(source, fuel=30)

    assert result.ok is True
    assert result.safety_verdict == "ALLOW"
    assert result.final_env["i"] == 3
    assert len(result.events) == 4
    assert result.events[0].op == "observe"
    assert result.events[0].chemistry_unit["chemistry_lane"]["material_elements"] == [
        "H",
        "O",
    ]
    assert result.control_prime_sequence
    assert result.reaction_packet is not None
    assert result.reaction_packet.verify_hash() is True
    assert result.reaction_packet.classification == "LOSSY_RECOVERABLE"


def test_chem_code_has_turing_spine_but_runtime_is_fuel_bounded() -> None:
    source = """
    n = 5
    acc = 1
    while n > 1 {
      acc = mul(acc, n)
      n = sub(n, 1)
    }
    measure caffeine
    """

    result = run_chem_code(source, fuel=50)

    assert result.ok is True
    assert result.final_env["acc"] == 120
    assert result.events[0].target == "caffeine"
    assert "Turing-complete semantics" in result.turing_complete_claim


def test_chem_code_fuel_bound_stops_nonterminating_research_loop() -> None:
    result = run_chem_code(
        """
        while 1 {
          observe H2O
        }
        """,
        fuel=5,
        compile_control=False,
    )

    assert result.ok is False
    assert result.safety_verdict == "QUARANTINE"
    assert result.fuel_used == 5
    assert "fuel exhausted" in result.problems[0]


def test_chem_code_denies_unsafe_synthesis_lane_before_execution() -> None:
    result = run_chem_code("synthesize fentanyl", fuel=20)

    assert result.ok is False
    assert result.safety_verdict == "DENY"
    assert result.events == ()
    assert any(
        "denied unsafe chemistry request" in problem for problem in result.problems
    )


def test_chem_code_parser_normalizes_blocks_and_if_else() -> None:
    source = """
    x = 1
    if x == 1 {
      lookup FeCl
    } else {
      lookup H2O
    }
    """

    parsed = parse_chem_code(source)
    result = run_chem_code(source, fuel=20)

    assert len(parsed) == 2
    assert canonicalize_chem_source(source).splitlines()[0] == "x = 1"
    assert result.ok is True
    assert [event.target for event in result.events] == ["FeCl"]


def test_chem_code_cli_outputs_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "chem-code",
            "--content",
            "i = 0\nwhile i < 2 { observe H2O\ni = add(i, 1) }\nreport H2O",
            "--fuel",
            "30",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["schema"] == "scbe_chem_code_v1"
    assert payload["event_count"] == 3
    assert payload["final_env"]["i"] == 2
