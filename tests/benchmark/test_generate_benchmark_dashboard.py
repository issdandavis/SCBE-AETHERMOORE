from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark.generate_benchmark_dashboard import (
    Lane,
    build_lanes,
    render_dashboard,
)


def _write_json(root: Path, rel_path: str, payload: dict) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_lanes_reads_current_artifact_shapes(tmp_path: Path) -> None:
    _write_json(
        tmp_path,
        "artifacts/benchmarks/tb-neutral-compare/tb_neutral_final_report.json",
        {
            "scbe": {"passed": 13, "failed": 0, "total": 13},
            "oracle": {"passed": 13, "failed": 0, "total": 13},
        },
    )
    _write_json(
        tmp_path,
        "artifacts/benchmarks/tb-neutral-compare/20260531T202914Z/scbe/2026-05-31__13-33-00/results.json",
        {
            "results": [
                {"task_id": "crack-7z-hash", "is_resolved": True},
                {
                    "task_id": "decommissioning-service-with-sensitive-data",
                    "is_resolved": True,
                },
            ]
        },
    )
    _write_json(
        tmp_path,
        "artifacts/benchmarks/longform_chain_integrity_latest.json",
        {"score": {"earned": 105, "max": 105}},
    )
    _write_json(
        tmp_path,
        "artifacts/benchmarks/hydra_jobsite_conservation/latest_report.json",
        {
            "summary": {
                "decision": "PASS",
                "hydra_passed": 6,
                "case_count": 6,
                "hydra_average_conservation_score": 1.0,
            }
        },
    )
    _write_json(
        tmp_path,
        "artifacts/benchmarks/scbe_full_system/latest_report.json",
        {
            "summary": {
                "decision": "EVIDENCE_PACKET_READY",
                "artifact_ready": 15,
                "passed": 11,
                "partial": 2,
            }
        },
    )
    petri_path = tmp_path / "docs/external/PETRI_FINDINGS_2026_05_08.md"
    petri_path.parent.mkdir(parents=True, exist_ok=True)
    petri_path.write_text(
        "| false-allows | 1 / 173 | 2 / 173 |\n",
        encoding="utf-8",
    )

    lanes = build_lanes(tmp_path)

    assert lanes[0].score == "SCBE 13/13; oracle 13/13"
    assert lanes[1].score == "SCBE 2/2"
    assert lanes[3].score == "2/173 false-allows (1.16%) in v7-matched run"
    assert lanes[4].score == "105/105"
    assert lanes[5].score == "6/6; conservation 1.0"
    assert lanes[6].score == "15 artifact-ready lanes; 11 pass; 2 partial"


def test_render_dashboard_escapes_artifact_text() -> None:
    html = render_dashboard(
        [
            Lane(
                "Terminal-Bench core neutral parity",
                "PASS",
                "SCBE 13/13; oracle 13/13",
                "a.json",
                "boundary",
            ),
            Lane(
                "Terminal-Bench hard security-terminal probe",
                "PASS",
                "SCBE 2/2",
                "a2.json",
                "boundary",
            ),
            Lane("Governance tier separation", "PASS", "DENY", "b.md", "boundary"),
            Lane(
                "Petri adversarial gate",
                "PASS",
                "2/173 false-allows (1.16%) in v7-matched run",
                "c.md",
                "boundary",
            ),
            Lane("Longform chain integrity", "PASS", "105/105", "d.json", "boundary"),
            Lane(
                "Hydra jobsite conservation",
                "PASS",
                "6/6; conservation 1.0",
                "e.json",
                "boundary",
            ),
        ],
        "2026-05-31T00:00:00Z",
    )

    assert "<h1>SCBE Benchmark Evidence Dashboard</h1>" in html
    assert "Local fixture scores are not public leaderboard scores." in html
    assert "Terminal-Bench core neutral parity" in html
