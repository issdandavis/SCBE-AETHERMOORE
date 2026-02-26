## ShopPanel — Buy/sell interface for tongue-themed items
##
## GDD Section 13: Economy with Gold, Proof Tokens, Culture Points, Reputation
## Each item has a tongue affinity and grants XP when purchased.

extends CanvasLayer

class_name ShopPanel

var panel: PanelContainer
var title_label: Label
var items_container: VBoxContainer
var gold_display: Label
var close_button: Button

var _shop_items: Array[Dictionary] = []
var _is_visible: bool = false
var _shop_npc_id: String = ""


func _ready() -> void:
	layer = 12
	_build_ui()
	visible = false

	EventBus.shop_opened.connect(_on_shop_opened)


func _input(event: InputEvent) -> void:
	if _is_visible and event.is_action_pressed("menu"):
		_close_shop()


func _build_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)

	# Semi-transparent background
	var bg := ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0, 0, 0, 0.5)
	root.add_child(bg)

	# Shop panel centered
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-150, -120)
	panel.size = Vector2(300, 240)
	root.add_child(panel)

	var vbox := VBoxContainer.new()
	panel.add_child(vbox)

	title_label = Label.new()
	title_label.text = "SHOP"
	title_label.add_theme_font_size_override("font_size", 14)
	title_label.add_theme_color_override("font_color", Color.GOLD)
	title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title_label)

	# Separator
	var sep := HSeparator.new()
	vbox.add_child(sep)

	# Gold display
	gold_display = Label.new()
	gold_display.add_theme_font_size_override("font_size", 10)
	gold_display.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vbox.add_child(gold_display)

	# Scrollable item list
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(280, 160)
	vbox.add_child(scroll)

	items_container = VBoxContainer.new()
	items_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(items_container)

	# Close button
	close_button = Button.new()
	close_button.text = "Close [ESC]"
	close_button.pressed.connect(_close_shop)
	vbox.add_child(close_button)


func _on_shop_opened(npc_id: String) -> void:
	_shop_npc_id = npc_id
	# Find NPC's shop items from HearthstoneManager NPCs
	# For now, use default items if we can't find the NPC
	_shop_items = _get_npc_shop_items(npc_id)
	_populate_items()
	_is_visible = true
	visible = true


func _get_npc_shop_items(npc_id: String) -> Array[Dictionary]:
	# Default shop items for Hearthstone Landing
	return [
		{"id": "potion_seal", "name": "Seal Salve", "price": 10, "tongue": "UM",
		 "desc": "Restores 30 seal integrity."},
		{"id": "focus_lens", "name": "Focus Lens", "price": 25, "tongue": "CA",
		 "desc": "+0.1 Insight for one encounter."},
		{"id": "drift_anchor", "name": "Drift Anchor", "price": 15, "tongue": "DR",
		 "desc": "Reduces drift by 0.05."},
		{"id": "ember_shard", "name": "Ember Shard", "price": 20, "tongue": "KO",
		 "desc": "+0.5 KO tongue XP."},
	]


func _populate_items() -> void:
	# Clear existing
	for child in items_container.get_children():
		child.queue_free()

	gold_display.text = "Gold: %d" % GameState.gold

	for item in _shop_items:
		var row := HBoxContainer.new()
		items_container.add_child(row)

		# Tongue color indicator
		var tongue_dot := ColorRect.new()
		tongue_dot.custom_minimum_size = Vector2(8, 8)
		var tongue_idx := _tongue_name_to_index(item.get("tongue", ""))
		tongue_dot.color = TongueSystem.get_tongue_color(tongue_idx) if tongue_idx >= 0 else Color.WHITE
		row.add_child(tongue_dot)

		# Item name + description
		var info := VBoxContainer.new()
		info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(info)

		var name_lbl := Label.new()
		name_lbl.text = item.get("name", "???")
		name_lbl.add_theme_font_size_override("font_size", 9)
		info.add_child(name_lbl)

		var desc_lbl := Label.new()
		desc_lbl.text = item.get("desc", "")
		desc_lbl.add_theme_font_size_override("font_size", 7)
		desc_lbl.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
		info.add_child(desc_lbl)

		# Buy button with price
		var buy_btn := Button.new()
		buy_btn.text = "%d G" % item.get("price", 0)
		buy_btn.custom_minimum_size = Vector2(50, 20)
		var item_data := item  # Capture for lambda
		buy_btn.pressed.connect(func(): _buy_item(item_data))
		row.add_child(buy_btn)


func _buy_item(item: Dictionary) -> void:
	var price: int = item.get("price", 0)
	if GameState.gold < price:
		EventBus.notification_requested.emit("Not enough gold!", Color.RED)
		return

	GameState.gold -= price
	GameState.add_item(item["id"], item["name"], 1, item.get("tongue", ""))

	# Grant tongue XP for purchase
	var tongue_idx := _tongue_name_to_index(item.get("tongue", ""))
	if tongue_idx >= 0:
		GameState.gain_tongue_xp(tongue_idx, 0.2)

	gold_display.text = "Gold: %d" % GameState.gold
	EventBus.notification_requested.emit(
		"Bought %s!" % item["name"], Color.GREEN)


func _close_shop() -> void:
	_is_visible = false
	visible = false
	EventBus.shop_closed.emit()


func _tongue_name_to_index(name: String) -> int:
	match name:
		"KO": return 0
		"AV": return 1
		"RU": return 2
		"CA": return 3
		"UM": return 4
		"DR": return 5
		_: return -1
