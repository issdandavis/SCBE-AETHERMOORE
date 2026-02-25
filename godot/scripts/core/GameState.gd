class_name GameState
extends Node

## Central game state singleton. Tracks inventory, flags, and session data.
## Attached to Main/GameState node.

var inventory: Dictionary = {}
var flags: Dictionary = {}
var session_id: String = ""

func _ready():
	add_to_group("game_state")
	session_id = _generate_session_id()
	print("GameState initialized. Session: ", session_id)

func add_item(item_id: String, qty: int = 1):
	inventory[item_id] = inventory.get(item_id, 0) + qty

func has_item(item_id: String) -> bool:
	return inventory.get(item_id, 0) > 0

func set_flag(flag: String, value: Variant = true):
	flags[flag] = value

func get_flag(flag: String, default: Variant = false) -> Variant:
	return flags.get(flag, default)

func _generate_session_id() -> String:
	return "ses_%d" % Time.get_unix_time_from_system()
