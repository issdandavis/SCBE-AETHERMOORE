from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "aws_free_tier_demo_stack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("aws_free_tier_demo_stack", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_demo_names_are_stack_scoped() -> None:
    module = _load_module()

    names = module.demo_names("SCBE_Free_Tier_Demo", "scbe-lambda-basic-exec")

    assert names.stack_name == "scbe-free-tier-demo"
    assert names.customers_table == "scbe-free-tier-demo-customers"
    assert names.usage_table == "scbe-free-tier-demo-usage-events"
    assert names.sns_topic == "scbe-free-tier-demo-upgrade-events"
    assert names.lambda_name == "scbe-free-tier-demo-capacity-gate"


def test_quota_ladder_has_monotonic_paid_capacity() -> None:
    module = _load_module()

    quotas = module.quota_ladder()
    actions = [quota.monthly_actions for quota in quotas]
    agents = [quota.monthly_agents for quota in quotas]

    assert [quota.tier for quota in quotas] == ["free", "starter", "pro", "business"]
    assert actions == sorted(actions)
    assert agents == sorted(agents)
    assert quotas[0].upgrade_at_percent < quotas[-1].upgrade_at_percent


def test_lambda_source_blocks_over_quota_and_allows_under_quota() -> None:
    module = _load_module()
    namespace: dict[str, object] = {}
    exec(module.lambda_source(), namespace)

    handler = namespace["handler"]
    allowed = handler(
        {"customer_id": "demo", "tier": "free", "used_actions": 10, "requested_actions": 3},
        None,
    )
    blocked = handler(
        {"customer_id": "demo", "tier": "free", "used_actions": 249, "requested_actions": 3},
        None,
    )

    allowed_body = json.loads(allowed["body"])
    blocked_body = json.loads(blocked["body"])
    assert allowed["statusCode"] == 200
    assert allowed_body["decision"] == "ALLOW"
    assert blocked["statusCode"] == 402
    assert blocked_body["decision"] == "HOLD_UPGRADE_REQUIRED"


def test_customer_guide_contains_no_secret_or_public_endpoint_claim() -> None:
    module = _load_module()
    names = module.demo_names("scbe-free-tier-demo", "scbe-lambda-basic-exec")
    packet = {
        "generated_at": "2026-05-03T00:00:00+00:00",
        "profile": "scbe-free-tier",
        "region": "us-east-1",
        "resources": names.__dict__,
        "quota_ladder": [quota.__dict__ for quota in module.quota_ladder()],
    }

    guide = module.render_customer_guide(packet)

    assert "SCBE Free Tier Demo User Guide" in guide
    assert "scbe-free-tier-demo-capacity-gate" in guide
    assert "API key" not in guide
    assert "secret access key" not in guide.lower()
    assert "authenticated public endpoint" in guide
