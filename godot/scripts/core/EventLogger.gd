class_name EventLogger
extends Node

## Logs gameplay events as JSONL for training data generation.
## Each line: {timestamp, event_type, payload, session_id}

var _log_path: String = "user://event_log.jsonl"
var _file: FileAccess = null

func _ready():
	add_to_group("event_logger")
	_file = FileAccess.open(_log_path, FileAccess.WRITE)
	if _file == null:
		push_warning("EventLogger: could not open log file at %s" % _log_path)

func log_event(event_type: String, payload: Dictionary = {}):
	if _file == null:
		return
	var gs := get_tree().get_first_node_in_group("game_state")
	var session_id := ""
	if gs:
		session_id = gs.session_id

	var entry := {
		"timestamp": Time.get_unix_time_from_system(),
		"event_type": event_type,
		"payload": payload,
		"session_id": session_id
	}
	_file.store_line(JSON.stringify(entry))
	_file.flush()

func _exit_tree():
	if _file:
		_file.close()
