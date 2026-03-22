#!/usr/bin/env python3
"""Orchestrate manhwa recap video + picture research runs and emit production packets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


DEFAULT_PRODUCTION_SPEC = {
    "webtoon_episode": {
        "working_canvas_width": 1600,
        "export_width": 800,
        "target_panels": "40-60",
        "gutter_px": {
            "fast": 50,
            "normal": 140,
            "dramatic_pause": 400,
        },
        "narrative_rule": "End each episode on a cliffhanger.",
    },
    "short_video": {
        "resolution": "1080x1920",
        "fps": 30,
    },
    "youtube_landscape": {
        "resolution": "1920x1080",
        "fps": 24,
    },
    "character_consistency_stack": {
        "core": [
            "LoRA (10-30 images per character)",
            "IPAdapter (pose + face reference)",
            "ControlNet OpenPose (pose lock)",
        ],
        "orchestration": "ComfyUI",
        "models": ["Anything V5", "Counterfeit V3", "AnimePro FLUX"],
    },
    "audio_mix_targets": {
        "narration_lufs": "-18 to -22 dB LUFS",
        "music_bed_delta_vs_voice": "10-15 dB lower than narration",
        "music_lufs_hint": "-30 to -25 dB",
        "voice_clarity_eq": "cut 2-4 kHz from music bed",
        "sfx_rule": "Use brief punctual SFX, avoid continuous clutter",
    },
    "motion_strategy": {
        "default": "Ken Burns via ffmpeg zoompan",
        "hero_moments": "2.5D parallax in DaVinci Resolve",
        "ai_video_note": "Use sparingly for in-between moments; comic fidelity may drift",
    },
}

DEFAULT_SOURCE_LANES = {
    "official_platform_specs": [
        "https://webtooncanvas.zendesk.com/",
        "https://help.tapas.io/",
        "https://www.youtube.com/creators/",
    ],
    "audio_and_sfx_sources": [
        "https://freesound.org/",
        "https://www.zapsplat.com/",
        "https://pixabay.com/sound-effects/",
    ],
    "market_and_industry": [
        "https://welcon.kocca.kr/",
        "https://www.korean-culture.org/",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run research synthesis for manhwa recap video/image production.")
    parser.add_argument("--repo-root", default="C:/Users/issda/SCBE-AETHERMOORE", help="Repository root path.")
    parser.add_argument("--topic", default="Marcus Chen Protocol Handshake Arc", help="Research topic.")
    parser.add_argument("--chapter-file", help="Optional chapter/story file for scene packet generation.")
    parser.add_argument("--chapter-title", default="Episode 01", help="Chapter title for packet generation.")
    parser.add_argument(
        "--output-dir",
        default="artifacts/manhwa_video_picture_research",
        help="Output directory (absolute or relative to repo root).",
    )
    parser.add_argument(
        "--run-internet-synthesis",
        action="store_true",
        help="Run scbe-internet-workflow-synthesis baseline+tuning before packet emission.",
    )
    parser.add_argument(
        "--build-scenes",
        action="store_true",
        help="Generate storyboard/prompt packets from --chapter-file.",
    )
    return parser.parse_args()


def _run_command(command: List[str], cwd: Path) -> Dict[str, object]:
    proc = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def _resolve_output_dir(repo_root: Path, output_arg: str) -> Path:
    path = Path(output_arg)
    if path.is_absolute():
        return path
    return repo_root / path


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_root = _resolve_output_dir(repo_root, args.output_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    synthesis_results = []

    if args.run_internet_synthesis:
        synth_script = Path("C:/Users/issda/.codex/skills/scbe-internet-workflow-synthesis/scripts/synthesize_pipeline_profile.py")
        e2e_script = Path("C:/Users/issda/.codex/skills/scbe-internet-workflow-synthesis/scripts/run_e2e_pipeline.py")
        profile_path = repo_root / "training" / "internet_workflow_profile.video-picture.json"

        if synth_script.exists() and e2e_script.exists():
            synthesis_results.append(
                _run_command(
                    [
                        sys.executable,
                        str(synth_script),
                        "--repo-root",
                        str(repo_root),
                        "--output",
                        str(profile_path),
                        "--force",
                    ],
                    cwd=repo_root,
                )
            )
            synthesis_results.append(
                _run_command(
                    [
                        sys.executable,
                        str(e2e_script),
                        "--repo-root",
                        str(repo_root),
                        "--profile",
                        str(profile_path),
                    ],
                    cwd=repo_root,
                )
            )
        else:
            synthesis_results.append(
                {
                    "status": "skipped",
                    "reason": "scbe-internet-workflow-synthesis scripts not found",
                }
            )

    scene_packet_manifest = None
    if args.build_scenes:
        if not args.chapter_file:
            raise ValueError("--build-scenes requires --chapter-file")
        chapter_file = Path(args.chapter_file)
        if not chapter_file.is_absolute():
            chapter_file = (repo_root / chapter_file).resolve()

        scene_output = run_dir / "scene_packets"
        scene_script = Path(__file__).parent / "build_scene_packets.py"
        scene_cmd = [
            sys.executable,
            str(scene_script),
            "--chapter-file",
            str(chapter_file),
            "--chapter-title",
            args.chapter_title,
            "--output-dir",
            str(scene_output),
        ]
        scene_packet_manifest = _run_command(scene_cmd, cwd=repo_root)

    recap_research_queries = [
        f"{args.topic} manhwa recap pacing hooks cliffhanger examples",
        f"{args.topic} youtube recap retention strategies 2026",
        "webtoon panel gutter pacing examples 50px 400px",
        "LoRA IPAdapter ControlNet OpenPose comic character consistency workflow",
        "narration LUFS target for YouTube storytelling videos",
    ]

    lane_packet = {
        "run_id": run_id,
        "topic": args.topic,
        "source_lanes": DEFAULT_SOURCE_LANES,
        "research_queries": recap_research_queries,
        "production_spec_defaults": DEFAULT_PRODUCTION_SPEC,
        "agent_lanes": [
            {
                "lane": "lane_a_research",
                "owner": "source-scout",
                "objective": "Collect verified production + platform rules.",
            },
            {
                "lane": "lane_b_visual",
                "owner": "prompt-architect",
                "objective": "Build image/video prompt packs with consistent character tokens.",
            },
            {
                "lane": "lane_c_audio",
                "owner": "audio-engineer",
                "objective": "Set cadence and mix passes to hit narration clarity targets.",
            },
            {
                "lane": "lane_d_overwatch",
                "owner": "overseer",
                "objective": "Run QA gates: source quality, style consistency, publish readiness.",
            },
        ],
        "command_handoff": {
            "build_story_series": "python scripts/publish/build_story_video_series.py --input <story.md> --output artifacts/youtube",
            "mix_bgm": "python scripts/publish/mix_story_bgm.py --queue artifacts/youtube/story_series_upload_queue.json --music-file <track.wav>",
            "upload_queue": "python scripts/publish/post_to_youtube.py --queue artifacts/youtube/story_series_upload_queue.json --privacy unlisted",
        },
    }

    checklist = """# Manhwa Recap Production Checklist

1. Verify platform specs (WEBTOON/Tapas/YouTube) and keep references in episode notes.
2. Lock character consistency stack (LoRA + IPAdapter + ControlNet OpenPose).
3. Generate storyboard with cliffhanger ending and gutter pacing plan.
4. Mix narration first, then music 10-15 dB lower, then punctual SFX.
5. Render preview, run QA for cadence, readability, and visual continuity.
6. Publish unlisted first, review retention hooks, then schedule public release.
"""

    (run_dir / "production_checklist.md").write_text(checklist, encoding="utf-8")
    (run_dir / "research_lane_packet.json").write_text(
        json.dumps(lane_packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "run_id": run_id,
        "repo_root": str(repo_root),
        "output_dir": str(run_dir),
        "topic": args.topic,
        "build_scenes": args.build_scenes,
        "scene_packet_result": scene_packet_manifest,
        "internet_synthesis": synthesis_results,
        "files": {
            "research_lane_packet": str(run_dir / "research_lane_packet.json"),
            "production_checklist": str(run_dir / "production_checklist.md"),
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

