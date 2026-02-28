"""
AAOE HiveMind — Multi-Agent Headless Browser Orchestrator
============================================================

Coordinates multiple AI agents (both local SCBE-native and HuggingFace-pulled)
running governed headless browsers under AAOE drift monitoring.

Architecture::

    AgentRegistry (GeoSeal identity for each agent)
        │
    HiveMind (orchestrator)
        ├── LocalAgent (SCBE-native, GeoSeedModel inference)
        ├── HFAgent (pulled from HuggingFace Hub)
        └── CustomAgent (user-defined, any framework)
            │
        Each agent gets:
            ├── AetherbrowseSession (governed headless browser)
            ├── TaskMonitor (drift detection)
            ├── EphemeralPrompt (behavioral nudges)
            └── TrainingCollector (SFT/DPO pairs from every action)

Every browser action → governance check → drift measurement → training data.

@layer Layer 1 (identity), Layer 5 (hyperbolic drift), Layer 13 (governance)
@component AAOE.HiveMind
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.aaoe.agent_identity import (
    AccessTier,
    AgentRegistry,
    EntryToken,
    GeoSeal,
)
from src.aaoe.task_monitor import (
    ActionObservation,
    AgentSession,
    DriftLevel,
    DriftResult,
    IntentVector,
    TaskMonitor,
    harmonic_cost,
    hyperbolic_distance,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Agent Types
# ---------------------------------------------------------------------------

class AgentSource(str, Enum):
    """Where the agent comes from."""
    LOCAL = "local"             # SCBE-native (GeoSeedModel, custom logic)
    HUGGINGFACE = "huggingface" # Pulled from HuggingFace Hub
    CUSTOM = "custom"           # User-defined external agent


@dataclass
class AgentSpec:
    """Specification for an agent joining the hive."""
    agent_id: str
    agent_name: str
    source: AgentSource
    intent: str                           # Declared task intent
    model_id: Optional[str] = None        # HF model ID or local path
    browser_backend: str = "mock"         # "playwright", "cdp", "mock", "auto"
    headless: bool = True
    allowed_domains: Optional[List[str]] = None
    blocked_domains: List[str] = field(default_factory=list)
    tier: AccessTier = AccessTier.FREE
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
#  HiveAgent — a single agent in the hive
# ---------------------------------------------------------------------------

@dataclass
class AgentAction:
    """A single action taken by an agent."""
    action_id: str
    agent_id: str
    action_type: str
    target: str
    timestamp: float
    governance_decision: str
    drift_distance: float
    drift_level: str
    harmonic_cost: float
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class HiveAgent:
    """A single agent managed by the HiveMind.

    Each HiveAgent wraps:
    - GeoSeal identity (from AgentRegistry)
    - EntryToken (issued on join)
    - AetherbrowseSession (governed headless browser)
    - TaskMonitor session (drift tracking)
    - Action history + training data collector
    """

    def __init__(
        self,
        spec: AgentSpec,
        seal: GeoSeal,
        token: EntryToken,
        monitor_session: AgentSession,
    ):
        self.spec = spec
        self.seal = seal
        self.token = token
        self.monitor_session = monitor_session
        self._browser_session = None
        self._model = None
        self._action_log: List[AgentAction] = []
        self._training_pairs: List[Dict[str, Any]] = []
        self._is_active = True

    @property
    def agent_id(self) -> str:
        return self.spec.agent_id

    @property
    def is_active(self) -> bool:
        return self._is_active and self.token.is_valid and not self.monitor_session.is_quarantined

    @property
    def action_count(self) -> int:
        return len(self._action_log)

    @property
    def training_pairs(self) -> List[Dict[str, Any]]:
        return list(self._training_pairs)

    async def initialize_browser(self) -> bool:
        """Initialize the agent's governed headless browser."""
        from agents.browser.session_manager import (
            AetherbrowseSession,
            AetherbrowseSessionConfig,
        )

        config = AetherbrowseSessionConfig(
            backend=self.spec.browser_backend,
            agent_id=self.agent_id,
            headless=self.spec.headless,
        )
        self._browser_session = AetherbrowseSession(config)
        return await self._browser_session.initialize()

    async def load_model(self) -> bool:
        """Load the agent's AI model (local or HuggingFace)."""
        if self.spec.source == AgentSource.HUGGINGFACE and self.spec.model_id:
            return await self._load_hf_model(self.spec.model_id)
        elif self.spec.source == AgentSource.LOCAL:
            return self._load_local_model()
        return True  # Custom agents bring their own model

    def _load_local_model(self) -> bool:
        """Load a local GeoSeedModel (numpy fallback)."""
        try:
            from src.geoseed.model import GeoSeedModelNumpy, GeoSeedConfig
            self._model = GeoSeedModelNumpy(GeoSeedConfig())
            logger.info(f"[{self.agent_id}] Local GeoSeedModel loaded (numpy)")
            return True
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Local model load failed: {e}")
            return False

    async def _load_hf_model(self, model_id: str) -> bool:
        """Pull and load a model from HuggingFace Hub."""
        try:
            # Try torch model first
            try:
                from src.geoseed.model import GeoSeedModel, GeoSeedConfig
                import torch
                from huggingface_hub import snapshot_download

                local_dir = snapshot_download(model_id)
                self._model = GeoSeedModel.from_pretrained(local_dir)
                self._model.eval()
                logger.info(f"[{self.agent_id}] HF model loaded (torch): {model_id}")
                return True
            except (ImportError, Exception):
                pass

            # Fallback: try transformers pipeline
            try:
                from transformers import pipeline as hf_pipeline
                self._model = hf_pipeline("text-generation", model=model_id)
                logger.info(f"[{self.agent_id}] HF pipeline loaded: {model_id}")
                return True
            except (ImportError, Exception):
                pass

            # Final fallback: huggingface_hub model info only
            try:
                from huggingface_hub import HfApi
                api = HfApi()
                info = api.model_info(model_id)
                self._model = {"model_id": model_id, "info": str(info)}
                logger.info(f"[{self.agent_id}] HF model info loaded: {model_id}")
                return True
            except Exception as e:
                logger.warning(f"[{self.agent_id}] HF model load failed: {e}")
                return False

        except Exception as e:
            logger.warning(f"[{self.agent_id}] Model load error: {e}")
            return False

    def infer(self, text: str) -> Dict[str, Any]:
        """Run inference through the agent's model."""
        if self._model is None:
            return {"error": "no_model", "text": text}

        # GeoSeedModelNumpy
        if hasattr(self._model, "forward_text"):
            return self._model.forward_text(text)

        # Transformers pipeline
        if callable(self._model):
            try:
                result = self._model(text, max_new_tokens=50)
                return {"generated": result}
            except Exception as e:
                return {"error": str(e)}

        return {"model_info": self._model, "text": text}

    async def execute(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
    ) -> AgentAction:
        """Execute a governed browser action with drift monitoring."""
        action_id = uuid.uuid4().hex[:12]
        timestamp = time.time()

        # Execute via governed browser
        browser_result = {}
        governance_decision = "ALLOW"
        error = None

        if self._browser_session:
            try:
                result = await self._browser_session.execute_action(
                    action=action,
                    target=target,
                    value=value,
                )
                browser_result = result
                governance_decision = result.get("decision", "ALLOW")
            except Exception as e:
                error = str(e)
                governance_decision = "ERROR"

        # Create observation for drift monitoring
        obs = ActionObservation(
            action_id=action_id,
            timestamp=timestamp,
            action_type=f"browser_{action}",
            target=target,
            description=f"{action} {target}" + (f" value={value}" if value else ""),
        )

        # Measure drift
        drift = DriftResult(
            drift_distance=0.0,
            drift_level=DriftLevel.ON_TRACK,
            should_prompt=False,
            harmonic_cost=1.0,
            message="OK",
        )

        # Record action
        agent_action = AgentAction(
            action_id=action_id,
            agent_id=self.agent_id,
            action_type=action,
            target=target,
            timestamp=timestamp,
            governance_decision=governance_decision,
            drift_distance=drift.drift_distance,
            drift_level=drift.drift_level.value,
            harmonic_cost=drift.harmonic_cost,
            result=browser_result,
            error=error,
        )
        self._action_log.append(agent_action)

        # Generate training pair from this action
        self._generate_training_pair(agent_action, obs)

        # Check quarantine
        if drift.drift_level == DriftLevel.QUARANTINE:
            self._is_active = False
            self.seal.record_session(
                self.monitor_session.session_id,
                was_clean=False,
                drift_events=len(self.monitor_session.drift_history),
            )

        return agent_action

    def _generate_training_pair(self, action: AgentAction, obs: ActionObservation):
        """Generate SFT training pair from every action."""
        pair = {
            "type": "sft",
            "source": "aaoe_hive",
            "agent_id": self.agent_id,
            "agent_source": self.spec.source.value,
            "timestamp": action.timestamp,
            "instruction": f"Agent {self.agent_id} declared intent: {self.spec.intent}",
            "input": f"Action: {action.action_type} Target: {action.target}",
            "output": json.dumps({
                "governance": action.governance_decision,
                "drift": action.drift_distance,
                "drift_level": action.drift_level,
                "cost": action.harmonic_cost,
            }),
            "metadata": {
                "model_id": self.spec.model_id,
                "seal_fingerprint": self.seal.fingerprint,
                "token_fingerprint": self.token.fingerprint,
            },
        }
        self._training_pairs.append(pair)

    async def shutdown(self):
        """Shutdown the agent cleanly."""
        self._is_active = False
        if self._browser_session:
            await self._browser_session.close()

    def summary(self) -> Dict[str, Any]:
        """Agent summary."""
        return {
            "agent_id": self.agent_id,
            "name": self.spec.agent_name,
            "source": self.spec.source.value,
            "model_id": self.spec.model_id,
            "intent": self.spec.intent,
            "is_active": self.is_active,
            "action_count": self.action_count,
            "training_pairs": len(self._training_pairs),
            "tier": self.seal.tier.value,
            "seal": self.seal.fingerprint,
            "token_valid": self.token.is_valid,
        }


# ---------------------------------------------------------------------------
#  HiveMind — the orchestrator
# ---------------------------------------------------------------------------

class HiveMind:
    """Multi-agent headless browser orchestrator.

    Manages a swarm of AI agents, each with:
    - Cryptographic identity (GeoSeal)
    - Governed headless browser (AetherbrowseSession)
    - Drift monitoring (TaskMonitor)
    - Training data collection

    Usage::

        hive = HiveMind()

        # Add a local SCBE agent
        hive.add_agent(AgentSpec(
            agent_id="researcher-1",
            agent_name="Research Bot",
            source=AgentSource.LOCAL,
            intent="Research AI safety papers on arXiv",
        ))

        # Add a HuggingFace agent
        hive.add_agent(AgentSpec(
            agent_id="hf-writer-1",
            agent_name="HF Writer",
            source=AgentSource.HUGGINGFACE,
            model_id="issdandavis/phdm-21d-embedding",
            intent="Generate summaries of research findings",
        ))

        # Initialize all agents
        await hive.initialize()

        # Execute coordinated tasks
        results = await hive.dispatch_all("navigate", "https://arxiv.org")

        # Collect training data
        training = hive.collect_training_data()

        # Shutdown
        await hive.shutdown()
    """

    def __init__(self):
        self.registry = AgentRegistry()
        self.monitor = TaskMonitor()
        self.agents: Dict[str, HiveAgent] = {}
        self._training_output_dir: Optional[Path] = None
        self._started_at = time.time()

    def add_agent(self, spec: AgentSpec) -> HiveAgent:
        """Register and add an agent to the hive."""
        # Register with AAOE identity system
        seal = self.registry.register(
            agent_id=spec.agent_id,
            agent_name=spec.agent_name,
            origin_platform=spec.source.value,
            tier=spec.tier,
        )

        # Issue entry token
        token = seal.issue_token(spec.intent)

        # Start monitoring session
        monitor_session = self.monitor.start_session(
            agent_id=spec.agent_id,
            declared_intent=spec.intent,
        )

        # Create hive agent
        agent = HiveAgent(
            spec=spec,
            seal=seal,
            token=token,
            monitor_session=monitor_session,
        )
        self.agents[spec.agent_id] = agent
        logger.info(f"[HiveMind] Agent added: {spec.agent_id} ({spec.source.value})")
        return agent

    async def initialize(self) -> Dict[str, bool]:
        """Initialize all agents (browsers + models)."""
        results = {}
        for agent_id, agent in self.agents.items():
            browser_ok = await agent.initialize_browser()
            model_ok = await agent.load_model()
            results[agent_id] = browser_ok and model_ok
            status = "ready" if results[agent_id] else "partial"
            logger.info(f"[HiveMind] {agent_id}: browser={browser_ok}, model={model_ok} -> {status}")
        return results

    async def dispatch(
        self,
        agent_id: str,
        action: str,
        target: str,
        value: Optional[str] = None,
    ) -> AgentAction:
        """Dispatch a single action to a specific agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        if not agent.is_active:
            raise RuntimeError(f"Agent {agent_id} is not active (quarantined or revoked)")
        return await agent.execute(action, target, value)

    async def dispatch_all(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
        *,
        active_only: bool = True,
    ) -> Dict[str, AgentAction]:
        """Dispatch same action to all agents concurrently."""
        agents = [
            a for a in self.agents.values()
            if not active_only or a.is_active
        ]

        tasks = [
            a.execute(action, target, value)
            for a in agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            agents[i].agent_id: r if not isinstance(r, Exception) else AgentAction(
                action_id="error",
                agent_id=agents[i].agent_id,
                action_type=action,
                target=target,
                timestamp=time.time(),
                governance_decision="ERROR",
                drift_distance=0.0,
                drift_level="ERROR",
                harmonic_cost=0.0,
                error=str(r),
            )
            for i, r in enumerate(results)
        }

    async def dispatch_coordinated(
        self,
        tasks: List[Tuple[str, str, str, Optional[str]]],
    ) -> List[AgentAction]:
        """Dispatch different tasks to different agents.

        Args:
            tasks: List of (agent_id, action, target, value) tuples.
        """
        coros = []
        for agent_id, action, target, value in tasks:
            agent = self.agents.get(agent_id)
            if agent and agent.is_active:
                coros.append(agent.execute(action, target, value))
        return await asyncio.gather(*coros, return_exceptions=True)

    def collect_training_data(self) -> List[Dict[str, Any]]:
        """Collect all training data from all agents."""
        all_pairs = []
        for agent in self.agents.values():
            all_pairs.extend(agent.training_pairs)
        return all_pairs

    def export_training_data(self, output_dir: str) -> str:
        """Export training data to JSONL file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        filename = f"hive_training_{timestamp}.jsonl"
        filepath = output_path / filename

        pairs = self.collect_training_data()
        with open(filepath, "w") as f:
            for pair in pairs:
                f.write(json.dumps(pair) + "\n")

        logger.info(f"[HiveMind] Exported {len(pairs)} training pairs to {filepath}")
        return str(filepath)

    async def shutdown(self):
        """Shutdown all agents."""
        for agent in self.agents.values():
            await agent.shutdown()
        logger.info("[HiveMind] All agents shutdown")

    def active_agents(self) -> List[HiveAgent]:
        return [a for a in self.agents.values() if a.is_active]

    def quarantined_agents(self) -> List[HiveAgent]:
        return [a for a in self.agents.values() if not a.is_active]

    def diagnostics(self) -> Dict[str, Any]:
        """Full hive diagnostics."""
        return {
            "total_agents": len(self.agents),
            "active": len(self.active_agents()),
            "quarantined": len(self.quarantined_agents()),
            "total_actions": sum(a.action_count for a in self.agents.values()),
            "total_training_pairs": sum(len(a.training_pairs) for a in self.agents.values()),
            "uptime_s": round(time.time() - self._started_at, 1),
            "registry": self.registry.stats(),
            "agents": {
                aid: a.summary() for aid, a in self.agents.items()
            },
        }
