from __future__ import annotations

import argparse
from copy import deepcopy
import json
import textwrap
from pathlib import Path

from scripts.webtoon_gen import compile_panel_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "artifacts" / "webtoon" / "panel_prompts"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "webtoon" / "hf_jobs" / "webtoon_hf_embedded_job.py"
DEFAULT_OUTPUT_REPO = "issdandavis/six-tongues-webtoon-panels"
DEFAULT_MODEL_ID = "black-forest-labs/FLUX.1-schnell"


def prepare_chapters(chapters: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for chapter in chapters:
        chapter_copy = deepcopy(chapter)
        panels = []
        for panel in chapter_copy.get("panels", []):
            panel_copy = deepcopy(panel)
            panel_copy["compiled_prompt"] = compile_panel_prompt(panel_copy, chapter_copy)
            panels.append(panel_copy)
        chapter_copy["panels"] = panels
        prepared.append(chapter_copy)
    return prepared


def _chapter_order(chapter_id: str) -> tuple[int, int]:
    if chapter_id.startswith("ch") and chapter_id[2:].isdigit():
        return (0, int(chapter_id[2:]))
    if chapter_id.startswith("int") and chapter_id[3:].isdigit():
        return (1, int(chapter_id[3:]))
    if chapter_id == "rootlight":
        return (2, 0)
    return (3, 0)


def _synthesize_missing_prompt_pack(existing_by_id: dict[str, dict]) -> dict[str, dict]:
    from scripts.build_ch01_prompts_v4 import build_packet as build_ch01_packet
    from scripts.gen_full_book_panels import (
        DEFAULT_SOURCE_DIR,
        create_panel_prompts_from_chapter,
        get_all_chapters,
        read_chapter,
        repo_relative_path,
    )
    from scripts.webtoon_quality_gate import lookup_episode_metadata

    synthesized = dict(existing_by_id)
    source_dir = DEFAULT_SOURCE_DIR

    if "ch01" not in synthesized:
        synthesized["ch01"] = build_ch01_packet()

    for chapter_ref in get_all_chapters(source_dir):
        chapter_id = chapter_ref["id"]
        if chapter_id in synthesized:
            continue

        chapter_text = read_chapter(chapter_ref["file"], source_dir)
        if not chapter_text:
            continue

        source_markdown = repo_relative_path(source_dir / chapter_ref["file"])
        episode_metadata = lookup_episode_metadata(chapter_id=chapter_id, source_markdown=source_markdown)
        synthesized[chapter_id] = create_panel_prompts_from_chapter(
            chapter_id,
            chapter_text,
            source_markdown=source_markdown,
            episode_metadata=episode_metadata,
        )

    return synthesized


def load_prompt_pack(prompts_dir: Path = PROMPTS_DIR) -> tuple[list[dict], int]:
    prompt_files = sorted(prompts_dir.glob("*_prompts.json"))
    chapters_by_id: dict[str, dict] = {}

    for prompt_file in prompt_files:
        chapter = json.loads(prompt_file.read_text(encoding="utf-8"))
        chapter_id = str(chapter.get("chapter_id") or prompt_file.stem.replace("_prompts", ""))
        chapters_by_id[chapter_id] = chapter

    chapters_by_id = _synthesize_missing_prompt_pack(chapters_by_id)
    chapters = [chapter for _, chapter in sorted(chapters_by_id.items(), key=lambda item: _chapter_order(item[0]))]
    total_panels = sum(len(chapter.get("panels", [])) for chapter in chapters)
    return prepare_chapters(chapters), total_panels


def build_uv_job_script(
    chapters: list[dict],
    *,
    default_output_repo: str = DEFAULT_OUTPUT_REPO,
    default_model_id: str = DEFAULT_MODEL_ID,
) -> str:
    if not chapters:
        raise ValueError("Prompt pack is empty.")

    prompt_pack_json = json.dumps(chapters, indent=2, ensure_ascii=False)
    total_panels = sum(len(ch.get("panels", [])) for ch in chapters)

    header = textwrap.dedent(
        """\
        # /// script
        # dependencies = [
        #   "diffusers>=0.35.0",
        #   "transformers>=4.50.0",
        #   "accelerate>=1.10.0",
        #   "huggingface_hub>=0.34.0",
        #   "safetensors>=0.6.0",
        #   "torch",
        # ]
        # ///
        """
    )

    body = f"""
import argparse
import json
import os
import shutil
import time
from pathlib import Path

import torch
from huggingface_hub import HfApi

PROMPT_PACK = json.loads(r'''{prompt_pack_json}''')
DEFAULT_OUTPUT_REPO = "{default_output_repo}"
DEFAULT_MODEL_ID = "{default_model_id}"


def parse_args():
    parser = argparse.ArgumentParser(description="Remote webtoon panel generation on Hugging Face Jobs")
    parser.add_argument("--output-repo", default=DEFAULT_OUTPUT_REPO, help="Dataset repo for generated outputs")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="Diffusers model id to use")
    parser.add_argument("--run-name", default=time.strftime("panels_%Y%m%d_%H%M%S"), help="Folder prefix in the dataset repo")
    parser.add_argument("--max-panels", type=int, default=None, help="Limit panels per chapter for smoke runs")
    parser.add_argument("--only-chapters", default="", help="Comma-separated chapter ids to include")
    parser.add_argument("--seed-base", type=int, default=4000)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--guidance-scale", type=float, default=0.0)
    return parser.parse_args()


def pick_pipeline(model_id: str):
    if "FLUX.1-schnell" in model_id:
        from diffusers import FluxPipeline

        pipe = FluxPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    else:
        from diffusers import AutoPipelineForText2Image

        pipe = AutoPipelineForText2Image.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )

    pipe = pipe.to("cuda")
    try:
        pipe.set_progress_bar_config(disable=False)
    except Exception:
        pass
    return pipe


def main():
    args = parse_args()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is required inside the job for dataset upload.")

    selected = PROMPT_PACK
    if args.only_chapters:
        keep = {{part.strip() for part in args.only_chapters.split(",") if part.strip()}}
        selected = [chapter for chapter in selected if chapter["chapter_id"] in keep]

    if not selected:
        raise RuntimeError("No chapters selected for generation.")

    print(f"Embedded chapters: {{len(PROMPT_PACK)}}")
    print(f"Selected chapters: {{len(selected)}}")
    print(f"Selected panels: {{sum(len(ch['panels']) if args.max_panels is None else min(len(ch['panels']), args.max_panels) for ch in selected)}}")
    print(f"Output repo: {{args.output_repo}}")
    print(f"Run name: {{args.run_name}}")
    print(f"Model: {{args.model_id}}")
    print(f"GPU: {{torch.cuda.get_device_name(0)}}")
    print(f"VRAM: {{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}} GB")

    work_dir = Path.cwd() / "webtoon_hf_job"
    output_dir = work_dir / "generated_panels"
    output_dir.mkdir(parents=True, exist_ok=True)

    pipe = pick_pipeline(args.model_id)

    total_generated = 0
    total_seen = 0
    t0_global = time.time()

    for chapter in selected:
        chapter_dir = output_dir / chapter["chapter_id"]
        chapter_dir.mkdir(exist_ok=True)
        chapter_results = []
        panels = chapter["panels"]
        if args.max_panels is not None:
            panels = panels[: args.max_panels]

        print("\\n" + "=" * 60)
        print(f"{{chapter['chapter_id']}}: {{chapter.get('title', '')[:70]}}")
        print(f"Panels in run: {{len(panels)}}")
        print("=" * 60)

        for idx, panel in enumerate(panels, start=1):
            total_seen += 1
            out_path = chapter_dir / f"{{panel['id']}}.png"
            prompt = panel.get("compiled_prompt") or panel.get("prompt") or ""

            print(
                f"  [{{idx}}/{{len(panels)}}] {{panel['id']}} ({{panel['w']}}x{{panel['h']}})...",
                end=" ",
                flush=True,
            )
            t0 = time.time()
            image = pipe(
                prompt,
                width=panel["w"],
                height=panel["h"],
                num_inference_steps=args.steps,
                guidance_scale=args.guidance_scale,
                generator=torch.Generator("cuda").manual_seed(args.seed_base + total_generated),
            ).images[0]
            image.save(str(out_path))
            elapsed = time.time() - t0
            size_kb = os.path.getsize(out_path) / 1024
            print(f"{{elapsed:.1f}}s, {{size_kb:.0f}}KB")
            total_generated += 1
            chapter_results.append({{
                "id": panel["id"],
                "path": str(out_path.relative_to(work_dir)),
                "elapsed": round(elapsed, 2),
                "width": panel["w"],
                "height": panel["h"],
            }})
            torch.cuda.empty_cache()

        (chapter_dir / "manifest.json").write_text(
            json.dumps(
                {{
                    "chapter": chapter["chapter_id"],
                    "title": chapter.get("title", ""),
                    "panels": chapter_results,
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }},
                indent=2,
            ),
            encoding="utf-8",
        )

    elapsed_total = time.time() - t0_global
    summary = {{
        "embedded_chapters": {len(chapters)},
        "embedded_panels": {total_panels},
        "selected_chapters": len(selected),
        "seen": total_seen,
        "generated": total_generated,
        "elapsed_seconds": round(elapsed_total, 1),
        "elapsed_minutes": round(elapsed_total / 60, 2),
        "model_id": args.model_id,
        "output_repo": args.output_repo,
        "run_name": args.run_name,
    }}
    summary_path = work_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    archive_base = work_dir / "six_tongues_panels"
    archive_path = shutil.make_archive(str(archive_base), "zip", output_dir)
    print(f"Archive: {{archive_path}}")

    api = HfApi(token=token)
    api.create_repo(args.output_repo, repo_type="dataset", exist_ok=True)
    api.upload_file(
        path_or_fileobj=archive_path,
        path_in_repo=f"{{args.run_name}}/six_tongues_panels.zip",
        repo_id=args.output_repo,
        repo_type="dataset",
    )
    api.upload_file(
        path_or_fileobj=str(summary_path),
        path_in_repo=f"{{args.run_name}}/run_summary.json",
        repo_id=args.output_repo,
        repo_type="dataset",
    )

    print("\\nUpload complete.")
    print(f"Dataset repo: https://huggingface.co/datasets/{{args.output_repo}}/tree/main/{{args.run_name}}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
"""

    return header + textwrap.dedent(body)


def write_uv_job_script(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    chapters, _ = load_prompt_pack()
    script = build_uv_job_script(chapters)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build embedded Hugging Face Jobs script for webtoon generation")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    chapters, total_panels = load_prompt_pack()
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_uv_job_script(chapters), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "chapters": len(chapters),
                "panels": total_panels,
            }
        )
    )


if __name__ == "__main__":
    main()
