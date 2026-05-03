import json
import subprocess
import sys

from scripts.system.build_coding_decks import build_manifest


def test_manifest_counts_match_grounded_surfaces():
    manifest = build_manifest()
    counts = manifest["counts"]

    assert counts["operation_cards"] == 64
    assert counts["primary_language_view_cards"] == 64 * 6
    assert counts["extended_language_view_cards"] == 64 * 2
    assert counts["all_language_view_cards"] == 64 * 8
    assert counts["binary_byte_cards"] == 256
    assert counts["stib_structure_cards"] == 13
    assert counts["pairing_cards"] == 54
    assert counts["current_grounded_minimum_cards"] == 899


def test_manifest_uses_stable_timestamp_by_default():
    assert build_manifest()["generated_at_utc"] == "stable"


def test_every_card_id_is_unique():
    manifest = build_manifest()
    cards = []
    for group in manifest["cards"].values():
        cards.extend(group)
    ids = [card["card_id"] for card in cards]
    assert len(ids) == len(set(ids))


def test_all_language_views_are_available_directly_or_by_inheritance():
    manifest = build_manifest()
    views = manifest["cards"]["language_views"]
    assert all(view["payload"]["template_available"] for view in views)

    go_views = [view for view in views if view["payload"]["tongue"] == "GO"]
    zig_views = [view for view in views if view["payload"]["tongue"] == "ZI"]
    assert all(view["payload"]["inherits_from"] == "CA" for view in go_views)
    assert all(view["payload"]["inherits_from"] == "RU" for view in zig_views)


def test_binary_deck_covers_full_byte_space():
    manifest = build_manifest()
    binary = manifest["cards"]["binary"]
    values = [card["payload"]["byte"] for card in binary]
    assert values == list(range(256))
    assert binary[0]["payload"]["binary"] == "00000000"
    assert binary[-1]["payload"]["binary"] == "11111111"


def test_pairing_deck_includes_witness_and_pairwise_routes():
    manifest = build_manifest()
    pairings = manifest["cards"]["pairings"]
    types = {card["card_type"] for card in pairings}
    assert {
        "witness_triangle",
        "complement_pair",
        "inheritance_pair",
        "primary_pair",
        "all_language_pair",
    }.issubset(types)


def test_cli_writes_manifest(tmp_path):
    out_path = tmp_path / "deck.json"
    proc = subprocess.run(
        [sys.executable, "scripts/system/build_coding_decks.py", "--out", str(out_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scbe_coding_deck_manifest_v1"
    assert payload["counts"]["current_grounded_minimum_cards"] == 899
