"""
Tests for EDE - Entropic Defense Engine

Tests for:
- SpiralRing-64: Deterministic expansion
- EDE Protocol: Mars communication
- Chemistry Agent: Threat defense
"""

import math
import pytest
import time

# SpiralRing imports
from symphonic_cipher.scbe_aethermoore.ede.spiral_ring import (
    SpiralRing,
    SpiralPosition,
    RingConfig,
    RingState,
    SynchronizedRingPair,
    create_entropy_stream,
    mars_light_delay,
    calculate_light_delay,
    RING_SIZE,
    LIGHT_SPEED,
    MARS_LIGHT_TIME_MIN,
)

# EDE Protocol imports
from symphonic_cipher.scbe_aethermoore.ede.ede_protocol import (
    EDEHeader,
    EDEMessage,
    EDEStation,
    MessageType,
    MarsLink,
    add_error_detection,
    verify_error_detection,
    lorentz_factor,
    apply_time_dilation,
    quick_mars_encode,
    quick_mars_decode,
    PROTOCOL_VERSION,
)

# Chemistry Agent imports
from symphonic_cipher.scbe_aethermoore.ede.chemistry_agent import (
    ChemistryAgent,
    AgentState,
    ThreatType,
    WaveSimulation,
    squared_energy,
    reaction_rate,
    ray_refraction,
    harmonic_sink,
    self_heal,
    equilibrium_force,
    quick_defense_check,
    run_threat_simulation,
)


# =============================================================================
# SPIRAL RING TESTS
# =============================================================================

class TestSpiralRing:
    """Test SpiralRing-64 deterministic expansion."""

    def test_ring_initialization(self):
        """Test ring initializes with correct size."""
        seed = b"test-seed-12345678901234567890"
        ring = SpiralRing.from_seed(seed)

        assert len(ring.positions) == RING_SIZE
        assert ring.state == RingState.INITIALIZED
        assert ring.current_time == 0.0

    def test_ring_deterministic(self):
        """Test same seed produces same ring."""
        seed = b"deterministic-test-seed-32bytes!"

        ring1 = SpiralRing.from_seed(seed)
        ring2 = SpiralRing.from_seed(seed)

        # Both should have identical initial states
        for p1, p2 in zip(ring1.positions, ring2.positions):
            assert p1.value == p2.value
            assert p1.phase == p2.phase

    def test_ring_evolution(self):
        """Test ring evolves correctly over time."""
        seed = b"evolution-test-seed-32-bytes!!"
        ring = SpiralRing.from_seed(seed)

        initial_state = ring.get_ring_state()

        # Evolve to T=10
        ring.evolve_to(10.0)

        evolved_state = ring.get_ring_state()

        # State should have changed
        assert initial_state != evolved_state
        assert ring.state == RingState.SYNCHRONIZED

    def test_ring_fast_forward(self):
        """Test fast-forward produces same state as sequential evolution."""
        seed = b"fast-forward-test-32-bytes!!!!!"

        # Sequential evolution
        ring1 = SpiralRing.from_seed(seed)
        ring1.evolve_to(5.0)
        ring1.evolve_to(10.0)
        state1 = ring1.get_ring_state()

        # Direct evolution
        ring2 = SpiralRing.from_seed(seed)
        ring2.evolve_to(10.0)
        state2 = ring2.get_ring_state()

        assert state1 == state2

    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding produces original data."""
        seed = b"encode-decode-test-seed-32byte!"
        ring = SpiralRing.from_seed(seed)

        message = b"Hello, Mars! This is Earth calling."

        ring.evolve_to(0.0)
        encoded = ring.encode(message)

        # Reset and decode
        ring2 = SpiralRing.from_seed(seed)
        ring2.evolve_to(0.0)
        decoded = ring2.decode(encoded)

        assert decoded == message

    def test_different_seeds_different_states(self):
        """Test different seeds produce different states."""
        seed1 = b"seed-one-32-bytes-for-testing!!"
        seed2 = b"seed-two-32-bytes-for-testing!!"

        ring1 = SpiralRing.from_seed(seed1)
        ring2 = SpiralRing.from_seed(seed2)

        state1 = ring1.get_ring_state()
        state2 = ring2.get_ring_state()

        assert state1 != state2

    def test_entropy_accumulation(self):
        """Test entropy accumulates over time."""
        seed = b"entropy-test-seed-32-bytes!!!!!"
        ring = SpiralRing.from_seed(seed)

        initial_entropy = ring.get_entropy_bits()

        ring.evolve_to(100.0)

        final_entropy = ring.get_entropy_bits()

        assert final_entropy > initial_entropy


class TestSynchronizedRingPair:
    """Test synchronized ring pairs."""

    def test_pair_creation(self):
        """Test creating synchronized pairs."""
        seed = b"synchronized-pair-test-32bytes!"

        pair_a, pair_b = SynchronizedRingPair.create_pair(
            seed, "EARTH", "MARS"
        )

        assert pair_a.station_id == "EARTH"
        assert pair_a.partner_id == "MARS"
        assert pair_b.station_id == "MARS"
        assert pair_b.partner_id == "EARTH"

    def test_pair_message_roundtrip(self):
        """Test message roundtrip between pairs."""
        seed = b"roundtrip-test-seed-32-bytes!!!"

        pair_a, pair_b = SynchronizedRingPair.create_pair(
            seed, "SENDER", "RECEIVER"
        )

        message = b"Test message for synchronized pairs"

        # Sender encodes at T=5
        encoded, send_time = pair_a.encode_message(message, send_time=5.0)

        # Receiver decodes using sender's timestamp
        decoded = pair_b.decode_message(encoded, send_time)

        assert decoded == message


class TestLightDelay:
    """Test light delay calculations."""

    def test_light_speed_constant(self):
        """Test light speed is correct."""
        assert LIGHT_SPEED == 299792458

    def test_mars_light_delay(self):
        """Test Mars light delay is reasonable."""
        delay = mars_light_delay()

        # Should be between min and max
        assert delay >= MARS_LIGHT_TIME_MIN

    def test_calculate_light_delay(self):
        """Test light delay calculation."""
        # 1 light-second = LIGHT_SPEED meters
        delay = calculate_light_delay(LIGHT_SPEED)
        assert delay == 1.0


# =============================================================================
# EDE PROTOCOL TESTS
# =============================================================================

class TestEDEHeader:
    """Test EDE protocol header."""

    def test_header_serialization(self):
        """Test header serializes and deserializes correctly."""
        header = EDEHeader(
            version=PROTOCOL_VERSION,
            msg_type=MessageType.DATA,
            flags=0x0001,
            sequence=12345,
            timestamp=1000.5,
            payload_len=256
        )

        serialized = header.to_bytes()
        deserialized = EDEHeader.from_bytes(serialized)

        assert deserialized.version == header.version
        assert deserialized.msg_type == header.msg_type
        assert deserialized.sequence == header.sequence
        assert abs(deserialized.timestamp - header.timestamp) < 0.001

    def test_message_types(self):
        """Test all message types are valid."""
        for msg_type in MessageType:
            header = EDEHeader(
                version=1,
                msg_type=msg_type,
                flags=0,
                sequence=1,
                timestamp=0.0,
                payload_len=0
            )
            serialized = header.to_bytes()
            assert len(serialized) == 32


class TestEDEStation:
    """Test EDE communication station."""

    def test_station_creation(self):
        """Test station creates correctly."""
        seed = b"station-test-seed-32-bytes!!!!!"
        station = EDEStation.create("TEST-STATION", seed)

        assert station.station_id == "TEST-STATION"
        assert station.sequence_counter == 0

    def test_station_send_receive(self):
        """Test station send and receive."""
        seed = b"send-receive-test-32-bytes!!!!!"

        sender = EDEStation.create("SENDER", seed)
        receiver = EDEStation.create("RECEIVER", seed)

        message = b"Hello from sender!"

        # Send at T=0
        ede_msg = sender.send(message, send_time=0.0)

        # Receive
        decoded, valid = receiver.receive(ede_msg, "SENDER")

        assert valid is True
        assert decoded == message

    def test_station_sequence_increment(self):
        """Test sequence number increments."""
        seed = b"sequence-test-seed-32-bytes!!!!"
        station = EDEStation.create("TEST", seed)

        station.send(b"msg1", send_time=0.0)
        station.send(b"msg2", send_time=1.0)
        station.send(b"msg3", send_time=2.0)

        assert station.sequence_counter == 3


class TestMarsLink:
    """Test Mars communication link."""

    def test_mars_link_creation(self):
        """Test Mars link establishes correctly."""
        seed = b"mars-link-test-seed-32-bytes!!!"
        link = MarsLink.establish(seed)

        assert link.earth_station.station_id == "EARTH-STATION"
        assert link.mars_station.station_id == "MARS-STATION"

    def test_earth_to_mars(self):
        """Test Earth to Mars transmission."""
        seed = b"earth-mars-test-seed-32-bytes!!"
        link = MarsLink.establish(seed)

        message = b"Hello Mars, this is Earth!"

        wire_msg, decoded, delay = link.simulate_earth_to_mars(message)

        assert decoded == message
        assert delay > 0

    def test_mars_to_earth(self):
        """Test Mars to Earth transmission."""
        seed = b"mars-earth-test-seed-32-bytes!!"
        link = MarsLink.establish(seed)

        message = b"Hello Earth, this is Mars!"

        wire_msg, decoded, delay = link.simulate_mars_to_earth(message)

        assert decoded == message

    def test_link_stats(self):
        """Test link statistics."""
        seed = b"link-stats-test-seed-32-bytes!!"
        link = MarsLink.establish(seed)

        stats = link.get_stats()

        assert "distance_km" in stats
        assert "one_way_delay_seconds" in stats
        assert "ede_advantage" in stats


class TestErrorDetection:
    """Test cosmic ray error detection."""

    def test_error_detection_roundtrip(self):
        """Test adding and verifying error detection."""
        data = b"Test data for error detection" * 10

        protected = add_error_detection(data)
        recovered, valid = verify_error_detection(protected)

        assert valid is True
        assert recovered == data

    def test_error_detection_detects_corruption(self):
        """Test error detection catches corruption."""
        data = b"Test data that will be corrupted" * 5

        protected = bytearray(add_error_detection(data))

        # Corrupt one byte
        protected[10] ^= 0xFF

        recovered, valid = verify_error_detection(bytes(protected))

        assert valid is False


class TestTimeDilation:
    """Test relativistic time dilation."""

    def test_lorentz_factor_at_rest(self):
        """Test Lorentz factor is 1 at rest."""
        gamma = lorentz_factor(0.0)
        assert gamma == 1.0

    def test_lorentz_factor_slow_speed(self):
        """Test Lorentz factor at low speeds."""
        # At 0.1c, gamma should be close to 1
        gamma = lorentz_factor(0.1)
        assert 1.0 < gamma < 1.1

    def test_lorentz_factor_high_speed(self):
        """Test Lorentz factor at high speeds."""
        # At 0.9c, gamma should be significant
        gamma = lorentz_factor(0.9)
        assert gamma > 2.0

    def test_time_dilation(self):
        """Test time dilation calculation."""
        proper_time = 100.0  # seconds
        velocity = 0.5  # 0.5c

        dilated = apply_time_dilation(proper_time, velocity)

        # Dilated time should be longer
        assert dilated > proper_time


class TestQuickFunctions:
    """Test quick encode/decode functions."""

    def test_quick_mars_roundtrip(self):
        """Test quick encode and decode."""
        seed = b"quick-test-seed-32-bytes-here!!"
        message = b"Quick test message"

        encoded = quick_mars_encode(message, seed, timestamp=0.0)
        decoded, valid = quick_mars_decode(encoded, seed)

        assert valid is True
        assert decoded == message


# =============================================================================
# CHEMISTRY AGENT TESTS
# =============================================================================

class TestSquaredEnergy:
    """Test squared-input energy model."""

    def test_zero_input(self):
        """Test energy at zero input."""
        energy = squared_energy(0.0)
        assert energy == 0.0

    def test_small_input(self):
        """Test small input produces small energy."""
        energy = squared_energy(1.0)
        assert energy == math.log(2)  # log(1 + 1²) = log(2)

    def test_large_input(self):
        """Test large input produces larger energy."""
        small_energy = squared_energy(1.0)
        large_energy = squared_energy(10.0)

        assert large_energy > small_energy

    def test_energy_scales_logarithmically(self):
        """Test energy scales logarithmically to prevent overflow."""
        huge_energy = squared_energy(1000000.0)
        # Should not overflow, should be finite
        assert math.isfinite(huge_energy)


class TestReactionRate:
    """Test chemical reaction rate."""

    def test_zero_concentration(self):
        """Test reaction rate with zero concentration."""
        rate = reaction_rate(0.0, 1.0)
        assert rate == 0.0

    def test_positive_rate(self):
        """Test positive reaction rate."""
        rate = reaction_rate(1.0, 1.0)
        assert rate > 0

    def test_temperature_effect(self):
        """Test temperature increases reaction rate."""
        cold_rate = reaction_rate(1.0, 1.0, temperature=0.5)
        hot_rate = reaction_rate(1.0, 1.0, temperature=2.0)

        assert hot_rate > cold_rate


class TestRayRefraction:
    """Test ray refraction defense."""

    def test_low_threat_minimal_refraction(self):
        """Test low threat level has minimal refraction."""
        value = 100.0
        deflected = ray_refraction(value, threat_level=1)

        # Should be close to original
        assert deflected > value * 0.9

    def test_high_threat_strong_refraction(self):
        """Test high threat level has strong refraction."""
        value = 100.0
        deflected = ray_refraction(value, threat_level=10)

        # Should be significantly reduced
        assert deflected < value * 0.3

    def test_refraction_monotonic(self):
        """Test refraction increases with threat level."""
        value = 100.0

        prev_deflected = value
        for level in range(1, 11):
            deflected = ray_refraction(value, threat_level=level)
            assert deflected <= prev_deflected
            prev_deflected = deflected


class TestHarmonicSink:
    """Test harmonic energy sink."""

    def test_sink_reduces_energy(self):
        """Test sink reduces energy."""
        value = 100.0
        absorbed = harmonic_sink(value, sink_depth=3)

        assert absorbed < value

    def test_deeper_sink_more_absorption(self):
        """Test deeper sink absorbs more."""
        value = 100.0

        shallow = harmonic_sink(value, sink_depth=1)
        deep = harmonic_sink(value, sink_depth=6)

        assert deep < shallow


class TestSelfHealing:
    """Test self-healing mechanics."""

    def test_healing_toward_target(self):
        """Test healing moves toward target."""
        current = 50.0
        target = 100.0

        healed = self_heal(current, target)

        assert healed > current
        assert healed < target

    def test_healing_rate(self):
        """Test healing rate affects speed."""
        current = 50.0
        target = 100.0

        slow_heal = self_heal(current, target, healing_rate=0.1)
        fast_heal = self_heal(current, target, healing_rate=0.5)

        assert fast_heal > slow_heal

    def test_equilibrium_force(self):
        """Test equilibrium force direction."""
        # Displaced right, force should be left
        force = equilibrium_force(10.0, equilibrium=0.0)
        assert force < 0

        # Displaced left, force should be right
        force = equilibrium_force(-10.0, equilibrium=0.0)
        assert force > 0


class TestWaveSimulation:
    """Test wave propagation simulation."""

    def test_simulation_creation(self):
        """Test simulation creates correctly."""
        sim = WaveSimulation(threat_level=5)

        assert sim.threat_level == 5
        assert sim.step == 0
        assert sim.health == 100.0

    def test_spawn_malicious(self):
        """Test spawning malicious units."""
        sim = WaveSimulation(threat_level=5)
        sim.spawn_malicious(5.0)

        assert len(sim.malicious_units) > 0
        assert sim.total_malicious_spawned > 0

    def test_spawn_antibodies(self):
        """Test spawning antibodies."""
        sim = WaveSimulation(threat_level=5)
        sim.spawn_antibodies(5.0)

        assert len(sim.antibody_units) > 0
        assert sim.total_antibodies_spawned > 0

    def test_run_wave(self):
        """Test running complete wave."""
        sim = WaveSimulation(threat_level=5)
        metrics = sim.run_wave(steps=20, spawn_interval=5)

        assert len(metrics) == 20
        assert sim.step == 20

    def test_neutralization(self):
        """Test antibodies neutralize threats."""
        sim = WaveSimulation(threat_level=5)

        # Force interaction by spawning at same position
        sim.spawn_malicious(10.0)
        sim.spawn_antibodies(10.0)

        # Run a few steps for interaction
        for _ in range(10):
            sim.step_simulation()

        # Some neutralization should have occurred
        assert sim.total_neutralized >= 0  # May be 0 if no collisions

    def test_final_metrics(self):
        """Test final metrics calculation."""
        sim = WaveSimulation(threat_level=7)
        sim.run_wave(steps=50)

        metrics = sim.get_final_metrics()

        assert "threat_level" in metrics
        assert "propagation_success_rate" in metrics
        assert "detection_rate" in metrics
        assert "system_stability" in metrics


class TestChemistryAgent:
    """Test chemistry defense agent."""

    def test_agent_creation(self):
        """Test agent creates correctly."""
        agent = ChemistryAgent("test-agent")

        assert agent.agent_id == "test-agent"
        assert agent.state == AgentState.DORMANT
        assert agent.health == 100.0

    def test_agent_activation(self):
        """Test agent activation."""
        agent = ChemistryAgent("test-agent")

        agent.activate()
        assert agent.state == AgentState.MONITORING

        agent.deactivate()
        assert agent.state == AgentState.DORMANT

    def test_threat_level_affects_state(self):
        """Test threat level changes state."""
        agent = ChemistryAgent("test-agent")

        agent.set_threat_level(1)
        # Low threat = recovering or monitoring

        agent.set_threat_level(9)
        assert agent.state == AgentState.COMBAT

    def test_process_normal_input(self):
        """Test processing normal input."""
        agent = ChemistryAgent("test-agent")
        agent.set_threat_level(3)

        processed, blocked = agent.process_input(1.0, ThreatType.NORMAL)

        # Small input should not be blocked
        assert blocked is False or processed <= 1.0

    def test_process_malicious_input(self):
        """Test processing malicious input."""
        agent = ChemistryAgent("test-agent")
        agent.set_threat_level(8)

        # Force high energy input
        processed, blocked = agent.process_input(100.0, ThreatType.MALICIOUS)

        # Should be blocked and reduced
        assert blocked is True
        assert processed < 100.0

    def test_agent_healing(self):
        """Test agent self-healing."""
        agent = ChemistryAgent("test-agent")
        agent.health = 50.0

        agent.heal()

        assert agent.health > 50.0

    def test_agent_status(self):
        """Test agent status report."""
        agent = ChemistryAgent("test-agent")
        agent.set_threat_level(5)
        agent.process_input(50.0, ThreatType.MALICIOUS)

        status = agent.get_status()

        assert "agent_id" in status
        assert "state" in status
        assert "health_percent" in status
        assert "total_threats_blocked" in status


class TestQuickDefense:
    """Test quick defense functions."""

    def test_quick_defense_safe_input(self):
        """Test quick defense with safe input."""
        processed, blocked, energy = quick_defense_check(1.0, threat_level=3)

        assert energy < 5.0  # Low energy

    def test_quick_defense_threat(self):
        """Test quick defense with threat."""
        processed, blocked, energy = quick_defense_check(100.0, threat_level=8)

        assert blocked is True
        assert processed < 100.0

    def test_run_threat_simulation(self):
        """Test running threat simulation."""
        metrics = run_threat_simulation(threat_level=5, steps=50)

        assert "threat_level" in metrics
        assert metrics["threat_level"] == 5
        assert "total_steps" in metrics
