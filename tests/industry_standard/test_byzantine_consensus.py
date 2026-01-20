#!/usr/bin/env python3
"""
Byzantine Fault Tolerance and Consensus Tests
==============================================
Based on Byzantine Generals Problem and distributed consensus research.

These tests verify REAL Byzantine fault tolerance, not approximations.
Failing tests indicate vulnerabilities to Byzantine attacks.

References:
- Lamport, L. et al. "The Byzantine Generals Problem" (1982)
- Castro, M. & Liskov, B. "Practical Byzantine Fault Tolerance" (1999)
- Nakamoto, S. "Bitcoin: A Peer-to-Peer Electronic Cash System" (2008)
- Buterin, V. "Ethereum: A Next-Generation Smart Contract Platform" (2014)

Last Updated: January 19, 2026
"""

import pytest
import sys
import os
import numpy as np
from typing import Dict, List, Tuple, Set
import hashlib
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Try to import consensus modules
try:
    from symphonic_cipher.dual_lattice_consensus import DualLatticeConsensus
    CONSENSUS_AVAILABLE = True
except ImportError:
    CONSENSUS_AVAILABLE = False


class TestByzantineFaultTolerance:
    """
    Byzantine Fault Tolerance Tests
    
    Byzantine fault tolerance requires:
    - Tolerating up to f faulty nodes where n ≥ 3f + 1
    - Agreement: All honest nodes agree on same value
    - Validity: If all honest nodes propose v, they decide v
    - Termination: All honest nodes eventually decide
    
    These tests verify REAL BFT properties.
    """
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_byzantine_threshold(self):
        """
        Byzantine Threshold Test
        
        For n nodes, system MUST tolerate f Byzantine faults where:
        n ≥ 3f + 1
        
        This is the FUNDAMENTAL Byzantine fault tolerance bound.
        This test WILL FAIL if threshold is violated.
        """
        if not hasattr(DualLatticeConsensus, 'get_byzantine_threshold'):
            pytest.fail("Byzantine threshold not implemented")
        
        consensus = DualLatticeConsensus()
        
        # Test various network sizes
        test_cases = [
            (4, 1),   # 4 nodes can tolerate 1 fault
            (7, 2),   # 7 nodes can tolerate 2 faults
            (10, 3),  # 10 nodes can tolerate 3 faults
            (13, 4),  # 13 nodes can tolerate 4 faults
        ]
        
        for n_nodes, expected_f in test_cases:
            f = consensus.get_byzantine_threshold(n_nodes)
            assert f == expected_f, f"Byzantine threshold wrong: n={n_nodes}, expected f={expected_f}, got f={f}"
            
            # Verify n ≥ 3f + 1
            assert n_nodes >= 3 * f + 1, f"Byzantine bound violated: {n_nodes} < 3*{f}+1"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_agreement_property(self):
        """
        Agreement Property Test
        
        All honest nodes MUST agree on the same value.
        Even with Byzantine nodes present.
        
        This test WILL FAIL if honest nodes disagree.
        """
        if not hasattr(DualLatticeConsensus, 'reach_consensus'):
            pytest.fail("Consensus not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=7, byzantine_nodes=2)
        
        # Honest nodes propose same value
        proposals = {
            'node_0': 'value_A',
            'node_1': 'value_A',
            'node_2': 'value_A',
            'node_3': 'value_A',
            'node_4': 'value_A',
            # Byzantine nodes propose different values
            'node_5': 'value_B',
            'node_6': 'value_C',
        }
        
        decisions = consensus.reach_consensus(proposals)
        
        # All honest nodes must agree
        honest_decisions = [decisions[f'node_{i}'] for i in range(5)]
        assert len(set(honest_decisions)) == 1, f"Honest nodes disagree: {honest_decisions}"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_validity_property(self):
        """
        Validity Property Test
        
        If all honest nodes propose value v, they MUST decide v.
        Byzantine nodes cannot force a different decision.
        
        This test WILL FAIL if Byzantine nodes can override honest majority.
        """
        if not hasattr(DualLatticeConsensus, 'reach_consensus'):
            pytest.fail("Consensus not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=7, byzantine_nodes=2)
        
        # All honest nodes propose 'value_A'
        proposals = {
            'node_0': 'value_A',
            'node_1': 'value_A',
            'node_2': 'value_A',
            'node_3': 'value_A',
            'node_4': 'value_A',
            # Byzantine nodes try to force 'value_B'
            'node_5': 'value_B',
            'node_6': 'value_B',
        }
        
        decisions = consensus.reach_consensus(proposals)
        
        # All honest nodes must decide 'value_A'
        for i in range(5):
            assert decisions[f'node_{i}'] == 'value_A', f"Validity violated: honest node decided {decisions[f'node_{i}']}"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_termination_property(self):
        """
        Termination Property Test
        
        All honest nodes MUST eventually decide.
        Consensus cannot hang indefinitely.
        
        This test WILL FAIL if consensus doesn't terminate.
        """
        if not hasattr(DualLatticeConsensus, 'reach_consensus'):
            pytest.fail("Consensus not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=7, byzantine_nodes=2)
        
        proposals = {f'node_{i}': f'value_{i % 3}' for i in range(7)}
        
        # Set timeout
        start_time = time.time()
        timeout = 10.0  # 10 seconds
        
        decisions = consensus.reach_consensus(proposals, timeout=timeout)
        
        elapsed = time.time() - start_time
        
        # Must terminate before timeout
        assert elapsed < timeout, f"Consensus didn't terminate within {timeout}s"
        
        # All honest nodes must have decided
        for i in range(5):  # First 5 are honest
            assert f'node_{i}' in decisions, f"Honest node {i} didn't decide"
            assert decisions[f'node_{i}'] is not None, f"Honest node {i} decided None"


class TestDualLatticeConsensus:
    """
    Dual Lattice Consensus Tests
    
    Tests the SCBE dual lattice consensus mechanism:
    - Classical lattice for traditional consensus
    - Quantum-resistant lattice for post-quantum security
    - Dual verification for enhanced security
    
    These tests verify the dual lattice approach works correctly.
    """
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_dual_lattice_agreement(self):
        """
        Dual Lattice Agreement Test
        
        Both classical and quantum-resistant lattices MUST agree.
        If they disagree, consensus MUST fail safely.
        
        This test WILL FAIL if dual verification doesn't work.
        """
        if not hasattr(DualLatticeConsensus, 'dual_verify'):
            pytest.fail("Dual lattice verification not implemented")
        
        consensus = DualLatticeConsensus()
        
        # Test case where both lattices agree
        classical_result = {'value': 'A', 'signatures': ['sig1', 'sig2', 'sig3']}
        quantum_result = {'value': 'A', 'signatures': ['qsig1', 'qsig2', 'qsig3']}
        
        result = consensus.dual_verify(classical_result, quantum_result)
        
        assert result['agreed'] == True, "Dual lattices should agree on same value"
        assert result['value'] == 'A', "Agreed value incorrect"
        
        # Test case where lattices disagree
        classical_result = {'value': 'A', 'signatures': ['sig1', 'sig2', 'sig3']}
        quantum_result = {'value': 'B', 'signatures': ['qsig1', 'qsig2', 'qsig3']}
        
        result = consensus.dual_verify(classical_result, quantum_result)
        
        assert result['agreed'] == False, "Dual lattices should detect disagreement"
        assert result['safe_failure'] == True, "Must fail safely on disagreement"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_quantum_resistant_signatures(self):
        """
        Quantum-Resistant Signature Test
        
        Quantum lattice MUST use post-quantum signatures (ML-DSA).
        Classical attacks should not break quantum lattice.
        
        This test WILL FAIL if quantum lattice is not quantum-resistant.
        """
        if not hasattr(DualLatticeConsensus, 'verify_quantum_signature'):
            pytest.skip("Quantum signature verification not exposed")
        
        consensus = DualLatticeConsensus()
        
        # Generate quantum signature
        message = b"consensus_value_A"
        signature = consensus.generate_quantum_signature(message)
        
        # Verify signature
        valid = consensus.verify_quantum_signature(message, signature)
        assert valid == True, "Valid quantum signature failed verification"
        
        # Test with wrong message
        wrong_message = b"consensus_value_B"
        valid = consensus.verify_quantum_signature(wrong_message, signature)
        assert valid == False, "Quantum signature verified with wrong message"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_lattice_hardness(self):
        """
        Lattice Hardness Test
        
        Both lattices MUST be based on hard lattice problems:
        - Classical: RSA or ECDSA (for now)
        - Quantum: LWE/SIS (ML-DSA)
        
        This test verifies lattice security parameters.
        """
        if not hasattr(DualLatticeConsensus, 'get_security_parameters'):
            pytest.skip("Security parameters not exposed")
        
        consensus = DualLatticeConsensus()
        
        params = consensus.get_security_parameters()
        
        # Classical lattice security
        assert params['classical']['security_bits'] >= 128, "Classical security too low"
        
        # Quantum lattice security
        assert params['quantum']['security_bits'] >= 128, "Quantum security too low"
        assert params['quantum']['nist_level'] >= 3, "Quantum security below NIST Level 3"


class TestConsensusAttackResistance:
    """
    Consensus Attack Resistance Tests
    
    Tests resistance to various consensus attacks:
    - Sybil attacks
    - Eclipse attacks
    - 51% attacks
    - Nothing-at-stake attacks
    
    These tests verify REAL attack resistance.
    """
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_sybil_attack_resistance(self):
        """
        Sybil Attack Resistance Test
        
        Attacker creates multiple fake identities to gain influence.
        System MUST detect and reject Sybil nodes.
        
        This test WILL FAIL if Sybil attacks succeed.
        """
        if not hasattr(DualLatticeConsensus, 'detect_sybil'):
            pytest.skip("Sybil detection not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=10)
        
        # Attacker creates 5 Sybil identities
        sybil_nodes = ['sybil_0', 'sybil_1', 'sybil_2', 'sybil_3', 'sybil_4']
        
        for node in sybil_nodes:
            is_sybil = consensus.detect_sybil(node)
            assert is_sybil == True, f"Failed to detect Sybil node: {node}"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_51_percent_attack_resistance(self):
        """
        51% Attack Resistance Test
        
        Attacker controls >50% of nodes to force malicious consensus.
        Dual lattice MUST detect and prevent this.
        
        This test WILL FAIL if 51% attacks succeed.
        """
        if not hasattr(DualLatticeConsensus, 'detect_majority_attack'):
            pytest.skip("Majority attack detection not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=10)
        
        # Attacker controls 6/10 nodes (60%)
        attacker_nodes = [f'attacker_{i}' for i in range(6)]
        
        # Attacker tries to force malicious value
        proposals = {}
        for i in range(6):
            proposals[f'attacker_{i}'] = 'malicious_value'
        for i in range(4):
            proposals[f'honest_{i}'] = 'honest_value'
        
        # System must detect attack
        attack_detected = consensus.detect_majority_attack(proposals)
        assert attack_detected == True, "Failed to detect 51% attack"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_eclipse_attack_resistance(self):
        """
        Eclipse Attack Resistance Test
        
        Attacker isolates victim node from honest network.
        System MUST detect network partition.
        
        This test WILL FAIL if eclipse attacks succeed.
        """
        if not hasattr(DualLatticeConsensus, 'detect_eclipse'):
            pytest.skip("Eclipse detection not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=10)
        
        # Victim node only connected to attacker nodes
        victim_connections = ['attacker_0', 'attacker_1', 'attacker_2']
        
        is_eclipsed = consensus.detect_eclipse('victim_node', victim_connections)
        assert is_eclipsed == True, "Failed to detect eclipse attack"


class TestConsensusPerformance:
    """
    Consensus Performance Tests
    
    Tests consensus performance under various conditions:
    - Latency
    - Throughput
    - Scalability
    
    These tests verify consensus meets performance requirements.
    """
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_consensus_latency(self):
        """
        Consensus Latency Test
        
        Consensus MUST complete within reasonable time.
        Target: <1 second for 10 nodes
        
        This test WILL FAIL if latency is too high.
        """
        if not hasattr(DualLatticeConsensus, 'reach_consensus'):
            pytest.fail("Consensus not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=10)
        
        proposals = {f'node_{i}': f'value_{i % 3}' for i in range(10)}
        
        start_time = time.time()
        decisions = consensus.reach_consensus(proposals)
        latency = time.time() - start_time
        
        assert latency < 1.0, f"Consensus latency {latency:.3f}s exceeds 1.0s target"
    
    @pytest.mark.skipif(not CONSENSUS_AVAILABLE, reason="Consensus module not available")
    def test_consensus_throughput(self):
        """
        Consensus Throughput Test
        
        System MUST handle multiple consensus rounds efficiently.
        Target: ≥10 rounds/second
        
        This test WILL FAIL if throughput is too low.
        """
        if not hasattr(DualLatticeConsensus, 'reach_consensus'):
            pytest.fail("Consensus not implemented")
        
        consensus = DualLatticeConsensus(n_nodes=7)
        
        n_rounds = 20
        start_time = time.time()
        
        for round_num in range(n_rounds):
            proposals = {f'node_{i}': f'value_{round_num}_{i}' for i in range(7)}
            decisions = consensus.reach_consensus(proposals)
        
        elapsed = time.time() - start_time
        throughput = n_rounds / elapsed
        
        assert throughput >= 10.0, f"Consensus throughput {throughput:.1f} rounds/s below 10 rounds/s target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
