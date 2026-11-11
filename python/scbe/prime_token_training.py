"""Fail-closed training mechanics for frozen prime-token input access.

This module can optimize only the small reader.  Material use requires both a
passing release audit and a separate human authorization receipt.  Checkpoints
contain adapter, optimizer, sampler, and RNG state in a hash-checked two-slot
lineage.  Existing parent or descendant weights are never overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import random
from typing import Callable, Final, Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as F

from .prime_token_input_access import (
    FullSystemPrimeTokenInputAccessLM,
    SealedPrimeTokenBatch,
)

CHECKPOINT_SCHEMA: Final = "scbe.prime-token-reader-checkpoint.v1"
POINTER_SCHEMA: Final = "scbe.prime-token-reader-pointer.v1"
AUTHORIZATION_SCHEMA: Final = "scbe.prime-token-material-authorization.v1"
AUDIT_SCHEMA: Final = "scbe.prime-token-frozen-input-access-release-audit.v1"


class MaterialReleaseError(RuntimeError):
    """Raised when a material run lacks its two independent release gates."""


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: str | Path, value: Mapping[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name(f".{target.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(pending, target)


def module_state_sha256(module: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(value.dtype).encode("ascii") + b"\0")
        digest.update(str(tuple(value.shape)).encode("ascii") + b"\0")
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def admit_material_launch(
    audit_path: str | Path,
    authorization_path: str | Path,
) -> dict[str, object]:
    """Require a passing machine audit and a separate human release receipt."""

    audit_file = Path(audit_path).resolve(strict=True)
    authorization_file = Path(authorization_path).resolve(strict=True)
    audit = json.loads(audit_file.read_text(encoding="utf-8"))
    authorization = json.loads(authorization_file.read_text(encoding="utf-8"))
    if audit.get("schema") != AUDIT_SCHEMA:
        raise MaterialReleaseError("release audit schema differs")
    if audit.get("status") != "READY_FOR_MANUAL_TRAINING_RELEASE_REVIEW":
        raise MaterialReleaseError("release audit has not cleared every prerequisite")
    if audit.get("error_count") != 0 or audit.get("blocker_count") != 0:
        raise MaterialReleaseError("release audit still reports errors or blockers")
    if authorization.get("schema") != AUTHORIZATION_SCHEMA:
        raise MaterialReleaseError("material authorization schema differs")
    if authorization.get("status") != "AUTHORIZED_FOR_MATERIAL_TRAINING":
        raise MaterialReleaseError("human material authorization is absent")
    if authorization.get("contract_id") != audit.get("contract_id"):
        raise MaterialReleaseError("authorization targets another release contract")
    if authorization.get("audit_sha256") != sha256_file(audit_file):
        raise MaterialReleaseError("authorization is not bound to this audit file")
    actor = authorization.get("authorized_by")
    if not isinstance(actor, str) or not actor.strip():
        raise MaterialReleaseError("authorization does not identify its human actor")
    if authorization.get("tool_dispatch") is not False:
        raise MaterialReleaseError("authorization must keep tool dispatch disabled")
    if authorization.get("partial_unfreeze") != "NONE":
        raise MaterialReleaseError("authorization must keep partial unfreeze closed")
    return {
        "audit": str(audit_file),
        "audit_sha256": sha256_file(audit_file),
        "authorization": str(authorization_file),
        "authorization_sha256": sha256_file(authorization_file),
        "contract_id": audit["contract_id"],
        "authorized_by": actor,
        "tool_dispatch": False,
        "partial_unfreeze": "NONE",
    }


@dataclass(frozen=True, slots=True)
class PrimeTrainingExample:
    record_ids: tuple[str, ...]
    splits: tuple[str, ...]
    source_families: tuple[str, ...]
    token_ids: Tensor
    targets: Tensor
    weights: Tensor
    packet: SealedPrimeTokenBatch
    output_positions: tuple[tuple[int, ...], ...]
    allowed_output_token_ids: tuple[int, ...]
    exact_evaluator_receipt_sha256: str
    task_kind: str = "bounded_route_or_function_token"

    def validate(self) -> None:
        self.packet.validate()
        if self.token_ids.ndim != 2 or self.token_ids.dtype != torch.long:
            raise ValueError("example token IDs must be torch.long [batch,time]")
        if self.targets.shape != self.token_ids.shape:
            raise ValueError("example targets differ from token IDs")
        if self.targets.dtype != torch.long:
            raise ValueError("example targets must use torch.long")
        if self.weights.shape != self.token_ids.shape:
            raise ValueError("example weights differ from token IDs")
        if not torch.is_floating_point(self.weights) or not torch.all(
            torch.isfinite(self.weights)
        ):
            raise ValueError("example weights must be finite floating-point values")
        if tuple(self.packet.owner_mask.shape) != tuple(self.token_ids.shape):
            raise ValueError("example packet differs from token IDs")
        batch_size = self.token_ids.shape[0]
        if not (
            len(self.record_ids)
            == len(self.splits)
            == len(self.source_families)
            == len(self.output_positions)
            == batch_size
        ):
            raise ValueError("example provenance rows differ from batch size")
        if not all(
            isinstance(value, str) and value.strip() for value in self.record_ids
        ) or not all(
            isinstance(value, str) and value.strip() for value in self.source_families
        ):
            raise ValueError("example record and source-family identities are required")
        if len(set(self.record_ids)) != len(self.record_ids):
            raise ValueError("example repeats a record identity")
        if any(
            split not in {"train", "validation", "final_test"} for split in self.splits
        ):
            raise ValueError("example split is invalid")
        if self.task_kind != "bounded_route_or_function_token":
            raise ValueError("example task must be a bounded route/function token")
        if len(self.exact_evaluator_receipt_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.exact_evaluator_receipt_sha256
        ):
            raise ValueError("example requires an exact evaluator receipt SHA-256")
        allowed = set(self.allowed_output_token_ids)
        if (
            not allowed
            or len(allowed) != len(self.allowed_output_token_ids)
            or any(
                isinstance(token_id, bool)
                or not isinstance(token_id, int)
                or token_id < 0
                for token_id in allowed
            )
        ):
            raise ValueError("example allowed output token IDs are invalid")
        if not torch.all((self.weights == 0) | (self.weights == 1)):
            raise ValueError("example supervision weights must be binary")
        if float(self.weights.sum()) <= 0.0:
            raise ValueError("example supervision mask is empty")
        expected_mask = torch.zeros_like(self.weights, dtype=torch.bool)
        for batch_index, positions in enumerate(self.output_positions):
            if not positions or positions != tuple(sorted(set(positions))):
                raise ValueError("example output positions must be sorted and unique")
            owner_positions = (
                self.packet.owner_mask[batch_index].nonzero().flatten().tolist()
            )
            if not owner_positions or max(owner_positions) > positions[0]:
                raise ValueError("example output precedes a required owner position")
            for position in positions:
                if position < 0 or position >= self.token_ids.shape[1]:
                    raise ValueError("example output position is out of bounds")
                expected_mask[batch_index, position] = True
                if int(self.targets[batch_index, position]) not in allowed:
                    raise ValueError(
                        "example target lies outside the bounded output set"
                    )
        if not torch.equal(self.weights.to(dtype=torch.bool), expected_mask):
            raise ValueError(
                "example supervision exists outside declared output positions"
            )


def validate_training_examples(examples: Sequence[PrimeTrainingExample]) -> None:
    """Validate one source-bounded training set before any optimizer is built."""

    if not examples:
        raise ValueError("training examples are empty")
    evaluator_receipts: set[str] = set()
    output_vocabularies: set[tuple[int, ...]] = set()
    task_kinds: set[str] = set()
    record_ids: set[str] = set()
    for example in examples:
        example.validate()
        if any(split != "train" for split in example.splits):
            raise ValueError("optimizer input contains a non-training split")
        overlap = record_ids.intersection(example.record_ids)
        if overlap:
            raise ValueError("optimizer input repeats a training record identity")
        record_ids.update(example.record_ids)
        evaluator_receipts.add(example.exact_evaluator_receipt_sha256)
        output_vocabularies.add(tuple(example.allowed_output_token_ids))
        task_kinds.add(example.task_kind)
    if len(evaluator_receipts) != 1:
        raise ValueError("training examples name different evaluator receipts")
    if len(output_vocabularies) != 1:
        raise ValueError("training examples use different bounded output vocabularies")
    if len(task_kinds) != 1:
        raise ValueError("training examples use different task kinds")


def masked_language_loss(logits: Tensor, targets: Tensor, weights: Tensor) -> Tensor:
    if logits.ndim != 3 or targets.shape != logits.shape[:2]:
        raise ValueError("logits and targets have incompatible shapes")
    if targets.dtype != torch.long or weights.shape != targets.shape:
        raise ValueError("targets or supervision weights are invalid")
    if int(targets.min()) < 0 or int(targets.max()) >= logits.shape[-1]:
        raise ValueError("target token lies outside model vocabulary")
    if not torch.all(torch.isfinite(weights)) or not torch.all(
        (weights == 0) | (weights == 1)
    ):
        raise ValueError("supervision weights must be finite binary values")
    per_token = F.cross_entropy(logits.transpose(1, 2), targets, reduction="none")
    mass = weights.sum()
    if float(mass.detach().cpu()) <= 0.0:
        raise ValueError("supervision mask is empty")
    return (per_token * weights).sum() / mass


def new_training_state(
    model: FullSystemPrimeTokenInputAccessLM,
    *,
    learning_rate: float,
    seed: int,
) -> tuple[torch.optim.Optimizer, torch.Generator]:
    if learning_rate <= 0:
        raise ValueError("learning rate must be positive")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    optimizer = torch.optim.AdamW(
        model.reader.parameters(), lr=learning_rate, weight_decay=0.0
    )
    sampler = torch.Generator(device="cpu").manual_seed(seed + 1009)
    return optimizer, sampler


def _capture_rng(sampler: torch.Generator) -> dict[str, object]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": (
            torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []
        ),
        "sampler": sampler.get_state(),
    }


def _restore_rng(state: Mapping[str, object], sampler: torch.Generator) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    if torch.cuda.is_available() and state.get("torch_cuda"):
        torch.cuda.set_rng_state_all(state["torch_cuda"])
    sampler.set_state(state["sampler"])


def _optimizer_to_device(
    optimizer: torch.optim.Optimizer, device: torch.device
) -> None:
    for state in optimizer.state.values():
        for key, value in state.items():
            if isinstance(value, Tensor):
                state[key] = value.to(device)


def save_adapter_checkpoint(
    output_dir: str | Path,
    *,
    model: FullSystemPrimeTokenInputAccessLM,
    optimizer: torch.optim.Optimizer,
    sampler: torch.Generator,
    step: int,
    save_every: int,
    identity: Mapping[str, str],
    metrics: Mapping[str, object],
) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    slot = "A" if (step // max(1, save_every)) % 2 == 0 else "B"
    target = output / f"adapter_{slot}.pt"
    pending = output / f"adapter_{slot}.pt.pending"
    payload = {
        "schema": CHECKPOINT_SCHEMA,
        "step": int(step),
        "identity": dict(identity),
        "adapter": model.adapter_state_dict(),
        "optimizer": optimizer.state_dict(),
        "rng": _capture_rng(sampler),
        "metrics": dict(metrics),
        "parent_sha256": module_state_sha256(model.core),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
        "tool_dispatch": False,
    }
    torch.save(payload, pending)
    os.replace(pending, target)
    pointer = {
        "schema": POINTER_SCHEMA,
        "slot": slot,
        "file": target.name,
        "sha256": sha256_file(target),
        "step": int(step),
        "identity_sha256": canonical_sha256(dict(identity)),
    }
    atomic_json(output / f"adapter_{slot}.json", pointer)
    atomic_json(output / "LATEST.json", pointer)
    return pointer


def load_adapter_checkpoint(
    output_dir: str | Path,
    *,
    model: FullSystemPrimeTokenInputAccessLM,
    optimizer: torch.optim.Optimizer,
    sampler: torch.Generator,
    expected_identity: Mapping[str, str],
    map_location: str | torch.device = "cpu",
) -> tuple[dict[str, object], dict[str, object]]:
    output = Path(output_dir).resolve(strict=True)
    pointer = json.loads((output / "LATEST.json").read_text(encoding="utf-8"))
    if pointer.get("schema") != POINTER_SCHEMA:
        raise RuntimeError("adapter pointer schema changed")
    target = (output / str(pointer.get("file"))).resolve(strict=True)
    if not target.is_relative_to(output) or sha256_file(target) != pointer.get(
        "sha256"
    ):
        raise RuntimeError("adapter checkpoint pointer/hash verification failed")
    payload = torch.load(target, map_location=map_location, weights_only=False)
    if payload.get("schema") != CHECKPOINT_SCHEMA:
        raise RuntimeError("adapter checkpoint schema changed")
    if payload.get("identity") != dict(expected_identity):
        raise RuntimeError("adapter checkpoint lineage identity differs")
    if pointer.get("identity_sha256") != canonical_sha256(dict(expected_identity)):
        raise RuntimeError("adapter pointer identity differs")
    if int(payload.get("step", -1)) != int(pointer.get("step", -2)):
        raise RuntimeError("adapter pointer step differs")
    if payload.get("parent_sha256") != module_state_sha256(model.core):
        raise RuntimeError("frozen parent differs from checkpoint lineage")
    model.load_adapter_state_dict(payload["adapter"])
    optimizer.load_state_dict(payload["optimizer"])
    _optimizer_to_device(optimizer, next(model.reader.parameters()).device)
    _restore_rng(payload["rng"], sampler)
    return payload, pointer


def train_steps(
    model: FullSystemPrimeTokenInputAccessLM,
    examples: Sequence[PrimeTrainingExample],
    *,
    steps: int,
    learning_rate: float,
    seed: int,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
    sampler: torch.Generator | None = None,
    start_step: int = 0,
    on_step: (
        Callable[[int, torch.optim.Optimizer, torch.Generator, dict], None] | None
    ) = None,
) -> tuple[torch.optim.Optimizer, torch.Generator, list[dict[str, object]]]:
    """Advance one reader lineage while proving the parent stayed unchanged."""

    if steps <= 0 or not examples:
        raise ValueError("training requires positive steps and non-empty examples")
    if (optimizer is None) != (sampler is None):
        raise ValueError("optimizer and sampler must be supplied together")
    validate_training_examples(examples)
    model.to(device)
    model.train()
    model.core.eval()
    model.reader.train()
    if optimizer is None or sampler is None:
        optimizer, sampler = new_training_state(
            model, learning_rate=learning_rate, seed=seed
        )
    parent_before = module_state_sha256(model.core)
    history: list[dict[str, object]] = []
    for offset in range(1, steps + 1):
        step = start_step + offset
        index = int(torch.randint(0, len(examples), (1,), generator=sampler).item())
        example = examples[index]
        optimizer.zero_grad(set_to_none=True)
        logits = model(
            example.token_ids.to(device),
            prime_packet=example.packet,
        )
        if max(example.allowed_output_token_ids) >= logits.shape[-1]:
            raise ValueError("allowed output token exceeds model vocabulary")
        loss = masked_language_loss(
            logits,
            example.targets.to(device),
            example.weights.to(device),
        )
        if not bool(torch.isfinite(loss).item()):
            raise RuntimeError("prime-token reader produced non-finite loss")
        loss.backward()
        if any(parameter.grad is not None for parameter in model.core.parameters()):
            raise RuntimeError("frozen full-system parent received a gradient")
        grad_norm = torch.nn.utils.clip_grad_norm_(model.reader.parameters(), 1.0)
        optimizer.step()
        if module_state_sha256(model.core) != parent_before:
            raise RuntimeError("frozen parent changed during reader training")
        metrics = {
            "step": step,
            "example_index": index,
            "loss": float(loss.detach().cpu()),
            "gradient_norm": float(grad_norm.detach().cpu()),
            "parent_sha256": parent_before,
        }
        history.append(metrics)
        if on_step is not None:
            on_step(step, optimizer, sampler, metrics)
    return optimizer, sampler, history


__all__ = [
    "AUDIT_SCHEMA",
    "AUTHORIZATION_SCHEMA",
    "CHECKPOINT_SCHEMA",
    "MaterialReleaseError",
    "POINTER_SCHEMA",
    "PrimeTrainingExample",
    "admit_material_launch",
    "atomic_json",
    "canonical_sha256",
    "load_adapter_checkpoint",
    "masked_language_loss",
    "module_state_sha256",
    "new_training_state",
    "save_adapter_checkpoint",
    "sha256_file",
    "train_steps",
    "validate_training_examples",
]
