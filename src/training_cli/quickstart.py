"""Print a ready-to-run dispatch command for a new HF Training Job.

Does NOT execute. Operator sees the command, copies it, runs it themselves.
This keeps the irreversible cloud-spend action out of the CLI's blast radius.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class QuickstartPlan:
    base_model: str
    dataset_path: str
    run_name: str
    trainer: str  # "sft" | "dpo" | "merge"
    flavor: str
    command: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_model": self.base_model,
            "dataset_path": self.dataset_path,
            "run_name": self.run_name,
            "trainer": self.trainer,
            "flavor": self.flavor,
            "command": self.command,
            "command_str": " ".join(self.command),
            "notes": list(self.notes),
        }


_TRAINER_TO_DISPATCH_SCRIPT: dict[str, str] = {
    "sft": "scripts/system/dispatch_coding_agent_hf_job.py",
    "dpo": "scripts/system/dispatch_coding_agent_dpo_hf_job.py",
    "merge": "scripts/system/dispatch_coding_model_merge_hf_job.py",
    "aligned-foundations": "scripts/system/dispatch_aligned_foundations_hf_job.py",
}


def plan_quickstart(
    *,
    base_model: str,
    dataset_path: str,
    run_name: str,
    trainer: str = "sft",
    flavor: str = "default",
    repo_root: Path | None = None,
) -> QuickstartPlan:
    repo_root = repo_root or Path.cwd()
    script = _TRAINER_TO_DISPATCH_SCRIPT.get(trainer)
    notes: list[str] = []

    if script is None:
        notes.append(f"unknown trainer '{trainer}'; supported: {sorted(_TRAINER_TO_DISPATCH_SCRIPT)}")
        script = _TRAINER_TO_DISPATCH_SCRIPT["sft"]

    script_path = repo_root / script
    if not script_path.exists():
        notes.append(f"warning: dispatch script {script} does not exist at {script_path}")

    dataset_full = repo_root / dataset_path
    if not dataset_full.exists():
        notes.append(f"warning: dataset {dataset_path} does not exist at {dataset_full}")

    command = [
        "python",
        script,
        "--run-name",
        run_name,
        "--base-model",
        base_model,
        "--data",
        dataset_path,
        "--flavor",
        flavor,
    ]

    notes.append("Review the command before running. Cloud dispatch is billable and not reversible.")
    notes.append("After dispatch, monitor with: python scripts/scbe-system-cli.py training status")

    return QuickstartPlan(
        base_model=base_model,
        dataset_path=dataset_path,
        run_name=run_name,
        trainer=trainer,
        flavor=flavor,
        command=command,
        notes=notes,
    )


def supported_trainers() -> list[str]:
    return sorted(_TRAINER_TO_DISPATCH_SCRIPT)


# Council dispatch type alias: matches src.agent_comms.tiered_council_dispatch.dispatch_tiered_council
# The function returns the agentbus-shaped dict with keys: solved, final_tier, final_answer,
# total_cents, budget_cents, escalation_path, attempts, note.
CouncilDispatchFn = Callable[..., dict[str, Any]]


_COUNCIL_PROMPT_TEMPLATE = (
    "You are advising on a SCBE training pipeline dispatch. The operator wants to "
    "review the plan before running it; you do not execute anything.\n\n"
    "Operator's plan:\n"
    "- run_name: {run_name}\n"
    "- base_model: {base_model}\n"
    "- dataset: {dataset_path}\n"
    "- trainer: {trainer}\n"
    "- flavor: {flavor}\n\n"
    "Available trainers:\n"
    "- sft: supervised fine-tuning, expects JSONL of [{{prompt, response}}].\n"
    "- dpo: direct preference optimization, expects JSONL of [{{prompt, chosen, rejected}}].\n"
    "- merge: merge multiple LoRA adapters into a base model.\n"
    "- aligned-foundations: aligned-foundations dispatch (specialized).\n\n"
    "Based ONLY on the dataset path naming, run name, and base model name:\n"
    "1. Confirm the trainer choice or recommend a swap.\n"
    "2. Flag any obvious mismatch (e.g. DPO trainer with an SFT-shaped dataset name).\n"
    "3. Suggest one specific check before dispatch.\n\n"
    "Respond in at most 4 short bullet lines. If the names alone are ambiguous, say so. "
    "Do not invent file contents."
)


def plan_quickstart_with_council(
    *,
    base_model: str,
    dataset_path: str,
    run_name: str,
    trainer: str = "sft",
    flavor: str = "default",
    repo_root: Path | None = None,
    budget_cents: float = 5.0,
    families_to_include: tuple[str, ...] | None = None,
    dispatch_fn: CouncilDispatchFn | None = None,
) -> QuickstartPlan:
    """Wrap plan_quickstart with a tiered-council advisory.

    Council is asked to confirm/correct the trainer choice and flag mismatches.
    Its text response is appended to the plan's notes; the deterministic dispatch
    command is NOT mutated. Operator still eyeballs the command before running.

    `dispatch_fn` is injectable for tests; defaults to the live dispatch when None.
    """

    base_plan = plan_quickstart(
        base_model=base_model,
        dataset_path=dataset_path,
        run_name=run_name,
        trainer=trainer,
        flavor=flavor,
        repo_root=repo_root,
    )

    if dispatch_fn is None:
        from src.agent_comms.tiered_council_dispatch import (
            CouncilDispatchConfig,
            dispatch_tiered_council,
        )

        config = CouncilDispatchConfig(families_to_include=families_to_include)

        def _live_dispatch(**kwargs: Any) -> dict[str, Any]:
            return dispatch_tiered_council(config=config, **kwargs)

        dispatch_fn = _live_dispatch

    prompt = _COUNCIL_PROMPT_TEMPLATE.format(
        run_name=run_name,
        base_model=base_model,
        dataset_path=dataset_path,
        trainer=trainer,
        flavor=flavor,
    )

    council_notes: list[str] = ["--- council advisory ---"]
    try:
        result = dispatch_fn(
            task=prompt,
            budget_cents=budget_cents,
            metadata={
                "source": "training_cli.quickstart",
                "run_name": run_name,
                "trainer": trainer,
            },
        )
    except Exception as exc:  # noqa: BLE001 -- never let advisory failure block the plan
        council_notes.append(f"council unavailable: {type(exc).__name__}: {exc}")
        return replace(base_plan, notes=[*base_plan.notes, *council_notes])

    solved = bool(result.get("solved", False))
    final_tier = result.get("final_tier")
    total_cents = result.get("total_cents", 0.0)
    final_answer = (result.get("final_answer") or "").strip()
    escalation_path = result.get("escalation_path") or []

    if solved and final_answer:
        council_notes.append(f"tier={final_tier} cost={total_cents:.4f}c")
        for line in final_answer.splitlines():
            line = line.rstrip()
            if line:
                council_notes.append(line)
    else:
        council_notes.append(
            f"council did not converge (solved={solved}, tier={final_tier}, "
            f"cost={total_cents:.4f}c, budget={budget_cents:.4f}c)"
        )
        if escalation_path:
            council_notes.append(f"escalation: {' -> '.join(escalation_path)}")

    return replace(base_plan, notes=[*base_plan.notes, *council_notes])
