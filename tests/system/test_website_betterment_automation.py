from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "system" / "website_betterment_automation.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_website_betterment_automation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_issue_needed_when_score_below_threshold() -> None:
    module = _load_module()
    summary = {
        "sales_audit": {"metrics": {"overall": 6.9}, "risks": []},
        "remote_app_config_smoke": {"ok": True},
    }
    assert module.issue_needed(summary, min_score=7.0) is True


def test_issue_not_needed_when_score_clean_and_smoke_ok() -> None:
    module = _load_module()
    summary = {
        "sales_audit": {"metrics": {"overall": 8.0}, "risks": []},
        "remote_app_config_smoke": {"ok": True},
    }
    assert module.issue_needed(summary, min_score=7.0) is False


def test_issue_body_contains_bounded_actions() -> None:
    module = _load_module()
    summary = {
        "created_at_utc": "2026-05-12T00:00:00Z",
        "summary_path": "artifacts/marketing/website_betterment_automation/summary.json",
        "sales_audit": {
            "page": "docs/index.html",
            "artifact_dir": "artifacts/marketing/website_betterment_automation/sales_audit",
            "metrics": {"overall": 6.5},
            "risks": ["No primary CTA found."],
            "backlog": [
                {
                    "page_slug": "proof/red-team-summary.html",
                    "reason": "Summarize proof surface in plain buyer language.",
                }
            ],
        },
        "remote_app_config_smoke": {
            "ok": False,
            "failure_count": 1,
            "failures": [{"name": "local:offers:schema", "detail": "bad schema"}],
        },
    }
    body = module.build_issue_body(summary, min_score=7.0)
    assert "Website Betterment Automation" in body
    assert "proof/red-team-summary.html" in body
    assert "local:offers:schema" in body
