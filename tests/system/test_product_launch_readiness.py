from __future__ import annotations

import json

from scripts.system.product_launch_readiness import audit_launch, main


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_launch_readiness_accepts_complete_catalog(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    legal = docs / "legal"
    legal.mkdir(parents=True)
    (docs / "workflow-snapshot.html").write_text("proof", encoding="utf-8")
    (docs / "supporter.html").write_text("proof", encoding="utf-8")
    (legal / "privacy.html").write_text("privacy", encoding="utf-8")
    (legal / "terms.html").write_text("terms", encoding="utf-8")
    (docs / "robots.txt").write_text("User-agent: *", encoding="utf-8")
    (docs / "sitemap.xml").write_text("<urlset />", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("llms", encoding="utf-8")

    offers = {
        "schema": "aethermoore-offers-v1",
        "offers": [
            {
                "id": "starter",
                "name": "Starter",
                "price_label": "$29",
                "type": "service",
                "checkout_url": "https://buy.stripe.com/test",
                "proof_url": "https://aethermoore.com/SCBE-AETHERMOORE/workflow-snapshot.html",
                "status": "live",
            },
            {
                "id": "monthly",
                "name": "Monthly",
                "price_label": "$99/month",
                "type": "subscription",
                "checkout_url": "https://buy.stripe.com/monthly",
                "proof_url": "https://aethermoore.com/SCBE-AETHERMOORE/supporter.html",
                "status": "live",
            },
            {
                "id": "tip",
                "name": "Tip",
                "price_label": "$5",
                "type": "one_time",
                "checkout_url": "https://buy.stripe.com/tip",
                "proof_url": "https://aethermoore.com/SCBE-AETHERMOORE/supporter.html",
                "status": "live",
            },
        ],
    }
    app_config = {
        "endpoints": {
            "offers_json": "https://aethermoore.com/SCBE-AETHERMOORE/offers.json",
            "privacy_policy": "https://aethermoore.com/SCBE-AETHERMOORE/legal/privacy.html",
            "terms_of_service": "https://aethermoore.com/SCBE-AETHERMOORE/legal/terms.html",
            "workflow_snapshot_checkout": "https://buy.stripe.com/test",
        }
    }
    offers_path = docs / "offers.json"
    app_config_path = docs / "app-config.json"
    _write_json(offers_path, offers)
    _write_json(app_config_path, app_config)

    import scripts.system.product_launch_readiness as readiness

    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    report = audit_launch(offers_path, app_config_path)

    assert report["ready"] is True
    assert report["score"] == 10.0
    assert report["starter_offer_ids"] == ["starter", "tip"]


def test_launch_readiness_flags_missing_checkout(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    offers_path = docs / "offers.json"
    app_config_path = docs / "app-config.json"
    _write_json(
        offers_path,
        {
            "schema": "aethermoore-offers-v1",
            "offers": [
                {
                    "id": "broken",
                    "name": "Broken",
                    "price_label": "$29",
                    "type": "service",
                    "checkout_url": "",
                    "proof_url": "https://aethermoore.com/SCBE-AETHERMOORE/missing.html",
                    "status": "live",
                }
            ],
        },
    )
    _write_json(app_config_path, {"endpoints": {}})

    import scripts.system.product_launch_readiness as readiness

    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    report = audit_launch(offers_path, app_config_path)

    assert report["ready"] is False
    assert any(check["name"] == "offer:broken:checkout_url" for check in report["checks"] if not check["ok"])


def test_cli_writes_report(tmp_path, monkeypatch) -> None:
    offers_path = tmp_path / "offers.json"
    app_config_path = tmp_path / "app-config.json"
    _write_json(offers_path, {"schema": "aethermoore-offers-v1", "offers": []})
    _write_json(app_config_path, {"endpoints": {}})

    import scripts.system.product_launch_readiness as readiness

    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    exit_code = main(
        [
            "--offers",
            str(offers_path),
            "--app-config",
            str(app_config_path),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "out" / "product-launch-readiness.json").exists()
