"""A deterministic VR-like developmental sandbox for Clay action curricula.

The simulation is the sandbox: it exposes only bounded toy memory and exact
action tokens.  It has no filesystem, process, network, provider, or shell
surface.  Canonical world coordinates remain authoritative while an
agent-centred transform moves the presented world, similar to a VR locomotion
frame.  Rewards are always computed in canonical coordinates so a moving view
cannot manufacture progress.

The lifecycle deliberately separates four phases:

``crawl``
    Low-force motor exploration against gravity and a restoring field.
``play``
    Full action force and target-seeking reward.
``swaddle``
    Action force and gravity are removed, damping rises, and a separate care
    signal marks consolidation.  The care signal is not credited to an action.
``release``
    Constraints return gradually before the next crawl/play cycle.

This is an executable curriculum mechanism, not evidence that a neural model
has improved.  The optional consolidation function is a bounded proximal
operator around a saved anchor; it never adds an unsigned bias to all weights.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from functools import lru_cache
import hashlib
import json
from typing import Any, Iterable, Literal

from action_compiler import TONGUE_ORDER, ca_word_for_opcode, radial_power_weight, render_tongue


SCHEMA = "clay.developmental-game-sandbox.v1"
TRANSITION_SCHEMA = "clay.developmental-transition.v1"
CONSOLIDATION_SCHEMA = "clay.weight-consolidation-proposal.v1"
ACTION_NAMES = (
    "rest",
    "push_x_positive",
    "push_x_negative",
    "push_y_positive",
    "push_y_negative",
    "inspect",
    "remember",
    "recall",
    "help",
)
ACTION_BYTES = tuple(range(0xA0, 0xA0 + len(ACTION_NAMES)))
MEMORY_SLOTS = 8
TONGUES = tuple(TONGUE_ORDER)
DRIVE_LABELS = {-1: "outcry", 0: "input", 1: "scope"}

Phase = Literal["crawl", "play", "swaddle", "release"]
Vec2 = tuple[Decimal, Decimal]


def D(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("sandbox decimals must be finite")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


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


def _vec_record(value: Vec2) -> list[str]:
    return [_decimal_text(value[0]), _decimal_text(value[1])]


def _add(left: Vec2, right: Vec2) -> Vec2:
    return left[0] + right[0], left[1] + right[1]


def _scale(value: Vec2, scalar: Decimal) -> Vec2:
    return value[0] * scalar, value[1] * scalar


def _sub(left: Vec2, right: Vec2) -> Vec2:
    return left[0] - right[0], left[1] - right[1]


def _norm(value: Vec2) -> Decimal:
    with localcontext() as context:
        context.prec = 34
        return (value[0] * value[0] + value[1] * value[1]).sqrt()


def _matvec(matrix: tuple[Vec2, Vec2], value: Vec2) -> Vec2:
    return (
        matrix[0][0] * value[0] + matrix[0][1] * value[1],
        matrix[1][0] * value[0] + matrix[1][1] * value[1],
    )


@dataclass(frozen=True, slots=True)
class LifecycleSchedule:
    crawl_ticks: int = 12
    play_ticks: int = 20
    swaddle_ticks: int = 8
    release_ticks: int = 8

    def __post_init__(self) -> None:
        if min(self.crawl_ticks, self.play_ticks, self.swaddle_ticks, self.release_ticks) < 1:
            raise ValueError("every lifecycle phase needs at least one tick")

    @property
    def cycle_ticks(self) -> int:
        return self.crawl_ticks + self.play_ticks + self.swaddle_ticks + self.release_ticks

    def phase_at(self, tick: int) -> Phase:
        if tick < 0:
            raise ValueError("tick cannot be negative")
        offset = tick % self.cycle_ticks
        if offset < self.crawl_ticks:
            return "crawl"
        offset -= self.crawl_ticks
        if offset < self.play_ticks:
            return "play"
        offset -= self.play_ticks
        if offset < self.swaddle_ticks:
            return "swaddle"
        return "release"


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    dt: Decimal = D("0.1")
    world_limit: Decimal = D("4")
    action_force: Decimal = D("1")
    gravity: Vec2 = (D("0"), D("-0.25"))
    restoring_strength: Decimal = D("0.12")
    target_radius: Decimal = D("0.3")
    outcry_trigger_ticks: int = 4
    outcry_duration_ticks: int = 2
    outcry_force_multiplier: Decimal = D("1.25")
    targets: tuple[Vec2, ...] = (
        (D("1.5"), D("0")),
        (D("0"), D("1.5")),
        (D("-1.5"), D("0")),
        (D("0"), D("-1.5")),
    )
    schedule: LifecycleSchedule = LifecycleSchedule()

    def __post_init__(self) -> None:
        for name in ("dt", "world_limit", "action_force", "restoring_strength", "target_radius"):
            value = getattr(self, name)
            if not value.is_finite() or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if self.outcry_trigger_ticks < 1 or self.outcry_duration_ticks < 1:
            raise ValueError("outcry trigger and duration must be positive")
        if (
            not self.outcry_force_multiplier.is_finite()
            or not D("1") <= self.outcry_force_multiplier <= D("1.5")
        ):
            raise ValueError("outcry force multiplier must lie in [1, 1.5]")
        if any(not component.is_finite() for component in self.gravity):
            raise ValueError("gravity must be finite")
        if not self.targets:
            raise ValueError("sandbox needs at least one target")
        for target in self.targets:
            if any(not component.is_finite() or abs(component) > self.world_limit for component in target):
                raise ValueError("target lies outside the bounded world")


@dataclass(frozen=True, slots=True)
class AgentStats:
    mobility: Decimal = D("0")
    curiosity: Decimal = D("0")
    stability: Decimal = D("0")

    def record(self) -> dict[str, str]:
        return {
            "mobility": _decimal_text(self.mobility),
            "curiosity": _decimal_text(self.curiosity),
            "stability": _decimal_text(self.stability),
        }


@dataclass(frozen=True, slots=True)
class SandboxState:
    tick: int
    position: Vec2
    velocity: Vec2
    target_index: int
    memory: tuple[int | None, ...]
    stats: AgentStats
    drive_trit: int = 0
    stagnation_ticks: int = 0
    outburst_ticks_remaining: int = 0

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError("state tick cannot be negative")
        if any(not component.is_finite() for component in (*self.position, *self.velocity)):
            raise ValueError("state vectors must be finite")
        if self.target_index < 0:
            raise ValueError("target index cannot be negative")
        if len(self.memory) != MEMORY_SLOTS:
            raise ValueError("toy memory has an exact bounded slot count")
        for value in self.memory:
            if value is not None and not -32768 <= value <= 32767:
                raise ValueError("toy memory values are signed 16-bit integers")
        if self.drive_trit not in DRIVE_LABELS:
            raise ValueError("developmental drive must be a balanced trit")
        if self.stagnation_ticks < 0 or self.outburst_ticks_remaining < 0:
            raise ValueError("developmental counters cannot be negative")

    def record(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "position": _vec_record(self.position),
            "velocity": _vec_record(self.velocity),
            "target_index": self.target_index,
            "memory": list(self.memory),
            "stats": self.stats.record(),
            "drive_trit": self.drive_trit,
            "drive_label": DRIVE_LABELS[self.drive_trit],
            "stagnation_ticks": self.stagnation_ticks,
            "outburst_ticks_remaining": self.outburst_ticks_remaining,
        }

    @property
    def sha256(self) -> str:
        return sha256_json(self.record())


@dataclass(frozen=True, slots=True)
class ToyAction:
    token_id: int
    slot: int | None = None
    value: int | None = None


@dataclass(frozen=True, slots=True)
class ActionToken:
    token_id: int
    name: str
    transport_byte: int
    weight_row: dict[str, Any]


@lru_cache(maxsize=None)
def action_token(token_id: int) -> ActionToken:
    if not 0 <= token_id < len(ACTION_NAMES):
        raise ValueError("toy action token lies outside the bounded table")
    row = radial_power_weight(token_id, len(ACTION_NAMES))
    return ActionToken(token_id, ACTION_NAMES[token_id], ACTION_BYTES[token_id], row.as_dict())


@lru_cache(maxsize=None)
def action_skin(token_id: int, tongue: str) -> str:
    token = action_token(token_id)
    if tongue not in TONGUES:
        raise ValueError("action tongue lies outside the Six Tongues table")
    return render_tongue(tongue, token.transport_byte, ca_word_for_opcode)


@lru_cache(maxsize=1)
def _skin_index() -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for token_id in range(len(ACTION_NAMES)):
        for tongue in TONGUES:
            skin = action_skin(token_id, tongue)
            if skin in result and result[skin][0] != token_id:
                raise RuntimeError("toy action tongue skin collision")
            result[skin] = (token_id, tongue)
    return result


def parse_action_skin(skin: str) -> tuple[int, str]:
    try:
        return _skin_index()[skin]
    except KeyError as error:
        raise ValueError("unknown toy action tongue skin") from error


@dataclass(frozen=True, slots=True)
class RewardChannels:
    task: Decimal
    care: Decimal
    stability: Decimal
    action_credit: Decimal

    def record(self) -> dict[str, str]:
        return {
            "task": _decimal_text(self.task),
            "care": _decimal_text(self.care),
            "stability": _decimal_text(self.stability),
            "action_credit": _decimal_text(self.action_credit),
        }


@dataclass(frozen=True, slots=True)
class Transition:
    schema: str
    phase: Phase
    action: dict[str, Any]
    before: dict[str, Any]
    after: dict[str, Any]
    rewards: dict[str, str]
    reward_trit: int
    observation: dict[str, Any]
    accepted: bool
    message: str
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class ConsolidationReceipt:
    schema: str
    before: tuple[str, ...]
    anchor: tuple[str, ...]
    after: tuple[str, ...]
    surface_strength: str
    center_strength: str
    center_indices: tuple[int, ...]
    care_signal: str
    receipt_sha256: str


def consolidate_weight_vector(
    weights: Iterable[Decimal | str | int | float],
    anchor: Iterable[Decimal | str | int | float],
    *,
    surface_strength: Decimal | str | float = D("0.05"),
    center_indices: Iterable[int] = (),
    center_strength: Decimal | str | float = D("0.10"),
    care_signal: Decimal | str | float = D("0.01"),
) -> ConsolidationReceipt:
    """Contract a proposed weight vector toward a saved anchor.

    The care signal is recorded separately and is never added to the weights.
    """

    before = tuple(D(value) for value in weights)
    anchors = tuple(D(value) for value in anchor)
    if not before or len(before) != len(anchors):
        raise ValueError("weights and anchor must have the same non-zero length")
    surface = D(surface_strength)
    center = D(center_strength)
    care = D(care_signal)
    if any(not value.is_finite() for value in (*before, *anchors, surface, center, care)):
        raise ValueError("consolidation values must be finite")
    if not D("0") <= surface <= D("1") or not D("0") <= center <= D("1") or care < 0:
        raise ValueError("consolidation strengths must lie in [0,1] and care be non-negative")
    indices = tuple(sorted(set(int(index) for index in center_indices)))
    if any(index < 0 or index >= len(before) for index in indices):
        raise ValueError("center index lies outside the weight vector")
    after_values: list[Decimal] = []
    for index, (value, origin) in enumerate(zip(before, anchors)):
        contracted = origin + (D("1") - surface) * (value - origin)
        if index in indices:
            contracted = origin + (D("1") - center) * (contracted - origin)
        after_values.append(contracted)
    before_text = tuple(_decimal_text(value) for value in before)
    anchor_text = tuple(_decimal_text(value) for value in anchors)
    after_text = tuple(_decimal_text(value) for value in after_values)
    body = {
        "schema": CONSOLIDATION_SCHEMA,
        "before": before_text,
        "anchor": anchor_text,
        "after": after_text,
        "surface_strength": _decimal_text(surface),
        "center_strength": _decimal_text(center),
        "center_indices": indices,
        "care_signal": _decimal_text(care),
    }
    return ConsolidationReceipt(
        schema=CONSOLIDATION_SCHEMA,
        before=before_text,
        anchor=anchor_text,
        after=after_text,
        surface_strength=body["surface_strength"],
        center_strength=body["center_strength"],
        center_indices=indices,
        care_signal=body["care_signal"],
        receipt_sha256=sha256_json(body),
    )


def verify_consolidation_receipt(receipt: ConsolidationReceipt) -> bool:
    body = {
        "schema": receipt.schema,
        "before": receipt.before,
        "anchor": receipt.anchor,
        "after": receipt.after,
        "surface_strength": receipt.surface_strength,
        "center_strength": receipt.center_strength,
        "center_indices": receipt.center_indices,
        "care_signal": receipt.care_signal,
    }
    return receipt.schema == CONSOLIDATION_SCHEMA and receipt.receipt_sha256 == sha256_json(body)


class DevelopmentalGameSandbox:
    """Bounded deterministic environment with toy memory and exact receipts."""

    def __init__(self, config: SandboxConfig = SandboxConfig()) -> None:
        self.config = config

    def initial_state(self) -> SandboxState:
        return SandboxState(
            tick=0,
            position=(D("0"), D("0")),
            velocity=(D("0"), D("0")),
            target_index=0,
            memory=(None,) * MEMORY_SLOTS,
            stats=AgentStats(),
            drive_trit=0,
            stagnation_ticks=0,
            outburst_ticks_remaining=0,
        )

    def phase(self, state: SandboxState) -> Phase:
        return self.config.schedule.phase_at(state.tick)

    @staticmethod
    def geometry_matrix(phase: Phase) -> tuple[Vec2, Vec2]:
        # Exact decimal matrices avoid platform trigonometry drift.
        return {
            "crawl": ((D("1"), D("0")), (D("0"), D("1"))),
            "play": ((D("1"), D("0.10")), (D("-0.10"), D("1"))),
            "swaddle": ((D("0.75"), D("0")), (D("0"), D("0.75"))),
            "release": ((D("0.90"), D("0.05")), (D("-0.05"), D("0.90"))),
        }[phase]

    def geometry_matrix_for_state(self, state: SandboxState) -> tuple[Vec2, Vec2]:
        """Return the presented/action frame for one canonical state.

        The base sandbox is intentionally unchanged.  Geometry extensions may
        override this hook to supply a causal local frame without replacing the
        canonical state or reward authority.
        """

        return self.geometry_matrix(self.phase(state))

    def environment_forces(
        self,
        state: SandboxState,
        phase: Phase,
        gravity_scale: Decimal,
    ) -> tuple[Vec2, Vec2]:
        """Return gravity and restoring force for the current state.

        Keeping the two terms separate preserves the exact arithmetic order of
        the original sandbox.  Regional field subclasses can add bounded local
        forces while the default path remains byte-for-byte stable.
        """

        del phase
        gravity = _scale(self.config.gravity, gravity_scale)
        restoring = _scale(state.position, -self.config.restoring_strength)
        return gravity, restoring

    def present_vector(self, state: SandboxState, value: Vec2) -> Vec2:
        """Project one canonical vector into the agent's current view.

        The default remains the original linear presentation exactly.  A
        regional geometry may override this hook with a bounded nonlinear
        projection while leaving canonical state and reward coordinates alone.
        """

        return _matvec(self.geometry_matrix_for_state(state), value)

    @staticmethod
    def _phase_parameters(phase: Phase) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """Return action scale, gravity scale, damping, and frame coupling."""

        return {
            "crawl": (D("0.60"), D("1"), D("0.10"), D("0.35")),
            "play": (D("1"), D("1"), D("0.06"), D("0.55")),
            "swaddle": (D("0"), D("0"), D("0.65"), D("1")),
            "release": (D("0.45"), D("0.35"), D("0.30"), D("0.80")),
        }[phase]

    def _target(self, state: SandboxState) -> Vec2:
        return self.config.targets[state.target_index % len(self.config.targets)]

    def observation(self, state: SandboxState) -> dict[str, Any]:
        phase = self.phase(state)
        matrix = self.geometry_matrix_for_state(state)
        _, _, _, coupling = self._phase_parameters(phase)
        frame_offset = _scale(state.position, -coupling)
        canonical_target = self._target(state)
        presented_position = self.present_vector(
            state, _add(state.position, frame_offset)
        )
        presented_target = self.present_vector(
            state, _add(canonical_target, frame_offset)
        )
        scope_vector = (
            canonical_target[0] - state.position[0],
            canonical_target[1] - state.position[1],
            self.config.world_limit - abs(state.position[0]),
            self.config.world_limit - abs(state.position[1]),
            _norm(state.velocity),
        )
        return {
            "schema": SCHEMA,
            "tick": state.tick,
            "phase": phase,
            "canonical_state_sha256": state.sha256,
            "presented_position": _vec_record(presented_position),
            "presented_target": _vec_record(presented_target),
            "frame_offset": _vec_record(frame_offset),
            "geometry_matrix": [_vec_record(row) for row in matrix],
            "drive_axis": {
                "trit": state.drive_trit,
                "label": DRIVE_LABELS[state.drive_trit],
                "latent_coordinate": [
                    *_vec_record(presented_position),
                    str(state.drive_trit),
                ],
            },
            "scope_vector": [_decimal_text(value) for value in scope_vector],
            "target_index": state.target_index,
            "memory_occupancy": sum(value is not None for value in state.memory),
        }

    @staticmethod
    def _validate_action(action: ToyAction, token: ActionToken) -> None:
        if token.name == "remember":
            if action.slot is None or action.value is None:
                raise ValueError("remember requires a slot and signed 16-bit value")
            if not 0 <= action.slot < MEMORY_SLOTS or not -32768 <= action.value <= 32767:
                raise ValueError("remember argument is outside toy memory")
        elif token.name == "recall":
            if action.slot is None or action.value is not None or not 0 <= action.slot < MEMORY_SLOTS:
                raise ValueError("recall requires one valid slot and no value")
        elif action.slot is not None or action.value is not None:
            raise ValueError("this toy action accepts no argument")

    @staticmethod
    def _action_vector(name: str) -> Vec2:
        return {
            "push_x_positive": (D("1"), D("0")),
            "push_x_negative": (D("-1"), D("0")),
            "push_y_positive": (D("0"), D("1")),
            "push_y_negative": (D("0"), D("-1")),
        }.get(name, (D("0"), D("0")))

    def _bounded_position(self, position: Vec2, velocity: Vec2) -> tuple[Vec2, Vec2]:
        limit = self.config.world_limit
        out_position = list(position)
        out_velocity = list(velocity)
        for axis in range(2):
            if out_position[axis] > limit:
                out_position[axis] = limit
                out_velocity[axis] = D("0")
            elif out_position[axis] < -limit:
                out_position[axis] = -limit
                out_velocity[axis] = D("0")
        return (out_position[0], out_position[1]), (out_velocity[0], out_velocity[1])

    def step(self, state: SandboxState, action: ToyAction, *, tongue: str = "CA") -> tuple[SandboxState, Transition]:
        token = action_token(action.token_id)
        self._validate_action(action, token)
        if tongue not in TONGUES:
            raise ValueError("step tongue lies outside the Six Tongues table")
        phase = self.phase(state)
        action_scale, gravity_scale, damping, _ = self._phase_parameters(phase)
        if state.outburst_ticks_remaining and phase != "swaddle":
            action_scale *= self.config.outcry_force_multiplier
        old_target = self._target(state)
        old_distance = _norm(_sub(old_target, state.position))
        memory = list(state.memory)
        message = "action accepted"
        curiosity_gain = D("0")
        if token.name == "remember":
            assert action.slot is not None and action.value is not None
            memory[action.slot] = action.value
            message = f"stored slot {action.slot}"
        elif token.name == "recall":
            assert action.slot is not None
            message = f"slot {action.slot}={memory[action.slot]}"
        elif token.name == "inspect":
            curiosity_gain = D("0.02")
            message = "bounded state inspected"
        elif token.name == "help":
            message = "available actions: " + ", ".join(ACTION_NAMES)

        raw_action = _scale(self._action_vector(token.name), self.config.action_force * action_scale)
        transformed_action = _matvec(self.geometry_matrix_for_state(state), raw_action)
        gravity, restoring = self.environment_forces(state, phase, gravity_scale)
        drag = _scale(state.velocity, -damping)
        acceleration = _add(_add(transformed_action, gravity), _add(restoring, drag))
        velocity = _add(state.velocity, _scale(acceleration, self.config.dt))
        position = _add(state.position, _scale(velocity, self.config.dt))
        position, velocity = self._bounded_position(position, velocity)

        new_distance = _norm(_sub(old_target, position))
        progress = old_distance - new_distance
        reached = new_distance <= self.config.target_radius
        task_reward = progress - D("0.001")
        target_index = state.target_index
        if reached:
            task_reward += D("1")
            target_index = (target_index + 1) % len(self.config.targets)
        care = D("0.02") if phase == "swaddle" else D("0")
        kinetic_before = _norm(state.velocity)
        kinetic_after = _norm(velocity)
        stability_reward = max(D("0"), kinetic_before - kinetic_after) if phase == "swaddle" else D("0")
        # Swaddle care is deliberately not assigned to the selected action.
        action_credit = D("0") if phase == "swaddle" else task_reward
        reward_trit = 1 if action_credit > 0 else -1 if action_credit < 0 else 0
        if phase == "swaddle":
            drive_trit = 0
            stagnation_ticks = 0
            outburst_ticks_remaining = 0
        elif token.name in {"rest", "inspect", "remember", "recall", "help"}:
            drive_trit = 0
            stagnation_ticks = state.stagnation_ticks
            outburst_ticks_remaining = max(0, state.outburst_ticks_remaining - 1)
        elif action_credit > 0:
            drive_trit = 1
            stagnation_ticks = 0
            outburst_ticks_remaining = 0
        else:
            stagnation_ticks = state.stagnation_ticks + 1
            if stagnation_ticks >= self.config.outcry_trigger_ticks:
                drive_trit = -1
                outburst_ticks_remaining = self.config.outcry_duration_ticks
                stagnation_ticks = 0
            else:
                drive_trit = 0
                outburst_ticks_remaining = max(0, state.outburst_ticks_remaining - 1)
        mobility_gain = _norm(_sub(position, state.position))
        stats = AgentStats(
            mobility=min(D("10"), state.stats.mobility + mobility_gain),
            curiosity=min(D("10"), state.stats.curiosity + curiosity_gain),
            stability=min(D("10"), state.stats.stability + care + stability_reward),
        )
        after_state = SandboxState(
            tick=state.tick + 1,
            position=position,
            velocity=velocity,
            target_index=target_index,
            memory=tuple(memory),
            stats=stats,
            drive_trit=drive_trit,
            stagnation_ticks=stagnation_ticks,
            outburst_ticks_remaining=outburst_ticks_remaining,
        )
        rewards = RewardChannels(task_reward, care, stability_reward, action_credit)
        action_record = {
            "token_id": token.token_id,
            "name": token.name,
            "transport_byte": token.transport_byte,
            "tongue": tongue,
            "skin": action_skin(token.token_id, tongue),
            "slot": action.slot,
            "value": action.value,
            "weight_row": token.weight_row,
            "drive_trit_before": state.drive_trit,
            "outburst_active": bool(state.outburst_ticks_remaining and phase != "swaddle"),
        }
        body = {
            "schema": TRANSITION_SCHEMA,
            "phase": phase,
            "action": action_record,
            "before": state.record(),
            "after": after_state.record(),
            "rewards": rewards.record(),
            "reward_trit": reward_trit,
            "observation": self.observation(after_state),
            "accepted": True,
            "message": message,
        }
        transition = Transition(
            schema=TRANSITION_SCHEMA,
            phase=phase,
            action=action_record,
            before=body["before"],
            after=body["after"],
            rewards=body["rewards"],
            reward_trit=reward_trit,
            observation=body["observation"],
            accepted=True,
            message=message,
            receipt_sha256=sha256_json(body),
        )
        return after_state, transition

    def sieve_actions(
        self,
        state: SandboxState,
        *,
        tongue: str = "CA",
        candidate_ids: Iterable[int] = range(5),
    ) -> tuple[ToyAction, tuple[tuple[int, str, str], ...]]:
        """One-step exact baseline over bounded motor actions.

        Rows contain token id, action-credit reward, and transition digest.  A
        learned policy must beat this baseline rather than being compared to a
        random actor only.
        """

        rows: list[tuple[int, Decimal, str]] = []
        for token_id in sorted(set(int(value) for value in candidate_ids)):
            candidate = ToyAction(token_id)
            _, transition = self.step(state, candidate, tongue=tongue)
            rows.append((token_id, D(transition.rewards["action_credit"]), transition.receipt_sha256))
        if not rows:
            raise ValueError("action sieve needs at least one candidate")
        selected = max(rows, key=lambda row: (row[1], -row[0]))
        ledger = tuple((token_id, _decimal_text(reward), digest) for token_id, reward, digest in rows)
        return ToyAction(selected[0]), ledger


def verify_transition(transition: Transition) -> bool:
    body = {
        "schema": transition.schema,
        "phase": transition.phase,
        "action": transition.action,
        "before": transition.before,
        "after": transition.after,
        "rewards": transition.rewards,
        "reward_trit": transition.reward_trit,
        "observation": transition.observation,
        "accepted": transition.accepted,
        "message": transition.message,
    }
    return transition.schema == TRANSITION_SCHEMA and transition.receipt_sha256 == sha256_json(body)


def curriculum_record(transition: Transition) -> dict[str, Any]:
    """Return one byte/token-exact supervised transition record."""

    if not verify_transition(transition):
        raise ValueError("cannot export an invalid transition")
    return {
        "schema": "clay.developmental-curriculum-record.v1",
        "document_id": transition.receipt_sha256,
        "input": {
            "state": transition.before,
            "action_token_id": transition.action["token_id"],
            "action_transport_byte": transition.action["transport_byte"],
            "action_skin": transition.action["skin"],
            "tongue": transition.action["tongue"],
        },
        "target": {
            "next_state_sha256": sha256_json(transition.after),
            "reward_trit": transition.reward_trit,
            "action_credit": transition.rewards["action_credit"],
            "legal": transition.accepted,
        },
        "provenance": {
            "transition_sha256": transition.receipt_sha256,
            "environment": SCHEMA,
        },
    }


__all__ = [
    "ACTION_BYTES",
    "ACTION_NAMES",
    "CONSOLIDATION_SCHEMA",
    "DRIVE_LABELS",
    "MEMORY_SLOTS",
    "SCHEMA",
    "TONGUES",
    "TRANSITION_SCHEMA",
    "ActionToken",
    "AgentStats",
    "ConsolidationReceipt",
    "DevelopmentalGameSandbox",
    "LifecycleSchedule",
    "RewardChannels",
    "SandboxConfig",
    "SandboxState",
    "ToyAction",
    "Transition",
    "action_skin",
    "action_token",
    "consolidate_weight_vector",
    "curriculum_record",
    "parse_action_skin",
    "verify_consolidation_receipt",
    "verify_transition",
]
