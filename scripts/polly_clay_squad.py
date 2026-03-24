#!/usr/bin/env python3
"""Polly + Clay squad orchestrator for governed multi-agent browser work.

Roles:
- Polly (leader): user-facing route controller and escalation manager
- Clay workers: concurrent execution lanes for browser actions

Design goals:
- Fast parallel execution via fixed worker pool
- Continuous operation option
- Lightweight human-in-the-loop (HITL) escalation artifacts
- Optional local browser service bootstrap
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import pathlib
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_ENDPOINT = "http://127.0.0.1:8001/v1/integrations/n8n/browse"
DEFAULT_CONTRACT_MAP = {
    "MIN": "polly_clay_min.json",
    "MID": "polly_clay_mid.json",
    "MAX": "polly_clay_max.json",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "item"


def _api_key(cli: Optional[str]) -> str:
    if cli and cli.strip():
        return cli.strip()
    for name in ("SCBE_API_KEY", "SCBE_BROWSER_API_KEY", "N8N_API_KEY", "BROWSER_AGENT_API_KEY"):
        token = os.getenv(name, "").strip()
        if token:
            return token
    raise RuntimeError("Missing API key (--api-key or SCBE_API_KEY/N8N_API_KEY)")


def _endpoint(cli: Optional[str]) -> str:
    if cli and cli.strip():
        return cli.strip()
    return os.getenv("SCBE_BROWSER_WEBHOOK_URL", DEFAULT_ENDPOINT).strip()


def _post(url: str, api_key: str, payload: Dict[str, Any], timeout_sec: int) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def _get_json(url: str, timeout_sec: int = 5) -> Dict[str, Any]:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_sec) as res:
        return json.loads(res.read().decode("utf-8"))


def _normalize_action(action: Dict[str, Any], order_index: int, action_index: int) -> Dict[str, Any]:
    a = dict(action)

    if "action" not in a and "type" in a:
        a["action"] = a["type"]

    if "target" not in a:
        if "url" in a:
            a["target"] = a["url"]
        elif "selector" in a:
            a["target"] = a["selector"]
        elif str(a.get("action", "")).strip().lower() == "screenshot":
            a["target"] = "full_page"

    if str(a.get("action", "")).strip().lower() == "type" and "value" not in a and "text" in a:
        a["value"] = a["text"]

    out = {
        "action": str(a.get("action", "")).strip().lower(),
        "target": str(a.get("target", "")).strip(),
    }

    if "value" in a and a["value"] is not None:
        out["value"] = str(a["value"])

    if "timeout_ms" in a and a["timeout_ms"] is not None:
        out["timeout_ms"] = int(a["timeout_ms"])

    if "include_full_data" in a:
        out["include_full_data"] = bool(a["include_full_data"])

    if not out["action"] or not out["target"]:
        raise ValueError(f"Order {order_index} action {action_index} missing action/target")

    return out


def _load_orders(path: pathlib.Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    orders = raw.get("orders")
    if not isinstance(orders, list) or not orders:
        raise ValueError("orders-file must contain non-empty orders[]")

    normalized: List[Dict[str, Any]] = []
    for oi, order in enumerate(orders, start=1):
        if not isinstance(order, dict):
            raise ValueError(f"Order {oi} must be an object")
        actions = order.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError(f"Order {oi} requires actions[]")
        prepared = dict(order)
        prepared["actions"] = [_normalize_action(dict(a), oi, ai) for ai, a in enumerate(actions, start=1)]
        if "order_id" not in prepared:
            prepared["order_id"] = f"order-{oi:03d}"
        normalized.append(prepared)

    return normalized


def _normalize_action_set(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out = sorted({str(v).strip().lower() for v in values if isinstance(v, (str, int, float)) and str(v).strip()})
    return out


def _parse_human_on(value: Optional[str], contract: Dict[str, Any]) -> set[str]:
    if value and value.strip():
        return {x.strip().upper() for x in str(value).split(",") if x.strip()}

    from_contract = contract.get("human_on")
    if isinstance(from_contract, list):
        parsed = {str(x).strip().upper() for x in from_contract if str(x).strip()}
        if parsed:
            return parsed

    return {"DENY", "ESCALATE", "QUARANTINE"}


def _load_risk_contract(contract_ref: str, repo_root: pathlib.Path) -> Dict[str, Any]:
    ref = str(contract_ref or "MID").strip()
    contracts_dir = (repo_root / "policies" / "contracts").resolve()

    alias = DEFAULT_CONTRACT_MAP.get(ref.upper())
    if alias:
        contract_path = (contracts_dir / alias).resolve()
    else:
        candidate = pathlib.Path(ref).expanduser()
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        contract_path = candidate.resolve()

    if not contract_path.exists():
        raise FileNotFoundError(f"Risk contract not found: {contract_path}")

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(contract, dict):
        raise ValueError("Risk contract must be a JSON object")

    risk_tier = str(contract.get("risk_tier", "")).strip().upper()
    if risk_tier not in {"MIN", "MID", "MAX"}:
        raise ValueError("Risk contract requires risk_tier in {MIN,MID,MAX}")

    allow_actions = _normalize_action_set(contract.get("allow_actions"))
    if not allow_actions:
        raise ValueError("Risk contract requires non-empty allow_actions[]")

    normalized = dict(contract)
    normalized["risk_tier"] = risk_tier
    normalized["allow_actions"] = allow_actions
    normalized["blocked_actions"] = _normalize_action_set(contract.get("blocked_actions"))
    normalized["require_human_for_actions"] = _normalize_action_set(contract.get("require_human_for_actions"))
    normalized["require_context_keys"] = [
        str(x).strip() for x in contract.get("require_context_keys", []) if str(x).strip()
    ]
    normalized["max_clays"] = int(contract.get("max_clays", 4) or 4)
    normalized["max_actions_per_request"] = int(contract.get("max_actions_per_request", 8) or 8)
    normalized["max_actions_per_order"] = int(contract.get("max_actions_per_order", 0) or 0)
    normalized["force_dry_run"] = bool(contract.get("force_dry_run", False))
    normalized["contract_id"] = str(contract.get("contract_id", f"POLLY_CLAY_{risk_tier}_V1"))
    normalized["_path"] = str(contract_path)

    hitl = contract.get("hitl") if isinstance(contract.get("hitl"), dict) else {}
    normalized["hitl"] = {
        "require_snapshot_on_escalation": bool(hitl.get("require_snapshot_on_escalation", True)),
        "auto_open_browser": bool(hitl.get("auto_open_browser", False)),
    }

    return normalized


def _route_orders_with_contract(
    orders: List[Dict[str, Any]],
    risk_contract: Dict[str, Any],
) -> Tuple[List[Tuple[int, Dict[str, Any]]], List[Dict[str, Any]]]:
    allowed = set(risk_contract.get("allow_actions", []))
    blocked = set(risk_contract.get("blocked_actions", []))
    require_human = set(risk_contract.get("require_human_for_actions", []))
    required_context_keys = list(risk_contract.get("require_context_keys", []))
    max_actions_per_order = int(risk_contract.get("max_actions_per_order", 0) or 0)
    force_dry_run = bool(risk_contract.get("force_dry_run", False))

    routed: List[Tuple[int, Dict[str, Any]]] = []
    blocked_results: List[Dict[str, Any]] = []

    for order_index, order in enumerate(orders, start=1):
        prepared = dict(order)
        prepared["_risk_tier"] = str(risk_contract.get("risk_tier", "MID"))

        reasons: List[str] = []
        hitl_reasons: List[str] = []

        actions = prepared.get("actions", [])
        if max_actions_per_order > 0 and len(actions) > max_actions_per_order:
            reasons.append(f"too_many_actions:{len(actions)}>{max_actions_per_order}")

        if required_context_keys:
            ctx = prepared.get("context", {})
            if not isinstance(ctx, dict):
                reasons.append("context_object_required")
            else:
                missing = [k for k in required_context_keys if not str(ctx.get(k, "")).strip()]
                if missing:
                    reasons.append(f"missing_context_keys:{','.join(missing)}")

        for action_index, action in enumerate(actions, start=1):
            action_name = str(action.get("action", "")).strip().lower()
            if action_name in blocked:
                reasons.append(f"blocked_action[{action_index}]={action_name}")
            if action_name not in allowed:
                reasons.append(f"not_allowed[{action_index}]={action_name}")
            if action_name in require_human:
                hitl_reasons.append(f"contract_review_required:action[{action_index}]={action_name}")

        if force_dry_run:
            prepared["dry_run"] = True

        if hitl_reasons:
            prepared["_contract_hitl_reasons"] = hitl_reasons

        if reasons:
            order_id = str(prepared.get("order_id", f"order-{order_index:03d}"))
            session_id = str(prepared.get("session_id", f"polly-gate-session-{order_index:03d}"))
            blocked_results.append(
                {
                    "order_id": order_id,
                    "order_index": order_index,
                    "clay_id": "polly-gate",
                    "session_id": session_id,
                    "request_error": "policy_blocked",
                    "needs_human": True,
                    "reasons": reasons,
                    "response": {
                        "status": "policy_blocked",
                        "session_id": session_id,
                        "results": [],
                        "total_actions": len(actions),
                        "executed_actions": 0,
                        "blocked_actions": len(actions),
                        "trace": "policy_blocked",
                    },
                    "hitl_snapshot": {},
                    "elapsed_ms": 0.0,
                    "risk_tier": prepared.get("_risk_tier"),
                }
            )
            continue

        routed.append((order_index, prepared))

    return routed, blocked_results


def _chunk(actions: List[Dict[str, Any]], max_actions: int) -> List[List[Dict[str, Any]]]:
    if max_actions <= 0:
        return [actions]
    return [actions[i : i + max_actions] for i in range(0, len(actions), max_actions)]


def _response_needs_human(
    response: Dict[str, Any],
    human_on: set[str],
    request_error: Optional[str],
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    if request_error:
        reasons.append(f"request_error:{request_error}")

    status = str(response.get("status", "")).strip().lower()
    if status not in {"success", "ok"}:
        reasons.append(f"status:{status or 'unknown'}")

    blocked = int(response.get("blocked_actions", 0) or 0)
    if blocked > 0:
        reasons.append(f"blocked_actions:{blocked}")

    results = response.get("results", [])
    if isinstance(results, list):
        for idx, row in enumerate(results, start=1):
            if not isinstance(row, dict):
                continue
            containment = row.get("containment", {})
            decision = str(containment.get("decision", "")).strip().upper() if isinstance(containment, dict) else ""
            if decision and decision in human_on:
                reasons.append(f"decision[{idx}]={decision}")

    return (len(reasons) > 0), reasons


def _extract_first_screenshot_b64(response: Dict[str, Any]) -> Optional[str]:
    rows = response.get("results", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        data = row.get("data", {})
        if not isinstance(data, dict):
            continue
        shot = data.get("screenshot")
        if isinstance(shot, str) and shot.strip():
            return shot.strip()
    return None


def _extract_text_preview(response: Dict[str, Any], max_chars: int = 1000) -> str:
    rows = response.get("results", [])
    if not isinstance(rows, list):
        return ""
    chunks: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        data = row.get("data", {})
        if not isinstance(data, dict):
            continue
        txt = data.get("text")
        if isinstance(txt, str) and txt.strip():
            chunks.append(txt.strip())
    if not chunks:
        return ""
    combined = "\n".join(chunks)
    return combined[:max_chars]


def _fetch_hitl_snapshot(
    endpoint: str,
    api_key: str,
    session_id: str,
    timeout_sec: int,
) -> Dict[str, Any]:
    payload = {
        "session_id": session_id,
        "source": "polly-hitl",
        "workflow_id": "polly-hitl-snapshot",
        "run_id": f"hitl-{int(time.time())}",
        "dry_run": False,
        "actions": [
            {"action": "screenshot", "target": "full_page", "include_full_data": True, "timeout_ms": 20000},
            {"action": "extract", "target": "body", "timeout_ms": 12000},
        ],
    }
    return _post(endpoint, api_key, payload, timeout_sec)


def _save_png_from_b64(value: str, path: pathlib.Path) -> bool:
    s = value.strip()
    if not s or s.endswith("..."):
        return False
    try:
        data = base64.b64decode(s, validate=True)
    except Exception:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def _build_html(hitl_items: List[Dict[str, Any]], html_path: pathlib.Path, screenshot_dir: pathlib.Path) -> None:
    cards: List[str] = []
    for item in hitl_items:
        order_id = html.escape(str(item.get("order_id", "")))
        clay_id = html.escape(str(item.get("clay_id", "")))
        reasons = "<br>".join(html.escape(str(r)) for r in item.get("reasons", []))
        text_preview = html.escape(str(item.get("text_preview", "")))
        shot_file = item.get("screenshot_file")
        shot_html = "<div class='muted'>No full screenshot captured</div>"
        if isinstance(shot_file, str) and shot_file:
            rel = html.escape(str(pathlib.Path("screenshots") / pathlib.Path(shot_file).name))
            shot_html = f"<a href='{rel}' target='_blank'><img src='{rel}' alt='screenshot'></a>"

        cards.append(
            f"""
<section class='card'>
  <h3>{order_id} <span class='muted'>({clay_id})</span></h3>
  <p><strong>Reasons:</strong><br>{reasons}</p>
  <details>
    <summary>Content preview</summary>
    <pre>{text_preview}</pre>
  </details>
  {shot_html}
</section>
""".strip()
        )

    body = "\n".join(cards) if cards else "<p>No pending HITL items.</p>"

    html_doc = f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Polly HITL Dashboard</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 1rem; background: #0e1318; color: #e8eef5; }}
h1 {{ margin: 0 0 0.4rem 0; }}
p {{ line-height: 1.4; }}
.grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
.card {{ background: #18222c; border: 1px solid #2f3e4e; border-radius: 10px; padding: 0.8rem; }}
.muted {{ color: #b3c0cc; }}
img {{ width: 100%; height: auto; border: 1px solid #2f3e4e; border-radius: 8px; }}
pre {{ white-space: pre-wrap; background: #0b1117; border: 1px solid #2f3e4e; padding: 0.6rem; border-radius: 8px; max-height: 240px; overflow: auto; }}
code {{ background: #0b1117; padding: 0.1rem 0.3rem; border-radius: 5px; }}
</style>
</head>
<body>
<h1>Polly HITL Dashboard</h1>
<p class='muted'>Generated at {_now_iso()} | Items: {len(hitl_items)}</p>
<div class='grid'>
{body}
</div>
</body>
</html>
"""

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_doc, encoding="utf-8")


def _start_local_service(host: str, port: int, api_key: str, repo_root: pathlib.Path) -> subprocess.Popen[str]:
    env = dict(os.environ)
    env["SCBE_API_KEY"] = api_key
    env["N8N_API_KEY"] = api_key

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "agents.browser.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    proc = subprocess.Popen(cmd, cwd=str(repo_root), env=env)

    health_url = f"http://{host}:{port}/health"
    for _ in range(40):
        time.sleep(0.5)
        try:
            _get_json(health_url, timeout_sec=3)
            return proc
        except Exception:
            continue

    proc.terminate()
    raise RuntimeError(f"Local browser service failed to start: {health_url}")


def _run_order(
    order: Dict[str, Any],
    order_index: int,
    clay_id: str,
    endpoint: str,
    api_key: str,
    timeout_sec: int,
    max_actions_per_request: int,
    human_on: set[str],
    fetch_hitl_snapshot: bool,
) -> Dict[str, Any]:
    order_id = str(order.get("order_id", f"order-{order_index:03d}"))
    session_id = str(order.get("session_id", f"{clay_id}-session-{order_index:03d}"))

    actions = order["actions"]
    chunks = _chunk(actions, max_actions_per_request)

    base_payload = {
        "session_id": session_id,
        "source": str(order.get("source", "polly-clay")),
        "workflow_id": str(order.get("workflow_id", "polly-clay-route")),
        "run_id": str(order.get("run_id", f"run-{int(time.time())}-{order_index}")),
        "dry_run": bool(order.get("dry_run", False)),
    }

    start = time.time()
    request_error: Optional[str] = None
    traces: List[str] = []
    merged_results: List[Dict[str, Any]] = []
    blocked_actions = 0

    try:
        for ci, chunk in enumerate(chunks, start=1):
            payload = {
                **base_payload,
                "actions": chunk,
                "chunk_index": ci,
                "chunk_count": len(chunks),
            }
            response = _post(endpoint, api_key, payload, timeout_sec)
            if isinstance(response.get("results"), list):
                merged_results.extend(response["results"])
            blocked_actions += int(response.get("blocked_actions", 0) or 0)
            trace = response.get("trace")
            if isinstance(trace, str):
                traces.append(trace)
    except Exception as exc:
        request_error = str(exc)

    aggregated = {
        "status": "request_error" if request_error else "success",
        "session_id": session_id,
        "results": merged_results,
        "total_actions": len(actions),
        "executed_actions": len(merged_results),
        "blocked_actions": blocked_actions,
        "trace": "|".join(traces) if traces else ("request_error" if request_error else "ok"),
    }

    needs_human, reasons = _response_needs_human(aggregated, human_on=human_on, request_error=request_error)

    contract_reasons = [str(x).strip() for x in order.get("_contract_hitl_reasons", []) if str(x).strip()]
    if contract_reasons:
        needs_human = True
        reasons.extend(contract_reasons)

    hitl_snapshot: Dict[str, Any] = {}
    if needs_human and fetch_hitl_snapshot:
        try:
            hitl_snapshot = _fetch_hitl_snapshot(endpoint, api_key, session_id=session_id, timeout_sec=timeout_sec)
        except Exception as exc:
            reasons.append(f"snapshot_error:{exc}")

    elapsed_ms = round((time.time() - start) * 1000.0, 2)

    return {
        "order_id": order_id,
        "risk_tier": str(order.get("_risk_tier", "")),
        "order_index": order_index,
        "clay_id": clay_id,
        "session_id": session_id,
        "request_error": request_error,
        "needs_human": needs_human,
        "reasons": reasons,
        "response": aggregated,
        "hitl_snapshot": hitl_snapshot,
        "elapsed_ms": elapsed_ms,
    }


def _write_hitl_artifacts(
    items: List[Dict[str, Any]],
    hitl_dir: pathlib.Path,
    open_browser: bool,
) -> Dict[str, Any]:
    hitl_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir = hitl_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    queue_path = hitl_dir / "queue.jsonl"
    html_path = hitl_dir / "index.html"

    processed: List[Dict[str, Any]] = []
    with queue_path.open("w", encoding="utf-8") as f:
        for item in items:
            snapshot = item.get("hitl_snapshot", {}) if isinstance(item.get("hitl_snapshot"), dict) else {}
            shot = _extract_first_screenshot_b64(snapshot)
            text_preview = _extract_text_preview(snapshot)

            shot_file = ""
            if isinstance(shot, str) and shot and not shot.endswith("..."):
                candidate = screenshots_dir / f"{_slug(item['order_id'])}_{_slug(item['clay_id'])}.png"
                if _save_png_from_b64(shot, candidate):
                    shot_file = str(candidate)

            row = {
                "created_at_utc": _now_iso(),
                "order_id": item["order_id"],
                "clay_id": item["clay_id"],
                "session_id": item["session_id"],
                "reasons": item.get("reasons", []),
                "text_preview": text_preview,
                "screenshot_file": shot_file,
                "response_trace": item.get("response", {}).get("trace"),
            }
            processed.append(row)
            f.write(json.dumps(row, sort_keys=True) + "\n")

    _build_html(processed, html_path=html_path, screenshot_dir=screenshots_dir)

    if open_browser and processed:
        try:
            webbrowser.open(html_path.resolve().as_uri())
        except Exception:
            pass

    return {
        "hitl_items": len(processed),
        "queue_jsonl": str(queue_path),
        "dashboard_html": str(html_path),
    }


def _run_once(
    orders: List[Dict[str, Any]],
    endpoint: str,
    api_key: str,
    clays: int,
    timeout_sec: int,
    max_actions_per_request: int,
    leader_name: str,
    human_on: set[str],
    hitl_dir: pathlib.Path,
    open_hitl_browser: bool,
    output_json: pathlib.Path,
    risk_contract: Dict[str, Any],
) -> Dict[str, Any]:
    routed_orders, blocked_by_contract = _route_orders_with_contract(orders, risk_contract)

    work_q: "queue.Queue[Tuple[int, Dict[str, Any]]]" = queue.Queue()
    for order_index, order in routed_orders:
        work_q.put((order_index, order))

    results: List[Dict[str, Any]] = list(blocked_by_contract)
    lock = threading.Lock()

    fetch_hitl_snapshot = bool(risk_contract.get("hitl", {}).get("require_snapshot_on_escalation", True))

    def worker(worker_idx: int) -> None:
        clay_id = f"clay-{worker_idx:02d}"
        while True:
            try:
                order_index, order = work_q.get_nowait()
            except queue.Empty:
                break
            try:
                out = _run_order(
                    order=order,
                    order_index=order_index,
                    clay_id=clay_id,
                    endpoint=endpoint,
                    api_key=api_key,
                    timeout_sec=timeout_sec,
                    max_actions_per_request=max_actions_per_request,
                    human_on=human_on,
                    fetch_hitl_snapshot=fetch_hitl_snapshot,
                )
                with lock:
                    results.append(out)
            finally:
                work_q.task_done()

    threads: List[threading.Thread] = []
    for i in range(1, max(1, clays) + 1):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    results_sorted = sorted(results, key=lambda x: int(x.get("order_index", 0)))

    hitl_items = [r for r in results_sorted if r.get("needs_human")]
    hitl_meta = _write_hitl_artifacts(hitl_items, hitl_dir=hitl_dir, open_browser=open_hitl_browser)

    success_count = sum(1 for r in results_sorted if not r.get("request_error"))
    summary = {
        "generated_at_utc": _now_iso(),
        "leader": leader_name,
        "clays": clays,
        "endpoint": endpoint,
        "total_orders": len(orders),
        "routed_orders": len(routed_orders),
        "blocked_by_contract": len(blocked_by_contract),
        "success_orders": success_count,
        "failed_orders": len(orders) - success_count,
        "needs_human": len(hitl_items),
        "human_on": sorted(list(human_on)),
        "risk_contract": {
            "contract_id": risk_contract.get("contract_id"),
            "risk_tier": risk_contract.get("risk_tier"),
            "path": risk_contract.get("_path"),
        },
        "results": results_sorted,
        "hitl": hitl_meta,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Polly+Clay governed browser squad")
    parser.add_argument("--orders-file", required=True, help="JSON file containing orders[]")
    parser.add_argument("--url", default=None, help="Browser endpoint URL")
    parser.add_argument("--api-key", default=None, help="API key (or env var)")
    parser.add_argument("--risk-contract", default="MID", help="MIN | MID | MAX or path to contract JSON")
    parser.add_argument("--clays", type=int, default=4, help="Number of Clay worker lanes")
    parser.add_argument("--leader", default="Polly", help="Leader label")
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--max-actions-per-request", type=int, default=None)
    parser.add_argument("--human-on", default=None, help="Comma-separated containment decisions requiring HITL")
    parser.add_argument("--output-json", default="artifacts/polly_clay/summary_latest.json")
    parser.add_argument("--hitl-dir", default="artifacts/polly_clay/hitl")
    parser.add_argument("--open-hitl-browser", action="store_true", help="Open local HITL dashboard if items exist")

    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--poll-sec", type=int, default=30, help="Seconds between continuous loops")

    parser.add_argument("--start-local-service", action="store_true", help="Launch local browser service before run")
    parser.add_argument("--service-host", default="127.0.0.1")
    parser.add_argument("--service-port", type=int, default=8001)

    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    orders_path = pathlib.Path(args.orders_file).expanduser().resolve()
    output_json = pathlib.Path(args.output_json).expanduser().resolve()
    hitl_dir = pathlib.Path(args.hitl_dir).expanduser().resolve()

    api_key = _api_key(args.api_key)
    endpoint = _endpoint(args.url)

    risk_contract = _load_risk_contract(args.risk_contract, repo_root=repo_root)
    human_on = _parse_human_on(args.human_on, risk_contract)

    contract_max_actions = int(risk_contract.get("max_actions_per_request", 8) or 8)
    max_actions_per_request = (
        int(args.max_actions_per_request) if args.max_actions_per_request is not None else contract_max_actions
    )
    if max_actions_per_request <= 0:
        raise ValueError("max-actions-per-request must be > 0")

    contract_max_clays = int(risk_contract.get("max_clays", args.clays) or args.clays)
    effective_clays = max(1, min(max(1, args.clays), max(1, contract_max_clays)))
    if effective_clays != args.clays:
        print(
            f"[polly] clays capped by contract ({risk_contract.get('risk_tier')}): "
            f"requested={args.clays} effective={effective_clays}"
        )

    open_hitl_browser = bool(args.open_hitl_browser or risk_contract.get("hitl", {}).get("auto_open_browser", False))

    service_proc: Optional[subprocess.Popen[str]] = None
    if args.start_local_service:
        endpoint = f"http://{args.service_host}:{args.service_port}/v1/integrations/n8n/browse"
        service_proc = _start_local_service(args.service_host, args.service_port, api_key=api_key, repo_root=repo_root)

    try:
        if not args.continuous:
            orders = _load_orders(orders_path)
            summary = _run_once(
                orders=orders,
                endpoint=endpoint,
                api_key=api_key,
                clays=effective_clays,
                timeout_sec=args.timeout_sec,
                max_actions_per_request=max_actions_per_request,
                leader_name=args.leader,
                human_on=human_on,
                hitl_dir=hitl_dir,
                open_hitl_browser=open_hitl_browser,
                output_json=output_json,
                risk_contract=risk_contract,
            )
            print(
                json.dumps(
                    {
                        "leader": summary["leader"],
                        "risk_tier": summary["risk_contract"]["risk_tier"],
                        "total_orders": summary["total_orders"],
                        "blocked_by_contract": summary["blocked_by_contract"],
                        "success_orders": summary["success_orders"],
                        "needs_human": summary["needs_human"],
                        "summary": str(output_json),
                        "hitl_dashboard": summary["hitl"]["dashboard_html"],
                    },
                    indent=2,
                )
            )
            return 0

        loop_count = 0
        while True:
            loop_count += 1
            orders = _load_orders(orders_path)
            run_output = output_json.with_name(f"{output_json.stem}.loop{loop_count:04d}{output_json.suffix}")
            summary = _run_once(
                orders=orders,
                endpoint=endpoint,
                api_key=api_key,
                clays=effective_clays,
                timeout_sec=args.timeout_sec,
                max_actions_per_request=max_actions_per_request,
                leader_name=args.leader,
                human_on=human_on,
                hitl_dir=hitl_dir,
                open_hitl_browser=open_hitl_browser,
                output_json=run_output,
                risk_contract=risk_contract,
            )
            output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(
                f"[loop {loop_count}] tier={summary['risk_contract']['risk_tier']} "
                f"success={summary['success_orders']}/{summary['total_orders']} "
                f"blocked={summary['blocked_by_contract']} needs_human={summary['needs_human']}"
            )
            time.sleep(max(1, args.poll_sec))

    except KeyboardInterrupt:
        print("Interrupted by user")
        return 130
    finally:
        if service_proc and service_proc.poll() is None:
            service_proc.terminate()
            try:
                service_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
