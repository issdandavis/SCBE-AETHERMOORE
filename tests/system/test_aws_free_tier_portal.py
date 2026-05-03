from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "aws_free_tier_portal.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("aws_free_tier_portal", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_operator_policy_is_limited_to_free_tier_lanes() -> None:
    module = _load_module()

    policy = module.build_operator_policy(
        "123456789012", "scbe-free-tier-operator", "scbe-lambda-basic-exec"
    )
    encoded = json.dumps(policy)

    assert "lambda:CreateFunction" in encoded
    assert "dynamodb:CreateTable" in encoded
    assert "sns:Publish" in encoded
    assert "ses:SendEmail" in encoded
    assert "AdministratorAccess" not in encoded
    assert "iam:*" not in encoded
    assert "arn:aws:iam::123456789012:role/scbe-lambda-basic-exec" in encoded


def test_lambda_trust_policy_only_allows_lambda_service() -> None:
    module = _load_module()

    policy = module.build_lambda_trust_policy()

    assert policy["Statement"] == [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ]


def test_read_root_csv_accepts_aws_headers(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "root.csv"
    path.write_text(
        "Access key ID,Secret access key\nAKIA_TEST,secret-test\n", encoding="utf-8"
    )

    creds = module.read_root_csv(path)

    assert creds.access_key_id == "AKIA_TEST"
    assert creds.secret_access_key == "secret-test"
