class_name SCBEClient
extends Node

## SCBE API Gateway Client — Godot talks to the SCBE backend.
## Every game action routes through here → Layer 9 (validate) → Layer 14 (sign)
## → backend (Oracle, training pipeline, governance gate).
##
## Endpoints map to existing SCBE FastAPI routes:
##   POST /api/v1/verify        → Oracle math validation
##   POST /api/v1/gate          → Governance decision (ALLOW/QUARANTINE/DENY)
##   POST /api/v1/training/batch → Upload training data
##   GET  /api/v1/state          → Fetch 21D canonical state

signal request_completed(endpoint: String, response: Dictionary)
signal request_failed(endpoint: String, error: String)

@export var base_url: String = "http://localhost:8000"
@export var api_version: String = "v1"

var _http: HTTPRequest = null
var _pending_callbacks: Dictionary = {}

func _ready():
	add_to_group("scbe_client")
	_http = HTTPRequest.new()
	add_child(_http)
	_http.request_completed.connect(_on_request_completed)

func get_api_url(endpoint: String) -> String:
	return "%s/api/%s/%s" % [base_url, api_version, endpoint]

# --- Oracle (Layer 11 math combat validation) ---

func verify_math_transform(before_expr: String, after_expr: String, transform: String,
		constraints: Dictionary = {}, callback: Callable = Callable()) -> Error:
	"""POST /verify — Oracle validates a combat move."""
	var body := {
		"before_expr": before_expr,
		"after_expr": after_expr,
		"transform": transform,
		"constraints": constraints
	}
	return _post("verify", body, callback)

# --- Governance Gate (all layers) ---

func gate_check(intent: Dictionary, context: Dictionary,
		callback: Callable = Callable()) -> Error:
	"""POST /gate — SCBE governance decision."""
	var body := {
		"intent": intent,
		"context": context,
		"source": "godot_client"
	}
	return _post("gate", body, callback)

# --- Training Pipeline (Layer 12) ---

func upload_training_batch(filepath: String, callback: Callable = Callable()) -> Error:
	"""POST /training/batch — Upload signed training events."""
	var f := FileAccess.open(filepath, FileAccess.READ)
	if f == null:
		request_failed.emit("training/batch", "Cannot open file: %s" % filepath)
		return ERR_FILE_NOT_FOUND

	var events: Array[Dictionary] = []
	while not f.eof_reached():
		var line := f.get_line().strip_edges()
		if line != "":
			var parsed = JSON.parse_string(line)
			if parsed != null:
				events.append(parsed)
	f.close()

	var body := {"events": events, "source": "godot_game"}
	return _post("training/batch", body, callback)

# --- State (21D canonical) ---

func fetch_canonical_state(callback: Callable = Callable()) -> Error:
	"""GET /state — Fetch current 21D canonical state from backend."""
	return _get("state", callback)

# --- Creature Evolution (Layer 7 via backend) ---

func request_evolution_check(creature_data: Dictionary,
		callback: Callable = Callable()) -> Error:
	"""POST /evolution/check — Backend validates evolution eligibility."""
	return _post("evolution/check", creature_data, callback)

# --- HTTP internals ---

func _post(endpoint: String, body: Dictionary, callback: Callable = Callable()) -> Error:
	var url := get_api_url(endpoint)
	var json_body := JSON.stringify(body)
	var headers := ["Content-Type: application/json", "Accept: application/json"]

	if callback.is_valid():
		_pending_callbacks[endpoint] = callback

	var err := _http.request(url, headers, HTTPClient.METHOD_POST, json_body)
	if err != OK:
		request_failed.emit(endpoint, "HTTP request error: %d" % err)
	return err

func _get(endpoint: String, callback: Callable = Callable()) -> Error:
	var url := get_api_url(endpoint)
	var headers := ["Accept: application/json"]

	if callback.is_valid():
		_pending_callbacks[endpoint] = callback

	var err := _http.request(url, headers, HTTPClient.METHOD_GET)
	if err != OK:
		request_failed.emit(endpoint, "HTTP request error: %d" % err)
	return err

func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray):
	var response_text := body.get_string_from_utf8()
	var parsed = JSON.parse_string(response_text)
	if parsed == null:
		parsed = {"raw": response_text, "error": "parse_failed"}

	if response_code >= 200 and response_code < 300:
		# Find matching callback by checking pending
		for endpoint in _pending_callbacks:
			var cb: Callable = _pending_callbacks[endpoint]
			_pending_callbacks.erase(endpoint)
			if cb.is_valid():
				cb.call(true, parsed)
			request_completed.emit(endpoint, parsed)
			break
	else:
		for endpoint in _pending_callbacks:
			var cb: Callable = _pending_callbacks[endpoint]
			_pending_callbacks.erase(endpoint)
			if cb.is_valid():
				cb.call(false, parsed)
			request_failed.emit(endpoint, "HTTP %d: %s" % [response_code, response_text])
			break
