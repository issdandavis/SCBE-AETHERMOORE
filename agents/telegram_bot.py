"""
SCBE-AETHERMOORE Telegram Bot — @SCBEAETRHBot
================================================

Real agent control interface for the SCBE system via Telegram.
Connects to all 17 Cloud Run API endpoints + HuggingFace PHDM model + Obsidian vaults.

Commands:
    /start              — Welcome + live system check
    /health             — Full health with subsystem checks
    /metrics            — Live governance metrics (decisions, rates, trust)
    /govern <text>      — Run 14-layer pipeline governance check
    /agent <id>         — Register or view an agent
    /trust <agent_id>   — Agent trust history
    /audit [agent_id]   — Recent audit log entries
    /alerts             — Pending system alerts
    /fleet <scenario>   — Run multi-agent fleet scenario
    /consensus <action> — Request multi-validator consensus
    /pipeline <action>  — Visualize all 14 pipeline layers
    /demo <type>        — Run live simulation (rogue/swarm/pipeline)
    /embed <text>       — 21D PHDM embedding from HuggingFace
    /compare <a>|<b>    — Cosine similarity + hyperbolic distance
    /context            — Obsidian vault shared context
    /catalog [id]       — Context Catalog archetype lookup
    /swarm <goal>       — Browser swarm task plan
    /help               — Full command reference

Usage:
    python agents/telegram_bot.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SCBEBot")

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SCBE_API_KEY = os.environ.get("SCBE_API_KEY", "scbe-dev-key")
CLOUD_RUN_URL = "https://scbe-api-956103948282.us-central1.run.app"
HF_SPACE_URL = "https://issdandavis-phdm-21d-embedding.hf.space/gradio_api"


def _obsidian_vault_candidates() -> List[Path]:
    """Return Obsidian vault candidates, with env var override first."""
    candidates: List[Path] = []

    env_vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if env_vault:
        candidates.append(Path(env_vault).expanduser())

    fallback_candidates = [
        Path(r"C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder"),
        Path(r"C:\Users\issda\OneDrive\Dropbox\Izack Realmforge"),
        Path(r"C:\Users\issda\Documents\Avalon Files"),
        Path(r"C:\AVALON BOOK SHIT\Izack Realmforge"),
    ]
    candidates.extend(fallback_candidates)

    seen: set[str] = set()
    unique_candidates: List[Path] = []
    for path in candidates:
        normalized = str(path).strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(path)
    return unique_candidates


def _resolve_obsidian_vault(*preferred_subpaths: str) -> Path:
    """Pick the first vault path that exists, prioritizing paths with hinted files."""
    candidates = _obsidian_vault_candidates()

    # First, try to match the expected file/directory hints in each vault.
    for subpath in preferred_subpaths:
        for vault in candidates:
            if vault.exists() and (vault / subpath).exists():
                return vault

    # Fallback to the first existing vault candidate.
    for vault in candidates:
        if vault.exists() and vault.is_dir():
            return vault

    # Final fallback if no folder exists yet.
    env_vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if env_vault:
        return Path(env_vault).expanduser()

    return Path(r"C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder")

# Bot was registered as telegram-bot agent on startup
BOT_AGENT_ID = "telegram-bot-lego"

# ---------------------------------------------------------------------------
#  HTTP Client (authenticated)
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


async def _api_get(
    path: str, params: Optional[Dict[str, str]] = None, auth: bool = True, timeout: int = 10
) -> Dict[str, Any]:
    """Authenticated GET to SCBE Cloud Run API."""
    import urllib.request
    import urllib.parse

    url = f"{CLOUD_RUN_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {"User-Agent": "SCBE-TelegramBot/1.0"}
    if auth:
        headers["SCBE_api_key"] = SCBE_API_KEY

    loop = asyncio.get_event_loop()
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=timeout)
        )
        data = json.loads(resp.read().decode())
        return {"ok": True, "data": data, "status": resp.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _api_post(
    path: str, payload: Dict[str, Any], auth: bool = True, timeout: int = 15
) -> Dict[str, Any]:
    """Authenticated POST to SCBE Cloud Run API."""
    import urllib.request

    url = f"{CLOUD_RUN_URL}{path}"
    body = json.dumps(payload).encode()

    headers = {
        "User-Agent": "SCBE-TelegramBot/1.0",
        "Content-Type": "application/json",
    }
    if auth:
        headers["SCBE_api_key"] = SCBE_API_KEY

    loop = asyncio.get_event_loop()
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=timeout)
        )
        data = json.loads(resp.read().decode())
        return {"ok": True, "data": data, "status": resp.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _hf_post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST to HuggingFace Gradio Space API."""
    import urllib.request

    url = f"{HF_SPACE_URL}{endpoint}"
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "SCBE-TelegramBot/1.0"}

    loop = asyncio.get_event_loop()
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=30)
        )
        data = json.loads(resp.read().decode())
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _hf_poll(endpoint: str, event_id: str, retries: int = 3) -> Optional[str]:
    """Poll HF Gradio event for SSE result."""
    import urllib.request

    url = f"{HF_SPACE_URL}{endpoint}/{event_id}"
    loop = asyncio.get_event_loop()

    for i in range(retries):
        await asyncio.sleep(2 + i)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SCBE-TelegramBot/1.0"})
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=15)
            )
            raw = resp.read().decode()
            # Gradio SSE format: lines starting with "data: "
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    return line[6:]
            return raw[:3500]
        except Exception:
            continue
    return None


def _read_obsidian_context() -> str:
    """Read the shared Obsidian context file."""
    vault = _resolve_obsidian_vault("AI Workspace/_context.md", "AI Workspace")
    ctx_path = vault / "AI Workspace" / "_context.md"
    if ctx_path.exists():
        text = ctx_path.read_text(encoding="utf-8")
        if len(text) > 3800:
            text = text[:3800] + "\n\n... (truncated)"
        return text
    return "Obsidian context not found."


def _read_context_room_index() -> str:
    """Read Context Room index from vault 2."""
    vault = _resolve_obsidian_vault("Context Room/00 - Index.md", "Context Room")
    idx = vault / "Context Room" / "00 - Index.md"
    if idx.exists():
        text = idx.read_text(encoding="utf-8")
        if len(text) > 2000:
            text = text[:2000] + "\n..."
        return text
    return "Context Room index not found."


def _msg(text: str) -> str:
    """Truncate to Telegram's 4096 char limit."""
    return text[:4090] if len(text) > 4090 else text


# ---------------------------------------------------------------------------
#  Command Handlers — System
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    # Live health check
    h = await _api_get("/v1/health", auth=False)
    api_ok = h["ok"] and h.get("data", {}).get("status") == "healthy"
    checks = h.get("data", {}).get("checks", {}) if h["ok"] else {}

    msg = (
        f"SCBE-AETHERMOORE v3.0.0\n"
        f"========================\n"
        f"Welcome, {user.first_name}.\n\n"
        f"API: {'HEALTHY' if api_ok else 'OFFLINE'}\n"
        f"  api: {checks.get('api', '?')} | pipeline: {checks.get('pipeline', '?')}\n"
        f"  storage: {checks.get('storage', '?')} | firebase: {checks.get('firebase', '?')}\n\n"
        f"Agent Control:\n"
        f"  /govern <text>  — L13 governance gate\n"
        f"  /agent <id>     — Register/view agent\n"
        f"  /fleet <name>   — Run fleet scenario\n"
        f"  /consensus <act> — Multi-sig approval\n"
        f"  /pipeline <act> — 14-layer visualization\n\n"
        f"Intelligence:\n"
        f"  /metrics    — Live decision stats\n"
        f"  /audit      — Recent decisions\n"
        f"  /alerts     — Pending alerts\n"
        f"  /embed      — 21D PHDM embedding\n"
        f"  /compare    — Text similarity\n\n"
        f"Knowledge:\n"
        f"  /context   — Obsidian shared state\n"
        f"  /catalog   — 25 task archetypes\n"
        f"  /swarm     — Browser swarm plan\n"
        f"  /demo      — Live simulations\n\n"
        f"Sacred Tongues: KO AV RU CA UM DR\n"
        f"Patent: USPTO #63/961,403\n"
        f"Time: {_now()}"
    )
    await update.message.reply_text(msg)


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await _api_get("/v1/health", auth=False)
    if not result["ok"]:
        await update.message.reply_text(f"API OFFLINE: {result['error']}")
        return

    d = result["data"]
    checks = d.get("checks", {})
    msg = (
        f"SCBE API Health\n"
        f"===============\n"
        f"Status: {d.get('status', '?').upper()}\n"
        f"Version: {d.get('version', '?')}\n"
        f"Timestamp: {d.get('timestamp', '?')}\n\n"
        f"Subsystems:\n"
        f"  API:      {checks.get('api', '?')}\n"
        f"  Pipeline: {checks.get('pipeline', '?')}\n"
        f"  Storage:  {checks.get('storage', '?')}\n"
        f"  Firebase: {checks.get('firebase', '?')}\n\n"
        f"Endpoint: {CLOUD_RUN_URL}"
    )
    await update.message.reply_text(msg)


# ---------------------------------------------------------------------------
#  Command Handlers — Governance
# ---------------------------------------------------------------------------


async def cmd_govern(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Usage: /govern <text>\n\n"
            "Runs the full 14-layer pipeline.\n"
            "Examples:\n"
            "  /govern read user profile data\n"
            "  /govern delete all production records\n"
            "  /govern send email to customer list"
        )
        return

    result = await _api_post("/v1/authorize", {
        "agent_id": BOT_AGENT_ID,
        "action": "EVALUATE",
        "target": text[:500],
        "context": {"source": "telegram", "user": update.effective_user.first_name},
    })

    if not result["ok"]:
        await update.message.reply_text(f"API error: {result['error']}")
        return

    d = result["data"]
    decision = d.get("decision", "?")
    score = d.get("score", 0)
    expl = d.get("explanation", {})

    icon = {"ALLOW": "ALLOW", "QUARANTINE": "QUAR", "DENY": "DENY"}.get(decision, "???")

    msg = (
        f"[{icon}] Governance Decision\n"
        f"{'=' * 30}\n"
        f"Decision: {decision}\n"
        f"Score: {score:.4f}\n"
        f"Decision ID: {d.get('decision_id', 'N/A')}\n"
    )
    if d.get("token"):
        msg += f"Auth Token: {d['token'][:20]}...\n"
    if d.get("expires_at"):
        msg += f"Expires: {d['expires_at']}\n"

    msg += f"\nExplanation:\n"
    for k, v in expl.items():
        if isinstance(v, dict):
            msg += f"  {k}:\n"
            for k2, v2 in v.items():
                msg += f"    {k2}: {v2}\n"
        else:
            msg += f"  {k}: {v}\n"

    msg += f"\nInput: {text[:150]}"
    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Agents
# ---------------------------------------------------------------------------


async def cmd_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "  /agent <id> — View agent info\n"
            "  /agent register <id> <name> <role> — Register new agent\n\n"
            "Roles: browser_automation, research, governance, monitoring"
        )
        return

    if args[0].lower() == "register" and len(args) >= 4:
        agent_id, name, role = args[1], args[2], args[3]
        result = await _api_post("/v1/agents", {
            "agent_id": agent_id,
            "name": name,
            "role": role,
            "initial_trust": 0.5,
        })
        if result["ok"]:
            d = result["data"]
            msg = (
                f"Agent Registered\n"
                f"  ID: {d.get('agent_id')}\n"
                f"  Name: {d.get('name')}\n"
                f"  Role: {d.get('role')}\n"
                f"  Trust: {d.get('trust_score', 0):.2f}"
            )
        else:
            msg = f"Registration failed: {result['error']}"
        await update.message.reply_text(msg)
        return

    # View agent
    agent_id = args[0]
    result = await _api_get(f"/v1/agents/{agent_id}")
    if result["ok"]:
        d = result["data"]
        msg = (
            f"Agent: {d.get('name', '?')}\n"
            f"  ID: {d.get('agent_id')}\n"
            f"  Role: {d.get('role', '?')}\n"
            f"  Trust Score: {d.get('trust_score', 0):.4f}\n"
            f"  Decisions: {d.get('decision_count', 0)}\n"
            f"  Created: {d.get('created_at', '?')}\n"
            f"  Last Active: {d.get('last_activity', '?')}"
        )
    else:
        msg = f"Agent '{agent_id}' not found or error: {result.get('error', '?')}"
    await update.message.reply_text(msg)


async def cmd_trust(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    agent_id = context.args[0] if context.args else ""
    if not agent_id:
        await update.message.reply_text("Usage: /trust <agent_id>")
        return

    result = await _api_get(f"/v1/agents/{agent_id}/trust-history", {"limit": "10"})
    if not result["ok"]:
        await update.message.reply_text(f"Error: {result['error']}")
        return

    data = result["data"]
    if isinstance(data, list):
        msg = f"Trust History: {agent_id}\n{'=' * 30}\n"
        for entry in data[:10]:
            ts = entry.get("timestamp", "?")[:19]
            score = entry.get("trust_score", 0)
            reason = entry.get("reason", "")
            msg += f"  {ts} | {score:.3f} | {reason}\n"
    else:
        msg = f"Trust data: {json.dumps(data, indent=2)[:3000]}"

    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Monitoring
# ---------------------------------------------------------------------------


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await _api_get("/v1/metrics")
    if not result["ok"]:
        await update.message.reply_text(f"Error: {result['error']}")
        return

    d = result["data"]
    total = d.get("total_decisions", 0)
    msg = (
        f"SCBE Governance Metrics\n"
        f"{'=' * 30}\n"
        f"Total Decisions: {total}\n\n"
        f"Breakdown:\n"
        f"  ALLOW:      {d.get('allow_count', 0)} ({d.get('allow_rate', 0):.1%})\n"
        f"  QUARANTINE: {d.get('quarantine_count', 0)} ({d.get('quarantine_rate', 0):.1%})\n"
        f"  DENY:       {d.get('deny_count', 0)} ({d.get('deny_rate', 0):.1%})\n\n"
        f"Avg Trust Score: {d.get('avg_trust_score', 0):.4f}\n"
        f"Firebase: {'connected' if d.get('firebase_connected') else 'disconnected'}\n"
        f"Time: {_now()}"
    )
    await update.message.reply_text(msg)


async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    params = {"limit": "10"}
    if context.args:
        params["agent_id"] = context.args[0]

    result = await _api_get("/v1/audit", params)
    if not result["ok"]:
        await update.message.reply_text(f"Error: {result['error']}")
        return

    data = result["data"]
    entries = data if isinstance(data, list) else data.get("entries", data.get("logs", []))

    if not entries:
        await update.message.reply_text("No audit entries found.")
        return

    msg = f"Audit Log (last {len(entries)})\n{'=' * 30}\n"
    for e in entries[:10]:
        ts = str(e.get("timestamp", "?"))[:19]
        agent = e.get("agent_id", "?")[:15]
        decision = e.get("decision", "?")
        action = e.get("action", "?")
        target = str(e.get("target", "?"))[:30]
        msg += f"{ts} | {agent} | {decision} | {action} → {target}\n"

    await update.message.reply_text(_msg(msg))


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = await _api_get("/v1/alerts", {"limit": "10", "pending_only": "true"})
    if not result["ok"]:
        await update.message.reply_text(f"Error: {result['error']}")
        return

    data = result["data"]
    alerts = data if isinstance(data, list) else data.get("alerts", [])

    if not alerts:
        await update.message.reply_text("No pending alerts. System clear.")
        return

    msg = f"Pending Alerts ({len(alerts)})\n{'=' * 30}\n"
    for a in alerts[:10]:
        sev = a.get("severity", "?").upper()
        atype = a.get("alert_type", "?")
        message = a.get("message", "?")[:60]
        aid = a.get("alert_id", "?")[:8]
        msg += f"  [{sev}] {atype}: {message} (id:{aid})\n"

    msg += "\nUse /ack <alert_id> to acknowledge."
    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Fleet & Consensus
# ---------------------------------------------------------------------------


async def cmd_fleet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = " ".join(context.args) if context.args else ""
    if not name:
        await update.message.reply_text(
            "Usage: /fleet <scenario_name>\n\n"
            "Runs a multi-agent fleet scenario through governance.\n\n"
            "Example: /fleet recon_mission\n\n"
            "Default fleet: 3 agents (KO scout, AV sniper, DR adjutant)"
        )
        return

    await update.message.reply_text(f"Running fleet scenario: {name}...")

    result = await _api_post("/v1/fleet/run-scenario", {
        "scenario_name": name,
        "agents": [
            {"agent_id": "ko-scout-01", "name": "KO Scout", "role": "reconnaissance", "initial_trust": 0.7},
            {"agent_id": "av-sniper-01", "name": "AV Sniper", "role": "extraction", "initial_trust": 0.7},
            {"agent_id": "dr-adjutant-01", "name": "DR Adjutant", "role": "coordination", "initial_trust": 0.8},
        ],
        "actions": [
            {"agent_id": "ko-scout-01", "action": "NAVIGATE", "target": f"recon:{name}", "sensitivity": 0.3},
            {"agent_id": "av-sniper-01", "action": "EXTRACT", "target": f"data:{name}", "sensitivity": 0.5},
            {"agent_id": "dr-adjutant-01", "action": "AGGREGATE", "target": f"results:{name}", "sensitivity": 0.4},
        ],
        "require_consensus": False,
    }, timeout=30)

    if not result["ok"]:
        await update.message.reply_text(f"Fleet error: {result['error']}")
        return

    d = result["data"]
    summary = d.get("summary", {})
    decisions = d.get("decisions", [])

    msg = (
        f"Fleet Scenario: {d.get('scenario_name', name)}\n"
        f"{'=' * 30}\n"
        f"Scenario ID: {d.get('scenario_id', '?')[:12]}\n\n"
        f"Summary:\n"
        f"  Total: {summary.get('total_actions', '?')}\n"
        f"  Allowed: {summary.get('allowed', '?')}\n"
        f"  Denied: {summary.get('denied', '?')}\n"
        f"  Quarantined: {summary.get('quarantined', '?')}\n\n"
        f"Decisions:\n"
    )
    for dec in decisions[:6]:
        agent = dec.get("agent_id", "?")[:15]
        decision = dec.get("decision", "?")
        score = dec.get("score", 0)
        msg += f"  {agent}: {decision} (score: {score:.3f})\n"

    metrics = d.get("metrics", {})
    if metrics:
        msg += f"\nMetrics:\n"
        for k, v in metrics.items():
            msg += f"  {k}: {v}\n"

    await update.message.reply_text(_msg(msg))


async def cmd_consensus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: /consensus <action> [target]\n\n"
            "Requests multi-validator approval.\n"
            "Example: /consensus DEPLOY production-config"
        )
        return

    action = args[0].upper()
    target = " ".join(args[1:]) if len(args) > 1 else "default-target"

    result = await _api_post("/v1/consensus", {
        "action": action,
        "target": target,
        "required_approvals": 3,
        "validator_ids": ["ko-validator", "ru-validator", "dr-validator"],
        "timeout_seconds": 30,
    }, timeout=35)

    if not result["ok"]:
        await update.message.reply_text(f"Consensus error: {result['error']}")
        return

    d = result["data"]
    msg = (
        f"Consensus Result\n"
        f"{'=' * 30}\n"
        f"ID: {d.get('consensus_id', '?')[:12]}\n"
        f"Status: {d.get('status', '?')}\n"
        f"Approvals: {d.get('approvals', 0)}/{d.get('required', 3)}\n"
        f"Rejections: {d.get('rejections', 0)}\n\n"
    )

    votes = d.get("votes", [])
    if votes:
        msg += "Votes:\n"
        for v in votes:
            vid = v.get("validator_id", "?")[:15]
            vote = v.get("vote", "?")
            msg += f"  {vid}: {vote}\n"

    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Demos & Pipeline
# ---------------------------------------------------------------------------


async def cmd_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    action = args[0].upper() if args else "READ"
    trust = float(args[1]) if len(args) > 1 else 0.7
    sensitivity = float(args[2]) if len(args) > 2 else 0.5

    result = await _api_get("/v1/demo/pipeline-layers", {
        "action": action, "trust": str(trust), "sensitivity": str(sensitivity)
    }, auth=False, timeout=15)

    if not result["ok"]:
        await update.message.reply_text(f"Error: {result['error']}")
        return

    d = result["data"]
    msg = (
        f"14-Layer Pipeline: {action}\n"
        f"{'=' * 30}\n"
        f"Trust: {trust} | Sensitivity: {sensitivity}\n\n"
    )

    layers = d.get("layers", d.get("pipeline", []))
    if isinstance(layers, list):
        for layer in layers:
            if isinstance(layer, dict):
                num = layer.get("layer", layer.get("number", "?"))
                name = layer.get("name", "?")
                result_val = layer.get("result", layer.get("output", "?"))
                msg += f"  L{num}: {name} → {result_val}\n"
            else:
                msg += f"  {layer}\n"
    else:
        msg += json.dumps(d, indent=2)[:3000]

    final = d.get("final_decision", d.get("decision", ""))
    if final:
        msg += f"\nFinal Decision: {final}"

    await update.message.reply_text(_msg(msg))


async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    demo_type = (context.args[0].lower() if context.args else "").strip()

    if demo_type not in ("rogue", "swarm", "pipeline"):
        await update.message.reply_text(
            "Usage: /demo <type>\n\n"
            "Available demos:\n"
            "  /demo rogue    — Rogue agent detection simulation\n"
            "  /demo swarm    — Decentralized swarm coordination\n"
            "  /demo pipeline — 14-layer pipeline visualization"
        )
        return

    await update.message.reply_text(f"Running {demo_type} simulation...")

    endpoints = {
        "rogue": "/v1/demo/rogue-detection",
        "swarm": "/v1/demo/swarm-coordination",
        "pipeline": "/v1/demo/pipeline-layers",
    }

    result = await _api_get(endpoints[demo_type], auth=False, timeout=20)
    if not result["ok"]:
        await update.message.reply_text(f"Demo error: {result['error']}")
        return

    d = result["data"]

    if demo_type == "rogue":
        msg = (
            f"Rogue Detection Simulation\n"
            f"{'=' * 30}\n"
            f"Steps: {d.get('steps', '?')}\n"
            f"Rogue Detected: {'YES' if d.get('rogue_detected') else 'NO'}\n"
            f"Detection Step: {d.get('detection_step', 'N/A')}\n"
            f"Consensus Votes: {d.get('consensus_votes', '?')}\n"
            f"False Positives: {d.get('false_positives', 0)}\n"
            f"Result: {d.get('result', '?')}\n"
        )
    elif demo_type == "swarm":
        msg = (
            f"Swarm Coordination Simulation\n"
            f"{'=' * 30}\n"
            f"Agents: {d.get('agents', '?')}\n"
            f"Initial Avg Distance: {d.get('initial_avg_distance', 0):.4f}\n"
            f"Final Avg Distance: {d.get('final_avg_distance', 0):.4f}\n"
            f"Collisions: {d.get('collisions', 0)}\n"
            f"Boundary Breaches: {d.get('boundary_breaches', 0)}\n"
            f"Coordination Score: {d.get('coordination_score', 0):.4f}\n"
        )
    else:
        msg = f"Pipeline Demo\n{'=' * 30}\n{json.dumps(d, indent=2)[:3500]}"

    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Intelligence (HuggingFace)
# ---------------------------------------------------------------------------


async def cmd_embed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Usage: /embed <text>\n\n"
            "Returns a 21D PHDM embedding vector.\n"
            "7 triads: SCBE, Dual-Lattice, PHDM, Tongues, M4, Swarm, HYDRA"
        )
        return

    await update.message.reply_text(f"Computing 21D embedding...")

    result = await _hf_post("/call/get_embedding", {"data": [text]})
    if not result["ok"]:
        await update.message.reply_text(f"HF Space error: {result['error']}\n(Space may be sleeping — retry in 30s)")
        return

    event_id = result["data"].get("event_id")
    if not event_id:
        await update.message.reply_text("No event returned.")
        return

    raw = await _hf_poll("/call/get_embedding", event_id)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                data = data[0]
            msg = f"21D Embedding: {text[:40]}...\n{'=' * 30}\n"
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        msg += f"\n{k}: [{', '.join(f'{x:.4f}' for x in v[:6])}]\n"
                    elif isinstance(v, (int, float)):
                        msg += f"{k}: {v:.6f}\n"
                    else:
                        msg += f"{k}: {v}\n"
            else:
                msg += str(data)[:3000]
        except (json.JSONDecodeError, TypeError):
            msg = f"Raw result:\n{raw[:3500]}"
    else:
        msg = "Embedding timed out. Space may be cold-starting."

    await update.message.reply_text(_msg(msg))


async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    full = " ".join(context.args) if context.args else ""
    if "|" not in full:
        await update.message.reply_text(
            "Usage: /compare text one | text two\n\n"
            "Returns cosine similarity + hyperbolic distance."
        )
        return

    parts = full.split("|", 1)
    text_a, text_b = parts[0].strip(), parts[1].strip()
    await update.message.reply_text(f"Comparing texts...")

    result = await _hf_post("/call/compare_texts", {"data": [text_a, text_b]})
    if not result["ok"]:
        await update.message.reply_text(f"HF error: {result['error']}")
        return

    event_id = result["data"].get("event_id")
    if not event_id:
        await update.message.reply_text("No event returned.")
        return

    raw = await _hf_poll("/call/compare_texts", event_id)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list) and data:
                data = data[0]
            msg = (
                f"Text Comparison\n{'=' * 30}\n"
                f"A: {text_a[:50]}\n"
                f"B: {text_b[:50]}\n\n"
            )
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (int, float)):
                        msg += f"{k}: {v:.6f}\n"
                    else:
                        msg += f"{k}: {v}\n"
            else:
                msg += str(data)[:3000]
        except (json.JSONDecodeError, TypeError):
            msg = f"Raw: {raw[:3500]}"
    else:
        msg = "Comparison timed out."

    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Knowledge
# ---------------------------------------------------------------------------


async def cmd_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sub = context.args[0].lower() if context.args else "shared"

    if sub == "room":
        text = _read_context_room_index()
    elif sub == "shared":
        text = _read_obsidian_context()
    else:
        text = (
            "Usage: /context [shared|room]\n"
            "  shared — Realmforge AI Workspace state\n"
            "  room   — Context Room index (112+ notes)"
        )

    await update.message.reply_text(_msg(text))


async def cmd_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    archetype_id = (context.args[0].upper() if context.args else "").strip()
    if not archetype_id:
        categories = {
            "Economy": "TRADE_BASIC, TRADE_ARBITRAGE, TRADE_CONTRABAND",
            "Faction": "FACTION_REPUTATION, FACTION_ENFORCEMENT, FACTION_DIPLOMACY",
            "Fleet": "FLEET_FORMATION, FLEET_PATHFINDING, FLEET_COMBAT",
            "Mission": "MISSION_DELIVERY, MISSION_CAMPAIGN, MISSION_CONDITION_GATE",
            "Brain": "BRAIN_SELF_DIAGNOSTIC, BRAIN_RECURSIVE_PLAN, BRAIN_CREATIVE_SYNTHESIS, BRAIN_PHASON_SHIFT",
            "Tongues": "TONGUE_ENCODE, TONGUE_CROSS_TRANSLATE, GEOSEAL_ENCRYPT",
            "Web": "WEB_NAVIGATE, WEB_PUBLISH, WEB_ANTIVIRUS",
            "Credits": "CREDIT_MINT, CREDIT_EXCHANGE, CREDIT_VAULT",
        }
        msg = "Context Catalog — 25 Archetypes\n" + "=" * 30 + "\n\n"
        for cat, items in categories.items():
            msg += f"{cat}:\n  {items}\n\n"
        msg += "Usage: /catalog <ARCHETYPE_ID>"
        await update.message.reply_text(msg)
        return

    try:
        from symphonic_cipher.scbe_aethermoore.concept_blocks.context_catalog import ContextCatalog
        catalog = ContextCatalog()
        entry = catalog.get(archetype_id)
        if entry:
            msg = (
                f"Archetype: {entry.archetype_id}\n"
                f"{'=' * 30}\n"
                f"Name: {entry.name}\n"
                f"Source: {entry.source_domain.value}\n"
                f"Tongue: {entry.denomination} (w={entry.tongue_weight:.3f})\n"
                f"Polyhedron: {entry.polyhedron.value}\n"
                f"Complexity: {entry.complexity_tier.value}\n"
                f"Radial Zone: {entry.radial_zone}\n"
                f"Required Layers: {sorted(entry.required_layers)}\n"
                f"Min Verdict: {entry.min_governance_verdict}\n"
                f"Energy: {entry.energy_range}\n"
                f"Legibility: {entry.base_legibility:.2f}\n\n"
                f"{entry.description}"
            )
        else:
            msg = f"'{archetype_id}' not found. /catalog for full list."
    except ImportError:
        msg = f"Catalog module not loaded. ID: {archetype_id}"

    await update.message.reply_text(_msg(msg))


async def cmd_swarm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    goal = " ".join(context.args) if context.args else ""
    if not goal:
        await update.message.reply_text(
            "Usage: /swarm <research goal>\n\n"
            "Plans a multi-agent browser research task.\n"
            "Example: /swarm find AI safety frameworks for multi-agent systems"
        )
        return

    # Also run a governance check on the swarm goal
    gov = await _api_post("/v1/authorize", {
        "agent_id": BOT_AGENT_ID,
        "action": "RESEARCH",
        "target": goal[:200],
        "context": {"task_type": "browser_swarm", "source": "telegram"},
    })

    gov_decision = "?"
    gov_score = 0.0
    if gov["ok"]:
        gov_decision = gov["data"].get("decision", "?")
        gov_score = gov["data"].get("score", 0)

    roles = [
        ("KO Scout", "Reconnaissance — visit seed URLs, map landscape"),
        ("AV Sniper", "Deep extraction — pull specific data, README parsing"),
        ("RU Support", "Validation — cross-reference findings, fact-check"),
        ("CA Tank", "Heavy scraping — handle rate limits, large pages"),
        ("UM Assassin", "Stealth fallback — retry failed URLs, anti-detection"),
        ("DR Adjutant", "Aggregation — merge findings, produce report"),
    ]

    msg = (
        f"Browser Swarm Plan\n"
        f"{'=' * 30}\n"
        f"Goal: {goal}\n"
        f"Governance: [{gov_decision}] (score: {gov_score:.3f})\n\n"
    )

    if gov_decision == "DENY":
        msg += "BLOCKED: Goal denied by L13 governance gate."
        await update.message.reply_text(msg)
        return

    msg += "Squad (Sacred Tongue Roles):\n"
    for role, desc in roles:
        msg += f"  {role}: {desc}\n"

    msg += (
        f"\nExecution Pipeline:\n"
        f"  1. Governance gate (14-layer) — {gov_decision}\n"
        f"  2. KO: Scout seed URLs\n"
        f"  3. AV: Extract targeted data\n"
        f"  4. RU: Validate + cross-reference\n"
        f"  5. SemanticAntivirus: Scan all content\n"
        f"  6. DR: Aggregate SwarmResult\n"
        f"  7. UM/CA: Retry any failed URLs\n\n"
        f"Safeguards:\n"
        f"  VisitedURLRegistry — no duplicate visits\n"
        f"  FindingsStore — content-hash dedup\n"
        f"  L12 Harmonic Wall — cost(d) = phi^(d^2)\n"
        f"  L13 Decision Gate — ALLOW/QUARANTINE/DENY per finding"
    )
    await update.message.reply_text(_msg(msg))


# ---------------------------------------------------------------------------
#  Command Handlers — Help & Fallback
# ---------------------------------------------------------------------------


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "SCBE-AETHERMOORE Bot\n"
        "=====================\n\n"
        "GOVERNANCE:\n"
        "  /govern <text>      — 14-layer pipeline check\n"
        "  /consensus <action> — Multi-validator approval\n"
        "  /pipeline <action>  — Visualize all 14 layers\n\n"
        "AGENTS:\n"
        "  /agent <id>         — View/register agent\n"
        "  /trust <agent_id>   — Trust score history\n"
        "  /fleet <scenario>   — Run fleet scenario\n\n"
        "MONITORING:\n"
        "  /health    — API health check\n"
        "  /metrics   — Decision statistics\n"
        "  /audit     — Recent audit entries\n"
        "  /alerts    — Pending alerts\n\n"
        "INTELLIGENCE:\n"
        "  /embed <text>     — 21D PHDM embedding\n"
        "  /compare <a>|<b>  — Text similarity\n"
        "  /demo <type>      — Live simulation\n\n"
        "KNOWLEDGE:\n"
        "  /context [shared|room] — Obsidian vault\n"
        "  /catalog [id]    — 25 task archetypes\n"
        "  /swarm <goal>    — Browser swarm plan\n\n"
        "Patent: USPTO #63/961,403\n"
        "Sacred Tongues: KO AV RU CA UM DR"
    )
    await update.message.reply_text(msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    # Natural language → try governance check
    if len(text) > 10:
        await update.message.reply_text(
            f"Evaluating: {text[:60]}...\n"
            f"(Use /govern for formal check, /help for commands)"
        )
    else:
        await update.message.reply_text("Use /help for commands.")


# ---------------------------------------------------------------------------
#  Startup — Register bot as agent
# ---------------------------------------------------------------------------


async def post_init(application: Application) -> None:
    """Register the Telegram bot as an agent on startup."""
    result = await _api_post("/v1/agents", {
        "agent_id": BOT_AGENT_ID,
        "name": "Lego (Telegram Bot)",
        "role": "telegram_interface",
        "initial_trust": 0.8,
    })
    if result["ok"]:
        logger.info(f"Registered bot agent: {BOT_AGENT_ID}")
    else:
        logger.warning(f"Agent registration: {result.get('error', 'unknown')}")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    print(f"Starting @SCBEAETRHBot (Lego)...")
    print(f"Cloud Run: {CLOUD_RUN_URL}")
    print(f"HF Space:  {HF_SPACE_URL}")
    print(f"API Key:   {'set' if SCBE_API_KEY else 'MISSING'}")
    print(f"Agent ID:  {BOT_AGENT_ID}")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Register all command handlers
    commands = [
        ("start", cmd_start),
        ("health", cmd_health),
        ("metrics", cmd_metrics),
        ("govern", cmd_govern),
        ("agent", cmd_agent),
        ("trust", cmd_trust),
        ("audit", cmd_audit),
        ("alerts", cmd_alerts),
        ("fleet", cmd_fleet),
        ("consensus", cmd_consensus),
        ("pipeline", cmd_pipeline),
        ("demo", cmd_demo),
        ("embed", cmd_embed),
        ("compare", cmd_compare),
        ("context", cmd_context),
        ("catalog", cmd_catalog),
        ("swarm", cmd_swarm),
        ("help", cmd_help),
    ]
    for name, handler in commands:
        app.add_handler(CommandHandler(name, handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"Bot running with {len(commands)} commands. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()




