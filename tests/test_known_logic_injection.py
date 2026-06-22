from python.helm.known_logic_injection import (
    DETERMINISTIC_FALLBACK,
    MODEL_ECHO_VERIFIED,
    KnownLogicPacket,
    chart_lookup_packet,
    if_then_packet,
    inject_or_fallback,
    prime_membership_packet,
    render_injection_prompt,
    run_known_tool,
    sieve_primes,
)


def test_sieve_is_deterministic_tool_source():
    assert sieve_primes(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    assert prime_membership_packet(97).answer == "prime"
    assert prime_membership_packet(100).answer == "composite"


def test_prompt_injects_process_and_answer_not_instructional_wishing():
    packet = prime_membership_packet(97)
    prompt = render_injection_prompt(packet)

    assert "KNOWN PROCESS" in prompt
    assert "KNOWN ANSWER" in prompt
    assert "sieve_primes(97)" in prompt
    assert prompt.rstrip().endswith("Do not re-derive it.")


def test_model_echo_is_accepted_only_when_verified():
    packet = prime_membership_packet(97)
    decision = inject_or_fallback(packet, "prime")

    assert decision["status"] == MODEL_ECHO_VERIFIED
    assert decision["model_output_accepted"] is True
    assert decision["answer"] == "prime"
    assert decision["false_success_count"] == 0


def test_model_fumble_uses_deterministic_fallback_without_false_success():
    packet = prime_membership_packet(97)
    decision = inject_or_fallback(packet, "composite")

    assert decision["status"] == DETERMINISTIC_FALLBACK
    assert decision["model_output_accepted"] is False
    assert decision["answer"] == "prime"
    assert decision["deterministic_answer"] == "prime"
    assert decision["closed"] is True
    assert decision["false_success_count"] == 0


def test_known_tool_registry_supports_nested_command_style_packets():
    packet = run_known_tool("if_then", {"condition": False, "when_true": "ship", "when_false": "repair"})
    decision = inject_or_fallback(packet, "ship")

    assert packet.answer == "repair"
    assert decision["status"] == DETERMINISTIC_FALLBACK
    assert decision["answer"] == "repair"


def test_chart_lookup_and_custom_verifier_for_structured_echo():
    packet = chart_lookup_packet({"alpha": {"route": "A", "risk": 2}}, "alpha")

    def same_json(candidate: str, pkt: KnownLogicPacket) -> bool:
        return candidate == pkt.answer

    assert packet.answer == '{"risk": 2, "route": "A"}'
    assert inject_or_fallback(packet, '{"risk": 2, "route": "A"}', verifier=same_json)["status"] == MODEL_ECHO_VERIFIED


def test_if_then_packet_is_exact_process_injection():
    packet = if_then_packet(True, "ALLOW", "DENY", label="tests_pass")

    assert packet.answer == "ALLOW"
    assert "If tests_pass is true" in packet.process
