#!/usr/bin/env python3
"""
3D Spatial Engine for SCBE-AETHERMOORE Six Tongues CLI.

Pure-stdlib 3D spatial engine providing:
  - Vec3 / Mat4 math (vectors, transforms, projections)
  - Mesh primitives (cube, sphere, tetrahedron, torus)
  - SpatialArray: non-linear 3D-addressed data grids with tongue ownership
  - AsciiRenderer: perspective projection to terminal with Unicode + ANSI color
  - TongueSpatialMapper: maps 6 Sacred Tongues to 3D axes via paired projection

No numpy required. Companion to six-tongues-cli.py.

@module cli/spatial-engine
@layer Layer 14
@component 3D Spatial Engine
@version 1.0.0
"""

import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════
# ANSI Colors — one per Sacred Tongue
# ═══════════════════════════════════════════════════════════════

TONGUE_ANSI = {
    "KO": "\033[96m",   # bright cyan
    "AV": "\033[95m",   # bright magenta/purple
    "RU": "\033[92m",   # bright green
    "CA": "\033[93m",   # bright yellow/orange
    "UM": "\033[91m",   # bright red
    "DR": "\033[35m",   # violet
}
ANSI_RESET = "\033[0m"
ANSI_DIM = "\033[2m"
ANSI_BOLD = "\033[1m"

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Tongue realm centers in 6D (from cymatic_voxel_net / six-tongues-cli)
REALM_CENTERS_6D = {
    "KO": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "AV": [0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
    "RU": [0.0, 0.4, 0.2, 0.0, 0.0, 0.0],
    "CA": [-0.2, -0.3, 0.4, 0.1, 0.0, 0.0],
    "UM": [0.0, 0.0, -0.5, 0.3, 0.2, 0.0],
    "DR": [0.1, -0.2, 0.0, -0.4, 0.3, 0.1],
}


# ═══════════════════════════════════════════════════════════════
# Vec3 — 3D Vector
# ═══════════════════════════════════════════════════════════════


class Vec3:
    """3D vector with full math operations."""

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self) -> str:
        return f"Vec3({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"

    def __add__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s: float) -> "Vec3":
        return Vec3(self.x * s, self.y * s, self.z * s)

    def __rmul__(self, s: float) -> "Vec3":
        return self.__mul__(s)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Vec3):
            return NotImplemented
        return abs(self.x - o.x) < 1e-9 and abs(self.y - o.y) < 1e-9 and abs(self.z - o.z) < 1e-9

    def dot(self, o: "Vec3") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> "Vec3":
        n = self.length()
        if n < 1e-12:
            return Vec3(0, 0, 0)
        return Vec3(self.x / n, self.y / n, self.z / n)

    def rotate_x(self, angle: float) -> "Vec3":
        c, s = math.cos(angle), math.sin(angle)
        return Vec3(self.x, self.y * c - self.z * s, self.y * s + self.z * c)

    def rotate_y(self, angle: float) -> "Vec3":
        c, s = math.cos(angle), math.sin(angle)
        return Vec3(self.x * c + self.z * s, self.y, -self.x * s + self.z * c)

    def rotate_z(self, angle: float) -> "Vec3":
        c, s = math.cos(angle), math.sin(angle)
        return Vec3(self.x * c - self.y * s, self.x * s + self.y * c, self.z)

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


# ═══════════════════════════════════════════════════════════════
# Mat4 — 4x4 Transform Matrix
# ═══════════════════════════════════════════════════════════════


class Mat4:
    """4x4 transformation matrix (row-major)."""

    __slots__ = ("m",)

    def __init__(self, data: Optional[List[float]] = None):
        if data is not None:
            if len(data) != 16:
                raise ValueError("Mat4 requires 16 elements")
            self.m = list(data)
        else:
            # Identity
            self.m = [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                0, 0, 0, 1,
            ]

    @staticmethod
    def identity() -> "Mat4":
        return Mat4()

    @staticmethod
    def rotate_x(angle: float) -> "Mat4":
        c, s = math.cos(angle), math.sin(angle)
        return Mat4([
            1, 0, 0, 0,
            0, c, -s, 0,
            0, s, c, 0,
            0, 0, 0, 1,
        ])

    @staticmethod
    def rotate_y(angle: float) -> "Mat4":
        c, s = math.cos(angle), math.sin(angle)
        return Mat4([
            c, 0, s, 0,
            0, 1, 0, 0,
            -s, 0, c, 0,
            0, 0, 0, 1,
        ])

    @staticmethod
    def rotate_z(angle: float) -> "Mat4":
        c, s = math.cos(angle), math.sin(angle)
        return Mat4([
            c, -s, 0, 0,
            s, c, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1,
        ])

    @staticmethod
    def translate(tx: float, ty: float, tz: float) -> "Mat4":
        return Mat4([
            1, 0, 0, tx,
            0, 1, 0, ty,
            0, 0, 1, tz,
            0, 0, 0, 1,
        ])

    @staticmethod
    def scale(sx: float, sy: float, sz: float) -> "Mat4":
        return Mat4([
            sx, 0, 0, 0,
            0, sy, 0, 0,
            0, 0, sz, 0,
            0, 0, 0, 1,
        ])

    @staticmethod
    def perspective(fov: float, aspect: float, near: float, far: float) -> "Mat4":
        f = 1.0 / math.tan(fov / 2.0)
        nf = near - far
        return Mat4([
            f / aspect, 0, 0, 0,
            0, f, 0, 0,
            0, 0, (far + near) / nf, 2 * far * near / nf,
            0, 0, -1, 0,
        ])

    def __mul__(self, other: "Mat4") -> "Mat4":
        a, b = self.m, other.m
        r = [0.0] * 16
        for i in range(4):
            for j in range(4):
                s = 0.0
                for k in range(4):
                    s += a[i * 4 + k] * b[k * 4 + j]
                r[i * 4 + j] = s
        return Mat4(r)

    def transform_vec3(self, v: Vec3) -> Vec3:
        m = self.m
        w = m[12] * v.x + m[13] * v.y + m[14] * v.z + m[15]
        if abs(w) < 1e-12:
            w = 1e-12
        return Vec3(
            (m[0] * v.x + m[1] * v.y + m[2] * v.z + m[3]) / w,
            (m[4] * v.x + m[5] * v.y + m[6] * v.z + m[7]) / w,
            (m[8] * v.x + m[9] * v.y + m[10] * v.z + m[11]) / w,
        )


# ═══════════════════════════════════════════════════════════════
# Mesh — Vertices + Edges + Faces
# ═══════════════════════════════════════════════════════════════


class Mesh:
    """3D mesh with vertices, edges, faces, and per-vertex tongue coloring."""

    def __init__(self):
        self.vertices: List[Vec3] = []
        self.edges: List[Tuple[int, int]] = []
        self.faces: List[List[int]] = []
        self.vertex_tongues: List[str] = []  # tongue label per vertex

    def add_vertex(self, v: Vec3, tongue: str = "KO") -> int:
        idx = len(self.vertices)
        self.vertices.append(v)
        self.vertex_tongues.append(tongue)
        return idx

    def add_edge(self, a: int, b: int) -> None:
        self.edges.append((a, b))

    def add_face(self, indices: List[int]) -> None:
        self.faces.append(indices)
        # Auto-add edges for the face
        for i in range(len(indices)):
            e = (indices[i], indices[(i + 1) % len(indices)])
            if e not in self.edges and (e[1], e[0]) not in self.edges:
                self.edges.append(e)

    def transform(self, mat: Mat4) -> "Mesh":
        """Return new mesh with all vertices transformed."""
        out = Mesh()
        out.edges = list(self.edges)
        out.faces = [list(f) for f in self.faces]
        out.vertex_tongues = list(self.vertex_tongues)
        for v in self.vertices:
            out.vertices.append(mat.transform_vec3(v))
        return out

    def bounds(self) -> Tuple[Vec3, Vec3]:
        if not self.vertices:
            return Vec3(), Vec3()
        mn = Vec3(
            min(v.x for v in self.vertices),
            min(v.y for v in self.vertices),
            min(v.z for v in self.vertices),
        )
        mx = Vec3(
            max(v.x for v in self.vertices),
            max(v.y for v in self.vertices),
            max(v.z for v in self.vertices),
        )
        return mn, mx


# ═══════════════════════════════════════════════════════════════
# Primitives
# ═══════════════════════════════════════════════════════════════


def cube(size: float = 1.0) -> Mesh:
    """Unit cube centered at origin."""
    m = Mesh()
    h = size / 2.0
    # 8 vertices
    verts = [
        Vec3(-h, -h, -h), Vec3(h, -h, -h), Vec3(h, h, -h), Vec3(-h, h, -h),
        Vec3(-h, -h, h), Vec3(h, -h, h), Vec3(h, h, h), Vec3(-h, h, h),
    ]
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR", "KO", "AV"]
    for v, t in zip(verts, tongues):
        m.add_vertex(v, t)
    # 6 faces
    for face in [[0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [0,3,7,4], [1,2,6,5]]:
        m.add_face(face)
    return m


def sphere(radius: float = 1.0, segments: int = 12) -> Mesh:
    """UV sphere wireframe."""
    m = Mesh()
    rings = segments // 2
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            tongue = TONGUES[(i + j) % 6]
            m.add_vertex(Vec3(x, y, z), tongue)
    # Edges: horizontal rings and vertical strips
    for i in range(rings + 1):
        for j in range(segments):
            curr = i * segments + j
            nxt = i * segments + (j + 1) % segments
            m.add_edge(curr, nxt)
            if i < rings:
                below = (i + 1) * segments + j
                m.add_edge(curr, below)
    return m


def tetrahedron(size: float = 1.0) -> Mesh:
    """Regular tetrahedron centered at origin."""
    m = Mesh()
    s = size / math.sqrt(2)
    verts = [Vec3(s, s, s), Vec3(s, -s, -s), Vec3(-s, s, -s), Vec3(-s, -s, s)]
    for i, v in enumerate(verts):
        m.add_vertex(v, TONGUES[i % 6])
    for face in [[0,1,2], [0,1,3], [0,2,3], [1,2,3]]:
        m.add_face(face)
    return m


def torus(major: float = 1.0, minor: float = 0.3, segments: int = 16) -> Mesh:
    """Toroidal mesh."""
    m = Mesh()
    rings = segments
    for i in range(rings):
        theta = 2 * math.pi * i / rings
        for j in range(segments):
            phi = 2 * math.pi * j / segments
            x = (major + minor * math.cos(phi)) * math.cos(theta)
            y = (major + minor * math.cos(phi)) * math.sin(theta)
            z = minor * math.sin(phi)
            tongue = TONGUES[(i + j) % 6]
            m.add_vertex(Vec3(x, y, z), tongue)
    for i in range(rings):
        for j in range(segments):
            curr = i * segments + j
            nxt_j = i * segments + (j + 1) % segments
            nxt_i = ((i + 1) % rings) * segments + j
            m.add_edge(curr, nxt_j)
            m.add_edge(curr, nxt_i)
    return m


def tongue_axes(length: float = 1.0) -> Mesh:
    """6 tongue direction vectors as 3D arrow lines from origin."""
    m = Mesh()
    mapper = TongueSpatialMapper()
    origin_idx = m.add_vertex(Vec3(0, 0, 0), "KO")
    for tg in TONGUES:
        direction = mapper.tongue_to_vec3(tg)
        tip = direction * length
        tip_idx = m.add_vertex(tip, tg)
        m.add_edge(origin_idx, tip_idx)
    return m


def spatial_array_cube(nx: int, ny: int, nz: int) -> Mesh:
    """3D grid mesh visualizing a SpatialArray bounding box."""
    m = Mesh()
    mapper = TongueSpatialMapper()
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                cx = (ix + 0.5) / nx
                cy = (iy + 0.5) / ny
                cz = (iz + 0.5) / nz
                tongue = mapper.classify_point(Vec3(cx - 0.5, cy - 0.5, cz - 0.5))
                idx = m.add_vertex(
                    Vec3(ix / max(1, nx - 1) - 0.5, iy / max(1, ny - 1) - 0.5, iz / max(1, nz - 1) - 0.5),
                    tongue,
                )
    # Grid edges along each axis
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                curr = ix * ny * nz + iy * nz + iz
                if ix + 1 < nx:
                    m.add_edge(curr, (ix + 1) * ny * nz + iy * nz + iz)
                if iy + 1 < ny:
                    m.add_edge(curr, ix * ny * nz + (iy + 1) * nz + iz)
                if iz + 1 < nz:
                    m.add_edge(curr, ix * ny * nz + iy * nz + (iz + 1))
    return m


# ═══════════════════════════════════════════════════════════════
# SpatialArray — Non-Linear 3D Code Arrays
# ═══════════════════════════════════════════════════════════════


class SpatialArray:
    """3D-addressed data grid with tongue ownership.

    Data stored at (x, y, z) integer coordinates, not flat indexes.
    Space divided into 6 tongue-owned regions via nearest realm center.
    """

    def __init__(self, nx: int, ny: int, nz: int):
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self._data: Dict[Tuple[int, int, int], Any] = {}
        self._mapper = TongueSpatialMapper()

    def set(self, x: int, y: int, z: int, value: Any) -> None:
        if not (0 <= x < self.nx and 0 <= y < self.ny and 0 <= z < self.nz):
            raise IndexError(f"({x},{y},{z}) out of bounds ({self.nx},{self.ny},{self.nz})")
        self._data[(x, y, z)] = value

    def get(self, x: int, y: int, z: int) -> Any:
        if not (0 <= x < self.nx and 0 <= y < self.ny and 0 <= z < self.nz):
            raise IndexError(f"({x},{y},{z}) out of bounds ({self.nx},{self.ny},{self.nz})")
        return self._data.get((x, y, z))

    def delete(self, x: int, y: int, z: int) -> None:
        self._data.pop((x, y, z), None)

    def count(self) -> int:
        return len(self._data)

    def owner_at(self, x: int, y: int, z: int) -> str:
        """Which tongue owns this coordinate?"""
        # Normalize to [-0.5, 0.5] range
        cx = (x + 0.5) / self.nx - 0.5
        cy = (y + 0.5) / self.ny - 0.5
        cz = (z + 0.5) / self.nz - 0.5
        return self._mapper.classify_point(Vec3(cx, cy, cz))

    def slice_plane(self, axis: str, index: int) -> Dict[Tuple[int, int], Any]:
        """Extract a 2D slice at the given axis value."""
        result: Dict[Tuple[int, int], Any] = {}
        for (x, y, z), val in self._data.items():
            if axis == "x" and x == index:
                result[(y, z)] = val
            elif axis == "y" and y == index:
                result[(x, z)] = val
            elif axis == "z" and z == index:
                result[(x, y)] = val
        return result

    def spiral_traverse(self) -> List[Tuple[Tuple[int, int, int], Any]]:
        """Iterate data in 3D spiral order from center outward."""
        cx, cy, cz = self.nx // 2, self.ny // 2, self.nz // 2
        coords = sorted(
            self._data.keys(),
            key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2,
        )
        return [(c, self._data[c]) for c in coords]

    def tongue_region(self, tongue: str) -> List[Tuple[Tuple[int, int, int], Any]]:
        """All occupied cells in the given tongue's region."""
        result = []
        for (x, y, z), val in self._data.items():
            if self.owner_at(x, y, z) == tongue:
                result.append(((x, y, z), val))
        return result

    def fill_tongue_data(self) -> None:
        """Fill every cell with its tongue owner metadata."""
        for x in range(self.nx):
            for y in range(self.ny):
                for z in range(self.nz):
                    tg = self.owner_at(x, y, z)
                    self.set(x, y, z, {"tongue": tg, "coord": (x, y, z)})


# ═══════════════════════════════════════════════════════════════
# TongueSpatialMapper — 6 Tongues to 3D Axes
# ═══════════════════════════════════════════════════════════════


class TongueSpatialMapper:
    """Maps 6 Sacred Tongues to 3D space via paired 6D->3D projection.

    Pairing: KO+AV -> X axis, RU+CA -> Y axis, UM+DR -> Z axis.
    Each tongue gets a primary direction in 3D from its 6D realm center.
    """

    AXIS_PAIRS = [("KO", "AV"), ("RU", "CA"), ("UM", "DR")]

    def __init__(self):
        self._tongue_dirs: Dict[str, Vec3] = {}
        for axis_idx, (tg_pos, tg_neg) in enumerate(self.AXIS_PAIRS):
            center_pos = REALM_CENTERS_6D[tg_pos]
            center_neg = REALM_CENTERS_6D[tg_neg]
            # Project 6D center to 3D via paired sum
            mag_pos = sum(abs(c) for c in center_pos) + 0.1
            mag_neg = sum(abs(c) for c in center_neg) + 0.1
            v_pos = Vec3()
            v_neg = Vec3()
            if axis_idx == 0:
                v_pos = Vec3(mag_pos, 0, 0)
                v_neg = Vec3(-mag_neg, 0, 0)
            elif axis_idx == 1:
                v_pos = Vec3(0, mag_pos, 0)
                v_neg = Vec3(0, -mag_neg, 0)
            else:
                v_pos = Vec3(0, 0, mag_pos)
                v_neg = Vec3(0, 0, -mag_neg)
            self._tongue_dirs[tg_pos] = v_pos.normalize()
            self._tongue_dirs[tg_neg] = v_neg.normalize()

    def tongue_to_vec3(self, tongue: str) -> Vec3:
        """Get the 3D direction vector for a tongue."""
        return self._tongue_dirs.get(tongue, Vec3())

    def classify_point(self, point: Vec3) -> str:
        """Classify which tongue owns a 3D point (nearest direction)."""
        best_tongue = "KO"
        best_dot = -999.0
        for tg, direction in self._tongue_dirs.items():
            d = point.dot(direction)
            if d > best_dot:
                best_dot = d
                best_tongue = tg
        return best_tongue

    def project_6d_to_3d(self, vec6d: List[float]) -> Vec3:
        """Project a 6D vector to 3D via paired axis summation."""
        v = (vec6d + [0] * 6)[:6]
        return Vec3(
            v[0] + v[1],  # KO+AV -> X
            v[2] + v[3],  # RU+CA -> Y
            v[4] + v[5],  # UM+DR -> Z
        )


# ═══════════════════════════════════════════════════════════════
# AsciiRenderer — 3D to Terminal
# ═══════════════════════════════════════════════════════════════

# Depth shading characters (darkest to brightest)
SHADE_CHARS = " .:-=+*#%@"

# Detect whether terminal supports Unicode
def _supports_unicode() -> bool:
    import locale
    try:
        enc = sys.stdout.encoding or locale.getpreferredencoding() or ""
        return enc.lower().replace("-", "") in ("utf8", "utf16", "utf32", "utf8sig")
    except Exception:
        return False

_UNICODE = _supports_unicode()
BLOCK_CHARS = " .oO#" if not _UNICODE else " \u2591\u2592\u2593\u2588"

# Box drawing / wireframe
LINE_H = "-" if not _UNICODE else "\u2500"
LINE_V = "|" if not _UNICODE else "\u2502"
CORNER_TL = "+" if not _UNICODE else "\u250c"
CORNER_TR = "+" if not _UNICODE else "\u2510"
CORNER_BL = "+" if not _UNICODE else "\u2514"
CORNER_BR = "+" if not _UNICODE else "\u2518"
CROSS = "+" if not _UNICODE else "\u253c"
DOT = "o"


class AsciiRenderer:
    """Project 3D meshes to terminal using perspective projection + ANSI color."""

    def __init__(self, width: int = 72, height: int = 36, use_color: bool = True):
        self.width = width
        self.height = height
        self.use_color = use_color
        self.camera_distance = 4.0
        self.fov = math.pi / 3

    def _project(self, v: Vec3) -> Tuple[float, float, float]:
        """Perspective project 3D point to 2D screen coords + depth."""
        z = v.z + self.camera_distance
        if z < 0.1:
            z = 0.1
        scale = self.camera_distance / z
        sx = v.x * scale * (self.height / 2) + self.width / 2
        sy = -v.y * scale * (self.height / 2) + self.height / 2
        return sx, sy, z

    def _colorize(self, char: str, tongue: str, depth: float, max_depth: float) -> str:
        if not self.use_color:
            return char
        color = TONGUE_ANSI.get(tongue, "")
        # Dim distant points
        brightness = 1.0 - 0.5 * min(1.0, depth / max(1.0, max_depth))
        if brightness < 0.5:
            return f"{ANSI_DIM}{color}{char}{ANSI_RESET}"
        return f"{color}{char}{ANSI_RESET}"

    def render_wireframe(self, mesh: Mesh) -> str:
        """Render mesh edges as wireframe using Bresenham line drawing."""
        canvas = [[" "] * self.width for _ in range(self.height)]
        depth_buf = [[999.0] * self.width for _ in range(self.height)]

        # Project all vertices
        projected = []
        max_depth = 1.0
        for v in mesh.vertices:
            sx, sy, d = self._project(v)
            projected.append((sx, sy, d))
            if d > max_depth:
                max_depth = d

        # Draw edges
        for a, b in mesh.edges:
            sx1, sy1, d1 = projected[a]
            sx2, sy2, d2 = projected[b]
            tongue_a = mesh.vertex_tongues[a] if a < len(mesh.vertex_tongues) else "KO"
            self._draw_line(canvas, depth_buf, sx1, sy1, d1, sx2, sy2, d2, tongue_a, max_depth)

        # Draw vertices on top
        for i, (sx, sy, d) in enumerate(projected):
            ix, iy = int(round(sx)), int(round(sy))
            if 0 <= ix < self.width and 0 <= iy < self.height:
                tongue = mesh.vertex_tongues[i] if i < len(mesh.vertex_tongues) else "KO"
                canvas[iy][ix] = self._colorize(DOT, tongue, d, max_depth)
                depth_buf[iy][ix] = d

        return "\n".join("".join(row) for row in canvas)

    def render_points(self, mesh: Mesh) -> str:
        """Render mesh as point cloud."""
        canvas = [[" "] * self.width for _ in range(self.height)]
        max_depth = 1.0
        projected = []
        for v in mesh.vertices:
            sx, sy, d = self._project(v)
            projected.append((sx, sy, d))
            if d > max_depth:
                max_depth = d

        # Sort by depth (far first) for proper occlusion
        indices = sorted(range(len(projected)), key=lambda i: -projected[i][2])
        for i in indices:
            sx, sy, d = projected[i]
            ix, iy = int(round(sx)), int(round(sy))
            if 0 <= ix < self.width and 0 <= iy < self.height:
                tongue = mesh.vertex_tongues[i] if i < len(mesh.vertex_tongues) else "KO"
                shade_idx = max(0, min(len(BLOCK_CHARS) - 1, int((1 - d / max_depth) * (len(BLOCK_CHARS) - 1))))
                ch = BLOCK_CHARS[shade_idx]
                canvas[iy][ix] = self._colorize(ch, tongue, d, max_depth)

        return "\n".join("".join(row) for row in canvas)

    def render_solid(self, mesh: Mesh) -> str:
        """Render mesh with filled faces using depth shading."""
        canvas = [[" "] * self.width for _ in range(self.height)]
        depth_buf = [[999.0] * self.width for _ in range(self.height)]

        projected = []
        max_depth = 1.0
        for v in mesh.vertices:
            sx, sy, d = self._project(v)
            projected.append((sx, sy, d))
            if d > max_depth:
                max_depth = d

        # Sort faces by average depth (painter's algorithm)
        face_depths = []
        for fi, face in enumerate(mesh.faces):
            avg_d = sum(projected[vi][2] for vi in face) / max(1, len(face))
            face_depths.append((fi, avg_d))
        face_depths.sort(key=lambda x: -x[1])

        for fi, _ in face_depths:
            face = mesh.faces[fi]
            if len(face) < 3:
                continue
            tongue = mesh.vertex_tongues[face[0]] if face[0] < len(mesh.vertex_tongues) else "KO"
            pts = [(projected[vi][0], projected[vi][1], projected[vi][2]) for vi in face]
            self._fill_face(canvas, depth_buf, pts, tongue, max_depth)

        return "\n".join("".join(row) for row in canvas)

    def render(self, mesh: Mesh, mode: str = "wireframe") -> str:
        """Render mesh with the specified mode."""
        if mode == "points":
            return self.render_points(mesh)
        elif mode == "solid":
            return self.render_solid(mesh)
        return self.render_wireframe(mesh)

    def _draw_line(
        self, canvas, depth_buf,
        x1: float, y1: float, d1: float,
        x2: float, y2: float, d2: float,
        tongue: str, max_depth: float,
    ) -> None:
        """Bresenham line drawing with depth interpolation."""
        ix1, iy1 = int(round(x1)), int(round(y1))
        ix2, iy2 = int(round(x2)), int(round(y2))
        dx = abs(ix2 - ix1)
        dy = abs(iy2 - iy1)
        sx = 1 if ix1 < ix2 else -1
        sy = 1 if iy1 < iy2 else -1
        err = dx - dy
        steps = max(dx, dy, 1)
        cx, cy = ix1, iy1
        for step in range(steps + 1):
            t = step / max(1, steps)
            depth = d1 + (d2 - d1) * t
            if 0 <= cx < self.width and 0 <= cy < self.height:
                if depth <= depth_buf[cy][cx]:
                    depth_buf[cy][cx] = depth
                    shade_idx = max(0, min(len(SHADE_CHARS) - 1, int((1 - depth / max(1, max_depth)) * (len(SHADE_CHARS) - 1))))
                    ch = SHADE_CHARS[shade_idx]
                    canvas[cy][cx] = self._colorize(ch if ch != " " else LINE_H, tongue, depth, max_depth)
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    def _fill_face(
        self, canvas, depth_buf,
        pts: List[Tuple[float, float, float]],
        tongue: str, max_depth: float,
    ) -> None:
        """Scanline fill a projected polygon."""
        if len(pts) < 3:
            return
        # Bounding box
        min_y = max(0, int(min(p[1] for p in pts)))
        max_y = min(self.height - 1, int(max(p[1] for p in pts)))

        for y in range(min_y, max_y + 1):
            intersections: List[Tuple[float, float]] = []  # (x, depth)
            n = len(pts)
            for i in range(n):
                x1, y1, d1 = pts[i]
                x2, y2, d2 = pts[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    if abs(y2 - y1) > 1e-6:
                        t = (y - y1) / (y2 - y1)
                        ix = x1 + t * (x2 - x1)
                        depth = d1 + t * (d2 - d1)
                        intersections.append((ix, depth))
            intersections.sort()
            for j in range(0, len(intersections) - 1, 2):
                x_start, d_start = intersections[j]
                x_end, d_end = intersections[j + 1]
                ix_start = max(0, int(x_start))
                ix_end = min(self.width - 1, int(x_end))
                for x in range(ix_start, ix_end + 1):
                    span = x_end - x_start
                    t = (x - x_start) / span if span > 1e-6 else 0
                    depth = d_start + t * (d_end - d_start)
                    if depth <= depth_buf[y][x]:
                        depth_buf[y][x] = depth
                        shade_idx = max(0, min(len(BLOCK_CHARS) - 1, int((1 - depth / max(1, max_depth)) * (len(BLOCK_CHARS) - 1))))
                        canvas[y][x] = self._colorize(BLOCK_CHARS[shade_idx], tongue, depth, max_depth)


# ═══════════════════════════════════════════════════════════════
# Self-Test
# ═══════════════════════════════════════════════════════════════


def selftest() -> int:
    """Run built-in selftest for the spatial engine."""
    errors = 0

    def check(label: str, condition: bool) -> None:
        nonlocal errors
        if not condition:
            print(f"  FAIL: {label}")
            errors += 1

    print("=== Spatial Engine Self-Test ===\n")

    # [1] Vec3 Math
    print("[1] Vec3 Math")
    a = Vec3(1, 2, 3)
    b = Vec3(4, 5, 6)
    check("add", (a + b) == Vec3(5, 7, 9))
    check("sub", (b - a) == Vec3(3, 3, 3))
    check("scale", (a * 2) == Vec3(2, 4, 6))
    check("rmul", (2 * a) == Vec3(2, 4, 6))
    check("neg", (-a) == Vec3(-1, -2, -3))
    check("dot", abs(a.dot(b) - 32.0) < 1e-9)
    cross = a.cross(b)
    check("cross", cross == Vec3(-3, 6, -3))
    check("length", abs(Vec3(3, 4, 0).length() - 5.0) < 1e-9)
    n = Vec3(0, 0, 5).normalize()
    check("normalize", abs(n.length() - 1.0) < 1e-9 and abs(n.z - 1.0) < 1e-9)
    # Rotation
    r = Vec3(1, 0, 0).rotate_z(math.pi / 2)
    check("rotate_z 90deg", abs(r.x) < 1e-9 and abs(r.y - 1.0) < 1e-9)
    r2 = Vec3(0, 1, 0).rotate_x(math.pi / 2)
    check("rotate_x 90deg", abs(r2.y) < 1e-9 and abs(r2.z - 1.0) < 1e-9)
    r3 = Vec3(0, 0, 1).rotate_y(math.pi / 2)
    check("rotate_y 90deg", abs(r3.x - 1.0) < 1e-9 and abs(r3.z) < 1e-9)

    # [2] Mat4 Transforms
    print("[2] Mat4 Transforms")
    ident = Mat4.identity()
    v = Vec3(1, 2, 3)
    check("identity transform", ident.transform_vec3(v) == v)
    t = Mat4.translate(10, 20, 30)
    check("translate", t.transform_vec3(Vec3(0, 0, 0)) == Vec3(10, 20, 30))
    s = Mat4.scale(2, 3, 4)
    check("scale", s.transform_vec3(Vec3(1, 1, 1)) == Vec3(2, 3, 4))
    # Rotation
    rx = Mat4.rotate_z(math.pi / 2)
    rv = rx.transform_vec3(Vec3(1, 0, 0))
    check("mat4 rotate_z", abs(rv.x) < 1e-6 and abs(rv.y - 1.0) < 1e-6)
    # Multiplication
    combined = Mat4.translate(1, 0, 0) * Mat4.scale(2, 2, 2)
    result = combined.transform_vec3(Vec3(1, 0, 0))
    check("mat4 multiply (translate*scale)", abs(result.x - 3.0) < 1e-6)
    # Perspective
    persp = Mat4.perspective(math.pi / 3, 1.0, 0.1, 100.0)
    check("perspective matrix created", persp.m[0] != 0)

    # [3] Mesh Primitives
    print("[3] Mesh Primitives")
    c = cube()
    check("cube has 8 vertices", len(c.vertices) == 8)
    check("cube has 12 edges", len(c.edges) == 12)
    check("cube has 6 faces", len(c.faces) == 6)
    check("cube vertex tongues assigned", len(c.vertex_tongues) == 8)

    sp = sphere(1.0, 8)
    check("sphere has vertices", len(sp.vertices) > 0)
    check("sphere has edges", len(sp.edges) > 0)

    tet = tetrahedron()
    check("tetrahedron has 4 vertices", len(tet.vertices) == 4)
    check("tetrahedron has 4 faces", len(tet.faces) == 4)

    tor = torus(1.0, 0.3, 8)
    check("torus has vertices", len(tor.vertices) > 0)
    check("torus has edges", len(tor.edges) > 0)

    axes = tongue_axes()
    check("tongue_axes has 7 vertices (origin + 6)", len(axes.vertices) == 7)
    check("tongue_axes has 6 edges", len(axes.edges) == 6)

    grid = spatial_array_cube(3, 3, 3)
    check("spatial_array_cube has 27 vertices", len(grid.vertices) == 27)

    # Mesh transform
    moved = c.transform(Mat4.translate(5, 0, 0))
    check("mesh transform preserves vertex count", len(moved.vertices) == len(c.vertices))
    check("mesh transform moves vertices", abs(moved.vertices[0].x - (c.vertices[0].x + 5)) < 1e-6)

    # Bounds
    mn, mx = c.bounds()
    check("cube bounds min", abs(mn.x + 0.5) < 1e-6)
    check("cube bounds max", abs(mx.x - 0.5) < 1e-6)

    # [4] SpatialArray
    print("[4] SpatialArray")
    arr = SpatialArray(8, 8, 8)
    arr.set(2, 3, 1, {"tongue": "KO", "token": "kor'vel", "value": 42})
    check("set/get", arr.get(2, 3, 1)["value"] == 42)
    check("get empty", arr.get(0, 0, 0) is None)
    arr.set(0, 0, 0, "origin")
    arr.set(7, 7, 7, "corner")
    check("count", arr.count() == 3)

    # Bounds check
    try:
        arr.set(8, 0, 0, "bad")
        check("out-of-bounds raises", False)
    except IndexError:
        check("out-of-bounds raises", True)

    # Slice
    arr.set(2, 0, 1, "z1a")
    arr.set(5, 5, 1, "z1b")
    sl = arr.slice_plane("z", 1)
    check("slice z=1 has entries", len(sl) >= 2)

    # Spiral traverse
    spiral = arr.spiral_traverse()
    check("spiral traverse returns all entries", len(spiral) == arr.count())

    # Tongue regions
    owner = arr.owner_at(0, 0, 0)
    check("owner_at returns tongue", owner in TONGUES)
    arr.fill_tongue_data()
    check("fill_tongue_data populates all", arr.count() == 8 * 8 * 8)
    region = arr.tongue_region("KO")
    check("tongue_region returns entries", len(region) > 0)

    # Delete
    arr.delete(0, 0, 0)
    check("delete removes entry", arr.get(0, 0, 0) is None)

    # [5] TongueSpatialMapper
    print("[5] TongueSpatialMapper")
    mapper = TongueSpatialMapper()
    for tg in TONGUES:
        d = mapper.tongue_to_vec3(tg)
        check(f"{tg} has unit direction", abs(d.length() - 1.0) < 1e-6)
    # KO should point in +X direction
    ko_dir = mapper.tongue_to_vec3("KO")
    check("KO points +X", ko_dir.x > 0)
    # AV should point in -X direction
    av_dir = mapper.tongue_to_vec3("AV")
    check("AV points -X", av_dir.x < 0)
    # Classification
    check("classify +X -> KO", mapper.classify_point(Vec3(1, 0, 0)) == "KO")
    check("classify -X -> AV", mapper.classify_point(Vec3(-1, 0, 0)) == "AV")
    # 6D to 3D projection
    v3 = mapper.project_6d_to_3d([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    check("6D->3D projection", abs(v3.x - 0.3) < 1e-9 and abs(v3.y - 0.7) < 1e-9 and abs(v3.z - 1.1) < 1e-9)

    # [6] AsciiRenderer
    print("[6] AsciiRenderer")
    renderer = AsciiRenderer(width=40, height=20, use_color=False)

    # Wireframe
    rot = Mat4.rotate_y(math.radians(30)) * Mat4.rotate_x(math.radians(20))
    c_rot = cube().transform(rot)
    wf = renderer.render_wireframe(c_rot)
    check("wireframe render produces output", len(wf) > 0)
    check("wireframe has correct height", len(wf.split("\n")) == 20)

    # Points
    pts = renderer.render_points(sphere(1.0, 8).transform(rot))
    check("points render produces output", len(pts) > 0)

    # Solid
    sol = renderer.render_solid(cube().transform(rot))
    check("solid render produces output", len(sol) > 0)

    # Render mode dispatch
    out = renderer.render(cube().transform(rot), mode="wireframe")
    check("render dispatch wireframe", len(out) > 0)
    out2 = renderer.render(cube().transform(rot), mode="solid")
    check("render dispatch solid", len(out2) > 0)
    out3 = renderer.render(cube().transform(rot), mode="points")
    check("render dispatch points", len(out3) > 0)

    # Render with color
    renderer_color = AsciiRenderer(width=40, height=20, use_color=True)
    colored = renderer_color.render_wireframe(c_rot)
    check("colored wireframe has ANSI codes", "\033[" in colored)

    # --- Summary ---
    print(f"\n{'=' * 40}")
    if errors == 0:
        print("spatial engine selftest ok -- all checks passed")
    else:
        print(f"spatial engine selftest FAILED -- {errors} check(s) failed")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(selftest())
