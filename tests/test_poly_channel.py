from python.scbe.poly_channel import classify_row, normalize_number, run_javascript, run_python, summarize


def test_normalize_number_handles_commas_and_fractions():
    assert normalize_number("$1,234") == 1234.0
    assert normalize_number("answer is 3/4") == 0.75


def test_js_channel_promotes_when_python_and_js_agree():
    row = classify_row(
        gold=7.0,
        final_value=None,
        py_value=7.0,
        js_value=7.0,
        model_confidence=0.9,
    )
    assert row["baseline_status"] == "ABSTAIN"
    assert row["poly_status"] == "TRIANGULATED"
    assert row["promoted_by_js"] is True
    assert row["poly_correct"] is True


def test_shared_misread_survives_polyglot_channel():
    row = classify_row(
        gold=8.0,
        final_value=7.0,
        py_value=7.0,
        js_value=7.0,
        model_confidence=0.95,
    )
    assert row["poly_status"] == "TRIANGULATED"
    assert row["poly_correct"] is False


def test_final_contradiction_blocks_runtime_promotion():
    row = classify_row(
        gold=83.0,
        final_value=20.0,
        py_value=945.0,
        js_value=945.0,
        model_confidence=1.0,
    )
    assert row["py_js_trust"] is True
    assert row["final_contradicts_execution"] is True
    assert row["promoted_by_js"] is False
    assert row["poly_status"] == "ABSTAIN"


def test_execution_firewall_rejects_host_access():
    py = run_python("import os\nprint(7)")
    js = run_javascript("const fs = require('fs'); console.log(7)")
    assert py.ok is False
    assert "blocked token" in py.error
    assert js.ok is False
    assert "blocked token" in js.error


def test_summarize_reports_lift_and_false_accept_delta():
    rows = [
        classify_row(gold=7, final_value=7, py_value=7, js_value=7, model_confidence=0.95),
        classify_row(gold=8, final_value=None, py_value=8, js_value=8, model_confidence=0.95),
        classify_row(gold=9, final_value=10, py_value=10, js_value=10, model_confidence=0.95),
    ]
    summary = summarize(rows)
    assert summary["baseline"]["trusted"] == 2
    assert summary["polyglot"]["trusted"] == 3
    assert summary["delta"]["trusted"] == 1
    assert summary["counts"]["promoted_by_js_correct"] == 1
