"""
Spiralverse DSL Type System

Built-in types for the Spiralverse programming language.

@module spiralverse/dsl/types
@version 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import math

# ============================================================================
# Constants
# ============================================================================

PHI = 1.618033988749895
PI = 3.141592653589793
E = 2.718281828459045


# ============================================================================
# Base Type
# ============================================================================

class SpiralverseType:
    """Base class for all Spiralverse types."""

    def __init__(self, type_name: str):
        self.type_name = type_name

    def __repr__(self) -> str:
        return f"<{self.type_name}>"


# ============================================================================
# Numeric Types
# ============================================================================

@dataclass
class NumericType(SpiralverseType):
    """Numeric value (int or float)."""
    value: float
    is_integer: bool = False

    def __init__(self, value: float, is_integer: bool = False):
        super().__init__("Numeric")
        self.value = value
        self.is_integer = is_integer

    def __repr__(self) -> str:
        if self.is_integer:
            return f"{int(self.value)}"
        return f"{self.value}"


# ============================================================================
# Wave Type
# ============================================================================

@dataclass
class WaveType(SpiralverseType):
    """
    Wave represents a signal with phase, amplitude, and frequency.

    Used for harmonic transformations in the Symphonic Cipher.
    """
    phase: float = 0.0       # Phase in radians
    amplitude: float = 1.0   # Amplitude [0, 1]
    frequency: float = 440.0  # Frequency in Hz (default A4)
    harmonics: List[float] = field(default_factory=list)  # Harmonic series

    def __init__(
        self,
        phase: float = 0.0,
        amplitude: float = 1.0,
        frequency: float = 440.0,
        harmonics: Optional[List[float]] = None,
    ):
        super().__init__("Wave")
        self.phase = phase
        self.amplitude = amplitude
        self.frequency = frequency
        self.harmonics = harmonics or [1.0]  # Fundamental only

    def sample(self, t: float) -> float:
        """Sample the wave at time t."""
        result = 0.0
        for i, h_amp in enumerate(self.harmonics, 1):
            result += h_amp * self.amplitude * math.sin(
                2 * PI * self.frequency * i * t + self.phase
            )
        return result

    def transform(self, phase_shift: float = 0.0, amp_scale: float = 1.0) -> "WaveType":
        """Create transformed copy of wave."""
        return WaveType(
            phase=self.phase + phase_shift,
            amplitude=self.amplitude * amp_scale,
            frequency=self.frequency,
            harmonics=self.harmonics.copy(),
        )

    def __repr__(self) -> str:
        return f"Wave(phase={self.phase:.3f}, amp={self.amplitude:.3f}, freq={self.frequency:.1f}Hz)"


# ============================================================================
# Position Type
# ============================================================================

@dataclass
class PositionType(SpiralverseType):
    """
    6D position in Spiralverse coordinate system.

    Maps to Position6D from six_d_navigator.py
    """
    # Physical axes (Poincaré ball)
    axiom: float = 0.0   # X
    flow: float = 0.0    # Y
    glyph: float = 0.0   # Z
    # Operational axes
    oracle: float = 0.0  # V (velocity/certainty)
    charm: float = 0.0   # H (harmony/priority)
    ledger: float = 128  # S (security 0-255)

    def __init__(
        self,
        axiom: float = 0.0,
        flow: float = 0.0,
        glyph: float = 0.0,
        oracle: float = 0.0,
        charm: float = 0.0,
        ledger: float = 128,
    ):
        super().__init__("Position")
        self.axiom = axiom
        self.flow = flow
        self.glyph = glyph
        self.oracle = oracle
        self.charm = charm
        self.ledger = ledger

    @property
    def physical(self) -> tuple:
        """Get physical coordinates."""
        return (self.axiom, self.flow, self.glyph)

    @property
    def operational(self) -> tuple:
        """Get operational coordinates."""
        return (self.oracle, self.charm, self.ledger)

    def distance_to(self, other: "PositionType") -> float:
        """Calculate 6D distance to another position."""
        # Physical: Euclidean (simplified from Poincaré)
        phys_dist = math.sqrt(
            (self.axiom - other.axiom) ** 2 +
            (self.flow - other.flow) ** 2 +
            (self.glyph - other.glyph) ** 2
        )

        # Operational: Normalized Euclidean
        op_dist = math.sqrt(
            (self.oracle - other.oracle) ** 2 +
            (self.charm - other.charm) ** 2 +
            ((self.ledger - other.ledger) / 255.0) ** 2
        )

        return math.sqrt(phys_dist ** 2 + op_dist ** 2)

    def __repr__(self) -> str:
        return (f"Position(axiom={self.axiom:.2f}, flow={self.flow:.2f}, "
                f"glyph={self.glyph:.2f}, oracle={self.oracle:.2f}, "
                f"charm={self.charm:.2f}, ledger={self.ledger:.0f})")


# ============================================================================
# Tongue Type
# ============================================================================

class TongueType(SpiralverseType):
    """
    Sacred Tongue domain identifier.

    One of: KO, AV, RU, CA, UM, DR
    """

    TONGUES = {
        "KO": {"weight": PHI ** 0, "phase": 0.0, "domain": "Light"},
        "AV": {"weight": PHI ** 1, "phase": PI / 3, "domain": "Water"},
        "RU": {"weight": PHI ** 2, "phase": 2 * PI / 3, "domain": "Wood"},
        "CA": {"weight": PHI ** 3, "phase": PI, "domain": "Fire"},
        "UM": {"weight": PHI ** 4, "phase": 4 * PI / 3, "domain": "Earth"},
        "DR": {"weight": PHI ** 5, "phase": 5 * PI / 3, "domain": "Metal"},
    }

    def __init__(self, name: str):
        if name.upper() not in self.TONGUES:
            raise ValueError(f"Unknown tongue: {name}")
        super().__init__("Tongue")
        self.name = name.upper()
        self.weight = self.TONGUES[self.name]["weight"]
        self.phase = self.TONGUES[self.name]["phase"]
        self.domain = self.TONGUES[self.name]["domain"]

    def __repr__(self) -> str:
        return f"Tongue({self.name}, weight={self.weight:.3f})"


# ============================================================================
# Pattern Type
# ============================================================================

@dataclass
class PatternType(SpiralverseType):
    """
    Executable pattern (function) in Spiralverse.

    Patterns transform inputs to outputs within a tongue domain.
    """
    name: str = ""
    tongue: Optional[TongueType] = None
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    body: Any = None  # AST nodes

    def __init__(
        self,
        name: str,
        tongue: Optional[TongueType] = None,
        input_types: Optional[List[str]] = None,
        output_types: Optional[List[str]] = None,
        body: Any = None,
    ):
        super().__init__("Pattern")
        self.name = name
        self.tongue = tongue
        self.input_types = input_types or []
        self.output_types = output_types or []
        self.body = body

    def __repr__(self) -> str:
        tongue_str = f"@{self.tongue.name}" if self.tongue else ""
        return f"Pattern({self.name}{tongue_str})"


# ============================================================================
# Flow Type
# ============================================================================

@dataclass
class FlowType(SpiralverseType):
    """
    Data flow pipeline in Spiralverse.

    Flows connect multiple patterns in sequence.
    """
    name: str = ""
    tongue: Optional[TongueType] = None
    stages: List[PatternType] = field(default_factory=list)

    def __init__(
        self,
        name: str,
        tongue: Optional[TongueType] = None,
        stages: Optional[List[PatternType]] = None,
    ):
        super().__init__("Flow")
        self.name = name
        self.tongue = tongue
        self.stages = stages or []

    def __repr__(self) -> str:
        stages_str = " | ".join(s.name for s in self.stages)
        return f"Flow({self.name}: {stages_str})"


# ============================================================================
# Signal Type
# ============================================================================

@dataclass
class SignalType(SpiralverseType):
    """
    Signal represents a time-series data stream.

    Used for audio processing and spectral analysis.
    """
    samples: List[float] = field(default_factory=list)
    sample_rate: int = 44100
    duration: float = 0.0

    def __init__(
        self,
        samples: Optional[List[float]] = None,
        sample_rate: int = 44100,
    ):
        super().__init__("Signal")
        self.samples = samples or []
        self.sample_rate = sample_rate
        self.duration = len(self.samples) / sample_rate if self.samples else 0.0

    @classmethod
    def from_wave(cls, wave: WaveType, duration: float, sample_rate: int = 44100) -> "SignalType":
        """Generate signal from wave."""
        num_samples = int(duration * sample_rate)
        samples = [
            wave.sample(i / sample_rate)
            for i in range(num_samples)
        ]
        return cls(samples=samples, sample_rate=sample_rate)

    def __repr__(self) -> str:
        return f"Signal({len(self.samples)} samples, {self.duration:.3f}s)"


# ============================================================================
# Vector Type
# ============================================================================

@dataclass
class VectorType(SpiralverseType):
    """
    N-dimensional vector.

    General-purpose vector for mathematical operations.
    """
    values: List[float] = field(default_factory=list)

    def __init__(self, values: Optional[List[float]] = None):
        super().__init__("Vector")
        self.values = values or []

    @property
    def dim(self) -> int:
        """Get vector dimension."""
        return len(self.values)

    def magnitude(self) -> float:
        """Calculate vector magnitude."""
        return math.sqrt(sum(v ** 2 for v in self.values))

    def normalize(self) -> "VectorType":
        """Return normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            return VectorType(self.values.copy())
        return VectorType([v / mag for v in self.values])

    def dot(self, other: "VectorType") -> float:
        """Dot product with another vector."""
        if self.dim != other.dim:
            raise ValueError("Vector dimensions must match")
        return sum(a * b for a, b in zip(self.values, other.values))

    def __add__(self, other: "VectorType") -> "VectorType":
        if self.dim != other.dim:
            raise ValueError("Vector dimensions must match")
        return VectorType([a + b for a, b in zip(self.values, other.values)])

    def __sub__(self, other: "VectorType") -> "VectorType":
        if self.dim != other.dim:
            raise ValueError("Vector dimensions must match")
        return VectorType([a - b for a, b in zip(self.values, other.values)])

    def __mul__(self, scalar: float) -> "VectorType":
        return VectorType([v * scalar for v in self.values])

    def __repr__(self) -> str:
        return f"Vector({self.values})"


# ============================================================================
# Type Registry
# ============================================================================

TYPE_REGISTRY: Dict[str, type] = {
    "Numeric": NumericType,
    "Wave": WaveType,
    "Position": PositionType,
    "Tongue": TongueType,
    "Pattern": PatternType,
    "Flow": FlowType,
    "Signal": SignalType,
    "Vector": VectorType,
}


def get_type(name: str) -> Optional[type]:
    """Get type class by name."""
    return TYPE_REGISTRY.get(name)


def create_value(type_name: str, *args, **kwargs) -> SpiralverseType:
    """Create a value of the specified type."""
    type_class = get_type(type_name)
    if type_class is None:
        raise ValueError(f"Unknown type: {type_name}")
    return type_class(*args, **kwargs)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Base
    "SpiralverseType",
    # Types
    "NumericType",
    "WaveType",
    "PositionType",
    "TongueType",
    "PatternType",
    "FlowType",
    "SignalType",
    "VectorType",
    # Constants
    "PHI",
    "PI",
    "E",
    # Registry
    "TYPE_REGISTRY",
    "get_type",
    "create_value",
]
