## Codex Terminal UI — In-game internet access with SCBE visualization
##
## Visual effects:
##   Green glow = ALLOW
##   Yellow shimmer = QUARANTINE
##   Red pulse = DENY (+ Polly warning)

extends Control

class_name CodexTerminalUI

@export var scbe_client: SCBEClient
@export var player: PlayerController

@onready var query_input: LineEdit = %QueryInput
@onready var category_selector: OptionButton = %CategorySelector
@onready var result_label: RichTextLabel = %ResultLabel
@onready var glow_effect: ColorRect = %GlowEffect
@onready var polly_warning: Label = %PollyWarning
@onready var rate_limit_bar: ProgressBar = %RateLimitBar
@onready var pipeline_display: VBoxContainer = %PipelineDisplay

# Tongue colors for visual feedback
const TONGUE_COLORS := {
	"KO": Color(0.86, 0.24, 0.24),
	"AV": Color(0.24, 0.71, 0.86),
	"RU": Color(0.86, 0.71, 0.24),
	"CA": Color(0.24, 0.86, 0.47),
	"UM": Color(0.55, 0.24, 0.86),
	"DR": Color(0.86, 0.47, 0.24),
}

# SCBE decision colors
const ALLOW_COLOR := Color(0.2, 0.9, 0.3, 0.3)
const QUARANTINE_COLOR := Color(0.9, 0.8, 0.2, 0.3)
const DENY_COLOR := Color(0.9, 0.2, 0.2, 0.5)


func _ready() -> void:
	visible = false

	# Populate categories
	category_selector.add_item("Math Reference", 0)
	category_selector.add_item("Lore Wiki", 1)
	category_selector.add_item("Creature Codex", 2)
	category_selector.add_item("Strategy Guide", 3)
	category_selector.add_item("Visual Thermal", 4)
	category_selector.add_item("External API", 5)

	if scbe_client:
		scbe_client.codex_evaluated.connect(_on_codex_result)

	polly_warning.visible = false


func open_terminal() -> void:
	visible = true
	query_input.grab_focus()
	glow_effect.color = Color(0.5, 0.5, 0.5, 0.1)
	result_label.text = "Terminal active. Enter your query."
	polly_warning.visible = false


func close_terminal() -> void:
	visible = false
	if player:
		player.end_interaction()


func _on_submit_pressed() -> void:
	var query := query_input.text.strip_edges()
	if query.is_empty():
		return

	var categories := ["math_reference", "lore_wiki", "creature_codex",
					   "strategy_guide", "visual_thermal", "external_api"]
	var cat := categories[category_selector.selected]

	result_label.text = "Evaluating through SCBE pipeline..."
	glow_effect.color = Color(0.5, 0.5, 0.8, 0.2)

	if scbe_client and player:
		scbe_client.evaluate_codex_request(cat, query, player.tongue_experience, 1)


func _on_codex_result(result: Dictionary) -> void:
	var decision: String = result.get("decision", "DENY")
	var harmonic_score: float = result.get("harmonic_score", 0.0)
	var polly_msg: String = result.get("polly_warning", "")
	var rate_remaining: int = result.get("rate_limit_remaining", 0)

	# Visual effect based on decision
	match decision:
		"ALLOW":
			glow_effect.color = ALLOW_COLOR
			result_label.text = "[color=green]ACCESS GRANTED[/color]\nHarmonic Score: %.2f\n\n[Fetching results...]" % harmonic_score
		"QUARANTINE":
			glow_effect.color = QUARANTINE_COLOR
			result_label.text = "[color=yellow]QUARANTINED[/color]\nHarmonic Score: %.2f\n\n[Limited access — response may be delayed]" % harmonic_score
		"DENY":
			glow_effect.color = DENY_COLOR
			result_label.text = "[color=red]ACCESS DENIED[/color]\nHarmonic Score: %.2f" % harmonic_score
		_:
			glow_effect.color = DENY_COLOR
			result_label.text = "[color=red]UNKNOWN DECISION[/color]"

	# Polly warning
	if polly_msg and polly_msg != "":
		polly_warning.text = polly_msg
		polly_warning.visible = true
	else:
		polly_warning.visible = false

	# Rate limit bar
	rate_limit_bar.value = rate_remaining

	# Pipeline layer display
	_update_pipeline_display(result.get("pipeline_layers", []))


func _update_pipeline_display(layers: Array) -> void:
	# Clear existing
	for child in pipeline_display.get_children():
		child.queue_free()

	for layer_data in layers:
		var label := Label.new()
		var layer_num: int = layer_data.get("layer", 0)
		var layer_name: String = layer_data.get("name", "Unknown")
		var score: float = layer_data.get("score", 0.0)
		var passed: bool = layer_data.get("passed", false)

		var status := "✓" if passed else "✗"
		label.text = "L%d %s: %.2f %s" % [layer_num, layer_name, score, status]
		label.add_theme_color_override("font_color", Color.GREEN if passed else Color.RED)

		pipeline_display.add_child(label)


func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("menu"):
		close_terminal()
