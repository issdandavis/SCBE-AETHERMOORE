"""Matched ordinary-MLP A/B for bounded hidden-sector pressure.

The learned network is intentionally conventional.  Every arm uses the same
three learned linear layers and differs only by a parameter-free operation on
the first 64 hidden values, read as an 8 x 8 sector matrix.  This keeps the
standard control honest while making push, pull, reflection, and wrong-binding
controls directly measurable.

The model proposes one exact developmental action token.  The deterministic
sandbox remains the execution and reward authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable, Mapping

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from developmental_game_sandbox import ACTION_BYTES, DevelopmentalGameSandbox, ToyAction
from trit_compiled_action_policy import (
    FEATURE_NAMES,
    MOTOR_ACTIONS,
    PolicyDataset,
    holdout_sandbox,
    sample_state,
    sha256_json,
    tensor_sha256,
    training_sandbox,
    vectorize_state,
)
from trit_token_weight_bank import balanced_trits, developmental_action_tokens, file_sha256


SCHEMA = "clay.topology-sector-action-ab.v1"
DATASET_SCHEMA = "clay.topology-sector-action-dataset.v1"
TRACE_SCHEMA = "clay.topology-sector-token-pressure-trace.v1"
SECTOR_COUNT = 8
SECTOR_WIDTH = 8
HIDDEN_WIDTH = SECTOR_COUNT * SECTOR_WIDTH
SCOPE_DX_INDEX = FEATURE_NAMES.index("scope_dx")
SCOPE_DY_INDEX = FEATURE_NAMES.index("scope_dy")
REFLECTION = (0, 7, 6, 5, 4, 3, 2, 1)
IDENTITY = tuple(range(SECTOR_COUNT))
SHUFFLED_BINDING = (3, 0, 5, 2, 7, 4, 1, 6)
RANDOM_FIXED_BINDING = (6, 2, 7, 1, 4, 0, 5, 3)
PRIMARY_CANDIDATE = "inverted_push"
HELD_SECTORS = (1, 4, 7)

DEFAULT_ROUTE_PACKAGE_PARENT = Path(
    r"C:\dev\_wt_clay_e80_strict_audit_20261104\home\training"
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def bytes_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ArmConfig:
    name: str
    pressure_sign: int
    inverted: bool
    strength: float
    pulses: int
    sector_map: tuple[int, ...] = IDENTITY
    profile_sigma: float = 1.0
    exponent_limit: float = 2.0
    neighbor_coupling: float = 0.12

    def validate(self) -> None:
        if not self.name or self.pressure_sign not in {-1, 0, 1}:
            raise ValueError("arm needs a name and signed trit pressure")
        if sorted(self.sector_map) != list(range(SECTOR_COUNT)):
            raise ValueError("sector map must be a complete bijection")
        if self.strength < 0 or self.pulses < 0:
            raise ValueError("pressure strength and pulse count cannot be negative")
        if self.pressure_sign == 0 and (self.strength != 0 or self.pulses != 0):
            raise ValueError("neutral pressure must have zero strength and pulses")
        if self.pressure_sign != 0 and (self.strength <= 0 or self.pulses < 1):
            raise ValueError("non-neutral pressure needs positive strength and pulses")
        if not all(
            math.isfinite(value) and value > 0
            for value in (self.profile_sigma, self.exponent_limit)
        ):
            raise ValueError("pressure profile and exponent bound must be finite and positive")
        if not math.isfinite(self.neighbor_coupling) or not 0 <= self.neighbor_coupling <= 0.5:
            raise ValueError("neighbor coupling must stay in [0, 0.5]")


ARM_CONFIGS: dict[str, ArmConfig] = {
    "standard": ArmConfig("standard", 0, False, 0.0, 0),
    "push": ArmConfig("push", 1, False, 1.0, 2),
    "pull": ArmConfig("pull", -1, False, 1.0, 2),
    "inverted_only": ArmConfig("inverted_only", 0, True, 0.0, 0),
    "inverted_push": ArmConfig("inverted_push", 1, True, 1.0, 2),
    "inverted_pull": ArmConfig("inverted_pull", -1, True, 1.0, 2),
    "shuffled_push": ArmConfig(
        "shuffled_push", 1, False, 1.0, 2, sector_map=SHUFFLED_BINDING
    ),
    "random_fixed_push": ArmConfig(
        "random_fixed_push", 1, False, 1.0, 2, sector_map=RANDOM_FIXED_BINDING
    ),
}
for _arm_config in ARM_CONFIGS.values():
    _arm_config.validate()


def scope_sector(features: Tensor) -> Tensor:
    """Map nonzero scope vectors to one of eight centered angle sectors."""

    if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
        raise ValueError("sector routing expects [batch, declared_features]")
    dx = features[:, SCOPE_DX_INDEX]
    dy = features[:, SCOPE_DY_INDEX]
    angle = torch.remainder(torch.atan2(dy, dx), 2.0 * math.pi)
    sector_width = 2.0 * math.pi / SECTOR_COUNT
    sectors = torch.floor((angle + 0.5 * sector_width) / sector_width).long()
    return torch.remainder(sectors, SECTOR_COUNT)


def _route_sectors(raw_sectors: Tensor, config: ArmConfig) -> Tensor:
    mapping = torch.tensor(config.sector_map, dtype=torch.long, device=raw_sectors.device)
    routed = mapping[raw_sectors]
    if config.inverted:
        reflection = torch.tensor(REFLECTION, dtype=torch.long, device=raw_sectors.device)
        routed = reflection[routed]
    return routed


def _circular_profile(routed: Tensor, config: ArmConfig, dtype: torch.dtype) -> Tensor:
    positions = torch.arange(SECTOR_COUNT, device=routed.device)[None, :]
    raw_distance = (positions - routed[:, None]).abs()
    distance = torch.minimum(raw_distance, SECTOR_COUNT - raw_distance).to(dtype)
    profile = torch.exp(-0.5 * (distance / config.profile_sigma) ** 2)
    # Equal L2 energy for every rotation and every one-to-one binding control.
    return F.normalize(profile, p=2.0, dim=-1)


def apply_sector_topology(
    hidden: Tensor, features: Tensor, config: ArmConfig
) -> tuple[Tensor, dict[str, Tensor]]:
    """Reflect and pressure an 8 x 8 hidden matrix with full diagnostics."""

    config.validate()
    if hidden.ndim != 2 or hidden.shape[1] != HIDDEN_WIDTH:
        raise ValueError("topology layer expects a 64-value hidden state")
    raw_sectors = scope_sector(features)
    routed = _route_sectors(raw_sectors, config)
    matrix = hidden.reshape(-1, SECTOR_COUNT, SECTOR_WIDTH)
    before = matrix
    if config.inverted:
        reflection = torch.tensor(REFLECTION, dtype=torch.long, device=hidden.device)
        matrix = matrix[:, reflection, :]
    reflected = matrix
    profile = _circular_profile(routed, config, hidden.dtype)

    if config.pressure_sign == 0:
        warped = reflected
        exponent = torch.zeros_like(profile)
    else:
        signed_dose = config.pressure_sign * config.strength * config.pulses
        exponent = torch.clamp(
            signed_dose * profile,
            min=-config.exponent_limit,
            max=config.exponent_limit,
        )
        row_mean = reflected.mean(dim=1, keepdim=True)
        centered = reflected - row_mean
        warped = row_mean + centered * torch.exp(exponent)[:, :, None]
        neighbor_average = 0.5 * (warped.roll(1, dims=1) + warped.roll(-1, dims=1))
        mix = config.neighbor_coupling * (1.0 - torch.exp(-exponent.abs()))
        warped = (1.0 - mix[:, :, None]) * warped + mix[:, :, None] * neighbor_average

    output = warped.reshape(-1, HIDDEN_WIDTH)
    diagnostics = {
        "raw_sector": raw_sectors,
        "routed_sector": routed,
        "profile": profile,
        "exponent": exponent,
        "pre_norms": torch.linalg.vector_norm(before, dim=-1),
        "reflected_norms": torch.linalg.vector_norm(reflected, dim=-1),
        "post_norms": torch.linalg.vector_norm(warped, dim=-1),
        "displacement_l2": torch.linalg.vector_norm(output - hidden, dim=-1),
    }
    return output, diagnostics


class StandardSectorActionMLP(nn.Module):
    """An ordinary MLP with one optional parameter-free topology operation."""

    def __init__(self, arm: str) -> None:
        super().__init__()
        if arm not in ARM_CONFIGS:
            raise ValueError(f"unknown topology arm: {arm}")
        self.arm = arm
        self.config = ARM_CONFIGS[arm]
        self.input_layer = nn.Linear(len(FEATURE_NAMES), HIDDEN_WIDTH)
        self.hidden_layer = nn.Linear(HIDDEN_WIDTH, HIDDEN_WIDTH)
        self.output_layer = nn.Linear(HIDDEN_WIDTH, len(MOTOR_ACTIONS))

    def forward(self, features: Tensor, *, return_diagnostics: bool = False):
        if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
            raise ValueError("action MLP expects [batch, declared_features]")
        hidden = F.gelu(self.input_layer(features))
        warped, topology = apply_sector_topology(hidden, features, self.config)
        body = F.gelu(self.hidden_layer(warped))
        logits = self.output_layer(body)
        if return_diagnostics:
            return logits, {"input_hidden": hidden, "warped_hidden": warped, "body": body, **topology}
        return logits

    @property
    def trainable_parameters(self) -> int:
        return sum(value.numel() for value in self.parameters() if value.requires_grad)


@dataclass(frozen=True, slots=True)
class SectorDataset:
    policy: PolicyDataset
    sectors: Tensor
    held_sector: int
    include_held_sector: bool
    receipt_sha256: str

    def verify(self) -> bool:
        if not self.policy.verify() or self.sectors.shape != self.policy.labels.shape:
            return False
        if self.sectors.dtype != torch.long or bool(
            torch.any((self.sectors < 0) | (self.sectors >= SECTOR_COUNT)).item()
        ):
            return False
        if self.include_held_sector:
            if not bool(torch.all(self.sectors == self.held_sector).item()):
                return False
        elif bool(torch.any(self.sectors == self.held_sector).item()):
            return False
        body = {
            "schema": DATASET_SCHEMA,
            "policy_sha256": self.policy.tensor_sha256,
            "sectors_sha256": tensor_sha256(self.sectors),
            "held_sector": self.held_sector,
            "include_held_sector": self.include_held_sector,
        }
        return self.receipt_sha256 == sha256_json(body)


def build_sector_dataset(
    sandbox: DevelopmentalGameSandbox,
    *,
    count: int,
    seed: int,
    split: str,
    source_family: str,
    held_sector: int,
    include_held_sector: bool,
) -> SectorDataset:
    """Build a replay-stable direction-disjoint dataset."""

    if count < 1 or held_sector not in range(SECTOR_COUNT):
        raise ValueError("dataset count/held sector is invalid")
    rng = random.Random(seed)
    features: list[Tensor] = []
    labels: list[int] = []
    sectors: list[int] = []
    attempts = 0
    maximum_attempts = count * 64
    while len(features) < count and attempts < maximum_attempts:
        attempts += 1
        state = sample_state(sandbox, rng)
        feature = vectorize_state(sandbox, state)
        sector = int(scope_sector(feature[None, :])[0].item())
        selected = sector == held_sector
        if selected != include_held_sector:
            continue
        action, _ = sandbox.sieve_actions(state)
        if action.token_id >= len(MOTOR_ACTIONS):
            raise RuntimeError("exact sieve selected an action outside the motor policy")
        features.append(feature)
        labels.append(action.token_id)
        sectors.append(sector)
    if len(features) != count:
        raise RuntimeError("could not fill the direction-disjoint dataset")
    feature_tensor = torch.stack(features)
    label_tensor = torch.tensor(labels, dtype=torch.long)
    sector_tensor = torch.tensor(sectors, dtype=torch.long)
    policy_body = {
        "features": tensor_sha256(feature_tensor),
        "labels": tensor_sha256(label_tensor),
        "split": split,
        "source_family": source_family,
        "config_sha256": sha256_json(asdict(sandbox.config)),
    }
    policy = PolicyDataset(
        feature_tensor,
        label_tensor,
        split,
        source_family,
        policy_body["config_sha256"],
        sha256_json(policy_body),
    )
    body = {
        "schema": DATASET_SCHEMA,
        "policy_sha256": policy.tensor_sha256,
        "sectors_sha256": tensor_sha256(sector_tensor),
        "held_sector": held_sector,
        "include_held_sector": include_held_sector,
    }
    result = SectorDataset(
        policy,
        sector_tensor,
        held_sector,
        include_held_sector,
        sha256_json(body),
    )
    if not result.verify():
        raise RuntimeError("direction-disjoint dataset failed its own receipt")
    return result


def _action_bytes_tensor(token_ids: Tensor) -> Tensor:
    table = torch.tensor(ACTION_BYTES[: len(MOTOR_ACTIONS)], dtype=torch.long, device=token_ids.device)
    return table[token_ids]


def _bit_rows(values: Tensor) -> Tensor:
    shifts = torch.arange(7, -1, -1, device=values.device)
    return ((values[:, None] >> shifts[None, :]) & 1).long()


def _trit_rows(values: Tensor) -> Tensor:
    rows = [balanced_trits(int(value), 6) for value in values.detach().cpu().tolist()]
    return torch.tensor(rows, dtype=torch.long, device=values.device)


def evaluate_model(
    model: StandardSectorActionMLP,
    dataset: SectorDataset,
    *,
    device: torch.device,
) -> dict[str, Any]:
    if not dataset.verify():
        raise ValueError("cannot evaluate an invalid sector dataset")
    model.eval()
    with torch.no_grad():
        logits, diagnostics = model(dataset.policy.features.to(device), return_diagnostics=True)
        labels = dataset.policy.labels.to(device)
        probabilities = logits.softmax(dim=-1)
        predictions = logits.argmax(dim=-1)
        loss = F.cross_entropy(logits, labels)
        one_hot = F.one_hot(labels, num_classes=len(MOTOR_ACTIONS)).to(probabilities.dtype)
        brier = ((probabilities - one_hot) ** 2).sum(dim=-1).mean()
        confidence = probabilities.max(dim=-1).values
        accuracy = (predictions == labels).float().mean()
        ece = torch.zeros((), device=device)
        for lower in torch.linspace(0.0, 0.9, 10, device=device):
            upper = lower + 0.1
            mask = (confidence >= lower) & (
                confidence < upper if float(upper) < 1.0 else confidence <= upper
            )
            if bool(mask.any()):
                ece += mask.float().mean() * (
                    confidence[mask].mean()
                    - (predictions[mask] == labels[mask]).float().mean()
                ).abs()
        confusion = torch.zeros(
            (len(MOTOR_ACTIONS), len(MOTOR_ACTIONS)), dtype=torch.int64, device=device
        )
        for truth, predicted in zip(labels, predictions, strict=True):
            confusion[truth, predicted] += 1
        f1_values = []
        for index in range(len(MOTOR_ACTIONS)):
            tp = confusion[index, index].float()
            fp = confusion[:, index].sum().float() - tp
            fn = confusion[index, :].sum().float() - tp
            denominator = 2 * tp + fp + fn
            f1_values.append(float((2 * tp / denominator).cpu()) if denominator else 0.0)
        target_bytes = _action_bytes_tensor(labels)
        predicted_bytes = _action_bytes_tensor(predictions)
        bit_accuracy = (_bit_rows(target_bytes) == _bit_rows(predicted_bytes)).float().mean()
        trit_accuracy = (_trit_rows(target_bytes) == _trit_rows(predicted_bytes)).float().mean()
        ordered = logits.sort(dim=-1, descending=True).values
    return {
        "records": len(labels),
        "loss": float(loss.cpu()),
        "accuracy": float(accuracy.cpu()),
        "macro_f1": sum(f1_values) / len(f1_values),
        "brier": float(brier.cpu()),
        "ece": float(ece.cpu()),
        "mean_margin": float((ordered[:, 0] - ordered[:, 1]).mean().cpu()),
        "bit_accuracy": float(bit_accuracy.cpu()),
        "trit_digit_accuracy": float(trit_accuracy.cpu()),
        "mean_topology_displacement": float(diagnostics["displacement_l2"].mean().cpu()),
        "maximum_topology_displacement": float(diagnostics["displacement_l2"].max().cpu()),
        "mean_pre_sector_norms": diagnostics["pre_norms"].mean(dim=0).cpu().tolist(),
        "mean_post_sector_norms": diagnostics["post_norms"].mean(dim=0).cpu().tolist(),
        "confusion": confusion.cpu().tolist(),
        "prediction_sha256": tensor_sha256(predictions),
        "logits_sha256": tensor_sha256(logits),
    }


def weight_diagnostics(model: StandardSectorActionMLP) -> dict[str, Any]:
    input_strength = torch.linalg.vector_norm(model.input_layer.weight.detach(), dim=0)
    feature_rows = sorted(
        (
            {"feature": name, "connection_l2": float(value)}
            for name, value in zip(FEATURE_NAMES, input_strength.cpu().tolist(), strict=True)
        ),
        key=lambda row: (-row["connection_l2"], row["feature"]),
    )
    hidden_columns = model.hidden_layer.weight.detach().reshape(
        HIDDEN_WIDTH, SECTOR_COUNT, SECTOR_WIDTH
    )
    output_columns = model.output_layer.weight.detach().reshape(
        len(MOTOR_ACTIONS), SECTOR_COUNT, SECTOR_WIDTH
    )
    return {
        "trainable_parameters": model.trainable_parameters,
        "parameter_l2": {
            name: float(torch.linalg.vector_norm(value.detach()).cpu())
            for name, value in model.named_parameters()
        },
        "strongest_input_connections": feature_rows[:12],
        "hidden_input_l2_by_sector": torch.linalg.vector_norm(
            hidden_columns, dim=(0, 2)
        ).cpu().tolist(),
        "output_l2_by_sector": torch.linalg.vector_norm(
            output_columns, dim=(0, 2)
        ).cpu().tolist(),
    }


def rollout_model(
    model: StandardSectorActionMLP,
    sandbox: DevelopmentalGameSandbox,
    *,
    steps: int,
) -> dict[str, Any]:
    model = model.to("cpu")
    model.eval()
    state = sandbox.initial_state()
    previous_target = state.target_index
    target_hits = 0
    oracle_matches = 0
    reward = 0.0
    actions = {name: 0 for name in MOTOR_ACTIONS}
    with torch.no_grad():
        for _ in range(steps):
            feature = vectorize_state(sandbox, state)[None, :]
            token_id = int(model(feature).argmax(dim=-1).item())
            oracle, _ = sandbox.sieve_actions(state)
            oracle_matches += int(token_id == oracle.token_id)
            actions[MOTOR_ACTIONS[token_id]] += 1
            state, transition = sandbox.step(state, ToyAction(token_id))
            reward += float(transition.rewards["action_credit"])
            if state.target_index != previous_target:
                target_hits += 1
                previous_target = state.target_index
    return {
        "steps": steps,
        "action_credit": reward,
        "target_hits": target_hits,
        "oracle_agreement": oracle_matches / steps,
        "actions": actions,
        "final_state_sha256": state.sha256,
    }


def load_route_authority(
    package_parent: Path = DEFAULT_ROUTE_PACKAGE_PARENT,
) -> tuple[Tensor, dict[str, Any], dict[int, str]]:
    """Load the existing byte hyperpath table without copying its implementation."""

    package_root = package_parent / "full_system_pretrain"
    required = (
        package_root / "parametric_hyperpath.py",
        package_root / "route_sieve.py",
        package_root / "hyperpath_token_sieve.py",
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("existing hyperpath route authority is incomplete")
    parent_text = str(package_parent)
    if parent_text not in sys.path:
        sys.path.insert(0, parent_text)
    from full_system_pretrain.hyperpath_token_sieve import build_hyperpath_feature_table

    table, receipt = build_hyperpath_feature_table()
    action_digests = {
        byte: tensor_sha256(table[byte]) for byte in ACTION_BYTES[: len(MOTOR_ACTIONS)]
    }
    authority = {
        "receipt": asdict(receipt),
        "receipt_sha256": receipt.digest(),
        "source_files": {str(path): file_sha256(path) for path in required},
        "action_route_rows": action_digests,
    }
    return table, authority, action_digests


def token_view(token_id: int, route_digests: Mapping[int, str]) -> dict[str, Any]:
    if token_id not in range(len(MOTOR_ACTIONS)):
        raise ValueError("token ID is outside the motor policy")
    token = developmental_action_tokens()[token_id]
    byte = token.transport_byte
    return {
        "token_id": token_id,
        "name": token.name,
        "transport_byte": byte,
        "hex": f"0x{byte:02X}",
        "bits_msb_first": [int(bit) for bit in f"{byte:08b}"],
        "balanced_trits_lsd_first": list(balanced_trits(byte, 6)),
        "method_trits": list(token.method_trits),
        "route_row_sha256": route_digests[byte],
    }


def write_token_pressure_trace(
    path: Path,
    model: StandardSectorActionMLP,
    dataset: SectorDataset,
    route_digests: Mapping[int, str],
    *,
    device: torch.device,
) -> dict[str, Any]:
    """Write every held example as a compressed, byte-exact diagnostic row."""

    if not dataset.verify():
        raise ValueError("trace dataset receipt failed")
    path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    with torch.no_grad():
        features = dataset.policy.features.to(device)
        logits, diagnostics = model(features, return_diagnostics=True)
        predictions = logits.argmax(dim=-1).cpu()
    cpu_logits = logits.cpu()
    diagnostics = {name: value.cpu() for name, value in diagnostics.items() if isinstance(value, Tensor)}
    config = model.config
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for index in range(len(dataset.policy.labels)):
            feature = dataset.policy.features[index]
            target_id = int(dataset.policy.labels[index])
            predicted_id = int(predictions[index])
            row = {
                "schema": TRACE_SCHEMA,
                "index": index,
                "arm": model.arm,
                "feature_sha256": tensor_sha256(feature),
                "scope": {
                    "dx": float(feature[SCOPE_DX_INDEX]),
                    "dy": float(feature[SCOPE_DY_INDEX]),
                    "raw_sector": int(diagnostics["raw_sector"][index]),
                    "routed_sector": int(diagnostics["routed_sector"][index]),
                    "orientation": -1 if config.inverted else 1,
                },
                "pressure": {
                    "trit": config.pressure_sign,
                    "strength": config.strength,
                    "pulses": config.pulses,
                    "profile": diagnostics["profile"][index].tolist(),
                    "exponent": diagnostics["exponent"][index].tolist(),
                    "pre_sector_norms": diagnostics["pre_norms"][index].tolist(),
                    "reflected_sector_norms": diagnostics["reflected_norms"][index].tolist(),
                    "post_sector_norms": diagnostics["post_norms"][index].tolist(),
                    "displacement_l2": float(diagnostics["displacement_l2"][index]),
                },
                "target": token_view(target_id, route_digests),
                "prediction": token_view(predicted_id, route_digests),
                "correct": target_id == predicted_id,
                "logits_float32_hex": [float(value).hex() for value in cpu_logits[index].tolist()],
            }
            handle.write(canonical_json(row) + "\n")
    return {
        "schema": TRACE_SCHEMA,
        "path": str(path),
        "records": len(dataset.policy.labels),
        "gzip_sha256": bytes_sha256(path),
        "all_tokens_byte_exact": True,
    }


def model_state_sha256(model: nn.Module) -> str:
    rows = []
    for name, value in sorted(model.state_dict().items()):
        rows.append((name, tensor_sha256(value)))
    return sha256_json(rows)


def parameter_count_by_arm() -> dict[str, int]:
    return {name: StandardSectorActionMLP(name).trainable_parameters for name in ARM_CONFIGS}


__all__ = [
    "ARM_CONFIGS",
    "DATASET_SCHEMA",
    "HELD_SECTORS",
    "HIDDEN_WIDTH",
    "PRIMARY_CANDIDATE",
    "SCHEMA",
    "SECTOR_COUNT",
    "ArmConfig",
    "SectorDataset",
    "StandardSectorActionMLP",
    "apply_sector_topology",
    "build_sector_dataset",
    "evaluate_model",
    "holdout_sandbox",
    "load_route_authority",
    "model_state_sha256",
    "parameter_count_by_arm",
    "rollout_model",
    "scope_sector",
    "training_sandbox",
    "weight_diagnostics",
    "write_token_pressure_trace",
]

