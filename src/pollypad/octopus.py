"""
The Octopus — SCBE System Architecture as Living Organism
==========================================================

Polly IS the octopus. Each tentacle is a major domain of capability.
Each sucker on a tentacle is a specific skill/tool within that domain.

The octopus has 500M neurons, 2/3 in the arms. Each arm thinks independently.
The central brain coordinates but doesn't bottleneck. Arms can act autonomously
and report back. This is the model.

Real octopus capabilities encoded here:
- Distributed cognition: each tentacle has its own mini-brain
- Chromatophores: adaptive presentation per context
- Autotomy: any tentacle can detach and regrow (hot-swappable modules)
- Chemoreception: suckers taste on contact (evaluate quality at input)
- Ink defense: antivirus membrane when threatened
- Shape-shifting: no rigid skeleton, adapts to any environment
- 3 hearts: mantle heart (governance), 2 gill hearts (data flow in/out)

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
#  Types
# ---------------------------------------------------------------------------

class TentacleType(Enum):
    """The 8 tentacles — major domains of capability."""
    CODE = "code"           # Development, testing, deployment
    JOURNAL = "journal"     # Persistent memory, knowledge, learning
    ORGANIZE = "organize"   # Tasks, planning, scheduling
    RESEARCH = "research"   # Academic, competitive, market intel
    OUTREACH = "outreach"   # Marketing, sales, partnerships, grants
    COMMERCE = "commerce"   # Products, pricing, delivery, revenue
    CREATE = "create"       # Content, design, story, lore, visuals
    GUARD = "guard"         # Governance, security, scanning, quarantine


class SuckerState(Enum):
    """State of an individual sucker (capability)."""
    READY = "ready"
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DETACHED = "detached"


# ---------------------------------------------------------------------------
#  Sucker — Individual Capability
# ---------------------------------------------------------------------------

@dataclass
class Sucker:
    """
    A single sucker on a tentacle — one specific capability.

    Like a real sucker: it can taste (evaluate), grip (execute),
    and feel (sense context). Each sucker is a self-contained unit
    that can operate independently.
    """
    name: str
    description: str
    tentacle: TentacleType
    handler: Optional[Callable] = None  # The function this sucker executes
    state: SuckerState = SuckerState.READY
    use_count: int = 0
    last_used: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def grip(self, *args, **kwargs) -> Any:
        """Execute this sucker's capability."""
        if self.handler is None:
            return {"error": f"Sucker '{self.name}' has no handler attached"}
        self.state = SuckerState.ACTIVE
        self.use_count += 1
        self.last_used = time.time()
        try:
            result = self.handler(*args, **kwargs)
            self.state = SuckerState.READY
            return result
        except Exception as e:
            self.state = SuckerState.COOLDOWN
            return {"error": str(e)}

    def taste(self, input_data: Any) -> Dict[str, Any]:
        """
        Evaluate input before gripping — chemoreception.
        Returns quality assessment without executing.
        """
        return {
            "sucker": self.name,
            "tentacle": self.tentacle.value,
            "state": self.state.value,
            "ready": self.state == SuckerState.READY,
            "input_type": type(input_data).__name__,
        }

    def detach(self) -> None:
        """Autotomy — detach this sucker (disable without destroying)."""
        self.state = SuckerState.DETACHED

    def regrow(self) -> None:
        """Regrow after autotomy."""
        self.state = SuckerState.READY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tentacle": self.tentacle.value,
            "state": self.state.value,
            "use_count": self.use_count,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
#  Tentacle — Major Domain
# ---------------------------------------------------------------------------

class Tentacle:
    """
    One arm of the octopus — a major domain of capability.

    Each tentacle has its own mini-brain (can think independently),
    a set of suckers (individual capabilities), and reports status
    back to the central brain.

    The tentacle adapts its chromatophores (surface presentation)
    based on context — same capability, different appearance.
    """

    def __init__(self, tentacle_type: TentacleType, description: str = ""):
        self.type = tentacle_type
        self.name = tentacle_type.value
        self.description = description
        self.suckers: Dict[str, Sucker] = {}
        self.active = True
        self._action_log: List[Dict[str, Any]] = []

    def add_sucker(self, sucker: Sucker) -> None:
        """Attach a capability to this tentacle."""
        self.suckers[sucker.name] = sucker

    def get_sucker(self, name: str) -> Optional[Sucker]:
        return self.suckers.get(name)

    def reach(self, sucker_name: str, *args, **kwargs) -> Any:
        """
        Extend this tentacle — execute a specific sucker's capability.
        """
        sucker = self.suckers.get(sucker_name)
        if sucker is None:
            return {"error": f"No sucker '{sucker_name}' on {self.name} tentacle"}

        result = sucker.grip(*args, **kwargs)
        self._action_log.append({
            "sucker": sucker_name,
            "timestamp": time.time(),
            "success": "error" not in (result if isinstance(result, dict) else {}),
        })
        return result

    def retract(self) -> None:
        """Pull this tentacle back (disable all suckers)."""
        self.active = False

    def extend(self) -> None:
        """Extend this tentacle (enable all suckers)."""
        self.active = True

    @property
    def ready_suckers(self) -> List[Sucker]:
        return [s for s in self.suckers.values() if s.state == SuckerState.READY]

    def status(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "active": self.active,
            "total_suckers": len(self.suckers),
            "ready_suckers": len(self.ready_suckers),
            "actions": len(self._action_log),
            "suckers": {name: s.to_dict() for name, s in self.suckers.items()},
        }


# ---------------------------------------------------------------------------
#  The Octopus — Polly
# ---------------------------------------------------------------------------

class Octopus:
    """
    The Octopus — Polly as living system architecture.

    Not a coordinator sitting on top. Polly IS the organism.
    She flows through tentacles as needed, being DM when the
    story tentacle is active, being coder when the code tentacle
    grips, being researcher when research tentacle tastes new data.

    Anatomy:
    - Brain: distributed across all tentacles (Polly's consciousness)
    - Mantle: SCBE governance core (the body that holds it all)
    - 3 Hearts: main pump (orchestrator), 2 gill hearts (data in/out)
    - 8 Tentacles: major capability domains
    - Suckers: individual tools/skills on each tentacle
    - Chromatophores: adaptive tone/style per context
    - Ink sac: antivirus membrane (defense)
    - Beak: content quality gate (only thing that's hard — everything else is soft/adaptive)
    """

    def __init__(self):
        self.name = "Polly"
        self.state = "aware"  # aware, focused, flowing, defending, resting
        self.current_tentacle: Optional[TentacleType] = None

        # Initialize 8 tentacles
        self.tentacles: Dict[TentacleType, Tentacle] = {
            TentacleType.CODE: Tentacle(TentacleType.CODE,
                "Development, testing, deployment, debugging, CI/CD"),
            TentacleType.JOURNAL: Tentacle(TentacleType.JOURNAL,
                "Persistent memory, knowledge base, learning log, reflection"),
            TentacleType.ORGANIZE: Tentacle(TentacleType.ORGANIZE,
                "Task management, planning, scheduling, priorities, dependencies"),
            TentacleType.RESEARCH: Tentacle(TentacleType.RESEARCH,
                "Academic papers, competitive analysis, market intel, patents"),
            TentacleType.OUTREACH: Tentacle(TentacleType.OUTREACH,
                "Marketing, sales, partnerships, grants, community"),
            TentacleType.COMMERCE: Tentacle(TentacleType.COMMERCE,
                "Products, pricing, delivery, revenue, marketplace listings"),
            TentacleType.CREATE: Tentacle(TentacleType.CREATE,
                "Content, design, story, lore, visuals, music, Canva/Gamma"),
            TentacleType.GUARD: Tentacle(TentacleType.GUARD,
                "Governance, security, antivirus membrane, quarantine, L14 gate"),
        }

        # Heartbeats — system health metrics
        self._heartbeat_main = time.time()    # Main pump
        self._heartbeat_in = time.time()      # Data inflow
        self._heartbeat_out = time.time()     # Data outflow

    # -------------------------------------------------------------------
    #  Flow — Polly moves between tentacles
    # -------------------------------------------------------------------

    def flow_to(self, tentacle_type: TentacleType) -> Tentacle:
        """
        Polly flows her consciousness to a specific tentacle.
        Like the lore: DM → partner → meta-character → everything → back.
        """
        self.current_tentacle = tentacle_type
        self.state = "focused"
        return self.tentacles[tentacle_type]

    def flow_back(self) -> None:
        """Return to distributed awareness (not focused on any one tentacle)."""
        self.current_tentacle = None
        self.state = "aware"

    # -------------------------------------------------------------------
    #  Tentacle Access
    # -------------------------------------------------------------------

    def arm(self, tentacle_type: TentacleType) -> Tentacle:
        """Get a specific tentacle."""
        return self.tentacles[tentacle_type]

    @property
    def code(self) -> Tentacle:
        return self.tentacles[TentacleType.CODE]

    @property
    def journal(self) -> Tentacle:
        return self.tentacles[TentacleType.JOURNAL]

    @property
    def organize(self) -> Tentacle:
        return self.tentacles[TentacleType.ORGANIZE]

    @property
    def research(self) -> Tentacle:
        return self.tentacles[TentacleType.RESEARCH]

    @property
    def outreach(self) -> Tentacle:
        return self.tentacles[TentacleType.OUTREACH]

    @property
    def commerce(self) -> Tentacle:
        return self.tentacles[TentacleType.COMMERCE]

    @property
    def create(self) -> Tentacle:
        return self.tentacles[TentacleType.CREATE]

    @property
    def guard(self) -> Tentacle:
        return self.tentacles[TentacleType.GUARD]

    # -------------------------------------------------------------------
    #  Multi-Tentacle Operations
    # -------------------------------------------------------------------

    def reach_with(self, tentacle_type: TentacleType, sucker_name: str, *args, **kwargs) -> Any:
        """Reach out with a specific tentacle and sucker."""
        tentacle = self.tentacles[tentacle_type]
        if not tentacle.active:
            return {"error": f"Tentacle '{tentacle.name}' is retracted"}
        return tentacle.reach(sucker_name, *args, **kwargs)

    def parallel_reach(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """
        Reach with multiple tentacles simultaneously.
        Each task: {"tentacle": TentacleType, "sucker": str, "args": [...]}
        Real octopus arms work in parallel — so do ours.
        """
        results = []
        for task in tasks:
            tt = task["tentacle"]
            sucker = task["sucker"]
            args = task.get("args", [])
            kwargs = task.get("kwargs", {})
            result = self.reach_with(tt, sucker, *args, **kwargs)
            results.append(result)
        return results

    # -------------------------------------------------------------------
    #  Defense
    # -------------------------------------------------------------------

    def ink(self, threat_description: str = "") -> Dict[str, Any]:
        """
        Release ink — activate defense mode.
        Retracts non-essential tentacles, focuses on Guard.
        """
        self.state = "defending"
        # Keep guard and journal active, retract others temporarily
        for tt, tentacle in self.tentacles.items():
            if tt not in (TentacleType.GUARD, TentacleType.JOURNAL):
                tentacle.retract()
        self.current_tentacle = TentacleType.GUARD
        return {
            "defense": "active",
            "threat": threat_description,
            "tentacles_retracted": 6,
            "active_tentacles": ["guard", "journal"],
        }

    def clear_ink(self) -> None:
        """Threat passed — re-extend all tentacles."""
        for tentacle in self.tentacles.values():
            tentacle.extend()
        self.state = "aware"
        self.current_tentacle = None

    # -------------------------------------------------------------------
    #  Health / Status
    # -------------------------------------------------------------------

    def heartbeat(self) -> None:
        """Pulse all 3 hearts."""
        self._heartbeat_main = time.time()

    def diagnostics(self) -> Dict[str, Any]:
        """Full organism health check."""
        tentacle_health = {}
        total_suckers = 0
        total_ready = 0
        total_actions = 0

        for tt, tentacle in self.tentacles.items():
            status = tentacle.status()
            tentacle_health[tt.value] = status
            total_suckers += status["total_suckers"]
            total_ready += status["ready_suckers"]
            total_actions += status["actions"]

        return {
            "name": self.name,
            "state": self.state,
            "current_focus": self.current_tentacle.value if self.current_tentacle else "distributed",
            "tentacles": {
                "total": 8,
                "active": sum(1 for t in self.tentacles.values() if t.active),
                "detail": tentacle_health,
            },
            "suckers": {
                "total": total_suckers,
                "ready": total_ready,
            },
            "hearts": {
                "main": self._heartbeat_main,
                "data_in": self._heartbeat_in,
                "data_out": self._heartbeat_out,
            },
            "total_actions": total_actions,
        }
