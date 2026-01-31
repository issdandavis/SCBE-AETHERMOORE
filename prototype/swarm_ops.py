"""
Swarm Operations Module - Agentic Flow & Task Orchestration.

This is about HOW agents work together to accomplish tasks:
- Task decomposition and assignment
- Agent-to-agent handoffs
- Parallel execution pipelines
- Real-time collaboration
- Self-healing and adaptive routing
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable, Any
from enum import Enum
import time
import uuid
from toy_phdm import ToyPHDM, Tongue, PHI, PYTHAGOREAN_COMMA


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_HANDOFF = "waiting_handoff"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AgentRole(Enum):
    """What each Sacred Tongue agent DOES operationally."""
    KO = ("Orchestrator", "Routes tasks, manages flow, makes routing decisions")
    AV = ("Messenger", "Handles I/O, API calls, data transport between agents")
    RU = ("Validator", "Checks policies, validates inputs, enforces rules")
    CA = ("Worker", "Does the actual computation, transforms data")
    UM = ("Guardian", "Security checks, redaction, access control")
    DR = ("Recorder", "Schema validation, state persistence, audit logging")

    def __init__(self, role: str, description: str):
        self.role = role
        self.description = description


@dataclass
class Task:
    """A unit of work to be executed by the swarm."""
    id: str
    name: str
    payload: Dict[str, Any]
    required_tongue: Optional[str] = None  # Which agent type should handle
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    children: List[str] = field(default_factory=list)  # Sub-tasks spawned


@dataclass
class Message:
    """Inter-agent message for coordination."""
    id: str
    from_agent: str
    to_agent: str
    msg_type: str  # "handoff", "request", "response", "broadcast"
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


@dataclass
class AgentState:
    """Operational state of an agent."""
    tongue: str
    role: AgentRole
    busy: bool = False
    current_task: Optional[str] = None
    task_queue: List[str] = field(default_factory=list)
    messages_inbox: List[Message] = field(default_factory=list)
    completed_tasks: int = 0
    failed_tasks: int = 0
    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0]))
    coherence: float = 1.0


class SwarmOrchestrator:
    """
    Orchestrates multi-agent task execution.

    The 6 agents work together in a pipeline:

    User Request
         ↓
    [KO: Orchestrator] → Decomposes task, routes to appropriate agents
         ↓
    [RU: Validator] → Validates inputs, checks policies
         ↓
    [AV: Messenger] → Fetches external data if needed
         ↓
    [CA: Worker] → Performs core computation
         ↓
    [UM: Guardian] → Security check, redaction
         ↓
    [DR: Recorder] → Logs result, persists state
         ↓
    Response
    """

    # Pipeline definitions - which agents handle which task types
    PIPELINES = {
        "query": ["KO", "RU", "CA", "DR"],           # Simple query
        "fetch": ["KO", "AV", "RU", "CA", "DR"],     # External data fetch
        "compute": ["KO", "RU", "CA", "CA", "DR"],   # Heavy computation (CA twice)
        "secure": ["KO", "RU", "UM", "CA", "UM", "DR"],  # Security-sensitive
        "admin": ["KO", "RU", "UM", "UM", "CA", "DR"],   # Admin action (double UM)
    }

    def __init__(self):
        """Initialize the swarm orchestrator."""
        self.phdm = ToyPHDM()
        self.agents: Dict[str, AgentState] = {}
        self.tasks: Dict[str, Task] = {}
        self.messages: List[Message] = []
        self.execution_log: List[Dict] = []
        self._initialize_agents()

    def _initialize_agents(self):
        """Set up all 6 agents with their operational roles."""
        for tongue in Tongue:
            role = AgentRole[tongue.name]
            pos = self.phdm.agents[tongue.name].position

            self.agents[tongue.name] = AgentState(
                tongue=tongue.name,
                role=role,
                position=pos,
                coherence=1.0
            )

    # ==================== Task Management ====================

    def create_task(self, name: str, payload: Dict[str, Any],
                    pipeline: str = "query",
                    dependencies: List[str] = None) -> Task:
        """
        Create a new task to be executed by the swarm.

        Args:
            name: Human-readable task name
            payload: Task data/parameters
            pipeline: Which pipeline to use (query, fetch, compute, secure, admin)
            dependencies: List of task IDs that must complete first

        Returns:
            Created Task object
        """
        task = Task(
            id=str(uuid.uuid4())[:8],
            name=name,
            payload=payload,
            dependencies=dependencies or [],
        )
        task.payload["_pipeline"] = pipeline

        self.tasks[task.id] = task
        self._log(f"📝 Created task: {task.name} [{task.id}]")

        return task

    def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.

        Returns task ID for tracking.
        """
        # Check dependencies
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                task.status = TaskStatus.BLOCKED
                self._log(f"⏸️  Task {task.id} blocked waiting for {dep_id}")
                return task.id

        # Route to orchestrator (KO)
        task.status = TaskStatus.ASSIGNED
        task.assigned_to = "KO"
        self.agents["KO"].task_queue.append(task.id)

        self._log(f"📤 Submitted task {task.id} to KO")
        return task.id

    def execute_pipeline(self, task_id: str) -> Dict[str, Any]:
        """
        Execute a task through its full pipeline.

        Returns execution result.
        """
        task = self.tasks.get(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}

        pipeline_name = task.payload.get("_pipeline", "query")
        pipeline = self.PIPELINES.get(pipeline_name, self.PIPELINES["query"])

        self._log(f"🚀 Executing task {task.id} via {pipeline_name} pipeline")
        self._log(f"   Pipeline: {' → '.join(pipeline)}")

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = time.time()

        result = task.payload.copy()
        del result["_pipeline"]

        # Execute through each agent in pipeline
        for i, agent_name in enumerate(pipeline):
            agent = self.agents[agent_name]

            self._log(f"   [{i+1}/{len(pipeline)}] {agent_name} ({agent.role.role})")

            # Simulate agent work
            try:
                result = self._agent_process(agent_name, task, result)

                # Handoff to next agent
                if i < len(pipeline) - 1:
                    next_agent = pipeline[i + 1]
                    self._send_message(agent_name, next_agent, "handoff", result)

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                self._log(f"   ❌ Failed at {agent_name}: {e}")
                return {"error": str(e), "failed_at": agent_name}

        # Complete
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result

        duration = task.completed_at - task.started_at
        self._log(f"✅ Task {task.id} completed in {duration:.3f}s")

        return result

    def _agent_process(self, agent_name: str, task: Task,
                       data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate an agent processing data.

        Each agent type does something different.
        """
        agent = self.agents[agent_name]
        agent.busy = True
        agent.current_task = task.id

        result = data.copy()

        # Simulate work based on agent role
        if agent_name == "KO":
            # Orchestrator: Add routing metadata
            result["_routed_by"] = "KO"
            result["_route_time"] = time.time()

        elif agent_name == "AV":
            # Messenger: Simulate external fetch
            if "fetch_url" in result:
                result["_fetched_data"] = f"[Data from {result['fetch_url']}]"
            result["_transported"] = True

        elif agent_name == "RU":
            # Validator: Check policies
            if "bypass" in str(result).lower():
                raise ValueError("Policy violation: bypass attempt detected")
            result["_validated"] = True
            result["_policy_check"] = "passed"

        elif agent_name == "CA":
            # Worker: Do computation
            if "compute" in result:
                # Simulate computation
                result["_computed"] = f"Result of: {result['compute']}"
            result["_processed"] = True

        elif agent_name == "UM":
            # Guardian: Security check
            sensitive_fields = ["password", "secret", "token", "key"]
            for field in sensitive_fields:
                if field in result:
                    result[field] = "[REDACTED]"
            result["_security_cleared"] = True

        elif agent_name == "DR":
            # Recorder: Log and persist
            result["_logged_at"] = time.time()
            result["_task_id"] = task.id
            result["_audit_hash"] = hash(str(result)) % 1000000

        agent.busy = False
        agent.current_task = None
        agent.completed_tasks += 1

        return result

    # ==================== Inter-Agent Communication ====================

    def _send_message(self, from_agent: str, to_agent: str,
                      msg_type: str, payload: Dict[str, Any]):
        """Send a message between agents."""
        msg = Message(
            id=str(uuid.uuid4())[:8],
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type,
            payload=payload
        )

        self.messages.append(msg)
        self.agents[to_agent].messages_inbox.append(msg)

    def broadcast(self, from_agent: str, msg_type: str, payload: Dict[str, Any]):
        """Broadcast a message to all agents."""
        for name in self.agents:
            if name != from_agent:
                self._send_message(from_agent, name, msg_type, payload)

    # ==================== Parallel Execution ====================

    def execute_parallel(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """
        Execute multiple independent tasks in parallel.

        Simulates concurrent execution across agents.
        """
        self._log(f"⚡ Parallel execution: {len(tasks)} tasks")

        results = []
        for task in tasks:
            self.submit_task(task)
            result = self.execute_pipeline(task.id)
            results.append(result)

        return results

    def fork_join(self, parent_task: Task, subtasks: List[Dict]) -> Dict[str, Any]:
        """
        Fork-join pattern: Split task into subtasks, execute, merge results.

        Args:
            parent_task: The main task
            subtasks: List of subtask definitions

        Returns:
            Merged result
        """
        self._log(f"🔀 Fork-join: {parent_task.name} → {len(subtasks)} subtasks")

        # Create subtasks
        child_tasks = []
        for i, st in enumerate(subtasks):
            child = self.create_task(
                name=f"{parent_task.name}_sub_{i}",
                payload=st,
                pipeline=st.get("_pipeline", "query")
            )
            child_tasks.append(child)
            parent_task.children.append(child.id)

        # Execute all subtasks
        results = self.execute_parallel(child_tasks)

        # Merge results
        merged = {
            "parent_task": parent_task.id,
            "subtask_results": results,
            "merged_at": time.time()
        }

        return merged

    # ==================== Adaptive Routing ====================

    def route_by_load(self, task: Task) -> str:
        """
        Route task to least-loaded agent of appropriate type.
        """
        required = task.required_tongue

        if required:
            return required

        # Find least busy agent
        min_queue = float('inf')
        best_agent = "KO"

        for name, agent in self.agents.items():
            queue_len = len(agent.task_queue)
            if queue_len < min_queue and not agent.busy:
                min_queue = queue_len
                best_agent = name

        return best_agent

    def route_by_coherence(self, task: Task) -> str:
        """
        Route to agent with highest coherence (health).
        """
        best_coherence = 0
        best_agent = "KO"

        for name, agent in self.agents.items():
            if agent.coherence > best_coherence:
                best_coherence = agent.coherence
                best_agent = name

        return best_agent

    # ==================== Self-Healing ====================

    def check_agent_health(self) -> Dict[str, float]:
        """Check health/coherence of all agents."""
        return {name: agent.coherence for name, agent in self.agents.items()}

    def heal_agent(self, agent_name: str):
        """Attempt to heal a degraded agent."""
        agent = self.agents[agent_name]

        if agent.coherence < 0.5:
            # Redistribute queue
            if agent.task_queue:
                backup = "KO" if agent_name != "KO" else "DR"
                self._log(f"🔧 Redistributing {len(agent.task_queue)} tasks from {agent_name} to {backup}")
                self.agents[backup].task_queue.extend(agent.task_queue)
                agent.task_queue = []

            # Reset agent
            agent.coherence = min(1.0, agent.coherence + 0.3)
            self._log(f"🔧 Healed {agent_name}, coherence now {agent.coherence:.2f}")

    def reroute_around_failure(self, failed_agent: str, task: Task) -> str:
        """
        Find alternate route when an agent fails.
        """
        # Define fallback mappings
        fallbacks = {
            "KO": "DR",  # Orchestrator → Recorder can route
            "AV": "KO",  # Messenger → Orchestrator handles directly
            "RU": "UM",  # Validator → Guardian can validate
            "CA": "KO",  # Worker → Orchestrator splits work
            "UM": "RU",  # Guardian → Validator has some security
            "DR": "KO",  # Recorder → Orchestrator logs
        }

        fallback = fallbacks.get(failed_agent, "KO")
        self._log(f"🔄 Rerouting from {failed_agent} to {fallback}")

        return fallback

    # ==================== Logging ====================

    def _log(self, message: str):
        """Log execution event."""
        entry = {
            "timestamp": time.time(),
            "message": message
        }
        self.execution_log.append(entry)
        print(message)

    def get_metrics(self) -> Dict:
        """Get swarm operational metrics."""
        total_completed = sum(a.completed_tasks for a in self.agents.values())
        total_failed = sum(a.failed_tasks for a in self.agents.values())

        return {
            "total_tasks": len(self.tasks),
            "completed": total_completed,
            "failed": total_failed,
            "success_rate": total_completed / max(1, total_completed + total_failed),
            "messages_sent": len(self.messages),
            "agent_loads": {
                name: len(agent.task_queue) for name, agent in self.agents.items()
            },
            "agent_coherence": {
                name: agent.coherence for name, agent in self.agents.items()
            }
        }


def demo():
    """Demonstrate swarm operations."""
    print("=" * 60)
    print("Swarm Operations Demo - Agentic Flow")
    print("=" * 60)

    swarm = SwarmOrchestrator()

    # Simple query task
    print("\n📋 Task 1: Simple Query")
    task1 = swarm.create_task(
        name="Get user profile",
        payload={"user_id": "123", "fields": ["name", "email"]},
        pipeline="query"
    )
    swarm.submit_task(task1)
    result1 = swarm.execute_pipeline(task1.id)
    print(f"   Result keys: {list(result1.keys())}")

    # Fetch task with external data
    print("\n📋 Task 2: External Fetch")
    task2 = swarm.create_task(
        name="Fetch weather data",
        payload={"fetch_url": "https://api.weather.com/today"},
        pipeline="fetch"
    )
    swarm.submit_task(task2)
    result2 = swarm.execute_pipeline(task2.id)
    print(f"   Fetched: {result2.get('_fetched_data', 'N/A')}")

    # Secure task with sensitive data
    print("\n📋 Task 3: Secure Operation")
    task3 = swarm.create_task(
        name="Process payment",
        payload={"amount": 100, "password": "secret123", "token": "abc"},
        pipeline="secure"
    )
    swarm.submit_task(task3)
    result3 = swarm.execute_pipeline(task3.id)
    print(f"   Password after processing: {result3.get('password', 'N/A')}")  # Should be [REDACTED]

    # Task that should fail (policy violation)
    print("\n📋 Task 4: Policy Violation (should fail)")
    task4 = swarm.create_task(
        name="Bypass security check",
        payload={"action": "bypass all filters"},
        pipeline="admin"
    )
    swarm.submit_task(task4)
    result4 = swarm.execute_pipeline(task4.id)
    print(f"   Result: {result4}")

    # Fork-join pattern
    print("\n📋 Task 5: Fork-Join (parallel subtasks)")
    parent = swarm.create_task(
        name="Aggregate reports",
        payload={"report_type": "summary"},
        pipeline="query"
    )
    subtasks = [
        {"region": "US", "compute": "sum(sales)"},
        {"region": "EU", "compute": "sum(sales)"},
        {"region": "APAC", "compute": "sum(sales)"},
    ]
    result5 = swarm.fork_join(parent, subtasks)
    print(f"   Merged {len(result5['subtask_results'])} subtask results")

    # Final metrics
    print("\n📊 Swarm Metrics:")
    metrics = swarm.get_metrics()
    print(f"   Total tasks: {metrics['total_tasks']}")
    print(f"   Completed: {metrics['completed']}")
    print(f"   Success rate: {metrics['success_rate']:.1%}")
    print(f"   Messages sent: {metrics['messages_sent']}")


if __name__ == "__main__":
    demo()
