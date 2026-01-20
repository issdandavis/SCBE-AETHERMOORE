"""
Constant 4: Stellar-to-Human Octave Mapping
f_human = f_stellar × 2^n

Author: Isaac Davis (@issdandavis)
Date: January 19, 2026
Patent: USPTO #63/961,403

Application: Stellar Pulse Protocol for spacecraft entropy regulation
Transposes stellar frequencies to audible range via octave doubling
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class OctaveTranspositionResult:
    """Result of octave transposition"""
    stellar_freq: float
    target_freq: float
    octaves: int
    human_freq: float
    period_stellar: float
    period_human: float
    period_ratio: float


class StellarOctaveMapping:
    """
    Constant 4: Stellar-to-Human Octave Mapping
    
    Framework: Transpose stellar frequencies to audible range via octave doubling
    
    Formula: f_human = f_stellar × 2^n
    where n ≈ 16 for Middle C (262 Hz) from Sun's 3 mHz
    
    Key Properties:
    - Octave doubling: Each octave doubles frequency (2^n)
    - Stellar alignment: Matches stellar p-mode oscillations
    - Audible range: Transposes to 20 Hz - 20 kHz
    - Entropy regulation: Enables resonant pulsing for spacecraft
    
    Applications:
    - Spacecraft harmonics for stellar wind interaction
    - Entropy regulation via resonant pulsing
    - Stellar camouflage (matching p-mode frequencies)
    - Bio-acoustics and exoplanet detection
    
    Example:
        >>> som = StellarOctaveMapping()
        >>> result = som.transpose(f_stellar=0.003, target_freq=262.0)
        >>> print(f"Sun (3 mHz) → {result.octaves} octaves → {result.human_freq:.2f} Hz")
        Sun (3 mHz) → 16 octaves → 196.61 Hz
    """
    
    # Stellar oscillation frequencies (mHz)
    STELLAR_FREQUENCIES = {
        'sun_p_mode': 0.003,      # 3 mHz (5-minute oscillation)
        'sun_g_mode': 0.0001,     # 0.1 mHz (low-frequency)
        'red_giant': 0.00005,     # 0.05 mHz
        'white_dwarf': 0.001,     # 1 mHz
        'neutron_star': 100.0,    # 100 Hz (pulsars)
    }
    
    # Audible range (Hz)
    AUDIBLE_MIN = 20.0
    AUDIBLE_MAX = 20000.0
    
    # Musical notes (Hz)
    MUSICAL_NOTES = {
        'C4': 261.63,  # Middle C
        'A4': 440.0,   # Concert A
        'C3': 130.81,
        'C5': 523.25,
    }
    
    def __init__(self):
        """Initialize Stellar Octave Mapping"""
        pass
    
    def transpose(self, f_stellar: float, 
                 target_freq: Optional[float] = None) -> OctaveTranspositionResult:
        """
        Transpose stellar frequency to human audible range
        
        Args:
            f_stellar: Stellar frequency (Hz or mHz)
            target_freq: Target frequency (Hz), if None uses audible range center
        
        Returns:
            OctaveTranspositionResult with transposition details
        """
        if f_stellar <= 0:
            raise ValueError("Stellar frequency must be > 0")
        
        # If no target specified, aim for middle of audible range
        if target_freq is None:
            target_freq = np.sqrt(self.AUDIBLE_MIN * self.AUDIBLE_MAX)  # Geometric mean
        
        # Compute octaves needed: n = log2(target / stellar)
        n_exact = np.log2(target_freq / f_stellar)
        n_rounded = round(n_exact)
        
        # Compute actual human frequency
        f_human = f_stellar * (2 ** n_rounded)
        
        # Compute periods
        period_stellar = 1.0 / f_stellar
        period_human = 1.0 / f_human
        period_ratio = period_stellar / period_human
        
        return OctaveTranspositionResult(
            stellar_freq=f_stellar,
            target_freq=target_freq,
            octaves=n_rounded,
            human_freq=f_human,
            period_stellar=period_stellar,
            period_human=period_human,
            period_ratio=period_ratio
        )
    
    def transpose_to_note(self, f_stellar: float, 
                         note: str = 'C4') -> OctaveTranspositionResult:
        """
        Transpose stellar frequency to specific musical note
        
        Args:
            f_stellar: Stellar frequency (Hz or mHz)
            note: Musical note (e.g., 'C4', 'A4')
        
        Returns:
            OctaveTranspositionResult
        """
        if note not in self.MUSICAL_NOTES:
            raise ValueError(f"Unknown note: {note}. Valid: {list(self.MUSICAL_NOTES.keys())}")
        
        target_freq = self.MUSICAL_NOTES[note]
        return self.transpose(f_stellar, target_freq)
    
    def is_audible(self, f_human: float) -> bool:
        """
        Check if frequency is in audible range
        
        Args:
            f_human: Human frequency (Hz)
        
        Returns:
            True if in audible range (20 Hz - 20 kHz)
        """
        return self.AUDIBLE_MIN <= f_human <= self.AUDIBLE_MAX
    
    def stellar_pulse_protocol(self, stellar_body: str = 'sun_p_mode') -> dict:
        """
        Generate Stellar Pulse Protocol parameters
        
        Args:
            stellar_body: Stellar body type (e.g., 'sun_p_mode', 'red_giant')
        
        Returns:
            Dictionary with protocol parameters
        """
        if stellar_body not in self.STELLAR_FREQUENCIES:
            raise ValueError(f"Unknown stellar body: {stellar_body}. "
                           f"Valid: {list(self.STELLAR_FREQUENCIES.keys())}")
        
        f_stellar = self.STELLAR_FREQUENCIES[stellar_body]
        result = self.transpose(f_stellar)
        
        # Ensure audible
        if not self.is_audible(result.human_freq):
            # Adjust octaves to bring into audible range
            if result.human_freq < self.AUDIBLE_MIN:
                while result.human_freq < self.AUDIBLE_MIN:
                    result = self.transpose(f_stellar, target_freq=result.human_freq * 2)
            else:
                while result.human_freq > self.AUDIBLE_MAX:
                    result = self.transpose(f_stellar, target_freq=result.human_freq / 2)
        
        return {
            'stellar_body': stellar_body,
            'stellar_freq_mHz': f_stellar * 1000,  # Convert to mHz
            'stellar_period_s': result.period_stellar,
            'octaves': result.octaves,
            'pulse_freq_Hz': result.human_freq,
            'pulse_period_ms': result.period_human * 1000,  # Convert to ms
            'is_audible': self.is_audible(result.human_freq),
            'entropy_regulation_mode': 'resonant_pulsing'
        }
    
    def entropy_regulation_sequence(self, stellar_body: str = 'sun_p_mode',
                                   duration_s: float = 60.0) -> dict:
        """
        Generate entropy regulation pulse sequence
        
        Args:
            stellar_body: Stellar body type
            duration_s: Sequence duration (seconds)
        
        Returns:
            Dictionary with pulse sequence parameters
        """
        protocol = self.stellar_pulse_protocol(stellar_body)
        
        # Compute number of pulses
        pulse_period_s = protocol['pulse_period_ms'] / 1000.0
        num_pulses = int(duration_s / pulse_period_s)
        
        # Generate pulse times
        pulse_times = np.arange(num_pulses) * pulse_period_s
        
        return {
            **protocol,
            'sequence_duration_s': duration_s,
            'num_pulses': num_pulses,
            'pulse_times_s': pulse_times,
            'duty_cycle': 0.5,  # 50% on/off
            'amplitude_modulation': 'sine'  # Smooth envelope
        }
    
    def stellar_camouflage_frequencies(self, stellar_body: str = 'sun_p_mode',
                                      num_harmonics: int = 5) -> List[float]:
        """
        Generate harmonic series for stellar camouflage
        
        Args:
            stellar_body: Stellar body type
            num_harmonics: Number of harmonics to generate
        
        Returns:
            List of harmonic frequencies (Hz)
        """
        f_stellar = self.STELLAR_FREQUENCIES[stellar_body]
        result = self.transpose(f_stellar)
        
        # Generate harmonics: f, 2f, 3f, 4f, ...
        harmonics = [result.human_freq * (i + 1) for i in range(num_harmonics)]
        
        # Filter to audible range
        audible_harmonics = [f for f in harmonics if self.is_audible(f)]
        
        return audible_harmonics
    
    def transposition_table(self, stellar_bodies: Optional[List[str]] = None) -> str:
        """
        Generate transposition table as formatted string
        
        Args:
            stellar_bodies: List of stellar body types (None = all)
        
        Returns:
            Formatted table string
        """
        if stellar_bodies is None:
            stellar_bodies = list(self.STELLAR_FREQUENCIES.keys())
        
        lines = [
            "Stellar-to-Human Octave Mapping",
            "",
            "| Stellar Body | f_stellar (mHz) | Octaves | f_human (Hz) | Audible? |",
            "|--------------|-----------------|---------|--------------|----------|"
        ]
        
        for body in stellar_bodies:
            if body not in self.STELLAR_FREQUENCIES:
                continue
            
            f_stellar = self.STELLAR_FREQUENCIES[body]
            result = self.transpose(f_stellar)
            audible = "✓" if self.is_audible(result.human_freq) else "✗"
            
            lines.append(
                f"| {body:12s} | "
                f"{f_stellar * 1000:15.3f} | "
                f"{result.octaves:7d} | "
                f"{result.human_freq:12.2f} | "
                f"{audible:8s} |"
            )
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return "StellarOctaveMapping()"


def demo():
    """Demonstration of Stellar Octave Mapping"""
    print("=" * 60)
    print("Constant 4: Stellar-to-Human Octave Mapping")
    print("f_human = f_stellar × 2^n")
    print("=" * 60)
    print()
    
    # Create instance
    som = StellarOctaveMapping()
    
    # Transposition table
    print(som.transposition_table())
    print()
    
    # Sun's p-mode example
    print("Sun's p-mode (3 mHz) Transposition:")
    result = som.transpose(f_stellar=0.003, target_freq=262.0)
    print(f"  Stellar Frequency: {result.stellar_freq * 1000:.3f} mHz")
    print(f"  Target Frequency: {result.target_freq:.2f} Hz (Middle C)")
    print(f"  Octaves: {result.octaves}")
    print(f"  Human Frequency: {result.human_freq:.2f} Hz")
    print(f"  Period Ratio: {result.period_ratio:.0f}x")
    print()
    
    # Stellar Pulse Protocol
    print("Stellar Pulse Protocol (Sun):")
    protocol = som.stellar_pulse_protocol('sun_p_mode')
    for key, value in protocol.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    
    # Entropy regulation sequence
    print("Entropy Regulation Sequence (60s):")
    sequence = som.entropy_regulation_sequence('sun_p_mode', duration_s=60.0)
    print(f"  Num Pulses: {sequence['num_pulses']}")
    print(f"  Pulse Frequency: {sequence['pulse_freq_Hz']:.2f} Hz")
    print(f"  Pulse Period: {sequence['pulse_period_ms']:.2f} ms")
    print(f"  Duty Cycle: {sequence['duty_cycle']:.0%}")
    print()
    
    # Stellar camouflage
    print("Stellar Camouflage Harmonics (Sun):")
    harmonics = som.stellar_camouflage_frequencies('sun_p_mode', num_harmonics=5)
    for i, f in enumerate(harmonics, 1):
        print(f"  Harmonic {i}: {f:.2f} Hz")


if __name__ == "__main__":
    demo()
