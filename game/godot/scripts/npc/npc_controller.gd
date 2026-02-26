## NPCController — NPC behavior, dialogue, quest interaction
##
## GDD Section 2.2: Every NPC interaction teaches a mechanic or advances a quest.
## NPCs are tied to tongues and have tongue-colored visual identity.

extends CharacterBody3D

class_name NPCController

@export var npc_id: String = "generic_npc"
@export var npc_name: String = "Villager"
@export var tongue_affinity: int = 0  # 0-5, which tongue this NPC represents
@export var is_shopkeeper: bool = false
@export var is_quest_giver: bool = false

# Dialogue lines: array of {"text": "...", "speaker": "name"}
@export var dialogue_lines: Array[Dictionary] = []

# Shop inventory (if shopkeeper)
@export var shop_items: Array[Dictionary] = []

# Quest data (if quest giver)
@export var quest_id: String = ""
@export var quest_data: Dictionary = {}

# Interaction state
var _can_interact: bool = false
var _has_been_talked_to: bool = false

# Visual
var _name_label: Label3D
var _interaction_indicator: MeshInstance3D


func _ready() -> void:
	# Add to interaction collision layer (layer 3)
	collision_layer = 0b0100
	collision_mask = 0

	_setup_name_label()
	_setup_interaction_indicator()


func _setup_name_label() -> void:
	_name_label = Label3D.new()
	_name_label.text = npc_name
	_name_label.position = Vector3(0, 2.2, 0)
	_name_label.font_size = 32
	_name_label.modulate = TongueSystem.get_tongue_color(tongue_affinity)
	_name_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_name_label.no_depth_test = true
	add_child(_name_label)


func _setup_interaction_indicator() -> void:
	# Floating diamond above NPC when interactable
	_interaction_indicator = MeshInstance3D.new()
	var mesh := PrismMesh.new()
	mesh.size = Vector3(0.2, 0.3, 0.2)
	_interaction_indicator.mesh = mesh
	_interaction_indicator.position = Vector3(0, 2.6, 0)
	_interaction_indicator.visible = false

	var mat := StandardMaterial3D.new()
	mat.albedo_color = TongueSystem.get_tongue_color(tongue_affinity)
	mat.emission_enabled = true
	mat.emission = TongueSystem.get_tongue_color(tongue_affinity)
	mat.emission_energy_multiplier = 2.0
	_interaction_indicator.material_override = mat

	add_child(_interaction_indicator)


func _physics_process(delta: float) -> void:
	# Bob the interaction indicator
	if _interaction_indicator.visible:
		_interaction_indicator.position.y = 2.6 + sin(Time.get_ticks_msec() * 0.003) * 0.1
		_interaction_indicator.rotate_y(delta * 2.0)


## Called when player enters interaction range
func set_interactable(can_interact: bool) -> void:
	_can_interact = can_interact
	_interaction_indicator.visible = can_interact


## Called when player presses interact
func interact() -> void:
	if not _can_interact:
		return

	_has_been_talked_to = true

	if is_shopkeeper:
		_open_shop()
	elif is_quest_giver and quest_id != "" and not GameState.completed_quests.has(quest_id):
		_offer_quest()
	else:
		_start_dialogue()


func _start_dialogue() -> void:
	if dialogue_lines.is_empty():
		# Default dialogue
		EventBus.dialogue_requested.emit(npc_name, [
			{"text": "Welcome to Hearthstone Landing!", "speaker": npc_name}
		])
	else:
		EventBus.dialogue_requested.emit(npc_name, dialogue_lines)
	EventBus.npc_dialogue_started.emit(npc_id)

	# Grant tongue XP for talking to NPCs
	GameState.gain_tongue_xp(tongue_affinity, 0.1)


func _open_shop() -> void:
	EventBus.shop_opened.emit(npc_id)
	EventBus.npc_dialogue_started.emit(npc_id)


func _offer_quest() -> void:
	# Check if quest is already active
	for q in GameState.active_quests:
		if q["id"] == quest_id:
			# Quest in progress — show progress dialogue
			EventBus.dialogue_requested.emit(npc_name, [
				{"text": "How's that task coming along?", "speaker": npc_name}
			])
			return

	# Offer new quest
	var quest_dialogue: Array[Dictionary] = []
	if quest_data.has("offer_text"):
		quest_dialogue.append({"text": quest_data["offer_text"], "speaker": npc_name})
	else:
		quest_dialogue.append({"text": "I have a task for you.", "speaker": npc_name})
	EventBus.dialogue_requested.emit(npc_name, quest_dialogue)
	GameState.start_quest(quest_id, quest_data)
