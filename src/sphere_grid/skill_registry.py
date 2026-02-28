"""
Skill Registry — discovers all skills across skill directories and indexes them as sphere grid nodes.

Each skill becomes a node on the grid, positioned by:
  - Phase (SENSE/PLAN/EXECUTE/PUBLISH) determined by skill domain
  - Primary Sacred Tongue determined by skill function
  - Difficulty derived from skill complexity/dependency count
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .canonical_state import (
    AV,
    CA,
    DR,
    KO,
    RU,
    UM,
    CanonicalState,
    make_skill_node_state,
)

# Skill directories to scan
SKILL_DIRS = [
    Path.home() / ".claude" / "skills",
    Path.home() / ".codex" / "skills",
    Path.home() / "SCBE-AETHERMOORE" / ".claude" / "skills",
]

# Domain-to-phase mapping: keywords in skill name/description -> operational phase
PHASE_KEYWORDS = {
    "SENSE": [
        "browse", "fetch", "probe", "research", "search", "explore", "read",
        "scan", "discover", "survey", "screenshot", "terminal", "web-research",
        "notion-fetch", "obsidian-vault", "graphics-debug", "openclaw",
        "clawbot", "moltbot",
    ],
    "PLAN": [
        "governance", "gate", "plan", "validate", "manifold", "entropy",
        "state-engine", "shepherd", "flock", "swarm", "orchestrat", "review",
        "brainstorm", "debug", "audit-intent", "context-catalog", "synthesis",
        "router", "route", "federation", "operations-tree",
    ],
    "EXECUTE": [
        "training", "pipeline", "deploy", "fleet", "execute", "build",
        "create", "generate", "sync", "ingest", "compile", "transform",
        "docker", "shopify", "telegram", "connector", "workflow", "n8n",
        "monster-creator", "map-editor", "mod-system", "zapier",
        "google-business", "merchant-center", "product-feed",
    ],
    "PUBLISH": [
        "publish", "content", "obsidian", "doc-maker", "story", "canon",
        "report", "hf-publish", "gumroad", "vercel", "deploy", "ship",
        "npm", "audit-write", "shop", "storefront", "listing", "offer",
        "launch", "monetize", "sales",
    ],
}

# Domain-to-tongue mapping: skill function -> primary Sacred Tongue
TONGUE_KEYWORDS = {
    KO: ["intent", "browse", "navigate", "search", "explore", "sense", "research"],
    AV: ["metadata", "fetch", "transport", "schema", "registry", "catalog", "notion"],
    RU: ["rule", "validate", "gate", "governance", "manifold", "binding", "review"],
    CA: ["compute", "transform", "training", "pipeline", "build", "code", "generate"],
    UM: ["security", "crypto", "secret", "seal", "entropy", "shield", "antivirus"],
    DR: ["structure", "publish", "audit", "deploy", "attest", "doc", "canon", "story"],
}


@dataclass
class SkillNode:
    """A skill indexed as a sphere grid node."""
    name: str
    description: str
    path: Path
    phase: str  # SENSE, PLAN, EXECUTE, PUBLISH
    primary_tongue: int  # KO=0..DR=5
    difficulty: float  # 0.0-1.0
    state: Optional[CanonicalState] = None
    dependencies: List[str] = field(default_factory=list)
    unlocked: bool = True
    telemetry_count: int = 0  # how many times this skill has been invoked

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
            "phase": self.phase,
            "primary_tongue": self.primary_tongue,
            "difficulty": self.difficulty,
            "state": self.state.to_dict() if self.state else None,
            "dependencies": self.dependencies,
            "unlocked": self.unlocked,
            "telemetry_count": self.telemetry_count,
        }


def _classify_phase(name: str, description: str) -> str:
    """Classify a skill into an operational phase."""
    text = f"{name} {description}".lower()
    scores = {phase: 0 for phase in PHASE_KEYWORDS}
    for phase, keywords in PHASE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[phase] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "EXECUTE"


def _classify_tongue(name: str, description: str) -> int:
    """Classify a skill's primary Sacred Tongue."""
    text = f"{name} {description}".lower()
    scores = {tongue: 0 for tongue in TONGUE_KEYWORDS}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[tongue] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else CA  # default to compute


def _parse_skill_md(skill_dir: Path) -> Optional[Dict[str, str]]:
    """Parse SKILL.md frontmatter for name and description."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Parse YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None

    frontmatter = match.group(1)
    result = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in ("name", "description"):
                result[key] = val
    return result if "name" in result else None


def discover_skills(extra_dirs: List[Path] = None) -> List[SkillNode]:
    """Discover all skills across all skill directories."""
    dirs = list(SKILL_DIRS)
    if extra_dirs:
        dirs.extend(extra_dirs)

    nodes: List[SkillNode] = []
    seen_names: set = set()

    for skill_root in dirs:
        if not skill_root.exists():
            continue
        for child in sorted(skill_root.iterdir()):
            if not child.is_dir():
                continue
            meta = _parse_skill_md(child)
            if not meta:
                continue
            name = meta["name"]
            if name in seen_names:
                continue
            seen_names.add(name)

            desc = meta.get("description", "")
            phase = _classify_phase(name, desc)
            tongue = _classify_tongue(name, desc)
            # Difficulty heuristic: longer description = more complex
            difficulty = min(1.0, len(desc) / 500.0)

            state = make_skill_node_state(name, phase, tongue, difficulty)
            nodes.append(SkillNode(
                name=name,
                description=desc[:200],
                path=child,
                phase=phase,
                primary_tongue=tongue,
                difficulty=difficulty,
                state=state,
            ))

    return nodes


def build_registry(extra_dirs: List[Path] = None) -> Dict[str, SkillNode]:
    """Build a name-indexed registry of all skills."""
    nodes = discover_skills(extra_dirs)
    return {n.name: n for n in nodes}


def save_registry(registry: Dict[str, SkillNode], path: Path):
    """Save registry to JSON."""
    data = {name: node.to_dict() for name, node in registry.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_registry(path: Path) -> Dict[str, dict]:
    """Load registry from JSON (raw dicts, not SkillNode objects)."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
