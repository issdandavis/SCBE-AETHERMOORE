"""
Constant 1: Harmonic Scaling Law
H(d, R) = R^(d²)

Author: Isaac Davis (@issdandavis)
Date: January 18, 2026
Patent: USPTO #63/961,403

Application: Cryptographic security scaling with super-exponential growth
"""

import numpy as np
from typing import Union, List
from dataclasses import dataclass


@dataclass
class HarmonicScalingResult:
    """Result of harmonic scaling computation"""
    dimensions: int
    ratio: float
    scaling_factor: float
    growth_rate: float
    security_bits: float


class HarmonicScalingLaw:
    """
    Constant 1: H(d, R) = R^(d²)
    
    Super-exponential growth from d² exponent, applied to cryptography
    for amplifying security with independent dimensions.
    
    Key Properties:
    - Super-exponential growth: each dimension increase multiplies complexity
    - Harmonic ratios: R based on musical intervals (e.g., 1.5 for perfect fifth)
    - Dimension independence: each dimension contributes multiplicatively
    
    Example:
        >>> hsl = HarmonicScalingLaw(R=1.5)
        >>> result = hsl.compute(d=6)
        >>> print(f"H(6, 1.5) = {result.scaling_factor:,.2f}")
        H(6, 1.5) = 2,184,164.41
    """
    
    # Musical interval ratios (Pythagorean tuning)
    RATIOS = {
        'unison': 1.0,
        'minor_second': 16/15,
        'major_second': 9/8,
        'minor_third': 6/5,
        'major_third': 5/4,
        'perfect_fourth': 4/3,
        'tritone': 45/32,
        'perfect_fifth': 3/2,  # Default
        'minor_sixth': 8/5,
        'major_sixth': 5/3,
        'minor_seventh': 16/9,
        'major_seventh': 15/8,
        'octave': 2.0
    }
    
    def __init__(self, R: float = 1.5):
        """
        Initialize Harmonic Scaling Law
        
        Args:
            R: Harmonic ratio (default 1.5 for perfect fifth)
        """
        if R <= 1.0:
            raise ValueError("R must be > 1.0 for growth")
        
        self.R = R
    
    def compute(self, d: int) -> HarmonicScalingResult:
        """
        Compute H(d, R) = R^(d²)
        
        Args:
            d: Number of dimensions (1-6 typical)
        
        Returns:
            HarmonicScalingResult with scaling factor and metadata
        """
        if d < 1:
            raise ValueError("Dimensions must be >= 1")
        
        # Core formula: H(d, R) = R^(d²)
        exponent = d ** 2
        scaling_factor = self.R ** exponent
        
        # Compute growth rate (ratio to previous dimension)
        if d > 1:
            prev_scaling = self.R ** ((d - 1) ** 2)
            growth_rate = scaling_factor / prev_scaling
        else:
            growth_rate = scaling_factor
        
        # Estimate security bits (log2 of scaling factor)
        security_bits = np.log2(scaling_factor)
        
        return HarmonicScalingResult(
            dimensions=d,
            ratio=self.R,
            scaling_factor=scaling_factor,
            growth_rate=growth_rate,
            security_bits=security_bits
        )
    
    def compute_range(self, d_min: int = 1, d_max: int = 6) -> List[HarmonicScalingResult]:
        """
        Compute scaling factors for range of dimensions
        
        Args:
            d_min: Minimum dimensions
            d_max: Maximum dimensions
        
        Returns:
            List of HarmonicScalingResult for each dimension
        """
        return [self.compute(d) for d in range(d_min, d_max + 1)]
    
    def growth_table(self, d_max: int = 6) -> str:
        """
        Generate growth table as formatted string
        
        Args:
            d_max: Maximum dimensions to display
        
        Returns:
            Formatted table string
        """
        results = self.compute_range(1, d_max)
        
        lines = [
            f"Harmonic Scaling Law: H(d, {self.R}) = {self.R}^(d²)",
            "",
            "| d | d² | H(d, R) | Growth | Security Bits |",
            "|---|----|---------| -------|---------------|"
        ]
        
        for result in results:
            lines.append(
                f"| {result.dimensions} | {result.dimensions**2:2d} | "
                f"{result.scaling_factor:,.2f} | "
                f"{result.growth_rate:.1f}x | "
                f"{result.security_bits:.1f} bits |"
            )
        
        return "\n".join(lines)
    
    def cryptographic_strength(self, d: int, base_bits: int = 128) -> float:
        """
        Compute effective cryptographic strength
        
        Args:
            d: Number of independent security dimensions
            base_bits: Base security level (e.g., 128-bit AES)
        
        Returns:
            Effective security bits after harmonic scaling
        """
        result = self.compute(d)
        
        # Effective bits = base_bits + log2(H(d, R))
        effective_bits = base_bits + result.security_bits
        
        return effective_bits
    
    @classmethod
    def from_interval(cls, interval: str) -> 'HarmonicScalingLaw':
        """
        Create instance from musical interval name
        
        Args:
            interval: Musical interval (e.g., 'perfect_fifth', 'octave')
        
        Returns:
            HarmonicScalingLaw instance with corresponding ratio
        
        Example:
            >>> hsl = HarmonicScalingLaw.from_interval('perfect_fifth')
            >>> hsl.R
            1.5
        """
        if interval not in cls.RATIOS:
            raise ValueError(f"Unknown interval: {interval}. "
                           f"Valid: {list(cls.RATIOS.keys())}")
        
        return cls(R=cls.RATIOS[interval])
    
    def __repr__(self) -> str:
        return f"HarmonicScalingLaw(R={self.R})"


def demo():
    """Demonstration of Harmonic Scaling Law"""
    print("=" * 60)
    print("Constant 1: Harmonic Scaling Law")
    print("H(d, R) = R^(d²)")
    print("=" * 60)
    print()
    
    # Default ratio (perfect fifth)
    hsl = HarmonicScalingLaw(R=1.5)
    print(hsl.growth_table(d_max=6))
    print()
    
    # Cryptographic strength example
    print("Cryptographic Strength Example:")
    print(f"Base: 128-bit AES")
    for d in range(1, 7):
        strength = hsl.cryptographic_strength(d, base_bits=128)
        print(f"  d={d}: {strength:.1f} effective bits")
    print()
    
    # Different intervals
    print("Different Musical Intervals:")
    for interval in ['perfect_fourth', 'perfect_fifth', 'octave']:
        hsl_interval = HarmonicScalingLaw.from_interval(interval)
        result = hsl_interval.compute(d=3)
        print(f"  {interval:20s} (R={hsl_interval.R:.3f}): "
              f"H(3, R) = {result.scaling_factor:,.2f}")


if __name__ == "__main__":
    demo()
