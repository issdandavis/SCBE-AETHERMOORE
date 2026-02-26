## CameraController — 3/4 top-down follow camera
##
## GDD spec: 3/4 top-down, slight diagonal shadow offset
## Smooth follow with look-ahead in movement direction.

extends Camera3D

class_name CameraController

@export var target: Node3D
@export var offset: Vector3 = Vector3(0, 10, 8)  # 3/4 top-down angle
@export var follow_speed: float = 5.0
@export var look_ahead: float = 2.0  # Pixels ahead in move direction
@export var rotation_angle: float = -45.0  # Pitch down

var _target_position: Vector3 = Vector3.ZERO
var _look_ahead_offset: Vector3 = Vector3.ZERO


func _ready() -> void:
	# Set initial pitch for 3/4 view
	rotation_degrees.x = rotation_angle
	if target:
		global_position = target.global_position + offset
		look_at(target.global_position, Vector3.UP)


func _physics_process(delta: float) -> void:
	if not target:
		return

	# Compute look-ahead based on target velocity
	if target is CharacterBody3D:
		var vel: Vector3 = (target as CharacterBody3D).velocity
		if vel.length() > 0.5:
			_look_ahead_offset = _look_ahead_offset.lerp(
				vel.normalized() * look_ahead, 3.0 * delta)
		else:
			_look_ahead_offset = _look_ahead_offset.lerp(Vector3.ZERO, 5.0 * delta)

	# Smooth follow
	_target_position = target.global_position + _look_ahead_offset + offset
	global_position = global_position.lerp(_target_position, follow_speed * delta)

	# Always look at target area
	var look_target := target.global_position + _look_ahead_offset
	look_at(look_target, Vector3.UP)
