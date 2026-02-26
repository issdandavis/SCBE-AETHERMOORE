## MainScene — Top-level controller that wires player, companion, camera, and UI
##
## Attaches to the Main node in main.tscn. Handles:
##   - Connecting player signals to companion + UI
##   - Camera target assignment
##   - NPC interaction routing
##   - Scene transitions

extends Node3D

@onready var player: PlayerController = $Player
@onready var companion: CompanionAI = $Crysling
@onready var camera: CameraController = $Camera
@onready var scbe_client: SCBEClient = $SCBEClient

# UI layers (instantiated at runtime)
var hud: HUD
var dialogue_panel: DialoguePanel
var shop_panel: ShopPanel

# NPC proximity tracking
var _nearby_npc: NPCController = null
const NPC_INTERACT_RANGE: float = 2.0


func _ready() -> void:
	# Wire camera to player
	camera.target = player

	# Wire companion to player
	companion.player = player
	companion.companion_id = "crysling_01"
	companion.species_id = "crysling"
	companion.tongue_position = [0.05, 0.0, 0.0, 0.4, 0.1, 0.0]
	companion.bond_level = 1
	companion.seal_integrity = 100.0
	companion.evolution_stage = "spark"
	player.active_companion = companion

	# Connect player signals
	player.attack_hit.connect(_on_player_attack)
	player.interact_triggered.connect(_on_player_interact)
	player.tongue_experience_gained.connect(_on_tongue_gained)

	# Instantiate UI
	_setup_ui()

	# Register starter companion in game state
	GameState.add_companion({
		"id": "crysling_01",
		"species": "crysling",
		"bond": 1,
		"tongue_position": [0.05, 0.0, 0.0, 0.4, 0.1, 0.0],
		"evolution_stage": "spark",
	})

	# Initial notification
	EventBus.notification_requested.emit(
		"Welcome to Hearthstone Landing!", Color.WHITE)


func _physics_process(_delta: float) -> void:
	_check_npc_proximity()


func _setup_ui() -> void:
	hud = HUD.new()
	add_child(hud)

	dialogue_panel = DialoguePanel.new()
	add_child(dialogue_panel)

	shop_panel = ShopPanel.new()
	add_child(shop_panel)


func _on_player_attack(damage: float, tongue: String) -> void:
	companion.on_player_attack(damage, tongue)
	EventBus.player_attacked.emit(damage, tongue)

	# Grant tongue XP for attacks
	var tongue_idx := 0
	match tongue:
		"KO": tongue_idx = 0
		"DR": tongue_idx = 5
	GameState.gain_tongue_xp(tongue_idx, 0.1)


func _on_player_interact(target: Node3D) -> void:
	if target is NPCController:
		var npc := target as NPCController
		npc.interact()
		EventBus.player_interacted.emit(target)


func _on_tongue_gained(tongue_index: int, amount: float) -> void:
	GameState.gain_tongue_xp(tongue_index, amount)

	# Check egg conditions
	var eggs := TongueSystem.check_egg_conditions(GameState.tongue_xp)
	for egg in eggs:
		EventBus.egg_condition_met.emit(egg)


## Check if player is near any NPC for interaction indicator
func _check_npc_proximity() -> void:
	var town := $HearthstoneLanding as Node3D
	if not town:
		return

	var closest_npc: NPCController = null
	var closest_dist := NPC_INTERACT_RANGE

	for child in town.get_children():
		if child is NPCController:
			var dist := player.global_position.distance_to(child.global_position)
			if dist < closest_dist:
				closest_dist = dist
				closest_npc = child as NPCController

	# Update interaction indicators
	if closest_npc != _nearby_npc:
		if _nearby_npc:
			_nearby_npc.set_interactable(false)
		_nearby_npc = closest_npc
		if _nearby_npc:
			_nearby_npc.set_interactable(true)
