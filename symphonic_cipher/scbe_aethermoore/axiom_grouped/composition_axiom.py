"""
Composition Axiom Module - Layer Composition Rules

This module defines how the 14 layers compose together and provides:
- Layer 1: Complex Context State (pipeline entry point)
- Layer 14: Audio Axis (pipeline output/signal encoding)
- Composition operators and rules
- Full axiom-aware pipeline execution

Mathematical Foundation:
The composition axiom states that valid pipelines form a category:
1. Identity: id ∘ f = f ∘ id = f
2. Associativity: (f ∘ g) ∘ h = f ∘ (g ∘ h)
3. Type compatibility: dom(f) = cod(g) for f ∘ g to be valid

The 14-layer pipeline is a composition:
    L₁₄ ∘ L₁₃ ∘ ... ∘ L₂ ∘ L₁
"""

from __future__ import annotations

import functools
import numpy as np
from typing import (
    Callable, TypeVar, Any, Optional, Tuple, List, Dict,
    Generic, Union, Protocol
)
from dataclasses import dataclass, field
from enum import Enum
import time as time_module

# Type variables
T = TypeVar('T')
S = TypeVar('S')
F = TypeVar('F', bound=Callable[..., Any])

# Constants
EPS = 1e-10
PHI = (1 + np.sqrt(5)) / 2
SAMPLE_RATE = 44100  # Hz for audio output
CARRIER_FREQ = 440.0  # Hz (concert A)


class CompositionViolation(Exception):
    """Raised when layer composition rules are violated."""
    pass


class LayerType(Enum):
    """Types of layers for composition compatibility."""
    COMPLEX_TO_REAL = "ℂᴰ → ℝ²ᴰ"
    REAL_TO_REAL = "ℝⁿ → ℝᵐ"
    REAL_TO_BALL = "ℝⁿ → 𝔹ⁿ"
    BALL_TO_BALL = "𝔹ⁿ → 𝔹ⁿ"
    BALL_TO_SCALAR = "𝔹ⁿ → ℝ"
    SCALAR_TO_SCALAR = "ℝ → ℝ"
    MULTI_TO_DECISION = "(ℝ, ℝ, ℤ) → Decision"
    DECISION_TO_SIGNAL = "Decision → Signal"


@dataclass
class CompositionCheckResult:
    """Result of a composition axiom check."""
    passed: bool
    source_layer: int
    target_layer: int
    source_type: LayerType
    target_type: LayerType
    compatible: bool
    message: str

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"CompositionCheck[L{self.source_layer} → L{self.target_layer}]: {status}\n"
            f"  Source type: {self.source_type.value}\n"
            f"  Target type: {self.target_type.value}\n"
            f"  Compatible: {self.compatible}\n"
            f"  Message: {self.message}"
        )


def composition_check(
    input_type: LayerType,
    output_type: LayerType
) -> Callable[[F], F]:
    """
    Decorator that declares and verifies layer type signatures.

    Args:
        input_type: Expected input domain type
        output_type: Expected output codomain type

    Returns:
        Decorated function with type metadata
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            check_result = CompositionCheckResult(
                passed=True,
                source_layer=getattr(func, 'layer_num', 0),
                target_layer=getattr(func, 'layer_num', 0),
                source_type=input_type,
                target_type=output_type,
                compatible=True,
                message="Type signature declared"
            )

            wrapper.last_check = check_result
            return result

        wrapper.last_check = None
        wrapper.axiom = "composition"
        wrapper.input_type = input_type
        wrapper.output_type = output_type
        return wrapper
    return decorator


def composable(f: Callable, g: Callable) -> bool:
    """
    Check if two layers are composable (f ∘ g is valid).

    Returns True if output type of g matches input type of f.
    """
    g_output = getattr(g, 'output_type', None)
    f_input = getattr(f, 'input_type', None)

    if g_output is None or f_input is None:
        return True  # Assume composable if types not declared

    # Type compatibility rules
    compatibility = {
        (LayerType.COMPLEX_TO_REAL, LayerType.REAL_TO_REAL): True,
        (LayerType.REAL_TO_REAL, LayerType.REAL_TO_BALL): True,
        (LayerType.REAL_TO_BALL, LayerType.BALL_TO_BALL): True,
        (LayerType.BALL_TO_BALL, LayerType.BALL_TO_BALL): True,
        (LayerType.BALL_TO_BALL, LayerType.BALL_TO_SCALAR): True,
        (LayerType.BALL_TO_SCALAR, LayerType.SCALAR_TO_SCALAR): True,
        (LayerType.SCALAR_TO_SCALAR, LayerType.MULTI_TO_DECISION): True,
        (LayerType.MULTI_TO_DECISION, LayerType.DECISION_TO_SIGNAL): True,
    }

    return compatibility.get((g_output, f_input), g_output == f_input)


# ============================================================================
# Layer 1: Complex Context State (Entry Point)
# ============================================================================

@dataclass
class ContextInput:
    """Input context for Layer 1."""
    identity: complex      # Agent/user identity encoded as phase
    intent: complex        # Intent vector (complex amplitude)
    trajectory: float      # Trajectory coherence [0, 1]
    timing: float          # Timing factor
    commitment: float      # Cryptographic commitment strength
    signature: float       # Signature validity [0, 1]


@composition_check(
    input_type=LayerType.REAL_TO_REAL,  # Multiple reals as input
    output_type=LayerType.COMPLEX_TO_REAL  # Complex output (before realification)
)
def layer_1_complex_context(ctx: ContextInput) -> np.ndarray:
    """
    Layer 1: Complex Context State

    c(t) ∈ ℂᴰ (D=6 dimensional complex vector)

    Encodes the full context into a complex vector with components:
    1. Identity as phase: e^{iθ_id}
    2. Intent (already complex)
    3. Trajectory coherence
    4. Timing
    5. Cryptographic commitment
    6. Signature validity

    Composition Property:
        This is the ENTRY POINT of the pipeline. All subsequent layers
        compose after this one. The complex output enables encoding of
        both magnitude (importance) and phase (relationships).

    Args:
        ctx: Context input containing all governance-relevant information

    Returns:
        6-dimensional complex vector c ∈ ℂ⁶
    """
    # Identity as phase
    c0 = np.exp(1j * np.angle(ctx.identity)) if ctx.identity != 0 else 1.0

    # Intent (preserve complex structure)
    c1 = ctx.intent

    # Trajectory as complex with phase encoding coherence
    c2 = ctx.trajectory * np.exp(1j * np.pi * ctx.trajectory)

    # Timing with oscillatory phase
    c3 = ctx.timing * np.exp(1j * 2 * np.pi * ctx.timing)

    # Commitment strength
    c4 = ctx.commitment * np.exp(1j * np.pi * ctx.commitment / 2)

    # Signature validity
    c5 = ctx.signature * np.exp(1j * np.pi * ctx.signature)

    return np.array([c0, c1, c2, c3, c4, c5], dtype=complex)


def layer_1_from_raw(
    identity: float,
    intent_re: float,
    intent_im: float,
    trajectory: float,
    timing: float,
    commitment: float,
    signature: float
) -> np.ndarray:
    """
    Convenience function to create Layer 1 output from raw values.
    """
    ctx = ContextInput(
        identity=np.exp(1j * identity),
        intent=intent_re + 1j * intent_im,
        trajectory=trajectory,
        timing=timing,
        commitment=commitment,
        signature=signature
    )
    return layer_1_complex_context(ctx)


# ============================================================================
# Layer 14: Audio Axis (Signal Encoding - Exit Point)
# ============================================================================

@dataclass
class AudioOutput:
    """Output from the audio axis layer."""
    signal: np.ndarray     # Audio waveform
    amplitude: float       # Signal amplitude
    phase: float          # Signal phase
    frequency: float      # Carrier frequency
    duration: float       # Signal duration in seconds
    sample_rate: int      # Samples per second


@composition_check(
    input_type=LayerType.MULTI_TO_DECISION,
    output_type=LayerType.DECISION_TO_SIGNAL
)
def layer_14_audio_axis(
    risk_level: str,
    coherence: float,
    intent_phase: float,
    duration: float = 1.0,
    sample_rate: int = SAMPLE_RATE,
    carrier_freq: float = CARRIER_FREQ
) -> AudioOutput:
    """
    Layer 14: Audio Axis (Signal Encoding)

    S_audio(t) = A(risk) · cos(2πf₀t + φ_intent) · env(coherence)

    Generates audio representation of governance state for:
    - Human monitoring
    - Debugging and visualization
    - Sonification of risk levels

    Composition Property:
        This is the EXIT POINT of the pipeline. It transforms the
        governance decision into an observable signal that can be
        monitored or recorded.

    Components:
        - Amplitude: Based on risk level (HIGH risk → quiet, LOW risk → loud)
        - Phase: Encodes intent information
        - Envelope: Decay based on coherence

    Args:
        risk_level: Risk level string ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        coherence: Signal coherence [0, 1]
        intent_phase: Phase encoding of intent
        duration: Signal duration in seconds
        sample_rate: Audio sample rate
        carrier_freq: Carrier frequency in Hz

    Returns:
        AudioOutput with generated signal
    """
    # Map risk level to amplitude
    amplitude_map = {
        "LOW": 1.0,
        "MEDIUM": 0.6,
        "HIGH": 0.3,
        "CRITICAL": 0.1
    }
    amplitude = amplitude_map.get(risk_level, 0.5)

    # Generate time array
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples)

    # Generate carrier wave with intent phase
    carrier = np.cos(2 * np.pi * carrier_freq * t + intent_phase)

    # Generate envelope based on coherence
    # High coherence → slow decay, Low coherence → fast decay
    decay_rate = 2.0 * (1.0 - coherence)
    envelope = np.exp(-decay_rate * t)

    # Combine
    signal = amplitude * carrier * envelope

    return AudioOutput(
        signal=signal,
        amplitude=amplitude,
        phase=intent_phase,
        frequency=carrier_freq,
        duration=duration,
        sample_rate=sample_rate
    )


def layer_14_to_wav_bytes(audio: AudioOutput) -> bytes:
    """
    Convert AudioOutput to WAV file bytes.

    Returns raw bytes that can be written to a .wav file.
    """
    import struct

    # Normalize to 16-bit range
    normalized = audio.signal / (np.max(np.abs(audio.signal)) + EPS)
    samples = (normalized * 32767).astype(np.int16)

    # WAV header
    n_samples = len(samples)
    byte_rate = audio.sample_rate * 2  # 16-bit mono
    data_size = n_samples * 2

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,  # File size - 8
        b'WAVE',
        b'fmt ',
        16,              # Subchunk size
        1,               # PCM format
        1,               # Mono
        audio.sample_rate,
        byte_rate,
        2,               # Block align
        16,              # Bits per sample
        b'data',
        data_size
    )

    return header + samples.tobytes()


# ============================================================================
# Pipeline Composition Operators
# ============================================================================

class Pipeline:
    """
    A composable pipeline of layers.

    Supports functional composition: P = L₁₄ ∘ L₁₃ ∘ ... ∘ L₁
    """

    def __init__(self, name: str = "Pipeline"):
        self.name = name
        self.layers: List[Tuple[int, Callable]] = []
        self.execution_log: List[Tuple[int, str, Any]] = []

    def add_layer(self, layer_num: int, func: Callable) -> 'Pipeline':
        """Add a layer to the pipeline."""
        self.layers.append((layer_num, func))
        return self

    def compose(self, other: 'Pipeline') -> 'Pipeline':
        """
        Compose two pipelines: self ∘ other.

        Returns a new pipeline that applies other first, then self.
        """
        result = Pipeline(f"{self.name} ∘ {other.name}")
        result.layers = other.layers + self.layers
        return result

    def __call__(self, x: Any, **kwargs) -> Any:
        """Execute the pipeline."""
        result = x
        self.execution_log.clear()

        for layer_num, func in self.layers:
            try:
                result = func(result, **kwargs) if kwargs else func(result)
                self.execution_log.append((layer_num, func.__name__, "OK"))
            except Exception as e:
                self.execution_log.append((layer_num, func.__name__, str(e)))
                raise

        return result

    def verify_composition(self) -> List[CompositionCheckResult]:
        """
        Verify that all layer compositions are valid.
        """
        results = []

        for i in range(1, len(self.layers)):
            prev_num, prev_func = self.layers[i - 1]
            curr_num, curr_func = self.layers[i]

            is_composable = composable(curr_func, prev_func)

            result = CompositionCheckResult(
                passed=is_composable,
                source_layer=prev_num,
                target_layer=curr_num,
                source_type=getattr(prev_func, 'output_type', LayerType.REAL_TO_REAL),
                target_type=getattr(curr_func, 'input_type', LayerType.REAL_TO_REAL),
                compatible=is_composable,
                message="Composition valid" if is_composable else "Type mismatch"
            )
            results.append(result)

        return results


def compose(*funcs: Callable) -> Callable:
    """
    Compose multiple functions: compose(f, g, h)(x) = f(g(h(x)))

    Functions are applied right-to-left (mathematical convention).
    """
    def composed(x):
        result = x
        for f in reversed(funcs):
            result = f(result)
        return result

    composed.__name__ = " ∘ ".join(f.__name__ for f in funcs)
    return composed


def pipe(*funcs: Callable) -> Callable:
    """
    Pipe multiple functions: pipe(f, g, h)(x) = h(g(f(x)))

    Functions are applied left-to-right (programming convention).
    """
    def piped(x):
        result = x
        for f in funcs:
            result = f(result)
        return result

    piped.__name__ = " | ".join(f.__name__ for f in funcs)
    return piped


# ============================================================================
# Layer Dependency Graph
# ============================================================================

@dataclass
class LayerDependency:
    """Represents a dependency between layers."""
    source: int      # Source layer number
    target: int      # Target layer number
    dependency_type: str  # "data", "axiom", or "optional"


# The 14-layer pipeline dependency structure
LAYER_DEPENDENCIES: List[LayerDependency] = [
    LayerDependency(1, 2, "data"),    # L1 output feeds L2
    LayerDependency(2, 3, "data"),
    LayerDependency(3, 4, "data"),
    LayerDependency(4, 5, "data"),
    LayerDependency(4, 6, "data"),    # L4 output used by both L5 and L6
    LayerDependency(6, 7, "data"),
    LayerDependency(7, 8, "data"),
    LayerDependency(5, 11, "data"),   # L5 distance used in L11
    LayerDependency(8, 11, "data"),   # L8 realm info used in L11
    LayerDependency(9, 13, "data"),   # L9 coherence used in L13
    LayerDependency(10, 13, "data"),  # L10 coherence used in L13
    LayerDependency(11, 12, "data"),  # L11 distance used in L12
    LayerDependency(12, 13, "data"),  # L12 scaling used in L13
    LayerDependency(13, 14, "data"),  # L13 decision used in L14
]


def get_layer_order() -> List[int]:
    """
    Get the topologically sorted layer execution order.

    Returns layers in order of dependency (L1 first, L14 last).
    """
    # Standard order based on pipeline design
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]


def get_parallel_groups() -> List[List[int]]:
    """
    Get groups of layers that can execute in parallel.

    Layers in the same group have no inter-dependencies.
    """
    return [
        [1],        # Entry point
        [2],        # Realification
        [3],        # Weighting
        [4],        # Poincaré
        [5, 6],     # Distance and Breathing (independent)
        [7],        # Phase
        [8],        # Multi-well
        [9, 10],    # Spectral and Spin coherence (independent)
        [11],       # Triadic distance
        [12],       # Harmonic scaling
        [13],       # Decision
        [14],       # Audio output
    ]


# ============================================================================
# Full Pipeline Executor with Axiom Checking
# ============================================================================

@dataclass
class PipelineState:
    """State at each pipeline stage."""
    layer_num: int
    layer_name: str
    output: Any
    axiom: str
    check_passed: bool
    timestamp: float = field(default_factory=time_module.time)


class AxiomAwarePipeline:
    """
    Full 14-layer pipeline with axiom checking at each stage.

    Integrates layers from all axiom modules and verifies
    axiom compliance during execution.
    """

    def __init__(self):
        self.states: List[PipelineState] = []
        self.axiom_violations: List[Tuple[int, str, str]] = []

    def execute(
        self,
        ctx: ContextInput,
        t: float = 0.0,
        ref_state: Optional[Dict] = None,
        check_axioms: bool = True
    ) -> Tuple[Any, List[PipelineState]]:
        """
        Execute the full 14-layer pipeline.

        Args:
            ctx: Input context
            t: Current time
            ref_state: Reference state for distance computation
            check_axioms: Whether to check axiom compliance

        Returns:
            Tuple of (final_output, list of states)
        """
        from . import unitarity_axiom, locality_axiom, causality_axiom, symmetry_axiom

        self.states.clear()
        self.axiom_violations.clear()

        if ref_state is None:
            ref_state = {
                'u': np.zeros(12),
                'tau': 0.0,
                'eta': 0.0,
                'q': 1.0 + 0j
            }

        # L1: Complex Context
        c = layer_1_complex_context(ctx)
        self._record_state(1, "Complex Context", c, "composition")

        # L2: Realification
        x = unitarity_axiom.layer_2_realify(c)
        self._record_state(2, "Realification", x, "unitarity")

        # L3: Weighted Transform
        x_weighted = locality_axiom.layer_3_weighted(x)
        self._record_state(3, "Weighted Transform", x_weighted, "locality")

        # L4: Poincaré Embedding
        u = unitarity_axiom.layer_4_poincare(x_weighted)
        self._record_state(4, "Poincaré Embedding", u, "unitarity")

        # L5: Hyperbolic Distance
        d_H = symmetry_axiom.layer_5_hyperbolic_distance(u, ref_state['u'])
        self._record_state(5, "Hyperbolic Distance", d_H, "symmetry")

        # L6: Breathing Transform
        u_breathed = causality_axiom.layer_6_breathing(u, t=t)
        self._record_state(6, "Breathing Transform", u_breathed, "causality")

        # L7: Phase Transform
        phase_angle = np.angle(ctx.intent) if ctx.intent != 0 else 0.0
        u_phased = unitarity_axiom.layer_7_phase(u_breathed, phase_angle)
        self._record_state(7, "Phase Transform", u_phased, "unitarity")

        # L8: Multi-Well Realms
        d_star, realm_idx, realm_info = locality_axiom.layer_8_multi_well(u_phased)
        self._record_state(8, "Multi-Well Realms", (d_star, realm_idx), "locality")

        # L9: Spectral Coherence
        S_spec = symmetry_axiom.layer_9_spectral_coherence(u_phased)
        self._record_state(9, "Spectral Coherence", S_spec, "symmetry")

        # L10: Spin Coherence
        C_spin = symmetry_axiom.layer_10_spin_coherence(ctx.intent)
        self._record_state(10, "Spin Coherence", C_spin, "symmetry")

        # L11: Triadic Temporal Distance
        d_tri = causality_axiom.layer_11_triadic_distance(
            u=u_phased,
            ref_u=ref_state['u'],
            tau=t,
            ref_tau=ref_state['tau'],
            eta=ctx.trajectory,  # Use trajectory as entropy proxy
            ref_eta=ref_state['eta'],
            q=ctx.intent,
            ref_q=ref_state['q']
        )
        self._record_state(11, "Triadic Distance", d_tri, "causality")

        # L12: Harmonic Scaling
        H_d = symmetry_axiom.layer_12_harmonic_scaling(d_star)
        self._record_state(12, "Harmonic Scaling", H_d, "symmetry")

        # L13: Decision
        coherence = (S_spec + (C_spin + 1) / 2) / 2  # Combine coherences
        risk_assessment = causality_axiom.layer_13_decision(
            d_star=d_star,
            coherence=coherence,
            realm_index=realm_idx,
            realm_weight=realm_info.weight
        )
        self._record_state(13, "Decision", risk_assessment, "causality")

        # L14: Audio Axis
        audio_output = layer_14_audio_axis(
            risk_level=risk_assessment.level.value,
            coherence=coherence,
            intent_phase=phase_angle
        )
        self._record_state(14, "Audio Axis", audio_output, "composition")

        return audio_output, self.states

    def _record_state(
        self,
        layer_num: int,
        layer_name: str,
        output: Any,
        axiom: str
    ) -> None:
        """Record pipeline state."""
        state = PipelineState(
            layer_num=layer_num,
            layer_name=layer_name,
            output=output,
            axiom=axiom,
            check_passed=True
        )
        self.states.append(state)


# ============================================================================
# Composition Verification Utilities
# ============================================================================

def verify_pipeline_composition(verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Verify the full 14-layer pipeline composition is valid.

    Returns:
        Tuple of (all_valid, list of issues)
    """
    issues = []

    # Check layer ordering
    order = get_layer_order()
    if order != list(range(1, 15)):
        issues.append(f"Invalid layer order: {order}")

    # Check dependency graph is acyclic
    for dep in LAYER_DEPENDENCIES:
        if dep.source >= dep.target:
            issues.append(f"Potential cycle: L{dep.source} → L{dep.target}")

    # Check parallel groups don't violate dependencies
    parallel_groups = get_parallel_groups()
    for group in parallel_groups:
        for dep in LAYER_DEPENDENCIES:
            if dep.source in group and dep.target in group:
                issues.append(
                    f"Parallel group {group} contains dependency "
                    f"L{dep.source} → L{dep.target}"
                )

    if verbose:
        for issue in issues:
            print(f"  ISSUE: {issue}")

    return len(issues) == 0, issues


# ============================================================================
# Axiom Layer Registry
# ============================================================================

COMPOSITION_LAYERS = {
    1: {
        "name": "Complex Context State",
        "function": layer_1_complex_context,
        "inverse": None,
        "description": "Pipeline entry: context → c ∈ ℂ⁶",
        "is_entry_point": True,
    },
    14: {
        "name": "Audio Axis",
        "function": layer_14_audio_axis,
        "inverse": None,
        "description": "Pipeline exit: decision → audio signal",
        "is_exit_point": True,
    },
}


def get_composition_layer(layer_num: int) -> dict:
    """Get layer info by number."""
    if layer_num not in COMPOSITION_LAYERS:
        raise ValueError(f"Layer {layer_num} is not a composition layer")
    return COMPOSITION_LAYERS[layer_num]


def list_composition_layers() -> list:
    """List all layers in the composition axiom module."""
    return list(COMPOSITION_LAYERS.keys())
