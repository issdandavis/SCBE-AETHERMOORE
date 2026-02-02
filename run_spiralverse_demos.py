#!/usr/bin/env python3
"""Run all Spiralverse demos with UTF-8 encoding."""
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 70)
print("  SPIRALVERSE 6-LANGUAGE CODEX SYSTEM v2.0 - Demo Suite")
print("=" * 70)
print()

# Run each demo
demos = [
    ("Polyglot Alphabet", "src.spiralverse.polyglot_alphabet"),
    ("6D Vector Navigation", "src.spiralverse.vector_6d"),
    ("Proximity Optimizer", "src.spiralverse.proximity_optimizer"),
    ("RWP2 Envelope", "src.spiralverse.rwp2_envelope"),
    ("Hive Memory", "src.spiralverse.hive_memory"),
]

for name, module in demos:
    print(f"\n{'='*70}")
    print(f"  RUNNING: {name}")
    print(f"{'='*70}\n")

    try:
        mod = __import__(module, fromlist=['demo'])
        if hasattr(mod, 'demo'):
            import asyncio
            if asyncio.iscoroutinefunction(mod.demo):
                asyncio.run(mod.demo())
            else:
                mod.demo()
        print(f"\n  [{name}] PASSED")
    except Exception as e:
        print(f"\n  [{name}] ERROR: {e}")

print("\n" + "=" * 70)
print("  ALL DEMOS COMPLETE")
print("=" * 70)
