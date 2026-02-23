"""
SCBE Web Agent — AgentOrchestrator
====================================

Long-running task management with state persistence, recovery, and
multi-agent coordination.

Manages the lifecycle of web tasks:
  PENDING → RUNNING → COMPLETED / FAILED / TIMEOUT

Handles:
- Task queuing and prioritization
- State checkpointing for crash recovery
- Timeout enforcement
- Multi-agent task distribution
- Buffer integration for content posting (social media, CMS, APIs)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .semantic_antivirus import SemanticAntivirus
from .web_polly_pad import WebPollyPad, PadMode
from .navigation_engine import NavigationEngine, PageUnderstanding


# ---------------------------------------------------------------------------
#  Task types
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    NAVIGATE = "navigate"           # Go to URL, extract info
    RESEARCH = "research"           # Multi-page research task
    FORM_FILL = "form_fill"         # Fill and submit forms
    MONITOR = "monitor"             # Watch a page for changes
    POST_CONTENT = "post_content"   # Post to social/CMS/API (Buffer-style)
    WORKFLOW = "workflow"            # Multi-step custom workflow


@dataclass
class WebTask:
    """A task submitted to the web agent."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    task_type: TaskType = TaskType.NAVIGATE
    description: str = ""
    target_url: Optional[str] = None
    goal: str = ""                      # Natural language goal
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5                   # 1=highest, 10=lowest
    max_steps: int = 100
    timeout_seconds: float = 3600.0     # 1 hour default
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional["TaskResult"] = None
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)

    # Content posting fields (Buffer integration)
    post_content: Optional[str] = None          # Text to post
    post_platforms: List[str] = field(default_factory=list)  # twitter, linkedin, etc.
    post_schedule: Optional[float] = None       # Unix timestamp for scheduled post
    post_media: List[str] = field(default_factory=list)      # Media file paths/URLs


@dataclass
class TaskResult:
    """Result of a completed web task."""

    task_id: str
    status: TaskStatus
    data: Dict[str, Any] = field(default_factory=dict)
    extracted_text: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)  # File paths
    urls_visited: List[str] = field(default_factory=list)
    steps_taken: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    governance_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "data": self.data,
            "extracted_text": self.extracted_text,
            "screenshots": self.screenshots,
            "urls_visited": self.urls_visited,
            "steps_taken": self.steps_taken,
            "duration_seconds": round(self.duration_seconds, 2),
            "errors": self.errors,
            "governance_stats": self.governance_stats,
        }


# ---------------------------------------------------------------------------
#  Content posting buffer (Buffer-style integration)
# ---------------------------------------------------------------------------

@dataclass
class PostJob:
    """A content posting job for social media / CMS / API."""

    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    platforms: List[str] = field(default_factory=list)
    media: List[str] = field(default_factory=list)
    schedule_at: Optional[float] = None
    status: str = "queued"          # queued, posting, posted, failed
    results: Dict[str, Any] = field(default_factory=dict)  # platform → result
    created_at: float = field(default_factory=time.time)

    @property
    def is_due(self) -> bool:
        if self.schedule_at is None:
            return True
        return time.time() >= self.schedule_at


class ContentPostingBuffer:
    """
    Buffer-style content posting queue.

    Supports scheduling posts across multiple platforms with governance
    scanning before each post goes out.
    """

    def __init__(self, antivirus: Optional[SemanticAntivirus] = None) -> None:
        self._antivirus = antivirus or SemanticAntivirus()
        self._queue: List[PostJob] = []
        self._posted: List[PostJob] = []

    def enqueue(
        self,
        content: str,
        platforms: List[str],
        media: Optional[List[str]] = None,
        schedule_at: Optional[float] = None,
    ) -> PostJob:
        """Add a post to the queue. Content is scanned before queuing."""
        # Governance scan
        profile = self._antivirus.scan(content)
        if profile.governance_decision == "DENY":
            job = PostJob(content=content, platforms=platforms, status="blocked")
            job.results["governance"] = profile.to_dict()
            return job

        job = PostJob(
            content=content,
            platforms=platforms,
            media=media or [],
            schedule_at=schedule_at,
        )
        self._queue.append(job)
        return job

    def get_due_posts(self) -> List[PostJob]:
        """Return posts that are due for publishing."""
        return [j for j in self._queue if j.is_due and j.status == "queued"]

    def mark_posted(self, job_id: str, platform: str, result: Any) -> None:
        """Record that a post was published on a platform."""
        for job in self._queue:
            if job.job_id == job_id:
                job.results[platform] = result
                # If all platforms done, move to posted
                if set(job.platforms).issubset(set(job.results.keys())):
                    job.status = "posted"
                    self._queue.remove(job)
                    self._posted.append(job)
                break

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def posted_count(self) -> int:
        return len(self._posted)


# ---------------------------------------------------------------------------
#  AgentOrchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """
    Top-level orchestrator for web agent tasks.

    Manages multiple concurrent tasks, each running on its own
    NavigationEngine + WebPollyPad.
    """

    def __init__(
        self,
        agent_id: str = "scbe-web-agent-001",
        checkpoint_dir: Optional[str] = None,
        antivirus: Optional[SemanticAntivirus] = None,
    ) -> None:
        self.agent_id = agent_id
        self._antivirus = antivirus or SemanticAntivirus()
        self._checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None

        self._tasks: Dict[str, WebTask] = {}
        self._engines: Dict[str, NavigationEngine] = {}
        self._posting_buffer = ContentPostingBuffer(self._antivirus)

    # -- task management -----------------------------------------------------

    def submit_task(self, task: WebTask) -> str:
        """Submit a new task. Returns task_id."""
        self._tasks[task.task_id] = task

        if task.task_type == TaskType.POST_CONTENT:
            # Route to posting buffer
            if task.post_content:
                self._posting_buffer.enqueue(
                    content=task.post_content,
                    platforms=task.post_platforms,
                    media=task.post_media,
                    schedule_at=task.post_schedule,
                )
            task.status = TaskStatus.COMPLETED
            return task.task_id

        # Create navigation engine for this task
        pad = WebPollyPad(
            pad_id=f"pad-{task.task_id}",
            mode=self._task_type_to_pad_mode(task.task_type),
            antivirus=self._antivirus,
        )
        engine = NavigationEngine(polly_pad=pad, antivirus=self._antivirus)
        engine.set_goal(goal_url=task.target_url, goal_description=task.goal)
        engine._state.max_steps = task.max_steps

        self._engines[task.task_id] = engine
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        return task.task_id

    def step_task(self, task_id: str, page: PageUnderstanding) -> Optional[Dict[str, Any]]:
        """
        Execute one navigation step for a task.
        Feed current page, get back next action.
        Returns action dict or None if task is done.
        """
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return None

        # Check timeout
        elapsed = time.time() - (task.started_at or time.time())
        if elapsed > task.timeout_seconds:
            task.status = TaskStatus.TIMEOUT
            return None

        engine = self._engines.get(task_id)
        if not engine:
            return None

        # Feed page observation
        engine.observe_page(page)

        # Get next action
        action = engine.next_action()
        if action is None:
            # Goal reached or budget exhausted
            self._complete_task(task_id)
            return None

        return {
            "action_type": action.action_type.value,
            "target": action.target,
            "data": action.data,
            "timeout_ms": action.timeout_ms,
            "metadata": action.metadata,
        }

    def report_step_result(self, task_id: str, success: bool, error: Optional[str] = None) -> Optional[str]:
        """Report the result of executing a step. Returns recovery strategy or None."""
        engine = self._engines.get(task_id)
        if not engine:
            return None

        recovery = engine.handle_result(success, error)
        if recovery:
            return recovery.value

        # Checkpoint
        self._checkpoint(task_id)
        return None

    def _complete_task(self, task_id: str) -> None:
        """Mark task as completed and build result."""
        task = self._tasks.get(task_id)
        engine = self._engines.get(task_id)
        if not task:
            return

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()

        nav_summary = engine.summary() if engine else {}
        pad_summary = nav_summary.get("pad_summary", {})

        task.result = TaskResult(
            task_id=task_id,
            status=task.status,
            urls_visited=engine._pad._visited_urls if engine else [],
            steps_taken=nav_summary.get("steps_taken", 0),
            duration_seconds=(task.completed_at - (task.started_at or task.completed_at)),
            governance_stats=pad_summary.get("antivirus_stats", {}),
        )

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[WebTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[WebTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.priority)

    # -- content posting -----------------------------------------------------

    @property
    def posting_buffer(self) -> ContentPostingBuffer:
        return self._posting_buffer

    # -- checkpointing -------------------------------------------------------

    def _checkpoint(self, task_id: str) -> None:
        """Save task state for crash recovery."""
        if not self._checkpoint_dir:
            return
        task = self._tasks.get(task_id)
        engine = self._engines.get(task_id)
        if not task:
            return

        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        cp = {
            "task_id": task_id,
            "timestamp": time.time(),
            "status": task.status.value,
            "steps_taken": engine.state.steps_taken if engine else 0,
            "current_url": engine.state.current_url if engine else "",
        }
        task.checkpoints.append(cp)

        cp_path = self._checkpoint_dir / f"{task_id}.json"
        cp_path.write_text(json.dumps(cp, indent=2), encoding="utf-8")

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _task_type_to_pad_mode(task_type: TaskType) -> PadMode:
        return {
            TaskType.NAVIGATE: "NAVIGATION",
            TaskType.RESEARCH: "SCIENCE",
            TaskType.FORM_FILL: "ENGINEERING",
            TaskType.MONITOR: "SYSTEMS",
            TaskType.POST_CONTENT: "COMMS",
            TaskType.WORKFLOW: "MISSION",
        }.get(task_type, "NAVIGATION")

    # -- status API ----------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for t in self._tasks.values():
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        return {
            "agent_id": self.agent_id,
            "total_tasks": len(self._tasks),
            "by_status": by_status,
            "posting_queue": self._posting_buffer.queue_size,
            "posted_total": self._posting_buffer.posted_count,
        }
