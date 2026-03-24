"""Generate Chapter 1 manhwa panels using SDXL Turbo on local GPU."""

import os
import sys
import time
import json
import torch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "kindle-app" / "www" / "manhwa" / "ch01" / "gen"
OUT.mkdir(parents=True, exist_ok=True)

STYLE = "manhwa webtoon panel, clean linework, soft atmospheric shading, Korean manhwa style, high quality digital art"

PANELS = [
    {
        "id": "p01",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Close-up of a coffee mug with a brown residue ring, sitting on a desk next to a glowing green terminal. 3:14 AM shown on a small clock. Dark office, only monitor light. Moody, noir atmosphere.",
    },
    {
        "id": "p02",
        "w": 1280,
        "h": 720,
        "prompt": f"{STYLE}. Wide shot of an Asian-American man in his 30s hunched over three monitors in a dark server room. Green terminal glow on his face, bags under his eyes. Fluorescent lights off. Isolation and focus.",
    },
    {
        "id": "p03",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Extreme close-up of a computer screen showing scrolling green text logs. One line highlighted in yellow: Line 4847. The reflection of a man's eyes visible in the monitor glass.",
    },
    {
        "id": "p04",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. A man's hands on a keyboard, typing intensely. The screen shows a network routing diagram with one unauthorized pathway glowing red among normal blue routes. Dramatic lighting from below.",
    },
    {
        "id": "p05",
        "w": 1280,
        "h": 720,
        "prompt": f"{STYLE}. IMPACT panel. The entire screen goes WHITE. The man recoils from his desk, hands up, chair sliding back. Pure white engulfs everything — walls, ceiling, floor. Overexposure effect, blinding.",
    },
    {
        "id": "p06",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. A man floating in pure white void, body twisting, expression of shock and terror. No ground, no walls, no reference points. His office clothes rumpled. Abstract geometric patterns faintly visible in the whiteness.",
    },
    {
        "id": "p07",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. KINETIC falling panel. A man plummeting through layers of abstract reality — colors, mathematical symbols, geodesic patterns, frequency waves. Motion blur. His body is a data point being transmitted through a system.",
    },
    {
        "id": "p08",
        "w": 1280,
        "h": 720,
        "prompt": f"{STYLE}. A man lying face-down on cold stone floor. Crystal formations grow from the walls and ceiling, refracting soft sourceless light. Ancient library shelves stretch upward into darkness. Dust motes float in the light.",
    },
    {
        "id": "p09",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Close-up of a large raven with glossy black-violet feathers perched on a crystal shelf. It wears a tiny graduation cap at a jaunty angle, a monocle over one eye, and a black silk bowtie. Its obsidian eyes stare down with sharp intelligence. Crystal bookshelves behind.",
    },
    {
        "id": "p10",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Shot-reverse-shot. Top half: the raven looking down imperiously. Bottom half: the man on the floor looking up in disbelief. Crystal library background. The scale difference between the tiny academic bird and the sprawled human.",
    },
    {
        "id": "p11",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. A raven transforming into a young woman — feathers flowing upward like ink in water, shape stretching and reorganizing. Wings extending, body lengthening. Mid-transformation, half bird half human. Magical but mechanical, like a window being resized.",
    },
    {
        "id": "p12",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. A young woman with glossy black feather-hair cascading down her shoulders. Wings folded against her back. Her eyes are polished obsidian — inhuman, sharp, reflective. She extends a hand downward toward the viewer. Crystal library behind her.",
    },
    {
        "id": "p13",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. The man takes the woman's hand. Their hands clasp. Warm amber crystal light around them. Her grip is strong. He looks up at her with cautious trust. She looks down with layered annoyance masking concern.",
    },
    {
        "id": "p14",
        "w": 1280,
        "h": 720,
        "prompt": f"{STYLE}. A crystal corridor stretching ahead. Walls of crystallized light, transparent floors. Doorways appear and vanish. The feathered woman walks ahead, wings folded. The man follows. Soft ticking sound visualized as subtle concentric rings in the crystal.",
    },
    {
        "id": "p15",
        "w": 1280,
        "h": 720,
        "prompt": f"{STYLE}. SPECTACLE panel. View through a gap in the crystal corridor. A vast alien landscape: violet-gold aurora sky, floating landmasses with grass growing upside down, rivers of pale blue luminescence, crystal bridges between hovering mountains. Breathtaking impossible geography.",
    },
    {
        "id": "p16",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Close-up of the man's face in profile, mouth open, staring out at the impossible landscape. Aurora light reflected in his eyes. Expression of pure awe and vertigo. Wind blowing his hair slightly.",
    },
    {
        "id": "p17",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. The feathered woman looking back over her shoulder at the man, head tilted at a bird-like angle. Her expression is amused but urgent. Crystal corridor behind her. Text would read: Do you have coffee here?",
    },
    {
        "id": "p18",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Close-up of the woman's face. Obsidian eyes studying the man. Her feathers smooth down along her shoulders — a gesture of something softer than annoyance. Warm amber light. A hint of a smile forming.",
    },
    {
        "id": "p19",
        "w": 1280,
        "h": 720,
        "prompt": f"{STYLE}. The woman walking ahead through the crystal corridor, wings folded, silhouetted against warm light. The man follows a few steps behind. Long shadows stretch on the transparent floor. A journey beginning.",
    },
    {
        "id": "p20",
        "w": 720,
        "h": 1280,
        "prompt": f"{STYLE}. Final panel. The man glances back once at the spot where he arrived — a faint warmth impression on the cold stone. Then turns forward, following the feathered woman into the light. His expression: resolve masking fear. The corridor ahead glows with promise and danger.",
    },
]


def main():
    from diffusers import AutoPipelineForText2Image

    print(f"Loading SDXL Turbo...")
    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe = pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)

    print(f"Generating {len(PANELS)} panels...")
    results = []
    for i, p in enumerate(PANELS):
        t0 = time.time()
        out_path = OUT / f"{p['id']}.png"
        print(f"  [{i+1}/{len(PANELS)}] {p['id']} ({p['w']}x{p['h']})...", end=" ", flush=True)

        image = pipe(
            prompt=p["prompt"],
            width=p["w"],
            height=p["h"],
            num_inference_steps=4,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(2000 + i),
        ).images[0]

        image.save(str(out_path))
        elapsed = time.time() - t0
        size_kb = os.path.getsize(out_path) / 1024
        print(f"{elapsed:.1f}s, {size_kb:.0f}KB")
        results.append({"id": p["id"], "path": str(out_path), "elapsed": round(elapsed, 1)})

        # Clear CUDA cache between panels
        torch.cuda.empty_cache()

    # Save manifest
    manifest = OUT / "manifest.json"
    with open(manifest, "w") as f:
        json.dump(
            {"chapter": "ch01", "panels": results, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}, f, indent=2
        )
    print(f"\nDone! {len(results)} panels saved to {OUT}")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()
