from scripts.research.prime_mod_layer_probe import (
    parse_layer_primes,
    run_layers,
    run_probe,
)


def test_parse_layer_primes_rejects_composites() -> None:
    try:
        parse_layer_primes("2,3,4")
    except ValueError as exc:
        assert "must be prime" in str(exc)
    else:
        raise AssertionError("composite layer was accepted")


def test_run_layers_keeps_prime_recall_above_layer_primes() -> None:
    results = run_layers(100, 200, (2, 3, 5, 7))

    assert all(result.recall == 1.0 for result in results)
    assert results[-1].candidate_count == 25
    assert results[-1].prime_count == 21
    assert results[-1].precision == round(21 / 25, 12)


def test_run_probe_reports_schema_and_config() -> None:
    report = run_probe(100, 200, (2, 3, 5))

    assert report["schema_version"] == "prime_mod_layer_probe_v1"
    assert report["config"]["range_count"] == 100
    assert len(report["results"]) == 3
