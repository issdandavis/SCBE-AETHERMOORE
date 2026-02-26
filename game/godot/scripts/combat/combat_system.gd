## CombatSystem — Manages damage calculation, type advantage, transform verification
##
## GDD Section 5: Dual combat (overworld real-time + arena tactical)
## GDD Section 6: Math-as-monsters (transforms verified by SymPy oracle)
## Type advantage: Cl(4,0) bivector commutator, NOT rock-paper-scissors

extends Node

class_name CombatSystem

# -- Transform definitions (GDD Section 6.2) --

enum TransformType {
	NORMALIZE,
	SUBSTITUTE,
	COMPLETE_SQUARE,
	FACTOR,
	BOUND,
	INVARIANT_CHECK,
	CASE_SPLIT,
	CONTRADICTION_PROBE,
	DIFFERENTIATE,
	INTEGRATE,
	APPLY_THEOREM,
	CHECK_DOMAIN,
}

const TRANSFORM_DATA: Dictionary = {
	TransformType.NORMALIZE:          {"name": "Normalize",          "risk": "low",    "cost": 1,  "tongue": 0},
	TransformType.SUBSTITUTE:         {"name": "Substitute",         "risk": "medium", "cost": 2,  "tongue": 1},
	TransformType.COMPLETE_SQUARE:    {"name": "CompleteSquare",     "risk": "low",    "cost": 2,  "tongue": 3},
	TransformType.FACTOR:             {"name": "Factor",             "risk": "medium", "cost": 3,  "tongue": 3},
	TransformType.BOUND:              {"name": "Bound",              "risk": "low",    "cost": 2,  "tongue": 5},
	TransformType.INVARIANT_CHECK:    {"name": "InvariantCheck",     "risk": "low",    "cost": 1,  "tongue": 4},
	TransformType.CASE_SPLIT:         {"name": "CaseSplit",          "risk": "medium", "cost": 4,  "tongue": 2},
	TransformType.CONTRADICTION_PROBE:{"name": "ContradictionProbe", "risk": "high",   "cost": 5,  "tongue": 2},
	TransformType.DIFFERENTIATE:      {"name": "Differentiate",      "risk": "medium", "cost": 3,  "tongue": 3},
	TransformType.INTEGRATE:          {"name": "Integrate",          "risk": "high",   "cost": 5,  "tongue": 3},
	TransformType.APPLY_THEOREM:      {"name": "ApplyTheorem",       "risk": "varies", "cost": 3,  "tongue": 5},
	TransformType.CHECK_DOMAIN:       {"name": "CheckDomain",        "risk": "low",    "cost": 1,  "tongue": 4},
}

# SCBE cost multiplier based on risk history
var risk_history: Array[float] = []
const RISK_WINDOW: int = 10

# Signals
signal damage_calculated(source: String, target: String, amount: float, effective: bool)
signal transform_result(transform_name: String, valid: bool, reward: float)


## Calculate overworld melee damage with type advantage
func calculate_melee_damage(base_damage: float, attacker_tongue: int,
							defender_tongue: int, attacker_phase: Array[float],
							defender_phase: Array[float]) -> Dictionary:
	var advantage := TongueSystem.compute_advantage(
		attacker_tongue, defender_tongue, attacker_phase, defender_phase)

	# Damage multiplier: 0.5x to 1.5x based on advantage
	var multiplier := 1.0 + advantage * 0.5
	var final_damage := base_damage * multiplier

	var is_effective := advantage > 0.1

	return {
		"damage": final_damage,
		"multiplier": multiplier,
		"advantage": advantage,
		"effective": is_effective,
		"tongue_name": TongueSystem.TONGUE_NAMES[attacker_tongue],
	}


## Get SCBE cost for a transform (GDD Section 6.4)
## Higher cost for historically error-prone transforms
func get_transform_cost(transform_type: TransformType) -> float:
	var data: Dictionary = TRANSFORM_DATA[transform_type]
	var base_cost: float = float(data["cost"])

	# Historical risk multiplier
	var recent_failures := 0.0
	for risk in risk_history:
		recent_failures += risk
	var risk_multiplier := 1.0 + recent_failures * 0.2

	# Risk-based multiplier
	var risk_level: String = data["risk"]
	match risk_level:
		"high":
			base_cost *= 1.5
		"medium":
			base_cost *= 1.2
		_:
			pass

	return base_cost * risk_multiplier


## Record a transform result (updates risk history)
func record_transform_result(transform_type: TransformType, valid: bool, reward: float) -> void:
	var risk_value := 0.0 if valid else 1.0
	risk_history.append(risk_value)
	if risk_history.size() > RISK_WINDOW:
		risk_history.pop_front()

	var data: Dictionary = TRANSFORM_DATA[transform_type]
	transform_result.emit(data["name"], valid, reward)

	# Award tongue XP for the transform's tongue
	if valid:
		var tongue_idx: int = data["tongue"]
		GameState.gain_tongue_xp(tongue_idx, absf(reward) * 0.5)


## Calculate companion assist damage (GDD Section 5.1)
func calculate_assist_damage(base_damage: float, bond_level: int,
							companion_tongue: int, enemy_tongue: int,
							companion_phase: Array[float],
							enemy_phase: Array[float]) -> float:
	var assist_ratio := 0.0
	if bond_level >= 7:
		assist_ratio = 0.8  # Autonomous
	elif bond_level >= 5:
		assist_ratio = 0.6  # Fusion
	elif bond_level >= 3:
		assist_ratio = 0.3  # Tag team
	else:
		return 0.0

	var advantage := TongueSystem.compute_advantage(
		companion_tongue, enemy_tongue, companion_phase, enemy_phase)
	var multiplier := 1.0 + advantage * 0.5

	return base_damage * assist_ratio * multiplier


## Calculate formation bonus (GDD Section 5.2)
## Returns damage/defense modifiers based on formation and spectral gap
func get_formation_bonus(formation: String, spectral_gap: float) -> Dictionary:
	match formation:
		"storm":
			return {"damage_mult": 1.4, "defense_mult": 0.7, "required_gap": 0.0}
		"phalanx":
			if spectral_gap > 0.3:
				return {"damage_mult": 0.8, "defense_mult": 1.5, "required_gap": 0.3}
			return {"damage_mult": 0.9, "defense_mult": 1.0, "required_gap": 0.3}
		"lance":
			return {"damage_mult": 1.6, "defense_mult": 0.6, "required_gap": 0.3}
		"web":
			if spectral_gap > 0.6:
				return {"damage_mult": 0.9, "defense_mult": 1.3, "required_gap": 0.6}
			return {"damage_mult": 0.8, "defense_mult": 0.9, "required_gap": 0.6}
		_:
			return {"damage_mult": 1.0, "defense_mult": 1.0, "required_gap": 0.0}
