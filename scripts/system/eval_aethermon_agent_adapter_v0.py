#!/usr/bin/env python3
"""Evaluate AETHERMON adapter v0 outputs against the held-out receipt target.

This is the promotion gate for the local proof lane. It can run now in
`oracle` or `abstain` mode, and later against base/adapter model predictions
without changing the scoring contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOLDOUT = REPO_ROOT / "training-data" / "sft" / "aethermon_agent_adapter_v0_holdout.sft.jsonl"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "aethermon_agent_adapter_v0" / "eval_receipt.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def row_id(row: dict[str, Any]) -> str:
    messages = row.get("messages", [])
    prompt_messages = [msg for msg in messages if msg.get("role") != "assistant"]
    payload = {
        "prompt_messages": prompt_messages,
        "meta": {
            key: row.get("meta", {}).get(key)
            for key in ("source", "adapter_mix_source", "domain", "kind", "tick", "topic", "concept_id")
        },
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def try_json(text: str) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    try:
        value = json.loads(text)
    except Exception as exc:  # noqa: BLE001 - diagnostics go into receipt
        return None, str(exc)
    if isinstance(value, (dict, list)):
        return value, None
    return None, "json root is not object or array"


def expected_content(row: dict[str, Any]) -> str:
    for message in reversed(row.get("messages", [])):
        if message.get("role") == "assistant":
            return str(message.get("content", ""))
    return ""


def user_content(row: dict[str, Any]) -> str:
    for message in row.get("messages", []):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def parse_aethermon_observation(row: dict[str, Any]) -> dict[str, Any] | None:
    text = user_content(row)
    marker = "observation:\n"
    if marker not in text:
        return None
    raw = text.split(marker, 1)[1].strip()
    value, _ = try_json(raw)
    return value if isinstance(value, dict) else None


def prediction_content_from_row(row: dict[str, Any]) -> str:
    for key in ("content", "prediction", "output", "response", "completion"):
        if key in row:
            value = row[key]
            return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=True)
    messages = row.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if message.get("role") == "assistant":
                return str(message.get("content", ""))
    return ""


def load_predictions(path: Path | None, rows: list[dict[str, Any]]) -> dict[str, str]:
    if path is None:
        return {}
    raw_predictions = read_jsonl(path)
    by_id: dict[str, str] = {}
    ordered: list[str] = []
    for item in raw_predictions:
        content = prediction_content_from_row(item)
        key = str(item.get("id") or item.get("row_id") or "")
        if key:
            by_id[key] = content
        ordered.append(content)
    if by_id:
        return by_id
    return {row_id(row): ordered[index] for index, row in enumerate(rows[: len(ordered)])}


def prediction_for(mode: str, row: dict[str, Any], predictions: dict[str, str]) -> tuple[str, bool]:
    rid = row_id(row)
    if mode == "oracle":
        return expected_content(row), True
    if mode == "abstain":
        return json.dumps({"abstain": True, "reason": "gate_closed_without_model"}, sort_keys=True), True
    if rid in predictions:
        return predictions[rid], True
    return json.dumps({"abstain": True, "reason": "missing_prediction", "row_id": rid}, sort_keys=True), False


def is_abstain(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    action = str(value.get("action", "")).upper()
    return bool(value.get("abstain") is True or action in {"ABSTAIN", "REFUSE", "UNKNOWN"})


def score_row(row: dict[str, Any], mode: str, predictions: dict[str, str]) -> dict[str, Any]:
    rid = row_id(row)
    expected_text = expected_content(row)
    expected_json, expected_error = try_json(expected_text)
    prediction_text, prediction_found = prediction_for(mode, row, predictions)
    prediction_json, prediction_error = try_json(prediction_text)
    meta = row.get("meta", {}) if isinstance(row.get("meta"), dict) else {}
    is_action_row = meta.get("domain") == "aethermon" and meta.get("kind") == "action_policy_tick"

    abstained = is_abstain(prediction_json)
    json_valid = prediction_json is not None
    trusted = json_valid and not abstained
    legal_action = None
    action_match = None
    expected_action = None
    predicted_action = None
    legal_actions: list[str] = []

    if is_action_row:
        observation = parse_aethermon_observation(row) or {}
        legal_actions = [str(item) for item in observation.get("legal_actions", [])]
        if isinstance(expected_json, dict):
            expected_action = expected_json.get("action")
        if isinstance(prediction_json, dict):
            predicted_action = prediction_json.get("action")
        legal_action = bool(predicted_action in legal_actions) if predicted_action and not abstained else False
        action_match = bool(predicted_action == expected_action) if predicted_action and not abstained else False
        trusted = bool(json_valid and not abstained and legal_action and action_match)

    return {
        "id": rid,
        "source": meta.get("source") or meta.get("adapter_mix_source") or "unknown",
        "domain": meta.get("domain"),
        "kind": meta.get("kind"),
        "prediction_found": prediction_found,
        "json_valid": json_valid,
        "abstained": abstained,
        "trusted": trusted,
        "expected_json_valid": expected_json is not None,
        "expected_json_error": expected_error,
        "prediction_json_error": prediction_error,
        "is_aethermon_action": is_action_row,
        "expected_action": expected_action,
        "predicted_action": predicted_action,
        "legal_action": legal_action,
        "action_match": action_match,
        "legal_actions": legal_actions,
    }


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def summarize(scores: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(scores)
    non_abstain = sum(1 for item in scores if not item["abstained"])
    action_scores = [item for item in scores if item["is_aethermon_action"]]
    action_non_abstain = [item for item in action_scores if not item["abstained"]]
    trusted = sum(1 for item in scores if item["trusted"])
    legal = sum(1 for item in action_scores if item["legal_action"] is True)
    matched = sum(1 for item in action_scores if item["action_match"] is True)
    summary = {
        "rows": total,
        "prediction_found": sum(1 for item in scores if item["prediction_found"]),
        "json_valid": sum(1 for item in scores if item["json_valid"]),
        "abstained": sum(1 for item in scores if item["abstained"]),
        "non_abstain": non_abstain,
        "trusted": trusted,
        "aethermon_action_rows": len(action_scores),
        "aethermon_action_non_abstain": len(action_non_abstain),
        "aethermon_legal_actions": legal,
        "aethermon_action_matches": matched,
    }
    summary["rates"] = {
        "json_valid": rate(summary["json_valid"], total),
        "abstain": rate(summary["abstained"], total),
        "trusted_precision_non_abstain": rate(trusted, non_abstain),
        "aethermon_legal_action": rate(legal, len(action_non_abstain)),
        "aethermon_action_match": rate(matched, len(action_non_abstain)),
    }
    summary["promotion_gate"] = {
        "ok": bool(
            total
            and summary["rates"]["json_valid"] >= 0.95
            and summary["rates"]["trusted_precision_non_abstain"] >= 0.8
            and summary["rates"]["aethermon_action_match"] >= 0.8
            and summary["rates"]["abstain"] <= 0.5
        ),
        "requires": {
            "json_valid_rate_min": 0.95,
            "trusted_precision_non_abstain_min": 0.8,
            "aethermon_action_match_min": 0.8,
            "abstain_rate_max": 0.5,
        },
    }
    return summary


def evaluate(holdout_path: Path, *, mode: str, predictions_path: Path | None, out_path: Path) -> dict[str, Any]:
    rows = read_jsonl(holdout_path)
    predictions = load_predictions(predictions_path, rows)
    scores = [score_row(row, mode, predictions) for row in rows]
    receipt = {
        "schema": "aethermon_agent_adapter_v0_eval_receipt",
        "generated_at": utc_now(),
        "source": "scripts/system/eval_aethermon_agent_adapter_v0.py",
        "mode": mode,
        "holdout": rel(holdout_path),
        "predictions": rel(predictions_path) if predictions_path else None,
        "summary": summarize(scores),
        "scores": scores,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate AETHERMON agent adapter v0 holdout predictions.")
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--mode", choices=["oracle", "abstain", "predictions"], default="oracle")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.mode == "predictions" and args.predictions is None:
        raise SystemExit("--predictions is required when --mode predictions")
    receipt = evaluate(args.holdout, mode=args.mode, predictions_path=args.predictions, out_path=args.out)
    if args.json:
        print(json.dumps({"ok": True, **receipt["summary"], "out": rel(args.out)}, indent=2, ensure_ascii=True))
    else:
        summary = receipt["summary"]
        print("AETHERMON adapter eval")
        print(f"  mode:              {args.mode}")
        print(f"  rows:              {summary['rows']}")
        print(f"  json valid:        {summary['rates']['json_valid']}")
        print(f"  abstain:           {summary['rates']['abstain']}")
        print(f"  trusted precision: {summary['rates']['trusted_precision_non_abstain']}")
        print(f"  action match:      {summary['rates']['aethermon_action_match']}")
        print(f"  promotion gate:    {summary['promotion_gate']['ok']}")
        print(f"  receipt:           {rel(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
