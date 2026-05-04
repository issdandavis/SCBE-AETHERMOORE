from pathlib import Path


def test_agentic_coding_workbench_entrypoint_exists():
    script = Path("scripts/training/build_agentic_coding_workbench.py")

    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "scbe_agentic_coding_workbench_manifest_v1" in text
    assert "generate_packet_traces_sft.py" in text
    assert "build_jupiter_ring_feedback.py" in text
