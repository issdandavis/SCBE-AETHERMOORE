"""
Flight Dynamics Physics Layer — 6-DOF + Rotor + VRS Recovery
=============================================================

Maps real aerodynamics onto the SCBE quantum frequency bundle:

    QHO excitation level → flight energy state (airspeed, altitude energy)
    Trit axes → control surfaces (structure=elevator, stability=aileron, creativity=rudder)
    Polymorphic forks → VRS recovery paths (Monty Hall multipath selection)
    Acoustic bands → engine power distribution (infra=idle, audible=cruise, ultra=afterburner)
    Visual vector → instrument panel (6 tongues = 6 gauges)

Real physics used (textbook, no approximation):
    Lift:   L = ½ρV²SC_L(α)
    Drag:   D = ½ρV²SC_D(α)
    Thrust: T = C_T·ρ·A·(ΩR)² (rotor)
    Weight: W = mg
    Induced velocity:  v_i = √(T / 2ρA)
    Stall:  α > α_crit ≈ 15° → C_L drops, C_D spikes
    VRS:    v_descent ≈ v_i → vortex ring state (recirculation)

6-DOF rigid body:
    F = ma  (translation: x, y, z)
    τ = Iα  (rotation: roll φ, pitch θ, yaw ψ)

Wires into:
    - quantum_frequency_bundle.py: QHO states → flight energy
    - multipath_generator.py: polymorphic forks → recovery paths
    - crossing_energy.py: governance cost → flight envelope limits
    - harmonic_dark_fill.py: acoustic bands → engine state

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.crypto.tri_bundle import PHI, TONGUE_WEIGHTS, TONGUE_FREQUENCIES
from src.crypto.trit_curriculum import TritSignal
from src.crypto.multipath_generator import MultiPathRecord

# ---------------------------------------------------------------------------
# Physical Constants (SI, sea-level ISA)
# ---------------------------------------------------------------------------

RHO_SEA_LEVEL = 1.225          # kg/m³ air density at sea level
G_ACCEL = 9.80665              # m/s² gravitational acceleration
GAMMA_AIR = 1.4                # adiabatic index for air
R_AIR = 287.058                # J/(kg·K) specific gas constant for air
T_SEA_LEVEL = 288.15           # K standard sea-level temperature
P_SEA_LEVEL = 101325.0         # Pa standard sea-level pressure

# Stall angle (degrees → radians)
ALPHA_CRIT_DEG = 15.0
ALPHA_CRIT_RAD = math.radians(ALPHA_CRIT_DEG)

# Maximum load factor before structural failure (civil aircraft)
G_LIMIT_POS = 3.8
G_LIMIT_NEG = -1.52

# Tongue → control surface mapping
TONGUE_CONTROL_MAP = {
    "structure": "elevator",     # pitch control (KO/DR axis)
    "stability": "aileron",      # roll control (AV/UM axis)
    "creativity": "rudder",      # yaw control (RU/CA axis)
}


# ---------------------------------------------------------------------------
# Aerodynamic Coefficients
# ---------------------------------------------------------------------------

def lift_coefficient(alpha_rad: float) -> float:
    """C_L(α) — lift coefficient as function of angle of attack.

    Pre-stall: C_L = 2π·sin(α) (thin airfoil theory)
    Post-stall: C_L drops by ~40% with turbulent separation

    Real: C_L_max ≈ 1.4-1.6 at α_crit ≈ 15°
    """
    if abs(alpha_rad) <= ALPHA_CRIT_RAD:
        # Thin airfoil: C_L = 2π·sin(α) ≈ 2πα for small α
        return 2 * math.pi * math.sin(alpha_rad)
    else:
        # Post-stall: separated flow, C_L drops
        sign = 1 if alpha_rad > 0 else -1
        cl_max = 2 * math.pi * math.sin(ALPHA_CRIT_RAD)
        overshoot = abs(alpha_rad) - ALPHA_CRIT_RAD
        # Exponential decay past stall
        return sign * cl_max * math.exp(-2.0 * overshoot)


def drag_coefficient(alpha_rad: float, cd0: float = 0.02) -> float:
    """C_D(α) — drag coefficient (parasitic + induced).

    C_D = C_D0 + C_L²/(π·e·AR)
    Using e=0.8, AR=8 as typical values.
    """
    cl = lift_coefficient(alpha_rad)
    e_oswald = 0.8
    aspect_ratio = 8.0
    cd_induced = cl ** 2 / (math.pi * e_oswald * aspect_ratio)
    return cd0 + cd_induced


def lift_force(velocity: float, alpha_rad: float, wing_area: float,
               rho: float = RHO_SEA_LEVEL) -> float:
    """L = ½ρV²SC_L(α) — lift force in Newtons."""
    cl = lift_coefficient(alpha_rad)
    return 0.5 * rho * velocity ** 2 * wing_area * cl


def drag_force(velocity: float, alpha_rad: float, wing_area: float,
               rho: float = RHO_SEA_LEVEL, cd0: float = 0.02) -> float:
    """D = ½ρV²SC_D(α) — drag force in Newtons."""
    cd = drag_coefficient(alpha_rad, cd0)
    return 0.5 * rho * velocity ** 2 * wing_area * cd


# ---------------------------------------------------------------------------
# Atmosphere Model (ISA)
# ---------------------------------------------------------------------------

def isa_density(altitude_m: float) -> float:
    """Air density at altitude (ISA troposphere model, valid to 11km).

    ρ(h) = ρ₀ · (T(h)/T₀)^(g/(L·R) - 1)
    where L = -0.0065 K/m (lapse rate)
    """
    lapse_rate = -0.0065  # K/m
    if altitude_m > 11000:
        altitude_m = 11000  # cap at tropopause
    temp = T_SEA_LEVEL + lapse_rate * altitude_m
    exponent = (G_ACCEL / (-lapse_rate * R_AIR)) - 1
    return RHO_SEA_LEVEL * (temp / T_SEA_LEVEL) ** exponent


# ---------------------------------------------------------------------------
# 6-DOF State
# ---------------------------------------------------------------------------

@dataclass
class SixDOFState:
    """Six degree-of-freedom rigid body state.

    Translation: position (x, y, z) and velocity (u, v, w)
    Rotation: Euler angles (phi, theta, psi) and rates (p, q, r)

    The 6-DOF maps to trit axes:
        structure → pitch (θ, q) → elevator
        stability → roll (φ, p) → aileron
        creativity → yaw (ψ, r) → rudder
    """
    # Position (m) — earth-fixed frame
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # altitude (positive up)

    # Velocity (m/s) — body frame
    u: float = 0.0  # forward (surge)
    v: float = 0.0  # lateral (sway)
    w: float = 0.0  # vertical (heave)

    # Euler angles (rad) — attitude
    phi: float = 0.0    # roll
    theta: float = 0.0  # pitch (maps to structure axis)
    psi: float = 0.0    # yaw

    # Angular rates (rad/s) — body frame
    p: float = 0.0  # roll rate
    q: float = 0.0  # pitch rate
    r: float = 0.0  # yaw rate

    @property
    def airspeed(self) -> float:
        """True airspeed |V| = √(u² + v² + w²)."""
        return math.sqrt(self.u ** 2 + self.v ** 2 + self.w ** 2)

    @property
    def angle_of_attack(self) -> float:
        """α = arctan(w/u) — angle of attack in radians."""
        if abs(self.u) < 1e-6:
            return 0.0
        return math.atan2(self.w, self.u)

    @property
    def sideslip(self) -> float:
        """β = arcsin(v/|V|) — sideslip angle."""
        v_total = self.airspeed
        if v_total < 1e-6:
            return 0.0
        return math.asin(max(-1, min(1, self.v / v_total)))

    @property
    def altitude(self) -> float:
        """Altitude above reference (positive up)."""
        return self.z

    @property
    def dynamic_pressure(self) -> float:
        """q = ½ρV² — dynamic pressure at current altitude."""
        rho = isa_density(max(0, self.z))
        return 0.5 * rho * self.airspeed ** 2

    @property
    def stall_margin(self) -> float:
        """How far from stall (1.0 = no AoA, 0.0 = at stall, <0 = post-stall)."""
        return 1.0 - abs(self.angle_of_attack) / ALPHA_CRIT_RAD

    @property
    def is_stalled(self) -> bool:
        """True if AoA exceeds critical angle."""
        return abs(self.angle_of_attack) > ALPHA_CRIT_RAD

    def g_load(self, lift_n: float, mass_kg: float) -> float:
        """G-load = L / W — load factor."""
        weight = mass_kg * G_ACCEL
        if weight < 1e-6:
            return 0.0
        return lift_n / weight

    def to_dict(self) -> dict:
        return {
            "position": {"x": round(self.x, 2), "y": round(self.y, 2), "z": round(self.z, 2)},
            "velocity": {"u": round(self.u, 2), "v": round(self.v, 2), "w": round(self.w, 2)},
            "attitude": {
                "phi_rad": round(self.phi, 4),
                "theta_rad": round(self.theta, 4),
                "psi_rad": round(self.psi, 4),
            },
            "angular_rates": {"p": round(self.p, 4), "q": round(self.q, 4), "r": round(self.r, 4)},
            "airspeed_ms": round(self.airspeed, 2),
            "aoa_deg": round(math.degrees(self.angle_of_attack), 2),
            "sideslip_deg": round(math.degrees(self.sideslip), 2),
            "stall_margin": round(self.stall_margin, 4),
            "is_stalled": self.is_stalled,
            "dynamic_pressure_pa": round(self.dynamic_pressure, 2),
        }


# ---------------------------------------------------------------------------
# Rotor Dynamics (Helicopter)
# ---------------------------------------------------------------------------

@dataclass
class RotorState:
    """Helicopter rotor dynamics state.

    T = C_T · ρ · A · (ΩR)²
    v_i = √(T / 2ρA)  — induced velocity (momentum theory)
    P = T · v_i        — induced power (hover)

    Maps to SCBE:
        Rotor RPM (Ω) ← tongue frequency (Hz) × excitation level
        Collective ← mean excitation (all tongues)
        Cyclic ← trit deviation (directional control)
        VRS margin ← descent rate vs induced velocity
    """
    rotor_radius: float = 5.0      # m (typical UH-60)
    rotor_rpm: float = 258.0       # nominal RPM
    num_blades: int = 4
    blade_chord: float = 0.53      # m
    ct: float = 0.0065             # thrust coefficient (typical)
    collective_deg: float = 10.0   # collective pitch (degrees)
    cyclic_lat_deg: float = 0.0    # lateral cyclic
    cyclic_lon_deg: float = 0.0    # longitudinal cyclic

    @property
    def disk_area(self) -> float:
        """A = πR² — rotor disk area."""
        return math.pi * self.rotor_radius ** 2

    @property
    def omega(self) -> float:
        """Ω = 2πn/60 — angular velocity (rad/s)."""
        return 2 * math.pi * self.rotor_rpm / 60.0

    @property
    def tip_speed(self) -> float:
        """V_tip = ΩR — blade tip speed (m/s)."""
        return self.omega * self.rotor_radius

    @property
    def thrust(self) -> float:
        """T = C_T · ρ · A · (ΩR)² — rotor thrust in Newtons."""
        return self.ct * RHO_SEA_LEVEL * self.disk_area * self.tip_speed ** 2

    @property
    def induced_velocity(self) -> float:
        """v_i = √(T / 2ρA) — momentum theory induced velocity."""
        t = self.thrust
        if t <= 0:
            return 0.0
        return math.sqrt(t / (2 * RHO_SEA_LEVEL * self.disk_area))

    @property
    def induced_power(self) -> float:
        """P_i = T · v_i — ideal induced power (Watts)."""
        return self.thrust * self.induced_velocity

    @property
    def solidity(self) -> float:
        """σ = Nc/(πR) — rotor solidity."""
        return (self.num_blades * self.blade_chord) / (math.pi * self.rotor_radius)

    def vrs_margin(self, descent_rate: float) -> float:
        """VRS margin: how close descent rate is to induced velocity.

        VRS onset when v_descent ≈ 0.7·v_i to 1.5·v_i
        Returns 1.0 = safe, 0.0 = VRS onset, <0 = deep VRS.

        The Monty Hall analogy: VRS is the "wrong door." The recovery
        paths (standard, Vuichard, autorotation) are the other doors.
        """
        vi = self.induced_velocity
        if vi < 1e-6:
            return 1.0
        ratio = abs(descent_rate) / vi
        # VRS zone: ratio ∈ [0.7, 1.5]
        if ratio < 0.7:
            return 1.0 - ratio / 0.7 * 0.0  # fully safe
        elif ratio < 1.5:
            # In the VRS danger zone
            return 1.0 - (ratio - 0.7) / 0.8  # linear decay
        else:
            return max(-1.0, -(ratio - 1.5))  # deep VRS

    def to_dict(self) -> dict:
        return {
            "rotor_radius_m": self.rotor_radius,
            "rotor_rpm": round(self.rotor_rpm, 1),
            "omega_rad_s": round(self.omega, 2),
            "tip_speed_ms": round(self.tip_speed, 1),
            "disk_area_m2": round(self.disk_area, 2),
            "thrust_n": round(self.thrust, 1),
            "induced_velocity_ms": round(self.induced_velocity, 2),
            "induced_power_w": round(self.induced_power, 1),
            "solidity": round(self.solidity, 4),
            "collective_deg": round(self.collective_deg, 1),
            "cyclic_lat_deg": round(self.cyclic_lat_deg, 1),
            "cyclic_lon_deg": round(self.cyclic_lon_deg, 1),
            "ct": self.ct,
        }


# ---------------------------------------------------------------------------
# VRS Recovery Paths (Polymorphic Fork → Recovery Selection)
# ---------------------------------------------------------------------------

class RecoveryType:
    STANDARD = "standard"
    VUICHARD = "vuichard"
    AUTOROTATION = "autorotation"
    TAIL_ROTOR_FAILURE = "tail_rotor_failure"


# Sacred Tongue hybrid mappings per recovery type
# Each recovery maps to dominant trit axis + tongue combination
SACRED_TONGUE_HYBRIDS = {
    RecoveryType.STANDARD: {
        "tongues": ["thulkoric", "avali"],
        "dominant_axis": "structure",
        "hybrid_phrase": "Thul'kor av'silan",
        "sensory": "weight and resonance grounded by flowing cyan light",
        "description": "Structure-axis dominant: forward cyclic restores directional control",
    },
    RecoveryType.VUICHARD: {
        "tongues": ["korvali", "thulkoric"],
        "dominant_axis": "stability",
        "hybrid_phrase": "Kor'val thul'sirek",
        "sensory": "mint chill binding laced with heavy resonant stone",
        "description": "Stability-axis dominant: lateral cyclic + 15% collective lifts sideways out of VRS",
    },
    RecoveryType.AUTOROTATION: {
        "tongues": ["draumbroth", "cassisivadan"],
        "dominant_axis": "structure",
        "hybrid_phrase": "Draum'bro cassi'vadan",
        "sensory": "iron forge heat surrendered to golden invention light",
        "description": "Structure-axis dominant: full down collective + flare trades altitude for rotor energy",
    },
    RecoveryType.TAIL_ROTOR_FAILURE: {
        "tongues": ["umbroth", "koraelin", "draumric"],
        "dominant_axis": "creativity",
        "hybrid_phrase": "Nar'shul sil'kor grondrak",
        "sensory": "echoing half-tones laced with mint chill grounding and heavy resonant stone/steam",
        "description": "Creativity-axis dominant: loss of yaw control → reduce collective + forward cyclic + running landing",
    },
}


@dataclass
class RecoveryPath:
    """A single VRS recovery technique.

    Standard:       Forward cyclic + lower collective → exit VRS forward
    Vuichard:       Lateral cyclic + slight collective increase → side exit
    Autorotation:   Full down collective → controlled descent → flare

    Each maps to a polymorphic fork path in the Monty Hall multipath:
        N forks → N possible recovery sequences
        Monty Hall advantage = probability the "other doors" contain a better path
    """
    recovery_type: str
    success_probability: float     # probability of successful recovery
    altitude_loss_m: float         # expected altitude loss during recovery
    time_to_recover_s: float       # expected recovery time
    control_inputs: Dict[str, float] = field(default_factory=dict)
    monty_hall_selected: bool = False  # was this the Monty Hall "switch" choice?
    sacred_tongue_hybrid: Optional[Dict] = None  # Sacred Tongue mapping for this recovery

    @property
    def severity(self) -> float:
        """Higher = more desperate (more altitude loss, lower success)."""
        if self.success_probability <= 0:
            return float('inf')
        return self.altitude_loss_m / (self.success_probability * 100)

    def to_dict(self) -> dict:
        d = {
            "type": self.recovery_type,
            "success_probability": round(self.success_probability, 4),
            "altitude_loss_m": round(self.altitude_loss_m, 1),
            "time_to_recover_s": round(self.time_to_recover_s, 1),
            "control_inputs": {k: round(v, 2) for k, v in self.control_inputs.items()},
            "severity": round(self.severity, 4),
            "monty_hall_selected": self.monty_hall_selected,
        }
        if self.sacred_tongue_hybrid:
            d["sacred_tongue_hybrid"] = self.sacred_tongue_hybrid
        return d


def compute_recovery_paths(
    vrs_margin: float,
    altitude_agl: float,
    multipath: Optional[MultiPathRecord] = None,
    tail_rotor_failed: bool = False,
) -> List[RecoveryPath]:
    """Generate recovery paths based on VRS severity and altitude.

    Maps polymorphic forks → recovery options. More forks = more
    recovery paths available (the Monty Hall advantage of options).

    Standard recovery: safest but needs altitude
    Vuichard: fastest but requires lateral clearance
    Autorotation: last resort, always available
    Tail rotor failure: creativity-axis dominant, running landing

    Each path carries a Sacred Tongue hybrid mapping — the conlang phrase
    that encodes the recovery technique as a spoken invocation.
    """
    paths = []

    # Standard: forward cyclic + lower collective
    # Better with more altitude (needs ~100m minimum)
    std_success = min(0.95, max(0.3, altitude_agl / 200.0))
    if vrs_margin < 0:
        std_success *= max(0.3, 1.0 + vrs_margin)  # deep VRS reduces success
    paths.append(RecoveryPath(
        recovery_type=RecoveryType.STANDARD,
        success_probability=std_success,
        altitude_loss_m=min(altitude_agl * 0.3, 150.0),
        time_to_recover_s=4.0 + abs(vrs_margin) * 3.0,
        control_inputs={
            "cyclic_forward": 0.7,
            "collective_down": -0.4,
            "pedal": 0.0,
        },
        sacred_tongue_hybrid=SACRED_TONGUE_HYBRIDS[RecoveryType.STANDARD],
    ))

    # Vuichard: lateral cyclic + slight collective increase
    # Faster but less reliable in deep VRS
    vui_success = min(0.90, max(0.4, 0.8 + vrs_margin * 0.3))
    paths.append(RecoveryPath(
        recovery_type=RecoveryType.VUICHARD,
        success_probability=vui_success,
        altitude_loss_m=min(altitude_agl * 0.15, 80.0),
        time_to_recover_s=2.5 + abs(vrs_margin) * 2.0,
        control_inputs={
            "cyclic_lateral": 0.8,
            "collective_up": 0.15,
            "pedal_opposite": 0.3,
        },
        sacred_tongue_hybrid=SACRED_TONGUE_HYBRIDS[RecoveryType.VUICHARD],
    ))

    # Autorotation: full down collective → controlled descent → flare
    # Always available but highest altitude loss
    auto_success = min(0.85, max(0.5, altitude_agl / 300.0))
    paths.append(RecoveryPath(
        recovery_type=RecoveryType.AUTOROTATION,
        success_probability=auto_success,
        altitude_loss_m=min(altitude_agl * 0.6, 250.0),
        time_to_recover_s=8.0 + altitude_agl / 100.0,
        control_inputs={
            "collective_full_down": -1.0,
            "cyclic_neutral": 0.0,
            "flare_altitude_m": max(10, altitude_agl * 0.05),
        },
        sacred_tongue_hybrid=SACRED_TONGUE_HYBRIDS[RecoveryType.AUTOROTATION],
    ))

    # Tail rotor failure: creativity-axis dominant
    # ψ̇ = (Q_main - Q_tail) / I_z → uncontrolled yaw
    # Recovery: reduce collective + forward cyclic + running landing
    if tail_rotor_failed:
        # Success depends heavily on altitude and airspeed
        trf_success = min(0.80, max(0.35, altitude_agl / 250.0))
        if altitude_agl < 50:
            trf_success *= 0.6  # low altitude = very dangerous
        paths.append(RecoveryPath(
            recovery_type=RecoveryType.TAIL_ROTOR_FAILURE,
            success_probability=trf_success,
            altitude_loss_m=min(altitude_agl * 0.8, 300.0),
            time_to_recover_s=10.0 + altitude_agl / 80.0,
            control_inputs={
                "collective_reduce": -0.8,
                "cyclic_forward": 0.6,
                "pedal_opposite": 1.0,
                "autorotative_entry": 1.0,
            },
            sacred_tongue_hybrid=SACRED_TONGUE_HYBRIDS[RecoveryType.TAIL_ROTOR_FAILURE],
        ))

    # Monty Hall selection: if multipath has forks, the "switch" choice
    # gets the advantage
    if multipath and multipath.forks:
        n_forks = len(multipath.forks)
        advantage = multipath.monty_hall_advantage
        # Sort by severity (lowest = best)
        paths.sort(key=lambda p: p.severity)
        # The "stay" choice is the first instinct (standard)
        # The "switch" choice (Monty Hall) favors the path with best
        # expected outcome — usually Vuichard
        if len(paths) >= 2:
            # Mark the best non-obvious path as Monty Hall selected
            paths[0].monty_hall_selected = True
            # Boost its success by the advantage factor
            paths[0].success_probability = min(
                0.99,
                paths[0].success_probability * (1 + advantage * 0.1)
            )

    return paths


# ---------------------------------------------------------------------------
# Tail Rotor Failure Dynamics
# ---------------------------------------------------------------------------

@dataclass
class TailRotorState:
    """Tail rotor failure dynamics.

    When the tail rotor fails, main rotor torque Q_main is uncompensated:
        ψ̇ = (Q_main - Q_tail) / I_z

    With Q_tail = 0 (total failure):
        ψ̇ = Q_main / I_z → uncontrolled yaw acceleration

    Recovery: reduce collective (lowers Q_main), forward cyclic (directional
    control via airflow), enter autorotation if needed.

    Maps to SCBE creativity axis (yaw = rudder = creativity).
    """
    failed: bool = False
    q_main_nm: float = 0.0          # main rotor torque (N·m)
    q_tail_nm: float = 0.0          # tail rotor torque (N·m), 0 if failed
    i_z_kgm2: float = 10000.0      # yaw moment of inertia (kg·m²)
    yaw_rate_dps: float = 0.0       # current yaw rate (deg/s)

    @property
    def yaw_acceleration_rads2(self) -> float:
        """ψ̈ = (Q_main - Q_tail) / I_z — yaw angular acceleration."""
        if self.i_z_kgm2 < 1e-6:
            return 0.0
        return (self.q_main_nm - self.q_tail_nm) / self.i_z_kgm2

    @property
    def net_torque_nm(self) -> float:
        """Uncompensated torque causing yaw."""
        return self.q_main_nm - self.q_tail_nm

    @property
    def is_controllable(self) -> bool:
        """Yaw rate below 90 deg/s is marginally controllable."""
        return abs(self.yaw_rate_dps) < 90.0

    def to_dict(self) -> dict:
        return {
            "failed": self.failed,
            "q_main_nm": round(self.q_main_nm, 1),
            "q_tail_nm": round(self.q_tail_nm, 1),
            "net_torque_nm": round(self.net_torque_nm, 1),
            "yaw_accel_rad_s2": round(self.yaw_acceleration_rads2, 4),
            "yaw_rate_dps": round(self.yaw_rate_dps, 1),
            "i_z_kgm2": round(self.i_z_kgm2, 1),
            "is_controllable": self.is_controllable,
        }


def compute_tail_rotor_state(
    rotor: RotorState,
    creativity_deviation: float,
) -> TailRotorState:
    """Derive tail rotor failure state from rotor dynamics + creativity axis.

    Large creativity deviation (|dev| > 0.10) triggers tail rotor failure.
    The creativity axis IS the yaw/rudder control — when it deviates hard,
    the anti-torque system is overwhelmed.

    Q_main ∝ rotor power (P = T·v_i → torque = P/Ω)
    Q_tail ∝ pedal authority (0 if failed)
    """
    # Main rotor torque from power: Q = P / Ω
    power = rotor.induced_power
    omega = rotor.omega
    q_main = power / omega if omega > 1e-3 else 0.0

    # Tail rotor failure if creativity axis deviates beyond threshold
    failed = abs(creativity_deviation) > 0.10

    # If not failed, tail rotor provides counter-torque
    q_tail = 0.0 if failed else q_main * 0.95  # 95% compensation normally

    # Yaw rate builds from uncompensated torque (simplified 1-step integration)
    i_z = 10000.0  # typical UH-60 yaw inertia
    yaw_accel = (q_main - q_tail) / i_z
    yaw_rate_dps = math.degrees(yaw_accel) * 2.0  # ~2 seconds of buildup

    return TailRotorState(
        failed=failed,
        q_main_nm=q_main,
        q_tail_nm=q_tail,
        i_z_kgm2=i_z,
        yaw_rate_dps=yaw_rate_dps,
    )


# ---------------------------------------------------------------------------
# Pacejka Tire Model (ground operations)
# ---------------------------------------------------------------------------

@dataclass
class PacejkaTireState:
    """Pacejka 'Magic Formula' tire model for ground operations.

    F = D · sin(C · arctan(B·slip - E·(B·slip - arctan(B·slip))))

    Where:
        B = stiffness factor
        C = shape factor (1.9 for lateral, 1.65 for longitudinal)
        D = peak force (μ · F_z, friction × normal load)
        E = curvature factor (-0.5 to 0.5 typical)
        slip = slip ratio (longitudinal) or slip angle (lateral)

    Maps to SCBE ground-state (n=0, the egg):
        Tire grip = stability boundary
        Slip angle = deviation from intended path (trit deviation)
        Peak force = maximum controllable force before breakaway
        Breakaway = the VRS of ground ops (sudden loss of control)

    Real coefficients from SAE J2452 / Pacejka "Tire and Vehicle Dynamics".
    """
    slip: float = 0.0               # slip ratio or angle (rad)
    normal_load_n: float = 20000.0  # F_z (N) — weight on tire
    mu_peak: float = 0.85           # peak friction coefficient (dry asphalt)
    b_stiffness: float = 10.0       # cornering stiffness factor
    c_shape: float = 1.9            # shape factor (lateral)
    e_curvature: float = -0.1       # curvature factor

    @property
    def d_peak_force(self) -> float:
        """D = μ · F_z — peak lateral force (N)."""
        return self.mu_peak * self.normal_load_n

    @property
    def lateral_force(self) -> float:
        """F = D·sin(C·arctan(B·s - E·(B·s - arctan(B·s)))) — Pacejka Magic Formula."""
        bs = self.b_stiffness * self.slip
        inner = bs - self.e_curvature * (bs - math.atan(bs))
        return self.d_peak_force * math.sin(self.c_shape * math.atan(inner))

    @property
    def grip_ratio(self) -> float:
        """How much of peak grip is being used: |F| / D.
        1.0 = at peak, >1.0 impossible (capped), <1.0 = margin available.
        """
        d = self.d_peak_force
        if d < 1e-6:
            return 0.0
        return min(1.0, abs(self.lateral_force) / d)

    @property
    def is_sliding(self) -> bool:
        """Past peak grip — tire is sliding (breakaway)."""
        return self.grip_ratio > 0.95

    def to_dict(self) -> dict:
        return {
            "slip_rad": round(self.slip, 4),
            "slip_deg": round(math.degrees(self.slip), 2),
            "normal_load_n": round(self.normal_load_n, 1),
            "mu_peak": self.mu_peak,
            "d_peak_force_n": round(self.d_peak_force, 1),
            "lateral_force_n": round(self.lateral_force, 1),
            "grip_ratio": round(self.grip_ratio, 4),
            "is_sliding": self.is_sliding,
            "b_stiffness": self.b_stiffness,
            "c_shape": self.c_shape,
            "e_curvature": self.e_curvature,
        }


def compute_pacejka_state(
    trit_structure_dev: float,
    mass_kg: float = 2000.0,
) -> PacejkaTireState:
    """Map trit structure deviation to Pacejka tire state.

    On the ground (n=0, the egg), structure deviation = steering input.
    The tire model determines if the ground vehicle maintains control
    or breaks away (the ground-state equivalent of VRS).

    slip_angle ∝ structure deviation (steering beyond grip = breakaway)
    normal_load = mass × g
    """
    # Slip angle from structure deviation: max dev 0.15 → ~12° slip
    slip_rad = trit_structure_dev * (math.radians(12.0) / 0.15)
    slip_rad = max(-math.radians(20), min(math.radians(20), slip_rad))

    normal_load = mass_kg * G_ACCEL

    return PacejkaTireState(
        slip=slip_rad,
        normal_load_n=normal_load,
    )


# ---------------------------------------------------------------------------
# Flight Dynamics State (combines 6-DOF + optional rotor)
# ---------------------------------------------------------------------------

@dataclass
class FlightDynamicsState:
    """Complete flight dynamics state derived from QHO bundle.

    The mapping from quantum to flight:
        QHO energy → kinetic energy (½mV²)
        Excitation level → altitude energy state
        Trit structure → pitch angle (elevator)
        Trit stability → roll angle (aileron)
        Trit creativity → yaw angle (rudder)
        Polymorphic forks → recovery path options
        Acoustic infra → engine idle / ground ops
        Acoustic audible → cruise power
        Acoustic ultra → max power / afterburner
        Visual vector → 6-gauge instrument panel
    """
    sixdof: SixDOFState
    rotor: Optional[RotorState] = None
    tail_rotor: Optional[TailRotorState] = None
    pacejka: Optional[PacejkaTireState] = None
    recovery_paths: List[RecoveryPath] = field(default_factory=list)
    flight_regime: str = "cruise"    # ground / takeoff / cruise / descent / stall / vrs / tail_rotor_failure
    power_state: str = "cruise"      # idle / cruise / max
    envelope_margin: float = 1.0     # 1.0 = center of envelope, 0.0 = at limit

    @property
    def total_energy_j(self) -> float:
        """Total mechanical energy = KE + PE.
        KE = ½mV², PE = mgh (using unit mass for normalization).
        """
        ke = 0.5 * self.sixdof.airspeed ** 2
        pe = G_ACCEL * max(0, self.sixdof.altitude)
        return ke + pe

    @property
    def specific_energy(self) -> float:
        """Specific energy (energy per unit mass) in m²/s²."""
        return self.total_energy_j

    @property
    def is_in_vrs(self) -> bool:
        """True if in vortex ring state (helicopter only)."""
        return self.flight_regime == "vrs"

    @property
    def best_recovery(self) -> Optional[RecoveryPath]:
        """Best available recovery path (lowest severity)."""
        if not self.recovery_paths:
            return None
        return min(self.recovery_paths, key=lambda p: p.severity)

    def to_dict(self) -> dict:
        result = {
            "sixdof": self.sixdof.to_dict(),
            "flight_regime": self.flight_regime,
            "power_state": self.power_state,
            "total_energy_j_per_kg": round(self.total_energy_j, 2),
            "specific_energy_m2s2": round(self.specific_energy, 2),
            "envelope_margin": round(self.envelope_margin, 4),
        }
        if self.rotor:
            result["rotor"] = self.rotor.to_dict()
        if self.tail_rotor:
            result["tail_rotor"] = self.tail_rotor.to_dict()
        if self.pacejka:
            result["pacejka"] = self.pacejka.to_dict()
        if self.recovery_paths:
            result["recovery_paths"] = [p.to_dict() for p in self.recovery_paths]
            best = self.best_recovery
            if best:
                result["best_recovery"] = best.to_dict()
        return result


# ---------------------------------------------------------------------------
# QHO → Flight Dynamics Mapper
# ---------------------------------------------------------------------------

def qho_to_flight_state(
    trit: TritSignal,
    multipath: MultiPathRecord,
    mean_excitation: float,
    max_excitation: int,
    acoustic_infra: float,
    acoustic_audible: float,
    acoustic_ultra: float,
    is_rotorcraft: bool = False,
) -> FlightDynamicsState:
    """Map quantum frequency bundle parameters to flight dynamics state.

    This is the bridge between QHO physics and aerodynamics:

    1. Excitation → airspeed (higher excitation = more energy = faster)
    2. Trit deviations → control surface deflections → attitude
    3. Acoustic bands → power state
    4. Polymorphic forks → available recovery paths
    5. Governance cost → envelope constraint
    """
    # --- Airspeed from excitation ---
    # n=0 → 30 m/s (stall speed), n=7 → 200 m/s (high speed)
    # V = V_stall + (V_max - V_stall) × (n/7)
    v_stall = 30.0    # m/s (~58 kt)
    v_max = 200.0      # m/s (~389 kt)
    airspeed = v_stall + (v_max - v_stall) * (mean_excitation / 7.0)

    # --- Altitude from max excitation ---
    # Higher max excitation = higher energy state = higher altitude
    # n=0 → 0m (ground), n=7 → 10000m (FL330)
    altitude = max_excitation / 7.0 * 10000.0

    # --- Attitude from trit deviations ---
    # Structure → pitch: positive deviation = nose up
    # Stability → roll: positive deviation = right bank
    # Creativity → yaw: positive deviation = right yaw
    max_angle_deg = 30.0  # maximum deflection mapping

    pitch_deg = trit.dev_structure / 0.15 * max_angle_deg
    pitch_deg = max(-max_angle_deg, min(max_angle_deg, pitch_deg))

    roll_deg = trit.dev_stability / 0.15 * max_angle_deg
    roll_deg = max(-max_angle_deg, min(max_angle_deg, roll_deg))

    yaw_deg = trit.dev_creativity / 0.15 * max_angle_deg
    yaw_deg = max(-max_angle_deg, min(max_angle_deg, yaw_deg))

    # Build 6-DOF
    theta_rad = math.radians(pitch_deg)
    phi_rad = math.radians(roll_deg)
    psi_rad = math.radians(yaw_deg)

    # Decompose airspeed into body-frame components
    u = airspeed * math.cos(theta_rad) * math.cos(psi_rad)
    v_body = airspeed * math.sin(psi_rad)  # sideslip from yaw
    w = airspeed * math.sin(theta_rad)     # AoA from pitch

    # Angular rates from trit deviation magnitude (more deviation = more dynamic)
    q_rate = trit.dev_structure * 2.0   # pitch rate ∝ structure deviation
    p_rate = trit.dev_stability * 2.0   # roll rate ∝ stability deviation
    r_rate = trit.dev_creativity * 2.0  # yaw rate ∝ creativity deviation

    sixdof = SixDOFState(
        x=0.0, y=0.0, z=altitude,
        u=u, v=v_body, w=w,
        phi=phi_rad, theta=theta_rad, psi=psi_rad,
        p=p_rate, q=q_rate, r=r_rate,
    )

    # --- Power state from acoustic bands ---
    if acoustic_ultra > 0.4:
        power_state = "max"
    elif acoustic_infra > 0.5:
        power_state = "idle"
    else:
        power_state = "cruise"

    # --- Flight regime ---
    if altitude < 10:
        regime = "ground"
    elif sixdof.is_stalled:
        regime = "stall"
    elif mean_excitation < 1.0:
        regime = "descent"
    elif mean_excitation > 5.0:
        regime = "climb"
    else:
        regime = "cruise"

    # --- Rotor dynamics (if rotorcraft) ---
    rotor = None
    tail_rotor_state = None
    if is_rotorcraft:
        # RPM from dominant tongue frequency × excitation scaling
        base_rpm = 258.0  # nominal UH-60
        rpm_scale = 0.8 + 0.4 * (mean_excitation / 7.0)
        rotor_rpm = base_rpm * rpm_scale

        # Collective from mean excitation (higher = more pitch = more thrust)
        collective = 5.0 + mean_excitation * 1.5  # 5° to 15.5°

        # Cyclic from trit deviations
        cyclic_lat = roll_deg * 0.3   # lateral cyclic ∝ roll demand
        cyclic_lon = pitch_deg * 0.3  # longitudinal cyclic ∝ pitch demand

        rotor = RotorState(
            rotor_rpm=rotor_rpm,
            collective_deg=collective,
            cyclic_lat_deg=cyclic_lat,
            cyclic_lon_deg=cyclic_lon,
        )

        # Tail rotor failure detection from creativity axis
        tail_rotor_state = compute_tail_rotor_state(rotor, trit.dev_creativity)
        if tail_rotor_state.failed:
            regime = "tail_rotor_failure"

        # Check VRS
        # Descent rate = negative w component
        descent_rate = max(0, -sixdof.w)
        vrs_m = rotor.vrs_margin(descent_rate)
        if vrs_m <= 0 and regime != "tail_rotor_failure":
            regime = "vrs"

    # --- Pacejka tire model (ground operations) ---
    pacejka = None
    if regime == "ground":
        pacejka = compute_pacejka_state(trit.dev_structure)

    # --- Envelope margin ---
    # Combine stall margin, G-load margin, altitude margin
    stall_m = max(0, sixdof.stall_margin)
    alt_m = 1.0 - max(0, altitude - 12000) / 3000  # margin above service ceiling
    alt_m = max(0, min(1, alt_m))
    envelope_margin = stall_m * alt_m

    # --- Recovery paths (if near envelope edge or VRS or tail rotor failure) ---
    recovery_paths = []
    tail_failed = tail_rotor_state.failed if tail_rotor_state else False
    if regime in ("stall", "vrs", "tail_rotor_failure") or envelope_margin < 0.3:
        vrs_m_val = 0.0
        if rotor:
            descent_rate = max(0, -sixdof.w)
            vrs_m_val = rotor.vrs_margin(descent_rate)
        recovery_paths = compute_recovery_paths(
            vrs_margin=vrs_m_val,
            altitude_agl=max(0, altitude),
            multipath=multipath,
            tail_rotor_failed=tail_failed,
        )

    return FlightDynamicsState(
        sixdof=sixdof,
        rotor=rotor,
        tail_rotor=tail_rotor_state,
        pacejka=pacejka,
        recovery_paths=recovery_paths,
        flight_regime=regime,
        power_state=power_state,
        envelope_margin=envelope_margin,
    )


# ---------------------------------------------------------------------------
# SFT Record Generation
# ---------------------------------------------------------------------------

def generate_flight_sft_record(
    text: str,
    flight: FlightDynamicsState,
    trit: TritSignal,
) -> dict:
    """Generate an SFT training record from flight dynamics analysis."""
    sixdof = flight.sixdof
    user_content = (
        f"Analyze the flight dynamics profile of this text:\n\n"
        f"\"{text[:200]}\"\n\n"
        f"Determine the flight regime, control state, energy level, "
        f"and any recovery paths."
    )

    # Control surface mapping from trit
    controls = (
        f"  Elevator (pitch): {math.degrees(sixdof.theta):.1f}° "
        f"← structure deviation {trit.dev_structure:+.4f}\n"
        f"  Aileron (roll): {math.degrees(sixdof.phi):.1f}° "
        f"← stability deviation {trit.dev_stability:+.4f}\n"
        f"  Rudder (yaw): {math.degrees(sixdof.psi):.1f}° "
        f"← creativity deviation {trit.dev_creativity:+.4f}"
    )

    recovery_text = ""
    if flight.recovery_paths:
        best = flight.best_recovery
        recovery_text = (
            f"\n\n**Recovery paths available:** {len(flight.recovery_paths)}\n"
            + "\n".join(
                f"  {p.recovery_type}: P(success)={p.success_probability:.2f}, "
                f"alt loss={p.altitude_loss_m:.0f}m, time={p.time_to_recover_s:.1f}s"
                f"{' [MONTY HALL SWITCH]' if p.monty_hall_selected else ''}"
                for p in flight.recovery_paths
            )
            + (f"\nBest path: {best.recovery_type} "
               f"(severity={best.severity:.3f})" if best else "")
        )

    rotor_text = ""
    if flight.rotor:
        r = flight.rotor
        rotor_text = (
            f"\n\n**Rotor dynamics:**\n"
            f"  RPM: {r.rotor_rpm:.0f}, Ω: {r.omega:.1f} rad/s\n"
            f"  Thrust: {r.thrust:.0f} N, v_i: {r.induced_velocity:.1f} m/s\n"
            f"  Collective: {r.collective_deg:.1f}°, "
            f"Cyclic: lat={r.cyclic_lat_deg:.1f}° lon={r.cyclic_lon_deg:.1f}°"
        )

    assistant_content = (
        f"**Flight Dynamics Analysis**\n\n"
        f"Regime: {flight.flight_regime.upper()}\n"
        f"Power state: {flight.power_state}\n"
        f"Envelope margin: {flight.envelope_margin:.3f}\n\n"
        f"**6-DOF state:**\n"
        f"  Airspeed: {sixdof.airspeed:.1f} m/s ({sixdof.airspeed * 1.944:.0f} kt)\n"
        f"  Altitude: {sixdof.altitude:.0f} m ({sixdof.altitude * 3.281:.0f} ft)\n"
        f"  AoA: {math.degrees(sixdof.angle_of_attack):.1f}°, "
        f"stall margin: {sixdof.stall_margin:.3f}\n"
        f"  Dynamic pressure: {sixdof.dynamic_pressure:.0f} Pa\n\n"
        f"**Control surfaces** (trit → attitude):\n{controls}\n\n"
        f"**Energy:**\n"
        f"  Total specific energy: {flight.specific_energy:.0f} m²/s²\n"
        f"  KE: {0.5 * sixdof.airspeed**2:.0f} m²/s², "
        f"PE: {G_ACCEL * max(0, sixdof.altitude):.0f} m²/s²"
        f"{rotor_text}{recovery_text}"
    )

    return {
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "source": "flight_dynamics_generator",
            "record_type": "flight_dynamics_analysis",
            "flight_state": flight.to_dict(),
        },
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.crypto.trit_curriculum import compute_trit_signal
    from src.crypto.multipath_generator import compute_multipath
    from src.crypto.quantum_frequency_bundle import (
        compute_qho_state,
        compute_acoustic_signature,
    )

    test_texts = [
        "The aircraft climbed through broken clouds at flight level 250",
        "Vortex ring state onset as the helicopter descended into its own downwash",
        "Autorotation is the last resort when all engines fail simultaneously",
        "Steady level cruise at 35000 feet burning 2400 pounds per hour",
        "The stall warning horn blared as the nose pitched up beyond critical alpha",
        "Love is the only force that transcends dimension and time",
        "Ground effect reduces induced drag within one rotor diameter of the surface",
        "Post-quantum cryptography uses lattice-based assumptions for security",
    ]

    print("=" * 70)
    print("FLIGHT DYNAMICS PHYSICS LAYER")
    print("6-DOF + Rotor + VRS Recovery — QHO-grounded")
    print("=" * 70)
    print()

    for text in test_texts:
        trit = compute_trit_signal(text[:256])
        mp = compute_multipath(trit)
        qho = compute_qho_state(text, trit, mp)
        acoustic = compute_acoustic_signature(qho)

        # Alternate between fixed-wing and rotorcraft
        is_rotor = any(w in text.lower() for w in ["helicopter", "rotor", "autorotation", "vortex", "ground effect"])

        flight = qho_to_flight_state(
            trit=trit,
            multipath=mp,
            mean_excitation=qho.mean_excitation,
            max_excitation=qho.max_excitation,
            acoustic_infra=acoustic.infrasonic_power,
            acoustic_audible=acoustic.audible_power,
            acoustic_ultra=acoustic.ultrasonic_power,
            is_rotorcraft=is_rotor,
        )

        s = flight.sixdof
        print(f"  [{flight.flight_regime:>7}] {flight.power_state:>6}  "
              f"V={s.airspeed:.0f}m/s  alt={s.altitude:.0f}m  "
              f"AoA={math.degrees(s.angle_of_attack):.1f}deg  "
              f"stall={s.stall_margin:.2f}  "
              f"E={flight.specific_energy:.0f}J/kg")
        if flight.rotor:
            r = flight.rotor
            print(f"    rotor: T={r.thrust:.0f}N  v_i={r.induced_velocity:.1f}m/s  "
                  f"RPM={r.rotor_rpm:.0f}  coll={r.collective_deg:.1f}deg")
        if flight.recovery_paths:
            best = flight.best_recovery
            print(f"    recovery: {len(flight.recovery_paths)} paths, "
                  f"best={best.recovery_type} P={best.success_probability:.2f}"
                  f"{' [MH]' if best.monty_hall_selected else ''}")
        print(f"    text: {text[:60]}")
        print()

    print("=" * 70)
