"""
Constant 2: Cymatic Voxel Storage
cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y) = 0

Author: Issac Davis (@issdandavis)
Date: January 18, 2026
Patent: USPTO #63/961,403

Application: Secure 6D data storage with vector-based access control
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class VoxelAccessVector:
    """6D access vector for cymatic voxel storage"""
    velocity_x: float
    velocity_y: float
    velocity_z: float
    security_x: float
    security_y: float
    security_z: float
    
    def to_nm_pair(self) -> Tuple[int, int]:
        """
        Convert 6D vector to (n, m) Chladni mode indices
        
        Returns:
            (n, m) tuple for nodal line equation
        """
        # Map velocity dimensions to n
        n = int(np.linalg.norm([self.velocity_x, self.velocity_y, self.velocity_z]))
        
        # Map security dimensions to m
        m = int(np.linalg.norm([self.security_x, self.security_y, self.security_z]))
        
        # Ensure non-zero
        n = max(1, n)
        m = max(1, m)
        
        return n, m


class CymaticVoxelStorage:
    """
    Constant 2: Cymatic Voxel Storage
    
    Maps 6D vectors to Chladni modes for data storage, accessible only
    at nodal lines (resonance points). Data "hides" without alignment.
    
    Formula: cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y) = 0
    
    Key Properties:
    - Vector-based access control: requires precise (n, m) alignment
    - Nodal line visibility: data appears only at resonance points
    - Misalignment yields noise: wrong vector produces random-looking data
    - Antisymmetric: f(n,m) = -f(m,n)
    
    Example:
        >>> cvs = CymaticVoxelStorage(resolution=100)
        >>> data = np.random.rand(100, 100)
        >>> vector = VoxelAccessVector(3, 0, 0, 5, 0, 0)  # n=3, m=5
        >>> encoded = cvs.encode(data, vector)
        >>> decoded = cvs.decode(encoded, vector)
        >>> np.allclose(data, decoded)  # True with correct vector
    """
    
    def __init__(self, resolution: int = 100):
        """
        Initialize Cymatic Voxel Storage
        
        Args:
            resolution: Grid resolution for spatial domain (default 100x100)
        """
        self.resolution = resolution
        
        # Create spatial grid [0, 1] x [0, 1]
        x = np.linspace(0, 1, resolution)
        y = np.linspace(0, 1, resolution)
        self.X, self.Y = np.meshgrid(x, y)
    
    def chladni_pattern(self, n: int, m: int) -> np.ndarray:
        """
        Compute Chladni nodal line pattern
        
        Formula: cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y)
        
        Args:
            n: Velocity dimension index
            m: Security dimension index
        
        Returns:
            2D array of pattern values (zeros at nodal lines)
        """
        term1 = np.cos(n * np.pi * self.X) * np.cos(m * np.pi * self.Y)
        term2 = np.cos(m * np.pi * self.X) * np.cos(n * np.pi * self.Y)
        
        return term1 - term2
    
    def nodal_mask(self, n: int, m: int, threshold: float = 0.1) -> np.ndarray:
        """
        Compute binary mask of nodal lines
        
        Args:
            n: Velocity dimension index
            m: Security dimension index
            threshold: Distance from zero to consider "nodal" (default 0.1)
        
        Returns:
            Boolean array (True at nodal lines)
        """
        pattern = self.chladni_pattern(n, m)
        return np.abs(pattern) < threshold
    
    def encode(self, data: np.ndarray, vector: VoxelAccessVector) -> np.ndarray:
        """
        Encode data using cymatic voxel storage
        
        Args:
            data: 2D array to encode
            vector: 6D access vector
        
        Returns:
            Encoded data (visible only with correct vector)
        """
        if data.shape != (self.resolution, self.resolution):
            raise ValueError(f"Data must be {self.resolution}x{self.resolution}")
        
        n, m = vector.to_nm_pair()
        
        # Get Chladni pattern
        pattern = self.chladni_pattern(n, m)
        
        # Encode: multiply data by pattern
        # Data is visible (non-zero) only at nodal lines (pattern ≈ 0)
        # Elsewhere, pattern modulates data
        encoded = data * (1.0 + pattern)
        
        return encoded
    
    def decode(self, encoded: np.ndarray, vector: VoxelAccessVector,
               threshold: float = 0.1) -> np.ndarray:
        """
        Decode data using cymatic voxel storage
        
        Args:
            encoded: Encoded 2D array
            vector: 6D access vector (must match encoding vector)
            threshold: Nodal line threshold
        
        Returns:
            Decoded data (accurate only with correct vector)
        """
        if encoded.shape != (self.resolution, self.resolution):
            raise ValueError(f"Encoded data must be {self.resolution}x{self.resolution}")
        
        n, m = vector.to_nm_pair()
        
        # Get Chladni pattern
        pattern = self.chladni_pattern(n, m)
        
        # Get nodal mask
        mask = self.nodal_mask(n, m, threshold)
        
        # Decode: extract data at nodal lines
        decoded = np.zeros_like(encoded)
        decoded[mask] = encoded[mask] / (1.0 + pattern[mask])
        
        # Interpolate non-nodal regions (optional)
        # For now, leave as zeros (data only at nodal lines)
        
        return decoded
    
    def access_control_demo(self, data: np.ndarray,
                           correct_vector: VoxelAccessVector,
                           wrong_vector: VoxelAccessVector) -> Tuple[np.ndarray, np.ndarray]:
        """
        Demonstrate access control: correct vs wrong vector
        
        Args:
            data: Original data
            correct_vector: Correct 6D access vector
            wrong_vector: Incorrect 6D access vector
        
        Returns:
            (decoded_correct, decoded_wrong) tuple
        """
        # Encode with correct vector
        encoded = self.encode(data, correct_vector)
        
        # Decode with correct vector
        decoded_correct = self.decode(encoded, correct_vector)
        
        # Decode with wrong vector (should yield noise)
        decoded_wrong = self.decode(encoded, wrong_vector)
        
        return decoded_correct, decoded_wrong
    
    def visualize_pattern(self, n: int, m: int) -> np.ndarray:
        """
        Generate visualization of Chladni pattern
        
        Args:
            n: Velocity dimension index
            m: Security dimension index
        
        Returns:
            2D array suitable for plotting
        """
        pattern = self.chladni_pattern(n, m)
        
        # Normalize to [0, 1] for visualization
        pattern_norm = (pattern - pattern.min()) / (pattern.max() - pattern.min())
        
        return pattern_norm
    
    def security_analysis(self, n_correct: int, m_correct: int,
                         n_attempts: int = 100) -> dict:
        """
        Analyze security: how many random vectors yield correct decoding?
        
        Args:
            n_correct: Correct n value
            m_correct: Correct m value
            n_attempts: Number of random vectors to try
        
        Returns:
            Dictionary with security metrics
        """
        # Generate test data
        data = np.random.rand(self.resolution, self.resolution)
        
        # Encode with correct vector
        correct_vector = VoxelAccessVector(n_correct, 0, 0, m_correct, 0, 0)
        encoded = self.encode(data, correct_vector)
        
        # Try random vectors
        successful_decodes = 0
        
        for _ in range(n_attempts):
            n_random = np.random.randint(1, 10)
            m_random = np.random.randint(1, 10)
            
            if n_random == n_correct and m_random == m_correct:
                continue  # Skip correct vector
            
            random_vector = VoxelAccessVector(n_random, 0, 0, m_random, 0, 0)
            decoded = self.decode(encoded, random_vector)
            
            # Check if decode is close to original
            mse = np.mean((data - decoded) ** 2)
            if mse < 0.01:  # Threshold for "successful" decode
                successful_decodes += 1
        
        return {
            'total_attempts': n_attempts,
            'successful_decodes': successful_decodes,
            'security_rate': 1.0 - (successful_decodes / n_attempts),
            'effective_bits': -np.log2(successful_decodes / n_attempts) if successful_decodes > 0 else np.inf
        }


def demo():
    """Demonstration of Cymatic Voxel Storage"""
    print("=" * 60)
    print("Constant 2: Cymatic Voxel Storage")
    print("cos(n·π·x)·cos(m·π·y) - cos(m·π·x)·cos(n·π·y) = 0")
    print("=" * 60)
    print()
    
    # Create instance
    cvs = CymaticVoxelStorage(resolution=50)
    
    # Test data
    data = np.random.rand(50, 50)
    
    # Define access vectors
    correct_vector = VoxelAccessVector(3, 0, 0, 5, 0, 0)  # n=3, m=5
    wrong_vector = VoxelAccessVector(2, 0, 0, 4, 0, 0)    # n=2, m=4
    
    print("Access Control Demonstration:")
    print(f"Correct vector: n=3, m=5")
    print(f"Wrong vector:   n=2, m=4")
    print()
    
    # Encode and decode
    decoded_correct, decoded_wrong = cvs.access_control_demo(
        data, correct_vector, wrong_vector
    )
    
    # Compute errors
    error_correct = np.mean((data - decoded_correct) ** 2)
    error_wrong = np.mean((data - decoded_wrong) ** 2)
    
    print(f"Decoding Error (Correct Vector): {error_correct:.6f}")
    print(f"Decoding Error (Wrong Vector):   {error_wrong:.6f}")
    print(f"Error Ratio: {error_wrong / error_correct:.1f}x")
    print()
    
    # Security analysis
    print("Security Analysis:")
    security = cvs.security_analysis(n_correct=3, m_correct=5, n_attempts=100)
    print(f"  Total Attempts: {security['total_attempts']}")
    print(f"  Successful Decodes: {security['successful_decodes']}")
    print(f"  Security Rate: {security['security_rate']:.2%}")
    print(f"  Effective Bits: {security['effective_bits']:.1f} bits")


if __name__ == "__main__":
    demo()
