"""Deterministic 4D domino event automaton for the SCBE coding spine.

The engine treats a domino as a small typed process cell.  Its spatial faces
carry ports, its fourth coordinate is event time, and a contact proposes one
ternary transition.  Proposals may move through the lattice, but a commit is
always a separate binary value and is only produced by an exact mirror check.

Clone roles provide directional priority only.  They never create a contact,
validate a port, or override mirror verification.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
from typing import Any, Iterable, Literal, Mapping, Sequence

Trit = Literal[-1, 0, 1]
CommitBit = Literal[0, 1]
PortMode = Literal["in", "out", "io", "closed"]
Boundary = Literal["OPEN", "CLOSED"]
OutcomeWall = Literal["THEOREM", "ENGINEERING", "TURN"]
Coord4 = tuple[int, int, int, int]

FACES = ("left", "right", "back", "front", "base", "top")
FACE_VECTORS: dict[str, tuple[int, int, int]] = {
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
    "back": (0, -1, 0),
    "front": (0, 1, 0),
    "base": (0, 0, -1),
    "top": (0, 0, 1),
}
VECTOR_FACES = {vector: face for face, vector in FACE_VECTORS.items()}
OPPOSITE_FACE = {
    "left": "right",
    "right": "left",
    "back": "front",
    "front": "back",
    "base": "top",
    "top": "base",
}
# The six face headings share the same hexagonal phase vocabulary as the roles.
FACE_ANGLE = {"right": 0, "front": 60, "top": 120, "left": 180, "back": 240, "base": 300}


@dataclass(frozen=True)
class CloneRole:
    name: str
    tongue: str
    direction: tuple[int, int]
    angle: int


CANONICAL_ROLES: tuple[CloneRole, ...] = (
    CloneRole("Scout", "KO", (1, 0), 0),
    CloneRole("Sniper", "AV", (0, 1), 60),
    CloneRole("Support", "RU", (-1, 1), 120),
    CloneRole("Tank", "CA", (-1, 0), 180),
    CloneRole("Assassin", "UM", (0, -1), 240),
    CloneRole("Adjutant", "DR", (1, -1), 300),
)
_ROLE_KEYS = {
    key: role
    for role in CANONICAL_ROLES
    for key in (role.name.lower(), role.tongue.lower(), f"{role.name}/{role.tongue}".lower())
}


@dataclass(frozen=True)
class FacePort:
    """One marked, typed face socket.

    ``mirror`` is an exact contract/signature token.  Empty or unequal mirror
    tokens may still carry a tentative trit, but can never produce a commit.
    """

    mark: str
    port_type: str
    mode: PortMode
    trit: Trit = 0
    mirror: str = ""
    imports: int = 0
    exports: int = 0
    discard: int = 0
    source: str = ""

    def canonical(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Domino:
    domino_id: str
    position: Coord4
    orientation: int
    faces: tuple[tuple[str, FacePort], ...]
    clone_role: CloneRole
    task_lens: str
    provenance: str
    initial_trit: Trit = 0

    def port(self, face: str) -> FacePort:
        for name, port in self.faces:
            if name == face:
                return port
        raise KeyError(face)

    def canonical(self) -> dict[str, Any]:
        return {
            "domino_id": self.domino_id,
            "position": list(self.position),
            "orientation": self.orientation,
            "faces": {face: port.canonical() for face, port in self.faces},
            "clone_role": asdict(self.clone_role),
            "task_lens": self.task_lens,
            "provenance": self.provenance,
            "initial_trit": self.initial_trit,
        }


@dataclass(frozen=True)
class DominoLattice:
    dominoes: tuple[Domino, ...]
    route_id: str
    boundary: Boundary
    configured_total: int
    receipt: str

    def domino(self, domino_id: str) -> Domino:
        for domino in self.dominoes:
            if domino.domino_id == domino_id:
                return domino
        raise KeyError(domino_id)


@dataclass(frozen=True)
class Contact:
    source_id: str
    target_id: str
    source_face: str
    target_face: str
    mark: str
    port_type: str
    event_time: int
    angle: int
    phase: int
    role_alignment: int

    def order_key(self) -> tuple[Any, ...]:
        return (
            self.event_time,
            -self.role_alignment,
            abs(self.phase),
            self.angle,
            self.source_id,
            self.target_id,
            self.source_face,
            self.target_face,
            self.port_type,
            self.mark,
        )


@dataclass(frozen=True)
class AutomatonState:
    lattice_receipt: str
    trits: tuple[tuple[str, Trit], ...]
    commits: tuple[tuple[str, CommitBit], ...]
    total: int
    step: int = 0

    def trit(self, domino_id: str) -> Trit:
        return _pair_value(self.trits, domino_id)

    def committed(self, domino_id: str) -> CommitBit:
        return _pair_value(self.commits, domino_id)

    def canonical(self, *, include_step: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "lattice_receipt": self.lattice_receipt,
            "trits": {key: value for key, value in self.trits},
            "commits": {key: value for key, value in self.commits},
            "total": self.total,
        }
        if include_step:
            payload["step"] = self.step
        return payload


@dataclass(frozen=True)
class ResolvedContact:
    contact: Contact
    proposal: Trit
    verified: CommitBit
    commit: CommitBit
    step: int
    route_id: str
    boundary: Boundary
    imports: int
    exports: int
    discard: int
    source: str
    mechanism: str
    claim_scope: str
    verdict: OutcomeWall
    verdict_basis: str
    hard_verified: CommitBit
    tested_element_set: tuple[str, ...]
    independent_channel: str
    supersedes: str

    def order_key(self) -> tuple[Any, ...]:
        return (self.step, *self.contact.order_key())

    def receipt_payload(self) -> dict[str, Any]:
        payload = {
            "route_id": self.route_id,
            "boundary": self.boundary,
            "imports": self.imports,
            "exports": self.exports,
            "discard": self.discard,
            "source": self.source,
            "mechanism": self.mechanism,
            "claim_scope": self.claim_scope,
            "verdict": self.verdict,
            "verdict_basis": self.verdict_basis,
            "hard_verified": self.hard_verified,
            "tested_element_set": list(self.tested_element_set),
            "independent_channel": self.independent_channel,
            "supersedes": self.supersedes,
            "proposal": self.proposal,
            "magnitude": abs(self.proposal),
            "commit": self.commit,
            "step": self.step,
            "when": {"step": self.step, "event_time": self.contact.event_time},
            "where": {
                "source": f"{self.contact.source_id}:{self.contact.source_face}",
                "target": f"{self.contact.target_id}:{self.contact.target_face}",
            },
            "prior_state": self.supersedes,
            "contact": asdict(self.contact),
        }
        return {"event_id": _canonical_hash(payload), **payload}


@dataclass(frozen=True)
class StepResult:
    state: AutomatonState
    events: tuple[ResolvedContact, ...]
    changed: bool
    receipt: str


@dataclass(frozen=True)
class AutomatonRun:
    status: Literal["fixed_point", "cycle", "step_cap"]
    final_state: AutomatonState
    steps: int
    state_receipts: tuple[str, ...]
    event_steps: tuple[tuple[ResolvedContact, ...], ...]
    cycle_start: int | None
    cycle_length: int | None
    termination_receipt: str


def _exact_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{label} must be an integer, got {type(value).__name__}")
    return value


def _trit(value: Any, label: str = "trit") -> Trit:
    value = _exact_int(value, label)
    if value not in (-1, 0, 1):
        raise ValueError(f"{label} must be one of -1, 0, 1")
    return value  # type: ignore[return-value]


def _sign(value: int) -> Trit:
    return 1 if value > 0 else -1 if value < 0 else 0


def _pair_value(pairs: Sequence[tuple[str, Any]], key: str) -> Any:
    for candidate, value in pairs:
        if candidate == key:
            return value
    raise KeyError(key)


def _canonical_value(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, str):
        return value.replace("\r\n", "\n")
    if value is None or type(value) in (int, float, bool):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _canonical_hash(value: Any) -> str:
    blob = json.dumps(_canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(blob.encode("utf-8")).hexdigest()


def _coerce_role(value: CloneRole | str) -> CloneRole:
    if isinstance(value, CloneRole):
        if value not in CANONICAL_ROLES:
            raise ValueError("clone_role must be one of the six canonical roles")
        return value
    if not isinstance(value, str):
        raise TypeError("clone_role must be a canonical role name or tongue")
    try:
        return _ROLE_KEYS[value.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"unknown clone role: {value!r}") from exc


def _coerce_port(value: FacePort | Mapping[str, Any] | str, face: str) -> FacePort:
    if isinstance(value, FacePort):
        port = value
    elif isinstance(value, str):
        port = FacePort(mark=value, port_type=value, mode="io")
    elif isinstance(value, Mapping):
        port_type = value.get("port_type", value.get("type"))
        if port_type is None:
            raise ValueError(f"face {face!r} is missing port_type")
        port = FacePort(
            mark=str(value.get("mark", "")),
            port_type=str(port_type),
            mode=str(value.get("mode", "io")),  # type: ignore[arg-type]
            trit=_trit(value.get("trit", 0), f"face {face} trit"),
            mirror=str(value.get("mirror", "")),
            imports=_exact_int(value.get("imports", 0), f"face {face} imports"),
            exports=_exact_int(value.get("exports", 0), f"face {face} exports"),
            discard=_exact_int(value.get("discard", 0), f"face {face} discard"),
            source=str(value.get("source", "")),
        )
    else:
        raise TypeError(f"face {face!r} must contain a FacePort, mapping, or string")
    if not port.mark or not port.port_type:
        raise ValueError(f"face {face!r} requires non-empty mark and port_type")
    if port.mode not in ("in", "out", "io", "closed"):
        raise ValueError(f"face {face!r} has invalid port mode {port.mode!r}")
    _trit(port.trit, f"face {face} trit")
    if min(port.imports, port.exports, port.discard) < 0:
        raise ValueError(f"face {face!r} accounting values must be non-negative")
    return port


def _coerce_domino(value: Domino | Mapping[str, Any]) -> Domino:
    if isinstance(value, Domino):
        raw_id = value.domino_id
        raw_position = value.position
        raw_orientation = value.orientation
        raw_faces: Mapping[str, Any] = dict(value.faces)
        raw_role: CloneRole | str = value.clone_role
        raw_lens = value.task_lens
        raw_provenance = value.provenance
        raw_trit = value.initial_trit
    elif isinstance(value, Mapping):
        raw_id = value.get("domino_id", value.get("id", ""))
        raw_position = value.get("position")
        raw_orientation = value.get("orientation")
        raw_faces = value.get("faces", {})
        raw_role = value.get("clone_role", value.get("role", ""))
        raw_lens = value.get("task_lens", "")
        raw_provenance = value.get("provenance", raw_id)
        raw_trit = value.get("initial_trit", value.get("trit", 0))
    else:
        raise TypeError("domino specification must be a Domino or mapping")

    domino_id = str(raw_id).strip()
    if not domino_id:
        raise ValueError("domino_id must be non-empty")
    if not isinstance(raw_position, (tuple, list)) or len(raw_position) != 4:
        raise ValueError(f"domino {domino_id!r} position must contain x, y, z, t")
    position: Coord4 = tuple(
        _exact_int(component, f"domino {domino_id} position[{index}]") for index, component in enumerate(raw_position)
    )  # type: ignore[assignment]
    orientation = _exact_int(raw_orientation, f"domino {domino_id} orientation") % 360
    if not isinstance(raw_faces, Mapping) or set(raw_faces) != set(FACES):
        raise ValueError(f"domino {domino_id!r} must define exactly the six faces {FACES}")
    faces = tuple((face, _coerce_port(raw_faces[face], face)) for face in FACES)
    task_lens = str(raw_lens).strip()
    if not task_lens:
        raise ValueError(f"domino {domino_id!r} task_lens must be non-empty")
    provenance = str(raw_provenance).strip()
    if not provenance:
        raise ValueError(f"domino {domino_id!r} provenance must be non-empty")
    return Domino(
        domino_id=domino_id,
        position=position,
        orientation=orientation,
        faces=faces,
        clone_role=_coerce_role(raw_role),
        task_lens=task_lens,
        provenance=provenance,
        initial_trit=_trit(raw_trit, f"domino {domino_id} initial_trit"),
    )


def compile_domino_lattice(
    dominoes: Iterable[Domino | Mapping[str, Any]],
    *,
    route_id: str = "domino-route",
    boundary: Boundary = "CLOSED",
    configured_total: int | None = None,
) -> DominoLattice:
    """Validate and canonicalize domino cells into a receipt-bound lattice."""
    compiled = tuple(sorted((_coerce_domino(domino) for domino in dominoes), key=lambda item: item.domino_id))
    ids = [domino.domino_id for domino in compiled]
    positions = [domino.position for domino in compiled]
    if len(ids) != len(set(ids)):
        raise ValueError("domino_id values must be unique")
    if len(positions) != len(set(positions)):
        raise ValueError("4D domino positions must be unique")
    route_id = str(route_id).strip()
    if not route_id:
        raise ValueError("route_id must be non-empty")
    if boundary not in ("OPEN", "CLOSED"):
        raise ValueError("boundary must be OPEN or CLOSED")
    total = len(compiled) if configured_total is None else _exact_int(configured_total, "configured_total")
    if total < 0:
        raise ValueError("configured_total must be non-negative")
    payload = {
        "schema": "scbe_domino_event_lattice_v1",
        "route_id": route_id,
        "boundary": boundary,
        "configured_total": total,
        "dominoes": [item.canonical() for item in compiled],
    }
    return DominoLattice(
        dominoes=compiled,
        route_id=route_id,
        boundary=boundary,
        configured_total=total,
        receipt=_canonical_hash(payload),
    )


def _ports_compatible(source: FacePort, target: FacePort) -> bool:
    return (
        source.mode in ("out", "io")
        and target.mode in ("in", "io")
        and source.mark == target.mark
        and source.port_type == target.port_type
    )


def _contact(source: Domino, target: Domino, source_face: str, target_face: str) -> Contact:
    source_port = source.port(source_face)
    sx, sy, _, st = source.position
    tx, ty, _, tt = target.position
    # Rotate the target outward normal by 180 degrees so perfect face alignment is zero.
    angle = (source.orientation + FACE_ANGLE[source_face] - (target.orientation + FACE_ANGLE[target_face] + 180)) % 360
    role_dx, role_dy = source.clone_role.direction
    return Contact(
        source_id=source.domino_id,
        target_id=target.domino_id,
        source_face=source_face,
        target_face=target_face,
        mark=source_port.mark,
        port_type=source_port.port_type,
        event_time=max(st, tt),
        angle=angle,
        phase=tt - st,
        role_alignment=(tx - sx) * role_dx + (ty - sy) * role_dy,
    )


def detect_contacts(lattice: DominoLattice) -> tuple[Contact, ...]:
    """Detect typed face contacts and return a total deterministic event order."""
    contacts: list[Contact] = []
    for index, left in enumerate(lattice.dominoes):
        lx, ly, lz, _ = left.position
        for right in lattice.dominoes[index + 1 :]:
            rx, ry, rz, _ = right.position
            delta = (rx - lx, ry - ly, rz - lz)
            if delta not in VECTOR_FACES:
                continue
            left_face = VECTOR_FACES[delta]
            right_face = OPPOSITE_FACE[left_face]
            left_port = left.port(left_face)
            right_port = right.port(right_face)
            if _ports_compatible(left_port, right_port):
                contacts.append(_contact(left, right, left_face, right_face))
            if _ports_compatible(right_port, left_port):
                contacts.append(_contact(right, left, right_face, left_face))
    return tuple(sorted(contacts, key=Contact.order_key))


def _initial_state(lattice: DominoLattice) -> AutomatonState:
    return AutomatonState(
        lattice_receipt=lattice.receipt,
        trits=tuple((domino.domino_id, domino.initial_trit) for domino in lattice.dominoes),
        commits=tuple((domino.domino_id, 0) for domino in lattice.dominoes),
        total=lattice.configured_total,
    )


def _coerce_state(lattice: DominoLattice, state: AutomatonState | Mapping[str, int] | None) -> AutomatonState:
    if state is None:
        return _initial_state(lattice)
    expected_ids = tuple(domino.domino_id for domino in lattice.dominoes)
    if isinstance(state, AutomatonState):
        if state.lattice_receipt != lattice.receipt:
            raise ValueError("automaton state belongs to a different lattice")
        if tuple(key for key, _ in state.trits) != expected_ids:
            raise ValueError("automaton state trit ids do not match the lattice")
        if tuple(key for key, _ in state.commits) != expected_ids:
            raise ValueError("automaton state commit ids do not match the lattice")
        for key, value in state.trits:
            _trit(value, f"state trit {key}")
        for key, value in state.commits:
            if type(value) is not int or value not in (0, 1):
                raise ValueError(f"state commit {key} must be binary")
        _exact_int(state.total, "state total")
        if state.total < 0:
            raise ValueError("state total must be non-negative")
        return state
    if set(state) != set(expected_ids):
        raise ValueError("state mapping ids must exactly match the lattice")
    return AutomatonState(
        lattice_receipt=lattice.receipt,
        trits=tuple((key, _trit(state[key], f"state trit {key}")) for key in expected_ids),
        commits=tuple((key, 0) for key in expected_ids),
        total=lattice.configured_total,
    )


def verify_mirrors(left: Any, right: Any) -> CommitBit:
    """Return one only for exact canonical mirrors; unsupported values fail closed."""
    try:
        return int(_canonical_value(left) == _canonical_value(right))  # type: ignore[return-value]
    except (TypeError, ValueError):
        return 0


def _angle_gate(angle: int) -> Trit:
    # Quantize into the six role/face sectors: forward, shoulder, hold, inverse, hold, shoulder.
    sector = ((angle + 30) // 60) % 6
    return (1, 1, 0, -1, 0, 1)[sector]  # type: ignore[return-value]


def resolve_contact(
    lattice: DominoLattice,
    contact: Contact,
    state: AutomatonState | Mapping[str, int] | None = None,
) -> ResolvedContact:
    """Resolve one contact into a tentative trit plus a hard binary commit bit."""
    current = _coerce_state(lattice, state)
    source = lattice.domino(contact.source_id)
    target = lattice.domino(contact.target_id)
    source_port = source.port(contact.source_face)
    target_port = target.port(contact.target_face)
    if not _ports_compatible(source_port, target_port):
        raise ValueError("contact ports are no longer compatible with the lattice")

    signal = _sign(current.trit(source.domino_id) + source_port.trit + target_port.trit)
    temporal_gate = -1 if contact.phase < 0 else 1
    proposal = _trit(signal * _angle_gate(contact.angle) * temporal_gate, "resolved proposal")
    verified: CommitBit = (
        verify_mirrors(source_port.mirror, target_port.mirror) if source_port.mirror and target_port.mirror else 0
    )
    commit: CommitBit = int(proposal == 1 and verified == 1)  # type: ignore[assignment]
    imports = target_port.imports
    exports = source_port.exports
    discard = source_port.discard + target_port.discard
    external_source = target_port.source or source_port.source
    delta = imports - exports - discard
    if lattice.boundary == "CLOSED" and delta != 0:
        raise ValueError("CLOSED contact violates configured-total conservation")
    if lattice.boundary == "OPEN" and (imports or exports or discard) and not external_source:
        raise ValueError("OPEN contact accounting requires an explicit source")
    if verified and proposal < 0:
        verdict: OutcomeWall = "THEOREM"
        verdict_basis = "verified_negative_constraint"
    elif verified:
        verdict = "ENGINEERING"
        verdict_basis = "exact_mirror_positive" if commit else "exact_mirror_neutral"
    else:
        verdict = "TURN"
        verdict_basis = "mirror_not_proven"
    source_channel = source_port.source.strip()
    target_channel = target_port.source.strip()
    independent_channel = (
        f"DECLARED_DISTINCT:{source_channel}->{target_channel}"
        if source_channel and target_channel and source_channel != target_channel
        else "UNPROVEN"
    )
    return ResolvedContact(
        contact=contact,
        proposal=proposal,
        verified=verified,
        commit=commit,
        step=current.step + 1,
        route_id=lattice.route_id,
        boundary=lattice.boundary,
        imports=imports,
        exports=exports,
        discard=discard,
        source=external_source or source.provenance,
        mechanism=f"typed_face_contact:{source_port.port_type}",
        claim_scope=target.task_lens,
        verdict=verdict,
        verdict_basis=verdict_basis,
        hard_verified=verified,
        tested_element_set=(
            f"{source.domino_id}:{contact.source_face}",
            f"{target.domino_id}:{contact.target_face}",
            contact.mark,
            contact.port_type,
        ),
        independent_channel=independent_channel,
        supersedes=state_receipt(current),
    )


def state_receipt(value: AutomatonState | DominoLattice | Mapping[str, Any]) -> str:
    """Hash a canonical semantic state.  Step number is intentionally excluded."""
    if isinstance(value, DominoLattice):
        return value.receipt
    if isinstance(value, AutomatonState):
        return _canonical_hash(value.canonical(include_step=False))
    return _canonical_hash(value)


def step_automaton(
    lattice: DominoLattice,
    state: AutomatonState | Mapping[str, int] | None = None,
    contacts: Iterable[Contact] | None = None,
) -> StepResult:
    """Apply one synchronous event step; event order cannot change the result."""
    current = _coerce_state(lattice, state)
    ordered_contacts = tuple(
        sorted(contacts if contacts is not None else detect_contacts(lattice), key=Contact.order_key)
    )
    events = tuple(resolve_contact(lattice, contact, current) for contact in ordered_contacts)
    incoming: dict[str, list[ResolvedContact]] = {domino.domino_id: [] for domino in lattice.dominoes}
    for event in events:
        incoming[event.contact.target_id].append(event)

    next_trits: list[tuple[str, Trit]] = []
    next_commits: list[tuple[str, CommitBit]] = []
    for domino in lattice.dominoes:
        target_events = incoming[domino.domino_id]
        if target_events:
            next_trit = _sign(sum(event.proposal for event in target_events))
        else:
            next_trit = current.trit(domino.domino_id)
        active = [event for event in target_events if event.proposal != 0]
        if active:
            verified_positive = (
                next_trit == 1
                and all(event.verified == 1 for event in active)
                and all(event.proposal >= 0 for event in active)
                and any(event.commit == 1 for event in active)
            )
            next_commit: CommitBit = int(verified_positive)  # type: ignore[assignment]
        else:
            next_commit = current.committed(domino.domino_id) if next_trit == 1 else 0
        next_trits.append((domino.domino_id, next_trit))
        next_commits.append((domino.domino_id, next_commit))

    next_state = AutomatonState(
        lattice_receipt=lattice.receipt,
        trits=tuple(next_trits),
        commits=tuple(next_commits),
        total=current.total + sum(event.imports - event.exports - event.discard for event in events),
        step=current.step + 1,
    )
    if next_state.total < 0:
        raise ValueError("transition accounting produced a negative configured total")
    if lattice.boundary == "CLOSED" and next_state.total != current.total:
        raise ValueError("CLOSED transition failed configured-total conservation")
    receipt = state_receipt(next_state)
    return StepResult(
        state=next_state,
        events=events,
        changed=receipt != state_receipt(current),
        receipt=receipt,
    )


def run_until_quiescent(
    lattice: DominoLattice,
    state: AutomatonState | Mapping[str, int] | None = None,
    *,
    max_steps: int = 64,
) -> AutomatonRun:
    """Run until a fixed point, a proven repeated state, or the explicit step cap."""
    max_steps = _exact_int(max_steps, "max_steps")
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    current = _coerce_state(lattice, state)
    initial_receipt = state_receipt(current)
    seen = {initial_receipt: 0}
    receipts = [initial_receipt]
    event_steps: list[tuple[ResolvedContact, ...]] = []
    contacts = detect_contacts(lattice)
    status: Literal["fixed_point", "cycle", "step_cap"] = "step_cap"
    cycle_start: int | None = None
    cycle_length: int | None = None

    for step in range(1, max_steps + 1):
        result = step_automaton(lattice, current, contacts)
        current = result.state
        receipts.append(result.receipt)
        event_steps.append(result.events)
        if not result.changed:
            status = "fixed_point"
            break
        if result.receipt in seen:
            status = "cycle"
            cycle_start = seen[result.receipt]
            cycle_length = step - cycle_start
            break
        seen[result.receipt] = step

    steps = len(event_steps)
    termination_payload = {
        "schema": "scbe_domino_automaton_run_v1",
        "status": status,
        "steps": steps,
        "state_receipts": receipts,
        "cycle_start": cycle_start,
        "cycle_length": cycle_length,
        "final_state": current.canonical(include_step=True),
        "events": [event.receipt_payload() for event_step in event_steps for event in event_step],
    }
    return AutomatonRun(
        status=status,
        final_state=current,
        steps=steps,
        state_receipts=tuple(receipts),
        event_steps=tuple(event_steps),
        cycle_start=cycle_start,
        cycle_length=cycle_length,
        termination_receipt=_canonical_hash(termination_payload),
    )


def emit_loom_program(
    source: StepResult | AutomatonRun | Iterable[ResolvedContact],
) -> str:
    """Emit a deterministic Loom counter program for the resolved event trace."""
    if isinstance(source, StepResult):
        events = list(source.events)
    elif isinstance(source, AutomatonRun):
        events = [event for event_step in source.event_steps for event in event_step]
    else:
        events = list(source)
    events.sort(key=ResolvedContact.order_key)

    lines = ["# scbe_domino_event_loom_v1"]
    for event in events:
        contact = event.contact
        lines.append(
            f"# step={event.step} time={contact.event_time} {contact.source_id}:{contact.source_face}"
            f"->{contact.target_id}:{contact.target_face} angle={contact.angle} phase={contact.phase}"
        )
        lines.append(
            f"# route={event.route_id} boundary={event.boundary} verdict={event.verdict}"
            f" hard_verified={event.hard_verified} imports={event.imports} exports={event.exports}"
            f" discard={event.discard}"
        )
        lines.append("inc events")
        lines.append("inc positive" if event.proposal > 0 else "inc negative" if event.proposal < 0 else "inc neutral")
        if event.verified:
            lines.append("inc verified")
        if event.commit:
            lines.append("inc commits")
    lines.extend(("out events", "out commits", "out verified", "halt"))
    return "\n".join(lines)


__all__ = [
    "AutomatonRun",
    "AutomatonState",
    "Boundary",
    "CANONICAL_ROLES",
    "CloneRole",
    "Contact",
    "Domino",
    "DominoLattice",
    "FacePort",
    "FACES",
    "ResolvedContact",
    "StepResult",
    "compile_domino_lattice",
    "detect_contacts",
    "emit_loom_program",
    "resolve_contact",
    "run_until_quiescent",
    "state_receipt",
    "step_automaton",
    "verify_mirrors",
]
