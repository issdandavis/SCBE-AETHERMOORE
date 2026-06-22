from __future__ import annotations

from pathlib import Path

from scripts.system import release_surface_audit


def test_release_surface_contract_is_current():
    report = release_surface_audit.audit()
    assert report["ok"], report
    ids = {surface["id"] for surface in report["surfaces"]}
    assert {
        "scbe_npm_sdk",
        "scbe_python_package",
        "buyer_product_zips",
        "workcell_download",
        "black_box_download",
        "docs_site",
        "training_eval",
    }.issubset(ids)


def test_release_surface_audit_catches_missing_npm_script(tmp_path: Path, monkeypatch):
    config = tmp_path / "release_surfaces.v1.json"
    config.write_text(
        """
{
  "schema": "scbe_release_surfaces_v1",
  "surfaces": [
    {
      "id": "bad",
      "repo": "SCBE-AETHERMOORE",
      "status": "ship",
      "role": "bad fixture",
      "owner_files": ["package.json"],
      "required_paths": [],
      "workflows": [],
      "build_commands": ["npm run definitely:missing"],
      "verification_commands": []
    }
  ]
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(release_surface_audit, "REPO_ROOT", Path.cwd())
    report = release_surface_audit.audit(config)
    assert not report["ok"]
    assert any("definitely:missing" in error for error in report["errors"])
