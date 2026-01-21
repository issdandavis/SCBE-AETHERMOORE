"""
Task and Workflow Management
=============================

Defines tasks, workflows, and execution pipelines for the AI orchestration system.

FEATURES:
=========
- Task definition and lifecycle management
- Workflow creation with dependencies
- Progress tracking and reporting
- Result aggregation
- Error handling and retry logic

Version: 1.0.0
"""

import uuid
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    agent_id: Optional[str] = None
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "agent_id": self.agent_id,
            "retries": self.retries,
        }


@dataclass
class Task:
    """
    Represents a unit of work to be executed by an agent.

    Tasks can have dependencies on other tasks and will only
    execute when all dependencies are complete.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    task_type: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)  # task IDs
    assigned_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "input_data": self.input_data,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.to_dict() if self.result else None,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if task is ready to run (all dependencies complete)."""
        if self.status != TaskStatus.PENDING:
            return False
        return all(dep in completed_tasks for dep in self.dependencies)


@dataclass
class WorkflowStep:
    """A step in a workflow, wrapping a task with additional workflow context."""
    task: Task
    on_success: Optional[str] = None  # next step name
    on_failure: Optional[str] = None  # step to run on failure
    condition: Optional[Callable[[Dict], bool]] = None  # conditional execution


class WorkflowStatus(Enum):
    """Workflow execution status."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Workflow:
    """
    A workflow is a collection of tasks with dependencies that execute
    in a defined order to accomplish a larger goal.

    Workflows support:
    - Sequential and parallel task execution
    - Conditional branching
    - Error handling and recovery
    - Progress tracking
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    entry_point: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)  # shared state
    results: Dict[str, TaskResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(
        self,
        name: str,
        task: Task,
        on_success: Optional[str] = None,
        on_failure: Optional[str] = None,
        condition: Optional[Callable[[Dict], bool]] = None
    ):
        """Add a step to the workflow."""
        self.steps[name] = WorkflowStep(
            task=task,
            on_success=on_success,
            on_failure=on_failure,
            condition=condition
        )
        if not self.entry_point:
            self.entry_point = name

    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to execute."""
        completed = {
            name for name, step in self.steps.items()
            if step.task.status == TaskStatus.COMPLETED
        }

        ready = []
        for name, step in self.steps.items():
            if step.task.is_ready(completed):
                # Check condition if exists
                if step.condition and not step.condition(self.context):
                    continue
                ready.append(step.task)

        return ready

    def get_progress(self) -> Dict[str, Any]:
        """Get workflow progress."""
        total = len(self.steps)
        completed = sum(
            1 for step in self.steps.values()
            if step.task.status == TaskStatus.COMPLETED
        )
        failed = sum(
            1 for step in self.steps.values()
            if step.task.status == TaskStatus.FAILED
        )
        running = sum(
            1 for step in self.steps.values()
            if step.task.status == TaskStatus.RUNNING
        )

        return {
            "workflow_id": self.id,
            "name": self.name,
            "status": self.status.value,
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": total - completed - failed - running,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "entry_point": self.entry_point,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": {
                name: {
                    "task": step.task.to_dict(),
                    "on_success": step.on_success,
                    "on_failure": step.on_failure,
                }
                for name, step in self.steps.items()
            },
            "results": {
                k: v.to_dict() for k, v in self.results.items()
            },
            "progress": self.get_progress(),
            "metadata": self.metadata,
        }


class TaskQueue:
    """
    Priority queue for tasks with dependency resolution.
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.completed: Set[str] = set()

    def add(self, task: Task):
        """Add task to queue."""
        self.tasks[task.id] = task

    def remove(self, task_id: str):
        """Remove task from queue."""
        if task_id in self.tasks:
            del self.tasks[task_id]

    def mark_completed(self, task_id: str, result: TaskResult):
        """Mark task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].result = result
            self.completed.add(task_id)

    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks ready for execution, sorted by priority."""
        ready = [
            task for task in self.tasks.values()
            if task.is_ready(self.completed)
        ]
        return sorted(ready, key=lambda t: t.priority.value, reverse=True)

    def get_status(self) -> Dict[str, int]:
        """Get queue status."""
        status_counts = {s: 0 for s in TaskStatus}
        for task in self.tasks.values():
            status_counts[task.status] += 1
        return {s.value: c for s, c in status_counts.items()}


class WorkflowExecutor:
    """
    Executes workflows by coordinating tasks across agents.
    """

    def __init__(self):
        self.active_workflows: Dict[str, Workflow] = {}
        self.task_queue = TaskQueue()
        self.execution_log: List[Dict[str, Any]] = []

    async def execute_workflow(
        self,
        workflow: Workflow,
        agent_executor: Callable[[Task], TaskResult]
    ) -> Dict[str, Any]:
        """
        Execute a workflow to completion.

        Args:
            workflow: The workflow to execute
            agent_executor: Function to execute a task and return result

        Returns:
            Execution summary
        """
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        self.active_workflows[workflow.id] = workflow

        self._log_event("workflow_started", {
            "workflow_id": workflow.id,
            "name": workflow.name,
        })

        # Add all tasks to queue
        for name, step in workflow.steps.items():
            self.task_queue.add(step.task)

        try:
            while True:
                # Get ready tasks
                ready_tasks = self.task_queue.get_ready_tasks()

                if not ready_tasks:
                    # Check if all done or stuck
                    if all(
                        step.task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                        for step in workflow.steps.values()
                    ):
                        break
                    # Wait for running tasks
                    await asyncio.sleep(0.1)
                    continue

                # Execute ready tasks (can be parallel)
                results = await asyncio.gather(*[
                    self._execute_task(task, agent_executor, workflow)
                    for task in ready_tasks
                ])

                # Process results
                for task, result in zip(ready_tasks, results):
                    self.task_queue.mark_completed(task.id, result)
                    workflow.results[task.id] = result

                    # Find next step based on success/failure
                    step = next(
                        (s for s in workflow.steps.values() if s.task.id == task.id),
                        None
                    )
                    if step:
                        if result.status == TaskStatus.COMPLETED and step.on_success:
                            next_step = workflow.steps.get(step.on_success)
                            if next_step:
                                next_step.task.status = TaskStatus.PENDING
                        elif result.status == TaskStatus.FAILED and step.on_failure:
                            next_step = workflow.steps.get(step.on_failure)
                            if next_step:
                                next_step.task.status = TaskStatus.PENDING

            # Determine final status
            failed_count = sum(
                1 for step in workflow.steps.values()
                if step.task.status == TaskStatus.FAILED
            )

            if failed_count > 0:
                workflow.status = WorkflowStatus.FAILED
            else:
                workflow.status = WorkflowStatus.COMPLETED

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            self._log_event("workflow_error", {
                "workflow_id": workflow.id,
                "error": str(e),
            })

        workflow.completed_at = datetime.now()

        self._log_event("workflow_completed", {
            "workflow_id": workflow.id,
            "status": workflow.status.value,
            "duration_ms": (
                workflow.completed_at - workflow.started_at
            ).total_seconds() * 1000,
        })

        return workflow.to_dict()

    async def _execute_task(
        self,
        task: Task,
        executor: Callable[[Task], TaskResult],
        workflow: Workflow
    ) -> TaskResult:
        """Execute a single task with retry logic."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        self._log_event("task_started", {
            "task_id": task.id,
            "name": task.name,
            "workflow_id": workflow.id,
        })

        while task.retry_count <= task.max_retries:
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    asyncio.create_task(self._run_executor(executor, task)),
                    timeout=task.timeout_seconds
                )

                task.completed_at = datetime.now()
                result.execution_time_ms = (
                    task.completed_at - task.started_at
                ).total_seconds() * 1000

                if result.status == TaskStatus.COMPLETED:
                    task.status = TaskStatus.COMPLETED
                    self._log_event("task_completed", {
                        "task_id": task.id,
                        "execution_time_ms": result.execution_time_ms,
                    })
                    return result

                # Task failed, maybe retry
                task.retry_count += 1
                if task.retry_count <= task.max_retries:
                    task.status = TaskStatus.RETRYING
                    self._log_event("task_retry", {
                        "task_id": task.id,
                        "retry_count": task.retry_count,
                    })
                    await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                else:
                    task.status = TaskStatus.FAILED
                    return result

            except asyncio.TimeoutError:
                task.retry_count += 1
                self._log_event("task_timeout", {
                    "task_id": task.id,
                    "timeout_seconds": task.timeout_seconds,
                })

            except Exception as e:
                task.retry_count += 1
                self._log_event("task_error", {
                    "task_id": task.id,
                    "error": str(e),
                })

        # Exhausted retries
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now()

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error="Max retries exceeded",
            started_at=task.started_at,
            completed_at=task.completed_at,
            retries=task.retry_count,
        )

    async def _run_executor(self, executor: Callable, task: Task) -> TaskResult:
        """Run the executor (may be sync or async)."""
        if asyncio.iscoroutinefunction(executor):
            return await executor(task)
        return executor(task)

    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an execution event."""
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data,
        })

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get the execution log."""
        return self.execution_log


# =============================================================================
# WORKFLOW TEMPLATES
# =============================================================================

def create_security_audit_workflow(target: str) -> Workflow:
    """Create a workflow for security auditing."""
    workflow = Workflow(
        name="Security Audit",
        description=f"Security audit workflow for {target}",
    )

    # Step 1: Scan for threats
    scan_task = Task(
        name="Threat Scan",
        task_type="threat_scan",
        input_data={"target": target},
    )
    workflow.add_step("scan", scan_task, on_success="analyze")

    # Step 2: Analyze findings
    analyze_task = Task(
        name="Analyze Findings",
        task_type="analyze",
        dependencies=[scan_task.id],
    )
    workflow.add_step("analyze", analyze_task, on_success="report")

    # Step 3: Generate report
    report_task = Task(
        name="Generate Report",
        task_type="generate_report",
        dependencies=[analyze_task.id],
    )
    workflow.add_step("report", report_task)

    return workflow


def create_research_workflow(query: str, domains: List[str]) -> Workflow:
    """Create a workflow for research tasks."""
    workflow = Workflow(
        name="Research Workflow",
        description=f"Research: {query}",
    )

    # Step 1: Search knowledge bases
    search_task = Task(
        name="Search Knowledge",
        task_type="search_knowledge",
        input_data={"query": query, "domains": domains},
    )
    workflow.add_step("search", search_task, on_success="analyze")

    # Step 2: Analyze results
    analyze_task = Task(
        name="Analyze Results",
        task_type="analyze",
        dependencies=[search_task.id],
    )
    workflow.add_step("analyze", analyze_task, on_success="summarize")

    # Step 3: Summarize findings
    summarize_task = Task(
        name="Summarize",
        task_type="summarize",
        dependencies=[analyze_task.id],
    )
    workflow.add_step("summarize", summarize_task)

    return workflow


def create_business_report_workflow(portfolio_id: str, report_type: str) -> Workflow:
    """Create a workflow for business reporting."""
    workflow = Workflow(
        name="Business Report",
        description=f"Generate {report_type} report for portfolio {portfolio_id}",
    )

    # Step 1: Load portfolio data
    load_task = Task(
        name="Load Portfolio",
        task_type="load_data",
        input_data={"portfolio_id": portfolio_id},
    )
    workflow.add_step("load", load_task, on_success="analyze")

    # Step 2: Analyze portfolio
    analyze_task = Task(
        name="Analyze Portfolio",
        task_type="portfolio_analysis",
        dependencies=[load_task.id],
    )
    workflow.add_step("analyze", analyze_task, on_success="report")

    # Step 3: Generate report
    report_task = Task(
        name="Generate Report",
        task_type="generate_report",
        input_data={"report_type": report_type},
        dependencies=[analyze_task.id],
    )
    workflow.add_step("report", report_task)

    return workflow
