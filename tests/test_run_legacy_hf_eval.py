from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_legacy_hf_eval import (
    EVAL_SCRIPT,
    build_eval_command,
    choose_python_for_eval,
    main,
)


def test_build_eval_command_targets_eval_script():
    command = build_eval_command(
        Path(r"C:\Users\issda\Python312\python.exe"), ["--json", "--limit", "2"]
    )

    assert command[0] == r"C:\Users\issda\Python312\python.exe"
    assert command[1] == str(EVAL_SCRIPT)
    assert command[-3:] == ["--json", "--limit", "2"]


def test_choose_python_prefers_explicit_runtime(monkeypatch):
    monkeypatch.setattr(
        "scripts.run_legacy_hf_eval.python_supports_local_adapter",
        lambda path: str(path).casefold().endswith("python312\\python.exe"),
    )

    selected = choose_python_for_eval(r"C:\Users\issda\Python312\python.exe")

    assert selected == Path(r"C:\Users\issda\Python312\python.exe")


def test_choose_python_uses_first_supported_candidate(monkeypatch):
    monkeypatch.setattr(
        "scripts.run_legacy_hf_eval.candidate_python_paths",
        lambda: [
            Path(r"C:\Python314\python.exe"),
            Path(r"C:\Users\issda\Python312\python.exe"),
        ],
    )
    monkeypatch.setattr(
        "scripts.run_legacy_hf_eval.python_supports_local_adapter",
        lambda path: str(path).casefold().endswith("python312\\python.exe"),
    )

    selected = choose_python_for_eval()

    assert selected == Path(r"C:\Users\issda\Python312\python.exe")


def test_choose_python_raises_when_no_runtime_is_usable(monkeypatch):
    monkeypatch.setattr(
        "scripts.run_legacy_hf_eval.candidate_python_paths",
        lambda: [Path(r"C:\Python314\python.exe")],
    )
    monkeypatch.setattr(
        "scripts.run_legacy_hf_eval.python_supports_local_adapter",
        lambda path: False,
    )

    with pytest.raises(RuntimeError, match="No compatible Python runtime found"):
        choose_python_for_eval()


def test_main_dry_run_skips_subprocess(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.run_legacy_hf_eval.choose_python_for_eval",
        lambda preferred_python=None: Path(r"C:\Users\issda\Python312\python.exe"),
    )

    def _should_not_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called during dry-run")

    monkeypatch.setattr("scripts.run_legacy_hf_eval.subprocess.run", _should_not_run)

    exit_code = main(["--dry-run", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Resolved command:" in captured.out
    assert "--json" in captured.out
