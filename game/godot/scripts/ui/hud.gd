## HUD — In-game heads-up display
##
## Shows: health bar, tongue meters (6 bars), companion bond,
## rank badge, gold counter, notification toasts.
## GDD: big pixel-font HUD with tongue glyphs + "Spiral Meter" (λ₂)

extends CanvasLayer

class_name HUD

# UI node references (built in _ready)
var health_bar: ProgressBar
var tongue_bars: Array[ProgressBar] = []
var tongue_labels: Array[Label] = []
var gold_label: Label
var rank_label: Label
var bond_label: Label
var notification_label: Label
var spiral_meter: ProgressBar  # Spectral gap λ₂

var _notification_timer: float = 0.0
const NOTIFICATION_DURATION: float = 3.0


func _ready() -> void:
	layer = 10
	_build_ui()
	_connect_signals()
	_update_all()


func _process(delta: float) -> void:
	# Fade notification
	if _notification_timer > 0:
		_notification_timer -= delta
		if _notification_timer <= 0:
			notification_label.visible = false


func _build_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	# -- Top-left: Health bar --
	var health_container := VBoxContainer.new()
	health_container.position = Vector2(8, 8)
	health_container.size = Vector2(120, 20)
	root.add_child(health_container)

	var health_label := Label.new()
	health_label.text = "SEAL"
	health_label.add_theme_font_size_override("font_size", 10)
	health_container.add_child(health_label)

	health_bar = ProgressBar.new()
	health_bar.custom_minimum_size = Vector2(120, 8)
	health_bar.max_value = 100
	health_bar.value = 100
	health_bar.show_percentage = false
	health_container.add_child(health_bar)

	# -- Top-left: Tongue meters (6 bars below health) --
	var tongue_container := VBoxContainer.new()
	tongue_container.position = Vector2(8, 42)
	root.add_child(tongue_container)

	for i in range(6):
		var row := HBoxContainer.new()
		tongue_container.add_child(row)

		var lbl := Label.new()
		lbl.text = TongueSystem.TONGUE_NAMES[i]
		lbl.add_theme_font_size_override("font_size", 8)
		lbl.add_theme_color_override("font_color", TongueSystem.get_tongue_color(i))
		lbl.custom_minimum_size = Vector2(20, 10)
		row.add_child(lbl)
		tongue_labels.append(lbl)

		var bar := ProgressBar.new()
		bar.custom_minimum_size = Vector2(80, 6)
		bar.max_value = 10.0
		bar.value = 0.0
		bar.show_percentage = false
		row.add_child(bar)
		tongue_bars.append(bar)

	# -- Top-right: Rank badge + Gold --
	var top_right := VBoxContainer.new()
	top_right.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	top_right.position = Vector2(-130, 8)
	top_right.size = Vector2(120, 50)
	root.add_child(top_right)

	rank_label = Label.new()
	rank_label.text = "Rank: F"
	rank_label.add_theme_font_size_override("font_size", 14)
	rank_label.add_theme_color_override("font_color", Color.GOLD)
	rank_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	top_right.add_child(rank_label)

	gold_label = Label.new()
	gold_label.text = "Gold: 50"
	gold_label.add_theme_font_size_override("font_size", 10)
	gold_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	top_right.add_child(gold_label)

	bond_label = Label.new()
	bond_label.text = "Bond: --"
	bond_label.add_theme_font_size_override("font_size", 10)
	bond_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	top_right.add_child(bond_label)

	# -- Bottom-right: Spiral Meter (λ₂) --
	var spiral_container := VBoxContainer.new()
	spiral_container.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	spiral_container.position = Vector2(-130, -40)
	spiral_container.size = Vector2(120, 30)
	root.add_child(spiral_container)

	var spiral_label := Label.new()
	spiral_label.text = "SPIRAL"
	spiral_label.add_theme_font_size_override("font_size", 8)
	spiral_label.add_theme_color_override("font_color", Color(0.8, 0.6, 1.0))
	spiral_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	spiral_container.add_child(spiral_label)

	spiral_meter = ProgressBar.new()
	spiral_meter.custom_minimum_size = Vector2(120, 6)
	spiral_meter.max_value = 1.0
	spiral_meter.value = 0.0
	spiral_meter.show_percentage = false
	spiral_container.add_child(spiral_meter)

	# -- Bottom-center: Notification toast --
	notification_label = Label.new()
	notification_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	notification_label.position = Vector2(-200, -30)
	notification_label.size = Vector2(400, 24)
	notification_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notification_label.add_theme_font_size_override("font_size", 12)
	notification_label.visible = false
	root.add_child(notification_label)


func _connect_signals() -> void:
	EventBus.player_health_changed.connect(_on_health_changed)
	EventBus.player_tongue_gained.connect(_on_tongue_gained)
	EventBus.notification_requested.connect(_on_notification)
	EventBus.companion_bond_changed.connect(_on_bond_changed)


func _update_all() -> void:
	health_bar.value = GameState.current_health
	health_bar.max_value = GameState.max_health

	for i in range(6):
		tongue_bars[i].value = GameState.tongue_xp[i]

	rank_label.text = "Rank: %s" % GameState.player_rank
	gold_label.text = "Gold: %d" % GameState.gold

	var comp := GameState.get_active_companion()
	if not comp.is_empty():
		bond_label.text = "Bond: %d" % comp.get("bond", 0)
	else:
		bond_label.text = "Bond: --"


func _on_health_changed(current: float, maximum: float) -> void:
	health_bar.max_value = maximum
	health_bar.value = current


func _on_tongue_gained(tongue_index: int, _amount: float) -> void:
	if tongue_index >= 0 and tongue_index < 6:
		tongue_bars[tongue_index].value = GameState.tongue_xp[tongue_index]


func _on_notification(message: String, color: Color) -> void:
	notification_label.text = message
	notification_label.add_theme_color_override("font_color", color)
	notification_label.visible = true
	_notification_timer = NOTIFICATION_DURATION


func _on_bond_changed(_companion_id: String, new_level: int) -> void:
	bond_label.text = "Bond: %d" % new_level
