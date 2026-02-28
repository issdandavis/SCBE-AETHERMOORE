#!/usr/bin/env python3
"""
Multi-Model Matrix — LLM Orchestrator for SCBE Fleet Nodes.

Spins up heterogeneous LLMs on Sacred Tongue nodes, bundles them for
consensus, and connects bundles so they develop cohesion over time.

Architecture:
  - ModelProvider: supported backend (Claude, Gemini, Ollama, …)
  - ModelConfig:   single model slot (provider + params + role)
  - ModelNode:     one tongue node hosting ≥1 models with a consensus rule
  - NodeBundle:    group of nodes whose cohesion grows with interaction
  - ModelMatrix:   top-level orchestrator (nodes, bundles, query API)

@module fleet/model_matrix
@layer Layer 5, Layer 13
@component Multi-Model Matrix
@version 1.0.0
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

TONGUE_NAMES: List[str] = ["KO", "AV", "RU", "CA", "UM", "DR"]

TONGUE_ROLES: Dict[str, str] = {
    "KO": "intent",          # flow orientation — intent analysis
    "AV": "creative",        # boundary condition — creative/narrative
    "RU": "security",        # constraint field — security/audit
    "CA": "compute",         # active operator — compute/optimisation
    "UM": "governance",      # entropic sink — governance/policy
    "DR": "architecture",    # structural tensor — structure/architecture
}


# ═══════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════

class ModelProvider(str, Enum):
    """Supported LLM backend providers."""

    CLAUDE = "claude"
    GEMINI = "gemini"
    LLAMA = "llama"
    MISTRAL = "mistral"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    OLLAMA = "ollama"


ConsensusStrategy = Literal["majority", "weighted", "chain", "debate"]


@dataclass
class ModelConfig:
    """Configuration for a single model slot on a node."""

    provider: ModelProvider
    model_id: str
    api_key_env: str = ""        # env-var name (never the raw key)
    temperature: float = 0.7
    max_tokens: int = 1024
    role: str = "general"        # e.g. "reasoner", "coder", "critic", "researcher"

    @property
    def api_key(self) -> Optional[str]:
        """Resolve the key from the environment at call time."""
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)


@dataclass
class ModelNode:
    """A single tongue-aligned node hosting one or more models."""

    node_id: str
    tongue: str                          # KO / AV / RU / CA / UM / DR
    models: List[ModelConfig] = field(default_factory=list)
    consensus_strategy: ConsensusStrategy = "majority"

    def __post_init__(self) -> None:
        if self.tongue not in TONGUE_NAMES:
            raise ValueError(f"tongue must be one of {TONGUE_NAMES}, got '{self.tongue}'")


@dataclass
class NodeBundle:
    """Group of interconnected nodes that develop cohesion over time."""

    bundle_id: str
    nodes: List[ModelNode] = field(default_factory=list)
    cohesion_score: float = 0.0          # [0, 1]
    interaction_count: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Provider Adapters
# ═══════════════════════════════════════════════════════════════

async def _call_claude(config: ModelConfig, prompt: str, context: Optional[str] = None) -> str:
    """Query Anthropic Claude. Falls back to mock if SDK unavailable."""
    try:
        import anthropic  # type: ignore[import-untyped]

        key = config.api_key
        if not key:
            return _mock("Claude", config, prompt)

        client = anthropic.Anthropic(api_key=key)
        messages = []
        if context:
            messages.append({"role": "user", "content": context})
            messages.append({"role": "assistant", "content": "Understood — context received."})
        messages.append({"role": "user", "content": prompt})

        resp = client.messages.create(
            model=config.model_id,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            messages=messages,
        )
        return resp.content[0].text  # type: ignore[union-attr]
    except ImportError:
        return _mock("Claude", config, prompt)
    except Exception as exc:
        return f"[Claude error: {exc}]"


async def _call_gemini(config: ModelConfig, prompt: str, context: Optional[str] = None) -> str:
    """Query Google Gemini. Falls back to mock if SDK unavailable."""
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        key = config.api_key
        if not key:
            return _mock("Gemini", config, prompt)

        genai.configure(api_key=key)
        model = genai.GenerativeModel(config.model_id)
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        resp = model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            ),
        )
        return resp.text  # type: ignore[union-attr]
    except ImportError:
        return _mock("Gemini", config, prompt)
    except Exception as exc:
        return f"[Gemini error: {exc}]"


async def _call_ollama(config: ModelConfig, prompt: str, context: Optional[str] = None) -> str:
    """Query a local Ollama instance at localhost:11434."""
    try:
        import urllib.request

        payload = json.dumps({
            "model": config.model_id,
            "prompt": f"{context}\n\n{prompt}" if context else prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
            return body.get("response", "[empty Ollama response]")
    except Exception as exc:
        return _mock("Ollama", config, prompt, note=str(exc))


async def _call_huggingface(config: ModelConfig, prompt: str, context: Optional[str] = None) -> str:
    """Query HuggingFace Inference API. Falls back to mock if SDK unavailable."""
    try:
        from huggingface_hub import InferenceClient  # type: ignore[import-untyped]

        key = config.api_key
        if not key:
            return _mock("HuggingFace", config, prompt)

        client = InferenceClient(model=config.model_id, token=key)
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        resp = client.text_generation(
            full_prompt,
            max_new_tokens=config.max_tokens,
            temperature=config.temperature,
        )
        return resp
    except ImportError:
        return _mock("HuggingFace", config, prompt)
    except Exception as exc:
        return f"[HuggingFace error: {exc}]"


async def _call_local(config: ModelConfig, prompt: str, context: Optional[str] = None) -> str:
    """Placeholder for loading a local model (GGUF, ONNX, etc.)."""
    return _mock("Local", config, prompt, note="local model loading not yet implemented")


def _mock(provider: str, config: ModelConfig, prompt: str, *, note: str = "") -> str:
    """Deterministic mock response for offline or missing-SDK scenarios."""
    digest = hashlib.sha256(prompt.encode()).hexdigest()[:12]
    parts = [
        f"[MOCK {provider}]",
        f"model={config.model_id}",
        f"role={config.role}",
        f"prompt_hash={digest}",
    ]
    if note:
        parts.append(f"note={note}")
    return " | ".join(parts)


# Provider dispatch table
_PROVIDER_DISPATCH = {
    ModelProvider.CLAUDE: _call_claude,
    ModelProvider.GEMINI: _call_gemini,
    ModelProvider.LLAMA: _call_ollama,      # Llama via Ollama
    ModelProvider.MISTRAL: _call_ollama,    # Mistral via Ollama
    ModelProvider.HUGGINGFACE: _call_huggingface,
    ModelProvider.LOCAL: _call_local,
    ModelProvider.OLLAMA: _call_ollama,
}


# ═══════════════════════════════════════════════════════════════
# Consensus Strategies
# ═══════════════════════════════════════════════════════════════

def _consensus_majority(responses: List[str]) -> str:
    """Pick the most common response. Ties go to the first seen."""
    if not responses:
        return ""
    counts: Dict[str, int] = {}
    for r in responses:
        counts[r] = counts.get(r, 0) + 1
    return max(counts, key=lambda k: counts[k])


def _consensus_weighted(responses: List[str]) -> str:
    """Concatenate all responses, separated by weight markers.

    In a full implementation this would score each by model capability,
    but for now it preserves all voices with ordinal markers.
    """
    if not responses:
        return ""
    parts = [f"[weight {i + 1}/{len(responses)}] {r}" for i, r in enumerate(responses)]
    return "\n".join(parts)


def _consensus_chain(responses: List[str]) -> str:
    """Return the last response (models refined sequentially)."""
    return responses[-1] if responses else ""


def _consensus_debate(responses: List[str]) -> str:
    """Concatenate as a debate transcript with alternating speakers."""
    if not responses:
        return ""
    lines = [f"[Speaker {i + 1}] {r}" for i, r in enumerate(responses)]
    return "\n---\n".join(lines)


_CONSENSUS = {
    "majority": _consensus_majority,
    "weighted": _consensus_weighted,
    "chain": _consensus_chain,
    "debate": _consensus_debate,
}


# ═══════════════════════════════════════════════════════════════
# ModelMatrix
# ═══════════════════════════════════════════════════════════════

class ModelMatrix:
    """Top-level orchestrator for multi-model, multi-node bundles.

    Usage::

        matrix = ModelMatrix.create_default_scbe_matrix()
        result = await matrix.query_node("KO-node", "Classify this user intent.")
        bundle_result = await matrix.query_bundle("scbe-core", "Full analysis.")
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, ModelNode] = {}
        self.bundles: Dict[str, NodeBundle] = {}
        self.interaction_log: List[Dict[str, Any]] = []

    # ── Node Management ──────────────────────────────────────

    def add_node(self, node: ModelNode) -> str:
        """Register a node and return its id."""
        self.nodes[node.node_id] = node
        return node.node_id

    def remove_node(self, node_id: str) -> bool:
        """Remove a node (also removes it from any bundle)."""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        for bundle in self.bundles.values():
            bundle.nodes = [n for n in bundle.nodes if n.node_id != node_id]
        return True

    # ── Bundle Management ────────────────────────────────────

    def create_bundle(self, node_ids: List[str], bundle_id: Optional[str] = None) -> str:
        """Create a bundle from existing nodes. Returns the bundle id."""
        bid = bundle_id or f"bundle-{uuid.uuid4().hex[:8]}"
        nodes = [self.nodes[nid] for nid in node_ids if nid in self.nodes]
        if not nodes:
            raise ValueError("No valid node ids provided")
        self.bundles[bid] = NodeBundle(bundle_id=bid, nodes=nodes)
        return bid

    # ── Queries ──────────────────────────────────────────────

    async def query_node(
        self,
        node_id: str,
        prompt: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query every model on a node and apply the node's consensus strategy.

        Returns a dict with keys: node_id, tongue, strategy, individual, consensus.
        """
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Unknown node: {node_id}")

        # Fan-out to all models on the node concurrently
        tasks = []
        for cfg in node.models:
            handler = _PROVIDER_DISPATCH.get(cfg.provider, _call_local)
            tasks.append(handler(cfg, prompt, context))

        individual: List[str] = await asyncio.gather(*tasks)

        # Apply consensus
        consensus_fn = _CONSENSUS.get(node.consensus_strategy, _consensus_majority)
        consensus = consensus_fn(individual)

        result: Dict[str, Any] = {
            "node_id": node_id,
            "tongue": node.tongue,
            "strategy": node.consensus_strategy,
            "individual": individual,
            "consensus": consensus,
            "timestamp": time.time(),
        }

        self._log_interaction("query_node", result)
        return result

    async def query_bundle(
        self,
        bundle_id: str,
        prompt: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query every node in a bundle, merge results, and update cohesion.

        Returns a dict with keys: bundle_id, node_results, merged, cohesion.
        """
        bundle = self.bundles.get(bundle_id)
        if bundle is None:
            raise KeyError(f"Unknown bundle: {bundle_id}")

        # Query all nodes concurrently
        node_tasks = [
            self.query_node(n.node_id, prompt, context)
            for n in bundle.nodes
        ]
        node_results: List[Dict[str, Any]] = await asyncio.gather(*node_tasks)

        # Merge: collect all consensus outputs
        consensuses = [r["consensus"] for r in node_results]
        merged = "\n\n".join(
            f"[{r['tongue']}] {r['consensus']}" for r in node_results
        )

        # Update cohesion based on agreement
        self._update_cohesion(bundle_id, consensuses)

        result: Dict[str, Any] = {
            "bundle_id": bundle_id,
            "node_results": node_results,
            "merged": merged,
            "cohesion": bundle.cohesion_score,
            "interaction_count": bundle.interaction_count,
            "timestamp": time.time(),
        }

        # Persist in bundle history (keep last 100)
        bundle.history.append({
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "cohesion": bundle.cohesion_score,
            "timestamp": result["timestamp"],
        })
        if len(bundle.history) > 100:
            bundle.history = bundle.history[-100:]

        self._log_interaction("query_bundle", result)
        return result

    # ── Cohesion ─────────────────────────────────────────────

    def _update_cohesion(self, bundle_id: str, responses: List[str]) -> None:
        """Increment cohesion based on how much the node outputs agree.

        Agreement ratio = (number of unique responses)^-1.
        Cohesion moves toward the running average with a decay factor.
        """
        bundle = self.bundles[bundle_id]
        bundle.interaction_count += 1

        if not responses:
            return

        n_unique = len(set(responses))
        agreement = 1.0 / n_unique  # 1.0 = perfect agreement

        # Exponential moving average — older interactions decay
        alpha = min(0.3, 2.0 / (bundle.interaction_count + 1))
        bundle.cohesion_score = (1 - alpha) * bundle.cohesion_score + alpha * agreement
        bundle.cohesion_score = max(0.0, min(1.0, bundle.cohesion_score))

    # ── Status ───────────────────────────────────────────────

    def get_matrix_status(self) -> Dict[str, Any]:
        """Full status snapshot of all nodes, bundles, and cohesion."""
        return {
            "nodes": {
                nid: {
                    "tongue": n.tongue,
                    "model_count": len(n.models),
                    "models": [
                        {"provider": m.provider.value, "model_id": m.model_id, "role": m.role}
                        for m in n.models
                    ],
                    "consensus": n.consensus_strategy,
                }
                for nid, n in self.nodes.items()
            },
            "bundles": {
                bid: {
                    "node_ids": [n.node_id for n in b.nodes],
                    "cohesion": round(b.cohesion_score, 4),
                    "interactions": b.interaction_count,
                    "history_len": len(b.history),
                }
                for bid, b in self.bundles.items()
            },
            "total_nodes": len(self.nodes),
            "total_bundles": len(self.bundles),
            "total_interactions": len(self.interaction_log),
        }

    # ── Internal ─────────────────────────────────────────────

    def _log_interaction(self, kind: str, data: Dict[str, Any]) -> None:
        self.interaction_log.append({"kind": kind, "ts": time.time(), **data})
        # Keep the log bounded
        if len(self.interaction_log) > 500:
            self.interaction_log = self.interaction_log[-500:]

    # ── Conversation Spin (Magnetic Field Dynamics) ────────
    #
    # Topics are charged particles in a 2D field.
    # Each Sacred Tongue node generates a magnetic field (B-vector)
    # that curves the conversation trajectory via Lorentz force:
    #
    #   F = q * (v x B)
    #
    # The path looks chaotic but follows deterministic physics —
    # natural fluctuations from the laws of nature applied to
    # machine systems.

    # Topic positions in a 2D semantic space
    _TOPIC_POSITIONS: Dict[str, tuple] = {
        "ai_safety": (0.0, 0.0),
        "governance": (1.0, 0.5),
        "alignment": (-0.5, 1.0),
        "cryptography": (1.5, -0.5),
        "ethics": (-1.0, 0.5),
        "game_design": (2.0, 2.0),
        "narrative": (1.5, 2.5),
        "mechanics": (2.5, 1.5),
        "training": (0.0, -1.5),
        "datasets": (-0.5, -2.0),
        "fine_tuning": (0.5, -2.0),
        "evaluation": (1.0, -1.5),
        "deployment": (2.0, -1.0),
        "cloud": (2.5, -0.5),
        "security": (1.0, 0.0),
        "policy": (0.5, 1.0),
        "audit": (1.5, 0.5),
        "quantum": (2.0, -1.5),
        "pqc": (2.5, -1.0),
        "economics": (3.0, 1.0),
        "monetization": (3.0, 1.5),
        "marketplace": (3.5, 1.0),
    }

    # Sacred Tongue magnetic field vectors (direction + strength)
    # Each tongue warps conversation trajectory toward its domain
    _TONGUE_B_FIELD: Dict[str, tuple] = {
        "KO": (0.0, 0.3),     # pulls toward intent/alignment (upward)
        "AV": (0.2, 0.2),     # pulls toward creativity (diagonal)
        "RU": (0.3, -0.1),    # pulls toward security (rightward)
        "CA": (0.1, -0.3),    # pulls toward compute/deployment (downward)
        "UM": (-0.2, 0.2),    # pulls toward governance (upper-left)
        "DR": (0.0, 0.0),     # neutral — structural observer
    }

    def conversation_spin(
        self,
        bundle_id: str,
        seed_topic: str,
        spins: int = 6,
        charge: float = 1.0,
        dt: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Generate a magnetically-curved topic trajectory across nodes.

        Uses Lorentz force F = q(v x B) where:
        - q = conversation charge (enthusiasm/urgency)
        - v = current velocity (topic drift direction)
        - B = Sacred Tongue magnetic field at current node

        The path appears chaotic but follows deterministic physics.
        Natural fluctuations from laws of nature applied to machine systems.
        """
        import math

        bundle = self.bundles.get(bundle_id)
        if not bundle:
            return [{"error": f"Bundle {bundle_id} not found"}]

        # Initial conditions
        current_topic = seed_topic.lower().replace(" ", "_")
        pos = list(self._TOPIC_POSITIONS.get(current_topic, (0.0, 0.0)))
        vel = [0.1, 0.05]  # initial drift velocity

        chain: List[Dict[str, Any]] = []

        for spin_idx in range(spins):
            node = bundle.nodes[spin_idx % len(bundle.nodes)]
            tongue = node.tongue

            # Get B-field for this tongue
            bx, by = self._TONGUE_B_FIELD.get(tongue, (0.0, 0.0))

            # Lorentz force: F = q * (v x B)
            # In 2D with B perpendicular to plane: F = q * |v| * |B| (rotational)
            # Fx = q * vy * Bz  (we use Bx as the perpendicular component)
            # Fy = -q * vx * Bz
            # Simplified: apply B as a torque on the velocity vector
            fx = charge * (vel[1] * by - vel[0] * bx * 0.5)
            fy = charge * (-vel[0] * bx + vel[1] * by * 0.5)

            # Update velocity (with damping to prevent runaway)
            vel[0] = vel[0] + fx * dt
            vel[1] = vel[1] + fy * dt
            speed = math.sqrt(vel[0] ** 2 + vel[1] ** 2)
            if speed > 1.0:  # terminal velocity
                vel[0] /= speed
                vel[1] /= speed

            # Update position
            pos[0] += vel[0] * dt
            pos[1] += vel[1] * dt

            # Find nearest topic to new position
            nearest_topic = current_topic
            nearest_dist = float("inf")
            for topic, (tx, ty) in self._TOPIC_POSITIONS.items():
                if topic == current_topic:
                    continue
                d = math.sqrt((pos[0] - tx) ** 2 + (pos[1] - ty) ** 2)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_topic = topic

            chain.append({
                "spin": spin_idx + 1,
                "tongue": tongue,
                "node_id": node.node_id,
                "from_topic": current_topic,
                "to_topic": nearest_topic,
                "position": [round(pos[0], 3), round(pos[1], 3)],
                "velocity": [round(vel[0], 3), round(vel[1], 3)],
                "force": [round(fx, 4), round(fy, 4)],
                "b_field": [bx, by],
                "distance_to_topic": round(nearest_dist, 3),
                "prompt": f"[{tongue}] As {TONGUE_ROLES[tongue]} specialist, "
                          f"the conversation drifts from '{current_topic}' toward "
                          f"'{nearest_topic}' (magnetic pull: B=[{bx},{by}]). "
                          f"Bridge these topics.",
            })
            current_topic = nearest_topic

        return chain

    # ── Factory ──────────────────────────────────────────────

    @classmethod
    def create_default_scbe_matrix(cls) -> "ModelMatrix":
        """Create a 6-node matrix mapped to the Sacred Tongues.

        Each tongue gets a purpose-aligned set of models:
          KO — intent analysis
          AV — creative / narrative
          RU — security / audit
          CA — compute / optimisation
          UM — governance / policy
          DR — structure / architecture
        """
        matrix = cls()

        # ── KO: Intent Analysis ──
        ko = ModelNode(
            node_id="KO-node",
            tongue="KO",
            consensus_strategy="chain",
            models=[
                ModelConfig(
                    provider=ModelProvider.CLAUDE,
                    model_id="claude-sonnet-4-20250514",
                    api_key_env="ANTHROPIC_API_KEY",
                    role="reasoner",
                    temperature=0.3,
                ),
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_id="llama3",
                    role="classifier",
                    temperature=0.1,
                ),
            ],
        )

        # ── AV: Creative / Narrative ──
        av = ModelNode(
            node_id="AV-node",
            tongue="AV",
            consensus_strategy="debate",
            models=[
                ModelConfig(
                    provider=ModelProvider.CLAUDE,
                    model_id="claude-sonnet-4-20250514",
                    api_key_env="ANTHROPIC_API_KEY",
                    role="narrator",
                    temperature=0.9,
                ),
                ModelConfig(
                    provider=ModelProvider.GEMINI,
                    model_id="gemini-2.0-flash",
                    api_key_env="GOOGLE_AI_API_KEY",
                    role="creative",
                    temperature=0.85,
                ),
            ],
        )

        # ── RU: Security / Audit ──
        ru = ModelNode(
            node_id="RU-node",
            tongue="RU",
            consensus_strategy="majority",
            models=[
                ModelConfig(
                    provider=ModelProvider.CLAUDE,
                    model_id="claude-sonnet-4-20250514",
                    api_key_env="ANTHROPIC_API_KEY",
                    role="auditor",
                    temperature=0.1,
                ),
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_id="mistral",
                    role="security-scanner",
                    temperature=0.0,
                ),
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_id="llama3",
                    role="red-team",
                    temperature=0.2,
                ),
            ],
        )

        # ── CA: Compute / Optimisation ──
        ca = ModelNode(
            node_id="CA-node",
            tongue="CA",
            consensus_strategy="weighted",
            models=[
                ModelConfig(
                    provider=ModelProvider.GEMINI,
                    model_id="gemini-2.0-flash",
                    api_key_env="GOOGLE_AI_API_KEY",
                    role="optimizer",
                    temperature=0.3,
                ),
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_id="deepseek-coder",
                    role="coder",
                    temperature=0.2,
                ),
            ],
        )

        # ── UM: Governance / Policy ──
        um = ModelNode(
            node_id="UM-node",
            tongue="UM",
            consensus_strategy="majority",
            models=[
                ModelConfig(
                    provider=ModelProvider.CLAUDE,
                    model_id="claude-sonnet-4-20250514",
                    api_key_env="ANTHROPIC_API_KEY",
                    role="policy-enforcer",
                    temperature=0.1,
                ),
                ModelConfig(
                    provider=ModelProvider.HUGGINGFACE,
                    model_id="issdandavis/phdm-21d-embedding",
                    api_key_env="HF_TOKEN",
                    role="governance-embedder",
                    temperature=0.0,
                ),
            ],
        )

        # ── DR: Structure / Architecture ──
        dr = ModelNode(
            node_id="DR-node",
            tongue="DR",
            consensus_strategy="chain",
            models=[
                ModelConfig(
                    provider=ModelProvider.CLAUDE,
                    model_id="claude-sonnet-4-20250514",
                    api_key_env="ANTHROPIC_API_KEY",
                    role="architect",
                    temperature=0.4,
                ),
                ModelConfig(
                    provider=ModelProvider.GEMINI,
                    model_id="gemini-2.0-flash",
                    api_key_env="GOOGLE_AI_API_KEY",
                    role="planner",
                    temperature=0.3,
                ),
            ],
        )

        for node in [ko, av, ru, ca, um, dr]:
            matrix.add_node(node)

        # Create the default SCBE core bundle with all 6 tongues
        matrix.create_bundle(
            node_ids=[n.node_id for n in [ko, av, ru, ca, um, dr]],
            bundle_id="scbe-core",
        )

        return matrix
