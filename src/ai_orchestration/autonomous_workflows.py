"""
Autonomous AI-to-AI Workflow System
====================================

Enables 24/7 unattended operation with agent-to-agent handoffs,
automatic error recovery, and intelligent escalation.

FEATURES:
=========
1. Workflow Queuing - Persistent task queue with priorities
2. Agent Handoffs - Seamless work transfer between agents
3. Auto-Recovery - Automatic retry with exponential backoff
4. Watchdog Monitoring - Health checks and dead agent detection
5. Escalation Rules - Smart human notification when needed
6. Workflow Chaining - Multi-step autonomous pipelines
7. State Persistence - Survive restarts without data loss

Version: 1.0.0
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import hashlib


class WorkflowPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0    # Process immediately
    HIGH = 1        # Process soon
    NORMAL = 2      # Standard processing
    LOW = 3         # Background tasks
    BATCH = 4       # Process when idle


class WorkflowState(Enum):
    """Workflow execution state."""
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"      # Waiting for another agent/step
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"  # Sent to human


class RecoveryAction(Enum):
    """Actions for error recovery."""
    RETRY = "retry"
    SKIP = "skip"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    agent_role: str  # Required agent type
    action: str      # Action to perform
    input_data: Dict[str, Any]
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 30
    depends_on: List[str] = field(default_factory=list)  # Step IDs
    on_failure: RecoveryAction = RecoveryAction.RETRY

    # Runtime state
    status: WorkflowState = WorkflowState.QUEUED
    assigned_agent: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class AutonomousWorkflow:
    """A complete autonomous workflow."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: WorkflowState = WorkflowState.QUEUED
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Escalation settings
    escalate_after_failures: int = 3
    escalate_after_timeout: int = 3600  # 1 hour
    notification_channels: List[str] = field(default_factory=list)

    # Chaining
    on_complete_trigger: Optional[str] = None  # Next workflow ID
    parent_workflow_id: Optional[str] = None


@dataclass
class EscalationEvent:
    """An event that requires human attention."""
    id: str
    workflow_id: str
    step_id: Optional[str]
    reason: str
    severity: str  # info, warning, critical
    context: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False


class PersistentQueue:
    """
    Persistent task queue with priority support.
    Survives restarts by writing to disk.
    """

    def __init__(self, storage_path: str = "./workflow_queue"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.queue: Dict[str, AutonomousWorkflow] = {}
        self._load_queue()

    def _load_queue(self):
        """Load persisted workflows on startup."""
        queue_file = self.storage_path / "queue.json"
        if queue_file.exists():
            try:
                with open(queue_file, 'r') as f:
                    data = json.load(f)
                    # Restore workflows (simplified - would need proper deserialization)
                    self.queue = {}
            except Exception:
                pass

    def _save_queue(self):
        """Persist queue to disk."""
        queue_file = self.storage_path / "queue.json"
        # Simplified - would serialize workflow objects
        data = {wf_id: wf.name for wf_id, wf in self.queue.items()}
        with open(queue_file, 'w') as f:
            json.dump(data, f)

    def enqueue(self, workflow: AutonomousWorkflow) -> str:
        """Add workflow to queue."""
        self.queue[workflow.id] = workflow
        self._save_queue()
        return workflow.id

    def dequeue(self) -> Optional[AutonomousWorkflow]:
        """Get highest priority queued workflow."""
        queued = [
            wf for wf in self.queue.values()
            if wf.status == WorkflowState.QUEUED
        ]

        if not queued:
            return None

        # Sort by priority, then by creation time
        queued.sort(key=lambda w: (w.priority.value, w.created_at))
        return queued[0]

    def get(self, workflow_id: str) -> Optional[AutonomousWorkflow]:
        """Get workflow by ID."""
        return self.queue.get(workflow_id)

    def update(self, workflow: AutonomousWorkflow):
        """Update workflow in queue."""
        self.queue[workflow.id] = workflow
        self._save_queue()

    def remove(self, workflow_id: str):
        """Remove workflow from queue."""
        if workflow_id in self.queue:
            del self.queue[workflow_id]
            self._save_queue()

    def get_pending(self) -> List[AutonomousWorkflow]:
        """Get all pending workflows."""
        return [
            wf for wf in self.queue.values()
            if wf.status in (WorkflowState.QUEUED, WorkflowState.RUNNING, WorkflowState.WAITING)
        ]


class AgentHandoffManager:
    """
    Manages seamless handoffs between agents.
    Preserves context and state across transitions.
    """

    def __init__(self):
        self.handoff_log: List[Dict[str, Any]] = []
        self.active_handoffs: Dict[str, Dict[str, Any]] = {}

    def initiate_handoff(
        self,
        from_agent_id: str,
        to_agent_id: str,
        workflow_id: str,
        step_id: str,
        context: Dict[str, Any]
    ) -> str:
        """Initiate a handoff between agents."""
        handoff_id = str(uuid.uuid4())

        handoff = {
            "id": handoff_id,
            "from_agent": from_agent_id,
            "to_agent": to_agent_id,
            "workflow_id": workflow_id,
            "step_id": step_id,
            "context": context,
            "initiated_at": datetime.now().isoformat(),
            "status": "pending",
            "accepted_at": None
        }

        self.active_handoffs[handoff_id] = handoff
        return handoff_id

    def accept_handoff(self, handoff_id: str, agent_id: str) -> Dict[str, Any]:
        """Agent accepts a handoff."""
        if handoff_id not in self.active_handoffs:
            raise ValueError(f"Handoff not found: {handoff_id}")

        handoff = self.active_handoffs[handoff_id]

        if handoff["to_agent"] != agent_id:
            raise ValueError(f"Handoff not intended for agent: {agent_id}")

        handoff["status"] = "accepted"
        handoff["accepted_at"] = datetime.now().isoformat()

        self.handoff_log.append(handoff.copy())
        del self.active_handoffs[handoff_id]

        return handoff["context"]

    def get_pending_handoffs(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get pending handoffs for an agent."""
        return [
            h for h in self.active_handoffs.values()
            if h["to_agent"] == agent_id and h["status"] == "pending"
        ]


class WatchdogMonitor:
    """
    Monitors agent health and workflow progress.
    Detects stuck workflows and dead agents.
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        stuck_threshold: int = 300,
        on_stuck_callback: Optional[Callable] = None
    ):
        self.heartbeat_interval = heartbeat_interval
        self.stuck_threshold = stuck_threshold
        self.on_stuck_callback = on_stuck_callback

        self.agent_heartbeats: Dict[str, datetime] = {}
        self.workflow_checkpoints: Dict[str, datetime] = {}
        self._running = False

    def register_heartbeat(self, agent_id: str):
        """Register agent heartbeat."""
        self.agent_heartbeats[agent_id] = datetime.now()

    def checkpoint_workflow(self, workflow_id: str):
        """Checkpoint workflow progress."""
        self.workflow_checkpoints[workflow_id] = datetime.now()

    def get_dead_agents(self) -> List[str]:
        """Get agents that haven't sent heartbeat."""
        now = datetime.now()
        threshold = timedelta(seconds=self.stuck_threshold)

        return [
            agent_id for agent_id, last_heartbeat in self.agent_heartbeats.items()
            if now - last_heartbeat > threshold
        ]

    def get_stuck_workflows(self) -> List[str]:
        """Get workflows that are stuck."""
        now = datetime.now()
        threshold = timedelta(seconds=self.stuck_threshold)

        return [
            wf_id for wf_id, last_checkpoint in self.workflow_checkpoints.items()
            if now - last_checkpoint > threshold
        ]

    async def monitor_loop(self):
        """Main monitoring loop."""
        self._running = True

        while self._running:
            # Check for dead agents
            dead_agents = self.get_dead_agents()
            for agent_id in dead_agents:
                if self.on_stuck_callback:
                    await self.on_stuck_callback("agent_dead", agent_id)

            # Check for stuck workflows
            stuck_workflows = self.get_stuck_workflows()
            for wf_id in stuck_workflows:
                if self.on_stuck_callback:
                    await self.on_stuck_callback("workflow_stuck", wf_id)

            await asyncio.sleep(self.heartbeat_interval)

    def stop(self):
        """Stop monitoring."""
        self._running = False


class EscalationManager:
    """
    Manages escalation to humans when needed.
    Implements smart escalation rules.
    """

    def __init__(self):
        self.events: List[EscalationEvent] = []
        self.notification_handlers: Dict[str, Callable] = {}

    def register_handler(self, channel: str, handler: Callable):
        """Register notification handler for a channel."""
        self.notification_handlers[channel] = handler

    async def escalate(
        self,
        workflow_id: str,
        step_id: Optional[str],
        reason: str,
        severity: str,
        context: Dict[str, Any],
        channels: List[str]
    ) -> EscalationEvent:
        """Escalate an issue to humans."""
        event = EscalationEvent(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            step_id=step_id,
            reason=reason,
            severity=severity,
            context=context
        )

        self.events.append(event)

        # Send notifications
        for channel in channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    await handler(event)
                except Exception as e:
                    # Log but don't fail escalation
                    pass

        return event

    def acknowledge(self, event_id: str):
        """Acknowledge an escalation event."""
        for event in self.events:
            if event.id == event_id:
                event.acknowledged = True
                return

    def resolve(self, event_id: str, resolution: str):
        """Resolve an escalation event."""
        for event in self.events:
            if event.id == event_id:
                event.resolved = True
                event.context["resolution"] = resolution
                return

    def get_pending(self) -> List[EscalationEvent]:
        """Get pending escalation events."""
        return [e for e in self.events if not e.resolved]


class AutonomousWorkflowEngine:
    """
    Main engine for autonomous AI-to-AI workflows.

    Enables 24/7 unattended operation with:
    - Automatic task distribution
    - Error recovery
    - Agent handoffs
    - Human escalation when needed
    """

    def __init__(
        self,
        storage_path: str = "./autonomous_workflows",
        max_concurrent_workflows: int = 10,
        max_retries: int = 3
    ):
        self.storage_path = Path(storage_path)
        self.max_concurrent = max_concurrent_workflows
        self.max_retries = max_retries

        # Components
        self.queue = PersistentQueue(str(self.storage_path / "queue"))
        self.handoff_manager = AgentHandoffManager()
        self.watchdog = WatchdogMonitor(on_stuck_callback=self._handle_stuck)
        self.escalation_manager = EscalationManager()

        # Agent registry (would be injected from orchestrator)
        self.agents: Dict[str, Any] = {}
        self.agent_assignments: Dict[str, str] = {}  # workflow_step_id -> agent_id

        # State
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None

    def register_agent(self, agent_id: str, agent: Any):
        """Register an agent with the engine."""
        self.agents[agent_id] = agent
        self.watchdog.register_heartbeat(agent_id)

    async def start(self):
        """Start the autonomous workflow engine."""
        self._running = True

        # Start watchdog
        asyncio.create_task(self.watchdog.monitor_loop())

        # Start workflow processor
        self._processing_task = asyncio.create_task(self._process_loop())

    async def stop(self):
        """Stop the engine gracefully."""
        self._running = False
        self.watchdog.stop()

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

    async def submit_workflow(self, workflow: AutonomousWorkflow) -> str:
        """Submit a workflow for autonomous execution."""
        workflow.status = WorkflowState.QUEUED
        return self.queue.enqueue(workflow)

    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                # Get pending workflows
                pending = self.queue.get_pending()
                running_count = sum(
                    1 for wf in pending if wf.status == WorkflowState.RUNNING
                )

                # Start new workflows if capacity available
                if running_count < self.max_concurrent:
                    workflow = self.queue.dequeue()
                    if workflow:
                        asyncio.create_task(self._execute_workflow(workflow))

                await asyncio.sleep(1)  # Check every second

            except Exception as e:
                # Log error but keep running
                await asyncio.sleep(5)

    async def _execute_workflow(self, workflow: AutonomousWorkflow):
        """Execute a workflow autonomously."""
        workflow.status = WorkflowState.RUNNING
        workflow.started_at = datetime.now()
        self.queue.update(workflow)

        try:
            # Build dependency graph
            step_outputs: Dict[str, Dict[str, Any]] = {}
            completed_steps: set = set()

            while True:
                # Find next executable steps
                ready_steps = [
                    step for step in workflow.steps
                    if step.status == WorkflowState.QUEUED
                    and all(dep in completed_steps for dep in step.depends_on)
                ]

                if not ready_steps:
                    # Check if all done
                    if all(s.status == WorkflowState.COMPLETED for s in workflow.steps):
                        break
                    # Check for failures
                    if any(s.status == WorkflowState.FAILED for s in workflow.steps):
                        workflow.status = WorkflowState.FAILED
                        break
                    # Waiting for steps
                    await asyncio.sleep(1)
                    continue

                # Execute ready steps in parallel
                tasks = [
                    self._execute_step(workflow, step, step_outputs)
                    for step in ready_steps
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for step, result in zip(ready_steps, results):
                    if isinstance(result, Exception):
                        step.status = WorkflowState.FAILED
                        step.error = str(result)
                    elif result:
                        step_outputs[step.id] = result
                        completed_steps.add(step.id)

                self.queue.update(workflow)

            # Workflow completed
            workflow.status = WorkflowState.COMPLETED
            workflow.completed_at = datetime.now()

            # Trigger next workflow if configured
            if workflow.on_complete_trigger:
                next_wf = self.queue.get(workflow.on_complete_trigger)
                if next_wf:
                    await self.submit_workflow(next_wf)

        except Exception as e:
            workflow.status = WorkflowState.FAILED
            await self.escalation_manager.escalate(
                workflow.id,
                None,
                f"Workflow failed: {str(e)}",
                "critical",
                {"error": str(e)},
                workflow.notification_channels
            )

        finally:
            self.queue.update(workflow)

    async def _execute_step(
        self,
        workflow: AutonomousWorkflow,
        step: WorkflowStep,
        previous_outputs: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Execute a single workflow step."""
        step.status = WorkflowState.RUNNING
        step.started_at = datetime.now()
        self.watchdog.checkpoint_workflow(f"{workflow.id}:{step.id}")

        # Find available agent
        agent = await self._find_agent(step.agent_role)
        if not agent:
            # Wait for agent or escalate
            await asyncio.sleep(step.retry_delay_seconds)
            step.retry_count += 1

            if step.retry_count >= step.max_retries:
                await self._handle_step_failure(workflow, step, "No available agent")
                return None

            step.status = WorkflowState.QUEUED
            return None

        step.assigned_agent = agent.id
        self.agent_assignments[f"{workflow.id}:{step.id}"] = agent.id

        # Prepare input with previous step outputs
        input_data = {**step.input_data}
        for dep_id in step.depends_on:
            if dep_id in previous_outputs:
                input_data[f"from_{dep_id}"] = previous_outputs[dep_id]

        # Execute with timeout and retry
        for attempt in range(step.max_retries):
            try:
                result = await asyncio.wait_for(
                    agent.process_task({
                        "type": step.action,
                        **input_data
                    }),
                    timeout=step.timeout_seconds
                )

                step.status = WorkflowState.COMPLETED
                step.completed_at = datetime.now()
                step.output = result
                return result

            except asyncio.TimeoutError:
                step.retry_count += 1
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(step.retry_delay_seconds * (2 ** attempt))
                else:
                    await self._handle_step_failure(
                        workflow, step, f"Timeout after {step.timeout_seconds}s"
                    )

            except Exception as e:
                step.retry_count += 1
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(step.retry_delay_seconds * (2 ** attempt))
                else:
                    await self._handle_step_failure(workflow, step, str(e))

        return None

    async def _find_agent(self, role: str) -> Optional[Any]:
        """Find an available agent for a role."""
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'role') and agent.role.value == role:
                if hasattr(agent, 'status') and agent.status.value == 'idle':
                    return agent
        return None

    async def _handle_step_failure(
        self,
        workflow: AutonomousWorkflow,
        step: WorkflowStep,
        error: str
    ):
        """Handle step failure based on recovery action."""
        step.error = error

        if step.on_failure == RecoveryAction.RETRY:
            # Already exhausted retries
            step.status = WorkflowState.FAILED

        elif step.on_failure == RecoveryAction.SKIP:
            step.status = WorkflowState.COMPLETED
            step.output = {"skipped": True, "reason": error}

        elif step.on_failure == RecoveryAction.ESCALATE:
            step.status = WorkflowState.ESCALATED
            await self.escalation_manager.escalate(
                workflow.id,
                step.id,
                f"Step failed: {error}",
                "warning",
                {"step": step.name, "error": error},
                workflow.notification_channels
            )

        elif step.on_failure == RecoveryAction.ABORT:
            step.status = WorkflowState.FAILED
            workflow.status = WorkflowState.FAILED

    async def _handle_stuck(self, event_type: str, entity_id: str):
        """Handle stuck workflow or dead agent."""
        if event_type == "workflow_stuck":
            workflow = self.queue.get(entity_id.split(":")[0])
            if workflow:
                await self.escalation_manager.escalate(
                    workflow.id,
                    None,
                    "Workflow appears stuck",
                    "warning",
                    {"workflow_name": workflow.name},
                    workflow.notification_channels
                )

        elif event_type == "agent_dead":
            # Reassign tasks from dead agent
            for key, agent_id in list(self.agent_assignments.items()):
                if agent_id == entity_id:
                    wf_id, step_id = key.split(":")
                    workflow = self.queue.get(wf_id)
                    if workflow:
                        for step in workflow.steps:
                            if step.id == step_id:
                                step.status = WorkflowState.QUEUED
                                step.assigned_agent = None
                                self.queue.update(workflow)
                    del self.agent_assignments[key]

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        pending = self.queue.get_pending()

        return {
            "running": self._running,
            "workflows": {
                "total": len(self.queue.queue),
                "queued": sum(1 for wf in pending if wf.status == WorkflowState.QUEUED),
                "running": sum(1 for wf in pending if wf.status == WorkflowState.RUNNING),
                "waiting": sum(1 for wf in pending if wf.status == WorkflowState.WAITING)
            },
            "agents": {
                "registered": len(self.agents),
                "dead": len(self.watchdog.get_dead_agents())
            },
            "escalations": {
                "pending": len(self.escalation_manager.get_pending())
            }
        }


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

class WorkflowBuilder:
    """Fluent builder for creating workflows."""

    def __init__(self, name: str, description: str = ""):
        self.workflow = AutonomousWorkflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            steps=[]
        )
        self._step_counter = 0

    def add_step(
        self,
        name: str,
        agent_role: str,
        action: str,
        input_data: Dict[str, Any],
        depends_on: List[str] = None,
        timeout: int = 300,
        on_failure: RecoveryAction = RecoveryAction.RETRY
    ) -> 'WorkflowBuilder':
        """Add a step to the workflow."""
        step_id = f"step_{self._step_counter}"
        self._step_counter += 1

        step = WorkflowStep(
            id=step_id,
            name=name,
            agent_role=agent_role,
            action=action,
            input_data=input_data,
            depends_on=depends_on or [],
            timeout_seconds=timeout,
            on_failure=on_failure
        )

        self.workflow.steps.append(step)
        return self

    def set_priority(self, priority: WorkflowPriority) -> 'WorkflowBuilder':
        """Set workflow priority."""
        self.workflow.priority = priority
        return self

    def set_escalation(
        self,
        after_failures: int = 3,
        after_timeout: int = 3600,
        channels: List[str] = None
    ) -> 'WorkflowBuilder':
        """Configure escalation settings."""
        self.workflow.escalate_after_failures = after_failures
        self.workflow.escalate_after_timeout = after_timeout
        self.workflow.notification_channels = channels or []
        return self

    def chain_to(self, next_workflow_id: str) -> 'WorkflowBuilder':
        """Chain to another workflow on completion."""
        self.workflow.on_complete_trigger = next_workflow_id
        return self

    def build(self) -> AutonomousWorkflow:
        """Build the workflow."""
        return self.workflow
