"""
Nodal Graph — Self-Propagating Training Network
=================================================

A directed graph where each node is a PolyhedralRecord and edges represent
tongue affinity, consonance proximity, and harmonic distance.

Self-propagation mechanics:
    1. Seed nodes are injected (generation 0).
    2. ALLOW nodes sprout neighbors via tongue complement + dead-tone rotation.
    3. QUARANTINE nodes store as boundary — no outbound edges.
    4. DENY nodes store as negative examples — terminal.
    5. Each generation produces the next wave of records.

Growth follows phi:
    - Edge weight = 1 / (1 + phi * harmonic_distance)
    - Nodes cluster by tongue affinity (phi-scaled hierarchy)
    - Dense clusters = well-understood domains
    - Sparse regions = frontiers needing more data

Dead tones prevent echo chambers:
    - New records rotate through all 3 dead tones
    - Each generation shifts baseline → different consonance landscape
    - Network can't drift into self-reinforcing hallucination

Training harvest:
    - POSITIVE nodes → SFT examples
    - BOUNDARY nodes → hard examples (DPO preferred)
    - NEGATIVE nodes → DPO rejected
    - All nodes carry 14 feature layers for multi-task training

@layer All layers (L1-L14)
@component Nodal Graph
@axiom A3 (Causality): generation ordering enforces time direction
@axiom A4 (Symmetry): edge weights are symmetric
@axiom A5 (Composition): graph preserves pipeline integrity

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .polyhedral_node import (
    PHI,
    ALL_TONGUES,
    DEAD_TONES,
    COMPLEMENT_MAP,
    TONGUE_WEIGHTS,
    GovernanceVerdict,
    PropagationLabel,
    PolyhedralRecord,
    generate_record,
)


# ---------------------------------------------------------------------------
# Edge and Graph structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NodalEdge:
    """Directed edge between two polyhedral records."""
    source_hash: str
    target_hash: str
    weight: float             # [0, 1] — higher = stronger affinity
    edge_type: str            # "tongue_complement", "dead_tone_rotation", "affinity"


@dataclass
class NodalGraph:
    """Self-propagating training network.

    Nodes are PolyhedralRecords. Edges connect related records.
    Growth happens by sprouting new records from ALLOW nodes.
    """
    nodes: Dict[str, PolyhedralRecord] = field(default_factory=dict)
    edges: List[NodalEdge] = field(default_factory=list)
    _edge_index: Dict[str, List[NodalEdge]] = field(default_factory=dict)

    # Statistics
    generation_count: int = 0
    total_allow: int = 0
    total_quarantine: int = 0
    total_deny: int = 0

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def density(self) -> float:
        """Graph density [0, 1]. Dense = well-connected."""
        n = self.node_count
        if n < 2:
            return 0.0
        max_edges = n * (n - 1)
        return self.edge_count / max_edges

    def add_node(self, record: PolyhedralRecord) -> bool:
        """Add a polyhedral record to the graph.

        Returns True if added, False if duplicate.
        """
        if record.node_hash in self.nodes:
            return False

        self.nodes[record.node_hash] = record
        self._edge_index[record.node_hash] = []

        # Update stats
        if record.verdict == GovernanceVerdict.ALLOW:
            self.total_allow += 1
        elif record.verdict == GovernanceVerdict.QUARANTINE:
            self.total_quarantine += 1
        else:
            self.total_deny += 1

        return True

    def add_edge(self, edge: NodalEdge) -> None:
        """Add a directed edge between two nodes."""
        if edge.source_hash in self.nodes and edge.target_hash in self.nodes:
            self.edges.append(edge)
            self._edge_index.setdefault(edge.source_hash, []).append(edge)

    def get_neighbors(self, node_hash: str) -> List[str]:
        """Get target hashes of all outbound edges from a node."""
        return [e.target_hash for e in self._edge_index.get(node_hash, [])]

    def get_node(self, node_hash: str) -> Optional[PolyhedralRecord]:
        return self.nodes.get(node_hash)

    def nodes_by_verdict(self, verdict: GovernanceVerdict) -> List[PolyhedralRecord]:
        return [n for n in self.nodes.values() if n.verdict == verdict]

    def nodes_by_generation(self, gen: int) -> List[PolyhedralRecord]:
        return [n for n in self.nodes.values() if n.generation == gen]

    def nodes_by_tongue(self, tongue: str) -> List[PolyhedralRecord]:
        return [n for n in self.nodes.values() if n.dominant_tongue == tongue]

    def harvest_positive(self) -> List[PolyhedralRecord]:
        """Get all ALLOW records for SFT training."""
        return self.nodes_by_verdict(GovernanceVerdict.ALLOW)

    def harvest_boundary(self) -> List[PolyhedralRecord]:
        """Get all QUARANTINE records for DPO boundary examples."""
        return self.nodes_by_verdict(GovernanceVerdict.QUARANTINE)

    def harvest_negative(self) -> List[PolyhedralRecord]:
        """Get all ESCALATE/DENY records for DPO rejected examples."""
        return (self.nodes_by_verdict(GovernanceVerdict.ESCALATE)
                + self.nodes_by_verdict(GovernanceVerdict.DENY))


# ---------------------------------------------------------------------------
# Edge weight computation
# ---------------------------------------------------------------------------

def compute_edge_weight(source: PolyhedralRecord, target: PolyhedralRecord) -> float:
    """Compute affinity-based edge weight between two records.

    weight = 1 / (1 + phi * d)

    where d combines:
        - Tongue distance (L2 distance between tongue vectors)
        - Consonance distance (difference in dissonance scores)
        - Dead-tone distance (0 if same, 0.5 if different)

    Higher weight = stronger affinity = closer in the lattice.
    """
    # Tongue vector distance
    s_vec = source.tongue_vector.as_tuple
    t_vec = target.tongue_vector.as_tuple
    tongue_dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(s_vec, t_vec)))

    # Consonance distance
    consonance_dist = abs(source.consonance.dissonance_score
                          - target.consonance.dissonance_score)

    # Dead-tone distance
    dead_tone_dist = 0.0 if source.dead_tone == target.dead_tone else 0.5

    # Combined distance
    d = tongue_dist + consonance_dist + dead_tone_dist

    # Phi-weighted harmonic edge weight
    return 1.0 / (1.0 + PHI * d)


# ---------------------------------------------------------------------------
# Propagation — the self-growing mechanism
# ---------------------------------------------------------------------------

def sprout_from_node(
    parent: PolyhedralRecord,
    raw_input: str,
    generation: int,
) -> List[PolyhedralRecord]:
    """Sprout new records from an ALLOW node.

    Propagation rules:
        1. Complement tongue gets a record (structural balance)
        2. Dead tone rotates to the next baseline (prevents echo chambers)
        3. Excitation decays by 1/phi per generation (cooling)

    Only ALLOW nodes can sprout. QUARANTINE/DENY are terminal.
    """
    if parent.verdict != GovernanceVerdict.ALLOW:
        return []

    children = []
    complement = COMPLEMENT_MAP[parent.dominant_tongue]

    # Dead-tone rotation: cycle through all 3
    tone_list = list(DEAD_TONES)
    current_idx = tone_list.index(parent.dead_tone) if parent.dead_tone in tone_list else 0
    next_tone = tone_list[(current_idx + 1) % len(tone_list)]

    # Excitation decay: each generation cools by 1/phi
    decayed_excitation = max(0.0, parent.excitation / PHI)

    # Child 1: complement tongue, rotated dead tone
    child1 = generate_record(
        raw_input=raw_input,
        dominant_tongue=complement,
        dead_tone=next_tone,
        excitation=decayed_excitation,
        generation=generation,
        parent_hash=parent.node_hash,
    )
    children.append(child1)

    # Child 2: same tongue, rotated dead tone (stability check)
    child2 = generate_record(
        raw_input=raw_input,
        dominant_tongue=parent.dominant_tongue,
        dead_tone=next_tone,
        excitation=decayed_excitation,
        generation=generation,
        parent_hash=parent.node_hash,
    )
    children.append(child2)

    return children


def grow_generation(
    graph: NodalGraph,
    raw_input: str,
) -> int:
    """Grow one generation of the nodal network.

    1. Find all ALLOW nodes at the current generation frontier.
    2. Sprout children from each.
    3. Add children + edges to the graph.
    4. Increment generation count.

    Returns the number of new nodes added.
    """
    frontier = graph.nodes_by_generation(graph.generation_count)
    allow_frontier = [n for n in frontier if n.verdict == GovernanceVerdict.ALLOW]

    next_gen = graph.generation_count + 1
    added = 0

    for parent in allow_frontier:
        children = sprout_from_node(parent, raw_input, next_gen)
        for child in children:
            if graph.add_node(child):
                added += 1
                # Add edge from parent to child
                weight = compute_edge_weight(parent, child)
                graph.add_edge(NodalEdge(
                    source_hash=parent.node_hash,
                    target_hash=child.node_hash,
                    weight=weight,
                    edge_type="tongue_complement" if child.dominant_tongue != parent.dominant_tongue else "dead_tone_rotation",
                ))

    graph.generation_count = next_gen
    return added


# ---------------------------------------------------------------------------
# Seeding — initializing the network
# ---------------------------------------------------------------------------

def seed_graph(
    raw_input: str,
    tongues: Optional[List[str]] = None,
    dead_tones: Optional[List[str]] = None,
    excitation: float = 3.0,
) -> NodalGraph:
    """Create a new nodal graph seeded with initial records.

    By default, seeds with all 6 tongues × first dead tone.
    """
    graph = NodalGraph()
    tongues = tongues or list(ALL_TONGUES)
    dead_tones = dead_tones or [DEAD_TONES[0]]

    for tongue in tongues:
        for tone in dead_tones:
            record = generate_record(
                raw_input=raw_input,
                dominant_tongue=tongue,
                dead_tone=tone,
                excitation=excitation,
                generation=0,
            )
            graph.add_node(record)

    # Connect seeds by tongue affinity
    seed_hashes = list(graph.nodes.keys())
    for i, h1 in enumerate(seed_hashes):
        for h2 in seed_hashes[i + 1:]:
            n1 = graph.nodes[h1]
            n2 = graph.nodes[h2]
            weight = compute_edge_weight(n1, n2)
            if weight > 0.3:  # only connect nodes with meaningful affinity
                graph.add_edge(NodalEdge(h1, h2, weight, "affinity"))
                graph.add_edge(NodalEdge(h2, h1, weight, "affinity"))

    return graph


def grow_network(
    raw_input: str,
    max_generations: int = 3,
    excitation: float = 3.0,
) -> NodalGraph:
    """Seed and grow a full nodal network.

    Args:
        raw_input: The text to process.
        max_generations: How many growth cycles to run.
        excitation: Initial QHO excitation level.

    Returns:
        A populated NodalGraph with self-propagated records.
    """
    graph = seed_graph(raw_input, excitation=excitation)

    for _ in range(max_generations):
        added = grow_generation(graph, raw_input)
        if added == 0:
            break  # Network has stabilized — no ALLOW nodes at frontier

    return graph


# ---------------------------------------------------------------------------
# Training data export
# ---------------------------------------------------------------------------

def export_training_pairs(graph: NodalGraph) -> Dict[str, List[dict]]:
    """Export the graph as training data pairs.

    Returns:
        {
            "sft": [...],       # ALLOW records → supervised fine-tuning
            "dpo_chosen": [...], # ALLOW records → DPO preferred
            "dpo_rejected": [...], # DENY records → DPO rejected
            "boundary": [...],  # QUARANTINE records → hard examples
        }
    """
    def record_to_dict(r: PolyhedralRecord) -> dict:
        return {
            "node_hash": r.node_hash,
            "raw_input": r.raw_input,
            "dominant_tongue": r.dominant_tongue,
            "dead_tone": r.dead_tone,
            "excitation": r.excitation,
            "generation": r.generation,
            "tongue_vector": list(r.tongue_vector.as_tuple),
            "prosody_rate": r.prosody.rate,
            "prosody_energy": r.prosody.energy,
            "prosody_chant_ratio": r.prosody.chant_ratio,
            "prosody_stress": r.prosody.stress_pattern,
            "agent_frequency_hz": r.prosody.agent_frequency_hz,
            "consonance_ratio": r.consonance.frequency_ratio,
            "consonance_interval": r.consonance.nearest_interval,
            "dissonance_score": r.consonance.dissonance_score,
            "beat_frequency": r.consonance.beat_frequency,
            "dark_fill_infra_freq": r.dark_fill.infra_freq,
            "dark_fill_audible_freq": r.dark_fill.audible_freq,
            "dark_fill_ultra_freq": r.dark_fill.ultra_freq,
            "darkness": r.dark_fill.darkness,
            "verdict": r.verdict.value,
            "propagation_label": r.propagation_label.value,
            "complement_tongue": r.complement_tongue,
        }

    positive = [record_to_dict(r) for r in graph.harvest_positive()]
    boundary = [record_to_dict(r) for r in graph.harvest_boundary()]
    negative = [record_to_dict(r) for r in graph.harvest_negative()]

    return {
        "sft": positive,
        "dpo_chosen": positive,
        "dpo_rejected": negative,
        "boundary": boundary,
    }
