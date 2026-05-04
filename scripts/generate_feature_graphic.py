"""Generate Google Play feature graphic (1024x500) for AetherCode."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

OUTPUT = Path("kindle-app/store-assets/feature-graphic.png")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

W, H = 1024, 500
BG = "#070b12"
ACCENT = "#17c6cf"
ACCENT2 = "#ff9152"
TEXT = "#e8f0fb"
DIM = "#a2b6cc"

# Provider colors for the 9 dots
DOT_COLORS = [
    "#17c6cf",  # Cyan
    "#ff9152",  # Orange
    "#2dd3a6",  # Green
    "#6366f1",  # Indigo
    "#f472b6",  # Pink
    "#a78bfa",  # Purple
    "#fbbf24",  # Amber
    "#38bdf8",  # Sky
    "#fb7185",  # Rose
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try common fonts
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    if bold:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_gradient_background(draw: ImageDraw.ImageDraw, img: Image.Image) -> None:
    # Top-left glow
    for r in range(400, 0, -4):
        alpha = int(30 * (r / 400))
        color = (23, 198, 207, alpha)
        draw.ellipse([(-r, -r), (r, r)], fill=color)
    # Top-right glow
    for r in range(300, 0, -4):
        alpha = int(20 * (r / 300))
        color = (255, 145, 82, alpha)
        draw.ellipse([(W - r, -r), (W + r, r)], fill=color)


def draw_dots_circle(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, colors: list[str]
) -> None:
    n = len(colors)
    for i, color in enumerate(colors):
        angle = (2 * math.pi * i / n) - math.pi / 2
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        # Glow
        for r in range(18, 6, -3):
            a = int(40 * (r / 18))
            c = ImageColor.getrgb(color) + (a,)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=c)
        # Core dot
        draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=color)


def main() -> None:
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Radial gradient background glows
    draw_gradient_background(draw, img)

    # Dark overlay for readability
    overlay = Image.new("RGBA", (W, H), (7, 11, 18, 180))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = load_font(72, bold=True)
    font_sub = load_font(32)
    font_tag = load_font(20)

    # Title: AetherCode
    draw.text((60, 160), "AetherCode", font=font_title, fill=ACCENT)

    # Subtitle: AI Round Table
    draw.text((60, 260), "AI Round Table", font=font_sub, fill=TEXT)

    # Tagline
    draw.text((60, 320), "Free. Governed. Multi-Model.", font=font_tag, fill=DIM)

    # 9 dots in a circle on the right side
    draw_dots_circle(draw, 820, 250, 90, DOT_COLORS)

    # Thin accent line under title
    draw.rectangle([60, 245, 360, 247], fill=ACCENT)

    # Subtle grid lines for tech feel
    for x in range(0, W, 64):
        draw.line([(x, 0), (x, H)], fill=(23, 198, 207, 8), width=1)
    for y in range(0, H, 64):
        draw.line([(0, y), (W, y)], fill=(23, 198, 207, 8), width=1)

    # Convert to RGB for PNG
    final = Image.new("RGB", (W, H), BG)
    final.paste(img, mask=img.split()[3])

    final.save(OUTPUT, "PNG")
    print(f"Feature graphic saved: {OUTPUT}")
    print(f"Dimensions: {W}x{H}")


if __name__ == "__main__":
    main()
