"""Tests for the PowerShell-style parameter-binding framework.

The framework lifts five PowerShell `[Parameter()]` features onto pydantic:
Mandatory, ValidateSet (Literal), ValidateRange (Field ge/le),
ValidatePattern (Field pattern), and ParameterSetName (model_config).
These tests cover the framework end to end via argparse dispatch and
also exercise the live `geoseal seal-here` subcommand to confirm the
glue holds in the running CLI.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

import pytest
from pydantic import ConfigDict, Field

from src.cli.param_binding import (
    BoundCommand,
    ParameterSetError,
    bind_subparser,
)


# ---------------------------------------------------------------------------
#  Models used as fixtures
# ---------------------------------------------------------------------------

class _SimpleCmd(BoundCommand):
    name: str = Field(..., description="Required name")
    count: int = Field(3, ge=1, le=10, description="How many (1-10)")
    flag: bool = Field(False, description="Boolean flag")
    tongue: Literal["ko", "av", "ru"] = Field("ko", description="Choice")
    tags: list[str] = Field(default_factory=list, description="Repeatable")


class _ParamSetCmd(BoundCommand):
    model_config = ConfigDict(
        extra="forbid",
        parameter_sets={
            "by-name":   ["location_name"],
            "by-coords": ["lat", "lon"],
        },
    )
    location_name: Optional[Literal["a", "b", "c"]] = Field(None, description="Named")
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(None, ge=-180.0, le=180.0)


def _make_parser_with(model, handler):
    parser = argparse.ArgumentParser()
    bind_subparser(parser, model, handler)
    return parser


# ---------------------------------------------------------------------------
#  Direct framework tests
# ---------------------------------------------------------------------------

def test_required_field_marked_required_in_argparse() -> None:
    parser = _make_parser_with(_SimpleCmd, lambda c, ns: 0)
    with pytest.raises(SystemExit):
        # `--name` is missing → argparse exits non-zero.
        parser.parse_args([])


def test_defaults_flow_through_argparse_and_validate() -> None:
    parser = _make_parser_with(_SimpleCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--name", "alpha"])
    bound = _SimpleCmd.from_namespace(ns)
    assert bound.name == "alpha"
    assert bound.count == 3       # default flowed through
    assert bound.flag is False    # store_true default
    assert bound.tongue == "ko"
    assert bound.tags == []


def test_validate_range_rejects_out_of_band_value() -> None:
    parser = _make_parser_with(_SimpleCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--name", "x", "--count", "99"])
    with pytest.raises(ParameterSetError) as exc:
        _SimpleCmd.from_namespace(ns)
    assert "less_than_equal" in str(exc.value) or "100" in str(exc.value) or "10" in str(exc.value)


def test_literal_choices_propagate_to_argparse() -> None:
    parser = _make_parser_with(_SimpleCmd, lambda c, ns: 0)
    with pytest.raises(SystemExit):
        # `xx` is not in {ko, av, ru} — argparse rejects before pydantic.
        parser.parse_args(["--name", "x", "--tongue", "xx"])


def test_repeatable_list_arg() -> None:
    parser = _make_parser_with(_SimpleCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--name", "x", "--tags", "a", "--tags", "b"])
    bound = _SimpleCmd.from_namespace(ns)
    assert bound.tags == ["a", "b"]


def test_boolean_flag_default_false_becomes_true_when_passed() -> None:
    parser = _make_parser_with(_SimpleCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--name", "x", "--flag"])
    bound = _SimpleCmd.from_namespace(ns)
    assert bound.flag is True


# ---------------------------------------------------------------------------
#  Parameter-set tests
# ---------------------------------------------------------------------------

def test_parameter_set_by_name_path_succeeds() -> None:
    parser = _make_parser_with(_ParamSetCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--location-name", "a"])
    bound = _ParamSetCmd.from_namespace(ns)
    assert bound.location_name == "a"
    assert bound.lat is None and bound.lon is None


def test_parameter_set_by_coords_path_succeeds() -> None:
    parser = _make_parser_with(_ParamSetCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--lat", "48.1", "--lon", "-123.4"])
    bound = _ParamSetCmd.from_namespace(ns)
    assert bound.lat == pytest.approx(48.1)
    assert bound.lon == pytest.approx(-123.4)


def test_parameter_sets_mutual_exclusion_rejected() -> None:
    parser = _make_parser_with(_ParamSetCmd, lambda c, ns: 0)
    ns = parser.parse_args(["--location-name", "a", "--lat", "48.1", "--lon", "-123.4"])
    with pytest.raises(ParameterSetError) as exc:
        _ParamSetCmd.from_namespace(ns)
    assert "mutually exclusive" in str(exc.value)


def test_no_parameter_set_satisfied_rejected() -> None:
    parser = _make_parser_with(_ParamSetCmd, lambda c, ns: 0)
    ns = parser.parse_args([])  # nothing supplied
    with pytest.raises(ParameterSetError) as exc:
        _ParamSetCmd.from_namespace(ns)
    assert "no parameter set satisfied" in str(exc.value)


def test_syntax_help_shows_parameter_sets() -> None:
    text = _ParamSetCmd.syntax_help()
    assert "[by-name]" in text and "[by-coords]" in text
    assert "--location-name" in text
    assert "--lat" in text and "--lon" in text


# ---------------------------------------------------------------------------
#  Live CLI integration: `geoseal seal-here`
# ---------------------------------------------------------------------------

GEOSEAL_CLI = "src/geoseal_cli.py"


def _run_cli(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "seal-here", *extra],
        capture_output=True, text=True, timeout=60,
    )


def test_seal_here_by_name_emits_packet_summary() -> None:
    proc = _run_cli(
        "--secret", "testkey",
        "--payload", "agent-state-42",
        "--location-name", "port-angeles",
        "--radius-km", "5",
    )
    assert proc.returncode == 0, proc.stderr
    body = proc.stdout.strip().splitlines()
    summary = json.loads("\n".join(body))
    assert summary["version"] == "geoseal-seal-here-v1"
    assert summary["fence"]["radius_m"] == 5000.0
    assert summary["tongue"] == "ko"
    assert summary["token_count"] > 0


def test_seal_here_by_coords_matches_by_name_for_same_point() -> None:
    by_name = _run_cli(
        "--secret", "testkey",
        "--payload", "agent-state-42",
        "--location-name", "port-angeles",
        "--radius-km", "5",
    )
    by_coords = _run_cli(
        "--secret", "testkey",
        "--payload", "agent-state-42",
        "--lat", "48.1181",
        "--lon", "-123.4307",
        "--radius-km", "5",
    )
    name_summary = json.loads(by_name.stdout)
    coord_summary = json.loads(by_coords.stdout)
    # The bijective transport guarantees byte-equal token streams for the
    # same payload + tongue, so the source/token hashes must agree.
    assert name_summary["source_sha256"] == coord_summary["source_sha256"]
    assert name_summary["token_sha256"] == coord_summary["token_sha256"]


def test_seal_here_radius_out_of_range_rejected() -> None:
    proc = _run_cli(
        "--secret", "k", "--payload", "p",
        "--location-name", "seattle",
        "--radius-km", "200",
    )
    assert proc.returncode != 0
    assert "less_than_equal" in proc.stderr or "100" in proc.stderr


def test_seal_here_both_sets_rejected() -> None:
    proc = _run_cli(
        "--secret", "k", "--payload", "p",
        "--location-name", "sequim",
        "--lat", "48.0", "--lon", "-123.0",
    )
    assert proc.returncode != 0
    assert "mutually exclusive" in proc.stderr


def test_seal_here_unknown_named_location_rejected_by_argparse() -> None:
    proc = _run_cli(
        "--secret", "k", "--payload", "p",
        "--location-name", "moscow",
    )
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr
