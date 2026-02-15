"""
SCBE Patrol/Wall Input Validation for Physics Simulation Core

Patrol: Checks inputs before they reach the engine, flags non-physical parameters.
Wall: Hard denial for parameters that would produce nonsensical or dangerous results.

Tongue classification: primary RU (established knowledge), secondary CA (computation),
                       tertiary KO (binding math to reality).

Compatible with SCBE-AETHERMOORE Layer 13 decision pattern (ALLOW / WARN / DENY).
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from .core import C  # speed of light


# =============================================================================
# DECISION OUTCOMES (matches Layer 13 pattern)
# =============================================================================

class Decision(Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


@dataclass
class ValidationResult:
    """Result of a patrol/wall check on simulation parameters."""
    decision: Decision
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.decision != Decision.DENY


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
        ValidationResult with decision (ALLOW / WARN / DENY) and details.
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

    response_body = {
        'simulation_type': simulation_type,
        'input_parameters': params,
        'results': sim_results,
        'validation': {
            'decision': result.decision.value,
            'warnings': result.warnings,
        },
    }

    return {
        'statusCode': 200,
        'body': json.dumps(response_body, indent=2)
    }
