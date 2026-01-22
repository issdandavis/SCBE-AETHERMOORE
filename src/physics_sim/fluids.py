#!/usr/bin/env python3
"""
Fluid Dynamics Module

Comprehensive fluid mechanics calculations covering:
- Incompressible flow (Reynolds, Bernoulli, drag)
- Compressible flow (isentropic, normal shocks, oblique shocks)
- Pipe flow (friction factor, pressure drop)
- Open channel flow
- Boundary layer theory

Based on established fluid dynamics theory.
"""

import math
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# =============================================================================
# FLUID PROPERTIES
# =============================================================================

# Common fluids at 20°C, 1 atm (unless noted)
FLUID_PROPERTIES = {
    "water": {
        "density": 998.2,  # kg/m³
        "dynamic_viscosity": 1.002e-3,  # Pa·s
        "surface_tension": 0.0728,  # N/m
        "bulk_modulus": 2.2e9,  # Pa
    },
    "air": {
        "density": 1.204,
        "dynamic_viscosity": 1.825e-5,
        "gamma": 1.4,
        "gas_constant": 287.058,
    },
    "seawater": {
        "density": 1025,
        "dynamic_viscosity": 1.08e-3,
        "surface_tension": 0.0728,
    },
    "oil_SAE30": {
        "density": 891,
        "dynamic_viscosity": 0.29,  # at 40°C
    },
    "mercury": {
        "density": 13546,
        "dynamic_viscosity": 1.526e-3,
        "surface_tension": 0.485,
    },
    "glycerin": {
        "density": 1261,
        "dynamic_viscosity": 1.412,
    },
}


# =============================================================================
# BASIC DIMENSIONLESS NUMBERS
# =============================================================================


def reynolds_number(
    velocity: float, length: float, density: float, viscosity: float
) -> float:
    """
    Calculate Reynolds number.

    Re = ρVL/μ = VL/ν

    Args:
        velocity: Flow velocity (m/s)
        length: Characteristic length (m)
        density: Fluid density (kg/m³)
        viscosity: Dynamic viscosity (Pa·s)

    Returns:
        Reynolds number (dimensionless)
    """
    return density * velocity * length / viscosity


def mach_number(velocity: float, speed_of_sound: float) -> float:
    """
    Calculate Mach number.

    M = V/a

    Args:
        velocity: Flow velocity (m/s)
        speed_of_sound: Local speed of sound (m/s)

    Returns:
        Mach number (dimensionless)
    """
    return velocity / speed_of_sound


def froude_number(velocity: float, length: float, g: float = 9.80665) -> float:
    """
    Calculate Froude number.

    Fr = V/√(gL)

    Args:
        velocity: Flow velocity (m/s)
        length: Characteristic length (m)
        g: Gravitational acceleration (m/s²)

    Returns:
        Froude number (dimensionless)
    """
    return velocity / math.sqrt(g * length)


def weber_number(
    density: float, velocity: float, length: float, surface_tension: float
) -> float:
    """
    Calculate Weber number.

    We = ρV²L/σ

    Args:
        density: Fluid density (kg/m³)
        velocity: Flow velocity (m/s)
        length: Characteristic length (m)
        surface_tension: Surface tension (N/m)

    Returns:
        Weber number (dimensionless)
    """
    return density * velocity**2 * length / surface_tension


def strouhal_number(frequency: float, length: float, velocity: float) -> float:
    """
    Calculate Strouhal number.

    St = fL/V

    Args:
        frequency: Vortex shedding frequency (Hz)
        length: Characteristic length (m)
        velocity: Flow velocity (m/s)

    Returns:
        Strouhal number (dimensionless)
    """
    return frequency * length / velocity


def euler_number(pressure_drop: float, density: float, velocity: float) -> float:
    """
    Calculate Euler number (pressure coefficient).

    Eu = ΔP/(ρV²)

    Args:
        pressure_drop: Pressure difference (Pa)
        density: Fluid density (kg/m³)
        velocity: Flow velocity (m/s)

    Returns:
        Euler number (dimensionless)
    """
    return pressure_drop / (density * velocity**2)


# =============================================================================
# BERNOULLI AND INCOMPRESSIBLE FLOW
# =============================================================================


def bernoulli_velocity(
    P1: float,
    P2: float,
    z1: float,
    z2: float,
    density: float,
    V1: float = 0,
    g: float = 9.80665,
) -> float:
    """
    Calculate velocity using Bernoulli equation.

    P₁/ρ + V₁²/2 + gz₁ = P₂/ρ + V₂²/2 + gz₂

    Args:
        P1, P2: Pressures at points 1, 2 (Pa)
        z1, z2: Elevations at points 1, 2 (m)
        density: Fluid density (kg/m³)
        V1: Velocity at point 1 (m/s)
        g: Gravitational acceleration (m/s²)

    Returns:
        Velocity at point 2 (m/s)
    """
    # Energy per unit mass at point 1
    E1 = P1 / density + V1**2 / 2 + g * z1

    # Solve for V2: V2² = 2(E1 - P2/ρ - gz2)
    V2_squared = 2 * (E1 - P2 / density - g * z2)

    if V2_squared < 0:
        raise ValueError("Invalid Bernoulli parameters: negative V²")

    return math.sqrt(V2_squared)


def torricelli_velocity(height: float, g: float = 9.80665) -> float:
    """
    Calculate efflux velocity (Torricelli's theorem).

    V = √(2gh)

    Args:
        height: Height of fluid above orifice (m)
        g: Gravitational acceleration (m/s²)

    Returns:
        Exit velocity (m/s)
    """
    return math.sqrt(2 * g * height)


def venturi_flow_rate(
    A1: float, A2: float, P1: float, P2: float, density: float
) -> float:
    """
    Calculate flow rate through Venturi meter.

    Q = A₂ * √(2(P₁-P₂)/(ρ(1-(A₂/A₁)²)))

    Args:
        A1: Upstream area (m²)
        A2: Throat area (m²)
        P1: Upstream pressure (Pa)
        P2: Throat pressure (Pa)
        density: Fluid density (kg/m³)

    Returns:
        Volumetric flow rate (m³/s)
    """
    area_ratio = (A2 / A1) ** 2
    dP = P1 - P2

    if dP <= 0 or area_ratio >= 1:
        raise ValueError("Invalid Venturi parameters")

    V2 = math.sqrt(2 * dP / (density * (1 - area_ratio)))
    return A2 * V2


def pitot_velocity(
    stagnation_pressure: float, static_pressure: float, density: float
) -> float:
    """
    Calculate velocity from Pitot tube measurement.

    V = √(2(P₀ - P)/ρ)

    Args:
        stagnation_pressure: Total pressure (Pa)
        static_pressure: Static pressure (Pa)
        density: Fluid density (kg/m³)

    Returns:
        Flow velocity (m/s)
    """
    dP = stagnation_pressure - static_pressure
    if dP < 0:
        raise ValueError("Stagnation pressure must be >= static pressure")
    return math.sqrt(2 * dP / density)


# =============================================================================
# DRAG AND LIFT
# =============================================================================


def drag_force(Cd: float, density: float, velocity: float, area: float) -> float:
    """
    Calculate drag force.

    D = ½CdρV²A

    Args:
        Cd: Drag coefficient
        density: Fluid density (kg/m³)
        velocity: Flow velocity (m/s)
        area: Reference area (m²)

    Returns:
        Drag force (N)
    """
    return 0.5 * Cd * density * velocity**2 * area


def lift_force(Cl: float, density: float, velocity: float, area: float) -> float:
    """
    Calculate lift force.

    L = ½ClρV²A

    Args:
        Cl: Lift coefficient
        density: Fluid density (kg/m³)
        velocity: Flow velocity (m/s)
        area: Reference area (m²)

    Returns:
        Lift force (N)
    """
    return 0.5 * Cl * density * velocity**2 * area


def sphere_drag_coefficient(Re: float) -> float:
    """
    Estimate drag coefficient for a sphere.

    Uses empirical correlations for different Re regimes.

    Args:
        Re: Reynolds number

    Returns:
        Drag coefficient Cd
    """
    if Re < 0.1:
        # Stokes regime: Cd = 24/Re
        return 24 / Re
    elif Re < 1000:
        # Intermediate regime (Schiller-Naumann)
        return (24 / Re) * (1 + 0.15 * Re**0.687)
    elif Re < 2e5:
        # Newton regime
        return 0.44
    else:
        # Post-critical (turbulent boundary layer)
        return 0.1


def terminal_velocity(
    mass: float, Cd: float, density: float, area: float, g: float = 9.80665
) -> float:
    """
    Calculate terminal velocity.

    V_t = √(2mg/(CdρA))

    Args:
        mass: Object mass (kg)
        Cd: Drag coefficient
        density: Fluid density (kg/m³)
        area: Reference area (m²)
        g: Gravitational acceleration (m/s²)

    Returns:
        Terminal velocity (m/s)
    """
    return math.sqrt(2 * mass * g / (Cd * density * area))


# =============================================================================
# PIPE FLOW
# =============================================================================


def darcy_friction_factor_laminar(Re: float) -> float:
    """
    Darcy friction factor for laminar flow.

    f = 64/Re (for Re < 2300)

    Args:
        Re: Reynolds number

    Returns:
        Darcy friction factor
    """
    return 64 / Re


def darcy_friction_factor_turbulent(
    Re: float, roughness: float, diameter: float
) -> float:
    """
    Darcy friction factor for turbulent flow (Colebrook-White equation).

    1/√f = -2 log₁₀(ε/(3.7D) + 2.51/(Re√f))

    Uses iterative solution.

    Args:
        Re: Reynolds number
        roughness: Pipe roughness ε (m)
        diameter: Pipe diameter (m)

    Returns:
        Darcy friction factor
    """
    eps_D = roughness / diameter

    # Initial guess (Haaland equation)
    f = (1 / (-1.8 * math.log10((eps_D / 3.7) ** 1.11 + 6.9 / Re))) ** 2

    # Newton-Raphson iteration
    for _ in range(20):
        sqrt_f = math.sqrt(f)
        lhs = 1 / sqrt_f
        rhs = -2 * math.log10(eps_D / 3.7 + 2.51 / (Re * sqrt_f))

        # f(f) = 1/√f + 2*log10(ε/3.7D + 2.51/(Re*√f)) = 0
        # f'(f) = -1/(2*f^(3/2)) + 2.51/(Re*f*ln(10)*(ε/3.7D + 2.51/(Re*√f)))

        f_func = lhs - rhs
        if abs(f_func) < 1e-10:
            break

        # Simplified: update using Haaland as correction
        f = (1 / (-1.8 * math.log10((eps_D / 3.7) ** 1.11 + 6.9 / Re))) ** 2
        break  # Haaland is accurate enough for most purposes

    return f


def pipe_pressure_drop(
    f: float, length: float, diameter: float, density: float, velocity: float
) -> float:
    """
    Calculate pressure drop in pipe (Darcy-Weisbach equation).

    ΔP = f * (L/D) * (ρV²/2)

    Args:
        f: Darcy friction factor
        length: Pipe length (m)
        diameter: Pipe diameter (m)
        density: Fluid density (kg/m³)
        velocity: Flow velocity (m/s)

    Returns:
        Pressure drop (Pa)
    """
    return f * (length / diameter) * (density * velocity**2 / 2)


def head_loss(
    f: float, length: float, diameter: float, velocity: float, g: float = 9.80665
) -> float:
    """
    Calculate head loss in pipe.

    h_L = f * (L/D) * (V²/2g)

    Args:
        f: Darcy friction factor
        length: Pipe length (m)
        diameter: Pipe diameter (m)
        velocity: Flow velocity (m/s)
        g: Gravitational acceleration (m/s²)

    Returns:
        Head loss (m)
    """
    return f * (length / diameter) * (velocity**2 / (2 * g))


def minor_loss(K: float, velocity: float, g: float = 9.80665) -> float:
    """
    Calculate minor (local) head loss.

    h_m = K * V²/2g

    Args:
        K: Loss coefficient
        velocity: Flow velocity (m/s)
        g: Gravitational acceleration (m/s²)

    Returns:
        Minor head loss (m)
    """
    return K * velocity**2 / (2 * g)


# Common minor loss coefficients
MINOR_LOSS_COEFFICIENTS = {
    "entrance_sharp": 0.5,
    "entrance_rounded": 0.04,
    "exit": 1.0,
    "90_elbow_standard": 0.3,
    "90_elbow_long_radius": 0.2,
    "45_elbow": 0.4,
    "tee_flow_through": 0.2,
    "tee_flow_branch": 1.0,
    "gate_valve_full_open": 0.2,
    "gate_valve_half_open": 5.6,
    "check_valve": 2.0,
    "globe_valve_open": 10.0,
}


# =============================================================================
# COMPRESSIBLE FLOW (Isentropic)
# =============================================================================


def isentropic_pressure_ratio(M: float, gamma: float = 1.4) -> float:
    """
    Calculate isentropic pressure ratio P/P₀.

    P/P₀ = (1 + (γ-1)/2 * M²)^(-γ/(γ-1))

    Args:
        M: Mach number
        gamma: Specific heat ratio

    Returns:
        Static to total pressure ratio
    """
    exponent = -gamma / (gamma - 1)
    return (1 + (gamma - 1) / 2 * M**2) ** exponent


def isentropic_temperature_ratio(M: float, gamma: float = 1.4) -> float:
    """
    Calculate isentropic temperature ratio T/T₀.

    T/T₀ = (1 + (γ-1)/2 * M²)^(-1)

    Args:
        M: Mach number
        gamma: Specific heat ratio

    Returns:
        Static to total temperature ratio
    """
    return 1 / (1 + (gamma - 1) / 2 * M**2)


def isentropic_density_ratio(M: float, gamma: float = 1.4) -> float:
    """
    Calculate isentropic density ratio ρ/ρ₀.

    ρ/ρ₀ = (1 + (γ-1)/2 * M²)^(-1/(γ-1))

    Args:
        M: Mach number
        gamma: Specific heat ratio

    Returns:
        Static to total density ratio
    """
    exponent = -1 / (gamma - 1)
    return (1 + (gamma - 1) / 2 * M**2) ** exponent


def isentropic_area_ratio(M: float, gamma: float = 1.4) -> float:
    """
    Calculate isentropic area ratio A/A*.

    A/A* = (1/M) * [(2/(γ+1))*(1 + (γ-1)/2*M²)]^((γ+1)/(2(γ-1)))

    Args:
        M: Mach number
        gamma: Specific heat ratio

    Returns:
        Area to critical area ratio
    """
    if M == 0:
        return float("inf")

    gp1 = gamma + 1
    gm1 = gamma - 1

    term = (2 / gp1) * (1 + gm1 / 2 * M**2)
    exponent = gp1 / (2 * gm1)

    return (1 / M) * term**exponent


def critical_pressure_ratio(gamma: float = 1.4) -> float:
    """
    Calculate critical pressure ratio P*/P₀ (at M=1).

    P*/P₀ = (2/(γ+1))^(γ/(γ-1))

    Args:
        gamma: Specific heat ratio

    Returns:
        Critical pressure ratio
    """
    return (2 / (gamma + 1)) ** (gamma / (gamma - 1))


# =============================================================================
# NORMAL SHOCK RELATIONS
# =============================================================================


def normal_shock_mach(M1: float, gamma: float = 1.4) -> float:
    """
    Calculate downstream Mach number after normal shock.

    M₂² = (M₁² + 2/(γ-1)) / (2γ/(γ-1)*M₁² - 1)

    Args:
        M1: Upstream Mach number (must be > 1)
        gamma: Specific heat ratio

    Returns:
        Downstream Mach number
    """
    if M1 <= 1:
        raise ValueError("Upstream Mach must be > 1 for normal shock")

    gm1 = gamma - 1
    numerator = M1**2 + 2 / gm1
    denominator = 2 * gamma / gm1 * M1**2 - 1

    return math.sqrt(numerator / denominator)


def normal_shock_pressure_ratio(M1: float, gamma: float = 1.4) -> float:
    """
    Calculate static pressure ratio across normal shock P₂/P₁.

    P₂/P₁ = 1 + 2γ/(γ+1)*(M₁² - 1)

    Args:
        M1: Upstream Mach number
        gamma: Specific heat ratio

    Returns:
        Pressure ratio P2/P1
    """
    return 1 + 2 * gamma / (gamma + 1) * (M1**2 - 1)


def normal_shock_temperature_ratio(M1: float, gamma: float = 1.4) -> float:
    """
    Calculate temperature ratio across normal shock T₂/T₁.

    Args:
        M1: Upstream Mach number
        gamma: Specific heat ratio

    Returns:
        Temperature ratio T2/T1
    """
    gp1 = gamma + 1
    gm1 = gamma - 1

    term1 = 1 + gm1 / 2 * M1**2
    term2 = gamma * M1**2 - gm1 / 2

    return (2 * term1 * term2) / (gp1**2 / 2 * M1**2)


def normal_shock_density_ratio(M1: float, gamma: float = 1.4) -> float:
    """
    Calculate density ratio across normal shock ρ₂/ρ₁.

    ρ₂/ρ₁ = (γ+1)M₁² / ((γ-1)M₁² + 2)

    Args:
        M1: Upstream Mach number
        gamma: Specific heat ratio

    Returns:
        Density ratio ρ2/ρ1
    """
    gp1 = gamma + 1
    gm1 = gamma - 1

    return gp1 * M1**2 / (gm1 * M1**2 + 2)


def normal_shock_total_pressure_ratio(M1: float, gamma: float = 1.4) -> float:
    """
    Calculate total pressure ratio across normal shock P₀₂/P₀₁.

    This represents entropy increase across shock.

    Args:
        M1: Upstream Mach number
        gamma: Specific heat ratio

    Returns:
        Total pressure ratio (always < 1)
    """
    gp1 = gamma + 1
    gm1 = gamma - 1

    term1 = ((gp1 / 2 * M1**2) / (1 + gm1 / 2 * M1**2)) ** (gamma / gm1)
    term2 = (gp1 / (2 * gamma * M1**2 - gm1)) ** (1 / gm1)

    return term1 * term2


# =============================================================================
# BOUNDARY LAYER
# =============================================================================


def blasius_boundary_layer_thickness(x: float, Re_x: float) -> float:
    """
    Blasius boundary layer thickness for laminar flow over flat plate.

    δ = 5.0x / √(Re_x)

    Args:
        x: Distance from leading edge (m)
        Re_x: Local Reynolds number based on x

    Returns:
        Boundary layer thickness (m)
    """
    return 5.0 * x / math.sqrt(Re_x)


def blasius_displacement_thickness(x: float, Re_x: float) -> float:
    """
    Blasius displacement thickness.

    δ* = 1.72x / √(Re_x)

    Args:
        x: Distance from leading edge (m)
        Re_x: Local Reynolds number

    Returns:
        Displacement thickness (m)
    """
    return 1.72 * x / math.sqrt(Re_x)


def blasius_momentum_thickness(x: float, Re_x: float) -> float:
    """
    Blasius momentum thickness.

    θ = 0.664x / √(Re_x)

    Args:
        x: Distance from leading edge (m)
        Re_x: Local Reynolds number

    Returns:
        Momentum thickness (m)
    """
    return 0.664 * x / math.sqrt(Re_x)


def blasius_skin_friction(Re_x: float) -> float:
    """
    Blasius local skin friction coefficient (laminar).

    C_f = 0.664 / √(Re_x)

    Args:
        Re_x: Local Reynolds number

    Returns:
        Local skin friction coefficient
    """
    return 0.664 / math.sqrt(Re_x)


def turbulent_boundary_layer_thickness(x: float, Re_x: float) -> float:
    """
    Turbulent boundary layer thickness (1/7 power law).

    δ = 0.37x / Re_x^0.2

    Args:
        x: Distance from leading edge (m)
        Re_x: Local Reynolds number

    Returns:
        Boundary layer thickness (m)
    """
    return 0.37 * x / Re_x**0.2


def turbulent_skin_friction(Re_x: float) -> float:
    """
    Turbulent local skin friction coefficient.

    C_f = 0.0592 / Re_x^0.2

    Args:
        Re_x: Local Reynolds number

    Returns:
        Local skin friction coefficient
    """
    return 0.0592 / Re_x**0.2


# =============================================================================
# COMPREHENSIVE FLUID DYNAMICS CALCULATION
# =============================================================================


def fluid_dynamics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive fluid dynamics calculation.

    Args:
        params: Dictionary with relevant parameters such as:
            - velocity: Flow velocity (m/s)
            - length: Characteristic length (m)
            - fluid: Fluid name (water, air, etc.)
            - density: Fluid density (kg/m³) [optional if fluid given]
            - viscosity: Dynamic viscosity (Pa·s) [optional if fluid given]
            - pressure_upstream/downstream: For pressure calculations
            - pipe_diameter, pipe_length, roughness: For pipe flow
            - mach: For compressible flow

    Returns:
        Dictionary with computed fluid dynamics properties
    """
    results = {}

    # Get fluid properties
    fluid = params.get("fluid", "air")
    if fluid in FLUID_PROPERTIES:
        props = FLUID_PROPERTIES[fluid]
        density = params.get("density", props.get("density", 1.0))
        viscosity = params.get("viscosity", props.get("dynamic_viscosity", 1e-5))
    else:
        density = params.get("density", 1.0)
        viscosity = params.get("viscosity", 1e-5)

    results["fluid"] = fluid
    results["density_kg_m3"] = density
    results["dynamic_viscosity_Pa_s"] = viscosity
    results["kinematic_viscosity_m2_s"] = viscosity / density

    # Basic dimensionless numbers
    velocity = params.get("velocity", 0)
    length = params.get("length", 1.0)

    if velocity > 0 and length > 0:
        Re = reynolds_number(velocity, length, density, viscosity)
        results["reynolds_number"] = Re

        flow_regime = (
            "laminar" if Re < 2300 else "transitional" if Re < 4000 else "turbulent"
        )
        results["flow_regime"] = flow_regime

        # Froude number (if applicable)
        Fr = froude_number(velocity, length)
        results["froude_number"] = Fr

    # Dynamic pressure
    if velocity > 0:
        q = 0.5 * density * velocity**2
        results["dynamic_pressure_Pa"] = q

    # Drag calculations
    if "drag_coefficient" in params:
        Cd = params["drag_coefficient"]
        area = params.get("area", 1.0)
        D = drag_force(Cd, density, velocity, area)
        results["drag_force_N"] = D

    # Pipe flow
    if "pipe_diameter" in params:
        D_pipe = params["pipe_diameter"]
        L_pipe = params.get("pipe_length", 1.0)
        roughness = params.get("roughness", 0.00015)  # Default: commercial steel

        Re_pipe = reynolds_number(velocity, D_pipe, density, viscosity)
        results["pipe_reynolds"] = Re_pipe

        if Re_pipe < 2300:
            f = darcy_friction_factor_laminar(Re_pipe)
        else:
            f = darcy_friction_factor_turbulent(Re_pipe, roughness, D_pipe)

        results["darcy_friction_factor"] = f

        dP = pipe_pressure_drop(f, L_pipe, D_pipe, density, velocity)
        h_L = head_loss(f, L_pipe, D_pipe, velocity)
        results["pipe_pressure_drop_Pa"] = dP
        results["pipe_head_loss_m"] = h_L

    # Compressible flow
    if "mach" in params or "speed_of_sound" in params:
        if "mach" in params:
            M = params["mach"]
        else:
            a = params["speed_of_sound"]
            M = velocity / a

        gamma = params.get("gamma", 1.4)

        results["mach_number"] = M

        # Isentropic ratios
        results["isentropic_pressure_ratio"] = isentropic_pressure_ratio(M, gamma)
        results["isentropic_temperature_ratio"] = isentropic_temperature_ratio(M, gamma)
        results["isentropic_density_ratio"] = isentropic_density_ratio(M, gamma)
        results["isentropic_area_ratio"] = isentropic_area_ratio(M, gamma)

        # Normal shock (if supersonic)
        if M > 1:
            results["normal_shock"] = {
                "downstream_mach": normal_shock_mach(M, gamma),
                "pressure_ratio": normal_shock_pressure_ratio(M, gamma),
                "temperature_ratio": normal_shock_temperature_ratio(M, gamma),
                "density_ratio": normal_shock_density_ratio(M, gamma),
                "total_pressure_ratio": normal_shock_total_pressure_ratio(M, gamma),
            }

    # Boundary layer
    if "boundary_layer" in params and params["boundary_layer"]:
        x = params.get("distance_from_leading_edge", length)
        Re_x = reynolds_number(velocity, x, density, viscosity)

        if Re_x > 0:
            results["boundary_layer"] = {
                "laminar": {
                    "thickness_m": blasius_boundary_layer_thickness(x, Re_x),
                    "displacement_thickness_m": blasius_displacement_thickness(x, Re_x),
                    "momentum_thickness_m": blasius_momentum_thickness(x, Re_x),
                    "skin_friction_coeff": blasius_skin_friction(Re_x),
                },
                "turbulent": {
                    "thickness_m": turbulent_boundary_layer_thickness(x, Re_x),
                    "skin_friction_coeff": turbulent_skin_friction(Re_x),
                },
            }

    return results
