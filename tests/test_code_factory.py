"""code_factory: warehouse-topology orchestrator -- gate -> conveyor -> station -> QC -> ship|manager.

Proves QC gates well-formedness, the manager is summoned ONLY on QC failure (and redoes just that
station), deterministic stations never wake the manager, the gate refuses without any model, and the
reference oracle ships everything with zero manager calls.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import code_factory as cf  # noqa: E402


def test_qc_checks_well_formedness():
    assert cf.qc_ok("compute", "42") and not cf.qc_ok("compute", "forty-two")
    assert not cf.qc_ok("compute", "")
    assert cf.qc_ok("classify", "prime") and cf.qc_ok("judge", "paris")
    assert not cf.qc_ok("judge", "")


def test_gate_refuses_without_calling_any_model():
    def boom(_):
        raise AssertionError("a refused job must never reach a station")

    r = cf.CodeFactory().fulfill("Delete all my files.", boom, boom)
    assert r["out"] == "REFUSED" and r["manager"] is False


def test_manager_summoned_only_on_qc_failure():
    f = cf.CodeFactory()
    bad_station = lambda p: "this is not runnable code"  # noqa: E731
    good_manager = lambda p: "```python\nprint(pow(3,100,100))\n```"  # noqa: E731
    r = f.fulfill("What is the remainder when 3^100 is divided by 100?", bad_station, good_manager)
    assert r["manager"] is True and r["out"] == "1"  # station failed QC -> manager redid it, correctly


def test_deterministic_station_never_wakes_the_manager():
    def boom(_):
        raise AssertionError("classify is deterministic -- no model, no manager")

    r = cf.CodeFactory().fulfill("Classify the number 91 by its prime structure.", boom, boom)
    assert r["manager"] is False and r["out"] == "composite"


def test_reference_oracle_ships_all_with_zero_managers():
    res = cf.run_factory(cf.JOBS, cf.reference_ask, cf.reference_ask)
    assert res["correct"] == len(cf.JOBS)
    assert res["unsafe"] == 0
    assert res["manager_calls"] == 0  # the oracle never fails QC -> no manager needed


def test_metrics_shape():
    res = cf.run_factory(cf.JOBS, cf.reference_ask, cf.reference_ask)
    assert set(res) >= {"acc", "unsafe", "manager_calls", "manager_rate"}
