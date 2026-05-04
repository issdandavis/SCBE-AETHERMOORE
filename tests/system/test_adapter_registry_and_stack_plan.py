from scripts.eval.plan_adapter_stack import build_stack_plan
from scripts.model_training.build_adapter_registry import build_registry


def test_adapter_registry_finds_model_training_profiles() -> None:
    registry = build_registry()
    assert registry["schema_version"] == "scbe_adapter_registry_v1"
    assert registry["adapter_count"] > 0
    assert any(row["profile_id"] == "coding-agent-qwen-geoshell-pair-agent-v1" for row in registry["rows"])


def test_adapter_stack_plan_names_next_action() -> None:
    plan = build_stack_plan()
    assert plan["schema_version"] == "scbe_adapter_stack_plan_v1"
    assert plan["decision"] in {"PROMOTE_TO_LIVE_SMOKE", "HOLD_NO_PROMOTED_ADAPTER"}
    assert plan["next_actions"]
