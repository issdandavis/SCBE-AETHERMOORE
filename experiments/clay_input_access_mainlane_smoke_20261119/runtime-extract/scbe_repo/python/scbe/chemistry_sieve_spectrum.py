"""Prime marks on the three ledger counts.

The prime test is clay_sieve.sieve_of_eratosthenes. Each proton, neutron, and
electron count is prime, composite, or an edge below 2. A composite count is
replaced by the primes that divide it. Word, code, charge, and valence ride
along. They are not sieved.
"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing import Any

from python.scbe.chemistry_science_score import ledger_from_formula

SCHEMA = "aethermoore_chemistry_sieve_spectrum_v1"
SIEVE_PATH = Path(r"C:\dev\loom\clay_sieve.py")
EDGE = "edge"
PRIME = "prime"
COMPOSITE = "composite"

BOUNDARY = (
    "Prime or not-prime comes from clay_sieve.sieve_of_eratosthenes. "
    "A factor is a smaller integer of that count, not a particle inside an electron. "
    "Word, code, charge, and valence are carried. They are not classified as prime."
)


@lru_cache(maxsize=1)
def _sieve_function():
    if not SIEVE_PATH.is_file():
        raise FileNotFoundError(f"prime sieve is not at {SIEVE_PATH}")
    spec = importlib.util.spec_from_file_location("clay_sieve_spectrum", SIEVE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load prime sieve from {SIEVE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sieve = getattr(module, "sieve_of_eratosthenes", None)
    if not callable(sieve):
        raise ImportError("clay_sieve.py has no sieve_of_eratosthenes")
    return sieve


@lru_cache(maxsize=64)
def primes_through(limit: int) -> tuple[int, ...]:
    """Primes <= limit from the loom sieve. Limits below 2 have no primes."""
    if limit < 2:
        return ()
    return tuple(int(prime) for prime in _sieve_function()(limit))


def classify(value: int) -> dict[str, Any]:
    """Mark one integer prime, composite, or edge."""
    number = int(value)
    if number < 2:
        kind = EDGE
        prime = False
    else:
        prime = number in set(primes_through(number))
        kind = PRIME if prime else COMPOSITE
    return {"value": number, "prime": prime, "kind": kind}


def _factors(value: int) -> list[int]:
    number = int(value)
    if number < 2:
        return []
    rest = number
    found: list[int] = []
    for prime in primes_through(number):
        if prime * prime > rest:
            break
        while rest % prime == 0:
            found.append(prime)
            rest //= prime
    if rest > 1:
        found.append(rest)
    return found


def fine_replacement(value: int, part: str) -> dict[str, Any]:
    """Replace a composite count by the primes that divide it. Primes stay."""
    marked = classify(value)
    if marked["kind"] == PRIME:
        return {
            "direction": "fine",
            "part": part,
            "rule": "survivor",
            "state": "survivor",
            "value": marked["value"],
            "kind": PRIME,
            "replaced_by": None,
        }
    if marked["kind"] == EDGE:
        return {
            "direction": "fine",
            "part": part,
            "rule": "survivor",
            "state": "edge",
            "value": marked["value"],
            "kind": EDGE,
            "replaced_by": None,
        }
    factors = _factors(marked["value"])
    return {
        "direction": "fine",
        "part": part,
        "rule": "factor_replacement",
        "state": "between",
        "value": marked["value"],
        "kind": COMPOSITE,
        "replaced_by": [classify(factor) for factor in factors],
    }


def _part_row(name: str, value: int | None) -> dict[str, Any]:
    if value is None:
        return {"part": name, "value": None, "prime": False, "kind": EDGE}
    marked = classify(int(value))
    marked["part"] = name
    return marked


def token_origin(formula: str, word: str, code: str, board_index: int) -> dict[str, Any]:
    """One molecular token: the three counts, plus the sub-parts that ride along."""
    ledger = ledger_from_formula(formula)
    exists = bool(ledger.get("exists"))
    protons = ledger.get("protons") if exists else None
    neutrons = ledger.get("neutrons") if exists else None
    electrons = ledger.get("electrons") if exists else None
    parts = {
        "protons": _part_row("protons", protons),
        "neutrons": _part_row("neutrons", neutrons),
        "electrons": _part_row("electrons", electrons),
    }
    return {
        "formula": formula,
        "exists": exists,
        "board_index": board_index,
        "parts": parts,
        "carried_subparts": {
            "word": word,
            "code": code,
            "charge": ledger.get("charge"),
            "charge_sign": ledger.get("charge_sign"),
            "valence_sum": ledger.get("valence_sum"),
        },
        "fine": (
            []
            if not exists
            else [
                fine_replacement(int(parts["protons"]["value"]), "protons"),
                fine_replacement(int(parts["neutrons"]["value"]), "neutrons"),
                fine_replacement(int(parts["electrons"]["value"]), "electrons"),
            ]
        ),
    }


def _fmt_part(part: dict[str, Any]) -> str:
    return f"{part['part'][0]}={part['value']} {part['kind']}"


def _fmt_factors(step: dict[str, Any]) -> str:
    factors = step.get("replaced_by") or []
    if not factors:
        return step["state"]
    shown = "*".join(str(factor["value"]) for factor in factors)
    return f"{step['value']} -> {shown}"


def drawing(receipt: dict[str, Any]) -> str:
    """Each token on its own line, with the prime mark and any factor replacement."""
    lines = [receipt["name"]]
    for token in receipt["tokens"]:
        if not token["exists"]:
            lines.append(f"  {token['formula']} outside the dimension table")
            continue
        parts = token["parts"]
        lines.append(
            f"  {token['formula']} "
            f"{_fmt_part(parts['protons'])} {_fmt_part(parts['neutrons'])} {_fmt_part(parts['electrons'])}"
        )
        carried = token["carried_subparts"]
        lines.append(f"    word={carried['word']} code={carried['code']} charge={carried['charge']}")
        for step in token["fine"]:
            lines.append(f"    {step['part']} {_fmt_factors(step)}")
    return "\n".join(lines)


def _board(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("board index must be an integer from 0 through 255")
    if value < 0 or value >= 256:
        raise ValueError("board index must be an integer from 0 through 255")
    return value


def spectrum(name: str, tokens: list[dict[str, Any]]) -> dict[str, Any]:
    """Spectrum of one chain. The first token is the origin."""
    if not str(name).strip():
        raise ValueError("name face must be a string")
    if not tokens:
        raise ValueError("a spectrum needs at least one token")
    built = [
        token_origin(
            str(token["formula"]).strip(),
            str(token["word"]).strip(),
            str(token["code"]).strip(),
            _board(token["board_index"]),
        )
        for token in tokens
    ]
    if any(not token["formula"] or not token["carried_subparts"]["word"] for token in built):
        raise ValueError("formula and word faces must be a string")
    path: list[dict[str, Any]] = []
    for token in built:
        path.extend(token["fine"])
    receipt = {
        "schema_version": SCHEMA,
        "kind": "sieve_spectrum",
        "name": str(name).strip(),
        "sieve": "clay_sieve.sieve_of_eratosthenes",
        "tokens": built,
        "origin": built[0],
        "path": path,
        "boundary": BOUNDARY,
    }
    receipt["drawing"] = drawing(receipt)
    return receipt
