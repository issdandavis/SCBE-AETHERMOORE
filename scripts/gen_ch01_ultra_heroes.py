"""Regenerate 6 hero panels with Imagen 4.0 Ultra for quality comparison."""

from google import genai
from google.genai import types
import os, time
from pathlib import Path
from PIL import Image

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
out = Path("artifacts/webtoon/ch01/v3-ultra")
out.mkdir(parents=True, exist_ok=True)

STYLE = (
    "manhwa webtoon illustration, full-width vertical scroll panel, "
    "clean confident linework with soft painterly atmospheric shading, "
    "cinematic camera angle, game-quality character design. "
    "Dynamic composition with Solo Leveling panel flow "
    "and Fog Hill of Five Elements painterly atmosphere. "
    "Extremely high quality, professional manhwa publication standard, 4K detail. "
)
MARCUS = (
    "Marcus Chen: 32-year-old Asian American man with Chinese heritage, "
    "short dark messy hair, tired dark brown eyes with dark circles underneath, "
    "light stubble on angular jawline, lean desk-worker build not muscular. "
    "Dark navy hoodie unzipped over wrinkled white button-down shirt, dark jeans. "
    "NO glasses ever. "
)
POLLY_RAVEN = (
    "Polly the raven: a fantasy raven TWICE normal raven size knee-height to human, "
    "glossy black-to-violet feathers that drink light, "
    "polished OBSIDIAN mineral eyes smooth reflective and unnaturally bright, "
    "wearing miniature graduation cap at jaunty angle, monocle over one eye, "
    "black silk bowtie neatly knotted at throat. "
)

heroes = {
    "p01-ultra": {
        "aspect": "3:4",
        "prompt": STYLE
        + "Color palette: cool blues, dark greens, warm amber desk lamp accent. "
        + MARCUS
        + "Scene: Over-the-shoulder angle of Marcus at his home desk at 3AM. "
        "His back and head visible, hunched forward looking at ONE large curved monitor "
        "showing green-on-black terminal code. Dark wood desk with papers, notebooks, pen. "
        "Coffee mug with brown residue ring. Warm desk lamp mixing amber with green glow. "
        "City skyline through window. His personal cave, not corporate. "
        "Camera: over-the-shoulder matching book cover. Mood: intimate exhaustion. ",
    },
    "p17-ultra": {
        "aspect": "3:4",
        "prompt": STYLE
        + "Color palette: warm amber, crystal refraction light. "
        + POLLY_RAVEN
        + "Scene: Polly perched on crystal shelf looking down at viewer. "
        "LARGE, imposing, filling upper half of frame. Cap at jaunty angle. "
        "Monocle catches crystal light. Bowtie neatly knotted. "
        "Feathers shift black to deep violet, drinking light. "
        "Crystal archive with glowing leather books stretches infinitely behind. "
        "Camera: LOW ANGLE looking UP. She has all authority. "
        "Mood: most memorable character introduction. Absurd dignity. ",
    },
    "p22-ultra": {
        "aspect": "9:16",
        "prompt": STYLE + "Color palette: warm amber crystal light. "
        "TWO-BEAT VERTICAL panel, same crystal archive background top and bottom. "
        "TOP HALF: Large raven with black-violet feathers mid-transformation. "
        "Feathers flowing UPWARD like dark ink dispersing in water. Dark smoke rising. "
        "No sparkles, no flash. Casual like a window being resized. "
        "BOTTOM HALF: Young woman stands where raven was. "
        "Black FEATHERS as hair, iridescent sheen. Wings folded. Dark scholarly robes. "
        "Obsidian mineral eyes IDENTICAL to raven above. She extends one hand. "
        "Mood: casual precision, utility not spectacle. ",
    },
    "p26-ultra": {
        "aspect": "9:16",
        "prompt": STYLE + "Color palette: violet-gold auroral sky, pale blue luminescence, warm amber. "
        "TALL SPLASH PANEL, painting worthy of a wall. "
        "View through gap in crystal corridor at impossible landscape. "
        "Auroral light violet and gold pulsing. Pale blue luminescent river. "
        "Landmasses FLOAT without mechanism, gravity paused. "
        "Undersides of floating masses have meadows with grass pointing DOWN. "
        "Crystal bridge, something with too many legs crosses it. "
        "Impossible but COHERENT, designed, inhabited. "
        "Crystal corridor walls frame the view. Mood: world-shock. ",
    },
    "p19-ultra": {
        "aspect": "3:4",
        "prompt": STYLE
        + "Color palette: warm amber, crystal refraction. "
        + MARCUS
        + POLLY_RAVEN
        + "Scene: Marcus on knees on ancient stone floor looking up. "
        "Polly on crystal shelf above, LARGE and imposing, looking down. "
        "Height difference emphasizes her authority. "
        "Crystal archive with glowing books stretches to infinity behind. "
        "Dust motes in warm sourceless light. "
        "Camera: ground level, both characters, vast archive. "
        "Mood: first meeting, disoriented engineer meets dignified raven. ",
    },
    "p12-ultra": {
        "aspect": "9:16",
        "prompt": STYLE
        + "Color palette: shifting geometric rainbow dissolving to warm amber. "
        + MARCUS
        + "TALL VERTICAL, reader scrolls through the fall. "
        "Marcus falling through LAYERS like geological strata. "
        "TOP: dissolving binary code. UPPER: geodesic wireframes, Poincare disks. "
        "LOWER: musical notation spirals, frequencies as color. "
        "NEAR BOTTOM: six colored glyphs (red-gold, blue-silver, purple, "
        "white-gold, shadow-black, earth-brown). BOTTOM: crystal architecture. "
        "Marcus disoriented, data packet being routed. Concentric rings from body. "
        "Camera: top-down. Mood: the scroll IS the fall. ",
    },
}

for name, data in heroes.items():
    path = out / f"{name}.png"
    if path.exists():
        print(f"SKIP {name}")
        continue
    print(f"GEN  {name} [Ultra, {data['aspect']}]...")
    try:
        result = client.models.generate_images(
            model="imagen-4.0-ultra-generate-001",
            prompt=data["prompt"],
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio=data["aspect"],
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
    time.sleep(3)

print("\nDone. Check artifacts/webtoon/ch01/v3-ultra/")
