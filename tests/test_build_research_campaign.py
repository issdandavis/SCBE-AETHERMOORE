from __future__ import annotations

import json
from pathlib import Path

from scripts.publish import build_research_campaign as module


def test_build_campaign_default_outputs(tmp_path: Path):
    artifact_root = tmp_path / "artifacts"
    platform_root = tmp_path / "platforms"
    note_path = tmp_path / "notes" / "campaign.md"

    result = module.build_campaign(
        campaign_id="unit-campaign",
        artifact_root=artifact_root,
        platform_root=platform_root,
        note_path=note_path,
    )

    assert result["article_count"] == 3
    assert result["platform_count"] >= 6
    assert result["claim_gate_pass"] is True
    assert note_path.exists()

    manifest = json.loads((artifact_root / "unit-campaign" / "campaign_manifest.json").read_text(encoding="utf-8"))
    posts = json.loads((artifact_root / "unit-campaign" / "campaign_posts.json").read_text(encoding="utf-8"))
    claim_report = json.loads((artifact_root / "unit-campaign" / "claim_gate_report.json").read_text(encoding="utf-8"))

    assert manifest["article_count"] == 3
    assert len(manifest["platforms"]) >= 6
    assert len(posts["posts"]) >= 18
    assert claim_report["summary"]["pass"] is True

