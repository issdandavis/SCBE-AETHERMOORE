"""
Hyperbolic Learning With Errors (H-LWE) for 6D vector encryption
Used in Spiralverse inter-agent messaging (Layer 7 + Layer 13)
"""

import numpy as np
from typing import Tuple, Dict

# Constants for LWE parameters (Kyber-like parameters for consistency)
N_DIM = 6 # Dimensions of the vector to encrypt/decrypt
Q = 3329  # Modulo q (prime number)
CHI = 2   # Error distribution bound for small errors

class HyperbolicLWE:
    """
    Implements a simplified LWE scheme adapted for a hyperbolic space,
    used to secure 6D state vectors transmitted between agents.
    """
    def __init__(self, dim: int = N_DIM, q: int = Q, chi: int = CHI):
        self.dim = dim
        self.q = q
        self.chi = chi

    def generate_keypair(self) -> Tuple[Dict, Dict]:
        """Generates a public/secret key pair for H-LWE."""
        # Public key matrix A (n x n)
        A = np.random.randint(0, self.q, size=(self.dim, self.dim))
        # Secret key vector s (1 x n)
        s = np.random.randint(0, self.q, size=self.dim)
        # Error vector e (n x 1)
        e = np.random.randint(-self.chi, self.chi + 1, size=self.dim)
        # Public key vector b = s @ A + e (1 x n)
        b = (s @ A + e) % self.q

        public_key = {'A': A, 'b': b}
        secret_key = {'s': s}
        return public_key, secret_key

    def encrypt_vector(self, vector: np.ndarray, public_key: dict) -> Dict:
        """Encrypt 6D hyperbolic vector using H-LWE."""
        # Validate input vector within Poincaré ball (norm < 1.0)
        if np.linalg.norm(vector) >= 0.999:
            # Note: A hard error here enforces the architectural constraint
            raise ValueError("Vector outside Poincaré ball constraint (norm must be < 1.0)")

        # Random vector r (n x 1)
        r = np.random.randint(0, self.q, size=self.dim)
        # Error vector e1 (n x 1)
        e1 = np.random.randint(-self.chi, self.chi + 1, size=self.dim)
        # Error scalar e2
        e2 = np.random.randint(-self.chi, self.chi + 1)

        # Ciphertext component u = A @ r + e1
        u = (public_key['A'] @ r + e1) % self.q
        # Ciphertext component v = b @ r + e2 + message_vector
        # Quantize vector message into integer space: scale by q/4
        message_scaled = (vector * (self.q // 4)).astype(int)
        v = (public_key['b'] @ r + e2 + message_scaled) % self.q

        return {'u': u.tolist(), 'v': v.tolist()}

    def decrypt_vector(self, ciphertext: dict, secret_key: dict) -> np.ndarray:
        """Decrypt and return 6D vector from ciphertext components."""
        s = secret_key['s']
        u = np.array(ciphertext['u'])
        v = np.array(ciphertext['v'])

        # Decryption calculation: pt = v - s @ u
        pt = (v - s @ u) % self.q

        # De-quantize back to float vector space
        vector = (pt / (self.q // 4)).astype(float)

        return vector

# Quick test to verify module loading and basic functionality
if __name__ == "__main__":
    scheme = HyperbolicLWE()
    public_key, secret_key = scheme.generate_keypair()

    # Example 6D vector within the Poincaré ball
    test_vector = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    print(f"Original Vector: {test_vector}")

    ciphertext = scheme.encrypt_vector(test_vector, public_key)
    print(f"Ciphertext: {ciphertext}")

    decrypted_vector = scheme.decrypt_vector(ciphertext, secret_key)
    print(f"Decrypted Vector: {decrypted_vector}")

    # Verify decryption accuracy (should be very close, small error from quantization)
    difference = np.linalg.norm(test_vector - decrypted_vector)
    print(f"Decryption Error Norm: {difference:.8f}")
