from __future__ import annotations

from scripts.system.tenreary_benchmark_harness import score_run


def test_score_run_detects_reliability_gap():
    payload = {
        "ok": False,
        "tenreary_name": "dual-browser-monetization-assistant",
        "generated_at": "2026-03-04T06:14:33Z",
        "steps_total": 4,
        "steps_ok": 3,
        "steps_failed": 1,
        "results": [
            {
                "id": "a",
                "type": "browser.navigate",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 100,
            },
            {
                "id": "b_secondary",
                "type": "browser.navigate",
                "status": "error",
                "started_at": "t",
                "elapsed_ms": 200,
            },
            {
                "id": "c",
                "type": "analysis.content",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 10,
            },
            {
                "id": "d",
                "type": "automation.emit",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 30,
            },
        ],
    }

    scored = score_run(payload, artifact_path="artifact.json")
    assert scored.reliability_score < 95.0
    assert scored.truth_assessment == "good_direction_reliability_gap"
    assert scored.elite_ready is False


def test_score_run_elite_ready_when_all_gates_pass():
    payload = {
        "ok": True,
        "tenreary_name": "three-by-three-monetization-grid",
        "generated_at": "2026-03-04T06:16:20Z",
        "steps_total": 5,
        "steps_ok": 5,
        "steps_failed": 0,
        "results": [
            {
                "id": "p_primary",
                "type": "browser.navigate",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 900,
            },
            {
                "id": "s_secondary",
                "type": "browser.navigate",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 1000,
            },
            {
                "id": "analyze",
                "type": "analysis.content",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 100,
                "data": {
                    "analysis": {"keyword_counts": {"shopify": 2, "conversion": 1}}
                },
            },
            {
                "id": "emit",
                "type": "automation.emit",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 300,
                "data": {"n8n": {"success": True}, "zapier": {"success": True}},
            },
            {
                "id": "connector",
                "type": "connector.execute",
                "status": "ok",
                "started_at": "t",
                "elapsed_ms": 300,
                "data": {"success": True},
            },
        ],
    }

    scored = score_run(payload, artifact_path="artifact.json")
    assert scored.reliability_score >= 95.0
    assert scored.governance_score >= 90.0
    assert scored.cash_signal_score >= 70.0
    assert scored.overall_score >= 85.0
    assert scored.truth_assessment == "validated_outperforming_candidate"
    assert scored.elite_ready is True
