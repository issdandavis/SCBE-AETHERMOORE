import json
import subprocess
import sys

from scbe_polly_pad import PAD_MODES, PollyPad, SquadSpace, UnitState, pad_namespace_key, scbe_decide


def test_public_runtime_exports_core_polly_pad_objects():
    assert "ENGINEERING" in PAD_MODES
    state = UnitState(unit_id="polly-1", x=0, y=0, z=0, coherence=0.9, d_star=0.2, h_eff=5)
    squad = SquadSpace(squad_id="demo", units={"polly-1": state})
    pad = PollyPad(unit_id="polly-1", mode="ENGINEERING")

    assert pad.tongue == "CA"
    assert "plan_only" in pad.tools
    assert pad.assist("code review", state, squad).startswith("HOT:")


def test_namespace_and_decision_are_deterministic():
    assert pad_namespace_key("polly-1", "ENGINEERING", "CA", 1) == "polly-1:ENGINEERING:CA:1"
    assert scbe_decide(d_star=0.1, coherence=0.9, h_eff=10) == "ALLOW"
    assert scbe_decide(d_star=3.0, coherence=0.9, h_eff=10) == "DENY"


def test_cli_modes_outputs_json():
    result = subprocess.run(
        [sys.executable, "-m", "scbe_polly_pad", "modes"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ENGINEERING"]["tongue"] == "CA"
    assert "code_exec_safe" in payload["ENGINEERING"]["tools"]


def test_cli_trace_outputs_route_decision():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scbe_polly_pad",
            "trace",
            "--state",
            "0.1,0.2,0.0,0.0,0.0,0.0",
            "--d-star",
            "0.2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["decision"] in {"ALLOW", "QUARANTINE", "DENY"}
    assert len(payload["traces"]) == 3
