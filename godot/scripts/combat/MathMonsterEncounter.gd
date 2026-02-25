class_name MathMonsterEncounter
extends Control

## Math Monster Battle UI — Pokémon-style encounter driven by transform moves.
## Player picks moves, Oracle validates, SCBE gates everything.
## Plugs into SquadCombat (Layer 11) for path checking + TrainingLogger (Layer 12).

signal encounter_won(problem_id: String)
signal encounter_lost(problem_id: String)

var _squad_combat: SquadCombat = null
var _current_problem: Dictionary = {}
var _party: Array[Creature] = []
var _active_creature_idx: int = 0

func _ready():
	_squad_combat = get_tree().get_first_node_in_group("squad_combat")

func start_battle(problem: Dictionary, party: Array[Creature]):
	"""Called from dungeon scene when player hits a math monster."""
	_current_problem = problem
	_party = party
	_active_creature_idx = 0
	visible = true

	# Display the problem
	$Panel/ProblemLabel.text = problem.get("display", "Solve: ???")
	$Panel/StepLabel.text = "Step 1 of %d" % problem.get("total_steps", 3)
	$Panel/MonsterName.text = problem.get("monster_name", "Math Monster")
	$Panel/MonsterHP.value = 100

	# Set up move buttons from active creature
	_refresh_move_buttons()

	if _squad_combat:
		_squad_combat.start_encounter(problem, party)

func _refresh_move_buttons():
	"""Update move buttons based on active creature's moveset."""
	var creature := _party[_active_creature_idx] if _active_creature_idx < _party.size() else null
	if creature == null:
		return

	var move_container := $Panel/Moves
	# Clear existing buttons
	for child in move_container.get_children():
		child.queue_free()

	# Create buttons for each move (max 4 Pokémon-style)
	for i in range(mini(creature.moves.size(), 4)):
		var move: Dictionary = creature.moves[i]
		var btn := Button.new()
		btn.text = move.get("name", "Move %d" % i)
		btn.tooltip_text = move.get("desc", "")
		var move_id: String = move.get("id", "")
		btn.pressed.connect(_on_move_pressed.bind(move_id))
		move_container.add_child(btn)

	# Also show universal transform moves
	for move_id in ["normalize", "complete_square", "domain_check", "factor", "substitute", "quadratic_formula"]:
		var move_data: Dictionary = SquadCombat.TRANSFORM_MOVES.get(move_id, {})
		if not move_data.is_empty():
			var btn := Button.new()
			btn.text = move_data.get("name", move_id)
			btn.tooltip_text = move_data.get("desc", "")
			btn.pressed.connect(_on_move_pressed.bind(move_id))
			move_container.add_child(btn)

func _on_move_pressed(move_id: String):
	"""Player selected a transform move."""
	if _squad_combat == null:
		return

	var result := _squad_combat.apply_move(move_id, _active_creature_idx)
	if not result.get("valid", false):
		$Panel/FeedbackLabel.text = "Blocked: %s" % result.get("reason", "invalid")
		return

	# Update UI
	var solved: bool = result.get("solved", false)
	var remaining: int = result.get("moves_remaining", 0)
	$Panel/StepLabel.text = "Moves left: %d" % remaining
	$Panel/FeedbackLabel.text = "Applied: %s" % move_id.capitalize()

	# Animate monster HP (visual feedback)
	var hp_loss := 100.0 / maxf(_current_problem.get("total_steps", 3), 1.0)
	$Panel/MonsterHP.value = maxf($Panel/MonsterHP.value - hp_loss, 0)

	if solved:
		_on_victory()
	elif result.get("result", "") == "DEFEAT":
		_on_defeat("Out of moves!")
	elif result.get("result", "") == "QUARANTINE":
		_on_defeat("Squad formation broken!")

func _on_victory():
	$Panel/FeedbackLabel.text = "VICTORY! Problem solved!"
	# Record to training logger
	var trainer := get_tree().get_first_node_in_group("training_logger")
	if trainer:
		trainer.record_game_event({
			"type": "combat_victory",
			"problem_id": _current_problem.get("id", "?"),
			"outcome": {"reward": 1.0}
		})
	# Record choice to Sacred Egg
	_record_egg_choice(0.3)
	encounter_won.emit(_current_problem.get("id", "?"))
	await get_tree().create_timer(2.0).timeout
	visible = false

func _on_defeat(reason: String):
	$Panel/FeedbackLabel.text = "DEFEAT: %s" % reason
	var trainer := get_tree().get_first_node_in_group("training_logger")
	if trainer:
		trainer.record_game_event({
			"type": "combat_defeat",
			"problem_id": _current_problem.get("id", "?"),
			"outcome": {"reward": -0.2, "reason": reason}
		})
	_record_egg_choice(-0.1)
	encounter_lost.emit(_current_problem.get("id", "?"))
	await get_tree().create_timer(2.0).timeout
	visible = false

func _record_egg_choice(moral_weight: float):
	"""Combat outcomes affect egg behavior accumulation."""
	var eggs := get_tree().get_nodes_in_group("sacred_egg")
	for egg in eggs:
		if egg is SacredEgg:
			egg.record_choice({
				"type": "combat_outcome",
				"moral_weight": moral_weight,
				"problem_id": _current_problem.get("id", "?")
			})

func switch_creature(idx: int):
	"""Swap active creature (Pokémon-style party rotation)."""
	if idx >= 0 and idx < _party.size():
		_active_creature_idx = idx
		_refresh_move_buttons()
		$Panel/CreatureName.text = _party[idx].display_name
