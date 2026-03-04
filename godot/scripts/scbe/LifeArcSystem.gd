class_name LifeArcSystem
extends Node

## Layer 7: Phase Modulation — Life-Sim Progression & Evolution Flux
## Drives youth → teen → adult arcs, creature evolution, career paths.
## Evolution is governed by SCBE flux ODE: unstable states snap back.

signal arc_progressed(arc_stage: String, result: Dictionary)
signal evolution_triggered(creature: Creature, new_form: int)
signal de_evolution_triggered(creature: Creature, reason: String)

# Arc durations (in-game days)
const ARC_DURATION := {
	"youth": 3,      # Days 1-3: starter village, egg, first dungeon
	"teen": 7,       # Days 4-10: academy, squad formation, career choice
	"adult": 14,     # Days 11-24: autonomous missions, world growth
}

# Flux parameters (Ornstein-Uhlenbeck)
const KAPPA := 0.18       # Mean reversion strength
const THETA := 0.0        # Long-term mean (safe center)
const SIGMA := 0.05       # Volatility
const RHO_E_MAX := 5.0    # Entropic ceiling — beyond this = de-evolution

var current_arc: String = "youth"
var arc_day: int = 0

func _ready():
	add_to_group("life_arc")

func advance_day(player_choices: Array[Dictionary], party: Array[Creature]):
	"""Called at end of each in-game day. Evolves flux for all party creatures."""
	arc_day += 1
	_check_arc_transition()

	for creature in party:
		var result := _process_creature_flux(creature, player_choices)
		if result.get("evolution", false):
			evolution_triggered.emit(creature, creature.form_index)
		elif result.get("de_evolution", false):
			de_evolution_triggered.emit(creature, result.get("reason", "instability"))

	arc_progressed.emit(current_arc, {"day": arc_day, "party_size": party.size()})

func _check_arc_transition():
	var duration: int = ARC_DURATION.get(current_arc, 999)
	if arc_day > duration:
		match current_arc:
			"youth":
				current_arc = "teen"
				arc_day = 1
			"teen":
				current_arc = "adult"
				arc_day = 1

func _process_creature_flux(creature: Creature, choices: Array[Dictionary]) -> Dictionary:
	"""Apply OU flux + choice perturbations. Check evolution/de-evolution."""
	# Ornstein-Uhlenbeck step
	var dt := 1.0  # 1 day
	var dW := randf_range(-1.0, 1.0) * sqrt(dt)
	creature.flux_nu += KAPPA * (THETA - creature.flux_nu) * dt + SIGMA * dW

	# Accumulate player choices as behavioral perturbations
	for choice in choices:
		var weight: float = choice.get("moral_weight", 0.0)
		creature.behavior_score = clampf(creature.behavior_score + weight * 0.1, -1.0, 1.0)
		if choice.has("state_delta"):
			creature.apply_choice_delta(choice.state_delta)

	# Recompute rho_e after perturbations
	creature._recompute_rho_e()

	# Evolution check
	if creature.can_evolve() and creature.flux_nu > 0.5:
		_evolve(creature)
		return {"evolution": true}

	# De-evolution check (governance snap)
	if creature.can_de_evolve():
		_de_evolve(creature)
		return {"de_evolution": true, "reason": "rho_e=%.2f behavior=%.2f" % [creature.rho_e, creature.behavior_score]}

	return {}

func _evolve(creature: Creature):
	"""Promote creature to next form. Log for training."""
	creature.form_index = mini(creature.form_index + 1, 3)
	creature.evolution_chain.append("%s_%s" % [creature.creature_id, creature.get_form_name().to_lower()])
	# Stat boost on evolution
	creature.max_hp *= 1.25
	creature.hp = creature.max_hp
	creature.attack *= 1.2
	creature.defense *= 1.2
	creature.speed *= 1.15

	_log("evolution", creature)

func _de_evolve(creature: Creature):
	"""Snap creature back one form. Governance enforcement."""
	if creature.form_index > 0:
		creature.form_index -= 1
		creature.max_hp *= 0.8
		creature.hp = minf(creature.hp, creature.max_hp)

	# Reset flux toward safe center
	creature.flux_nu *= 0.5
	creature.behavior_score = clampf(creature.behavior_score + 0.2, -1.0, 1.0)

	_log("de_evolution", creature)

func _log(event_type: String, creature: Creature):
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("layer7_%s" % event_type, creature.to_training_dict())

func simulate_life_arc(arc_stage: String, player_choices: Array[Dictionary]) -> Dictionary:
	"""Full arc simulation for training data generation."""
	var duration: int = ARC_DURATION.get(arc_stage, 3)
	var flux := 0.0
	for day in range(duration):
		var dW := randf_range(-1.0, 1.0)
		flux += KAPPA * (THETA - flux) * 1.0 + SIGMA * dW
		for choice in player_choices:
			flux += choice.get("moral_weight", 0.0) * 0.05

	var rho_e := absf(flux)
	if rho_e > RHO_E_MAX:
		return {"result": "DE_EVOLUTION", "message": "Instability — career snap", "rho_e": rho_e}
	return {"result": "PROGRESS", "flux": flux, "rho_e": rho_e, "arc": arc_stage}
