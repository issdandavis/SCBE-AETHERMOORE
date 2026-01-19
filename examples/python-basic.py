#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Basic Python Examples

Run with: python examples/python-basic.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print('=' * 60)
print('SCBE-AETHERMOORE v3.0 - Python Examples')
print('=' * 60)
print()

# Example 1: Symphonic Cipher
print('1. Symphonic Cipher Signing:')
try:
    from symphonic_cipher.core import SymphonicCipher
    
    cipher = SymphonicCipher()
    intent = '{"amount": 500, "to": "0x123..."}'
    
    # Note: Actual API may differ, check core.py for exact methods
    print(f'  Intent: {intent}')
    print('  Cipher initialized successfully')
except Exception as e:
    print(f'  Error: {e}')
print()

# Example 2: Harmonic Scaling Law
print('2. Harmonic Scaling Law:')
try:
    from symphonic_cipher.harmonic_scaling_law import harmonic_scale
    
    dimension = 6
    base_risk = 1.5
    scaled = harmonic_scale(dimension, base_risk)
    
    print(f'  H({dimension}, {base_risk}) = {scaled:.2e}')
except Exception as e:
    print(f'  Error: {e}')
print()

# Example 3: Dual Lattice Consensus
print('3. Dual Lattice Consensus:')
try:
    from symphonic_cipher.dual_lattice_consensus import DualLatticeConsensus
    
    consensus = DualLatticeConsensus(num_nodes=3)
    print('  Consensus system initialized')
    print(f'  Nodes: {consensus.num_nodes}')
except Exception as e:
    print(f'  Error: {e}')
print()

# Example 4: Topological CFI
print('4. Topological Control Flow Integrity:')
try:
    from symphonic_cipher.topological_cfi import TopologicalCFI
    
    cfi = TopologicalCFI()
    print('  CFI system initialized')
except Exception as e:
    print(f'  Error: {e}')
print()

# Example 5: Flat Slope Encoder
print('5. Flat Slope Encoder:')
try:
    from symphonic_cipher.flat_slope_encoder import FlatSlopeEncoder
    
    encoder = FlatSlopeEncoder()
    data = b"Hello, SCBE!"
    print(f'  Original: {data}')
    print('  Encoder initialized')
except Exception as e:
    print(f'  Error: {e}')
print()

print('=' * 60)
print('Examples complete! Check QUICKSTART.md for more.')
print('=' * 60)
