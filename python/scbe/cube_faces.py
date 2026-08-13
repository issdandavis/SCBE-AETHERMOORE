"""
cube_faces — one token core, every surface a different use (the Rubik's cube).

A token is ONE bijective object. Rotate it to any face and you get a different
decoder of the same core — and you can always rotate back (no information lost).
This assembles every face from the real engines, so the cube is real, not a mock:

  * core        — the raw bytes / hex (the single object every face decodes)
  * chemistry   — CubeToken.chem_face: semantic class -> element -> 6-channel trit
  * roles       — that trit read as control/IO/scope/math/security/transform (tongue_roles)
  * code        — CubeToken.code_faces: the 6 Sacred-Tongue coding-language faces
  * governance  — CubeToken.gov_face: semantic class + ALLOW/QUARANTINE band
  * wolfram     — each byte is an elementary cellular-automaton rule + complexity class
  * color       — clay_colors PALETTE/mix/nearest, the function Clay was trained on
  * affect      — emotional_syntax_tree.analyze_affect, the Heart Vault taxonomy

CARS AND ROADS (Issac, 2026-08-06). A token is a car; bijectivity is the road system.
A road is two-way: drive out to the face, drive back, and the same car arrives. A
destination is one-way: many cars park in the same spot and you cannot tell from the
spot which car it was.

That distinction was ALREADY TRUE in this file and was never written down, which made it
easy to misread `bijective` as a claim about all of them. It is not:

    CubeToken.is_bijective() == all(from_face(t, face(t)).token == token for t in TONGUES)

It quantifies over TONGUES only. The six Sacred-Tongue code faces are the roads.
`chemistry` collapses a token to one element, `audio` to `sum(raw) % 12`, `wolfram` to the
first 8 bytes' CA rules — all one-way, none of them under the proof, and correctly so.

So adding `color` and `affect` CANNOT break bijectivity: both are destinations. The real
hazard is the opposite one, and it had no guard at all — someone later paving a one-way
street INTO the road network, where `is_bijective()` would start returning False with no
explanation of which face did it. `road_map` names every face's kind, and `_road_check`
fails loudly and specifically if a declared road does not round-trip.

AFFECT IS A PROPERTY OF THE TRIP, NOT THE CAR. `analyze_affect("loop")` returns neutral at
confidence 0.2 with no evidence, and so does every other bare token — emotion lives in the
utterance a token rode in on, not in four bytes. `all_faces(token, context=...)` therefore
takes an optional passenger; without one the face reports `context_is_token: True` so a
neutral reading is never mistaken for a measurement.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

try:
    from python.scbe.cube_token import TONGUES, CubeToken
    from python.scbe.wolfram_face import token_rule as _wolfram_rule
    from python.scbe.tongue_roles import TONGUE_ROLE
    from python.scbe.atomic_tokenization import chemical_element, parse_formula
    from python.scbe.bit_spine import BitSpine
except ModuleNotFoundError:  # pragma: no cover - direct execution
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from python.scbe.cube_token import TONGUES, CubeToken
    from python.scbe.wolfram_face import token_rule as _wolfram_rule
    from python.scbe.tongue_roles import TONGUE_ROLE
    from python.scbe.atomic_tokenization import chemical_element, parse_formula
    from python.scbe.bit_spine import BitSpine


_PHI = (1 + 5**0.5) / 2
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# The color and affect engines live in the loom lane, not in SCBE. They are imported
# OPTIONALLY and on purpose: hard-wiring SCBE to C:\dev\loom would make this package
# unimportable wherever loom is absent, and a face that fakes values when its engine is
# missing is worse than one that says so. If an engine cannot be loaded the face is still
# emitted, carrying `available: False` and the reason.
#
# Do NOT derive this by walking up from __file__. SCBE-AETHERMOORE lives in the PROFILE
# (C:\Users\issda\SCBE-AETHERMOORE), not under C:\dev, so four levels up lands on
# C:\Users\issda\loom, which does not exist — and `C:\dev\SCBE-AETHERMOORE` is a junction
# to the same files, so the walk-up answer changes with which path you opened. The farm
# root is the stable fact; the package's own location is not.
def _loom_root() -> tuple[str | None, str]:
    cands = [os.environ.get("CLAY_LOOM_PATH"), r"C:\dev\loom", "/c/dev/loom"]
    tried = [c for c in cands if c]
    for c in tried:
        if os.path.isdir(c):
            return c, ""
    return None, "no loom checkout at any of: %s" % ", ".join(tried)


_LOOM, _LOOM_ERR = _loom_root()

# `loom_multiplex` and `node_catalog` sit together under clay-one-repo/vault/multiplex.
# That pair is the REAL address space, and it is a different checkout from loom proper.
_MPLEX = os.environ.get("CLAY_MULTIPLEX_PATH") or r"C:\dev\clay-one-repo\vault\multiplex"


_ENGINES: Dict[str, Any] = {}


def _load_loom(module: str, root: str | None = None):
    """Import a loom engine WITHOUT letting it disturb this package's import resolution.

    `emotional_syntax_tree._load_heart_vault()` does `sys.path.insert(0, ...)` with a path
    under C:\\Users\\issda\\SCBE-AETHERMOORE so it can read the Heart Vault emotion
    taxonomy. Position ZERO — so after the affect engine loads, `from scbe import
    encode_bytes` inside `cube_token._tongue_encode` resolves to the python/scbe PACKAGE
    instead of the root CLI module and every tongue face dies with ImportError. Wiring a
    face broke the roads, by a route that has nothing to do with the face.

    So sys.path is snapshotted and restored around the import, and loading is lazy and
    memoised rather than done at module import: a consumer that never touches color or
    affect never pays for either engine, and nothing about the cube changes by importing it.
    """
    import importlib
    import sys

    if module in _ENGINES:
        return _ENGINES[module]
    where = root or _LOOM
    if where is None:
        _ENGINES[module] = (None, _LOOM_ERR)
        return _ENGINES[module]
    if not os.path.isdir(where):
        _ENGINES[module] = (None, "no checkout at %s" % where)
        return _ENGINES[module]

    # `tongues` is a TOP-LEVEL package name owned by two different lanes: SCBE's
    # src/tongues/ and the multiplex's vault/multiplex/tongues/. SCBE's wins on sys.path
    # and, worse, sys.modules caches whichever loaded first, so `loom_multiplex`'s
    # `from tongues import tongue_opcodes` fails with SCBE's version already resolved.
    # Prepending is only safe because sys.path AND the evicted modules are both restored
    # below — the engine sees its own lane, the host never notices.
    # MEASURED 2026-08-13 -- prepending `where` is NOT sufficient, and the reason is a
    # Python import rule rather than an ordering mistake:
    #
    #     SCBE     src/tongues/__init__.py present  -> REGULAR package
    #     loom     tongues/  (no __init__.py)       -> namespace package
    #     multiplex tongues/ (no __init__.py)       -> namespace package
    #
    # A regular package ALWAYS beats a namespace package, at ANY sys.path position. So once
    # SCBE's src is on the path, `from tongues import tongue_opcodes` resolves to SCBE's
    # tongues (which has no tongue_opcodes) and no amount of insert(0) or sys.modules
    # eviction changes it. That is why the address face loaded when it ran FIRST and failed
    # after any engine had put src on the path -- a load-order-dependent failure with a
    # cause that is not load order.
    #
    # The competing root therefore has to be REMOVED for the duration of the import, not
    # out-prioritised. sys.path is restored in `finally` exactly as before, so the host
    # never observes the gap.
    saved_path = list(sys.path)
    shadowed = ("tongues", "tongue_opcodes", "node_catalog", "loom_multiplex")
    # evict submodules too: `tongues.role_registry` keeps the parent package alive.
    saved_mods = {k: v for k, v in list(sys.modules.items())
                  if any(k == s or k.startswith(s + ".") for s in shadowed)}
    try:
        for k in saved_mods:
            if k != module:
                del sys.modules[k]
        # There are TWO shadowing conflicts here and they point opposite ways, which is
        # why fixing one alone just moves the error:
        #
        #   tongues -> SCBE/src/tongues/ is a REGULAR package and beats the engine's
        #              namespace package. Its path entry must be dropped.
        #   scbe    -> SCBE/scbe.py is a MODULE and beats SCBE/python/scbe/, the real
        #              package. multiplex's tongue_opcodes.py does `import
        #              scbe.instrument`, so the module form yields
        #              "No module named 'scbe.instrument'; 'scbe' is not a package".
        #              Its path entry must be dropped and python/ put in front.
        #
        # Removing the whole SCBE tree kills both problems and the dependency with them.
        # So: drop only entries that actually compete, and guarantee the two roots the
        # engine needs are first.
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../python
        keep = {os.path.abspath(where), pkg_root}

        def _competes(p: str) -> bool:
            base = os.path.abspath(p or ".")
            if base in keep:
                return False
            if any(os.path.isfile(os.path.join(base, s, "__init__.py")) for s in shadowed):
                return True
            return os.path.isfile(os.path.join(base, "scbe.py"))

        # a module-form `scbe` already in sys.modules survives any path change
        stale_scbe = sys.modules.get("scbe")
        if stale_scbe is not None and not hasattr(stale_scbe, "__path__"):
            saved_mods["scbe"] = stale_scbe
            del sys.modules["scbe"]

        sys.path[:] = [where, pkg_root] + [p for p in saved_path if not _competes(p)]
        got = (importlib.import_module(module), None)
    except Exception as exc:  # engine absent or broken — say which, do not invent values
        got = (None, "%s: %s" % (type(exc).__name__, exc))
    finally:
        sys.path[:] = saved_path  # undo the engine's own insert(0, ...) too
        for k, m in saved_mods.items():
            if k != module:
                sys.modules[k] = m
    _ENGINES[module] = got
    return got


def _raw_bytes(cube: CubeToken) -> bytes:
    r = cube.raw
    return r if isinstance(r, (bytes, bytearray)) else r()


def _bits_face(raw: bytes) -> Dict[str, Any]:
    """The center ball: byte-exact binary / hex / trit projections (bit_spine)."""
    spine = BitSpine(raw)
    trits = spine.trits()
    return {"binary": spine.bits(), "hex": spine.hex(), "trit_count": len(trits), "trits": trits[:24]}


def _audio_face(raw: bytes, trit: Dict[str, int]) -> Dict[str, Any]:
    """The hear sense: a phi-stepped frequency + musical note for the token."""
    bsum = sum(raw)
    freq = round(440.0 * (_PHI ** ((bsum % 12) / 12.0)), 2)
    overtones = {t: round(440.0 * (_PHI ** (i / 6.0)), 1) for i, t in enumerate(TONGUE_ROLE) if trit.get(t, 0) > 0}
    return {
        "phi_base_hz": 440.0,
        "phi_frequency_hz": freq,
        "note": _NOTES[bsum % 12],
        "active_tongue_overtones": overtones,
    }


def _wolfram_face(raw: bytes) -> Dict[str, Any]:
    """Each byte of the token is an elementary CA rule with a complexity class."""
    rules = []
    for b in list(raw)[:8]:
        info = _wolfram_rule(b)
        rules.append(
            {
                "byte": b,
                "rule": info["rule"],
                "class": info["class"],
                "class_name": info["class_name"],
                "universal": info["universal"],
            }
        )
    return {"per_byte_rules": rules, "any_universal": any(r["universal"] for r in rules)}


def _address_face(token: str) -> Dict[str, Any]:
    """WHERE the token sits on the wafer: multi-point, six-dimensional, charged, stated.

    Issac, 2026-08-06: "are you using multi point geospatial coordinates in 6 dimensions as
    the addresses, as well as word charge and state". The answer had been NO — a crc32 hash
    was standing in — and the real thing was already built in `loom_multiplex`:

      xyz per depth level   opcode_xyz(op) = (op//16, (op%16)//4, op%4), ONE 3-D point per
                            level of the route. An Address is a ROUTE through recursively
                            repeated 4x4x4 boxes, so it is multi-POINT by construction, not
                            one coordinate.
      domain                address_domain() -> nested EXACT half-open XYZ intervals in
                            `Fraction`, so containment is rational and cannot drift.
      six dimensions        tongue_forms(op) -> six reversible surface words, and it ASSERTS
                            parse(render(op)) == op, so every tongue is a ROAD by construction.
      word charge           +-1 per cell, additive.
      state                 frame (true_north | current_north), orientation_count,
                            active_tongue, fixed.

    THE GAP THIS FACE EXISTS TO MAKE VISIBLE. `node_catalog.CATALOG` is exactly 64 cells and
    they are OPERATIONS -- add, sub, mul, div, mod, pow. 'loop', 'ward' and 'calc' are not in
    it. **Arbitrary tokens have no address on this wafer**, and no placement map from token
    to cell exists yet; building one is the "till the field" job, not something a hash
    substitutes for. So an unplaced token reports `placed: False` with the reason, per the
    standing rule that unplaceable is named, never silently dropped.
    """
    mplex, err = _load_loom("loom_multiplex", _MPLEX)
    cat, cerr = _load_loom("node_catalog", _MPLEX)
    if mplex is None or cat is None:
        return {"available": False, "reason": err or cerr,
                "engine": "clay-one-repo/vault/multiplex"}

    cell = cat.CATALOG.get(token)
    if cell is None:
        # PLACEMENT MAP, added 2026-08-13. The gap named above is closed, and NOT by a
        # hash -- the docstring rules that out and it is right to. The multiplex numbers
        # give a bijection outright:
        #
        #     4x4x4 = 64 cells, x 4 orientations = 256 = the byte, factored
        #     byte b -> (cell = b >> 2, orientation = b & 3);  b = (cell << 2) | orient
        #
        # Total and injective in both directions, so no collision policy is needed and
        # nothing has to be inverted. A multi-byte token is therefore not one cell but a
        # PATH through the wafer, which is what Address(parts) already models. Proven at
        # C:\dev\loom\clay_address.py -- 7,168 byte/step checks and 4,096 random blobs,
        # 0 failures, plus a machine-exact graph-Fourier roundtrip over the same cells.
        #
        # The 64 catalog OPERATIONS stay authoritative for their own tokens; this branch
        # only serves tokens that had no address at all before.
        raw = token.encode("utf-8")
        cells = [b >> 2 for b in raw]
        postal = [(i % 4, b >> 2, b & 3) for i, b in enumerate(raw)]
        recovered = bytes((c << 2) | o for _, c, o in postal)
        depth_cap = getattr(mplex, "DEFAULT_MAX_DEPTH", 12)
        nested = mplex.Address(tuple(cells[:depth_cap])) if cells else None
        return {
            "available": True,
            "placed": True,
            "placement": "bijective-byte",
            "reason": "not a catalog operation; placed by the byte<->(cell,orientation) "
                      "bijection, so the token occupies a path rather than one cell",
            "catalog_size": len(cat.CATALOG),
            "address": str(nested) if nested is not None else None,
            "postal": postal,
            "xyz_per_level": [mplex.opcode_xyz(c) for c in cells[:depth_cap]],
            # length prefix first so lexicographic order matches shelf order; without it
            # a short address sorts as a prefix of a longer one.
            "library_index": "%04d:%s" % (len(postal),
                                          ".".join("%d-%02d-%d" % p for p in postal)),
            "roundtrip_exact": recovered == raw,
            # a nested Address caps at DEFAULT_MAX_DEPTH; `postal` never truncates, and
            # the difference is reported rather than silently swallowed.
            "nested_truncated": len(cells) > depth_cap,
            "bytes": len(raw),
        }

    op = cell.byte if hasattr(cell, "byte") else getattr(cell, "opcode", None)
    addr = mplex.Address((op,))
    rec = mplex.cell_record(addr, charge=+1)
    return {
        "available": True,
        "placed": True,
        "address": rec["address"],
        "opcode": rec["opcode"],
        "xyz_per_level": [mplex.opcode_xyz(p) for p in addr.parts],
        "domain": str(rec["domain"]),
        "six_dimensional": rec["tongue_forms"],
        "charge": rec["charge"],
        "state": {k: rec.get(k) for k in
                  ("frame", "fixed", "orientation_count", "active_tongue", "word")},
        "realm": getattr(cell, "realm", None),
    }


def _color_face(raw: bytes, chem: Dict[str, Any]) -> Dict[str, Any]:
    """The see sense. A DESTINATION, not a road — many tokens land on the same swatch.

    Uses the real `clay_colors` PALETTE / `nearest` / `mix`, i.e. the exact function Clay
    was trained on (`clay_colors.pt`), rather than a second colour scheme invented here.

    TWO CHANNELS, AND THEY ARE NOT THE SAME KIND OF THING. Conflating them is what made
    the first version useless.

      `address`  crc32 -> RGB. DECORRELATED from the bytes on purpose, so it spreads.
                 Measured over a 49-token vocabulary: 14 of 16 swatches used, largest bin
                 28.6%. It discriminates and it carries NO meaning — two tokens with
                 adjacent addresses are not related.
                 (28.6% on gray is geometry, not a defect: gray is the palette centroid,
                 so it owns the most volume in a nearest-neighbour partition.)

      `meaning`  the lit tongue roles, each given a palette colour and MIXED pairwise by
                 `clay_colors.mix` — the composable function, so control+math reads as
                 the colour those two make. Coarse (six roles) and None when chemistry is
                 UNRESOLVED, e.g. 'calc'.

    `byte_fold` IS MEASURED DEGENERATE AND IS KEPT ANYWAY. Folding the bytes positionally
    (0::3, 1::3, 2::3) sent 84% of that same vocabulary to gray using 4 of 16 swatches; a
    seeded XOR variant was worse at 100% pink, 1 of 16. Cause: lowercase ASCII occupies
    bytes 97-122, a thin sliver of the cube, so any direct fold piles up near the centroid.
    It stays in the output under Issac's own rule for the two unreceipted laws — deleting
    it would hide that it was checked — and it is labelled so nobody reads it as an address.
    """
    import zlib

    colors, err = _load_loom("clay_colors")
    if colors is None:
        return {"available": False, "reason": err, "engine": "loom/clay_colors.py"}

    h = zlib.crc32(raw)
    addr_rgb = ((h >> 16) & 255, (h >> 8) & 255, h & 255)
    fold_rgb = tuple(sum(raw[i::3]) % 256 if raw[i::3] else 0 for i in range(3))

    # each active role gets a palette colour, then they are MIXED (not concatenated)
    roles = [t for t in TONGUE_ROLE if chem.get("trit_vector", {}).get(t, 0) > 0]
    names = colors.NAMES
    role_colors = {t: names[(sum(t.encode("utf-8")) % len(names))] for t in roles}
    mixed = None
    for c in role_colors.values():
        mixed = c if mixed is None else colors.mix(mixed, c)

    return {
        "available": True,
        # NOT an address. crc32 spreads (14/16 swatches, largest bin 28.6%, n=49) and that
        # is all it does -- two tokens with adjacent values are unrelated, so no geometry
        # works on it. The real address is `faces.address`; this is a stable random label
        # and is named as one.
        "spread_label": {"rgb": addr_rgb, "swatch": colors.nearest(addr_rgb),
                         "source": "crc32", "discriminates": True, "is_an_address": False,
                         "measured": "14/16 swatches, largest bin 28.6% (n=49)"},
        "meaning": {"role_colors": role_colors, "role_mix": mixed,
                    "source": "chemistry trit -> clay_colors.mix", "composable": True},
        "byte_fold": {"rgb": fold_rgb, "swatch": colors.nearest(fold_rgb),
                      "discriminates": False,
                      "measured": "4/16 swatches, 84% gray (n=49) -- degenerate, kept as a "
                                  "record that it was checked"},
        "palette_size": len(names),
        "invertible": False,
    }


def _affect_face(text: str, is_token: bool) -> Dict[str, Any]:
    """The feel sense. A DESTINATION, and one that is honest about having nothing to read.

    `analyze_affect` is phrase-cued, so a bare token scores nothing and falls through to
    neutral at confidence 0.2 with empty evidence — measured, not assumed:
    'loop', 'ward' and 'calc' all return exactly that. Emotion is a property of the
    utterance a token rode in on, not of four bytes.

    `context_is_token` is therefore emitted on every reading taken without a passenger, so
    a neutral value can never be mistaken for a measurement of neutrality. `evidence` is
    the phrase list the deterministic v1 parser actually matched, kept per the voice-box
    rule that a later learned model may add labels only in a NEW sidecar and may never
    silently rewrite the v1 result.
    """
    engine, err = _load_loom("emotional_syntax_tree")
    if engine is None:
        return {"available": False, "reason": err,
                "engine": "loom/emotional_syntax_tree.py"}

    a = engine.analyze_affect(text)
    return {
        "available": True,
        "context_is_token": is_token,
        "primary": a.primary,
        "labels": list(a.labels),
        "valence": a.valence,
        "arousal": a.arousal,
        "intensity": a.intensity,
        "confidence": a.confidence,
        "mixed": a.mixed,
        "ambivalent": a.ambivalent,
        "attachment": a.attachment,
        "pain": a.pain,
        "comfort": a.comfort,
        "memory_continuity": a.memory_continuity,
        "protective_anchor": a.protective_anchor,
        "restraint": a.restraint,
        "force_relation": a.force_relation,
        "heart_vault_poincare": list(a.poincare),
        "evidence": list(a.evidence),
        "parser": "emotional_syntax_tree.v1",
        "invertible": False,
    }


def _road_check(cube: CubeToken) -> Dict[str, Any]:
    """Which faces are ROADS, which are DESTINATIONS, and does every road still go both ways?

    `is_bijective()` returns one bool for all six tongues at once. When it flips to False
    it does not say WHICH tongue stopped round-tripping, and nothing anywhere warned that
    a newly added face must not be pushed into TONGUES. This reports per road, so paving a
    one-way street into the road network fails loudly and names itself.
    """
    roads, broken = {}, []
    for t in TONGUES:
        surface = cube.face(t)
        back = CubeToken.from_face(t, surface).token
        ok = back == cube.token
        roads[t] = {"surface": surface, "returns": back, "two_way": ok}
        if not ok:
            broken.append(t)
    return {
        "roads": roads,
        "destinations": ["bits", "chemistry", "roles", "audio", "governance",
                         "wolfram", "color", "affect"],
        "all_roads_two_way": not broken,
        "broken_roads": broken,
        "invariant": "a road round-trips to the exact token; a destination does not and "
                     "is not claimed to. `bijective` quantifies over roads ONLY.",
    }


def _role_face(chem: Dict[str, Any]) -> List[str]:
    """Read the chemistry trit vector as the Sacred-Tongue roles it lights."""
    if not chem.get("semantic_resolved", False):
        return []
    tv = chem.get("trit_vector", {})
    return [TONGUE_ROLE[t]["role"] for t in TONGUE_ROLE if tv.get(t, 0) > 0]


def all_faces(token: str, context: str | None = None) -> Dict[str, Any]:
    """One core token, decoded through every face of the cube.

    `context` is the utterance the token rode in on. It feeds the affect face only —
    every other face reads the token's own bytes. Omit it and affect reports
    `context_is_token: True` alongside its neutral reading.

    Additive only: every key this returned before is still returned, `bijective` still
    means exactly what it meant. `color`, `affect` and `road_map` are new.
    """
    cube = CubeToken(token)
    raw = _raw_bytes(cube)
    chem = dict(cube.chem_face())
    real = chemical_element(token)
    if real is not None:
        chem["real_element"] = {
            "symbol": real.symbol,
            "Z": real.Z,
            "group": real.group,
            "period": real.period,
            "valence": real.valence,
            "electronegativity": real.electronegativity,
        }
    composition = parse_formula(token)
    if composition and len(composition) > 1:
        chem["composition"] = composition
    return {
        "token": token,
        "core": {"hex": raw.hex(), "bytes": list(raw), "byte_count": len(raw)},
        "faces": {
            "bits": _bits_face(raw),
            "chemistry": chem,
            "roles": _role_face(chem),
            "audio": _audio_face(raw, chem.get("trit_vector", {})),
            "code": cube.code_faces(),
            "governance": cube.gov_face(),
            "wolfram": _wolfram_face(raw),
            "color": _color_face(raw, chem),
            "affect": _affect_face(context if context is not None else token,
                                   context is None),
            "address": _address_face(token),
        },
        "bijective": cube.is_bijective(),
        "road_map": _road_check(cube),
    }


def _demo() -> None:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    for tok in ("loop", "ward", "calc"):
        f = all_faces(tok)
        print(f"\n=== cube: '{tok}'  (core {f['core']['hex']}, bijective={f['bijective']}) ===")
        ch = f["faces"]["chemistry"]
        print(
            f"  chemistry : {ch['semantic_class']} -> {ch['element']} "
            f"(Z={ch['Z']}, val={ch['valence']})  trit={ch['trit_vector']}"
        )
        print(f"  roles     : {', '.join(f['faces']['roles']) or '-'}")
        print(f"  governance: {f['faces']['governance']}")
        wf = f["faces"]["wolfram"]
        print(
            "  wolfram   : "
            + " ".join(f"{r['byte']}={r['class']}" for r in wf["per_byte_rules"])
            + f"  (universal={wf['any_universal']})"
        )
        print(f"  code (KO) : python -> {f['faces']['code']['KO']['tokens']}")
        co = f["faces"]["color"]
        print(f"  color     : address={co['address']['swatch']:<8} "
              f"meaning={co['meaning']['role_mix']}  "
              f"(byte_fold={co['byte_fold']['swatch']}, degenerate)" if co.get("available")
              else f"  color     : UNAVAILABLE ({co.get('reason')})")
        af = f["faces"]["affect"]
        print(f"  affect    : {af.get('primary')} conf={af.get('confidence')} "
              f"force={af.get('force_relation')} evidence={af.get('evidence')}"
              if af.get("available") else f"  affect    : UNAVAILABLE ({af.get('reason')})")
        rm = f["road_map"]
        print(f"  roads     : {len(rm['roads'])} two-way={rm['all_roads_two_way']}"
              f"{'  BROKEN=' + str(rm['broken_roads']) if rm['broken_roads'] else ''}")

    # affect with a passenger -- the same token, now riding in an utterance
    print("\n=== affect is a property of the TRIP, not the car ===")
    for ctx in (None, "I let go and he is alive"):
        a = all_faces("ward", ctx)["faces"]["affect"]
        label = "no context (token only)" if ctx is None else repr(ctx)
        if not a.get("available"):
            print(f"  {label:<32} -> UNAVAILABLE ({a.get('reason')})")
            continue
        print(f"  {label:<32} -> {a['primary']:<9} conf={a['confidence']:.2f} "
              f"force={a['force_relation']} evidence={list(a['evidence'])}")


if __name__ == "__main__":
    _demo()
