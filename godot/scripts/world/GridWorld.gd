class_name GridWorld
extends Node3D

func _ready():
	# Connect all interactables so Player can detect them.
	for area in get_tree().get_nodes_in_group("interactable_area"):
		_wire_area(area)

	# Wire any Interactable nodes we own
	_wire_all_interactables()

func _wire_all_interactables():
	var qs := get_tree().get_first_node_in_group("quest_system")
	for node in get_tree().get_nodes_in_group("interactable"):
		if node is Interactable and qs:
			(node as Interactable).interacted.connect(qs.on_interaction)

func _wire_area(area):
	pass
