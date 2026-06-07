from __future__ import annotations

import json

from python.scbe.rosetta_control import build_rosetta_control_node
from python.scbe.rosetta_control_ingress import (
    CONTROL_SOURCE_INGRESS_PASS,
    CONTROL_SOURCE_SHAPE_FAILED,
    INVALID_CONTROL_SOURCE_HEADER,
    MISSING_CONTROL_SOURCE_HEADER,
    ingest_rosetta_control_source,
)


def _source(target: str = "python") -> str:
    node = build_rosetta_control_node(
        "factorial(5)",
        targets=[target],
        fn_name="factorial_5",
        run=False,
    )
    return node.artifacts[0].source


def _prime_tape() -> tuple[int, ...]:
    node = build_rosetta_control_node(
        "factorial(5)",
        targets=["python"],
        fn_name="factorial_5",
        run=False,
    )
    return node.control_tape.primes


def test_rosetta_control_ingress_round_trips_source_to_control_tape() -> None:
    ingress = ingest_rosetta_control_source(_source("python"))

    assert ingress.ok is True
    assert ingress.verdict == CONTROL_SOURCE_INGRESS_PASS
    assert ingress.expression == "factorial(5)"
    assert ingress.target == "python"
    assert ingress.fn_name == "factorial_5"
    assert ingress.value == 120
    assert ingress.control_prime_sequence == _prime_tape()
    assert "CTRL:WHILE" in ingress.roles


def test_rosetta_control_ingress_accepts_all_control_targets() -> None:
    expected = _prime_tape()

    for target in ("python", "typescript", "go", "c"):
        ingress = ingest_rosetta_control_source(_source(target))

        assert ingress.ok is True, target
        assert ingress.target == target
        assert ingress.control_prime_sequence == expected


def test_rosetta_control_ingress_rejects_missing_header() -> None:
    source = _source("python").split("\n", 1)[1]

    ingress = ingest_rosetta_control_source(source)

    assert ingress.ok is False
    assert ingress.verdict == MISSING_CONTROL_SOURCE_HEADER


def test_rosetta_control_ingress_rejects_tampered_header_expression() -> None:
    source = _source("python").replace('"factorial(5)"', '"gcd(48,18)"', 1)

    ingress = ingest_rosetta_control_source(source)

    assert ingress.ok is False
    assert ingress.verdict == CONTROL_SOURCE_SHAPE_FAILED
    assert ingress.shape_verdict == "UNTRACED_CONTROL_SOURCE"


def test_rosetta_control_ingress_rejects_bad_header_prime_tape() -> None:
    source = _source("python").replace(
        '"prime_tape":"', '"prime_tape":"not-a-prime ', 1
    )

    ingress = ingest_rosetta_control_source(source)

    assert ingress.ok is False
    assert ingress.verdict == INVALID_CONTROL_SOURCE_HEADER
    assert "prime_tape is invalid" in "; ".join(ingress.problems)


def test_rosetta_control_ingress_rejects_injected_payload() -> None:
    source = _source("typescript").replace("{\n", "{\n  console.log('pwned');\n", 1)

    ingress = ingest_rosetta_control_source(source)

    assert ingress.ok is False
    assert ingress.verdict == CONTROL_SOURCE_SHAPE_FAILED
    assert ingress.shape_verdict == "UNTRACED_CONTROL_SOURCE"


def test_scbe_code_ingest_rosetta_control_source_cli() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "ingest-rosetta-control-source",
            "--content",
            _source("python"),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(stdout)
    assert payload["verdict"] == CONTROL_SOURCE_INGRESS_PASS
    assert payload["expression"] == "factorial(5)"
    assert payload["control_prime_sequence"] == list(_prime_tape())


def test_scbe_code_ingest_rosetta_control_source_cli_rejects_missing_header() -> None:
    from tests.agents.test_scbe_code import _run_cli

    rc, stdout, _ = _run_cli(
        [
            "ingest-rosetta-control-source",
            "--content",
            "def f():\n    return 1\n",
            "--json",
        ]
    )

    assert rc == 1
    payload = json.loads(stdout)
    assert payload["verdict"] == MISSING_CONTROL_SOURCE_HEADER
