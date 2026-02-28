class_name EventValidator
extends Node

## Layer 9: Authentication Envelope — Event Validation & Sanitization
## Every player choice, academy event, and combat action passes through here.
## Prevents Hollow Tongue exploits in choice scripts.
## Coherence check via FFT on tokenized Sacred Tongue representation.

signal event_validated(event: Dictionary, coherence: float)
signal event_quarantined(event: Dictionary, reason: String)

const COHERENCE_THRESHOLD := 0.7
const MAX_EVENT_SIZE := 4096   # Bytes — reject oversized payloads

# Sacred Tongue token grid (simplified 6-tongue mapping)
# Full 16x16 grids live on the SCBE backend; this is the client-side fast check
const TONGUE_WEIGHTS := {
	"KO": 1.00,
	"AV": 1.618,
	"RU": 2.618,
	"CA": 4.236,
	"UM": 6.854,
	"DR": 11.09
}

func _ready():
	add_to_group("event_validator")

func validate(event: Dictionary) -> Dictionary:
	"""Full validation pipeline. Returns {valid, coherence, sanitized_event}."""
	# Step 1: Size check
	var raw := JSON.stringify(event)
	if raw.length() > MAX_EVENT_SIZE:
		_quarantine(event, "Payload too large: %d bytes" % raw.length())
		return {"valid": false, "reason": "oversized"}

	# Step 2: Sanitize — strip injection attempts
	var sanitized := _sanitize(raw)
	if sanitized != raw:
		_log("sanitized_event", {"original_len": raw.length(), "clean_len": sanitized.length()})

	# Step 3: Re-parse sanitized
	var clean_event: Dictionary = JSON.parse_string(sanitized)
	if clean_event == null:
		_quarantine(event, "Sanitization destroyed event structure")
		return {"valid": false, "reason": "parse_fail"}

	# Step 4: Token boundary check — Sacred Tongue coherence
	var tokens := _tokenize_sacred(clean_event)
	var coherence := _compute_coherence(tokens)

	if coherence < COHERENCE_THRESHOLD:
		_quarantine(clean_event, "Low coherence: %.3f" % coherence)
		return {"valid": false, "coherence": coherence, "reason": "low_coherence"}

	# Step 5: Pass
	event_validated.emit(clean_event, coherence)
	_log("event_passed", {"coherence": coherence, "type": clean_event.get("type", "unknown")})
	return {"valid": true, "coherence": coherence, "sanitized_event": clean_event}

func _sanitize(raw: String) -> String:
	"""Remove script tags, null bytes, and control characters."""
	var clean := raw
	# Strip <script> tags
	var regex := RegEx.new()
	regex.compile("<script[^>]*>.*?</script>")
	clean = regex.sub(clean, "", true)
	# Strip null bytes
	clean = clean.replace("\u0000", "")
	# Strip non-printable control chars (keep newlines, tabs)
	var result := ""
	for c in clean:
		var code := c.unicode_at(0)
		if code >= 32 or code == 10 or code == 13 or code == 9:
			result += c
	return result

func _tokenize_sacred(event: Dictionary) -> Array[float]:
	"""Map event fields to Sacred Tongue token values."""
	var choice_text: String = str(event.get("choice", ""))
	var outcome_text: String = str(event.get("outcome", ""))
	var combined := choice_text + outcome_text

	var tokens: Array[float] = []
	for i in range(combined.length()):
		var char_val := float(combined.unicode_at(i))
		# Weight by tongue affinity (cycle through tongues)
		var tongue_keys := TONGUE_WEIGHTS.keys()
		var tongue: String = tongue_keys[i % tongue_keys.size()]
		tokens.append(char_val * TONGUE_WEIGHTS[tongue])
	return tokens

func _compute_coherence(tokens: Array[float]) -> float:
	"""Simplified FFT coherence: low-frequency dominance = coherent."""
	if tokens.is_empty():
		return 1.0  # Empty event is trivially coherent

	# DFT magnitude approximation (no complex FFT in GDScript — send to backend for full)
	var n := tokens.size()
	var dc_component := 0.0
	var ac_energy := 0.0
	for t in tokens:
		dc_component += t
	dc_component = absf(dc_component) / n

	for k in range(1, mini(n, 32)):  # First 32 harmonics
		var re := 0.0
		var im := 0.0
		for i in range(n):
			var angle := 2.0 * PI * k * i / n
			re += tokens[i] * cos(angle)
			im += tokens[i] * sin(angle)
		ac_energy += sqrt(re * re + im * im)

	if dc_component + ac_energy < 0.001:
		return 1.0
	return dc_component / (dc_component + ac_energy)

func _quarantine(event: Dictionary, reason: String):
	event_quarantined.emit(event, reason)
	_log("quarantine", {"reason": reason, "event_type": event.get("type", "?")})

func _log(event_type: String, payload: Dictionary):
	var logger := get_tree().get_first_node_in_group("event_logger")
	if logger:
		logger.log_event("layer9_%s" % event_type, payload)
