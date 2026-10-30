"""Use real Git histories to verify catalog boundaries and merge accounting."""

import importlib.util
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ops/change_catalog.py"
SPEC = importlib.util.spec_from_file_location("change_catalog", SCRIPT)
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)


def run(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def repo(tmp_path):
    run(tmp_path, "init", "-b", "main")
    run(tmp_path, "config", "user.name", "Catalog Test")
    run(tmp_path, "config", "user.email", "catalog@example.invalid")
    return tmp_path


def commit(repo, filename, text, message):
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    run(repo, "add", filename)
    run(repo, "commit", "-m", message)
    return run(repo, "rev-parse", "HEAD")


def test_exact_bounds_merge_accounting_and_determinism(repo):
    base = commit(repo, "README.md", "base", "base excluded")
    run(repo, "checkout", "-b", "feature")
    feature = commit(repo, "src/crypto/example.py", "feature", "feat: crypto")
    run(repo, "checkout", "main")
    direct = commit(repo, "docs/test.md", "direct", "docs: direct")
    run(repo, "merge", "--no-ff", "feature", "-m", "merge feature")
    head = run(repo, "rev-parse", "HEAD")
    result = catalog.build_catalog(repo, "owner/repo", base, head)
    assert result == catalog.build_catalog(repo, "owner/repo", base, head)
    assert result["commit_count"] == 3
    assert result["first_parent_landing_count"] == 2
    records = {entry["sha"]: entry for entry in result["commits"]}
    assert base not in records
    assert not records[feature]["mainline_landing"]
    assert records[direct]["mainline_landing"]
    assert records[head]["paths"] == ["src/crypto/example.py"]
    assert records[head]["areas"] == ["crypto"]
    assert records[head]["parents"] == [direct, feature]


def test_rejects_nonancestor_and_unsafe_revision(repo):
    base = commit(repo, "README.md", "base", "base")
    head = commit(repo, "README.md", "next", "next")
    with pytest.raises(ValueError):
        catalog.build_catalog(repo, "owner/repo", head, base)
    with pytest.raises(ValueError, match="full lowercase"):
        catalog.build_catalog(repo, "owner/repo", "--all", head)
    with pytest.raises(ValueError, match="owner/name"):
        catalog.build_catalog(repo, "owner/repo?bad", base, head)


def test_rejects_shallow_side_branch_inside_range(repo):
    base = commit(repo, "README.md", "base", "base")
    run(repo, "checkout", "-b", "feature")
    feature = commit(repo, "src/crypto/example.py", "feature", "feature")
    run(repo, "checkout", "main")
    commit(repo, "docs/test.md", "direct", "direct")
    run(repo, "merge", "--no-ff", "feature", "-m", "merge")
    head = run(repo, "rev-parse", "HEAD")
    (repo / ".git/shallow").write_text(feature + "\n")
    with pytest.raises(ValueError, match="shallow history boundary"):
        catalog.build_catalog(repo, "owner/repo", base, head)


def test_empty_range_and_markdown_safety(repo):
    base = commit(repo, "README.md", "base", "base")
    empty = catalog.build_catalog(repo, "owner/repo", base, base)
    assert empty["commit_count"] == 0
    head = commit(repo, "docs/file.md", "x", "docs: | <img> @person " + chr(96) + "x")
    rendered = catalog.render_markdown(catalog.build_catalog(repo, "owner/repo", base, head))
    assert "&#124;" in rendered
    assert "&lt;img&gt;" in rendered
    assert "&#64;person" in rendered
    assert "&#96;x" in rendered
    assert "<img>" not in rendered
