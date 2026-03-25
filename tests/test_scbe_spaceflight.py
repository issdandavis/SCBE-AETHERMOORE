#!/usr/bin/env python3
"""
Comprehensive tests for scbe_spaceflight module.

Each of the six classes (DelayTolerantBundle, HyperbolicTrajectory,
DockingProtocol, ReentryShield, StarTracker, ConstellationFleet) has
at least four dedicated tests covering happy-path, edge cases, error
handling, and SCBE-specific invariants.

Run with:  python -m pytest tests/test_scbe_spaceflight.py -v
"""

from __future__ import annotations

import hashlib
import hmac
import math
import sys
import os

import pytest

# Ensure the source directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scbe_spaceflight import (
    CustodyEntry,
    DelayTolerantBundle,
    HyperbolicTrajectory,
    DockingProtocol,
    DockingState,
    ReentryShield,
    ReentryResult,
    StarTracker,
    ConstellationFleet,
    PHI,
    PI,
    R_FIFTH,
)

# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


def _sha256_hex(data: str) -> str:
    """Return a valid 64-char hex SHA-256 digest."""
    return hashlib.sha256(data.encode()).hexdigest()


ORIGIN_6D = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
DEST_6D = (1.0, 2.0, 3.0, 0.5, 0.8, 1.0)


# =========================================================================
# 1. DelayTolerantBundle tests
# =========================================================================


class TestDelayTolerantBundle:
    """Tests for store-and-forward message bundles."""

    def test_add_and_verify_custody_chain(self):
        """Adding valid relay entries produces a verifiable chain."""
        bundle = DelayTolerantBundle(
            payload=b"hello deep space",
            sender_id="earth-station",
            receiver_id="mars-relay",
        )
        for i in range(5):
            sig = _sha256_hex(f"relay-{i}-attestation")
            bundle.add_custody(f"relay-{i}", sig)

        assert len(bundle.custody_chain) == 5
        assert bundle.verify_custody_chain() is True

    def test_empty_chain_fails_verification(self):
        """An empty custody chain does not verify."""
        bundle = DelayTolerantBundle(payload=b"empty", sender_id="A", receiver_id="B")
        assert bundle.verify_custody_chain() is False

    def test_duplicate_relay_fails_verification(self):
        """A chain with duplicate relay IDs (loop) is rejected."""
        bundle = DelayTolerantBundle(payload=b"dup", sender_id="A", receiver_id="B")
        sig = _sha256_hex("sig1")
        bundle.add_custody("relay-1", sig)
        # Force duplicate by directly appending
        bundle.custody_chain.append(CustodyEntry(relay_id="relay-1", signature_hash=sig, order_index=1))
        assert bundle.verify_custody_chain() is False

    def test_invalid_signature_rejected_on_add(self):
        """add_custody rejects a malformed signature hash."""
        bundle = DelayTolerantBundle(payload=b"bad", sender_id="A", receiver_id="B")
        with pytest.raises(ValueError, match="64-character"):
            bundle.add_custody("relay-x", "not-a-valid-hash")

    def test_compute_bundle_hash_deterministic(self):
        """The bundle hash is deterministic given the same content."""
        bundle = DelayTolerantBundle(
            payload=b"determinism",
            sender_id="A",
            receiver_id="B",
            created_epoch=0.0,
        )
        bundle.add_custody("relay-0", _sha256_hex("r0"))
        h1 = bundle.compute_bundle_hash()
        h2 = bundle.compute_bundle_hash()
        assert h1 == h2
        assert len(h1) == 64

    def test_is_expired(self):
        """Bundles respect their TTL."""
        bundle = DelayTolerantBundle(
            payload=b"ttl",
            sender_id="A",
            receiver_id="B",
            ttl=10.0,
            created_epoch=100.0,
        )
        assert bundle.is_expired(now=105.0) is False
        assert bundle.is_expired(now=111.0) is True


# =========================================================================
# 2. HyperbolicTrajectory tests
# =========================================================================


class TestHyperbolicTrajectory:
    """Tests for hyperbolic trajectories through 6D protocol space."""

    def test_compute_path_length(self):
        """compute_path returns the requested number of waypoints."""
        traj = HyperbolicTrajectory(
            origin=ORIGIN_6D,
            destination=DEST_6D,
            eccentricity=1.5,
        )
        path = traj.compute_path(steps=50)
        assert len(path) == 50
        # Each waypoint is 6D
        for wp in path:
            assert len(wp) == 6

    def test_eccentricity_must_exceed_one(self):
        """Constructor rejects eccentricity <= 1."""
        with pytest.raises(ValueError, match="Eccentricity"):
            HyperbolicTrajectory(ORIGIN_6D, DEST_6D, eccentricity=0.9)

    def test_gravity_assist_deflects_trajectory(self):
        """A gravity assist changes the destination."""
        traj = HyperbolicTrajectory(ORIGIN_6D, DEST_6D, eccentricity=2.0)
        body = (5.0, 5.0, 5.0, 0.0, 0.0, 0.0)
        new_traj = traj.gravity_assist(body, body_mass=100.0)
        # Destination should have shifted toward the body
        assert new_traj.destination != traj.destination
        # Eccentricity should have decreased (but remain > 1)
        assert new_traj.eccentricity >= 1.001

    def test_fuel_cost_is_positive(self):
        """Fuel cost is always a positive finite number."""
        traj = HyperbolicTrajectory(ORIGIN_6D, DEST_6D, eccentricity=1.2)
        cost = traj.fuel_cost()
        assert cost > 0
        assert math.isfinite(cost)

    def test_fuel_cost_uses_golden_ratio(self):
        """Fuel cost formula H(d,R) = R * pi^(phi*d) uses PHI."""
        traj = HyperbolicTrajectory(ORIGIN_6D, DEST_6D, eccentricity=1.5)
        d = traj.path_length(steps=50)
        expected = R_FIFTH * (PI ** (PHI * d))
        actual = traj.fuel_cost()
        # They should be close (both use 50 steps internally)
        assert abs(actual - expected) / expected < 0.01

    def test_path_starts_near_origin_and_ends_near_dest(self):
        """First waypoint should be near origin, last near destination."""
        traj = HyperbolicTrajectory(ORIGIN_6D, DEST_6D, eccentricity=1.5)
        path = traj.compute_path(steps=100)
        first = path[0]
        last = path[-1]
        dist_origin = math.sqrt(sum((a - b) ** 2 for a, b in zip(first, ORIGIN_6D)))
        dist_dest = math.sqrt(sum((a - b) ** 2 for a, b in zip(last, DEST_6D)))
        # First waypoint is at t=0, so the linear part is 0 (at origin),
        # with only a small hyperbolic modulation
        assert dist_origin < 2.0, f"First waypoint too far from origin: {dist_origin}"
        # Last waypoint is at t=1 (destination + small modulation)
        assert dist_dest < 2.0, f"Last waypoint too far from destination: {dist_dest}"


# =========================================================================
# 3. DockingProtocol tests
# =========================================================================


class TestDockingProtocol:
    """Tests for the docking (authentication) state machine."""

    def _full_dock(self) -> DockingProtocol:
        """Helper: run the complete happy-path handshake."""
        dp = DockingProtocol()
        dp.initiate("local-node", "remote-node")
        dp.negotiate_cipher_suite(
            ["AES-256-GCM", "ChaCha20"],
            ["ChaCha20", "AES-256-GCM"],
        )
        shared = dp.exchange_keys(local_pubkey=5, remote_pubkey=7, prime=23)
        # Compute correct HMAC response
        challenge = b"dock-challenge-42"
        response = hmac.new(shared, challenge, hashlib.sha256).digest()
        dp.verify_and_dock(challenge, response)
        return dp

    def test_happy_path_reaches_docked(self):
        """A correct handshake ends in the DOCKED state."""
        dp = self._full_dock()
        assert dp.state == DockingState.DOCKED
        assert dp.history == [
            "DISCOVERY",
            "NEGOTIATION",
            "KEY_EXCHANGE",
            "VERIFICATION",
            "DOCKED",
        ]

    def test_no_common_suite_fails(self):
        """Negotiation with disjoint suites transitions to FAILED."""
        dp = DockingProtocol()
        dp.initiate("A", "B")
        result = dp.negotiate_cipher_suite(["AES-256"], ["ChaCha20"])
        assert result is None
        assert dp.state == DockingState.FAILED

    def test_bad_hmac_response_fails(self):
        """Wrong HMAC response transitions to FAILED."""
        dp = DockingProtocol()
        dp.initiate("A", "B")
        dp.negotiate_cipher_suite(["AES"], ["AES"])
        dp.exchange_keys(3, 7, 23)
        ok = dp.verify_and_dock(b"challenge", b"wrong-response-bytes-here!!!!!!!!")
        assert ok is False
        assert dp.state == DockingState.FAILED

    def test_invalid_transition_raises(self):
        """Attempting an out-of-order transition raises RuntimeError."""
        dp = DockingProtocol()
        with pytest.raises(RuntimeError, match="Invalid transition"):
            # Can't jump straight to KEY_EXCHANGE from DISCOVERY
            dp.exchange_keys(1, 2, 23)

    def test_empty_ids_fail_initiation(self):
        """Empty local or remote ID causes FAILED."""
        dp = DockingProtocol()
        state = dp.initiate("", "remote")
        assert state == DockingState.FAILED

    def test_cipher_suite_local_preference(self):
        """The first locally-preferred common suite is selected."""
        dp = DockingProtocol()
        dp.initiate("A", "B")
        suite = dp.negotiate_cipher_suite(
            ["ChaCha20", "AES-256-GCM"],
            ["AES-256-GCM", "ChaCha20"],
        )
        assert suite == "ChaCha20"  # local preference wins


# =========================================================================
# 4. ReentryShield tests
# =========================================================================


class TestReentryShield:
    """Tests for ablative token boundary crossing."""

    def test_successful_crossing(self):
        """Crossing with enough tokens succeeds and decrements tokens."""
        shield = ReentryShield(token_count=10, target_trust_zone="CORE")
        result, zone = shield.cross_boundary("EDGE", heat_flux=3.0)
        assert result == ReentryResult.SUCCESS
        assert zone == "CORE"
        assert shield.remaining_tokens() == 7

    def test_catastrophic_failure_on_exhaustion(self):
        """Running out of tokens mid-crossing is catastrophic."""
        shield = ReentryShield(token_count=2, target_trust_zone="CORE")
        result, zone = shield.cross_boundary("EDGE", heat_flux=5.0)
        assert result == ReentryResult.CATASTROPHIC_FAILURE
        assert zone == "DESTROYED"
        assert shield.remaining_tokens() == 0

    def test_zero_flux_free_pass(self):
        """Zero heat flux costs nothing and always succeeds."""
        shield = ReentryShield(token_count=1, target_trust_zone="SAFE")
        result, zone = shield.cross_boundary("UNSAFE", heat_flux=0.0)
        assert result == ReentryResult.SUCCESS
        assert zone == "SAFE"
        assert shield.remaining_tokens() == 1  # no tokens consumed

    def test_already_exhausted_tokens(self):
        """Attempting any crossing with 0 tokens is catastrophic."""
        shield = ReentryShield(token_count=0, target_trust_zone="CORE")
        result, zone = shield.cross_boundary("EDGE", heat_flux=1.0)
        assert result == ReentryResult.CATASTROPHIC_FAILURE
        assert zone == "DESTROYED"

    def test_multiple_crossings_deplete_tokens(self):
        """Repeated crossings deplete the token pool linearly."""
        shield = ReentryShield(token_count=10, target_trust_zone="CORE")
        for _ in range(5):
            result, _ = shield.cross_boundary("EDGE", heat_flux=2.0)
            assert result == ReentryResult.SUCCESS
        assert shield.remaining_tokens() == 0
        # Next crossing should fail
        result, zone = shield.cross_boundary("EDGE", heat_flux=1.0)
        assert result == ReentryResult.CATASTROPHIC_FAILURE

    def test_crossing_log_recorded(self):
        """Every crossing attempt is logged."""
        shield = ReentryShield(token_count=5, target_trust_zone="CORE")
        shield.cross_boundary("EDGE", heat_flux=1.0)
        shield.cross_boundary("EDGE", heat_flux=2.0)
        log = shield.crossing_log
        assert len(log) == 2
        assert log[0]["cost"] == 1
        assert log[1]["cost"] == 2


# =========================================================================
# 5. StarTracker tests
# =========================================================================


class TestStarTracker:
    """Tests for star-catalog certificate verification."""

    CATALOG = {
        "Polaris": (0.0, 0.0, 100.0, 0.0, 0.0, 0.0),
        "Sirius": (10.0, 5.0, 50.0, 0.1, 0.2, 0.3),
        "Vega": (-5.0, 8.0, 70.0, 0.0, 0.5, 0.1),
        "Deneb": (20.0, -3.0, 90.0, 0.0, 0.0, 1.0),
    }

    def test_identify_nearest_star(self):
        """Observations are matched to the closest catalog star."""
        tracker = StarTracker(self.CATALOG)
        obs = [(0.1, 0.1, 100.1, 0.0, 0.0, 0.0)]  # near Polaris
        matches = tracker.identify_stars(obs)
        assert len(matches) == 1
        assert matches[0].star_id == "Polaris"
        assert matches[0].distance < 1.0

    def test_identify_multiple_observations(self):
        """Multiple observations match their respective nearest stars."""
        tracker = StarTracker(self.CATALOG)
        obs = [
            (0.1, 0.1, 100.1, 0.0, 0.0, 0.0),  # Polaris
            (10.1, 5.1, 50.1, 0.1, 0.2, 0.3),  # Sirius
            (-5.1, 8.1, 70.1, 0.0, 0.5, 0.1),  # Vega
        ]
        matches = tracker.identify_stars(obs)
        ids = [m.star_id for m in matches]
        assert ids == ["Polaris", "Sirius", "Vega"]

    def test_compute_attitude_identity_when_perfect(self):
        """When observations match catalog exactly, attitude is identity."""
        tracker = StarTracker(self.CATALOG)
        obs = [self.CATALOG["Polaris"], self.CATALOG["Sirius"]]
        matches = tracker.identify_stars(obs)
        q = tracker.compute_attitude(matches)
        # Identity quaternion: (0, 0, 0, 1)
        assert abs(q[3] - 1.0) < 0.01
        assert abs(q[0]) < 0.01
        assert abs(q[1]) < 0.01
        assert abs(q[2]) < 0.01

    def test_compute_attitude_is_unit_quaternion(self):
        """The attitude quaternion always has unit magnitude."""
        tracker = StarTracker(self.CATALOG)
        obs = [
            (1.0, 1.0, 101.0, 0.0, 0.0, 0.0),
            (11.0, 6.0, 51.0, 0.1, 0.2, 0.3),
        ]
        matches = tracker.identify_stars(obs)
        q = tracker.compute_attitude(matches)
        norm = math.sqrt(sum(c * c for c in q))
        assert abs(norm - 1.0) < 1e-9

    def test_verify_position_within_tolerance(self):
        """A claimed position close to observations verifies."""
        tracker = StarTracker(self.CATALOG)
        obs = [
            (0.1, 0.1, 100.1, 0.0, 0.0, 0.0),
            (0.2, -0.1, 99.9, 0.0, 0.0, 0.0),
        ]
        # Centroid of observations ~ (0.15, 0.0, 100.0, ...)
        claimed = (0.15, 0.0, 100.0, 0.0, 0.0, 0.0)
        assert tracker.verify_position(claimed, tolerance=1.0, observed_positions=obs)

    def test_verify_position_out_of_tolerance(self):
        """A claimed position far from observations fails."""
        tracker = StarTracker(self.CATALOG)
        obs = [(0.0, 0.0, 100.0, 0.0, 0.0, 0.0)]
        claimed = (50.0, 50.0, 50.0, 0.0, 0.0, 0.0)
        assert not tracker.verify_position(claimed, tolerance=1.0, observed_positions=obs)

    def test_verify_position_catalog_fallback(self):
        """Without observations, position is checked against the catalog."""
        tracker = StarTracker(self.CATALOG)
        # Exactly at Polaris
        assert tracker.verify_position((0.0, 0.0, 100.0, 0.0, 0.0, 0.0), tolerance=0.1)
        # Nowhere near any star
        assert not tracker.verify_position((999.0, 999.0, 999.0, 0.0, 0.0, 0.0), tolerance=1.0)

    def test_empty_catalog_raises(self):
        """An empty catalog is rejected."""
        with pytest.raises(ValueError, match="at least one"):
            StarTracker({})


# =========================================================================
# 6. ConstellationFleet tests
# =========================================================================


class TestConstellationFleet:
    """Tests for BFT consensus across a multi-vessel formation."""

    def test_propose_and_reach_consensus(self):
        """A supermajority vote leads to consensus."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("PHALANX")
        # 2/3 of 12 = 8 approvals needed
        for v in fleet.vessels[:8]:
            fleet.vote(v, approve=True)
        assert fleet.check_consensus() == "PHALANX"

    def test_no_consensus_without_supermajority(self):
        """Fewer than 2/3 approvals yields no consensus."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("LANCE")
        for v in fleet.vessels[:7]:
            fleet.vote(v, approve=True)
        assert fleet.check_consensus() is None

    def test_shift_formation_atomically(self):
        """shift_formation changes formation only if consensus is met."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("WEB")
        for v in fleet.vessels[:9]:
            fleet.vote(v, approve=True)
        assert fleet.shift_formation("WEB") is True
        assert fleet.current_formation == "WEB"
        # Proposal should be cleared after shift
        assert fleet.check_consensus() is None

    def test_shift_formation_fails_without_consensus(self):
        """shift_formation returns False if consensus is not met."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("STORM")
        fleet.vote(fleet.vessels[0], approve=True)
        assert fleet.shift_formation("STORM") is False
        assert fleet.current_formation is None

    def test_invalid_formation_rejected(self):
        """An unknown formation name is rejected."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        with pytest.raises(ValueError, match="Unknown formation"):
            fleet.propose_formation("DIAMOND")

    def test_vote_without_proposal_raises(self):
        """Voting without an active proposal raises ValueError."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        with pytest.raises(ValueError, match="No active proposal"):
            fleet.vote(fleet.vessels[0], approve=True)

    def test_unknown_vessel_rejected(self):
        """A vote from an unknown vessel is rejected."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("CONSTELLATION")
        with pytest.raises(ValueError, match="Unknown vessel"):
            fleet.vote("V-99", approve=True)

    def test_squads_partition_fleet(self):
        """The fleet is split into two equally-sized squads."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        assert len(fleet.squad_a) == 6
        assert len(fleet.squad_b) == 6
        assert set(fleet.squad_a) & set(fleet.squad_b) == set()
        assert set(fleet.squad_a) | set(fleet.squad_b) == set(fleet.vessels)

    def test_rejections_prevent_consensus(self):
        """Enough rejections block consensus even with some approvals."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("PHALANX")
        # 5 approve, 7 reject
        for v in fleet.vessels[:5]:
            fleet.vote(v, approve=True)
        for v in fleet.vessels[5:]:
            fleet.vote(v, approve=False)
        assert fleet.check_consensus() is None
        tally = fleet.vote_count()
        assert tally["approve"] == 5
        assert tally["reject"] == 7

    def test_new_proposal_clears_old_votes(self):
        """Starting a new proposal resets the ballot."""
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("LANCE")
        for v in fleet.vessels[:8]:
            fleet.vote(v, approve=True)
        assert fleet.check_consensus() == "LANCE"
        # New proposal clears
        fleet.propose_formation("STORM")
        assert fleet.check_consensus() is None
        assert fleet.vote_count() == {"approve": 0, "reject": 0}


# =========================================================================
# Cross-cutting SCBE invariant tests
# =========================================================================


class TestSCBEInvariants:
    """Tests that verify architectural invariants from SCBE-AETHERMOORE."""

    def test_golden_ratio_constant(self):
        """PHI matches the canonical golden ratio value."""
        assert abs(PHI - 1.618033988749895) < 1e-12

    def test_harmonic_fuel_cost_monotonic(self):
        """Fuel cost increases with trajectory distance (harmonic wall)."""
        short_traj = HyperbolicTrajectory(
            origin=ORIGIN_6D,
            destination=(0.1, 0.1, 0.1, 0.0, 0.0, 0.0),
            eccentricity=1.5,
        )
        medium_traj = HyperbolicTrajectory(
            origin=ORIGIN_6D,
            destination=(1.0, 1.0, 1.0, 0.5, 0.5, 0.5),
            eccentricity=1.5,
        )
        assert short_traj.fuel_cost() < medium_traj.fuel_cost()

    def test_custody_chain_sha256_integrity(self):
        """Custody chain uses SHA-256 (matches SCBE HKDF-SHA256 choice)."""
        bundle = DelayTolerantBundle(
            payload=b"integrity-test",
            sender_id="src",
            receiver_id="dst",
        )
        sig = hashlib.sha256(b"test-relay").hexdigest()
        bundle.add_custody("relay-0", sig)
        # Verify the stored hash is a proper SHA-256 digest
        entry = bundle.custody_chain[0]
        assert len(entry.signature_hash) == 64

    def test_bft_threshold_matches_3f_plus_1(self):
        """BFT consensus threshold is ceil(2n/3), consistent with 3f+1.

        For n=12, f_max=4, threshold=ceil(8)=8.
        """
        fleet = ConstellationFleet(fleet_size=12, squad_size=6)
        fleet.propose_formation("PHALANX")
        # 7 approvals -- not enough
        for v in fleet.vessels[:7]:
            fleet.vote(v, approve=True)
        assert fleet.check_consensus() is None
        # 8 approvals -- consensus
        fleet.vote(fleet.vessels[7], approve=True)
        assert fleet.check_consensus() == "PHALANX"


# -------------------------------------------------------------------------
# CLI entry point
# -------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
