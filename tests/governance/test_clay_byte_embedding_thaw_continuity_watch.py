from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from python.scbe.clay_byte_embedding_thaw_continuity_watch import (
    POINTER_SCHEMA,
    checkpoint_snapshot,
    exact_process_state,
    file_sha256,
    load_contract,
    process_matches,
    relaunch_eligibility,
)


def _write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _manifest() -> dict:
    return {
        "config": {
            "arms": ["byte_thaw_multiview"],
            "seeds": [7],
            "checkpoint_every": 500,
        }
    }


def _pointer(run: Path, *, generation: int = 0, step: int = 500) -> Path:
    directory = run / "horses" / "byte_thaw_multiview-seed-7" / "checkpoints"
    slot = "slot-a.pt" if generation % 2 == 0 else "slot-b.pt"
    slot_path = _write(directory / slot, f"generation-{generation}".encode())
    value = {
        "schema": POINTER_SCHEMA,
        "slot": slot,
        "sha256": file_sha256(slot_path),
        "generation": generation,
        "step": step,
        "updated_at_utc": "2026-11-15T00:00:00+00:00",
    }
    path = directory / "latest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_checkpoint_pointer_slot_hash_and_cadence_pass(tmp_path: Path) -> None:
    _pointer(tmp_path, generation=2, step=1500)

    snapshot = checkpoint_snapshot(tmp_path, _manifest())

    assert snapshot["valid"] is True
    assert snapshot["pointer_count"] == 1
    assert snapshot["total_checkpoint_steps"] == 1500


@pytest.mark.parametrize("failure", ["hash", "parity", "cadence", "horse"])
def test_checkpoint_integrity_failures_are_closed(tmp_path: Path, failure: str) -> None:
    pointer_path = _pointer(tmp_path, generation=2, step=1500)
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if failure == "hash":
        (pointer_path.parent / "slot-a.pt").write_bytes(b"changed")
    elif failure == "parity":
        pointer["slot"] = "slot-b.pt"
        _write(pointer_path.parent / "slot-b.pt", b"other")
        pointer["sha256"] = file_sha256(pointer_path.parent / "slot-b.pt")
        pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
    elif failure == "cadence":
        pointer["step"] = 1499
        pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
    else:
        rogue = tmp_path / "horses" / "undeclared-seed-8" / "checkpoints" / "latest.json"
        rogue.parent.mkdir(parents=True)
        rogue.write_text(pointer_path.read_text(encoding="utf-8"), encoding="utf-8")
        _write(rogue.parent / "slot-a.pt", b"generation-2")

    snapshot = checkpoint_snapshot(tmp_path, _manifest())

    assert snapshot["valid"] is False
    assert snapshot["errors"]


def _identities() -> dict:
    common = {
        "executable_names": ["python.exe", "pythonw.exe"],
        "required_option_values": {"--output-dir": r"C:\run", "--threads": "2"},
    }
    return {
        "successor_gate": {
            **common,
            "script_aliases": [r"C:\repo\wait.py", r"python\scbe\wait.py"],
        },
        "campaign_child": {
            **common,
            "script_aliases": [r"C:\repo\campaign.py"],
        },
        "recovery_wrapper": {
            "executable_names": ["pythonw.exe"],
            "script_aliases": [r"C:\ops\run_headless.py"],
            "required_option_values": {"--config": r"C:\run\relaunch.json"},
        },
    }


def _process(pid: int, name: str, argv: list[str]) -> dict:
    return {"pid": pid, "parent_pid": 1, "name": name, "argv": argv}


def test_process_identity_requires_exact_script_and_option_values() -> None:
    identity = _identities()["campaign_child"]
    exact = _process(
        4,
        "python.exe",
        ["python.exe", r"C:\repo\campaign.py", "--output-dir", r"C:\run", "--threads", "2"],
    )
    wrong = {**exact, "argv": [*exact["argv"][:-1], "3"]}

    assert process_matches(exact, identity) is True
    assert process_matches(wrong, identity) is False


def test_exact_wrapper_counts_as_retry_authority() -> None:
    wrapper = _process(
        8,
        "pythonw.exe",
        ["pythonw.exe", r"C:\ops\run_headless.py", "--config", r"C:\run\relaunch.json"],
    )

    state = exact_process_state([wrapper], {"process_identities": _identities()})

    assert state["wrapper_present"] is True
    assert state["wrapper_pids"] == [8]


def _absent() -> dict:
    return {
        "valid": True,
        "parent_present": False,
        "child_present": False,
        "wrapper_present": False,
    }


def test_relaunch_requires_two_clean_absence_polls_and_all_gates() -> None:
    eligible, reasons = relaunch_eligibility(
        first_process_state=_absent(),
        second_process_state=_absent(),
        result_exists=False,
        static_valid=True,
        checkpoint_valid=True,
        free_bytes=25 * 1024**3,
        minimum_free_bytes=25 * 1024**3,
        relaunch_count=0,
        maximum_relaunches=1,
    )

    assert eligible is True
    assert reasons == []


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"second_process_state": {**_absent(), "child_present": True}}, "second poll"),
        ({"result_exists": True}, "atomic result"),
        ({"static_valid": False}, "static binding"),
        ({"checkpoint_valid": False}, "checkpoint gate"),
        ({"free_bytes": 25 * 1024**3 - 1}, "disk floor"),
        ({"relaunch_count": 1}, "authority exhausted"),
    ],
)
def test_relaunch_is_fail_closed(change: dict, reason: str) -> None:
    values = {
        "first_process_state": _absent(),
        "second_process_state": _absent(),
        "result_exists": False,
        "static_valid": True,
        "checkpoint_valid": True,
        "free_bytes": 25 * 1024**3,
        "minimum_free_bytes": 25 * 1024**3,
        "relaunch_count": 0,
        "maximum_relaunches": 1,
    }
    values.update(change)

    eligible, reasons = relaunch_eligibility(**values)

    assert eligible is False
    assert any(reason in item for item in reasons)


def test_contract_is_hash_pinned_and_requires_disk_floor(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "schema": "clay.byte-embedding-thaw-continuity-watch.v1.contract",
                "maximum_relaunches": 1,
                "minimum_free_gib": 25.0,
            }
        ),
        encoding="utf-8",
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    assert load_contract(path, digest)["maximum_relaunches"] == 1
    with pytest.raises(RuntimeError, match="hash differs"):
        load_contract(path, "0" * 64)
