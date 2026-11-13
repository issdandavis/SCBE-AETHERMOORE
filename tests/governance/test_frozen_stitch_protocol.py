from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from python.scbe.frozen_stitch_protocol import (
    DEFAULT_STITCH_PATH,
    DEFAULT_STITCH_REGISTRY,
    StitchRegistry,
    build_stitch_envelope,
    verify_stitch_chain,
)
from python.scbe.reaction_state import sha256_value


def _payload(contract_id: str) -> dict[str, object]:
    contract = DEFAULT_STITCH_REGISTRY.contract(contract_id)
    payload: dict[str, object] = {key: f"fixture:{key}" for key in contract.required_payload_keys}
    for key in contract.sha256_payload_keys:
        payload[key] = sha256_value({"fixture": key})
    for key in contract.boolean_payload_keys:
        payload[key] = True
    for key, values in contract.enum_payload_values:
        payload[key] = values[0]
    return payload


def test_default_registry_forms_one_continuous_layering_path() -> None:
    contracts = DEFAULT_STITCH_REGISTRY.validate_path(DEFAULT_STITCH_PATH)

    assert len(contracts) == 10
    assert contracts[0].source_component == "tokenizer.byte_identity"
    assert contracts[-1].target_component == "reaction.ledger"
    assert DEFAULT_STITCH_REGISTRY.component("action.compiler").authority == "EXECUTE_AFTER_GATE"
    assert all(
        component.authority != "EXECUTE_AFTER_GATE"
        for component in DEFAULT_STITCH_REGISTRY.components
        if component.component_id != "action.compiler"
    )
    for contract in contracts:
        source = DEFAULT_STITCH_REGISTRY.component(contract.source_component)
        target = DEFAULT_STITCH_REGISTRY.component(contract.target_component)
        assert source.output_schema == contract.payload_schema == target.input_schema

    reference14 = DEFAULT_STITCH_REGISTRY.component("governance.reference14")
    assert len(reference14.implementation_sections) == 15
    source_digest = hashlib.sha256(Path("src/scbe_14layer_reference.py").read_bytes()).hexdigest()
    assert source_digest == reference14.implementation_source_sha256


def test_single_stitch_is_hash_bound_to_payload_and_reaction_receipt() -> None:
    contract_id = "stitch.atomic-to-neighborhood"
    envelope = build_stitch_envelope(
        contract_id,
        _payload(contract_id),
        identity_root="token-deed:0001",
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        step_clock=7,
        context_epoch=2,
        adapter_delta={"charge_gain": 0.25},
        generated_at_utc="2026-11-13T00:00:00Z",
    )

    assert envelope.verify(DEFAULT_STITCH_REGISTRY) is True
    assert envelope.reaction_packet.classification == "BIJECTIVE"
    assert envelope.reaction_packet.source.identity == envelope.reaction_packet.target.identity


def test_payload_tamper_is_detected() -> None:
    contract_id = "stitch.neighborhood-to-fusion"
    envelope = build_stitch_envelope(
        contract_id,
        _payload(contract_id),
        identity_root="token-deed:0002",
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        step_clock=8,
        context_epoch=2,
        generated_at_utc="2026-11-13T00:00:00Z",
    )
    tampered_payload = {**envelope.payload, "charge_gain": "tampered"}
    tampered = replace(
        envelope,
        payload_json=json.dumps(tampered_payload, sort_keys=True, separators=(",", ":")),
    )

    assert tampered.verify(DEFAULT_STITCH_REGISTRY) is False


def test_nested_inputs_and_decoded_views_cannot_mutate_a_frozen_envelope() -> None:
    contract_id = "stitch.atomic-to-neighborhood"
    payload = _payload(contract_id)
    payload["atomic_states"] = [{"tau": [1, 0, -1]}]
    deltas = {"charge_gain": 0.25}
    envelope = build_stitch_envelope(
        contract_id,
        payload,
        identity_root="token-deed:immutable",
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        step_clock=4,
        context_epoch=1,
        adapter_delta=deltas,
        generated_at_utc="2026-11-13T00:00:00Z",
    )

    payload["atomic_states"][0]["tau"][0] = -1
    deltas["charge_gain"] = 1.0
    decoded = envelope.payload
    decoded["atomic_states"][0]["tau"][1] = 1
    decoded_delta = envelope.adapter_delta
    decoded_delta["charge_gain"] = 0.9

    assert envelope.payload["atomic_states"][0]["tau"] == [1, 0, -1]
    assert envelope.adapter_delta == {"charge_gain": 0.25}
    assert envelope.verify(DEFAULT_STITCH_REGISTRY) is True


def test_reaction_packet_substitution_fails_even_after_rehashing_the_envelope() -> None:
    contract_id = "stitch.atomic-to-neighborhood"
    envelope = build_stitch_envelope(
        contract_id,
        _payload(contract_id),
        identity_root="token-deed:packet-binding",
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        step_clock=7,
        context_epoch=2,
        generated_at_utc="2026-11-13T00:00:00Z",
    )
    wrong_packet = replace(
        envelope.reaction_packet,
        step=99,
        bounded_operation="stitch.neighborhood-to-fusion",
        packet_hash=None,
    ).with_hash()
    substituted = replace(
        envelope,
        reaction_packet_json=json.dumps(wrong_packet.to_dict(), sort_keys=True, separators=(",", ":")),
        stitch_hash=None,
    ).with_hash()

    assert substituted.verify(DEFAULT_STITCH_REGISTRY) is False


def test_rehashed_reaction_packet_cannot_downgrade_checks_or_claims() -> None:
    contract_id = "stitch.atomic-to-neighborhood"
    envelope = build_stitch_envelope(
        contract_id,
        _payload(contract_id),
        identity_root="token-deed:packet-policy",
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        step_clock=7,
        context_epoch=2,
        generated_at_utc="2026-11-13T00:00:00Z",
    )
    packet = envelope.reaction_packet
    downgraded_checks = replace(
        packet,
        recalculation=replace(
            packet.recalculation,
            syntax_ok=None,
            unit_checks_ok=None,
            identity_ok=None,
        ),
    )
    mutations = (
        downgraded_checks,
        replace(packet, semantic_engravings=["forged"]),
        replace(packet, loss_notes=["unbound loss"]),
        replace(packet, claim_boundary=["authority widened"]),
    )
    for mutation in mutations:
        rehashed_packet = replace(mutation, packet_hash=None).with_hash()
        rehashed_envelope = replace(
            envelope,
            reaction_packet_json=json.dumps(rehashed_packet.to_dict(), sort_keys=True, separators=(",", ":")),
            stitch_hash=None,
        ).with_hash()
        assert rehashed_envelope.verify(DEFAULT_STITCH_REGISTRY) is False


def test_registry_substitution_and_invented_compiler_gate_fail_closed() -> None:
    contract_id = "stitch.compiler-to-reentry"
    payload = _payload(contract_id)
    envelope = build_stitch_envelope(
        contract_id,
        payload,
        identity_root="token-deed:compiler",
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        step_clock=9,
        context_epoch=3,
        generated_at_utc="2026-11-13T00:00:00Z",
    )
    changed_components = list(DEFAULT_STITCH_REGISTRY.components)
    changed_components[0] = replace(changed_components[0], implementation_status="substituted registry")
    changed_registry = StitchRegistry(changed_components, DEFAULT_STITCH_REGISTRY.contracts)
    assert envelope.verify(changed_registry) is False

    payload["gate_decision"] = "ALLOW_WITHOUT_PROOF"
    with pytest.raises(ValueError, match="gate_decision"):
        build_stitch_envelope(
            contract_id,
            payload,
            identity_root="token-deed:compiler",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
            step_clock=9,
            context_epoch=3,
        )


def test_custom_registry_cannot_downgrade_compiler_policy() -> None:
    changed_components = [
        (replace(component, authority="PROPOSE_ONLY") if component.component_id == "action.compiler" else component)
        for component in DEFAULT_STITCH_REGISTRY.components
    ]
    with pytest.raises(ValueError, match="action.compiler"):
        StitchRegistry(changed_components, DEFAULT_STITCH_REGISTRY.contracts)

    changed_contracts = [
        (
            replace(contract, enum_payload_values=())
            if contract.contract_id == "stitch.compiler-to-reentry"
            else contract
        )
        for contract in DEFAULT_STITCH_REGISTRY.contracts
    ]
    with pytest.raises(ValueError, match="gate-decision policy"):
        StitchRegistry(DEFAULT_STITCH_REGISTRY.components, changed_contracts)

    with pytest.raises(ValueError, match="authority"):
        replace(DEFAULT_STITCH_REGISTRY.components[0], authority="ROOT")


def test_stitch_registry_manifest_and_lookup_tables_cannot_diverge() -> None:
    registry = StitchRegistry(
        DEFAULT_STITCH_REGISTRY.components,
        DEFAULT_STITCH_REGISTRY.contracts,
    )
    manifest_hash = registry.manifest_hash

    with pytest.raises(AttributeError, match="immutable"):
        registry.components = ()
    with pytest.raises(AttributeError, match="immutable"):
        registry.contracts = ()
    with pytest.raises(TypeError):
        registry._component_by_id["action.compiler"] = registry.components[0]

    assert registry.manifest_hash == manifest_hash
    assert registry.component("action.compiler").authority == "EXECUTE_AFTER_GATE"


def test_nonfinite_payload_and_malformed_compiler_hash_fail_closed() -> None:
    contract_id = "stitch.compiler-to-reentry"
    payload = _payload(contract_id)
    payload["canonical_result"] = {"value": float("nan")}
    with pytest.raises(ValueError, match="finite JSON"):
        build_stitch_envelope(
            contract_id,
            payload,
            identity_root="token-deed:compiler",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
            step_clock=9,
            context_epoch=3,
        )

    payload = _payload(contract_id)
    payload["compiler_hash"] = "not-a-hash"
    with pytest.raises(ValueError, match="SHA-256"):
        build_stitch_envelope(
            contract_id,
            payload,
            identity_root="token-deed:compiler",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
            step_clock=9,
            context_epoch=3,
        )


def test_unknown_or_oversized_adapter_delta_fails_closed() -> None:
    contract_id = "stitch.atomic-to-neighborhood"
    with pytest.raises(ValueError, match="unknown adapter delta"):
        build_stitch_envelope(
            contract_id,
            _payload(contract_id),
            identity_root="token-deed:0003",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
            step_clock=9,
            context_epoch=2,
            adapter_delta={"secret_width": 0.5},
        )
    with pytest.raises(ValueError, match="within"):
        build_stitch_envelope(
            contract_id,
            _payload(contract_id),
            identity_root="token-deed:0003",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
            step_clock=9,
            context_epoch=2,
            adapter_delta={"edge_gain": 1.5},
        )


def test_full_stitch_chain_replays_with_two_independent_hash_links() -> None:
    envelopes = []
    previous_stitch_hash = None
    previous_packet_hash = None
    for offset, contract_id in enumerate(DEFAULT_STITCH_PATH):
        envelope = build_stitch_envelope(
            contract_id,
            _payload(contract_id),
            identity_root="token-deed:0042",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
            step_clock=100 + offset,
            context_epoch=4,
            previous_stitch_hash=previous_stitch_hash,
            previous_reaction_packet_hash=previous_packet_hash,
            generated_at_utc="2026-11-13T00:00:00Z",
        )
        envelopes.append(envelope)
        previous_stitch_hash = envelope.stitch_hash
        previous_packet_hash = envelope.reaction_packet.packet_hash

    assert verify_stitch_chain(envelopes) is True
    broken = list(envelopes)
    broken[3] = replace(broken[3], previous_stitch_hash="0" * 64)
    assert verify_stitch_chain(broken) is False
