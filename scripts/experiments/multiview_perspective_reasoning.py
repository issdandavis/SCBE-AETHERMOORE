from __future__ import annotations

"""Controlled six-tongue test for conserved facts, differing views, and path reasoning.

This is deliberately not a test of whether a reversible codec is "smart".  It asks
whether a small neural system can use an exact byte identity while retaining surface
form, perspective, disagreement cause, and reversible transition structure.

The world is synthetic so every invariant and every reason for disagreement is known.
The six Sacred Tongues are transport views.  Six separate evidence lenses are semantic
perspectives; the two sixes are never treated as the same axis.
"""

import argparse
import hashlib
import json
import math
import os
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

# Required by deterministic CUDA matrix multiplication. This must be set
# before the first CUDA context is created.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch
import torch.nn as nn
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[2]
SIX_TONGUES_ROOT = REPO_ROOT / "packages" / "sixtongues"
if str(SIX_TONGUES_ROOT) not in sys.path:
    sys.path.insert(0, str(SIX_TONGUES_ROOT))

import sixtongues as ST  # noqa: E402


TONGUES = tuple(ST.TONGUES)
N_STATES = 64
N_LENSES = 6
INPUT_DIM = 128
CORE_DIM = 32
RESIDUAL_DIM = 16
OP_DELTAS = (-9, -5, -3, -1, 1, 3, 5, 9)
OP_TO_INDEX = {delta: index for index, delta in enumerate(OP_DELTAS)}
INVERSE_INDEX = torch.tensor([OP_TO_INDEX[-delta] for delta in OP_DELTAS], dtype=torch.long)
TRUTH_WEIGHTS = (3, 2, 2, -2, -1, 1)
SEMANTIC_TEST_STATES = (1, 2, 4, 6, 9, 11, 13, 14, 19, 21, 31, 32, 0, 18, 30, 43)
DEFAULT_OUTPUT = Path("artifacts") / "multiview_perspective_reasoning_20261021"


@dataclass(frozen=True)
class Arm:
    name: str
    feature_mode: str
    relational: bool
    cycle: bool
    preserve_residual: bool


ARMS = (
    Arm("aligned_identity_only", "aligned", False, False, True),
    Arm("aligned_relational", "aligned", True, False, True),
    Arm("aligned_relational_cycle", "aligned", True, True, True),
    Arm("aligned_cycle_no_residual", "aligned", True, True, False),
    Arm("shuffled_relational_cycle", "shuffled", True, True, True),
    Arm("ordinary_relational_cycle", "ordinary", True, True, True),
    Arm("random_relational_cycle", "random", True, True, True),
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_state_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        tensor = value.detach().contiguous().cpu()
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def configure_determinism(device: torch.device) -> dict[str, object]:
    """Select kernels suitable for exact same-seed replay."""
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    if device.type == "cuda":
        # MultiheadAttention otherwise selects a fast fused kernel that PyTorch
        # warns is nondeterministic on this GPU. The math path is slower but
        # this experiment is small and reproducibility matters more.
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_math_sdp(True)
    return {
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "flash_sdp_enabled": bool(torch.backends.cuda.flash_sdp_enabled()),
        "memory_efficient_sdp_enabled": bool(torch.backends.cuda.mem_efficient_sdp_enabled()),
        "math_sdp_enabled": bool(torch.backends.cuda.math_sdp_enabled()),
    }


def state_bits(state: int) -> tuple[int, ...]:
    return tuple((state >> bit) & 1 for bit in range(6))


def signed_bits(state: int) -> tuple[int, ...]:
    return tuple(1 if value else -1 for value in state_bits(state))


def trit(score: int, threshold: int = 2) -> int:
    if score >= threshold:
        return 1
    if score <= -threshold:
        return -1
    return 0


def truth_for(state: int) -> int:
    return trit(sum(weight * bit for weight, bit in zip(TRUTH_WEIGHTS, signed_bits(state))))


def lens_stance(state: int, lens: int) -> int:
    """Each lens omits one evidence axis; disagreement therefore has a known cause."""
    weights = list(TRUTH_WEIGHTS)
    weights[lens] = 0
    return trit(sum(weight * bit for weight, bit in zip(weights, signed_bits(state))))


def disagreement_reason(state: int, lens: int) -> int:
    """0..5 names the omitted axis; 6 means the omission did not alter the stance."""
    return lens if lens_stance(state, lens) != truth_for(state) else 6


def majority(values: Sequence[int]) -> int:
    counts = {value: values.count(value) for value in (-1, 0, 1)}
    largest = max(counts.values())
    tied = [value for value, count in counts.items() if count == largest]
    if 0 in tied:
        return 0
    return min(tied)


def surface_features(token: str) -> list[float]:
    """A bounded surface residue; canonical byte components are stored separately."""
    out = [0.0] * 64
    lowered = token.lower()
    for index, char in enumerate(lowered):
        out[(ord(char) * 17 + index * 13) % 64] += 1.0
    for index, (left, right) in enumerate(zip(lowered, lowered[1:])):
        out[(ord(left) * 31 + ord(right) * 7 + index) % 64] += 1.0
    scale = math.sqrt(sum(value * value for value in out)) or 1.0
    return [value / scale for value in out]


def token_feature(byte_value: int, tongue_index: int) -> torch.Tensor:
    tongue = TONGUES[tongue_index]
    token = ST.encode_bytes(bytes([byte_value]), tongue)
    decoded = ST.decode_tokens(token, tongue)
    if decoded != bytes([byte_value]):
        raise AssertionError(f"non-bijective token at byte={byte_value}, tongue={tongue}")
    vector = torch.zeros(INPUT_DIM, dtype=torch.float32)
    vector[0:8] = torch.tensor([(byte_value >> bit) & 1 for bit in range(8)], dtype=torch.float32)
    vector[8 + (byte_value >> 4)] = 1.0
    vector[24 + (byte_value & 15)] = 1.0
    vector[40 + tongue_index] = 1.0
    vector[46:110] = torch.tensor(surface_features(token))
    vector[110] = len(token) / 16.0
    vector[111] = token.index("'") / 12.0
    vector[112] = sum(char in "aeiou" for char in token.lower()) / max(len(token), 1)
    vector[113] = (byte_value + 1) / 64.0
    for offset in range(14):
        vector[114 + offset] = math.sin((byte_value + 1) * (offset + 1) * 0.173 + tongue_index)
    return F.normalize(vector, dim=0)


def ordinary_feature(byte_value: int, tongue_index: int) -> torch.Tensor:
    """Equal-width ordinary numeric code with the same exact byte and lane information."""
    vector = torch.zeros(INPUT_DIM, dtype=torch.float32)
    vector[0:8] = torch.tensor([(byte_value >> bit) & 1 for bit in range(8)], dtype=torch.float32)
    vector[8 + (byte_value >> 4)] = 1.0
    vector[24 + (byte_value & 15)] = 1.0
    vector[40 + tongue_index] = 1.0
    for offset in range(64):
        vector[46 + offset] = math.sin(
            (byte_value + 1) * (offset + 1) * 0.173 + tongue_index * 0.619
        )
    vector[110] = (byte_value + 1) / 64.0
    vector[111] = (tongue_index + 1) / 6.0
    for offset in range(16):
        vector[112 + offset] = math.cos(
            (byte_value + 1) * (offset + 1) * 0.117 + tongue_index * 0.271
        )
    return F.normalize(vector, dim=0)


def build_features(mode: str) -> torch.Tensor:
    aligned = torch.stack(
        [
            torch.stack([token_feature(state, tongue) for tongue in range(len(TONGUES))])
            for state in range(N_STATES)
        ]
    )
    if mode == "aligned":
        return aligned
    if mode == "ordinary":
        return torch.stack(
            [
                torch.stack([ordinary_feature(state, tongue) for tongue in range(len(TONGUES))])
                for state in range(N_STATES)
            ]
        )
    if mode == "shuffled":
        shuffled = aligned.clone()
        for tongue in range(len(TONGUES)):
            generator = torch.Generator().manual_seed(8100 + tongue)
            shuffled[:, tongue] = aligned[torch.randperm(N_STATES, generator=generator), tongue]
        return shuffled
    if mode == "random":
        generator = torch.Generator().manual_seed(9107)
        values = torch.randn(N_STATES, len(TONGUES), INPUT_DIM, generator=generator)
        values[:, :, 40:46] = 0.0
        for tongue in range(len(TONGUES)):
            values[:, tongue, 40 + tongue] = 1.0
        return F.normalize(values, dim=-1)
    raise ValueError(f"unknown feature mode {mode!r}")


def verify_round_trips() -> dict[str, object]:
    failures: list[dict[str, object]] = []
    for byte_value in range(256):
        for tongue in TONGUES:
            token = ST.encode_bytes(bytes([byte_value]), tongue)
            decoded = ST.decode_tokens(token, tongue)
            if decoded != bytes([byte_value]):
                failures.append({"byte": byte_value, "tongue": tongue, "token": token})
    return {
        "checks": 256 * len(TONGUES),
        "passed": 256 * len(TONGUES) - len(failures),
        "failures": failures,
    }


def transition_split() -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]]]:
    """Hold an edge and its exact inverse together so reverse scoring cannot leak."""
    held: set[tuple[int, int]] = set()
    for delta in (1, 3, 5, 9):
        positive_index = OP_TO_INDEX[delta]
        negative_index = OP_TO_INDEX[-delta]
        for start in range(N_STATES):
            if (start * 13 + delta * 7) % 7 == 0:
                target = (start + delta) % N_STATES
                held.add((start, positive_index))
                held.add((target, negative_index))
    train: list[tuple[int, int, int]] = []
    test: list[tuple[int, int, int]] = []
    for start in range(N_STATES):
        for op_index, delta in enumerate(OP_DELTAS):
            row = (start, op_index, (start + delta) % N_STATES)
            (test if (start, op_index) in held else train).append(row)
    return train, test


class PerspectiveTransitionNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(INPUT_DIM, 96),
            nn.GELU(),
            nn.Linear(96, CORE_DIM + RESIDUAL_DIM),
        )
        # Keep the six forms as separate nodes.  A learned query reads their
        # shared core; lens-specific queries can follow different paths over
        # those same nodes without changing the conserved byte identity.
        self.base_query = nn.Parameter(torch.zeros(1, 1, CORE_DIM))
        self.form_attention = nn.MultiheadAttention(CORE_DIM, 4, batch_first=True)
        self.lane_head = nn.Linear(RESIDUAL_DIM, len(TONGUES))
        self.bit_head = nn.Linear(CORE_DIM, 6)
        self.truth_head = nn.Sequential(nn.Linear(CORE_DIM, 48), nn.GELU(), nn.Linear(48, 3))
        self.lens_embedding = nn.Embedding(N_LENSES, 12)
        self.lens_query = nn.Linear(12, CORE_DIM, bias=False)
        self.stance_head = nn.Sequential(nn.Linear(CORE_DIM + 12, 48), nn.GELU(), nn.Linear(48, 3))
        self.reason_head = nn.Sequential(nn.Linear(CORE_DIM + 12, 48), nn.GELU(), nn.Linear(48, 7))
        self.op_embedding = nn.Embedding(len(OP_DELTAS), 16)
        self.transition = nn.Sequential(
            nn.Linear(CORE_DIM + 16, 64),
            nn.GELU(),
            nn.Linear(64, CORE_DIM),
        )

    def encode(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encoder(values)
        return F.normalize(encoded[..., :CORE_DIM], dim=-1), encoded[..., CORE_DIM:]

    def step(self, core: torch.Tensor, op_index: torch.Tensor) -> torch.Tensor:
        operation = self.op_embedding(op_index)
        delta = self.transition(torch.cat([core, operation], dim=-1))
        return F.normalize(core + delta, dim=-1)

    def attend(
        self,
        forms: torch.Tensor,
        query: torch.Tensor | None = None,
        need_weights: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        if forms.ndim != 3 or forms.shape[-2:] != (len(TONGUES), CORE_DIM):
            raise ValueError("attention expects [batch, six forms, core dim]")
        if query is None:
            query_nodes = self.base_query.expand(forms.shape[0], -1, -1)
        else:
            query_nodes = query.unsqueeze(1)
        value, weights = self.form_attention(
            query_nodes,
            forms,
            forms,
            need_weights=need_weights,
            average_attn_weights=False,
        )
        return F.normalize(value[:, 0], dim=-1), weights if need_weights else None

    def lens_inputs(
        self,
        forms: torch.Tensor,
        lens: torch.Tensor,
        need_weights: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        embedding = self.lens_embedding(lens)
        query = self.base_query[:, 0].expand(forms.shape[0], -1) + self.lens_query(embedding)
        attended, weights = self.attend(forms, query=query, need_weights=need_weights)
        return torch.cat([attended, embedding], dim=-1), weights


def prototypes(model: PerspectiveTransitionNet, cores: torch.Tensor) -> torch.Tensor:
    value, _ = model.attend(cores)
    return value


def identity_loss(cores: torch.Tensor, temperature: float = 0.09) -> torch.Tensor:
    total = cores.new_tensor(0.0)
    labels = torch.arange(N_STATES, device=cores.device)
    summed = cores.sum(dim=1)
    for lane in range(len(TONGUES)):
        other = F.normalize((summed - cores[:, lane]) / (len(TONGUES) - 1), dim=-1)
        logits = cores[:, lane] @ other.T / temperature
        total = total + F.cross_entropy(logits, labels)
    return total / len(TONGUES)


def tensor_rows(rows: Sequence[tuple[int, int, int]], device: torch.device) -> tuple[torch.Tensor, ...]:
    return tuple(torch.tensor([row[index] for row in rows], device=device) for index in range(3))


def train_arm(
    arm: Arm,
    seed: int,
    steps: int,
    device: torch.device,
    trace_every: int = 100,
) -> tuple[PerspectiveTransitionNet, list[dict[str, float]]]:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    features = build_features(arm.feature_mode).to(device)
    model = PerspectiveTransitionNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    train_rows, _ = transition_split()
    starts, operations, targets = tensor_rows(train_rows, device)
    inverse = INVERSE_INDEX.to(device)[operations]
    all_lane_targets = torch.arange(len(TONGUES), device=device).repeat(N_STATES)
    bits = torch.tensor([state_bits(state) for state in range(N_STATES)], dtype=torch.float32, device=device)
    semantic_train = torch.tensor(
        [state for state in range(N_STATES) if state not in SEMANTIC_TEST_STATES], device=device
    )
    truth_targets = torch.tensor([truth_for(int(state)) + 1 for state in semantic_train], device=device)
    semantic_states = semantic_train.repeat_interleave(N_LENSES)
    semantic_lenses = torch.arange(N_LENSES, device=device).repeat(len(semantic_train))
    stance_targets = torch.tensor(
        [lens_stance(int(state), int(lens)) + 1 for state, lens in zip(semantic_states, semantic_lenses)],
        device=device,
    )
    reason_targets = torch.tensor(
        [disagreement_reason(int(state), int(lens)) for state, lens in zip(semantic_states, semantic_lenses)],
        device=device,
    )
    trace: list[dict[str, float]] = []

    for step in range(steps):
        optimizer.zero_grad(set_to_none=True)
        cores, residual = model.encode(features)
        proto = prototypes(model, cores)
        loss_id = identity_loss(cores)
        loss_lane = F.cross_entropy(model.lane_head(residual.reshape(-1, RESIDUAL_DIM)), all_lane_targets)
        loss_bits = F.binary_cross_entropy_with_logits(model.bit_head(proto), bits)
        loss = loss_id + 0.25 * loss_bits
        if arm.preserve_residual:
            loss = loss + 0.25 * loss_lane

        loss_transition = proto.new_tensor(0.0)
        loss_truth = proto.new_tensor(0.0)
        loss_stance = proto.new_tensor(0.0)
        loss_reason = proto.new_tensor(0.0)
        loss_cycle = proto.new_tensor(0.0)
        if arm.relational:
            predicted = model.step(proto[starts], operations)
            transition_logits = predicted @ proto.T / 0.09
            loss_transition = F.cross_entropy(transition_logits, targets)
            loss_truth = F.cross_entropy(model.truth_head(proto[semantic_train]), truth_targets)
            lens_input, _ = model.lens_inputs(cores[semantic_states], semantic_lenses)
            loss_stance = F.cross_entropy(model.stance_head(lens_input), stance_targets)
            loss_reason = F.cross_entropy(model.reason_head(lens_input), reason_targets)
            loss = loss + loss_transition + 0.55 * loss_truth + 0.75 * loss_stance + 0.50 * loss_reason
            if arm.cycle:
                returned = model.step(predicted, inverse)
                loss_cycle = F.cross_entropy(returned @ proto.T / 0.09, starts)
                loss = loss + 0.65 * loss_cycle

        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss for {arm.name} seed {seed} step {step}")
        loss.backward()
        for name, parameter in model.named_parameters():
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                raise RuntimeError(f"non-finite gradient {name} for {arm.name} seed {seed}")
        optimizer.step()
        if step == 0 or (step + 1) % trace_every == 0 or step + 1 == steps:
            trace.append(
                {
                    "step": step + 1,
                    "loss": float(loss.detach().cpu()),
                    "identity": float(loss_id.detach().cpu()),
                    "lane": float(loss_lane.detach().cpu()),
                    "bits": float(loss_bits.detach().cpu()),
                    "transition": float(loss_transition.detach().cpu()),
                    "truth": float(loss_truth.detach().cpu()),
                    "stance": float(loss_stance.detach().cpu()),
                    "reason": float(loss_reason.detach().cpu()),
                    "cycle": float(loss_cycle.detach().cpu()),
                }
            )
    return model, trace


def accuracy(prediction: torch.Tensor, target: torch.Tensor) -> float:
    return float((prediction == target).float().mean().cpu()) if len(target) else 0.0


def roll(model: PerspectiveTransitionNet, start: torch.Tensor, operations: Sequence[int]) -> torch.Tensor:
    state = start
    for operation in operations:
        op = torch.full((state.shape[0],), operation, dtype=torch.long, device=state.device)
        state = model.step(state, op)
    return state


def deterministic_paths(count: int = 256) -> list[tuple[int, tuple[int, ...]]]:
    rng = random.Random(20261021)
    paths = []
    for _ in range(count):
        start = rng.randrange(N_STATES)
        length = rng.randrange(2, 6)
        paths.append((start, tuple(rng.randrange(len(OP_DELTAS)) for _ in range(length))))
    return paths


def path_target(start: int, operations: Sequence[int]) -> int:
    value = start
    for operation in operations:
        value = (value + OP_DELTAS[operation]) % N_STATES
    return value


def activation_snapshot(
    model: PerspectiveTransitionNet,
    features: torch.Tensor,
    proto: torch.Tensor,
) -> dict[str, object]:
    cores, residual = model.encode(features)
    _, base_attention = model.attend(cores, need_weights=True)
    selected = (1, 6, 19, 32)
    events: dict[str, object] = {}
    for state in selected:
        core_cos = cores[state] @ cores[state].T
        residual_norm = F.normalize(residual[state], dim=-1)
        residual_cos = residual_norm @ residual_norm.T
        lenses = torch.arange(N_LENSES, device=features.device)
        lens_input, lens_attention = model.lens_inputs(
            cores[state].unsqueeze(0).expand(N_LENSES, -1, -1), lenses, need_weights=True
        )
        stance_prob = F.softmax(model.stance_head(lens_input), dim=-1)
        reason_prob = F.softmax(model.reason_head(lens_input), dim=-1)
        events[str(state)] = {
            "truth": truth_for(state),
            "stances": [lens_stance(state, lens) for lens in range(N_LENSES)],
            "core_cosine": core_cos.detach().cpu().tolist(),
            "residual_cosine": residual_cos.detach().cpu().tolist(),
            "lane_predictions": model.lane_head(residual[state]).argmax(-1).detach().cpu().tolist(),
            "base_attention_by_head": base_attention[state, :, 0].detach().cpu().tolist(),
            "lens_attention_by_lens_and_head": lens_attention[:, :, 0].detach().cpu().tolist(),
            "stance_probabilities": stance_prob.detach().cpu().tolist(),
            "reason_probabilities": reason_prob.detach().cpu().tolist(),
        }
    start = 7
    operations = tuple(OP_TO_INDEX[value] for value in (1, 3, -5, 9))
    state = proto[start : start + 1]
    trace = [{"step": 0, "true_state": start, "predicted_state": start, "core_norm": 1.0}]
    true_state = start
    for index, operation in enumerate(operations, 1):
        state = roll(model, state, (operation,))
        true_state = (true_state + OP_DELTAS[operation]) % N_STATES
        predicted = int((state @ proto.T).argmax(-1).item())
        trace.append(
            {
                "step": index,
                "operation": OP_DELTAS[operation],
                "true_state": true_state,
                "predicted_state": predicted,
                "core_norm": float(state.norm(dim=-1).item()),
            }
        )
    return {"events": events, "forward_trace": trace}


@torch.no_grad()
def evaluate(model: PerspectiveTransitionNet, arm: Arm, seed: int, device: torch.device) -> dict[str, object]:
    model.eval()
    features = build_features(arm.feature_mode).to(device)
    cores, residual = model.encode(features)
    proto = prototypes(model, cores)
    labels = torch.arange(N_STATES, device=device)
    summed = cores.sum(dim=1)
    identity_hits = []
    for lane in range(len(TONGUES)):
        other = F.normalize((summed - cores[:, lane]) / (len(TONGUES) - 1), dim=-1)
        identity_hits.append((cores[:, lane] @ other.T).argmax(-1))
    identity_prediction = torch.stack(identity_hits, dim=1)
    identity_top1 = accuracy(identity_prediction, labels[:, None].expand_as(identity_prediction))
    lane_prediction = model.lane_head(residual.reshape(-1, RESIDUAL_DIM)).argmax(-1)
    lane_target = torch.arange(len(TONGUES), device=device).repeat(N_STATES)
    lane_accuracy = accuracy(lane_prediction, lane_target)
    bit_prediction = (torch.sigmoid(model.bit_head(proto)) >= 0.5).long()
    bit_target = torch.tensor([state_bits(state) for state in range(N_STATES)], device=device)
    byte_exact = float((bit_prediction == bit_target).all(dim=1).float().mean().cpu())

    _, test_rows = transition_split()
    starts, operations, targets = tensor_rows(test_rows, device)
    predicted = model.step(proto[starts], operations)
    predicted_state = (predicted @ proto.T).argmax(-1)
    positive = torch.tensor([OP_DELTAS[int(op)] > 0 for op in operations], device=device)
    forward_accuracy = accuracy(predicted_state[positive], targets[positive])
    backward_accuracy = accuracy(predicted_state[~positive], targets[~positive])
    returned = model.step(predicted, INVERSE_INDEX.to(device)[operations])
    cycle_accuracy = accuracy((returned @ proto.T).argmax(-1), starts)

    paths = deterministic_paths()
    path_forward_hits = 0
    path_backward_hits = 0
    rollback_hits = 0
    postrollback_hits = 0
    for start_value, path in paths:
        current = proto[start_value : start_value + 1]
        end = roll(model, current, path)
        expected = path_target(start_value, path)
        path_forward_hits += int((end @ proto.T).argmax(-1).item() == expected)
        inverse_path = tuple(int(INVERSE_INDEX[operation]) for operation in reversed(path))
        back = roll(model, end, inverse_path)
        path_backward_hits += int((back @ proto.T).argmax(-1).item() == start_value)
        wrong = path[:2]
        displaced = roll(model, current, wrong)
        recovered = roll(model, displaced, tuple(int(INVERSE_INDEX[op]) for op in reversed(wrong)))
        rollback_hits += int((recovered @ proto.T).argmax(-1).item() == start_value)
        final = roll(model, recovered, path)
        postrollback_hits += int((final @ proto.T).argmax(-1).item() == expected)

    rng = random.Random(77123)
    branch_hits = 0
    branch_total = 128
    for _ in range(branch_total):
        start_value = rng.randrange(N_STATES)
        candidates: list[tuple[int, ...]] = []
        endpoints: set[int] = set()
        while len(candidates) < 4:
            candidate = tuple(rng.randrange(len(OP_DELTAS)) for _ in range(3))
            endpoint = path_target(start_value, candidate)
            if endpoint not in endpoints:
                endpoints.add(endpoint)
                candidates.append(candidate)
        correct = rng.randrange(4)
        goal = path_target(start_value, candidates[correct])
        scores = []
        for candidate in candidates:
            endpoint_latent = roll(model, proto[start_value : start_value + 1], candidate)
            scores.append(float((endpoint_latent @ proto[goal]).item()))
        branch_hits += int(max(range(4), key=lambda index: scores[index]) == correct)

    test_states = torch.tensor(SEMANTIC_TEST_STATES, device=device)
    truth_target = torch.tensor([truth_for(state) + 1 for state in SEMANTIC_TEST_STATES], device=device)
    truth_prediction = model.truth_head(proto[test_states]).argmax(-1)
    truth_accuracy = accuracy(truth_prediction, truth_target)
    semantic_states = test_states.repeat_interleave(N_LENSES)
    semantic_lenses = torch.arange(N_LENSES, device=device).repeat(len(test_states))
    lens_input, _ = model.lens_inputs(cores[semantic_states], semantic_lenses)
    stance_prediction = model.stance_head(lens_input).argmax(-1)
    stance_target = torch.tensor(
        [lens_stance(int(state), int(lens)) + 1 for state, lens in zip(semantic_states, semantic_lenses)],
        device=device,
    )
    reason_prediction = model.reason_head(lens_input).argmax(-1)
    reason_target = torch.tensor(
        [disagreement_reason(int(state), int(lens)) for state, lens in zip(semantic_states, semantic_lenses)],
        device=device,
    )
    disagreement_mask = reason_target != 6
    stance_accuracy = accuracy(stance_prediction, stance_target)
    reason_disagreement_accuracy = accuracy(
        reason_prediction[disagreement_mask], reason_target[disagreement_mask]
    )
    stance_matrix = stance_prediction.view(len(test_states), N_LENSES)
    stance_target_matrix = stance_target.view(len(test_states), N_LENSES)
    disagreement_vector_exact = float(
        (stance_matrix == stance_target_matrix).all(dim=1).float().mean().cpu()
    )
    minority_mask_values = []
    for state in SEMANTIC_TEST_STATES:
        values = [lens_stance(state, lens) for lens in range(N_LENSES)]
        dominant = majority(values)
        minority_mask_values.extend(value != dominant for value in values)
    minority_mask = torch.tensor(minority_mask_values, device=device)
    minority_accuracy = accuracy(stance_prediction[minority_mask], stance_target[minority_mask])
    majority_truth = [
        majority([lens_stance(state, lens) for lens in range(N_LENSES)]) + 1
        for state in SEMANTIC_TEST_STATES
    ]
    majority_truth_accuracy = accuracy(torch.tensor(majority_truth, device=device), truth_target)
    trap_mask = torch.tensor(
        [
            majority([lens_stance(state, lens) for lens in range(N_LENSES)]) != truth_for(state)
            for state in SEMANTIC_TEST_STATES
        ],
        device=device,
    )
    model_trap_truth_accuracy = accuracy(truth_prediction[trap_mask], truth_target[trap_mask])

    metrics = {
        "identity_top1": identity_top1,
        "lane_residual_accuracy": lane_accuracy,
        "byte_exact": byte_exact,
        "forward_heldout": forward_accuracy,
        "backward_heldout": backward_accuracy,
        "cycle_heldout": cycle_accuracy,
        "multistep_forward": path_forward_hits / len(paths),
        "multistep_backward": path_backward_hits / len(paths),
        "parallel_branch_selection": branch_hits / branch_total,
        "rollback_recovery": rollback_hits / len(paths),
        "postrollback_target": postrollback_hits / len(paths),
        "truth_heldout": truth_accuracy,
        "perspective_stance_heldout": stance_accuracy,
        "disagreement_reason_heldout": reason_disagreement_accuracy,
        "disagreement_vector_exact": disagreement_vector_exact,
        "minority_view_accuracy": minority_accuracy,
        "majority_vote_truth_baseline": majority_truth_accuracy,
        "model_truth_on_majority_traps": model_trap_truth_accuracy,
    }
    reasoning_keys = (
        "forward_heldout",
        "backward_heldout",
        "multistep_forward",
        "multistep_backward",
        "parallel_branch_selection",
        "rollback_recovery",
    )
    interpretation_keys = (
        "truth_heldout",
        "perspective_stance_heldout",
        "disagreement_reason_heldout",
        "minority_view_accuracy",
    )
    metrics["reasoning_floor"] = min(metrics[key] for key in reasoning_keys)
    metrics["interpretation_floor"] = min(metrics[key] for key in interpretation_keys)
    metrics["joint_floor"] = min(metrics["reasoning_floor"], metrics["interpretation_floor"])
    return {
        "arm": arm.name,
        "seed": seed,
        "metrics": metrics,
        "activation_snapshot": activation_snapshot(model, features, proto),
    }


def comparison(runs: Sequence[dict[str, object]], left: str, right: str, metric: str) -> dict[str, object]:
    left_rows = {int(row["seed"]): float(row["metrics"][metric]) for row in runs if row["arm"] == left}
    right_rows = {int(row["seed"]): float(row["metrics"][metric]) for row in runs if row["arm"] == right}
    seeds = sorted(set(left_rows) & set(right_rows))
    effects = [left_rows[seed] - right_rows[seed] for seed in seeds]
    left_values = [left_rows[seed] for seed in seeds]
    right_values = [right_rows[seed] for seed in seeds]
    if len(seeds) > 1:
        pooled = math.sqrt((statistics.variance(left_values) + statistics.variance(right_values)) / 2)
    else:
        pooled = math.inf
    mean_effect = statistics.mean(effects) if effects else 0.0
    return {
        "left": left,
        "right": right,
        "metric": metric,
        "seeds": seeds,
        "left_values": left_values,
        "right_values": right_values,
        "paired_effects": effects,
        "mean_effect": mean_effect,
        "two_pooled_sd": 2 * pooled,
        "all_positive": bool(effects) and all(effect > 0 for effect in effects),
        "clears_two_pooled_sd": bool(effects) and mean_effect > 2 * pooled,
    }


def analyze(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    comparisons: dict[str, dict[str, object]] = {}
    for metric in ("reasoning_floor", "interpretation_floor", "joint_floor"):
        comparisons[f"aligned_vs_ordinary_{metric}"] = comparison(
            runs, "aligned_relational_cycle", "ordinary_relational_cycle", metric
        )
        comparisons[f"aligned_vs_shuffled_{metric}"] = comparison(
            runs, "aligned_relational_cycle", "shuffled_relational_cycle", metric
        )
        comparisons[f"cycle_vs_no_cycle_{metric}"] = comparison(
            runs, "aligned_relational_cycle", "aligned_relational", metric
        )
    residual = comparison(
        runs, "aligned_relational_cycle", "aligned_cycle_no_residual", "lane_residual_accuracy"
    )
    residual_reasoning = comparison(
        runs, "aligned_relational_cycle", "aligned_cycle_no_residual", "reasoning_floor"
    )
    comparisons["residual_lane_effect"] = residual
    comparisons["residual_reasoning_effect"] = residual_reasoning
    tokenizer_specific = all(
        comparisons[f"aligned_vs_{control}_{metric}"]["all_positive"]
        and comparisons[f"aligned_vs_{control}_{metric}"]["clears_two_pooled_sd"]
        for control in ("ordinary", "shuffled")
        for metric in ("reasoning_floor", "interpretation_floor")
    )
    cycle_supported = all(
        comparisons[f"cycle_vs_no_cycle_{metric}"]["all_positive"]
        and comparisons[f"cycle_vs_no_cycle_{metric}"]["clears_two_pooled_sd"]
        for metric in ("reasoning_floor", "interpretation_floor")
    )
    residual_supported = (
        residual["all_positive"]
        and residual["clears_two_pooled_sd"]
        and residual_reasoning["mean_effect"] >= -0.02
    )
    return {
        "comparisons": comparisons,
        "claim_rules": {
            "tokenizer_specific_reasoning_support": tokenizer_specific,
            "cycle_objective_support": cycle_supported,
            "split_residual_preserves_form_without_material_reasoning_loss": residual_supported,
        },
        "scope": (
            "Synthetic mechanism test only. It can establish preservation, path manipulation, and "
            "perspective separation under known rules; it cannot establish historical, religious, "
            "moral, or open-domain judgment."
        ),
    }


def render_report(receipt: dict[str, object]) -> str:
    runs = receipt["runs"]
    lines = [
        "# Multiview perspective reasoning result",
        "",
        f"Generated: {receipt['created_at']}",
        "",
        "The six tongues are reversible transport views. The six evidence lenses are separate semantic perspectives.",
        "This benchmark keeps invariant truth, each lens's stance, and the exact omitted-evidence reason as separate targets.",
        "",
        "## Mean metrics across seeds",
        "",
        "| arm | identity | fwd | back | multi-fwd | multi-back | branch | rollback | truth | stance | why | minority | lane |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        rows = [row for row in runs if row["arm"] == arm.name]
        def mean(metric: str) -> float:
            return statistics.mean(float(row["metrics"][metric]) for row in rows)
        lines.append(
            "| {name} | {identity:.3f} | {fwd:.3f} | {back:.3f} | {mf:.3f} | {mb:.3f} | "
            "{branch:.3f} | {rollback:.3f} | {truth:.3f} | {stance:.3f} | {why:.3f} | "
            "{minority:.3f} | {lane:.3f} |".format(
                name=arm.name,
                identity=mean("identity_top1"),
                fwd=mean("forward_heldout"),
                back=mean("backward_heldout"),
                mf=mean("multistep_forward"),
                mb=mean("multistep_backward"),
                branch=mean("parallel_branch_selection"),
                rollback=mean("rollback_recovery"),
                truth=mean("truth_heldout"),
                stance=mean("perspective_stance_heldout"),
                why=mean("disagreement_reason_heldout"),
                minority=mean("minority_view_accuracy"),
                lane=mean("lane_residual_accuracy"),
            )
        )
    lines.extend(["", "## Pre-registered claim gates", ""])
    for claim, passed in receipt["analysis"]["claim_rules"].items():
        lines.append(f"- {claim}: **{'PASS' if passed else 'NOT ESTABLISHED'}**")
    lines.extend(
        [
            "",
            "A failed gate means this bounded mechanism did not separate from both controls by the registered noise rule.",
            "It does not turn exact round trips into a reasoning claim, and it does not erase useful traceability.",
            "",
            f"Scope: {receipt['analysis']['scope']}",
        ]
    )
    return "\n".join(lines) + "\n"


def preflight(output_dir: Path, device: torch.device) -> dict[str, object]:
    started = time.perf_counter()
    determinism = configure_determinism(device)
    round_trips = verify_round_trips()
    feature_shapes = {mode: list(build_features(mode).shape) for mode in ("aligned", "ordinary", "shuffled", "random")}
    models = [PerspectiveTransitionNet() for _ in ARMS]
    parameter_counts = [sum(parameter.numel() for parameter in model.parameters()) for model in models]
    train_rows, test_rows = transition_split()
    held = {(start, operation) for start, operation, _ in test_rows}
    inverse_closed = all(
        (((target, int(INVERSE_INDEX[operation]))) in held)
        for start, operation, target in test_rows
    )
    perspective_reasons = {
        disagreement_reason(state, lens) for state in range(N_STATES) for lens in range(N_LENSES)
    }
    traps = [
        state
        for state in range(N_STATES)
        if majority([lens_stance(state, lens) for lens in range(N_LENSES)]) != truth_for(state)
    ]
    # One real update proves every arm's graph is connected and finite; products are discarded.
    gradient_checks = {}
    for arm in ARMS:
        model, trace = train_arm(arm, seed=101, steps=1, device=device, trace_every=1)
        gradient_checks[arm.name] = {
            "finite_loss": math.isfinite(trace[-1]["loss"]),
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        }
        del model
    # A same-seed replay catches nondeterministic attention or matrix kernels
    # before a multi-seed comparison is allowed to consume the run budget.
    replay_arm = next(arm for arm in ARMS if arm.name == "aligned_relational_cycle")
    replay_hashes = []
    for _ in range(2):
        replay_model, _ = train_arm(replay_arm, seed=20261021, steps=3, device=device, trace_every=3)
        replay_hashes.append(model_state_sha256(replay_model))
        del replay_model
    exact_replay = replay_hashes[0] == replay_hashes[1]
    result = {
        "schema": "scbe.multiview-perspective-reasoning-preflight.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "determinism": determinism,
        "exact_replay": {"passed": exact_replay, "state_sha256": replay_hashes},
        "round_trips": round_trips,
        "feature_shapes": feature_shapes,
        "parameter_counts": parameter_counts,
        "all_parameter_matched": len(set(parameter_counts)) == 1,
        "train_transition_rows": len(train_rows),
        "held_transition_rows": len(test_rows),
        "inverse_closed_holdout": inverse_closed,
        "reason_classes_present": sorted(perspective_reasons),
        "majority_trap_count": len(traps),
        "majority_traps": traps,
        "gradient_checks": gradient_checks,
        "elapsed_seconds": time.perf_counter() - started,
        "passed": (
            not round_trips["failures"]
            and all(shape == [N_STATES, len(TONGUES), INPUT_DIM] for shape in feature_shapes.values())
            and len(set(parameter_counts)) == 1
            and inverse_closed
            and perspective_reasons == set(range(7))
            and len(traps) > 0
            and all(row["finite_loss"] for row in gradient_checks.values())
            and exact_replay
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "PREFLIGHT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_experiment(output_dir: Path, steps: int, seeds: Sequence[int], device: torch.device) -> dict[str, object]:
    preflight_result = preflight(output_dir, device)
    if not preflight_result["passed"]:
        raise RuntimeError("preflight failed; refusing final matrix")
    started = time.perf_counter()
    runs: list[dict[str, object]] = []
    for arm in ARMS:
        for seed in seeds:
            run_started = time.perf_counter()
            model, trace = train_arm(arm, seed, steps, device)
            result = evaluate(model, arm, seed, device)
            result["elapsed_seconds"] = time.perf_counter() - run_started
            result["training_trace"] = trace
            result["parameter_count"] = sum(parameter.numel() for parameter in model.parameters())
            runs.append(result)
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{arm.name}_s{seed}.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
    receipt = {
        "schema": "scbe.multiview-perspective-reasoning.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "seeds": list(seeds),
        "device": str(device),
        "arms": [asdict(arm) for arm in ARMS],
        "chances": {
            "state_retrieval": 1 / N_STATES,
            "trit": 1 / 3,
            "reason": 1 / 7,
            "parallel_branch": 1 / 4,
            "tongue_lane": 1 / len(TONGUES),
        },
        "preflight_sha256": sha256_file(output_dir / "PREFLIGHT.json"),
        "source": {
            "runner": {"path": str(Path(__file__)), "sha256": sha256_file(Path(__file__))},
            "six_tongues": {"path": str(Path(ST.__file__)), "sha256": sha256_file(Path(ST.__file__))},
        },
        "runs": runs,
        "analysis": analyze(runs),
        "elapsed_seconds": time.perf_counter() - started,
        "automatic_promotion": False,
        "provider_spend": 0,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "RESULTS.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (output_dir / "REPORT.md").write_text(render_report(receipt), encoding="utf-8")
    return receipt


def parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--seeds", type=parse_seeds, default=(11, 23, 37))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "auto":
        device_name = "cpu"
    if device_name == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA requested but unavailable")
    device = torch.device(device_name)
    torch.set_num_threads(max(1, min(torch.get_num_threads(), 4)))
    configure_determinism(device)
    if args.preflight_only:
        result = preflight(args.output_dir, device)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    result = run_experiment(args.output_dir, args.steps, args.seeds, device)
    print(render_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
