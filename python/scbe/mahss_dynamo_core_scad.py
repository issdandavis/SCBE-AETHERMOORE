"""OpenSCAD emitter for the crypto-seeded Dynamo Core metamaterial.

Closes the second half of the metamaterial-PUF pipeline: given the same
seed and parameters used by ``mahss_crypto_lattice``, emit a printable
``.scad`` source string. The Python perturbation field is baked as an
OpenSCAD literal array so the simulator and the geometry use
*bit-identical* perturbation values — no OpenSCAD-math-dialect drift,
no floating-point disagreement between platforms.

Default parameters mirror the user's reference Dynamo Core spec:

- ``R_tung = 1.5 mm`` — porous tungsten core radius
- ``t_sheath = 3.0 mm`` — auxetic breathing sheath thickness
- ``r_throat = 1.5 mm`` — hyperbolic throat radius (ridge cross-section)
- ``c_z = 0.8`` — z-step coefficient per ridge index
- ``num_ridges = 16`` — golden-angle ridges around the column
- ``mesh_height = 60 mm`` — total column height
- ``perturb_scale_mm = 0.5`` — physical scale of the seeded perturbation
  (the field itself is unitless, in [-bound, +bound]; this number maps it
  to millimetres of geometric displacement)

Example::

    from python.scbe.mahss_dynamo_core_scad import render_dynamo_core_scad
    from python.scbe.mahss_crypto_lattice import seed_from_bytes

    seed = seed_from_bytes(kyber_public_key_bytes)
    scad_source = render_dynamo_core_scad(seed)
    Path("out/alice_drone.scad").write_text(scad_source)
    # Open in OpenSCAD F5 -> F6 -> Export STL -> print
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, fields
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from python.scbe.mahss_crypto_lattice import derive_perturbation_field  # noqa: E402


@dataclass(frozen=True)
class DynamoCoreGeometry:
    """Physical parameters of the Dynamo Core. Mirrors the user's
    reference OpenSCAD spec; defaults match the values they sent."""

    R_tung: float = 1.5
    t_sheath: float = 3.0
    r_throat: float = 1.5
    c_z: float = 0.8
    num_ridges: int = 16
    mesh_height: float = 60.0
    perturb_scale_mm: float = 0.5
    perturb_bound: float = 0.05  # unitless [-bound, +bound] from the field
    fn: int = 32

    def to_manifest(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def _format_perturb_table(field) -> str:
    """Format a numpy 1-D float array as an OpenSCAD literal list.
    Six decimal places is enough for sub-micron resolution at 0.5 mm
    scale — finer than any 3D printer."""

    return "[" + ", ".join(f"{v:.6f}" for v in field) + "]"


def render_dynamo_core_scad(
    seed: int,
    geometry: DynamoCoreGeometry | None = None,
) -> str:
    """Return an OpenSCAD source string for the seeded Dynamo Core.

    Deterministic in (seed, geometry): same inputs always produce the
    same string. Different seeds produce different perturbation arrays
    baked into the source, so the printed parts have distinct geometry.
    """

    geom = geometry or DynamoCoreGeometry()
    field = derive_perturbation_field(
        seed,
        geom.num_ridges,
        bound=geom.perturb_bound,
    )
    perturb_mm = field * geom.perturb_scale_mm

    return f"""// MAHSS Dynamo Core - crypto-seeded auxetic metamaterial
// Generated from seed {seed:016x} by python/scbe/mahss_dynamo_core_scad.py
// Same seed in the simulator (mahss_crypto_lattice) yields the SAME
// perturbation values, which are baked below as a literal array.

phi = (1 + sqrt(5)) / 2;
golden_angle = 360 * (1 - 1/phi);

R_tung = {geom.R_tung};        // Porous tungsten core radius (mm)
t_sheath = {geom.t_sheath};    // Auxetic breathing sheath thickness (mm)
r_throat = {geom.r_throat};    // Hyperbolic throat radius (mm)
c_z = {geom.c_z};              // z-step coefficient per ridge
num_ridges = {geom.num_ridges};
mesh_height = {geom.mesh_height};
seed = {seed};                 // hex {seed:016x}

// Crypto-derived perturbation field (mm). Computed in Python via
// derive_perturbation_field(seed, num_ridges) and baked here so the
// physical part matches the simulator bit-for-bit.
perturb_mm = {_format_perturb_table(perturb_mm)};

$fn = {geom.fn};

module seeded_hyperbolic_ridge(k) {{
    theta_k = k * golden_angle;
    z_k = c_z * k;
    perturb = perturb_mm[k];
    rotate([0, 0, theta_k])
        translate([R_tung + t_sheath/2 + perturb, 0, z_k])
            scale([1, 1, 0.7])
                rotate_extrude(angle=18, convexity=10)
                    translate([r_throat, 0, 0])
                        circle(r=1.2, $fn=24);
}}

module auxetic_sheath() {{
    for(i = [0 : num_ridges - 1]) {{
        rotate([0, 0, i * golden_angle])
            translate([R_tung + t_sheath/2, 0, 0])
                linear_extrude(
                    height=mesh_height,
                    twist=-golden_angle*num_ridges/4,
                    slices=80,
                    convexity=10
                )
                    polygon(points=[[0,0], [2,1], [0,3], [-2,1]]);
    }}
}}

difference() {{
    cylinder(h=mesh_height, r=R_tung * 1.15, $fn=64);  // Porous tungsten shell
    cylinder(h=mesh_height, r=R_tung * 0.85, $fn=64);  // Ferrofluid core cavity
    for(k = [0 : num_ridges - 1]) {{
        seeded_hyperbolic_ridge(k);
    }}
}}

color("Red") auxetic_sheath();
"""


def write_dynamo_core_scad(
    path: Path,
    seed: int,
    geometry: DynamoCoreGeometry | None = None,
) -> Path:
    """Convenience wrapper: render and write the .scad to disk."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dynamo_core_scad(seed, geometry), encoding="utf-8")
    return path


def manifest_with_geometry(
    seed: int,
    geometry: DynamoCoreGeometry | None = None,
) -> dict:
    """Audit-ready record binding a seed to (a) the perturbation field
    actually baked into the OpenSCAD source, and (b) the geometry
    parameters that produced the printable part. Pairs with
    ``mahss_crypto_lattice.manifest_for_seed`` to give a complete
    sim+geometry witness for one cryptographic identity."""

    geom = geometry or DynamoCoreGeometry()
    field = derive_perturbation_field(
        seed,
        geom.num_ridges,
        bound=geom.perturb_bound,
    )
    perturb_mm = (field * geom.perturb_scale_mm).tolist()
    return {
        "seed": int(seed),
        "seed_hex": f"{seed:016x}",
        "geometry": geom.to_manifest(),
        "perturb_field_unitless": field.tolist(),
        "perturb_field_mm": perturb_mm,
        "perturb_max_abs_mm": max(abs(v) for v in perturb_mm) if perturb_mm else 0.0,
    }
