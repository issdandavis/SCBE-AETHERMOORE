from __future__ import annotations

import json
from pathlib import Path

from scripts.publish.play_store_readiness_gate import run_gate, write_report


def _write_valid_inputs(tmp_path: Path) -> dict[str, Path]:
    aab = tmp_path / "app-release.aab"
    aab.write_bytes(b"x" * 1_100_000)
    listing = tmp_path / "store-listing-aetherbrowse.md"
    listing.write_text(
        "\n".join(
            [
                "# Google Play / Amazon Listing - AetherBrowse",
                "## Short Description",
                "## Full Description",
                "## Privacy Policy URL",
                "https://example.test/privacy",
                "## Support URL",
                "https://example.test/support",
                "Suggested Package Name",
                "com.issdandavis.aetherbrowse",
                "Feature graphic",
                "Phone screenshots",
                "7-inch tablet",
                "10-inch tablet",
            ]
        ),
        encoding="utf-8",
    )
    privacy = tmp_path / "PRIVACY.md"
    privacy.write_text(
        "\n".join(
            [
                "# Privacy Policy",
                "## API Keys",
                "## Third-Party AI Providers",
                "## Local Storage",
                "## Data Deletion",
                "## Contact",
            ]
        ),
        encoding="utf-8",
    )
    build_gradle = tmp_path / "build.gradle"
    build_gradle.write_text(
        "\n".join(
            [
                'def appVariant = (System.getenv("AETHERCODE_APP_VARIANT") ?: "").toLowerCase()',
                'def nativeAppId = isAetherBrowse ? "com.issdandavis.aetherbrowse" : "com.issdandavis.aethercode"',
                "versionCode 2",
                'versionName "1.1.0"',
                "signingConfigs { release { } }",
            ]
        ),
        encoding="utf-8",
    )
    android_dir = tmp_path / "kindle-app" / "android"
    android_dir.mkdir(parents=True)
    (android_dir / ".gitignore").write_text("*.jks\n*.keystore\nsigning.local.properties\n", encoding="utf-8")
    return {"aab": aab, "listing": listing, "privacy": privacy, "build_gradle": build_gradle}


def test_play_store_gate_passes_complete_local_release_packet(tmp_path: Path, monkeypatch) -> None:
    paths = _write_valid_inputs(tmp_path)
    import scripts.publish.play_store_readiness_gate as gate

    monkeypatch.setattr(gate, "REPO", tmp_path)

    report = run_gate(**paths)

    assert report["decision"] == "PASS"
    assert report["counts"]["PASS"] == 5
    artifact = next(row for row in report["findings"] if row["gate"] == "artifact")
    assert artifact["evidence"]["bytes"] == 1_100_000
    assert len(artifact["evidence"]["sha256"]) == 64


def test_play_store_gate_holds_for_missing_screenshots(tmp_path: Path, monkeypatch) -> None:
    paths = _write_valid_inputs(tmp_path)
    import scripts.publish.play_store_readiness_gate as gate

    monkeypatch.setattr(gate, "REPO", tmp_path)
    paths["listing"].write_text(
        "Privacy Policy URL\nSupport URL\nShort Description\nFull Description\ncom.issdandavis.aetherbrowse\n",
        encoding="utf-8",
    )

    report = run_gate(**paths)

    assert report["decision"] == "HOLD"
    listing = next(row for row in report["findings"] if row["gate"] == "listing")
    assert listing["decision"] == "HOLD"
    assert "Feature graphic" in listing["evidence"]["missing_asset_markers"]


def test_play_store_gate_writes_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    paths = _write_valid_inputs(tmp_path)
    import scripts.publish.play_store_readiness_gate as gate

    monkeypatch.setattr(gate, "REPO", tmp_path)
    report = run_gate(**paths)
    out = tmp_path / "latest.json"
    md = tmp_path / "latest.md"

    write_report(report, out, md)

    assert json.loads(out.read_text(encoding="utf-8"))["decision"] == "PASS"
    assert "Play Store Readiness Gate" in md.read_text(encoding="utf-8")
