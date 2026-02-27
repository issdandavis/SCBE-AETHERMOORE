class_name NPCController
extends Node3D

@export var npc_id: String = "npc"
@export var display_name: String = "NPC"
@export var dialogue_id: String = "default"

func _ready():
	var ia := $Interactable as Interactable
	ia.interacted.connect(_on_interacted)

func _on_interacted(action_id: String, node: Node):
	if action_id != "talk":
		return
	var hud := get_tree().get_first_node_in_group("hud")
	if hud:
		hud.open_dialogue(display_name, dialogue_id, npc_id)
