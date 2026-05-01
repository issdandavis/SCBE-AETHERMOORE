from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module():
    import importlib.util

    path = REPO_ROOT / "scripts" / "benchmark" / "cli_quest_wrapper.py"
    spec = importlib.util.spec_from_file_location("_cli_quest_wrapper_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sample_manifest_validates() -> None:
    module = load_module()
    quests = module.load_manifest(REPO_ROOT / "config" / "eval" / "cli_quest_tasks.sample.json")
    validation = module.validate_quests(quests)
    assert validation["ok"], validation
    assert {quest.source for quest in quests} == {"bashcrawl", "clmystery", "terminus"}


def test_prepare_quest_copies_workspace_and_writes_training_record(tmp_path: Path) -> None:
    source = tmp_path / "source_quest"
    entrance = source / "entrance"
    entrance.mkdir(parents=True)
    (entrance / "scroll").write_text("Use ls, cat, and grep to find the gem.\n", encoding="utf-8")
    (entrance / "room.txt").write_text("gem: sapphire\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "scbe_cli_quest_manifest_v1",
                "quests": [
                    {
                        "quest_id": "fixture-bashcrawl",
                        "source": "bashcrawl",
                        "title": "Fixture Bashcrawl",
                        "local_path": str(source),
                        "start_path": "entrance",
                        "instructions_file": "scroll",
                        "objective": "Find the gem.",
                        "success_markers": ["gem found"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    module = load_module()
    quest = module.load_manifest(manifest)[0]
    result = module.prepare_quest(quest, tmp_path / "runs")
    assert result["ok"] is True
    run_dir = Path(result["run_dir"])
    assert (run_dir / "quest_packet.json").exists()
    training = json.loads((run_dir / "training_record.json").read_text(encoding="utf-8"))
    assert training["category"] == "agentic-cli-quest"
    assert training["routing"]["recommended_role_pair"] == ["Navigator", "Verifier"]
    assert Path(result["start_path"]).name == "entrance"


def test_prepare_missing_source_reports_fetch_instruction(tmp_path: Path) -> None:
    module = load_module()
    quest = module.CliQuest(
        quest_id="missing",
        source="clmystery",
        title="Missing",
        local_path=str(tmp_path / "missing"),
        start_path=".",
        objective="Solve it.",
        instructions_file="step0",
        success_markers=["answer"],
        allowed_commands=["ls"],
        sandbox="copy",
        max_steps=3,
        repo_url="https://github.com/veltman/clmystery",
        license="unknown",
    )
    result = module.prepare_quest(quest, tmp_path / "runs")
    assert result["ok"] is False
    assert result["status"] == "missing_source"
    assert "clone or export" in result["recommended_fetch"]


def test_cli_validate_subcommand() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark/cli_quest_wrapper.py", "validate"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
