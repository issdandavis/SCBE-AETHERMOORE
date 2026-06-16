"""Cube hardware bridge — wire protocol, transports, and the bridge loop."""

import pytest

from python.scbe import cube_bridge as BR
from python.scbe import polyglot as P


def test_parse_wire_notation():
    assert BR.parse_wire("R") == ["R"]
    assert BR.parse_wire("U'") == ["U'"]
    assert BR.parse_wire("Ui") == ["U'"]
    assert BR.parse_wire("F2") == ["F", "F"]
    assert BR.parse_wire("R U' F2 GO") == ["R", "U'", "F", "F", "GO"]


def test_parse_wire_rejects_bad_token():
    with pytest.raises(ValueError):
        BR.parse_wire("X")
    with pytest.raises(ValueError):
        BR.parse_wire("R9")


def test_parse_wire_byte_compact_form():
    assert BR.parse_wire_byte(0x02) == "F"  # face index 2 = F, cw
    assert BR.parse_wire_byte(0x0A) == "F'"  # bit 3 set = counter-clockwise
    assert BR.parse_wire_byte(0x00) == "U"
    with pytest.raises(ValueError):
        BR.parse_wire_byte(0x07)  # face index 7 out of range


def test_sim_source_from_string_and_list():
    assert list(BR.SimSource("R U GO").moves()) == ["R", "U", "GO"]
    assert list(BR.SimSource(["R", "F'"]).moves()) == ["R", "F'"]


def test_bridge_runs_committed_program(capsys):
    cmds = []
    rc = BR.bridge(BR.SimSource("R U F' GO"), on_command=lambda p: cmds.append(p))
    out = capsys.readouterr().out
    assert rc == 0
    assert "twist: right clockwise -> ADD" in out
    assert 'command "add, inc, pow"' in out
    assert cmds == [P.program_bytes("add", "inc", "pow")]


def test_bridge_flushes_at_end_of_stream_without_go(capsys):
    cmds = []
    BR.bridge(BR.SimSource("R R"), on_command=lambda p: cmds.append(p))
    assert cmds == [P.program_bytes("add", "add")]  # end-of-stream commits


def test_serial_and_ble_fail_clearly_without_hardware():
    # whether the optional dep is missing OR the port/device is bogus, it must raise
    with pytest.raises(Exception):
        BR.SerialSource("NOT_A_REAL_PORT_XYZ")
