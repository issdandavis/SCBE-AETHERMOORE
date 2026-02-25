class_name PQCSigner
extends Node

## Layer 14: Topological CFI / PQC Protocol — Signed Nodal Provenance
## Signs every game event for tamper-proof training data.
## Client-side: HMAC-SHA256 with session key (full ML-DSA-65 runs on backend).
## Includes 21D metadata slice (dims 16-21: swarm + culture state).

const HMAC_KEY_ENVVAR := "SCBE_GAME_HMAC_KEY"
var _session_key: String = ""
var _sign_counter: int = 0

func _ready():
	add_to_group("pqc_signer")
	_session_key = _derive_session_key()

func sign_event(event: Dictionary) -> Dictionary:
	"""Sign a game event with HMAC + 21D metadata."""
	_sign_counter += 1

	var payload := JSON.stringify(event)
	var signature := _hmac_sha256(payload)

	var signed := event.duplicate(true)
	signed["_pqc"] = {
		"signature": signature,
		"algorithm": "HMAC-SHA256-client",   # Backend upgrades to ML-DSA-65
		"counter": _sign_counter,
		"ts": Time.get_unix_time_from_system(),
		"21d_meta": _get_21d_culture_slice(),
		"session_id": _get_session_id()
	}

	_log("signed", {"counter": _sign_counter, "event_type": event.get("type", "?")})
	return signed

func verify_event(signed_event: Dictionary) -> bool:
	"""Client-side verification (re-compute HMAC)."""
	var pqc: Dictionary = signed_event.get("_pqc", {})
	if pqc.is_empty():
		return false

	# Strip signature fields, re-sign, compare
	var event_copy := signed_event.duplicate(true)
	event_copy.erase("_pqc")
	var expected := _hmac_sha256(JSON.stringify(event_copy))
	return expected == pqc.get("signature", "")

func _hmac_sha256(message: String) -> String:
	"""HMAC-SHA256 using Godot's crypto."""
	var key_bytes := _session_key.to_utf8_buffer()
	var msg_bytes := message.to_utf8_buffer()

	# HMAC: H((K xor opad) || H((K xor ipad) || message))
	var block_size := 64
	if key_bytes.size() > block_size:
		key_bytes = key_bytes.sha256_buffer()
	while key_bytes.size() < block_size:
		key_bytes.append(0)

	var o_key_pad := PackedByteArray()
	var i_key_pad := PackedByteArray()
	o_key_pad.resize(block_size)
	i_key_pad.resize(block_size)
	for i in range(block_size):
		o_key_pad[i] = key_bytes[i] ^ 0x5c
		i_key_pad[i] = key_bytes[i] ^ 0x36

	# Inner hash
	var inner := PackedByteArray()
	inner.append_array(i_key_pad)
	inner.append_array(msg_bytes)
	var inner_hash := inner.sha256_buffer()

	# Outer hash
	var outer := PackedByteArray()
	outer.append_array(o_key_pad)
	outer.append_array(inner_hash)
	return outer.sha256_buffer().hex_encode()

func _derive_session_key() -> String:
	"""Derive session key from environment or generate ephemeral."""
	var env_key := OS.get_environment(HMAC_KEY_ENVVAR)
	if env_key != "":
		return env_key
	# Ephemeral key for local play — backend re-signs with ML-DSA-65
	var crypto := Crypto.new()
	return crypto.generate_random_bytes(32).hex_encode()

func _get_21d_culture_slice() -> Array:
	"""Dims 16-21 of canonical state: swarm coherence + culture metrics."""
	var gs := get_tree().get_first_node_in_group("game_state")
	if gs and gs.has_meta("state_21d"):
		var full_state: Array = gs.get_meta("state_21d")
		if full_state.size() >= 21:
			return full_state.slice(15, 21)
	return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

func _get_session_id() -> String:
	var gs := get_tree().get_first_node_in_group("game_state")
	if gs:
		return gs.session_id
	return "unknown"

func _log(event_type: String, payload: Dictionary):
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("layer14_%s" % event_type, payload)
