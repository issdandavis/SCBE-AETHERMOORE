class_name QuestSystem
extends Node

@export var quest_file: String = ""
var data := {}
var state := {
	"active_step": "start",
	"flags": {}
}

func _ready():
	add_to_group("quest_system")
	_load_quests()

func _load_quests():
	if quest_file == "":
		push_warning("Quest file not set.")
		return
	var f := FileAccess.open(quest_file, FileAccess.READ)
	data = JSON.parse_string(f.get_as_text())
	print("Loaded quests:", data.get("title", "?"))

func set_flag(flag: String, value := true):
	state.flags[flag] = value

func has_flag(flag: String) -> bool:
	return bool(state.flags.get(flag, false))

func on_dialogue_finished(npc_id: String, dialogue_id: String):
	# Day 1 progression
	if npc_id == "townfolk_a" and dialogue_id == "package_receiver":
		set_flag("delivered_package", true)
		_maybe_advance()

	if npc_id == "polly" and dialogue_id == "polly_intro":
		set_flag("met_polly", true)
		_maybe_advance()

	if npc_id == "marcus" and dialogue_id == "marcus_meet":
		set_flag("met_marcus", true)
		_maybe_advance()

func on_interaction(action_id: String, node: Node):
	if action_id == "fix_ward_pylon":
		set_flag("fixed_pylon", true)
		_maybe_advance()
	if action_id == "enter_dungeon":
		print("Dungeon entrance triggered (Sprint 3 scene swap).")

func _maybe_advance():
	# Ordered steps for Day 1
	var order := ["delivered_package", "fixed_pylon", "met_polly", "met_marcus"]
	for flag in order:
		if not has_flag(flag):
			return

	# All done
	print("Day 1 complete -> grant Egg + Academy Letter")
	var gs := get_tree().root.get_node("Main/GameState") if get_tree().root.has_node("Main/GameState") else null
	if gs:
		gs.set_meta("has_egg", true)
		gs.set_meta("has_academy_letter", true)
