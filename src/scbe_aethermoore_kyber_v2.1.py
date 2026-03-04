"""
Kyber v2.1 (ML-KEM-768) integration for SCBE-AETHERMOORE (Layer 13).
"""

import os
from typing import Tuple, Optional, Any

# --- Constants ---
# Use ML-KEM-768 for PQC security level 3
KYBER_ALG_NAME = "ML-KEM-768"
_FORCE_SKIP_LIBOQS = os.getenv("SCBE_FORCE_SKIP_LIBOQS", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

class SCBEKyber:
    """
    Implements PQC key encapsulation/decapsulation using Kyber.
    Used for securing communication channels between clusters (AWS, GCP)
    and agents (Polly Pads).
    """
    def __init__(self):
        self.kem: Optional[Any] = None
        self.public_key: Optional[bytes] = None
        self.secret_key: Optional[bytes] = None
        if _FORCE_SKIP_LIBOQS:
            self.kem = None
            return
        try:
            from oqs import KeyEncapsulation  # local import avoids module import side effects
            self.kem = KeyEncapsulation(KYBER_ALG_NAME)
            print(f"PQC module initialized: {KYBER_ALG_NAME}")
        except BaseException as e:
            print(f"Error initializing Kyber ({KYBER_ALG_NAME}): {e}")
            self.kem = None

    def generate_keypair(self) -> bytes:
        """Generates a new Kyber key pair and stores secret key internally."""
        if self.kem is None:
            raise RuntimeError("Kyber module failed to initialize.")
        self.public_key, self.secret_key = self.kem.generate_keypair()
        return self.public_key

    def encapsulate(self, peer_public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulates a shared secret for a peer."""
        if self.kem is None:
            raise RuntimeError("Kyber module failed to initialize.")
        ciphertext, shared_secret = self.kem.encaps(peer_public_key)
        return ciphertext, shared_secret

    def decapsulate(self, ciphertext: bytes) -> bytes:
        """Decapsulates a ciphertext to retrieve the shared secret."""
        if self.kem is None or self.secret_key is None:
            raise RuntimeError("Kyber module not initialized or missing secret key.")
        return self.kem.decaps(ciphertext)

# Quick test to verify module loading and basic functionality
if __name__ == "__main__":
    try:
        # Generate keys for Alice (initiator)
        alice_kyber = SCBEKyber()
        alice_public_key = alice_kyber.generate_keypair()

        # Generate keys for Bob (receiver)
        bob_kyber = SCBEKyber()
        bob_public_key = bob_kyber.generate_keypair()

        # Alice encapsulates a secret for Bob
        ciphertext, shared_secret_alice = alice_kyber.encapsulate(bob_public_key)

        # Bob decapsulates the shared secret
        shared_secret_bob = bob_kyber.decapsulate(ciphertext)

        # Verify shared secrets match
        if shared_secret_alice == shared_secret_bob:
            print("PQC Kyber Key Exchange Successful!")
        else:
            print("PQC Kyber Key Exchange Failed!")

    except RuntimeError as e:
        print(f"PQC test failed to run: {e}")
