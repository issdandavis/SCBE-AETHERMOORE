## Companion AI — Follows player, assists in combat based on bond level
##
## Bond levels:
##   1: Basic follow
##   3: Tag team attacks
##   5: Fusion moves
##   7: Autonomous combat

extends CharacterBody3D

class_name CompanionAI

# References
@export var player: PlayerController
@export var follow_distance: float = 2.0
@export var follow_speed: float = 4.0
@export var catch_up_speed: float = 8.0
@export var catch_up_distance: float = 5.0

# Companion data (mirrors 21D canonical state)
var companion_id: String = ""
var species_id: String = ""
var tongue_position: Array[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
var bond_level: int = 1
var seal_integrity: float = 100.0
var evolution_stage: String = "spark"
var emotional_state: String = "content"

# State
enum AIState { FOLLOW, IDLE, ASSIST, AUTONOMOUS }
var current_state: AIState = AIState.FOLLOW

# Internal
var _idle_timer: float = 0.0

# Signals
signal assist_attack(damage: float)
signal bond_event(event_type: String)


func _ready() -> void:
	current_state = AIState.FOLLOW


func _physics_process(delta: float) -> void:
	if not player:
		return

	match current_state:
		AIState.FOLLOW:
			_process_follow(delta)
		AIState.IDLE:
			_process_idle(delta)
		AIState.ASSIST:
			_process_assist(delta)
		AIState.AUTONOMOUS:
			_process_autonomous(delta)


func _process_follow(delta: float) -> void:
	var distance := global_position.distance_to(player.global_position)

	if distance < follow_distance * 0.8:
		# Close enough, idle briefly
		velocity = velocity.move_toward(Vector3.ZERO, follow_speed * delta * 5)
	else:
		var direction := (player.global_position - global_position).normalized()
		# Choose speed based on distance
		var speed := catch_up_speed if distance > catch_up_distance else follow_speed
		velocity = direction * speed

		# Face movement direction
		if direction.length() > 0.1:
			var target_rot := atan2(direction.x, direction.z)
			rotation.y = lerp_angle(rotation.y, target_rot, 8.0 * delta)

	move_and_slide()


func _process_idle(delta: float) -> void:
	_idle_timer -= delta
	velocity = Vector3.ZERO
	if _idle_timer <= 0:
		current_state = AIState.FOLLOW


func _process_assist(delta: float) -> void:
	# Move toward player's attack target, deal assist damage
	# Triggered by player's attack_hit signal at bond level >= 3
	pass


func _process_autonomous(delta: float) -> void:
	# Independent combat AI — bond level 7+
	# Uses tongue position for ability selection
	pass


## Called when player attacks — companion assists if bond is high enough
func on_player_attack(damage: float, tongue: String) -> void:
	if bond_level >= 3:
		# Tag team: companion follows up
		var assist_damage := damage * 0.3
		assist_attack.emit(assist_damage)
		bond_event.emit("tag_team")
	elif bond_level >= 5:
		# Fusion move: combined attack
		var fusion_damage := damage * 0.6
		assist_attack.emit(fusion_damage)
		bond_event.emit("fusion")


## Update companion data from backend response
func update_from_state(data: Dictionary) -> void:
	if data.has("tongue_position"):
		tongue_position = data["tongue_position"]
	if data.has("bond_level"):
		bond_level = data["bond_level"]
	if data.has("seal_integrity"):
		seal_integrity = data["seal_integrity"]
	if data.has("evolution_stage"):
		evolution_stage = data["evolution_stage"]
	if data.has("emotional_state"):
		emotional_state = data["emotional_state"]


## Get dominant tongue index
func get_dominant_tongue() -> int:
	var max_idx := 0
	for i in range(1, 6):
		if tongue_position[i] > tongue_position[max_idx]:
			max_idx = i
	return max_idx
