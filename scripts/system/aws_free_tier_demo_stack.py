#!/usr/bin/env python3
"""Deploy a small AWS free-tier demo stack for SCBE customer capacity gating.

This script is intentionally conservative:

- it uses the limited ``scbe-free-tier`` profile created by
  ``aws_free_tier_portal.py``;
- it defaults to dry-run;
- it creates only low-capacity DynamoDB tables, one SNS topic, and one Lambda;
- it does not create a public endpoint;
- it never prints or stores secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = "scbe-free-tier"
DEFAULT_REGION = "us-east-1"
DEFAULT_STACK = "scbe-free-tier-demo"
DEFAULT_ROLE = "scbe-lambda-basic-exec"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "aws_free_tier_demo"
GUIDE_PATH = REPO_ROOT / "docs" / "customer-guides" / "SCBE_FREE_TIER_DEMO_USER_GUIDE.md"


@dataclass(frozen=True)
class DemoNames:
    stack_name: str
    customers_table: str
    usage_table: str
    sns_topic: str
    lambda_name: str
    lambda_role_name: str


@dataclass(frozen=True)
class DemoQuota:
    tier: str
    monthly_actions: int
    monthly_agents: int
    monthly_research_packets: int
    upgrade_at_percent: int


def demo_names(stack_name: str, lambda_role_name: str) -> DemoNames:
    safe = stack_name.replace("_", "-").lower()
    return DemoNames(
        stack_name=safe,
        customers_table=f"{safe}-customers",
        usage_table=f"{safe}-usage-events",
        sns_topic=f"{safe}-upgrade-events",
        lambda_name=f"{safe}-capacity-gate",
        lambda_role_name=lambda_role_name,
    )


def quota_ladder() -> list[DemoQuota]:
    return [
        DemoQuota("free", 250, 2, 25, 80),
        DemoQuota("starter", 2_500, 6, 250, 85),
        DemoQuota("pro", 25_000, 18, 2_500, 90),
        DemoQuota("business", 250_000, 64, 25_000, 92),
    ]


def lambda_source() -> str:
    return r'''
import json
import os


DEFAULT_QUOTAS = {
    "free": {"monthly_actions": 250, "monthly_agents": 2, "monthly_research_packets": 25, "upgrade_at_percent": 80},
    "starter": {"monthly_actions": 2500, "monthly_agents": 6, "monthly_research_packets": 250, "upgrade_at_percent": 85},
    "pro": {"monthly_actions": 25000, "monthly_agents": 18, "monthly_research_packets": 2500, "upgrade_at_percent": 90},
    "business": {"monthly_actions": 250000, "monthly_agents": 64, "monthly_research_packets": 25000, "upgrade_at_percent": 92},
}


def _payload(event):
    if isinstance(event, dict) and isinstance(event.get("body"), str):
        try:
            return json.loads(event["body"])
        except json.JSONDecodeError:
            return {}
    return event if isinstance(event, dict) else {}


def handler(event, context):
    quotas = json.loads(os.environ.get("SCBE_DEMO_QUOTAS", json.dumps(DEFAULT_QUOTAS)))
    payload = _payload(event)
    tier = str(payload.get("tier") or "free").lower()
    used_actions = int(payload.get("used_actions") or 0)
    requested_actions = max(1, int(payload.get("requested_actions") or 1))
    customer_id = str(payload.get("customer_id") or "demo-customer")
    quota = quotas.get(tier, quotas["free"])
    limit = int(quota["monthly_actions"])
    projected = used_actions + requested_actions
    usage_percent = round((projected / limit) * 100, 2) if limit else 100.0
    allowed = projected <= limit
    upgrade_signal = usage_percent >= int(quota["upgrade_at_percent"])
    body = {
        "schema_version": "scbe_capacity_gate_demo_v1",
        "customer_id": customer_id,
        "tier": tier,
        "allowed": allowed,
        "used_actions": used_actions,
        "requested_actions": requested_actions,
        "monthly_action_limit": limit,
        "remaining_after_request": max(0, limit - projected),
        "usage_percent": usage_percent,
        "upgrade_signal": upgrade_signal,
        "decision": "ALLOW" if allowed else "HOLD_UPGRADE_REQUIRED",
    }
    return {"statusCode": 200 if allowed else 402, "body": json.dumps(body, sort_keys=True)}
'''.lstrip()


def aws_env(region: str) -> dict[str, str]:
    env = os.environ.copy()
    env["AWS_DEFAULT_REGION"] = region
    return env


def run_aws(
    args: list[str],
    *,
    profile: str,
    region: str,
    check: bool = False,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["aws", *args, "--profile", profile, "--region", region],
        cwd=str(REPO_ROOT),
        env=aws_env(region),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def parse_json(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def table_exists(name: str, *, profile: str, region: str) -> bool:
    proc = run_aws(
        ["dynamodb", "describe-table", "--table-name", name, "--output", "json"],
        profile=profile,
        region=region,
    )
    return proc.returncode == 0


def create_table_args(table_name: str, *, usage_table: bool) -> list[str]:
    attrs = [{"AttributeName": "customer_id", "AttributeType": "S"}]
    key_schema = [{"AttributeName": "customer_id", "KeyType": "HASH"}]
    if usage_table:
        attrs.append({"AttributeName": "event_id", "AttributeType": "S"})
        key_schema.append({"AttributeName": "event_id", "KeyType": "RANGE"})
    return [
        "dynamodb",
        "create-table",
        "--table-name",
        table_name,
        "--attribute-definitions",
        json.dumps(attrs, separators=(",", ":")),
        "--key-schema",
        json.dumps(key_schema, separators=(",", ":")),
        "--provisioned-throughput",
        "ReadCapacityUnits=1,WriteCapacityUnits=1",
        "--output",
        "json",
    ]


def ensure_table(
    table_name: str,
    *,
    usage_table: bool,
    profile: str,
    region: str,
    execute: bool,
) -> str:
    if table_exists(table_name, profile=profile, region=region):
        return "exists"
    if not execute:
        return "would_create"
    run_aws(
        create_table_args(table_name, usage_table=usage_table),
        profile=profile,
        region=region,
        check=True,
    )
    wait_for_table(table_name, profile=profile, region=region)
    return "created"


def wait_for_table(table_name: str, *, profile: str, region: str) -> None:
    for _ in range(24):
        proc = run_aws(
            ["dynamodb", "describe-table", "--table-name", table_name, "--output", "json"],
            profile=profile,
            region=region,
        )
        payload = parse_json(proc)
        status = payload.get("Table", {}).get("TableStatus")
        if status == "ACTIVE":
            return
        time.sleep(5)
    raise TimeoutError(f"DynamoDB table did not become ACTIVE: {table_name}")


def ensure_topic(name: str, *, profile: str, region: str, execute: bool) -> dict[str, Any]:
    if not execute:
        return {"status": "would_create", "topic_arn": None}
    payload = parse_json(
        run_aws(
            ["sns", "create-topic", "--name", name, "--output", "json"],
            profile=profile,
            region=region,
            check=True,
        )
    )
    return {"status": "created_or_exists", "topic_arn": payload.get("TopicArn")}


def lambda_role_arn(role_name: str, *, profile: str, region: str) -> str:
    payload = parse_json(
        run_aws(
            ["iam", "get-role", "--role-name", role_name, "--output", "json"],
            profile=profile,
            region=region,
            check=True,
        )
    )
    arn = str(payload.get("Role", {}).get("Arn") or "")
    if not arn:
        raise RuntimeError(f"Unable to resolve Lambda role ARN for {role_name}")
    return arn


def write_lambda_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("lambda_function.py", lambda_source())


def ensure_lambda(
    names: DemoNames,
    *,
    profile: str,
    region: str,
    artifact_dir: Path,
    execute: bool,
) -> dict[str, Any]:
    zip_path = artifact_dir / f"{names.lambda_name}.zip"
    write_lambda_zip(zip_path)
    quotas = {
        quota.tier: {
            "monthly_actions": quota.monthly_actions,
            "monthly_agents": quota.monthly_agents,
            "monthly_research_packets": quota.monthly_research_packets,
            "upgrade_at_percent": quota.upgrade_at_percent,
        }
        for quota in quota_ladder()
    }
    env_vars = json.dumps({"Variables": {"SCBE_DEMO_QUOTAS": json.dumps(quotas, sort_keys=True)}}, separators=(",", ":"))
    if not execute:
        return {"status": "would_create_or_update", "zip_path": str(zip_path)}

    get_proc = run_aws(
        ["lambda", "get-function", "--function-name", names.lambda_name, "--output", "json"],
        profile=profile,
        region=region,
    )
    if get_proc.returncode == 0:
        run_aws(
            [
                "lambda",
                "update-function-code",
                "--function-name",
                names.lambda_name,
                "--zip-file",
                f"fileb://{zip_path}",
                "--output",
                "json",
            ],
            profile=profile,
            region=region,
            check=True,
        )
        run_aws(
            [
                "lambda",
                "update-function-configuration",
                "--function-name",
                names.lambda_name,
                "--environment",
                env_vars,
                "--output",
                "json",
            ],
            profile=profile,
            region=region,
            check=True,
        )
        status = "updated"
    else:
        role_arn = lambda_role_arn(names.lambda_role_name, profile=profile, region=region)
        run_aws(
            [
                "lambda",
                "create-function",
                "--function-name",
                names.lambda_name,
                "--runtime",
                "python3.12",
                "--handler",
                "lambda_function.handler",
                "--role",
                role_arn,
                "--zip-file",
                f"fileb://{zip_path}",
                "--timeout",
                "10",
                "--memory-size",
                "128",
                "--environment",
                env_vars,
                "--output",
                "json",
            ],
            profile=profile,
            region=region,
            check=True,
        )
        status = "created"
    return {"status": status, "zip_path": str(zip_path)}


def seed_demo_records(
    names: DemoNames, *, profile: str, region: str, topic_arn: str | None, execute: bool
) -> dict[str, str]:
    if not execute:
        return {
            "customer": "would_put",
            "usage_event": "would_put",
            "sns_publish": "would_publish" if topic_arn else "would_skip_no_topic",
        }
    now = datetime.now(timezone.utc).isoformat()
    customer = {
        "customer_id": {"S": "demo-customer"},
        "tier": {"S": "free"},
        "created_at": {"S": now},
        "status": {"S": "demo"},
    }
    usage_event = {
        "customer_id": {"S": "demo-customer"},
        "event_id": {"S": f"demo-{now}"},
        "action_count": {"N": "1"},
        "event_type": {"S": "demo_stack_deploy"},
        "created_at": {"S": now},
    }
    run_aws(
        ["dynamodb", "put-item", "--table-name", names.customers_table, "--item", json.dumps(customer), "--output", "json"],
        profile=profile,
        region=region,
        check=True,
    )
    run_aws(
        ["dynamodb", "put-item", "--table-name", names.usage_table, "--item", json.dumps(usage_event), "--output", "json"],
        profile=profile,
        region=region,
        check=True,
    )
    sns_status = "skipped_no_topic"
    if topic_arn:
        run_aws(
            [
                "sns",
                "publish",
                "--topic-arn",
                topic_arn,
                "--subject",
                "SCBE demo stack deployed",
                "--message",
                json.dumps({"stack": names.stack_name, "event": "demo_stack_deploy", "created_at": now}, sort_keys=True),
                "--output",
                "json",
            ],
            profile=profile,
            region=region,
            check=True,
        )
        sns_status = "published"
    return {"customer": "put", "usage_event": "put", "sns_publish": sns_status}


def invoke_demo_lambda(names: DemoNames, *, profile: str, region: str, artifact_dir: Path, execute: bool) -> dict[str, Any]:
    payload = {"customer_id": "demo-customer", "tier": "free", "used_actions": 199, "requested_actions": 3}
    if not execute:
        return {"status": "would_invoke", "payload": payload}
    out_path = artifact_dir / "lambda_invoke_response.json"
    proc = run_aws(
        [
            "lambda",
            "invoke",
            "--function-name",
            names.lambda_name,
            "--payload",
            json.dumps(payload, separators=(",", ":")),
            "--cli-binary-format",
            "raw-in-base64-out",
            str(out_path),
            "--output",
            "json",
        ],
        profile=profile,
        region=region,
        timeout=180,
    )
    return {
        "status": "invoked" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "stderr": proc.stderr.strip(),
        "response_path": str(out_path),
    }


def ses_status(*, profile: str, region: str, execute: bool) -> dict[str, Any]:
    if not execute:
        return {"status": "would_check_quota_and_identities"}
    quota = parse_json(
        run_aws(["ses", "get-send-quota", "--output", "json"], profile=profile, region=region)
    )
    identities = parse_json(
        run_aws(["ses", "list-identities", "--output", "json"], profile=profile, region=region)
    )
    return {
        "status": "checked",
        "send_quota": quota,
        "identity_count": len(identities.get("Identities", [])),
        "send_demo_email": "skipped_until_identity_verified",
    }


def render_customer_guide(packet: dict[str, Any]) -> str:
    names = packet["resources"]
    return f"""# SCBE Free Tier Demo User Guide

Generated: {packet["generated_at"]}

This guide is generated from the same packet used to deploy the demo stack. It is the
buyer-facing version of the working prototype: a small customer-capacity gate built
from AWS Lambda, Amazon DynamoDB, Amazon SNS, and Amazon SES quota inspection.

## What The Demo Proves

- A customer record can live in `{names["customers_table"]}`.
- Usage events can be recorded in `{names["usage_table"]}`.
- A capacity gate can run as `{names["lambda_name"]}`.
- Upgrade signals can publish through `{names["sns_topic"]}`.
- Email delivery stays gated until Amazon SES identities are verified.

## Run The Local Check

```powershell
aws sts get-caller-identity --profile {packet["profile"]} --region {packet["region"]}
```

## Invoke The Capacity Gate

```powershell
$payloadPath = "artifacts/aws_free_tier_demo_payload.json"
'{{"customer_id":"demo-customer","tier":"free","used_actions":199,"requested_actions":3}}' | Set-Content -Path $payloadPath -Encoding utf8
aws lambda invoke --function-name {names["lambda_name"]} --payload file://$payloadPath --cli-binary-format raw-in-base64-out --profile {packet["profile"]} --region {packet["region"]} artifacts/aws_free_tier_demo_response.json
Get-Content artifacts/aws_free_tier_demo_response.json
```

## Customer Ladder

| Tier | Monthly actions | Agents | Research packets | Upgrade signal |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(f'| {q["tier"]} | {q["monthly_actions"]} | {q["monthly_agents"]} | {q["monthly_research_packets"]} | {q["upgrade_at_percent"]}% |' for q in packet["quota_ladder"])}

## Promotion Rule

Keep the stack in demo mode until the customer guide, the Lambda response, the
DynamoDB seed records, and the SES identity status are all present. After that,
the next paid tier adds an authenticated public endpoint and real email delivery.
"""


def write_artifacts(packet: dict[str, Any], artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "demo_stack_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8"
    )
    GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GUIDE_PATH.write_text(render_customer_guide(packet), encoding="utf-8")


def build_packet(args: argparse.Namespace, names: DemoNames, artifact_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": "scbe_aws_free_tier_demo_stack_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execute": bool(args.execute),
        "profile": args.profile,
        "region": args.region,
        "artifact_dir": str(artifact_dir),
        "resources": asdict(names),
        "quota_ladder": [asdict(quota) for quota in quota_ladder()],
        "cost_guardrails": {
            "public_endpoint_created": False,
            "dynamodb_capacity": "PROVISIONED 1 RCU / 1 WCU per table",
            "ses_email_send": "disabled until identity verification",
            "secrets_printed": False,
        },
        "official_free_tier_references": [
            "https://aws.amazon.com/free/serverless/",
            "https://aws.amazon.com/lambda/pricing/",
            "https://aws.amazon.com/dynamodb/pricing/",
        ],
    }


def run_demo_stack(args: argparse.Namespace) -> dict[str, Any]:
    names = demo_names(args.stack_name, args.lambda_role_name)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(args.artifact_root) / names.stack_name / stamp
    packet = build_packet(args, names, artifact_dir)
    packet["actions"] = {
        "customers_table": ensure_table(
            names.customers_table,
            usage_table=False,
            profile=args.profile,
            region=args.region,
            execute=bool(args.execute),
        ),
        "usage_table": ensure_table(
            names.usage_table,
            usage_table=True,
            profile=args.profile,
            region=args.region,
            execute=bool(args.execute),
        ),
    }
    topic = ensure_topic(names.sns_topic, profile=args.profile, region=args.region, execute=bool(args.execute))
    packet["actions"]["sns_topic"] = topic
    packet["actions"]["lambda"] = ensure_lambda(
        names,
        profile=args.profile,
        region=args.region,
        artifact_dir=artifact_dir,
        execute=bool(args.execute),
    )
    packet["actions"]["seed"] = seed_demo_records(
        names,
        profile=args.profile,
        region=args.region,
        topic_arn=topic.get("topic_arn"),
        execute=bool(args.execute),
    )
    packet["actions"]["lambda_invoke"] = invoke_demo_lambda(
        names, profile=args.profile, region=args.region, artifact_dir=artifact_dir, execute=bool(args.execute)
    )
    packet["actions"]["ses"] = ses_status(profile=args.profile, region=args.region, execute=bool(args.execute))
    write_artifacts(packet, artifact_dir)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy or plan the SCBE AWS free-tier demo stack")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--stack-name", default=DEFAULT_STACK)
    parser.add_argument("--lambda-role-name", default=DEFAULT_ROLE)
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--execute", action="store_true", help="Create or update AWS demo resources")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = run_demo_stack(args)
    if args.json:
        print(json.dumps(packet, indent=2, sort_keys=True))
    else:
        mode = "EXECUTE" if args.execute else "DRY-RUN"
        resources = packet["resources"]
        print(f"SCBE AWS free-tier demo stack [{mode}]")
        print(f"profile={packet['profile']} region={packet['region']} stack={resources['stack_name']}")
        print(f"guide={GUIDE_PATH}")
        print(f"packet={Path(packet['artifact_dir']) / 'demo_stack_packet.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
