from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.aetherpp.lower import lower_ast
from scripts.aetherpp.parse import ast_to_dict, parse_program

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_lowering_builds_route_packet_with_bijection() -> None:
    nodes = parse_program(
        "set goal to route to python. "
        "apply discrete fold 1.0 to manifold 0 in tongue KO. "
        'encode "add" in tongue AV. '
        "run route."
    )
    packet = lower_ast(ast_to_dict(nodes), source_name="unit.aether")
    route = packet["shell_contract"]["route_packet"]
    assert packet["schema_version"] == "geoseal-aether-route-v1"
    assert route["route_tongue"] == "AV"
    assert route["route_language"] == "typescript"
    assert packet["build_bijection"]["ok"] is True


def test_cli_check_mode() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/aetherpp/cli.py",
            "--program",
            "set goal to safe route. apply discrete fold 0.5 to manifold 0 in tongue KO. run route.",
            "--check",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["statement_count"] == 3
    assert payload["bijection_ok"] is True
