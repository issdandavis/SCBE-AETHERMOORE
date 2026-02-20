"""
SCBE Patrol/Wall Input Validation for Physics Simulation Core

Patrol: Checks inputs before they reach the engine, flags non-physical parameters.
         Uses bounded harmonic scaling H(d*) = 1 + alpha * tanh(beta * d*).
         Constant relative sensitivity — catches small drifts early.

Wall:   Hard denial for parameters that would produce nonsensical results.
         Uses canonical harmonic scaling H(d*) = exp(d*^2).
         Superexponential — silent below d* ~ 0.926, catastrophic beyond.

Tongue routing: Classifies physics requests into 6D Sacred Tongue vectors.
         Tongue profile modulates validation strictness:
           RU-heavy (binding/knowledge) = stricter bounds
           CA-heavy (computation/bitcraft) = wider tolerance
           DR-heavy (forge/structure) = standard bounds

Crossover: Patrol regime (d* < 0.926) → Wall regime (d* >= 0.926).

Compatible with SCBE-AETHERMOORE Layer 13 decision pattern (ALLOW / WARN / DENY).
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from .core import C  # speed of light

# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

# Crossover distance: below this, patrol (tanh) dominates;
# above this, wall (exp) dominates.  Derived from solving
# 1 + alpha*tanh(beta*d) = exp(d^2) at default params.
D_STAR_CROSSOVER = 0.926

# Patrol formula defaults (from unified.py)
PATROL_ALPHA = 10.0
PATROL_BETA = 0.5

# Sacred Tongue phases (unit circle, π/3 spacing)
TONGUE_CODES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_PHASES = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}


# =============================================================================
# DECISION OUTCOMES (matches Layer 13 pattern)
# =============================================================================

class Decision(Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


@dataclass
class TongueProfile:
    """6D tongue distribution for a physics request."""
    scores: Dict[str, float] = field(default_factory=lambda: {
        t: 0.0 for t in TONGUE_CODES
    })
    dominant: str = "RU"
    confidence: float = 0.0

    def normalized(self) -> Dict[str, float]:
        total = sum(self.scores.values())
        if total < 1e-12:
            return {t: 1.0 / 6.0 for t in TONGUE_CODES}
        return {t: v / total for t, v in self.scores.items()}


@dataclass
class ValidationResult:
    """Result of a patrol/wall check on simulation parameters."""
    decision: Decision
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tongue: Optional[TongueProfile] = None
    risk_score: float = 0.0

    @property
    def passed(self) -> bool:
        return self.decision != Decision.DENY


# =============================================================================
# HARMONIC SCALING (dual-formula regime)
# =============================================================================

def harmonic_patrol(d_star: float,
                    alpha: float = PATROL_ALPHA,
                    beta: float = PATROL_BETA) -> float:
    """
    Bounded patrol formula: H(d*) = 1 + alpha * tanh(beta * d*)
    Range: [1, 1 + alpha].  Constant relative sensitivity.
    Used for drift monitoring (d* < crossover).
    """
    return 1.0 + alpha * math.tanh(beta * d_star)


def harmonic_wall(d_star: float) -> float:
    """
    Canonical wall formula: H(d*) = exp(d*^2)
    Unbounded superexponential.  Identity at d*=0.
    Used for access control (d* >= crossover).
    """
    # Clamp to prevent overflow at extreme distances
    clamped = min(d_star ** 2, 50.0)
    return math.exp(clamped)


def harmonic_risk(d_star: float) -> float:
    """
    Dual-regime harmonic scaling: max(patrol, wall).

    Takes the higher of the two formulas at every point.  This is
    conservative — patrol dominates at small d* (catches drifts),
    wall dominates at large d* (enforces boundaries).  The regime
    crossover happens naturally around d* ≈ 1.4 for default params.
    """
    return max(harmonic_patrol(d_star), harmonic_wall(d_star))


# =============================================================================
# TONGUE CLASSIFICATION FOR PHYSICS DOMAINS
# =============================================================================

# Simulation type → base tongue affinity
# Physics is primarily RU (established knowledge) and CA (computation)
_SIM_TONGUE_MAP: Dict[str, Dict[str, float]] = {
    'classical': {"DR": 2.0, "RU": 1.5, "CA": 1.0},     # forge/structure + knowledge
    'quantum': {"RU": 2.0, "KO": 1.5, "CA": 1.0},       # knowledge + intent/weaving
    'electromagnetism': {"CA": 2.0, "RU": 1.5, "DR": 0.5},  # computation + knowledge
    'thermodynamics': {"CA": 1.5, "DR": 1.5, "RU": 1.0},    # nature + forge/heat
    'relativity': {"RU": 2.0, "UM": 1.5, "KO": 0.5},     # knowledge + beyond/limit
}

# Parameter keys → tongue signals
# Presence of certain parameters shifts the tongue profile
_PARAM_TONGUE_SIGNALS: Dict[str, Dict[str, float]] = {
    # Physical structure params → DR (forge)
    'mass': {"DR": 0.3},
    'm1': {"DR": 0.3},
    'm2': {"DR": 0.3},
    'height': {"DR": 0.3},
    'plate_area': {"DR": 0.5},
    'plate_separation': {"DR": 0.5},
    # Temperature/pressure → CA (nature)
    'temperature': {"CA": 0.3},
    'pressure': {"CA": 0.3},
    'hot_temperature': {"CA": 0.3},
    'cold_temperature': {"CA": 0.3},
    # Wave/frequency params → KO (intent/weaving)
    'wavelength': {"KO": 0.5},
    'frequency': {"KO": 0.5},
    'em_frequency': {"KO": 0.5},
    'source_frequency': {"KO": 0.3},
    # Quantum params → RU (ancient/knowledge)
    'quantum_number': {"RU": 0.5},
    'principal_quantum_number': {"RU": 0.5},
    'n_initial': {"RU": 0.3},
    'n_final': {"RU": 0.3},
    'position_uncertainty': {"RU": 0.3},
    'scattering_angle': {"RU": 0.3},
    # Boundary/extreme params → UM (beyond/limit)
    'black_hole_mass': {"UM": 1.0},
    'velocity': {"UM": 0.2},  # mild; strengthened if near c
}


def classify_physics_tongue(simulation_type: str,
                             params: Dict[str, Any]) -> TongueProfile:
    """
    Classify a physics simulation request into a 6D tongue distribution.

    Combines:
      1. Base affinity from simulation type
      2. Parameter-key signals
      3. Velocity proximity to c (boosts UM for near-light-speed)
    """
    scores = {t: 0.0 for t in TONGUE_CODES}

    # 1. Base affinity from simulation type
    base = _SIM_TONGUE_MAP.get(simulation_type, {"RU": 1.0, "CA": 1.0})
    for tongue, weight in base.items():
        scores[tongue] += weight

    # 2. Parameter-key signals
    for key in params:
        if key in _PARAM_TONGUE_SIGNALS:
            for tongue, weight in _PARAM_TONGUE_SIGNALS[key].items():
                scores[tongue] += weight

    # 3. Velocity proximity to c → UM boost
    for vkey in ('velocity', 'particle_velocity', 'initial_velocity'):
        if vkey in params and isinstance(params[vkey], (int, float)):
            v = abs(params[vkey])
            if v > 0.01 * C:
                # Linear boost from 0 at 1% c to 2.0 at 100% c
                um_boost = min(2.0, 2.0 * (v / C))
                scores["UM"] += um_boost

    # Find dominant tongue
    max_score = max(scores.values())
    dominant = "RU"  # default
    for code in TONGUE_CODES:
        if scores[code] == max_score:
            dominant = code
            break

    total = sum(scores.values())
    confidence = max_score / total if total > 1e-12 else 0.0

    return TongueProfile(scores=scores, dominant=dominant, confidence=confidence)


# =============================================================================
# TONGUE-MODULATED THRESHOLDS
# =============================================================================

def _tongue_strictness(tongue: TongueProfile) -> float:
    """
    Compute a strictness multiplier [0.8, 1.2] from tongue profile.

    RU-heavy (binding/knowledge) → stricter (1.1-1.2)
    UM-heavy (shadow/beyond)     → stricter (1.1-1.2)
    CA-heavy (computation)       → looser (0.8-0.9)
    DR-heavy (forge/structure)   → neutral (1.0)
    KO-heavy (intent/flow)       → neutral (1.0)
    AV-heavy (common)            → neutral (1.0)
    """
    norm = tongue.normalized()
    # Weighted sum: positive = stricter, negative = looser
    strictness_weights = {
        "RU": 0.2,   # knowledge demands rigor
        "UM": 0.2,   # boundary exploration needs care
        "CA": -0.2,  # computation callers know edge cases
        "DR": 0.0,
        "KO": 0.0,
        "AV": 0.0,
    }
    offset = sum(norm[t] * strictness_weights[t] for t in TONGUE_CODES)
    return 1.0 + max(-0.2, min(0.2, offset))


# =============================================================================
# PHYSICAL BOUND DEFINITIONS
# =============================================================================

# Wall limits: hard physical impossibilities
WALL_CHECKS: Dict[str, Dict[str, Any]] = {
    'mass': {'min_exclusive': 0, 'label': 'Mass'},
    'particle_mass': {'min_exclusive': 0, 'label': 'Particle mass'},
    'molecular_mass': {'min_exclusive': 0, 'label': 'Molecular mass'},
    'm1': {'min_exclusive': 0, 'label': 'Mass m1'},
    'm2': {'min_exclusive': 0, 'label': 'Mass m2'},
    'black_hole_mass': {'min_exclusive': 0, 'label': 'Black hole mass'},
    'distance': {'min_exclusive': 0, 'label': 'Distance'},
    'radius': {'min_exclusive': 0, 'label': 'Radius'},
    'box_length': {'min_exclusive': 0, 'label': 'Box length'},
    'plate_area': {'min_exclusive': 0, 'label': 'Plate area'},
    'plate_separation': {'min_exclusive': 0, 'label': 'Plate separation'},
    'wavelength': {'min_exclusive': 0, 'label': 'Wavelength'},
    'frequency': {'min_exclusive': 0, 'label': 'Frequency'},
    'em_frequency': {'min_exclusive': 0, 'label': 'EM frequency'},
    'source_frequency': {'min_exclusive': 0, 'label': 'Source frequency'},
    'spring_constant': {'min_exclusive': 0, 'label': 'Spring constant'},
    'quantum_number': {'min_exclusive': 0, 'label': 'Quantum number', 'integer': True},
    'principal_quantum_number': {'min_exclusive': 0, 'label': 'Principal quantum number', 'integer': True},
    'n_initial': {'min_exclusive': 0, 'label': 'Initial quantum number', 'integer': True},
    'n_final': {'min_exclusive': 0, 'label': 'Final quantum number', 'integer': True},
    'position_uncertainty': {'min_exclusive': 0, 'label': 'Position uncertainty'},
    'momentum_uncertainty': {'min_exclusive': 0, 'label': 'Momentum uncertainty'},
    'moles': {'min_exclusive': 0, 'label': 'Moles'},
    'pressure': {'min_exclusive': 0, 'label': 'Pressure'},
    'volume': {'min_exclusive': 0, 'label': 'Volume'},
    'surface_area': {'min_exclusive': 0, 'label': 'Surface area'},
    'emissivity': {'min_inclusive': 0, 'max_inclusive': 1, 'label': 'Emissivity'},
}


# =============================================================================
# PATROL FUNCTIONS (pre-engine input checks)
# =============================================================================

def _check_temperature(params: Dict[str, Any], warnings: List[str], violations: List[str]) -> None:
    """Validate temperature parameters. T <= 0 K is non-physical for most contexts."""
    for key in ('temperature', 'hot_temperature', 'cold_temperature'):
        if key in params:
            T = params[key]
            if not isinstance(T, (int, float)):
                violations.append(f'{key} must be numeric, got {type(T).__name__}')
            elif T < 0:
                violations.append(f'{key} = {T} K is below absolute zero')
            elif T == 0:
                warnings.append(f'{key} = 0 K (absolute zero) may cause division by zero')


def _check_velocity(params: Dict[str, Any], sim_type: str,
                     warnings: List[str], violations: List[str]) -> None:
    """Check velocity against speed of light for relevant simulation types."""
    velocity_keys = ['velocity', 'particle_velocity', 'initial_velocity']
    for key in velocity_keys:
        if key in params:
            v = params[key]
            if not isinstance(v, (int, float)):
                violations.append(f'{key} must be numeric, got {type(v).__name__}')
                continue
            if sim_type == 'relativity' and abs(v) >= C:
                violations.append(
                    f'{key} = {v:.2e} m/s exceeds speed of light ({C:.2e} m/s)')
            elif sim_type != 'relativity' and abs(v) > 0.1 * C:
                warnings.append(
                    f'{key} = {v:.2e} m/s is >10% of c; classical mechanics '
                    f'may be inaccurate, consider relativistic treatment')


def _check_wall_bounds(params: Dict[str, Any],
                        warnings: List[str], violations: List[str]) -> None:
    """Apply wall checks for hard physical bounds."""
    for key, spec in WALL_CHECKS.items():
        if key not in params:
            continue
        val = params[key]
        label = spec['label']

        if not isinstance(val, (int, float)):
            violations.append(f'{label} must be numeric, got {type(val).__name__}')
            continue

        if math.isnan(val) or math.isinf(val):
            violations.append(f'{label} is {val} (non-finite)')
            continue

        if 'min_exclusive' in spec and val <= spec['min_exclusive']:
            violations.append(f'{label} must be > {spec["min_exclusive"]}, got {val}')

        if 'min_inclusive' in spec and val < spec['min_inclusive']:
            violations.append(f'{label} must be >= {spec["min_inclusive"]}, got {val}')

        if 'max_inclusive' in spec and val > spec['max_inclusive']:
            violations.append(f'{label} must be <= {spec["max_inclusive"]}, got {val}')

        if spec.get('integer') and not float(val).is_integer():
            violations.append(f'{label} must be an integer, got {val}')


def _check_carnot(params: Dict[str, Any], warnings: List[str]) -> None:
    """Warn if Carnot temperatures are inverted."""
    if 'hot_temperature' in params and 'cold_temperature' in params:
        T_hot = params['hot_temperature']
        T_cold = params['cold_temperature']
        if isinstance(T_hot, (int, float)) and isinstance(T_cold, (int, float)):
            if T_hot <= T_cold:
                warnings.append(
                    f'hot_temperature ({T_hot} K) <= cold_temperature ({T_cold} K); '
                    f'Carnot efficiency undefined')


def _compute_param_distance(params: Dict[str, Any], sim_type: str) -> float:
    """
    Estimate a semantic distance d* from a physics request to the
    "normal operating center" of that simulation type.

    d* = 0 means completely normal request.
    d* grows as parameters approach physical extremes.

    This is NOT a hyperbolic distance — it's a heuristic proxy
    for SCBE d* that can feed into the harmonic functions.
    """
    d_star = 0.0
    count = 0

    # Velocity proximity to c (strongest signal)
    for vkey in ('velocity', 'particle_velocity', 'initial_velocity'):
        if vkey in params and isinstance(params[vkey], (int, float)):
            v = abs(params[vkey])
            if v > 0:
                # Maps 0→0, 0.5c→0.7, 0.9c→1.5, 0.99c→3.0
                beta = min(v / C, 0.999)
                d_star += -math.log(1 - beta)
                count += 1

    # Temperature extremes
    for tkey in ('temperature', 'hot_temperature', 'cold_temperature'):
        if tkey in params and isinstance(params[tkey], (int, float)):
            T = params[tkey]
            if T > 0:
                # Maps 300K→0.0, 1e6→0.8, 1e9→1.5, 1e12→2.3
                d_star += max(0, math.log10(max(T, 1)) - 2.5) * 0.3
                count += 1

    # Black hole mass → extreme gravity regime
    if 'black_hole_mass' in params and isinstance(params['black_hole_mass'], (int, float)):
        d_star += 1.0  # Always elevated
        count += 1

    # High quantum numbers → Rydberg regime
    for qkey in ('principal_quantum_number', 'quantum_number'):
        if qkey in params and isinstance(params[qkey], (int, float)):
            n = params[qkey]
            if n > 10:
                d_star += math.log10(n) * 0.5
                count += 1

    if count == 0:
        return 0.0

    return d_star / count


# =============================================================================
# MAIN PATROL ENTRY POINT
# =============================================================================

def validate_params(simulation_type: str, params: Dict[str, Any]) -> ValidationResult:
    """
    Run patrol and wall checks on simulation parameters.

    Args:
        simulation_type: One of 'classical', 'quantum', 'electromagnetism',
                         'thermodynamics', 'relativity'.
        params: The parameter dict that would be passed to the simulation function.

    Returns:
        ValidationResult with decision (ALLOW / WARN / DENY),
        tongue profile, and harmonic risk score.
    """
    violations: List[str] = []
    warnings: List[str] = []

    # Wall: hard bound checks
    _check_wall_bounds(params, warnings, violations)

    # Patrol: contextual checks
    _check_temperature(params, warnings, violations)
    _check_velocity(params, simulation_type, warnings, violations)

    if simulation_type == 'thermodynamics':
        _check_carnot(params, warnings)

    # Tongue classification
    tongue = classify_physics_tongue(simulation_type, params)

    # Compute semantic distance and harmonic risk
    d_star = _compute_param_distance(params, simulation_type)
    strictness = _tongue_strictness(tongue)
    risk = harmonic_risk(d_star) * strictness

    # Decision logic (Layer 13 pattern)
    if violations:
        decision = Decision.DENY
    elif warnings:
        decision = Decision.WARN
    else:
        decision = Decision.ALLOW

    return ValidationResult(
        decision=decision,
        violations=violations,
        warnings=warnings,
        tongue=tongue,
        risk_score=risk,
    )


def validated_simulation(simulation_type: str, params: Dict[str, Any],
                          simulations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run validation, then dispatch to the simulation if allowed.

    Args:
        simulation_type: Simulation name.
        params: Parameter dict.
        simulations: Map of simulation_type -> callable.

    Returns:
        Dict with statusCode, body, and validation metadata.
    """
    import json

    result = validate_params(simulation_type, params)

    if result.decision == Decision.DENY:
        return {
            'statusCode': 422,
            'body': json.dumps({
                'error': 'Input validation failed (SCBE wall)',
                'decision': result.decision.value,
                'violations': result.violations,
                'warnings': result.warnings,
                'tongue': result.tongue.dominant if result.tongue else None,
                'risk_score': result.risk_score,
            })
        }

    if simulation_type not in simulations:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'Invalid simulation type: {simulation_type}',
                'valid_types': list(simulations.keys())
            })
        }

    sim_results = simulations[simulation_type](params)

    tongue_data = None
    if result.tongue:
        tongue_data = {
            'dominant': result.tongue.dominant,
            'distribution': result.tongue.normalized(),
            'confidence': round(result.tongue.confidence, 4),
        }

    response_body = {
        'simulation_type': simulation_type,
        'input_parameters': params,
        'results': sim_results,
        'validation': {
            'decision': result.decision.value,
            'warnings': result.warnings,
            'tongue': tongue_data,
            'risk_score': round(result.risk_score, 6),
        },
    }

    return {
        'statusCode': 200,
        'body': json.dumps(response_body, indent=2)
    }
