## Player Controller — Zelda-style 3D movement + combat
## 3/4 top-down camera, 8-direction movement, sword combat, dodge roll.
##
## Input: WASD movement, J light attack, K heavy attack, Space dodge, E interact

extends CharacterBody3D

class_name PlayerController

# Movement
@export var move_speed: float = 5.0
@export var dodge_speed: float = 12.0
@export var dodge_duration: float = 0.3
@export var rotation_speed: float = 10.0

# Combat
@export var light_damage: float = 10.0
@export var heavy_damage: float = 25.0
@export var heavy_charge_time: float = 0.5
@export var attack_cooldown: float = 0.3

# State
enum State { IDLE, MOVE, ATTACK_LIGHT, ATTACK_HEAVY, DODGE, INTERACT }
var current_state: State = State.IDLE

# Internal
var _move_direction: Vector3 = Vector3.ZERO
var _dodge_timer: float = 0.0
var _attack_timer: float = 0.0
var _is_invulnerable: bool = false

# Tongue experience accumulation (sent to backend)
var tongue_experience: Array[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

# Companion following
var active_companion: Node3D = null

# Signals
signal attack_hit(damage: float, tongue: String)
signal dodge_started()
signal dodge_ended()
signal interact_triggered(target: Node3D)
signal tongue_experience_gained(tongue_index: int, amount: float)


func _ready() -> void:
	current_state = State.IDLE


func _physics_process(delta: float) -> void:
	match current_state:
		State.IDLE, State.MOVE:
			_process_movement(delta)
			_check_combat_input()
			_check_interact()
		State.DODGE:
			_process_dodge(delta)
		State.ATTACK_LIGHT, State.ATTACK_HEAVY:
			_process_attack(delta)
		State.INTERACT:
			pass  # Handled by UI


func _process_movement(delta: float) -> void:
	# Get input direction
	var input_dir := Vector2.ZERO
	input_dir.x = Input.get_axis("move_left", "move_right")
	input_dir.y = Input.get_axis("move_up", "move_down")

	if input_dir.length() > 0.1:
		input_dir = input_dir.normalized()
		# Convert to 3D (top-down: x = right, z = forward/down)
		_move_direction = Vector3(input_dir.x, 0, input_dir.y)

		# Rotate toward movement direction
		var target_rotation := atan2(_move_direction.x, _move_direction.z)
		rotation.y = lerp_angle(rotation.y, target_rotation, rotation_speed * delta)

		velocity = _move_direction * move_speed
		current_state = State.MOVE
	else:
		velocity = velocity.move_toward(Vector3.ZERO, move_speed * delta * 10)
		if velocity.length() < 0.1:
			current_state = State.IDLE

	move_and_slide()


func _check_combat_input() -> void:
	if _attack_timer > 0:
		return

	if Input.is_action_just_pressed("dodge"):
		_start_dodge()
	elif Input.is_action_just_pressed("attack_light"):
		_start_light_attack()
	elif Input.is_action_just_pressed("attack_heavy"):
		_start_heavy_attack()


func _check_interact() -> void:
	if Input.is_action_just_pressed("interact"):
		# Raycast forward to find interactable
		var space := get_world_3d().direct_space_state
		var from := global_position + Vector3.UP * 0.5
		var to := from + -transform.basis.z * 2.0
		var query := PhysicsRayQueryParameters3D.create(from, to)
		query.collision_mask = 0b0100  # Interaction layer
		var result := space.intersect_ray(query)
		if result:
			interact_triggered.emit(result.collider)
			current_state = State.INTERACT


func _start_dodge() -> void:
	current_state = State.DODGE
	_dodge_timer = dodge_duration
	_is_invulnerable = true
	velocity = _move_direction * dodge_speed if _move_direction.length() > 0.1 else -transform.basis.z * dodge_speed
	dodge_started.emit()


func _process_dodge(delta: float) -> void:
	_dodge_timer -= delta
	move_and_slide()
	if _dodge_timer <= 0:
		_is_invulnerable = false
		current_state = State.IDLE
		dodge_ended.emit()


func _start_light_attack() -> void:
	current_state = State.ATTACK_LIGHT
	_attack_timer = attack_cooldown
	# Hit detection handled by AnimationPlayer signal
	attack_hit.emit(light_damage, "KO")


func _start_heavy_attack() -> void:
	current_state = State.ATTACK_HEAVY
	_attack_timer = heavy_charge_time + attack_cooldown
	attack_hit.emit(heavy_damage, "DR")


func _process_attack(delta: float) -> void:
	_attack_timer -= delta
	# Slow down during attack
	velocity = velocity.move_toward(Vector3.ZERO, move_speed * delta * 5)
	move_and_slide()
	if _attack_timer <= 0:
		current_state = State.IDLE


## Add tongue experience from gameplay actions
func gain_tongue_experience(tongue_index: int, amount: float) -> void:
	if tongue_index >= 0 and tongue_index < 6:
		tongue_experience[tongue_index] += amount
		tongue_experience_gained.emit(tongue_index, amount)


## Check if player is invulnerable (during dodge)
func is_invulnerable() -> bool:
	return _is_invulnerable


## End interaction state (called by UI)
func end_interaction() -> void:
	current_state = State.IDLE
