#!/usr/bin/env python3
"""Lightweight FastAPI server for receiving GitHub webhooks.

Validates X-Hub-Signature-256 via HMAC-SHA256, extracts a task summary from
the payload, and routes the event through the dual-tentacle lane system.

Start:
    python -m uvicorn scripts.system.github_webhook_server:app --host 127.0.0.1 --port 8002

Env:
    GITHUB_WEBHOOK_SECRET  — shared secret configured in the GitHub webhook settings.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Import lane primitives from the existing dual-tentacle router.
# ---------------------------------------------------------------------------
from scripts.system.github_dual_tentacle_router import (
    CLI_LANE,
    CODESPACES_LANE,
    CROSSTALK_LOG,
    LANE_ROOT,
    WEBHOOK_LANE,
    LanePacket,
    append_jsonl,
    choose_lane,
    lane_path,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SCBE GitHub Webhook Server",
    description="Receives GitHub webhooks and routes them into dual-tentacle lanes.",
    version="0.1.0",
)

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

LANE_FILES: dict[str, Path] = {
    "webhook_lane": WEBHOOK_LANE,
    "cli_lane": CLI_LANE,
    "codespaces_lane": CODESPACES_LANE,
    "cross_talk": CROSSTALK_LOG,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _verify_signature(body: bytes, signature_header: str | None) -> None:
    """Validate HMAC-SHA256 signature sent by GitHub.

    Raises HTTPException(403) when the signature is missing or invalid.
    """
    if not WEBHOOK_SECRET:
        # No secret configured — skip validation (development mode).
        return

    if not signature_header:
        raise HTTPException(status_code=403, detail="Missing X-Hub-Signature-256 header.")

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        raise HTTPException(status_code=403, detail="Invalid signature format.")

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[len(prefix):]

    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Signature verification failed.")


def _extract_task(event_type: str, payload: dict[str, Any]) -> str:
    """Pull a human-readable task summary from the webhook payload."""
    if event_type == "push":
        commits = payload.get("commits", [])
        if commits:
            return commits[-1].get("message", "push event").split("\n", 1)[0]
        return "push event (no commits)"

    if event_type == "pull_request":
        pr = payload.get("pull_request", {})
        action = payload.get("action", "")
        title = pr.get("title", "unknown PR")
        number = pr.get("number", "?")
        return f"{action} PR #{number}: {title}"

    if event_type == "issues":
        issue = payload.get("issue", {})
        action = payload.get("action", "")
        title = issue.get("title", "unknown issue")
        number = issue.get("number", "?")
        return f"{action} issue #{number}: {title}"

    if event_type in ("issue_comment", "pull_request_review_comment"):
        comment = payload.get("comment", {})
        body = (comment.get("body") or "")[:80]
        return f"comment: {body}"

    if event_type == "release":
        release = payload.get("release", {})
        tag = release.get("tag_name", "?")
        action = payload.get("action", "")
        return f"{action} release {tag}"

    if event_type == "workflow_run":
        run = payload.get("workflow_run", {})
        name = run.get("name", "workflow")
        conclusion = run.get("conclusion", "unknown")
        return f"workflow_run {name}: {conclusion}"

    if event_type == "check_run":
        check = payload.get("check_run", {})
        name = check.get("name", "check")
        status = check.get("status", "unknown")
        return f"check_run {name}: {status}"

    if event_type == "create" or event_type == "delete":
        ref = payload.get("ref", "?")
        ref_type = payload.get("ref_type", "?")
        return f"{event_type} {ref_type} {ref}"

    if event_type == "ping":
        hook_id = payload.get("hook_id", "?")
        return f"ping from hook {hook_id}"

    # Fallback: use action field if present, else generic.
    action = payload.get("action", "")
    return f"{event_type} {action}".strip() or f"handle {event_type} event"


def _count_lines(path: Path) -> int:
    """Count lines in a JSONL file, returning 0 if the file does not exist."""
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "github-webhook-server",
        "port": 8002,
        "lane_root": str(LANE_ROOT),
    }


@app.get("/lanes/status")
async def lanes_status() -> dict[str, Any]:
    counts = {name: _count_lines(path) for name, path in LANE_FILES.items()}
    return {
        "status": "ok",
        "lane_root": str(LANE_ROOT),
        "counts": counts,
        "total": sum(counts.values()),
    }


@app.post("/github/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> JSONResponse:
    body = await request.body()

    # 1. Validate signature.
    _verify_signature(body, x_hub_signature_256)

    # 2. Parse payload.
    try:
        payload: dict[str, Any] = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}")

    event_type = (x_github_event or "unknown").strip()

    # 3. Extract task summary from payload.
    task = _extract_task(event_type, payload)

    # 4. Route through dual-tentacle lane chooser.
    lane = choose_lane(event_type, task)

    # 5. Build lane packet.
    repo = ""
    if "repository" in payload:
        repo = payload["repository"].get("full_name", "")
    repo = repo or "SCBE-AETHERMOORE"

    packet_id = f"gh-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    packet = LanePacket(
        packet_id=packet_id,
        created_at=_utc_now(),
        sender="webhook.server",
        recipient_lane=lane,
        intent="webhook_ingest",
        status="received",
        repo=repo,
        event_type=event_type,
        task=task,
        payload=payload,
        next_action=f"Process task in {lane} and emit ack packet.",
        risk="low",
    )

    packet_dict = packet.to_dict()

    # 6. Append to the target lane JSONL.
    append_jsonl(lane_path(lane), packet_dict)

    # 7. Cross-talk mirror entry.
    append_jsonl(
        CROSSTALK_LOG,
        {
            "created_at": packet.created_at,
            "packet_id": packet.packet_id,
            "from": "webhook.server",
            "to": lane,
            "repo": repo,
            "event_type": event_type,
            "task": task,
            "status": "received",
            "risk": "low",
        },
    )

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "packet_id": packet_id,
            "lane": lane,
            "event_type": event_type,
            "task": task,
        },
    )


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")
