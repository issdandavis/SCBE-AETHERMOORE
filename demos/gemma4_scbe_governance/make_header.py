"""Generate a 4096x2304 (16:9) developer page header for SCBE-AETHERMOORE.

Spec target: JPEG or 24-bit PNG (not transparent), up to 1 MB. We emit JPEG
at quality 90 because PNG at this resolution would exceed the size cap.

Composition:
  - Deep navy radial gradient background (slightly lighter at center)
  - Centered Poincare disk hero (re-using make_logo.py's geometry,
    scaled up) with 6 Sacred Tongue petals + golden phi-spiral rings
  - Horizontal phi-spaced concentric arcs sweeping outward to suggest
    the 14-layer pipeline extending toward the edges
  - Bottom edge thin Sacred Tongue color stripe (KO/AV/RU/CA/UM/DR)

Output: artifacts/branding/scbe_dev_header_4096x2304.jpg

Usage:
  python demos/gemma4_scbe_governance/make_header.py
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "branding"
OUT = OUT_DIR / "scbe_dev_header_4096x2304.jpg"

W, H = 4096, 2304
PHI = (1 + 5 ** 0.5) / 2

BG_DARK = np.array([6, 10, 26], dtype=np.float32)       # outer corners
BG_LIGHT = np.array([14, 22, 56], dtype=np.float32)     # center
GOLD = (212, 175, 55)
CYAN = (45, 200, 220)

# 6 Sacred Tongue petal colors, ordered KO, AV, RU, CA, UM, DR
TONGUE_COLORS = [
    (66, 110, 240),    # KO  Kor'aelin — royal blue
    (40, 170, 110),    # AV  Avali — emerald
    (210, 60, 70),     # RU  Runethic — ruby
    (140, 90, 200),    # CA  Cassisivadan — amethyst
    (235, 180, 60),    # UM  Umbroth — amber gold
    (30, 30, 38),      # DR  Draumric — onyx
]


def lerp_color(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def radial_gradient_bg(w: int, h: int) -> np.ndarray:
    """Vectorized radial gradient from BG_LIGHT (center) to BG_DARK (corners)."""
    cx, cy = w / 2, h / 2
    yy, xx = np.indices((h, w), dtype=np.float32)
    dx = xx - cx
    dy = yy - cy
    r = np.sqrt(dx * dx + dy * dy)
    rmax = math.sqrt(cx * cx + cy * cy)
    t = np.clip(r / rmax, 0.0, 1.0)
    # Soften with a curve so center stays light
    t = t ** 0.85
    t3 = t[..., None]
    rgb = (BG_LIGHT * (1 - t3) + BG_DARK * t3).astype(np.uint8)
    return rgb


def draw_concentric_arcs(img: Image.Image, center: tuple[int, int], r_min: int, r_max: int, count: int) -> None:
    """Phi-spaced concentric rings sweeping the full canvas — soft, layered."""
    cx, cy = center
    radii = []
    r = r_min
    step = (r_max / r_min) ** (1.0 / max(1, count - 1))
    for _ in range(count):
        radii.append(r)
        r *= step
    overlay = Image.new("RGB", img.size, (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i, rr in enumerate(radii):
        t = i / max(1, len(radii) - 1)
        col = lerp_color((40, 50, 90), GOLD, 0.15 + 0.45 * t)
        bbox = (cx - rr, cy - rr, cx + rr, cy + rr)
        od.ellipse(bbox, outline=col, width=2)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2.5))
    # Composite via screen blend (max channel)
    base_arr = np.array(img, dtype=np.uint8)
    over_arr = np.array(overlay, dtype=np.uint8)
    blended = np.maximum(base_arr, over_arr)
    img.paste(Image.fromarray(blended))


def draw_six_petal_flower(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int) -> None:
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
    bg_tup = tuple(int(v) for v in BG_DARK)
    dot_r = max(12, radius // 6)
    draw.ellipse(
        (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
        fill=GOLD,
        outline=bg_tup,
        width=6,
    )
    inner_r = max(4, dot_r // 3)
    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        fill=bg_tup,
    )


def draw_gradient_ring(img: Image.Image, center: tuple[int, int], radius: int, thickness: int) -> None:
    """Vectorized cyan→gold gradient ring at the Poincare boundary."""
    cx, cy = center
    arr = np.array(img, dtype=np.uint8)
    h, w = arr.shape[:2]
    yy, xx = np.indices((h, w))
    dx = xx - cx
    dy = yy - cy
    d2 = dx * dx + dy * dy
    inner = (radius - thickness) ** 2
    outer = radius * radius
    mask = (d2 >= inner) & (d2 <= outer)
    ang = np.arctan2(dy, dx)
    t = (np.sin(ang) + 1) / 2
    cyan = np.array(CYAN, dtype=np.float32)
    gold = np.array(GOLD, dtype=np.float32)
    grad = (cyan * (1 - t)[..., None] + gold * t[..., None]).astype(np.uint8)
    arr[mask] = grad[mask]
    img.paste(Image.fromarray(arr))


def draw_radial_glow(img: Image.Image, center: tuple[int, int], inner: int, outer: int) -> None:
    cx, cy = center
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.indices((h, w))
    dx = xx - cx
    dy = yy - cy
    r = np.sqrt(dx * dx + dy * dy)
    mask = (r >= inner) & (r <= outer)
    t = np.clip((r - inner) / max(1, outer - inner), 0, 1)
    glow = np.array(GOLD, dtype=np.float32)
    blend = (1 - t) * 0.45  # how much glow to add
    blend3 = blend[..., None]
    add = glow[None, None, :] * blend3
    arr[mask] = np.clip(arr[mask] + add[mask], 0, 255)
    img.paste(Image.fromarray(arr.astype(np.uint8)))


def draw_tongue_stripe(img: Image.Image, height_px: int) -> None:
    """Bottom edge horizontal stripe with all 6 Sacred Tongue colors."""
    arr = np.array(img, dtype=np.uint8)
    h, w = arr.shape[:2]
    seg = w // len(TONGUE_COLORS)
    y0 = h - height_px
    for i, color in enumerate(TONGUE_COLORS):
        x0 = i * seg
        x1 = (i + 1) * seg if i < len(TONGUE_COLORS) - 1 else w
        arr[y0:h, x0:x1] = np.array(color, dtype=np.uint8)
    img.paste(Image.fromarray(arr))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bg = radial_gradient_bg(W, H)
    img = Image.fromarray(bg, mode="RGB")
    cx, cy = W // 2, H // 2

    # Outer concentric arcs for depth
    draw_concentric_arcs(img, (cx, cy), r_min=380, r_max=int(W * 0.6), count=22)

    # Hero Poincare disk centered — use 80% of the canvas height
    hero_r = int(H * 0.40)
    flower_r = int(hero_r * 0.45)
    draw_radial_glow(img, (cx, cy), inner=int(flower_r * 0.9), outer=int(flower_r * 2.2))

    draw = ImageDraw.Draw(img)
    # Inner phi rings around the flower (the 14 layers folded)
    radii = []
    r = hero_r * 0.95
    for _ in range(7):
        radii.append(r)
        r = r / PHI ** 0.4
    for i, rr in enumerate(radii):
        t = i / max(1, len(radii) - 1)
        col = lerp_color((60, 70, 110), GOLD, 0.15 + 0.4 * t)
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=col, width=2)

    draw_six_petal_flower(draw, (cx, cy), flower_r)
    draw_gradient_ring(img, (cx, cy), hero_r, thickness=14)

    # Bottom Sacred Tongue stripe (subtle, 1.5% of height)
    draw_tongue_stripe(img, height_px=int(H * 0.015))

    # Save as JPEG at quality 90 to fit under 1 MB
    img.save(OUT, "JPEG", quality=90, optimize=True)
    size_kb = OUT.stat().st_size // 1024
    print(f"Wrote {OUT} ({size_kb} KB, {img.mode}, {img.size})")


if __name__ == "__main__":
    main()
