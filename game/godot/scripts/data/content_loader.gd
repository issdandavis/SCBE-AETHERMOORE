## ContentLoader — Data-driven content system (Tuxemon-style)
##
## Loads creatures, items, NPCs, techniques, and maps from JSON files.
## New content = add a JSON file. No GDScript changes needed.
##
## Paths:
##   res://data/creatures/*.json  — Seal Entity definitions
##   res://data/items/items.json  — Item catalog
##   res://data/npcs/*.json       — NPC definitions per zone
##   res://data/techniques/transforms.json — Math transform catalog
##   res://data/maps/*.json       — Map layouts

extends Node

class_name ContentLoader

# Cached data
var creatures: Dictionary = {}  # id → creature dict
var items: Dictionary = {}      # id → item dict
var npcs: Dictionary = {}       # id → npc dict
var transforms: Dictionary = {} # id → transform dict
var maps: Dictionary = {}       # id → map dict

var _loaded: bool = false


## Load all content from JSON data files
func load_all() -> void:
	if _loaded:
		return
	_load_creatures()
	_load_items()
	_load_npcs()
	_load_transforms()
	_load_maps()
	_loaded = true


func _load_creatures() -> void:
	var dir := DirAccess.open("res://data/creatures")
	if not dir:
		push_warning("ContentLoader: No creatures directory found")
		return
	dir.list_dir_begin()
	var filename := dir.get_next()
	while filename != "":
		if filename.ends_with(".json"):
			var data := _read_json("res://data/creatures/" + filename)
			if data and data.has("id"):
				creatures[data["id"]] = data
		filename = dir.get_next()


func _load_items() -> void:
	var data := _read_json("res://data/items/items.json")
	if data and data.has("items"):
		for item in data["items"]:
			if item.has("id"):
				items[item["id"]] = item


func _load_npcs() -> void:
	var dir := DirAccess.open("res://data/npcs")
	if not dir:
		push_warning("ContentLoader: No npcs directory found")
		return
	dir.list_dir_begin()
	var filename := dir.get_next()
	while filename != "":
		if filename.ends_with(".json"):
			var data := _read_json("res://data/npcs/" + filename)
			if data and data.has("npcs"):
				for npc in data["npcs"]:
					if npc.has("id"):
						npcs[npc["id"]] = npc
		filename = dir.get_next()


func _load_transforms() -> void:
	var data := _read_json("res://data/techniques/transforms.json")
	if data and data.has("transforms"):
		for t in data["transforms"]:
			if t.has("id"):
				transforms[t["id"]] = t


func _load_maps() -> void:
	var dir := DirAccess.open("res://data/maps")
	if not dir:
		push_warning("ContentLoader: No maps directory found")
		return
	dir.list_dir_begin()
	var filename := dir.get_next()
	while filename != "":
		if filename.ends_with(".json"):
			var data := _read_json("res://data/maps/" + filename)
			if data and data.has("id"):
				maps[data["id"]] = data
		filename = dir.get_next()


func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		push_warning("ContentLoader: File not found: %s" % path)
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	if not file:
		return null
	var json := JSON.new()
	if json.parse(file.get_as_text()) != OK:
		push_warning("ContentLoader: JSON parse error in %s" % path)
		return null
	return json.data


## Get a creature definition by ID
func get_creature(creature_id: String) -> Dictionary:
	return creatures.get(creature_id, {})


## Get an item definition by ID
func get_item(item_id: String) -> Dictionary:
	return items.get(item_id, {})


## Get an NPC definition by ID
func get_npc(npc_id: String) -> Dictionary:
	return npcs.get(npc_id, {})


## Get a transform definition by ID
func get_transform(transform_id: String) -> Dictionary:
	return transforms.get(transform_id, {})


## Get a map definition by ID
func get_map(map_id: String) -> Dictionary:
	return maps.get(map_id, {})


## Get all creatures for a specific tongue
func get_creatures_by_tongue(tongue: String) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for c in creatures.values():
		if c.get("tongue", "") == tongue:
			result.append(c)
	return result


## Get all transforms unlocked at or below a floor
func get_unlocked_transforms(floor: int) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for t in transforms.values():
		if t.get("unlock_floor", 999) <= floor:
			result.append(t)
	return result


## Get NPCs for a specific map
func get_npcs_for_map(map_id: String) -> Array[Dictionary]:
	var map_data := get_map(map_id)
	if map_data.is_empty():
		return []
	# Return all NPCs (in a real implementation, filter by map association)
	var result: Array[Dictionary] = []
	for npc in npcs.values():
		result.append(npc)
	return result


## Validate all loaded content (returns array of error strings)
func validate() -> Array[String]:
	var errors: Array[String] = []

	# Check creature tongue references
	var valid_tongues := ["KO", "AV", "RU", "CA", "UM", "DR"]
	for c in creatures.values():
		if c.get("tongue", "") not in valid_tongues:
			errors.append("Creature '%s' has invalid tongue '%s'" % [c.get("id"), c.get("tongue")])

	# Check item references in NPC shops
	for npc in npcs.values():
		if npc.get("is_shopkeeper", false):
			for item_id in npc.get("shop_inventory", []):
				if not items.has(item_id):
					errors.append("NPC '%s' shop references missing item '%s'" % [npc.get("id"), item_id])

	# Check transform tongue references
	for t in transforms.values():
		if t.get("tongue", "") not in valid_tongues:
			errors.append("Transform '%s' has invalid tongue '%s'" % [t.get("id"), t.get("tongue")])

	return errors
