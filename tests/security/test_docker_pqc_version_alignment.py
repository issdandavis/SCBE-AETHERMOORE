"""Keep the Cloud Build native/Python liboqs layers on one release."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_docker_liboqs_matches_python_requirement() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    python_match = re.search(r"(?m)^liboqs-python==(?P<version>\d+\.\d+\.\d+)$", requirements)
    native_match = re.search(r"liboqs/archive/refs/tags/(?P<version>\d+\.\d+\.\d+)\.tar\.gz", dockerfile)

    assert python_match is not None, "requirements.txt must pin liboqs-python"
    assert native_match is not None, "Dockerfile must pin the native liboqs source release"
    assert native_match.group("version") == python_match.group("version")
    assert dockerfile.count("pip install --no-cache-dir liboqs-python") == 0
