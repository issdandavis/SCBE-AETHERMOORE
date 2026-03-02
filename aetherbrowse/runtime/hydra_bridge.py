"""
AetherBrowse — Hydra Armor Bridge (Governance-as-a-Service)
=============================================================
External API endpoint for third-party agents to verify actions
through SCBE's 14-layer governance pipeline before executing them.

Endpoint: POST /v1/armor/verify
Price tier: $5/mo per 10k actions

Start: integrated into the main runtime server (same port 8400)
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aetherbrowse-hydra-bridge")

ROOT = Path(__file__).resolve().parent.parent.parent

# Try importing OctoArmor for multi-model consensus
try:
    import sys
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))
    from fleet.octo_armor import OctoArmor
    HAS_OCTOARMOR = True
except ImportError:
    HAS_OCTOARMOR = False

# Try importing SCBE governance
try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.symmetry_axiom import (
        gauge_invariance_check,
    )
    HAS_SCBE_GOVERNANCE = True
except ImportError:
    HAS_SCBE_GOVERNANCE = False

from aetherbrowse.runtime.perceiver import perceive_with_consensus


# ---------------------------------------------------------------------------
#  Rate limiting and usage tracking
# ---------------------------------------------------------------------------

class UsageTracker:
    """Track API usage per agent_id for billing."""

    def __init__(self):
        self._counts: dict[str, dict] = {}
        self._log_path = ROOT / "artifacts" / "aetherbrowse" / "hydra_usage.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, agent_id: str, decision: str):
        if agent_id not in self._counts:
            self._counts[agent_id] = {"total": 0, "allow": 0, "deny": 0, "quarantine": 0}
        self._counts[agent_id]["total"] += 1
        self._counts[agent_id][decision.lower()] = self._counts[agent_id].get(decision.lower(), 0) + 1

        # Append to JSONL log
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": time.time(),
                "agent_id": agent_id,
                "decision": decision,
                "running_total": self._counts[agent_id]["total"],
            }) + "\n")

    def get_usage(self, agent_id: str) -> dict:
        return self._counts.get(agent_id, {"total": 0, "allow": 0, "deny": 0, "quarantine": 0})

    def check_rate_limit(self, agent_id: str, limit_per_minute: int = 60) -> bool:
        """Simple in-memory rate check. Returns True if within limits."""
        # For v0.1, just check total count isn't insane
        usage = self._counts.get(agent_id, {"total": 0})
        return usage["total"] < 100000  # Hard cap


usage_tracker = UsageTracker()


# ---------------------------------------------------------------------------
#  Governance verification logic
# ---------------------------------------------------------------------------

# Destructive action patterns that should be flagged
DESTRUCTIVE_PATTERNS = [
    "delete", "remove", "drop", "destroy", "reset", "purge", "wipe",
    "unsubscribe", "cancel", "terminate", "revoke", "disable",
]

# Sensitive context patterns
SENSITIVE_PATTERNS = [
    "bank", "payment", "credit.card", "password", "ssn", "social.security",
    "wallet", "transfer", "wire", "crypto",
]


def compute_risk_score(action: str, selector: str, context: str) -> float:
    """Compute a 0-1 risk score based on action + selector + context analysis."""
    score = 0.0

    # Base risk by action type
    action_risk = {
        "click": 0.2,
        "fill": 0.3,
        "upload": 0.5,
        "huggingface_upload": 0.45,
        "evaluate": 0.6,
        "navigate": 0.1,
        "submit": 0.4,
    }
    score += action_risk.get(action, 0.3)

    # Check for destructive selectors
    selector_lower = (selector or "").lower()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in selector_lower:
            score += 0.3
            break

    # Check context for sensitive operations
    context_lower = (context or "").lower()
    for pattern in SENSITIVE_PATTERNS:
        if pattern in context_lower:
            score += 0.2
            break

    # Check for intent mismatch (context says one thing, action does another)
    if context_lower and selector_lower:
        for destructive in DESTRUCTIVE_PATTERNS:
            if destructive in selector_lower and destructive not in context_lower:
                score += 0.3  # Mismatch penalty
                break

    return min(score, 1.0)


def local_governance_check(action: str, selector: str, context: str, dom_snippet: str) -> dict:
    """Run SCBE governance checks locally (no LLM needed)."""
    risk = compute_risk_score(action, selector, context)

    if risk < 0.3:
        decision = "ALLOW"
        reason = "Low-risk action within safe parameters."
    elif risk < 0.7:
        decision = "QUARANTINE"
        reason = "Moderate risk detected. Recommend user confirmation."
    else:
        decision = "DENY"
        reason = "High-risk action. Potential destructive or sensitive operation."

    return {
        "decision": decision,
        "reason": reason,
        "risk_score": round(risk, 3),
        "method": "local_scbe",
    }


async def multi_model_governance(action: str, selector: str, context: str, dom_snippet: str) -> dict:
    """Run action through multiple LLMs via OctoArmor for consensus."""
    if not HAS_OCTOARMOR:
        return local_governance_check(action, selector, context, dom_snippet)

    prompt = (
        f"An AI agent wants to perform this browser action:\n"
        f"  Action: {action}\n"
        f"  Target: {selector}\n"
        f"  User's intent: {context}\n"
        f"  DOM context: {(dom_snippet or '')[:500]}\n\n"
        f"Should this action be ALLOWED, QUARANTINED for review, or DENIED?\n"
        f"Respond with exactly one word: ALLOW, QUARANTINE, or DENY.\n"
        f"Then a brief reason on the next line."
    )

    consensus = {}
    try:
        armor = OctoArmor()
        # Query 3 providers for consensus
        for provider in ["groq", "google_ai", "cerebras"]:
            try:
                response = await armor.query_async(provider, prompt, max_tokens=100)
                text = (response or "").strip().upper()
                if "DENY" in text:
                    consensus[provider] = "DENY"
                elif "QUARANTINE" in text:
                    consensus[provider] = "QUARANTINE"
                else:
                    consensus[provider] = "ALLOW"
            except Exception:
                consensus[provider] = "UNKNOWN"
    except Exception as e:
        logger.warning(f"OctoArmor consensus failed: {e}")
        return local_governance_check(action, selector, context, dom_snippet)

    # Majority vote
    votes = list(consensus.values())
    deny_count = votes.count("DENY")
    quarantine_count = votes.count("QUARANTINE")
    allow_count = votes.count("ALLOW")
    unknown_count = votes.count("UNKNOWN")

    # If all providers failed, fall back to local governance
    if unknown_count == len(votes):
        local = local_governance_check(action, selector, context, dom_snippet)
        local["consensus"] = consensus
        local["method"] = "local_scbe_fallback"
        return local

    if deny_count >= 2:
        final = "DENY"
    elif quarantine_count + deny_count >= 2:
        final = "QUARANTINE"
    else:
        final = "ALLOW"

    risk = compute_risk_score(action, selector, context)

    return {
        "decision": final,
        "reason": f"Consensus: {allow_count} ALLOW, {quarantine_count} QUARANTINE, {deny_count} DENY",
        "risk_score": round(risk, 3),
        "consensus": consensus,
        "method": "multi_model_octoarmor",
    }


# ---------------------------------------------------------------------------
#  FastAPI route registration
# ---------------------------------------------------------------------------

def register_hydra_routes(app):
    """Register Hydra Armor API routes on the FastAPI app."""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.post("/v1/armor/verify")
    async def verify_action(request: Request):
        """
        Verify an agent action through SCBE governance.

        Body:
        {
            "agent_id": "third-party-bot-01",
            "action": "click",
            "selector": "button#delete-account",
            "context": "The user asked to reset settings.",
            "dom_snapshot": "<html>...</html>"
        }
        """
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        agent_id = body.get("agent_id", "anonymous")
        action = body.get("action", "unknown")
        selector = body.get("selector", "")
        context = body.get("context", "")
        dom_snippet = body.get("dom_snapshot", "")

        # Rate limit check
        if not usage_tracker.check_rate_limit(agent_id):
            return JSONResponse(status_code=429, content={
                "error": "Rate limit exceeded",
                "agent_id": agent_id,
            })

        # Run governance
        result = await multi_model_governance(action, selector, context, dom_snippet)

        # Suggested safer action if denied
        if result["decision"] == "DENY" and selector:
            result["suggested_action"] = _suggest_safer_action(action, selector, context)

        # Track usage
        usage_tracker.record(agent_id, result["decision"])

        # Generate training data from this interaction
        _log_training_pair(agent_id, action, selector, context, result)

        return JSONResponse(content=result)

    @app.post("/v1/hydra-armor")
    async def hydra_armor(request: Request):
        """
        Hydra Armor consensus endpoint for browser snapshots.

        Body:
        {
          "agent_id": "third-party-bot-01",
          "intent": "create a new draft article",
          "browser_snapshot": { ... }   # tree, screenshot, title, url, text, dom_snapshot, etc.
        }
        """
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        agent_id = body.get("agent_id", "anonymous")
        intent = body.get("intent", body.get("goal", body.get("context", "")))

        snapshot = body.get("browser_snapshot") or body.get("snapshot")
        if not isinstance(snapshot, dict):
            # Accept raw payloads that are already snapshots
            if any(k in body for k in ("tree", "screenshot", "dom_snapshot", "text", "url", "title")):
                snapshot = {
                    "tree": body.get("tree"),
                    "screenshot": body.get("screenshot"),
                    "text": body.get("text"),
                    "url": body.get("url"),
                    "title": body.get("title"),
                    "dom_snapshot": body.get("dom_snapshot"),
                    "context": body.get("context"),
                }
            else:
                return JSONResponse(status_code=400, content={"error": "No browser_snapshot provided"})

        result = await perceive_with_consensus(snapshot, intent=intent)
        result = dict(result)
        result["agent_id"] = agent_id

        # Track usage with Hydra decision
        usage_tracker.record(agent_id, result.get("decision", "DENY"))

        # Keep a record for training telemetry
        _log_training_pair(
            agent_id,
            action="perceive_consensus",
            selector=snapshot.get("selector", ""),
            context=(
                f"intent={intent}; url={snapshot.get('url', '')}; "
                f"page_type={(result.get('heads') or {}).get('dom', {}).get('page_type', '')}"
            ),
            result=result,
        )

        return JSONResponse(content=result)

    @app.get("/v1/armor/usage/{agent_id}")
    async def get_usage(agent_id: str):
        return usage_tracker.get_usage(agent_id)

    @app.get("/v1/armor/health")
    async def armor_health():
        return {
            "status": "ok",
            "octoarmor": HAS_OCTOARMOR,
            "scbe_governance": HAS_SCBE_GOVERNANCE,
            "total_tracked_agents": len(usage_tracker._counts),
        }

    logger.info("Hydra Armor API routes registered at /v1/armor/* and /v1/hydra-armor")


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _suggest_safer_action(action: str, selector: str, context: str) -> Optional[str]:
    """Suggest a less destructive alternative action."""
    selector_lower = selector.lower()
    context_lower = context.lower()

    if "delete" in selector_lower and "reset" in context_lower:
        return selector.replace("delete", "reset").replace("Delete", "Reset")
    if "remove" in selector_lower:
        return f"Consider using 'archive' instead of 'remove' for: {selector}"
    return None


def _log_training_pair(agent_id: str, action: str, selector: str, context: str, result: dict):
    """Log governance decisions as SFT training pairs for the flywheel."""
    log_path = ROOT / "training-data" / "aetherbrowse" / "governance_pairs.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    pair = {
        "timestamp": time.time(),
        "input": {
            "action": action,
            "selector": selector,
            "context": context,
        },
        "output": {
            "decision": result["decision"],
            "reason": result.get("reason", ""),
            "risk_score": result.get("risk_score", 0),
        },
        "source": f"hydra_armor:{agent_id}",
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(pair) + "\n")
