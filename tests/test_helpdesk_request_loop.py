from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "helpdesk_request_loop.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("helpdesk_request_loop", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_submit_evaluate_and_plan_ticket_without_source_edits(tmp_path: Path) -> None:
    module = _load_module()

    ticket = module.submit_ticket(
        title="Agentbus pipe should accept JSON events",
        body="Tester wants a Zapier style pipe.",
        kind="feature",
        root=tmp_path,
    )
    evaluation = module.evaluate_ticket(ticket, root=tmp_path)
    plan = module.build_fix_plan(ticket, evaluation, root=tmp_path)

    assert ticket["schema_version"] == "scbe-helpdesk-ticket-v1"
    assert evaluation["decision"] == "PLAN_FIX"
    assert "scripts/system/agentbus_pipe.mjs" in evaluation["impacted_paths"]
    assert plan["execution_policy"] == "plan_only_no_source_edits"
    assert Path(plan["path"]).exists()


def test_seed_demo_creates_tickets_evaluations_and_fix_plans(tmp_path: Path) -> None:
    module = _load_module()

    result = module.seed_demo(tmp_path)

    assert result["schema_version"] == "scbe-helpdesk-seed-result-v1"
    assert result["count"] == 3
    assert (tmp_path / "tickets.jsonl").exists()
    assert (tmp_path / "evaluations.jsonl").exists()
    assert len(list((tmp_path / "fix_plans").glob("*.json"))) == 3


def test_helpdesk_cli_submit_outputs_plan(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--root",
            str(tmp_path),
            "submit",
            "--kind",
            "bug",
            "--title",
            "Watcher missed latest mirror round",
            "--body",
            "Tester saw stale watcher state.",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ticket"]["kind"] == "bug"
    assert payload["evaluation"]["severity"] == "high"
    assert payload["plan"]["path"].endswith(".json")
