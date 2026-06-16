import json
import random
import subprocess
import sys

from python.scbe import overcreation as OC


def test_generate_program_is_stack_valid_and_deterministic():
    a = OC.generate_program(random.Random(7), min_len=8, max_len=8)
    b = OC.generate_program(random.Random(7), min_len=8, max_len=8)
    assert a == b

    depth = 3
    for op in a:
        arity = OC.B.EXACT[op][0]
        assert depth >= arity
        depth = depth - arity + 1


def test_run_loop_is_deterministic_and_ranked():
    a = OC.run_loop(count=80, seed=3, top=5, max_len=8)
    b = OC.run_loop(count=80, seed=3, top=5, max_len=8)
    assert a == b
    scores = [row["surprise_score"] for row in a["top"]]
    assert scores == sorted(scores, reverse=True)
    assert a["kept"] >= len(a["top"]) > 0


def test_top_candidates_are_complete_bounded_and_nonlinear():
    payload = OC.run_loop(count=120, seed=4, top=8, max_len=9)
    assert any(row["nonlinear_ops"] for row in payload["top"])
    for row in payload["top"]:
        assert row["relation"] != "incomplete"
        assert abs(row["logic"]) <= payload["filters"]["max_abs_result"]
        assert abs(row["intuition"]) <= payload["filters"]["max_abs_result"]
        assert row["surprise_score"] >= 0.0


def test_cli_json_smoke():
    proc = subprocess.run(
        [
            sys.executable,
            "scbe.py",
            "overcreate",
            "--count",
            "40",
            "--top",
            "3",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["schema"] == "scbe_overcreation_v1"
    assert len(payload["top"]) <= 3
