import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "src" / "longform" / "longform_cli.py"


def _run(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=workspace,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
    )


def _ledger_events(workspace: Path) -> list[dict]:
    ledger = workspace / ".scbe-longform" / "ledger.jsonl"
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_do_squad_dispatches_each_stage_through_agent_bus(tmp_path):
    result = _run(
        tmp_path,
        "do",
        "prove the longform squad dispatch lane",
        "--loops",
        "1",
        "--land-every-stage",
        "--squad",
        "--dispatch-provider",
        "offline",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["kind"] == "do_complete"

    events = _ledger_events(tmp_path)
    dispatches = [event for event in events if event["kind"] == "agentbus_dispatch"]
    stages = [event for event in events if event["kind"] == "stage_complete"]

    assert len(dispatches) == 1
    assert dispatches[0]["payload"]["status"] == "dispatched"
    assert dispatches[0]["payload"]["dispatch"]["enabled"] is True
    assert dispatches[0]["payload"]["dispatch"]["provider"] == "offline"
    assert len(stages) == 1
    assert stages[0]["payload"]["status"] == "dispatched"
    assert stages[0]["payload"]["dispatch_enabled"] is True
