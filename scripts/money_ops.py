#!/usr/bin/env python3
"""Money Ops Runner — one-click monetization execution.

This script converts the existing SCBE revenue pieces into one practical run:

* generate and govern content for the queue
* check all OctoArmor tentacle readiness (free providers)
* run a small paid-work quote cycle via AgentMarketplace
* optionally push Polly training data to Hugging Face

No single command should touch production credentials directly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


# project-local imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

# Load .env so provider keys and tokens are available
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                if _v and _k.strip():
                    os.environ.setdefault(_k.strip(), _v.strip())


from src.fleet.octo_armor import OctoArmor, TrainingFlywheel
from src.fleet.agent_marketplace import AgentMarketplace
from src.security.secret_store import get_secret
from scripts import revenue_engine


PRODUCT_TAGLINE = {
    "SCBE n8n Workflow Starter Pack": "Automates ops + governance",
    "AI Governance Toolkit": "Paid scan + calculator + templates",
    "Content Spin Engine": "Fibonacci/Flywheel content multiplication",
    "HYDRA Agent Templates": "Fleet orchestration + templates",
}


def _mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "missing"
    if len(value) <= 8:
        return "set"
    return f"{value[:4]}...{value[-4:]}"


def _check_secret(name: str, *, required: bool = False) -> Dict[str, str]:
    value = get_secret(name, "")
    return {
        "name": name,
        "required": "yes" if required else "optional",
        "status": "set" if value else "missing",
        "value": _mask_secret(value),
    }


def revenue_status() -> Dict[str, Any]:
    queue_dir = (REPO_ROOT / "artifacts" / "content_queue").resolve()
    queued = 0
    published = 0
    blocked = 0

    if queue_dir.exists():
        for path in queue_dir.glob("*.json"):
            with open(path, "r", encoding="utf-8") as fh:
                try:
                    entry = json.load(fh)
                except json.JSONDecodeError:
                    continue
            status = entry.get("status", "queued")
            if status == "published":
                published += 1
            elif status == "blocked":
                blocked += 1
            else:
                queued += 1

    return {
        "queue_dir": str(queue_dir),
        "queued": queued,
        "published": published,
        "blocked": blocked,
    }


def readiness_report() -> Dict[str, Any]:
    armor = OctoArmor()
    status = armor.tentacle_status()

    provider_keys = [
        "STRIPE_SECRET_KEY",
        "GUMROAD_API_TOKEN",
        "HF_TOKEN",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "MISTRAL_API_KEY",
        "GOOGLE_AI_API_KEY",
        "COHERE_API_KEY",
        "CLOUDFLARE_API_KEY",
        "GITHUB_TOKEN",
    ]
    secrets = {_check_secret(name)["name"]: _check_secret(name) for name in provider_keys}

    available = sum(1 for row in status if row.get("available"))
    ready = [row["tentacle"] for row in status if row.get("available")]

    return {
        "available_tentacles": available,
        "total_tentacles": len(status),
        "ready_tentacles": ready,
        "status_rows": status,
        "secrets": secrets,
    }


def generate_content(topic: str | None = None, do_spin: bool = False, depth: int = 2) -> Dict[str, Any]:
    """Generate + govern content and return summary metadata."""
    result = revenue_engine.run_pipeline()
    summary = {
        "mode": "seed_pipeline",
        "generated": result.generated,
        "passed_governance": result.passed_governance,
        "queued": result.queued,
        "blocked": result.blocked,
    }

    if do_spin:
        spin_result = revenue_engine.run_spin_pipeline(topic=topic, depth=depth) if topic else revenue_engine.run_spin_pipeline(depth=depth)
        summary.update({
            "spin_mode": "targeted" if topic else "all",
            "spin_topic": topic or "all",
            "spin_depth": depth,
            "spin_generated": spin_result.generated,
            "spin_queued": spin_result.queued,
            "spin_passed": spin_result.passed_governance,
            "spin_blocked": spin_result.blocked,
        })

    summary.update(revenue_status())
    return summary


async def probe_providers(prompt: str = "Give one practical AI safety monetization idea.") -> List[Dict[str, Any]]:
    armor = OctoArmor()
    ready = armor.available_tentacles()
    results: List[Dict[str, Any]] = []

    if not ready:
        return [{"status": "blocked", "reason": "no available free providers configured"}]

    # Run at most 3 probes to avoid burning free quota
    for tentacle in ready[:3]:
        try:
            outcome = await armor.reach(prompt, preferred_tentacle=tentacle, task_type="content")
            results.append({
                "tentacle": tentacle.value,
                "status": "ok",
                "response_len": len(outcome.get("response", "")),
                "decision": outcome.get("decision"),
                "quality": outcome.get("quality_score"),
            })
        except Exception as exc:
            results.append({
                "tentacle": tentacle.value,
                "status": "error",
                "error": str(exc)[:180],
            })

    return results


def marketplace_demo() -> Dict[str, Any]:
    market = AgentMarketplace()
    client = market.register_client(
        name="SCBE Pilot",
        email="pilot@scbe.aethermoore.local",
        payment_method="stripe",
    )
    job = market.submit_job(
        client_id=client.client_id,
        category="security_audit",
        title="AI safety posture + governance hardening",
        description="Audit an AI service for drift governance and create controls.",
    )
    quote = job.quote
    if not quote:
        return {"error": "quote_generation_failed"}

    pay = market.accept_quote(job.job_id)
    return {
        "client_id": client.client_id,
        "job_id": job.job_id,
        "quote_id": quote.quote_id,
        "pre_payment": quote.pre_payment,
        "estimated_total": quote.estimated_total,
        "breakdown": quote.breakdown,
        "acceptance": pay,
    }


def push_to_hf_if_ready() -> Dict[str, Any]:
    armor = OctoArmor()
    flywheel = TrainingFlywheel(armor=armor)
    ready = bool(get_secret("HF_TOKEN", ""))
    if not ready:
        return {
            "status": "skipped",
            "reason": "HF_TOKEN not configured in secret store or env",
        }

    result = flywheel.push_to_hf()
    return result


def write_report(payload: Dict[str, Any], outfile: Path) -> None:
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with open(outfile, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def print_section(title: str) -> None:
    print(f"\n{'=' * 10} {title} {'=' * 10}")


async def run_money_day(args: argparse.Namespace) -> int:
    report: Dict[str, Any] = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "actions": [],
    }

    print_section("Money Mode Readiness")
    ready = readiness_report()
    print(f"Ready providers: {ready['available_tentacles']}/{ready['total_tentacles']}")
    for row in ready["status_rows"]:
        flag = "READY" if row.get("available") else "NO_KEY"
        print(f"  - {row.get('tentacle'):16} [{flag}] {row.get('cost', 'n/a'):>10} models={row.get('free_models')}")
    report["readiness"] = ready
    report["actions"].append("readiness")

    print_section("Generate Revenue Content")
    content = generate_content(topic=args.spin_topic, do_spin=args.spin, depth=args.spin_depth)
    print(f"Content generated: {content['generated']} -> passed={content['passed_governance']} queued={content['queued']}")
    if args.spin:
        print(f"Spin generated: {content['spin_generated']} -> queued={content['spin_queued']}")
    print(f"Queue status: {content['queued']} queued, {content['blocked']} blocked, {content['published']} published")
    report["content"] = content
    report["actions"].append("content")

    if args.probe:
        print_section("Provider Probe")
        probe = await probe_providers()
        report["provider_probe"] = probe
        for row in probe:
            if row.get("status") == "ok":
                print(f"  {row['tentacle']:16} OK len={row.get('response_len')}")
            else:
                print(f"  {row['tentacle']:16} ERROR {row.get('error')}")
        report["actions"].append("provider_probe")

    if args.marketplace:
        print_section("Marketplace Quote")
        offer = marketplace_demo()
        print(f"  Quote job: {offer.get('job_id')} pre_payment=${offer.get('pre_payment')}")
        print(f"  Estimated total: ${offer.get('estimated_total')}")
        report["marketplace"] = offer
        report["actions"].append("marketplace")

    if args.push_hf:
        print_section("HF Training Push")
        push = push_to_hf_if_ready()
        if push.get("status") == "ok":
            print(f"  HF push: ok ({push.get('repo')})")
        else:
            reason = push.get("error") or push.get("reason") or "unknown"
            print(f"  HF push: {push.get('status')} reason={reason}")
        report["hf_push"] = push
        report["actions"].append("hf_push")

    # Add a quick money list for immediate execution
    print_section("Live Sales Catalog")
    for name, tagline in PRODUCT_TAGLINE.items():
        print(f"  {name}: {tagline}")

    report_file = REPO_ROOT / "artifacts" / "money_ops" / "last_run.json"
    write_report(report, report_file)
    print_section("Run Artifact")
    print(f"Saved report: {report_file}")
    print("Run `python scripts/gumroad_publish.py links` to copy live product + Stripe links to your sales pages.")
    return 0


def show_status() -> int:
    print_section("Money Ops Status")
    ready = readiness_report()
    print(f"Ready providers: {ready['available_tentacles']}/{ready['total_tentacles']}")
    print(f"HF token: {ready['secrets']['HF_TOKEN']['status']} ({ready['secrets']['HF_TOKEN']['value']})")
    print(f"Gumroad token: {ready['secrets']['GUMROAD_API_TOKEN']['status']} ({ready['secrets']['GUMROAD_API_TOKEN']['value']})")
    print(f"Stripe token: {ready['secrets']['STRIPE_SECRET_KEY']['status']} ({ready['secrets']['STRIPE_SECRET_KEY']['value']})")

    for row in ready["status_rows"]:
        print(f"  {row.get('tentacle'):16} key={bool(row.get('has_key'))} cost={row.get('cost')}")

    print(f"\nQueue: {revenue_status()}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute practical monetization ops.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run money-day execution loop")
    run_cmd.add_argument("--spin", action="store_true", help="Also run spin pipeline")
    run_cmd.add_argument("--spin-topic", default="", help="Spin topic override")
    run_cmd.add_argument("--spin-depth", type=int, default=2, help="Spin depth")
    run_cmd.add_argument("--probe", action="store_true", help="Probe 1-3 available free providers")
    run_cmd.add_argument("--marketplace", action="store_true", help="Generate a sample revenue quote")
    run_cmd.add_argument("--push-hf", action="store_true", help="Push training logs to HuggingFace")

    sub.add_parser("status", help="Print money readiness + secret status")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "status":
        return show_status()

    if args.command == "run":
        spin_topic = args.spin_topic.strip() or None
        args.spin_topic = spin_topic
        return asyncio.run(run_money_day(args))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
