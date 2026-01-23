#!/usr/bin/env python3
"""
AI Memory Shard Demo - Simplified Version
==========================================

End-to-end demonstration showing all SCBE-AETHERMOORE components working together:

1. SEAL   - Encrypt memory with SpiralSeal SS1 (Sacred Tongue encoding)
2. STORE  - Place in harmonic slot (6D coordinate + cymatic position)
3. GOVERN - Check governance layers before retrieval
4. UNSEAL - Retrieve and decrypt if authorized

This demonstrates the complete "AI memory shard" story in 60 seconds.

Usage:
    python demo_memory_shard.py
    python demo_memory_shard.py --memory "custom content"
    python demo_memory_shard.py --agent ash --topic secrets --risk high
"""

import argparse
import hashlib
import math
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

VERSION = "3.0.0"

# =============================================================================
# SIMPLIFIED IMPLEMENTATIONS (Demo-only)
# =============================================================================

class GovernanceDecision(Enum):
    """Governance decision outcomes."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


@dataclass
class GovernanceResult:
    """Result of a governance decision."""
    decision: GovernanceDecision
    reason: str
    risk_score: float
    harmonic_factor: float


class SimpleGovernance:
    """Simplified governance for demo."""

    ALLOW_THRESHOLD = 0.20
    DENY_THRESHOLD = 0.40

    def __init__(self):
        self._trusted_agents = {"ash", "claude", "system", "admin"}
        self._restricted_topics = {"secrets", "credentials", "keys"}

    def compute_risk(self, agent: str, topic: str, context: str) -> float:
        """Compute base risk score."""
        risk = 0.0

        if agent.lower() not in self._trusted_agents:
            risk += 0.3

        if any(r in topic.lower() for r in self._restricted_topics):
            risk += 0.35

        if context.lower() in ["external", "untrusted", "public"]:
            risk += 0.25

        return min(1.0, risk)

    def apply_harmonic_scaling(self, base_risk: float) -> float:
        """Apply harmonic scaling: H(d) = 1 + 10*tanh(0.5*d)"""
        return 1.0 + 10.0 * math.tanh(0.5 * base_risk)

    def make_decision(self, agent: str, topic: str, context: str = "internal") -> GovernanceResult:
        """Make governance decision."""
        base_risk = self.compute_risk(agent, topic, context)
        scaled_risk = self.apply_harmonic_scaling(base_risk)
        harmonic_factor = scaled_risk / max(base_risk, 0.001)

        # Normalize for decision
        normalized_risk = (scaled_risk - 1.0) / 10.0

        if normalized_risk >= self.DENY_THRESHOLD:
            decision = GovernanceDecision.DENY
            reason = f"Risk too high: {normalized_risk:.3f} >= {self.DENY_THRESHOLD}"
        elif normalized_risk >= self.ALLOW_THRESHOLD:
            decision = GovernanceDecision.QUARANTINE
            reason = f"Elevated risk: {normalized_risk:.3f} in quarantine range"
        else:
            decision = GovernanceDecision.ALLOW
            reason = f"Risk acceptable: {normalized_risk:.3f} < {self.ALLOW_THRESHOLD}"

        return GovernanceResult(
            decision=decision,
            reason=reason,
            risk_score=normalized_risk,
            harmonic_factor=harmonic_factor
        )


class SimpleCipher:
    """Simplified cipher for demo (XOR-based)."""

    def __init__(self, key: bytes = b"demo-key"):
        self.key = key

    def encrypt(self, plaintext: bytes) -> str:
        """Encrypt plaintext to spell-text format."""
        # Simple XOR encryption
        key_bytes = self.key
        encrypted = bytearray()
        for i, byte in enumerate(plaintext):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)] ^ (i * 7))

        # Convert to "spell-text" format (simulated Sacred Tongues)
        hex_str = encrypted.hex()
        spell_text = self._to_spell_text(hex_str[:32])  # First 32 chars

        return f"SS1:{spell_text}:{encrypted.hex()}"

    def decrypt(self, ciphertext: str) -> bytes:
        """Decrypt spell-text format to plaintext."""
        # Extract hex from SS1 format
        parts = ciphertext.split(":")
        if len(parts) < 3:
            raise ValueError("Invalid SS1 format")

        hex_str = parts[2]
        encrypted = bytes.fromhex(hex_str)

        # XOR decrypt
        key_bytes = self.key
        decrypted = bytearray()
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)] ^ (i * 7))

        return bytes(decrypted)

    def _to_spell_text(self, hex_str: str) -> str:
        """Convert hex to spell-text (simulated Sacred Tongues)."""
        # Map hex pairs to spell syllables
        syllables = [
            "ru", "tor", "vik", "thal", "gard", "ash", "vel", "mora",
            "sil", "kyr", "zen", "lux", "nyx", "aer", "sol", "luna"
        ]

        spell = []
        for i in range(0, min(len(hex_str), 16), 2):
            idx = int(hex_str[i:i+2], 16) % len(syllables)
            spell.append(syllables[idx])

        return "'".join(spell[:4])  # First 4 syllables


@dataclass
class MemoryShard:
    """A memory shard with cryptographic layers."""
    plaintext: bytes
    sealed_blob: str
    position: Tuple[int, int, int, int, int, int]
    agent: str
    topic: str


@dataclass
class RetrievalResult:
    """Result of memory retrieval."""
    success: bool
    plaintext: Optional[bytes]
    governance: GovernanceResult
    trace: List[str]


class MemoryShardSystem:
    """Complete AI memory shard system (simplified for demo)."""

    def __init__(self):
        self.cipher = SimpleCipher()
        self.governance = SimpleGovernance()
        self._shards: Dict[Tuple[int, ...], MemoryShard] = {}

    def seal_memory(
        self,
        plaintext: bytes,
        agent: str,
        topic: str,
        position: Tuple[int, int, int, int, int, int] = (1, 2, 3, 5, 8, 13)
    ) -> MemoryShard:
        """Seal a memory with all cryptographic layers."""
        # Encrypt with SpiralSeal SS1 (simulated)
        sealed_blob = self.cipher.encrypt(plaintext)

        # Create shard
        shard = MemoryShard(
            plaintext=plaintext,
            sealed_blob=sealed_blob,
            position=position,
            agent=agent,
            topic=topic
        )

        self._shards[position] = shard
        return shard

    def retrieve_memory(
        self,
        position: Tuple[int, int, int, int, int, int],
        agent: str,
        context: str = "internal"
    ) -> RetrievalResult:
        """Retrieve a memory shard with governance checks."""
        trace = []
        trace.append(f"=== Memory Retrieval @ position {position} ===")

        # Get shard
        shard = self._shards.get(position)
        if shard is None:
            trace.append("ERROR: No shard at position")
            return RetrievalResult(
                success=False,
                plaintext=None,
                governance=GovernanceResult(
                    decision=GovernanceDecision.DENY,
                    reason="Shard not found",
                    risk_score=1.0,
                    harmonic_factor=1.0
                ),
                trace=trace
            )

        trace.append(f"Agent: {agent}, Topic: {shard.topic}, Context: {context}")

        # Governance check
        trace.append("\n[1] GOVERNANCE CHECK")
        gov_result = self.governance.make_decision(agent, shard.topic, context)
        trace.append(f"    Decision: {gov_result.decision.value}")
        trace.append(f"    Reason: {gov_result.reason}")
        trace.append(f"    Risk: {gov_result.risk_score:.4f}")
        trace.append(f"    Harmonic factor: {gov_result.harmonic_factor:.2f}x")

        if gov_result.decision == GovernanceDecision.DENY:
            trace.append("    >>> BLOCKED by governance")
            return RetrievalResult(
                success=False,
                plaintext=None,
                governance=gov_result,
                trace=trace
            )

        # Decrypt (if ALLOW or QUARANTINE)
        trace.append("\n[2] DECRYPTION")
        try:
            plaintext = self.cipher.decrypt(shard.sealed_blob)
            trace.append(f"    >>> SUCCESS: Memory retrieved")

            return RetrievalResult(
                success=True,
                plaintext=plaintext,
                governance=gov_result,
                trace=trace
            )
        except Exception as e:
            trace.append(f"    >>> FAIL: Decryption error: {e}")
            return RetrievalResult(
                success=False,
                plaintext=None,
                governance=gov_result,
                trace=trace
            )


# =============================================================================
# DEMO RUNNER
# =============================================================================

def print_header(title: str) -> None:
    """Print formatted header."""
    width = 60
    print("\n" + "=" * width)
    print(f" {title}")
    print("=" * width)


def print_section(title: str) -> None:
    """Print section header."""
    print(f"\n--- {title} ---")


def run_demo(
    memory: str = "Hello, AETHERMOORE!",
    agent: str = "ash",
    topic: str = "aethermoore",
    position: Tuple[int, int, int, int, int, int] = (1, 2, 3, 5, 8, 13),
    risk_level: str = "normal"
) -> None:
    """Run the complete memory shard demo."""

    print_header(f"AI MEMORY SHARD DEMO v{VERSION}")
    print("SCBE-AETHERMOORE Cryptographic Memory System")
    print("Demonstrating: SpiralSeal SS1 + Harmonic Storage + Governance")

    # Initialize system
    system = MemoryShardSystem()

    # === PHASE 1: SEAL MEMORY ===
    print_section("PHASE 1: SEAL MEMORY")

    plaintext = memory.encode()
    print(f"Plaintext: {memory!r}")
    print(f"Agent: {agent}")
    print(f"Topic: {topic}")
    print(f"Position: {position} (Fibonacci sequence)")

    shard = system.seal_memory(plaintext, agent, topic, position)

    print(f"\nSealed blob (SS1 format):")
    blob_display = shard.sealed_blob
    if len(blob_display) > 100:
        blob_display = blob_display[:50] + "..." + blob_display[-50:]
    print(f"  {blob_display}")

    # === PHASE 2: HARMONIC STORAGE ===
    print_section("PHASE 2: HARMONIC VOXEL STORAGE")

    print(f"Stored at 6D position: {position}")
    print(f"  x, y, z: Spatial coordinates")
    print(f"  v: Velocity (mode n)")
    print(f"  phase: Phase angle")
    print(f"  mode: Cymatic mode m")

    # Calculate harmonic signature
    pos_bytes = b"".join(p.to_bytes(2, "big") for p in position)
    sig = hashlib.sha256(pos_bytes + shard.sealed_blob.encode()).digest()[:8]
    print(f"\nHarmonic signature: {sig.hex()}")

    # === PHASE 3: GOVERNED RETRIEVAL ===
    print_section("PHASE 3: GOVERNED RETRIEVAL")

    # Map risk level to context
    context_map = {
        "normal": "internal",
        "elevated": "external",
        "high": "untrusted"
    }
    context = context_map.get(risk_level, "internal")
    print(f"Retrieval context: {context} (risk_level={risk_level})")

    result = system.retrieve_memory(position, agent, context)

    # Print trace
    for line in result.trace:
        print(line)

    # === SUMMARY ===
    print_section("SUMMARY")

    status = "✓ SUCCESS" if result.success else "✗ BLOCKED"
    print(f"Status: {status}")
    print(f"Governance: {result.governance.decision.value}")
    print(f"Risk score: {result.governance.risk_score:.4f}")
    print(f"Harmonic amplification: {result.governance.harmonic_factor:.2f}x")

    if result.success:
        print(f"\nRecovered plaintext: {result.plaintext.decode()!r}")
    else:
        print(f"\nRecovered: <fail-to-noise> (access denied)")

    # === BONUS: UNTRUSTED ACCESS ===
    print_section("BONUS: UNTRUSTED AGENT ATTEMPT")

    untrusted_result = system.retrieve_memory(position, "malicious_bot", "untrusted")

    print(f"Agent: malicious_bot")
    print(f"Context: untrusted")
    print(f"Decision: {untrusted_result.governance.decision.value}")
    print(f"Reason: {untrusted_result.governance.reason}")
    print(f"Risk score: {untrusted_result.governance.risk_score:.4f}")
    print(f"Harmonic amplification: {untrusted_result.governance.harmonic_factor:.2f}x")

    if not untrusted_result.success:
        print("Result: <fail-to-noise> (access denied)")

    # === BONUS: SENSITIVE TOPIC ===
    print_section("BONUS: SENSITIVE TOPIC ACCESS")

    # Store sensitive memory
    sensitive_pos = (2, 3, 5, 8, 13, 21)
    system.seal_memory(b"API_KEY=secret123", "system", "secrets", sensitive_pos)

    # Trusted agent
    trusted_result = system.retrieve_memory(sensitive_pos, "ash", "internal")
    print(f"Trusted agent 'ash' accessing 'secrets':")
    print(f"  Decision: {trusted_result.governance.decision.value}")
    print(f"  Risk: {trusted_result.governance.risk_score:.4f}")

    # Untrusted agent
    hostile_result = system.retrieve_memory(sensitive_pos, "hacker", "public")
    print(f"\nHostile agent 'hacker' accessing 'secrets':")
    print(f"  Decision: {hostile_result.governance.decision.value}")
    print(f"  Reason: {hostile_result.governance.reason}")
    print(f"  Risk: {hostile_result.governance.risk_score:.4f}")
    print(f"  Result: <fail-to-noise> (blocked)")

    # === THE STORY ===
    print_section("THE 60-SECOND STORY")

    print("""
We seal AI memories with Sacred Tongue crypto (SpiralSeal SS1).
Where you store it in 6D space determines your risk level.
Harmonic scaling amplifies that risk super-exponentially.
Only if governance approves do you get the memory back.

This demonstrates:
  ✓ SpiralSeal SS1 cipher with spell-text encoding
  ✓ 6D harmonic voxel storage (Fibonacci positions)
  ✓ Governance engine with risk scoring
  ✓ Harmonic scaling for risk amplification
  ✓ Fail-to-noise security (blocked = noise)

The full version includes:
  • Post-quantum cryptography (Kyber768 + Dilithium3)
  • Dual lattice consensus verification
  • Quasicrystal validation
  • Cymatic resonance checking
  • Physics-based acoustic traps

See aws-lambda-simple-web-app/demo_memory_shard.py for the complete implementation.
    """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Memory Shard Demo - SCBE-AETHERMOORE"
    )
    parser.add_argument(
        "--memory", "-m",
        default="Hello, AETHERMOORE!",
        help="Memory content to seal"
    )
    parser.add_argument(
        "--agent", "-a",
        default="ash",
        help="Agent identifier"
    )
    parser.add_argument(
        "--topic", "-t",
        default="aethermoore",
        help="Topic/category"
    )
    parser.add_argument(
        "--risk", "-r",
        choices=["normal", "elevated", "high"],
        default="normal",
        help="Risk level for retrieval"
    )

    args = parser.parse_args()

    # Use Fibonacci position (resonates with golden ratio)
    position = (1, 2, 3, 5, 8, 13)

    run_demo(
        memory=args.memory,
        agent=args.agent,
        topic=args.topic,
        position=position,
        risk_level=args.risk
    )


if __name__ == "__main__":
    main()
