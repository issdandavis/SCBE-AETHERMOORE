## GameState — Global state manager for player progression, save/load, quests
##
## Tracks: player stats, tongue XP, inventory, quest log, floor progress,
## companion roster, and economy currencies.

extends Node

# -- Player identity --
var player_name: String = "Chen"  # Marcus Chen's child
var player_rank: String = "F"
var current_floor: int = 1

# -- Tongue experience (raw accumulation) --
var tongue_xp: Array[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

# -- Player stats (derived from tongue XP + skill tree) --
var max_health: float = 100.0
var current_health: float = 100.0
var player_level: int = 1

# -- Skill tree points (6 paths from GDD Section 7) --
var skill_points: Dictionary = {
	"command":   0,  # KO — Initiative
	"compute":   0,  # CA — Combo
	"entropy":   0,  # RU — Burst
	"structure": 0,  # DR — Tank
	"transport": 0,  # AV — Mobility
	"security":  0,  # UM — Support
}

# -- Economy (GDD Section 13) --
var gold: int = 50  # Starting gold
var proof_tokens: int = 0
var culture_points: int = 0
var reputation: int = 0

# -- Inventory --
var inventory: Array[Dictionary] = []
# Item format: {"id": "potion_heal", "name": "Seal Salve", "quantity": 3, "tongue": "UM"}

# -- Companion roster --
var companions: Array[Dictionary] = []
# Companion format: {"id": "crysling_01", "species": "crysling", "bond": 1, ...}

var active_companion_index: int = -1  # -1 = none

# -- Quest log --
var active_quests: Array[Dictionary] = []
var completed_quests: Array[String] = []

# -- Tutorial state --
var tutorial_completed: Dictionary = {
	"movement": false,
	"delivery": false,
	"ward_pylon": false,
	"polly_chase": false,
	"meet_marcus": false,
	"first_egg": false,
}

# -- Flags --
var has_academy_letter: bool = false
var has_met_marcus: bool = false
var has_met_polly: bool = false


func _ready() -> void:
	pass


## Add tongue experience and emit event
func gain_tongue_xp(tongue_index: int, amount: float) -> void:
	if tongue_index >= 0 and tongue_index < 6:
		tongue_xp[tongue_index] += amount
		EventBus.player_tongue_gained.emit(tongue_index, amount)


## Get normalized tongue distribution [0,1] for each tongue
func get_tongue_distribution() -> Array[float]:
	var total := 0.0
	for xp in tongue_xp:
		total += xp
	if total < 0.01:
		return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
	var dist: Array[float] = []
	for xp in tongue_xp:
		dist.append(xp / total)
	return dist


## Get dominant tongue index
func get_dominant_tongue() -> int:
	var max_idx := 0
	for i in range(1, 6):
		if tongue_xp[i] > tongue_xp[max_idx]:
			max_idx = i
	return max_idx


## Add item to inventory
func add_item(item_id: String, item_name: String, quantity: int = 1, tongue: String = "") -> void:
	for item in inventory:
		if item["id"] == item_id:
			item["quantity"] += quantity
			return
	inventory.append({"id": item_id, "name": item_name, "quantity": quantity, "tongue": tongue})


## Remove item from inventory
func remove_item(item_id: String, quantity: int = 1) -> bool:
	for i in range(inventory.size()):
		if inventory[i]["id"] == item_id:
			inventory[i]["quantity"] -= quantity
			if inventory[i]["quantity"] <= 0:
				inventory.remove_at(i)
			return true
	return false


## Check if player has item
func has_item(item_id: String, quantity: int = 1) -> bool:
	for item in inventory:
		if item["id"] == item_id and item["quantity"] >= quantity:
			return true
	return false


## Add companion to roster
func add_companion(companion_data: Dictionary) -> void:
	companions.append(companion_data)
	if active_companion_index == -1:
		active_companion_index = companions.size() - 1


## Get active companion data
func get_active_companion() -> Dictionary:
	if active_companion_index >= 0 and active_companion_index < companions.size():
		return companions[active_companion_index]
	return {}


## Start a quest
func start_quest(quest_id: String, quest_data: Dictionary) -> void:
	quest_data["id"] = quest_id
	quest_data["status"] = "active"
	active_quests.append(quest_data)
	EventBus.quest_updated.emit(quest_id, "started")


## Complete a quest
func complete_quest(quest_id: String) -> void:
	for i in range(active_quests.size()):
		if active_quests[i]["id"] == quest_id:
			active_quests.remove_at(i)
			completed_quests.append(quest_id)
			EventBus.quest_updated.emit(quest_id, "completed")
			return


## Apply damage to player
func take_damage(amount: float) -> void:
	current_health = maxf(0.0, current_health - amount)
	EventBus.player_health_changed.emit(current_health, max_health)


## Heal player
func heal(amount: float) -> void:
	current_health = minf(max_health, current_health + amount)
	EventBus.player_health_changed.emit(current_health, max_health)


## Get rank string from floor
func rank_from_floor(floor: int) -> String:
	if floor <= 10: return "F"
	if floor <= 20: return "E"
	if floor <= 30: return "D"
	if floor <= 40: return "C"
	if floor <= 50: return "B"
	if floor <= 60: return "A"
	if floor <= 70: return "S"
	if floor <= 80: return "SS"
	if floor <= 90: return "SSS"
	return "Transcendent"


## Save game state to file
func save_game(slot: int = 0) -> void:
	var save_data := {
		"player_name": player_name,
		"player_rank": player_rank,
		"current_floor": current_floor,
		"tongue_xp": tongue_xp,
		"max_health": max_health,
		"current_health": current_health,
		"player_level": player_level,
		"skill_points": skill_points,
		"gold": gold,
		"proof_tokens": proof_tokens,
		"culture_points": culture_points,
		"reputation": reputation,
		"inventory": inventory,
		"companions": companions,
		"active_companion_index": active_companion_index,
		"active_quests": active_quests,
		"completed_quests": completed_quests,
		"tutorial_completed": tutorial_completed,
		"has_academy_letter": has_academy_letter,
		"has_met_marcus": has_met_marcus,
		"has_met_polly": has_met_polly,
	}
	var path := "user://save_%d.json" % slot
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(save_data, "\t"))


## Load game state from file
func load_game(slot: int = 0) -> bool:
	var path := "user://save_%d.json" % slot
	if not FileAccess.file_exists(path):
		return false
	var file := FileAccess.open(path, FileAccess.READ)
	if not file:
		return false
	var json := JSON.new()
	if json.parse(file.get_as_text()) != OK:
		return false
	var data: Dictionary = json.data
	player_name = data.get("player_name", "Chen")
	player_rank = data.get("player_rank", "F")
	current_floor = data.get("current_floor", 1)
	max_health = data.get("max_health", 100.0)
	current_health = data.get("current_health", 100.0)
	player_level = data.get("player_level", 1)
	gold = data.get("gold", 50)
	proof_tokens = data.get("proof_tokens", 0)
	culture_points = data.get("culture_points", 0)
	reputation = data.get("reputation", 0)
	has_academy_letter = data.get("has_academy_letter", false)
	has_met_marcus = data.get("has_met_marcus", false)
	has_met_polly = data.get("has_met_polly", false)
	# Arrays need explicit reconstruction
	if data.has("tongue_xp"):
		tongue_xp.clear()
		for v in data["tongue_xp"]:
			tongue_xp.append(float(v))
	if data.has("inventory"):
		inventory = data["inventory"]
	if data.has("companions"):
		companions = data["companions"]
	if data.has("active_quests"):
		active_quests = data["active_quests"]
	if data.has("completed_quests"):
		completed_quests = data["completed_quests"]
	if data.has("tutorial_completed"):
		tutorial_completed = data["tutorial_completed"]
	if data.has("skill_points"):
		skill_points = data["skill_points"]
	active_companion_index = data.get("active_companion_index", -1)
	return true
