from src.symphonic.multipath.band import arbitrate_cell, closure_check, summarize_closure


def test_arbitrate_cell_prefers_dr_then_ru_then_others():
    result = arbitrate_cell(7, {"CA": 1, "KO": 1, "RU": 1, "DR": 1})
    assert result.writers == ("DR", "RU", "KO", "CA")
    assert result.winner == "DR"
    assert result.failure_mode == "write_write_collision"
    assert result.desync_required is True
    assert result.safety_risk == "HIGH"


def test_arbitrate_cell_escalates_ru_over_ca_on_write_collision():
    result = arbitrate_cell(11, {"CA": 1, "RU": 1})
    assert result.writers == ("RU", "CA")
    assert result.winner == "RU"
    assert result.desync_required is True
    assert result.safety_risk == "HIGH"
    assert result.correctness_risk == "HIGH"


def test_arbitrate_cell_resolves_gc_languages_by_correctness_priority_only():
    result = arbitrate_cell(13, {"KO": 1, "AV": 1, "UM": 1})
    assert result.writers == ("AV", "UM", "KO")
    assert result.winner == "AV"
    assert result.desync_required is False
    assert result.safety_risk == "LOW"
    assert result.correctness_risk == "HIGH"


def test_closure_check_summarizes_band_conflicts():
    results = closure_check(
        {
            1: {"CA": 1, "RU": 1},
            2: {"AV": 1, "KO": 1},
            3: {"DR": 1},
        }
    )
    summary = summarize_closure(results)
    assert summary == {
        "resolved": 1,
        "desync_required": 1,
        "failures": 2,
        "safety_high": 1,
        "correctness_high": 2,
    }
