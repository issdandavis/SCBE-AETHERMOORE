from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

REGIMEN_SCHEMA = REPO / "schemas" / "agent_endurance_regimen_v1.schema.json"
TASKSET_SCHEMA = REPO / "schemas" / "agent_endurance_taskset_v1.schema.json"
RUN_SCHEMA = REPO / "schemas" / "agent_endurance_run_report_v1.schema.json"

REGIMEN_EXAMPLE = REPO / "schemas" / "examples" / "agent_endurance_regimen_v1.example.json"
TASKSET_EXAMPLE = REPO / "schemas" / "examples" / "agent_endurance_taskset_v1.example.json"
RUN_EXAMPLE = REPO / "schemas" / "examples" / "agent_endurance_run_report_v1.example.json"

SPEC_DOC = REPO / "docs" / "specs" / "AGENT_ENDURANCE_TRAINING_REGIMEN_v1.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_artifacts_exist() -> None:
    for path in (
        REGIMEN_SCHEMA,
        TASKSET_SCHEMA,
        RUN_SCHEMA,
        REGIMEN_EXAMPLE,
        TASKSET_EXAMPLE,
        RUN_EXAMPLE,
        SPEC_DOC,
    ):
        assert path.exists(), f"missing artifact: {path}"


def test_schema_versions_are_locked() -> None:
    regimen = _load(REGIMEN_SCHEMA)
    taskset = _load(TASKSET_SCHEMA)
    run = _load(RUN_SCHEMA)
    assert regimen["properties"]["schema_version"]["const"] == "scbe_agent_endurance_regimen_v1"
    assert taskset["properties"]["schema_version"]["const"] == "scbe_agent_endurance_taskset_v1"
    assert run["properties"]["schema_version"]["const"] == "scbe_agent_endurance_run_report_v1"


def test_regimen_example_weights_sum_to_one() -> None:
    payload = _load(REGIMEN_EXAMPLE)
    weights = payload["score_weights"]
    total = (
        float(weights["correctness"])
        + float(weights["robustness"])
        + float(weights["efficiency"])
        + float(weights["process_quality"])
        + float(weights["safety"])
    )
    assert abs(total - 1.0) < 1e-9, f"weights must sum to 1.0, got {total}"


def test_taskset_example_task_ids_unique() -> None:
    payload = _load(TASKSET_EXAMPLE)
    ids = [row["task_id"] for row in payload["tasks"]]
    assert len(ids) == len(set(ids)), "task ids must be unique"


def test_run_example_threshold_consistency() -> None:
    payload = _load(RUN_EXAMPLE)
    total = float(payload["scores"]["total"])
    safety = float(payload["scores"]["safety"])
    min_total = float(payload["thresholds"]["minimum_total_score"])
    min_safety = float(payload["thresholds"]["minimum_safety_score"])
    assert total >= min_total
    assert safety >= min_safety
    assert payload["pass"] is True
