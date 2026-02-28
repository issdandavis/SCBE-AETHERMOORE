class_name Interactable
extends Area3D

@export var action_id: String = "interact"
@export var prompt_text: String = "Interact"

signal interacted(action_id: String, node: Node)

func _ready():
	add_to_group("interactable")
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func interact():
	interacted.emit(action_id, get_parent())

func _on_body_entered(body):
	if body is PlayerController:
		body.register_interactable(self)

func _on_body_exited(body):
	if body is PlayerController:
		body.unregister_interactable(self)
