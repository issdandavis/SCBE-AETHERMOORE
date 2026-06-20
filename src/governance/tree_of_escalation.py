"""Tree of Escalation v0.5 — compilation-driven multi-tongue escalation.

v0.1: data structures (Lane, Band, Posture, NodeKind, Node, BridgeEdge,
LanePair, VoidStats, Tree, NULL_BRIDGE_VOID_ID).
v0.2: bridge matrix + walker (BridgeMatrix, Reader protocol, OpTrace,
HashReader reference, walk()). Bicameral read with majority-convergence,
bit-depth escalation across DEFAULT_LADDER.
v0.3: sandbox loop (Flag, MoralPrior protocol, IdentityPrior,
IsolationPrior, sandbox()) and input-shape adversarial pair selection
(classify_domain, select_initial_pair).
v0.4: termination posture switch — HUMBLE mints a deterministic
provisional from observed streams; RIGID returns abridged_form=None
with a refusal_reason. ProvisionalRegistry tracks corroboration with
a deterministic call-counter decay policy.
v0.5: L14 audio emission adapter (AudioEvent, TreeAudioEmission,
emit_audio). Each node renders to an audio event with frequency from
tri_bundle.TONGUE_FREQUENCIES; the three Bands map to a tri-octave
signature (INFRA = -2 octaves, AUDIBLE = fundamental, ULTRA = +2
octaves). Synthesis itself is left to downstream consumers.

The structures here implement the locked architectural decisions:

  - Six Sacred Tongue lanes (Kor'aelin, Avali, Runethic, Cassisivadan,
    Umbroth, Draumric) plus a CUSTOM slot for pluggable substrates.
  - Three concurrent bands per lane (INFRA / AUDIBLE / ULTRA).
  - Adversarial lane-pair selection (Primary Resolver + Adversarial
    Reader, chosen by input domain).
  - NULL-bridge serialization as edge-property AND singleton sink:
    per-failure metadata on the edge, aggregate stats on the void node.
  - Posture switch (HUMBLE mints provisional, RIGID refuses) for
    novel-truth termination.

Composes with: ``bijective_tamper.py``, ``identifier_canonicality.py``,
``src/symphonic/audio/tri_bundle.py``, and the seed bridge matrix at
``artifacts/cross_language_lookup/``.
"""

from __future__ import annotations

import enum
import hashlib
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Sequence, Tuple

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

NULL_BRIDGE_VOID_ID: int = 0
"""Canonical id of the singleton sink node for untranslatable bridges.

Per-failure metadata lives on the edges that point here, NOT on this
node. This node carries aggregate stats only.
"""


# --------------------------------------------------------------------------- #
# Lane — the six Sacred Tongue readers (plus a pluggable slot)
# --------------------------------------------------------------------------- #


class Lane(str, enum.Enum):
    """Reader identifier. Six tongues plus a CUSTOM slot for pluggability.

    Order matches the phi-weighted bit-depth ladder T1..T6.
    """

    KORAELIN = "koraelin"  # T1, Python-spirit
    AVALI = "avali"  # T2, JavaScript-spirit
    RUNETHIC = "runethic"  # T3, Rust-spirit
    CASSISIVADAN = "cassisivadan"  # T4, Mathematica-spirit
    UMBROTH = "umbroth"  # T5, Haskell-spirit
    DRAUMRIC = "draumric"  # T6, Markdown-spirit
    CUSTOM = "custom"  # Pluggable substrate; not in default ladder


LANE_PHI_WEIGHT: Dict[Lane, float] = {
    Lane.KORAELIN: 1.00,
    Lane.AVALI: 1.62,
    Lane.RUNETHIC: 2.62,
    Lane.CASSISIVADAN: 4.24,
    Lane.UMBROTH: 6.85,
    Lane.DRAUMRIC: 11.09,
}
"""Phi-scaled weights per tongue. CUSTOM intentionally omitted — its
weight is set per-instance by whoever registers the substrate.
"""


LANE_TIER: Dict[Lane, int] = {
    Lane.KORAELIN: 1,
    Lane.AVALI: 2,
    Lane.RUNETHIC: 3,
    Lane.CASSISIVADAN: 4,
    Lane.UMBROTH: 5,
    Lane.DRAUMRIC: 6,
}
"""Bit-depth tier per lane. CUSTOM omitted; pluggable substrates
declare their own tier at registration time.
"""


DEFAULT_LADDER: Tuple[Lane, ...] = (
    Lane.KORAELIN,
    Lane.AVALI,
    Lane.RUNETHIC,
    Lane.CASSISIVADAN,
    Lane.UMBROTH,
    Lane.DRAUMRIC,
)
"""Canonical phi-weighted escalation order. v0.2+ walker climbs this."""


# --------------------------------------------------------------------------- #
# Band — concurrent state-of-knowledge marker (NOT a tier)
# --------------------------------------------------------------------------- #


class Band(str, enum.Enum):
    INFRA = "infra"  # Pre-computed deterministic atoms (cache, lookup)
    AUDIBLE = "audible"  # Live execution trace
    ULTRA = "ultra"  # Speculative continuations (predicted next ops)


# --------------------------------------------------------------------------- #
# Posture — termination behavior on T6 exhaustion
# --------------------------------------------------------------------------- #


class Posture(str, enum.Enum):
    HUMBLE = "humble"  # Mint a provisional abridged form, file for revisit
    RIGID = "rigid"  # Refuse to compile; return NULL with reason


class Termination(str, enum.Enum):
    """How the walker exited.

    INCOMPLETE is the initial state on a fresh Tree before walk() runs.
    Real termination values are set by walk() before return.
    """

    INCOMPLETE = "incomplete"  # Walk did not run (initial state)
    ABRIDGED = "abridged"  # Strict majority converged
    PROVISIONAL = "provisional"  # HUMBLE mint on T6 exhaustion (v0.4)
    REFUSED = "refused"  # RIGID refusal on T6 exhaustion (v0.4)


# --------------------------------------------------------------------------- #
# NodeKind — categorizes nodes in the tree
# --------------------------------------------------------------------------- #


class NodeKind(str, enum.Enum):
    OP = "op"  # Atomic op trace from a lane
    SANDBOX_PROVISIONAL = "sandbox_provisional"  # Flagged-input provisional ingest
    SANDBOX_INSPECTION = "sandbox_inspection"  # Inspect-under-priors output
    SANDBOX_INTERNALIZED = "sandbox_internalized"  # Own-interpretation node
    NULL_BRIDGE_VOID = "null_bridge_void"  # Singleton sink for null bridges
    PROVISIONAL_MINT = "provisional_mint"  # Humble-posture termination


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #


def hash_payload(data: bytes) -> bytes:
    """SHA-256 of a payload. Returns the raw 32-byte digest."""
    return hashlib.sha256(data).digest()


# --------------------------------------------------------------------------- #
# Node
# --------------------------------------------------------------------------- #


@dataclass
class Node:
    """A node in the escalation tree.

    Most nodes are OP traces from a lane. Special node kinds (sandbox,
    void, provisional) carry kind-specific information in ``payload``.
    The ``lane`` and ``band`` fields are None for non-OP nodes.
    """

    id: int
    kind: NodeKind
    lane: Optional[Lane] = None
    band: Optional[Band] = None
    op_id: Optional[str] = None
    args_hash: Optional[bytes] = None
    result_hash: Optional[bytes] = None
    source: str = ""
    payload: Dict[str, object] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# BridgeEdge — directed edge between nodes
# --------------------------------------------------------------------------- #


@dataclass
class BridgeEdge:
    """Directed edge representing one step of the bridge matrix M.

    For successful bridges (M[i,j](op) is not None):
        is_untranslatable=False, information_variance carries the
        statistical disagreement delta between source and target.

    For NULL bridges:
        is_untranslatable=True, target_id=NULL_BRIDGE_VOID_ID,
        untranslatable_reason and untranslatable_op_id record the
        per-failure metadata.
    """

    source_id: int
    target_id: int
    is_untranslatable: bool = False
    information_variance: float = 0.0
    untranslatable_reason: Optional[str] = None
    untranslatable_op_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# LanePair — adversarial pairing (resolved Q5)
# --------------------------------------------------------------------------- #


@dataclass
class LanePair:
    """Initial-read pair selected by input-shape adversarial pairing.

    primary: lane with highest historical capability in this domain.
    adversary: lane with highest historical disagreement delta against
               primary in the same domain.
    domain: the classified input domain that drove the selection
            (audit field; not used by the walker, only by replay).
    """

    primary: Lane
    adversary: Lane
    domain: str = ""

    def __post_init__(self) -> None:
        if self.primary == self.adversary:
            raise ValueError(f"LanePair primary and adversary must differ; got {self.primary}")


# --------------------------------------------------------------------------- #
# VoidStats — aggregate stats carried by the singleton sink node
# --------------------------------------------------------------------------- #


@dataclass
class VoidStats:
    """Aggregate statistics on the singleton NULL_BRIDGE_VOID node.

    Per-failure metadata lives on the edges, NOT here. This node holds
    rollups for queryable audit.
    """

    incoming_edge_count: int = 0
    distinct_ops_failed: int = 0
    failures_by_lane_pair: Dict[Tuple[Lane, Lane], int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Tree
# --------------------------------------------------------------------------- #


@dataclass
class Tree:
    """The escalation tree. One per call.

    On construction, the singleton VOID sink is inserted at index
    ``NULL_BRIDGE_VOID_ID`` (always the first node). All real nodes are
    appended after it; their ids are their index in ``nodes``.

    NO EXECUTION LOGIC. The walker, sandbox loop, and provisional-mint
    behavior live in v0.2+.
    """

    nodes: List[Node] = field(default_factory=list)
    edges: List[BridgeEdge] = field(default_factory=list)
    lane_pair: Optional[LanePair] = None
    posture: Posture = Posture.HUMBLE
    tier_reached: int = 0
    void_stats: VoidStats = field(default_factory=VoidStats)
    abridged_form: Optional[bytes] = None
    sandbox_invoked: bool = False
    provisional_minted: bool = False
    terminated_as: Termination = Termination.INCOMPLETE
    refusal_reason: str = ""
    provisional_corroboration_count: int = 0

    def __post_init__(self) -> None:
        if not self.nodes:
            self.nodes.append(
                Node(
                    id=NULL_BRIDGE_VOID_ID,
                    kind=NodeKind.NULL_BRIDGE_VOID,
                    source="tree_init",
                )
            )

    def add_node(self, node: Node) -> int:
        """Append a node. Caller must set ``node.id`` to the next index."""
        if node.id != len(self.nodes):
            raise ValueError(f"node id {node.id} != insertion index {len(self.nodes)}")
        self.nodes.append(node)
        return node.id

    def add_edge(self, edge: BridgeEdge) -> None:
        """Append an edge. NULL-bridge edges update void_stats automatically.

        ``distinct_ops_failed`` is recomputed from scratch each time so
        cross-edge dedup is correct.
        """
        if (
            edge.target_id < 0
            or edge.target_id >= len(self.nodes)
            or edge.source_id < 0
            or edge.source_id >= len(self.nodes)
        ):
            raise ValueError(f"edge endpoints out of range: {edge.source_id} -> {edge.target_id}")
        if edge.is_untranslatable and edge.target_id != NULL_BRIDGE_VOID_ID:
            raise ValueError("untranslatable edges must terminate at NULL_BRIDGE_VOID_ID")
        self.edges.append(edge)
        if edge.is_untranslatable:
            self.void_stats.incoming_edge_count += 1
            distinct_ops = {
                e.untranslatable_op_id for e in self.edges if e.is_untranslatable and e.untranslatable_op_id is not None
            }
            self.void_stats.distinct_ops_failed = len(distinct_ops)
            if self.lane_pair is not None:
                key = (self.lane_pair.primary, self.lane_pair.adversary)
                self.void_stats.failures_by_lane_pair[key] = self.void_stats.failures_by_lane_pair.get(key, 0) + 1


# =========================================================================== #
#  v0.2 — Bridge matrix, readers, walker
# =========================================================================== #


# --------------------------------------------------------------------------- #
#  OpTrace — one atomic operation observation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class OpTrace:
    """One atomic operation as observed in a lane.

    op_id is human-readable for audit (e.g., ``"koraelin.tokenize[0:32]"``).
    args_hash and result_hash are 32-byte SHA-256 digests.
    """

    op_id: str
    args_hash: bytes
    result_hash: bytes


# --------------------------------------------------------------------------- #
#  Reader protocol + reference HashReader
# --------------------------------------------------------------------------- #


class Reader(Protocol):
    """A lane reader: payload bytes -> sequence of atomic op traces.

    Implementations are pluggable per the gunpowder principle. The walker
    does not assume what the reader does internally; it only consumes the
    op-stream the reader emits.
    """

    def read(self, payload: bytes) -> Sequence[OpTrace]:
        raise NotImplementedError


@dataclass
class HashReader:
    """Reference reader for v0.2 testing and demos.

    The reader's final result_hash is ``sha256(payload || perturb)``. Two
    HashReaders with empty perturb agree. A reader with a non-empty
    perturb diverges from clean readers — this is how v0.2 tests
    demonstrate escalation behavior without needing real LLM lanes.
    """

    lane: Lane
    perturb: bytes = b""

    def read(self, payload: bytes) -> Sequence[OpTrace]:
        return (
            OpTrace(
                op_id=f"{self.lane.value}.read",
                args_hash=hash_payload(payload),
                result_hash=hash_payload(payload + self.perturb),
            ),
        )


# --------------------------------------------------------------------------- #
#  Bridge matrix M
# --------------------------------------------------------------------------- #

BridgeFn = Callable[[OpTrace], Optional[OpTrace]]


class BridgeMatrix:
    """6x6 (plus CUSTOM) registry of readers and inter-lane bridges.

    Identity bridges (M[i,i]) are implicit and always return the input op
    unchanged. Off-diagonal bridges may return None to signal a NULL
    bridge, which the walker records as an untranslatable edge into the
    singleton sink.
    """

    def __init__(self) -> None:
        self._readers: Dict[Lane, Reader] = {}
        self._bridges: Dict[Tuple[Lane, Lane], BridgeFn] = {}

    def register_reader(self, lane: Lane, reader: Reader) -> None:
        self._readers[lane] = reader

    def register_bridge(self, src: Lane, dst: Lane, fn: BridgeFn) -> None:
        if src == dst:
            raise ValueError("identity bridge is implicit; do not register")
        self._bridges[(src, dst)] = fn

    def reader_for(self, lane: Lane) -> Reader:
        if lane not in self._readers:
            raise KeyError(f"no reader registered for {lane}")
        return self._readers[lane]

    def has_reader(self, lane: Lane) -> bool:
        return lane in self._readers

    def bridge(self, src: Lane, dst: Lane, op: OpTrace) -> Optional[OpTrace]:
        if src == dst:
            return op
        fn = self._bridges.get((src, dst))
        if fn is None:
            return None
        return fn(op)


# --------------------------------------------------------------------------- #
#  Convergence — strict-majority on final result_hash
# --------------------------------------------------------------------------- #


def majority_converged(
    streams: Dict[Lane, Sequence[OpTrace]],
    extra_votes: Sequence[bytes] = (),
) -> Optional[bytes]:
    """Return the strict-majority final result_hash, or None.

    Per spec: "abridged form lives at the LOWEST tier where MAJORITY
    agreed." Agreement is exact-hash on the final op of each lane's
    stream. Strict majority: more than half of all voters (lane streams
    + extra_votes) must produce the same final hash.

    extra_votes (v0.3+) are additional result_hashes that participate
    in the vote alongside the lane streams — used by the sandbox loop
    to inject the internalized own-interpretation as an extra voter.
    """
    if not streams and not extra_votes:
        return None
    finals: List[Optional[bytes]] = []
    for stream in streams.values():
        finals.append(stream[-1].result_hash if stream else None)
    finals.extend(extra_votes)
    counts = Counter(finals)
    most_common, count = counts.most_common(1)[0]
    if most_common is None:
        return None
    if count * 2 > len(finals):
        return most_common
    return None


# --------------------------------------------------------------------------- #
#  Walker
# --------------------------------------------------------------------------- #

# =========================================================================== #
#  v0.3 — Sandbox loop and adversarial pair selection
# =========================================================================== #


# --------------------------------------------------------------------------- #
#  Flag — what an upstream gate raised about the input
# --------------------------------------------------------------------------- #


@dataclass
class Flag:
    """A signal from an upstream gate that the input needs sandbox routing.

    A flag does NOT block the read. It diverts the read through the
    sandbox loop before the bicameral read fans out.

    source: which gate raised it (e.g., "bijective_tamper",
            "identifier_canonicality").
    kind:   gate-specific kind (e.g., "syntax", "mixed_script").
    severity: 0.0-1.0; informational for audit, not used to gate.
    metadata: gate-specific structured payload.
    """

    source: str
    kind: str
    severity: float = 0.0
    metadata: Dict[str, object] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
#  MoralPrior protocol + reference implementations
# --------------------------------------------------------------------------- #


@dataclass
class InspectionResult:
    """Output of one prior inspecting the flagged payload.

    transformed_payload is a re-rendering of the input through this
    prior's lens — NOT a verdict. The walker uses transformed payloads
    to compute the internalized own-interpretation hash that joins the
    convergence vote.
    """

    prior_id: str
    transformed_payload: bytes
    notes: str = ""


class MoralPrior(Protocol):
    """A prior that inspects flagged input and returns a transformed reading."""

    @property
    def prior_id(self) -> str:
        raise NotImplementedError

    def inspect(self, payload: bytes, flags: Sequence[Flag]) -> InspectionResult:
        raise NotImplementedError


@dataclass
class IdentityPrior:
    """Reference no-op prior: returns the payload unchanged.

    Useful as a baseline when callers want to invoke the sandbox
    machinery without transforming the input.
    """

    prior_id: str = "identity"

    def inspect(self, payload: bytes, flags: Sequence[Flag]) -> InspectionResult:
        return InspectionResult(
            prior_id=self.prior_id,
            transformed_payload=payload,
            notes="identity prior; no transform applied",
        )


@dataclass
class IsolationPrior:
    """Reference prior that wraps payload in an isolation envelope.

    Demonstrates a non-trivial prior. Production deployments register
    their own moral-compass priors instead of (or alongside) this.
    """

    prior_id: str = "isolation"
    envelope: bytes = b"<isolated>"

    def inspect(self, payload: bytes, flags: Sequence[Flag]) -> InspectionResult:
        return InspectionResult(
            prior_id=self.prior_id,
            transformed_payload=self.envelope + payload + self.envelope,
            notes=f"wrapped in {self.envelope!r}; flag_count={len(flags)}",
        )


# --------------------------------------------------------------------------- #
#  Sandbox loop
# --------------------------------------------------------------------------- #


def sandbox(
    payload: bytes,
    flags: Sequence[Flag],
    priors: Sequence[MoralPrior],
    tree: Tree,
) -> bytes:
    """Run the sandbox loop on flagged input. Mutates tree.

    Spec section 6 steps:
      1. Provisional ingest -> SANDBOX_PROVISIONAL node.
      2. Inspection under each prior -> SANDBOX_INSPECTION node per prior.
      3. Internalize: combine prior outputs deterministically.
      4. Add SANDBOX_INTERNALIZED node carrying the internalized hash.

    Returns the internalized own-interpretation payload (raw bytes, not
    hash). The caller hashes it and passes the hash as an extra_vote to
    majority_converged so the sandbox interpretation participates in
    the convergence decision without overriding it.
    """
    if not flags:
        raise ValueError("sandbox called with no flags")
    if not priors:
        raise ValueError("sandbox called with no priors registered")

    tree.add_node(
        Node(
            id=len(tree.nodes),
            kind=NodeKind.SANDBOX_PROVISIONAL,
            source="sandbox.provisional_ingest",
            payload={
                "raw_hash": hash_payload(payload).hex(),
                "flags": [{"source": f.source, "kind": f.kind, "severity": f.severity} for f in flags],
            },
        )
    )

    inspection_results: List[InspectionResult] = []
    for prior in priors:
        result = prior.inspect(payload, flags)
        inspection_results.append(result)
        tree.add_node(
            Node(
                id=len(tree.nodes),
                kind=NodeKind.SANDBOX_INSPECTION,
                source=f"sandbox.inspection.{result.prior_id}",
                payload={
                    "prior_id": result.prior_id,
                    "transformed_hash": hash_payload(result.transformed_payload).hex(),
                    "notes": result.notes,
                },
            )
        )

    internalized = b""
    for r in inspection_results:
        internalized += hash_payload(r.transformed_payload)
    internalized_hash = hash_payload(internalized)

    tree.add_node(
        Node(
            id=len(tree.nodes),
            kind=NodeKind.SANDBOX_INTERNALIZED,
            source="sandbox.internalize",
            result_hash=internalized_hash,
            payload={
                "prior_count": len(inspection_results),
                "internalized_hash": internalized_hash.hex(),
            },
        )
    )

    tree.sandbox_invoked = True
    return internalized


# --------------------------------------------------------------------------- #
#  Input-shape adversarial pair selection (Q5 lock)
# --------------------------------------------------------------------------- #

DOMAIN_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "formal_logic": ("forall", "exists", "implies", "lemma", "theorem", "axiom"),
    "low_level": ("malloc", "ptr", "buffer", "unsafe", "&mut", "asm"),
    "symbolic_math": ("integral", "matrix", "eigen", "tensor", "polynomial"),
    "scripting": ("function ", "var ", "const ", "=>", "console.log"),
    "linguistic_nuance": ("metaphor", "connotation", "rhetoric", "irony"),
}
"""Stub keyword table for v0.3 domain classification. Replace with a
learned classifier in v0.4+.
"""


DOMAIN_PRIMARY: Dict[str, Lane] = {
    "default": Lane.KORAELIN,
    "formal_logic": Lane.UMBROTH,
    "low_level": Lane.RUNETHIC,
    "symbolic_math": Lane.CASSISIVADAN,
    "scripting": Lane.AVALI,
    "linguistic_nuance": Lane.DRAUMRIC,
}
"""Domain -> Primary Resolver lane (highest historical capability stub)."""


DOMAIN_ADVERSARY: Dict[str, Lane] = {
    "default": Lane.AVALI,
    "formal_logic": Lane.AVALI,
    "low_level": Lane.DRAUMRIC,
    "symbolic_math": Lane.AVALI,
    "scripting": Lane.UMBROTH,
    "linguistic_nuance": Lane.RUNETHIC,
}
"""Domain -> Adversarial Reader lane (highest historical disagreement
delta against primary in this domain — stub).
"""


def classify_domain(payload: bytes) -> str:
    """Stub domain classifier. v0.3 uses keyword matching.

    v0.4+ will replace with a learned classifier. Falls back to
    ``"default"`` when no keyword matches or the payload isn't
    decodable as UTF-8.
    """
    try:
        text = payload.decode("utf-8", errors="replace").lower()
    except Exception:
        return "default"
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return domain
    return "default"


def select_initial_pair(payload: bytes) -> LanePair:
    """Q5-locked input-shape adversarial pair selection.

    Classifies the input domain, picks the lane with highest historical
    capability in that domain (Primary Resolver), and pairs it with the
    lane that historically disagrees most with the Primary in that
    domain (Adversarial Reader). v0.3 uses static stub tables; v0.4+
    will populate from real capability/disagreement metrics.
    """
    domain = classify_domain(payload)
    primary = DOMAIN_PRIMARY.get(domain, Lane.KORAELIN)
    adversary = DOMAIN_ADVERSARY.get(domain, Lane.AVALI)
    if primary == adversary:
        adversary = Lane.AVALI if primary != Lane.AVALI else Lane.KORAELIN
    return LanePair(primary=primary, adversary=adversary, domain=domain)


# --------------------------------------------------------------------------- #
#  Walker (v0.3: sandbox + adversarial pair selection wired in)
# --------------------------------------------------------------------------- #


def walk(
    payload: bytes,
    matrix: BridgeMatrix,
    *,
    posture: Posture = Posture.HUMBLE,
    initial_pair: Optional[LanePair] = None,
    flags: Sequence[Flag] = (),
    priors: Sequence[MoralPrior] = (),
    provisional_registry: Optional["ProvisionalRegistry"] = None,
) -> Tree:
    """Bicameral read + bit-depth escalation.

    v0.3 additions:
      - If ``flags`` is non-empty, route through sandbox loop first;
        the internalized own-interpretation hash joins convergence vote.
      - When ``initial_pair`` is None, use input-shape adversarial pair
        selection (Q5 lock) instead of the static Kor'aelin+Avali
        default.

    v0.4 additions:
      - On T6 exhaustion under HUMBLE posture, mint a deterministic
        provisional from observed streams and set
        ``terminated_as=PROVISIONAL``.
      - On T6 exhaustion under RIGID posture, leave abridged_form=None
        and set ``terminated_as=REFUSED`` with a refusal_reason.
      - When ``provisional_registry`` is supplied and a provisional is
        minted, the registry records the mint and the resulting
        corroboration_count is propagated to ``tree``.
    """
    tree = Tree(posture=posture)

    extra_votes: List[bytes] = []
    if flags:
        if not priors:
            raise ValueError("flags supplied but no priors registered")
        internalized = sandbox(payload, flags, priors, tree)
        extra_votes.append(hash_payload(internalized))

    if initial_pair is None:
        initial_pair = select_initial_pair(payload)
    tree.lane_pair = initial_pair

    active_lanes: List[Lane] = [initial_pair.primary, initial_pair.adversary]
    streams: Dict[Lane, Sequence[OpTrace]] = {}

    def _ingest(lane: Lane, source_label: str) -> None:
        stream = matrix.reader_for(lane).read(payload)
        streams[lane] = stream
        for op in stream:
            tree.add_node(
                Node(
                    id=len(tree.nodes),
                    kind=NodeKind.OP,
                    lane=lane,
                    band=Band.AUDIBLE,
                    op_id=op.op_id,
                    args_hash=op.args_hash,
                    result_hash=op.result_hash,
                    source=source_label,
                )
            )

    for lane in active_lanes:
        _ingest(lane, "walker.bicameral_read")
    tree.tier_reached = max(
        (LANE_TIER.get(lane, 0) for lane in active_lanes),
        default=0,
    )

    abridged = majority_converged(streams, extra_votes=extra_votes)
    if abridged is not None:
        tree.abridged_form = abridged
        tree.terminated_as = Termination.ABRIDGED
        return tree

    for next_lane in DEFAULT_LADDER:
        if next_lane in active_lanes:
            continue
        if LANE_TIER[next_lane] <= tree.tier_reached:
            continue
        active_lanes.append(next_lane)
        _ingest(next_lane, "walker.escalation")
        tree.tier_reached = LANE_TIER[next_lane]
        abridged = majority_converged(streams, extra_votes=extra_votes)
        if abridged is not None:
            tree.abridged_form = abridged
            tree.terminated_as = Termination.ABRIDGED
            return tree

    # T6 exhaustion — posture switch (v0.4)
    if posture == Posture.HUMBLE:
        provisional_hash = mint_provisional(streams, extra_votes=extra_votes)
        tree.add_node(
            Node(
                id=len(tree.nodes),
                kind=NodeKind.PROVISIONAL_MINT,
                source="walker.provisional_mint",
                result_hash=provisional_hash,
                payload={
                    "tier_reached": tree.tier_reached,
                    "lane_count": len(streams),
                    "provisional_hash": provisional_hash.hex(),
                },
            )
        )
        tree.abridged_form = provisional_hash
        tree.provisional_minted = True
        tree.terminated_as = Termination.PROVISIONAL
        if provisional_registry is not None:
            rec = provisional_registry.record(provisional_hash)
            tree.provisional_corroboration_count = rec.corroboration_count
    else:
        tree.refusal_reason = (
            f"no representation across T1..T{tree.tier_reached}; " f"{len(streams)} lanes did not converge"
        )
        tree.terminated_as = Termination.REFUSED

    return tree


# =========================================================================== #
#  v0.4 — Provisional minting + decay registry
# =========================================================================== #


def mint_provisional(
    streams: Dict[Lane, Sequence[OpTrace]],
    extra_votes: Sequence[bytes] = (),
) -> bytes:
    """Synthesize a provisional abridged form from observed streams.

    Deterministic: collect the unique final result_hashes across all
    lanes (and any extra_votes from the sandbox loop), sort, concatenate,
    and SHA-256. Same set of voters always produces the same provisional.

    The hash is intentionally NOT distinguishable from a majority-converged
    hash by inspection alone — the distinction lives in the Tree
    (``tree.terminated_as == PROVISIONAL`` and ``provisional_minted=True``).
    """
    finals: set = set()
    for stream in streams.values():
        if stream:
            finals.add(stream[-1].result_hash)
    for vote in extra_votes:
        finals.add(vote)
    if not finals:
        return hash_payload(b"")
    sorted_finals = sorted(finals)
    return hash_payload(b"".join(sorted_finals))


@dataclass
class ProvisionalRecord:
    """One minted provisional with its corroboration history.

    minted_at and last_seen_at are monotonic call-counter values from
    the registry, NOT wall-clock — keeps the registry deterministic for
    replay and audit.
    """

    provisional_hash: bytes
    minted_at: int
    corroboration_count: int = 0
    last_seen_at: int = 0


class ProvisionalRegistry:
    """In-memory registry of minted provisionals with decay policy.

    Deterministic by design: uses a monotonic call counter rather than
    wall-clock time. Decay removes provisionals that are stale (last
    seen more than ``decay_window`` calls ago) AND under-corroborated
    (fewer than ``min_corroborations`` re-mints).

    Defaults are conservative — most v0.4 deployments will tune these
    based on workload. Production wire-up is v1.0.
    """

    def __init__(
        self,
        *,
        decay_window: int = 100,
        min_corroborations: int = 3,
    ) -> None:
        self._store: Dict[bytes, ProvisionalRecord] = {}
        self._call_counter: int = 0
        self.decay_window = decay_window
        self.min_corroborations = min_corroborations

    @property
    def call_counter(self) -> int:
        return self._call_counter

    def record(self, provisional_hash: bytes) -> ProvisionalRecord:
        """Mint a new provisional or corroborate an existing one.

        First call for a given hash creates a record with
        ``corroboration_count=0``. Each subsequent call for the same
        hash increments ``corroboration_count`` and refreshes
        ``last_seen_at``.
        """
        self._call_counter += 1
        rec = self._store.get(provisional_hash)
        if rec is None:
            rec = ProvisionalRecord(
                provisional_hash=provisional_hash,
                minted_at=self._call_counter,
                corroboration_count=0,
                last_seen_at=self._call_counter,
            )
            self._store[provisional_hash] = rec
        else:
            rec.corroboration_count += 1
            rec.last_seen_at = self._call_counter
        return rec

    def get(self, provisional_hash: bytes) -> Optional[ProvisionalRecord]:
        return self._store.get(provisional_hash)

    def decay(self) -> List[bytes]:
        """Remove stale, un-corroborated provisionals. Returns removed hashes."""
        removed: List[bytes] = []
        for h, rec in list(self._store.items()):
            stale = (self._call_counter - rec.last_seen_at) > self.decay_window
            under_corroborated = rec.corroboration_count < self.min_corroborations
            if stale and under_corroborated:
                del self._store[h]
                removed.append(h)
        return removed

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, provisional_hash: bytes) -> bool:
        return provisional_hash in self._store


# =========================================================================== #
#  v0.5 — L14 audio emission adapter
# =========================================================================== #


# Frequencies are sourced from the canonical tri_bundle table so the audio
# emission stays in sync with the Crypto/L14 substrate. Imported lazily inside
# helpers to avoid a hard module-import cycle if tri_bundle ever evolves; the
# fallback table mirrors the values at the time of writing.
_FALLBACK_LANE_FREQUENCY_HZ: Dict[Lane, float] = {
    Lane.KORAELIN: 440.00,  # A4 — ko in tri_bundle
    Lane.AVALI: 523.25,  # C5 — av
    Lane.RUNETHIC: 293.66,  # D4 — ru
    Lane.CASSISIVADAN: 659.25,  # E5 — ca
    Lane.UMBROTH: 196.00,  # G3 — um
    Lane.DRAUMRIC: 392.00,  # G4 — dr
}


LANE_TO_TRI_BUNDLE_CODE: Dict[Lane, str] = {
    Lane.KORAELIN: "ko",
    Lane.AVALI: "av",
    Lane.RUNETHIC: "ru",
    Lane.CASSISIVADAN: "ca",
    Lane.UMBROTH: "um",
    Lane.DRAUMRIC: "dr",
}


BAND_FREQUENCY_MULTIPLIER: Dict[Band, float] = {
    Band.INFRA: 0.25,  # -2 octaves
    Band.AUDIBLE: 1.0,  # fundamental
    Band.ULTRA: 4.0,  # +2 octaves
}


SYSTEM_FUNDAMENTAL_HZ: float = 440.0
"""Fundamental frequency for non-lane (system) events: sandbox nodes,
provisional mints. Tri-octave signature still applies via Band multiplier.
"""


def _lane_frequency_hz(lane: Optional[Lane]) -> float:
    """Resolve a lane's fundamental frequency, with tri_bundle as the
    canonical source and a fallback table baked in.
    """
    if lane is None or lane == Lane.CUSTOM:
        return SYSTEM_FUNDAMENTAL_HZ
    try:
        from src.crypto.tri_bundle import TONGUE_FREQUENCIES

        code = LANE_TO_TRI_BUNDLE_CODE[lane]
        return TONGUE_FREQUENCIES[code]
    except Exception:
        return _FALLBACK_LANE_FREQUENCY_HZ.get(lane, SYSTEM_FUNDAMENTAL_HZ)


def _frequency_for(lane: Optional[Lane], band: Band) -> float:
    """Per-(lane, band) frequency: lane fundamental times band multiplier."""
    return _lane_frequency_hz(lane) * BAND_FREQUENCY_MULTIPLIER[band]


def _amplitude_from_hash(h: Optional[bytes], default: float = 0.5) -> float:
    """Deterministic amplitude in [0.0, 1.0] derived from a result_hash.

    Empty/None hash falls back to ``default``. First byte of the hash
    is used so the amplitude reflects the head of the digest space
    (uniform if hash is uniform).
    """
    if not h:
        return default
    return h[0] / 255.0


def _phase_from_id(node_id: int) -> float:
    """Phase angle in [0, 2π) derived from node_id. Wraps every 16 ids."""
    return (2.0 * math.pi * node_id / 16.0) % (2.0 * math.pi)


# --------------------------------------------------------------------------- #
#  AudioEvent + TreeAudioEmission
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AudioEvent:
    """One audio event derived from a tree node.

    lane is None for system events (sandbox nodes, provisional mints,
    void). band always set — system events still pick a band so the
    emission has consistent tri-band structure.
    """

    source_node_id: int
    lane: Optional[Lane]
    band: Band
    frequency_hz: float
    amplitude: float
    phase_rad: float
    duration_s: float
    label: str


@dataclass
class TreeAudioEmission:
    """Audio emission from one tree.

    events is the canonical ordered list (matches node order). by_lane
    and by_band are convenience indexes computed on demand.
    """

    events: List[AudioEvent] = field(default_factory=list)

    def by_lane(self) -> Dict[Optional[Lane], List[AudioEvent]]:
        out: Dict[Optional[Lane], List[AudioEvent]] = {}
        for e in self.events:
            out.setdefault(e.lane, []).append(e)
        return out

    def by_band(self) -> Dict[Band, List[AudioEvent]]:
        out: Dict[Band, List[AudioEvent]] = {}
        for e in self.events:
            out.setdefault(e.band, []).append(e)
        return out


# --------------------------------------------------------------------------- #
#  Per-NodeKind emission rules
# --------------------------------------------------------------------------- #

# Map: NodeKind -> (band, label, default_amplitude). Lane is taken from the
# node when present, else None. NULL_BRIDGE_VOID is intentionally absent —
# the void sink emits nothing.
_NODEKIND_EMISSION: Dict[NodeKind, Tuple[Band, str, float]] = {
    NodeKind.OP: (Band.AUDIBLE, "op", 0.5),
    NodeKind.SANDBOX_PROVISIONAL: (Band.INFRA, "sandbox.provisional", 0.7),
    NodeKind.SANDBOX_INSPECTION: (Band.INFRA, "sandbox.inspection", 0.5),
    NodeKind.SANDBOX_INTERNALIZED: (Band.AUDIBLE, "sandbox.internalize", 0.6),
    NodeKind.PROVISIONAL_MINT: (Band.ULTRA, "provisional_mint", 0.8),
}


def emit_audio(
    tree: Tree,
    *,
    event_duration_s: float = 0.05,
) -> TreeAudioEmission:
    """Render a tree as a sequence of AudioEvents.

    Emission rules per NodeKind:
      OP                    -> AUDIBLE band, lane fundamental
      SANDBOX_PROVISIONAL   -> INFRA band, system fundamental
      SANDBOX_INSPECTION    -> INFRA band, system fundamental
      SANDBOX_INTERNALIZED  -> AUDIBLE band, system fundamental
      PROVISIONAL_MINT      -> ULTRA band, system fundamental
      NULL_BRIDGE_VOID      -> silent (no event)

    Frequency = lane_fundamental * band_multiplier (tri-octave signature).
    Amplitude = first byte of result_hash / 255 (or default per kind).
    Phase = 2*pi * node_id / 16, wrapping.

    Synthesis to a waveform is left to downstream consumers; v0.5 ships
    the EVENT stream only.
    """
    emission = TreeAudioEmission()
    for node in tree.nodes:
        rule = _NODEKIND_EMISSION.get(node.kind)
        if rule is None:
            continue  # NULL_BRIDGE_VOID and any future silent kinds
        band, label, default_amp = rule
        # OP nodes: prefer the node's own band if set, fall back to rule.
        if node.kind == NodeKind.OP and node.band is not None:
            band = node.band
        lane = node.lane if node.kind == NodeKind.OP else None
        emission.events.append(
            AudioEvent(
                source_node_id=node.id,
                lane=lane,
                band=band,
                frequency_hz=_frequency_for(lane, band),
                amplitude=_amplitude_from_hash(node.result_hash, default=default_amp),
                phase_rad=_phase_from_id(node.id),
                duration_s=event_duration_s,
                label=label,
            )
        )
    return emission
