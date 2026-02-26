## EventBus — Global signal relay for decoupled communication
##
## Avoids tight coupling between game systems. Any node can emit/listen
## without holding a direct reference.

extends Node

# -- Player events --
signal player_attacked(damage: float, tongue: String)
signal player_dodged()
signal player_interacted(target: Node3D)
signal player_tongue_gained(tongue_index: int, amount: float)
signal player_health_changed(current: float, maximum: float)

# -- Companion events --
signal companion_assist(damage: float)
signal companion_bond_changed(companion_id: String, new_level: int)
signal companion_evolution_ready(companion_id: String, options: Array)
signal companion_hatched(egg_type: String, species: String)
signal companion_state_updated(companion_id: String, state: Dictionary)

# -- Combat events --
signal combat_started(encounter_data: Dictionary)
signal combat_ended(result: Dictionary)
signal transform_applied(transform_name: String, valid: bool, reward: float)
signal combat_damage_dealt(source: String, target: String, amount: float, tongue: String)

# -- World events --
signal zone_entered(zone_name: String, tongue: String)
signal npc_dialogue_started(npc_id: String)
signal npc_dialogue_ended(npc_id: String)
signal shop_opened(shop_id: String)
signal shop_closed()
signal codex_terminal_activated(terminal_id: String)
signal quest_updated(quest_id: String, status: String)

# -- SCBE events --
signal scbe_decision(decision: String, harmonic_score: float)
signal scbe_pipeline_result(layers: Array)

# -- Tower events --
signal tower_floor_entered(floor: int)
signal tower_wave_started(wave: int)
signal tower_wave_cleared(wave: int)
signal tower_corruption_detected(tower_id: String, level: float)

# -- Egg events --
signal egg_condition_met(egg_type: String)
signal egg_hatching_started(egg_type: String)

# -- UI events --
signal dialogue_requested(speaker: String, lines: Array)
signal dialogue_choice_made(choice_index: int)
signal notification_requested(message: String, color: Color)
