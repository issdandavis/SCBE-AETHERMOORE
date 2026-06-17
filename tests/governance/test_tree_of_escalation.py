"""Unit tests for Tree of Escalation v0.1 data structures.

v0.1 is data-structures-only: no walker, no sandbox, no execution.
These tests verify construction, invariants, and the locked
architectural decisions (Q5 adversarial pairing, Q6 NULL-bridge
serialization).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance.tree_of_escalation import (  # noqa: E402
    BAND_FREQUENCY_MULTIPLIER,
    DEFAULT_LADDER,
    DOMAIN_ADVERSARY,
    DOMAIN_PRIMARY,
    LANE_PHI_WEIGHT,
    LANE_TIER,
    LANE_TO_TRI_BUNDLE_CODE,
    NULL_BRIDGE_VOID_ID,
    SYSTEM_FUNDAMENTAL_HZ,
    AudioEvent,
    Band,
    BridgeEdge,
    BridgeMatrix,
    Flag,
    HashReader,
    IdentityPrior,
    InspectionResult,
    IsolationPrior,
    Lane,
    LanePair,
    Node,
    NodeKind,
    OpTrace,
    Posture,
    ProvisionalRegistry,
    Termination,
    Tree,
    VoidStats,
    classify_domain,
    emit_audio,
    hash_payload,
    majority_converged,
    mint_provisional,
    sandbox,
    select_initial_pair,
    walk,
)

# --------------------------------------------------------------------------- #
#  Lane enumeration — six tongues plus CUSTOM
# --------------------------------------------------------------------------- #


def test_lane_enum_has_six_tongues_plus_custom():
    expected = {
        "koraelin",
        "avali",
        "runethic",
        "cassisivadan",
        "umbroth",
        "draumric",
        "custom",
    }
    assert {lane.value for lane in Lane} == expected


def test_default_ladder_excludes_custom():
    assert Lane.CUSTOM not in DEFAULT_LADDER
    assert len(DEFAULT_LADDER) == 6


def test_default_ladder_in_phi_weight_ascending_order():
    weights = [LANE_PHI_WEIGHT[lane] for lane in DEFAULT_LADDER]
    assert weights == sorted(weights)


def test_lane_tier_assignment_t1_to_t6():
    tiers = [LANE_TIER[lane] for lane in DEFAULT_LADDER]
    assert tiers == [1, 2, 3, 4, 5, 6]


def test_custom_lane_intentionally_omitted_from_weight_and_tier():
    assert Lane.CUSTOM not in LANE_PHI_WEIGHT
    assert Lane.CUSTOM not in LANE_TIER


# --------------------------------------------------------------------------- #
#  Band — three concurrent substrates
# --------------------------------------------------------------------------- #


def test_band_enum_has_three_substrates():
    assert {b.value for b in Band} == {"infra", "audible", "ultra"}


# --------------------------------------------------------------------------- #
#  Posture — humble vs rigid
# --------------------------------------------------------------------------- #


def test_posture_enum_has_humble_and_rigid():
    assert {p.value for p in Posture} == {"humble", "rigid"}


# --------------------------------------------------------------------------- #
#  NodeKind covers all categories from the spec
# --------------------------------------------------------------------------- #


def test_node_kind_covers_all_spec_categories():
    expected = {
        "op",
        "sandbox_provisional",
        "sandbox_inspection",
        "sandbox_internalized",
        "null_bridge_void",
        "provisional_mint",
    }
    assert {k.value for k in NodeKind} == expected


# --------------------------------------------------------------------------- #
#  hash_payload — sanity
# --------------------------------------------------------------------------- #


def test_hash_payload_returns_32_bytes():
    h = hash_payload(b"hello")
    assert isinstance(h, bytes)
    assert len(h) == 32


def test_hash_payload_deterministic():
    assert hash_payload(b"abc") == hash_payload(b"abc")
    assert hash_payload(b"abc") != hash_payload(b"abd")


# --------------------------------------------------------------------------- #
#  Tree — singleton VOID is auto-inserted
# --------------------------------------------------------------------------- #


def test_tree_init_inserts_void_singleton_at_canonical_id():
    t = Tree()
    assert len(t.nodes) == 1
    assert t.nodes[0].id == NULL_BRIDGE_VOID_ID
    assert t.nodes[0].kind == NodeKind.NULL_BRIDGE_VOID


def test_tree_void_is_first_node_index_zero():
    t = Tree()
    assert NULL_BRIDGE_VOID_ID == 0
    assert t.nodes[NULL_BRIDGE_VOID_ID].kind == NodeKind.NULL_BRIDGE_VOID


def test_tree_default_posture_is_humble():
    assert Tree().posture == Posture.HUMBLE


# --------------------------------------------------------------------------- #
#  add_node — id must match insertion index
# --------------------------------------------------------------------------- #


def test_add_node_appends_with_matching_id():
    t = Tree()
    n = Node(id=1, kind=NodeKind.OP, lane=Lane.KORAELIN, band=Band.AUDIBLE)
    nid = t.add_node(n)
    assert nid == 1
    assert t.nodes[1] is n


def test_add_node_rejects_id_mismatch():
    t = Tree()
    bad = Node(id=99, kind=NodeKind.OP)
    with pytest.raises(ValueError, match="node id"):
        t.add_node(bad)


# --------------------------------------------------------------------------- #
#  LanePair — adversarial pairing invariants (Q5)
# --------------------------------------------------------------------------- #


def test_lane_pair_carries_domain_field():
    pair = LanePair(
        primary=Lane.KORAELIN,
        adversary=Lane.UMBROTH,
        domain="formal_logic",
    )
    assert pair.domain == "formal_logic"


def test_lane_pair_rejects_self_pairing():
    with pytest.raises(ValueError, match="must differ"):
        LanePair(primary=Lane.AVALI, adversary=Lane.AVALI)


def test_lane_pair_allows_custom_lane_as_adversary():
    pair = LanePair(primary=Lane.KORAELIN, adversary=Lane.CUSTOM)
    assert pair.adversary == Lane.CUSTOM


# --------------------------------------------------------------------------- #
#  BridgeEdge — defaults and NULL-bridge invariants (Q6)
# --------------------------------------------------------------------------- #


def test_bridge_edge_defaults_to_translatable():
    e = BridgeEdge(source_id=1, target_id=2)
    assert e.is_untranslatable is False
    assert e.untranslatable_reason is None
    assert e.untranslatable_op_id is None


def test_null_bridge_edge_carries_failure_metadata_on_edge_not_void():
    """Q6: per-failure metadata lives on the edge, NOT the singleton."""
    t = Tree()
    src = Node(id=1, kind=NodeKind.OP, lane=Lane.KORAELIN)
    t.add_node(src)
    e = BridgeEdge(
        source_id=1,
        target_id=NULL_BRIDGE_VOID_ID,
        is_untranslatable=True,
        untranslatable_reason="no quantum-allocation analogue in tongue j",
        untranslatable_op_id="qmem_alloc_v1",
    )
    t.add_edge(e)
    # Metadata is on the edge:
    assert t.edges[0].untranslatable_reason.startswith("no quantum")
    assert t.edges[0].untranslatable_op_id == "qmem_alloc_v1"
    # The void node still carries no per-failure metadata, only stats:
    assert t.nodes[NULL_BRIDGE_VOID_ID].payload == {}


def test_null_bridge_must_terminate_at_void_singleton():
    t = Tree()
    src = Node(id=1, kind=NodeKind.OP, lane=Lane.AVALI)
    t.add_node(src)
    bad = BridgeEdge(
        source_id=1,
        target_id=1,  # NOT the void singleton
        is_untranslatable=True,
    )
    with pytest.raises(ValueError, match="NULL_BRIDGE_VOID"):
        t.add_edge(bad)


def test_edge_endpoints_validated():
    t = Tree()
    bad = BridgeEdge(source_id=42, target_id=NULL_BRIDGE_VOID_ID)
    with pytest.raises(ValueError, match="out of range"):
        t.add_edge(bad)


# --------------------------------------------------------------------------- #
#  VoidStats aggregation (Q6)
# --------------------------------------------------------------------------- #


def test_void_stats_increment_on_null_bridge():
    t = Tree()
    a = Node(id=1, kind=NodeKind.OP, lane=Lane.KORAELIN)
    t.add_node(a)
    t.add_edge(
        BridgeEdge(
            source_id=1,
            target_id=NULL_BRIDGE_VOID_ID,
            is_untranslatable=True,
            untranslatable_op_id="op_a",
        )
    )
    assert t.void_stats.incoming_edge_count == 1
    assert t.void_stats.distinct_ops_failed == 1


def test_void_stats_distinct_ops_dedup():
    t = Tree()
    a = Node(id=1, kind=NodeKind.OP, lane=Lane.KORAELIN)
    b = Node(id=2, kind=NodeKind.OP, lane=Lane.AVALI)
    t.add_node(a)
    t.add_node(b)
    for src in (1, 2, 1):  # three failures, two distinct ops
        t.add_edge(
            BridgeEdge(
                source_id=src,
                target_id=NULL_BRIDGE_VOID_ID,
                is_untranslatable=True,
                untranslatable_op_id=("op_a" if src == 1 else "op_b"),
            )
        )
    assert t.void_stats.incoming_edge_count == 3
    assert t.void_stats.distinct_ops_failed == 2


def test_void_stats_lane_pair_attribution():
    t = Tree()
    t.lane_pair = LanePair(primary=Lane.KORAELIN, adversary=Lane.UMBROTH)
    a = Node(id=1, kind=NodeKind.OP, lane=Lane.KORAELIN)
    t.add_node(a)
    t.add_edge(
        BridgeEdge(
            source_id=1,
            target_id=NULL_BRIDGE_VOID_ID,
            is_untranslatable=True,
            untranslatable_op_id="op_a",
        )
    )
    key = (Lane.KORAELIN, Lane.UMBROTH)
    assert t.void_stats.failures_by_lane_pair[key] == 1


def test_translatable_edge_does_not_touch_void_stats():
    t = Tree()
    a = Node(id=1, kind=NodeKind.OP, lane=Lane.KORAELIN)
    b = Node(id=2, kind=NodeKind.OP, lane=Lane.AVALI)
    t.add_node(a)
    t.add_node(b)
    t.add_edge(BridgeEdge(source_id=1, target_id=2, information_variance=0.42))
    assert t.void_stats.incoming_edge_count == 0
    assert t.void_stats.distinct_ops_failed == 0


# --------------------------------------------------------------------------- #
#  Standalone VoidStats default invariants
# --------------------------------------------------------------------------- #


def test_void_stats_defaults_zero():
    s = VoidStats()
    assert s.incoming_edge_count == 0
    assert s.distinct_ops_failed == 0
    assert s.failures_by_lane_pair == {}


# =========================================================================== #
#  v0.2 — BridgeMatrix, HashReader, walker
# =========================================================================== #


def _all_clean_matrix() -> BridgeMatrix:
    matrix = BridgeMatrix()
    for lane in DEFAULT_LADDER:
        matrix.register_reader(lane, HashReader(lane=lane))
    return matrix


def test_hash_reader_clean_payload_is_deterministic():
    r = HashReader(lane=Lane.KORAELIN)
    a = r.read(b"hello")
    b = r.read(b"hello")
    assert a[0].result_hash == b[0].result_hash


def test_hash_reader_perturb_changes_result_hash():
    clean = HashReader(lane=Lane.AVALI)
    dirty = HashReader(lane=Lane.AVALI, perturb=b"X")
    assert clean.read(b"hi")[0].result_hash != dirty.read(b"hi")[0].result_hash


def test_bridge_matrix_identity_implicit():
    m = BridgeMatrix()
    op = OpTrace(op_id="t", args_hash=b"\x00" * 32, result_hash=b"\x01" * 32)
    assert m.bridge(Lane.KORAELIN, Lane.KORAELIN, op) is op


def test_bridge_matrix_unregistered_returns_null():
    m = BridgeMatrix()
    op = OpTrace(op_id="t", args_hash=b"\x00" * 32, result_hash=b"\x01" * 32)
    assert m.bridge(Lane.KORAELIN, Lane.AVALI, op) is None


def test_bridge_matrix_registered_bridge_invoked():
    m = BridgeMatrix()
    sentinel = OpTrace(op_id="bridged", args_hash=b"\x02" * 32, result_hash=b"\x03" * 32)
    m.register_bridge(Lane.KORAELIN, Lane.AVALI, lambda _op: sentinel)
    op = OpTrace(op_id="t", args_hash=b"\x00" * 32, result_hash=b"\x01" * 32)
    assert m.bridge(Lane.KORAELIN, Lane.AVALI, op) is sentinel


def test_bridge_matrix_reader_for_missing_raises():
    m = BridgeMatrix()
    with pytest.raises(KeyError):
        m.reader_for(Lane.RUNETHIC)


def test_bridge_matrix_register_identity_bridge_rejected():
    m = BridgeMatrix()
    with pytest.raises(ValueError, match="identity"):
        m.register_bridge(Lane.KORAELIN, Lane.KORAELIN, lambda op: op)


# --- majority_converged ---------------------------------------------------- #


def test_majority_converged_unanimous_returns_hash():
    h = b"\xaa" * 32
    streams = {
        Lane.KORAELIN: (OpTrace("a", b"", h),),
        Lane.AVALI: (OpTrace("b", b"", h),),
    }
    assert majority_converged(streams) == h


def test_majority_converged_split_returns_none():
    streams = {
        Lane.KORAELIN: (OpTrace("a", b"", b"\xaa" * 32),),
        Lane.AVALI: (OpTrace("b", b"", b"\xbb" * 32),),
    }
    assert majority_converged(streams) is None


def test_majority_converged_strict_majority_in_five():
    h_clean = b"\xcc" * 32
    streams = {
        Lane.KORAELIN: (OpTrace("a", b"", b"\x01" * 32),),  # dirty
        Lane.AVALI: (OpTrace("b", b"", b"\x02" * 32),),  # dirty
        Lane.RUNETHIC: (OpTrace("c", b"", h_clean),),  # clean
        Lane.CASSISIVADAN: (OpTrace("d", b"", h_clean),),  # clean
        Lane.UMBROTH: (OpTrace("e", b"", h_clean),),  # clean
    }
    assert majority_converged(streams) == h_clean


def test_majority_converged_no_strict_majority_in_four():
    h = b"\xdd" * 32
    streams = {
        Lane.KORAELIN: (OpTrace("a", b"", b"\x01" * 32),),
        Lane.AVALI: (OpTrace("b", b"", b"\x02" * 32),),
        Lane.RUNETHIC: (OpTrace("c", b"", h),),
        Lane.CASSISIVADAN: (OpTrace("d", b"", h),),
    }
    # 2 of 4 is not STRICT majority
    assert majority_converged(streams) is None


# --- walker --------------------------------------------------------------- #


def test_walker_bicameral_converges_when_clean():
    matrix = _all_clean_matrix()
    tree = walk(b"hello", matrix)
    assert tree.abridged_form is not None
    assert tree.abridged_form == hash_payload(b"hello")
    assert tree.tier_reached == 2  # T1 (KO) + T2 (AV)
    assert tree.lane_pair.primary == Lane.KORAELIN
    assert tree.lane_pair.adversary == Lane.AVALI


def test_walker_records_op_nodes_for_each_lane_read():
    matrix = _all_clean_matrix()
    tree = walk(b"abc", matrix)
    op_nodes = [n for n in tree.nodes if n.kind == NodeKind.OP]
    # Two lanes converged on first read -> exactly 2 op nodes
    assert len(op_nodes) == 2
    assert {n.lane for n in op_nodes} == {Lane.KORAELIN, Lane.AVALI}
    assert all(n.band == Band.AUDIBLE for n in op_nodes)


def test_walker_escalates_when_pair_diverges():
    matrix = BridgeMatrix()
    matrix.register_reader(Lane.KORAELIN, HashReader(Lane.KORAELIN, perturb=b"X"))
    matrix.register_reader(Lane.AVALI, HashReader(Lane.AVALI, perturb=b"Y"))
    matrix.register_reader(Lane.RUNETHIC, HashReader(Lane.RUNETHIC))
    matrix.register_reader(Lane.CASSISIVADAN, HashReader(Lane.CASSISIVADAN))
    matrix.register_reader(Lane.UMBROTH, HashReader(Lane.UMBROTH))
    matrix.register_reader(Lane.DRAUMRIC, HashReader(Lane.DRAUMRIC))
    tree = walk(b"input", matrix)
    # Convergence happens at T5 (UM): 3 of 5 lanes are clean -> strict majority
    assert tree.abridged_form == hash_payload(b"input")
    assert tree.tier_reached == 5


def test_walker_t6_exhaustion_rigid_refuses():
    # All six lanes perturbed differently — never converges
    matrix = BridgeMatrix()
    for i, lane in enumerate(DEFAULT_LADDER):
        matrix.register_reader(lane, HashReader(lane, perturb=bytes([i])))
    tree = walk(b"input", matrix, posture=Posture.RIGID)
    assert tree.abridged_form is None
    assert tree.tier_reached == 6
    assert tree.provisional_minted is False
    assert tree.terminated_as == Termination.REFUSED
    assert tree.refusal_reason  # non-empty


def test_walker_respects_explicit_initial_pair():
    matrix = _all_clean_matrix()
    pair = LanePair(
        primary=Lane.RUNETHIC,
        adversary=Lane.UMBROTH,
        domain="formal_logic",
    )
    tree = walk(b"x", matrix, initial_pair=pair)
    assert tree.lane_pair == pair
    assert tree.abridged_form is not None
    # Initial tier is the higher of the two: UMBROTH = T5
    assert tree.tier_reached == 5


def test_walker_posture_propagates_to_tree():
    matrix = _all_clean_matrix()
    tree = walk(b"x", matrix, posture=Posture.RIGID)
    assert tree.posture == Posture.RIGID


def test_walker_missing_reader_raises():
    matrix = BridgeMatrix()
    matrix.register_reader(Lane.KORAELIN, HashReader(Lane.KORAELIN))
    # Avali never registered -> KeyError on bicameral read
    with pytest.raises(KeyError):
        # pin pair to KORAELIN+AVALI so we don't depend on default classifier
        walk(
            b"x",
            matrix,
            initial_pair=LanePair(
                primary=Lane.KORAELIN,
                adversary=Lane.AVALI,
            ),
        )


# =========================================================================== #
#  v0.3 — Flag, MoralPrior, sandbox, adversarial pair selection
# =========================================================================== #


# --- Flag ----------------------------------------------------------------- #


def test_flag_defaults():
    f = Flag(source="bijective_tamper", kind="syntax")
    assert f.severity == 0.0
    assert f.metadata == {}


def test_flag_carries_metadata():
    f = Flag(
        source="identifier_canonicality",
        kind="mixed_script",
        severity=0.9,
        metadata={"identifier": "pаssword"},
    )
    assert f.metadata["identifier"] == "pаssword"


# --- IdentityPrior / IsolationPrior --------------------------------------- #


def test_identity_prior_returns_payload_unchanged():
    p = IdentityPrior()
    r = p.inspect(b"hello", [Flag("test", "test")])
    assert r.transformed_payload == b"hello"
    assert r.prior_id == "identity"


def test_isolation_prior_wraps_payload():
    p = IsolationPrior(envelope=b"|")
    r = p.inspect(b"x", [Flag("test", "test")])
    assert r.transformed_payload == b"|x|"
    assert r.prior_id == "isolation"


def test_inspection_result_carries_notes():
    r = InspectionResult(prior_id="x", transformed_payload=b"y", notes="hi")
    assert r.notes == "hi"


# --- sandbox() ------------------------------------------------------------ #


def test_sandbox_requires_flags():
    t = Tree()
    with pytest.raises(ValueError, match="no flags"):
        sandbox(b"x", [], [IdentityPrior()], t)


def test_sandbox_requires_priors():
    t = Tree()
    with pytest.raises(ValueError, match="no priors"):
        sandbox(b"x", [Flag("s", "k")], [], t)


def test_sandbox_adds_provisional_inspections_and_internalized_nodes():
    t = Tree()
    flags = [Flag("bijective_tamper", "syntax", 0.5)]
    priors = [IdentityPrior(), IsolationPrior()]
    sandbox(b"hello", flags, priors, t)
    # 1 VOID + 1 provisional + 2 inspection + 1 internalized = 5 total
    assert len(t.nodes) == 5
    kinds = [n.kind for n in t.nodes]
    assert kinds.count(NodeKind.SANDBOX_PROVISIONAL) == 1
    assert kinds.count(NodeKind.SANDBOX_INSPECTION) == 2
    assert kinds.count(NodeKind.SANDBOX_INTERNALIZED) == 1


def test_sandbox_sets_tree_invoked_flag():
    t = Tree()
    sandbox(b"x", [Flag("s", "k")], [IdentityPrior()], t)
    assert t.sandbox_invoked is True


def test_sandbox_internalized_node_has_result_hash():
    t = Tree()
    sandbox(b"x", [Flag("s", "k")], [IdentityPrior()], t)
    internalized = next(n for n in t.nodes if n.kind == NodeKind.SANDBOX_INTERNALIZED)
    assert internalized.result_hash is not None
    assert len(internalized.result_hash) == 32


def test_sandbox_provisional_records_flags():
    t = Tree()
    flags = [Flag("a", "k1", 0.3), Flag("b", "k2", 0.7)]
    sandbox(b"x", flags, [IdentityPrior()], t)
    prov = next(n for n in t.nodes if n.kind == NodeKind.SANDBOX_PROVISIONAL)
    recorded = prov.payload["flags"]
    assert len(recorded) == 2
    assert recorded[0]["source"] == "a"
    assert recorded[1]["kind"] == "k2"


# --- classify_domain ------------------------------------------------------ #


@pytest.mark.parametrize(
    "text,expected_domain",
    [
        ("forall x, x = x", "formal_logic"),
        ("Theorem: there exists a prime", "formal_logic"),
        ("malloc(64); buffer overflow risk", "low_level"),
        ("integral of x^2 dx", "symbolic_math"),
        ("function add(a, b) { return a + b; }", "scripting"),
        ("the metaphor of the woods", "linguistic_nuance"),
        ("just some random text", "default"),
        ("", "default"),
    ],
)
def test_classify_domain_keyword_match(text, expected_domain):
    assert classify_domain(text.encode("utf-8")) == expected_domain


def test_classify_domain_handles_non_utf8():
    # Invalid UTF-8 bytes shouldn't crash — fall back to default
    assert classify_domain(b"\xff\xfe\xfd random bytes") == "default"


# --- select_initial_pair -------------------------------------------------- #


def test_select_initial_pair_default_domain():
    pair = select_initial_pair(b"random text")
    assert pair.domain == "default"
    assert pair.primary == Lane.KORAELIN
    assert pair.adversary == Lane.AVALI


def test_select_initial_pair_formal_logic():
    pair = select_initial_pair(b"forall x, x implies x")
    assert pair.domain == "formal_logic"
    assert pair.primary == Lane.UMBROTH  # Haskell-spirit
    assert pair.adversary == Lane.AVALI  # JS-spirit


def test_select_initial_pair_low_level():
    pair = select_initial_pair(b"malloc(buffer)")
    assert pair.domain == "low_level"
    assert pair.primary == Lane.RUNETHIC  # Rust-spirit
    assert pair.adversary == Lane.DRAUMRIC  # Markdown-spirit


def test_select_initial_pair_never_self_pair():
    # All domain mappings must produce distinct primary/adversary
    for domain, primary in DOMAIN_PRIMARY.items():
        adversary = DOMAIN_ADVERSARY.get(domain, Lane.AVALI)
        assert primary != adversary, f"domain {domain} self-pairs on {primary}"


# --- walker integration with v0.3 features --------------------------------- #


def test_walker_uses_adversarial_selection_when_no_explicit_pair():
    matrix = _all_clean_matrix()
    tree = walk(b"forall x, x", matrix)
    # formal_logic -> Umbroth + Avali
    assert tree.lane_pair.primary == Lane.UMBROTH
    assert tree.lane_pair.adversary == Lane.AVALI
    assert tree.lane_pair.domain == "formal_logic"


def test_walker_with_flags_invokes_sandbox():
    matrix = _all_clean_matrix()
    tree = walk(
        b"hello",
        matrix,
        flags=[Flag("bijective_tamper", "syntax", 0.5)],
        priors=[IdentityPrior()],
    )
    assert tree.sandbox_invoked is True
    sandbox_kinds = {NodeKind.SANDBOX_PROVISIONAL, NodeKind.SANDBOX_INSPECTION, NodeKind.SANDBOX_INTERNALIZED}
    sandbox_nodes = [n for n in tree.nodes if n.kind in sandbox_kinds]
    assert len(sandbox_nodes) == 3  # provisional + 1 inspection + internalized


def test_walker_without_flags_no_sandbox_nodes():
    matrix = _all_clean_matrix()
    tree = walk(b"hello", matrix)
    assert tree.sandbox_invoked is False
    sandbox_kinds = {NodeKind.SANDBOX_PROVISIONAL, NodeKind.SANDBOX_INSPECTION, NodeKind.SANDBOX_INTERNALIZED}
    sandbox_nodes = [n for n in tree.nodes if n.kind in sandbox_kinds]
    assert sandbox_nodes == []


def test_walker_flags_without_priors_raises():
    matrix = _all_clean_matrix()
    with pytest.raises(ValueError, match="no priors"):
        walk(b"x", matrix, flags=[Flag("s", "k")])


def test_walker_sandbox_vote_does_not_override_lane_majority():
    """Clean lanes converge on hash(payload); sandbox interpretation
    differs but is outvoted. Abridged form is still the lane majority.
    """
    matrix = _all_clean_matrix()
    tree = walk(
        b"hello",
        matrix,
        flags=[Flag("bijective_tamper", "syntax")],
        priors=[IdentityPrior()],
    )
    # 2 lanes vote hash("hello"); sandbox votes hash(hash(hash("hello"))).
    # Strict majority needs >50% which means 2 of 3 -> lanes win.
    assert tree.abridged_form == hash_payload(b"hello")


def test_walker_explicit_pair_overrides_classifier():
    matrix = _all_clean_matrix()
    pin = LanePair(primary=Lane.RUNETHIC, adversary=Lane.UMBROTH, domain="pinned")
    tree = walk(b"forall x, x", matrix, initial_pair=pin)
    # Even though payload classifies as formal_logic, explicit pair wins
    assert tree.lane_pair == pin


# =========================================================================== #
#  v0.4 — Termination, provisional minting, decay registry
# =========================================================================== #


def _all_perturbed_matrix() -> BridgeMatrix:
    """All six lanes perturbed differently — guaranteed T6 exhaustion."""
    matrix = BridgeMatrix()
    for i, lane in enumerate(DEFAULT_LADDER):
        matrix.register_reader(lane, HashReader(lane, perturb=bytes([i + 1])))
    return matrix


# --- Termination enum ----------------------------------------------------- #


def test_termination_enum_has_four_states():
    assert {t.value for t in Termination} == {
        "incomplete",
        "abridged",
        "provisional",
        "refused",
    }


def test_tree_default_termination_is_incomplete():
    assert Tree().terminated_as == Termination.INCOMPLETE


# --- Walker termination tagging ------------------------------------------- #


def test_walker_converged_tags_abridged():
    matrix = _all_clean_matrix()
    tree = walk(b"x", matrix)
    assert tree.terminated_as == Termination.ABRIDGED


def test_walker_humble_t6_exhaustion_mints_provisional():
    matrix = _all_perturbed_matrix()
    tree = walk(b"input", matrix)  # HUMBLE default
    assert tree.tier_reached == 6
    assert tree.provisional_minted is True
    assert tree.abridged_form is not None
    assert tree.terminated_as == Termination.PROVISIONAL
    assert any(n.kind == NodeKind.PROVISIONAL_MINT for n in tree.nodes)


def test_walker_rigid_t6_exhaustion_refuses_with_reason():
    matrix = _all_perturbed_matrix()
    tree = walk(b"input", matrix, posture=Posture.RIGID)
    assert tree.tier_reached == 6
    assert tree.provisional_minted is False
    assert tree.abridged_form is None
    assert tree.terminated_as == Termination.REFUSED
    assert "no representation" in tree.refusal_reason
    assert "T1..T6" in tree.refusal_reason


def test_walker_humble_no_provisional_mint_node_when_converged():
    matrix = _all_clean_matrix()
    tree = walk(b"x", matrix)
    assert not any(n.kind == NodeKind.PROVISIONAL_MINT for n in tree.nodes)


# --- mint_provisional ----------------------------------------------------- #


def test_mint_provisional_deterministic():
    streams = {
        Lane.KORAELIN: (OpTrace("a", b"", b"\x01" * 32),),
        Lane.AVALI: (OpTrace("b", b"", b"\x02" * 32),),
    }
    a = mint_provisional(streams)
    b = mint_provisional(streams)
    assert a == b
    assert len(a) == 32


def test_mint_provisional_order_independent():
    s1 = {
        Lane.KORAELIN: (OpTrace("a", b"", b"\x01" * 32),),
        Lane.AVALI: (OpTrace("b", b"", b"\x02" * 32),),
    }
    s2 = {
        Lane.AVALI: (OpTrace("b", b"", b"\x02" * 32),),
        Lane.KORAELIN: (OpTrace("a", b"", b"\x01" * 32),),
    }
    assert mint_provisional(s1) == mint_provisional(s2)


def test_mint_provisional_includes_extra_votes():
    streams = {Lane.KORAELIN: (OpTrace("a", b"", b"\x01" * 32),)}
    a = mint_provisional(streams)
    b = mint_provisional(streams, extra_votes=[b"\x99" * 32])
    assert a != b


def test_mint_provisional_empty_input_returns_hash_of_empty():
    assert mint_provisional({}) == hash_payload(b"")


# --- ProvisionalRegistry -------------------------------------------------- #


def test_registry_first_record_is_a_mint_with_zero_corroboration():
    reg = ProvisionalRegistry()
    rec = reg.record(b"\xaa" * 32)
    assert rec.corroboration_count == 0
    assert rec.minted_at == 1
    assert rec.last_seen_at == 1


def test_registry_second_record_corroborates():
    reg = ProvisionalRegistry()
    h = b"\xaa" * 32
    reg.record(h)
    rec = reg.record(h)
    assert rec.corroboration_count == 1
    assert rec.minted_at == 1  # original mint
    assert rec.last_seen_at == 2  # refreshed


def test_registry_distinct_hashes_independent():
    reg = ProvisionalRegistry()
    a = reg.record(b"\xaa" * 32)
    b = reg.record(b"\xbb" * 32)
    assert a.minted_at == 1
    assert b.minted_at == 2
    assert len(reg) == 2


def test_registry_get_returns_record_or_none():
    reg = ProvisionalRegistry()
    h = b"\xcc" * 32
    assert reg.get(h) is None
    reg.record(h)
    assert reg.get(h) is not None


def test_registry_contains_membership():
    reg = ProvisionalRegistry()
    h = b"\xdd" * 32
    assert h not in reg
    reg.record(h)
    assert h in reg


def test_registry_decay_removes_stale_under_corroborated():
    reg = ProvisionalRegistry(decay_window=2, min_corroborations=2)
    stale = b"\x01" * 32
    reg.record(stale)
    # advance counter past decay_window without re-recording stale
    for _ in range(5):
        reg.record(b"\x02" * 32)
    removed = reg.decay()
    assert stale in removed
    assert stale not in reg


def test_registry_decay_keeps_corroborated_even_if_stale():
    reg = ProvisionalRegistry(decay_window=2, min_corroborations=2)
    h = b"\xee" * 32
    reg.record(h)
    reg.record(h)  # corroboration_count=1
    reg.record(h)  # corroboration_count=2 -> meets threshold
    # let it go stale by recording other things
    for _ in range(10):
        reg.record(b"\x02" * 32)
    reg.decay()
    assert h in reg


def test_registry_decay_keeps_recent_even_if_under_corroborated():
    reg = ProvisionalRegistry(decay_window=100, min_corroborations=5)
    h = b"\xff" * 32
    reg.record(h)
    reg.decay()
    assert h in reg


# --- Walker integration with registry ------------------------------------- #


def test_walker_records_provisional_in_registry():
    matrix = _all_perturbed_matrix()
    reg = ProvisionalRegistry()
    tree = walk(b"input", matrix, provisional_registry=reg)
    assert tree.terminated_as == Termination.PROVISIONAL
    assert tree.provisional_corroboration_count == 0  # first mint
    assert tree.abridged_form in reg


def test_walker_corroboration_count_increments_on_repeat():
    matrix = _all_perturbed_matrix()
    reg = ProvisionalRegistry()
    t1 = walk(b"input", matrix, provisional_registry=reg)
    t2 = walk(b"input", matrix, provisional_registry=reg)
    assert t1.provisional_corroboration_count == 0
    assert t2.provisional_corroboration_count == 1
    # Both walks produced the same provisional (deterministic mint)
    assert t1.abridged_form == t2.abridged_form


def test_walker_rigid_does_not_touch_registry():
    matrix = _all_perturbed_matrix()
    reg = ProvisionalRegistry()
    tree = walk(b"input", matrix, posture=Posture.RIGID, provisional_registry=reg)
    assert tree.terminated_as == Termination.REFUSED
    assert len(reg) == 0


def test_walker_converged_does_not_touch_registry():
    matrix = _all_clean_matrix()
    reg = ProvisionalRegistry()
    tree = walk(b"x", matrix, provisional_registry=reg)
    assert tree.terminated_as == Termination.ABRIDGED
    assert len(reg) == 0


# =========================================================================== #
#  v0.5 — L14 audio emission adapter
# =========================================================================== #


# --- Constants --------------------------------------------------------------#


def test_lane_to_tri_bundle_code_covers_all_six_tongues():
    expected = {
        Lane.KORAELIN: "ko",
        Lane.AVALI: "av",
        Lane.RUNETHIC: "ru",
        Lane.CASSISIVADAN: "ca",
        Lane.UMBROTH: "um",
        Lane.DRAUMRIC: "dr",
    }
    assert LANE_TO_TRI_BUNDLE_CODE == expected


def test_band_frequency_multiplier_tri_octave_signature():
    # INFRA = -2 octaves, AUDIBLE = fundamental, ULTRA = +2 octaves
    assert BAND_FREQUENCY_MULTIPLIER[Band.INFRA] == 0.25
    assert BAND_FREQUENCY_MULTIPLIER[Band.AUDIBLE] == 1.0
    assert BAND_FREQUENCY_MULTIPLIER[Band.ULTRA] == 4.0


def test_system_fundamental_is_a4():
    assert SYSTEM_FUNDAMENTAL_HZ == 440.0


# --- AudioEvent ------------------------------------------------------------- #


def test_audio_event_is_frozen():
    e = AudioEvent(
        source_node_id=1,
        lane=Lane.KORAELIN,
        band=Band.AUDIBLE,
        frequency_hz=440.0,
        amplitude=0.5,
        phase_rad=0.0,
        duration_s=0.05,
        label="op",
    )
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        e.amplitude = 0.9  # type: ignore[misc]


# --- emit_audio ------------------------------------------------------------- #


def test_emit_audio_empty_tree_produces_no_events():
    """A fresh Tree only contains the VOID singleton, which is silent."""
    tree = Tree()
    em = emit_audio(tree)
    assert em.events == []


def test_emit_audio_op_node_uses_lane_fundamental_at_audible_band():
    matrix = _all_clean_matrix()
    tree = walk(
        b"x",
        matrix,
        initial_pair=LanePair(
            primary=Lane.KORAELIN,
            adversary=Lane.AVALI,
        ),
    )
    em = emit_audio(tree)
    op_events = [e for e in em.events if e.label == "op"]
    assert len(op_events) == 2
    ko_event = next(e for e in op_events if e.lane == Lane.KORAELIN)
    assert ko_event.band == Band.AUDIBLE
    assert ko_event.frequency_hz == 440.0  # ko fundamental
    av_event = next(e for e in op_events if e.lane == Lane.AVALI)
    assert av_event.frequency_hz == 523.25  # av fundamental


def test_emit_audio_amplitude_derived_from_result_hash():
    matrix = _all_clean_matrix()
    tree = walk(b"abc", matrix)
    em = emit_audio(tree)
    op = next(e for e in em.events if e.label == "op")
    op_node = next(n for n in tree.nodes if n.id == op.source_node_id)
    assert op.amplitude == op_node.result_hash[0] / 255.0


def test_emit_audio_void_node_is_silent():
    tree = Tree()
    # Void singleton is at index 0; emit nothing for it
    em = emit_audio(tree)
    assert all(e.source_node_id != NULL_BRIDGE_VOID_ID for e in em.events)


def test_emit_audio_sandbox_emits_infra_and_audible_events():
    matrix = _all_clean_matrix()
    tree = walk(
        b"x",
        matrix,
        flags=[Flag("bijective_tamper", "syntax")],
        priors=[IdentityPrior()],
    )
    em = emit_audio(tree)
    labels = {e.label for e in em.events}
    assert "sandbox.provisional" in labels
    assert "sandbox.inspection" in labels
    assert "sandbox.internalize" in labels
    # provisional + inspection on INFRA band
    provisional = next(e for e in em.events if e.label == "sandbox.provisional")
    assert provisional.band == Band.INFRA
    inspection = next(e for e in em.events if e.label == "sandbox.inspection")
    assert inspection.band == Band.INFRA
    # internalize on AUDIBLE
    internalize = next(e for e in em.events if e.label == "sandbox.internalize")
    assert internalize.band == Band.AUDIBLE


def test_emit_audio_provisional_mint_on_ultra_band():
    matrix = _all_perturbed_matrix()
    tree = walk(b"x", matrix)  # HUMBLE -> mint
    em = emit_audio(tree)
    mint_events = [e for e in em.events if e.label == "provisional_mint"]
    assert len(mint_events) == 1
    assert mint_events[0].band == Band.ULTRA
    # ULTRA at system fundamental = 440 * 4 = 1760 Hz (A6)
    assert mint_events[0].frequency_hz == 1760.0
    assert mint_events[0].lane is None


def test_emit_audio_rigid_refusal_no_provisional_event():
    matrix = _all_perturbed_matrix()
    tree = walk(b"x", matrix, posture=Posture.RIGID)
    em = emit_audio(tree)
    assert all(e.label != "provisional_mint" for e in em.events)


def test_emit_audio_phase_wraps_every_16_nodes():
    # Build two events with node ids 0 and 16: phases should match
    tree = Tree()
    # Add 16 OP nodes after the VOID singleton
    for _ in range(16):
        tree.add_node(
            Node(
                id=len(tree.nodes),
                kind=NodeKind.OP,
                lane=Lane.KORAELIN,
                band=Band.AUDIBLE,
                result_hash=b"\x00" * 32,
            )
        )
    em = emit_audio(tree)
    # node id 16 should have the same phase as node id 0... but node id 0 is
    # VOID (silent). node id 16 wraps to phase 0 (= 2*pi*16/16 = 2*pi mod 2*pi)
    e16 = next(e for e in em.events if e.source_node_id == 16)
    assert abs(e16.phase_rad) < 1e-9


def test_emit_audio_index_by_lane_and_band():
    matrix = _all_clean_matrix()
    tree = walk(
        b"x",
        matrix,
        initial_pair=LanePair(
            primary=Lane.KORAELIN,
            adversary=Lane.AVALI,
        ),
    )
    em = emit_audio(tree)
    by_lane = em.by_lane()
    assert Lane.KORAELIN in by_lane
    assert Lane.AVALI in by_lane
    by_band = em.by_band()
    assert Band.AUDIBLE in by_band
    assert all(e.band == Band.AUDIBLE for e in by_band[Band.AUDIBLE])


def test_emit_audio_event_duration_is_configurable():
    matrix = _all_clean_matrix()
    tree = walk(b"x", matrix)
    em_short = emit_audio(tree, event_duration_s=0.01)
    em_long = emit_audio(tree, event_duration_s=0.5)
    assert all(e.duration_s == 0.01 for e in em_short.events)
    assert all(e.duration_s == 0.5 for e in em_long.events)


def test_emit_audio_event_count_matches_emittable_node_count():
    matrix = _all_clean_matrix()
    tree = walk(b"x", matrix)
    # Tree has: 1 VOID (silent) + N OP nodes
    op_node_count = sum(1 for n in tree.nodes if n.kind == NodeKind.OP)
    em = emit_audio(tree)
    assert len(em.events) == op_node_count


def test_emit_audio_band_multiplier_applied_correctly():
    """Direct test: an INFRA-band Kor'aelin OP node should be at 440/4 = 110 Hz."""
    tree = Tree()
    tree.add_node(
        Node(
            id=len(tree.nodes),
            kind=NodeKind.OP,
            lane=Lane.KORAELIN,
            band=Band.INFRA,
            result_hash=b"\x80" * 32,
        )
    )
    em = emit_audio(tree)
    e = em.events[0]
    assert e.frequency_hz == 110.0  # 440 * 0.25
    assert e.amplitude == 0x80 / 255.0
