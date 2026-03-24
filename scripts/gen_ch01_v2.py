"""
Chapter 1 Panel Generation Script v2
Source of truth: artifacts/webtoon/ch01_adaptation_script_v2.md
Generates 13 panels (9 NEW + 4 REGENERATE) using Imagen 4.0
"""

import os
import sys
import time
import json
from pathlib import Path

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
OUT_DIR = Path("C:/Users/issda/SCBE-AETHERMOORE/artifacts/webtoon/ch01/v2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "imagen-4.0-generate-001"

# All 13 panels to generate, keyed by panel number from adaptation script
PANELS = {
    "ch01-v2-p01": {
        "title": "The Desk",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, clean linework, soft atmospheric shading, "
            "vertical panel composition. A lonely late-night corporate office at 3:14 AM. "
            "A 32-year-old Asian American man sits hunched forward at a desk with three computer monitors "
            "showing green-on-black terminal code. He wears a dark navy hoodie over a wrinkled white button-down shirt. "
            "The overhead fluorescent lights are OFF — the only light comes from the monitors, "
            "painting his face in green glow. A coffee mug with a brown residue ring sits at his elbow. "
            "Behind him on a shelf: three framed photos catching screen-glow, a dead succulent plant, "
            "stacked papers. Through a glass partition below, a tiny security guard walks alone. "
            "The office is empty, institutional, submarine-like. Atmosphere of exhaustion and isolation. "
            "Dark blues and greens only. No cyberpunk neon. No server racks. Regular corporate office. "
            "High quality digital art, manhwa style."
        ),
    },
    "ch01-v2-p03": {
        "title": "The Shelf - Bryce Memorial",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, clean linework, soft atmospheric shading. "
            "Close-up macro shot of a desk shelf in a dark office, lit only by green computer monitor glow. "
            "Three framed photos on the shelf catching the green light: "
            "first photo shows a woman at a graduation ceremony, "
            "second photo shows a casual group of young tech workers. "
            "Third photo, placed slightly apart from the others, shows a young man with dark brown hair, "
            "short beard, blue eyes, wearing a blue plaid button-down shirt, chin resting on his fist, "
            "warm easy grin like he is about to say something funny. Outdoor setting in that photo. "
            "Next to the photos: a dead succulent plant in a small pot, and a stack of papers. "
            "The shelf feels personal in an otherwise institutional space. "
            "Mood: the only warm things in a cold room. Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p06": {
        "title": "The Hit - Whiteout",
        "status": "REGENERATE",
        "prompt": (
            "manhwa webtoon scene illustration, dramatic impact panel. "
            "A dark office being completely consumed by impossible white light. "
            "A 32-year-old Asian American man in a navy hoodie is half-rising from his office chair, "
            "palms up, bracing against nothing, recoiling in shock — NOT celebrating, NOT reaching upward. "
            "His desk, monitors, and walls are dissolving into blinding white. "
            "A coffee mug on the desk is the last object still casting a shadow. "
            "The white is oversaturated, burning, bloom effect — reality being overwritten, not a computer crash. "
            "Everything bleaching out from the center. "
            "No blue screen. No explosion. No portal. Pure reality-breaking white. "
            "Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p07": {
        "title": "What Do You Intend",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, minimalist panel. "
            "Extreme close-up of a pair of wide-open dark brown eyes against a pure white void. "
            "Only the eyes, bridge of nose, and eyebrows are visible. Everything else is white emptiness. "
            "The eyes express searching, fear, and incomprehension. "
            "Very faint, barely visible ghostly text floats in the white: 'What do you intend?' "
            "The white space feels oppressive and judging, not peaceful. "
            "Minimalist composition, almost entirely white with just the eyes as anchor. "
            "Manhwa style, clean linework, high quality digital art."
        ),
    },
    "ch01-v2-p08": {
        "title": "The Packet - Transmission Fall",
        "status": "REGENERATE",
        "prompt": (
            "manhwa webtoon scene illustration, tall vertical kinetic panel. "
            "A 32-year-old Asian American man in a hoodie falling through layers of abstract space, "
            "NOT a galaxy tunnel. He is falling through visible STRATA like geological layers: "
            "top layer is dissolving binary code and hex numbers, "
            "middle layer has geometric wireframes — geodesic spheres and Poincare disk models, "
            "lower layer has musical notation twisted into colored spirals, "
            "near bottom: six colored glyphs flash past like highway signs "
            "(red-gold, blue-silver, deep purple, white-gold, shadow-black, earth-brown), "
            "bottom layer resolves into crystal architecture forming. "
            "The man looks disoriented, not heroic. He is a data packet being transmitted through a system. "
            "Concentric rings radiate from his body like a sustained tone. "
            "No glasses. Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p09": {
        "title": "Cheek on Stone",
        "status": "REGENERATE",
        "prompt": (
            "manhwa webtoon scene illustration, quiet ground-level panel. "
            "A 32-year-old Asian American man lies face-down on ancient smooth stone floor, "
            "his cheek pressed flat against the cold stone, eyes half-open with relief. "
            "One hand in foreground, fingers splayed on the stone, trembling. "
            "He wears a navy hoodie over a wrinkled button-down. "
            "Behind him, crystal walls rise with shelves carved directly into translucent crystal, "
            "filled with leather-bound books that each have a faint warm glow around their spines. "
            "The ceiling curves upward impossibly high — grown from crystal, not built. "
            "Sourceless soft light refracts through the crystal. Dust motes float in the air. "
            "Ground-level camera angle. Mood: bodily relief after falling through reality. "
            "No glasses. Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p10": {
        "title": "The Archive Breathes",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, tall vertical establishing shot. "
            "Low angle looking UP at a vast crystal library from floor level. "
            "Crystal shelves stretch upward toward a ceiling that might be thirty feet high or infinite. "
            "The crystal formations are organic, grown not carved — natural geometry. "
            "Hundreds of leather-bound books fill the shelves, each with a faint individual warm glow "
            "as if humming at different frequencies. Tiny light halos around each book spine. "
            "The light is sourceless, soft, refracted through translucent crystal — warm amber tones. "
            "No torches, no candles, no gothic arches. Pure crystal architecture. "
            "The room itself feels alive. Dust motes catch the light. "
            "Mood: reverence and unease — the books are signaling, not decorating. "
            "Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p13": {
        "title": "The Stakes - 72 Hours",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, dialogue panel. "
            "In a crystal library archive, a large raven (twice normal size, black-to-violet feathers, "
            "wearing a miniature graduation cap, monocle over one eye, and black silk bowtie) "
            "stands at eye level with a 32-year-old Asian American man who has just stood up. "
            "The man stands because lying down felt like the wrong posture for this conversation. "
            "He wears a navy hoodie over a button-down shirt. "
            "The raven's feathers are subtly pressed flat against her body — a micro-expression of fear, "
            "not for herself but for him. Her obsidian eyes carry concern hidden behind professional delivery. "
            "The man's expression is processing, calculating — engineer receiving bad data, not panicking. "
            "Crystal shelves with glowing books in background. Warm amber crystal light. "
            "Mood: existential stakes delivered plainly. "
            "Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p14": {
        "title": "The Transformation",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, two-beat vertical transformation panel. "
            "TOP HALF: A large raven with black-violet feathers beginning to transform — "
            "feathers flowing UPWARD like ink dispersing in water, the shape stretching and reorganizing. "
            "No flash of light, no magical sparkles, no dramatic effects. "
            "The transformation is casual and efficient, like a computer window being resized. "
            "BOTTOM HALF: A young woman (appears 20) now stands where the raven was. "
            "She has glossy black FEATHERS instead of hair, cascading past her shoulders in an iridescent curtain. "
            "Black wings folded neatly against her back. "
            "Her eyes are polished obsidian — IDENTICAL to the raven's eyes, unchanged. "
            "Her fingers are slightly too long, nails dark and iridescent. "
            "She wears dark formal robes. Her expression is still mildly annoyed. "
            "Crystal archive background. Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p16": {
        "title": "We Have Infrastructure",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, medium-wide corridor panel. "
            "A crystal corridor stretching into the distance. The walls are translucent crystal, "
            "the floor looks transparent but solid. A doorway appears ahead, glowing softly. "
            "Walking ahead: a young woman (appears 20) in dark formal robes with black feathered wings "
            "folded against her back, black feather-hair cascading past shoulders, "
            "her wings slightly spread catching crystal light in prismatic fragments. "
            "Following behind her: a 32-year-old Asian American man in a hoodie and button-down, "
            "leaning forward as he walks — an engineer studying a new system, not cowering. "
            "The corridor feels maintained and functional, not decorative. Infrastructure, not scenery. "
            "Cool crystal blues and warm amber light mixing. "
            "Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p17": {
        "title": "The Impossible - Aethermoor Reveal",
        "status": "REGENERATE",
        "prompt": (
            "manhwa webtoon scene illustration, breathtaking landscape reveal panel. "
            "View through a gap in a crystal corridor wall, looking out at an impossible landscape. "
            "A sky with soft auroral light in violet and gold, pulsing gently. "
            "Below: a river of pale blue LUMINESCENCE (not normal water) winds between structures "
            "that are part building, part mountain. "
            "Several landmasses FLOAT in the air without any visible mechanism — gravity simply paused. "
            "On the undersides of floating landmasses, meadows grow with grass pointing DOWNWARD. "
            "A bridge of crystal arcs between two floating masses, and something with too many legs "
            "walks across it with quiet purpose. "
            "The world feels impossible but COHERENT — designed, inhabited, structural. "
            "Not chaotic fantasy. Organized impossibility. "
            "Manhwa style, high quality digital art."
        ),
    },
    "ch01-v2-p19": {
        "title": "Caw-fee",
        "status": "NEW",
        "prompt": (
            "manhwa webtoon scene illustration, dialogue comedy panel. "
            "In a crystal corridor, a young woman with black feather-hair and small black wings "
            "wearing dark formal robes has stopped mid-stride and turned around, "
            "her head tilted at a sharp bird-like angle, one eyebrow raised in genuine confusion. "
            "Facing her: a 32-year-old Asian American man in a hoodie rubbing the back of his neck, "
            "a small half-smile on his face for the first time. "
            "The moment is warm and human — a relief valve after tension. "
            "She is confused, he is amused. Crystal corridor behind them, warm ambient light. "
            "The energy between them is shifting from guide/subject toward something more equal. "
            "Manhwa style, clean linework, high quality digital art."
        ),
    },
}


def generate_panel(panel_id, panel_data):
    """Generate a single panel using Imagen 4.0."""
    out_path = OUT_DIR / f"{panel_id}.png"
    if out_path.exists():
        print(f"  SKIP {panel_id} (already exists)")
        return True

    print(f"  GEN  {panel_id}: {panel_data['title']} [{panel_data['status']}]")
    try:
        result = client.models.generate_images(
            model=MODEL,
            prompt=panel_data["prompt"],
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
            ),
        )
        if result.generated_images:
            with open(out_path, "wb") as f:
                f.write(result.generated_images[0].image.image_bytes)
            print(f"  OK   {panel_id} -> {out_path}")
            return True
        else:
            print(f"  FAIL {panel_id}: no images returned")
            return False
    except Exception as e:
        print(f"  ERR  {panel_id}: {e}")
        return False


def main():
    # Generate specific panels if passed as args, otherwise all
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PANELS.keys())

    print(f"Chapter 1 v2 Generation — {len(targets)} panels")
    print(f"Model: {MODEL}")
    print(f"Output: {OUT_DIR}")
    print()

    results = {}
    for panel_id in targets:
        if panel_id not in PANELS:
            print(f"  UNKNOWN panel: {panel_id}")
            continue
        ok = generate_panel(panel_id, PANELS[panel_id])
        results[panel_id] = "OK" if ok else "FAIL"
        time.sleep(2)  # rate limit courtesy

    print()
    print("=== Results ===")
    for pid, status in results.items():
        print(f"  {pid}: {status}")

    # Save generation log
    log_path = OUT_DIR / "generation_log.json"
    log = {
        "model": MODEL,
        "panels": {
            pid: {"title": PANELS[pid]["title"], "status": PANELS[pid]["status"], "result": results.get(pid, "SKIPPED")}
            for pid in targets
            if pid in PANELS
        },
    }
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"\nLog saved to {log_path}")


if __name__ == "__main__":
    main()
