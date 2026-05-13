#!/usr/bin/env python3
"""Build an autonomous autopromo campaign for the Workflow Snapshot offer.

The goal is to make marketing an output of the SCBE workflow rather than a
fresh blank-page task. This script reads the live offer catalog, generates
channel-specific campaign assets, self-reviews them, revises weak items, and
writes a machine-readable publish queue. It does not post without a connected
publisher credential.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OFFERS_PATH = REPO_ROOT / "docs" / "offers.json"
OUT_ROOT = REPO_ROOT / "artifacts" / "revenue" / "workflow_snapshot_autopromo"
OFFER_ID = "workflow_snapshot_starter"
DEFAULT_ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_offer(path: Path = OFFERS_PATH, offer_id: str = OFFER_ID) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    for offer in catalog.get("offers", []):
        if offer.get("id") == offer_id:
            result = dict(offer)
            result["site_base"] = catalog.get("site_base", "")
            result["usage_policy"] = catalog.get("usage_policy", {})
            result["payment_methods"] = catalog.get("payment_methods", {})
            return result
    raise ValueError(f"offer not found: {offer_id}")


def _load_env_file(path: Path) -> dict[str, bool]:
    loaded: dict[str, bool] = {}
    if not path.exists():
        return loaded
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded[key] = bool(value)
    return loaded


def _link(offer: dict[str, Any], key: str, fallback: str = "") -> str:
    value = offer.get(key)
    return str(value) if value else fallback


def _cash_app(offer: dict[str, Any]) -> str:
    alternate = offer.get("alternate_checkout", {})
    if isinstance(alternate, dict) and alternate.get("cash_app"):
        return str(alternate["cash_app"])
    payment_methods = offer.get("payment_methods", {})
    cash_app = payment_methods.get("cash_app", {}) if isinstance(payment_methods, dict) else {}
    if isinstance(cash_app, dict):
        return str(cash_app.get("cashtag", ""))
    return ""


def _offer_summary(offer: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": offer["id"],
        "name": offer["name"],
        "price_label": offer["price_label"],
        "status": offer["status"],
        "proof_url": _link(offer, "proof_url"),
        "checkout_url": _link(offer, "checkout_url"),
        "cash_app": _cash_app(offer),
        "scope": offer.get("scope", []),
        "checkout_note": offer.get("checkout_note", ""),
    }


def _campaign_items(offer: dict[str, Any]) -> list[dict[str, Any]]:
    proof_url = _link(offer, "proof_url")
    checkout_url = _link(offer, "checkout_url")
    cash_app = _cash_app(offer)
    price = str(offer["price_label"])
    short_offer = (
        "AI Agent Workflow Snapshot: a fixed-scope read of one agent workflow, "
        "repo, prompt chain, MCP stack, or automation flow."
    )
    outcome = (
        "You get a concise findings memo covering drift risks, unsafe tool paths, "
        "missing recovery states, observability gaps, prompt-injection surfaces, "
        "and three prioritized fixes."
    )
    payment_line = (
        f"Start here: {proof_url}. Pay through Stripe checkout: {checkout_url}. "
        f"Cash App is also available: {cash_app}."
    )
    return [
        {
            "id": "x_thread",
            "channel": "x",
            "format": "thread",
            "risk": "low",
            "goal": "one founder or developer clicks the offer page",
            "posts": [
                (
                    "I added a small fixed-scope offer for people building AI agents: "
                    f"{short_offer} {price}. {proof_url}"
                ),
                (
                    "The point is not a giant consulting engagement. It is one clear pass over a workflow: "
                    "where can it drift, loop, misuse tools, lose logs, or fail without recovery?"
                ),
                (
                    "Deliverable: a concise findings memo, three prioritized fixes, and a path to a deeper "
                    "governance snapshot only if the workflow actually needs it."
                ),
                (
                    "Good fit: CrewAI, LangGraph, MCP stacks, local Ollama flows, custom automation chains, "
                    "AI coding agents, or prompt/tool workflows that keep breaking."
                ),
                payment_line,
            ],
        },
        {
            "id": "linkedin_post",
            "channel": "linkedin",
            "format": "post",
            "risk": "low",
            "goal": "one technical operator replies with a workflow",
            "text": (
                f"I opened a fixed-scope {price} AI Agent Workflow Snapshot.\n\n"
                "It is for small teams, solo founders, and developers who already have an AI agent or automation flow, "
                "but need a second set of eyes on where it can break.\n\n"
                f"{outcome}\n\n"
                "Good inputs: GitHub repo, agent diagram, prompt chain, MCP/tool stack, LangGraph/CrewAI setup, "
                "or a short description of the workflow.\n\n"
                f"Offer page: {proof_url}\n"
                f"Checkout: {checkout_url}\n"
                f"Cash App: {cash_app}"
            ),
        },
        {
            "id": "reddit_sideproject",
            "channel": "reddit",
            "format": "discussion_draft",
            "risk": "medium",
            "goal": "ask for workflows to review without sounding like spam",
            "title": "I made a small AI-agent workflow review offer. What failure modes should the example report include?",
            "text": (
                "I am turning my AI-agent governance work into a small fixed-scope review: one workflow in, "
                "one findings memo out.\n\n"
                "The review looks for drift, unsafe tool paths, missing recovery states, observability gaps, "
                "and prompt-injection surfaces. The goal is practical: three fixes the builder can apply.\n\n"
                "I am not trying to pitch a giant platform. I am trying to make a useful small product for people "
                "already building agents. What would you want to see in a sample report before buying something "
                "like this?\n\n"
                f"Current offer page for context: {proof_url}"
            ),
        },
        {
            "id": "github_discussion",
            "channel": "github",
            "format": "discussion_post",
            "risk": "low",
            "goal": "convert npm/GitHub users into a service-credit buyer",
            "title": "New fixed-scope AI Agent Workflow Snapshot",
            "text": (
                "I added a fixed-scope Workflow Snapshot for builders using the SCBE stack or similar agent workflows.\n\n"
                f"{outcome}\n\n"
                "Useful inputs include a repo link, agent routing diagram, prompt chain, MCP tool setup, or failed automation trace.\n\n"
                f"Offer: {proof_url}\n"
                f"Price: {price}\n"
                f"Payment: Stripe checkout or Cash App {cash_app}\n\n"
                "This is intentionally small: one workflow, one readable memo, three prioritized fixes."
            ),
        },
        {
            "id": "hf_community",
            "channel": "huggingface",
            "format": "community_post",
            "risk": "low",
            "goal": "reach model/dataset users who already understand evals",
            "title": "AI agent workflow review for local and hybrid model stacks",
            "text": (
                "I am offering a small Workflow Snapshot for AI-agent and local-model automation stacks.\n\n"
                "The review is not about claiming a model is good or bad. It checks the workflow around the model: "
                "routing, recovery, logs, tool boundaries, drift points, and observable failure states.\n\n"
                f"Price: {price}. Offer page: {proof_url}\n\n"
                "Best fit: local Ollama flows, HF Router experiments, custom CLI agents, benchmark harnesses, "
                "and teams trying to make smaller/free models useful through better orchestration."
            ),
        },
        {
            "id": "email_warm",
            "channel": "email",
            "format": "warm_email",
            "risk": "low",
            "goal": "send only to people who already know the work or asked about agents",
            "subject": "Small AI workflow review offer",
            "text": (
                "Hi,\n\n"
                "I added a small fixed-scope offer for AI-agent workflows.\n\n"
                f"{short_offer}\n\n"
                f"{outcome}\n\n"
                f"It is {price}. The page is here: {proof_url}\n\n"
                "If you have one workflow that keeps breaking, send the repo/diagram/prompt chain and I can do the first pass.\n\n"
                "- Issac"
            ),
        },
    ]


def _send_plan(offer: dict[str, Any], drafts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "ready_to_publish_when_connector_is_available",
        "generated_at_utc": _now_iso(),
        "offer_id": offer["id"],
        "offer_url": _link(offer, "proof_url"),
        "default_price": offer["price_label"],
        "principles": [
            "Do not mass-send cold private messages.",
            "Do not claim guaranteed revenue, certification, legal advice, or compliance approval.",
            "Prefer public posts, warm contacts, and communities where AI-agent workflow review is relevant.",
            "If a platform dislikes promotional posts, use the question-style draft instead.",
            "Keep payment simple: offer page first, Ko-fi or Cash App only until the exact Stripe link exists.",
        ],
        "daily_budget_minutes": 20,
        "autonomous_loop": [
            "Publish one public item through the first connected safe channel.",
            "If no publisher credential exists, enqueue the item and stop without asking the user to rewrite it.",
            "Check for replies or clicks on the next cycle.",
            "Use objections and clicks to select the next item.",
            "Regenerate the campaign when offer text, price, or payment links change.",
        ],
        "campaign_item_ids": [str(draft["id"]) for draft in drafts],
    }


def _text_for_scoring(item: dict[str, Any]) -> str:
    pieces: list[str] = []
    for key in ("title", "subject", "text"):
        if item.get(key):
            pieces.append(str(item[key]))
    for post in item.get("posts", []) if isinstance(item.get("posts"), list) else []:
        pieces.append(str(post))
    return "\n".join(pieces)


def _score_item(item: dict[str, Any], offer: dict[str, Any]) -> dict[str, Any]:
    text = _text_for_scoring(item)
    proof_url = _link(offer, "proof_url")
    score = 0
    checks: dict[str, bool] = {
        "has_offer_url": proof_url in text,
        "has_price": str(offer["price_label"]) in text or "$99" in text,
        "names_buyer_or_workflow": any(word in text.lower() for word in ["agent", "workflow", "automation", "mcp"]),
        "names_deliverable": any(word in text.lower() for word in ["memo", "fixes", "findings", "review"]),
        "avoids_guarantee": not any(word in text.lower() for word in ["guaranteed", "certified", "legal advice"]),
    }
    score += sum(20 for ok in checks.values() if ok)
    return {"score": score, "checks": checks, "passed": score >= 80 and all(checks.values())}


def _revise_item(item: dict[str, Any], offer: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    if score["passed"]:
        return item
    proof_url = _link(offer, "proof_url")
    price = str(offer["price_label"])
    repair_line = (
        f" Offer: AI Agent Workflow Snapshot ({price}). Deliverable: concise findings memo "
        f"with three prioritized fixes. Page: {proof_url}"
    )
    revised = dict(item)
    if "posts" in revised and isinstance(revised["posts"], list):
        posts = [str(post) for post in revised["posts"]]
        if posts:
            posts[-1] = posts[-1].rstrip() + repair_line
        revised["posts"] = posts
    else:
        revised["text"] = str(revised.get("text", "")).rstrip() + "\n\n" + repair_line.strip()
    revised["auto_revised"] = True
    return revised


def _self_review_campaign(
    items: list[dict[str, Any]], offer: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    final_items: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    for item in items:
        initial = _score_item(item, offer)
        revised = _revise_item(item, offer, initial)
        final = _score_item(revised, offer)
        final_item = dict(revised)
        final_item["quality_gate"] = final
        final_item["status"] = "ready_to_publish" if final["passed"] else "needs_connector_or_offer_fix"
        final_items.append(final_item)
        reviews.append(
            {
                "id": item["id"],
                "initial": initial,
                "final": final,
                "auto_revised": bool(final_item.get("auto_revised", False)),
            }
        )
    return final_items, reviews


def _connector_status() -> dict[str, Any]:
    envs = {
        "n8n_x_ops": {
            "endpoint_env": "N8N_X_OPS_WEBHOOK_URL",
            "token_env": "N8N_X_OPS_API_KEY",
            "ready": bool(os.environ.get("N8N_X_OPS_WEBHOOK_URL", "").strip()),
        },
        "scbe_x": {
            "endpoint_env": "SCBE_X_WEBHOOK_URL",
            "token_env": "SCBE_X_WEBHOOK_TOKEN",
            "ready": bool(os.environ.get("SCBE_X_WEBHOOK_URL", "").strip()),
        },
        "github": {
            "endpoint_env": "GITHUB_TOKEN",
            "token_env": "GITHUB_TOKEN",
            "ready": bool(os.environ.get("GITHUB_TOKEN", "").strip() or os.environ.get("GH_TOKEN", "").strip()),
        },
        "huggingface": {
            "endpoint_env": "HF_TOKEN",
            "token_env": "HF_TOKEN",
            "ready": bool(
                os.environ.get("HF_TOKEN", "").strip()
                or os.environ.get("HUGGINGFACE_TOKEN", "").strip()
                or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
            ),
        },
        "bluesky": {
            "endpoint_env": "BLUESKY_HANDLE",
            "token_env": "BLUESKY_APP_PASSWORD",
            "ready": bool(
                os.environ.get("BLUESKY_HANDLE", "").strip() and os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
            ),
        },
    }
    return {
        name: {
            "ready": data["ready"],
            "endpoint_env": data["endpoint_env"],
            "token_env": data["token_env"],
        }
        for name, data in envs.items()
    }


def _x_text(item: dict[str, Any]) -> str:
    if item.get("channel") == "x" and isinstance(item.get("posts"), list):
        return "\n\n".join(str(post) for post in item["posts"])
    return _text_for_scoring(item)


def _build_x_ops_queue(campaign_items: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in campaign_items:
        channel = str(item.get("channel", ""))
        if channel not in {"x", "linkedin", "github", "huggingface"}:
            continue
        if item.get("status") != "ready_to_publish":
            continue
        items.append(
            {
                "action": "post",
                "campaign": "workflow_snapshot_starter",
                "source_id": item["id"],
                "channel": channel,
                "text": _x_text(item),
                "url": item.get("offer_url", ""),
                "quality_gate": item.get("quality_gate", {}),
            }
        )
    return {"items": items}


def _build_bluesky_queue(campaign_items: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in campaign_items:
        if item.get("status") != "ready_to_publish":
            continue
        channel = str(item.get("channel", ""))
        if channel not in {"x", "linkedin", "huggingface"}:
            continue
        text = (
            "AI agent workflow keep breaking? I opened a $99 Workflow Snapshot: "
            "one repo/diagram/prompt chain in, one concise findings memo out, "
            "with drift/tool/recovery/logging risks and 3 fixes.\n\n"
            "https://aethermoore.com/SCBE-AETHERMOORE/workflow-snapshot.html"
        )
        items.append(
            {
                "action": "post",
                "campaign": "workflow_snapshot_starter",
                "source_id": item["id"],
                "platform": "bluesky",
                "text": text,
                "quality_gate": item.get("quality_gate", {}),
            }
        )
    return {"items": items}


def _operator_markdown(offer: dict[str, Any], drafts: list[dict[str, Any]], send_plan: dict[str, Any]) -> str:
    summary = _offer_summary(offer)
    lines = [
        "# Workflow Snapshot Autopromo Packet",
        "",
        "This packet turns the live offer into an autonomous marketing campaign. It is not a strategy doc.",
        "",
        "## Offer",
        f"- Name: {summary['name']}",
        f"- Price: {summary['price_label']}",
        f"- Page: {summary['proof_url']}",
        f"- Checkout: {summary['checkout_url']}",
        f"- Cash App: {summary['cash_app']}",
        "",
        "## Autonomous Loop",
    ]
    for item in send_plan["autonomous_loop"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Ready Campaign Items"])
    for draft in drafts:
        lines.extend(["", f"### {draft['id']} ({draft['channel']})"])
        if "title" in draft:
            lines.extend(["Title:", "```text", str(draft["title"]), "```"])
        if "subject" in draft:
            lines.extend(["Subject:", "```text", str(draft["subject"]), "```"])
        if "posts" in draft:
            for index, post in enumerate(draft["posts"], start=1):
                lines.extend([f"Post {index}:", "```text", str(post), "```"])
        else:
            lines.extend(["Body:", "```text", str(draft["text"]), "```"])
    lines.extend(
        [
            "",
            "## Connector Rule",
            "- If X/n8n, GitHub, Hugging Face, Bluesky, or another publisher credential is connected, the queue can be consumed by an automation runner.",
            "- If no publisher credential is connected in this shell, the campaign is still complete and waits in the queue.",
            "- Do not send cold private-message batches.",
            "- Do not fabricate customers, case studies, certifications, or guarantees.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_packet(out_root: Path = OUT_ROOT, *, offers_path: Path = OFFERS_PATH) -> dict[str, Path]:
    offer = _read_offer(offers_path)
    seed_items = _campaign_items(offer)
    campaign_items, reviews = _self_review_campaign(seed_items, offer)
    send_plan = _send_plan(offer, campaign_items)
    slug = _now_slug()
    out_dir = out_root / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    packet = {
        "schema": "scbe-workflow-snapshot-autopromo-v1",
        "generated_at_utc": _now_iso(),
        "offer": _offer_summary(offer),
        "campaign_items": campaign_items,
        "self_review": reviews,
        "send_plan": send_plan,
        "connector_status": _connector_status(),
    }

    packet_path = out_dir / "campaign_packet.json"
    drafts_path = out_dir / "campaign_items.json"
    plan_path = out_dir / "send_plan.json"
    markdown_path = out_dir / "operator_next_actions.md"
    queue_path = out_dir / "campaign_queue.jsonl"
    x_ops_queue_path = out_dir / "x_ops_queue.json"
    bluesky_queue_path = out_dir / "bluesky_queue.json"

    packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=True), encoding="utf-8")
    drafts_path.write_text(json.dumps(campaign_items, indent=2, ensure_ascii=True), encoding="utf-8")
    plan_path.write_text(json.dumps(send_plan, indent=2, ensure_ascii=True), encoding="utf-8")
    markdown_path.write_text(_operator_markdown(offer, campaign_items, send_plan), encoding="utf-8")
    queue_path.write_text(
        "".join(json.dumps(item, ensure_ascii=True) + "\n" for item in campaign_items),
        encoding="utf-8",
    )
    x_ops_queue_path.write_text(
        json.dumps(_build_x_ops_queue(campaign_items), indent=2, ensure_ascii=True), encoding="utf-8"
    )
    bluesky_queue_path.write_text(
        json.dumps(_build_bluesky_queue(campaign_items), indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return {
        "folder": out_dir,
        "packet": packet_path,
        "drafts": drafts_path,
        "send_plan": plan_path,
        "markdown": markdown_path,
        "queue": queue_path,
        "x_ops_queue": x_ops_queue_path,
        "bluesky_queue": bluesky_queue_path,
    }


def _http_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return {"ok": 200 <= response.status < 300, "status": response.status, "json": json.loads(body or "{}")}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        return {"ok": False, "status": exc.code, "body": body}
    except Exception as exc:  # pragma: no cover - network failures vary
        return {"ok": False, "status": 0, "body": str(exc)}


def publish_bluesky(bluesky_queue: Path, *, dry_run: bool = False, max_items: int = 1) -> int:
    handle = os.environ.get("BLUESKY_HANDLE", "").strip()
    app_password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
    queue = json.loads(bluesky_queue.read_text(encoding="utf-8"))
    items = list(queue.get("items", []))[:max_items]
    if dry_run:
        for index, item in enumerate(items, start=1):
            print(f"[bluesky dry-run] #{index} {json.dumps(item, ensure_ascii=True)}")
        return 0
    if not handle or not app_password:
        print("[bluesky] skipped: BLUESKY_HANDLE and BLUESKY_APP_PASSWORD are not loaded")
        return 2
    session = _http_json(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        {"identifier": handle, "password": app_password},
    )
    if not session.get("ok"):
        print(f"[bluesky] login failed status={session.get('status')}")
        return 1
    session_json = session["json"]
    token = str(session_json.get("accessJwt", ""))
    did = str(session_json.get("did", ""))
    if not token or not did:
        print("[bluesky] login failed: missing token or did")
        return 1
    failures = 0
    for index, item in enumerate(items, start=1):
        result = _http_json(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            {
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": str(item["text"]),
                    "createdAt": _now_iso().replace("+00:00", "Z"),
                },
            },
            headers={"authorization": f"Bearer {token}"},
        )
        print(f"[bluesky] #{index} status={result.get('status')} ok={result.get('ok')}")
        failures += 0 if result.get("ok") else 1
    return 1 if failures else 0


def publish_packet(x_ops_queue: Path, *, dry_run: bool = False) -> int:
    webhook = os.environ.get("N8N_X_OPS_WEBHOOK_URL", "").strip() or os.environ.get("SCBE_X_WEBHOOK_URL", "").strip()
    api_key = os.environ.get("N8N_X_OPS_API_KEY", "").strip() or os.environ.get("SCBE_X_WEBHOOK_TOKEN", "").strip()
    cmd = [
        "node",
        "scripts/system/x_ops_queue_runner.mjs",
        "--queue",
        str(x_ops_queue),
    ]
    if webhook:
        cmd.extend(["--webhook", webhook])
    if api_key:
        cmd.extend(["--api-key", api_key])
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, check=False)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and optionally publish a Workflow Snapshot marketing campaign."
    )
    parser.add_argument("--out-root", default=str(OUT_ROOT), help="Output root for generated packet.")
    parser.add_argument(
        "--env-file", default=str(DEFAULT_ENV_FILE), help="Optional .env file to load before publishing."
    )
    parser.add_argument("--publish", action="store_true", help="Send ready queue to the configured n8n/X webhook.")
    parser.add_argument("--publish-bluesky", action="store_true", help="Publish one ready campaign item to Bluesky.")
    parser.add_argument("--dry-run", action="store_true", help="Print publish payloads without calling the webhook.")
    args = parser.parse_args()
    loaded = _load_env_file(Path(args.env_file))
    if loaded:
        print(f"loaded_env_key_count={len(loaded)}")
    paths = build_packet(Path(args.out_root))
    for name, path in paths.items():
        try:
            shown = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        except ValueError:
            shown = str(path)
        print(f"{name}={shown}")
    status = 0
    if args.publish or (args.dry_run and not args.publish_bluesky):
        status = max(status, publish_packet(paths["x_ops_queue"], dry_run=args.dry_run))
    if args.publish_bluesky:
        status = max(status, publish_bluesky(paths["bluesky_queue"], dry_run=args.dry_run))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
