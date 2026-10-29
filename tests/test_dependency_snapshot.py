from pathlib import Path

import pytest

from scripts.build_dependency_snapshot import build_snapshot, load_locked_dependencies

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_SHA = "a" * 40


def test_current_lock_submits_all_patched_security_floors() -> None:
    snapshot, skipped_vcs = build_snapshot(
        REPO_ROOT,
        sha=TEST_SHA,
        ref="refs/heads/main",
        job_id="test",
        scanned="2026-08-08T00:00:00Z",
    )
    resolved = snapshot["manifests"]["pyproject.toml"]["resolved"]

    expected = {
        "pillow": "13.0.0",
        "aiohttp": "3.14.4",
        "black": "26.10.1",
        "certifi": "2026.10.23",
        "cryptography": "50.0.0",
        "filelock": "4.2.1",
        "pyasn1": "0.6.4",
        "soupsieve": "2.9.1",
        "mcp": "1.30.0",
        "bedrock-agentcore": "1.19.0",
        "opentelemetry-api": "1.45.1",
        "pygments": "2.20.0",
        "strands-agents": "1.48.0",
        "urllib3": "2.8.0",
        "uv": "0.13.4",
        "virtualenv": "21.14.13",
    }
    for name, version in expected.items():
        assert resolved[name]["package_url"] == f"pkg:pypi/{name}@{version}"
        assert resolved[name]["relationship"] == "direct"

    assert len(resolved) >= 180
    assert len(skipped_vcs) == 2


def test_lock_parser_normalizes_names_and_rejects_ambiguous_entries(tmp_path: Path) -> None:
    valid_lock = tmp_path / "valid.txt"
    valid_lock.write_text("PyYAML==6.0.3\n-e git+https://example.test/repo.git#egg=demo\n", encoding="utf-8")

    locked, skipped_vcs = load_locked_dependencies(valid_lock)

    assert locked == {"pyyaml": "6.0.3"}
    assert len(skipped_vcs) == 1

    invalid_lock = tmp_path / "invalid.txt"
    invalid_lock.write_text("unpinned>=1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported lock entry"):
        load_locked_dependencies(invalid_lock)
