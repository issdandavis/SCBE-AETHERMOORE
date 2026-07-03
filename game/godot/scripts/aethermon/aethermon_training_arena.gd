## AETHERMON Training Arena
##
## Visual mirror for scripts/system/aethermon_training_arena.py.
## The Python gym owns simulation truth and emits receipts; this scene renders
## the same board/sprite manifest inside Godot for play and inspection.

extends Node2D

class_name AethermonTrainingArena

@export var cell_size: int = 24
@export var manifest_path: String = "res://assets/aethermon/training_manifest.json"
@export var player_species: String = "kindlemote"

var _manifest: Dictionary = {}
var _board: Array = []
var _player: Sprite2D


func _ready() -> void:
	_load_manifest()
	_draw_board()


func _load_manifest() -> void:
	if not FileAccess.file_exists(manifest_path):
		push_warning("AETHERMON manifest missing: %s. Run scripts/system/aethermon_training_arena.py first." % manifest_path)
		return
	var text := FileAccess.get_file_as_string(manifest_path)
	var parsed := JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("AETHERMON manifest did not parse as a dictionary.")
		return
	_manifest = parsed
	_board = _manifest.get("board", [])
	cell_size = int(_manifest.get("tile_size", cell_size))


func _draw_board() -> void:
	if _board.is_empty():
		return
	for row in range(_board.size()):
		var line: String = _board[row]
		for col in range(line.length()):
			var cell := line.substr(col, 1)
			_draw_floor_cell(row, col, cell)
			match cell:
				"A":
					_player = _spawn_sprite(player_species, row, col)
				"R":
					_spawn_sprite("rival_venom", row, col)
				"B":
					_spawn_sprite("berry", row, col)
				"T":
					_spawn_sprite("training_pad", row, col)
				"H":
					_spawn_sprite("hazard", row, col)
				"N":
					_spawn_sprite("nexus", row, col)


func _draw_floor_cell(row: int, col: int, cell: String) -> void:
	var rect := ColorRect.new()
	rect.position = Vector2(col * cell_size, row * cell_size)
	rect.size = Vector2(cell_size, cell_size)
	if cell == "#":
		rect.color = Color(0.12, 0.13, 0.16, 1.0)
	else:
		rect.color = Color(0.78, 0.81, 0.74, 1.0)
	add_child(rect)


func _spawn_sprite(sprite_id: String, row: int, col: int) -> Sprite2D:
	var sprite := Sprite2D.new()
	var info: Dictionary = _manifest.get("sprites", {}).get(sprite_id, {})
	var texture_path: String = info.get("path", "")
	if texture_path != "":
		sprite.texture = load(texture_path)
	sprite.position = Vector2(col * cell_size + cell_size / 2, row * cell_size + cell_size / 2)
	add_child(sprite)
	return sprite


func apply_training_tick(tick: Dictionary) -> void:
	if not _player:
		return
	var after: Dictionary = tick.get("after", {})
	var pos: Array = after.get("position", [])
	if pos.size() == 2:
		_player.position = Vector2(int(pos[1]) * cell_size + cell_size / 2, int(pos[0]) * cell_size + cell_size / 2)
