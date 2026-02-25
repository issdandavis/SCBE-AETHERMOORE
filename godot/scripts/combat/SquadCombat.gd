class_name SquadCombat
extends Node

## Layer 11: Polyhedral Hamiltonian Defense Manifold — Squad Path & Math Combat
## Math monsters = Hamiltonian path constraints on the squad formation graph.
## Squad members must maintain ds² continuity — broken paths = QUARANTINE.
## Combat = formal proof: player applies transform moves to solve math problems.

signal combat_started(problem: Dictionary)
signal combat_resolved(result: Dictionary)
signal squad_path_broken(member_idx: int, ds2: float)
signal transform_applied(move: Dictionary, valid: bool)

const DS2_MAX := 5.0   # Maximum geodesic distance between squad members
const MAX_MOVES := 10   # Move limit per encounter

# Transform moves available (Pokémon-style move list)
const TRANSFORM_MOVES := {
	"normalize": {
		"name": "Normalize",
		"desc": "Divide both sides to isolate the leading coefficient",
		"cost": 1,
		"tongue": "KO",
		"scbe_risk": 0.1
	},
	"complete_square": {
		"name": "Complete the Square",
		"desc": "Add (b/2)² to both sides",
		"cost": 2,
		"tongue": "RU",
		"scbe_risk": 0.2
	},
	"domain_check": {
		"name": "Domain Check",
		"desc": "Verify solution is in the valid domain",
		"cost": 1,
		"tongue": "CA",
		"scbe_risk": 0.05
	},
	"factor": {
		"name": "Factor",
		"desc": "Factor the expression into (x-a)(x-b) form",
		"cost": 2,
		"tongue": "AV",
		"scbe_risk": 0.15
	},
	"substitute": {
		"name": "Substitute",
		"desc": "Replace variable with expression",
		"cost": 2,
		"tongue": "UM",
		"scbe_risk": 0.3
	},
	"quadratic_formula": {
		"name": "Quadratic Formula",
		"desc": "Apply x = (-b ± √(b²-4ac)) / 2a",
		"cost": 3,
		"tongue": "DR",
		"scbe_risk": 0.4
	}
}

var _current_problem: Dictionary = {}
var _move_history: Array[Dictionary] = []
var _squad: Array[Creature] = []
var _moves_remaining: int = MAX_MOVES

func _ready():
	add_to_group("squad_combat")

func start_encounter(problem: Dictionary, squad: Array[Creature]):
	"""Begin a math monster encounter with the current squad."""
	_current_problem = problem
	_squad = squad
	_move_history = []
	_moves_remaining = MAX_MOVES

	_log("combat_start", {
		"problem": problem,
		"squad_size": squad.size(),
		"topic": problem.get("topic", "unknown")
	})
	combat_started.emit(problem)

func apply_move(move_id: String, creature_idx: int) -> Dictionary:
	"""Player selects a transform move from a creature's moveset."""
	if _moves_remaining <= 0:
		return _resolve("DEFEAT", "Out of moves")

	var move: Dictionary = TRANSFORM_MOVES.get(move_id, {})
	if move.is_empty():
		return {"valid": false, "reason": "Unknown move"}

	_moves_remaining -= 1

	# Check squad path integrity (Hamiltonian constraint)
	if not _check_squad_path():
		return _resolve("QUARANTINE", "Squad path broken — formation snap")

	# SCBE gate check via EventValidator
	var validator := get_tree().get_first_node_in_group("event_validator")
	if validator:
		var event := {
			"type": "combat_move",
			"choice": move_id,
			"creature": _squad[creature_idx].creature_id if creature_idx < _squad.size() else "none",
			"problem_id": _current_problem.get("id", "?")
		}
		var validation := validator.validate(event)
		if not validation.get("valid", false):
			return {"valid": false, "reason": "SCBE gate rejected: %s" % validation.get("reason", "?")}

	# Record the move
	var step := {
		"move_id": move_id,
		"move_name": move.name,
		"creature_idx": creature_idx,
		"moves_remaining": _moves_remaining,
		"before_expr": _current_problem.get("current_expr", ""),
	}
	_move_history.append(step)

	# Check if problem is solved (simplified — real check goes to Oracle)
	var solved := _check_solved(move_id)
	transform_applied.emit(move, solved)

	if solved:
		return _resolve("VICTORY", "Problem solved in %d moves" % _move_history.size())

	return {"valid": true, "solved": false, "moves_remaining": _moves_remaining}

func _check_squad_path() -> bool:
	"""Verify Hamiltonian path continuity: ds² between adjacent squad members."""
	for i in range(1, _squad.size()):
		var ds2 := _compute_ds2(_squad[i - 1], _squad[i])
		if ds2 > DS2_MAX:
			squad_path_broken.emit(i, ds2)
			_log("squad_path_broken", {"member": i, "ds2": ds2})
			return false
	return true

func _compute_ds2(a: Creature, b: Creature) -> float:
	"""Geodesic distance² between two creatures' 21D states."""
	var sum := 0.0
	for j in range(mini(a.state_21d.size(), b.state_21d.size())):
		var diff := a.state_21d[j] - b.state_21d[j]
		sum += diff * diff
	return sum

func _check_solved(last_move: String) -> bool:
	"""Simplified solve check. Real validation goes to Oracle HTTP service."""
	var required_moves: Array = _current_problem.get("required_moves", [])
	if required_moves.is_empty():
		return false
	# Check if all required moves have been applied
	var applied_ids: Array[String] = []
	for step in _move_history:
		applied_ids.append(step.move_id)
	for req in required_moves:
		if req not in applied_ids:
			return false
	return true

func _resolve(result: String, message: String) -> Dictionary:
	"""End the encounter. Compute rewards, update creatures, log training data."""
	var reward := 0.0
	match result:
		"VICTORY":
			reward = 1.0
			# Boost behavior for all squad creatures
			for c in _squad:
				c.behavior_score = clampf(c.behavior_score + 0.1, -1.0, 1.0)
		"DEFEAT":
			reward = -0.2
		"QUARANTINE":
			reward = -0.5
			for c in _squad:
				c.behavior_score = clampf(c.behavior_score - 0.1, -1.0, 1.0)

	var outcome := {
		"result": result,
		"message": message,
		"reward": reward,
		"moves_used": _move_history.size(),
		"training_pair": {
			"problem": _current_problem,
			"moves": _move_history,
			"result": result,
			"reward": reward
		}
	}

	_log("combat_resolved", outcome)
	combat_resolved.emit(outcome)
	return outcome

func _log(event_type: String, payload: Dictionary):
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("layer11_%s" % event_type, payload)
