#!/usr/bin/env python3
"""
SCBE Terminal Ops CLI
=====================

Terminal-first control for SCBE mobile goals + connector workflows.
This wraps the existing API endpoints in src/api/main.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


def _json_print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


@dataclass
class APIClient:
    base_url: str
    api_key: str
    timeout: int = 20

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urlrequest.Request(url=url, method=method.upper(), headers=headers, data=data)
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if raw.strip():
                    return json.loads(raw)
                return {"status": "ok", "data": {}}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"{method} {path} -> network error: {exc.reason}") from exc


def _new_client(args: argparse.Namespace) -> APIClient:
    return APIClient(base_url=args.base_url, api_key=args.api_key, timeout=args.timeout)


def _parse_targets(text: str) -> list[str]:
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def cmd_templates(args: argparse.Namespace) -> int:
    client = _new_client(args)
    out = client.call("GET", "/mobile/connectors/templates")
    _json_print(out)
    return 0


def cmd_connector_list(args: argparse.Namespace) -> int:
    client = _new_client(args)
    out = client.call("GET", "/mobile/connectors")
    _json_print(out)
    return 0


def cmd_connector_add(args: argparse.Namespace) -> int:
    client = _new_client(args)
    payload: dict[str, Any] = {
        "name": args.name,
        "kind": args.kind,
        "endpoint_url": args.endpoint_url,
        "http_method": args.http_method,
        "timeout_seconds": args.connector_timeout,
        "payload_mode": args.payload_mode,
        "auth_type": args.auth_type,
        "auth_token": args.auth_token,
        "auth_header_name": args.auth_header_name,
        "shop_domain": args.shop_domain,
        "shopify_api_version": args.shopify_api_version,
        "enabled": True,
    }
    # drop empty fields to let API defaults apply cleanly
    payload = {k: v for k, v in payload.items() if v not in ("", None)}
    out = client.call("POST", "/mobile/connectors", payload)
    _json_print(out)
    return 0


def cmd_goal_create(args: argparse.Namespace) -> int:
    client = _new_client(args)
    payload = _build_goal_payload(
        goal=args.goal,
        channel=args.channel,
        priority=args.priority,
        execution_mode=args.execution_mode,
        targets=args.targets,
        no_human_gate=args.no_human_gate,
        connector_id=args.connector_id,
    )
    out = client.call("POST", "/mobile/goals", payload)
    _json_print(out)
    return 0


def cmd_goal_list(args: argparse.Namespace) -> int:
    client = _new_client(args)
    out = client.call("GET", "/mobile/goals")
    _json_print(out)
    return 0


def cmd_goal_status(args: argparse.Namespace) -> int:
    client = _new_client(args)
    out = client.call("GET", f"/mobile/goals/{args.goal_id}")
    _json_print(out)
    return 0


def _approve(client: APIClient, goal_id: str, note: str) -> dict[str, Any]:
    return client.call("POST", f"/mobile/goals/{goal_id}/approve", {"note": note})


def _advance(client: APIClient, goal_id: str, note: str) -> dict[str, Any]:
    return client.call("POST", f"/mobile/goals/{goal_id}/advance", {"note": note})


def _build_goal_payload(
    *,
    goal: str,
    channel: str,
    priority: str,
    execution_mode: str,
    targets: str,
    no_human_gate: bool,
    connector_id: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "goal": goal,
        "channel": channel,
        "priority": priority,
        "execution_mode": execution_mode,
        "targets": _parse_targets(targets),
        "require_human_for_high_risk": not no_human_gate,
    }
    if connector_id:
        payload["connector_id"] = connector_id
    return payload


def _run_goal_until_terminal(
    client: APIClient,
    *,
    goal_id: str,
    max_steps: int,
    poll_seconds: float,
    note: str,
    auto_approve_high_risk: bool,
) -> int:
    max_steps = max(1, max_steps)
    for _ in range(max_steps):
        out = _advance(client, goal_id, note)
        _json_print(out)

        status = str(out.get("status", ""))
        data = out.get("data", {}) or {}
        goal_status = str(data.get("status", ""))

        if status == "blocked" and goal_status == "review_required":
            if auto_approve_high_risk:
                appr = _approve(client, goal_id, "auto-approved via scbe_terminal_ops --auto-approve-high-risk")
                _json_print(appr)
                time.sleep(poll_seconds)
                continue
            print("Goal requires human approval. Run:", file=sys.stderr)
            print(f"  python scripts/scbe_terminal_ops.py --api-key <key> goal approve --goal-id {goal_id}", file=sys.stderr)
            return 2

        if goal_status in {"completed", "failed"}:
            return 0 if goal_status == "completed" else 3

        time.sleep(poll_seconds)

    print(f"Reached max steps ({max_steps}) without terminal state.", file=sys.stderr)
    return 4


def cmd_goal_run(args: argparse.Namespace) -> int:
    client = _new_client(args)
    return _run_goal_until_terminal(
        client,
        goal_id=args.goal_id,
        max_steps=args.max_steps,
        poll_seconds=args.poll_seconds,
        note=args.note,
        auto_approve_high_risk=args.auto_approve_high_risk,
    )


def cmd_goal_approve(args: argparse.Namespace) -> int:
    client = _new_client(args)
    out = _approve(client, args.goal_id, args.note)
    _json_print(out)
    return 0


def _run_alias_flow(args: argparse.Namespace, *, channel: str, default_goal: str) -> int:
    client = _new_client(args)
    goal_text = (args.goal or "").strip() or default_goal
    payload = _build_goal_payload(
        goal=goal_text,
        channel=channel,
        priority=args.priority,
        execution_mode=args.execution_mode,
        targets=args.targets,
        no_human_gate=args.no_human_gate,
        connector_id=args.connector_id,
    )
    created = client.call("POST", "/mobile/goals", payload)
    _json_print(created)

    goal_id = ((created.get("data") or {}).get("goal_id") or "").strip()
    if not goal_id:
        print("Goal creation response missing goal_id.", file=sys.stderr)
        return 1
    if args.no_run:
        return 0
    return _run_goal_until_terminal(
        client,
        goal_id=goal_id,
        max_steps=args.max_steps,
        poll_seconds=args.poll_seconds,
        note=args.note,
        auto_approve_high_risk=args.auto_approve_high_risk,
    )


def cmd_research(args: argparse.Namespace) -> int:
    return _run_alias_flow(
        args,
        channel="web_research",
        default_goal="Research sources, filter results, and assemble a training brief",
    )


def cmd_article(args: argparse.Namespace) -> int:
    return _run_alias_flow(
        args,
        channel="content_ops",
        default_goal="Draft article batch, schedule submissions, and publish report",
    )


def cmd_products(args: argparse.Namespace) -> int:
    return _run_alias_flow(
        args,
        channel="store_ops",
        default_goal="Collect store state, prioritize actions, and run product operations",
    )


def _add_alias_flow_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--goal", default="")
    parser.add_argument("--priority", default="high", choices=["low", "normal", "high", "critical"])
    parser.add_argument("--execution-mode", default="connector", choices=["simulate", "hydra_headless", "connector"])
    parser.add_argument("--connector-id", default="")
    parser.add_argument("--targets", default="", help="Comma-separated URLs/targets")
    parser.add_argument("--no-human-gate", action="store_true", help="Disable high-risk approval gate")
    parser.add_argument("--no-run", action="store_true", help="Create goal but do not advance")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--poll-seconds", type=float, default=0.2)
    parser.add_argument("--note", default="advance via scbe_terminal_ops")
    parser.add_argument("--auto-approve-high-risk", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SCBE terminal operations CLI")
    p.add_argument("--base-url", default="http://127.0.0.1:8000", help="SCBE API base URL")
    p.add_argument("--api-key", required=True, help="x-api-key value")
    p.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")

    sub = p.add_subparsers(dest="cmd", required=True)

    sp_templates = sub.add_parser("templates", help="List connector templates")
    sp_templates.set_defaults(func=cmd_templates)

    sp_conn = sub.add_parser("connector", help="Connector operations")
    sp_conn_sub = sp_conn.add_subparsers(dest="connector_cmd", required=True)

    sp_conn_list = sp_conn_sub.add_parser("list", help="List connectors")
    sp_conn_list.set_defaults(func=cmd_connector_list)

    sp_conn_add = sp_conn_sub.add_parser("add", help="Register connector")
    sp_conn_add.add_argument("--name", required=True)
    sp_conn_add.add_argument(
        "--kind",
        required=True,
        choices=[
            "n8n",
            "zapier",
            "shopify",
            "slack",
            "notion",
            "airtable",
            "github_actions",
            "linear",
            "discord",
            "generic_webhook",
        ],
    )
    sp_conn_add.add_argument("--endpoint-url", default="", help="Endpoint URL (optional for shopify if shop_domain set)")
    sp_conn_add.add_argument("--http-method", default="POST", choices=["POST", "PUT", "PATCH", "DELETE", "GET"])
    sp_conn_add.add_argument("--connector-timeout", type=int, default=8)
    sp_conn_add.add_argument(
        "--payload-mode",
        default="scbe_step",
        choices=["scbe_step", "raw_step", "shopify_graphql_read"],
    )
    sp_conn_add.add_argument("--auth-type", default="none", choices=["none", "bearer", "header"])
    sp_conn_add.add_argument("--auth-token", default="")
    sp_conn_add.add_argument("--auth-header-name", default="x-api-key")
    sp_conn_add.add_argument("--shop-domain", default="")
    sp_conn_add.add_argument("--shopify-api-version", default="2025-10")
    sp_conn_add.set_defaults(func=cmd_connector_add)

    sp_goal = sub.add_parser("goal", help="Goal operations")
    sp_goal_sub = sp_goal.add_subparsers(dest="goal_cmd", required=True)

    sp_goal_create = sp_goal_sub.add_parser("create", help="Create a goal")
    sp_goal_create.add_argument("--goal", required=True)
    sp_goal_create.add_argument("--channel", default="store_ops", choices=["store_ops", "web_research", "content_ops", "custom"])
    sp_goal_create.add_argument("--priority", default="normal", choices=["low", "normal", "high", "critical"])
    sp_goal_create.add_argument("--execution-mode", default="simulate", choices=["simulate", "hydra_headless", "connector"])
    sp_goal_create.add_argument("--connector-id", default="")
    sp_goal_create.add_argument("--targets", default="", help="Comma-separated URLs/targets")
    sp_goal_create.add_argument("--no-human-gate", action="store_true", help="Disable high-risk approval gate")
    sp_goal_create.set_defaults(func=cmd_goal_create)

    sp_goal_list = sp_goal_sub.add_parser("list", help="List goals")
    sp_goal_list.set_defaults(func=cmd_goal_list)

    sp_goal_status = sp_goal_sub.add_parser("status", help="Get goal status")
    sp_goal_status.add_argument("--goal-id", required=True)
    sp_goal_status.set_defaults(func=cmd_goal_status)

    sp_goal_run = sp_goal_sub.add_parser("run", help="Advance goal until complete/fail/review-needed")
    sp_goal_run.add_argument("--goal-id", required=True)
    sp_goal_run.add_argument("--max-steps", type=int, default=20)
    sp_goal_run.add_argument("--poll-seconds", type=float, default=0.2)
    sp_goal_run.add_argument("--note", default="advance via scbe_terminal_ops")
    sp_goal_run.add_argument("--auto-approve-high-risk", action="store_true")
    sp_goal_run.set_defaults(func=cmd_goal_run)

    sp_goal_approve = sp_goal_sub.add_parser("approve", help="Approve high-risk goal step")
    sp_goal_approve.add_argument("--goal-id", required=True)
    sp_goal_approve.add_argument("--note", default="approved from terminal")
    sp_goal_approve.set_defaults(func=cmd_goal_approve)

    sp_research = sub.add_parser("research", help="Alias: create + run web research goal")
    _add_alias_flow_args(sp_research)
    sp_research.set_defaults(func=cmd_research)

    sp_article = sub.add_parser("article", help="Alias: create + run content/article goal")
    _add_alias_flow_args(sp_article)
    sp_article.set_defaults(func=cmd_article)

    sp_products = sub.add_parser("products", help="Alias: create + run product/store goal")
    _add_alias_flow_args(sp_products)
    sp_products.set_defaults(func=cmd_products)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
