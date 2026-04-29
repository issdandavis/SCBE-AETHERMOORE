from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _run_cli_with_input(payload: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", *args],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_encode_decode_cmd_roundtrip() -> None:
    encoded = _run_cli("encode-cmd", "--tongue", "KO", "hello")
    assert encoded.returncode == 0, encoded.stderr
    decoded = _run_cli("decode-cmd", "--tongue", "KO", encoded.stdout.strip())
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == "hello"


def test_xlate_cmd_preserves_payload() -> None:
    encoded = _run_cli("encode-cmd", "--tongue", "KO", "abc")
    assert encoded.returncode == 0, encoded.stderr
    translated = _run_cli(
        "xlate-cmd", "--src", "KO", "--dst", "AV", encoded.stdout.strip()
    )
    assert translated.returncode == 0, translated.stderr
    decoded = _run_cli("decode-cmd", "--tongue", "AV", translated.stdout.strip())
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == "abc"


def test_encode_decode_cmd_roundtrip_unicode() -> None:
    payload = "Unicode: café 漢字 😀\nline2\tindent"
    encoded = _run_cli("encode-cmd", "--tongue", "KO", payload)
    assert encoded.returncode == 0, encoded.stderr
    decoded = _run_cli("decode-cmd", "--tongue", "KO", encoded.stdout.strip())
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == payload


def test_encode_decode_cmd_roundtrip_via_stdin() -> None:
    payload = "stdin payload\nwith multiple lines\nand symbols :: =>"
    encoded = _run_cli_with_input(payload, "encode-cmd", "--tongue", "AV")
    assert encoded.returncode == 0, encoded.stderr
    decoded = _run_cli_with_input(encoded.stdout, "decode-cmd", "--tongue", "AV")
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == payload


def test_xlate_cmd_pairwise_lattice_preserves_payload() -> None:
    payload = "pairwise lattice payload: café 漢字 -> map/filter/reduce"
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
    for src in tongues:
        encoded = _run_cli("encode-cmd", "--tongue", src, payload)
        assert encoded.returncode == 0, f"{src}: {encoded.stderr}"
        for dst in tongues:
            translated = _run_cli(
                "xlate-cmd", "--src", src, "--dst", dst, encoded.stdout.strip()
            )
            assert translated.returncode == 0, f"{src}->{dst}: {translated.stderr}"
            decoded = _run_cli("decode-cmd", "--tongue", dst, translated.stdout.strip())
            assert decoded.returncode == 0, f"{src}->{dst}: {decoded.stderr}"
            assert decoded.stdout == payload


def test_xlate_cmd_multihop_chain_preserves_payload() -> None:
    payload = "multihop payload with unicode 😀 and symbols {}[]"
    encoded = _run_cli("encode-cmd", "--tongue", "KO", payload)
    assert encoded.returncode == 0, encoded.stderr
    current = encoded.stdout.strip()
    chain = [("KO", "AV"), ("AV", "RU"), ("RU", "KO")]
    for src, dst in chain:
        translated = _run_cli("xlate-cmd", "--src", src, "--dst", dst, current)
        assert translated.returncode == 0, f"{src}->{dst}: {translated.stderr}"
        current = translated.stdout.strip()
    decoded = _run_cli("decode-cmd", "--tongue", "KO", current)
    assert decoded.returncode == 0, decoded.stderr
    assert decoded.stdout == payload


def test_binary_to_tokenizer_maps_bits_to_tokens_and_prime_language() -> None:
    result = _run_cli(
        "binary-to-tokenizer", "--tongue", "KO", "--json", "01101000 01101001"
    )
    assert result.returncode == 0, result.stderr
    mapping = json.loads(result.stdout)
    assert mapping["version"] == "geoseal-binary-tokenizer-map-v1"
    assert mapping["tongue"] == "KO"
    assert mapping["conlang"] == "Kor'aelin"
    assert mapping["prime_language"] == "python"
    assert mapping["language_matches_prime"] is True
    assert mapping["byte_count"] == 2
    assert len(mapping["rows"]) == 2
    assert mapping["rows"][0]["bits"] == "01101000"
    assert mapping["harmonic_spiral"]["ball_model"] == "harmonic_poincare_like_ball"
    assert mapping["harmonic_spiral"]["state_count"] == 2
    assert mapping["harmonic_spiral"]["valid_count"] == 2
    assert set(mapping["harmonic_spiral"]["states"][0]["position"]) == {"x", "y", "z"}
    assert mapping["roundtrip"]["bytes_ok"] is True
    assert mapping["roundtrip"]["decoded_utf8"] == "hi"


def test_binary_to_tokenizer_flags_language_mismatch() -> None:
    result = _run_cli(
        "binary-to-tokenizer",
        "--tongue",
        "CA",
        "--language",
        "python",
        "--json",
        "01100001",
    )
    assert result.returncode == 0, result.stderr
    mapping = json.loads(result.stdout)
    assert mapping["tongue"] == "CA"
    assert mapping["prime_language"] == "c"
    assert mapping["requested_language"] == "python"
    assert mapping["language_matches_prime"] is False


def test_atomic_shows_row_metadata() -> None:
    result = _run_cli("atomic", "add")
    assert result.returncode == 0, result.stderr
    assert '"name": "add"' in result.stdout
    assert '"trit":' in result.stdout
    assert '"feat":' in result.stdout


def test_code_packet_emits_source_packet(tmp_path: Path) -> None:
    source_file = tmp_path / "sample.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["version"] == "scbe-code-weight-packet-v1"
    assert packet["source_name"] == "sample.py"
    assert packet["language"] == "python"
    assert packet["transport"]["tongue"] == "KO"
    assert packet["labels"]["conlang"] == "Kor'aelin"
    assert packet["binary"]["byte_count"] > 0
    assert packet["tokenizer"]["conlang"] == "Kor'aelin"
    assert len(packet["language_views"]) == 6
    assert packet["braille_lane"]["version"] == "scbe-braille-cell-lane-v1"
    assert packet["braille_lane"]["binary_surface"]["cell_count"] > 0
    assert packet["braille_lane"]["token_surface"]["token_count"] == len(
        packet["lexical_tokens"]
    )
    assert packet["stisa"]["version"] == "scbe-stisa-surface-v1"
    assert len(packet["stisa"]["field_definitions"]) == 8
    assert len(packet["stisa"]["token_rows"]) == len(packet["lexical_tokens"])
    assert len(packet["stisa"]["token_rows"][0]["feature_vector"]) == 8
    assert packet["stisa"]["binary_groups"]
    assert packet["structural_parse"]["provider"] == "tree_sitter"
    assert packet["structural_parse"]["planned_provider"] == "tree_sitter"
    assert packet["scip_symbol_index"]["provider"] == "tree_sitter_symbol_graph"
    assert packet["scip_symbol_index"]["planned_provider"] == "scip"
    assert packet["semantic_token_bridge"]["provider"] == "tree_sitter_semantic_tokens"
    assert packet["semantic_token_bridge"]["planned_provider"] == "lsp_semantic_tokens"
    assert "def" in packet["lexical_tokens"]
    assert packet["route_ir"]["schema_version"] == "scbe_route_ir_v1"
    assert packet["route_ir"]["route"]["tongue"] == "KO"
    assert packet["route_ir"]["source"]["language"] == "python"
    assert packet["route_ir"]["hashes"]["plan_sha256"]
    assert packet["execution_lane"]["schema_version"] == "scbe_execution_lane_v1"
    assert "binary" in packet["execution_lane"]["core_lanes"]
    assert packet["atomic_states"]
    assert packet["ternary_semantics"]["version"] == "scbe-ternary-semantics-v1"
    assert packet["ternary_semantics"]["checksum"]
    assert packet["ternary_semantics"]["atomic_tau_projection"]["KO"] in (-1, 0, 1)
    assert packet["ternary_semantics"]["route_projection"]["KO"] in (-1, 0, 1)


def test_explain_route_surfaces_ir_and_backend_chain(tmp_path: Path) -> None:
    source_file = tmp_path / "explain_sample.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    result = _run_cli(
        "explain-route",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"] == "geoseal-route-explain-v1"
    assert payload["route_ir"]["schema_version"] == "scbe_route_ir_v1"
    assert payload["provider_chain"]["resolved_chain"]


def test_backend_registry_lists_core_lanes() -> None:
    result = _run_cli("backend-registry", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"] == "geoseal-backend-registry-v1"
    assert payload["backends"]
    for row in payload["backends"]:
        assert "python" in row["supports_lanes"]
        assert "binary" in row["supports_lanes"]


def test_history_and_replay_from_swarm_record(tmp_path: Path) -> None:
    ledger = tmp_path / "history.jsonl"
    swarm = _run_cli(
        "swarm",
        "add",
        "--tongues",
        "KO",
        "--ledger",
        str(ledger),
        "--json",
        "a=2",
        "b=3",
    )
    assert swarm.returncode == 0, swarm.stderr
    history = _run_cli("history", "--ledger", str(ledger), "--json")
    assert history.returncode == 0, history.stderr
    hist_payload = json.loads(history.stdout)
    assert hist_payload["version"] == "geoseal-history-v1"
    assert hist_payload["count"] >= 1
    replay = _run_cli("replay", "--ledger", str(ledger), "--json")
    assert replay.returncode == 0, replay.stderr
    replay_payload = json.loads(replay.stdout)
    assert replay_payload["version"] == "geoseal-replay-v1"


def test_code_packet_captures_semantic_gloss_for_hello_world(tmp_path: Path) -> None:
    source_file = tmp_path / "hello.py"
    source_file.write_text('print("Hello, world!")\n', encoding="utf-8")

    result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["semantic_expression"]["label"] == "hello_world"
    assert packet["semantic_expression"]["gloss"] == "hello world"
    assert packet["semantic_token_bridge"]["tokens"]
    assert packet["semantic_expression"]["quarks"] == ["output_emit", "string_literal"]


def test_code_packet_generic_bin_collects_quarks_for_nonlexicon_code(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "generic_shape.py"
    source_file.write_text(
        "import math\n\nclass Greeter:\n    pass\n\ndef area(r):\n    value = math.pi * r * r\n    return value\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["semantic_expression"]["label"] == "generic_program_bin"
    quarks = set(packet["semantic_expression"]["quarks"])
    assert {
        "import_binding",
        "class_shape",
        "function_shape",
        "assignment_flow",
        "return_flow",
        "arithmetic_transform",
    } <= quarks


def test_code_packet_generic_bin_collects_domain_well_quarks(tmp_path: Path) -> None:
    source_file = tmp_path / "domain_wells.py"
    source_file.write_text(
        """def monitor(patient, voltage, current, risk_score, window_minutes):
    summary = {"status": "allow"}
    if voltage > 4.2 or current > 3.0 or risk_score > 0.8:
        summary["status"] = "hold"
    return summary
""",
        encoding="utf-8",
    )

    result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    quarks = set(packet["semantic_expression"]["quarks"])
    assert {
        "comparison_gate",
        "timing_window",
        "measurement_signal",
        "risk_gate",
        "care_state",
        "summary_emit",
    } <= quarks


def test_code_packet_scaffolds_structure_symbol_and_semantic_layers(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "shape.py"
    source_file.write_text(
        "import math\n\nclass Greeter:\n    pass\n\ndef area(r):\n    return math.pi * r * r\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert "math" in packet["structural_parse"]["captures"]["imports"]
    assert "Greeter" in packet["structural_parse"]["captures"]["classes"]
    assert "area" in packet["structural_parse"]["captures"]["functions"]
    definition_symbols = {
        item["symbol"] for item in packet["scip_symbol_index"]["symbols"]["definitions"]
    }
    assert {"math", "Greeter", "area"} <= definition_symbols
    token_types = {
        item["token_type"] for item in packet["semantic_token_bridge"]["tokens"]
    }
    assert "keyword" in token_types
    assert "function" in token_types or "class" in token_types
    assert packet["scip_symbol_index"]["symbols"]["references"] == []


def test_code_packet_respects_explicit_c_language_lane(tmp_path: Path) -> None:
    source_file = tmp_path / "battery_guard.c"
    source_file.write_text(
        "int battery_guard(double temp_c, double soc) {\n"
        "  if (temp_c > 45.0) return 0;\n"
        "  if (soc < 0.15) return 1;\n"
        "  return 2;\n"
        "}\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "c",
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["route"]["tongue"] == "CA"
    assert packet["labels"]["conlang"] == "Cassisivadan"
    assert packet["transport"]["tongue"] == "CA"


def test_braille_lane_cli_emits_polyhedral_rhombic_cells(tmp_path: Path) -> None:
    source_file = tmp_path / "braille_sample.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "braille-lane",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    lane = json.loads(result.stdout)
    assert lane["version"] == "scbe-braille-cell-lane-v1"
    assert lane["cell_schema"]["bits_per_cell"] == 6
    assert lane["binary_surface"]["cell_count"] > 0
    first_cell = lane["binary_surface"]["cells"][0]
    assert first_cell["polyhedral_face"] in {
        "north",
        "east",
        "south",
        "west",
        "zenith",
        "nadir",
    }
    assert first_cell["rhombic_block"] in {"alpha", "beta", "gamma", "delta"}
    assert set(first_cell["position"]) == {"x", "y", "z"}


def test_braille_lane_cli_reads_packet_artifact(tmp_path: Path) -> None:
    source_file = tmp_path / "packet_sample.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    packet_file = tmp_path / "packet.json"

    packet_result = _run_cli(
        "code-packet",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert packet_result.returncode == 0, packet_result.stderr
    packet_file.write_text(packet_result.stdout, encoding="utf-8")

    lane_result = _run_cli(
        "braille-lane",
        "--packet-file",
        str(packet_file),
        "--json",
    )
    assert lane_result.returncode == 0, lane_result.stderr
    lane = json.loads(lane_result.stdout)
    assert lane["version"] == "scbe-braille-cell-lane-v1"
    assert lane["token_surface"]["token_count"] >= 1


def test_interaction_graph_connects_source_tokens_atoms_and_views(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "graph_sample.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "interaction-graph",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--max-binary-nodes",
        "8",
    )
    assert result.returncode == 0, result.stderr
    graph = json.loads(result.stdout)
    assert graph["version"] == "scbe-interaction-graph-v1"
    assert graph["route_tongue"] == "KO"
    assert graph["summary"]["lexical_token_count"] > 0
    assert graph["summary"]["atomic_state_count"] > 0
    assert graph["summary"]["stisa_row_count"] > 0
    assert graph["summary"]["language_view_count"] == 6
    assert graph["summary"]["binary_group_count"] > 0
    assert graph["summary"]["harmonic_spiral_state_count"] > 0

    node_ids = {node["id"] for node in graph["nodes"]}
    assert "source:program" in node_ids
    assert any(node_id.startswith("semantic:") for node_id in node_ids)
    assert any(node_id.startswith("quark:") for node_id in node_ids)
    assert "route:tongue:KO" in node_ids
    assert any(node_id.startswith("token:") for node_id in node_ids)
    assert any(node_id.startswith("stisa:") for node_id in node_ids)
    assert any(node_id.startswith("atom:") for node_id in node_ids)
    assert any(node_id.startswith("transport_token:") for node_id in node_ids)
    assert any(node_id.startswith("binary_group:") for node_id in node_ids)
    assert any(node_id.startswith("braille:") for node_id in node_ids)
    assert any(node_id.startswith("spiral:") for node_id in node_ids)
    assert "view:KO:python" in node_ids

    edge_triplets = {
        (edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]
    }
    assert ("source:program", "route:tongue:KO", "routes_to") in edge_triplets
    assert any(relation == "maps_to_stisa_row" for _, _, relation in edge_triplets)
    assert any(relation == "maps_to_atomic_state" for _, _, relation in edge_triplets)
    assert any(
        relation == "projects_to_braille_cell" for _, _, relation in edge_triplets
    )
    assert any(
        relation == "evolves_to_harmonic_state" for _, _, relation in edge_triplets
    )
    assert any(
        relation == "projects_to_language_view" for _, _, relation in edge_triplets
    )
    assert any(relation == "decomposes_to_quark" for _, _, relation in edge_triplets)


def test_interaction_graph_mermaid_and_dot_formats(tmp_path: Path) -> None:
    source_file = tmp_path / "graph_formats.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    mermaid = _run_cli(
        "interaction-graph",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--format",
        "mermaid",
        "--max-binary-nodes",
        "2",
    )
    assert mermaid.returncode == 0, mermaid.stderr
    assert "flowchart TD" in mermaid.stdout
    assert "source_program: graph_formats.py" in mermaid.stdout
    assert "generic_program_bin" in mermaid.stdout
    assert "routes_to" in mermaid.stdout

    dot = _run_cli(
        "interaction-graph",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--format",
        "dot",
        "--max-binary-nodes",
        "2",
    )
    assert dot.returncode == 0, dot.stderr
    assert "digraph SCBEInteractionGraph" in dot.stdout
    assert 'label="source_program: graph_formats.py"' in dot.stdout
    assert 'label="semantic_expression: generic program bin:' in dot.stdout
    assert 'label="routes_to"' in dot.stdout


def test_topology_view_emits_polygons_chains_and_compass(tmp_path: Path) -> None:
    source_file = tmp_path / "topology_case.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "topology-view",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--max-binary-nodes",
        "8",
    )
    assert result.returncode == 0, result.stderr
    topology = json.loads(result.stdout)
    assert topology["version"] == "scbe-topology-view-v1"
    assert topology["route_tongue"] == "KO"
    assert len(topology["axes"]) == 8
    assert topology["summary"]["node_count"] > 0
    assert topology["summary"]["edge_count"] > 0
    assert topology["summary"]["polygon_count"] > 0
    assert topology["summary"]["leyline_count"] >= 3
    assert topology["surfaces"]["stisa_row_count"] > 0
    assert topology["surfaces"]["harmonic_spiral_state_count"] > 0
    assert topology["dictionaries"]["coding_languages"]["primary"]["KO"] == "python"
    assert topology["dictionaries"]["coding_languages"]["all"]["GO"] == "go"
    assert topology["dictionaries"]["tokenizer_tongues"]["primary"] == [
        "KO",
        "AV",
        "RU",
        "CA",
        "UM",
        "DR",
    ]
    add_binding = next(
        entry
        for entry in topology["dictionaries"]["keyboard_command_map"]
        if entry["command_key"] == "add"
    )
    assert add_binding["key_slot"] == "A1"
    assert add_binding["phase_operation"] == "arithmetic:add"
    assert add_binding["languages"]["RU"]["language"] == "rust"
    assert isinstance(add_binding["primary_transport_tokens"]["KO"], str)
    active_bindings = topology["dictionaries"]["active_command_bindings"]
    assert "arithmetic:add" in active_bindings["phase_candidates"]
    assert "ARITHMETIC" in active_bindings["band_hints"]
    assert active_bindings["anchor_command"]["command_key"] == "add"
    assert active_bindings["anchor_command"]["key_slot"] == "A1"
    assert active_bindings["anchor_command"]["topology_local_relevance_score"] > 0
    assert any(
        entry["command_key"] == "sub" for entry in active_bindings["nearby_commands"]
    )
    assert topology["operative_command"]["command_key"] == "add"
    assert topology["operative_command"]["phase_operation"] == "arithmetic:add"
    assert topology["operative_command"]["key_slot"] == "A1"
    assert topology["route_packet"]["operative_command"] == "arithmetic:add"
    assert topology["route_packet"]["command_key"] == "add"
    assert topology["route_packet"]["key_slot"] == "A1"
    assert topology["route_packet"]["binary_input"] == "000000"
    assert topology["route_packet"]["route_tongue"] == "KO"
    assert topology["route_packet"]["route_language"] == "Python"
    assert isinstance(topology["route_packet"]["transport_tokens"]["KO"], str)
    assert "sub" in topology["route_packet"]["support_commands"]
    assert topology["route_packet"]["cost_retro_summary"]["route_total_cost"] > 0
    assert topology["route_packet"]["cost_retro_summary"]["preferred_leyline"] in {
        "semantic_backbone",
        "binary_spine",
        "harmonic_spine",
    }
    assert (
        topology["summary"]["operative_command"]["phase_operation"] == "arithmetic:add"
    )
    assert topology["summary"]["route_packet"]["operative_command"] == "arithmetic:add"
    assert topology["cost_retro"]["objective"]["operative_command"] == "arithmetic:add"
    assert topology["cost_retro"]["totals"]["route_total_cost"] > 0
    assert topology["cost_retro"]["route_memory"]["preferred_leyline"] in {
        "semantic_backbone",
        "binary_spine",
        "harmonic_spine",
    }
    assert (
        topology["summary"]["cost_retro"]["route_total_cost"]
        == topology["cost_retro"]["totals"]["route_total_cost"]
    )
    assert any(node["kind"] == "data_polygon" for node in topology["nodes"])
    assert any(
        edge["relation"] == "amino_backbone_traverse" for edge in topology["edges"]
    )

    polygon = topology["polygons"][0]
    assert polygon["token"]
    assert len(polygon["normalized_vector"]) == 8
    assert len(polygon["vertices"]) == 8
    assert set(polygon["centroid"]) == {"x", "y", "z"}
    assert polygon["compass_sector"]

    if topology["summary"]["chain_count"] > 0:
        chain = topology["chains"][0]
        assert chain["relation"] == "amino_backbone_traverse"
        assert chain["heading_label"]
        assert set(chain["delta"]) == {"x", "y", "z"}

    leyline_kinds = {entry["kind"] for entry in topology["leylines"]}
    assert {"semantic_backbone", "binary_spine", "harmonic_spine"} <= leyline_kinds
    assert topology["compass"]["heading_label"]
    assert len(topology["compass"]["trend_axes"]) == 3


def test_testing_cli_surfaces_route_packet_and_execution(tmp_path: Path) -> None:
    source_file = tmp_path / "testing_shell.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "testing-cli",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--execute",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["route_packet"]["operative_command"] == "arithmetic:add"
    assert payload["playback"]["route_packet"]["command_key"] == "add"
    assert payload["playback"]["execution"]["op"] == "add"
    assert payload["playback"]["execution"]["tongue"] == "KO"
    assert payload["playback"]["execution"]["ran"] is True
    assert payload["playback"]["execution"]["returncode"] == 0
    assert payload["playback"]["execution"]["stdout"] == "10"
    assert payload["honeycomb_analysis"]["matched_output"] == "10"
    assert payload["route_packet"]["stability_adjusted_route_score"] > 0
    assert payload["route_packet"]["route_confidence"] > 0
    assert payload["topology"]["route_packet"]["stability_adjusted_route_score"] > 0
    assert (
        payload["topology"]["operative_command"]["stability_adjusted_route_score"] > 0
    )


def test_cross_domain_sequence_builds_near_related_field_steps(tmp_path: Path) -> None:
    source_file = tmp_path / "cross_domain_add.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "cross-domain-sequence",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    sequence = payload["sequence"]
    assert sequence["version"] == "geoseal-cross-domain-sequence-v1"
    assert "coding" in sequence["inferred_domains"]
    assert "mathematics" in sequence["inferred_domains"]
    assert sequence["route_packet"]["command_key"] == "add"
    assert sequence["steps"][0]["step_kind"] == "anchor"
    assert sequence["steps"][0]["tongue"] == "KO"
    assert sequence["steps"][0]["phase_operation"] == "arithmetic:add"
    assert any(step["step_kind"] == "domain_projection" for step in sequence["steps"])
    assert any(step["domain"] == "mathematics" for step in sequence["steps"])
    assert any(
        step["step_kind"] == "support_projection" and step["command_key"] == "sub"
        for step in sequence["steps"]
    )


def test_cross_domain_sequence_accepts_topology_view_artifact(tmp_path: Path) -> None:
    source_file = tmp_path / "cross_domain_topology.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    topology_result = _run_cli(
        "topology-view",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert topology_result.returncode == 0, topology_result.stderr
    topology_path = tmp_path / "cross_domain.topology.json"
    topology_path.write_text(topology_result.stdout, encoding="utf-8")

    result = _run_cli(
        "cross-domain-sequence",
        "--topology-file",
        str(topology_path),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    sequence = payload["sequence"]
    assert sequence["route_packet"]["operative_command"] == "arithmetic:add"
    assert sequence["steps"][0]["key_slot"] == "A1"
    assert sequence["steps"][0]["command_key"] == "add"


def test_honeycomb_analysis_matches_outputs_and_tracks_remainders(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "honeycomb_add.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = _run_cli(
        "honeycomb-analysis",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--branch-width",
        "1",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    analysis = payload["analysis"]
    assert analysis["version"] == "geoseal-honeycomb-analysis-v1"
    assert analysis["center_cell"]["command_key"] == "add"
    assert analysis["matched_output"] == "10"
    assert analysis["post_decimal_depth"]["runnable_cell_count"] >= 2
    assert analysis["post_decimal_depth"]["max_abs_remainder"] == "0"
    assert analysis["post_decimal_depth"]["stability_ratio"] == 1.0
    assert analysis["feedback"]["stability_adjusted_route_score"] > 0
    assert analysis["feedback"]["route_confidence"] > 0
    assert set(analysis["feedback"]["stable_tongues"]) >= {"KO", "AV"}
    assert any(
        cell["tongue"] == "KO" and cell["value"] == "10"
        for cell in analysis["numeric_cells"]
    )
    assert any(
        cell["tongue"] == "AV" and cell["value"] == "10"
        for cell in analysis["numeric_cells"]
    )


def test_project_scaffold_builds_pacman_style_web_project(tmp_path: Path) -> None:
    output_dir = tmp_path / "pacman_scaffold"
    result = _run_cli(
        "project-scaffold",
        "--content",
        "build a pacman style web game with pellets, a maze, and arrow key movement",
        "--language",
        "python",
        "--output-dir",
        str(output_dir),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"] == "geoseal-project-scaffold-v1"
    assert payload["project_kind"] == "pacman_web"
    assert (output_dir / "index.html").exists()
    assert (output_dir / "style.css").exists()
    assert (output_dir / "game.js").exists()
    assert (output_dir / "project_manifest.json").exists()
    manifest = json.loads(
        (output_dir / "project_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["route_packet"]["command_key"] == "add"
    assert manifest["honeycomb_feedback"]["route_confidence"] > 0
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Pacman Scaffold" in index_html
    game_js = (output_dir / "game.js").read_text(encoding="utf-8")
    assert "pellets" in game_js
    assert "ArrowUp" in game_js


def test_topology_view_mermaid_and_dot_formats(tmp_path: Path) -> None:
    source_file = tmp_path / "topology_formats.py"
    source_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    mermaid = _run_cli(
        "topology-view",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--format",
        "mermaid",
        "--max-binary-nodes",
        "4",
    )
    assert mermaid.returncode == 0, mermaid.stderr
    assert "flowchart LR" in mermaid.stdout
    assert "polygon:" in mermaid.stdout

    dot = _run_cli(
        "topology-view",
        "--source-file",
        str(source_file),
        "--language",
        "python",
        "--format",
        "dot",
        "--max-binary-nodes",
        "4",
    )
    assert dot.returncode == 0, dot.stderr
    assert "digraph SCBETopologyView" in dot.stdout
    assert 'label="polygon:' in dot.stdout


def test_cognition_map_emits_multiwell_metrics(tmp_path: Path) -> None:
    source_file = tmp_path / "cognition_case.py"
    source_file.write_text(
        """def route_case(sensor, patient, risk_score, tick_window):
    route = {"status": "allow"}
    if sensor["wind"] > 20 or patient["pressure"] > 150 or risk_score > 0.8:
        route["status"] = "hold"
    return route
""",
        encoding="utf-8",
    )

    result = _run_cli(
        "cognition-map",
        "--source-file",
        str(source_file),
        "--language",
        "python",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"] == "scbe-cognition-map-v1"
    assert payload["semantic_label"] == "generic_program_bin"
    assert "measurement" in payload["well_scores"]
    assert "governance" in payload["well_scores"]
    assert payload["overlay_planes"]
    assert payload["ternary"]["counts"]["positive"] >= 1
    assert "tongue_projection" in payload["ternary"]
    assert payload["dual_ternary"]["history_length"] > 0
    assert payload["tri_manifold"]["tick"] > 0


def test_cluster_and_formation_graphs_emit_cross_lattice_layers(tmp_path: Path) -> None:
    source_file = tmp_path / "graph_layers.rs"
    source_file.write_text(
        "fn relay_window(latency_ms: u64, thermal_ok: bool) -> &'static str {\n"
        '    if !thermal_ok { return "hold"; }\n'
        '    if latency_ms > 1200 { return "store_and_forward"; }\n'
        '    "direct_relay"\n'
        "}\n",
        encoding="utf-8",
    )

    cluster = _run_cli(
        "cluster-graph",
        "--source-file",
        str(source_file),
        "--language",
        "rust",
        "--max-binary-nodes",
        "8",
    )
    assert cluster.returncode == 0, cluster.stderr
    cluster_graph = json.loads(cluster.stdout)
    assert cluster_graph["version"] == "scbe-cluster-graph-v1"
    assert {
        "source_field",
        "semantic_field",
        "atomic_mesh",
        "language_projection",
    } <= set(cluster_graph["summary"]["cluster_kinds"])
    assert any(node["metadata"]["mesh_block"] for node in cluster_graph["nodes"])

    formation = _run_cli(
        "formation-graph",
        "--source-file",
        str(source_file),
        "--language",
        "rust",
        "--max-binary-nodes",
        "8",
    )
    assert formation.returncode == 0, formation.stderr
    formation_graph = json.loads(formation.stdout)
    assert formation_graph["version"] == "scbe-formation-graph-v1"
    assert (
        formation_graph["summary"]["formation_count"]
        == cluster_graph["summary"]["cluster_count"]
    )
    assert all(node["metadata"]["anchor_mode"] for node in formation_graph["nodes"])
    assert all(edge["metadata"]["cross_lattice"] for edge in formation_graph["edges"])
    assert all(edge["metadata"]["non_linear_grid"] for edge in formation_graph["edges"])


def test_emit_json_bundle_shows_language_conlang_binary_and_tokenizer() -> None:
    result = _run_cli("emit", "add", "--json", "a=2", "b=3")
    assert result.returncode == 0, result.stderr
    bundle = json.loads(result.stdout)
    assert bundle["op"] == "add"
    assert bundle["semantic_expression"]["gloss"] == "add x and y"
    assert len(bundle["variants"]) == 6
    languages = {variant["language"] for variant in bundle["variants"]}
    conlangs = {variant["conlang"] for variant in bundle["variants"]}
    assert {"python", "typescript", "rust", "c", "julia", "haskell"} <= languages
    assert {
        "Kor'aelin",
        "Avali",
        "Runethic",
        "Cassisivadan",
        "Umbroth",
        "Draumric",
    } <= conlangs
    assert all(variant["binary"]["byte_count"] > 0 for variant in bundle["variants"])
    assert all(
        variant["tokenizer"]["token_count"] > 0 for variant in bundle["variants"]
    )


def test_code_roundtrip_executes_rust_prime_lane(tmp_path: Path) -> None:
    source_file = tmp_path / "hello.rs"
    source_file.write_text(
        'fn main() {\n    println!("Runethic Rust prime lane");\n}\n',
        encoding="utf-8",
    )

    result = _run_cli(
        "code-roundtrip",
        "--source",
        str(source_file),
        "--lang",
        "rust",
        "--tongue",
        "RU",
        "--execute",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["language"] == "rust"
    assert payload["tongue"] == "RU"
    assert payload["language_matches_prime"] is True
    assert payload["byte_identical"] is True
    assert payload["execution"]["original"]["ran"] is True
    assert payload["execution"]["decoded"]["ran"] is True
    assert payload["execution"]["stdout_identical"] is True
    assert payload["execution"]["returncode_identical"] is True
    assert payload["execution"]["original"]["stdout"] == "Runethic Rust prime lane\n"
