"""
Sacred Egg Node — each sphere grid node IS a Sacred Egg.

An egg is:
  - An Obsidian note (knowledge/state frontmatter)
  - A 21D CanonicalState (position on the manifold)
  - An n8n workflow trigger (hyperlane connection)
  - A governance gate (hatching condition)

Hatching = unlocking the node on the sphere grid.
Hatching conditions = governance thresholds on the 21D state.

Obsidian note format:
  ---
  egg_name: "korath-scout"
  tongue: KO
  phase: SENSE
  state_21d: [0.5, 0.05, 0.05, 0.05, 0.05, 0.05, 0.0, ...]
  hatching_conditions:
    min_tongue_strength: 0.3
    min_coherence: 0.5
    required_tongues: [KO]
  n8n_trigger: "webhook:egg-korath-scout"
  connected_eggs: ["avali-fetch", "runecub-validate"]
  ---
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .canonical_state import (
    TONGUE_NAMES,
    TONGUE_PHASES,
    TONGUE_WEIGHTS,
    CanonicalState,
    compute_ds_squared,
    governance_gate,
    harmonic_wall_cost,
)


@dataclass
class HatchingCondition:
    """Conditions that must be met for a Sacred Egg to hatch (node unlock)."""
    min_tongue_strength: float = 0.3
    min_coherence: float = 0.5
    required_tongues: List[int] = field(default_factory=lambda: [0])
    max_risk: float = 0.8
    max_entropy_density: float = 2.0

    def check(self, player_state: CanonicalState) -> bool:
        for tongue_idx in self.required_tongues:
            if player_state.data[tongue_idx] < self.min_tongue_strength:
                return False
        if player_state.coherence < self.min_coherence:
            return False
        if player_state.risk > self.max_risk:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "min_tongue_strength": self.min_tongue_strength,
            "min_coherence": self.min_coherence,
            "required_tongues": [TONGUE_NAMES[t] for t in self.required_tongues],
            "max_risk": self.max_risk,
            "max_entropy_density": self.max_entropy_density,
        }


@dataclass
class SacredEggNode:
    """A Sacred Egg = a sphere grid node with hatching mechanics."""
    name: str
    skill_name: str  # maps to a real skill
    tongue: int
    phase: str  # SENSE, PLAN, EXECUTE, PUBLISH
    state: CanonicalState
    hatching: HatchingCondition
    hatched: bool = False
    hatch_timestamp: Optional[float] = None
    connected_eggs: List[str] = field(default_factory=list)
    n8n_webhook_id: str = ""
    obsidian_note_path: str = ""
    invocation_count: int = 0
    training_pairs_generated: int = 0

    @property
    def tongue_name(self) -> str:
        return TONGUE_NAMES[self.tongue]

    @property
    def n8n_trigger_url(self) -> str:
        return f"http://127.0.0.1:5680/webhook/egg-{self.name}"

    def try_hatch(self, player_state: CanonicalState) -> bool:
        if self.hatched:
            return True
        if self.hatching.check(player_state):
            self.hatched = True
            self.hatch_timestamp = time.time()
            return True
        return False

    def generate_training_pair(self, action: str, outcome: str, player_state: CanonicalState) -> dict:
        """Generate an SFT training pair from this egg's invocation."""
        self.training_pairs_generated += 1
        ds2 = compute_ds_squared(player_state, self.state)
        decision = governance_gate(player_state, self.tongue)
        return {
            "instruction": f"Navigate to {self.name} ({self.phase}/{self.tongue_name}) and {action}",
            "input": json.dumps({
                "player_state_21d": list(player_state.data),
                "egg_state_21d": list(self.state.data),
                "ds_squared": ds2,
                "governance_decision": decision,
                "phase": self.phase,
                "tongue": self.tongue_name,
            }),
            "output": outcome,
            "metadata": {
                "egg": self.name,
                "skill": self.skill_name,
                "phase": self.phase,
                "tongue": self.tongue_name,
                "ds2_total": ds2["total"],
                "timestamp": time.time(),
            },
        }

    def to_obsidian_frontmatter(self) -> str:
        """Generate Obsidian YAML frontmatter for this egg."""
        lines = ["---"]
        lines.append(f"egg_name: \"{self.name}\"")
        lines.append(f"skill: \"{self.skill_name}\"")
        lines.append(f"tongue: {self.tongue_name}")
        lines.append(f"phase: {self.phase}")
        lines.append(f"hatched: {str(self.hatched).lower()}")
        lines.append(f"difficulty: {self.hatching.min_tongue_strength:.2f}")
        lines.append(f"n8n_trigger: \"webhook:egg-{self.name}\"")
        lines.append(f"connected_eggs: [{', '.join(self.connected_eggs)}]")
        lines.append(f"state_radius: {self.state.radius:.4f}")
        lines.append(f"state_coherence: {self.state.coherence:.4f}")
        lines.append(f"state_risk: {self.state.risk:.4f}")
        lines.append(f"invocations: {self.invocation_count}")
        lines.append(f"training_pairs: {self.training_pairs_generated}")
        lines.append("---")
        return "\n".join(lines)

    def to_obsidian_note(self) -> str:
        """Generate a complete Obsidian note for this egg."""
        fm = self.to_obsidian_frontmatter()
        body_lines = [
            f"# {self.name}",
            "",
            f"**Phase**: {self.phase} | **Tongue**: {self.tongue_name} | "
            f"**Status**: {'Hatched' if self.hatched else 'Sealed'}",
            "",
            "## Connections (Hyperlanes)",
            "",
        ]
        for conn in self.connected_eggs:
            body_lines.append(f"- [[{conn}]]")
        body_lines.extend([
            "",
            "## Hatching Conditions",
            "",
            f"- Min tongue strength ({self.tongue_name}): {self.hatching.min_tongue_strength:.2f}",
            f"- Min coherence: {self.hatching.min_coherence:.2f}",
            f"- Required tongues: {', '.join(TONGUE_NAMES[t] for t in self.hatching.required_tongues)}",
            f"- Max risk: {self.hatching.max_risk:.2f}",
            "",
            "## n8n Workflow Trigger",
            "",
            f"```",
            f"POST {self.n8n_trigger_url}",
            f"Content-Type: application/json",
            f"",
            f'{{"egg": "{self.name}", "action": "invoke", "player_state": [...]}}',
            f"```",
            "",
            "## 21D State Vector",
            "",
            f"```",
            f"Tongue:    {list(self.state.tongue)}",
            f"Phase:     {list(self.state.phase)}",
            f"Telemetry: {list(self.state.telemetry)}",
            f"```",
            "",
            "## Training Data",
            "",
            f"- Invocations: {self.invocation_count}",
            f"- Training pairs generated: {self.training_pairs_generated}",
        ])
        return fm + "\n\n" + "\n".join(body_lines)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "skill_name": self.skill_name,
            "tongue": self.tongue_name,
            "phase": self.phase,
            "state_21d": list(self.state.data),
            "hatching": self.hatching.to_dict(),
            "hatched": self.hatched,
            "hatch_timestamp": self.hatch_timestamp,
            "connected_eggs": self.connected_eggs,
            "n8n_webhook_id": self.n8n_webhook_id,
            "obsidian_note_path": self.obsidian_note_path,
            "invocation_count": self.invocation_count,
            "training_pairs_generated": self.training_pairs_generated,
        }


def skill_node_to_egg(skill_node, connections: List[str] = None) -> SacredEggNode:
    """Convert a SkillNode from the registry into a SacredEggNode."""
    tongue = skill_node.primary_tongue
    difficulty = skill_node.difficulty

    hatching = HatchingCondition(
        min_tongue_strength=max(0.1, difficulty * 0.5),
        min_coherence=max(0.3, 1.0 - difficulty * 0.5),
        required_tongues=[tongue],
        max_risk=min(0.9, 1.0 - difficulty * 0.3),
    )

    # Higher phases need Hodge dual tongue too
    from .grid_generator import PHASE_ORDER
    phase_idx = PHASE_ORDER.index(skill_node.phase) if skill_node.phase in PHASE_ORDER else 0
    if phase_idx >= 2:
        dual_map = {0: 5, 5: 0, 1: 4, 4: 1, 2: 3, 3: 2}
        hatching.required_tongues.append(dual_map[tongue])

    return SacredEggNode(
        name=f"egg-{skill_node.name}",
        skill_name=skill_node.name,
        tongue=tongue,
        phase=skill_node.phase,
        state=skill_node.state,
        hatching=hatching,
        hatched=skill_node.unlocked,
        connected_eggs=connections or [],
    )


def export_eggs_to_obsidian(eggs: List[SacredEggNode], vault_dir: Path):
    """Export all Sacred Egg nodes as Obsidian notes."""
    egg_dir = vault_dir / "Sphere Grid"
    egg_dir.mkdir(parents=True, exist_ok=True)

    for egg in eggs:
        note_path = egg_dir / f"{egg.name}.md"
        note_path.write_text(egg.to_obsidian_note(), encoding="utf-8")
        egg.obsidian_note_path = str(note_path)

    # Write index note
    index_lines = [
        "# Sphere Grid — Sacred Egg Index",
        "",
        f"Total eggs: {len(eggs)}",
        f"Hatched: {sum(1 for e in eggs if e.hatched)}",
        f"Sealed: {sum(1 for e in eggs if not e.hatched)}",
        "",
    ]
    for phase in ["SENSE", "PLAN", "EXECUTE", "PUBLISH"]:
        phase_eggs = [e for e in eggs if e.phase == phase]
        index_lines.append(f"## {phase}")
        index_lines.append("")
        for egg in phase_eggs:
            status = "hatched" if egg.hatched else "sealed"
            index_lines.append(f"- [[{egg.name}]] ({egg.tongue_name}, {status})")
        index_lines.append("")

    (egg_dir / "Sphere Grid Index.md").write_text("\n".join(index_lines), encoding="utf-8")


def export_eggs_training_data(eggs: List[SacredEggNode], output_path: Path):
    """Export training pair metadata for all eggs as JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for egg in eggs:
            f.write(json.dumps(egg.to_dict()) + "\n")
