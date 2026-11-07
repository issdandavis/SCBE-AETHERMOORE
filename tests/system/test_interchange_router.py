"""Reference tests for typed cross-substrate routing and evidence discernment."""

from __future__ import annotations

import pytest

from python.scbe.interchange_router import (
    BackendCapability,
    BackendKind,
    ClaimType,
    DiscernmentRecord,
    EvidenceObservation,
    EvidenceVerdict,
    HyperTokenEnvelope,
    MixtureComponent,
    OperationContract,
    TypeAdapter,
    route_operation,
)


def _capability(target_id: str, kind: BackendKind, **changes) -> BackendCapability:
    values = {
        "target_id": target_id,
        "kind": kind,
        "operations": frozenset({"nand"}),
        "input_types": frozenset({"bit_pair"}),
        "output_types": frozenset({"bit"}),
        "latency_ms": 2.0,
        "energy_j": 0.2,
        "fidelity": 0.999,
        "trust": 0.95,
        "private_local": True,
        "deterministic": True,
        "policy_tags": frozenset({"internal"}),
    }
    values.update(changes)
    return BackendCapability(**values)


def test_direct_and_adapter_routes_share_an_exact_operation_contract():
    contract = OperationContract(
        operation_id="op-1",
        operation="nand",
        input_type="bit_pair",
        output_type="bit",
        max_latency_ms=20.0,
        max_energy_j=2.0,
        min_fidelity=0.95,
        requires_deterministic=True,
        required_policy_tags=frozenset({"internal"}),
    )
    cpu = _capability("cpu-0", BackendKind.CPU)
    fluidic = _capability(
        "fluidic-0",
        BackendKind.FLUIDIC,
        input_types=frozenset({"bubble_pair"}),
        latency_ms=8.0,
        energy_j=0.05,
        fidelity=0.98,
    )
    adapter = TypeAdapter("bits-to-bubbles", "bit_pair", "bubble_pair", 1.0, 0.1, 0.99)

    decision = route_operation(contract, [fluidic, cpu], [adapter])

    assert decision.selected.target_id == "cpu-0"
    assert {item.target_id for item in decision.eligible} == {"cpu-0", "fluidic-0"}
    fluid_route = next(item for item in decision.eligible if item.target_id == "fluidic-0")
    assert fluid_route.adapters == ("bits-to-bubbles",)
    assert len(decision.receipt_sha256) == 64

    reversed_decision = route_operation(contract, [cpu, fluidic], [adapter])
    assert reversed_decision.receipt_sha256 == decision.receipt_sha256


def test_hard_privacy_and_semantics_cannot_be_waived_by_a_high_score():
    contract = OperationContract(
        operation_id="op-private",
        operation="nand",
        input_type="bit_pair",
        output_type="bit",
        requires_private_local=True,
    )
    remote = _capability(
        "remote-perfect",
        BackendKind.REMOTE_MODEL,
        private_local=False,
        fidelity=1.0,
        trust=1.0,
    )
    local = _capability("local", BackendKind.CPU, fidelity=0.97)

    decision = route_operation(contract, [remote, local])

    assert decision.selected.target_id == "local"
    assert decision.rejected == (("remote-perfect", ("private_local_required",)),)


def test_no_untyped_crossing_is_silently_invented():
    contract = OperationContract("op-2", "nand", "word", "bit")
    target = _capability("fluidic", BackendKind.FLUIDIC, input_types=frozenset({"bubble_pair"}))

    with pytest.raises(ValueError, match="no_typed_input_path"):
        route_operation(contract, [target])


def test_conflicting_liquids_keep_the_discernment_trit_unresolved():
    record = DiscernmentRecord(
        "claim-1",
        ClaimType.FACT,
        (
            EvidenceObservation("e1", "source-a", EvidenceVerdict.SUPPORTED, 0.9, "2026-11-07T00:00:00Z"),
            EvidenceObservation(
                "e2",
                "source-b",
                EvidenceVerdict.CONTRADICTED,
                0.8,
                "2026-11-07T00:01:00Z",
            ),
        ),
    )

    result = record.evaluate()

    assert result.verdict is EvidenceVerdict.UNRESOLVED
    assert result.confidence == 0.0
    assert result.support_count == result.contradiction_count == 1


def test_opinion_content_is_not_mislabeled_as_an_external_fact():
    record = DiscernmentRecord(
        "preference-1",
        ClaimType.PREFERENCE,
        (EvidenceObservation("e1", "speaker", EvidenceVerdict.SUPPORTED, 1.0, "2026-11-07T00:00:00Z"),),
    )

    assert record.evaluate().verdict is EvidenceVerdict.UNRESOLVED


def test_hyper_token_preserves_source_bundles_and_visible_mixture_order():
    digest = "a" * 64
    envelope = HyperTokenEnvelope(
        occurrence_id="source-a:section-2:word-4",
        payload_sha256=digest,
        tokenizer_sha256="b" * 64,
        source_bundle_ids=("source-a", "source-b"),
        mixture_trace=(
            MixtureComponent("c1", "source-a", 0, 0.7, "supports", "identity"),
            MixtureComponent("c2", "source-b", 1, 0.3, "qualifies", "summary-v1"),
        ),
    )

    assert [item.source_bundle_id for item in envelope.mixture_trace] == [
        "source-a",
        "source-b",
    ]
    assert [item.weight for item in envelope.mixture_trace] == [0.7, 0.3]
