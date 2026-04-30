from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "system" / "collect_sam_coding_opportunities.py"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_sam_coding_opportunities", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_plan_redacts_api_key():
    module = load_module()
    args = Namespace(
        endpoint="https://api.sam.gov/prod/opportunities/v2/search",
        keyword=["software development"],
        posted_from="04/01/2026",
        posted_to="04/30/2026",
        days=30,
        limit=10,
        ptype="o",
        execute=False,
    )

    plan = module.build_plan(args, "secret-key")

    assert plan["api_key_present"] is True
    assert plan["queries"][0]["params"]["api_key"] == "<redacted>"
    assert plan["queries"][0]["params"]["q"] == "software development"


def test_normalize_opportunities_metadata_only():
    module = load_module()
    payload = {
        "opportunitiesData": [
            {
                "noticeId": "N1",
                "title": "Software development support",
                "fullParentPathName": "Agency",
                "postedDate": "04/29/2026",
                "responseDeadLine": "05/10/2026",
                "type": "Solicitation",
                "naicsCode": "541511",
                "classificationCode": "DA10",
                "uiLink": "https://sam.gov/opp/N1/view",
            }
        ]
    }

    rows = module.normalize_opportunities(payload, keyword="software")

    assert rows == [
        {
            "notice_id": "N1",
            "title": "Software development support",
            "agency": "Agency",
            "posted_date": "04/29/2026",
            "response_deadline": "05/10/2026",
            "type": "Solicitation",
            "naics": "541511",
            "classification_code": "DA10",
            "ui_link": "https://sam.gov/opp/N1/view",
            "keyword": "software",
            "training_use": "metadata_to_task_shape_only",
        }
    ]


def test_dry_run_cli_does_not_require_key(monkeypatch):
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.delenv("SAM_GOV_API_KEY", raising=False)

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/collect_sam_coding_opportunities.py",
            "--keyword",
            "software development",
            "--posted-from",
            "04/01/2026",
            "--posted-to",
            "04/30/2026",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["dry_run"] is True
    assert payload["plan"]["api_key_present"] is False
