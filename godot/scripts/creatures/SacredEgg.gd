class_name SacredEgg
extends Node3D

## Sacred Egg — hatches into a creature based on accumulated player choices.
## Layer 7: Phase modulation determines which creature form emerges.
## The egg "observes" player behavior from the moment Marcus gives it.

signal egg_hatched(creature: Creature)
signal egg_pulse(rho_e: float, behavior: float)

@export var egg_id: String = "sacred_egg_001"

# Accumulated behavior from player actions while carrying the egg
var _behavior_accumulator: float = 0.0
var _choice_history: Array[Dictionary] = []
var _state_21d: Array[float] = []
var _hatch_threshold: float = 10.0   # Total positive choices needed to hatch
var _is_hatched: bool = false

# Evolution table: behavior range → creature_id
var _hatch_table: Array[Dictionary] = [
	{"min": 0.8,  "creature": "luminos",    "element": "DR", "desc": "Pure light guardian"},
	{"min": 0.4,  "creature": "verdantis",  "element": "CA", "desc": "Nature healer"},
	{"min": 0.0,  "creature": "cipherling", "element": "RU", "desc": "Balanced cipher fox"},
	{"min": -0.5, "creature": "umbraxis",   "element": "UM", "desc": "Shadow trickster"},
	{"min": -1.0, "creature": "voidmaw",    "element": "KO", "desc": "Chaotic void beast"},
]

func _ready():
	_state_21d.resize(21)
	_state_21d.fill(0.0)
	add_to_group("sacred_egg")

func record_choice(choice: Dictionary):
	"""Called whenever player makes a meaningful choice while carrying the egg."""
	if _is_hatched:
		return
	_choice_history.append(choice)
	var weight: float = choice.get("moral_weight", 0.0)
	_behavior_accumulator += weight
	# Perturb 21D state
	if choice.has("state_delta"):
		for i in range(mini(choice.state_delta.size(), 21)):
			_state_21d[i] += choice.state_delta[i]
	_check_hatch_ready()
	var rho_e := _compute_rho_e()
	egg_pulse.emit(rho_e, _normalized_behavior())

func _normalized_behavior() -> float:
	if _choice_history.is_empty():
		return 0.0
	return clampf(_behavior_accumulator / maxf(_choice_history.size(), 1.0), -1.0, 1.0)

func _compute_rho_e() -> float:
	var sum_sq := 0.0
	for v in _state_21d:
		sum_sq += v * v
	return sqrt(sum_sq)

func _check_hatch_ready():
	if _choice_history.size() >= _hatch_threshold:
		_try_hatch()

func _try_hatch():
	if _is_hatched:
		return
	_is_hatched = true
	var behavior := _normalized_behavior()
	var creature := _determine_creature(behavior)
	creature.hatched_from_egg = true
	creature.behavior_score = behavior
	creature.state_21d = _state_21d.duplicate()
	creature.evolution_chain.append(creature.creature_id + "_baby")

	# Log for training
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("egg_hatched", {
			"egg_id": egg_id,
			"creature": creature.creature_id,
			"behavior": behavior,
			"rho_e": _compute_rho_e(),
			"choices_count": _choice_history.size()
		})

	egg_hatched.emit(creature)

func _determine_creature(behavior: float) -> Creature:
	"""Walk the hatch table — first match wins (sorted high→low)."""
	var c := Creature.new()
	for entry in _hatch_table:
		if behavior >= entry.min:
			c.creature_id = entry.creature
			c.display_name = entry.creature.capitalize()
			c.element = entry.element
			break
	if c.creature_id == "":
		c.creature_id = "cipherling"
		c.display_name = "Cipherling"
		c.element = "RU"
	return c

func get_visual_hint() -> Color:
	"""Egg glows based on accumulated behavior — UI feedback."""
	var b := _normalized_behavior()
	if b > 0.5:
		return Color(0.9, 0.95, 1.0)   # Bright white-blue (aligned)
	elif b > 0.0:
		return Color(0.6, 0.9, 0.6)    # Green (positive)
	elif b > -0.5:
		return Color(0.9, 0.7, 0.3)    # Amber (neutral-risky)
	else:
		return Color(0.6, 0.1, 0.1)    # Dark red (adversarial)
