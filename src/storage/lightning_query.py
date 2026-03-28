"""Lightning Query — Dielectric Breakdown Search
=================================================

Models query routing on atmospheric lightning physics:

  1. STEPPED LEADER (pre-ionization)
     On ingest, each record deposits a lightweight "charge" into a
     routing structure — a bloom filter + tongue affinity per zone.
     This pre-ionizes channels through the data space.

  2. CHANNEL FORMATION (query arrival)
     When a query arrives, its tongue signature + intent vector
     creates an "electric field" that follows pre-ionized channels.
     The field propagates through zones of matching tongue affinity,
     skipping zones where the bloom filter says "no match."

  3. MULTI-BRANCH PROBE (branching discharge)
     Like lightning branching through a medium, the query sends
     parallel probes into the top-k candidate zones simultaneously.
     Early termination: if any probe hits a strong match (distance
     below threshold), other probes are killed.

  4. RETURN STROKE (confirmation + trim)
     The best-match probe triggers a "return stroke" — confirmation
     signal that reinforces the channel. Failed branches get
     negative feedback (nodal trim) that decays their affinity
     score, making them less likely to be probed next time.

  5. HARMONIC RECOMPUTE (adaptive routing)
     After each query cycle, the routing table absorbs the
     negative resonance from failed branches and re-weights
     the stepped leader charges. Over time, the routing
     structure learns the actual query patterns.

Physics mapping:
  - Dielectric medium = data structure (octree/lattice/QC drive)
  - Breakdown voltage = query match threshold
  - Paschen gap = hyperbolic distance between query and answer
  - Ionization = bloom filter + tongue affinity charge
  - Lichtenberg branching = multi-probe parallel search
  - Return stroke = result confirmation + channel reinforcement

The key insight: by maintaining "environmental conditions" (pre-charged
routing hints), we reduce the effective search space BEFORE the query
arrives. The query then follows the path of least resistance instead
of scanning.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI**k for k in range(6))


# =========================================================================== #
#  Bloom Filter (lightweight pre-ionization)
# =========================================================================== #


class TongueBloom:
    """Tiny bloom filter per zone — pre-screens which tongues are present."""

    def __init__(self, size_bits: int = 64):
        self.size = size_bits
        self.bits = 0

    def _hash(self, tongue: str, salt: int) -> int:
        h = hashlib.blake2s(f"{tongue}:{salt}".encode(), digest_size=4).digest()
        return int.from_bytes(h, "big") % self.size

    def add(self, tongue: str) -> None:
        for salt in range(3):  # 3 hash functions
            self.bits |= 1 << self._hash(tongue, salt)

    def might_contain(self, tongue: str) -> bool:
        for salt in range(3):
            if not (self.bits & (1 << self._hash(tongue, salt))):
                return False
        return True

    @property
    def fill_ratio(self) -> float:
        return bin(self.bits).count("1") / self.size


# =========================================================================== #
#  Stepped Leader — Pre-ionized routing structure
# =========================================================================== #


@dataclass
class LeaderCharge:
    """Charge deposited by records in a zone during ingest."""

    zone_id: str
    tongue_bloom: TongueBloom
    tongue_affinity: Dict[str, float]  # tongue → accumulated weight
    record_count: int = 0
    centroid: Optional[np.ndarray] = None
    # Adaptive: negative feedback from failed queries
    penalty: float = 0.0
    hit_count: int = 0
    miss_count: int = 0

    @property
    def effective_charge(self) -> float:
        """Net charge = affinity - penalty. Higher = more likely to be probed."""
        total_affinity = sum(self.tongue_affinity.values())
        return max(0.0, total_affinity - self.penalty)

    @property
    def conductivity(self) -> float:
        """How easily the query flows through this zone (hit rate)."""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.5  # neutral
        return self.hit_count / total


@dataclass
class ProbeResult:
    """Result from one branch of the lightning probe."""

    zone_id: str
    records_found: List[Tuple[str, float]]  # (record_id, distance)
    probe_time_us: int
    hit: bool
    branch_depth: int


@dataclass
class StrokeResult:
    """Full lightning query result after return stroke."""

    query_tongue: str
    best_matches: List[Tuple[str, float]]  # (record_id, distance)
    branches_probed: int
    branches_pruned: int
    total_time_us: int
    channel_path: List[str]  # zone_ids traversed
    negative_feedback: Dict[str, float]  # zone_id → penalty applied


# =========================================================================== #
#  Lightning Query Engine
# =========================================================================== #


class LightningQuery:
    """Dielectric breakdown search engine.

    Wraps any storage surface with pre-ionized routing for near-instant
    query resolution when environmental conditions match.
    """

    def __init__(
        self,
        match_threshold: float = 0.3,
        max_branches: int = 6,
        penalty_decay: float = 0.9,
        penalty_increment: float = 0.1,
        reinforcement: float = 0.05,
    ):
        self.match_threshold = match_threshold
        self.max_branches = max_branches
        self.penalty_decay = penalty_decay
        self.penalty_increment = penalty_increment
        self.reinforcement = reinforcement

        # Routing structure: zone_id → LeaderCharge
        self.leaders: Dict[str, LeaderCharge] = {}

        # Record store: record_id → (zone_id, tongue_coords, content)
        self.records: Dict[str, Tuple[str, List[float], bytes]] = {}

        # Zone-local index: zone_id → list of (record_id, tongue_vec as ndarray)
        self._zone_index: Dict[str, List[Tuple[str, np.ndarray]]] = {}

        # Query history for harmonic recompute
        self._query_count = 0
        self._total_probes = 0
        self._total_pruned = 0

    # ------------------------------------------------------------------ #
    #  Step 1: STEPPED LEADER (ingest — pre-ionize channels)
    # ------------------------------------------------------------------ #

    def ingest(
        self,
        record_id: str,
        zone_id: str,
        tongue: str,
        tongue_coords: List[float],
        content: bytes = b"",
    ) -> None:
        """Deposit charge into the routing structure during ingest."""
        if zone_id not in self.leaders:
            self.leaders[zone_id] = LeaderCharge(
                zone_id=zone_id,
                tongue_bloom=TongueBloom(),
                tongue_affinity={t: 0.0 for t in TONGUES},
            )

        leader = self.leaders[zone_id]
        leader.tongue_bloom.add(tongue)
        leader.tongue_affinity[tongue] = (
            leader.tongue_affinity.get(tongue, 0.0)
            + TONGUE_WEIGHTS[TONGUES.index(tongue)]
        )
        leader.record_count += 1

        # Update centroid incrementally
        tc = np.array(tongue_coords, dtype=float)
        if leader.centroid is None:
            leader.centroid = tc.copy()
        else:
            # Running average
            n = leader.record_count
            leader.centroid = leader.centroid * ((n - 1) / n) + tc / n

        self.records[record_id] = (zone_id, tongue_coords, content)

        # Zone-local index for fast vectorized search
        if zone_id not in self._zone_index:
            self._zone_index[zone_id] = []
        self._zone_index[zone_id].append((record_id, tc.copy()))

    # ------------------------------------------------------------------ #
    #  Step 2: CHANNEL FORMATION (rank zones by field strength)
    # ------------------------------------------------------------------ #

    def _rank_zones(
        self,
        query_tongue: str,
        query_coords: List[float],
    ) -> List[Tuple[str, float]]:
        """Rank zones by "field strength" — how strongly the query is
        attracted to each zone.

        Field = tongue_affinity[query_tongue] * conductivity / (distance + 1)
                - penalty
        """
        query_vec = np.array(query_coords, dtype=float)
        ranked = []

        for zone_id, leader in self.leaders.items():
            # Bloom filter pre-screen
            if not leader.tongue_bloom.might_contain(query_tongue):
                continue

            # Tongue affinity for the query tongue
            affinity = leader.tongue_affinity.get(query_tongue, 0.0)
            if affinity <= 0:
                continue

            # Distance to zone centroid (Paschen gap)
            if leader.centroid is not None:
                gap = float(np.linalg.norm(query_vec - leader.centroid))
            else:
                gap = 1.0

            # Conductivity (learned from hit/miss history)
            cond = leader.conductivity

            # Field strength: attraction / gap, penalized by failures
            field = (affinity * cond) / (gap + 0.1) - leader.penalty

            if field > 0:
                ranked.append((zone_id, field))

        # Sort by field strength descending
        ranked.sort(key=lambda x: -x[1])
        return ranked

    # ------------------------------------------------------------------ #
    #  Step 3: MULTI-BRANCH PROBE
    # ------------------------------------------------------------------ #

    def _probe_zone(
        self,
        zone_id: str,
        query_coords: List[float],
        top_k: int,
    ) -> ProbeResult:
        """Probe a single zone using vectorized numpy distance."""
        t0 = time.perf_counter_ns()
        query_vec = np.array(query_coords, dtype=float)
        weights = np.array(TONGUE_WEIGHTS, dtype=float)

        zone_entries = self._zone_index.get(zone_id, [])
        if not zone_entries:
            elapsed = (time.perf_counter_ns() - t0) // 1000
            return ProbeResult(
                zone_id=zone_id,
                records_found=[],
                probe_time_us=elapsed,
                hit=False,
                branch_depth=1,
            )

        # Vectorized: stack all zone vectors, compute weighted distances in one shot
        ids = [e[0] for e in zone_entries]
        mat = np.array([e[1] for e in zone_entries], dtype=float)
        diffs = (mat - query_vec[None, :]) * weights[None, :]
        dists = np.linalg.norm(diffs, axis=1)

        # Top-k via argpartition (O(n) instead of O(n log n))
        if len(dists) > top_k:
            idx = np.argpartition(dists, top_k)[:top_k]
            idx = idx[np.argsort(dists[idx])]
        else:
            idx = np.argsort(dists)

        matches = [(ids[i], float(dists[i])) for i in idx]
        elapsed = (time.perf_counter_ns() - t0) // 1000

        hit = len(matches) > 0 and matches[0][1] < self.match_threshold

        return ProbeResult(
            zone_id=zone_id,
            records_found=matches,
            probe_time_us=elapsed,
            hit=hit,
            branch_depth=1,
        )

    # ------------------------------------------------------------------ #
    #  Step 4: RETURN STROKE (confirm + trim)
    # ------------------------------------------------------------------ #

    def _return_stroke(
        self,
        probes: List[ProbeResult],
        top_k: int,
    ) -> StrokeResult:
        """Merge probe results, reinforce hits, penalize misses."""
        all_matches: List[Tuple[str, float]] = []
        channel_path = []
        branches_probed = len(probes)
        branches_pruned = 0
        negative_feedback: Dict[str, float] = {}

        for probe in probes:
            channel_path.append(probe.zone_id)
            all_matches.extend(probe.records_found)

            leader = self.leaders.get(probe.zone_id)
            if leader is None:
                continue

            if probe.hit:
                # Reinforce: reduce penalty, increment hit count
                leader.hit_count += 1
                leader.penalty = max(0.0, leader.penalty - self.reinforcement)
            else:
                # Nodal trim: increment penalty, track miss
                leader.miss_count += 1
                leader.penalty += self.penalty_increment
                negative_feedback[probe.zone_id] = leader.penalty
                branches_pruned += 1

        # Deduplicate and sort
        seen = set()
        unique_matches = []
        for rec_id, dist in sorted(all_matches, key=lambda x: x[1]):
            if rec_id not in seen:
                seen.add(rec_id)
                unique_matches.append((rec_id, round(dist, 6)))

        total_time = sum(p.probe_time_us for p in probes)

        return StrokeResult(
            query_tongue=probes[0].zone_id if probes else "",
            best_matches=unique_matches[:top_k],
            branches_probed=branches_probed,
            branches_pruned=branches_pruned,
            total_time_us=total_time,
            channel_path=channel_path,
            negative_feedback=negative_feedback,
        )

    # ------------------------------------------------------------------ #
    #  Step 5: HARMONIC RECOMPUTE (decay penalties over time)
    # ------------------------------------------------------------------ #

    def _harmonic_recompute(self) -> None:
        """Decay penalties so old failures don't permanently block zones."""
        for leader in self.leaders.values():
            leader.penalty *= self.penalty_decay

    # ------------------------------------------------------------------ #
    #  Public API: Lightning Strike
    # ------------------------------------------------------------------ #

    def strike(
        self,
        query_tongue: str,
        query_coords: List[float],
        top_k: int = 5,
    ) -> StrokeResult:
        """Execute a full lightning query.

        1. Rank zones by field strength (channel formation)
        2. Probe top-N zones in parallel (multi-branch)
        3. Return stroke: merge, reinforce hits, penalize misses
        4. Harmonic recompute: decay penalties
        """
        self._query_count += 1

        # Channel formation
        ranked = self._rank_zones(query_tongue, query_coords)

        if not ranked:
            return StrokeResult(
                query_tongue=query_tongue,
                best_matches=[],
                branches_probed=0,
                branches_pruned=0,
                total_time_us=0,
                channel_path=[],
                negative_feedback={},
            )

        # Multi-branch probe (top N zones)
        n_branches = min(self.max_branches, len(ranked))
        probes = []
        for zone_id, _field in ranked[:n_branches]:
            probe = self._probe_zone(zone_id, query_coords, top_k)
            probes.append(probe)

            # Early termination: if we found a strong match, stop branching
            if probe.hit and probe.records_found:
                if probe.records_found[0][1] < self.match_threshold * 0.5:
                    break

        self._total_probes += len(probes)

        # Return stroke
        result = self._return_stroke(probes, top_k)
        result.query_tongue = query_tongue
        self._total_pruned += result.branches_pruned

        # Harmonic recompute every 10 queries
        if self._query_count % 10 == 0:
            self._harmonic_recompute()

        return result

    def stats(self) -> Dict[str, Any]:
        total_records = len(self.records)
        total_zones = len(self.leaders)
        total_charge = sum(leader.effective_charge for leader in self.leaders.values())
        avg_conductivity = sum(
            leader.conductivity for leader in self.leaders.values()
        ) / max(1, total_zones)
        penalized_zones = sum(
            1 for leader in self.leaders.values() if leader.penalty > 0.01
        )

        return {
            "type": "LightningQuery",
            "total_records": total_records,
            "total_zones": total_zones,
            "total_charge": round(total_charge, 2),
            "avg_conductivity": round(avg_conductivity, 4),
            "penalized_zones": penalized_zones,
            "queries_executed": self._query_count,
            "total_probes": self._total_probes,
            "total_pruned": self._total_pruned,
            "avg_probes_per_query": round(
                self._total_probes / max(1, self._query_count), 2
            ),
            "prune_rate": round(self._total_pruned / max(1, self._total_probes), 4),
        }
