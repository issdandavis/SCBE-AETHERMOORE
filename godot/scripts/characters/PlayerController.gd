class_name PlayerController
extends CharacterBody3D

@export var speed := 5.0
@export var roll_speed := 9.0
@export var roll_time := 0.25

var _rolling := false
var _roll_t := 0.0
var _roll_dir := Vector3.ZERO

var _nearby: Array[Interactable] = []

func _ready():
	add_to_group("player")

func _physics_process(delta):
	_handle_roll(delta)
	if _rolling:
		velocity = _roll_dir * roll_speed
	else:
		var input_dir := Vector3.ZERO
		input_dir.x = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
		input_dir.z = Input.get_action_strength("move_back") - Input.get_action_strength("move_forward")
		input_dir = input_dir.normalized()

		velocity.x = input_dir.x * speed
		velocity.z = input_dir.z * speed
		velocity.y = 0

		if input_dir.length() > 0.01:
			look_at(global_position + input_dir, Vector3.UP)

	move_and_slide()

func _unhandled_input(event):
	if event.is_action_pressed("roll") and not _rolling:
		_start_roll()
	if event.is_action_pressed("interact"):
		_try_interact()
	if event.is_action_pressed("attack_light"):
		_attack("light")
	if event.is_action_pressed("attack_heavy"):
		_attack("heavy")

func _start_roll():
	_rolling = true
	_roll_t = 0.0
	_roll_dir = -transform.basis.z.normalized()
	if _roll_dir.length() < 0.01:
		_roll_dir = Vector3.FORWARD

func _handle_roll(delta):
	if not _rolling:
		return
	_roll_t += delta
	if _roll_t >= roll_time:
		_rolling = false

func _try_interact():
	if _nearby.is_empty():
		return
	var best: Interactable = _nearby[0]
	var best_d := global_position.distance_to(best.global_position)
	for it in _nearby:
		var d := global_position.distance_to(it.global_position)
		if d < best_d:
			best = it
			best_d = d
	best.interact()

func _attack(kind: String):
	# placeholder: later hook AnimationTree + hitboxes
	print("Attack:", kind)

func register_interactable(it: Interactable):
	if not _nearby.has(it):
		_nearby.append(it)

func unregister_interactable(it: Interactable):
	_nearby.erase(it)
