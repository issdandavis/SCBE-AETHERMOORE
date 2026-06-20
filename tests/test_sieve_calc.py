"""sieve_calc: the prime sieve (src.numtheory + src.prime_category) wired as deterministic stepwise
calc steps -- the model never does the exact number work, only the judgement on top.

These tests prove the sieve does primality/factorization/region-triangulation in code, the model is
only asked to label/route, and a wrong judgement rewinds against the sieve's facts.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.sieve_calc import classify_number_task, route_by_region_task  # noqa: E402
from python.scbe.stepwise import always_proposer, run_stepwise, scripted_proposer  # noqa: E402
from src.prime_category import PrimeCategories  # noqa: E402


def test_sieve_computes_primality_and_factors_not_the_model():
    r = run_stepwise(classify_number_task(97), scripted_proposer(["prime"]))
    assert r["completed"] is True and r["answer"] == "prime"
    assert r["model_calls"] == 1  # only the label was asked of the model
    assert r["state"]["is_prime"] is True and r["state"]["nfac"] == 1  # sieve facts, exact


def test_a_wrong_label_rewinds_against_the_sieve_facts():
    # 91 = 7 * 13: the model guesses 'prime', the sieve's is_prime=False rejects it -> rewind
    r = run_stepwise(classify_number_task(91), scripted_proposer(["prime", "composite"]))
    assert r["completed"] is True and r["answer"] == "composite"
    assert r["rewinds"] == 1
    assert r["state"]["is_prime"] is False and r["state"]["nfac"] == 2


def test_classify_covers_the_rule_branches():
    for n, label in [(1, "unit"), (7, "prime"), (8, "prime-power"), (12, "composite")]:
        r = run_stepwise(classify_number_task(n), scripted_proposer([label]))
        assert r["completed"] is True and r["answer"] == label


def test_region_triangulation_routes_by_factored_regions():
    pc = PrimeCategories(["security", "coding", "chemistry", "music"])
    code = pc.code(["coding", "music"])  # 3 * 7
    handlers = {"scanner": "security", "codegen": "coding", "daw": "music"}
    # 'scanner' serves a region the code is NOT in -> misstep; 'codegen' serves 'coding' -> ok
    r = run_stepwise(route_by_region_task(pc, code, handlers), scripted_proposer(["scanner", "codegen"]))
    assert r["completed"] is True and r["answer"] == "codegen"
    assert r["rewinds"] == 1
    assert sorted(r["state"]["regions"]) == ["coding", "music"]  # recovered by factoring the code


def test_a_handler_for_an_absent_region_never_verifies():
    pc = PrimeCategories(["security", "coding", "music"])
    code = pc.code(["coding"])  # only the 'coding' region
    handlers = {"scanner": "security", "codegen": "coding"}
    r = run_stepwise(route_by_region_task(pc, code, handlers), always_proposer("scanner"), max_rewinds=2)
    assert r["completed"] is False and r["stuck_at"] == "handler"  # honest ceiling, no false route
