from __future__ import annotations

import pytest

from python.scbe.turing_rubix import (
    build_jump_table,
    conlang_projection,
    display_faces,
    face_spin_state,
    moves_to_program,
    parse_moves,
    program_to_moves,
    quark_projection,
    run_moves,
)


def test_moves_compile_to_brainfuck_equivalent_program() -> None:
    moves = parse_moves("R R U U D F U' F'")
    assert moves_to_program(moves) == ">>++.[-]"


def test_program_to_moves_round_trips_executable_ops() -> None:
    program = ">,.<+-[]"
    moves = program_to_moves(program)
    assert moves_to_program(moves) == program


def test_run_outputs_byte_from_cube_turns() -> None:
    result = run_moves("U U U U U U U U U U D")
    assert result["program"] == "++++++++++."
    assert result["machine"]["output_bytes"] == [10]


def test_loop_clears_cell() -> None:
    result = run_moves("U U U F U' F'")
    assert result["program"] == "+++[-]"
    assert result["machine"]["tape"] == {}


def test_conlang_projection_maps_faces_to_tongues() -> None:
    rows = conlang_projection(parse_moves("R L U D F B"))
    assert [row["tongue"] for row in rows] == ["KO", "AV", "RU", "CA", "UM", "DR"]
    assert rows[0]["instruction_name"] == "ptr_right"


def test_face_spin_state_tracks_quarter_turns_modulo_four() -> None:
    spin = face_spin_state(parse_moves("R R R R U U' F'"))

    assert spin["R"] == 0
    assert spin["U"] == 0
    assert spin["F"] == 3


def test_quark_projection_tags_faces_as_particle_commands() -> None:
    rows = quark_projection(parse_moves("U D R'"))

    assert rows[0]["flavor"] == "up"
    assert rows[0]["electric_charge_thirds"] == 2
    assert rows[1]["flavor"] == "down"
    assert rows[1]["electric_charge_thirds"] == -1
    assert rows[2]["flavor"] == "charm"
    assert rows[2]["anti"] is True
    assert rows[2]["electric_charge_thirds"] == -2
    assert rows[2]["color"].startswith("anti-")


def test_run_includes_six_face_display_packet() -> None:
    result = run_moves("U U U D")
    faces = result["display_faces"]["faces"]

    assert result["display_faces"]["schema"] == "scbe_turing_rubix_display_faces_v1"
    assert result["display_faces"]["spin_state"]["U"] == 3
    assert result["display_faces"]["spin_state"]["D"] == 1
    assert result["quark_projection"][0]["flavor"] == "up"
    assert result["atomic_faces"]["R"]["field"] == "authority / control / flow start"
    assert result["atomic_faces"]["R"]["phi_weight"] == 1.00
    assert result["atomic_faces"]["R"]["atomic_op_8_vector"][0] == 1
    assert result["atomic_faces"]["B"]["field"] == "schema / integrity / authentication"
    assert result["atomic_faces"]["B"]["phi_weight"] == 11.09
    assert len(result["atomic_faces"]["B"]["atomic_op_8_vector"]) == 8
    assert set(faces) == {"R", "L", "U", "D", "F", "B"}
    assert faces["R"]["app"] == "terminal"
    assert faces["D"]["app"] == "output"
    assert "bytes [3]" in faces["D"]["lines"]
    assert result["spine_core"] in faces["B"]["lines"]


def test_display_faces_can_project_empty_program() -> None:
    result = run_moves("")
    packet = display_faces(result)

    assert "program <empty>" in packet["faces"]["R"]["lines"]
    assert "last <none>" in packet["faces"]["U"]["lines"]


def test_unmatched_loop_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_jump_table("[++")
