from __future__ import annotations

from scripts.system.run_core_python_checks import (
    OPTIONAL_TEST_IGNORES,
    build_pytest_command,
    summary_payload,
)


def test_build_pytest_command_includes_optional_ignores():
    command = build_pytest_command(("tests",), maxfail=2)

    assert command[1:4] == ["-m", "pytest", "-v"]
    assert "tests" in command
    assert "--ignore=tests/node_modules" in command
    assert "--maxfail=2" in command
    for ignored in OPTIONAL_TEST_IGNORES:
        assert f"--ignore={ignored}" in command


def test_summary_payload_records_repo_settings():
    command = build_pytest_command(("tests",), maxfail=1)
    payload = summary_payload(command)

    assert payload["command"] == command
    assert payload["env"]["SCBE_FORCE_SKIP_LIBOQS"] == "1"
    assert payload["optional_ignores"] == list(OPTIONAL_TEST_IGNORES)
