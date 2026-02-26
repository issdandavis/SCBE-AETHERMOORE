## CanonicalState — 21D state vector for Seal Entities (companions)
##
## Block A: Tongue Position (R^6) — slots 0-5
## Block B: Phase Angles (R^6) — slots 6-11
## Block C: Telemetry (R^9) — slots 12-20
##   [12] flux → Speed
##   [13] coherence_s → Insight
##   [14] coherence_bi → Emotional state
##   [15] coherence_tri → Perception
##   [16] risk → Risk Tolerance
##   [17] entropy_rate → Entropy Affinity
##   [18] stabilization → Resilience
##   [19] radius r → Proof Power
##   [20] harmonic_energy → Authority

class_name CanonicalState
extends RefCounted

const DIM: int = 21

# Full 21D vector
var state: Array[float] = []

# Evolution thresholds at radius r
const EVOLUTION_THRESHOLDS: Array[float] = [0.3, 0.5, 0.7, 0.85, 0.95]
const INSTABILITY_THRESHOLD: float = 0.95


func _init(initial_state: Array[float] = []) -> void:
	if initial_state.size() == DIM:
		state = initial_state.duplicate()
	else:
		state = []
		for i in range(DIM):
			state.append(0.0)


# -- Block accessors --

## Tongue position (R^6): what elemental alignment
func get_tongue_position() -> Array[float]:
	return state.slice(0, 6)

func set_tongue_position(pos: Array[float]) -> void:
	for i in range(mini(6, pos.size())):
		state[i] = pos[i]


## Phase angles (R^6): combat timing, pitch
func get_phase_angles() -> Array[float]:
	return state.slice(6, 12)

func set_phase_angles(phases: Array[float]) -> void:
	for i in range(mini(6, phases.size())):
		state[6 + i] = phases[i]


## Telemetry accessors
func get_flux() -> float: return state[12]
func get_insight() -> float: return state[13]
func get_emotional() -> float: return state[14]
func get_perception() -> float: return state[15]
func get_risk_tolerance() -> float: return state[16]
func get_entropy_affinity() -> float: return state[17]
func get_resilience() -> float: return state[18]
func get_proof_power() -> float: return state[19]
func get_authority() -> float: return state[20]

func set_flux(v: float) -> void: state[12] = v
func set_insight(v: float) -> void: state[13] = v
func set_emotional(v: float) -> void: state[14] = v
func set_perception(v: float) -> void: state[15] = v
func set_risk_tolerance(v: float) -> void: state[16] = v
func set_entropy_affinity(v: float) -> void: state[17] = v
func set_resilience(v: float) -> void: state[18] = v
func set_proof_power(v: float) -> void: state[19] = v
func set_authority(v: float) -> void: state[20] = v


# -- Derived stats --

## Compute radius r = ||tongue_position|| (L2 norm of Block A)
func radius() -> float:
	var sum_sq := 0.0
	for i in range(6):
		sum_sq += state[i] * state[i]
	return sqrt(sum_sq)


## Get evolution stage index (0-4 based on radius thresholds)
func evolution_stage_index() -> int:
	var r := radius()
	for i in range(EVOLUTION_THRESHOLDS.size() - 1, -1, -1):
		if r >= EVOLUTION_THRESHOLDS[i]:
			return i + 1
	return 0


## Check if over-evolution risk is present (r > 0.95)
func is_unstable() -> bool:
	return radius() > INSTABILITY_THRESHOLD


## Dominant tongue index (highest value in Block A)
func dominant_tongue() -> int:
	var max_idx := 0
	for i in range(1, 6):
		if state[i] > state[max_idx]:
			max_idx = i
	return max_idx


## Drift level: distance from nearest stable alignment axis
func drift_level() -> float:
	var pos := get_tongue_position()
	var r := radius()
	if r < 0.001:
		return 0.0
	# Drift = 1 - (max component / radius)
	var max_comp := 0.0
	for v in pos:
		max_comp = maxf(max_comp, absf(v))
	return 1.0 - (max_comp / r)


## Seal integrity (HP equivalent) derived from resilience + radius
func seal_integrity() -> float:
	return clampf(get_resilience() * (1.0 - drift_level()) * 100.0, 0.0, 100.0)


## Combat speed derived from flux
func combat_speed() -> float:
	return get_flux() * 10.0 + 5.0


## Serialize to Dictionary for SCBE backend
func to_dict() -> Dictionary:
	return {
		"state": state.duplicate(),
		"radius": radius(),
		"dominant_tongue": dominant_tongue(),
		"evolution_stage": evolution_stage_index(),
		"drift": drift_level(),
		"is_unstable": is_unstable(),
	}


## Load from Dictionary
static func from_dict(data: Dictionary) -> CanonicalState:
	if data.has("state"):
		return CanonicalState.new(data["state"])
	return CanonicalState.new()


## Create a starter Crysling state (CA-dominant)
static func create_crysling() -> CanonicalState:
	var cs := CanonicalState.new()
	# Block A: CA-dominant tongue position
	cs.state[3] = 0.4   # CA primary
	cs.state[0] = 0.05  # Trace KO
	cs.state[4] = 0.1   # Some UM
	# Block B: Default phase angles
	cs.state[6] = 0.0
	cs.state[7] = 0.5
	cs.state[8] = 0.2
	# Block C: Starter telemetry
	cs.set_flux(0.3)          # Moderate speed
	cs.set_insight(0.4)       # Good analysis
	cs.set_perception(0.2)    # Low perception
	cs.set_risk_tolerance(0.1)
	cs.set_entropy_affinity(0.15)
	cs.set_resilience(0.5)    # Decent toughness
	cs.set_proof_power(0.35)  # Moderate proof power
	cs.set_authority(0.1)     # Low governance weight
	return cs
