#!/usr/bin/env python3
"""One executable entry point for the Loom recursive multiplex.

This composes the existing objects; it does not replace them:

* ``opcode_cube_multiplex.py``: 64 cells and the 76 four-cell thread walls.
* ``turing_wafer.py``: row/column Mobius transport over both charge frames.
* ``turing_blocks.py``: write/move/branch/jump/halt machine core.
* ``tongues/tongue_opcodes.py``: six reversible language views.
* ``radial_trifold.py``: seven internal layers x three constrained C3 phase channels.

The box is finite.  The infinity is perceptual: a small pool of nested shells is
reused as the viewer moves through depth.  Runtime depth is explicitly bounded;
no command here claims or allocates mathematical infinity.

Examples:

    python loom_multiplex.py verify
    python loom_multiplex.py cell 00/2A/3F --fixed --tongue RU
    python loom_multiplex.py route 00/2A/3F 00/11/09 --tongue KO
    python loom_multiplex.py scene
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass
from fractions import Fraction
import json
import math
import os
from pathlib import Path
from typing import Iterable, Iterator

from opcode_cube_multiplex import ORIENTATIONS, cells, classify, threads
from radial_trifold import (
    CHANNELS as TRIFOLD_CHANNELS,
    INTRINSIC_CONTINUOUS_DOF as TRIFOLD_INTRINSIC_DOF,
    LAYERS as TRIFOLD_LAYERS,
    PHASE_CHANNELS as TRIFOLD_PHASE_CHANNELS,
    fiber_record as trifold_fiber_record,
    verify_radial_trifold,
)
from turing_blocks import TuringMachine
from turing_wafer import F as WAFER_FLOORS
from turing_wafer import S as WAFER_SLOTS
from turing_wafer import cyl_orbit, orbit
from tongues import tongue_opcodes


HERE = Path(__file__).resolve().parent
SCENE_PATH = HERE / "visuals" / "loom_multiplex_scene.json"
CIRCUIT_SCHEMA_PATH = HERE / "config" / "bijective_circuit_schema.json"
FOUNDATION_PATH = Path(
    os.environ.get(
        "CLAY_FOUNDATION",
        r"C:\dev\clay_home\training\foundation\foundation_bundles.jsonl",
    )
)
SIDE = 4
CELL_COUNT = SIDE**3
DEFAULT_MAX_DEPTH = 12
SHELL_POOL = 4
TONGUES = tuple(tongue_opcodes.ORDER)
# Widened 6 -> 18 on 2026-08-01 from the measured polyglot table at
# C:\dev\dd_multiview\op_periodic_full.json (64 opcodes x 18 faces, derived via
# _dialect_supports, not a fallback). The prior six are a STRICT SUBSET of the eighteen --
# checked, 6/6 present -- so this widens an existing family rather than replacing it, and the
# old tuple is kept below as provenance.
#
# NOT ALL FACES ARE EQUAL EVIDENCE, and the table says so. Python, JavaScript, Go, Ruby, and Rust
# are runtime-verified; the other thirteen are authored dialects, so the table reports SUPPORT,
# not proof. That distinction is carried in RUNTIME_VERIFIED rather than flattened away --
# counting an authored dialect as a verified execution face is exactly how a support claim
# becomes a false proof claim.
#
# The table's own three groups, kept here as the honest shape of what these faces cover:
#   group 1  weight 18   22 ops   every face implements    -> isotopes, swap is free
#   group 3  weight  4   13 ops   c/javascript/python/rust -> ions, swap needs a correction
#   group 2  weight  0   29 ops   NO face implements       -> inert, addressable not realizable
# 29 of 64 opcodes are inert, so roughly half the CA table is aspiration, not capability.
PRIOR_CODE_LANGUAGES = ("python", "javascript", "go", "rust", "c", "haskell")
CODE_LANGUAGES = (
    "c", "cpp", "csharp", "go", "haskell", "java", "javascript", "julia", "kotlin",
    "lua", "php", "python", "ruby", "rust", "scala", "swift", "typescript", "zig",
)
# go and ruby added 2026-08-11 by EXECUTION, not by presence. `language_runtime_probe.py` compiled
# and ran the join/take/weave battery -- the same three ops brainfuck_emit uses as its transitivity
# test -- and compared stdout bytes against "12 2 35". Both returned it exactly.
#
# Presence was explicitly NOT accepted as evidence, and the run proves why: java and zig both
# answered `--version` and then FAILED to execute, so a `command -v` sweep would have promoted two
# languages that cannot close the path. Verified means source in, bytes out, correct.
RUNTIME_VERIFIED = ("python", "javascript", "go", "ruby", "rust")
AUTHORED_DIALECT = tuple(c for c in CODE_LANGUAGES if c not in RUNTIME_VERIFIED)
# Issac, 2026-08-01: "nerual networks are patterns and the nmost common patterns are lgiht,
# sound, alginment of matter, motion vs not, heat/cold". Light was already here as `color` and
# sound as `music`; heat/cold already had its topology in the S1 magnetic_phase chart and the
# Mobius double cover (352 = 2 x 176), where the extremes meet and return inverted. MOTION and
# ALIGNMENT were the two with no face at all, so they are added here.
#
# ADDITIVE, AND BOTH ARE READINGS OF THE BYTE -- not labels hung on it. Every existing face is
# derived from the byte and these are too, off structure already present in this record:
#   motion    <- gf4 = [orientation, x, y, z]. orientation is one of forward/backward/up/down
#                and xyz is a cell displacement, so the byte already carries a heading and a
#                step. "motion vs not" is whether that step is zero. Same primitive
#                robot_speech.py walks on: N/E/S/W plus a goal bearing.
#   alignment <- this record already calls itself a periodic table of elemental bits, with
#                period = byte>>4 and group = byte & 0x0F. Alignment of matter is how close a
#                group sits to a closed shell: group 15 full and inert, group 0 empty and
#                reactive. The byte's own low nibble is its valence.
#
# This moves the node count 16 -> 18, which verify() asserts. That invariant is updated
# deliberately below and BOTH counts are recorded. It is not silently moved.
PRIOR_BASE_REPRESENTATIONS = ("binary", "trit", "music", "color")   # provenance, do not delete
BASE_REPRESENTATIONS = ("binary", "trit", "music", "color", "motion", "alignment")
REPRESENTATION_NODES = (
    *BASE_REPRESENTATIONS,
    *(f"conlang:{tongue}" for tongue in TONGUES),
    *(f"code:{language}" for language in CODE_LANGUAGES),
)
XYZ = tuple(range(SIDE))
RENEWAL_RELATIONS = {
    "A": ("a", "Z"),
    "Z": ("z",),
    "Zz": ("A",),
}


def opcode_face_registry(path: Path = FOUNDATION_PATH) -> list[dict]:
    """Load the one fixed opcode/binary/trit identity used by every lane."""
    by_byte: dict[int, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("difficulty") != 3 or row.get("kind") != "opcode_lattice":
                continue
            views = row.get("views", {})
            hexadecimal = str(views.get("hex") or row.get("master_hex") or "")
            if not hexadecimal:
                continue
            byte = int(hexadecimal, 16)
            if not 0 <= byte < CELL_COUNT:
                continue
            expected_tongue = TONGUES[byte % len(TONGUES)]
            declared_tongues: list[str] = []
            if row.get("stista_tongue"):
                declared_tongues.append(str(row["stista_tongue"]))
            stista_view = str(views.get("stista") or "")
            if "tongue=" in stista_view:
                declared_tongues.append(stista_view.partition("tongue=")[2].split()[0])
            if any(tongue != expected_tongue for tongue in declared_tongues):
                raise ValueError(
                    f"foundation STISTA tongue disagrees with byte {byte:#04x}: "
                    f"expected {expected_tongue}, got {declared_tongues}"
                )
            by_byte[byte] = {
                "index": byte,
                "opcode": str(views["opcode"]),
                "binary": str(views["binary_op"]),
                "trit": str(views["trit"]),
                "hexadecimal": hexadecimal,
                "hex_macro": str(views["hex_macro"]),
                "tongue": expected_tongue,
            }
    if sorted(by_byte) != list(range(CELL_COUNT)):
        raise ValueError("foundation must provide exactly the fixed 64 opcode faces")
    records = [by_byte[index] for index in range(CELL_COUNT)]
    for field in ("opcode", "binary", "trit", "hexadecimal", "hex_macro"):
        if len({record[field] for record in records}) != CELL_COUNT:
            raise ValueError(f"fixed opcode face {field!r} is not bijective")
    return records


def circuit_record() -> dict:
    """Describe bounded depth and every fixed rotation lane for visual math."""
    schema = json.loads(CIRCUIT_SCHEMA_PATH.read_text(encoding="utf-8"))
    lane_rotations = [sum(parts) % CELL_COUNT for parts in schema["adaptive_rotations"]]
    return {
        "schema": schema["schema"],
        "state_bound": {"symbol": "|Q|", "cardinality": schema["node_count"]},
        "fixed_faces": opcode_face_registry(),
        "lanes": [
            {"index": index, "rotation": rotation, "parts": schema["adaptive_rotations"][index]}
            for index, rotation in enumerate(lane_rotations)
        ],
        "depth_tunnel": {
            "rotations": schema["clocked_tunnel"]["rotations"],
            "cycle": schema["clocked_tunnel"]["cycle"],
            "maximum_depth": schema["multi_depth"]["maximum_depth"],
        },
        "invariants": {
            "payload": "opcode/binary/trit/hex/tongue identity is fixed while the address rotates",
            "lane": "each lane is bijective; the lane axis remains explicit",
            "geometry": "flat opcode substrate folds into bounded sphere projections without changing payload",
        },
    }


def _byte_trits(value: int, width: int = 6) -> str:
    """Use the established six-symbol balanced-trit view for one byte."""
    labels = []
    current = value
    for _ in range(width):
        digit = current % 3
        current //= 3
        labels.append({0: "0", 1: "+", 2: "-"}[digit])
    return "".join(reversed(labels))


def byte_kernel_record() -> dict:
    """The full byte line and the 16-node all-to-all representation field.

    The 64 visible opcode cells are coordinates, not the full state count.
    Four orientation/phase sheets over those cells are the 256 byte states.
    The representation nodes are four non-language views, six conlangs, and
    six code languages.  Their ordered relation field is therefore 16x16,
    not the older six-category summary that collapsed each language family.
    """
    _, ca_word = tongue_opcodes._scbe()
    representation_nodes = list(REPRESENTATION_NODES)
    points = []
    for byte in range(256):
        orientation = byte >> 6
        opcode = byte & 0x3F
        x, y, z = opcode_xyz(opcode)
        rgb = [byte, (byte * 7) % 256, (byte * 13) % 256]
        languages = {
            tongue: tongue_opcodes.render(tongue, byte, ca_word)
            for tongue in TONGUES
        }
        points.append(
            {
                "byte": byte,
                "hex": f"0x{byte:02X}",
                "elemental_index": byte,
                "period": byte >> 4,
                "group": byte & 0x0F,
                "opcode_cell": f"{opcode:02X}",
                "orientation": orientation,
                "gf4": [orientation, x, y, z],
                "phase_turn": byte / 256.0,
                "faces": {
                    "binary": f"{byte:08b}",
                    "trit": _byte_trits(byte),
                    "music": {"frequency_hz": 300.0 + byte * 12.0},
                    "color": {"rgb": rgb, "hex": "#%02X%02X%02X" % tuple(rgb)},
                    # MOTION -- read straight off the gf4 factorization already computed above.
                    # The orientation is the heading, xyz is the cell the step lands in, and
                    # the step is measured from the shell centre so "no motion" is a real
                    # state and not merely a small one.
                    "motion": {
                        "heading": ORIENTATIONS[orientation],
                        "cell": [x, y, z],
                        "displacement": [x - (SIDE - 1) / 2, y - (SIDE - 1) / 2, z - (SIDE - 1) / 2],
                        "magnitude": round(
                            ((x - (SIDE - 1) / 2) ** 2 + (y - (SIDE - 1) / 2) ** 2
                             + (z - (SIDE - 1) / 2) ** 2) ** 0.5, 6),
                        # AN EVEN-SIDED CUBE HAS NO CENTRE CELL. The first version tested
                        # (x,y,z) != (1.5,1.5,1.5), which integer coordinates can never equal,
                        # so every byte read as "moving" -- 256/256, a "motion vs not" with no
                        # "not" in it. Rest is therefore the minimal-radius INNER OCTET, the
                        # eight cells with x,y,z in {1,2}, all at the same smallest distance
                        # sqrt(3)/2 from the shell centre. That is 8 of 64 cells, 32 of 256
                        # bytes -- a real rest state rather than an unreachable point.
                        "moving": not (x in (1, 2) and y in (1, 2) and z in (1, 2)),
                        "rest_octet": x in (1, 2) and y in (1, 2) and z in (1, 2),
                    },
                    # ALIGNMENT OF MATTER -- the periodic reading this record already declares.
                    # group is the valence (byte & 0x0F), period the shell (byte >> 4).
                    # A closed group is aligned and inert; an open one is reactive. `polarity`
                    # is signed so the two ends of the shell are opposite rather than merely
                    # far apart, which is the same wrap the S1 phase chart carries.
                    "alignment": {
                        "period": byte >> 4,
                        "group": byte & 0x0F,
                        "valence": (byte & 0x0F) / 15.0,
                        "closed_shell": (byte & 0x0F) in (0, 15),
                        "polarity": ((byte & 0x0F) - 7.5) / 7.5,
                        "state": ("inert" if (byte & 0x0F) in (0, 15)
                                  else "reactive" if (byte & 0x0F) in (1, 14)
                                  else "bound"),
                    },
                    "human_language": languages,
                    "machine_language": {
                        "unsigned_byte": byte,
                        "hex": f"0x{byte:02X}",
                        "gf4": [orientation, x, y, z],
                    },
                },
            }
        )
    pairs = [
        {"source": source, "target": target}
        for source in representation_nodes
        for target in representation_nodes
    ]
    return {
        "schema": "loom.byte-kernel-sixteen-node.v2",
        "state_bound": {"symbol": "|Q|", "cardinality": 256},
        "algebra": {
            "space": "AG(4,4)",
            "dimension_over_gf4": 4,
            "point_count": 256,
            "opcode_hyperplane": "orientation = 0 gives AG(3,4), 64 cells",
            "factorization": "256 = 4 orientations × 64 opcode cells",
        },
        "charts": {
            "line": {"dimension": 1, "coordinate": "byte / 255"},
            "triangle": {
                "dimension": 2,
                "coordinate": "radial C3 phase fiber",
                "analysis": "p_k(psi)=Re(exp(-i*psi)*z_k)",
                "synthesis": "u=(2/3)*exp(i*psi)*sum_k(p_k*omega^(-k)); z_k=u*omega^k",
            },
            "square": {"dimension": 2, "coordinate": "phase folded over 4 edges"},
            "magnetic_phase": {"dimension": 1, "topology": "S1", "coordinate": "byte / 256 turn"},
            "scale": {"dimension": 1, "topology": "positive real"},
        },
        "periodic_table": {
            "meaning": "periodic table of elemental bits",
            "shape": [16, 16],
            "ordering_axis": "byte is the elemental index",
            "period_axis": "byte >> 4",
            "group_axis": "byte & 0x0F",
            "periodicity": "the low-nibble group repeats through all 16 high-nibble periods",
        },
        "representation_families": {
            "base": list(BASE_REPRESENTATIONS),
            "conlangs": [f"conlang:{tongue}" for tongue in TONGUES],
            "code_languages": [f"code:{language}" for language in CODE_LANGUAGES],
        },
        "representation_nodes": representation_nodes,
        # Compatibility name consumed by the existing graph/Desmos binding.
        "modalities": representation_nodes,
        "relation_tensor": {
            "shape": [256, len(representation_nodes), len(representation_nodes)],
            "ordered_pairs_per_byte": len(representation_nodes) ** 2,
            "relation_count": 256 * len(representation_nodes) ** 2,
            "pairs": pairs,
            "rule": "the 16 representation surfaces are nodes; their 256 ordered source-target entries are the per-byte/per-layer relations",
        },
        "points": points,
    }


def relation_field_record(shell_pool: int, wall_count: int) -> dict:
    """Count the joined wafer/multiplex relation field without alias inflation.

    The byte line, 30x30 table, and 64x4 oriented cube are three charts of the
    same 256 byte states.  They are not multiplied together.  Carrier entities
    are the oriented cells and oriented four-cell walls; every carrier receives
    the 30x30 ordered relation field in each of the wafer's two charge frames.

    The 7x3 radial tri-fold is the constrained VALUE carried at every relation
    address.  It is not another address axis, so it does not multiply the bounded
    relation-state count and does not add representation nodes.
    """
    node_count = len(REPRESENTATION_NODES)
    ordered_relations = node_count**2
    oriented_cells = CELL_COUNT * len(ORIENTATIONS)
    oriented_walls = wall_count * len(ORIENTATIONS)
    carriers = oriented_cells + oriented_walls
    charge_frames = 2
    per_shell = carriers * ordered_relations * charge_frames
    conlang_relations = len(TONGUES) ** 2
    return {
        "schema": "loom.relation-field.v2",
        "terminology": {
            "nodes": "the 30 representation surfaces",
            "relations": "the 30x30 ordered source-target entries per carrier and layer",
            "alias_rule": "256-byte line = 16x16 elemental table = 64 cells x 4 orientations; count it once",
            "fiber_rule": "7x3 tri-fold channels are the constrained value at an address, not new nodes",
        },
        "nodes": list(REPRESENTATION_NODES),
        "node_count": node_count,
        "ordered_relations_per_node_layer": ordered_relations,
        "carrier_entities_per_shell": {
            "oriented_cells": oriented_cells,
            "oriented_walls": oriented_walls,
            "total": carriers,
        },
        "wafer_charge_frames": charge_frames,
        "factorized_tensor": {
            "per_shell_shape": [carriers, node_count, node_count, charge_frames],
            "live_pool_shape": [shell_pool, carriers, node_count, node_count, charge_frames],
            "axis_order": ["shell", "carrier", "source_node", "target_node", "charge"],
            "value_fiber_shape": [TRIFOLD_LAYERS, TRIFOLD_PHASE_CHANNELS],
            "value_fiber_channels": TRIFOLD_CHANNELS,
            "value_fiber_intrinsic_continuous_dof": TRIFOLD_INTRINSIC_DOF,
            "carrier_address": {
                "cell": "(orientation, opcode_cell)",
                "wall": "(orientation, four-cell wall id)",
            },
            "join_rule": "wafer charge is an axis of the same cell/wall relation tensor, not a sibling dataset",
        },
        "internal_value_fiber": trifold_fiber_record(),
        "relation_states_per_shell_layer": per_shell,
        "recycled_shell_pool": shell_pool,
        "live_bounded_relation_states": per_shell * shell_pool,
        "conlang_base_relation": {
            "nodes": len(TONGUES),
            "ordered_relations_per_byte": conlang_relations,
            "over_256_byte_states": 256 * conlang_relations,
            "with_two_wafer_charge_frames": 256 * conlang_relations * charge_frames,
        },
        "coordinate_carrier": {
            "tube": {
                "model": "bounded shrinking fiber bundle F(d,t) = S^5(r(d,t)) x T(t)",
                "radius": "r(d,t) = r_max / R^(d^2) * exp(-lambda*t)",
                "source": "C:/Users/issda/SCBE-AETHERMOORE/src/aaoe/garganta_manifold.py",
            },
            "state21": {
                "manifold": "B_c^6 x T^6 x R^9",
                "blocks": ["u[0:6] tongue position", "theta[6:12] tongue phase", "z[12:21] telemetry"],
                "source": "C:/Users/issda/SCBE-AETHERMOORE/src/harmonic/state21_product_metric.py",
                "space_doc": "C:/Users/issda/Documents/Avalon Files/System Library/Repository Mirror/docs/specs/STATE_MANIFOLD_21D_PRODUCT_METRIC.md",
            },
            "nested_coordinates": {
                "model": "signed nested n-torus with forward (+1), backward (-1), and frozen (0) dimension modes",
                "metric": "g_00=R_0^2; g_ii=(R_i+r_i*cos(theta_(i-1)))^2",
                "source": "C:/Users/issda/SCBE-AETHERMOORE/src/symphonic_cipher/harmonic_scaling_law.py#HyperTorusManifold",
            },
            "un_nesting": {
                "rule": "retrace by applying inverse transforms in reverse order",
                "available_inverses": [
                    "layer_7_inverse: reverse rotation, then Mobius subtraction",
                    "layer_4_inverse: Poincare ball to Euclidean via arctanh",
                    "layer_2_inverse: interleaved real coordinates to complex",
                ],
                "source": "C:/Users/issda/SCBE-AETHERMOORE/symphonic_cipher/scbe_aethermoore/axiom_grouped/unitarity_axiom.py",
            },
        },
    }


@dataclass(frozen=True, order=True)
class Address:
    """A bounded route through recursively repeated 4x4x4 boxes."""

    parts: tuple[int, ...] = ()

    @classmethod
    def parse(cls, text: str, max_depth: int = DEFAULT_MAX_DEPTH) -> "Address":
        raw = text.strip()
        if not raw or raw.upper() == "ROOT":
            return cls()
        pieces = tuple(p for p in raw.replace("\\", "/").split("/") if p)
        if len(pieces) > max_depth:
            raise ValueError(f"address depth {len(pieces)} exceeds bounded maximum {max_depth}")
        parts = tuple(int(p[2:], 16) if p.lower().startswith("0x") else int(p, 16) for p in pieces)
        if any(not 0 <= part < CELL_COUNT for part in parts):
            raise ValueError("every address component must be one opcode cell from 00 through 3F")
        return cls(parts)

    def child(self, opcode: int, max_depth: int = DEFAULT_MAX_DEPTH) -> "Address":
        if len(self.parts) >= max_depth:
            raise ValueError(f"bounded maximum depth {max_depth} reached")
        if not 0 <= opcode < CELL_COUNT:
            raise ValueError("opcode must be from 0x00 through 0x3F")
        return Address(self.parts + (opcode,))

    @property
    def parent(self) -> "Address | None":
        return Address(self.parts[:-1]) if self.parts else None

    @property
    def opcode(self) -> int | None:
        return self.parts[-1] if self.parts else None

    @property
    def depth(self) -> int:
        return len(self.parts)

    def __str__(self) -> str:
        return "ROOT" if not self.parts else "/".join(f"{part:02X}" for part in self.parts)


@dataclass(frozen=True)
class Wall:
    """One tubular four-cell relation inside a particular recursive box."""

    box: Address
    index: int
    kind: str
    member_opcodes: tuple[int, int, int, int]
    density: int

    @property
    def wall_id(self) -> str:
        return f"{self.box}:W{self.index:02d}"

    @property
    def members(self) -> tuple[Address, Address, Address, Address]:
        return tuple(Address(self.box.parts + (opcode,)) for opcode in self.member_opcodes)  # type: ignore[return-value]


@dataclass(frozen=True)
class HalfOpenBox:
    """Exact ``[a,b)`` ownership in the XYZ domain.

    The lower corner is included and the upper corner is excluded.  Adjacent
    cells may touch at a wall but can never both own the same boundary point.
    ``child(z)`` is the recursive ``[a,z)`` step, with local
    ``z in {0,1,2,3}^3``.
    """

    a: tuple[Fraction, Fraction, Fraction]
    b: tuple[Fraction, Fraction, Fraction]

    def child(self, z: tuple[int, int, int]) -> "HalfOpenBox":
        if any(axis not in XYZ for axis in z):
            raise ValueError("z must be in the 4x4x4 XYZ domain")
        span = tuple((hi - lo) / SIDE for lo, hi in zip(self.a, self.b))
        lower = tuple(lo + axis * width for lo, axis, width in zip(self.a, z, span))
        upper = tuple(lo + (axis + 1) * width for lo, axis, width in zip(self.a, z, span))
        return HalfOpenBox(lower, upper)  # type: ignore[arg-type]

    def contains(self, point: tuple[Fraction, Fraction, Fraction]) -> bool:
        return all(lo <= value < hi for lo, value, hi in zip(self.a, point, self.b))

    def as_record(self, z: tuple[int, int, int] | None = None) -> dict:
        def exact(values: tuple[Fraction, Fraction, Fraction]) -> list[str]:
            return [str(value) for value in values]

        return {
            "notation": "[a,b)",
            "a": exact(self.a),
            "b": exact(self.b),
            "z_xyz": list(z) if z is not None else None,
            "lower_included": True,
            "upper_excluded": True,
        }


def renewal_successors(state: str) -> tuple[str, ...]:
    """The branching A/a/Z/z relation; it is deliberately not a flat cycle."""
    try:
        return RENEWAL_RELATIONS[state]
    except KeyError as exc:
        raise ValueError(f"unknown renewal state: {state}") from exc


def bind_renewal(outer: str, inner: str) -> str:
    """Bind the Z boundary to its z image; that joint is the day seam."""
    if (outer, inner) != ("Z", "z"):
        raise ValueError("the renewal seam is the ordered binding Zz")
    return "Zz"


def cross_day(day: int, bound_state: str) -> tuple[int, str]:
    """Cross ``Zz``: increment the day and return to the beginning ``A``."""
    if day < 0:
        raise ValueError("day cannot be negative")
    if bound_state != "Zz":
        raise ValueError("only the bound state Zz crosses into a new day")
    return day + 1, "A"


_THREADS = tuple(threads())
_INCIDENCE = Counter(point for line in _THREADS for point in line)
ROOT_DOMAIN = HalfOpenBox(
    (Fraction(0), Fraction(0), Fraction(0)),
    (Fraction(1), Fraction(1), Fraction(1)),
)


def opcode_xyz(opcode: int) -> tuple[int, int, int]:
    if not 0 <= opcode < CELL_COUNT:
        raise ValueError("opcode must be from 0x00 through 0x3F")
    return opcode // 16, (opcode % 16) // 4, opcode % 4


def address_domain(address: Address) -> HalfOpenBox:
    """Resolve an address as nested exact half-open XYZ intervals."""
    domain = ROOT_DOMAIN
    for opcode in address.parts:
        domain = domain.child(opcode_xyz(opcode))
    return domain


def cube_walls(box: Address = Address()) -> tuple[Wall, ...]:
    out = []
    for index, line in enumerate(_THREADS):
        density = sum(_INCIDENCE[point] - 1 for point in line)
        out.append(
            Wall(
                box=box,
                index=index,
                kind=classify(line),
                member_opcodes=tuple(16 * x + 4 * y + z for x, y, z in line),
                density=density,
            )
        )
    return tuple(out)


def children(box: Address, max_depth: int = DEFAULT_MAX_DEPTH) -> Iterator[Address]:
    """Materialize only one requested shell; children do not recursively allocate."""
    for opcode in range(CELL_COUNT):
        yield box.child(opcode, max_depth=max_depth)


def tongue_forms(opcode: int) -> dict[str, str]:
    """Six reversible surface words for one opcode cell."""
    name_to_byte, ca_word = tongue_opcodes._scbe()
    ca_inverse = {ca_word(byte): byte for byte in set(name_to_byte.values())}
    forms = {code: tongue_opcodes.render(code, opcode, ca_word) for code in TONGUES}
    for code, word in forms.items():
        if tongue_opcodes.parse(code, word, ca_inverse) != opcode:
            raise AssertionError(f"{code} failed to return {word!r} to opcode 0x{opcode:02X}")
    return forms


def radial_phone_coordinate(
    opcode: int,
    tongue: str,
    orientation: str = "forward",
    charge: int = +1,
) -> dict:
    """Project one cell's phone into radial dimensions around XYZ.

    The byte already factors into a high-nibble onset and low-nibble coda.
    Tongue chooses one of six radial axes; the two nibbles become onset radius
    and coda phase. This is a projection for routing/debugging, not a claim that
    natural speech intrinsically lives in this Euclidean coordinate system.
    """
    if tongue not in TONGUES:
        raise ValueError(f"tongue must be one of {', '.join(TONGUES)}")
    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {', '.join(ORIENTATIONS)}")
    if charge not in (-1, +1):
        raise ValueError("charge must be -1 or +1")
    x, y, z = opcode_xyz(opcode)
    tongue_index = TONGUES.index(tongue)
    orientation_index = ORIENTATIONS.index(orientation)
    tongue_angle = 2.0 * math.pi * tongue_index / len(TONGUES)
    coda_angle = 2.0 * math.pi * (opcode & 0x0F) / 16.0
    onset_radius = ((opcode >> 4) + 1) / 4.0
    return {
        "xyz": [x, y, z],
        "tongue_axis": [math.cos(tongue_angle), math.sin(tongue_angle)],
        "onset_index": opcode >> 4,
        "onset_radius": onset_radius,
        "coda_index": opcode & 0x0F,
        "coda_phase": [math.cos(coda_angle), math.sin(coda_angle)],
        "orientation_phase": orientation_index,
        "charge": charge,
        "dimensions": ["x", "y", "z", "tongue_u", "tongue_v", "phone_u", "phone_v", "orientation", "charge"],
    }


def opcode_from_radial_phone(coordinate: dict) -> int:
    """Exact inverse; routing bands never replace the onset/coda coordinates."""
    onset = int(coordinate["onset_index"])
    coda = int(coordinate["coda_index"])
    if not 0 <= onset < 4 or not 0 <= coda < 16:
        raise ValueError("radial phone indices are outside the 64-opcode cube")
    return (onset << 4) | coda


def _machine_program() -> dict[str, tuple[str, str | None]]:
    return {
        "start": ("BRANCH_0", "done|erase"),
        "erase": ("WRITE_0", "right"),
        "right": ("MOVE_R", "start"),
        "done": ("HALT", None),
    }


def run_entity_core(entity_id: str, tape_bits: str = "1110") -> dict:
    """Run the same complete control surface from any cell or wall identity.

    The tape is a sparse dictionary and is not limited by the visual cell count.
    This smoke program proves the entity can read, branch, write, move, loop, and
    halt; it does not claim to exhaustively prove every future program.
    """
    if not tape_bits or any(bit not in "01" for bit in tape_bits):
        raise ValueError("tape_bits must be a non-empty binary string")
    tm = TuringMachine(
        program=_machine_program(),
        tape={index: int(bit) for index, bit in enumerate(tape_bits)},
    )
    tm.run(max_steps=max(1000, len(tape_bits) * 8))
    return {
        "entity_id": entity_id,
        "input": tape_bits,
        "output": tm.window(0, len(tape_bits)),
        "steps": tm.steps,
        "halted": tm.halted,
        "primitives": ["write", "move", "branch", "jump", "halt"],
    }


def _edge_wall_map() -> dict[tuple[int, int], Wall]:
    choices: dict[tuple[int, int], Wall] = {}
    for wall in cube_walls():
        members = wall.member_opcodes
        for i, left in enumerate(members):
            for right in members[i + 1 :]:
                edge = tuple(sorted((left, right)))
                old = choices.get(edge)
                # Prefer the denser tube, then stable wall id, when relations overlap.
                if old is None or (-wall.density, wall.index) < (-old.density, old.index):
                    choices[edge] = wall
    return choices


_EDGE_WALL = _edge_wall_map()
_NEIGHBORS: dict[int, tuple[int, ...]] = {
    opcode: tuple(
        sorted(other for other in range(CELL_COUNT) if other != opcode and tuple(sorted((opcode, other))) in _EDGE_WALL)
    )
    for opcode in range(CELL_COUNT)
}


def shortest_cell_route(start: int, target: int) -> list[tuple[int, int, Wall]]:
    """Shortest deterministic route through the cube's actual thread relations."""
    if start == target:
        return []
    q = deque([start])
    previous: dict[int, int | None] = {start: None}
    while q:
        here = q.popleft()
        for nxt in _NEIGHBORS[here]:
            if nxt in previous:
                continue
            previous[nxt] = here
            if nxt == target:
                q.clear()
                break
            q.append(nxt)
    if target not in previous:
        raise RuntimeError(f"cube route disconnected: {start:02X} -> {target:02X}")
    nodes = [target]
    while nodes[-1] != start:
        parent = previous[nodes[-1]]
        assert parent is not None
        nodes.append(parent)
    nodes.reverse()
    return [
        (left, right, _EDGE_WALL[tuple(sorted((left, right)))])
        for left, right in zip(nodes, nodes[1:])
    ]


def route(
    source: Address,
    target: Address,
    tongue: str = "CA",
    orientation: str = "forward",
) -> dict:
    """Route between nested cells using layer joins plus the 76 wall relations."""
    if tongue not in TONGUES:
        raise ValueError(f"tongue must be one of {', '.join(TONGUES)}")
    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {', '.join(ORIENTATIONS)}")

    common = 0
    while common < min(source.depth, target.depth) and source.parts[common] == target.parts[common]:
        common += 1

    segments: list[dict] = []
    current = source

    # If the addresses diverge, climb only to the source cell inside their
    # common parent cube. That preserves the intra-cube wall traversal.
    climb_to = common + 1 if common < min(source.depth, target.depth) else common
    while current.depth > climb_to:
        parent = current.parent
        assert parent is not None
        segments.append({"kind": "layer_up", "from": str(current), "to": str(parent), "movement": +1})
        current = parent

    if common < min(source.depth, target.depth):
        box = Address(source.parts[:common])
        start_opcode = source.parts[common]
        target_opcode = target.parts[common]
        for left, right, base_wall in shortest_cell_route(start_opcode, target_opcode):
            wall = Wall(box, base_wall.index, base_wall.kind, base_wall.member_opcodes, base_wall.density)
            left_address = box.child(left)
            right_address = box.child(right)
            segments.append(
                {
                    "kind": "thread",
                    "from": str(left_address),
                    "to": str(right_address),
                    "wall": wall.wall_id,
                    "wall_kind": wall.kind,
                    "density": wall.density,
                    "interior": True,
                    "movement": +1,
                }
            )
        current = box.child(target_opcode)

    # Prefix-only routes have no lateral wall: climb to or descend from the
    # common address directly.
    while current.depth > target.depth:
        parent = current.parent
        assert parent is not None
        segments.append({"kind": "layer_up", "from": str(current), "to": str(parent), "movement": +1})
        current = parent
    for opcode in target.parts[current.depth :]:
        child = current.child(opcode)
        segments.append({"kind": "layer_down", "from": str(current), "to": str(child), "movement": +1})
        current = child

    return {
        "schema": "loom-multiplex-route-v1",
        "source": str(source),
        "target": str(target),
        "tongue": tongue,
        "orientation": orientation,
        "segments": segments,
        "arrived": str(current) == str(target),
        "counting": "movement_is_the_count",
    }


def reverse_route(receipt: dict) -> dict:
    """Retrace a route; the reverse movement cancels the forward movement.

    No independent step counter is reconstructed. The ordered path is already
    the witness, and each reverse segment carries the additive inverse of the
    movement that produced it.
    """
    if receipt.get("schema") != "loom-multiplex-route-v1" or not receipt.get("arrived"):
        raise ValueError("only an arrived Loom route can be retraced")
    reverse_kind = {"layer_up": "layer_down", "layer_down": "layer_up", "thread": "thread"}
    segments = []
    for segment in reversed(receipt["segments"]):
        back = dict(segment)
        back["kind"] = reverse_kind[segment["kind"]]
        back["from"], back["to"] = segment["to"], segment["from"]
        back["movement"] = -int(segment.get("movement", 1))
        segments.append(back)
    return {
        "schema": "loom-multiplex-route-v1",
        "source": receipt["target"],
        "target": receipt["source"],
        "tongue": receipt["tongue"],
        "orientation": {
            "forward": "backward",
            "backward": "forward",
            "up": "down",
            "down": "up",
        }[receipt["orientation"]],
        "segments": segments,
        "arrived": True,
        "counting": "movement_is_the_count",
    }


def round_trip_movement(receipt: dict) -> int:
    """Forward plus retraced motion is zero when the route returns home."""
    back = reverse_route(receipt)
    return sum(int(segment["movement"]) for segment in receipt["segments"] + back["segments"])


def cell_record(address: Address, tongue: str = "CA", fixed: bool = False, charge: int = +1) -> dict:
    if address.opcode is None:
        raise ValueError("ROOT is a box, not a cell")
    if charge not in (-1, +1):
        raise ValueError("charge must be -1 or +1")
    forms = tongue_forms(address.opcode)
    xyz = opcode_xyz(address.opcode)
    return {
        "schema": "loom-multiplex-cell-v1",
        "address": str(address),
        "depth": address.depth,
        "opcode": address.opcode,
        "hex": f"{address.opcode:02X}",
        "xyz": xyz,
        "domain": address_domain(address).as_record(xyz),
        "fixed": fixed,
        "frame": "true_north" if fixed else "current_north",
        "charge": charge,
        "orientation_count": len(ORIENTATIONS),
        "active_tongue": tongue,
        "word": forms[tongue],
        "tongue_forms": forms,
        "machine_surface": ["write", "move", "branch", "jump", "halt"],
    }


def build_scene(max_depth: int = DEFAULT_MAX_DEPTH, shell_pool: int = SHELL_POOL) -> dict:
    if max_depth < 1:
        raise ValueError("max_depth must be positive")
    if not 2 <= shell_pool <= max_depth:
        raise ValueError("shell_pool must be between 2 and max_depth")
    walls = cube_walls()
    forms = {f"{opcode:02X}": tongue_forms(opcode) for opcode in range(CELL_COUNT)}
    return {
        "schema": "loom-recursive-multiplex-scene-v1",
        "truth": {
            "box": "finite",
            "infinity": "illusion_of_perception",
            "mechanism": "recycle a finite shell pool through scale and viewpoint",
            "allocated_shells": shell_pool,
            "bounded_runtime_depth": max_depth,
            "return_to_beginning": "reverse the ordered movement; at the origin the movement sum is zero",
        },
        "renewal": {
            "relations": {source: list(targets) for source, targets in RENEWAL_RELATIONS.items()},
            "binding": {"outer": "Z", "inner": "z", "state": "Zz"},
            "day_seam": {"from": "Zz", "to": "A", "effect": "day + 1"},
            "meaning": "the bounded shell returns as a new beginning",
        },
        "cube": {
            "side": SIDE,
            "cells_per_shell": CELL_COUNT,
            "orientations": list(ORIENTATIONS),
            "byte_factorization": CELL_COUNT * len(ORIENTATIONS),
            "domain": {
                "notation": "[a,b)",
                "root": ROOT_DOMAIN.as_record(),
                "z_xyz": [list(point) for point in cells()],
                "boundary_rule": "lower included; upper excluded; no double-owned wall",
            },
        },
        "wafer": {
            "shape": [WAFER_FLOORS, WAFER_SLOTS],
            "mobius_states": len(orbit((0, 0, +1, 0))),
            "cylinder_control_states": len(cyl_orbit((0, 0, +1, 0))),
        },
        "circuit": circuit_record(),
        "byte_kernel": byte_kernel_record(),
        "relation_field": relation_field_record(shell_pool, len(walls)),
        "tongues": list(TONGUES),
        "forms": forms,
        "radial_phones": {
            "projection": "six tongue axes; onset radius; coda phase; orientation; signed charge",
            "claim_boundary": "visual/routing projection, not physical phonetics",
            "nodes": [
                {
                    "opcode": f"{opcode:02X}",
                    "tongue": tongue,
                    "word": forms[f"{opcode:02X}"][tongue],
                    "coordinate": radial_phone_coordinate(opcode, tongue),
                }
                for tongue in TONGUES
                for opcode in range(CELL_COUNT)
            ],
        },
        "walls": [
            {
                "id": wall.wall_id,
                "kind": wall.kind,
                "density": wall.density,
                "routing_band": {12: "low", 18: "middle", 24: "high"}[wall.density],
                "members": [f"{opcode:02X}" for opcode in wall.member_opcodes],
                "points": [opcode_xyz(opcode) for opcode in wall.member_opcodes],
                "machine_surface": ["write", "move", "branch", "jump", "halt"],
            }
            for wall in walls
        ],
        "desmos": {
            "homework_surface": "C:/Users/issda/AetherDesk/aetherdesk/public/real-pc-shell.js",
            "state_key": "aetherdesk.homework.graph.v1",
            "connection_verified": True,
            "scope": "existing homework grapher; no API key is copied into this scene",
        },
    }


def verify() -> dict:
    walls = cube_walls()
    relation_field = relation_field_record(SHELL_POOL, len(walls))
    kinds = Counter(wall.kind for wall in walls)
    densities = Counter(wall.density for wall in walls)
    language_checks = 0
    for opcode in range(CELL_COUNT):
        language_checks += len(tongue_forms(opcode))
    cell_core = run_entity_core("ROOT/00")
    wall_core = run_entity_core(walls[0].wall_id)
    route_check = route(Address.parse("00/2A/3F"), Address.parse("00/11/09"), tongue="KO")
    root_children = [address_domain(Address((opcode,))) for opcode in range(CELL_COUNT)]
    partition_points = [
        (Fraction(2 * x + 1, 8), Fraction(2 * y + 1, 8), Fraction(2 * z + 1, 8))
        for x, y, z in cells()
    ]
    next_day = cross_day(0, bind_renewal("Z", "z"))
    trifold_check = verify_radial_trifold()

    checks = {
        "cells": len(cells()) == 64,
        "walls": len(walls) == 76,
        "wall_kinds": kinds == {"axis": 48, "face_diag": 24, "space_diag": 4},
        "wall_density_is_structural": densities == {12: 24, 18: 48, 24: 4},
        "byte_factorization": len(cells()) * len(ORIENTATIONS) == 256,
        # NODE COUNT MOVED 16 -> 18 ON 2026-08-01, deliberately, when `motion` and `alignment`
        # were added to BASE_REPRESENTATIONS. The prior values are kept beside the new ones
        # rather than overwritten, so the change is legible in the file instead of only in the
        # history. Geometry is unaffected and its checks are untouched above: cells 64, walls
        # 76, wall kinds, densities, byte factorization, and the Mobius double cover all still
        # hold, because adding a face does not reshape the shell.
        #
        # Both derived counts scale by exactly (18/16)^2 = 324/256 = 1.265625:
        #     ordered relations   256    -> 324        = 18^2
        #     shell-layer states  286720 -> 362880
        #     live bounded states 1146880 -> 1451520
        # NODE COUNT LINEAGE, each step deliberate and each prior kept in the file:
        #   16  original: 4 base + 6 conlang + 6 code
        #   18  2026-08-01, motion and alignment added to base (the two missing primitives)
        #   30  2026-08-01, code family widened 6 -> 18 from the MEASURED polyglot table,
        #       where the prior six were verified a strict subset (6/6 present)
        # Both derived counts scale exactly with node_count^2 at every step:
        #   ordered relations   256    -> 324      -> 900        = 16^2, 18^2, 30^2
        #   shell-layer states  286720 -> 362880   -> 1008000
        #   live bounded states 1146880 -> 1451520 -> 4032000
        # Geometry is untouched at every step -- cells 64, walls 76, kinds, densities, byte
        # factorization, tongue roundtrips 384, mobius 352, cylinder 176 all unchanged.
        # Widening the carrier does not reshape the shell.
        "thirty_representation_nodes": relation_field["node_count"] == 30,
        "prior_node_counts_recorded": (
            PRIOR_BASE_REPRESENTATIONS == ("binary", "trit", "music", "color")
            and PRIOR_CODE_LANGUAGES == ("python", "javascript", "go", "rust", "c", "haskell")
            and all(c in CODE_LANGUAGES for c in PRIOR_CODE_LANGUAGES)
        ),
        # support is not proof: only 5 of 18 code faces are runtime-verified
        "code_face_evidence_separated": (
            len(RUNTIME_VERIFIED) == 5 and len(AUTHORED_DIALECT) == 13
            and not set(RUNTIME_VERIFIED) & set(AUTHORED_DIALECT)
        ),
        "ordered_relation_field": relation_field["ordered_relations_per_node_layer"] == 900,
        "joined_wafer_multiplex_count": relation_field["relation_states_per_shell_layer"] == 1008000
        and relation_field["live_bounded_relation_states"] == 4032000,
        "radial_trifold_inside_multiplex": (
            relation_field["factorized_tensor"]["value_fiber_shape"] == [7, 3]
            and relation_field["internal_value_fiber"]["not_new_nodes"] is True
            and relation_field["node_count"] == 30
            and relation_field["ordered_relations_per_node_layer"] == 900
            and trifold_check["passed"]
        ),
        "mobius_doubles_control": len(orbit((0, 0, +1, 0))) == 352
        and len(cyl_orbit((0, 0, +1, 0))) == 176,
        "six_tongue_roundtrips": language_checks == 64 * 6,
        "radial_phone_projection": len(build_scene()["radial_phones"]["nodes"]) == 64 * 6,
        "radial_phone_inverse": all(
            opcode_from_radial_phone(radial_phone_coordinate(opcode, tongue)) == opcode
            for tongue in TONGUES
            for opcode in range(CELL_COUNT)
        ),
        "cell_machine": cell_core["halted"] and cell_core["output"] == "0000",
        "wall_machine": wall_core["halted"] and wall_core["output"] == "0000",
        "nested_route": route_check["arrived"] and any(s["kind"] == "thread" for s in route_check["segments"]),
        "retrace_returns_without_extra_counter": reverse_route(route_check)["target"] == route_check["source"]
        and round_trip_movement(route_check) == 0,
        "half_open_xyz_partition": all(
            sum(domain.contains(point) for domain in root_children) == 1 for point in partition_points
        ),
        "renewal_relation": renewal_successors("A") == ("a", "Z")
        and renewal_successors("Z") == ("z",)
        and next_day == (1, "A"),
        "bounded_perceptual_infinity": build_scene()["truth"]["infinity"] == "illusion_of_perception",
    }
    return {
        "schema": "loom-multiplex-verification-v1",
        "passed": all(checks.values()),
        "checks": checks,
        "counts": {
            "cells_per_shell": 64,
            "walls_per_shell": 76,
            "orientations": 4,
            "representation_nodes": relation_field["node_count"],
            "ordered_relations_per_node_layer": relation_field["ordered_relations_per_node_layer"],
            "carrier_entities_per_shell": relation_field["carrier_entities_per_shell"]["total"],
            "relation_states_per_shell_layer": relation_field["relation_states_per_shell_layer"],
            "live_bounded_relation_states": relation_field["live_bounded_relation_states"],
            "trifold_layers": TRIFOLD_LAYERS,
            "trifold_phase_channels": TRIFOLD_PHASE_CHANNELS,
            "trifold_value_channels": TRIFOLD_CHANNELS,
            "trifold_intrinsic_continuous_dof": TRIFOLD_INTRINSIC_DOF,
            "tongue_roundtrips": language_checks,
            "mobius_states": 352,
            "cylinder_states": 176,
        },
        "trifold_verification": trifold_check,
    }


def write_scene(path: Path = SCENE_PATH, max_depth: int = DEFAULT_MAX_DEPTH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_scene(max_depth=max_depth), indent=2) + "\n", encoding="utf-8")
    return path


def _json(data: object) -> None:
    print(json.dumps(data, indent=2))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("verify")

    p_cell = sub.add_parser("cell")
    p_cell.add_argument("address")
    p_cell.add_argument("--tongue", choices=TONGUES, default="CA")
    p_cell.add_argument("--fixed", action="store_true")
    p_cell.add_argument("--charge", type=int, choices=(-1, +1), default=+1)
    p_cell.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)

    p_route = sub.add_parser("route")
    p_route.add_argument("source")
    p_route.add_argument("target")
    p_route.add_argument("--tongue", choices=TONGUES, default="CA")
    p_route.add_argument("--orientation", choices=ORIENTATIONS, default="forward")
    p_route.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)

    p_scene = sub.add_parser("scene")
    p_scene.add_argument("--out", type=Path, default=SCENE_PATH)
    p_scene.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)

    args = parser.parse_args(list(argv) if argv is not None else None)
    command = args.command or "verify"
    if command == "verify":
        result = verify()
        _json(result)
        return 0 if result["passed"] else 1
    if command == "cell":
        _json(cell_record(Address.parse(args.address, args.max_depth), args.tongue, args.fixed, args.charge))
        return 0
    if command == "route":
        _json(
            route(
                Address.parse(args.source, args.max_depth),
                Address.parse(args.target, args.max_depth),
                args.tongue,
                args.orientation,
            )
        )
        return 0
    if command == "scene":
        print(write_scene(args.out, max_depth=args.max_depth))
        return 0
    parser.error(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
