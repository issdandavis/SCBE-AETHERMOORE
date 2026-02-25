class_name TrainingLogger
extends Node

## Layer 12: Entropic Defense Engine — Core Training & Culture Growth
## Collects all game events, validates via Layer 9, signs via Layer 14,
## batches for HF upload. Feeds the autonomous 24/7 poly-AI training loop.
## This is the Godot-side client for scripts/ouroboros_self_learn.py.

signal batch_ready(batch: Array[Dictionary])
signal upload_complete(count: int)

const BATCH_SIZE := 100
const RHO_E_MAX := 5.0

var _buffer: Array[Dictionary] = []
var _total_approved: int = 0
var _total_rejected: int = 0
var _upload_path: String = "user://training_batches/"

func _ready():
	add_to_group("training_logger")
	# Ensure batch output directory exists
	DirAccess.make_dir_recursive_absolute(_upload_path)

func record_game_event(event: Dictionary):
	"""Main entry point — every significant game event flows here."""
	# Layer 9: Validate
	var validator := get_tree().get_first_node_in_group("event_validator")
	if validator:
		var result := validator.validate(event)
		if not result.get("valid", false):
			_total_rejected += 1
			_log("rejected", {"reason": result.get("reason", "?"), "event_type": event.get("type", "?")})
			return

	# Compute rho_e for the event outcome
	var rho_e := _compute_event_rho_e(event)
	if rho_e >= RHO_E_MAX:
		_total_rejected += 1
		_log("entropy_rejected", {"rho_e": rho_e, "event_type": event.get("type", "?")})
		return

	# Layer 14: Sign the event
	var signer := get_tree().get_first_node_in_group("pqc_signer")
	var signed_event := event.duplicate(true)
	if signer:
		signed_event = signer.sign_event(event)

	# Add training metadata
	signed_event["_training_meta"] = {
		"rho_e": rho_e,
		"approved_at": Time.get_unix_time_from_system(),
		"batch_index": _buffer.size()
	}

	_buffer.append(signed_event)
	_total_approved += 1
	_log("approved", {"rho_e": rho_e, "buffer_size": _buffer.size()})

	# Check batch threshold
	if _buffer.size() >= BATCH_SIZE:
		_flush_batch()

func _compute_event_rho_e(event: Dictionary) -> float:
	"""Approximate entropic divergence from event outcome data."""
	var outcome = event.get("outcome", {})
	if outcome is Dictionary:
		# Use training_pair if available (combat events)
		var reward: float = outcome.get("reward", 0.0)
		var moves_used: int = outcome.get("moves_used", 0)
		# Higher move count + negative reward = higher entropy
		return absf(reward) * 0.5 + moves_used * 0.3
	return 0.0

func _flush_batch():
	"""Write batch to disk as JSONL and signal for upload."""
	if _buffer.is_empty():
		return

	var batch := _buffer.duplicate(true)
	_buffer.clear()

	# Write to disk
	var filename := "batch_%d.jsonl" % Time.get_unix_time_from_system()
	var filepath := _upload_path + filename
	var f := FileAccess.open(filepath, FileAccess.WRITE)
	if f:
		for event in batch:
			f.store_line(JSON.stringify(event))
		f.close()
		_log("batch_written", {"file": filename, "count": batch.size()})

	batch_ready.emit(batch)

	# Trigger SCBE backend upload via HTTP
	_upload_to_scbe(filepath, batch.size())

func _upload_to_scbe(filepath: String, count: int):
	"""POST batch to SCBE training pipeline endpoint."""
	var client := get_tree().get_first_node_in_group("scbe_client")
	if client:
		client.upload_training_batch(filepath, func(success: bool):
			if success:
				upload_complete.emit(count)
				_log("upload_success", {"count": count})
			else:
				_log("upload_failed", {"count": count, "file": filepath})
		)

func get_stats() -> Dictionary:
	return {
		"total_approved": _total_approved,
		"total_rejected": _total_rejected,
		"buffer_size": _buffer.size(),
		"approval_rate": float(_total_approved) / maxf(_total_approved + _total_rejected, 1.0)
	}

func force_flush():
	"""Manual flush — useful at session end or dungeon completion."""
	_flush_batch()

func _log(event_type: String, payload: Dictionary):
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("layer12_%s" % event_type, payload)
