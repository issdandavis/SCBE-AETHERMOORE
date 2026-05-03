#!/usr/bin/env python3
"""Bootstrap a limited AWS CLI profile from a root access-key CSV.

The script is designed for the one-time "portal switch" from a root key to a
bounded automation profile. It defaults to dry-run. With --execute, it uses the
root key only in-process, creates a limited IAM user and Lambda execution role,
creates an access key for that IAM user, and writes a named AWS CLI profile.

It never prints secret access keys.
"""

from __future__ import annotations

import argparse
import configparser
import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT_CSV = (
    Path.home()
    / ".scbe"
    / "secrets"
    / "incoming"
    / "2026-05-03-key-intake"
    / "03-csv-key-material-caa632186a21.csv"
)
DEFAULT_PROFILE = "scbe-free-tier"
DEFAULT_USER = "scbe-free-tier-operator"
DEFAULT_REGION = "us-east-1"
DEFAULT_ROLE = "scbe-lambda-basic-exec"
INLINE_POLICY_NAME = "SCBEFreeTierOperatorPolicy"


@dataclass(frozen=True)
class AwsRootCredentials:
    access_key_id: str
    secret_access_key: str


def read_root_csv(path: Path) -> AwsRootCredentials:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No credential rows found in {path}")
    row = rows[0]
    access = (
        row.get("Access key ID")
        or row.get("AWS_ACCESS_KEY_ID")
        or row.get("aws_access_key_id")
        or ""
    ).strip()
    secret = (
        row.get("Secret access key")
        or row.get("AWS_SECRET_ACCESS_KEY")
        or row.get("aws_secret_access_key")
        or ""
    ).strip()
    if not access or not secret:
        raise ValueError("CSV must contain Access key ID and Secret access key columns")
    return AwsRootCredentials(access_key_id=access, secret_access_key=secret)


def build_operator_policy(
    account_id: str, user_name: str, role_name: str
) -> dict[str, Any]:
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "LambdaDynamoSnsSesFreeTierLane",
                "Effect": "Allow",
                "Action": [
                    "lambda:CreateFunction",
                    "lambda:UpdateFunctionCode",
                    "lambda:UpdateFunctionConfiguration",
                    "lambda:GetFunction",
                    "lambda:ListFunctions",
                    "lambda:InvokeFunction",
                    "lambda:DeleteFunction",
                    "dynamodb:CreateTable",
                    "dynamodb:DescribeTable",
                    "dynamodb:ListTables",
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DeleteItem",
                    "sns:CreateTopic",
                    "sns:Publish",
                    "sns:Subscribe",
                    "sns:ListTopics",
                    "sns:DeleteTopic",
                    "ses:GetSendQuota",
                    "ses:GetSendStatistics",
                    "ses:ListIdentities",
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                "Resource": "*",
            },
            {
                "Sid": "PassOnlyScbeLambdaRole",
                "Effect": "Allow",
                "Action": ["iam:GetRole", "iam:PassRole"],
                "Resource": role_arn,
            },
            {
                "Sid": "ManageOwnAccessKeysOnly",
                "Effect": "Allow",
                "Action": [
                    "iam:GetUser",
                    "iam:ListAccessKeys",
                    "iam:CreateAccessKey",
                    "iam:UpdateAccessKey",
                    "iam:DeleteAccessKey",
                ],
                "Resource": f"arn:aws:iam::{account_id}:user/{user_name}",
            },
            {
                "Sid": "ReadCallerIdentity",
                "Effect": "Allow",
                "Action": ["sts:GetCallerIdentity"],
                "Resource": "*",
            },
        ],
    }


def build_lambda_trust_policy() -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def root_env(creds: AwsRootCredentials, region: str) -> dict[str, str]:
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = creds.access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = creds.secret_access_key
    env["AWS_DEFAULT_REGION"] = region
    return env


def run_aws(
    args: list[str], env: dict[str, str], *, check: bool = False
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["aws", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def json_or_none(proc: subprocess.CompletedProcess[str]) -> dict[str, Any] | None:
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def ensure_user(env: dict[str, str], user_name: str, *, execute: bool) -> str:
    proc = run_aws(
        ["iam", "get-user", "--user-name", user_name, "--output", "json"], env
    )
    if proc.returncode == 0:
        return "exists"
    if execute:
        run_aws(
            ["iam", "create-user", "--user-name", user_name, "--output", "json"],
            env,
            check=True,
        )
    return "created" if execute else "would_create"


def ensure_lambda_role(env: dict[str, str], role_name: str, *, execute: bool) -> str:
    proc = run_aws(
        ["iam", "get-role", "--role-name", role_name, "--output", "json"], env
    )
    if proc.returncode == 0:
        return "exists"
    if execute:
        trust = json.dumps(build_lambda_trust_policy(), separators=(",", ":"))
        run_aws(
            [
                "iam",
                "create-role",
                "--role-name",
                role_name,
                "--assume-role-policy-document",
                trust,
                "--output",
                "json",
            ],
            env,
            check=True,
        )
        run_aws(
            [
                "iam",
                "attach-role-policy",
                "--role-name",
                role_name,
                "--policy-arn",
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            ],
            env,
            check=True,
        )
    return "created" if execute else "would_create"


def put_user_policy(
    env: dict[str, str], user_name: str, policy: dict[str, Any], *, execute: bool
) -> str:
    if execute:
        run_aws(
            [
                "iam",
                "put-user-policy",
                "--user-name",
                user_name,
                "--policy-name",
                INLINE_POLICY_NAME,
                "--policy-document",
                json.dumps(policy, separators=(",", ":")),
            ],
            env,
            check=True,
        )
        return "updated"
    return "would_update"


def create_access_key(
    env: dict[str, str], user_name: str, *, execute: bool, force_new_key: bool
) -> dict[str, Any]:
    proc = run_aws(
        ["iam", "list-access-keys", "--user-name", user_name, "--output", "json"], env
    )
    existing = []
    if proc.returncode == 0:
        payload = json.loads(proc.stdout)
        existing = payload.get("AccessKeyMetadata", [])
    if existing and not force_new_key:
        return {
            "status": "blocked_existing_access_key",
            "existing_key_count": len(existing),
            "note": "Use --force-new-key only if you intentionally want another IAM access key.",
        }
    if not execute:
        return {"status": "would_create", "existing_key_count": len(existing)}
    payload = json_or_none(
        run_aws(
            ["iam", "create-access-key", "--user-name", user_name, "--output", "json"],
            env,
            check=True,
        )
    )
    access_key = (payload or {}).get("AccessKey", {})
    return {
        "status": "created",
        "access_key_id": access_key.get("AccessKeyId"),
        "secret_access_key": access_key.get("SecretAccessKey"),
    }


def write_aws_profile(profile: str, region: str, key_result: dict[str, Any]) -> str:
    access = str(key_result.get("access_key_id") or "")
    secret = str(key_result.get("secret_access_key") or "")
    if not access or not secret:
        return "skipped_no_new_key"

    aws_dir = Path.home() / ".aws"
    aws_dir.mkdir(parents=True, exist_ok=True)
    credentials_path = aws_dir / "credentials"
    config_path = aws_dir / "config"

    creds = configparser.RawConfigParser()
    creds.read(credentials_path)
    if not creds.has_section(profile):
        creds.add_section(profile)
    creds.set(profile, "aws_access_key_id", access)
    creds.set(profile, "aws_secret_access_key", secret)
    with credentials_path.open("w", encoding="utf-8") as handle:
        creds.write(handle)

    cfg = configparser.RawConfigParser()
    cfg.read(config_path)
    section = f"profile {profile}"
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, "region", region)
    cfg.set(section, "output", "json")
    with config_path.open("w", encoding="utf-8") as handle:
        cfg.write(handle)
    return "written"


def run_bootstrap(args: argparse.Namespace) -> dict[str, Any]:
    creds = read_root_csv(Path(args.root_csv))
    env = root_env(creds, args.region)
    identity = (
        json_or_none(
            run_aws(["sts", "get-caller-identity", "--output", "json"], env, check=True)
        )
        or {}
    )
    account_id = str(identity.get("Account") or "")
    arn = str(identity.get("Arn") or "")
    if not account_id:
        raise RuntimeError("Unable to resolve AWS account id")

    policy = build_operator_policy(account_id, args.user_name, args.lambda_role_name)
    result: dict[str, Any] = {
        "schema_version": "scbe_aws_free_tier_portal_bootstrap_v1",
        "execute": bool(args.execute),
        "profile": args.profile,
        "region": args.region,
        "account_id": account_id,
        "root_identity_arn": arn,
        "root_key_values_printed": False,
        "planned": {
            "iam_user": args.user_name,
            "inline_policy": INLINE_POLICY_NAME,
            "lambda_execution_role": args.lambda_role_name,
            "aws_cli_profile": args.profile,
            "allowed_service_lanes": [
                "lambda",
                "dynamodb",
                "sns",
                "ses",
                "cloudwatch_logs",
            ],
        },
    }
    result["user"] = ensure_user(env, args.user_name, execute=args.execute)
    result["lambda_role"] = ensure_lambda_role(
        env, args.lambda_role_name, execute=args.execute
    )
    result["policy"] = put_user_policy(
        env, args.user_name, policy, execute=args.execute
    )
    key_result = create_access_key(
        env,
        args.user_name,
        execute=args.execute,
        force_new_key=bool(args.force_new_key),
    )
    redacted_key_result = {
        k: v for k, v in key_result.items() if k != "secret_access_key"
    }
    result["access_key"] = redacted_key_result
    result["profile_write"] = (
        write_aws_profile(args.profile, args.region, key_result)
        if args.execute
        else "dry_run"
    )
    if args.execute and result["profile_write"] == "written":
        proc = subprocess.run(
            [
                "aws",
                "sts",
                "get-caller-identity",
                "--profile",
                args.profile,
                "--output",
                "json",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        result["profile_identity_check"] = {
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
        }
        if proc.returncode == 0:
            payload = json.loads(proc.stdout)
            result["profile_identity_check"]["arn"] = payload.get("Arn")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a limited SCBE AWS free-tier operator profile"
    )
    parser.add_argument("--root-csv", default=str(DEFAULT_ROOT_CSV))
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--user-name", default=DEFAULT_USER)
    parser.add_argument("--lambda-role-name", default=DEFAULT_ROLE)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Mutate AWS IAM and write the named AWS CLI profile",
    )
    parser.add_argument(
        "--force-new-key",
        action="store_true",
        help="Create a new IAM access key even if one already exists",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_bootstrap(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        mode = "EXECUTE" if args.execute else "DRY-RUN"
        print(f"SCBE AWS free-tier portal bootstrap [{mode}]")
        print(
            f"profile={result['profile']} user={result['planned']['iam_user']} account={result['account_id']}"
        )
        print(
            f"user={result['user']} role={result['lambda_role']} policy={result['policy']}"
        )
        print(
            f"access_key={result['access_key'].get('status')} profile_write={result['profile_write']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
