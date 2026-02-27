## SCBE Client — HTTP bridge between Godot and SCBE Python backend
##
## All game state mutations flow through the SCBE pipeline.
## Codex terminal requests are evaluated by the 14-layer pipeline.
##
## Backend: FastAPI + Uvicorn at configurable URL.

extends Node

class_name SCBEClient

# Configuration
@export var backend_url: String = "http://localhost:8000"
@export var timeout: float = 10.0

# Internal
var _http_client: HTTPRequest

# Signals
signal request_completed(response: Dictionary)
signal request_failed(error: String)
signal codex_evaluated(result: Dictionary)


func _ready() -> void:
	_http_client = HTTPRequest.new()
	_http_client.timeout = timeout
	add_child(_http_client)
	_http_client.request_completed.connect(_on_request_completed)


## Evaluate a codex terminal request through SCBE pipeline
func evaluate_codex_request(category: String, query: String, player_tongue: Array[float], player_floor: int) -> void:
	var body := {
		"category": category,
		"query": query,
		"player_tongue": player_tongue,
		"player_floor": player_floor,
		"timestamp": Time.get_unix_time_from_system()
	}
	_post("/api/game/codex/evaluate", body)


## Submit a companion state update
func update_companion_state(companion_id: String, state_update: Dictionary) -> void:
	var body := {
		"companion_id": companion_id,
		"update": state_update
	}
	_post("/api/game/companion/update", body)


## Check evolution availability
func check_evolution(companion_id: String) -> void:
	_get("/api/game/evolution/check/%s" % companion_id)


## Submit combat result
func submit_combat_result(encounter_data: Dictionary) -> void:
	_post("/api/game/combat/result", encounter_data)


## Get tower floor data
func get_floor_data(floor: int) -> void:
	_get("/api/game/tower/floor/%d" % floor)


## Log game event for training pipeline
func log_event(event_data: Dictionary) -> void:
	_post("/api/game/events/log", event_data)


## Check egg hatching conditions
func check_egg_hatching(player_tongue: Array[float]) -> void:
	var body := {"player_tongue": player_tongue}
	_post("/api/game/eggs/check", body)


# -- HTTP helpers --

func _post(path: String, body: Dictionary) -> void:
	var json := JSON.stringify(body)
	var headers := ["Content-Type: application/json"]
	var url := backend_url + path
	_http_client.request(url, headers, HTTPClient.METHOD_POST, json)


func _get(path: String) -> void:
	var url := backend_url + path
	_http_client.request(url)


func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit("HTTP request failed with result: %d" % result)
		return

	if response_code < 200 or response_code >= 300:
		request_failed.emit("HTTP %d error" % response_code)
		return

	var json := JSON.new()
	var parse_result := json.parse(body.get_string_from_utf8())
	if parse_result != OK:
		request_failed.emit("JSON parse error")
		return

	var data: Dictionary = json.data
	request_completed.emit(data)

	# Route to specific signal based on response type
	if data.has("codex_evaluation"):
		codex_evaluated.emit(data["codex_evaluation"])
