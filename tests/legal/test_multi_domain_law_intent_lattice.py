from scripts.legal.multi_domain_law_intent_lattice import run_lattice


def test_multi_domain_law_intent_lattice_runs() -> None:
    report = run_lattice()

    assert report["schema"] == "scbe_multi_domain_law_intent_lattice_v1"
    assert report["case_count"] == 4
    assert report["metrics"]["domain_count"] == 5
    assert report["metrics"]["axis_count"] == 8
    assert report["metrics"]["expected_domain_coverage_rate"] >= 0.75


def test_inverse_criminality_space_separates_repair_from_concealment() -> None:
    report = run_lattice()
    cases = {case["packet_id"]: case for case in report["cases"]}

    planned = cases["planned_targeted_action"]["inverse_criminality_space"]
    accident = cases["accident_with_repair"]["inverse_criminality_space"]

    assert planned["dark_space_score"] > accident["dark_space_score"]
    assert planned["class"] in {"shadow_region", "dark_core"}
    assert accident["class"] == "star_bearing"


def test_lattice_keeps_cautious_non_conviction_language() -> None:
    report = run_lattice()
    caution = report["cautious_language"].lower()

    assert "not guilt" in caution
    assert "burden of proof" in caution
    assert "fact finder" in caution
    assert "conviction metric" not in caution
