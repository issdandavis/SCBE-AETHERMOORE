"""Generate a 512x512 24-bit PNG developer logo for SCBE-AETHERMOORE.

Procedural / deterministic — no external image gen. Composition mirrors the
visual identity:

  - Poincare disk boundary (cyan→gold gradient ring)
  - 14 phi-spaced concentric rings (the 14-layer pipeline)
  - 6-petal central hexagonal flower in Sacred Tongue colors:
      KO=royal blue, AV=emerald, RU=ruby, CA=amethyst, UM=amber gold, DR=onyx
  - Deep navy background

Output: artifacts/branding/scbe_dev_logo_512.png

Usage:
  python demos/gemma4_scbe_governance/make_logo.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "branding"
OUT = OUT_DIR / "scbe_dev_logo_512.png"

SIZE = 512
PHI = (1 + 5 ** 0.5) / 2

BG = (8, 12, 32)             # deep navy
GOLD = (212, 175, 55)
CYAN = (45, 200, 220)
RING_FAINT = (60, 70, 110)

# 6 Sacred Tongue petal colors, ordered KO, AV, RU, CA, UM, DR
TONGUE_COLORS = [
    (66, 110, 240),    # KO  Kor'aelin — royal blue
    (40, 170, 110),    # AV  Avali — emerald
    (210, 60, 70),     # RU  Runethic — ruby
    (140, 90, 200),    # CA  Cassisivadan — amethyst
    (235, 180, 60),    # UM  Umbroth — amber gold
    (30, 30, 38),      # DR  Draumric — onyx
]


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def draw_gradient_ring(img: Image.Image, center: tuple[int, int], radius: int, thickness: int) -> None:
    """Cyan→gold gradient ring as the Poincare boundary, drawn pixel-precise."""
    cx, cy = center
    px = img.load()
    r_outer = radius
    r_inner = radius - thickness
    for y in range(max(0, cy - r_outer - 1), min(img.height, cy + r_outer + 2)):
        for x in range(max(0, cx - r_outer - 1), min(img.width, cx + r_outer + 2)):
            dx = x - cx
            dy = y - cy
            d2 = dx * dx + dy * dy
            if r_inner * r_inner <= d2 <= r_outer * r_outer:
                ang = math.atan2(dy, dx)
                # smooth gradient: cyan at top, gold at bottom
                t = (math.sin(ang) + 1) / 2
                col = lerp_color(CYAN, GOLD, t)
                px[x, y] = col


def draw_phi_concentric_rings(draw: ImageDraw.ImageDraw, center: tuple[int, int], outer: int) -> None:
    """7 concentric rings spaced by phi (representing 14 layers folded as paired primary/secondary)."""
    cx, cy = center
    radii = []
    r = outer * 0.85
    for _ in range(7):
        radii.append(r)
        r = r / PHI ** 0.4
    for i, rr in enumerate(radii):
        t = i / max(1, len(radii) - 1)
        col = lerp_color(RING_FAINT, GOLD, 0.18 + t * 0.35)
        bbox = (cx - rr, cy - rr, cx + rr, cy + rr)
        draw.ellipse(bbox, outline=col, width=1)


def draw_radial_glow(img: Image.Image, center: tuple[int, int], inner: int, outer: int) -> None:
    """Soft radial glow behind the flower, gold→bg."""
    cx, cy = center
    px = img.load()
    o2 = outer * outer
    i2 = inner * inner
    for y in range(max(0, cy - outer - 1), min(img.height, cy + outer + 2)):
        for x in range(max(0, cx - outer - 1), min(img.width, cx + outer + 2)):
            dx = x - cx
            dy = y - cy
            d2 = dx * dx + dy * dy
            if i2 <= d2 <= o2:
                t = (math.sqrt(d2) - inner) / max(1, outer - inner)
                # warm glow
                glow = lerp_color(GOLD, BG, t)
                cur = px[x, y]
                # blend
                px[x, y] = (
                    (cur[0] + glow[0]) // 2,
                    (cur[1] + glow[1]) // 2,
                    (cur[2] + glow[2]) // 2,
                )


def draw_six_petal_flower(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int) -> None:
    """Central hexagonal flower — 6 leaf-shaped petals in Sacred Tongue colors."""
    cx, cy = center
    for i, color in enumerate(TONGUE_COLORS):
        ang_deg = -90 + i * 60
        ang = math.radians(ang_deg)
        tx = cx + radius * math.cos(ang)
        ty = cy + radius * math.sin(ang)
        lang = math.radians(ang_deg - 28)
        rang = math.radians(ang_deg + 28)
        lr = radius * 0.55
        lx = cx + lr * math.cos(lang)
        ly = cy + lr * math.sin(lang)
        rx = cx + lr * math.cos(rang)
        ry = cy + lr * math.sin(rang)
        draw.polygon([(cx, cy), (lx, ly), (tx, ty), (rx, ry)], fill=color, outline=GOLD)
    # gold center cap
    dot_r = max(6, radius // 6)
    draw.ellipse(
        (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
        fill=GOLD,
        outline=BG,
        width=3,
    )
    # tiny inner dark dot for contrast
    inner_r = max(2, dot_r // 3)
    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        fill=BG,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    cx, cy = SIZE // 2, SIZE // 2
    outer_r = SIZE // 2 - 20

    flower_r = int(outer_r * 0.50)
    draw_phi_concentric_rings(draw, (cx, cy), outer_r)
    draw_radial_glow(img, (cx, cy), inner=flower_r, outer=int(flower_r * 1.6))
    draw_six_petal_flower(draw, (cx, cy), flower_r)
    draw_gradient_ring(img, (cx, cy), outer_r, thickness=8)

    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB, mode={img.mode}, size={img.size})")


if __name__ == "__main__":
    main()
