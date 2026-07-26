"""Focused tests for the deterministic multidimensional domino automaton."""

from __future__ import annotations

import pytest

from src.coding_spine.domino_event_automaton import (
    FACES,
    compile_domino_lattice,
    detect_contacts,
    emit_loom_program,
    resolve_contact,
    run_until_quiescent,
    state_receipt,
    step_automaton,
    verify_mirrors,
)


def _faces(**overrides):
    faces = {
        face: {
            "mark": f"closed:{face}",
            "port_type": "void",
            "mode": "closed",
            "trit": 0,
            "mirror": "",
        }
        for face in FACES
    }
    faces.update(overrides)
    return faces


def _port(mark="signal", *, mode="io", trit=0, mirror="mirror-v1", imports=0, exports=0, discard=0, source=""):
    return {
        "mark": mark,
        "port_type": "event",
        "mode": mode,
        "trit": trit,
        "mirror": mirror,
        "imports": imports,
        "exports": exports,
        "discard": discard,
        "source": source,
    }


def _domino(domino_id, position, *, orientation=0, role="Scout", trit=0, faces=None):
    return {
        "id": domino_id,
        "position": position,
        "orientation": orientation,
        "faces": faces or _faces(),
        "clone_role": role,
        "task_lens": f"lens:{domino_id}",
        "initial_trit": trit,
    }


def test_compile_and_contacts_are_deterministic_and_time_ordered():
    center = _domino(
        "center",
        (0, 0, 0, 0),
        faces=_faces(right=_port("late", mode="out", trit=1), front=_port("early", mode="out", trit=1)),
    )
    late = _domino("late", (1, 0, 0, 2), faces=_faces(left=_port("late", mode="in")))
    early = _domino("early", (0, 1, 0, 1), faces=_faces(back=_port("early", mode="in")))

    lattice_a = compile_domino_lattice([center, late, early])
    lattice_b = compile_domino_lattice([early, center, late])
    contacts_a = detect_contacts(lattice_a)
    contacts_b = detect_contacts(lattice_b)

    assert lattice_a.receipt == lattice_b.receipt == state_receipt(lattice_a)
    assert contacts_a == contacts_b
    assert [(contact.target_id, contact.event_time) for contact in contacts_a] == [("early", 1), ("late", 2)]
    assert [contact.angle for contact in contacts_a] == [0, 0]
    assert emit_loom_program(step_automaton(lattice_a)) == emit_loom_program(step_automaton(lattice_b))


def test_hard_mirror_verification_is_the_only_commit_gate():
    source = _domino(
        "source",
        (0, 0, 0, 0),
        trit=1,
        faces=_faces(right=_port(mode="out", trit=1, mirror="expected")),
    )
    unverified_target = _domino(
        "target",
        (1, 0, 0, 1),
        faces=_faces(left=_port(mode="in", trit=1, mirror="different")),
    )
    unverified = compile_domino_lattice([source, unverified_target])
    unverified_step = step_automaton(unverified)

    assert verify_mirrors({"contract": 1}, {"contract": 1}) == 1
    assert verify_mirrors("expected", "different") == 0
    assert unverified_step.state.trit("target") == 1
    assert unverified_step.events[0].verified == 0
    assert unverified_step.state.committed("target") == 0

    verified_target = _domino(
        "target",
        (1, 0, 0, 1),
        faces=_faces(left=_port(mode="in", trit=1, mirror="expected")),
    )
    verified_step = step_automaton(compile_domino_lattice([source, verified_target]))
    assert verified_step.events[0].verified == 1
    assert verified_step.state.committed("target") == 1
    receipt = verified_step.events[0].receipt_payload()
    assert receipt["verdict"] == "ENGINEERING"
    assert receipt["verdict_basis"] == "exact_mirror_positive"
    assert receipt["hard_verified"] == 1
    assert receipt["route_id"] == "domino-route"
    assert receipt["tested_element_set"]
    assert receipt["independent_channel"] == "UNPROVEN"
    assert len(receipt["event_id"]) == 64
    assert len(receipt["prior_state"]) == 64

    negative_source = _domino(
        "source",
        (0, 0, 0, 0),
        trit=-1,
        faces=_faces(right=_port(mode="out", trit=-1, mirror="expected")),
    )
    negative_target = _domino(
        "target",
        (1, 0, 0, 1),
        faces=_faces(left=_port(mode="in", trit=-1, mirror="expected")),
    )
    negative = step_automaton(compile_domino_lattice([negative_source, negative_target]))
    assert negative.events[0].proposal == -1
    assert negative.events[0].receipt_payload()["verdict"] == "THEOREM"
    assert negative.events[0].commit == 0


def test_fixed_point_cycle_and_step_cap_have_distinct_receipts():
    aligned = compile_domino_lattice(
        [
            _domino("a", (0, 0, 0, 0), trit=1, faces=_faces(right=_port(mode="io"))),
            _domino("b", (1, 0, 0, 0), trit=1, faces=_faces(left=_port(mode="io"))),
        ]
    )
    fixed = run_until_quiescent(aligned, max_steps=4)
    assert fixed.status == "fixed_point"

    inverted = compile_domino_lattice(
        [
            _domino("a", (0, 0, 0, 0), orientation=0, trit=1, faces=_faces(right=_port(mode="io"))),
            _domino("b", (1, 0, 0, 0), orientation=180, trit=1, faces=_faces(left=_port(mode="io"))),
        ]
    )
    cycle = run_until_quiescent(inverted, max_steps=4)
    capped = run_until_quiescent(inverted, max_steps=1)

    assert cycle.status == "cycle"
    assert cycle.cycle_start == 1
    assert cycle.cycle_length == 2
    assert capped.status == "step_cap"
    assert len({fixed.termination_receipt, cycle.termination_receipt, capped.termination_receipt}) == 3
    assert all(
        len(receipt) == 64
        for receipt in (fixed.termination_receipt, cycle.termination_receipt, capped.termination_receipt)
    )


def test_resolver_is_exhaustively_ternary_across_states_angles_and_phases():
    for orientation in range(0, 360, 60):
        for source_trit in (-1, 0, 1):
            for target_trit in (-1, 0, 1):
                lattice = compile_domino_lattice(
                    [
                        _domino(
                            "a",
                            (0, 0, 0, 0),
                            trit=source_trit,
                            faces=_faces(right=_port(mode="out")),
                        ),
                        _domino(
                            "b",
                            (1, 0, 0, target_trit),
                            orientation=orientation,
                            trit=target_trit,
                            faces=_faces(left=_port(mode="in")),
                        ),
                    ]
                )
                contact = detect_contacts(lattice)[0]
                event = resolve_contact(lattice, contact)
                assert type(contact.angle) is int
                assert type(contact.phase) is int
                assert event.proposal in (-1, 0, 1)
                assert event.commit in (0, 1)


def test_float_geometry_is_rejected_instead_of_silently_rounded():
    with pytest.raises(TypeError, match="position"):
        compile_domino_lattice([_domino("bad", (0.5, 0, 0, 0))])
    with pytest.raises(TypeError, match="orientation"):
        compile_domino_lattice([_domino("bad", (0, 0, 0, 0), orientation=60.0)])


def test_boundary_accounting_is_guarded_and_receipted():
    source = _domino(
        "source",
        (0, 0, 0, 0),
        trit=1,
        faces=_faces(right=_port(mode="out", exports=1, source="external:queue")),
    )
    target = _domino(
        "target",
        (1, 0, 0, 1),
        faces=_faces(left=_port(mode="in", imports=2, source="external:queue")),
    )
    closed = compile_domino_lattice([source, target], boundary="CLOSED", configured_total=4)
    with pytest.raises(ValueError, match="conservation"):
        step_automaton(closed)

    opened = compile_domino_lattice([source, target], route_id="route-open-1", boundary="OPEN", configured_total=4)
    step = step_automaton(opened)
    event = step.events[0]
    assert step.state.total == 5
    assert event.route_id == "route-open-1"
    assert event.boundary == "OPEN"
    assert (event.imports, event.exports, event.discard, event.source) == (2, 1, 0, "external:queue")
    assert event.verdict in {"THEOREM", "ENGINEERING", "TURN"}
