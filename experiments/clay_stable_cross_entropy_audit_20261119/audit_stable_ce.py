"""Read-only audit of Clay logits for hard-target softmax collapse.

Implements Equation 6 from Barron, Gnanapragasam, and Tschannen,
"A Fix for Softmax and Cross-Entropy" (arXiv:2610.31642v3).  The active
campaign and its checkpoints are opened read-only; this script never trains.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Iterable

import torch
import torch.nn.functional as F

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from python.scbe.clay_stable_cross_entropy import (  # noqa: E402
    stable_hard_target_cross_entropy,
)


SCHEMA = "clay.stable-cross-entropy-audit.result.v1"
PAPER = "arXiv:2610.31642v3"
SEEDS = (20261134, 20261135, 20261136)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def synthetic_control() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for name, loss_function in (
        ("standard", lambda z, t: F.cross_entropy(z, t, reduction="none")),
        (
            "fixed",
            lambda z, t: stable_hard_target_cross_entropy(
                z, t, reduction="none"
            ),
        ),
    ):
        logits = torch.tensor(
            [[9.0, -9.0, -9.0]], dtype=torch.float32, requires_grad=True
        )
        targets = torch.tensor([0])
        losses = loss_function(logits, targets)
        gradient = torch.autograd.grad(losses.sum(), logits)[0]
        rows[name] = {
            "loss": float(losses[0].detach()),
            "gradient": [float(value) for value in gradient[0]],
            "gradient_sum": float(gradient.sum()),
        }
    return rows


def _quantiles(values: list[float]) -> dict[str, float]:
    tensor = torch.tensor(values, dtype=torch.float64)
    levels = (0.5, 0.9, 0.99, 0.999, 1.0)
    result = torch.quantile(tensor, torch.tensor(levels, dtype=torch.float64))
    return {f"q{level:g}": float(value) for level, value in zip(levels, result)}


def _iter_batches(count: int, size: int) -> Iterable[list[int]]:
    for start in range(0, count, size):
        yield list(range(start, min(start + size, count)))


def audit_split(
    *,
    model: torch.nn.Module,
    rows: tuple[tuple[str, str], ...],
    stoi: dict[str, int],
    make_batch: Any,
    batch_size: int,
) -> dict[str, Any]:
    margins: list[float] = []
    token_count = 0
    standard_zero_loss = 0
    fixed_zero_loss = 0
    collapsed_target_gradients = 0
    maximum_standard_gradient_sum_error = 0.0
    maximum_fixed_gradient_sum_error = 0.0
    maximum_loss_delta = 0.0

    for indices in _iter_batches(len(rows), batch_size):
        inputs, labels, masks = make_batch(rows, indices, stoi, "cpu")
        with torch.no_grad():
            raw_logits, _ = model(inputs, "action")
            selected = raw_logits[masks.to(dtype=torch.bool)]
            selected_targets = labels[masks.to(dtype=torch.bool)]

        target_logits = selected.gather(-1, selected_targets[:, None])
        non_targets = selected.clone()
        non_targets.scatter_(-1, selected_targets[:, None], -math.inf)
        margin = target_logits[:, 0] - torch.logsumexp(non_targets, dim=-1)
        margins.extend(float(value) for value in margin)

        standard_logits = selected.detach().requires_grad_(True)
        standard_losses = F.cross_entropy(
            standard_logits, selected_targets, reduction="none"
        )
        standard_gradient = torch.autograd.grad(
            standard_losses.sum(), standard_logits
        )[0]

        fixed_logits = selected.detach().requires_grad_(True)
        fixed_losses = stable_hard_target_cross_entropy(
            fixed_logits, selected_targets, reduction="none"
        )
        fixed_gradient = torch.autograd.grad(fixed_losses.sum(), fixed_logits)[0]

        row_ids = torch.arange(len(selected_targets))
        standard_target = standard_gradient[row_ids, selected_targets]
        fixed_target = fixed_gradient[row_ids, selected_targets]
        collapsed_target_gradients += int(
            ((standard_target == 0) & (fixed_target != 0)).sum()
        )
        standard_zero_loss += int((standard_losses == 0).sum())
        fixed_zero_loss += int((fixed_losses == 0).sum())
        maximum_standard_gradient_sum_error = max(
            maximum_standard_gradient_sum_error,
            float(standard_gradient.sum(dim=-1).abs().max()),
        )
        maximum_fixed_gradient_sum_error = max(
            maximum_fixed_gradient_sum_error,
            float(fixed_gradient.sum(dim=-1).abs().max()),
        )
        maximum_loss_delta = max(
            maximum_loss_delta,
            float(
                (fixed_losses.detach() - standard_losses.detach()).abs().max()
            ),
        )
        token_count += len(selected_targets)

    return {
        "rows": len(rows),
        "supervised_tokens": token_count,
        "target_margin": _quantiles(margins),
        "margin_above_fp32_cliff_16_6": sum(value > 16.6 for value in margins),
        "standard_zero_loss_tokens": standard_zero_loss,
        "fixed_zero_loss_tokens": fixed_zero_loss,
        "collapsed_target_gradients": collapsed_target_gradients,
        "maximum_standard_gradient_sum_error": maximum_standard_gradient_sum_error,
        "maximum_fixed_gradient_sum_error": maximum_fixed_gradient_sum_error,
        "maximum_absolute_loss_delta": maximum_loss_delta,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_root = args.source_root.resolve(strict=True)
    sys.path.insert(0, str(source_root))
    from python.scbe.clay_frozen_multiview_adapter import (  # noqa: PLC0415
        FrozenActionModel,
        make_batch,
    )
    from python.scbe.clay_frozen_multiview_data import (  # noqa: PLC0415
        build_frozen_multiview_dataset,
    )
    from python.scbe.clay_paired_orbit_training import (  # noqa: PLC0415
        ClaySourceAdapter,
    )

    baseline = args.baseline_run.resolve(strict=True)
    manifest_path = baseline / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provider = ClaySourceAdapter(Path(manifest["config"]["source_dir"]))
    dataset = build_frozen_multiview_dataset(
        provider,
        rows_per_view=int(manifest["config"]["rows_per_view"]),
        holdout_rows=int(manifest["config"]["holdout_rows"]),
        seed=int(manifest["config"]["data_seed"]),
    )
    expected_dataset = manifest["dataset"]["manifest_sha256"]
    actual_dataset = dataset.manifest["manifest_sha256"]
    if actual_dataset != expected_dataset:
        raise RuntimeError("regenerated dataset differs from pinned baseline")

    per_seed = []
    for seed in SEEDS:
        model_path = (
            baseline
            / "horses"
            / f"frozen_adapter_multiview-seed-{seed}"
            / "MODEL.pt"
        )
        payload = torch.load(model_path, map_location="cpu", weights_only=False)
        vocabulary = list(payload["vocab"])
        stoi = {token: index for index, token in enumerate(vocabulary)}
        model = FrozenActionModel(len(vocabulary))
        model.load_state_dict(payload["model_state"])
        model.set_path("adapter")
        model.eval()
        split_results = {}
        for split, source_rows in (
            ("multiview_train", dataset.multiview_rows),
            ("source_disjoint_holdout", dataset.holdout_rows),
        ):
            print(f"auditing seed={seed} split={split}", flush=True)
            split_results[split] = audit_split(
                model=model,
                rows=tuple(row.pair() for row in source_rows),
                stoi=stoi,
                make_batch=make_batch,
                batch_size=args.batch_size,
            )
        per_seed.append(
            {
                "seed": seed,
                "model_path": str(model_path),
                "model_sha256": sha256(model_path),
                "splits": split_results,
            }
        )

    collapse_count = sum(
        split["collapsed_target_gradients"]
        for row in per_seed
        for split in row["splits"].values()
    )
    return {
        "schema": SCHEMA,
        "paper": PAPER,
        "authority": "READ_ONLY_MEASUREMENT_NO_TRAINING_NO_PROMOTION",
        "torch_version": torch.__version__,
        "baseline_manifest": str(manifest_path),
        "baseline_manifest_sha256": sha256(manifest_path),
        "dataset_manifest_sha256": actual_dataset,
        "dataset_manifest_matches": True,
        "synthetic_control": synthetic_control(),
        "per_seed": per_seed,
        "real_collapsed_target_gradients": collapse_count,
        "active_path_susceptible": collapse_count > 0,
        "interpretation": (
            "The pinned trained model exhibits standard-CE target-gradient collapse."
            if collapse_count
            else "No supervised token in this bounded audit reached target-gradient collapse."
        ),
        "scope": (
            "Arithmetic audit only. It does not establish a training-quality gain; "
            "the active successor remains storage-gated and untouched."
        ),
        "elapsed_seconds": time.monotonic(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main() -> int:
    started = time.monotonic()
    args = parse_args()
    result = run(args)
    result["elapsed_seconds"] = time.monotonic() - started
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "active_path_susceptible": result["active_path_susceptible"],
        "real_collapsed_target_gradients": result["real_collapsed_target_gradients"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
