"""Matched data-arm test for paired concept-orbit exposure in Clay.

This campaign deliberately uses one ordinary MLP for every arm.  The changed
variable is the data support and batching: static unique rows, repeated rows,
independent multi-view rows, or the same latent state rendered through all
declared training views.  The held diagonal source is never used for updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any, Mapping, Protocol, Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F

SCHEMA = "clay.paired-orbit-data-campaign.v2"
ARMS = (
    "static_unique",
    "static_repeated",
    "curriculum_independent",
    "paired_orbit_shuffled",
    "paired_orbit_grouped",
)
PRIMARY_ARM = "paired_orbit_grouped"
CONTROLS = ARMS[:-1]
FEATURE_WIDTH = 37
ACTION_COUNT = 5
VIEW_COUNT = 3


class PairedOrbitError(ValueError):
    """Raised when source data or a campaign invariant is invalid."""


class DataProvider(Protocol):
    """Minimal interface implemented by the read-only Clay source adapter."""

    source_hashes: Mapping[str, str]

    def training_sandboxes(self) -> tuple[Any, ...]: ...

    def holdout_sandbox(self) -> Any: ...

    def sample_state(self, sandbox: Any, rng: random.Random) -> Any: ...

    def materialize(self, sandbox: Any, state: Any) -> tuple[Tensor, int, int]: ...


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_sha256(value: Tensor) -> str:
    cpu = value.detach().cpu().contiguous()
    header = f"{cpu.dtype}|{tuple(cpu.shape)}|".encode("ascii")
    return hashlib.sha256(header + cpu.numpy().tobytes()).hexdigest()


def state_dict_sha256(state: Mapping[str, Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        value = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _atomic_torch(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(dict(value), temporary)
    os.replace(temporary, path)


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


class ClaySourceAdapter:
    """Read the existing Clay generators without modifying their worktree."""

    def __init__(self, source_dir: str | Path) -> None:
        self.source_dir = Path(source_dir).resolve(strict=True)
        required = {
            "policy": self.source_dir / "trit_compiled_action_policy.py",
            "topology": self.source_dir / "topology_sector_action_ab.py",
            "sandbox": self.source_dir / "developmental_game_sandbox.py",
            "regional": self.source_dir / "regional_breathing_field.py",
        }
        missing = [str(path) for path in required.values() if not path.is_file()]
        if missing:
            raise PairedOrbitError(f"Clay source files are missing: {missing}")
        if str(self.source_dir) not in sys.path:
            sys.path.insert(0, str(self.source_dir))
        self._policy = importlib.import_module("trit_compiled_action_policy")
        self._topology = importlib.import_module("topology_sector_action_ab")
        self.source_hashes = {
            name: file_sha256(path) for name, path in required.items()
        }
        if len(self._policy.FEATURE_NAMES) != FEATURE_WIDTH:
            raise PairedOrbitError("Clay source feature width changed")
        if len(self._policy.MOTOR_ACTIONS) != ACTION_COUNT:
            raise PairedOrbitError("Clay source action width changed")

    def training_sandboxes(self) -> tuple[Any, ...]:
        result = tuple(self._policy.training_curriculum_sandboxes())
        if len(result) != VIEW_COUNT:
            raise PairedOrbitError(
                "paired campaign requires exactly three training views"
            )
        return result

    def holdout_sandbox(self) -> Any:
        return self._policy.holdout_sandbox()

    def sample_state(self, sandbox: Any, rng: random.Random) -> Any:
        return self._policy.sample_state(sandbox, rng)

    def materialize(self, sandbox: Any, state: Any) -> tuple[Tensor, int, int]:
        feature = self._policy.vectorize_state(sandbox, state)
        sector = int(self._topology.scope_sector(feature[None, :])[0].item())
        selected, _ = sandbox.sieve_actions(state)
        label = int(selected.token_id)
        if feature.shape != (FEATURE_WIDTH,) or label not in range(ACTION_COUNT):
            raise PairedOrbitError("Clay source emitted an invalid policy row")
        return feature, label, sector


@dataclass(frozen=True, slots=True)
class OrbitBank:
    name: str
    features: Tensor
    labels: Tensor
    sectors: Tensor
    groups: Tensor
    views: Tensor
    complete_groups: bool
    manifest_sha256: str

    def verify(self) -> bool:
        count = self.features.shape[0]
        if self.features.shape != (count, FEATURE_WIDTH):
            return False
        if any(
            value.shape != (count,)
            for value in (self.labels, self.sectors, self.groups, self.views)
        ):
            return False
        if any(
            value.dtype != torch.int64
            for value in (self.labels, self.sectors, self.groups, self.views)
        ):
            return False
        if bool(torch.any((self.labels < 0) | (self.labels >= ACTION_COUNT))):
            return False
        if not bool(torch.isfinite(self.features).all()):
            return False
        if self.complete_groups:
            counts = torch.bincount(self.groups)
            if counts.numel() == 0 or not bool(torch.all(counts == VIEW_COUNT)):
                return False
            for group in range(counts.numel()):
                if set(self.views[self.groups == group].tolist()) != set(
                    range(VIEW_COUNT)
                ):
                    return False
        body = _bank_body(
            self.name,
            self.features,
            self.labels,
            self.sectors,
            self.groups,
            self.views,
            self.complete_groups,
        )
        return self.manifest_sha256 == sha256_json(body)


def _bank_body(
    name: str,
    features: Tensor,
    labels: Tensor,
    sectors: Tensor,
    groups: Tensor,
    views: Tensor,
    complete_groups: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "records": int(features.shape[0]),
        "feature_sha256": tensor_sha256(features),
        "label_sha256": tensor_sha256(labels),
        "sector_sha256": tensor_sha256(sectors),
        "group_sha256": tensor_sha256(groups),
        "view_sha256": tensor_sha256(views),
        "complete_groups": complete_groups,
    }


def make_bank(
    name: str,
    rows: Sequence[tuple[Tensor, int, int, int, int]],
    *,
    complete_groups: bool,
) -> OrbitBank:
    if not rows:
        raise PairedOrbitError("orbit bank cannot be empty")
    features = torch.stack([row[0] for row in rows]).to(torch.float32)
    labels = torch.tensor([row[1] for row in rows], dtype=torch.int64)
    sectors = torch.tensor([row[2] for row in rows], dtype=torch.int64)
    groups = torch.tensor([row[3] for row in rows], dtype=torch.int64)
    views = torch.tensor([row[4] for row in rows], dtype=torch.int64)
    body = _bank_body(name, features, labels, sectors, groups, views, complete_groups)
    result = OrbitBank(
        name,
        features,
        labels,
        sectors,
        groups,
        views,
        complete_groups,
        sha256_json(body),
    )
    if not result.verify():
        raise PairedOrbitError(f"{name} failed its own receipt")
    return result


def _collect_rows(
    provider: DataProvider,
    sandbox: Any,
    *,
    count: int,
    held_sector: int,
    include_held: bool,
    seed: int,
    view: int,
) -> list[tuple[Tensor, int, int, int, int]]:
    rng = random.Random(seed)
    rows: list[tuple[Tensor, int, int, int, int]] = []
    attempts = 0
    while len(rows) < count and attempts < count * 96:
        attempts += 1
        state = provider.sample_state(sandbox, rng)
        feature, label, sector = provider.materialize(sandbox, state)
        if (sector == held_sector) != include_held:
            continue
        rows.append((feature, label, sector, len(rows), view))
    if len(rows) != count:
        raise PairedOrbitError("could not fill a declared data split")
    return rows


def build_data_arms(
    provider: DataProvider,
    *,
    held_sector: int,
    orbit_count: int,
    seed: int,
) -> dict[str, OrbitBank]:
    """Build equal-row controls and paired three-view state orbits."""

    if orbit_count < 1 or held_sector not in range(8):
        raise PairedOrbitError("orbit count and held sector must be valid")
    sandboxes = provider.training_sandboxes()
    total = orbit_count * VIEW_COUNT

    static_unique_rows = _collect_rows(
        provider,
        sandboxes[0],
        count=total,
        held_sector=held_sector,
        include_held=False,
        seed=seed + 11,
        view=0,
    )
    independent_rows: list[tuple[Tensor, int, int, int, int]] = []
    for view, sandbox in enumerate(sandboxes):
        rows = _collect_rows(
            provider,
            sandbox,
            count=orbit_count,
            held_sector=held_sector,
            include_held=False,
            seed=seed + 101 * (view + 1),
            view=view,
        )
        independent_rows.extend(
            (feature, label, sector, group + view * orbit_count, view)
            for feature, label, sector, group, _ in rows
        )

    rng = random.Random(seed + 1009)
    paired_rows: list[tuple[Tensor, int, int, int, int]] = []
    canonical_rows: list[tuple[Tensor, int, int, int, int]] = []
    attempts = 0
    while len(canonical_rows) < orbit_count and attempts < orbit_count * 192:
        attempts += 1
        state = provider.sample_state(sandboxes[0], rng)
        views = [provider.materialize(sandbox, state) for sandbox in sandboxes]
        if any(sector == held_sector for _, _, sector in views):
            continue
        group = len(canonical_rows)
        for view, (feature, label, sector) in enumerate(views):
            paired_rows.append((feature, label, sector, group, view))
        feature, label, sector = views[0]
        canonical_rows.append((feature, label, sector, group, 0))
    if len(canonical_rows) != orbit_count:
        raise PairedOrbitError("could not fill complete paired state orbits")

    repeated_rows = [
        (feature.clone(), label, sector, group, repeat)
        for feature, label, sector, group, _ in canonical_rows
        for repeat in range(VIEW_COUNT)
    ]
    banks = {
        "static_unique": make_bank(
            "static_unique", static_unique_rows, complete_groups=False
        ),
        "static_repeated": make_bank(
            "static_repeated", repeated_rows, complete_groups=True
        ),
        "curriculum_independent": make_bank(
            "curriculum_independent", independent_rows, complete_groups=False
        ),
        "paired_orbit_shuffled": make_bank(
            "paired_orbit_shuffled", paired_rows, complete_groups=True
        ),
        "paired_orbit_grouped": make_bank(
            "paired_orbit_grouped", paired_rows, complete_groups=True
        ),
    }
    if any(bank.features.shape[0] != total for bank in banks.values()):
        raise PairedOrbitError("matched data arms changed row count")
    if (
        banks["paired_orbit_shuffled"].manifest_sha256
        == banks["paired_orbit_grouped"].manifest_sha256
    ):
        # The tensor data is intentionally exact; only the training sampler differs.
        pass
    return banks


def build_evaluation_banks(
    provider: DataProvider,
    *,
    held_sector: int,
    count: int,
    seed: int,
) -> tuple[OrbitBank, OrbitBank]:
    training = provider.training_sandboxes()[0]
    holdout = provider.holdout_sandbox()
    held_rows = _collect_rows(
        provider,
        holdout,
        count=count,
        held_sector=held_sector,
        include_held=True,
        seed=seed + 2003,
        view=0,
    )
    anchor_rows = _collect_rows(
        provider,
        training,
        count=count,
        held_sector=held_sector,
        include_held=False,
        seed=seed + 3001,
        view=0,
    )
    return (
        make_bank("holdout", held_rows, complete_groups=False),
        make_bank("anchor", anchor_rows, complete_groups=False),
    )


class StandardActionMLP(nn.Module):
    """Ordinary matched learner used to isolate the data intervention."""

    def __init__(self, hidden_width: int = 64) -> None:
        super().__init__()
        self.input_layer = nn.Linear(FEATURE_WIDTH, hidden_width)
        self.hidden_layer = nn.Linear(hidden_width, hidden_width)
        self.output_layer = nn.Linear(hidden_width, ACTION_COUNT)

    def forward(self, features: Tensor) -> Tensor:
        hidden = F.gelu(self.input_layer(features))
        hidden = F.gelu(self.hidden_layer(hidden))
        return self.output_layer(hidden)


def _metrics(
    logits: Tensor, labels: Tensor, *, min_stable_support: int = 1
) -> dict[str, Any]:
    if min_stable_support < 1:
        raise PairedOrbitError("minimum stable class support must be positive")
    probabilities = F.softmax(logits, dim=-1)
    predictions = probabilities.argmax(dim=-1)
    confusion = torch.zeros((ACTION_COUNT, ACTION_COUNT), dtype=torch.int64)
    for truth, predicted in zip(labels.cpu(), predictions.cpu(), strict=True):
        confusion[int(truth), int(predicted)] += 1
    per_class: list[float | None] = []
    supported_f1: list[float] = []
    stable_f1: list[float] = []
    stable_accuracy: list[float] = []
    all_f1: list[float] = []
    absent_classes: list[int] = []
    sparse_classes: list[int] = []
    class_support: list[int] = []
    for index in range(ACTION_COUNT):
        true_positive = int(confusion[index, index])
        support = int(confusion[index].sum())
        class_support.append(support)
        predicted = int(confusion[:, index].sum())
        if support:
            per_class.append(true_positive / support)
        else:
            per_class.append(None)
            absent_classes.append(index)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        all_f1.append(f1)
        if support:
            supported_f1.append(f1)
        if support >= min_stable_support:
            stable_f1.append(f1)
            stable_accuracy.append(true_positive / support)
        elif support:
            sparse_classes.append(index)
    supported_accuracy = [value for value in per_class if value is not None]
    if not stable_f1:
        raise PairedOrbitError(
            "evaluation has no class at the stable support threshold"
        )
    return {
        "accuracy": float((predictions == labels).to(torch.float64).mean().item()),
        "macro_f1": statistics.fmean(supported_f1),
        "full_action_macro_f1": statistics.fmean(all_f1),
        "stable_macro_f1": statistics.fmean(stable_f1),
        "worst_class_accuracy": min(supported_accuracy),
        "worst_stable_class_accuracy": min(stable_accuracy),
        "cross_entropy": float(F.cross_entropy(logits, labels).item()),
        "per_class_accuracy": per_class,
        "supported_class_count": len(supported_accuracy),
        "stable_class_count": len(stable_f1),
        "stable_class_support_threshold": min_stable_support,
        "class_support": class_support,
        "absent_true_classes": absent_classes,
        "sparse_true_classes": sparse_classes,
        "predictions_into_absent_classes": int(
            confusion[:, absent_classes].sum().item() if absent_classes else 0
        ),
        "confusion": confusion.tolist(),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    bank: OrbitBank,
    device: torch.device,
    *,
    min_stable_support: int = 1,
) -> dict[str, Any]:
    model.eval()
    logits: list[Tensor] = []
    for chunk in bank.features.split(2048):
        logits.append(model(chunk.to(device)).cpu())
    return _metrics(
        torch.cat(logits), bank.labels, min_stable_support=min_stable_support
    )


def _group_matrix(bank: OrbitBank) -> Tensor:
    if not bank.complete_groups:
        raise PairedOrbitError("grouped sampler requires complete orbit groups")
    groups = int(bank.groups.max().item()) + 1
    matrix = torch.empty((groups, VIEW_COUNT), dtype=torch.int64)
    for group in range(groups):
        rows = torch.nonzero(bank.groups == group, as_tuple=False).flatten()
        for row in rows:
            matrix[group, int(bank.views[row])] = row
    return matrix


def _sample_indices(
    bank: OrbitBank,
    arm: str,
    batch_size: int,
    generator: torch.Generator,
    group_matrix: Tensor | None = None,
) -> Tensor:
    if arm == "paired_orbit_grouped":
        if batch_size % VIEW_COUNT:
            raise PairedOrbitError("grouped batch size must be divisible by three")
        matrix = group_matrix if group_matrix is not None else _group_matrix(bank)
        groups = torch.randint(
            0, matrix.shape[0], (batch_size // VIEW_COUNT,), generator=generator
        )
        return matrix[groups].reshape(-1)
    return torch.randint(0, bank.features.shape[0], (batch_size,), generator=generator)


def _clone_state(model: nn.Module) -> dict[str, Tensor]:
    return {
        name: value.detach().cpu().clone() for name, value in model.state_dict().items()
    }


def _weight_effect(
    initial: Mapping[str, Tensor], final: Mapping[str, Tensor]
) -> dict[str, Any]:
    changed = 0
    total = 0
    squared = 0.0
    for name in initial:
        delta = final[name].to(torch.float64) - initial[name].to(torch.float64)
        changed += int(torch.count_nonzero(delta).item())
        total += delta.numel()
        squared += float(torch.sum(delta * delta).item())
    return {
        "changed_scalars": changed,
        "total_scalars": total,
        "changed_ratio": changed / total,
        "l2_drift": math.sqrt(squared),
    }


def gradient_coherence(
    model: nn.Module,
    paired_bank: OrbitBank,
    *,
    device: torch.device,
    groups: int = 64,
) -> dict[str, Any]:
    """Cosine alignment of gradients from the three views of the same states."""

    matrix = _group_matrix(paired_bank)[:groups]
    vectors: list[Tensor] = []
    model.train()
    for view in range(VIEW_COUNT):
        model.zero_grad(set_to_none=True)
        indices = matrix[:, view]
        logits = model(paired_bank.features[indices].to(device))
        loss = F.cross_entropy(logits, paired_bank.labels[indices].to(device))
        loss.backward()
        vector = torch.cat(
            [
                parameter.grad.detach().flatten()
                for parameter in model.parameters()
                if parameter.grad is not None
            ]
        )
        vectors.append(vector)
    cosines = [
        float(F.cosine_similarity(vectors[left], vectors[right], dim=0).item())
        for left in range(VIEW_COUNT)
        for right in range(left + 1, VIEW_COUNT)
    ]
    model.zero_grad(set_to_none=True)
    return {
        "groups": int(matrix.shape[0]),
        "pair_cosines": cosines,
        "mean_cosine": statistics.fmean(cosines),
        "min_cosine": min(cosines),
    }


def train_horse(
    root: Path,
    *,
    held_sector: int,
    arm: str,
    seed: int,
    bank: OrbitBank,
    paired_probe: OrbitBank,
    holdout: OrbitBank,
    anchor: OrbitBank,
    steps: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    log_every: int,
    hidden_width: int,
    device: torch.device,
    evaluation_min_class_support: int,
) -> dict[str, Any]:
    horse = root / "horses" / f"held-{held_sector}" / f"{arm}-seed-{seed}"
    result_path = horse / "RESULT.json"
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
    horse.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    model = StandardActionMLP(hidden_width).to(device)
    initial = _clone_state(model)
    initial_hash = state_dict_sha256(initial)
    initial_coherence = gradient_coherence(model, paired_probe, device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(held_sector * 1_000_000 + seed)
    features = bank.features.to(device)
    labels = bank.labels.to(device)
    group_matrix = _group_matrix(bank) if arm == "paired_orbit_grouped" else None

    best_state = _clone_state(model)
    best_anchor = evaluate(
        model,
        anchor,
        device,
        min_stable_support=evaluation_min_class_support,
    )
    best_step = 0
    trace: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(1, steps + 1):
        indices = _sample_indices(
            bank, arm, batch_size, generator, group_matrix=group_matrix
        ).to(device)
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(model(features[indices]), labels[indices])
        loss.backward()
        gradient_norm = float(
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0).item()
        )
        optimizer.step()
        if step % log_every == 0 or step == steps:
            anchor_metrics = evaluate(
                model,
                anchor,
                device,
                min_stable_support=evaluation_min_class_support,
            )
            score = (
                anchor_metrics["macro_f1"],
                anchor_metrics["accuracy"],
                -anchor_metrics["cross_entropy"],
            )
            best_score = (
                best_anchor["macro_f1"],
                best_anchor["accuracy"],
                -best_anchor["cross_entropy"],
            )
            if score > best_score:
                best_anchor = anchor_metrics
                best_state = _clone_state(model)
                best_step = step
            trace.append(
                {
                    "step": step,
                    "train_loss": float(loss.item()),
                    "gradient_norm": gradient_norm,
                    "anchor_accuracy": anchor_metrics["accuracy"],
                    "anchor_macro_f1": anchor_metrics["macro_f1"],
                }
            )

    final_state = _clone_state(model)
    model.load_state_dict(best_state, strict=True)
    holdout_metrics = evaluate(
        model,
        holdout,
        device,
        min_stable_support=evaluation_min_class_support,
    )
    selected_anchor = evaluate(
        model,
        anchor,
        device,
        min_stable_support=evaluation_min_class_support,
    )
    final_coherence = gradient_coherence(model, paired_probe, device=device)
    _atomic_torch(horse / "INITIAL.pt", initial)
    _atomic_torch(horse / "BEST.pt", best_state)
    _atomic_torch(horse / "FINAL.pt", final_state)
    body: dict[str, Any] = {
        "schema": "clay.paired-orbit-horse.v2",
        "held_sector": held_sector,
        "arm": arm,
        "seed": seed,
        "steps": steps,
        "batch_size": batch_size,
        "trainable_parameters": sum(
            parameter.numel() for parameter in model.parameters()
        ),
        "data_manifest_sha256": bank.manifest_sha256,
        "initial_weight_sha256": initial_hash,
        "best_weight_sha256": state_dict_sha256(best_state),
        "final_weight_sha256": state_dict_sha256(final_state),
        "best_step": best_step,
        "holdout": holdout_metrics,
        "anchor": selected_anchor,
        "initial_gradient_coherence": initial_coherence,
        "selected_gradient_coherence": final_coherence,
        "weight_effect": _weight_effect(initial, best_state),
        "final_weight_effect": _weight_effect(initial, final_state),
        "trace": trace,
        "elapsed_seconds": time.perf_counter() - started,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    result = {**body, "result_sha256": sha256_json(body)}
    _atomic_json(result_path, result)
    return result


def _mean_sd(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def _two_pooled_sd(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2 or len(right) < 2:
        return None
    pooled = math.sqrt((statistics.variance(left) + statistics.variance(right)) / 2.0)
    return 2.0 * pooled


def aggregate(
    horses: Sequence[Mapping[str, Any]],
    *,
    arms: Sequence[str] = ARMS,
    primary_arm: str = PRIMARY_ARM,
    controls: Sequence[str] = CONTROLS,
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in arms:
        rows = [row for row in horses if row["arm"] == arm]
        if not rows:
            raise PairedOrbitError(f"arm has no completed horses: {arm}")
        # Flattening names keeps the market writer compact and avoids hiding split zeros.
        summary[arm] = {
            f"{split}_{metric}": _mean_sd([float(row[split][metric]) for row in rows])
            for split in ("holdout", "anchor")
            for metric in (
                "accuracy",
                "macro_f1",
                "stable_macro_f1",
                "worst_class_accuracy",
                "worst_stable_class_accuracy",
                "cross_entropy",
            )
        }
        summary[arm]["gradient_coherence"] = _mean_sd(
            [float(row["selected_gradient_coherence"]["mean_cosine"]) for row in rows]
        )
        summary[arm]["weight_l2_drift"] = _mean_sd(
            [float(row["weight_effect"]["l2_drift"]) for row in rows]
        )

    comparisons: dict[str, Any] = {}
    candidate_rows = [row for row in horses if row["arm"] == primary_arm]
    for control in controls:
        control_rows = [row for row in horses if row["arm"] == control]
        metrics: dict[str, Any] = {}
        for metric in (
            "accuracy",
            "macro_f1",
            "stable_macro_f1",
            "worst_class_accuracy",
            "worst_stable_class_accuracy",
        ):
            candidate = [float(row["holdout"][metric]) for row in candidate_rows]
            baseline = [float(row["holdout"][metric]) for row in control_rows]
            threshold = _two_pooled_sd(candidate, baseline)
            delta = statistics.fmean(candidate) - statistics.fmean(baseline)
            metrics[metric] = {
                "delta": delta,
                "two_pooled_sd": threshold,
                "clears_noise_gate": threshold is not None and delta > threshold,
            }
        anchor_candidate = statistics.fmean(
            float(row["anchor"]["accuracy"]) for row in candidate_rows
        )
        anchor_control = statistics.fmean(
            float(row["anchor"]["accuracy"]) for row in control_rows
        )
        comparisons[control] = {
            "holdout": metrics,
            "anchor_accuracy_delta": anchor_candidate - anchor_control,
            "retention_within_two_points": anchor_candidate >= anchor_control - 0.02,
        }

    fully_powered = all(
        comparison["holdout"][metric]["clears_noise_gate"]
        for comparison in comparisons.values()
        for metric in ("accuracy", "stable_macro_f1")
    )
    retained = all(
        comparison["retention_within_two_points"] for comparison in comparisons.values()
    )
    signal_name = (
        "PAIRED_ORBIT_DATA_SIGNAL"
        if primary_arm == PRIMARY_ARM
        else f"{primary_arm.upper()}_DATA_SIGNAL"
    )
    verdict = signal_name if fully_powered and retained else "NO_SELECTION"
    return {
        "primary_arm": primary_arm,
        "controls": list(controls),
        "arms": summary,
        "comparisons": comparisons,
        "verdict": verdict,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


def _save_bank(path: Path, bank: OrbitBank) -> None:
    _atomic_torch(
        path,
        {
            "features": bank.features,
            "labels": bank.labels,
            "sectors": bank.sectors,
            "groups": bank.groups,
            "views": bank.views,
            "complete_groups": bank.complete_groups,
            "manifest_sha256": bank.manifest_sha256,
        },
    )


def render_market(result: Mapping[str, Any]) -> str:
    lines = [
        "# Paired Concept-Orbit Data Market",
        "",
        f"Verdict: `{result['aggregate']['verdict']}`",
        "",
        "| Data arm | Holdout acc | All-supported F1 | Stable F1 | Worst stable | Anchor acc | Gradient cosine | Weight drift |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in result["configuration"]["arms"]:
        row = result["aggregate"]["arms"][arm]
        lines.append(
            f"| {arm} | {row['holdout_accuracy']['mean']:.4f} | "
            f"{row['holdout_macro_f1']['mean']:.4f} | "
            f"{row['holdout_stable_macro_f1']['mean']:.4f} | "
            f"{row['holdout_worst_stable_class_accuracy']['mean']:.4f} | "
            f"{row['anchor_accuracy']['mean']:.4f} | "
            f"{row['gradient_coherence']['mean']:.4f} | "
            f"{row['weight_l2_drift']['mean']:.4f} |"
        )
    lines.extend(
        (
            "",
            "The same standard MLP and budget were used for every arm. The diagonal",
            "holdout never entered training or checkpoint selection. No model is promoted",
            "or partially unfrozen by this mechanics campaign.",
            "",
        )
    )
    return "\n".join(lines)


def run_campaign(
    output: str | Path,
    provider: DataProvider,
    *,
    seeds: Sequence[int] = (11, 29, 47),
    held_sectors: Sequence[int] = (1, 4, 7),
    orbit_count: int = 2666,
    evaluation_records: int = 1000,
    steps: int = 1200,
    batch_size: int = 192,
    learning_rate: float = 0.001,
    weight_decay: float = 0.0001,
    log_every: int = 100,
    hidden_width: int = 64,
    device_name: str = "auto",
    arms: Sequence[str] = ARMS,
    primary_arm: str = PRIMARY_ARM,
    controls: Sequence[str] | None = None,
    data_seed_offset: int = 0,
    evaluation_min_class_support: int = 1,
) -> dict[str, Any]:
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if len(seeds) < 1 or len(held_sectors) < 1:
        raise PairedOrbitError("campaign needs seeds and held sectors")
    if batch_size % VIEW_COUNT:
        raise PairedOrbitError("batch size must be divisible by three")
    if evaluation_min_class_support < 1:
        raise PairedOrbitError("evaluation minimum class support must be positive")
    selected_arms = tuple(dict.fromkeys(arms))
    if not selected_arms or any(arm not in ARMS for arm in selected_arms):
        raise PairedOrbitError("campaign arms must be a non-empty subset of ARMS")
    if primary_arm not in selected_arms:
        raise PairedOrbitError("primary arm must be included in campaign arms")
    selected_controls = tuple(
        controls
        if controls is not None
        else (arm for arm in selected_arms if arm != primary_arm)
    )
    if (
        not selected_controls
        or any(control not in selected_arms for control in selected_controls)
        or primary_arm in selected_controls
    ):
        raise PairedOrbitError("controls must be non-primary selected arms")
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    configuration = {
        "arms": list(selected_arms),
        "primary_arm": primary_arm,
        "controls": list(selected_controls),
        "data_seed_offset": data_seed_offset,
        "evaluation_min_class_support": evaluation_min_class_support,
        "seeds": list(seeds),
        "held_sectors": list(held_sectors),
        "orbit_count": orbit_count,
        "records_per_arm": orbit_count * VIEW_COUNT,
        "evaluation_records": evaluation_records,
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "log_every": log_every,
        "hidden_width": hidden_width,
        "device": str(device),
    }
    campaign_body = {
        "schema": SCHEMA,
        "created_at_utc": utc_now(),
        "configuration": configuration,
        "implementation_sha256": {"module": file_sha256(Path(__file__))},
        "source_hashes": dict(provider.source_hashes),
        "standard_control": "static_unique",
        "primary_arm": primary_arm,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    campaign = {**campaign_body, "campaign_sha256": sha256_json(campaign_body)}
    campaign_path = root / "CAMPAIGN.json"
    if campaign_path.is_file():
        existing = json.loads(campaign_path.read_text(encoding="utf-8"))
        comparable = dict(existing)
        comparable.pop("created_at_utc", None)
        comparable.pop("campaign_sha256", None)
        expected = dict(campaign)
        expected.pop("created_at_utc", None)
        expected.pop("campaign_sha256", None)
        if comparable != expected:
            raise PairedOrbitError("existing campaign configuration differs")
        campaign = existing
    else:
        _atomic_json(campaign_path, campaign)

    data_manifests: dict[str, Any] = {}
    fold_data: dict[int, tuple[dict[str, OrbitBank], OrbitBank, OrbitBank]] = {}
    for held in held_sectors:
        data_seed = 2026111300 + held + data_seed_offset
        banks = build_data_arms(
            provider, held_sector=held, orbit_count=orbit_count, seed=data_seed
        )
        holdout, anchor = build_evaluation_banks(
            provider,
            held_sector=held,
            count=evaluation_records,
            seed=data_seed,
        )
        folder = root / "inputs" / f"held-{held}"
        for name, bank in {**banks, "holdout": holdout, "anchor": anchor}.items():
            path = folder / f"{name}.pt"
            if not path.is_file():
                _save_bank(path, bank)
        data_manifests[str(held)] = {
            name: bank.manifest_sha256
            for name, bank in {**banks, "holdout": holdout, "anchor": anchor}.items()
        }
        fold_data[held] = (banks, holdout, anchor)
    _atomic_json(root / "DATASET_MANIFESTS.json", data_manifests)

    horses: list[dict[str, Any]] = []
    total = len(held_sectors) * len(selected_arms) * len(seeds)
    for held in held_sectors:
        banks, holdout, anchor = fold_data[held]
        for arm in selected_arms:
            for seed in seeds:
                active = {
                    "schema": "clay.paired-orbit-active.v1",
                    "updated_at_utc": utc_now(),
                    "completed": len(horses),
                    "total": total,
                    "held_sector": held,
                    "arm": arm,
                    "seed": seed,
                }
                _atomic_json(root / "ACTIVE_HORSE.json", active)
                horses.append(
                    train_horse(
                        root,
                        held_sector=held,
                        arm=arm,
                        seed=seed,
                        bank=banks[arm],
                        paired_probe=banks["paired_orbit_grouped"],
                        holdout=holdout,
                        anchor=anchor,
                        steps=steps,
                        batch_size=batch_size,
                        learning_rate=learning_rate,
                        weight_decay=weight_decay,
                        log_every=log_every,
                        hidden_width=hidden_width,
                        device=device,
                        evaluation_min_class_support=evaluation_min_class_support,
                    )
                )
                _atomic_json(
                    root / "STATUS.json",
                    {
                        "schema": "clay.paired-orbit-status.v1",
                        "updated_at_utc": utc_now(),
                        "state": "RUNNING",
                        "completed": len(horses),
                        "total": total,
                        "promotion_authorized": False,
                    },
                )

    aggregate_result = aggregate(
        horses,
        arms=selected_arms,
        primary_arm=primary_arm,
        controls=selected_controls,
    )
    body = {
        "schema": SCHEMA,
        "campaign_sha256": campaign["campaign_sha256"],
        "state": "COMPLETE_MECHANICS_NO_PROMOTION",
        "configuration": configuration,
        "dataset_manifests": data_manifests,
        "horses": horses,
        "aggregate": aggregate_result,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    result = {**body, "result_sha256": sha256_json(body)}
    _atomic_json(root / "RESULT.json", result)
    _atomic_text(root / "MARKET_REPORT.md", render_market(result))
    _atomic_json(
        root / "STATUS.json",
        {
            "schema": "clay.paired-orbit-status.v1",
            "updated_at_utc": utc_now(),
            "state": result["state"],
            "completed": total,
            "total": total,
            "verdict": aggregate_result["verdict"],
            "result_sha256": result["result_sha256"],
            "promotion_authorized": False,
        },
    )
    return result


__all__ = [
    "ACTION_COUNT",
    "ARMS",
    "CONTROLS",
    "ClaySourceAdapter",
    "DataProvider",
    "FEATURE_WIDTH",
    "OrbitBank",
    "PRIMARY_ARM",
    "PairedOrbitError",
    "SCHEMA",
    "StandardActionMLP",
    "aggregate",
    "build_data_arms",
    "build_evaluation_banks",
    "canonical_json",
    "evaluate",
    "gradient_coherence",
    "make_bank",
    "render_market",
    "run_campaign",
    "sha256_json",
    "state_dict_sha256",
    "tensor_sha256",
    "train_horse",
]
