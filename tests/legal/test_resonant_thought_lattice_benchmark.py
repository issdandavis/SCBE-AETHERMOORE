from scripts.legal.resonant_thought_lattice_benchmark import run_benchmark


def test_resonant_thought_lattice_improves_fixture_score() -> None:
    report = run_benchmark()

    assert report["schema"] == "scbe_resonant_thought_lattice_benchmark_v1"
    assert report["case_count"] == 8
    assert report["metrics"]["lattice_mean"] > report["metrics"]["baseline_mean"]
    assert report["metrics"]["improved_cases"] >= 6
    assert report["metrics"]["regressed_cases"] == 0


def test_resonant_thought_lattice_reports_cautious_claim_language() -> None:
    report = run_benchmark()
    language = report["cautious_claim_language"].lower()

    assert "deterministic" in language
    assert "baseline" in language
    assert "does not establish live-model generalization" in language
    assert "guarantee" not in language
