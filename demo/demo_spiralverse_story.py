#!/usr/bin/env python3
"""
demo_spiralverse_story.py
=========================
Story-driven demo runner for SpiralVerse Protocol (multi-sig enabled).
"""

import asyncio
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spiralverse_core import (
    Agent6D, SecurityGate, Roundtable, RWPEnvelope,
    pricing_tier, TONGUES, NonceCache
)

async def demonstrate_spiralverse():
    print("=" * 80)
    print("SPIRALVERSE PROTOCOL - COMPLETE DEMONSTRATION (Story + Core, Multi-Sig)")
    print("=" * 80)
    print()

    master_key = b"demo_master_key_12345678"  # demo key only
    nonce_cache = NonceCache(window_ms=60_000)
    gate = SecurityGate()

    # Agents
    print("PART 1: Creating AI Agents in 6D Space")
    print("-" * 80)
    alice = Agent6D("Alice-GPT", (1.0, 2.0, 3.0, 0.5, 1.5, 2.5))
    bob   = Agent6D("Bob-Claude", (1.1, 2.1, 3.1, 0.6, 1.6, 2.6))
    eve   = Agent6D("Eve-Hacker", (10.0, 15.0, 20.0, 5.0, 8.0, 12.0), trust_score=0.2)

    print(f"  [+] Alice (trusted): {alice.position[:3]}...")
    print(f"  [+] Bob   (trusted): {bob.position[:3]}...")
    print(f"  [+] Eve (low trust): {eve.position[:3]}...")
    print()
    print(f"  Distance Alice->Bob: {alice.distance_to(bob):.2f}")
    print(f"  Distance Alice->Eve: {alice.distance_to(eve):.2f}")
    print()

    # Pricing tiers
    print("PART 2: Harmonic Complexity Pricing")
    print("-" * 80)
    for depth in [1, 2, 3, 4]:
        tier = pricing_tier(depth)
        print(f"  Depth {depth}: {tier['tier']:12} | Complexity {tier['complexity']:8.2f} | {tier['description']}")
    print()

    # Envelope create/seal
    print("PART 3: Creating Secure Envelope (Multi-Signature RWP demo v2.1)")
    print("-" * 80)

    message = {
        "action": "transfer_funds",
        "amount": 1000,
        "from": "account_123",
        "to": "account_456",
    }

    # Put action in AAD so policy is enforceable without decrypting payload
    aad = {"action": "transfer_funds", "mode": "STRICT"}

    required = Roundtable.required_tongues(aad["action"])
    print(f"  Action '{aad['action']}' requires quorum tongues: {required}")

    env = RWPEnvelope.seal(
        master_key=master_key,
        primary_tongue="KO",
        origin="Alice-GPT",
        payload_obj=message,
        aad=aad,
        signing_tongues=required,  # sign exactly with quorum tongues
        kid_default="k1"
    )
    sealed = env.to_dict()

    print(f"  Primary Tongue: {sealed['primary_tongue']} ({TONGUES[sealed['primary_tongue']]})")
    print(f"  Origin: {sealed['origin']}")
    print(f"  Timestamp(ms): {sealed['ts_ms']}")
    print(f"  Nonce: {sealed['nonce'][:16]}...")
    print(f"  Signed Tongues: {sorted(list(sealed['sigs'].keys()))}")
    print(f"  Payload (encrypted b64): {sealed['payload'][:40]}...")
    print()

    # Verify/open
    print("PART 4: Verifying Envelope (Policy + Replay + Multi-Sig)")
    print("-" * 80)

    decision, result = RWPEnvelope.verify_and_open(sealed, master_key, nonce_cache, debug=True)
    print(f"  Decision: {decision}")
    print("  Result:", json.dumps(result, indent=2))
    print()

    # Tamper one signature -> DENY (fail-to-noise)
    print("PART 5: Tamper Detection (Corrupt one signature)")
    print("-" * 80)

    tampered = dict(sealed)
    tampered["sigs"] = dict(sealed["sigs"])
    # corrupt KO signature
    tampered["sigs"]["KO"] = "deadbeef" * 8

    decision2, result2 = RWPEnvelope.verify_and_open(tampered, master_key, nonce_cache, debug=True)
    print(f"  Decision: {decision2}")
    print("  Result:", result2)
    print()

    # Replay attempt -> DENY (fail-to-noise)
    print("PART 6: Replay Protection (Same Envelope Again)")
    print("-" * 80)

    decision3, result3 = RWPEnvelope.verify_and_open(sealed, master_key, nonce_cache, debug=True)
    print(f"  Replay Decision: {decision3}")
    print("  Replay Result:", result3)
    print()

    # Security gate checks
    print("PART 7: Security Gate Checks (Time Dilation)")
    print("-" * 80)

    print("\n  Scenario 1: Alice wants READ (internal)")
    r1 = await gate.check(alice, "read", {"source": "internal"})
    print(f"    Status: {r1['status'].upper()} | score={r1['score']:.2f} | wait={r1['dwell_ms']:.0f}ms")

    print("\n  Scenario 2: Alice wants DELETE (internal)")
    r2 = await gate.check(alice, "delete", {"source": "internal"})
    print(f"    Status: {r2['status'].upper()} | score={r2['score']:.2f} | wait={r2['dwell_ms']:.0f}ms")
    if r2["status"] != "allow":
        print(f"    Reason: {r2.get('reason','N/A')}")

    print("\n  Scenario 3: Eve (trust=0.2) wants READ (external)")
    r3 = await gate.check(eve, "read", {"source": "external"})
    print(f"    Status: {r3['status'].upper()} | score={r3['score']:.2f} | wait={r3['dwell_ms']:.0f}ms")
    if r3["status"] != "allow":
        print(f"    Reason: {r3.get('reason','N/A')}")
    print()

    print("=" * 80)
    print("SUMMARY (Plain English)")
    print("=" * 80)
    print("""
- Messages are sealed with multi-tongue signatures.
- Policy requires specific tongues based on action (Roundtable quorum).
- Replay attempts are denied.
- Tampering yields deterministic noise (no oracle feedback).
- Risky behavior gets slowed down (time dilation).

Next obvious upgrade: multi-agent signatures from distinct keys (not derived from one master),
and replacing demo stream-XOR with AEAD in production.
""")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(demonstrate_spiralverse())
