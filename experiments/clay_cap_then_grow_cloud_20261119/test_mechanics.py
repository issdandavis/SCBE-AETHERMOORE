"""Bounded no-checkpoint mechanics smoke for the cloud code-out campaign."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import torch


HERE = Path(__file__).resolve().parent
RUNTIME = (
    HERE.parent
    / "clay_input_access_mainlane_smoke_20261119"
    / "runtime-extract"
)


class MemoryCheckpoint:
    def __init__(self, _directory: Path) -> None:
        self.saved = []

    def load(self):
        return None

    def save(self, payload, generation: int) -> None:
        self.saved.append((int(payload["step"]), generation))


def main() -> None:
    runner_path = HERE / "kernel" / "run_cap_then_grow_kaggle.py"
    spec = importlib.util.spec_from_file_location("cap_then_grow_runner", runner_path)
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)

    scbe_root = RUNTIME / "scbe_repo"
    sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_frozen_multiview_adapter as core

    core.TwoSlotCheckpoint = MemoryCheckpoint
    runner.UPDATES = 2
    runner.CHECKPOINT_EVERY = 1
    train, held, dataset_hash = runner.build_rows()
    assert len(train) == 1534 and len(held) == 1509
    parent = torch.load(
        RUNTIME / "baseline_run/parents/seed-20261134/PARENT.pt",
        map_location="cpu",
        weights_only=False,
    )
    model, receipt = runner.train_one(
        core,
        parent=parent,
        rows=[(row.prompt, row.target) for row in train],
        seed=20261134,
        arm="candidate",
        checkpoint_root=HERE / "unused-memory-checkpoint",
        dataset_sha256=dataset_hash,
        status_path=HERE / "MECHANICS_STATUS.json",
    )
    assert receipt["steps"] == 2
    assert receipt["trainable_parameters"] == 140820
    assert receipt["frozen_core_bit_identical"] is True
    assert runner.trainable_hash(model) != receipt["initial_trainable_sha256"]
    print("MECHANICS_PASS")


if __name__ == "__main__":
    main()
