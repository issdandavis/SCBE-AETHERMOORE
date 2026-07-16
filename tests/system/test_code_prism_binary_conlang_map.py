from scripts.system.code_prism_binary_conlang_map import build_map


def test_code_prism_binary_conlang_map_core_receipts() -> None:
    payload = build_map(sample="compile")

    assert payload["schema"] == "scbe_code_prism_binary_conlang_orientation_map_v1"
    assert len(payload["orientation_rows"]) == 6
    assert payload["code_prism"]["parser_supported_sources"] == [
        "c",
        "go",
        "haskell",
        "julia",
        "python",
        "rust",
        "typescript",
    ]
    assert payload["code_prism"]["emitter_supported_targets"] == [
        "c",
        "go",
        "haskell",
        "julia",
        "python",
        "rust",
        "typescript",
    ]
    assert set(payload["ca_isa_stib"]["supported_targets"]) >= {
        "python",
        "typescript",
        "go",
        "rust",
        "c",
        "julia",
        "haskell",
        "zig",
    }
    assert payload["ca_isa_stib"]["supported_opcode_templates"] == 64
    assert payload["ca_isa_stib"]["stib"]["roundtrip_ok"] is True
    assert all(payload["bit_spine_hex"]["roundtrip"].values())
    assert payload["conlang_tokenizers"]["python_cube_token"]["all_faces_roundtrip"] is True


def test_code_prism_binary_conlang_map_marks_all_primary_lanes_active() -> None:
    payload = build_map(sample="compile")
    rows = {row["tongue"]: row for row in payload["orientation_rows"]}

    assert rows["KO"]["code_prism_primary"]["full_source_status"] == "active_safe_subset"
    assert rows["AV"]["code_prism_primary"]["full_source_status"] == "active_safe_subset"
    assert rows["RU"]["code_prism_primary"]["full_source_status"] == "active_safe_subset"
    assert rows["CA"]["code_prism_primary"]["full_source_status"] == "active_safe_subset"
    assert rows["UM"]["code_prism_primary"]["full_source_status"] == "active_safe_subset"
    assert rows["DR"]["code_prism_primary"]["full_source_status"] == "active_safe_subset"
    assert rows["RU"]["ca_stib_target_supported"] is True
    assert rows["CA"]["ca_stib_target_supported"] is True
    assert rows["UM"]["ca_stib_target_supported"] is True
    assert rows["DR"]["ca_stib_target_supported"] is True


def test_code_prism_binary_conlang_map_hash_ignores_generated_time() -> None:
    left = build_map(sample="compile")
    right = build_map(sample="compile")

    assert left["map_sha256"] == right["map_sha256"]
