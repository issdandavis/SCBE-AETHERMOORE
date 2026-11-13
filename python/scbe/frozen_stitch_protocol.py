"""Thin, typed stitch protocols for frozen SCBE components.

The registry names the supported boundaries without pretending that every
component shares one runtime.  A stitch is a bounded adapter envelope: it may
carry a small declared delta, but it cannot mutate a frozen component or grant
execution authority.  Every envelope receives an ordinary reaction-state
receipt so the existing ledger remains the audit substrate.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, replace
from types import MappingProxyType
from typing import Any, Literal, Sequence

from .reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    ReactionStatePacket,
    build_reaction_state_packet,
    packet_from_dict,
    sha256_value,
)

STITCH_ENVELOPE_SCHEMA = "scbe_frozen_stitch_envelope_v1"
STITCH_REGISTRY_SCHEMA = "scbe_frozen_stitch_registry_v1"

FreezePolicy = Literal[
    "FROZEN_CORE", "BOUNDED_STITCH", "TELEMETRY_ONLY", "DETERMINISTIC_GATE"
]
Authority = Literal[
    "PROPOSE_ONLY", "OBSERVE_ONLY", "VALIDATE_ONLY", "EXECUTE_AFTER_GATE"
]

VALID_FREEZE_POLICIES = frozenset(
    {"FROZEN_CORE", "BOUNDED_STITCH", "TELEMETRY_ONLY", "DETERMINISTIC_GATE"}
)
VALID_AUTHORITIES = frozenset(
    {"PROPOSE_ONLY", "OBSERVE_ONLY", "VALIDATE_ONLY", "EXECUTE_AFTER_GATE"}
)
COMPILER_COMPONENT_ID = "action.compiler"
COMPILER_CONTRACT_ID = "stitch.compiler-to-reentry"
COMPILER_GATE_DECISIONS = ("ALLOW", "DENY", "QUARANTINE", "ESCALATE")
REQUIRED_STITCH_ENGRAVING = "frozen component boundary preserved"
STITCH_CLAIM_BOUNDARY = (
    "stitch transports validated state; it does not prove neural benefit",
    "learned or geometric values do not bypass the deterministic action gate",
)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _strict_json(value: Any, *, name: str) -> str:
    """Canonicalize one detached, finite JSON value.

    Storing canonical text keeps a frozen envelope deeply immutable even when
    the caller later mutates its original dictionaries or lists.
    """

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite JSON data") from exc
    # Round-trip once so tuples and custom mapping subclasses cannot retain
    # caller-owned aliases or representation-dependent behavior.
    decoded = json.loads(encoded)
    return json.dumps(
        decoded,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _decode_json_object(value: str, *, name: str) -> dict[str, Any]:
    decoded = json.loads(value)
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) for key in decoded
    ):
        raise ValueError(f"{name} must encode a JSON object")
    return decoded


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    component_id: str
    role: str
    input_schema: str
    output_schema: str
    freeze_policy: FreezePolicy
    authority: Authority
    implementation_status: str
    evidence_receipt_sha256: str | None = None
    evidence_status: str | None = None
    implementation_source_sha256: str | None = None
    implementation_sections: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "implementation_sections", tuple(self.implementation_sections)
        )
        if not all(
            (
                self.component_id,
                self.role,
                self.input_schema,
                self.output_schema,
                self.implementation_status,
            )
        ):
            raise ValueError("component fields must not be empty")
        if self.freeze_policy not in VALID_FREEZE_POLICIES:
            raise ValueError("component freeze_policy is not recognized")
        if self.authority not in VALID_AUTHORITIES:
            raise ValueError("component authority is not recognized")
        if self.evidence_receipt_sha256 is not None and not _is_sha256(
            self.evidence_receipt_sha256
        ):
            raise ValueError("evidence_receipt_sha256 must be a SHA-256 digest")
        if (self.evidence_receipt_sha256 is None) != (self.evidence_status is None):
            raise ValueError("evidence receipt and status must be supplied together")
        if self.implementation_source_sha256 is not None and not _is_sha256(
            self.implementation_source_sha256
        ):
            raise ValueError("implementation_source_sha256 must be a SHA-256 digest")
        if len(self.implementation_sections) != len(set(self.implementation_sections)):
            raise ValueError("implementation_sections must be unique")


@dataclass(frozen=True, slots=True)
class StitchContract:
    contract_id: str
    source_component: str
    target_component: str
    payload_schema: str
    required_payload_keys: tuple[str, ...]
    parameter_slots: tuple[str, ...] = ()
    sha256_payload_keys: tuple[str, ...] = ()
    boolean_payload_keys: tuple[str, ...] = ()
    enum_payload_values: tuple[tuple[str, tuple[str, ...]], ...] = ()
    max_abs_delta: float = 1.0
    max_payload_bytes: int = 65_536

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "required_payload_keys", tuple(self.required_payload_keys)
        )
        object.__setattr__(self, "parameter_slots", tuple(self.parameter_slots))
        object.__setattr__(self, "sha256_payload_keys", tuple(self.sha256_payload_keys))
        object.__setattr__(
            self, "boolean_payload_keys", tuple(self.boolean_payload_keys)
        )
        object.__setattr__(
            self,
            "enum_payload_values",
            tuple(
                (str(name), tuple(values)) for name, values in self.enum_payload_values
            ),
        )
        if (
            not self.contract_id
            or not self.source_component
            or not self.target_component
        ):
            raise ValueError("stitch identity fields must not be empty")
        if not self.payload_schema:
            raise ValueError("payload_schema must not be empty")
        if not math.isfinite(self.max_abs_delta) or self.max_abs_delta <= 0.0:
            raise ValueError("max_abs_delta must be finite and positive")
        if self.max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be positive")
        if len(self.required_payload_keys) != len(set(self.required_payload_keys)):
            raise ValueError("required_payload_keys must be unique")
        if len(self.parameter_slots) != len(set(self.parameter_slots)):
            raise ValueError("parameter_slots must be unique")
        required = set(self.required_payload_keys)
        typed = set(self.sha256_payload_keys) | set(self.boolean_payload_keys)
        enum_keys = [name for name, _values in self.enum_payload_values]
        typed.update(enum_keys)
        if not typed <= required:
            raise ValueError("typed payload keys must also be required payload keys")
        if len(enum_keys) != len(set(enum_keys)):
            raise ValueError("enum payload keys must be unique")
        for name, values in self.enum_payload_values:
            if not name or not values or len(values) != len(set(values)):
                raise ValueError("enum payload rules require a name and unique values")


@dataclass(frozen=True, slots=True)
class StitchEnvelope:
    """One replayable handoff between two registered frozen boundaries."""

    contract_id: str
    source_component: str
    target_component: str
    identity_root: str
    runtime_profile: str
    step_clock: int
    context_epoch: int
    payload_schema: str
    payload_json: str
    payload_sha256: str
    adapter_delta_json: str
    previous_stitch_hash: str | None
    previous_reaction_packet_hash: str | None
    reaction_packet_json: str
    stitch_hash: str | None = None
    schema_version: str = STITCH_ENVELOPE_SCHEMA

    @property
    def payload(self) -> dict[str, Any]:
        """Return a detached JSON value; callers cannot mutate the sealed receipt."""

        return _decode_json_object(self.payload_json, name="payload")

    @property
    def adapter_delta(self) -> dict[str, float]:
        decoded = _decode_json_object(self.adapter_delta_json, name="adapter_delta")
        return {str(name): float(value) for name, value in decoded.items()}

    @property
    def reaction_packet(self) -> ReactionStatePacket:
        return packet_from_dict(
            _decode_json_object(self.reaction_packet_json, name="reaction_packet")
        )

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "source_component": self.source_component,
            "target_component": self.target_component,
            "identity_root": self.identity_root,
            "runtime_profile": self.runtime_profile,
            "step_clock": self.step_clock,
            "context_epoch": self.context_epoch,
            "payload_schema": self.payload_schema,
            "payload": self.payload,
            "payload_sha256": self.payload_sha256,
            "adapter_delta": self.adapter_delta,
            "previous_stitch_hash": self.previous_stitch_hash,
            "previous_reaction_packet_hash": self.previous_reaction_packet_hash,
            "reaction_packet": self.reaction_packet.to_dict(),
            "schema_version": self.schema_version,
        }

    def compute_hash(self) -> str:
        return sha256_value(self.unsigned_dict())

    def with_hash(self) -> "StitchEnvelope":
        return replace(self, stitch_hash=self.compute_hash())

    def verify(self, registry: "StitchRegistry" | None = None) -> bool:
        try:
            if self.schema_version != STITCH_ENVELOPE_SCHEMA:
                return False
            if not self.stitch_hash or self.stitch_hash != self.compute_hash():
                return False
            if self.payload_sha256 != sha256_value(self.payload):
                return False
            packet = self.reaction_packet
            if not packet.verify_hash():
                return False
            if packet.source.identity != self.identity_root:
                return False
            if packet.target.identity != self.identity_root:
                return False
            if packet.source.payload_sha256 != self.payload_sha256:
                return False
            if packet.target.payload_sha256 != self.payload_sha256:
                return False
            if packet.previous_packet_hash != self.previous_reaction_packet_hash:
                return False
            if registry is not None:
                registry.validate_envelope(self)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False
        return True


class StitchRegistry:
    """Structurally immutable registry for component and boundary contracts."""

    __slots__ = (
        "_components",
        "_contracts",
        "_component_by_id",
        "_contract_by_id",
    )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("StitchRegistry is immutable")

    def __init__(
        self, components: Sequence[ComponentSpec], contracts: Sequence[StitchContract]
    ) -> None:
        component_tuple = tuple(components)
        contract_tuple = tuple(contracts)
        component_by_id = MappingProxyType(
            {component.component_id: component for component in component_tuple}
        )
        contract_by_id = MappingProxyType(
            {contract.contract_id: contract for contract in contract_tuple}
        )
        object.__setattr__(self, "_components", component_tuple)
        object.__setattr__(self, "_contracts", contract_tuple)
        object.__setattr__(self, "_component_by_id", component_by_id)
        object.__setattr__(self, "_contract_by_id", contract_by_id)
        if len(self._component_by_id) != len(self.components):
            raise ValueError("component_id values must be unique")
        if len(self._contract_by_id) != len(self.contracts):
            raise ValueError("contract_id values must be unique")
        for contract in self.contracts:
            if contract.source_component not in self._component_by_id:
                raise ValueError(f"unknown stitch source: {contract.source_component}")
            if contract.target_component not in self._component_by_id:
                raise ValueError(f"unknown stitch target: {contract.target_component}")
            source = self.component(contract.source_component)
            target = self.component(contract.target_component)
            if contract.payload_schema != source.output_schema:
                raise ValueError(
                    f"{contract.contract_id} payload schema does not match "
                    f"{source.component_id} output schema"
                )
            if contract.payload_schema != target.input_schema:
                raise ValueError(
                    f"{contract.contract_id} payload schema does not match "
                    f"{target.component_id} input schema"
                )
        executable = tuple(
            component
            for component in self.components
            if component.authority == "EXECUTE_AFTER_GATE"
        )
        if any(
            component.component_id != COMPILER_COMPONENT_ID for component in executable
        ):
            raise ValueError("execution authority is restricted to action.compiler")
        if COMPILER_COMPONENT_ID in self._component_by_id:
            compiler = self.component(COMPILER_COMPONENT_ID)
            if (
                compiler.authority != "EXECUTE_AFTER_GATE"
                or compiler.freeze_policy != "DETERMINISTIC_GATE"
            ):
                raise ValueError(
                    "action.compiler must retain deterministic gated authority"
                )
        if COMPILER_CONTRACT_ID in self._contract_by_id:
            compiler_contract = self.contract(COMPILER_CONTRACT_ID)
            enum_rules = dict(compiler_contract.enum_payload_values)
            if (
                compiler_contract.source_component != COMPILER_COMPONENT_ID
                or "gate_decision" not in compiler_contract.required_payload_keys
                or enum_rules.get("gate_decision") != COMPILER_GATE_DECISIONS
            ):
                raise ValueError(
                    "compiler stitch must retain the canonical gate-decision policy"
                )

    @property
    def components(self) -> tuple[ComponentSpec, ...]:
        return self._components

    @property
    def contracts(self) -> tuple[StitchContract, ...]:
        return self._contracts

    def component(self, component_id: str) -> ComponentSpec:
        try:
            return self._component_by_id[component_id]
        except KeyError as exc:
            raise ValueError(f"unknown component: {component_id}") from exc

    def contract(self, contract_id: str) -> StitchContract:
        try:
            return self._contract_by_id[contract_id]
        except KeyError as exc:
            raise ValueError(f"unknown stitch contract: {contract_id}") from exc

    def validate_path(self, contract_ids: Sequence[str]) -> tuple[StitchContract, ...]:
        if not contract_ids:
            raise ValueError("a stitch path requires at least one contract")
        contracts = tuple(self.contract(contract_id) for contract_id in contract_ids)
        for contract in contracts:
            source = self.component(contract.source_component)
            target = self.component(contract.target_component)
            if not (
                source.output_schema == contract.payload_schema == target.input_schema
            ):
                raise ValueError(
                    f"wire schema mismatch at {contract.contract_id}: "
                    f"{source.output_schema!r} -> {contract.payload_schema!r} -> "
                    f"{target.input_schema!r}"
                )
        for left, right in zip(contracts, contracts[1:]):
            if left.target_component != right.source_component:
                raise ValueError(
                    f"stitch path gap: {left.contract_id} ends at {left.target_component}, "
                    f"but {right.contract_id} starts at {right.source_component}"
                )
        return contracts

    def validate_envelope(self, envelope: StitchEnvelope) -> None:
        contract = self.contract(envelope.contract_id)
        source = self.component(contract.source_component)
        target = self.component(contract.target_component)
        if envelope.source_component != contract.source_component:
            raise ValueError("envelope source does not match the stitch contract")
        if envelope.target_component != contract.target_component:
            raise ValueError("envelope target does not match the stitch contract")
        if envelope.payload_schema != contract.payload_schema:
            raise ValueError(
                "envelope payload schema does not match the stitch contract"
            )
        missing = set(contract.required_payload_keys) - set(envelope.payload)
        if missing:
            raise ValueError(
                f"stitch payload is missing required keys: {sorted(missing)}"
            )
        encoded_size = len(
            _strict_json(envelope.payload, name="payload").encode("utf-8")
        )
        if encoded_size > contract.max_payload_bytes:
            raise ValueError("stitch payload exceeds the contract byte limit")
        for name in contract.sha256_payload_keys:
            if not _is_sha256(envelope.payload.get(name)):
                raise ValueError(f"payload field {name!r} must be a SHA-256 digest")
        for name in contract.boolean_payload_keys:
            if not isinstance(envelope.payload.get(name), bool):
                raise ValueError(f"payload field {name!r} must be boolean")
        for name, allowed in contract.enum_payload_values:
            if envelope.payload.get(name) not in allowed:
                raise ValueError(
                    f"payload field {name!r} must be one of {list(allowed)!r}"
                )
        unknown_slots = set(envelope.adapter_delta) - set(contract.parameter_slots)
        if unknown_slots:
            raise ValueError(f"unknown adapter delta slots: {sorted(unknown_slots)}")
        for name, value in envelope.adapter_delta.items():
            if not math.isfinite(value) or abs(value) > contract.max_abs_delta:
                raise ValueError(
                    f"adapter delta {name!r} must be finite and within "
                    f"[-{contract.max_abs_delta}, {contract.max_abs_delta}]"
                )
        if envelope.step_clock < 0 or envelope.context_epoch < 0:
            raise ValueError("step_clock and context_epoch must be non-negative")
        if not envelope.identity_root or not envelope.runtime_profile:
            raise ValueError("identity_root and runtime_profile are required")

        packet = envelope.reaction_packet
        if packet.schema_version != "scbe_reaction_state_packet_v1":
            raise ValueError(
                "reaction packet schema does not match the stitch contract"
            )
        if packet.step != envelope.step_clock:
            raise ValueError("reaction packet step does not match the stitch clock")
        if packet.bounded_operation != contract.contract_id:
            raise ValueError(
                "reaction packet operation does not match the stitch contract"
            )
        if packet.source.representation != source.output_schema:
            raise ValueError(
                "reaction source representation does not match the wire schema"
            )
        if packet.target.representation != target.input_schema:
            raise ValueError(
                "reaction target representation does not match the wire schema"
            )
        if packet.source.metadata.get("component_id") != source.component_id:
            raise ValueError("reaction source component metadata does not match")
        if packet.target.metadata.get("component_id") != target.component_id:
            raise ValueError("reaction target component metadata does not match")
        if packet.domain != "mixed":
            raise ValueError("stitch reaction packets must use the mixed domain")
        if packet.source.metadata != {"component_id": source.component_id}:
            raise ValueError("reaction source metadata contains undeclared fields")
        if packet.target.metadata != {"component_id": target.component_id}:
            raise ValueError("reaction target metadata contains undeclared fields")
        if any(
            value is not None
            for value in (
                packet.source.language,
                packet.source.tongue,
                packet.target.language,
                packet.target.tongue,
            )
        ):
            raise ValueError(
                "stitch reaction endpoints contain undeclared routing tags"
            )
        recalculation = packet.recalculation
        if (
            recalculation.syntax_ok is not True
            or recalculation.unit_checks_ok is not True
            or recalculation.identity_ok is not True
        ):
            raise ValueError("reaction packet lacks required affirmative checks")
        if (
            recalculation.tests_ok is not None
            or recalculation.scientific_checks_ok is not None
        ):
            raise ValueError("reaction packet claims undeclared checks")
        if set(recalculation.extra) != {
            "context_epoch",
            "adapter_delta",
            "stitch_registry_hash",
        }:
            raise ValueError("reaction recalculation contains undeclared fields")
        if recalculation.extra.get("context_epoch") != envelope.context_epoch:
            raise ValueError("reaction context epoch does not match the envelope")
        if recalculation.extra.get("adapter_delta") != envelope.adapter_delta:
            raise ValueError("reaction adapter delta does not match the envelope")
        if recalculation.extra.get("stitch_registry_hash") != self.manifest_hash:
            raise ValueError("reaction packet is not bound to this stitch registry")
        if packet.classification != "BIJECTIVE":
            raise ValueError("stitch packets must preserve declared identity")
        expected_engravings = [
            REQUIRED_STITCH_ENGRAVING,
            f"payload schema: {contract.payload_schema}",
            f"runtime profile: {envelope.runtime_profile}",
        ]
        if packet.semantic_engravings != expected_engravings:
            raise ValueError("reaction semantic engravings do not match the stitch")
        if packet.loss_notes:
            raise ValueError("bijective stitch packets cannot declare unbound loss")
        if packet.claim_boundary != list(STITCH_CLAIM_BOUNDARY):
            raise ValueError("reaction claim boundary does not match the stitch policy")
        if any(
            value is not None
            for value in (
                packet.signature,
                packet.signature_alg,
                packet.signer_public_key,
            )
        ):
            raise ValueError("stitch envelopes carry unsigned audit packets only")

        # Authority is enforced at the only executable boundary. The envelope
        # remains an unsigned audit receipt, not an execution credential.
        if source.authority == "EXECUTE_AFTER_GATE" or (
            contract.contract_id == COMPILER_CONTRACT_ID
            or source.component_id == COMPILER_COMPONENT_ID
        ):
            if (
                contract.contract_id != COMPILER_CONTRACT_ID
                or source.component_id != COMPILER_COMPONENT_ID
                or source.authority != "EXECUTE_AFTER_GATE"
            ):
                raise ValueError("executable authority appeared on an unknown boundary")
            if envelope.payload.get("gate_decision") not in COMPILER_GATE_DECISIONS:
                raise ValueError("compiler gate decision is not recognized")

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": STITCH_REGISTRY_SCHEMA,
            "components": [asdict(component) for component in self.components],
            "contracts": [asdict(contract) for contract in self.contracts],
        }

    @property
    def manifest_hash(self) -> str:
        return sha256_value(self.manifest())


REFERENCE14_IMPLEMENTATION_SECTIONS = (
    "layer_0_intent_modulation",
    "layer_1_complex_state",
    "layer_2_realification",
    "layer_3_weighted_transform",
    "layer_4_poincare_embedding",
    "layer_5_hyperbolic_distance",
    "layer_6_breathing_transform",
    "layer_7_phase_transform",
    "layer_8_realm_distance",
    "layer_9_spectral_observation",
    "layer_10_spin_coherence",
    "layer_11_triadic_temporal",
    "layer_12_harmonic_scaling",
    "layer_14_audio_axis",
    "layer_13_risk_decision",
)


DEFAULT_COMPONENTS = (
    ComponentSpec(
        "tokenizer.byte_identity",
        "Preserve canonical byte/token identity at ingress and re-entry.",
        "bytes-or-token-deed-v1",
        "atomic-token-request-v1",
        "FROZEN_CORE",
        "VALIDATE_ONLY",
        "contract seam; concrete table is externally pinned",
    ),
    ComponentSpec(
        "atomic.tokenization",
        "Map a token, language, and context to AtomicTokenState.",
        "atomic-token-request-v1",
        "atomic-context-request-v1",
        "FROZEN_CORE",
        "PROPOSE_ONLY",
        "frozen atomic map plus typed context-request wrapper",
    ),
    ComponentSpec(
        "atomic.neighborhood",
        "Build local edges and equilibrate bounded semantic charge.",
        "atomic-context-request-v1",
        "semantic-charge-fusion-request-v1",
        "BOUNDED_STITCH",
        "PROPOSE_ONLY",
        "implemented in python/scbe/atomic_context_bundle.py",
    ),
    ComponentSpec(
        "chemical.fusion",
        "Reconstruct six-trit votes from atomic states and typed edges.",
        "semantic-charge-fusion-request-v1",
        "stista-token-ingress-v1",
        "FROZEN_CORE",
        "PROPOSE_ONLY",
        "frozen chemical fusion plus typed STISTA-ingress wrapper",
    ),
    ComponentSpec(
        "stista.multiplane",
        "Validate typed multi-plane circuit connectivity and arbitration.",
        "stista-token-ingress-v1",
        "stista-circuit-result-v1",
        "FROZEN_CORE",
        "VALIDATE_ONLY",
        "historical external circuit receipt; current source drift detected; neural promotion blocked",
        "2b46a0730541536dd66615011af2a1df908faaaa30addc0d0a2e018e119c4888",
        "HISTORICAL_PASS_SOURCE_DRIFT_DETECTED_20261113",
    ),
    ComponentSpec(
        "governance.reference14",
        "Run the pinned L0-L14 reference sections and emit a governed observation.",
        "stista-circuit-result-v1",
        "scbe-reference14-result-v1",
        "FROZEN_CORE",
        "VALIDATE_ONLY",
        "implemented in src/scbe_14layer_reference.py; frozen boundary only",
        implementation_source_sha256="4da98db6d5d61bd02801e485d84a3c9b5cc6069a331b20ac16ae22807f0fcc6d",
        implementation_sections=REFERENCE14_IMPLEMENTATION_SECTIONS,
    ),
    ComponentSpec(
        "state.9d.telemetry",
        "Carry context, monotonic time, entropy, and complex phase telemetry.",
        "scbe-reference14-result-v1",
        "scbe-state-envelope-9d-v1",
        "TELEMETRY_ONLY",
        "OBSERVE_ONLY",
        "named profile required; elapsed time remains separate from wrapped phase",
    ),
    ComponentSpec(
        "phdm.21d.geometry",
        "Provide a bounded geometric view with explicit projection provenance.",
        "scbe-state-envelope-9d-v1",
        "scbe-phdm-21d-view-v1",
        "FROZEN_CORE",
        "PROPOSE_ONLY",
        "implemented view; does not grant action authority",
    ),
    ComponentSpec(
        "action.compiler",
        "Validate and compile an allowed action through deterministic gates.",
        "scbe-phdm-21d-view-v1",
        "compiled-action-receipt-v1",
        "DETERMINISTIC_GATE",
        "EXECUTE_AFTER_GATE",
        "contract seam; concrete compiler is pinned separately",
    ),
    ComponentSpec(
        "tokenizer.reentry",
        "Canonical-serialize results through the frozen tokenizer boundary.",
        "compiled-action-receipt-v1",
        "tokenizer-reentry-v1",
        "FROZEN_CORE",
        "VALIDATE_ONLY",
        "required by the STISTA multi-plane contract",
    ),
    ComponentSpec(
        "reaction.ledger",
        "Hash-link the transformation receipt without changing execution.",
        "tokenizer-reentry-v1",
        "scbe_reaction_state_packet_v1",
        "DETERMINISTIC_GATE",
        "VALIDATE_ONLY",
        "implemented in python/scbe/reaction_state.py",
    ),
)


DEFAULT_CONTRACTS = (
    StitchContract(
        "stitch.tokenizer-to-atomic",
        "tokenizer.byte_identity",
        "atomic.tokenization",
        "atomic-token-request-v1",
        ("tokenizer_id", "token_table_sha256", "identity_root", "token"),
        sha256_payload_keys=("token_table_sha256",),
    ),
    StitchContract(
        "stitch.atomic-to-neighborhood",
        "atomic.tokenization",
        "atomic.neighborhood",
        "atomic-context-request-v1",
        ("identity_root", "atomic_states", "positions", "step_clock", "context_epoch"),
        ("edge_gain", "charge_gain", "drift_gain"),
    ),
    StitchContract(
        "stitch.neighborhood-to-fusion",
        "atomic.neighborhood",
        "chemical.fusion",
        "semantic-charge-fusion-request-v1",
        ("bundle_hash", "equilibrium_hash", "semantic_charges", "charge_gain"),
        ("charge_gain",),
        ("bundle_hash", "equilibrium_hash"),
    ),
    StitchContract(
        "stitch.fusion-to-stista",
        "chemical.fusion",
        "stista.multiplane",
        "stista-token-ingress-v1",
        (
            "identity_root",
            "tau_hat",
            "fusion_diagnostics",
            "tokenizer_reentry_required",
        ),
        boolean_payload_keys=("tokenizer_reentry_required",),
    ),
    StitchContract(
        "stitch.stista-to-reference14",
        "stista.multiplane",
        "governance.reference14",
        "stista-circuit-result-v1",
        (
            "circuit_receipt_hash",
            "reference14_input",
            "runtime_profile",
        ),
        sha256_payload_keys=("circuit_receipt_hash",),
    ),
    StitchContract(
        "stitch.reference14-to-9d",
        "governance.reference14",
        "state.9d.telemetry",
        "scbe-reference14-result-v1",
        (
            "reference14_source_sha256",
            "decision",
            "risk_base",
            "risk_prime",
            "layer_contracts",
            "context6",
            "elapsed_step",
            "entropy",
            "phase_real",
            "phase_imag",
        ),
        ("telemetry_gain",),
        ("reference14_source_sha256",),
        enum_payload_values=(("decision", ("ALLOW", "QUARANTINE", "DENY")),),
    ),
    StitchContract(
        "stitch.9d-to-phdm",
        "state.9d.telemetry",
        "phdm.21d.geometry",
        "scbe-state-envelope-9d-v1",
        (
            "context6",
            "elapsed_step",
            "entropy",
            "phase_real",
            "phase_imag",
            "runtime_profile",
        ),
        ("geometry_gain",),
    ),
    StitchContract(
        "stitch.phdm-to-compiler",
        "phdm.21d.geometry",
        "action.compiler",
        "scbe-phdm-21d-view-v1",
        ("identity_root", "projection_record", "candidate_action"),
    ),
    StitchContract(
        "stitch.compiler-to-reentry",
        "action.compiler",
        "tokenizer.reentry",
        "compiled-action-receipt-v1",
        ("compiler_hash", "action_hash", "gate_decision", "canonical_result"),
        sha256_payload_keys=("compiler_hash", "action_hash"),
        enum_payload_values=(("gate_decision", COMPILER_GATE_DECISIONS),),
    ),
    StitchContract(
        "stitch.reentry-to-ledger",
        "tokenizer.reentry",
        "reaction.ledger",
        "tokenizer-reentry-v1",
        ("identity_root", "tokenizer_id", "round_trip_ok", "canonical_result_hash"),
        sha256_payload_keys=("canonical_result_hash",),
        boolean_payload_keys=("round_trip_ok",),
    ),
)


DEFAULT_STITCH_PATH = tuple(contract.contract_id for contract in DEFAULT_CONTRACTS)
DEFAULT_STITCH_REGISTRY = StitchRegistry(DEFAULT_COMPONENTS, DEFAULT_CONTRACTS)


def build_stitch_envelope(
    contract_id: str,
    payload: dict[str, Any],
    *,
    identity_root: str,
    runtime_profile: str,
    step_clock: int,
    context_epoch: int,
    adapter_delta: dict[str, float] | None = None,
    previous_stitch_hash: str | None = None,
    previous_reaction_packet_hash: str | None = None,
    generated_at_utc: str | None = None,
    registry: StitchRegistry = DEFAULT_STITCH_REGISTRY,
) -> StitchEnvelope:
    """Validate, receipt, and hash one frozen-boundary handoff."""

    contract = registry.contract(contract_id)
    payload_json = _strict_json(payload, name="payload")
    payload_copy = _decode_json_object(payload_json, name="payload")
    payload_hash = sha256_value(payload_copy)
    deltas = {name: float(value) for name, value in (adapter_delta or {}).items()}
    adapter_delta_json = _strict_json(deltas, name="adapter_delta")
    packet = build_reaction_state_packet(
        domain="mixed",
        step=step_clock,
        bounded_operation=contract.contract_id,
        source=ReactionEndpoint(
            identity=identity_root,
            representation=registry.component(contract.source_component).output_schema,
            payload_sha256=payload_hash,
            metadata={"component_id": contract.source_component},
        ),
        target=ReactionEndpoint(
            identity=identity_root,
            representation=registry.component(contract.target_component).input_schema,
            payload_sha256=payload_hash,
            metadata={"component_id": contract.target_component},
        ),
        semantic_engravings=[
            REQUIRED_STITCH_ENGRAVING,
            f"payload schema: {contract.payload_schema}",
            f"runtime profile: {runtime_profile}",
        ],
        loss_notes=[],
        recalculation=ReactionRecalculation(
            syntax_ok=True,
            unit_checks_ok=True,
            identity_ok=True,
            extra={
                "context_epoch": context_epoch,
                "adapter_delta": deltas,
                "stitch_registry_hash": registry.manifest_hash,
            },
        ),
        identity_preserved=True,
        claim_boundary=list(STITCH_CLAIM_BOUNDARY),
        previous_packet_hash=previous_reaction_packet_hash,
        generated_at_utc=generated_at_utc,
    )
    envelope = StitchEnvelope(
        contract_id=contract.contract_id,
        source_component=contract.source_component,
        target_component=contract.target_component,
        identity_root=identity_root,
        runtime_profile=runtime_profile,
        step_clock=step_clock,
        context_epoch=context_epoch,
        payload_schema=contract.payload_schema,
        payload_json=payload_json,
        payload_sha256=payload_hash,
        adapter_delta_json=adapter_delta_json,
        previous_stitch_hash=previous_stitch_hash,
        previous_reaction_packet_hash=previous_reaction_packet_hash,
        reaction_packet_json=_strict_json(packet.to_dict(), name="reaction_packet"),
    )
    registry.validate_envelope(envelope)
    return envelope.with_hash()


def verify_stitch_chain(
    envelopes: Sequence[StitchEnvelope],
    *,
    registry: StitchRegistry = DEFAULT_STITCH_REGISTRY,
) -> bool:
    """Verify hashes, continuity, identity, runtime profile, and monotonic time."""

    if not envelopes:
        return False
    try:
        registry.validate_path([envelope.contract_id for envelope in envelopes])
    except ValueError:
        return False

    identity = envelopes[0].identity_root
    profile = envelopes[0].runtime_profile
    previous_hash: str | None = None
    previous_packet_hash: str | None = None
    previous_step = -1
    previous_epoch = -1
    for envelope in envelopes:
        if not envelope.verify(registry):
            return False
        if envelope.identity_root != identity or envelope.runtime_profile != profile:
            return False
        if envelope.previous_stitch_hash != previous_hash:
            return False
        if envelope.previous_reaction_packet_hash != previous_packet_hash:
            return False
        if (
            envelope.step_clock < previous_step
            or envelope.context_epoch < previous_epoch
        ):
            return False
        previous_hash = envelope.stitch_hash
        previous_packet_hash = envelope.reaction_packet.packet_hash
        previous_step = envelope.step_clock
        previous_epoch = envelope.context_epoch
    return True
