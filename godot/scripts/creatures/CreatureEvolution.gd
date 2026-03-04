class_name CreatureEvolution
extends Node

## Creature Evolution Tree — Digimon-style branching based on behavior + tongue affinity.
## NOT level-based. Driven by Layer 7 flux, rho_e, and player choices.
## Each creature has 4 forms: Baby → Rookie → Champion → Ultimate.
## Branch at each stage depends on dominant Sacred Tongue affinity.

signal evolution_available(creature: Creature, options: Array[Dictionary])

# Evolution tree: creature_id → form_index → Array of possible evolutions
# Each evolution requires: min_behavior, dominant_tongue, and rho_e < threshold
var _tree: Dictionary = {}

func _ready():
	add_to_group("evolution_tree")
	_load_tree()

func _load_tree():
	"""Load evolution data from JSON (or use built-in defaults)."""
	var f := FileAccess.open("res://data/creatures/evolution_tree.json", FileAccess.READ)
	if f:
		_tree = JSON.parse_string(f.get_as_text())
		return
	# Fallback defaults
	_tree = _default_tree()

func check_evolution(creature: Creature) -> Array[Dictionary]:
	"""Return available evolution paths for a creature."""
	var paths: Array[Dictionary] = []
	var branches: Array = _tree.get(creature.creature_id, {}).get(str(creature.form_index), [])

	for branch in branches:
		if _meets_requirements(creature, branch):
			paths.append(branch)

	if not paths.is_empty():
		evolution_available.emit(creature, paths)
	return paths

func evolve(creature: Creature, target_id: String) -> bool:
	"""Execute evolution to a specific target form."""
	var paths := check_evolution(creature)
	for path in paths:
		if path.get("target_id", "") == target_id:
			creature.creature_id = target_id
			creature.display_name = path.get("target_name", target_id.capitalize())
			creature.form_index += 1
			creature.evolution_chain.append(target_id)
			# Apply stat changes
			creature.max_hp *= path.get("hp_mult", 1.25)
			creature.hp = creature.max_hp
			creature.attack *= path.get("atk_mult", 1.2)
			creature.defense *= path.get("def_mult", 1.2)
			creature.speed *= path.get("spd_mult", 1.15)
			# Learn new move if provided
			if path.has("new_move"):
				if creature.moves.size() < 4:
					creature.moves.append(path.new_move)
			_log_evolution(creature, target_id)
			return true
	return false

func _meets_requirements(creature: Creature, branch: Dictionary) -> bool:
	var min_behavior: float = branch.get("min_behavior", 0.0)
	var max_rho_e: float = branch.get("max_rho_e", 5.0)
	var required_tongue: String = branch.get("dominant_tongue", "")

	if creature.behavior_score < min_behavior:
		return false
	if creature.rho_e > max_rho_e:
		return false
	if required_tongue != "":
		var affinities := creature.get_tongue_affinities()
		var dominant := _get_dominant_tongue(affinities)
		if dominant != required_tongue:
			return false
	return true

func _get_dominant_tongue(affinities: Dictionary) -> String:
	var best_tongue := ""
	var best_val := -999.0
	for tongue in affinities:
		if affinities[tongue] > best_val:
			best_val = affinities[tongue]
			best_tongue = tongue
	return best_tongue

func _log_evolution(creature: Creature, target: String):
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("creature_evolution", {
			"creature": creature.creature_id,
			"target": target,
			"form": creature.get_form_name(),
			"behavior": creature.behavior_score,
			"rho_e": creature.rho_e,
			"chain": creature.evolution_chain
		})

func _default_tree() -> Dictionary:
	return {
		"luminos": {
			"0": [
				{"target_id": "luminos_radiant", "target_name": "Radiant Luminos", "dominant_tongue": "DR", "min_behavior": 0.5, "max_rho_e": 3.0, "hp_mult": 1.3, "atk_mult": 1.1, "def_mult": 1.3, "spd_mult": 1.1},
				{"target_id": "luminos_swift", "target_name": "Swift Luminos", "dominant_tongue": "AV", "min_behavior": 0.3, "max_rho_e": 4.0, "hp_mult": 1.1, "atk_mult": 1.2, "def_mult": 1.1, "spd_mult": 1.4}
			],
			"1": [
				{"target_id": "luminos_champion", "target_name": "Luminos Champion", "min_behavior": 0.6, "max_rho_e": 2.5, "hp_mult": 1.3, "atk_mult": 1.3, "def_mult": 1.3, "spd_mult": 1.2}
			]
		},
		"verdantis": {
			"0": [
				{"target_id": "verdantis_bloom", "target_name": "Bloom Verdantis", "dominant_tongue": "CA", "min_behavior": 0.3, "max_rho_e": 4.0, "hp_mult": 1.4, "atk_mult": 1.0, "def_mult": 1.2, "spd_mult": 1.1},
				{"target_id": "verdantis_thorn", "target_name": "Thorn Verdantis", "dominant_tongue": "UM", "min_behavior": 0.0, "max_rho_e": 5.0, "hp_mult": 1.1, "atk_mult": 1.3, "def_mult": 1.1, "spd_mult": 1.2}
			]
		},
		"cipherling": {
			"0": [
				{"target_id": "cipher_sage", "target_name": "Cipher Sage", "dominant_tongue": "RU", "min_behavior": 0.4, "max_rho_e": 3.5, "hp_mult": 1.2, "atk_mult": 1.2, "def_mult": 1.2, "spd_mult": 1.2},
				{"target_id": "cipher_rogue", "target_name": "Cipher Rogue", "dominant_tongue": "KO", "min_behavior": -0.2, "max_rho_e": 5.0, "hp_mult": 1.0, "atk_mult": 1.4, "def_mult": 1.0, "spd_mult": 1.5}
			]
		},
		"umbraxis": {
			"0": [
				{"target_id": "umbra_shade", "target_name": "Umbra Shade", "dominant_tongue": "UM", "min_behavior": -0.3, "max_rho_e": 5.0, "hp_mult": 1.1, "atk_mult": 1.3, "def_mult": 1.2, "spd_mult": 1.3}
			]
		},
		"voidmaw": {
			"0": [
				{"target_id": "void_devourer", "target_name": "Void Devourer", "dominant_tongue": "KO", "min_behavior": -1.0, "max_rho_e": 5.0, "hp_mult": 1.5, "atk_mult": 1.5, "def_mult": 0.8, "spd_mult": 0.9}
			]
		}
	}
