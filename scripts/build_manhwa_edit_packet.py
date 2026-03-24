#!/usr/bin/env python3
"""
Build a fine-edit handoff packet for rendered manhwa panels.

This does not edit pixels itself. It packages the rendered images plus the
story/prompt/continuity context so the panel can move into Photoshop, Canva,
or Adobe Express with less guesswork.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from scripts.render_grok_storyboard_packet import build_render_jobs, load_packet


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "webtoon" / "edit_packets"


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def suggest_app_lane(edit_goal: str, app_override: str, panel: dict[str, Any]) -> str:
    if app_override != "auto":
        return app_override

    goal = edit_goal.lower()
    if any(token in goal for token in ["text", "caption", "thumbnail", "layout", "promo", "poster", "cover"]):
        return "canva"
    if any(token in goal for token in ["background color", "animate", "template", "social"]):
        return "adobe-express"
    if panel.get("render_tier") == "hero":
        return "photoshop"
    return "photoshop"


def app_lane_notes(app_lane: str) -> list[str]:
    if app_lane == "canva":
        return [
            "Use Canva for text overlays, speech bubble cleanup, thumbnail composition, or promo layouts.",
            "Do not use Canva for subtle anatomy repair or painterly relighting if Photoshop is available.",
        ]
    if app_lane == "adobe-express":
        return [
            "Use Adobe Express for quick background swaps, social adaptations, and template-driven promo edits.",
            "Keep panel storytelling intact; this lane is for packaging and lightweight presentation changes.",
        ]
    return [
        "Use Photoshop for anatomy fixes, lighting cleanup, paintovers, masking, and continuity-preserving image edits.",
        "Keep the beat, silhouette, and environment logic locked while repairing the frame.",
    ]


def preserve_notes(panel: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    characters = set(as_list(panel.get("characters")))
    if "marcus" in characters:
        notes.append(
            "Preserve Marcus as early-30s Asian-American, tired, lean, dark messy hair, rumpled office-worker silhouette."
        )
    if "polly_raven" in characters:
        notes.append("Preserve Polly raven form: oversized raven, obsidian eyes, grad cap, monocle, black bowtie.")
    if "polly_human" in characters:
        notes.append(
            "Preserve Polly human form: feather-hair, wings, obsidian eyes, formal dark robes, precise posture."
        )

    environment = str(panel.get("environment") or "")
    if environment == "earth_office":
        notes.append(
            "Keep Earth office grounded: green terminal glow, dead fluorescents, late-night corporate realism."
        )
    elif environment in {"crystal_library", "crystal_corridor"}:
        notes.append("Keep crystal spaces physical and architectural, not generic fantasy fog.")
    elif environment == "aethermoor_exterior":
        notes.append("Keep the exterior impossible but coherent: operational world, not dream mush.")
    elif environment == "white_void":
        notes.append("Keep the white-out as reality erasure, not explosion smoke or abstract galaxy filler.")

    continuity = str(panel.get("continuity") or "").strip()
    if continuity:
        notes.append(f"Continuity: {continuity}")
    return notes


def merge_manifest_outputs(
    packet: dict[str, Any],
    *,
    manifest_path: str | None,
    output_root: str | None,
) -> list[dict[str, Any]]:
    packet_path = Path(packet.get("_packet_path", "packet.json"))
    _, jobs = build_render_jobs(packet_path, output_root=output_root, dry_run=True)
    jobs_by_id = {job["id"]: dict(job) for job in jobs}

    if manifest_path:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        for panel in manifest.get("panels", []):
            job = jobs_by_id.get(panel.get("id"))
            if not job:
                continue
            job.update(
                {
                    "output": panel.get("output", job.get("output")),
                    "backend": panel.get("backend", job.get("backend")),
                    "prompt": panel.get("prompt", job.get("prompt")),
                    "scene_summary": panel.get("scene_summary", job.get("scene_summary")),
                    "story_job": panel.get("story_job", job.get("story_job")),
                    "continuity": panel.get("continuity", job.get("continuity")),
                    "environment": panel.get("environment", job.get("environment")),
                    "arc_lock": panel.get("arc_lock", job.get("arc_lock")),
                }
            )
    return [jobs_by_id[job_id] for job_id in jobs_by_id]


def build_edit_packet(
    *,
    packet_path: str,
    manifest_path: str | None,
    only_ids: list[str],
    limit: int | None,
    edit_goal: str,
    app: str,
    output_dir: str | None,
) -> Path:
    packet = load_packet(packet_path)
    packet["_packet_path"] = str(Path(packet_path))
    chapter_id = str(packet.get("chapter_id") or "packet")
    merged_panels = merge_manifest_outputs(packet, manifest_path=manifest_path, output_root=None)

    selected = []
    selected_ids = set(only_ids)
    for panel in merged_panels:
        if selected_ids and panel["id"] not in selected_ids:
            continue
        selected.append(panel)
        if limit is not None and len(selected) >= limit:
            break

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    packet_dir = Path(output_dir or (DEFAULT_OUTPUT_ROOT / chapter_id / f"{timestamp}-fine-edit"))
    packet_dir.mkdir(parents=True, exist_ok=True)

    edit_panels: list[dict[str, Any]] = []
    for panel in selected:
        app_lane = suggest_app_lane(edit_goal, app, panel)
        edit_panels.append(
            {
                "id": panel["id"],
                "image_path": panel.get("output"),
                "sequence_id": panel.get("sequence_id"),
                "sequence_title": panel.get("sequence_title"),
                "type": panel.get("type"),
                "render_tier": panel.get("render_tier"),
                "backend": panel.get("backend"),
                "scene_summary": panel.get("scene_summary"),
                "story_job": panel.get("story_job"),
                "prompt": panel.get("prompt"),
                "recommended_app": app_lane,
                "app_notes": app_lane_notes(app_lane),
                "edit_goal": edit_goal,
                "preserve": preserve_notes(panel),
            }
        )

    panel_apps = [panel["recommended_app"] for panel in edit_panels]
    resolved_default_app = app if app != "auto" else (panel_apps[0] if panel_apps else "photoshop")
    output = {
        "chapter_id": chapter_id,
        "packet": packet_path,
        "manifest": manifest_path,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "edit_goal": edit_goal,
        "recommended_default_app": resolved_default_app,
        "panel_count": len(edit_panels),
        "panels": edit_panels,
    }

    json_path = packet_dir / "edit_packet.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    markdown_lines = [
        f"# {chapter_id} Fine Edit Packet",
        "",
        f"- Packet: `{packet_path}`",
        f"- Manifest: `{manifest_path or 'none'}`",
        f"- Edit goal: `{edit_goal}`",
        f"- Panels: `{len(edit_panels)}`",
        "",
    ]
    for panel in edit_panels:
        markdown_lines.extend(
            [
                f"## {panel['id']}",
                f"- Image: `{panel['image_path']}`",
                f"- App: `{panel['recommended_app']}`",
                f"- Sequence: `{panel.get('sequence_title')}`",
                f"- Beat: `{panel.get('scene_summary')}`",
                f"- Story job: `{panel.get('story_job')}`",
                f"- Prompt: `{panel.get('prompt')}`",
                "- App notes:",
                *[f"  - {note}" for note in panel["app_notes"]],
                "- Preserve:",
                *[f"  - {note}" for note in panel["preserve"]],
                "",
            ]
        )
    markdown_path = packet_dir / "edit_packet.md"
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    html_lines = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Fine Edit Packet</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;} .card{border:1px solid #ccc;padding:16px;margin:0 0 20px;} img{max-width:320px;display:block;margin:0 0 12px;}</style>",
        "</head><body>",
        f"<h1>{chapter_id} Fine Edit Packet</h1>",
        f"<p>Edit goal: {edit_goal}</p>",
    ]
    for panel in edit_panels:
        html_lines.append("<div class='card'>")
        html_lines.append(f"<h2>{panel['id']}</h2>")
        image_path = panel.get("image_path")
        if image_path and Path(image_path).exists():
            html_lines.append(f"<img src='{Path(image_path).resolve().as_uri()}' alt='{panel['id']}'>")
        html_lines.append(f"<p><strong>App:</strong> {panel['recommended_app']}</p>")
        html_lines.append(f"<p><strong>Beat:</strong> {panel.get('scene_summary') or ''}</p>")
        html_lines.append(f"<p><strong>Story job:</strong> {panel.get('story_job') or ''}</p>")
        html_lines.append("<ul>")
        for note in panel["app_notes"]:
            html_lines.append(f"<li>{note}</li>")
        for note in panel["preserve"]:
            html_lines.append(f"<li>{note}</li>")
        html_lines.append("</ul></div>")
    html_lines.append("</body></html>")
    html_path = packet_dir / "contact_sheet.html"
    html_path.write_text("\n".join(html_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    print(f"HTML: {html_path}")
    return json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a fine-edit handoff packet for rendered manhwa panels.")
    parser.add_argument("--packet", required=True, help="Storyboard packet JSON path.")
    parser.add_argument("--manifest", default=None, help="Optional router manifest path for actual rendered outputs.")
    parser.add_argument("--only", action="append", default=[], help="Select specific panel ids.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of panels in the packet.")
    parser.add_argument(
        "--edit-goal",
        default="Fine edit anatomy, lighting, and continuity without changing the story beat.",
        help="Human edit goal written into the handoff packet.",
    )
    parser.add_argument(
        "--app",
        choices=["auto", "photoshop", "canva", "adobe-express"],
        default="auto",
        help="Force a specific app lane or let the script recommend one.",
    )
    parser.add_argument("--output-dir", default=None, help="Optional output directory for the edit packet.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_edit_packet(
        packet_path=args.packet,
        manifest_path=args.manifest,
        only_ids=args.only,
        limit=args.limit,
        edit_goal=args.edit_goal,
        app=args.app,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
