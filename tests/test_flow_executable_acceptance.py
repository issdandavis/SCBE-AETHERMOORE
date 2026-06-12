"""The flow loop's workingness gate must be a REAL executable check, not prose.

These tests drive `_execute_flow_packet` directly with benign commands so the
outcome is deterministic (no live agent bus). They lock the contract that makes
"recognized for not working but stubs" true:

  - a packet with an executable acceptance that passes  -> passed, verified
  - a packet whose acceptance fails (stub artifact)      -> NOT passed, REWORK
  - a packet with no acceptance command                  -> honestly unverified
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_cli():
    spec = importlib.util.spec_from_file_location("scbe_system_cli", ROOT / "scripts" / "scbe-system-cli.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scbe_system_cli"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


CLI = _load_cli()

OK = ["python", "-c", "import sys; sys.exit(0)"]
FAIL = ["python", "-c", "import sys; sys.exit(1)"]


def _run(packet: dict) -> dict:
    return CLI._execute_flow_packet(packet, ROOT, 30)


def test_passing_acceptance_marks_packet_verified_and_passed() -> None:
    result = _run(
        {
            "goal": "write a working artifact",
            "dispatch_command": OK,
            "acceptance_command": OK,
        }
    )
    assert result["executed"] is True
    assert result["returncode"] == 0
    assert result["passed"] is True
    assert result["workingness_verified"] is True
    assert result["acceptance"]["checked"] is True
    assert result["acceptance"]["verified"] is True
    assert "recovery" not in result


def test_failing_acceptance_blocks_pass_and_demands_rework() -> None:
    # The work command exits 0 (a stub "looks" done) but the acceptance check fails.
    result = _run(
        {
            "goal": "emit a stub that does not actually work",
            "dispatch_command": OK,
            "acceptance_command": FAIL,
        }
    )
    assert result["executed"] is True
    assert result["returncode"] == 0  # the command itself ran clean...
    assert result["passed"] is False  # ...but it is NOT done
    assert result["workingness_verified"] is True
    assert result["acceptance"]["checked"] is True
    assert result["acceptance"]["verified"] is False
    assert result["recovery"]["strategy"] == "REWORK"


def test_stdout_contains_expectation_is_enforced() -> None:
    result = _run(
        {
            "goal": "produce the required token",
            "dispatch_command": OK,
            "acceptance_command": ["python", "-c", "print('PACMAN_OK')"],
            "acceptance_expect": {"stdout_contains": "PACMAN_OK"},
        }
    )
    assert result["passed"] is True
    assert result["acceptance"]["verified"] is True

    miss = _run(
        {
            "goal": "fail the token check",
            "dispatch_command": OK,
            "acceptance_command": ["python", "-c", "print('nope')"],
            "acceptance_expect": {"stdout_contains": "PACMAN_OK"},
        }
    )
    assert miss["passed"] is False
    assert miss["acceptance"]["verified"] is False
    assert miss["recovery"]["strategy"] == "REWORK"


def test_no_acceptance_command_is_honestly_unverified() -> None:
    result = _run(
        {
            "goal": "no executable acceptance declared",
            "dispatch_command": OK,
        }
    )
    assert result["passed"] is True  # command succeeded
    assert result["workingness_verified"] is False  # but we did NOT verify it
    assert result["acceptance"]["checked"] is False


def test_failed_work_command_does_not_reach_acceptance() -> None:
    result = _run(
        {
            "goal": "the work itself fails",
            "dispatch_command": FAIL,
            "acceptance_command": OK,
        }
    )
    assert result["passed"] is False
    assert result["returncode"] != 0
    assert result["acceptance"]["checked"] is False
    assert "recovery" in result


def test_board_passes_acceptance_command_through_to_ready_row() -> None:
    # Locks the wiring: a bundle's acceptance_command must survive the
    # status-board build and land on the ready packet the executor consumes.
    bundle = {
        "packets": [
            {
                "task_id": "t::00::scope",
                "step_id": "scope",
                "owner_role": "Implementation Engineer",
                "goal": "do it",
                "dependencies": [],
                "workingness_gate": {"executable": True},
                "acceptance_command": ["python", "-c", "print('ok')"],
                "acceptance_expect": {"stdout_contains": "ok"},
            }
        ]
    }
    board = CLI._build_flow_status_board(bundle, ROOT, set(), set())
    row = board["next_packets"][0]
    assert row["status"] == "ready"
    assert row["acceptance_command"] == ["python", "-c", "print('ok')"]
    assert row["acceptance_expect"] == {"stdout_contains": "ok"}


def test_dry_run_previews_whether_acceptance_would_run() -> None:
    result = _run(
        {
            "goal": "preview only",
            "dispatch_command": OK,
            "acceptance_command": OK,
        }
    )
    # sanity: real run already covered above; here exercise dry-run preview
    preview = CLI._execute_flow_packet(
        {"goal": "preview", "dispatch_command": OK, "acceptance_command": OK},
        ROOT,
        30,
        dry_run=True,
    )
    assert preview["executed"] is False
    assert preview["acceptance"]["would_run"] is True
    assert result["passed"] is True
