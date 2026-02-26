class_name DeterministicRNG
extends Node

## Seeded RNG for reproducible encounters and training data.
## Every dungeon run with the same seed produces the same sequence.

var rng := RandomNumberGenerator.new()
var _seed: int = 0

func _ready():
	add_to_group("rng")

func set_seed(s: int):
	_seed = s
	rng.seed = s

func get_seed() -> int:
	return _seed

func next_int(lo: int, hi: int) -> int:
	return rng.randi_range(lo, hi)

func next_float() -> float:
	return rng.randf()

func next_bool(probability: float = 0.5) -> bool:
	return rng.randf() < probability

func shuffle(arr: Array) -> Array:
	var out := arr.duplicate()
	for i in range(out.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var tmp = out[i]
		out[i] = out[j]
		out[j] = tmp
	return out
