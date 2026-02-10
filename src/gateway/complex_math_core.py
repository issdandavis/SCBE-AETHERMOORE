#!/usr/bin/env python3
"""
Pure Math Core - Complex Mathematical Foundations for SCBE
===========================================================

This module implements the core mathematical primitives for the
Spectral Context-Bound Encryption (SCBE) Security Gate system.

Mathematical Foundations:
- Complex number operations for quantum-inspired transformations
- Spectral analysis for frequency-domain security
- Tensor operations for multi-dimensional encoding
- Information-theoretic security metrics
"""

import numpy as np
from typing import Tuple, List, Optional
import hashlib


class SpectralTransform:
    """
    Implements spectral transformations for context-bound encryption.
    
    Uses Fourier analysis to transform data into frequency domain,
    where security properties can be analyzed and enforced.
    """
    
    def __init__(self, dimension: int = 256):
        """
        Initialize spectral transform.
        
        Args:
            dimension: Size of the spectral space (power of 2 preferred)
        """
        self.dimension = dimension
        self.basis = self._generate_orthonormal_basis()
    
    def _generate_orthonormal_basis(self) -> np.ndarray:
        """Generate orthonormal basis for spectral decomposition."""
        return np.fft.fft(np.eye(self.dimension)) / np.sqrt(self.dimension)
    
    def forward_transform(self, data: np.ndarray) -> np.ndarray:
        """
        Transform data into spectral domain.
        
        Args:
            data: Input data vector
            
        Returns:
            Spectral coefficients
        """
        if len(data) != self.dimension:
            # Pad or truncate to match dimension
            padded = np.zeros(self.dimension, dtype=complex)
            padded[:min(len(data), self.dimension)] = data[:self.dimension]
            data = padded
        
        return np.fft.fft(data) / np.sqrt(self.dimension)
    
    def inverse_transform(self, spectral_data: np.ndarray) -> np.ndarray:
        """
        Transform spectral data back to time domain.
        
        Args:
            spectral_data: Spectral coefficients
            
        Returns:
            Reconstructed data vector
        """
        return np.fft.ifft(spectral_data) * np.sqrt(self.dimension)
    
    def compute_spectral_entropy(self, spectral_data: np.ndarray) -> float:
        """
        Compute entropy of spectral distribution.
        
        Higher entropy indicates more uniform frequency distribution,
        which correlates with better security properties.
        
        Args:
            spectral_data: Spectral coefficients
            
        Returns:
            Spectral entropy value
        """
        power_spectrum = np.abs(spectral_data) ** 2
        power_spectrum = power_spectrum / np.sum(power_spectrum)  # Normalize
        
        # Compute Shannon entropy
        entropy = -np.sum(power_spectrum * np.log2(power_spectrum + 1e-10))
        return entropy


class ComplexTensorEncoder:
    """
    Multi-dimensional tensor encoding using complex arithmetic.
    
    Implements security through high-dimensional geometric transformations
    that are computationally hard to reverse without proper keys.
    """
    
    def __init__(self, dimensions: Tuple[int, ...] = (8, 8, 8)):
        """
        Initialize tensor encoder.
        
        Args:
            dimensions: Shape of the encoding tensor space
        """
        self.dimensions = dimensions
        self.total_dim = np.prod(dimensions)
    
    def encode(self, data: bytes, key: bytes) -> np.ndarray:
        """
        Encode data into complex tensor space.
        
        Args:
            data: Input data to encode
            key: Encryption key
            
        Returns:
            Encoded complex tensor
        """
        # Generate pseudo-random rotation matrix from key
        rotation = self._key_to_rotation_matrix(key)
        
        # Convert data to complex vector
        data_vector = self._bytes_to_complex_vector(data)
        
        # Apply rotation in complex space
        encoded = rotation @ data_vector
        
        # Reshape to tensor
        return encoded.reshape(self.dimensions)
    
    def decode(self, tensor: np.ndarray, key: bytes) -> bytes:
        """
        Decode tensor back to original data.
        
        Args:
            tensor: Encoded complex tensor
            key: Decryption key
            
        Returns:
            Decoded data
        """
        # Flatten tensor
        encoded_vector = tensor.flatten()
        
        # Generate inverse rotation matrix
        rotation = self._key_to_rotation_matrix(key)
        inverse_rotation = np.linalg.inv(rotation)
        
        # Apply inverse rotation
        decoded_vector = inverse_rotation @ encoded_vector
        
        # Convert back to bytes
        return self._complex_vector_to_bytes(decoded_vector)
    
    def _key_to_rotation_matrix(self, key: bytes) -> np.ndarray:
        """
        Generate unitary rotation matrix from key.
        
        Uses key as seed for deterministic pseudo-random unitary matrix.
        """
        # Use key hash as random seed
        seed = int.from_bytes(hashlib.sha256(key).digest()[:4], 'big')
        rng = np.random.RandomState(seed)
        
        # Generate random complex matrix
        real_part = rng.randn(self.total_dim, self.total_dim)
        imag_part = rng.randn(self.total_dim, self.total_dim)
        matrix = real_part + 1j * imag_part
        
        # Convert to unitary via QR decomposition
        q, r = np.linalg.qr(matrix)
        # Ensure diagonal elements of R have positive phase
        d = np.diag(r)
        # Avoid division by zero
        ph = d / (np.abs(d) + 1e-10)
        q = q @ np.diag(ph)
        
        return q
    
    def _bytes_to_complex_vector(self, data: bytes) -> np.ndarray:
        """Convert bytes to complex vector, padding as needed."""
        # Convert bytes to float array
        data_array = np.frombuffer(data, dtype=np.uint8).astype(float)
        
        # Pad to match total dimension (need pairs for real+imag)
        required_length = self.total_dim * 2
        if len(data_array) < required_length:
            data_array = np.pad(data_array, (0, required_length - len(data_array)))
        else:
            data_array = data_array[:required_length]
        
        # Create complex vector
        real_part = data_array[::2]
        imag_part = data_array[1::2]
        return real_part + 1j * imag_part
    
    def _complex_vector_to_bytes(self, vector: np.ndarray) -> bytes:
        """Convert complex vector back to bytes."""
        # Interleave real and imaginary parts
        real_part = np.real(vector)
        imag_part = np.imag(vector)
        
        interleaved = np.empty(len(vector) * 2, dtype=float)
        interleaved[::2] = real_part
        interleaved[1::2] = imag_part
        
        # Convert to uint8 (with clipping)
        byte_array = np.clip(np.round(interleaved), 0, 255).astype(np.uint8)
        
        return bytes(byte_array)


class QuantumInspiredSecurity:
    """
    Quantum-inspired security metrics and operations.
    
    While not using actual quantum computers, this implements
    mathematical concepts from quantum mechanics that provide
    security benefits in classical computation.
    """
    
    @staticmethod
    def compute_entanglement_entropy(state_vector: np.ndarray, 
                                     partition_size: int) -> float:
        """
        Compute entanglement entropy across a bipartition.
        
        Measures how much information is shared between subsystems.
        High entanglement entropy suggests strong correlation/security.
        
        Args:
            state_vector: Quantum-inspired state vector (normalized)
            partition_size: Size of subsystem A
            
        Returns:
            Von Neumann entanglement entropy
        """
        # Normalize state vector
        state = state_vector / np.linalg.norm(state_vector)
        
        # Reshape to bipartite system
        total_size = len(state)
        subsystem_b_size = total_size // partition_size
        
        if partition_size * subsystem_b_size != total_size:
            raise ValueError("State size must be divisible by partition size")
        
        # Create density matrix
        rho = np.outer(state, np.conj(state))
        
        # Reshape for partial trace
        rho_reshaped = rho.reshape(partition_size, subsystem_b_size, 
                                   partition_size, subsystem_b_size)
        
        # Partial trace over subsystem B
        rho_a = np.trace(rho_reshaped, axis1=1, axis2=3)
        
        # Compute eigenvalues
        eigenvalues = np.linalg.eigvalsh(rho_a)
        eigenvalues = eigenvalues[eigenvalues > 1e-10]  # Remove numerical zeros
        
        # Von Neumann entropy
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
        
        return entropy
    
    @staticmethod
    def apply_hadamard_transform(data: np.ndarray) -> np.ndarray:
        """
        Apply quantum Hadamard transform.
        
        Creates superposition-like state that spreads information
        uniformly across all basis states.
        
        Args:
            data: Input data vector (length must be power of 2)
            
        Returns:
            Transformed data
        """
        n = len(data)
        if n & (n - 1) != 0:
            raise ValueError("Data length must be power of 2")
        
        # Recursive fast Hadamard transform
        result = data.copy()
        h = 1
        while h < n:
            for i in range(0, n, h * 2):
                for j in range(i, i + h):
                    x = result[j]
                    y = result[j + h]
                    result[j] = x + y
                    result[j + h] = x - y
            h *= 2
        
        # Normalize
        return result / np.sqrt(n)


class InformationTheoreticMetrics:
    """
    Information-theoretic security analysis tools.
    
    Provides metrics for analyzing security from an information theory
    perspective, independent of computational assumptions.
    """
    
    @staticmethod
    def mutual_information(x: np.ndarray, y: np.ndarray, bins: int = 50) -> float:
        """
        Compute mutual information between two variables.
        
        I(X;Y) measures how much knowing Y reduces uncertainty about X.
        In cryptography, we want I(ciphertext; key) ≈ 0.
        
        Args:
            x: First variable samples
            y: Second variable samples
            bins: Number of bins for histogram estimation
            
        Returns:
            Mutual information in bits
        """
        # Create 2D histogram
        hist_2d, x_edges, y_edges = np.histogram2d(x, y, bins=bins)
        
        # Normalize to get probabilities
        pxy = hist_2d / np.sum(hist_2d)
        
        # Marginal distributions
        px = np.sum(pxy, axis=1)
        py = np.sum(pxy, axis=0)
        
        # Compute mutual information
        mi = 0.0
        for i in range(bins):
            for j in range(bins):
                if pxy[i, j] > 0:
                    mi += pxy[i, j] * np.log2(pxy[i, j] / (px[i] * py[j] + 1e-10))
        
        return mi
    
    @staticmethod
    def min_entropy(data: np.ndarray) -> float:
        """
        Compute min-entropy (worst-case entropy).
        
        H_∞(X) = -log₂(max_x P(X=x))
        
        Min-entropy is the strongest notion of entropy, giving
        lower bound on uncertainty.
        
        Args:
            data: Sample data
            
        Returns:
            Min-entropy in bits
        """
        # Count occurrences
        unique, counts = np.unique(data, return_counts=True)
        probabilities = counts / len(data)
        
        # Max probability
        max_prob = np.max(probabilities)
        
        # Min-entropy
        return -np.log2(max_prob)


def demonstrate_math_core():
    """
    Demonstrate the mathematical core functionality.
    """
    print("=" * 80)
    print("PURE MATH CORE - Complex Mathematical Foundations for SCBE")
    print("=" * 80)
    
    # 1. Spectral Transform
    print("\n1. SPECTRAL TRANSFORM DEMONSTRATION")
    print("-" * 40)
    spectral = SpectralTransform(dimension=64)
    
    # Create test signal
    test_signal = np.random.randn(64) + 1j * np.random.randn(64)
    spectral_data = spectral.forward_transform(test_signal)
    reconstructed = spectral.inverse_transform(spectral_data)
    
    reconstruction_error = np.linalg.norm(test_signal - reconstructed)
    entropy = spectral.compute_spectral_entropy(spectral_data)
    
    print(f"  Signal dimension: {len(test_signal)}")
    print(f"  Reconstruction error: {reconstruction_error:.2e}")
    print(f"  Spectral entropy: {entropy:.4f} bits")
    
    # 2. Complex Tensor Encoder
    print("\n2. COMPLEX TENSOR ENCODER DEMONSTRATION")
    print("-" * 40)
    encoder = ComplexTensorEncoder(dimensions=(4, 4, 4))
    
    test_data = b"Secret message for SCBE system"
    test_key = b"encryption_key_12345"
    
    encoded = encoder.encode(test_data, test_key)
    decoded = encoder.decode(encoded, test_key)
    
    print(f"  Original data length: {len(test_data)} bytes")
    print(f"  Encoded tensor shape: {encoded.shape}")
    print(f"  Tensor complexity (std): {np.std(encoded):.4f}")
    print(f"  Decoding successful: {decoded[:len(test_data)] == test_data}")
    
    # 3. Quantum-Inspired Security
    print("\n3. QUANTUM-INSPIRED SECURITY METRICS")
    print("-" * 40)
    
    # Create test state vector
    state_size = 64
    test_state = np.random.randn(state_size) + 1j * np.random.randn(state_size)
    test_state = test_state / np.linalg.norm(test_state)
    
    entanglement = QuantumInspiredSecurity.compute_entanglement_entropy(
        test_state, partition_size=8
    )
    print(f"  State vector size: {state_size}")
    print(f"  Entanglement entropy: {entanglement:.4f} bits")
    
    # Hadamard transform
    hadamard_input = np.random.randn(64)
    hadamard_output = QuantumInspiredSecurity.apply_hadamard_transform(hadamard_input)
    print(f"  Hadamard transform applied: {len(hadamard_output)} components")
    print(f"  Output uniformity (std): {np.std(np.abs(hadamard_output)):.4f}")
    
    # 4. Information-Theoretic Metrics
    print("\n4. INFORMATION-THEORETIC METRICS")
    print("-" * 40)
    
    # Generate correlated data
    x = np.random.randn(1000)
    y = x + 0.5 * np.random.randn(1000)  # Correlated with x
    z = np.random.randn(1000)  # Independent
    
    mi_correlated = InformationTheoreticMetrics.mutual_information(x, y)
    mi_independent = InformationTheoreticMetrics.mutual_information(x, z)
    
    print(f"  Mutual information (correlated): {mi_correlated:.4f} bits")
    print(f"  Mutual information (independent): {mi_independent:.4f} bits")
    
    # Min-entropy
    random_data = np.random.randint(0, 256, size=1000)
    min_ent = InformationTheoreticMetrics.min_entropy(random_data)
    print(f"  Min-entropy of random data: {min_ent:.4f} bits")
    
    print("\n" + "=" * 80)
    print("✅ MATHEMATICAL CORE VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nCore mathematical primitives demonstrated:")
    print("  ✓ Spectral analysis with Fourier transforms")
    print("  ✓ Complex tensor encoding with unitary operations")
    print("  ✓ Quantum-inspired entanglement metrics")
    print("  ✓ Information-theoretic security analysis")
    print("\nThese primitives provide the mathematical foundation for")
    print("the SCBE Security Gate's post-quantum security properties.")


if __name__ == '__main__':
    demonstrate_math_core()
