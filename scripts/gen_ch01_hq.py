"""Generate 20 hand-crafted Chapter 1 panels via HF API with locked character descriptions."""

import requests, os, time
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN", "")
headers = {"Authorization": f"Bearer {HF_TOKEN}"}
API = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
OUT = Path("C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/manhwa/ch01/hq")
OUT.mkdir(parents=True, exist_ok=True)

MARCUS = "young Asian-American man, age 32, short messy black hair, no glasses, lean build, rumpled grey dress shirt, dark circles under eyes, sharp observant expression"
POLLY_RAVEN = "enormous raven twice normal size, glossy black-violet iridescent feathers, polished obsidian mineral eyes, tiny graduation cap at jaunty angle, monocle over one eye, black silk bowtie at throat"
POLLY_HUMAN = "young woman with glossy black feather-hair cascading to shoulders, large dark wings folded on back, polished obsidian inhuman eyes, slightly too-long fingers with dark iridescent nails, sharp annoyed expression masking concern"
STYLE = "manhwa webtoon panel, clean confident linework, soft atmospheric gradient shading, no hatching, Korean manhwa style, high quality digital art, cinematic composition"

PANELS = [
    {
        "id": "ch01-hq-p01",
        "prompt": f"{STYLE}. Extreme close-up of a coffee mug with brown residue ring on a desk. Green terminal glow reflects off the ceramic. Clock shows 3:14 AM. Dark empty office. Moody noir atmosphere. No people visible.",
    },
    {
        "id": "ch01-hq-p02",
        "prompt": f"{STYLE}. Wide establishing shot. {MARCUS} hunched over three monitors in a dark server room. Green terminal light paints his face. Fluorescent lights off. Server racks behind glass walls. Complete isolation.",
    },
    {
        "id": "ch01-hq-p03",
        "prompt": f"{STYLE}. Close-up of a computer monitor showing scrolling green code. One line highlighted bright yellow among thousands of green lines. Reflection of dark eyes visible in the monitor glass. Dramatic.",
    },
    {
        "id": "ch01-hq-p04",
        "prompt": f"{STYLE}. {MARCUS} leaning forward intensely, hands on keyboard. Screen shows a network diagram with one unauthorized red pathway glowing among normal blue routes. Green light from below illuminates his determined face.",
    },
    {
        "id": "ch01-hq-p05",
        "prompt": f"{STYLE}. IMPACT panel. Everything goes pure blinding WHITE. A man recoils, hands up, chair flying back. The white engulfs walls ceiling floor everything. Total overexposure. Overwhelming brightness consuming the room.",
    },
    {
        "id": "ch01-hq-p06",
        "prompt": f"{STYLE}. {MARCUS} floating alone in infinite white void. Body twisting in shock. No ground no walls no reference points. Rumpled office clothes. Faint abstract geometric mathematical patterns barely visible in the whiteness.",
    },
    {
        "id": "ch01-hq-p07",
        "prompt": f"{STYLE}. KINETIC vertical falling panel. {MARCUS} plummeting through layers of abstract reality. Swirling colors, mathematical symbols, geodesic wireframe patterns, frequency waves streaking past. Heavy motion blur.",
    },
    {
        "id": "ch01-hq-p08",
        "prompt": f"{STYLE}. {MARCUS} lying face-down on cold ancient stone floor. Crystal formations grow from walls and ceiling, refracting soft warm amber sourceless light. Towering bookshelves of leather volumes stretch upward into darkness. Dust motes float.",
    },
    {
        "id": "ch01-hq-p09",
        "prompt": f"{STYLE}. {POLLY_RAVEN} perched on a crystal shelf four feet above, looking down imperiously. Crystal bookshelves fill the background glowing warm amber. The raven is huge and magnificent and clearly judging.",
    },
    {
        "id": "ch01-hq-p10",
        "prompt": f"{STYLE}. Split panel. TOP HALF: {POLLY_RAVEN} looking down from crystal shelf with sharp intelligent obsidian eyes. BOTTOM HALF: {MARCUS} on the stone floor looking up in total disbelief. Scale difference between bird and human.",
    },
    {
        "id": "ch01-hq-p11",
        "prompt": f"{STYLE}. TRANSFORMATION. A large raven unfolding upward, feathers flowing like ink in water, shape stretching and lengthening. Mid-transformation between bird and human. Wings extending. Magical but mechanical. Warm amber crystal light.",
    },
    {
        "id": "ch01-hq-p12",
        "prompt": f"{STYLE}. {POLLY_HUMAN} standing in warm amber crystal library light. Wings folded elegantly against her back. She extends one hand downward toward the viewer. Expression is layered annoyance masking something softer. Alien and beautiful.",
    },
    {
        "id": "ch01-hq-p13",
        "prompt": f"{STYLE}. Two hands clasping. Close-up of their grip. Her fingers slightly too long with dark iridescent nails. His hand ordinary human. Warm amber light between them. A moment of trust forming. Intimate composition.",
    },
    {
        "id": "ch01-hq-p14",
        "prompt": f"{STYLE}. Wide shot of a crystal corridor stretching ahead. Walls of crystallized light, transparent floors. {POLLY_HUMAN} walks ahead wings folded. {MARCUS} follows a few steps behind. Doorways materialize and vanish. Subtle light rings pulse.",
    },
    {
        "id": "ch01-hq-p15",
        "prompt": f"{STYLE}. SPECTACLE SPLASH. Vast impossible landscape through a gap in crystal corridor. Violet-gold aurora sky. Floating landmasses with upside-down grass. Rivers of pale blue luminescence. Crystal bridges between hovering islands. Breathtaking alien geography.",
    },
    {
        "id": "ch01-hq-p16",
        "prompt": f"{STYLE}. Close-up profile of {MARCUS}. Mouth slightly open. Staring at impossible landscape. Aurora light in violet and gold reflected in his dark eyes. Expression of pure awe mixed with vertigo. Wind in his hair.",
    },
    {
        "id": "ch01-hq-p17",
        "prompt": f"{STYLE}. {POLLY_HUMAN} looking back over her shoulder, head tilted at a sharp bird-like angle. Amused but urgent expression. Crystal corridor behind her. Obsidian eyes catch the light. The moment she hears about coffee.",
    },
    {
        "id": "ch01-hq-p18",
        "prompt": f"{STYLE}. Close-up of {POLLY_HUMAN} face. Obsidian eyes studying someone with ancient evaluation. Feather-hair smooths down along shoulders. Warm amber light. A hint of real smile forming. Five centuries of loss meeting new hope.",
    },
    {
        "id": "ch01-hq-p19",
        "prompt": f"{STYLE}. {POLLY_HUMAN} walking ahead through crystal corridor, wings folded, silhouetted against warm golden light. {MARCUS} follows behind, smaller silhouette. Long shadows on transparent floor. A journey beginning. Two people walking into the unknown.",
    },
    {
        "id": "ch01-hq-p20",
        "prompt": f"{STYLE}. Final panel. {MARCUS} glancing back over his shoulder at the spot where he arrived. Faint warmth on cold stone. Body turned forward, following the light. Expression resolve masking fear masking curiosity. Corridor ahead glows with promise and danger.",
    },
]

print(f"Generating {len(PANELS)} hand-crafted Ch1 panels...")
total = 0
t0 = time.time()

for i, p in enumerate(PANELS):
    out = OUT / f"{p['id']}.png"
    if out.exists():
        print(f"  [{i+1}] {p['id']} exists, skip")
        continue

    for attempt in range(3):
        try:
            resp = requests.post(API, headers=headers, json={"inputs": p["prompt"]}, timeout=120)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(out, "wb") as f:
                    f.write(resp.content)
                total += 1
                elapsed = time.time() - t0
                print(f"  [{i+1}/20] {p['id']} — {len(resp.content)//1024}KB ({elapsed:.0f}s)")
                break
            elif resp.status_code == 429:
                print(f"  Rate limited, waiting 30s...")
                time.sleep(30)
            else:
                print(f"  {p['id']} — {resp.status_code}, retry {attempt+1}")
                time.sleep(5)
        except Exception as e:
            print(f"  {p['id']} — error: {e}, retry {attempt+1}")
            time.sleep(5)

    time.sleep(1)

elapsed = time.time() - t0
print(f"\nDone: {total} panels in {elapsed:.0f}s ({elapsed/60:.1f}m)")
