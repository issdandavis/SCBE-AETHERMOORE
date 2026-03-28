from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "publish" / "post_all.py"
    spec = importlib.util.spec_from_file_location("post_all_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_post_all_campaign_posts_dry_run(tmp_path: Path, monkeypatch):
    module = _load_module()

    devto_file = tmp_path / "devto.md"
    hf_file = tmp_path / "hf.md"
    gh_file = tmp_path / "gh.md"
    medium_file = tmp_path / "medium.md"
    for path in (devto_file, hf_file, gh_file, medium_file):
        path.write_text("# Test\n\nBody", encoding="utf-8")

    manifest = {
        "posts": [
            {
                "id": "devto-post",
                "platform": "devto",
                "site": "devto",
                "title": "Devto test",
                "content_file": str(devto_file),
                "tags": ["ai", "governance"],
                "series": "SCBE Research Notes",
                "target": {},
            },
            {
                "id": "hf-post",
                "platform": "huggingface",
                "site": "huggingface_model",
                "title": "HF test",
                "content_file": str(hf_file),
                "target": {
                    "repo_id": "issdandavis/phdm-21d-embedding",
                    "repo_type": "model",
                },
            },
            {
                "id": "gh-post",
                "platform": "github",
                "site": "github",
                "title": "GH test",
                "content_file": str(gh_file),
                "target": {
                    "owner": "issdandavis",
                    "repo": "SCBE-AETHERMOORE",
                    "category": "General",
                },
            },
            {
                "id": "medium-post",
                "platform": "medium",
                "site": "medium",
                "title": "Medium test",
                "content_file": str(medium_file),
                "target": {},
            },
        ]
    }
    manifest_path = tmp_path / "campaign_posts.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(module, "EVIDENCE_DIR", tmp_path / "evidence")
    monkeypatch.setattr(
        module,
        "_run_devto_publish",
        lambda *args, **kwargs: ("dry_run_ready", "devto ok"),
    )
    monkeypatch.setattr(module, "_run_hf_publish", lambda *args, **kwargs: ("dry_run_ready", "hf ok"))
    monkeypatch.setattr(
        module,
        "_run_github_publish_file",
        lambda *args, **kwargs: ("dry_run_ready", "gh ok"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "post_all.py",
            "--dry-run",
            "--campaign-posts",
            str(manifest_path),
            "--only",
            "github,huggingface,devto,medium",
        ],
    )

    rc = module.main()
    assert rc == 0

    evidence_files = sorted((tmp_path / "evidence").glob("post_all_*.json"))
    assert evidence_files
    evidence = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    statuses = {row["site"]: row["status"] for row in evidence["statuses"]}
    assert statuses["devto"] == "dry_run_ready"
    assert statuses["huggingface_model"] == "dry_run_ready"
    assert statuses["github"] == "dry_run_ready"
    assert statuses["medium"] == "staged_manual"
