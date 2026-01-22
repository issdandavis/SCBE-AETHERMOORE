"""
AI Orchestrator - Central Control System
=========================================

The main orchestrator that coordinates all AI agents, manages workflows,
handles secure communication, and provides the unified interface for the system.

FEATURES:
=========
- Agent lifecycle management
- Secure message routing
- Workflow execution
- Load balancing
- Health monitoring
- Knowledge base integration

Version: 1.0.0
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .agents import (
    Agent,
    AgentRole,
    AgentStatus,
    AgentConfig,
    AgentMessage,
    SecurityAgent,
    ResearchAgent,
    BusinessAgent,
    EngineerAgent,
    CoordinatorAgent,
    create_agent,
)
from .tasks import Task, Workflow, TaskResult, TaskStatus, WorkflowExecutor
from .security import SecurityGate, SecurityConfig, ThreatLevel
from .logging import AuditLogger, WorkflowTracker, SecureStorage, LogLevel, LogCategory


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    max_agents: int = 50
    max_concurrent_tasks: int = 100
    enable_security: bool = True
    enable_logging: bool = True
    storage_path: str = "./scbe_data"
    knowledge_path: str = "./knowledge_bases"
    auto_load_packs: List[str] = field(default_factory=list)


class AgentRegistry:
    """
    Registry for all AI agents in the system.
    """

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.agents_by_role: Dict[AgentRole, List[str]] = {
            role: [] for role in AgentRole
        }

    def register(self, agent: Agent) -> str:
        """Register an agent."""
        self.agents[agent.id] = agent
        self.agents_by_role[agent.role].append(agent.id)
        return agent.id

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]
        self.agents_by_role[agent.role].remove(agent_id)
        del self.agents[agent_id]
        return True

    def get(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_by_role(self, role: AgentRole) -> List[Agent]:
        """Get all agents with a specific role."""
        return [
            self.agents[aid]
            for aid in self.agents_by_role.get(role, [])
            if aid in self.agents
        ]

    def get_available(self, role: Optional[AgentRole] = None) -> List[Agent]:
        """Get all available (idle) agents."""
        agents = self.agents.values()
        if role:
            agents = self.get_by_role(role)

        return [a for a in agents if a.status == AgentStatus.IDLE]

    def get_all(self) -> List[Agent]:
        """Get all registered agents."""
        return list(self.agents.values())

    def count(self) -> int:
        """Get total agent count."""
        return len(self.agents)


class Orchestrator:
    """
    Main orchestrator for the AI system.

    This is the central control point that:
    - Manages all AI agents
    - Routes messages securely
    - Executes workflows
    - Integrates knowledge bases
    - Handles logging and audit
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.registry = AgentRegistry()
        self.security_gate = SecurityGate() if self.config.enable_security else None

        # Storage
        storage_path = Path(self.config.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        self.storage = SecureStorage(str(storage_path / "secure"))
        self.audit_logger = AuditLogger(str(storage_path / "audit"))
        self.workflow_tracker = WorkflowTracker(self.audit_logger)
        self.workflow_executor = WorkflowExecutor()

        # Knowledge bases
        self.knowledge_bases: Dict[str, Dict[str, Any]] = {}

        # State
        self.started_at: Optional[datetime] = None
        self.is_running = False
        self.message_queue: asyncio.Queue = asyncio.Queue()

        # Load configured packs
        for pack_name in self.config.auto_load_packs:
            self._load_knowledge_pack(pack_name)

    async def start(self):
        """Start the orchestrator."""
        self.is_running = True
        self.started_at = datetime.now()

        self.audit_logger.log(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "orchestrator",
            "Orchestrator started",
            {
                "config": {
                    "max_agents": self.config.max_agents,
                    "security_enabled": self.config.enable_security,
                }
            },
        )

        # Start message processing
        asyncio.create_task(self._process_messages())

    async def stop(self):
        """Stop the orchestrator."""
        self.is_running = False

        # Notify all agents
        for agent in self.registry.get_all():
            agent.status = AgentStatus.OFFLINE

        self.audit_logger.log(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "orchestrator",
            "Orchestrator stopped",
            {"uptime_seconds": (datetime.now() - self.started_at).total_seconds()},
        )

        self.audit_logger.flush()

    # =========================================================================
    # AGENT MANAGEMENT
    # =========================================================================

    def create_agent(self, role: AgentRole, name: str, **kwargs) -> Agent:
        """Create and register a new agent."""
        if self.registry.count() >= self.config.max_agents:
            raise RuntimeError(
                f"Maximum agent limit reached ({self.config.max_agents})"
            )

        agent = create_agent(role, name, **kwargs)
        self.registry.register(agent)

        self.audit_logger.log_agent_action(
            agent.id, "created", {"name": name, "role": role.value}
        )

        return agent

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the system."""
        agent = self.registry.get(agent_id)
        if not agent:
            return False

        self.audit_logger.log_agent_action(
            agent_id, "removed", {"name": agent.name, "role": agent.role.value}
        )

        return self.registry.unregister(agent_id)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.registry.get(agent_id)

    def list_agents(self, role: Optional[AgentRole] = None) -> List[Dict[str, Any]]:
        """List all agents or filter by role."""
        if role:
            agents = self.registry.get_by_role(role)
        else:
            agents = self.registry.get_all()

        return [a.get_status() for a in agents]

    # =========================================================================
    # SECURE MESSAGING
    # =========================================================================

    async def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: str = "request",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentMessage]:
        """Send a secure message between agents."""
        sender = self.registry.get(sender_id)
        receiver = self.registry.get(receiver_id)

        if not sender or not receiver:
            return None

        # Security check
        if self.security_gate:
            allowed, sanitized, events = self.security_gate.check_input(
                content, sender_id
            )

            for event in events:
                self.audit_logger.log_security_event(
                    sender_id,
                    event.threat_type.value,
                    {"threat_level": event.threat_level.name, "blocked": event.blocked},
                    LogLevel.WARNING if event.blocked else LogLevel.INFO,
                )

            if not allowed:
                return None

            content = sanitized

        # Create message
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            timestamp=datetime.now(),
            content=content,
            encrypted=True,
            signature="",  # Will be signed
            message_type=message_type,
            metadata=metadata or {},
        )

        # Sign message
        if self.security_gate:
            signed_content = self.security_gate.sign_message(content, sender_id)
            message.content = signed_content
            message.signature = signed_content.split(":")[0]

        # Log communication
        import hashlib

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        self.audit_logger.log_communication(
            sender_id, receiver_id, message_type, content_hash
        )

        # Queue for delivery
        await self.message_queue.put(message)

        return message

    async def _process_messages(self):
        """Process message queue."""
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)

                receiver = self.registry.get(message.receiver_id)
                if receiver:
                    # Verify message if security enabled
                    content = message.content
                    if self.security_gate and ":" in content:
                        valid, original = self.security_gate.verify_message(
                            content, message.sender_id
                        )
                        if valid:
                            content = original
                        else:
                            self.audit_logger.log_security_event(
                                message.sender_id,
                                "invalid_signature",
                                {"receiver": message.receiver_id},
                            )
                            continue

                    # Update message with verified content
                    message.content = content

                    # Deliver to receiver
                    response = await receiver.receive_message(message)

                    if response:
                        # Queue response
                        await self.message_queue.put(response)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.audit_logger.log(
                    LogLevel.ERROR,
                    LogCategory.SYSTEM,
                    "orchestrator",
                    f"Message processing error: {str(e)}",
                    {},
                )

    # =========================================================================
    # TASK & WORKFLOW EXECUTION
    # =========================================================================

    async def execute_task(
        self,
        task: Task,
        agent_id: Optional[str] = None,
    ) -> TaskResult:
        """Execute a single task."""
        # Find agent
        if agent_id:
            agent = self.registry.get(agent_id)
        else:
            # Auto-assign based on task type
            available = self.registry.get_available()
            agent = available[0] if available else None

        if not agent:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error="No available agent",
            )

        task.assigned_agent = agent.id
        agent.status = AgentStatus.BUSY

        self.audit_logger.log_task_event(
            task.id,
            "started",
            agent.id,
            {"task_type": task.task_type, "input": task.input_data},
        )

        try:
            start_time = datetime.now()
            result_data = await agent.process_task(task.input_data)
            end_time = datetime.now()

            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output=result_data,
                started_at=start_time,
                completed_at=end_time,
                execution_time_ms=(end_time - start_time).total_seconds() * 1000,
                agent_id=agent.id,
            )

            self.audit_logger.log_task_event(
                task.id,
                "completed",
                agent.id,
                {"execution_time_ms": result.execution_time_ms},
            )

        except Exception as e:
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                agent_id=agent.id,
            )

            self.audit_logger.log_task_event(
                task.id, "failed", agent.id, {"error": str(e)}
            )

        finally:
            agent.status = AgentStatus.IDLE
            agent.task_count += 1

        return result

    async def execute_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute a complete workflow."""
        self.workflow_tracker.start_workflow(
            workflow.id, workflow.name, "orchestrator", workflow.metadata
        )

        async def task_executor(task: Task) -> TaskResult:
            result = await self.execute_task(task)
            self.workflow_tracker.log_step(
                workflow.id,
                task.name,
                result.status.value,
                result.agent_id or "unknown",
                result.output,
            )
            return result

        result = await self.workflow_executor.execute_workflow(workflow, task_executor)

        self.workflow_tracker.complete_workflow(
            workflow.id, result.get("status", "unknown"), result
        )

        return result

    # =========================================================================
    # KNOWLEDGE BASE MANAGEMENT
    # =========================================================================

    def _load_knowledge_pack(self, pack_name: str) -> bool:
        """Load a knowledge pack into memory."""
        # This would load from the science_packs module
        # For now, create a placeholder
        self.knowledge_bases[pack_name] = {
            "name": pack_name,
            "loaded_at": datetime.now().isoformat(),
            "status": "loaded",
        }

        self.audit_logger.log(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            "orchestrator",
            f"Knowledge pack loaded: {pack_name}",
            {"pack_name": pack_name},
        )

        return True

    def load_knowledge(self, pack_name: str, data: Dict[str, Any]) -> bool:
        """Load custom knowledge data."""
        self.knowledge_bases[pack_name] = data

        # Distribute to relevant agents
        for agent in self.registry.get_all():
            if pack_name in agent.config.knowledge_bases:
                agent.load_knowledge(pack_name, data)

        return True

    def get_loaded_knowledge(self) -> List[str]:
        """Get list of loaded knowledge bases."""
        return list(self.knowledge_bases.keys())

    # =========================================================================
    # SYSTEM STATUS & REPORTING
    # =========================================================================

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        agents = self.registry.get_all()

        return {
            "orchestrator": {
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "is_running": self.is_running,
                "uptime_seconds": (
                    (datetime.now() - self.started_at).total_seconds()
                    if self.started_at
                    else 0
                ),
            },
            "agents": {
                "total": len(agents),
                "by_status": {
                    status.value: sum(1 for a in agents if a.status == status)
                    for status in AgentStatus
                },
                "by_role": {
                    role.value: len(self.registry.get_by_role(role))
                    for role in AgentRole
                },
            },
            "knowledge_bases": self.get_loaded_knowledge(),
            "security": (
                self.security_gate.get_security_report()
                if self.security_gate
                else {"enabled": False}
            ),
            "workflows": {
                "active": len(self.workflow_tracker.get_active_workflows()),
                "completed": len(self.workflow_tracker.completed_workflows),
            },
        }

    def get_audit_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate audit report."""
        logs = self.audit_logger.query(
            start_time=start_time, end_time=end_time, limit=10000
        )

        return {
            "period": {
                "start": start_time.isoformat() if start_time else "all_time",
                "end": end_time.isoformat() if end_time else "now",
            },
            "total_entries": len(logs),
            "by_category": {
                cat.value: sum(1 for l in logs if l.category == cat)
                for cat in LogCategory
            },
            "by_level": {
                level.name: sum(1 for l in logs if l.level == level)
                for level in LogLevel
            },
            "chain_integrity": self.audit_logger.verify_chain_integrity(),
            "workflow_summary": self.workflow_tracker.generate_report(
                start_time, end_time
            ),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_orchestrator(
    enable_security: bool = True,
    storage_path: str = "./scbe_data",
    auto_create_agents: bool = True,
) -> Orchestrator:
    """Create a configured orchestrator with default agents."""
    config = OrchestratorConfig(
        enable_security=enable_security,
        storage_path=storage_path,
    )

    orchestrator = Orchestrator(config)

    if auto_create_agents:
        # Create default agent team
        orchestrator.create_agent(AgentRole.COORDINATOR, "MainCoordinator")
        orchestrator.create_agent(AgentRole.SECURITY, "SecurityGuard")
        orchestrator.create_agent(AgentRole.RESEARCH, "Researcher")
        orchestrator.create_agent(AgentRole.ENGINEER, "Engineer")

    return orchestrator


async def quick_start() -> Orchestrator:
    """Quick start an orchestrator with default configuration."""
    orchestrator = create_orchestrator()
    await orchestrator.start()
    return orchestrator
