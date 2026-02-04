#!/usr/bin/env python3
"""Run Dual Lattice demo with UTF-8 encoding."""
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("  DUAL LATTICE CROSS-STITCH - Hyperbolic Multi-Agent Coordination")
print("=" * 80)
print()

from src.crypto.dual_lattice import demo
demo()
