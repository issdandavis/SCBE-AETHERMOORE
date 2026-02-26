## HearthstoneManager — Tutorial town logic, NPC placement, quest orchestration
##
## GDD Section 2.1 — Hearthstone Landing (Tutorial Town)
## Day 1 errands that secretly teach mechanics:
##   - Deliver packages → movement + navigation + NPC interaction
##   - Fix a broken ward pylon → first Tongue interaction (KO)
##   - Chase Polly through the market → introduces the raven companion
##   - Meet Marcus → companion egg + Academy enrollment letter
##
## Layout: 15×15 tile area with central market, Marcus's house, shop, ward pylon

extends Node3D

# NPC references (populated in _ready)
var npcs: Dictionary = {}

# GridMap reference
@onready var grid_map: GridMap = $GridMap

# Tutorial quest chain
var tutorial_phase: int = 0


func _ready() -> void:
	_build_town()
	_spawn_npcs()
	_setup_tutorial_quests()

	EventBus.quest_updated.connect(_on_quest_updated)
	EventBus.npc_dialogue_ended.connect(_on_dialogue_ended)


## Build the 15×15 GridMap town layout procedurally
func _build_town() -> void:
	# Create mesh library for Hearthstone (neutral tongue = -1)
	var mesh_lib := GridMapBuilder.create_tongue_mesh_library(-1)
	grid_map.mesh_library = mesh_lib
	grid_map.cell_size = Vector3(1, 1, 1)

	# Hearthstone Landing layout (15×15)
	# Legend:
	#   0 = grass ground
	#   5 = stone path
	#   1 = low wall / fence
	#   2 = building floor
	#   3 = building wall
	#   4 = water (fountain)
	#   7 = ward pylon
	var layout: Array[Array] = [
		#  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14
		[1, 1, 1, 1, 1, 1, 0, 5, 0, 1, 1, 1, 1, 1, 1],  # 0  North wall
		[1, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 1],  # 1
		[1, 0, 3, 3, 2, 0, 0, 5, 0, 0, 3, 3, 2, 0, 1],  # 2  Marcus house | Shop
		[1, 0, 3, 2, 2, 0, 0, 5, 0, 0, 3, 2, 2, 0, 1],  # 3
		[1, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 1],  # 4
		[1, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 0, 0, 0, 1],  # 5  Cross path
		[0, 0, 0, 0, 5, 0, 0, 4, 0, 0, 5, 0, 0, 0, 0],  # 6
		[5, 5, 5, 5, 5, 0, 4, 4, 4, 0, 5, 5, 5, 5, 5],  # 7  Center fountain + main road
		[0, 0, 0, 0, 5, 0, 0, 4, 0, 0, 5, 0, 0, 0, 0],  # 8
		[1, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 0, 0, 0, 1],  # 9  Cross path
		[1, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 1],  # 10
		[1, 0, 3, 3, 2, 0, 0, 5, 0, 0, 0, 7, 0, 0, 1],  # 11 Academy | Ward pylon
		[1, 0, 3, 2, 2, 0, 0, 5, 0, 0, 0, 0, 0, 0, 1],  # 12
		[1, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 1],  # 13
		[1, 1, 1, 1, 1, 1, 0, 5, 0, 1, 1, 1, 1, 1, 1],  # 14 South wall
	]

	# Place tiles — ground layer at y=0, structures at y=0 or y=1
	for z in range(15):
		for x in range(15):
			var tile_type: int = layout[z][x]
			match tile_type:
				0:  # Grass
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_GROUND)
				1:  # Wall
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_GROUND)
					grid_map.set_cell_item(Vector3i(x, 1, z), GridMapBuilder.TILE_WALL)
				2:  # Building floor
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_BUILDING_FLOOR)
				3:  # Building wall
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_BUILDING_FLOOR)
					grid_map.set_cell_item(Vector3i(x, 1, z), GridMapBuilder.TILE_BUILDING_WALL)
				4:  # Water (fountain)
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_WATER)
				5:  # Path
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_PATH)
				7:  # Ward pylon
					grid_map.set_cell_item(Vector3i(x, 0, z), GridMapBuilder.TILE_GROUND)
					grid_map.set_cell_item(Vector3i(x, 1, z), GridMapBuilder.TILE_WARD_PYLON)


## Spawn the 5 tutorial NPCs
func _spawn_npcs() -> void:
	# 1. Marcus Chen — at his house (NW)
	_create_npc("marcus", "Marcus Chen", 3, 3, 0, [
		{"text": "Welcome home. The Academy awaits you.", "speaker": "Marcus Chen"},
		{"text": "Take this egg. It chose you before you were born.", "speaker": "Marcus Chen"},
		{"text": "And here — your enrollment letter. Make us proud.", "speaker": "Marcus Chen"},
	])

	# 2. Shopkeeper Greta — at the shop (NE)
	_create_npc_shop("greta", "Greta", 11, 3, 5, [
		{"id": "potion_seal", "name": "Seal Salve", "price": 10, "tongue": "UM",
		 "desc": "Restores 30 seal integrity to a companion."},
		{"id": "focus_lens", "name": "Focus Lens", "price": 25, "tongue": "CA",
		 "desc": "Boosts Insight by 0.1 for one encounter."},
		{"id": "drift_anchor", "name": "Drift Anchor", "price": 15, "tongue": "DR",
		 "desc": "Reduces drift level by 0.05."},
		{"id": "ember_shard", "name": "Ember Shard", "price": 20, "tongue": "KO",
		 "desc": "Grants 0.5 KO tongue XP."},
	])

	# 3. Elder Tomas — quest giver near the fountain
	_create_npc_quest("tomas", "Elder Tomas", 6, 6, 4,
		"delivery_quest",
		{"name": "Package Delivery", "offer_text": "Could you deliver this package to Marcus? He's at the house to the northwest.", "type": "delivery"},
		[{"text": "Ah, a new face! Would you help an old man?", "speaker": "Elder Tomas"}]
	)

	# 4. Ward Keeper Sila — near the broken pylon
	_create_npc_quest("sila", "Ward Keeper Sila", 12, 11, 0,
		"ward_pylon_quest",
		{"name": "Fix the Ward Pylon", "offer_text": "The ward pylon is flickering! Channel some KO energy into it to stabilize it.", "type": "repair"},
		[{"text": "The wards are weakening... Can you help?", "speaker": "Ward Keeper Sila"}]
	)

	# 5. Polly (the raven) — near the market, starts chase sequence
	_create_npc("polly", "Polly", 8, 9, 1, [
		{"text": "*Caw!* Shiny! Shiny!", "speaker": "Polly"},
		{"text": "*The raven eyes you curiously, then takes flight...*", "speaker": ""},
	])


func _create_npc(id: String, display_name: String, x: int, z: int,
				 tongue: int, dialogue: Array[Dictionary]) -> void:
	var npc := _make_npc_body(id, display_name, tongue)
	npc.dialogue_lines = dialogue
	npc.position = Vector3(x + 0.5, 0.5, z + 0.5)
	add_child(npc)
	npcs[id] = npc


func _create_npc_shop(id: String, display_name: String, x: int, z: int,
					  tongue: int, items: Array[Dictionary]) -> void:
	var npc := _make_npc_body(id, display_name, tongue)
	npc.is_shopkeeper = true
	npc.shop_items = items
	npc.dialogue_lines = [
		{"text": "Welcome to my shop! Take a look.", "speaker": display_name}
	]
	npc.position = Vector3(x + 0.5, 0.5, z + 0.5)
	add_child(npc)
	npcs[id] = npc


func _create_npc_quest(id: String, display_name: String, x: int, z: int,
					   tongue: int, q_id: String, q_data: Dictionary,
					   dialogue: Array[Dictionary]) -> void:
	var npc := _make_npc_body(id, display_name, tongue)
	npc.is_quest_giver = true
	npc.quest_id = q_id
	npc.quest_data = q_data
	npc.dialogue_lines = dialogue
	npc.position = Vector3(x + 0.5, 0.5, z + 0.5)
	add_child(npc)
	npcs[id] = npc


func _make_npc_body(id: String, display_name: String, tongue: int) -> NPCController:
	var npc := NPCController.new()
	npc.npc_id = id
	npc.npc_name = display_name
	npc.tongue_affinity = tongue

	# Visual body: capsule mesh with tongue color
	var mesh_inst := MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.25
	capsule.height = 1.0
	mesh_inst.mesh = capsule
	mesh_inst.position = Vector3(0, 0.5, 0)

	var mat := StandardMaterial3D.new()
	mat.albedo_color = TongueSystem.get_tongue_color(tongue)
	mat.roughness = 0.6
	mesh_inst.material_override = mat
	npc.add_child(mesh_inst)

	# Collision shape
	var col := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.3
	shape.height = 1.2
	col.shape = shape
	col.position = Vector3(0, 0.6, 0)
	npc.add_child(col)

	return npc


func _setup_tutorial_quests() -> void:
	# Tutorial starts at phase 0
	tutorial_phase = 0
	# The delivery quest teaches movement
	# The ward pylon quest teaches tongue interaction
	# Polly chase teaches companion mechanics
	# Meeting Marcus gives the first egg


func _on_quest_updated(quest_id: String, status: String) -> void:
	if status == "completed":
		match quest_id:
			"delivery_quest":
				GameState.tutorial_completed["delivery"] = true
				GameState.gain_tongue_xp(1, 1.0)  # AV XP for delivery
				GameState.gold += 15
				EventBus.notification_requested.emit(
					"Delivery complete! +15 Gold, +1.0 AV XP", Color.GOLD)
			"ward_pylon_quest":
				GameState.tutorial_completed["ward_pylon"] = true
				GameState.gain_tongue_xp(0, 2.0)  # KO XP for ward repair
				EventBus.notification_requested.emit(
					"Ward stabilized! +2.0 KO XP", Color(0.86, 0.24, 0.24))


func _on_dialogue_ended(npc_id: String) -> void:
	match npc_id:
		"marcus":
			if not GameState.has_met_marcus:
				GameState.has_met_marcus = true
				GameState.has_academy_letter = true
				GameState.tutorial_completed["meet_marcus"] = true
				# Give first egg
				EventBus.egg_condition_met.emit("crystal")
				EventBus.notification_requested.emit(
					"Received: Sacred Egg (Crystal) + Academy Letter!", Color.GOLD)
		"polly":
			if not GameState.has_met_polly:
				GameState.has_met_polly = true
				GameState.tutorial_completed["polly_chase"] = true
				EventBus.notification_requested.emit(
					"Polly joins as your guide raven!", Color(0.86, 0.71, 0.24))
