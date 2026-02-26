## DialoguePanel — NPC dialogue display with typewriter effect
##
## GDD Section 2.2: No cutscene longer than 90 seconds.
## Dialogue advances on interact key press.

extends CanvasLayer

class_name DialoguePanel

var panel: PanelContainer
var speaker_label: Label
var text_label: RichTextLabel
var advance_hint: Label

var _lines: Array[Dictionary] = []
var _current_line: int = 0
var _is_visible: bool = false
var _typewriter_progress: float = 0.0
var _typewriter_speed: float = 30.0  # Characters per second
var _current_text: String = ""
var _text_complete: bool = false


func _ready() -> void:
	layer = 11
	_build_ui()
	visible = false

	EventBus.dialogue_requested.connect(_on_dialogue_requested)


func _process(delta: float) -> void:
	if not _is_visible:
		return

	# Typewriter effect
	if not _text_complete:
		_typewriter_progress += _typewriter_speed * delta
		var chars := int(_typewriter_progress)
		if chars >= _current_text.length():
			text_label.text = _current_text
			_text_complete = true
			advance_hint.text = "[E] Continue"
		else:
			text_label.text = _current_text.substr(0, chars)


func _input(event: InputEvent) -> void:
	if not _is_visible:
		return

	if event.is_action_pressed("interact"):
		if not _text_complete:
			# Skip typewriter — show full text
			text_label.text = _current_text
			_text_complete = true
			advance_hint.text = "[E] Continue"
		else:
			_advance_dialogue()


func _build_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	# Dialogue box at bottom of screen
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	panel.position = Vector2(20, -80)
	panel.size = Vector2(440, 70)
	root.add_child(panel)

	var vbox := VBoxContainer.new()
	panel.add_child(vbox)

	speaker_label = Label.new()
	speaker_label.add_theme_font_size_override("font_size", 10)
	speaker_label.add_theme_color_override("font_color", Color.GOLD)
	vbox.add_child(speaker_label)

	text_label = RichTextLabel.new()
	text_label.custom_minimum_size = Vector2(400, 35)
	text_label.bbcode_enabled = false
	text_label.scroll_active = false
	text_label.add_theme_font_size_override("normal_font_size", 9)
	vbox.add_child(text_label)

	advance_hint = Label.new()
	advance_hint.text = ""
	advance_hint.add_theme_font_size_override("font_size", 7)
	advance_hint.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	advance_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vbox.add_child(advance_hint)


func _on_dialogue_requested(speaker: String, lines: Array) -> void:
	_lines = []
	for line in lines:
		_lines.append(line as Dictionary)
	_current_line = 0
	_is_visible = true
	visible = true
	_show_line()


func _show_line() -> void:
	if _current_line >= _lines.size():
		_close()
		return

	var line: Dictionary = _lines[_current_line]
	var speaker: String = line.get("speaker", "")
	_current_text = line.get("text", "")

	speaker_label.text = speaker if speaker != "" else ""
	text_label.text = ""
	_typewriter_progress = 0.0
	_text_complete = false
	advance_hint.text = "[E] Skip"


func _advance_dialogue() -> void:
	_current_line += 1
	if _current_line >= _lines.size():
		_close()
	else:
		_show_line()


func _close() -> void:
	_is_visible = false
	visible = false
	_lines.clear()
	_current_line = 0
	# Notify that dialogue ended
	if _lines.size() > 0:
		var speaker: String = _lines[0].get("speaker", "")
		EventBus.npc_dialogue_ended.emit(speaker)
