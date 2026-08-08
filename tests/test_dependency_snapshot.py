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
        "pillow": "12.3.0",
        "aiohttp": "3.14.3",
        "cryptography": "50.0.0",
        "pyasn1": "0.6.4",
        "soupsieve": "2.9.1",
        "mcp": "1.28.1",
        "bedrock-agentcore": "1.19.0",
    }
    for name, version in expected.items():
        assert resolved[name]["package_url"] == f"pkg:pypi/{name}@{version}"
        assert resolved[name]["relationship"] == "direct"

    assert len(resolved) >= 200
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
