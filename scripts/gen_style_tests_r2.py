"""Style consistency tests - Round 2: aspect ratios, two-character, macro, transformation."""

import argparse
from google import genai
from google.genai import types
import os, time
from PIL import Image

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
OUT = "artifacts/webtoon/ch01/style_tests"
MODEL_BY_TIER = {
    "fast": "imagen-4.0-fast-generate-001",
    "standard": "imagen-4.0-generate-001",
    "ultra": "imagen-4.0-ultra-generate-001",
}
DEFAULT_TIER = "standard"

STYLE = (
    "manhwa webtoon illustration, full-width vertical scroll panel, "
    "clean confident linework with soft painterly atmospheric shading, "
    "cinematic camera angle, game-quality character design. "
    "Dynamic composition with Solo Leveling panel flow "
    "and Fog Hill of Five Elements painterly atmosphere. "
)

MARCUS = (
    "Marcus Chen: 32-year-old Asian American man with Chinese heritage, "
    "short dark messy hair, tired dark brown eyes with dark circles underneath, "
    "light stubble on angular jawline, lean desk-worker build not muscular. "
    "Dark navy hoodie unzipped over wrinkled white button-down shirt, dark jeans. "
    "NO glasses ever. "
)

POLLY_RAVEN = (
    "Polly the raven: a fantasy raven TWICE normal raven size, "
    "glossy black-to-violet feathers that drink light, "
    "polished OBSIDIAN mineral eyes that are smooth reflective and unnaturally bright, "
    "wearing miniature graduation cap monocle and black silk bowtie. "
)

tests = {
    "test07_tall_fall": {
        "prompt": (
            STYLE + "TALL VERTICAL composition, portrait orientation. "
            "Color palette: shifting rainbow geometric layers dissolving into warm amber. "
            + MARCUS
            + "Scene: Marcus falling headfirst through layers of abstract space. "
            "Top of image: dissolving binary code and data. "
            "Middle: geodesic wireframes and Poincare disk geometry. "
            "Bottom: crystal formations resolving into architecture. "
            "He is disoriented, arms reaching, a data packet being transmitted. "
            "Camera: top-down, viewer looks down at him falling away. "
            "Mood: dislocation with terrible order. "
            "High quality digital art."
        ),
        "ratio": "9:16",
    },
    "test08_wide_whiteout": {
        "prompt": (
            STYLE + "WIDE LANDSCAPE composition, compressed height for impact. "
            "Color palette: draining from dark office blues to overwhelming pure white. "
            + MARCUS
            + "Scene: Marcus half-rising from his office chair, palms up, bracing against nothing. "
            "The entire office is being consumed by impossible white light from the monitors outward. "
            "Desk edges dissolving. Coffee mug is the last object with a shadow. "
            "The white BURNS, oversaturated bloom effect. Reality is being overwritten. "
            "Camera: frontal, slightly low angle. "
            "Mood: shock, reality re-authenticating. "
            "High quality digital art."
        ),
        "ratio": "16:9",
    },
    "test09_two_char_meeting": {
        "prompt": (
            STYLE
            + "Color palette: warm amber crystal light, soft directionless glow. "
            + MARCUS
            + POLLY_RAVEN
            + "Scene: Marcus on his knees on smooth ancient stone floor, looking up. "
            "Polly the raven perches on a crystal shelf about four feet above his head, "
            "looking down at him with sharp annoyed intelligence. "
            "Behind them: a vast crystal archive library with shelves stretching impossibly high, "
            "leather-bound books with faint warm glow around each spine. "
            "Camera: ground level, showing both characters and the scale of the archive. "
            "Mood: first meeting, absurd dignity meets disoriented engineer. "
            "High quality digital art."
        ),
        "ratio": "3:4",
    },
    "test10_macro_coffee": {
        "prompt": (
            STYLE + "MACRO CLOSE-UP composition, tight crop on a single object. "
            "Color palette: cool blues, dark greens, green terminal glow reflection. "
            "Scene: Extreme close-up of a white ceramic coffee mug on a dark office desk. "
            "The mug has a visible brown residue RING marking the tidal line of the last sip. "
            "The coffee inside is dead black and cold. "
            "Green terminal code is reflected in the liquid surface. "
            "Keyboard edge visible. NO characters, just the mug and desk. "
            "Camera: macro, slightly above, intimate detail shot. "
            "Mood: stale, mineral, tactile and unglamorous. "
            "High quality digital art."
        ),
        "ratio": "1:1",
    },
    "test11_transformation": {
        "prompt": (
            STYLE + "TWO-BEAT VERTICAL panel composition, split into top and bottom halves. "
            "Color palette: warm amber crystal light. "
            "TOP HALF: A large raven with black-violet feathers mid-transformation, "
            "feathers flowing UPWARD like ink dispersing in water. Shape stretching upward. "
            "No sparkles, no flash, no magical girl effects. Casual like resizing a window. "
            "BOTTOM HALF: A young woman now stands where the raven was. "
            "Black FEATHERS as hair cascading past shoulders. Black wings folded against back. "
            "Dark scholarly robes. Polished obsidian mineral eyes IDENTICAL to the raven above. "
            "She extends one hand. Expression: mildly annoyed, practical. "
            "The two halves share the same background and angle, one form flowing into the other. "
            "Mood: casual precision, not spectacle. Utility, not magic. "
            "High quality digital art."
        ),
        "ratio": "9:16",
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run round-2 Imagen style tests.")
    parser.add_argument("tests", nargs="*", help="Optional test ids such as test07_tall_fall")
    parser.add_argument("--tier", choices=sorted(MODEL_BY_TIER.keys()), default=DEFAULT_TIER)
    parser.add_argument("--model", default=None, help="Override the Imagen model id directly")
    parser.add_argument("--out-dir", default=None, help="Output directory override")
    parser.add_argument("--sleep-sec", type=float, default=1.0)
    return parser.parse_args()


def main():
    args = parse_args()
    model = args.model or MODEL_BY_TIER[args.tier]
    out_dir = args.out_dir or os.path.join(OUT, args.tier if not args.model else model.replace("/", "__"))
    os.makedirs(out_dir, exist_ok=True)
    target_ids = args.tests or list(tests.keys())
    print(f"Round 2 style tests — {len(target_ids)} cases")
    print(f"Tier: {args.tier}")
    print(f"Model: {model}")
    print(f"Output: {out_dir}")

    for name in target_ids:
        if name not in tests:
            print(f"SKIP {name}: unknown test id")
            continue
        data = tests[name]
        path = os.path.join(out_dir, f"{name}.png")
        ratio = data.get("ratio", "1:1")
        print(f"GEN {name} (aspect {ratio})...")
        try:
            result = client.models.generate_images(
                model=model,
                prompt=data["prompt"],
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio=ratio,
                ),
            )
            if result.generated_images:
                with open(path, "wb") as f:
                    f.write(result.generated_images[0].image.image_bytes)
                img = Image.open(path)
                print(f"  OK {img.size[0]}x{img.size[1]}")
            else:
                print(f"  FAIL: no image")
        except Exception as e:
            print(f"  ERR: {e}")
        time.sleep(args.sleep_sec)

    print("Round 2 done.")


if __name__ == "__main__":
    main()
