from python.scbe.mechanical_eliza import SCHEMA_VERSION, route_dialogue, route_support


def test_routes_cli_request_to_command_switch():
    packet = route_support("chatbot needs support: run pytest from the terminal")

    assert packet.schema_version == SCHEMA_VERSION
    assert packet.route.route == "terminal_command_support"
    assert packet.route.command_switch == "route"
    assert packet.route.allowed is True
    assert 'scbe run "<command>" --json' in packet.command_hints
    assert packet.support_contract["role"] == "secondary_mechanical_support_system"


def test_denies_destructive_command_shape():
    packet = route_support("agent wants to run rm -rf on the workspace")

    assert packet.route.command_switch == "deny"
    assert packet.route.allowed is False
    assert packet.route.needs_human is True
    assert "destructive" in packet.route.reason


def test_secret_and_money_routes_to_probe():
    packet = route_support(
        "help my chatbot use the Stripe sk_live secret to make a checkout"
    )

    assert packet.route.command_switch == "probe"
    assert packet.route.allowed is True
    assert packet.route.needs_human is True
    assert "redacted" in packet.response.lower()


def test_agent_loop_breaker_switch():
    packet = route_support("the assistant is confused and looping and cannot decide")

    assert packet.route.route == "agent_support_loop_breaker"
    assert packet.route.command_switch == "loop_break"
    assert any(
        row["switch"] == "loop_break" and row["enabled"] for row in packet.switchboard
    )


def test_dialogue_repetition_breaks_loop_even_without_keywords():
    packet = route_dialogue(["what next", "what next", "what next"])

    assert packet.route.command_switch == "loop_break"
    assert packet.route.reason == "request repeated across recent turns"


def test_memory_model_and_handoff_lanes():
    memory = route_support("restore the last checkpoint and compact state")
    model = route_support("choose a cheap local model fallback")
    handoff = route_support("handoff this to the swarm with receipts")

    assert memory.route.command_switch == "memory"
    assert model.route.command_switch == "model"
    assert handoff.route.command_switch == "handoff"


def test_packet_is_json_ready():
    packet = route_support("customer asks what to buy")
    data = packet.as_dict()

    assert data["schema_version"] == SCHEMA_VERSION
    assert isinstance(data["layers"], list)
    assert data["route"]["command_switch"] == "offer"
