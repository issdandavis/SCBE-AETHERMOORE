class_name DialogueSystem
extends Control

var _speaker := ""
var _dialogue_id := ""
var _npc_id := ""

# Minimal embedded dialogue database (replace later with JSON)
var DB := {
	"polly_intro": [
		"...So you can see the windows too.",
		"Don't stare. You'll scare the townsfolk.",
		"If you want to meet your father, prove you can help people first."
	],
	"package_receiver": [
		"Oh! That parcel is for me?",
		"Thank you. If you're running errands, check the Ward Pylon near the square."
	],
	"marcus_meet": [
		"You've grown.",
		"I can't stay long. The outer systems are unstable.",
		"Take this Sacred Egg. Your behavior will decide what hatches.",
		"And this... your Academy enrollment."
	]
}

var _idx := 0

func start_dialogue(speaker_name: String, dialogue_id: String, npc_id: String):
	_speaker = speaker_name
	_dialogue_id = dialogue_id
	_npc_id = npc_id
	_idx = 0
	$Panel/Name.text = speaker_name
	_render()

func _unhandled_input(event):
	if not visible:
		return
	if event.is_action_pressed("interact"):
		_next()

func _next():
	_idx += 1
	_render()

func _render():
	var lines: Array = DB.get(_dialogue_id, ["..."])
	if _idx >= lines.size():
		visible = false
		_emit_dialogue_finished()
		return
	$Panel/Text.text = "[color=#ddd]" + str(lines[_idx]) + "[/color]"

func _emit_dialogue_finished():
	var qs := get_tree().get_first_node_in_group("quest_system")
	if qs:
		qs.on_dialogue_finished(_npc_id, _dialogue_id)
