"""Tests for src.training_cli — fully isolated against tmp_path repo roots."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.training_cli.cli import build_parser, main
from src.training_cli.heartbeat import HEARTBEAT_REL, read_heartbeat
from src.training_cli.quickstart import (
    plan_quickstart,
    plan_quickstart_with_council,
    supported_trainers,
)
from src.training_cli.runs import list_runs
from src.training_cli.status import collect_status
from src.training_cli.verdicts import load_verdicts, parse_verdict_file
from src.training_cli import guides as guides_module

# ----------------------------- helpers -----------------------------


def _write_verdict(
    repo_root: Path, run_name: str, job_id: str, *, overall_pass: bool, scaffold: bool, pass_rate: float = 1.0
) -> Path:
    eval_dir = repo_root / "training" / "runs" / run_name / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    path = eval_dir / f"{job_id}_verdict.json"
    payload = {
        "job_id": job_id,
        "report": {
            "schema": "scbe_stage6_regression_report_v1",
            "generated_utc": "2026-05-05T02:11:09.529007+00:00",
            "adapter": "/tmp/adapter",
            "base_model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "n_total": 5,
            "n_pass": int(round(pass_rate * 5)),
            "pass_rate": pass_rate,
            "minimum_pass_rate": 0.8,
            "must_pass_results": {"a": True, "b": True, "c": True},
            "must_pass_all_ok": overall_pass,
            "overall_pass": overall_pass,
            "constrained_gate_scaffold": scaffold,
            "results": [],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_heartbeat(repo_root: Path, line: str) -> Path:
    path = repo_root / HEARTBEAT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(line, encoding="ascii")
    return path


# ----------------------------- verdict parsing -----------------------------


def test_parse_verdict_file_returns_structured_data(tmp_path: Path) -> None:
    path = _write_verdict(tmp_path, "run-a", "job-1", overall_pass=True, scaffold=False, pass_rate=1.0)
    v = parse_verdict_file(path)
    assert v is not None
    assert v.run_name == "run-a"
    assert v.job_id == "job-1"
    assert v.overall_pass is True
    assert v.scaffold is False
    assert v.pass_rate == 1.0
    assert v.status == "PASS"


def test_parse_verdict_file_returns_none_on_garbage(tmp_path: Path) -> None:
    path = tmp_path / "junk.json"
    path.write_text("not json", encoding="utf-8")
    assert parse_verdict_file(path) is None


def test_load_verdicts_returns_newest_first(tmp_path: Path) -> None:
    p1 = _write_verdict(tmp_path, "run-a", "job-old", overall_pass=True, scaffold=True)
    p2 = _write_verdict(tmp_path, "run-a", "job-new", overall_pass=False, scaffold=False)
    # Force mtime ordering
    import os
    import time

    os.utime(p1, (time.time() - 10, time.time() - 10))
    runs_root = tmp_path / "training" / "runs"
    verdicts = load_verdicts(runs_root)
    assert [v.job_id for v in verdicts] == ["job-new", "job-old"]


def test_load_verdicts_empty_when_no_runs(tmp_path: Path) -> None:
    assert load_verdicts(tmp_path / "training" / "runs") == []


# ----------------------------- runs listing -----------------------------


def test_list_runs_returns_runs_with_eval_metadata(tmp_path: Path) -> None:
    _write_verdict(tmp_path, "run-a", "job-1", overall_pass=True, scaffold=False)
    _write_verdict(tmp_path, "run-a", "job-2", overall_pass=False, scaffold=True)
    (tmp_path / "training" / "runs" / "run-b").mkdir(parents=True, exist_ok=True)

    runs = list_runs(tmp_path / "training" / "runs")
    by_name = {r.name: r for r in runs}
    assert "run-a" in by_name
    assert "run-b" in by_name
    assert by_name["run-a"].verdict_count == 2
    assert by_name["run-a"].has_eval is True
    assert by_name["run-b"].verdict_count == 0
    assert by_name["run-b"].has_eval is False


def test_list_runs_empty_when_root_missing(tmp_path: Path) -> None:
    assert list_runs(tmp_path / "nonexistent") == []


# ----------------------------- heartbeat -----------------------------


def test_read_heartbeat_counts_chars(tmp_path: Path) -> None:
    _write_heartbeat(tmp_path, ".....x...x..?...")
    hb = read_heartbeat(tmp_path)
    assert hb.exists is True
    assert hb.length == 16
    assert hb.success_count == 13  # ..... + ... + .. + ... = 13 dots
    assert hb.fail_count == 2
    assert hb.error_count == 1
    assert hb.health in {"degraded", "mostly_green"}


def test_read_heartbeat_no_file_returns_no_data(tmp_path: Path) -> None:
    hb = read_heartbeat(tmp_path)
    assert hb.exists is False
    assert hb.health == "no_data"
    assert hb.length == 0


def test_read_heartbeat_all_dots_is_all_green(tmp_path: Path) -> None:
    _write_heartbeat(tmp_path, "." * 50)
    hb = read_heartbeat(tmp_path)
    assert hb.health == "all_green"


# ----------------------------- status aggregation -----------------------------


def test_collect_status_combines_all_sources(tmp_path: Path) -> None:
    _write_verdict(tmp_path, "run-a", "job-1", overall_pass=True, scaffold=True, pass_rate=1.0)
    _write_heartbeat(tmp_path, "..x.")
    status = collect_status(tmp_path)
    assert len(status.runs) == 1
    assert len(status.recent_verdicts) == 1
    assert status.heartbeat.exists is True
    assert status.latest_status == "PASS"
    assert status.latest_pass_rate == 1.0
    assert "run-a" in status.to_dict()["runs"][0]["name"]


# ----------------------------- guides -----------------------------


def test_guide_list_topics_has_canonical_set() -> None:
    topics = set(guides_module.list_topics())
    expected = {"sft", "dpo", "lora", "merge", "datasets", "hf-jobs", "kaggle", "scbe-stack"}
    assert expected.issubset(topics)


def test_guide_read_returns_body_for_known_topic() -> None:
    body = guides_module.read_guide("sft")
    assert body is not None
    assert "Supervised Fine-Tuning" in body


def test_guide_read_returns_none_for_unknown_topic() -> None:
    assert guides_module.read_guide("totally-not-a-topic") is None


# ----------------------------- quickstart -----------------------------


def test_quickstart_supported_trainers_includes_sft_dpo_merge() -> None:
    trainers = supported_trainers()
    assert "sft" in trainers
    assert "dpo" in trainers
    assert "merge" in trainers


def test_quickstart_plan_emits_dispatch_command(tmp_path: Path) -> None:
    plan = plan_quickstart(
        base_model="Qwen/Qwen2.5-Coder-0.5B-Instruct",
        dataset_path="training-data/sft/foo.jsonl",
        run_name="test-run",
        trainer="dpo",
        repo_root=tmp_path,
    )
    assert plan.command[0] == "python"
    assert plan.command[1].endswith("dispatch_coding_agent_dpo_hf_job.py")
    assert "--run-name" in plan.command
    assert "test-run" in plan.command
    assert any("does not exist" in n or "warning" in n.lower() for n in plan.notes)


def test_quickstart_plan_falls_back_to_sft_for_unknown_trainer(tmp_path: Path) -> None:
    plan = plan_quickstart(
        base_model="bm",
        dataset_path="dp",
        run_name="rn",
        trainer="not-a-trainer",
        repo_root=tmp_path,
    )
    assert any("unknown trainer" in n for n in plan.notes)
    assert plan.command[1].endswith("dispatch_coding_agent_hf_job.py")


# ----------------------------- argparse / cli wiring -----------------------------


def test_build_parser_lists_all_subcommands() -> None:
    parser = build_parser()
    sub_action = next(
        a for a in parser._actions if isinstance(a, type(parser._actions[-1])) and getattr(a, "choices", None)
    )
    expected = {"status", "runs", "verdicts", "heartbeat", "guide", "quickstart"}
    assert expected.issubset(set(sub_action.choices))


def test_cli_status_runs_against_isolated_repo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_verdict(tmp_path, "run-a", "job-1", overall_pass=True, scaffold=False, pass_rate=1.0)
    _write_heartbeat(tmp_path, "...")
    rc = main(["--repo-root", str(tmp_path), "status", "--json"])
    assert rc == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["latest_status"] == "PASS"
    assert payload["latest_pass_rate"] == 1.0


def test_cli_guide_unknown_topic_returns_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--repo-root", str(tmp_path), "guide", "definitely-not-a-topic"])
    assert rc == 1


def test_cli_guide_known_topic_prints_body(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["guide", "sft"])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "Supervised Fine-Tuning" in captured


def test_cli_quickstart_emits_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(
        [
            "--repo-root",
            str(tmp_path),
            "quickstart",
            "--run-name",
            "test",
            "--base-model",
            "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "--data",
            "training-data/x.jsonl",
            "--trainer",
            "dpo",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["trainer"] == "dpo"
    assert payload["command"][0] == "python"
    assert "dispatch_coding_agent_dpo_hf_job.py" in payload["command_str"]


# ----------------------------- council quickstart -----------------------------


def _fake_solved_dispatch(*, task: str, budget_cents: float, metadata=None) -> dict:
    return {
        "schema_version": "scbe_tiered_council_dispatch_v1",
        "council_schema_version": "scbe_tiered_council_v1",
        "solved": True,
        "final_tier": 0,
        "final_answer": "- Trainer choice looks correct.\n- Dataset name matches DPO shape.\n- Verify scaffold flag before dispatch.",
        "total_cents": 0.0,
        "budget_cents": budget_cents,
        "rubric_threshold": 0.7,
        "escalation_path": ["tier0:score=1.00:passed=True:cents=0.0000"],
        "attempts": [],
        "note": "rubric_passed_at_tier_0",
        "metadata": dict(metadata or {}),
    }


def _fake_unsolved_dispatch(*, task: str, budget_cents: float, metadata=None) -> dict:
    return {
        "schema_version": "scbe_tiered_council_dispatch_v1",
        "council_schema_version": "scbe_tiered_council_v1",
        "solved": False,
        "final_tier": None,
        "final_answer": "",
        "total_cents": 0.0,
        "budget_cents": budget_cents,
        "rubric_threshold": 0.7,
        "escalation_path": ["tier0:no_providers", "tier1:no_providers"],
        "attempts": [],
        "note": "rubric_never_passed_or_no_tier_available",
        "metadata": dict(metadata or {}),
    }


def test_plan_quickstart_with_council_appends_advisory_notes_on_solved(tmp_path: Path) -> None:
    plan = plan_quickstart_with_council(
        base_model="Qwen/Qwen2.5-Coder-0.5B-Instruct",
        dataset_path="training-data/dpo/foo.jsonl",
        run_name="rn",
        trainer="dpo",
        repo_root=tmp_path,
        dispatch_fn=_fake_solved_dispatch,
    )
    joined = "\n".join(plan.notes)
    assert "council advisory" in joined
    assert "Trainer choice looks correct" in joined
    assert "Verify scaffold flag" in joined
    # deterministic command must remain unmutated by the council
    assert plan.command[1].endswith("dispatch_coding_agent_dpo_hf_job.py")


def test_plan_quickstart_with_council_handles_unsolved(tmp_path: Path) -> None:
    plan = plan_quickstart_with_council(
        base_model="bm",
        dataset_path="dp",
        run_name="rn",
        trainer="sft",
        repo_root=tmp_path,
        dispatch_fn=_fake_unsolved_dispatch,
    )
    joined = "\n".join(plan.notes)
    assert "did not converge" in joined
    assert "escalation:" in joined


def test_plan_quickstart_with_council_swallows_dispatch_exceptions(tmp_path: Path) -> None:
    def _raises(**kwargs):
        raise RuntimeError("boom")

    plan = plan_quickstart_with_council(
        base_model="bm",
        dataset_path="dp",
        run_name="rn",
        trainer="sft",
        repo_root=tmp_path,
        dispatch_fn=_raises,
    )
    joined = "\n".join(plan.notes)
    assert "council unavailable" in joined
    assert "RuntimeError" in joined
    # plan still has a valid dispatch command
    assert plan.command[0] == "python"


def test_plan_quickstart_with_council_passes_budget_and_metadata(tmp_path: Path) -> None:
    captured: dict = {}

    def _capture(*, task: str, budget_cents: float, metadata=None) -> dict:
        captured["task"] = task
        captured["budget_cents"] = budget_cents
        captured["metadata"] = dict(metadata or {})
        return _fake_solved_dispatch(task=task, budget_cents=budget_cents, metadata=metadata)

    plan_quickstart_with_council(
        base_model="bm",
        dataset_path="dp",
        run_name="rn-special",
        trainer="merge",
        repo_root=tmp_path,
        budget_cents=2.5,
        dispatch_fn=_capture,
    )
    assert captured["budget_cents"] == 2.5
    assert captured["metadata"]["run_name"] == "rn-special"
    assert captured["metadata"]["trainer"] == "merge"
    assert "merge: merge multiple LoRA adapters" in captured["task"]


def test_cli_quickstart_council_flag_routes_through_council(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.training_cli.cli.plan_quickstart_with_council",
        lambda **kwargs: plan_quickstart_with_council(dispatch_fn=_fake_solved_dispatch, **kwargs),
    )
    rc = main(
        [
            "--repo-root",
            str(tmp_path),
            "quickstart",
            "--run-name",
            "council-test",
            "--base-model",
            "bm",
            "--data",
            "training-data/x.jsonl",
            "--trainer",
            "dpo",
            "--council",
            "--council-budget-cents",
            "1.0",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    notes_joined = "\n".join(payload["notes"])
    assert "council advisory" in notes_joined
    assert "Trainer choice looks correct" in notes_joined
