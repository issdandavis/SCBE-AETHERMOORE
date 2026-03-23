from __future__ import annotations

from copy import deepcopy
import json
import textwrap
from pathlib import Path

from scripts.webtoon_gen import compile_panel_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "artifacts" / "webtoon" / "panel_prompts"
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "webtoon_panel_generation_embedded_colab.ipynb"


def lines(text: str) -> list[str]:
    return [f"{line}\n" for line in text.strip("\n").splitlines()]


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": lines(source),
    }


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines(source),
    }


def build_prompt_pack() -> tuple[list[dict], int]:
    prompt_files = sorted(PROMPTS_DIR.glob("*_prompts.json"))
    chapters: list[dict] = []
    total_panels = 0

    for prompt_file in prompt_files:
        chapter = json.loads(prompt_file.read_text(encoding="utf-8"))
        chapter_copy = deepcopy(chapter)
        panels = []
        for panel in chapter_copy.get("panels", []):
            panel_copy = deepcopy(panel)
            panel_copy["compiled_prompt"] = compile_panel_prompt(panel_copy, chapter_copy)
            panels.append(panel_copy)
        chapter_copy["panels"] = panels
        chapters.append(chapter_copy)
        total_panels += len(chapter.get("panels", []))

    if not chapters:
        raise FileNotFoundError(f"No prompt files found in {PROMPTS_DIR}")

    return chapters, total_panels


def build_notebook(chapters: list[dict], total_panels: int) -> dict:
    prompt_pack_json = json.dumps(chapters, indent=2, ensure_ascii=False)

    embedded_cell = f"""
PROMPT_PACK = json.loads(r'''{prompt_pack_json}''')
print(f"Embedded chapters: {{len(PROMPT_PACK)}}")
print(f"Embedded panels: {{sum(len(ch['panels']) for ch in PROMPT_PACK)}}")
print("Sample chapters:", ", ".join(ch["chapter_id"] for ch in PROMPT_PACK[:5]))
"""

    setup_cell = """
from pathlib import Path
import json
import time

USE_GOOGLE_DRIVE = True
DRIVE_ROOT = "SCBE/webtoon_offload"
RUN_NAME = time.strftime("panels_%Y%m%d_%H%M%S")
ONLY_CHAPTERS = None  # Example: ["ch01", "ch02"]
MAX_PANELS = None     # Example: 10 for a smoke run
DOWNLOAD_ZIP_TO_LOCAL = False

base_dir = Path("/content")
drive_dir = None

if USE_GOOGLE_DRIVE:
    try:
        from google.colab import drive

        drive.mount("/content/drive", force_remount=False)
        drive_dir = Path("/content/drive/MyDrive") / DRIVE_ROOT / RUN_NAME
        drive_dir.mkdir(parents=True, exist_ok=True)
        base_dir = drive_dir
        print(f"Drive output: {drive_dir}")
    except Exception as exc:
        print(f"Drive mount unavailable, falling back to local Colab storage: {exc}")

work_dir = base_dir / "webtoon_panel_run"
work_dir.mkdir(parents=True, exist_ok=True)
output_dir = work_dir / "generated_panels"
output_dir.mkdir(exist_ok=True)

selected_pack = PROMPT_PACK
if ONLY_CHAPTERS:
    only = set(ONLY_CHAPTERS)
    selected_pack = [ch for ch in PROMPT_PACK if ch["chapter_id"] in only]

manifest = {
    "run_name": RUN_NAME,
    "chapters": len(selected_pack),
    "total_panels": sum(len(ch["panels"]) for ch in selected_pack),
    "drive_enabled": bool(drive_dir),
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
manifest_path = work_dir / "embedded_prompt_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps(manifest, indent=2))
"""

    install_cell = """
!pip install -q diffusers transformers accelerate safetensors torch
"""

    load_model_cell = """
import torch
from diffusers import AutoPipelineForText2Image

MODEL_ID = "stabilityai/sdxl-turbo"
NUM_INFERENCE_STEPS = 4
GUIDANCE_SCALE = 0.0
SEED_BASE = 4000

print("Loading SDXL Turbo...")
pipe = AutoPipelineForText2Image.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    variant="fp16",
)
pipe = pipe.to("cuda")
pipe.set_progress_bar_config(disable=False)

print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
"""

    generate_cell = """
import os
import time
import json

total_generated = 0
total_skipped = 0
total_seen = 0
t0_global = time.time()

for chapter in selected_pack:
    chapter_dir = output_dir / chapter["chapter_id"]
    chapter_dir.mkdir(exist_ok=True)
    chapter_results = []

    panels = chapter["panels"]
    if MAX_PANELS is not None:
        panels = panels[:MAX_PANELS]

    print("\\n" + "=" * 60)
    print(f"{chapter['chapter_id']}: {chapter.get('title', '')[:70]}")
    print(f"Panels in run: {len(panels)}")
    print("=" * 60)

    for idx, panel in enumerate(panels, start=1):
        total_seen += 1
        out_path = chapter_dir / f"{panel['id']}.png"

        if out_path.exists():
            print(f"  [{idx}] {panel['id']} - exists, skipping")
            total_skipped += 1
            chapter_results.append({"id": panel["id"], "path": str(out_path), "skipped": True})
            continue

        print(
            f"  [{idx}/{len(panels)}] {panel['id']} ({panel['w']}x{panel['h']})...",
            end=" ",
            flush=True,
        )
        t0 = time.time()

        image = pipe(
            prompt=panel.get("compiled_prompt") or panel["prompt"],
            width=panel["w"],
            height=panel["h"],
            num_inference_steps=NUM_INFERENCE_STEPS,
            guidance_scale=GUIDANCE_SCALE,
            generator=torch.Generator("cuda").manual_seed(SEED_BASE + total_generated),
        ).images[0]

        image.save(str(out_path))
        elapsed = time.time() - t0
        size_kb = os.path.getsize(out_path) / 1024
        print(f"{elapsed:.1f}s, {size_kb:.0f}KB")

        total_generated += 1
        chapter_results.append(
            {
                "id": panel["id"],
                "path": str(out_path),
                "elapsed": round(elapsed, 2),
                "width": panel["w"],
                "height": panel["h"],
            }
        )

        torch.cuda.empty_cache()

    chapter_manifest = {
        "chapter": chapter["chapter_id"],
        "title": chapter.get("title", ""),
        "panel_count": len(chapter_results),
        "panels": chapter_results,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (chapter_dir / "manifest.json").write_text(json.dumps(chapter_manifest, indent=2), encoding="utf-8")

elapsed_total = time.time() - t0_global
summary = {
    "generated": total_generated,
    "skipped": total_skipped,
    "seen": total_seen,
    "elapsed_seconds": round(elapsed_total, 1),
    "elapsed_minutes": round(elapsed_total / 60, 2),
    "output_dir": str(output_dir),
}
(work_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("\\n" + json.dumps(summary, indent=2))
"""

    archive_cell = """
import os
import shutil

archive_path = shutil.make_archive(str(work_dir / "six_tongues_panels"), "zip", output_dir)
print(f"Archive: {archive_path}")
print(f"Archive size: {os.path.getsize(archive_path) / 1024 / 1024:.1f} MB")

if DOWNLOAD_ZIP_TO_LOCAL:
    try:
        from google.colab import files

        files.download(archive_path)
    except Exception as exc:
        print(f"Download skipped: {exc}")
"""

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {
                "provenance": [],
                "gpuType": "T4",
                "collapsed_sections": [],
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
            },
            "language_info": {
                "name": "python",
            },
            "accelerator": "GPU",
        },
        "cells": [
            markdown_cell(
                textwrap.dedent(
                    f"""
                    # Webtoon Panel Generation - Embedded Remote Offload

                    This notebook is the remote-first version of the panel generator.

                    It already embeds:
                    - {len(chapters)} chapter prompt files
                    - {total_panels} total panel prompts

                    What it fixes:
                    - no separate prompt-pack upload
                    - save outputs to Google Drive by default
                    - resume by skipping any panel image that already exists
                    - keep the heavy generation on Colab GPU instead of your local machine
                    """
                )
            ),
            code_cell("import json"),
            code_cell(embedded_cell),
            code_cell(setup_cell),
            code_cell(install_cell),
            code_cell(load_model_cell),
            code_cell(generate_cell),
            code_cell(archive_cell),
        ],
    }
    return notebook


def main() -> None:
    chapters, total_panels = build_prompt_pack()
    notebook = build_notebook(chapters, total_panels)
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {NOTEBOOK_PATH}")
    print(f"Chapters: {len(chapters)}")
    print(f"Panels: {total_panels}")


if __name__ == "__main__":
    main()
