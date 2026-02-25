class_name Creature
extends Resource

## Base creature with 21D state vector slice.
## Pokémon-style creature governed by SCBE flux and behavioral alignment.
## Evolution is NOT level-based — it's driven by player choices + rho_e stability.

@export var creature_id: String = ""
@export var display_name: String = ""
@export var form_index: int = 0          # Current evolution form (0=baby, 1=rookie, 2=champion, 3=ultimate)
@export var element: String = "neutral"  # KO/AV/RU/CA/UM/DR tongue affinity
@export var hp: float = 100.0
@export var max_hp: float = 100.0
@export var attack: float = 10.0
@export var defense: float = 10.0
@export var speed: float = 10.0

# 21D state: first 9 = SCBE xi vector, next 6 = tongue affinities, last 6 = behavioral
var state_21d: Array[float] = []

# Behavioral accumulator — player choices shift this
var behavior_score: float = 0.0      # -1.0 (adversarial) to +1.0 (aligned)
var rho_e: float = 0.0               # Entropic divergence (must stay < 5.0 for evolution)
var flux_nu: float = 0.0             # Current evolution flux

# Evolution history
var evolution_chain: Array[String] = []
var hatched_from_egg: bool = false

# Combat moves (max 4, Pokémon-style)
var moves: Array[Dictionary] = []

func _init():
	state_21d.resize(21)
	state_21d.fill(0.0)

func get_form_name() -> String:
	var forms := ["Baby", "Rookie", "Champion", "Ultimate"]
	return forms[clampi(form_index, 0, 3)]

func apply_choice_delta(choice_vector: Array[float]):
	"""Player choices perturb the 21D state — this drives evolution."""
	for i in range(mini(choice_vector.size(), 21)):
		state_21d[i] += choice_vector[i]
	_recompute_rho_e()

func _recompute_rho_e():
	"""Entropic divergence from safe manifold center."""
	var sum_sq := 0.0
	for v in state_21d:
		sum_sq += v * v
	rho_e = sqrt(sum_sq)

func can_evolve() -> bool:
	"""Evolution requires low entropy + positive behavior."""
	return rho_e < 5.0 and behavior_score > 0.3 and form_index < 3

func can_de_evolve() -> bool:
	"""High entropy or adversarial behavior causes de-evolution."""
	return rho_e > 5.0 or behavior_score < -0.5

func get_tongue_affinities() -> Dictionary:
	"""Dimensions 9-14 map to Sacred Tongue weights."""
	return {
		"KO": state_21d[9],
		"AV": state_21d[10],
		"RU": state_21d[11],
		"CA": state_21d[12],
		"UM": state_21d[13],
		"DR": state_21d[14]
	}

func to_training_dict() -> Dictionary:
	"""Serialize for HF training data export."""
	return {
		"creature_id": creature_id,
		"form": get_form_name(),
		"element": element,
		"state_21d": state_21d,
		"behavior_score": behavior_score,
		"rho_e": rho_e,
		"moves": moves,
		"evolution_chain": evolution_chain
	}
