import json

import pytest

from ai_orchestration.tasks import (
    Task,
    TaskResult,
    TaskStatus,
    TerminationPolicy,
    Workflow,
    WorkflowExecutor,
)


@pytest.mark.asyncio
async def test_workflow_harness_emits_sequenced_events_and_checkpoint(tmp_path):
    workflow = Workflow(id="harness-run", name="Harness Run")
    task = Task(id="task-1", name="Step 1", task_type="unit")
    workflow.add_step("step1", task)

    async def executor(unit: Task) -> TaskResult:
        return TaskResult(
            task_id=unit.id, status=TaskStatus.COMPLETED, output={"ok": True}
        )

    runner = WorkflowExecutor(checkpoint_dir=tmp_path / "checkpoints")
    result = await runner.execute_workflow(workflow, executor)

    assert result["status"] == "completed"

    events = runner.get_execution_log()
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert {event["surface"] for event in events} == {"operational"}

    checkpoint_path = tmp_path / "checkpoints" / "harness-run.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["schema"] == "scbe_workflow_checkpoint_v1"
    assert checkpoint["workflow"]["status"] == "completed"
    assert checkpoint["workflow"]["steps"]["step1"]["task"]["status"] == "completed"


@pytest.mark.asyncio
async def test_termination_policy_pauses_before_unbounded_loop(tmp_path):
    workflow = Workflow(id="bounded-run", name="Bounded Run")
    workflow.add_step("step1", Task(id="task-1", name="Step 1", task_type="unit"))

    async def executor(unit: Task) -> TaskResult:
        return TaskResult(task_id=unit.id, status=TaskStatus.COMPLETED)

    runner = WorkflowExecutor(
        checkpoint_dir=tmp_path / "checkpoints",
        termination_policy=TerminationPolicy(max_events=1),
    )
    result = await runner.execute_workflow(workflow, executor)

    assert result["status"] == "paused"
    assert any(
        event["event"] == "workflow_paused" for event in runner.get_execution_log()
    )


@pytest.mark.asyncio
async def test_workflow_stall_is_failed_instead_of_hanging():
    workflow = Workflow(id="stalled-run", name="Stalled Run")
    workflow.add_step(
        "blocked",
        Task(
            id="blocked-task",
            name="Blocked",
            task_type="unit",
            dependencies=["missing-task"],
        ),
    )

    async def executor(unit: Task) -> TaskResult:
        return TaskResult(task_id=unit.id, status=TaskStatus.COMPLETED)

    runner = WorkflowExecutor()
    result = await runner.execute_workflow(workflow, executor)

    assert result["status"] == "failed"
    assert any(
        event["event"] == "workflow_stalled" for event in runner.get_execution_log()
    )


@pytest.mark.asyncio
async def test_checkpoint_resume_skips_completed_work(tmp_path):
    workflow = Workflow(id="resume-run", name="Resume Run")
    first = Task(id="first", name="First", task_type="unit")
    second = Task(id="second", name="Second", task_type="unit", dependencies=["first"])
    workflow.add_step("first", first)
    workflow.add_step("second", second)

    calls = []

    async def first_executor(unit: Task) -> TaskResult:
        calls.append(unit.id)
        return TaskResult(task_id=unit.id, status=TaskStatus.COMPLETED)

    first_runner = WorkflowExecutor(
        checkpoint_dir=tmp_path / "checkpoints",
        termination_policy=TerminationPolicy(max_events=3),
    )
    paused = await first_runner.execute_workflow(workflow, first_executor)
    assert paused["status"] == "paused"
    assert calls == ["first"]

    resumed_workflow = Workflow(id="resume-run", name="Resume Run")
    resumed_workflow.add_step("first", Task(id="first", name="First", task_type="unit"))
    resumed_workflow.add_step(
        "second",
        Task(id="second", name="Second", task_type="unit", dependencies=["first"]),
    )

    resumed_calls = []

    async def resume_executor(unit: Task) -> TaskResult:
        resumed_calls.append(unit.id)
        return TaskResult(task_id=unit.id, status=TaskStatus.COMPLETED)

    second_runner = WorkflowExecutor(checkpoint_dir=tmp_path / "checkpoints")
    completed = await second_runner.execute_workflow(resumed_workflow, resume_executor)

    assert completed["status"] == "completed"
    assert resumed_calls == ["second"]
