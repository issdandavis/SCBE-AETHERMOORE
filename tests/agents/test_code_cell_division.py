from __future__ import annotations

from python.scbe.code_cell_division import divide_code_organism


def test_code_cell_division_reconstructs_source_exactly() -> None:
    source = "def f(a, b):\n    return abs(a) + abs(b)\n"

    division = divide_code_organism(source, language="python", parent_id="code:test")

    assert division.reconstructed_source == source
    assert division.identity_preserved is True
    assert division.reaction_packet.classification == "BIJECTIVE"
    assert division.reaction_packet.verify_hash() is True


def test_code_cells_carry_atomic_state_and_ca_prime_when_applicable() -> None:
    division = divide_code_organism("abs add", language="python", parent_id="code:ops")
    non_ws = [cell for cell in division.cells if cell.kind != "whitespace"]

    assert [cell.text for cell in non_ws] == ["abs", "add"]
    assert [cell.ca_prime for cell in non_ws] == [29, 2]
    assert all(cell.atomic_state is not None for cell in non_ws)
    assert division.fusion is not None
    assert set(division.fusion.tau_hat) == {"KO", "AV", "RU", "CA", "UM", "DR"}


def test_code_cell_packet_is_machine_serializable() -> None:
    payload = divide_code_organism("x = abs(y)\n", language="python").to_dict()

    assert payload["schema"] == "scbe_code_cell_division_v1"
    assert payload["cell_count"] > 0
    assert payload["reaction_packet"]["classification"] == "BIJECTIVE"
