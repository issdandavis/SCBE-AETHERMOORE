#!/usr/bin/env python3
"""
Evaluate campaign metrics and emit retrigger actions with cooldown controls.

Input:
- metrics JSONL
- retrigger rules JSON
Optional:
- state JSON (tracks last trigger time by rule/post)
Output:
- retrigger actions JSON
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create retrigger actions from campaign metrics.")
    parser.add_argument("--metrics", required=True, help="Path to metrics JSONL")
    parser.add_argument("--rules", required=True, help="Path to retrigger rules JSON")
    parser.add_argument("--out", required=True, help="Output path for actions JSON")
    parser.add_argument(
        "--state",
        default="",
        help="Optional state JSON path. Saves and loads last trigger timestamps for cooldown.",
    )
    parser.add_argument(
        "--now",
        default="",
        help="Optional ISO timestamp in UTC. Defaults to current UTC time.",
    )
    return parser.parse_args()


def parse_ts(raw: str) -> datetime:
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def now_utc(raw: str) -> datetime:
    return parse_ts(raw) if raw else datetime.now(timezone.utc)


def ts_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def latest_by_post(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        post_id = str(row.get("post_id", "")).strip()
        if not post_id:
            continue
        ts_raw = str(row.get("timestamp", ""))
        if not ts_raw:
            continue
        try:
            ts = parse_ts(ts_raw)
        except ValueError:
            continue
        existing = out.get(post_id)
        if existing is None:
            out[post_id] = row
        else:
            try:
                existing_ts = parse_ts(str(existing.get("timestamp", "")))
            except ValueError:
                existing_ts = datetime.min.replace(tzinfo=timezone.utc)
            if ts > existing_ts:
                out[post_id] = row
    return out


def metric_value(row: Dict[str, Any], metric: str) -> float:
    impressions = float(row.get("impressions", 0) or 0)
    clicks = float(row.get("clicks", 0) or 0)
    conversions = float(row.get("conversions", row.get("leads", 0)) or 0)

    if metric == "impressions":
        return impressions
    if metric == "clicks":
        return clicks
    if metric == "conversions":
        return conversions
    if metric == "ctr":
        return (clicks / impressions) if impressions > 0 else 0.0
    if metric == "cvr":
        return (conversions / clicks) if clicks > 0 else 0.0
    return 0.0


def compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "lt":
        return value < threshold
    if operator == "lte":
        return value <= threshold
    if operator == "gt":
        return value > threshold
    if operator == "gte":
        return value >= threshold
    if operator == "eq":
        return value == threshold
    return False


def state_key(rule_name: str, post_id: str) -> str:
    return f"{rule_name}::{post_id}"


def should_cooldown(last_ts: str, cooldown_minutes: int, now: datetime) -> bool:
    if not last_ts:
        return False
    try:
        fired = parse_ts(last_ts)
    except ValueError:
        return False
    return now < fired + timedelta(minutes=max(1, cooldown_minutes))


def normalize_rules(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        rules = payload.get("rules")
        if isinstance(rules, list):
            return [r for r in rules if isinstance(r, dict)]
    return []


def main() -> int:
    args = parse_args()
    now = now_utc(args.now)
    metrics = read_jsonl(Path(args.metrics))
    rules_payload = read_json(Path(args.rules), default=[])
    rules = normalize_rules(rules_payload)

    state_path = Path(args.state) if args.state else None
    state = read_json(state_path, default={}) if state_path else {}
    if not isinstance(state, dict):
        state = {}

    latest = latest_by_post(metrics)
    actions: List[Dict[str, Any]] = []

    for post_id, row in latest.items():
        channel = str(row.get("channel", "")).strip().lower()
        for rule in rules:
            rule_name = str(rule.get("name", "rule")).strip() or "rule"
            metric = str(rule.get("metric", "ctr")).strip().lower()
            operator = str(rule.get("operator", "lt")).strip().lower()
            threshold = float(rule.get("threshold", 0))
            cooldown = int(rule.get("cooldown_minutes", 60))
            action_name = str(rule.get("action", "refresh_copy")).strip()
            rule_channel = str(rule.get("channel", "")).strip().lower()

            if rule_channel and rule_channel != channel:
                continue

            value = metric_value(row, metric)
            if not compare(value, operator, threshold):
                continue

            key = state_key(rule_name, post_id)
            if should_cooldown(str(state.get(key, "")), cooldown, now):
                continue

            actions.append(
                {
                    "ts": ts_iso(now),
                    "post_id": post_id,
                    "channel": row.get("channel", ""),
                    "rule": rule_name,
                    "metric": metric,
                    "value": value,
                    "operator": operator,
                    "threshold": threshold,
                    "action": action_name,
                }
            )
            state[key] = ts_iso(now)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": ts_iso(now),
        "actions": actions,
        "summary": {
            "metrics_rows": len(metrics),
            "posts_observed": len(latest),
            "rules": len(rules),
            "actions": len(actions),
        },
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if state_path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"Saved actions: {out_path}")
    print(f"Actions emitted: {len(actions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
