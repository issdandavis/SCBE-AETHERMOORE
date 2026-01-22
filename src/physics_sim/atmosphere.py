#!/usr/bin/env python3
"""
Atmospheric Physics Module

International Standard Atmosphere (ISA) model and atmospheric calculations.
Based on US Standard Atmosphere 1976 and real atmospheric physics.

Features:
- ISA temperature/pressure/density profiles up to 86 km
- Speed of sound calculations
- Dynamic viscosity (Sutherland's law)
- Mach number and compressibility
- Atmospheric composition
"""

import math
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

# =============================================================================
# ATMOSPHERIC CONSTANTS
# =============================================================================

# Sea level standard values (ISA)
SEA_LEVEL_TEMPERATURE = 288.15  # K (15°C)
SEA_LEVEL_PRESSURE = 101325.0  # Pa
SEA_LEVEL_DENSITY = 1.225  # kg/m³

# Gas constants
GAMMA_AIR = 1.4  # Heat capacity ratio for air
R_SPECIFIC_AIR = 287.058  # Specific gas constant for air (J/(kg·K))
MOLAR_MASS_AIR = 0.0289644  # kg/mol

# Gravitational acceleration (standard)
G0 = 9.80665  # m/s²

# Sutherland's constants for air
SUTHERLAND_C = 120.0  # K
SUTHERLAND_MU0 = 1.716e-5  # Pa·s at T0
SUTHERLAND_T0 = 273.15  # K


# =============================================================================
# ISA LAYER DEFINITIONS (Geopotential altitude)
# =============================================================================


@dataclass
class ISALayer:
    """ISA atmospheric layer definition."""

    h_base: float  # Base geopotential altitude (m)
    T_base: float  # Base temperature (K)
    lapse_rate: float  # Temperature lapse rate (K/m), negative = cooling


ISA_LAYERS = [
    ISALayer(0, 288.15, -0.0065),  # Troposphere
    ISALayer(11000, 216.65, 0.0),  # Tropopause
    ISALayer(20000, 216.65, 0.001),  # Stratosphere 1
    ISALayer(32000, 228.65, 0.0028),  # Stratosphere 2
    ISALayer(47000, 270.65, 0.0),  # Stratopause
    ISALayer(51000, 270.65, -0.0028),  # Mesosphere 1
    ISALayer(71000, 214.65, -0.002),  # Mesosphere 2
]

# Maximum valid altitude for ISA model
MAX_ALTITUDE = 86000  # m


# =============================================================================
# CORE ISA FUNCTIONS
# =============================================================================


def _get_layer(altitude: float) -> Tuple[ISALayer, int]:
    """Get the ISA layer for a given altitude."""
    for i, layer in enumerate(ISA_LAYERS):
        if i == len(ISA_LAYERS) - 1:
            return layer, i
        if altitude < ISA_LAYERS[i + 1].h_base:
            return layer, i
    return ISA_LAYERS[-1], len(ISA_LAYERS) - 1


def isa_temperature(altitude: float) -> float:
    """
    Calculate ISA temperature at given geopotential altitude.

    Args:
        altitude: Geopotential altitude in meters (0 to 86000)

    Returns:
        Temperature in Kelvin
    """
    altitude = max(0, min(altitude, MAX_ALTITUDE))
    layer, _ = _get_layer(altitude)

    delta_h = altitude - layer.h_base
    return layer.T_base + layer.lapse_rate * delta_h


def isa_pressure(altitude: float) -> float:
    """
    Calculate ISA pressure at given geopotential altitude.

    Uses barometric formula with different equations for
    isothermal and gradient layers.

    Args:
        altitude: Geopotential altitude in meters

    Returns:
        Pressure in Pascals
    """
    altitude = max(0, min(altitude, MAX_ALTITUDE))

    # Start from sea level
    P = SEA_LEVEL_PRESSURE
    T = SEA_LEVEL_TEMPERATURE

    prev_h = 0
    for i, layer in enumerate(ISA_LAYERS):
        h_top = ISA_LAYERS[i + 1].h_base if i < len(ISA_LAYERS) - 1 else MAX_ALTITUDE
        h_layer_top = min(altitude, h_top)

        if h_layer_top <= layer.h_base:
            break

        delta_h = h_layer_top - max(prev_h, layer.h_base)

        if abs(layer.lapse_rate) < 1e-10:
            # Isothermal layer: P = P_base * exp(-g*h/(R*T))
            P = P * math.exp(-G0 * delta_h / (R_SPECIFIC_AIR * T))
        else:
            # Gradient layer: P = P_base * (T/T_base)^(-g/(L*R))
            T_new = T + layer.lapse_rate * delta_h
            exponent = -G0 / (layer.lapse_rate * R_SPECIFIC_AIR)
            P = P * (T_new / T) ** exponent
            T = T_new

        prev_h = h_layer_top

        if altitude <= h_top:
            break

    return P


def isa_density(altitude: float) -> float:
    """
    Calculate ISA density at given geopotential altitude.

    Uses ideal gas law: ρ = P / (R * T)

    Args:
        altitude: Geopotential altitude in meters

    Returns:
        Density in kg/m³
    """
    T = isa_temperature(altitude)
    P = isa_pressure(altitude)
    return P / (R_SPECIFIC_AIR * T)


def speed_of_sound(temperature: float) -> float:
    """
    Calculate speed of sound in air.

    a = √(γ * R * T)

    Args:
        temperature: Temperature in Kelvin

    Returns:
        Speed of sound in m/s
    """
    return math.sqrt(GAMMA_AIR * R_SPECIFIC_AIR * temperature)


def dynamic_viscosity(temperature: float) -> float:
    """
    Calculate dynamic viscosity using Sutherland's law.

    μ = μ₀ * (T/T₀)^(3/2) * (T₀ + C) / (T + C)

    Args:
        temperature: Temperature in Kelvin

    Returns:
        Dynamic viscosity in Pa·s
    """
    return (
        SUTHERLAND_MU0
        * (temperature / SUTHERLAND_T0) ** 1.5
        * (SUTHERLAND_T0 + SUTHERLAND_C)
        / (temperature + SUTHERLAND_C)
    )


def kinematic_viscosity(temperature: float, density: float) -> float:
    """
    Calculate kinematic viscosity.

    ν = μ / ρ

    Args:
        temperature: Temperature in Kelvin
        density: Density in kg/m³

    Returns:
        Kinematic viscosity in m²/s
    """
    return dynamic_viscosity(temperature) / density


# =============================================================================
# COMPRESSIBILITY AND MACH NUMBER
# =============================================================================


def mach_number(velocity: float, temperature: float) -> float:
    """
    Calculate Mach number.

    M = V / a

    Args:
        velocity: Flow velocity in m/s
        temperature: Temperature in Kelvin

    Returns:
        Mach number (dimensionless)
    """
    a = speed_of_sound(temperature)
    return velocity / a


def stagnation_temperature(T_static: float, mach: float) -> float:
    """
    Calculate stagnation (total) temperature.

    T₀ = T * (1 + (γ-1)/2 * M²)

    Args:
        T_static: Static temperature in Kelvin
        mach: Mach number

    Returns:
        Stagnation temperature in Kelvin
    """
    return T_static * (1 + (GAMMA_AIR - 1) / 2 * mach**2)


def stagnation_pressure(P_static: float, mach: float) -> float:
    """
    Calculate stagnation (total) pressure (isentropic).

    P₀ = P * (1 + (γ-1)/2 * M²)^(γ/(γ-1))

    Args:
        P_static: Static pressure in Pascals
        mach: Mach number

    Returns:
        Stagnation pressure in Pascals
    """
    exponent = GAMMA_AIR / (GAMMA_AIR - 1)
    return P_static * (1 + (GAMMA_AIR - 1) / 2 * mach**2) ** exponent


def dynamic_pressure(density: float, velocity: float) -> float:
    """
    Calculate dynamic pressure.

    q = ½ρV²

    Args:
        density: Density in kg/m³
        velocity: Velocity in m/s

    Returns:
        Dynamic pressure in Pascals
    """
    return 0.5 * density * velocity**2


def impact_pressure(P_static: float, mach: float) -> float:
    """
    Calculate impact pressure (Pitot tube reading - static).

    For M < 1 (subsonic): q_c = P₀ - P
    For M > 1 (supersonic): Uses Rayleigh formula

    Args:
        P_static: Static pressure in Pascals
        mach: Mach number

    Returns:
        Impact pressure in Pascals
    """
    if mach < 1:
        # Subsonic: isentropic
        P0 = stagnation_pressure(P_static, mach)
        return P0 - P_static
    else:
        # Supersonic: Rayleigh pitot formula
        # P₀₂/P₁ = [(γ+1)²M²/(4γM²-2(γ-1))]^(γ/(γ-1)) * [(1-γ+2γM²)/(γ+1)]
        gp1 = GAMMA_AIR + 1
        gm1 = GAMMA_AIR - 1

        term1 = (gp1**2 * mach**2) / (4 * GAMMA_AIR * mach**2 - 2 * gm1)
        term2 = (1 - GAMMA_AIR + 2 * GAMMA_AIR * mach**2) / gp1

        P02_P1 = (term1 ** (GAMMA_AIR / gm1)) * term2
        P02 = P02_P1 * P_static

        return P02 - P_static


# =============================================================================
# ATMOSPHERIC COMPOSITION
# =============================================================================

ATMOSPHERIC_COMPOSITION = {
    "N2": {"fraction": 0.78084, "molar_mass": 28.0134},
    "O2": {"fraction": 0.20946, "molar_mass": 31.9988},
    "Ar": {"fraction": 0.00934, "molar_mass": 39.948},
    "CO2": {"fraction": 0.000417, "molar_mass": 44.01},
    "Ne": {"fraction": 0.00001818, "molar_mass": 20.1797},
    "He": {"fraction": 0.00000524, "molar_mass": 4.0026},
    "CH4": {"fraction": 0.00000187, "molar_mass": 16.04},
    "Kr": {"fraction": 0.00000114, "molar_mass": 83.798},
}


def partial_pressure(total_pressure: float, gas: str) -> float:
    """
    Calculate partial pressure of a gas.

    Args:
        total_pressure: Total atmospheric pressure in Pa
        gas: Gas name (N2, O2, Ar, CO2, etc.)

    Returns:
        Partial pressure in Pa
    """
    if gas not in ATMOSPHERIC_COMPOSITION:
        raise ValueError(f"Unknown gas: {gas}")

    return total_pressure * ATMOSPHERIC_COMPOSITION[gas]["fraction"]


# =============================================================================
# ALTITUDE CONVERSIONS
# =============================================================================


def geopotential_to_geometric(h_geopotential: float) -> float:
    """
    Convert geopotential altitude to geometric altitude.

    h_geometric = (R_earth * h_geopotential) / (R_earth - h_geopotential)

    Args:
        h_geopotential: Geopotential altitude in meters

    Returns:
        Geometric altitude in meters
    """
    R_earth = 6356766  # Earth's radius for geopotential (m)
    return (R_earth * h_geopotential) / (R_earth - h_geopotential)


def geometric_to_geopotential(h_geometric: float) -> float:
    """
    Convert geometric altitude to geopotential altitude.

    h_geopotential = (R_earth * h_geometric) / (R_earth + h_geometric)

    Args:
        h_geometric: Geometric altitude in meters

    Returns:
        Geopotential altitude in meters
    """
    R_earth = 6356766
    return (R_earth * h_geometric) / (R_earth + h_geometric)


def pressure_altitude(pressure: float) -> float:
    """
    Calculate pressure altitude from measured pressure.

    Uses ISA model to find altitude that would give this pressure.

    Args:
        pressure: Measured pressure in Pascals

    Returns:
        Pressure altitude in meters
    """
    # Binary search for altitude
    h_low, h_high = 0, MAX_ALTITUDE

    while h_high - h_low > 0.1:  # 0.1m precision
        h_mid = (h_low + h_high) / 2
        P_mid = isa_pressure(h_mid)

        if P_mid > pressure:
            h_low = h_mid
        else:
            h_high = h_mid

    return (h_low + h_high) / 2


def density_altitude(temperature: float, pressure: float) -> float:
    """
    Calculate density altitude.

    The altitude in ISA where the density equals the actual density.

    Args:
        temperature: Actual temperature in Kelvin
        pressure: Actual pressure in Pascals

    Returns:
        Density altitude in meters
    """
    actual_density = pressure / (R_SPECIFIC_AIR * temperature)

    # Binary search
    h_low, h_high = -1000, MAX_ALTITUDE

    while h_high - h_low > 0.1:
        h_mid = (h_low + h_high) / 2
        rho_mid = isa_density(h_mid)

        if rho_mid > actual_density:
            h_low = h_mid
        else:
            h_high = h_mid

    return (h_low + h_high) / 2


# =============================================================================
# COMPREHENSIVE ATMOSPHERE CALCULATION
# =============================================================================


def atmosphere(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive atmospheric physics calculation.

    Args:
        params: Dictionary with any of:
            - altitude: Geopotential altitude (m)
            - geometric_altitude: Geometric altitude (m)
            - velocity: Flow velocity (m/s)
            - measured_pressure: For pressure altitude (Pa)
            - measured_temperature: For density altitude (K)

    Returns:
        Dictionary with all computed atmospheric properties
    """
    results = {}

    # Determine altitude
    if "geometric_altitude" in params:
        h_geo = geometric_to_geopotential(params["geometric_altitude"])
        results["geopotential_altitude"] = h_geo
    elif "altitude" in params:
        h_geo = params["altitude"]
    else:
        h_geo = 0  # Sea level default

    h_geo = max(0, min(h_geo, MAX_ALTITUDE))

    # Basic ISA properties
    T = isa_temperature(h_geo)
    P = isa_pressure(h_geo)
    rho = isa_density(h_geo)
    a = speed_of_sound(T)
    mu = dynamic_viscosity(T)
    nu = kinematic_viscosity(T, rho)

    results.update(
        {
            "temperature_K": T,
            "temperature_C": T - 273.15,
            "pressure_Pa": P,
            "pressure_hPa": P / 100,
            "pressure_atm": P / 101325,
            "density_kg_m3": rho,
            "speed_of_sound_m_s": a,
            "dynamic_viscosity_Pa_s": mu,
            "kinematic_viscosity_m2_s": nu,
        }
    )

    # Velocity-dependent properties
    if "velocity" in params:
        V = params["velocity"]
        M = mach_number(V, T)
        q = dynamic_pressure(rho, V)
        T0 = stagnation_temperature(T, M)
        P0 = stagnation_pressure(P, M)
        q_impact = impact_pressure(P, M)

        results.update(
            {
                "mach_number": M,
                "dynamic_pressure_Pa": q,
                "stagnation_temperature_K": T0,
                "stagnation_pressure_Pa": P0,
                "impact_pressure_Pa": q_impact,
                "flow_regime": (
                    "subsonic"
                    if M < 0.8
                    else (
                        "transonic"
                        if M < 1.2
                        else "supersonic" if M < 5 else "hypersonic"
                    )
                ),
            }
        )

        # Reynolds number per unit length
        Re_per_m = rho * V / mu
        results["reynolds_per_meter"] = Re_per_m

    # Pressure altitude
    if "measured_pressure" in params:
        h_pressure = pressure_altitude(params["measured_pressure"])
        results["pressure_altitude_m"] = h_pressure
        results["pressure_altitude_ft"] = h_pressure * 3.28084

    # Density altitude
    if "measured_temperature" in params and "measured_pressure" in params:
        h_density = density_altitude(
            params["measured_temperature"], params["measured_pressure"]
        )
        results["density_altitude_m"] = h_density
        results["density_altitude_ft"] = h_density * 3.28084

    # Partial pressures of main gases
    results["partial_pressures_Pa"] = {
        gas: partial_pressure(P, gas) for gas in ["N2", "O2", "Ar", "CO2"]
    }

    return results
