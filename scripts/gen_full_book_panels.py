"""
Generate manhwa panels for the ENTIRE Six Tongues Protocol book.
Reads each chapter, creates 15-20 panel prompts per chapter, generates images.

Usage:
    python scripts/gen_full_book_panels.py                    # All chapters
    python scripts/gen_full_book_panels.py --chapter ch02     # Single chapter
    python scripts/gen_full_book_panels.py --prompts-only     # Just write prompts, no generation
    python scripts/gen_full_book_panels.py --start ch05       # Start from chapter 5
"""

import os
import sys
import json
import time
import argparse
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = ROOT / "content" / "book" / "reader-edition"
CHAPTERS_DIR = DEFAULT_SOURCE_DIR
OUT_BASE = ROOT / "kindle-app" / "www" / "manhwa"
PROMPTS_DIR = ROOT / "artifacts" / "webtoon" / "panel_prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from webtoon_quality_gate import default_report_path, govern_packet, lookup_episode_metadata
except ImportError:  # pragma: no cover - import path fallback for tests
    from scripts.webtoon_quality_gate import default_report_path, govern_packet, lookup_episode_metadata

STYLE = "manhwa webtoon panel, clean linework, soft atmospheric shading, Korean manhwa style, high quality digital art"

# Character visual anchors (from production bible)
CHARACTERS = {
    "marcus": "Asian-American man early 30s, short dark messy hair, lean desk-worker build, rumpled dress shirt",
    "polly_raven": "large raven twice normal size, glossy black-violet feathers, polished obsidian eyes, graduation cap monocle bowtie",
    "polly_human": "young woman with glossy black feather-hair, wings folded on back, obsidian eyes, slightly too-long fingers",
    "senna": "woman, controlled composure, lower register presence, weary but precise, governor bearing",
    "alexander": "teenager face but grandfather patience, calm steady ageless quality, gentle but firm",
    "bram": "large man, deep gravelly presence, sparse words, maintenance worker hands, no-nonsense",
    "izack": "robed figure, silhouette, pipe smoke, surrounded by dimensional readouts, unreachable depth",
}

# Environment palettes
ENVIRONMENTS = {
    "earth_office": "dark office, green terminal glow, dead fluorescents, server racks behind glass",
    "white_void": "pure white void, no reference points, abstract geometric patterns faintly visible",
    "crystal_library": "crystal formations growing from walls and ceiling, sourceless warm amber light, ancient leather-bound books humming on shelves",
    "crystal_corridor": "crystallized light walls, transparent floors, doorways appearing and vanishing, soft ticking",
    "aethermoor_exterior": "violet-gold aurora sky, floating landmasses, upside-down grass, rivers of pale blue luminescence, crystal bridges",
    "maintenance_shafts": "CA-white conduit glow, iron brackets, utilitarian darkness",
    "civic_terraces": "gold afternoon light, open sky, warm stone",
    "underroot": "bioluminescent root-light, deep mineral gold, wet stone",
    "shardfold": "storm-prismatic light, iron sea, aperiodic quasicrystal cliff geometry",
    "verdant_tithe": "layered emerald shadow, silver pollen, cathedral-dim forest",
    "void_seed_chamber": "shadow-black anti-light, geometric dread, UM darkness",
    "pocket_meadow": "permanent golden-hour, too-green grass, held time, pipe smoke",
}

# Panel types and their visual characteristics
PANEL_TYPES = {
    "ESTABLISHING": "wide shot, environmental detail, sets location",
    "IMPACT": "full-width, compressed height, forces the eye, dramatic moment",
    "KINETIC": "extra-tall vertical, motion blur, movement and action",
    "REVEAL": "two-beat setup-payoff, character or secret shown",
    "SPECTACLE": "full spread, maximum detail, the screenshot panel",
    "QUIET": "simple composition, negative space, breathing room",
    "DIALOGUE": "shot-reverse-shot, expression close-ups, conversation",
    "SPLASH": "series-defining moment, largest panel, most detail",
    "CLOSING": "final panel, emotional resolution, forward momentum",
}

STYLE_SYSTEM = {
    "global_tags": [
        "story-first composition",
        "stable worldbuilding",
        "deliberate style shifts only on key beats",
    ]
}

STYLE_BIBLE = {
    "visual_language": (
        "Korean webtoon / manhwa with cinematic lighting, readable acting, "
        "strong environmental storytelling, and clean panel-to-panel motion."
    ),
    "rules": [
        "Keep environment identity stable inside the active chapter arc.",
        "Preserve character anchors even when pacing or finish changes.",
        "Use spectacle as emphasis instead of flattening every panel into the same intensity.",
    ],
}

GENERATION_PROFILE = {
    "model_id": "black-forest-labs/FLUX.1-schnell",
    "default_steps": 4,
    "guidance_scale": 0.0,
    "seed_mode": "panel-index-offset",
    "trigger_phrases": ["sixtongues_style"],
    "style_adapter": {
        "repo_id": "issdandavis/six-tongues-art-lora",
        "adapter_name": "six-tongues-style",
        "trigger_word": "sixtongues_style",
        "scale": 0.9,
    },
    "require_adapter": False,
}

PALETTE_BY_ENV = {
    "earth_office": "cool blues, dead office greens, green terminal glow accents",
    "white_void": "pure white with overexposed edges and faint auroral data traces",
    "crystal_library": "warm amber crystal light with grounded stone neutrals",
    "crystal_corridor": "warm amber crystal light mixed with cool blue refractions",
    "aethermoor_exterior": "violet-gold sky, pale blue luminescence, warm amber crystal",
    "maintenance_shafts": "cold conduit white, iron gray, utility shadows",
    "civic_terraces": "gold afternoon light, warm stone, civic calm",
    "underroot": "bioluminescent root-light, deep mineral gold, wet stone",
    "shardfold": "storm-prismatic light, iron sea slate, quasicrystal glare",
    "verdant_tithe": "emerald shadow, silver pollen, forest cathedral dimness",
    "void_seed_chamber": "shadow-black anti-light, geometric dread, void contrast",
    "pocket_meadow": "permanent golden-hour warmth, too-green grass, soft held-time haze",
}

ARC_LOCKS_BY_ENV = {
    "earth_office": "earth_protocol_noir",
    "white_void": "protocol_transmission",
    "crystal_library": "archive_grounded_magic",
    "crystal_corridor": "archive_grounded_magic",
    "aethermoor_exterior": "aethermoor_world_reveal",
}

CORNERSTONE_STYLE_BY_TYPE = {
    "ESTABLISHING": "standard_dialogue",
    "IMPACT": "dark_gritty",
    "KINETIC": "dark_gritty",
    "REVEAL": "ethereal_divine",
    "SPECTACLE": "ethereal_divine",
    "QUIET": "standard_dialogue",
    "DIALOGUE": "standard_dialogue",
    "SPLASH": "ethereal_divine",
    "CLOSING": "standard_dialogue",
}

MOOD_BY_TYPE = {
    "ESTABLISHING": "introspective",
    "IMPACT": "tension",
    "KINETIC": "action",
    "REVEAL": "awe",
    "SPECTACLE": "awe",
    "QUIET": "introspective",
    "DIALOGUE": "drama",
    "SPLASH": "awe",
    "CLOSING": "slice_of_life",
}

PANEL_FLEX_BY_TYPE = {
    "IMPACT": "painterly_impact",
    "SPECTACLE": "painterly_impact",
}

CAMERA_BY_TYPE = {
    "ESTABLISHING": "wide establishing shot",
    "IMPACT": "compressed wide impact frame",
    "KINETIC": "tall vertical kinetic frame",
    "REVEAL": "two-beat reveal frame",
    "SPECTACLE": "landscape spectacle panel",
    "QUIET": "breathing panel with negative space",
    "DIALOGUE": "shot-reverse-shot with clear acting",
    "SPLASH": "full splash composition",
    "CLOSING": "closing beat frame with forward momentum",
}


def repo_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def build_panel_entry(
    *,
    chapter_id,
    panel_num,
    ptype,
    width,
    height,
    env,
    char_desc,
    chars,
    scene_summary,
    prompt_suffix,
):
    env_desc = ENVIRONMENTS.get(env, "")
    scene_prompt = f"{env_desc}. {char_desc}. {scene_summary}. {prompt_suffix}."
    prompt = f"{STYLE}. {scene_prompt}"

    panel = {
        "id": f"{chapter_id}-p{panel_num:02d}",
        "type": ptype,
        "w": width,
        "h": height,
        "prompt": prompt,
        "scene_prompt": scene_prompt,
        "scene_summary": scene_summary[:200],
        "environment": env,
        "characters": chars,
        "arc_lock": ARC_LOCKS_BY_ENV.get(env),
        "cornerstone_style": CORNERSTONE_STYLE_BY_TYPE.get(ptype, "standard_dialogue"),
        "mood": MOOD_BY_TYPE.get(ptype, "introspective"),
        "camera_angle": CAMERA_BY_TYPE.get(ptype),
        "style_metadata": {
            "color_palette": PALETTE_BY_ENV.get(env),
            "camera_angle": CAMERA_BY_TYPE.get(ptype),
            "composition": PANEL_TYPES.get(ptype),
            "mood": MOOD_BY_TYPE.get(ptype, "introspective"),
            "character_anchor": char_desc,
        },
    }

    panel_flex = PANEL_FLEX_BY_TYPE.get(ptype)
    if panel_flex:
        panel["panel_flex"] = panel_flex
        panel["style_metadata"]["panel_flex"] = panel_flex

    return panel


def read_chapter(filename, chapters_dir=CHAPTERS_DIR):
    """Read a chapter file and return its text."""
    path = chapters_dir / filename
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def extract_scenes(text):
    """Extract key scenes from chapter text for panel creation."""
    scenes = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]

    # Find scene breaks (marked by * * * or ---)
    current_scene = []
    for para in paragraphs:
        if para.strip() in ("* * *", "---", "***"):
            if current_scene:
                scenes.append("\n\n".join(current_scene))
                current_scene = []
        else:
            current_scene.append(para)
    if current_scene:
        scenes.append("\n\n".join(current_scene))

    return scenes


def create_panel_prompts_from_chapter(
    chapter_id,
    text,
    target_panels=20,
    *,
    source_markdown=None,
    episode_metadata=None,
):
    """Create panel prompts from chapter text using heuristic scene extraction."""
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1) if title_match else chapter_id

    scenes = extract_scenes(text)
    panels = []
    panel_num = 0

    # Distribute panels across scenes
    _panels_per_scene = max(1, target_panels // max(len(scenes), 1))

    for scene_idx, scene in enumerate(scenes):
        lines = [l.strip() for l in scene.split("\n") if l.strip()]
        if not lines:
            continue

        # Pick key moments from each scene
        # First line = establishing shot
        if panel_num < target_panels:
            panel_num += 1
            # Detect environment
            env = "crystal_library"  # default
            scene_lower = scene.lower()
            if any(w in scene_lower for w in ["terminal", "monitor", "office", "server", "keyboard"]):
                env = "earth_office"
            elif any(w in scene_lower for w in ["white", "void", "light", "dissolve"]):
                env = "white_void"
            elif any(w in scene_lower for w in ["corridor", "hallway", "passage"]):
                env = "crystal_corridor"
            elif any(w in scene_lower for w in ["sky", "aurora", "floating", "landscape", "mountain"]):
                env = "aethermoor_exterior"
            elif any(w in scene_lower for w in ["underroot", "root", "tunnel"]):
                env = "underroot"
            elif any(w in scene_lower for w in ["forest", "verdant", "trees"]):
                env = "verdant_tithe"
            elif any(w in scene_lower for w in ["void seed", "shadow", "darkness", "geometric dread"]):
                env = "void_seed_chamber"
            elif any(w in scene_lower for w in ["meadow", "golden hour", "pipe"]):
                env = "pocket_meadow"
            elif any(w in scene_lower for w in ["shard", "cliff", "storm", "iron sea"]):
                env = "shardfold"
            elif any(w in scene_lower for w in ["terrace", "civic", "afternoon"]):
                env = "civic_terraces"
            elif any(w in scene_lower for w in ["maintenance", "shaft", "conduit"]):
                env = "maintenance_shafts"

            # Detect characters present
            chars = []
            if "marcus" in scene_lower or "chen" in scene_lower:
                chars.append("marcus")
            if "polly" in scene_lower or "raven" in scene_lower:
                if "feather" in scene_lower and "hair" in scene_lower:
                    chars.append("polly_human")
                else:
                    chars.append("polly_raven")
            if "senna" in scene_lower:
                chars.append("senna")
            if "alexander" in scene_lower:
                chars.append("alexander")
            if "bram" in scene_lower:
                chars.append("bram")
            if "izack" in scene_lower:
                chars.append("izack")

            char_desc = ". ".join(CHARACTERS.get(c, "") for c in chars[:2])

            # Determine panel type based on content
            if scene_idx == 0:
                ptype = "ESTABLISHING"
            elif any(w in scene_lower for w in ["white", "impact", "explosion", "scream", "fell", "crash"]):
                ptype = "IMPACT"
            elif any(w in scene_lower for w in ["running", "falling", "chase", "fled"]):
                ptype = "KINETIC"
            elif any(w in scene_lower for w in ["revealed", "saw", "realized", "understood", "transform"]):
                ptype = "REVEAL"
            elif any(w in scene_lower for w in ["impossible", "vast", "cathedral", "landscape", "spectacle"]):
                ptype = "SPECTACLE"
            elif any(w in scene_lower for w in ["said", "asked", "replied", "spoke", "muttered"]):
                ptype = "DIALOGUE"
            elif scene_idx == len(scenes) - 1:
                ptype = "CLOSING"
            else:
                ptype = "QUIET"

            # Extract a key sentence for the prompt
            key_sentences = [l for l in lines if len(l) > 30 and not l.startswith("*")][:3]
            scene_summary = key_sentences[0][:150] if key_sentences else lines[0][:150]

            # Determine dimensions
            if ptype in ("ESTABLISHING", "SPECTACLE", "SPLASH"):
                w, h = 1280, 720
            else:
                w, h = 720, 1280

            panels.append(
                build_panel_entry(
                    chapter_id=chapter_id,
                    panel_num=panel_num,
                    ptype=ptype,
                    width=w,
                    height=h,
                    env=env,
                    char_desc=char_desc,
                    chars=chars,
                    scene_summary=scene_summary,
                    prompt_suffix=PANEL_TYPES.get(ptype, ""),
                )
            )

        # Add more panels for longer scenes
        if len(lines) > 10 and panel_num < target_panels:
            # Dialogue panel from middle of scene
            mid = len(lines) // 2
            dialogue_lines = [l for l in lines[mid : mid + 5] if '"' in l or l.startswith("*")]
            if dialogue_lines:
                panel_num += 1
                panels.append(
                    build_panel_entry(
                        chapter_id=chapter_id,
                        panel_num=panel_num,
                        ptype="DIALOGUE",
                        width=720,
                        height=1280,
                        env=env,
                        char_desc=char_desc,
                        chars=chars,
                        scene_summary=dialogue_lines[0][:150],
                        prompt_suffix="Shot-reverse-shot, expression close-ups",
                    )
                )

        # Add closing panel for last scene
        if scene_idx == len(scenes) - 1 and panel_num < target_panels:
            panel_num += 1
            panels.append(
                build_panel_entry(
                    chapter_id=chapter_id,
                    panel_num=panel_num,
                    ptype="CLOSING",
                    width=720,
                    height=1280,
                    env=env,
                    char_desc=char_desc,
                    chars=chars,
                    scene_summary="Final moment of the chapter. Emotional resolution, forward momentum. The journey continues.",
                    prompt_suffix="final panel, emotional resolution, forward momentum",
                )
            )

    packet = {
        "chapter_id": chapter_id,
        "episode_id": (episode_metadata or {}).get("episode_id", chapter_id),
        "title": title,
        "section_title": (episode_metadata or {}).get("title", title),
        "section_type": (episode_metadata or {}).get(
            "section_type", "interlude" if chapter_id.startswith("int") else "chapter"
        ),
        "source_markdown": (episode_metadata or {}).get("source_markdown", source_markdown),
        "key_script": (episode_metadata or {}).get("key_script"),
        "target_panel_min": (episode_metadata or {}).get("target_panel_min", max(1, target_panels - 2)),
        "target_panel_max": (episode_metadata or {}).get("target_panel_max", target_panels + 2),
        "status": (episode_metadata or {}).get("status", "packet-draft"),
        "panel_count": len(panels),
        "style_system": STYLE_SYSTEM,
        "style_bible": STYLE_BIBLE,
        "character_anchors": CHARACTERS,
        "generation_profile": deepcopy(GENERATION_PROFILE),
        "panels": panels,
    }
    return packet


def generate_panels(chapter_data, pipe=None):
    """Generate images for all panels in a chapter."""
    import torch

    ch_id = chapter_data["chapter_id"]
    out_dir = OUT_BASE / ch_id / "gen"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, p in enumerate(chapter_data["panels"]):
        out_path = out_dir / f"{p['id']}.png"
        if out_path.exists():
            print(f"  [{i+1}/{len(chapter_data['panels'])}] {p['id']} — exists, skipping")
            results.append({"id": p["id"], "path": str(out_path), "skipped": True})
            continue

        t0 = time.time()
        print(
            f"  [{i+1}/{len(chapter_data['panels'])}] {p['id']} ({p['w']}x{p['h']}) {p['type']}...", end=" ", flush=True
        )

        image = pipe(
            prompt=p["prompt"],
            width=p["w"],
            height=p["h"],
            num_inference_steps=4,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(3000 + i),
        ).images[0]

        image.save(str(out_path))
        elapsed = time.time() - t0
        size_kb = os.path.getsize(out_path) / 1024
        print(f"{elapsed:.1f}s, {size_kb:.0f}KB")
        results.append({"id": p["id"], "path": str(out_path), "elapsed": round(elapsed, 1)})
        torch.cuda.empty_cache()

    # Save manifest
    manifest = out_dir / "manifest.json"
    with open(manifest, "w") as f:
        json.dump(
            {
                "chapter": ch_id,
                "title": chapter_data["title"],
                "panels": results,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            f,
            indent=2,
        )

    return results


def get_all_chapters(chapters_dir=CHAPTERS_DIR):
    """Get ordered list of all chapter files."""
    chapters = []
    # Main chapters
    for i in range(1, 28):
        fname = f"ch{i:02d}.md"
        if (chapters_dir / fname).exists():
            chapters.append({"id": f"ch{i:02d}", "file": fname})
    # Interludes
    for f in sorted(chapters_dir.glob("interlude-*.md")):
        # interlude-01-pollys-vigil.md -> int01
        num = f.stem.split("-")[1]
        chapters.append({"id": f"int{num}", "file": f.name})
    # Rootlight
    if (chapters_dir / "ch-rootlight.md").exists():
        chapters.append({"id": "rootlight", "file": "ch-rootlight.md"})
    return chapters


def main():
    parser = argparse.ArgumentParser(description="Generate manhwa panels for the full Six Tongues Protocol")
    parser.add_argument("--chapter", "-c", help="Generate for a single chapter (e.g., ch02)")
    parser.add_argument("--start", "-s", help="Start from this chapter (e.g., ch05)")
    parser.add_argument("--prompts-only", action="store_true", help="Just write prompts, don't generate images")
    parser.add_argument("--panels", "-n", type=int, default=15, help="Target panels per chapter (default: 15)")
    parser.add_argument(
        "--source-dir", default=str(DEFAULT_SOURCE_DIR), help="Source manuscript directory (default: reader-edition)"
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    all_chapters = get_all_chapters(source_dir)
    print(f"Found {len(all_chapters)} chapters/interludes")

    # Filter
    if args.chapter:
        all_chapters = [c for c in all_chapters if c["id"] == args.chapter]
    elif args.start:
        start_idx = next((i for i, c in enumerate(all_chapters) if c["id"] == args.start), 0)
        all_chapters = all_chapters[start_idx:]

    print(f"Processing {len(all_chapters)} chapters, {args.panels} panels each")
    print(f"Estimated total: ~{len(all_chapters) * args.panels} panels")
    print()

    # Phase 1: Generate all prompts
    all_prompts = {}
    rejected_chapters = []
    for ch in all_chapters:
        text = read_chapter(ch["file"], source_dir)
        if not text:
            print(f"  SKIP {ch['id']} — file not readable")
            continue
        source_markdown = repo_relative_path(source_dir / ch["file"])
        episode_metadata = lookup_episode_metadata(chapter_id=ch["id"], source_markdown=source_markdown)
        chapter_data = create_panel_prompts_from_chapter(
            ch["id"],
            text,
            target_panels=args.panels,
            source_markdown=source_markdown,
            episode_metadata=episode_metadata,
        )

        prompt_file = PROMPTS_DIR / f"{ch['id']}_prompts.json"
        chapter_data, report = govern_packet(
            chapter_data,
            packet_path=prompt_file,
            auto_fix=True,
            rewrite_prompts=True,
        )
        all_prompts[ch["id"]] = chapter_data

        # Save prompts
        with open(prompt_file, "w") as f:
            json.dump(chapter_data, f, indent=2)
        report_file = default_report_path(prompt_file, chapter_data)
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        approval = "approved" if report["approved"] else "rejected"
        print(
            f"  {ch['id']}: {chapter_data['title'][:50]} — "
            f"{chapter_data['panel_count']} panels, score {report['score']} ({approval})"
        )
        if not report["approved"]:
            rejected_chapters.append({"chapter_id": ch["id"], "report": report_file, "errors": report["errors"]})

    total_panels = sum(d["panel_count"] for d in all_prompts.values())
    print(f"\nTotal: {total_panels} panels across {len(all_prompts)} chapters")
    print(f"Prompts saved to: {PROMPTS_DIR}")

    if rejected_chapters:
        print("\nGoverned packet failures:")
        for rejected in rejected_chapters:
            print(f"  {rejected['chapter_id']}: {rejected['report']}")
            for error in rejected["errors"]:
                print(f"    - {error}")
        raise SystemExit(1)

    if args.prompts_only:
        print("Prompts-only mode — skipping image generation.")
        return

    # Phase 2: Generate images
    print(f"\nLoading SDXL Turbo for generation...")
    import torch
    from diffusers import AutoPipelineForText2Image

    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe = pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)

    t0_total = time.time()
    for ch_id, chapter_data in all_prompts.items():
        print(f"\n{'='*50}")
        print(f"  {ch_id}: {chapter_data['title'][:50]}")
        print(f"  {chapter_data['panel_count']} panels")
        print(f"{'='*50}")
        generate_panels(chapter_data, pipe)

    elapsed_total = time.time() - t0_total
    print(f"\n{'='*50}")
    print(f"  COMPLETE: {total_panels} panels in {elapsed_total:.0f}s ({elapsed_total/60:.1f}m)")
    print(f"  Output: {OUT_BASE}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
