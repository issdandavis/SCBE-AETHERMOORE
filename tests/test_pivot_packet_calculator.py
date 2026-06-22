from python.helm.pivot_packet_calculator import (
    MODEL_SYSTEM_PROMPT,
    build_packet_records,
    build_pivot_packet,
    calculator_packet_from_text,
    summarize_packets,
    to_dpo_record,
    to_sft_record,
    topic_row_to_packet,
)


def test_calculable_conversation_routes_to_deterministic_packet():
    packet = calculator_packet_from_text("what is the 10th prime?")

    assert packet is not None
    assert packet.answer == "29"
    assert packet.task == "agentic_calculator"
    assert packet.calculator["tool"] == "nth_prime"
    assert packet.calculator["verified"] is True
    assert packet.false_success_count == 0
    assert "hidden chain-of-thought" not in packet.render().lower()


def test_model_fumble_does_not_override_known_calculator_answer():
    packet = calculator_packet_from_text("what is the 10th prime?", model_output="31")

    assert packet is not None
    assert packet.answer == "29"
    assert packet.status == "deterministic_fallback"
    assert packet.false_success_count == 0


def test_non_calculator_pivot_uses_polite_structured_packet():
    packet = build_pivot_packet(
        user_text="please pivot from the code bug to the deployment plan",
        answer="First preserve the bug receipt, then route the next action to deployment verification.",
        pivot_from="code_bug",
        pivot_to="deployment_plan",
    )
    rendered = packet.render()

    assert packet.status == "pivot_packet"
    assert "Please be careful" in rendered
    assert "If you would kindly" in rendered
    assert "visible_reasoning_summary" in rendered
    assert "false_success_count: 0" in rendered


def test_topic_rows_become_chat_sft_records_with_packet_target():
    row = {
        "instruction": "What is the Six Tongues Protocol?",
        "response": "It is the semantic/governance substrate for SCBE and Aethermoor.",
        "topic": "Six Tongues",
        "tongue": "KO",
        "trajectory": "curve",
    }
    packet = topic_row_to_packet(row)
    sft = to_sft_record(packet)

    assert sft["messages"][0]["content"] == MODEL_SYSTEM_PROMPT
    assert sft["messages"][1]["content"] == row["instruction"]
    assert "<SCBE_PIVOT_PACKET" in sft["messages"][2]["content"]
    assert sft["meta"]["false_success_count"] == 0


def test_packet_records_and_dpo_keep_zero_false_success_contract():
    rows = [
        {"instruction": "binary of 10", "response": "1010", "topic": "math", "tongue": "CA"},
        {"instruction": "How should we pivot carefully?", "response": "Name the old context and the new one."},
    ]
    sft = build_packet_records(rows)
    packet = build_pivot_packet(user_text="How should we pivot carefully?", answer="Name the old and new context.")
    dpo = to_dpo_record(packet, rejected="Just change topics randomly.")
    summary = summarize_packets([topic_row_to_packet(r) for r in rows] + [packet])

    assert len(sft) == 2
    assert dpo["meta"]["false_success_count"] == 0
    assert summary["contract_passed"] is True
    assert summary["false_success_count"] == 0
