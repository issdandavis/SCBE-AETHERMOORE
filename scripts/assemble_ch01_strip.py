"""
Assemble Chapter 1 v3 panels into a cinematic vertical scroll strip.
Variable heights, scroll gaps per scene, 800px wide target.
Source: manhwa-cinematic-forge skill assembly rules.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json

SRC = Path("C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/ch01/v3")
OUT = Path("C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/ch01")
WIDTH = 800
BG_COLOR = (10, 14, 20)  # dark manhwa background

# Panel sequence with scroll gaps and target heights
# gap_after = pixels of dark space AFTER this panel
# target_h = target height when scaled to 800px wide (None = use native aspect ratio)
SEQUENCE = [
    # ── SCENE 1: THE OFFICE ──
    {"id": "p01", "target_h": 1100, "gap_after": 40},  # Establishing - tall
    {"id": "p02", "target_h": 600, "gap_after": 20},  # Coffee macro - standard
    {"id": "p03", "target_h": 350, "gap_after": 60},  # Bryce shelf - wide strip
    {"id": "p04", "target_h": 250, "gap_after": 40},  # Breathing - terminal glow
    {"id": "p05", "target_h": 600, "gap_after": 20},  # Line 4847 - standard
    {"id": "p06", "target_h": 600, "gap_after": 20},  # Found you - standard
    {"id": "p07", "target_h": 300, "gap_after": 40},  # The sip - wide detail
    {"id": "p08", "target_h": 300, "gap_after": 100},  # Guard below - wide, SCENE BREAK after
    # ── SCENE 2: THE WHITEOUT ──
    {"id": "p09", "target_h": 350, "gap_after": 0},  # Impact - SLAM CUT (0 gap)
    {"id": "p10", "target_h": 300, "gap_after": 0},  # What do you intend - narrow
    {"id": "p11", "target_h": 200, "gap_after": 80},  # Breathing - white to black
    # ── SCENE 3: THE FALL ──
    {"id": "p12", "target_h": 1600, "gap_after": 0},  # The fall - EXTRA TALL, slam into next
    # ── SCENE 4: ARRIVAL ──
    {"id": "p13", "target_h": 200, "gap_after": 60},  # Breathing - sliver of amber
    {"id": "p14", "target_h": 1000, "gap_after": 40},  # Cheek on stone - tall
    {"id": "p15", "target_h": 1400, "gap_after": 40},  # Archive breathes - tall reveal
    {"id": "p16", "target_h": 250, "gap_after": 100},  # Breathing - book hum, SCENE BREAK
    # ── SCENE 5: POLLY ──
    {"id": "p17", "target_h": 1100, "gap_after": 40},  # Raven reveal - tall
    {"id": "p18", "target_h": 600, "gap_after": 20},  # Corvid stare - standard
    {"id": "p19", "target_h": 1000, "gap_after": 40},  # Threat assessment - tall
    {"id": "p20", "target_h": 600, "gap_after": 40},  # Polly fear micro - standard
    {"id": "p21", "target_h": 1000, "gap_after": 120},  # Stakes 72h - tall, EMOTIONAL BREAK
    # ── SCENE 6: TRANSFORMATION ──
    {"id": "p22", "target_h": 1400, "gap_after": 40},  # Transformation - tall two-beat
    {"id": "p23", "target_h": 300, "gap_after": 40},  # Handshake macro - wide
    {"id": "p24", "target_h": 250, "gap_after": 80},  # Breathing - shadows walking
    # ── SCENE 7: THE WORLD ──
    {"id": "p25", "target_h": 1000, "gap_after": 40},  # Infrastructure corridor - tall
    {"id": "p26", "target_h": 1600, "gap_after": 0},  # Aethermoor reveal - SPLASH, slam
    {"id": "p27", "target_h": 600, "gap_after": 40},  # Marcus awe - standard
    {"id": "p28", "target_h": 1000, "gap_after": 40},  # Caw-fee dialogue - tall
    {"id": "p29", "target_h": 900, "gap_after": 60},  # Following Polly - medium-tall
    {"id": "p30", "target_h": 1000, "gap_after": 0},  # Closing - tall, no gap (end)
]


def load_and_resize(panel_id, target_h):
    """Load panel, resize to 800px wide with target height."""
    path = SRC / f"ch01-v3-{panel_id}.png"
    if not path.exists():
        print(f"  MISSING: {path}")
        return None

    img = Image.open(path).convert("RGB")
    orig_w, orig_h = img.size

    # First scale to 800px wide
    ratio = WIDTH / orig_w
    scaled_h = int(orig_h * ratio)

    # If target_h specified, crop/pad to target height
    img = img.resize((WIDTH, scaled_h), Image.LANCZOS)

    if target_h and abs(scaled_h - target_h) > 20:
        # Create target-sized canvas and center the image
        canvas = Image.new("RGB", (WIDTH, target_h), BG_COLOR)
        if scaled_h > target_h:
            # Crop from center
            top = (scaled_h - target_h) // 2
            cropped = img.crop((0, top, WIDTH, top + target_h))
            canvas.paste(cropped, (0, 0))
        else:
            # Pad with dark background
            top = (target_h - scaled_h) // 2
            canvas.paste(img, (0, top))
        return canvas
    return img


def assemble():
    """Assemble all panels into a single vertical strip."""
    panels = []
    total_h = 0

    print(f"Assembling {len(SEQUENCE)} panels into vertical strip...")
    print(f"Width: {WIDTH}px\n")

    for entry in SEQUENCE:
        pid = entry["id"]
        target_h = entry["target_h"]
        gap = entry["gap_after"]

        img = load_and_resize(pid, target_h)
        if img is None:
            continue

        panels.append({"img": img, "gap": gap, "id": pid})
        total_h += img.height + gap
        print(f"  {pid}: {img.width}x{img.height} + {gap}px gap")

    print(f"\nTotal strip height: {total_h}px")
    print(f"Estimated scroll screens (at 800px viewport): {total_h / 800:.1f}")

    # Assemble
    strip = Image.new("RGB", (WIDTH, total_h), BG_COLOR)
    y = 0
    for p in panels:
        strip.paste(p["img"], (0, y))
        y += p["img"].height + p["gap"]

    # Save full strip
    strip_path = OUT / "ch01-v3-strip.png"
    strip.save(strip_path, "PNG")
    print(f"\nFull strip: {strip_path} ({strip.width}x{strip.height})")

    # Also save as JPEG for smaller file size
    strip_jpg = OUT / "ch01-v3-strip.jpg"
    strip.save(strip_jpg, "JPEG", quality=92)
    print(f"JPEG strip: {strip_jpg}")

    # Slice into platform-ready chunks (max 1280px tall per slice)
    slice_dir = OUT / "ch01-v3-slices"
    slice_dir.mkdir(exist_ok=True)
    slice_h = 1280
    slice_count = 0
    for sy in range(0, strip.height, slice_h):
        box = (0, sy, WIDTH, min(sy + slice_h, strip.height))
        sl = strip.crop(box)
        slice_count += 1
        sl_path = slice_dir / f"ch01-v3-slice-{slice_count:03d}.jpg"
        sl.save(sl_path, "JPEG", quality=92)

    print(f"Slices: {slice_count} files in {slice_dir}")

    # Save assembly manifest
    manifest = {
        "version": "v3",
        "width": WIDTH,
        "total_height": total_h,
        "panel_count": len(panels),
        "slice_count": slice_count,
        "scroll_screens": round(total_h / 800, 1),
        "panels": [{"id": p["id"], "height": p["img"].height, "gap_after": p["gap"]} for p in panels],
    }
    manifest_path = OUT / "ch01-v3-assembly-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}")

    return strip


if __name__ == "__main__":
    assemble()
