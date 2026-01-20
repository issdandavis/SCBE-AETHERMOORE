"""
Horadam/Transcript Test Vectors for SCBE-AETHERMOORE
Implements rigorous cryptographic test vectors per engineering review

Author: Isaac Davis (@issdandavis)
Date: January 19, 2026
Reference: Engineering Review - Priority Fixes 1-5
"""

import hashlib
import hmac
import numpy as np
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class ContextVector:
    """L2 Context Vector Definition (152 bytes total)"""
    client_id: bytes       # 32 bytes - X25519 or ML-KEM public key fingerprint
    node_id: bytes         # 32 bytes - Serving node identity
    policy_epoch: int      # 8 bytes - Monotonic counter
    langues_coords: bytes  # 48 bytes - 6 × 8-byte fixed-point tongue weights
    intent_hash: bytes     # 32 bytes - H(canonicalized intent payload)
    timestamp: int         # 8 bytes - Unix epoch, milliseconds
    
    def serialize(self) -> bytes:
        """Serialize context vector for transcript binding"""
        return (
            self.client_id +
            self.node_id +
            self.policy_epoch.to_bytes(8, 'big') +
            self.langues_coords +
            self.intent_hash +
            self.timestamp.to_bytes(8, 'big')
        )


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract using HMAC-SHA3-256"""
    return hmac.new(salt, ikm, hashlib.sha3_256).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand using HMAC-SHA3-256"""
    output = b''
    counter = 1
    
    while len(output) < length:
        output += hmac.new(prk, output[-32:] + info + bytes([counter]), hashlib.sha3_256).digest()
        counter += 1
    
    return output[:length]


def compute_transcript(ctx: ContextVector, kem_ciphertext: bytes,
                      dsa_public_key: bytes, session_nonce: bytes) -> bytes:
    """
    Compute transcript hash for session binding
    
    transcript = SHA3-256("SCBE-v1-transcript" || ctx || kem_ct || dsa_pk || nonce)
    """
    h = hashlib.sha3_256()
    h.update(b"SCBE-v1-transcript")
    h.update(ctx.serialize())
    h.update(kem_ciphertext)
    h.update(dsa_public_key)
    h.update(session_nonce)
    
    return h.digest()


def derive_session_keys(kem_shared_secret: bytes, classical_shared_secret: bytes,
                       transcript: bytes) -> Tuple[bytes, bytes]:
    """
    Derive session keys from shared secrets and transcript
    
    PRK = HKDF-Extract(salt="SCBE-session-v1", IKM=kem_ss || classical_ss)
    session_keys = HKDF-Expand(PRK, info=transcript, L=64)
    
    Returns: (encrypt_key, mac_key) each 32 bytes
    """
    # Extract
    salt = b"SCBE-session-v1"
    ikm = kem_shared_secret + classical_shared_secret
    prk = hkdf_extract(salt, ikm)
    
    # Expand
    session_keys = hkdf_expand(prk, transcript, 64)
    
    return session_keys[:32], session_keys[32:]


def derive_horadam_seeds(session_prk: bytes, tongue_index: int,
                        session_nonce: bytes) -> Tuple[int, int]:
    """
    Derive Horadam seeds from session secret
    
    (α_i, β_i) = HKDF-Expand(PRK=session_PRK,
                             info="horadam-seed" || tongue_index || nonce,
                             L=16)
    
    Returns: (alpha, beta) as 64-bit integers
    """
    info = b"horadam-seed" + bytes([tongue_index]) + session_nonce
    seed_bytes = hkdf_expand(session_prk, info, 16)
    
    alpha = int.from_bytes(seed_bytes[:8], 'big')
    beta = int.from_bytes(seed_bytes[8:], 'big')
    
    return alpha, beta


def horadam_sequence(alpha: int, beta: int, n: int, mod: int = 2**64) -> int:
    """
    Compute nth term of Horadam sequence
    
    H_0 = α
    H_1 = β
    H_n = H_{n-1} + H_{n-2} mod 2^64
    """
    if n == 0:
        return alpha % mod
    if n == 1:
        return beta % mod
    
    h_prev2 = alpha % mod
    h_prev1 = beta % mod
    
    for _ in range(2, n + 1):
        h_curr = (h_prev1 + h_prev2) % mod
        h_prev2 = h_prev1
        h_prev1 = h_curr
    
    return h_prev1


def compute_drift(h_expected: List[int], h_observed: List[int],
                 phi: float = 1.618033988749895) -> List[float]:
    """
    Compute normalized drift between expected and observed sequences
    
    δ_i(n) = |H_expected(n) - H_observed(n)| / φ^n
    """
    drifts = []
    
    for n, (exp, obs) in enumerate(zip(h_expected, h_observed)):
        if n == 0:
            drifts.append(0.0)
        else:
            delta = abs(exp - obs) / (phi ** n)
            drifts.append(delta)
    
    return drifts


def compute_triadic_invariant(v1: np.ndarray, v2: np.ndarray, v3: np.ndarray) -> float:
    """
    Compute triadic invariant (scalar triple product)
    
    Δ_ijk = det([v_i | v_j | v_k]) = v_i · (v_j × v_k)
    """
    # Normalize vectors to unit sphere
    v1_norm = v1 / (np.linalg.norm(v1) + 1e-10)
    v2_norm = v2 / (np.linalg.norm(v2) + 1e-10)
    v3_norm = v3 / (np.linalg.norm(v3) + 1e-10)
    
    # Scalar triple product
    cross = np.cross(v2_norm, v3_norm)
    delta = np.dot(v1_norm, cross)
    
    return delta


def horadam_to_vector(h_n: int, h_n1: int, h_n2: int, mod: int = 2**21) -> np.ndarray:
    """
    Convert Horadam sequence values to 3D vector
    
    v_i(n) = [H_n mod 2^21, H_{n-1} mod 2^21, H_{n-2} mod 2^21]
    """
    return np.array([
        h_n % mod,
        h_n1 % mod,
        h_n2 % mod
    ], dtype=np.float64)


# ============================================================================
# TEST VECTOR SET 1: CLEAN SEQUENCES (NO DRIFT)
# ============================================================================

def generate_clean_vectors():
    """Generate test vectors with no perturbation (δ=0)"""
    
    # Mock secrets (DO NOT USE IN PRODUCTION)
    mock_secret = b'\x00' * 32
    session_nonce = b'\x01' * 12
    
    # Derive PRK
    salt = b"SCBE-session-v1"
    prk = hkdf_extract(salt, mock_secret)
    
    # 6 tongues (Korean, Avestan, Russian, Catalan, Umbrian, Doric)
    tongue_names = ["KO", "AV", "RU", "CA", "UM", "DR"]
    
    print("=" * 80)
    print("TEST VECTOR SET 1: CLEAN HORADAM SEQUENCES (NO DRIFT)")
    print("=" * 80)
    print(f"Secret: {mock_secret.hex()}")
    print(f"Nonce:  {session_nonce.hex()}")
    print()
    
    print("Tongue | α_i (hex)        | β_i (hex)        | H_0 ... H_5 (hex)")
    print("-" * 80)
    
    sequences = {}
    
    for i, name in enumerate(tongue_names):
        alpha, beta = derive_horadam_seeds(prk, i, session_nonce)
        
        # Compute first 32 terms
        h_values = [horadam_sequence(alpha, beta, n) for n in range(32)]
        sequences[name] = h_values
        
        # Print first 6 terms
        h_str = ", ".join([f"0x{h:x}" for h in h_values[:6]])
        print(f"{name:6s} | 0x{alpha:016x} | 0x{beta:016x} | {h_str}")
    
    print()
    print("Norm δ(n): All 0.0000 (no drift)")
    print()
    
    return sequences


# ============================================================================
# TEST VECTOR SET 2: PERTURBED SEQUENCES (1% START NOISE, SHOWING DRIFT)
# ============================================================================

def generate_perturbed_vectors():
    """Generate test vectors with 1% perturbation showing drift amplification"""
    
    # Mock secrets
    mock_secret = b'\x00' * 32
    session_nonce = b'\x01' * 12
    
    # Derive PRK
    salt = b"SCBE-session-v1"
    prk = hkdf_extract(salt, mock_secret)
    
    tongue_names = ["KO", "AV", "RU", "CA", "UM", "DR"]
    perturbation = 0.01  # 1% noise
    
    print("=" * 80)
    print("TEST VECTOR SET 2: PERTURBED SEQUENCES (1% START NOISE)")
    print("=" * 80)
    print(f"Perturbation: {perturbation * 100}%")
    print()
    
    print("Tongue | δ_0      | δ_1      | δ_2      | δ_5      | δ_10     | δ_20     | δ_31")
    print("-" * 80)
    
    all_drifts = []
    
    for i, name in enumerate(tongue_names):
        alpha, beta = derive_horadam_seeds(prk, i, session_nonce)
        
        # Expected sequence
        h_expected = [horadam_sequence(alpha, beta, n) for n in range(32)]
        
        # Perturbed sequence (1% noise on seeds)
        alpha_perturbed = int(alpha * (1 + perturbation)) % (2**64)
        beta_perturbed = int(beta * (1 + perturbation)) % (2**64)
        h_observed = [horadam_sequence(alpha_perturbed, beta_perturbed, n) for n in range(32)]
        
        # Compute drifts
        drifts = compute_drift(h_expected, h_observed)
        all_drifts.append(drifts)
        
        # Print selected drift values
        print(f"{name:6s} | {drifts[0]:.4e} | {drifts[1]:.4e} | {drifts[2]:.4e} | "
              f"{drifts[5]:.4e} | {drifts[10]:.4e} | {drifts[20]:.4e} | {drifts[31]:.4e}")
    
    # Compute norm of drift vector
    print()
    print("Norm ||δ||:")
    for n in [0, 1, 2, 5, 10, 20, 31]:
        drift_vec = [drifts[n] for drifts in all_drifts]
        norm = np.linalg.norm(drift_vec)
        print(f"  n={n:2d}: {norm:.4e}")
    
    print()
    print("Note: Drifts amplify ~φ^n; by n=31, norms ~10^18 (log to detect early)")
    print()


# ============================================================================
# TEST VECTOR SET 3: TRIADIC INVARIANT (TONGUES 0-2, n=0-5)
# ============================================================================

def generate_triadic_vectors():
    """Generate triadic invariant test vectors"""
    
    # Mock secrets
    mock_secret = b'\x00' * 32
    session_nonce = b'\x01' * 12
    
    # Derive PRK
    salt = b"SCBE-session-v1"
    prk = hkdf_extract(salt, mock_secret)
    
    tongue_names = ["KO", "AV", "RU"]
    perturbation = 0.01
    
    print("=" * 80)
    print("TEST VECTOR SET 3: TRIADIC INVARIANT (TONGUES 0-2)")
    print("=" * 80)
    print()
    
    # Generate sequences for 3 tongues
    sequences_clean = []
    sequences_perturbed = []
    
    for i in range(3):
        alpha, beta = derive_horadam_seeds(prk, i, session_nonce)
        
        # Clean
        h_clean = [horadam_sequence(alpha, beta, n) for n in range(8)]
        sequences_clean.append(h_clean)
        
        # Perturbed
        alpha_p = int(alpha * (1 + perturbation)) % (2**64)
        beta_p = int(beta * (1 + perturbation)) % (2**64)
        h_perturbed = [horadam_sequence(alpha_p, beta_p, n) for n in range(8)]
        sequences_perturbed.append(h_perturbed)
    
    # Compute triadic invariants
    print("n | Δ_012 Clean | Δ_012 Perturbed | |Δ_diff| | Stable (ε=0.1)?")
    print("-" * 80)
    
    delta_clean_prev = 0.0
    delta_perturbed_prev = 0.0
    
    for n in range(3, 8):  # Need n-2, n-1, n for vectors
        # Clean vectors
        v0_clean = horadam_to_vector(sequences_clean[0][n], sequences_clean[0][n-1], sequences_clean[0][n-2])
        v1_clean = horadam_to_vector(sequences_clean[1][n], sequences_clean[1][n-1], sequences_clean[1][n-2])
        v2_clean = horadam_to_vector(sequences_clean[2][n], sequences_clean[2][n-1], sequences_clean[2][n-2])
        
        delta_clean = compute_triadic_invariant(v0_clean, v1_clean, v2_clean)
        
        # Perturbed vectors
        v0_pert = horadam_to_vector(sequences_perturbed[0][n], sequences_perturbed[0][n-1], sequences_perturbed[0][n-2])
        v1_pert = horadam_to_vector(sequences_perturbed[1][n], sequences_perturbed[1][n-1], sequences_perturbed[1][n-2])
        v2_pert = horadam_to_vector(sequences_perturbed[2][n], sequences_perturbed[2][n-1], sequences_perturbed[2][n-2])
        
        delta_perturbed = compute_triadic_invariant(v0_pert, v1_pert, v2_pert)
        
        # Stability check
        if n == 3:
            stable = "N/A (first)"
        else:
            diff_clean = abs(delta_clean - delta_clean_prev)
            diff_perturbed = abs(delta_perturbed - delta_perturbed_prev)
            stable = "Stable" if max(diff_clean, diff_perturbed) < 0.1 else "Unstable"
        
        delta_diff = abs(delta_clean - delta_perturbed)
        
        print(f"{n} | {delta_clean:11.6f} | {delta_perturbed:15.6f} | {delta_diff:9.6f} | {stable}")
        
        delta_clean_prev = delta_clean
        delta_perturbed_prev = delta_perturbed
    
    print()
    print("Stability criterion: |Δ_n - Δ_{n-1}| < ε_Δ = 0.1")
    print()


# ============================================================================
# TEST VECTOR SET 4: CONTEXT VECTOR AND TRANSCRIPT BINDING
# ============================================================================

def generate_transcript_vectors():
    """Generate context vector and transcript binding test vectors"""
    
    print("=" * 80)
    print("TEST VECTOR SET 4: CONTEXT VECTOR AND TRANSCRIPT BINDING")
    print("=" * 80)
    print()
    
    # Create context vector
    ctx = ContextVector(
        client_id=b'\x01' * 32,
        node_id=b'\x02' * 32,
        policy_epoch=1,
        langues_coords=b'\x03' * 48,
        intent_hash=hashlib.sha3_256(b"test intent").digest(),
        timestamp=1737340800000  # 2026-01-20 00:00:00 UTC
    )
    
    # Mock cryptographic materials
    kem_ciphertext = b'\x04' * 1088  # ML-KEM-768 ciphertext size
    dsa_public_key = b'\x05' * 1952  # ML-DSA-65 public key size
    session_nonce = b'\x06' * 12
    
    # Compute transcript
    transcript = compute_transcript(ctx, kem_ciphertext, dsa_public_key, session_nonce)
    
    print("Context Vector:")
    print(f"  client_id:      {ctx.client_id.hex()[:32]}...")
    print(f"  node_id:        {ctx.node_id.hex()[:32]}...")
    print(f"  policy_epoch:   {ctx.policy_epoch}")
    print(f"  langues_coords: {ctx.langues_coords.hex()[:32]}...")
    print(f"  intent_hash:    {ctx.intent_hash.hex()}")
    print(f"  timestamp:      {ctx.timestamp}")
    print()
    
    print("Cryptographic Materials:")
    print(f"  kem_ciphertext: {kem_ciphertext.hex()[:32]}... (1088 bytes)")
    print(f"  dsa_public_key: {dsa_public_key.hex()[:32]}... (1952 bytes)")
    print(f"  session_nonce:  {session_nonce.hex()}")
    print()
    
    print("Transcript Hash:")
    print(f"  {transcript.hex()}")
    print()
    
    # Derive session keys
    kem_shared_secret = b'\x07' * 32
    classical_shared_secret = b'\x08' * 32
    
    encrypt_key, mac_key = derive_session_keys(kem_shared_secret, classical_shared_secret, transcript)
    
    print("Session Keys:")
    print(f"  encrypt_key: {encrypt_key.hex()}")
    print(f"  mac_key:     {mac_key.hex()}")
    print()


def main():
    """Run all test vector generation"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  HORADAM/TRANSCRIPT TEST VECTORS FOR SCBE-AETHERMOORE".center(78) + "║")
    print("║" + "  Engineering Review - Priority Fixes Implementation".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    generate_clean_vectors()
    generate_perturbed_vectors()
    generate_triadic_vectors()
    generate_transcript_vectors()
    
    print("=" * 80)
    print("TEST VECTOR GENERATION COMPLETE")
    print("=" * 80)
    print()
    print("These vectors demonstrate:")
    print("  1. Deterministic Horadam sequence generation from HKDF-derived seeds")
    print("  2. Drift amplification detection (φ^n scaling)")
    print("  3. Triadic invariant stability checking")
    print("  4. Context vector serialization and transcript binding")
    print("  5. Session key derivation from transcript hash")
    print()
    print("Security properties:")
    print("  - Seeds derived from session secret (not predictable)")
    print("  - Transcript binds all session parameters cryptographically")
    print("  - Drift detection is one-way (reveals anomaly, not internal state)")
    print("  - Keys committed to full session context via HKDF")
    print()


if __name__ == "__main__":
    main()
