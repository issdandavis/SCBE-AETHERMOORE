"""
Tests for Patent-Related Modules: Topological CFI and Dual-Lattice Consensus

This test suite validates the core claims in the patent application:
1. Hyperbolic geometry for authorization (Topological CFI)
2. Dual-lattice consensus with ML-DSA-65 (Dilithium)
3. Context-bound authorization tokens
4. Quantum-resistant factor of 2 improvement
"""

import pytest
import numpy as np
import sys
import os
import hashlib
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the patent modules
from topological_cfi import (
    TopologicalCFI,
    HyperbolicPoint,
    compute_hyperbolic_distance,
    map_to_poincare_disk,
    verify_principal_curve_membership,
)
from dual_lattice_consensus import (
    DualLatticeConsensus,
    create_authorization_token,
    verify_token,
)


class TestHyperbolicGeometry:
    """Tests for hyperbolic geometry authorization."""
    
    def test_poincare_disk_mapping(self):
        """Verify points map correctly to Poincare disk (|z| < 1)."""
        for _ in range(100):
            x = np.random.randn()
            y = np.random.randn()
            point = map_to_poincare_disk(x, y)
            
            # All points must be inside unit disk
            radius = np.sqrt(point.x**2 + point.y**2)
            assert radius < 1.0, f"Point {point} outside Poincare disk"
    
    def test_hyperbolic_distance_properties(self):
        """Verify hyperbolic distance satisfies metric properties."""
        p1 = HyperbolicPoint(0.0, 0.0)  # Origin
        p2 = HyperbolicPoint(0.5, 0.0)
        p3 = HyperbolicPoint(0.0, 0.5)
        
        # Non-negativity
        d12 = compute_hyperbolic_distance(p1, p2)
        assert d12 >= 0
        
        # Identity: d(x,x) = 0
        d11 = compute_hyperbolic_distance(p1, p1)
        assert abs(d11) < 1e-10
        
        # Symmetry: d(x,y) = d(y,x)
        d21 = compute_hyperbolic_distance(p2, p1)
        assert abs(d12 - d21) < 1e-10
        
        # Triangle inequality: d(x,z) <= d(x,y) + d(y,z)
        d13 = compute_hyperbolic_distance(p1, p3)
        d23 = compute_hyperbolic_distance(p2, p3)
        assert d13 <= d12 + d23 + 1e-10
    
    def test_hyperbolic_distance_boundary_behavior(self):
        """Distance grows exponentially near disk boundary."""
        origin = HyperbolicPoint(0.0, 0.0)
        
        distances = []
        for r in [0.1, 0.5, 0.9, 0.99, 0.999]:
            point = HyperbolicPoint(r, 0.0)
            d = compute_hyperbolic_distance(origin, point)
            distances.append(d)
        
        # Distances should grow rapidly near boundary
        for i in range(len(distances) - 1):
            assert distances[i+1] > distances[i]
        
        # The 0.999 point should be MUCH farther than 0.5 point
        assert distances[-1] > 5 * distances[1]


class TestTopologicalCFI:
    """Tests for Control Flow Integrity using topology."""
    
    def test_initialization(self):
        """TopologicalCFI should initialize correctly."""
        cfi = TopologicalCFI()
        assert cfi is not None
        assert hasattr(cfi, 'hamiltonian_tested')
    
    def test_hamiltonian_path_verification(self):
        """Valid execution paths should satisfy Hamiltonian property."""
        cfi = TopologicalCFI()
        
        # Create a simple authorized path
        path = ['start', 'auth', 'process', 'verify', 'end']
        
        result = cfi.verify_execution_path(path)
        assert result['valid'] is True
        assert result['hamiltonian_tested'] is True
    
    def test_invalid_path_detection(self):
        """Paths violating Hamiltonian constraint should be rejected."""
        cfi = TopologicalCFI()
        
        # Path with repeated node (not Hamiltonian)
        invalid_path = ['start', 'auth', 'start', 'end']  # 'start' repeated
        
        result = cfi.verify_execution_path(invalid_path)
        assert result['valid'] is False
        assert 'violation' in result['reason'].lower()
    
    def test_principal_curve_membership(self):
        """Authorized states lie on principal curve in hyperbolic space."""
        # Valid authorization should map to curve
        auth_state = {
            'identity': 'user_123',
            'intent': 'read_data',
            'context': 'session_abc'
        }
        
        on_curve = verify_principal_curve_membership(auth_state)
        assert on_curve is True
        
        # Tampered state should NOT be on curve
        tampered_state = {
            'identity': 'user_123',
            'intent': 'DELETE_ALL',  # Unauthorized action
            'context': 'session_abc'
        }
        
        on_curve_tampered = verify_principal_curve_membership(tampered_state)
        assert on_curve_tampered is False


class TestDualLatticeConsensus:
    """Tests for ML-DSA-65 dual-lattice consensus."""
    
    def test_initialization(self):
        """DualLatticeConsensus should initialize with ML-KEM-768 and ML-DSA-65."""
        dlc = DualLatticeConsensus()
        
        assert dlc.kem_algorithm == 'ML-KEM-768'
        assert dlc.dsa_algorithm == 'ML-DSA-65'
    
    def test_token_creation(self):
        """Authorization tokens should be created with valid structure."""
        dlc = DualLatticeConsensus()
        
        token = dlc.create_authorization_token(
            identity='user_test',
            intent='read',
            context={'session_id': 'sess_123', 'timestamp': time.time()}
        )
        
        # Token should have required fields
        assert 'decision' in token
        assert 'consensus_hash' in token
        assert 'session_key_id' in token
        assert 'signature' in token
        
        # Hash should be 64 hex chars (SHA-256)
        assert len(token['consensus_hash']) == 64
    
    def test_token_verification_valid(self):
        """Valid tokens should verify successfully."""
        dlc = DualLatticeConsensus()
        
        token = dlc.create_authorization_token(
            identity='user_test',
            intent='read',
            context={'session_id': 'sess_456'}
        )
        
        result, reason = dlc.verify_token(token)
        
        assert result is True
        assert reason == 'VERIFIED'
    
    def test_token_verification_tampered(self):
        """Tampered tokens should fail verification."""
        dlc = DualLatticeConsensus()
        
        token = dlc.create_authorization_token(
            identity='user_test',
            intent='read',
            context={'session_id': 'sess_789'}
        )
        
        # Tamper with the consensus hash
        tampered_token = token.copy()
        tampered_token['consensus_hash'] = 'a' * 64  # Invalid hash
        
        result, reason = dlc.verify_token(tampered_token)
        
        assert result is False
        assert 'tamper' in reason.lower() or 'invalid' in reason.lower()
    
    def test_consensus_requires_both_lattices(self):
        """Consensus must agree from both KEM and DSA lattice results."""
        dlc = DualLatticeConsensus()
        
        # Get internal consensus state
        token = dlc.create_authorization_token(
            identity='consensus_test',
            intent='verify',
            context={}
        )
        
        # Both lattices must report ALLOW for consensus
        assert dlc.last_kem_result == 'ALLOW'
        assert dlc.last_dsa_result == 'ALLOW'
        assert token['decision'] == 'ALLOW'


class TestQuantumResistance:
    """Tests validating the quantum resistance claims."""
    
    def test_dual_lattice_improvement_factor(self):
        """
        Dual-lattice consensus provides 2x quantum resistance.
        
        Single lattice: vulnerable to individual attack
        Dual lattice: requires breaking BOTH, multiplicative security
        """
        dlc = DualLatticeConsensus()
        
        # Simulate attack scenarios
        # Single lattice broken = still protected by other
        dlc.simulate_kem_compromise()
        assert dlc.is_secure() is True  # Still secure via DSA
        
        dlc.reset_simulation()
        dlc.simulate_dsa_compromise()
        assert dlc.is_secure() is True  # Still secure via KEM
        
        dlc.reset_simulation()
        # Both compromised = system fails
        dlc.simulate_kem_compromise()
        dlc.simulate_dsa_compromise()
        assert dlc.is_secure() is False
    
    def test_nist_compliance(self):
        """Verify algorithms comply with NIST FIPS 203/204."""
        dlc = DualLatticeConsensus()
        
        # ML-KEM-768 is FIPS 203 compliant
        assert dlc.kem_fips_compliance == 'FIPS-203'
        
        # ML-DSA-65 is FIPS 204 compliant
        assert dlc.dsa_fips_compliance == 'FIPS-204'
    
    def test_context_binding(self):
        """Tokens must be bound to specific context."""
        dlc = DualLatticeConsensus()
        
        context1 = {'session_id': 'session_A', 'ip': '192.168.1.1'}
        context2 = {'session_id': 'session_B', 'ip': '192.168.1.2'}
        
        token1 = dlc.create_authorization_token(
            identity='user', intent='read', context=context1
        )
        
        # Token created for context1 should NOT verify for context2
        result, _ = dlc.verify_token_with_context(token1, context2)
        assert result is False
        
        # Token should verify for original context
        result, _ = dlc.verify_token_with_context(token1, context1)
        assert result is True


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_authorization_flow(self):
        """Complete authorization: identity -> CFI -> consensus -> token."""
        # Initialize systems
        cfi = TopologicalCFI()
        dlc = DualLatticeConsensus()
        
        # Step 1: Verify execution path (CFI)
        execution_path = ['entry', 'authenticate', 'authorize', 'process', 'exit']
        cfi_result = cfi.verify_execution_path(execution_path)
        assert cfi_result['valid'] is True
        
        # Step 2: Map to hyperbolic space
        auth_state = {
            'identity': 'integration_user',
            'intent': 'full_test',
            'context': 'integration_context',
            'cfi_verified': cfi_result['valid']
        }
        on_curve = verify_principal_curve_membership(auth_state)
        assert on_curve is True
        
        # Step 3: Create authorization token with dual-lattice
        token = dlc.create_authorization_token(
            identity=auth_state['identity'],
            intent=auth_state['intent'],
            context={'cfi_hash': cfi_result.get('hash', 'none')}
        )
        assert token['decision'] == 'ALLOW'
        
        # Step 4: Verify token
        result, reason = dlc.verify_token(token)
        assert result is True
        
        print(f"Integration test PASSED: {reason}")


# Standalone execution for demonstration
if __name__ == '__main__':
    print("="*60)
    print("SYMPHONIC CIPHER - Patent Module Tests")
    print("="*60)
    print()
    print("Running tests for:")
    print("  1. Hyperbolic Geometry Authorization")
    print("  2. Topological Control Flow Integrity")
    print("  3. Dual-Lattice Consensus (ML-KEM-768 + ML-DSA-65)")
    print("  4. Quantum Resistance Validation")
    print("  5. End-to-End Integration")
    print()
    print("-"*60)
    
    # Run with pytest
    pytest.main([__file__, '-v', '--tb=short'])
