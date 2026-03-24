"""
AetherGates — Controlled Portals from the Everweave

Izack's governed portal network connecting Aethermoor to external data realms.
Each Gate maps to a Sacred Tongue affinity and provides governance-checked
access to free external API endpoints.

Lore: The AetherGates were forged by Izack after discovering that the
Everweave's data lattices could resonate with external protocol realms.
Each gate requires authorization through the appropriate Sacred Tongue,
and all transit is logged by Rath — the Observer Agent who monitors
all portal traffic from the Timeless Observatory.

Gate Registry:
  KO (Authority)  → Governance & system status gates
  AV (Transport)  → Geographic & location gates
  RU (Policy)     → News, knowledge & public data gates
  CA (Compute)    → Crypto, finance & math gates
  UM (Security)   → IP lookup, threat intel & security gates
  DR (Schema)     → Random data, quotes & schema generation gates
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

logger = logging.getLogger("aether_gates")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ── Sacred Tongue Affinity ───────────────────────────────────────────


class Tongue(str, Enum):
    KO = "KO"  # Authority / Control
    AV = "AV"  # Transport / Messaging
    RU = "RU"  # Policy / Constraints
    CA = "CA"  # Compute / Encryption
    UM = "UM"  # Security / Secrets
    DR = "DR"  # Schema / Authentication


# ── Privilege Tiers ──────────────────────────────────────────────────


class PrivilegeTier(str, Enum):
    OBSERVER = "observer"  # Read-only, monitoring (Rath tier)
    SCOUT = "scout"  # Read + limited external calls
    OPERATOR = "operator"  # Read + write + external calls
    ARCHITECT = "architect"  # Full access, can modify gates
    ADMIN = "admin"  # Izack tier — all permissions


TIER_PERMISSIONS = {
    PrivilegeTier.OBSERVER: {
        "can_read_gates": True,
        "can_invoke_gates": False,
        "can_write_artifacts": False,
        "can_modify_gates": False,
        "can_spawn_agents": False,
        "can_cross_talk": True,  # read only
        "max_requests_per_minute": 0,
    },
    PrivilegeTier.SCOUT: {
        "can_read_gates": True,
        "can_invoke_gates": True,
        "can_write_artifacts": False,
        "can_modify_gates": False,
        "can_spawn_agents": False,
        "can_cross_talk": True,
        "max_requests_per_minute": 10,
    },
    PrivilegeTier.OPERATOR: {
        "can_read_gates": True,
        "can_invoke_gates": True,
        "can_write_artifacts": True,
        "can_modify_gates": False,
        "can_spawn_agents": True,
        "can_cross_talk": True,
        "max_requests_per_minute": 60,
    },
    PrivilegeTier.ARCHITECT: {
        "can_read_gates": True,
        "can_invoke_gates": True,
        "can_write_artifacts": True,
        "can_modify_gates": True,
        "can_spawn_agents": True,
        "can_cross_talk": True,
        "max_requests_per_minute": 120,
    },
    PrivilegeTier.ADMIN: {
        "can_read_gates": True,
        "can_invoke_gates": True,
        "can_write_artifacts": True,
        "can_modify_gates": True,
        "can_spawn_agents": True,
        "can_cross_talk": True,
        "max_requests_per_minute": 999,
    },
}


# ── Agent Privilege Registry ─────────────────────────────────────────

AGENT_PRIVILEGES: Dict[str, PrivilegeTier] = {
    "agent.claude": PrivilegeTier.ADMIN,
    "agent.codex": PrivilegeTier.ADMIN,
    "agent.gemini": PrivilegeTier.OPERATOR,
    "agent.grok": PrivilegeTier.OPERATOR,
    "agent.rath": PrivilegeTier.OBSERVER,  # The Observer — SAO Rath
    "agent.polly": PrivilegeTier.SCOUT,
    "agent.kael": PrivilegeTier.SCOUT,
    "agent.aria": PrivilegeTier.OPERATOR,
    "agent.zara": PrivilegeTier.OPERATOR,
    "agent.eldrin": PrivilegeTier.SCOUT,
    "agent.clay": PrivilegeTier.SCOUT,
}


def get_agent_permissions(agent_id: str) -> Dict[str, Any]:
    """Get permissions for an agent. Unknown agents get SCOUT tier."""
    tier = AGENT_PRIVILEGES.get(agent_id, PrivilegeTier.SCOUT)
    perms = TIER_PERMISSIONS[tier].copy()
    perms["tier"] = tier.value
    perms["agent_id"] = agent_id
    return perms


def check_permission(agent_id: str, permission: str) -> bool:
    """Check if an agent has a specific permission."""
    perms = get_agent_permissions(agent_id)
    return bool(perms.get(permission, False))


# ── Gate Definition ──────────────────────────────────────────────────


@dataclass
class AetherGate:
    """A controlled portal to an external API realm."""

    name: str
    tongue: Tongue
    endpoint: str
    description: str
    lore: str  # In-world flavor text
    method: str = "GET"
    params: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    response_key: Optional[str] = None  # Extract specific key from response
    min_tier: PrivilegeTier = PrivilegeTier.SCOUT
    cost_weight: float = 1.0  # Governance cost multiplier
    active: bool = True


# ── Gate Registry ────────────────────────────────────────────────────

GATE_REGISTRY: Dict[str, AetherGate] = {
    # ── KO: Authority / Status Gates ──
    "ko-system-health": AetherGate(
        name="System Health Portal",
        tongue=Tongue.KO,
        endpoint="https://httpbin.org/status/200",
        description="Ping external realm availability",
        lore="The Authority Gate verifies the heartbeat of connected realms.",
    ),
    "ko-ip-echo": AetherGate(
        name="Identity Mirror",
        tongue=Tongue.KO,
        endpoint="https://api.ipify.org?format=json",
        description="Reveal the caller's external identity",
        lore="The Mirror of Authority reflects your true network identity.",
    ),
    # ── AV: Transport / Geographic Gates ──
    "av-geocode": AetherGate(
        name="Cartographer's Gate",
        tongue=Tongue.AV,
        endpoint="https://nominatim.openstreetmap.org/search",
        description="Geocode addresses to coordinates",
        lore="Eldrin's portal to the Cartographer's Archive — turn names into coordinates.",
        params={"format": "json", "limit": "5"},
        headers={"User-Agent": "AetherGate/1.0 (SCBE-AETHERMOORE)"},
    ),
    "av-country-ip": AetherGate(
        name="Realm Locator",
        tongue=Tongue.AV,
        endpoint="https://api.country.is",
        description="Determine country by IP address",
        lore="The Transport Gate reveals which realm a traveler hails from.",
    ),
    "av-restcountries": AetherGate(
        name="Atlas of Realms",
        tongue=Tongue.AV,
        endpoint="https://restcountries.com/v3.1/all",
        description="Full atlas of all world realms (countries)",
        lore="The complete atlas maintained by AV Transport scribes.",
        params={"fields": "name,capital,population,region,flags"},
    ),
    # ── RU: Policy / Knowledge Gates ──
    "ru-hackernews-top": AetherGate(
        name="Chronicle Gate",
        tongue=Tongue.RU,
        endpoint="https://hacker-news.firebaseio.com/v0/topstories.json",
        description="Top stories from the Hacker News chronicle",
        lore="Aria's portal to the Policy Chronicle — latest decrees from the tech realm.",
    ),
    "ru-hackernews-item": AetherGate(
        name="Chronicle Scroll",
        tongue=Tongue.RU,
        endpoint="https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
        description="Read a specific chronicle entry",
        lore="Unroll a single scroll from the Policy Chronicle.",
    ),
    "ru-wikipedia-summary": AetherGate(
        name="Lorekeeper's Gate",
        tongue=Tongue.RU,
        endpoint="https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
        description="Fetch encyclopedia summaries",
        lore="The Lorekeeper's portal to the world's largest knowledge archive.",
        headers={"User-Agent": "AetherGate/1.0 (SCBE-AETHERMOORE; issdandavis@gmail.com)"},
    ),
    "ru-open-trivia": AetherGate(
        name="Scholar's Trial Gate",
        tongue=Tongue.RU,
        endpoint="https://opentdb.com/api.php",
        description="Generate trivia challenges",
        lore="Test your knowledge at Aria's Scholar Trial — random questions from all domains.",
        params={"amount": "5", "type": "multiple"},
    ),
    # ── CA: Compute / Finance Gates ──
    "ca-bitcoin-price": AetherGate(
        name="Crypto Oracle",
        tongue=Tongue.CA,
        endpoint="https://api.coindesk.com/v1/bpi/currentprice.json",
        description="Current Bitcoin price index",
        lore="Zara's portal to the Crypto Oracle — real-time value from the computation realm.",
    ),
    "ca-coingecko-simple": AetherGate(
        name="Market Compass",
        tongue=Tongue.CA,
        endpoint="https://api.coingecko.com/api/v3/simple/price",
        description="Crypto prices across multiple coins",
        lore="The Market Compass tracks the pulse of digital currency realms.",
        params={"ids": "bitcoin,ethereum,solana", "vs_currencies": "usd"},
    ),
    "ca-exchange-rates": AetherGate(
        name="Currency Bridge",
        tongue=Tongue.CA,
        endpoint="https://open.er-api.com/v6/latest/USD",
        description="Current exchange rates from USD",
        lore="The Currency Bridge connects the financial realms of all nations.",
    ),
    "ca-numbers-math": AetherGate(
        name="Number Oracle",
        tongue=Tongue.CA,
        endpoint="http://numbersapi.com/random/math?json",
        description="Random mathematical facts",
        lore="Zara consults the Number Oracle for mathematical truths.",
    ),
    # ── UM: Security / Intel Gates ──
    "um-ip-geolocation": AetherGate(
        name="Shadow Scanner",
        tongue=Tongue.UM,
        endpoint="https://get.geojs.io/v1/ip/geo.json",
        description="Detailed IP geolocation intelligence",
        lore="Kael's Shadow Scanner — reveal the hidden location behind any network address.",
    ),
    "um-headers-inspect": AetherGate(
        name="Protocol Inspector",
        tongue=Tongue.UM,
        endpoint="https://httpbin.org/headers",
        description="Inspect your HTTP headers as others see them",
        lore="The Protocol Inspector reveals what you unknowingly broadcast.",
    ),
    "um-dns-lookup": AetherGate(
        name="Name Resolver",
        tongue=Tongue.UM,
        endpoint="https://dns.google/resolve",
        description="DNS resolution via Google",
        lore="The Name Resolver traces domain names to their true addresses.",
        params={"type": "A"},
    ),
    # ── DR: Schema / Random Data Gates ──
    "dr-random-quote": AetherGate(
        name="Wisdom Gate",
        tongue=Tongue.DR,
        endpoint="https://api.quotable.io/random",
        description="Random wisdom from the quote archives",
        lore="Polly's portal to the Wisdom Archive — 'CAW! Every quote holds a schema.'",
    ),
    "dr-random-advice": AetherGate(
        name="Oracle of Counsel",
        tongue=Tongue.DR,
        endpoint="https://api.adviceslip.com/advice",
        description="Random advice from the oracle",
        lore="The Oracle of Counsel speaks from the Schema dimension.",
    ),
    "dr-random-user": AetherGate(
        name="Identity Forge",
        tongue=Tongue.DR,
        endpoint="https://randomuser.me/api/",
        description="Generate random user profiles",
        lore="The Identity Forge creates phantom identities for testing portals.",
    ),
    "dr-placeholder-posts": AetherGate(
        name="Echo Chamber",
        tongue=Tongue.DR,
        endpoint="https://jsonplaceholder.typicode.com/posts",
        description="Placeholder content for testing",
        lore="The Echo Chamber generates phantom data for portal calibration.",
    ),
    "dr-pokemon": AetherGate(
        name="Creature Codex",
        tongue=Tongue.DR,
        endpoint="https://pokeapi.co/api/v2/pokemon/{name}",
        description="Look up creature data from the Pokémon realm",
        lore="The Creature Codex archives beings from a parallel dimension.",
    ),
}


# ── Rath: The Observer Agent ─────────────────────────────────────────


@dataclass
class RathObservation:
    """A single observation by Rath, the Observer Agent."""

    timestamp: str
    gate_name: str
    agent_id: str
    tier: str
    action: str  # "invoke", "denied", "error", "rate_limited"
    latency_ms: float
    success: bool
    details: str = ""


class RathObserver:
    """
    Rath — The Observer Agent from the Timeless Observatory.

    Like Rath in SAO: Alicization, this agent silently monitors all
    portal traffic, logs anomalies, and enforces rate limits.
    Rath does not intervene — only observes and records.
    """

    def __init__(self):
        self._log: List[RathObservation] = []
        self._rate_counters: Dict[str, List[float]] = {}  # agent -> [timestamps]
        self._log_path = REPO_ROOT / "artifacts" / "agent_comm" / "rath_observations.jsonl"

    def observe(self, obs: RathObservation) -> None:
        """Record an observation."""
        self._log.append(obs)
        self._persist(obs)

    def check_rate_limit(self, agent_id: str, max_rpm: int) -> bool:
        """Check if agent is within rate limit. Returns True if allowed."""
        if max_rpm <= 0:
            return False
        now = time.time()
        window = 60.0
        if agent_id not in self._rate_counters:
            self._rate_counters[agent_id] = []
        # Prune old entries
        self._rate_counters[agent_id] = [t for t in self._rate_counters[agent_id] if now - t < window]
        if len(self._rate_counters[agent_id]) >= max_rpm:
            return False
        self._rate_counters[agent_id].append(now)
        return True

    def _persist(self, obs: RathObservation) -> None:
        """Write observation to JSONL log."""
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(obs)) + "\n")
        except Exception:
            pass  # Rath never crashes the system

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent observations."""
        return [asdict(o) for o in self._log[-limit:]]

    def stats(self) -> Dict[str, Any]:
        """Return observation statistics."""
        total = len(self._log)
        denials = sum(1 for o in self._log if o.action == "denied")
        errors = sum(1 for o in self._log if o.action == "error")
        by_gate: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        for o in self._log:
            by_gate[o.gate_name] = by_gate.get(o.gate_name, 0) + 1
            by_agent[o.agent_id] = by_agent.get(o.agent_id, 0) + 1
        return {
            "total_observations": total,
            "denials": denials,
            "errors": errors,
            "by_gate": by_gate,
            "by_agent": by_agent,
        }


# Singleton observer
rath = RathObserver()


# ── Gate Invocation Engine ───────────────────────────────────────────


async def invoke_gate(
    gate_id: str,
    agent_id: str = "agent.claude",
    params: Optional[Dict[str, str]] = None,
    path_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Invoke an AetherGate with full governance checks.

    Args:
        gate_id: Registry key (e.g. "ca-bitcoin-price")
        agent_id: The calling agent
        params: Additional query parameters
        path_vars: Path template variables (e.g. {"title": "Python"} for Wikipedia)

    Returns:
        Gate response with metadata and Rath observation
    """
    if httpx is None:
        return {"ok": False, "error": "httpx not installed"}

    gate = GATE_REGISTRY.get(gate_id)
    if gate is None:
        return {"ok": False, "error": f"Unknown gate: {gate_id}"}

    if not gate.active:
        return {"ok": False, "error": f"Gate {gate_id} is dormant"}

    # Permission check
    perms = get_agent_permissions(agent_id)
    if not perms.get("can_invoke_gates"):
        obs = RathObservation(
            timestamp=_utc_now(),
            gate_name=gate_id,
            agent_id=agent_id,
            tier=perms["tier"],
            action="denied",
            latency_ms=0,
            success=False,
            details=f"Tier {perms['tier']} cannot invoke gates",
        )
        rath.observe(obs)
        return {"ok": False, "error": f"Permission denied: {perms['tier']} tier cannot invoke gates"}

    # Rate limit check
    max_rpm = perms.get("max_requests_per_minute", 10)
    if not rath.check_rate_limit(agent_id, max_rpm):
        obs = RathObservation(
            timestamp=_utc_now(),
            gate_name=gate_id,
            agent_id=agent_id,
            tier=perms["tier"],
            action="rate_limited",
            latency_ms=0,
            success=False,
            details=f"Rate limit exceeded: {max_rpm}/min",
        )
        rath.observe(obs)
        return {"ok": False, "error": f"Rate limited: {max_rpm} requests/minute for {perms['tier']} tier"}

    # Build URL with path variables
    url = gate.endpoint
    if path_vars:
        for key, val in path_vars.items():
            url = url.replace(f"{{{key}}}", val)

    # Merge params
    merged_params = {**gate.params}
    if params:
        merged_params.update(params)

    # Invoke
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if gate.method == "GET":
                resp = await client.get(url, params=merged_params, headers=gate.headers)
            else:
                resp = await client.post(url, json=merged_params, headers=gate.headers)

        latency = (time.monotonic() - start) * 1000

        if resp.status_code >= 400:
            obs = RathObservation(
                timestamp=_utc_now(),
                gate_name=gate_id,
                agent_id=agent_id,
                tier=perms["tier"],
                action="error",
                latency_ms=latency,
                success=False,
                details=f"HTTP {resp.status_code}",
            )
            rath.observe(obs)
            return {
                "ok": False,
                "gate": gate_id,
                "tongue": gate.tongue.value,
                "status": resp.status_code,
                "error": f"Gate returned HTTP {resp.status_code}",
            }

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if gate.response_key and isinstance(data, dict):
            data = data.get(gate.response_key, data)

        obs = RathObservation(
            timestamp=_utc_now(),
            gate_name=gate_id,
            agent_id=agent_id,
            tier=perms["tier"],
            action="invoke",
            latency_ms=latency,
            success=True,
        )
        rath.observe(obs)

        return {
            "ok": True,
            "gate": gate_id,
            "gate_name": gate.name,
            "tongue": gate.tongue.value,
            "lore": gate.lore,
            "latency_ms": round(latency, 1),
            "data": data,
        }

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        obs = RathObservation(
            timestamp=_utc_now(),
            gate_name=gate_id,
            agent_id=agent_id,
            tier=perms["tier"],
            action="error",
            latency_ms=latency,
            success=False,
            details=str(exc),
        )
        rath.observe(obs)
        return {"ok": False, "gate": gate_id, "error": str(exc)}


def list_gates(tongue: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all registered gates, optionally filtered by tongue."""
    gates = []
    for gid, gate in GATE_REGISTRY.items():
        if tongue and gate.tongue.value != tongue.upper():
            continue
        gates.append(
            {
                "id": gid,
                "name": gate.name,
                "tongue": gate.tongue.value,
                "endpoint": gate.endpoint,
                "description": gate.description,
                "lore": gate.lore,
                "min_tier": gate.min_tier.value,
                "active": gate.active,
            }
        )
    return gates


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
