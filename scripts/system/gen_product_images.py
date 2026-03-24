#!/usr/bin/env python3
"""Generate professional product cover images for Shopify store."""
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 1200
OUT = Path(__file__).resolve().parent.parent.parent / "artifacts" / "shopify-product-images"
OUT.mkdir(parents=True, exist_ok=True)

products = [
    {
        "file": "hydra-armor-api",
        "title": "HYDRA ARMOR",
        "subtitle": "AI Governance API",
        "price": "FREE TIER",
        "bg": [(15, 20, 50), (30, 80, 160)],
        "accent": (0, 200, 255),
        "icon": "shield",
    },
    {
        "file": "scbe-governance-toolkit",
        "title": "SCBE GOVERNANCE",
        "subtitle": "Security Toolkit",
        "price": "$29.99",
        "bg": [(20, 10, 40), (100, 30, 120)],
        "accent": (200, 100, 255),
        "icon": "lock",
    },
    {
        "file": "n8n-workflow-bundle",
        "title": "N8N WORKFLOWS",
        "subtitle": "AI Automation Bundle",
        "price": "$149.00",
        "bg": [(10, 30, 20), (20, 120, 80)],
        "accent": (0, 255, 150),
        "icon": "flow",
    },
    {
        "file": "spiralverse-training-data",
        "title": "SPIRALVERSE",
        "subtitle": "AI Training Data Pack",
        "price": "$49.99",
        "bg": [(40, 10, 10), (160, 40, 40)],
        "accent": (255, 100, 80),
        "icon": "spiral",
    },
    {
        "file": "worldforge-engine",
        "title": "WORLDFORGE",
        "subtitle": "Game Engine",
        "price": "$49.99",
        "bg": [(30, 25, 10), (150, 100, 20)],
        "accent": (255, 200, 50),
        "icon": "cube",
    },
    {
        "file": "k12-curriculum",
        "title": "K-12 COMPLETE",
        "subtitle": "Curriculum System",
        "price": "$19.99",
        "bg": [(10, 20, 40), (40, 100, 180)],
        "accent": (100, 200, 255),
        "icon": "book",
    },
    {
        "file": "hydra-notion-templates",
        "title": "HYDRA TEMPLATES",
        "subtitle": "For Notion",
        "price": "$9.99",
        "bg": [(25, 15, 30), (80, 50, 100)],
        "accent": (180, 150, 255),
        "icon": "grid",
    },
]


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_radial_gradient(draw, cx, cy, radius, center_color, edge_color):
    for r in range(radius, 0, -2):
        t = r / radius
        c = lerp_color(center_color, edge_color, t)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)


def draw_shield(draw, cx, cy, size, color):
    s = size
    pts = [
        (cx, cy - s),
        (cx + s * 0.7, cy - s * 0.7),
        (cx + s * 0.7, cy + s * 0.2),
        (cx, cy + s),
        (cx - s * 0.7, cy + s * 0.2),
        (cx - s * 0.7, cy - s * 0.7),
    ]
    draw.polygon(pts, outline=color, width=5)
    draw.line(
        [(cx - s * 0.25, cy), (cx - s * 0.05, cy + s * 0.2), (cx + s * 0.3, cy - s * 0.2)],
        fill=color,
        width=6,
    )


def draw_lock(draw, cx, cy, size, color):
    s = size * 0.4
    draw.rounded_rectangle([cx - s, cy - s * 0.1, cx + s, cy + s * 1.5], radius=12, outline=color, width=5)
    draw.arc([cx - s * 0.6, cy - s * 1.4, cx + s * 0.6, cy + s * 0.1], 180, 0, fill=color, width=5)
    draw.ellipse([cx - s * 0.15, cy + s * 0.3, cx + s * 0.15, cy + s * 0.7], fill=color)


def draw_flow(draw, cx, cy, size, color):
    r = size * 0.12
    nodes = [
        (cx - size * 0.4, cy - size * 0.3),
        (cx, cy),
        (cx + size * 0.4, cy + size * 0.3),
        (cx + size * 0.4, cy - size * 0.3),
        (cx - size * 0.4, cy + size * 0.3),
    ]
    for n in nodes[1:]:
        draw.line([nodes[1] if n != nodes[0] else nodes[0], n], fill=color, width=3)
    draw.line([nodes[0], nodes[1]], fill=color, width=3)
    for x, y in nodes:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def draw_spiral(draw, cx, cy, size, color):
    pts = []
    for i in range(300):
        t = i / 300.0
        angle = t * 6 * math.pi
        r = t * size * 0.5
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=3)


def draw_cube(draw, cx, cy, size, color):
    s = size * 0.35
    off = size * 0.15
    front = [(cx - s, cy - s + off), (cx + s, cy - s + off), (cx + s, cy + s + off), (cx - s, cy + s + off)]
    top = [(cx - s, cy - s + off), (cx - s + off, cy - s), (cx + s + off, cy - s), (cx + s, cy - s + off)]
    right = [(cx + s, cy - s + off), (cx + s + off, cy - s), (cx + s + off, cy + s), (cx + s, cy + s + off)]
    draw.polygon(front, outline=color, width=4)
    draw.polygon(top, outline=color, width=4)
    draw.polygon(right, outline=color, width=4)


def draw_book(draw, cx, cy, size, color):
    s = size * 0.4
    draw.polygon(
        [(cx, cy - s), (cx - s * 1.2, cy - s * 0.8), (cx - s * 1.2, cy + s * 0.8), (cx, cy + s)],
        outline=color,
        width=4,
    )
    draw.polygon(
        [(cx, cy - s), (cx + s * 1.2, cy - s * 0.8), (cx + s * 1.2, cy + s * 0.8), (cx, cy + s)],
        outline=color,
        width=4,
    )
    draw.line([(cx, cy - s), (cx, cy + s)], fill=color, width=3)
    for i in range(3):
        yy = cy - s * 0.3 + i * s * 0.35
        draw.line([(cx + s * 0.2, yy), (cx + s * 0.9, yy)], fill=color, width=2)


def draw_grid(draw, cx, cy, size, color):
    s = size * 0.4
    gap = s * 0.15
    cell = (s * 2 - gap * 2) / 3
    for r in range(3):
        for c in range(3):
            x1 = cx - s + c * (cell + gap)
            y1 = cy - s + r * (cell + gap)
            draw.rounded_rectangle([x1, y1, x1 + cell, y1 + cell], radius=8, outline=color, width=3)


ICON_FUNCS = {
    "shield": draw_shield,
    "lock": draw_lock,
    "flow": draw_flow,
    "spiral": draw_spiral,
    "cube": draw_cube,
    "book": draw_book,
    "grid": draw_grid,
}

FONT_PATHS = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]
FONT_BOLD_PATHS = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]


def load_font(size, bold=False):
    for p in (FONT_BOLD_PATHS if bold else FONT_PATHS):
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


for p in products:
    img = Image.new("RGB", (W, H), p["bg"][0])
    draw = ImageDraw.Draw(img)

    # Background gradient
    draw_radial_gradient(draw, W // 2, H, int(W * 1.2), p["bg"][1], p["bg"][0])

    # Subtle grid pattern overlay
    grid_color = tuple(min(255, c + 12) for c in p["bg"][0])
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)

    # Accent glow behind icon
    glow = tuple(c // 4 for c in p["accent"])
    draw_radial_gradient(draw, W // 2, 420, 250, glow, p["bg"][0])

    # Icon
    fn = ICON_FUNCS.get(p["icon"])
    if fn:
        fn(draw, W // 2, 420, 160, p["accent"])

    # Brand badge
    badge_font = load_font(22, bold=True)
    draw.rounded_rectangle([60, 50, 350, 90], radius=6, fill=p["accent"])
    draw.text((72, 55), "AETHERMOORE WORKS", fill=(0, 0, 0), font=badge_font)

    # Title
    title_font = load_font(72, bold=True)
    draw.text((80, 640), p["title"], fill=(255, 255, 255), font=title_font)

    # Subtitle
    sub_font = load_font(36)
    draw.text((80, 730), p["subtitle"], fill=p["accent"], font=sub_font)

    # Divider
    draw.line([(80, 800), (W - 80, 800)], fill=p["accent"], width=2)

    # Price
    price_font = load_font(56, bold=True)
    draw.text((80, 830), p["price"], fill=(255, 255, 255), font=price_font)

    # Tag
    tag_font = load_font(24)
    draw.rounded_rectangle([80, 930, 290, 970], radius=4, outline=p["accent"], width=2)
    draw.text((96, 937), "DIGITAL PRODUCT", fill=p["accent"], font=tag_font)

    # Bottom accent bar
    draw.rectangle([(0, H - 8), (W, H)], fill=p["accent"])

    out_path = OUT / f"{p['file']}.png"
    img.save(str(out_path), "PNG")
    print(f"Generated: {out_path.name}")

print(f"\nAll 7 images saved to {OUT}")
