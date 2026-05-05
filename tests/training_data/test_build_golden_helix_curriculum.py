from __future__ import annotations

import json
from pathlib import Path

from scripts.training_data.build_golden_helix_curriculum import (
    DEFAULT_LANES,
    GOLDEN_ANGLE_DEG,
    golden_target_lane,
    load_candidates,
    schedule_candidates,
    write_outputs,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_golden_target_lane_uses_non_repeating_angle() -> None:
    lane0, angle0, radius0 = golden_target_lane(0, DEFAULT_LANES)
    lane1, angle1, radius1 = golden_target_lane(1, DEFAULT_LANES)

    assert lane0 == DEFAULT_LANES[0]
    assert angle0 == 0.0
    assert abs(angle1 - GOLDEN_ANGLE_DEG) < 1e-6
    assert radius0 == 1.0
    assert radius1 > 1.0
    assert lane1 != lane0


def test_load_candidates_classifies_existing_row_shapes(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "training-data" / "sample.jsonl",
        [
            {"source": "docs/CODING_SYSTEMS_MASTER_REFERENCE.md", "text": "python repair"},
            {"smiles": "CCO", "tags": ["organic"], "manual_valence_check": "ok"},
            {"source": "docs/MOTION_ASSEMBLY_SCHEMA.md", "motion_assembly": {"role": "dynamics"}},
            {"source": "docs/SS1_TOKENIZER_PROTOCOL.md", "binary": "01000001"},
        ],
    )

    candidates = load_candidates(tmp_path, ("training-data/*.jsonl",), DEFAULT_LANES)
    lanes = {candidate.primary_lane for candidate in candidates}

    assert {"coding", "chemistry", "motion", "tokenizer"}.issubset(lanes)
    assert all(candidate.row_sha256 for candidate in candidates)
    assert all(candidate.bond_lanes for candidate in candidates)


def test_schedule_candidates_adds_neighbor_bonds_and_metadata(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "training-data" / "sample.jsonl",
        [
            {"source": "docs/CODING_SYSTEMS_MASTER_REFERENCE.md", "text": "python repair"},
            {"smiles": "CCO", "tags": ["organic"], "manual_valence_check": "ok"},
            {"source": "docs/DARPA_MATHBAC/evidence.md", "text": "research source"},
            {"source": "docs/GEOS EAL_ACCESS_CONTROL.md", "tags": ["governance"]},
        ],
    )
    candidates = load_candidates(tmp_path, ("training-data/*.jsonl",), DEFAULT_LANES)
    schedule = schedule_candidates(candidates, DEFAULT_LANES)

    assert [row["curriculum_index"] for row in schedule] == list(range(len(schedule)))
    assert schedule[0]["previous_row_sha256"] == ""
    assert schedule[0]["next_row_sha256"] == schedule[1]["row_sha256"]
    assert schedule[-1]["previous_row_sha256"] == schedule[-2]["row_sha256"]
    assert schedule[-1]["next_row_sha256"] == ""
    assert all("helix_angle_deg" in row for row in schedule)
    assert all("target_lane" in row for row in schedule)


def test_write_outputs_creates_manifest_schedule_and_readme(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "training-data" / "sample.jsonl",
        [
            {"source": "docs/CODING_SYSTEMS_MASTER_REFERENCE.md", "text": "python repair"},
            {"smiles": "CCO", "tags": ["organic"], "manual_valence_check": "ok"},
        ],
    )
    candidates = load_candidates(tmp_path, ("training-data/*.jsonl",), DEFAULT_LANES)
    schedule = schedule_candidates(candidates, DEFAULT_LANES)
    manifest = write_outputs(tmp_path / "out", schedule, DEFAULT_LANES, ("training-data/*.jsonl",))

    assert manifest["schema_version"] == "scbe_golden_helix_curriculum_v1"
    assert manifest["row_count"] == 2
    assert (tmp_path / "out" / "schedule.jsonl").exists()
    assert (tmp_path / "out" / "manifest.json").exists()
    assert (tmp_path / "out" / "README.md").exists()
