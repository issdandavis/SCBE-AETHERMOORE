from scripts.research.prime_alphabet_circuit_probe import (
    ALPHABET_SIZE,
    apply_rotating_circuit,
    evaluate_symbols,
    gap_mod26,
    rotation_offset,
    run_probe,
    value_mod26,
)


def test_rotation_offset_covers_every_start_position_once() -> None:
    offsets = [rotation_offset(cycle * ALPHABET_SIZE) for cycle in range(ALPHABET_SIZE)]

    assert offsets[:3] == [0, 25, 24]
    assert sorted(offsets) == list(range(ALPHABET_SIZE))


def test_apply_rotating_circuit_moves_second_cycle_to_z_start() -> None:
    symbols = [0] * (ALPHABET_SIZE * 2)
    rotated = apply_rotating_circuit(symbols)

    assert rotated[0] == 0
    assert rotated[ALPHABET_SIZE - 1] == 0
    assert rotated[ALPHABET_SIZE] == 25


def test_behavior_encoders_use_values_and_gaps() -> None:
    primes = [2, 3, 5, 7, 11]

    assert value_mod26(primes) == [2, 3, 5, 7, 11]
    assert gap_mod26(primes) == [1, 2, 2, 4]


def test_evaluate_symbols_detects_ordered_alternation_above_shuffle() -> None:
    symbols = ([0, 1] * 400) + ([2, 3] * 400)
    result = evaluate_symbols(
        encoding="demo",
        base_symbols=symbols,
        mode="direct",
        null_seeds=40,
        complete_circuits=False,
    )

    assert result.stats.adjacent_mi_bits > result.null_p95_mi
    assert result.verdict == "CLEARS_MI_NULL"


def test_run_probe_returns_all_default_encodings() -> None:
    report = run_probe(
        limit=20_000, max_primes=2_000, null_seeds=5, complete_circuits=True
    )

    assert report["schema_version"] == "prime_alphabet_circuit_probe_v1"
    assert len(report["results"]) == 10
