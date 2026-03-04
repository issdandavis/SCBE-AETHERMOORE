class_name HUD
extends CanvasLayer

func _ready():
	add_to_group("hud")

func open_dialogue(speaker_name: String, dialogue_id: String, npc_id: String):
	var box := $DialogueBox
	box.visible = true
	box.start_dialogue(speaker_name, dialogue_id, npc_id)

func close_dialogue():
	$DialogueBox.visible = false
