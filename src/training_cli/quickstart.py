"""Print a ready-to-run dispatch command for a new HF Training Job.

Does NOT execute. Operator sees the command, copies it, runs it themselves.
This keeps the irreversible cloud-spend action out of the CLI's blast radius.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
