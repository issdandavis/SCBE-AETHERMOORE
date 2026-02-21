"""
Aethermoor Spiral Engine (MVP)
==============================

Linux-first deterministic strategy simulation that maps SCBE runtime signals into
playable systems:

- Exploration map (procedural regions)
- Inventory + crafting
- Skill progression
- Mission routing through Sacred Tongues
- Sheaf-cohomology consistency checks (Tarski fixed-point on temporal lattice)
- Temporal harmonic gate for ALLOW / QUARANTINE / DENY / EXILE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random
from typing import Dict, List, Tuple

from .temporal_intent import TemporalSecurityGate, IntentState, MAX_INTENT_ACCUMULATION
from ..harmonic.tarski_sheaf import (
    TemporalSheaf,
    make_temporal_sheaf,
    fail_to_noise_projection,
    obstruction_count,
)
from ..scbe_math_reference import triadic_risk


TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


class Action(str, Enum):
    EXPLORE = "explore"
    ROUTE = "route"
    CRAFT = "craft"
    STABILIZE = "stabilize"
    RESOLVE_QUARANTINE = "resolve_quarantine"


@dataclass(frozen=True)
class Region:
    region_id: int
    name: str
    hazard: float  # 0..1 (distance pressure)
    richness: float  # 0..1 (resource yield)
    discovered: bool = False


@dataclass
class Mission:
    mission_id: str
    name: str
    objective_packets: int
    packets_routed: int = 0
    quarantines: int = 0
    denials: int = 0
    completed: bool = False


@dataclass
class Inventory:
    alloy: int = 0
    crystal: int = 0
    data_shard: int = 0
    consensus_seal: int = 0
    spectral_filter: int = 0


@dataclass(frozen=True)
class VoxelCell:
    key: str
    terrain: str
    x: int
    y: int
    z: int
    v: int
    p: int
    s: int
    heat: float
    coherence: float


@dataclass
class SkillTree:
    tongues: Dict[str, int] = field(default_factory=lambda: {t: 0 for t in TONGUES})
    pads: Dict[str, int] = field(
        default_factory=lambda: {
            "engineering": 0,
            "navigation": 0,
            "systems": 0,
            "science": 0,
            "communications": 0,
            "mission_planning": 0,
        }
    )
    skill_points: int = 0


@dataclass
class TurnOutcome:
    tick: int
    action: Action
    tongue: str
    region_id: int
    distance: float
    x_factor: float
    harmonic_wall: float
    harm_score: float
    friction_multiplier: float
    omega: float
    decision: str
    permission_color: str
    weakest_lock: str
    lock_vector: Dict[str, float | str]
    voxel_key: str
    terrain: str
    voxel_discovered: bool
    watcher_fast: float
    watcher_memory: float
    watcher_governance: float
    d_tri: float
    triadic_from_rings: float
    triadic_from_sheaf: float
    triadic_stable: float
    sheaf_obstructions: int
    trust: float
    coherence: float
    mission_progress: Tuple[int, int]
    inventory: Inventory
    notes: List[str]


@dataclass
class PlayerState:
    current_region: int = 0
    selected_tongue: str = "KO"
    trust: float = 1.0
    coherence: float = 1.0
    accumulated_intent: float = 0.0
    entropy: float = 0.05


class AethermoorSpiralEngine:
    """
    First-playable Spiral Engine with SCBE decision chain + sheaf consistency.
    """

    def __init__(self, seed: int = 42, region_count: int = 16) -> None:
        self._rng = random.Random(seed)
        self.seed = seed
        self.tick = 0
        self.player = PlayerState()
        self.inventory = Inventory(alloy=2, crystal=1, data_shard=1)
        self.skills = SkillTree()
        self.world = self._generate_world(region_count)
        self.voxels: Dict[str, VoxelCell] = {}
        self.mission = Mission(
            mission_id="M-001",
            name="Stabilize Aethermoor Relay",
            objective_packets=12,
        )
        self._gate = TemporalSecurityGate()
        self._agent_id = "architect"

    # ---------------------------------------------------------------------
    # Map, skills, and sheaf system
    # ---------------------------------------------------------------------

    def _generate_world(self, n: int) -> List[Region]:
        names = [
            "Core Basin",
            "Lantern Verge",
            "Mirror Dunes",
            "Aether Rift",
            "Crown Shoals",
            "Drift Bloom",
            "Obsidian Fold",
            "Whisper Step",
            "Torus Reach",
            "Glass Delta",
            "Pillar Fault",
            "Bright Hollow",
            "Night Lattice",
            "Delta Gate",
            "Phase Garden",
            "Rook Shelf",
        ]
        regions: List[Region] = []
        for i in range(n):
            hazard = min(1.0, max(0.0, self._rng.uniform(0.05, 0.95)))
            richness = min(1.0, max(0.0, self._rng.uniform(0.10, 0.95)))
            regions.append(
                Region(
                    region_id=i,
                    name=names[i % len(names)],
                    hazard=hazard,
                    richness=richness,
                    discovered=(i == 0),
                )
            )
        return regions

    def select_tongue(self, tongue: str) -> None:
        t = str(tongue).upper()
        if t not in TONGUES:
            raise ValueError(f"invalid tongue: {tongue}")
        self.player.selected_tongue = t

    def upgrade_tongue(self, tongue: str) -> bool:
        t = str(tongue).upper()
        if t not in TONGUES or self.skills.skill_points < 1:
            return False
        self.skills.skill_points -= 1
        self.skills.tongues[t] += 1
        return True

    def _spectral_score(self, tongue: str) -> float:
        base = {
            "KO": 0.78,
            "AV": 0.80,
            "RU": 0.76,
            "CA": 0.82,
            "UM": 0.74,
            "DR": 0.79,
        }[tongue]
        lvl = self.skills.tongues[tongue]
        return min(0.99, base + 0.03 * lvl)

    def _triadic_obstruction(self, distance: float, entropy: float, trust: float) -> tuple[float, int]:
        # Map continuous signals to a 4-level lattice {0,1,2,3}
        # 0 = ALLOW-like, 3 = DENY-like.
        fast = min(3, int(distance * 4.0))
        memory = min(3, int(self.player.accumulated_intent / 2.5))
        governance = min(3, int((1.0 - trust) * 4.0 + entropy * 2.0))

        assignment = {"Ti": fast, "Tm": memory, "Tg": governance}

        # Twisted but monotone temporal restrictions: future cannot relax more than 1 level.
        def relax_one(v: int) -> int:
            return max(0, v - 1)

        twisted = {
            ("Ti", "Tm"): relax_one,
            ("Tm", "Tg"): relax_one,
        }
        sheaf: TemporalSheaf = make_temporal_sheaf(
            nodes=("Ti", "Tm", "Tg"),
            lattice_values=(0, 1, 2, 3),
            twisted_edges=twisted,
        )
        _ = fail_to_noise_projection(sheaf, assignment)
        obs = obstruction_count(sheaf, assignment)
        stable = max(0.0, 1.0 - obs / 3.0)
        return stable, obs

    # ---------------------------------------------------------------------
    # Crafting and actions
    # ---------------------------------------------------------------------

    def craft(self, item: str) -> bool:
        key = item.strip().lower()
        if key == "consensus_seal":
            if self.inventory.alloy >= 2 and self.inventory.crystal >= 1:
                self.inventory.alloy -= 2
                self.inventory.crystal -= 1
                self.inventory.consensus_seal += 1
                return True
            return False
        if key == "spectral_filter":
            if self.inventory.data_shard >= 2 and self.inventory.crystal >= 1:
                self.inventory.data_shard -= 2
                self.inventory.crystal -= 1
                self.inventory.spectral_filter += 1
                return True
            return False
        return False

    def _explore_step(self) -> List[str]:
        notes: List[str] = []
        current = self.player.current_region
        candidates = [i for i in range(len(self.world)) if i != current]
        nxt = self._rng.choice(candidates)
        self.player.current_region = nxt
        region = self.world[nxt]
        if not region.discovered:
            self.world[nxt] = Region(
                region_id=region.region_id,
                name=region.name,
                hazard=region.hazard,
                richness=region.richness,
                discovered=True,
            )
            notes.append(f"discovered:{region.name}")
        yield_roll = self._rng.random()
        if yield_roll < region.richness:
            self.inventory.data_shard += 1
            notes.append("found:data_shard")
        if yield_roll < region.richness * 0.65:
            self.inventory.alloy += 1
            notes.append("found:alloy")
        if yield_roll < region.richness * 0.35:
            self.inventory.crystal += 1
            notes.append("found:crystal")
        return notes

    def _route_packet(self, decision: str) -> None:
        if decision == "ALLOW":
            self.mission.packets_routed += 1
            if self.mission.packets_routed >= self.mission.objective_packets:
                self.mission.completed = True
            self.skills.skill_points += 1
        elif decision == "QUARANTINE":
            self.mission.quarantines += 1
        elif decision in {"DENY", "EXILE"}:
            self.mission.denials += 1

    @staticmethod
    def _q01(value: float, bins: int = 16) -> int:
        val = max(0.0, min(1.0, float(value)))
        return min(bins - 1, int(val * bins))

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _terrain_from_coherence(hazard: float, coherence: float, heat: float) -> str:
        if coherence >= 0.75 and hazard <= 0.40:
            return "glow_meadow"
        if coherence >= 0.60 and heat < 0.20:
            return "crystal_garden"
        if coherence <= 0.30 and hazard >= 0.70:
            return "storm_maw"
        if coherence <= 0.45:
            return "shadow_brush"
        if hazard >= 0.75:
            return "rift_spines"
        return "ember_steppe"

    def _discover_voxel(self, region: Region, distance: float) -> tuple[VoxelCell, bool]:
        # Coherence-shaped procedural voxel address [X,Y,Z,V,P,S].
        x = region.region_id % 16
        y = self._q01(region.hazard)
        z = self._q01(region.richness)
        v = self._q01(1.0 - self.player.coherence)
        p = self._q01(distance)
        s = self._q01((self.player.coherence * 0.65) + ((1.0 - region.hazard) * 0.35))
        key = f"{x:02d}:{y:02d}:{z:02d}:{v:02d}:{p:02d}:{s:02d}"

        heat = min(1.0, distance * max(0.5, self.player.accumulated_intent))
        terrain = self._terrain_from_coherence(region.hazard, self.player.coherence, heat)
        cell = VoxelCell(
            key=key,
            terrain=terrain,
            x=x,
            y=y,
            z=z,
            v=v,
            p=p,
            s=s,
            heat=heat,
            coherence=self.player.coherence,
        )
        is_new = key not in self.voxels
        self.voxels[key] = cell
        return cell, is_new

    def _three_watchers(self, distance: float, trust: float, entropy: float) -> dict[str, float]:
        # Three watcher ring signals normalized to 0..1.
        i_fast = self._clamp01(distance)
        i_memory = self._clamp01(self.player.accumulated_intent / MAX_INTENT_ACCUMULATION)
        i_governance = self._clamp01(((1.0 - trust) * 0.7) + (entropy * 0.3))
        d_tri = self._clamp01(triadic_risk(i_fast, i_memory, i_governance))
        triadic_from_rings = self._clamp01(1.0 - d_tri)
        return {
            "i_fast": i_fast,
            "i_memory": i_memory,
            "i_governance": i_governance,
            "d_tri": d_tri,
            "triadic_from_rings": triadic_from_rings,
        }

    # ---------------------------------------------------------------------
    # Main turn step
    # ---------------------------------------------------------------------

    def step(self, action: Action, *, craft_item: str = "") -> TurnOutcome:
        self.tick += 1
        notes: List[str] = []
        tongue = self.player.selected_tongue
        region = self.world[self.player.current_region]

        if action == Action.EXPLORE:
            notes.extend(self._explore_step())
            region = self.world[self.player.current_region]
        elif action == Action.CRAFT:
            ok = self.craft(craft_item)
            notes.append(f"craft:{craft_item}:{'ok' if ok else 'fail'}")
        elif action == Action.STABILIZE:
            if self.inventory.consensus_seal > 0:
                self.inventory.consensus_seal -= 1
                self.player.coherence = min(1.0, self.player.coherence + 0.08)
                self.player.trust = min(1.0, self.player.trust + 0.05)
                notes.append("stabilize:seal")
            else:
                self.player.coherence = min(1.0, self.player.coherence + 0.02)
                notes.append("stabilize:minor")
        elif action == Action.RESOLVE_QUARANTINE:
            # Expensive but lowers intent heat
            spend = min(self.inventory.data_shard, 1)
            self.inventory.data_shard -= spend
            self.player.accumulated_intent = max(0.0, self.player.accumulated_intent - 0.6 - 0.2 * spend)
            self.player.coherence = min(1.0, self.player.coherence + 0.04)
            notes.append("quarantine_resolve")

        # --- SCBE chain signals ---
        distance = min(0.995, max(0.0, region.hazard + self._rng.uniform(-0.04, 0.04)))
        velocity = max(0.0, distance - self.player.coherence * 0.35)
        harmony = max(-1.0, min(1.0, 2.0 * self.player.coherence - 1.0))

        self._gate.record_observation(
            self._agent_id,
            distance=distance,
            velocity=velocity,
            harmony=harmony,
        )
        status = self._gate.get_status(self._agent_id)
        self.player.trust = float(status["trust_score"])
        self.player.accumulated_intent = float(status["accumulated_intent"])

        triadic_from_sheaf, obs = self._triadic_obstruction(
            distance=distance,
            entropy=self.player.entropy,
            trust=self.player.trust,
        )
        watchers = self._three_watchers(distance=distance, trust=self.player.trust, entropy=self.player.entropy)
        triadic_stable = self._clamp01(triadic_from_sheaf * watchers["triadic_from_rings"])

        spectral = self._spectral_score(tongue)
        if self.inventory.spectral_filter > 0:
            spectral = min(0.99, spectral + 0.05)

        lock = self._gate.compute_lock_vector(
            self._agent_id,
            pqc_valid=True,
            triadic_stable=triadic_stable,
            spectral_score=spectral,
        )
        omega = lock.omega

        # Game-facing decision bands tuned for playability while preserving fail-closed exile.
        if lock.decision == "EXILE":
            decision = "EXILE"
        elif omega >= 0.70:
            decision = "ALLOW"
        elif omega >= 0.30:
            decision = "QUARANTINE"
        else:
            decision = "DENY"

        self.player.coherence = max(0.0, min(1.0, 0.55 * self.player.coherence + 0.45 * triadic_stable))
        self.player.entropy = max(0.0, min(1.0, 1.0 - self.player.coherence))

        voxel, voxel_discovered = self._discover_voxel(region, distance)

        self._route_packet(decision)
        if decision == "QUARANTINE":
            notes.append("event:quarantine")
        elif decision == "DENY":
            notes.append("event:deny")
        elif decision == "EXILE":
            notes.append("event:exile")
        elif decision == "ALLOW":
            notes.append("event:allow")
        notes.append(
            "watchers:"
            f"fast={watchers['i_fast']:.3f},"
            f"memory={watchers['i_memory']:.3f},"
            f"governance={watchers['i_governance']:.3f},"
            f"d_tri={watchers['d_tri']:.3f}"
        )
        if voxel_discovered:
            notes.append(f"voxel:new:{voxel.key}:{voxel.terrain}")
        else:
            notes.append(f"voxel:seen:{voxel.key}")

        return TurnOutcome(
            tick=self.tick,
            action=action,
            tongue=tongue,
            region_id=self.player.current_region,
            distance=distance,
            x_factor=float(status["x_factor"]),
            harmonic_wall=lock.harmonic_wall,
            harm_score=lock.harm_score,
            friction_multiplier=lock.latency_multiplier,
            omega=omega,
            decision=decision,
            permission_color=lock.permission_color,
            weakest_lock=lock.weakest_lock,
            lock_vector=lock.to_dict(),
            voxel_key=voxel.key,
            terrain=voxel.terrain,
            voxel_discovered=voxel_discovered,
            watcher_fast=watchers["i_fast"],
            watcher_memory=watchers["i_memory"],
            watcher_governance=watchers["i_governance"],
            d_tri=watchers["d_tri"],
            triadic_from_rings=watchers["triadic_from_rings"],
            triadic_from_sheaf=triadic_from_sheaf,
            triadic_stable=triadic_stable,
            sheaf_obstructions=obs,
            trust=self.player.trust,
            coherence=self.player.coherence,
            mission_progress=(self.mission.packets_routed, self.mission.objective_packets),
            inventory=Inventory(**self.inventory.__dict__),
            notes=notes,
        )

    def snapshot(self) -> dict:
        return {
            "tick": self.tick,
            "region": self.player.current_region,
            "tongue": self.player.selected_tongue,
            "trust": round(self.player.trust, 6),
            "coherence": round(self.player.coherence, 6),
            "intent": round(self.player.accumulated_intent, 6),
            "mission": {
                "id": self.mission.mission_id,
                "name": self.mission.name,
                "routed": self.mission.packets_routed,
                "target": self.mission.objective_packets,
                "quarantines": self.mission.quarantines,
                "denials": self.mission.denials,
                "completed": self.mission.completed,
            },
            "inventory": self.inventory.__dict__,
            "skills": {
                "tongues": self.skills.tongues,
                "pads": self.skills.pads,
                "skill_points": self.skills.skill_points,
            },
            "voxels": {
                "discovered": len(self.voxels),
            },
        }


def run_demo(seed: int = 7, turns: int = 12) -> dict:
    """
    Deterministic smoke simulation for CLI/docs.
    """
    engine = AethermoorSpiralEngine(seed=seed, region_count=12)
    actions = [
        Action.EXPLORE,
        Action.ROUTE,
        Action.ROUTE,
        Action.CRAFT,
        Action.STABILIZE,
        Action.EXPLORE,
        Action.ROUTE,
        Action.RESOLVE_QUARANTINE,
        Action.ROUTE,
        Action.EXPLORE,
        Action.ROUTE,
        Action.STABILIZE,
    ]
    history: List[dict] = []
    for i in range(turns):
        action = actions[i % len(actions)]
        craft_item = "consensus_seal" if action == Action.CRAFT else ""
        out = engine.step(action, craft_item=craft_item)
        history.append(
            {
                "tick": out.tick,
                "action": out.action.value,
                "decision": out.decision,
                "omega": round(out.omega, 6),
                "harm_score": round(out.harm_score, 6),
                "friction": round(out.friction_multiplier, 6),
                "permission_color": out.permission_color,
                "weakest_lock": out.weakest_lock,
                "voxel_key": out.voxel_key,
                "terrain": out.terrain,
                "voxel_discovered": out.voxel_discovered,
                "watchers": {
                    "fast": round(out.watcher_fast, 6),
                    "memory": round(out.watcher_memory, 6),
                    "governance": round(out.watcher_governance, 6),
                    "d_tri": round(out.d_tri, 6),
                },
                "omega_factors": {
                    "pqc": out.lock_vector["pqc_factor"],
                    "harm": out.lock_vector["harm_score"],
                    "drift": out.lock_vector["drift_factor"],
                    "triadic": out.lock_vector["triadic_stable"],
                    "spectral": out.lock_vector["spectral_score"],
                },
                "obstructions": out.sheaf_obstructions,
                "progress": list(out.mission_progress),
            }
        )
    return {"final": engine.snapshot(), "history": history}
