"""
Run this on Google Colab with a GPU runtime.

Upload panel_prompts/ folder from your local machine, or clone the repo.
This script reads the prompt JSONs and generates all panels using SDXL Turbo.

Steps:
1. Open Google Colab (colab.research.google.com)
2. Set runtime to GPU (T4 or better)
3. Upload this script or paste it in a cell
4. Run it
5. Download the generated panels
"""

# Cell 1: Install dependencies
# !pip install diffusers transformers accelerate safetensors torch

import os
import json
import time
import torch
from pathlib import Path
from diffusers import AutoPipelineForText2Image

# Cell 2: Config
PROMPTS_DIR = Path("panel_prompts")  # Upload this folder from your local machine
OUTPUT_DIR = Path("generated_panels")
OUTPUT_DIR.mkdir(exist_ok=True)

# Cell 3: Load model
print("Loading SDXL Turbo...")
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sdxl-turbo",
    torch_dtype=torch.float16,
    variant="fp16",
)
pipe = pipe.to("cuda")
pipe.set_progress_bar_config(disable=False)
print(f"Model loaded. GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# Cell 4: Generate all panels
prompt_files = sorted(PROMPTS_DIR.glob("*_prompts.json"))
print(f"Found {len(prompt_files)} chapter prompt files")

total_generated = 0
total_skipped = 0
t0_global = time.time()

for pf in prompt_files:
    with open(pf) as f:
        chapter_data = json.load(f)

    ch_id = chapter_data["chapter_id"]
    ch_dir = OUTPUT_DIR / ch_id
    ch_dir.mkdir(exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  {ch_id}: {chapter_data.get('title', '')[:50]}")
    print(f"  {len(chapter_data['panels'])} panels")
    print(f"{'='*50}")

    results = []
    for i, panel in enumerate(chapter_data["panels"]):
        out_path = ch_dir / f"{panel['id']}.png"

        if out_path.exists():
            print(f"  [{i+1}] {panel['id']} — exists, skipping")
            total_skipped += 1
            results.append({"id": panel["id"], "path": str(out_path), "skipped": True})
            continue

        t0 = time.time()
        print(
            f"  [{i+1}/{len(chapter_data['panels'])}] {panel['id']} ({panel['w']}x{panel['h']})...", end=" ", flush=True
        )

        image = pipe(
            prompt=panel["prompt"],
            width=panel["w"],
            height=panel["h"],
            num_inference_steps=4,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(4000 + total_generated),
        ).images[0]

        image.save(str(out_path))
        elapsed = time.time() - t0
        size_kb = os.path.getsize(out_path) / 1024
        print(f"{elapsed:.1f}s, {size_kb:.0f}KB")
        total_generated += 1
        results.append({"id": panel["id"], "path": str(out_path), "elapsed": round(elapsed, 1)})

        torch.cuda.empty_cache()

    # Save chapter manifest
    manifest = ch_dir / "manifest.json"
    with open(manifest, "w") as f:
        json.dump(
            {
                "chapter": ch_id,
                "title": chapter_data.get("title", ""),
                "panels": results,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            f,
            indent=2,
        )

elapsed_total = time.time() - t0_global
print(f"\n{'='*50}")
print(f"  COMPLETE")
print(f"  Generated: {total_generated} panels")
print(f"  Skipped: {total_skipped} panels")
print(f"  Total time: {elapsed_total:.0f}s ({elapsed_total/60:.1f}m)")
print(f"  Output: {OUTPUT_DIR}")
print(f"{'='*50}")

# Cell 5: Zip for download
import shutil

shutil.make_archive("six_tongues_panels", "zip", OUTPUT_DIR)
print(f"Download: six_tongues_panels.zip ({os.path.getsize('six_tongues_panels.zip')/1024/1024:.1f} MB)")

# In Colab, run this to download:
# from google.colab import files
# files.download("six_tongues_panels.zip")
