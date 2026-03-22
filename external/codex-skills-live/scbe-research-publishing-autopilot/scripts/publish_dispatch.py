#!/usr/bin/env python3
"""
Dispatch publish events to real channel endpoints with strict approval gating.

Input:
- dispatch_plan.json
- campaign_posts.json (for text/body payload data)
- connectors.json (endpoint config)
- approvals.json (required unless --allow-unapproved)
Optional:
- claim_gate_report.json
- state.json (idempotency)

Output:
- dispatch_log.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch publish events with approval and safety gates.")
    parser.add_argument("--plan", required=True, help="Path to dispatch_plan.json")
    parser.add_argument("--posts", required=True, help="Path to campaign_posts.json")
    parser.add_argument("--connectors", required=True, help="Path to connectors.json")
    parser.add_argument("--approval", default="", help="Path to approvals.json")
    parser.add_argument("--claim-report", default="", help="Optional claim gate report; blocks on fail")
    parser.add_argument("--out-log", required=True, help="Output dispatch log JSONL path")
    parser.add_argument("--state", default="", help="Optional state JSON path for idempotency")
    parser.add_argument(
        "--execute-until",
        default="",
        help="Optional ISO timestamp; execute publish events whose ts <= value",
    )
    parser.add_argument("--allow-unapproved", action="store_true", help="Bypass approval requirement")
    parser.add_argument("--dry-run", action="store_true", help="Do not send HTTP requests")
    return parser.parse_args()


def parse_ts(raw: str) -> datetime:
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def ts_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_posts(payload: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(payload, dict):
        maybe_posts = payload.get("posts")
        if isinstance(maybe_posts, list):
            payload = maybe_posts
    if not isinstance(payload, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        post_id = str(row.get("id", row.get("post_id", ""))).strip()
        if not post_id:
            continue
        out[post_id] = row
    return out


def normalize_approvals(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        maybe = payload.get("approvals")
        if isinstance(maybe, list):
            return [x for x in maybe if isinstance(x, dict)]
        rows: List[Dict[str, Any]] = []
        for k, v in payload.items():
            if isinstance(v, dict):
                row = {"post_id": k}
                row.update(v)
                rows.append(row)
        return rows
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def is_approved(approvals: List[Dict[str, Any]], post_id: str, channel: str, now: datetime) -> Tuple[bool, str]:
    for row in approvals:
        ap_post = str(row.get("post_id", "")).strip()
        ap_channel = str(row.get("channel", "")).strip().lower()
        if ap_post != post_id:
            continue
        if ap_channel and ap_channel != channel.lower():
            continue
        if not bool(row.get("approved", False)):
            continue
        expires_at = str(row.get("expires_at", "")).strip()
        if expires_at:
            try:
                if now > parse_ts(expires_at):
                    continue
            except ValueError:
                continue
        approver = str(row.get("approved_by", "")).strip() or "unknown"
        return True, approver
    return False, ""


def event_id(event: Dict[str, Any]) -> str:
    campaign_id = str(event.get("campaign_id", "campaign"))
    ts = str(event.get("ts", ""))
    channel = str(event.get("channel", ""))
    post_id = str(event.get("post_id", ""))
    return f"{campaign_id}|{ts}|{channel}|{post_id}"


def check_claim_report(claim_report_path: Optional[Path]) -> Tuple[bool, str]:
    if claim_report_path is None:
        return True, "no_claim_report"
    payload = read_json(claim_report_path, default={})
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    passed = bool(summary.get("pass", False))
    if not passed:
        failed = int(summary.get("claims_failed", -1))
        return False, f"claim_gate_failed:{failed}"
    return True, "claim_gate_passed"


def connector_for(connectors: Dict[str, Any], channel: str) -> Dict[str, Any]:
    raw = connectors.get("connectors", {}) if isinstance(connectors, dict) else {}
    if not isinstance(raw, dict):
        return {}
    cfg = raw.get(channel)
    if isinstance(cfg, dict):
        return cfg
    # default fallback connector
    fallback = raw.get("default")
    return fallback if isinstance(fallback, dict) else {}


def send_webhook(payload: Dict[str, Any], connector: Dict[str, Any], timeout_seconds: int, dry_run: bool) -> Tuple[bool, str]:
    endpoint_env = str(connector.get("endpoint_env", "")).strip()
    token_env = str(connector.get("token_env", "")).strip()
    method = str(connector.get("method", "POST")).strip().upper()
    headers = dict(connector.get("headers", {})) if isinstance(connector.get("headers", {}), dict) else {}

    if not endpoint_env:
        return False, "missing_endpoint_env"
    endpoint = os.getenv(endpoint_env, "").strip()
    if not endpoint:
        return False, f"missing_env:{endpoint_env}"

    headers.setdefault("Content-Type", "application/json")
    if token_env:
        token = os.getenv(token_env, "").strip()
        if token:
            headers.setdefault("Authorization", f"Bearer {token}")

    if dry_run:
        return True, f"dry_run_webhook:{endpoint}"

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=max(5, timeout_seconds)) as resp:
            status = getattr(resp, "status", 200)
            if 200 <= status < 300:
                return True, f"http_{status}"
            return False, f"http_{status}"
    except urllib.error.HTTPError as exc:
        return False, f"http_error_{exc.code}"
    except urllib.error.URLError as exc:
        return False, f"url_error:{exc.reason}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{type(exc).__name__}"


def send_event(payload: Dict[str, Any], connector: Dict[str, Any], timeout_seconds: int, dry_run: bool) -> Tuple[bool, str]:
    mode = str(connector.get("mode", "webhook")).strip().lower()
    if mode == "stdout":
        return True, "stdout"
    if mode == "webhook":
        return send_webhook(payload, connector, timeout_seconds, dry_run)
    return False, f"unknown_mode:{mode}"


def extra_post_fields(post_data: Dict[str, Any]) -> Dict[str, Any]:
    reserved = {
        "id",
        "post_id",
        "channel",
        "title",
        "text",
        "body",
        "cta",
        "offer_path",
    }
    out: Dict[str, Any] = {}
    for key, value in post_data.items():
        if key in reserved:
            continue
        out[key] = value
    return out


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)

    plan = read_json(Path(args.plan), default={})
    posts = normalize_posts(read_json(Path(args.posts), default=[]))
    connectors = read_json(Path(args.connectors), default={})
    approvals = normalize_approvals(read_json(Path(args.approval), default=[])) if args.approval else []

    claim_report_path = Path(args.claim_report) if args.claim_report else None
    claim_ok, claim_status = check_claim_report(claim_report_path)
    if not claim_ok:
        print(f"Blocked: {claim_status}")
        return 3

    state_path = Path(args.state) if args.state else None
    state = read_json(state_path, default={}) if state_path else {}
    if not isinstance(state, dict):
        state = {}
    sent_ids = set(state.get("sent_event_ids", [])) if isinstance(state.get("sent_event_ids", []), list) else set()

    execute_until: Optional[datetime] = None
    if args.execute_until:
        execute_until = parse_ts(args.execute_until)

    events = plan.get("events", []) if isinstance(plan, dict) else []
    if not isinstance(events, list):
        events = []

    default_timeout = 20
    if isinstance(connectors, dict):
        defaults = connectors.get("defaults", {})
        if isinstance(defaults, dict):
            default_timeout = int(defaults.get("timeout_seconds", default_timeout))

    out_path = Path(args.out_log)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    sent = 0
    blocked = 0
    failed = 0

    with out_path.open("a", encoding="utf-8") as log_f:
        for event in events:
            if not isinstance(event, dict):
                continue
            if str(event.get("type", "")).lower() != "publish":
                continue

            ts_raw = str(event.get("ts", "")).strip()
            if not ts_raw:
                continue
            try:
                event_ts = parse_ts(ts_raw)
            except ValueError:
                continue

            if execute_until and event_ts > execute_until:
                continue

            total += 1
            eid = event_id(event)
            if eid in sent_ids:
                row = {
                    "ts": ts_iso(now),
                    "event_id": eid,
                    "status": "skipped_already_sent",
                    "channel": event.get("channel", ""),
                    "post_id": event.get("post_id", ""),
                }
                log_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                continue

            post_id = str(event.get("post_id", "")).strip()
            channel = str(event.get("channel", "")).strip()
            post_data = posts.get(post_id, {})

            if not args.allow_unapproved:
                ok, approver = is_approved(approvals, post_id, channel, now)
                if not ok:
                    blocked += 1
                    row = {
                        "ts": ts_iso(now),
                        "event_id": eid,
                        "status": "blocked_unapproved",
                        "channel": channel,
                        "post_id": post_id,
                    }
                    log_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    continue
            else:
                approver = "bypass"

            connector = connector_for(connectors, channel)
            if not connector:
                failed += 1
                row = {
                    "ts": ts_iso(now),
                    "event_id": eid,
                    "status": "failed_missing_connector",
                    "channel": channel,
                    "post_id": post_id,
                }
                log_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                continue

            payload = {
                "campaign_id": event.get("campaign_id", ""),
                "event_id": eid,
                "channel": channel,
                "post_id": post_id,
                "title": post_data.get("title", event.get("payload", {}).get("title", "")),
                "text": post_data.get("text", post_data.get("body", "")),
                "cta": post_data.get("cta", event.get("payload", {}).get("cta", "")),
                "offer_path": post_data.get("offer_path", event.get("payload", {}).get("offer_path", "")),
                "approved_by": approver,
                "source_status": claim_status,
                "event_payload": event.get("payload", {}),
                "post_data": post_data,
                "meta": extra_post_fields(post_data),
            }

            ok, reason = send_event(payload, connector, timeout_seconds=default_timeout, dry_run=args.dry_run)
            status = "sent" if ok else "failed_send"
            if ok:
                sent += 1
                sent_ids.add(eid)
            else:
                failed += 1

            row = {
                "ts": ts_iso(now),
                "event_id": eid,
                "status": status,
                "reason": reason,
                "channel": channel,
                "post_id": post_id,
            }
            log_f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if state_path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state["sent_event_ids"] = sorted(sent_ids)
        state["updated_at"] = ts_iso(now)
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"Dispatch summary total={total} sent={sent} blocked={blocked} failed={failed}")
    return 0 if failed == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
