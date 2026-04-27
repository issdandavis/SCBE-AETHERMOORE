from scripts.system.plan_remote_non_quantized_merge import build_plan


def test_remote_merge_plan_blocks_quarantined_rows():
    gate = {
        "policy_id": "test",
        "promotion_gates": {
            "quarantine_decisions": ["QUARANTINE_STRUCTURED_BEHAVIOR", "PROMOTION_BLOCKED"],
        },
        "merge_policy": {"dare_ties_default": {"density": 0.53}},
    }
    matrix = {
        "rows": [
            {
                "name": "bad-adapter",
                "lane": "dsl",
                "adapter": "local/bad",
                "decision": "QUARANTINE_STRUCTURED_BEHAVIOR",
                "gates": [
                    {"name": "frozen_perplexity", "status": "pass", "value": "ppl=3.0"},
                    {"name": "dsl_executable", "status": "fail", "value": "acc=0.0%"},
                    {"name": "stage6_regression", "status": "fail", "value": "pass_rate=20%"},
                ],
            }
        ]
    }

    plan = build_plan(gate, matrix, {"pairs": []})

    assert plan["next_action"] == "BLOCK_MERGE_BUILD_REPAIR_DATA"
    assert plan["rows"][0]["status"] == "quarantine"
    assert plan["candidate_counts"]["quarantined"] == 1
    assert plan["foundation_goal"]["current_best_architecture"].startswith("multi-adapter router")
    assert plan["merge_ladder"][0]["step"] == "router_only"
    assert not plan["quantization_allowed"]
    assert not plan["local_heavy_work_allowed"]


def test_remote_merge_plan_prefers_dare_ties_when_drift_conflicts():
    gate = {
        "policy_id": "test",
        "promotion_gates": {"quarantine_decisions": []},
        "merge_policy": {"dare_ties_default": {"density": 0.53}},
    }
    matrix = {
        "rows": [
            {
                "name": "good-adapter",
                "lane": "coding",
                "adapter": "hf/good",
                "decision": "ROUTE_CANDIDATE",
                "gates": [
                    {"name": "frozen_perplexity", "status": "pass", "value": "ppl=2.0"},
                    {"name": "dsl_executable", "status": "pass", "value": "acc=90%"},
                    {"name": "stage6_regression", "status": "pass", "value": "pass_rate=100%"},
                    {"name": "functional_benchmark", "status": "pass", "value": "6/6"},
                ],
            }
        ]
    }
    drift = {"pairs": [{"decision": "route_only_conflict_high"}]}

    plan = build_plan(gate, matrix, drift)

    assert plan["next_action"] == "REMOTE_DARE_TIES_CANDIDATE_ONLY"
    assert plan["remote_dispatch_hint"]["preferred_merge_method"] == "dare_ties"
    assert plan["remote_dispatch_hint"]["non_quantized"] is True
    assert "well_select" in plan["repair_priorities"][0]
