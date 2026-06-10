"""Compose the cross-language lookup view into a single inspection artifact.

Pulls together the three substrate layers that already live in the repo:
  1. Per-tongue 256-byte bijection from `src.crypto.sacred_tongues`
  2. Tongue -> primary language map from `src.ca_lexicon` (incl. extended GO/ZI)
  3. 64-op LEXICON with 6-tongue (and via overrides, 8-tongue) code templates

Output: artifacts/cross_language_lookup/full_cross_language_lookup.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crypto.sacred_tongues import (  # noqa: E402
    SACRED_TONGUE_TOKENIZER,
    SECTION_TONGUES,
    TONGUES,
)
from src.ca_lexicon import (  # noqa: E402
    EXTENDED_LANG_MAP,
    EXTENDED_TONGUE_NAMES,
    LANG_MAP,
    LEXICON,
    PHI,
    TONGUE_NAMES,
    TONGUE_PARENT,
    _GO_OVERRIDES,
    _ZI_OVERRIDES,
)

_EXT_OVERRIDES = {"GO": _GO_OVERRIDES, "ZI": _ZI_OVERRIDES}


OUT_DIR = PROJECT_ROOT / "artifacts" / "cross_language_lookup"
OUT_PATH = OUT_DIR / "full_cross_language_lookup.json"


def _tongue_metadata() -> dict:
    """Merge sacred_tongues.TongueSpec metadata with ca_lexicon language map."""
    rows = []
    for code in TONGUE_NAMES:
        spec = TONGUES[code.lower()]
        rows.append(
            {
                "code": code,
                "name": spec.name,
                "primary_language": LANG_MAP[code],
                "harmonic_frequency_hz": spec.harmonic_frequency,
                "domain": spec.domain,
                "parent": None,
                "extended": False,
            }
        )
    for code in EXTENDED_TONGUE_NAMES:
        parent = TONGUE_PARENT[code]
        parent_spec = TONGUES[parent.lower()]
        rows.append(
            {
                "code": code,
                "name": code,
                "primary_language": EXTENDED_LANG_MAP[code],
                "harmonic_frequency_hz": parent_spec.harmonic_frequency,
                "domain": f"extended dialect of {parent}",
                "parent": parent,
                "extended": True,
            }
        )
    return rows


def _byte_tables() -> dict:
    """For each canonical tongue, emit the 256-row byte->token bijection."""
    tables = {}
    for code in TONGUE_NAMES:
        lower = code.lower()
        spec = TONGUES[lower]
        rows = []
        b2t = SACRED_TONGUE_TOKENIZER.byte_to_token[lower]
        for b in range(256):
            hi = (b >> 4) & 0x0F
            lo = b & 0x0F
            rows.append(
                {
                    "byte_int": b,
                    "byte_hex": f"0x{b:02X}",
                    "hi_nibble": hi,
                    "lo_nibble": lo,
                    "prefix": spec.prefixes[hi],
                    "suffix": spec.suffixes[lo],
                    "token": b2t[b],
                }
            )
        tables[code] = rows
    return tables


def _lexicon_rows() -> list:
    """Flatten LEXICON into a JSON-friendly array with raw 8-language templates per op.

    Templates keep their `{a}`, `{b}` placeholders so the artifact remains a
    code-template lookup, not a pre-formatted snippet dump. Extended tongues
    (GO/ZI) inherit the parent template when no explicit override exists.
    """
    rows = []
    for op_id in sorted(LEXICON.keys()):
        entry = LEXICON[op_id]
        templates = dict(entry.code)  # KO/AV/RU/CA/UM/DR raw templates
        for ext, overrides in _EXT_OVERRIDES.items():
            if entry.name in overrides:
                templates[ext] = overrides[entry.name]
                templates[f"{ext}_inherits_from"] = None
            else:
                parent = TONGUE_PARENT[ext]
                templates[ext] = entry.code[parent]
                templates[f"{ext}_inherits_from"] = parent
        rows.append(
            {
                "op_id": op_id,
                "op_hex": f"0x{op_id:02X}",
                "name": entry.name,
                "band": entry.band,
                "chi": entry.chi,
                "valence": entry.valence,
                "trit": list(entry.trit),
                "feat": list(entry.feat),
                "note": entry.note,
                "code": templates,
            }
        )
    return rows


def _metrics_block() -> dict:
    """Phi constants + per-tongue weights so the metrics layer is preserved."""
    weights = {}
    for i, code in enumerate(TONGUE_NAMES):
        weights[code] = PHI**i
    return {
        "phi": PHI,
        "phi_squared": PHI * PHI,
        "tongue_phi_weights": weights,
        "section_routing": dict(SECTION_TONGUES),
    }


def validate_artifact(artifact: dict) -> dict:
    """Hard checks for coverage/integrity before publishing artifact."""
    problems: list[str] = []
    tongues = artifact.get("tongues", [])
    byte_tables = artifact.get("byte_tables", {})
    lexicon = artifact.get("lexicon", [])

    if artifact.get("schema") != "scbe_cross_language_lookup_v1":
        problems.append("schema mismatch")

    if len(tongues) < len(TONGUE_NAMES):
        problems.append(f"expected >= {len(TONGUE_NAMES)} tongues, got {len(tongues)}")

    # Canonical 6 tongues must have full 256-row bijection.
    for code in TONGUE_NAMES:
        rows = byte_tables.get(code)
        if not isinstance(rows, list):
            problems.append(f"{code}: missing byte table")
            continue
        if len(rows) != 256:
            problems.append(f"{code}: expected 256 rows, got {len(rows)}")
        byte_ints = {row.get("byte_int") for row in rows}
        tokens = {row.get("token") for row in rows}
        if byte_ints != set(range(256)):
            problems.append(f"{code}: byte_int coverage is not 0..255")
        if len(tokens) != 256:
            problems.append(f"{code}: token uniqueness broken ({len(tokens)} distinct)")

    if len(lexicon) != 64:
        problems.append(f"expected 64 lexicon rows, got {len(lexicon)}")
    else:
        required_primary = set(TONGUE_NAMES)
        for row in lexicon:
            code = row.get("code", {})
            missing = sorted(required_primary - set(code))
            if missing:
                problems.append(
                    f"{row.get('name')}: missing primary code templates {missing}"
                )

    return {"ok": not problems, "problems": problems}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Validate existing artifact and exit."
    )
    args = parser.parse_args()

    if args.check:
        if not OUT_PATH.exists():
            print(
                json.dumps(
                    {"ok": False, "error": f"artifact missing: {OUT_PATH}"}, indent=2
                )
            )
            return 1
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        validation = validate_artifact(existing)
        print(
            json.dumps(
                {"ok": validation["ok"], "problems": validation["problems"]}, indent=2
            )
        )
        return 0 if validation["ok"] else 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tongues = _tongue_metadata()
    byte_tables = _byte_tables()
    lexicon = _lexicon_rows()
    metrics = _metrics_block()

    artifact = {
        "schema": "scbe_cross_language_lookup_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": (
            "Composed view of the SCBE byte<->token bijection, tongue->language "
            "map, and 64-op multilingual lexicon. Substrate sources: "
            "src/crypto/sacred_tongues.py and src/ca_lexicon/__init__.py."
        ),
        "patent_reference": "US Provisional #63/961,403",
        "tongues": tongues,
        "byte_tables": byte_tables,
        "lexicon": lexicon,
        "metrics": metrics,
        "counts": {
            "canonical_tongues": len(TONGUE_NAMES),
            "extended_tongues": len(EXTENDED_TONGUE_NAMES),
            "bytes_per_tongue": 256,
            "total_byte_token_rows": 256 * len(TONGUE_NAMES),
            "lexicon_ops": len(lexicon),
            "code_snippets_per_op": len(lexicon[0]["code"]) if lexicon else 0,
            "total_code_snippets": sum(len(r["code"]) for r in lexicon),
        },
    }
    validation = validate_artifact(artifact)
    if not validation["ok"]:
        print(json.dumps({"ok": False, "problems": validation["problems"]}, indent=2))
        return 1

    OUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    size = OUT_PATH.stat().st_size
    print(f"[xlang-lookup] wrote {OUT_PATH}")
    print(f"[xlang-lookup] size: {size:,} bytes")
    print(f"[xlang-lookup] counts: {json.dumps(artifact['counts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
