from __future__ import annotations

"""Recreate and export the measured lattice-snap weights without pickle."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import torch
from safetensors.torch import load_file, save_file

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import multiview_perspective_reasoning as BASE  # noqa: E402
import spiral_staircase_lattice_snap as SNAP  # noqa: E402
import spiral_staircase_reasoning as COUPLED  # noqa: E402


DEFAULT_RESULTS = Path("artifacts") / "spiral_staircase_lattice_snap_20261021" / "RESULTS.json"
DEFAULT_OUTPUT = Path("artifacts") / "spiral_staircase_lattice_snap_20261021" / "checkpoints"
DEFAULT_ARM = "aligned_receipt_phi"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cpu_state(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {
        name: value.detach().contiguous().cpu()
        for name, value in model.state_dict().items()
    }


def save_verified_checkpoint(
    model: SNAP.LatticeSnapStaircaseNet,
    path: Path,
    *,
    expected_state_sha256: str,
    metadata: Mapping[str, str],
) -> dict[str, object]:
    """Save a safe tensor file, reload it, and prove its state hash."""
    actual = COUPLED.model_state_sha256(model)
    if actual != expected_state_sha256:
        raise RuntimeError(f"state mismatch before save: expected {expected_state_sha256}, got {actual}")
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(cpu_state(model), str(path), metadata=dict(metadata))

    restored = SNAP.LatticeSnapStaircaseNet()
    restored.load_state_dict(load_file(str(path), device="cpu"), strict=True)
    restored_hash = COUPLED.model_state_sha256(restored)
    if restored_hash != expected_state_sha256:
        raise RuntimeError(
            f"state mismatch after reload: expected {expected_state_sha256}, got {restored_hash}"
        )
    return {
        "path": str(path),
        "file_sha256": sha256_file(path),
        "state_sha256": restored_hash,
        "bytes": path.stat().st_size,
        "parameter_count": sum(parameter.numel() for parameter in restored.parameters()),
        "reload_verified": True,
    }


def export_measured_weights(
    results_path: Path,
    output_dir: Path,
    *,
    arm_name: str,
    seeds: Sequence[int] | None,
    device: torch.device,
) -> dict[str, object]:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    arm = next((candidate for candidate in SNAP.ARMS if candidate.name == arm_name), None)
    if arm is None:
        raise ValueError(f"unknown arm {arm_name!r}")
    measured = {
        int(run["seed"]): run
        for run in results["runs"]
        if run["arm"] == arm_name
    }
    selected = tuple(sorted(measured)) if seeds is None else tuple(seeds)
    missing = [seed for seed in selected if seed not in measured]
    if missing:
        raise ValueError(f"seeds absent from measured results: {missing}")

    checkpoints = []
    steps = int(results["steps"])
    for seed in selected:
        model, _ = SNAP.train_arm(arm, seed, steps, device)
        run = measured[seed]
        path = output_dir / f"{arm_name}_s{seed}.safetensors"
        checkpoint = save_verified_checkpoint(
            model,
            path,
            expected_state_sha256=str(run["state_sha256"]),
            metadata={
                "schema": "scbe.spiral-staircase-lattice-snap-weights.v1",
                "arm": arm_name,
                "seed": str(seed),
                "steps": str(steps),
                "source_sha256": str(results["source"]["sha256"]),
                "results_sha256": sha256_file(results_path),
            },
        )
        checkpoint.update(
            {
                "arm": arm_name,
                "seed": seed,
                "steps": steps,
                "deep_route_floor": float(run["metrics"]["deep_route_floor"]),
                "deep_full_route_exact": float(run["metrics"]["deep_full_route_exact"]),
            }
        )
        checkpoints.append(checkpoint)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    manifest = {
        "schema": "scbe.spiral-staircase-lattice-snap-checkpoints.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": "safetensors",
        "device_used_to_recreate": str(device),
        "results_path": str(results_path),
        "results_sha256": sha256_file(results_path),
        "executed_source_sha256": str(results["source"]["sha256"]),
        "arm": arm_name,
        "checkpoints": checkpoints,
        "all_state_hashes_match": all(item["reload_verified"] for item in checkpoints),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "CHECKPOINT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--arm", default=DEFAULT_ARM)
    parser.add_argument("--seeds", type=COUPLED.parse_seeds)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args(list(argv) if argv is not None else None)

    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "auto":
        device_name = "cpu"
    if device_name == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA requested but unavailable")
    device = torch.device(device_name)
    torch.set_num_threads(max(1, min(torch.get_num_threads(), 4)))
    BASE.configure_determinism(device)
    manifest = export_measured_weights(
        args.results,
        args.output_dir,
        arm_name=args.arm,
        seeds=args.seeds,
        device=device,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
