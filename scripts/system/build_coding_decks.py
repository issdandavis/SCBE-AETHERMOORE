#!/usr/bin/env python3
"""Build SCBE coding-language decks from the grounded opcode substrate.

The deck is intentionally substrate-first:

* one canonical operation card per CA opcode,
* one language-view card for every operation/language projection,
* one binary card for every byte value,
* a small STIB structure deck for the canonical binary envelope,
* pairing cards for witness, complement, parent, and pairwise routes.

This does not claim to cover every programming language in the world yet. It
deduces the current grounded deck size from the language lanes and binary
surfaces already implemented in this repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "config" / "coding_decks" / "coding_deck_manifest.v1.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


STIB_STRUCTURE_FIELDS = [
    "magic",
    "version_major",
    "version_minor",
    "tongue_id",
    "flags",
    "fn_name_length",
    "fn_name_utf8",
    "arg_count",
    "arg_name_length",
    "arg_name_utf8",
    "op_count_u16_be",
    "opcode_byte",
    "sha256_integrity",
]

COMPLEMENT_PAIRS = [("KO", "DR"), ("AV", "UM"), ("RU", "CA")]


@dataclass(frozen=True)
class DeckCard:
    card_id: str
    card_type: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "card_type": self.card_type,
            "payload": self.payload,
        }


def _import_surfaces():
    from src.ca_lexicon import (  # noqa: PLC0415
        ALL_LANG_MAP,
        ALL_TONGUE_NAMES,
        EXTENDED_TONGUE_NAMES,
        LANG_MAP,
        LEXICON,
        TONGUE_NAMES,
        TONGUE_PARENT,
    )
    from src.symphonic_cipher.scbe_aethermoore.trijective import DEFAULT_WITNESSES  # noqa: PLC0415

    return {
        "lexicon": LEXICON,
        "primary_tongues": list(TONGUE_NAMES),
        "extended_tongues": list(EXTENDED_TONGUE_NAMES),
        "all_tongues": list(ALL_TONGUE_NAMES),
        "primary_lang_map": dict(LANG_MAP),
        "all_lang_map": dict(ALL_LANG_MAP),
        "tongue_parent": dict(TONGUE_PARENT),
        "default_witnesses": dict(DEFAULT_WITNESSES),
    }


def _operation_cards(lexicon: dict[int, Any]) -> list[DeckCard]:
    cards: list[DeckCard] = []
    for op_id, entry in sorted(lexicon.items()):
        cards.append(
            DeckCard(
                card_id=f"op:{op_id:02x}:{entry.name}",
                card_type="operation",
                payload={
                    "op_id": op_id,
                    "op_hex": f"0x{op_id:02X}",
                    "name": entry.name,
                    "band": entry.band,
                    "chi": entry.chi,
                    "valence": entry.valence,
                    "trit": list(entry.trit),
                    "feat": list(entry.feat),
                    "note": entry.note,
                },
            )
        )
    return cards


def _language_view_cards(
    lexicon: dict[int, Any],
    all_tongues: list[str],
    all_lang_map: dict[str, str],
    tongue_parent: dict[str, str],
) -> list[DeckCard]:
    cards: list[DeckCard] = []
    for op_id, entry in sorted(lexicon.items()):
        for tongue in all_tongues:
            language = all_lang_map[tongue]
            direct_template = tongue in entry.code
            parent = tongue_parent.get(tongue)
            cards.append(
                DeckCard(
                    card_id=f"view:{tongue.lower()}:{op_id:02x}:{entry.name}",
                    card_type="language_view",
                    payload={
                        "op_id": op_id,
                        "op_hex": f"0x{op_id:02X}",
                        "op_name": entry.name,
                        "tongue": tongue,
                        "language": language,
                        "template_available": direct_template or parent is not None,
                        "template_source": "direct" if direct_template else "inherited",
                        "inherits_from": parent,
                    },
                )
            )
    return cards


def _binary_cards() -> list[DeckCard]:
    return [
        DeckCard(
            card_id=f"byte:{value:02x}",
            card_type="binary_byte",
            payload={
                "byte": value,
                "hex": f"0x{value:02X}",
                "binary": format(value, "08b"),
            },
        )
        for value in range(256)
    ]


def _stib_cards() -> list[DeckCard]:
    return [
        DeckCard(
            card_id=f"stib-field:{field}",
            card_type="stib_structure",
            payload={"field": field, "wire_format": "python.scbe.tongue_isa_binary.STIB"},
        )
        for field in STIB_STRUCTURE_FIELDS
    ]


def _pairing_cards(
    primary_tongues: list[str],
    all_tongues: list[str],
    tongue_parent: dict[str, str],
    default_witnesses: dict[str, tuple[str, str]],
) -> list[DeckCard]:
    cards: list[DeckCard] = []

    for anchor, witnesses in sorted(default_witnesses.items()):
        cards.append(
            DeckCard(
                card_id=f"pair:witness:{anchor.lower()}:{witnesses[0].lower()}-{witnesses[1].lower()}",
                card_type="witness_triangle",
                payload={"anchor": anchor, "witnesses": list(witnesses)},
            )
        )

    for left, right in COMPLEMENT_PAIRS:
        cards.append(
            DeckCard(
                card_id=f"pair:complement:{left.lower()}-{right.lower()}",
                card_type="complement_pair",
                payload={"left": left, "right": right},
            )
        )

    for child, parent in sorted(tongue_parent.items()):
        cards.append(
            DeckCard(
                card_id=f"pair:parent:{child.lower()}->{parent.lower()}",
                card_type="inheritance_pair",
                payload={"child": child, "parent": parent},
            )
        )

    for left, right in combinations(primary_tongues, 2):
        cards.append(
            DeckCard(
                card_id=f"pair:primary:{left.lower()}-{right.lower()}",
                card_type="primary_pair",
                payload={"left": left, "right": right},
            )
        )

    for left, right in combinations(all_tongues, 2):
        cards.append(
            DeckCard(
                card_id=f"pair:all:{left.lower()}-{right.lower()}",
                card_type="all_language_pair",
                payload={"left": left, "right": right},
            )
        )

    return cards


def build_manifest(generated_at_utc: str = "stable") -> dict[str, Any]:
    surfaces = _import_surfaces()
    lexicon = surfaces["lexicon"]
    primary_tongues = surfaces["primary_tongues"]
    extended_tongues = surfaces["extended_tongues"]
    all_tongues = surfaces["all_tongues"]
    all_lang_map = surfaces["all_lang_map"]

    operation_cards = _operation_cards(lexicon)
    language_view_cards = _language_view_cards(lexicon, all_tongues, all_lang_map, surfaces["tongue_parent"])
    binary_cards = _binary_cards()
    stib_cards = _stib_cards()
    pairing_cards = _pairing_cards(
        primary_tongues,
        all_tongues,
        surfaces["tongue_parent"],
        surfaces["default_witnesses"],
    )

    current_grounded_minimum = (
        len(operation_cards)
        + len(language_view_cards)
        + len(binary_cards)
        + len(stib_cards)
        + len(pairing_cards)
    )
    grounded_language_view_total = len(operation_cards) * len(all_tongues)
    primary_language_view_total = len(operation_cards) * len(primary_tongues)

    return {
        "schema_version": "scbe_coding_deck_manifest_v1",
        "generated_at_utc": generated_at_utc,
        "design_rule": "Substrate card first; language cards are projections, not separate truth sources.",
        "sources": {
            "operation_substrate": "src.ca_lexicon.LEXICON",
            "binary_transport": "python.scbe.tongue_isa_binary.STIB",
            "witness_pairs": "src.symphonic_cipher.scbe_aethermoore.trijective.DEFAULT_WITNESSES",
        },
        "language_lanes": {
            "primary": {tongue: surfaces["primary_lang_map"][tongue] for tongue in primary_tongues},
            "extended": {tongue: all_lang_map[tongue] for tongue in extended_tongues},
            "all": {tongue: all_lang_map[tongue] for tongue in all_tongues},
        },
        "counts": {
            "operation_cards": len(operation_cards),
            "primary_language_view_cards": primary_language_view_total,
            "extended_language_view_cards": len(operation_cards) * len(extended_tongues),
            "all_language_view_cards": grounded_language_view_total,
            "binary_byte_cards": len(binary_cards),
            "stib_structure_cards": len(stib_cards),
            "pairing_cards": len(pairing_cards),
            "current_grounded_minimum_cards": current_grounded_minimum,
            "cards_per_new_language_lane": len(operation_cards),
            "pairing_cards_added_per_new_language_lane": len(all_tongues),
        },
        "deduction": {
            "current_formula": "64 operation + (64 * 8 language views) + 256 binary bytes + 13 STIB fields + pairing cards",
            "new_language_formula": "add 64 language-view cards plus N existing pair cards for the new lane",
            "world_complete_warning": "World-complete programming coverage is not deducible yet; this manifest covers the repo-grounded substrate and current language lanes.",
        },
        "cards": {
            "operations": [card.to_dict() for card in operation_cards],
            "language_views": [card.to_dict() for card in language_view_cards],
            "binary": [card.to_dict() for card in binary_cards],
            "stib": [card.to_dict() for card in stib_cards],
            "pairings": [card.to_dict() for card in pairing_cards],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output manifest JSON path.")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON to stdout.")
    parser.add_argument("--generated-at-now", action="store_true", help="Use the current UTC time instead of stable.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at_utc = datetime.now(timezone.utc).isoformat() if args.generated_at_now else "stable"
    manifest = build_manifest(generated_at_utc=generated_at_utc)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(
            json.dumps(
                {
                    "schema_version": manifest["schema_version"],
                    "output_path": str(out_path),
                    "counts": manifest["counts"],
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
