"""The evidence lane works from a checkout without a profile-installed skill."""

from pathlib import Path

import pytest

from scripts.system import octoarms_dispatch as dispatch


@pytest.mark.parametrize("bundled,profile", [(True, False), (True, True), (False, True), (False, False)])
def test_evidence_browser_dependency_selection(tmp_path, monkeypatch, bundled, profile):
    repo = tmp_path / "repo"
    home = tmp_path / "profile"
    bundle_path = repo / "scripts/hydra/hydra_terminal_browse.mjs"
    profile_path = home / ".codex/skills/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs"
    repo.mkdir()
    for present, path in ((bundled, bundle_path), (profile, profile_path)):
        if present:
            path.parent.mkdir(parents=True)
            path.write_text("// selection fixture; never executed\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    calls = []

    def capture(command, cwd):
        calls.append((command, cwd))
        return {"returncode": 0}

    monkeypatch.setattr(dispatch, "_run", capture)
    url = "https://example.invalid/fixture"
    result = dispatch._browse_evidence_run(repo, url, repo / "evidence.json")
    if bundled or profile:
        selected = bundle_path if bundled else profile_path
        assert result["returncode"] == 0
        assert calls == [(["node", str(selected), "--url", url, "--out", "evidence.json"], repo)]
    else:
        assert result["returncode"] == 2
        assert calls == []
        assert str(bundle_path) in result["stderr"] and str(profile_path) in result["stderr"]
