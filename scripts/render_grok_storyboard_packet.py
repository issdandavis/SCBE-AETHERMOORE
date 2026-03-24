#!/usr/bin/env python3
"""
Render storyboard packets through the live multi-backend image router.

This keeps Chapter/episode prompt packets usable even when the production
lane is Imagen-first instead of the older local FLUX path.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from scripts.grok_image_gen import BACKENDS, check_backends, generate, pick_best_backend
from scripts.webtoon_gen import compile_panel_prompt


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "webtoon" / "generated_router"

SUPPORTED_ASPECTS: dict[str, float] = {
    "1:1": 1.0,
    "3:4": 3 / 4,
    "4:3": 4 / 3,
    "9:16": 9 / 16,
    "16:9": 16 / 9,
}

DEFAULT_ROUTER_PROFILE: dict[str, Any] = {
    "hero_backend": "imagen-ultra",
    "batch_backend": "imagen",
    "fallback_backend": "hf",
    "output_root": str(DEFAULT_OUTPUT_ROOT),
}


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def merge_negative_prompts(*values: Any) -> str | None:
    parts: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, list):
            for item in value:
                parts.extend(piece.strip() for piece in str(item).split(",") if piece.strip())
            continue
        parts.extend(piece.strip() for piece in str(value).split(",") if piece.strip())
    merged = ", ".join(dict.fromkeys(parts))
    return merged or None


def character_negative_prompt(packet: dict[str, Any], panel: dict[str, Any]) -> str | None:
    negatives = packet.get("character_negative_anchors", {})
    if not isinstance(negatives, dict):
        return None
    parts: list[str] = []
    for character in as_list(panel.get("characters")):
        negative = negatives.get(character)
        if negative:
            parts.append(str(negative))
    return merge_negative_prompts(parts)


def nearest_supported_aspect(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "3:4"
    ratio = width / height
    return min(SUPPORTED_ASPECTS, key=lambda aspect: abs(SUPPORTED_ASPECTS[aspect] - ratio))


def load_packet(packet_path: str | Path) -> dict[str, Any]:
    path = Path(packet_path)
    return json.loads(path.read_text(encoding="utf-8"))


def merged_router_profile(packet: dict[str, Any], *, output_root: str | None = None) -> dict[str, Any]:
    profile = dict(DEFAULT_ROUTER_PROFILE)
    if isinstance(packet.get("generation_router_profile"), dict):
        for key, value in packet["generation_router_profile"].items():
            if value is not None:
                profile[key] = value
    if output_root:
        profile["output_root"] = output_root
    return profile


def render_tier(panel: dict[str, Any]) -> str:
    tier = str(panel.get("render_tier") or "batch").strip().lower()
    if tier in {"hero", "batch", "fallback"}:
        return tier
    return "batch"


def preferred_backend_for_panel(panel: dict[str, Any], profile: dict[str, Any]) -> str:
    explicit_backend = panel.get("backend")
    if explicit_backend:
        return str(explicit_backend)
    tier = render_tier(panel)
    if tier == "hero":
        return str(profile["hero_backend"])
    if tier == "fallback":
        return str(profile["fallback_backend"])
    return str(profile["batch_backend"])


def resolve_backend(
    preferred: str,
    *,
    fallback: str,
    backend_override: str | None = None,
    available_backends: dict[str, bool] | None = None,
    dry_run: bool = False,
) -> tuple[str, bool]:
    if backend_override:
        available = available_backends.get(backend_override, False) if available_backends else True
        return backend_override, available

    available_backends = available_backends or {}
    if available_backends.get(preferred):
        return preferred, True
    if available_backends.get(fallback):
        return fallback, True

    try:
        best = pick_best_backend()
        return best, available_backends.get(best, True)
    except SystemExit:
        if dry_run:
            return preferred, available_backends.get(preferred, False)
        raise


def default_output_path(packet: dict[str, Any], panel: dict[str, Any], index: int, output_root: Path) -> Path:
    chapter_id = str(packet.get("chapter_id") or Path(output_root).name)
    panel_id = str(panel.get("id") or f"{chapter_id}-p{index + 1:02d}")
    return output_root / chapter_id / f"{panel_id}.png"


def should_retry_with_fallback(exc: Exception) -> bool:
    text = str(exc)
    markers = (
        "RESOURCE_EXHAUSTED",
        "quota",
        "429",
        "rate limit",
        "too many requests",
    )
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def normalize_panel(packet: dict[str, Any], panel: dict[str, Any], index: int, output_root: Path) -> dict[str, Any]:
    normalized = dict(panel)
    normalized.setdefault("id", f"{packet.get('chapter_id', 'packet')}-p{index + 1:02d}")
    normalized.setdefault("width", normalized.pop("w", None) or 720)
    normalized.setdefault("height", normalized.pop("h", None) or 1280)
    normalized.setdefault("output", str(default_output_path(packet, normalized, index, output_root)))
    merged_negative = merge_negative_prompts(
        packet.get("default_negative_prompt"),
        character_negative_prompt(packet, normalized),
        normalized.get("negative_prompt"),
    )
    if merged_negative:
        normalized["negative_prompt"] = merged_negative
    return normalized


def build_render_jobs(
    packet_path: str | Path,
    *,
    output_root: str | None = None,
    only_ids: list[str] | None = None,
    limit: int | None = None,
    backend_override: str | None = None,
    dry_run: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    packet = load_packet(packet_path)
    root_path = Path(output_root or merged_router_profile(packet)["output_root"])
    router_profile = merged_router_profile(packet, output_root=str(root_path))
    available = check_backends()

    jobs: list[dict[str, Any]] = []
    selected_ids = set(only_ids or [])
    for index, raw_panel in enumerate(packet.get("panels", [])):
        panel = normalize_panel(packet, raw_panel, index, root_path)
        if selected_ids and panel["id"] not in selected_ids:
            continue
        prompt = str(compile_panel_prompt(panel, packet) or panel.get("prompt") or "").strip()
        preferred_backend = preferred_backend_for_panel(panel, router_profile)
        resolved_backend, backend_available = resolve_backend(
            preferred_backend,
            fallback=str(router_profile["fallback_backend"]),
            backend_override=backend_override,
            available_backends=available,
            dry_run=dry_run,
        )
        job = {
            "id": panel["id"],
            "sequence_id": panel.get("sequence_id"),
            "sequence_index": panel.get("sequence_index"),
            "sequence_title": panel.get("sequence_title"),
            "type": panel.get("type"),
            "render_tier": render_tier(panel),
            "preferred_backend": preferred_backend,
            "backend": resolved_backend,
            "backend_available": backend_available,
            "aspect": str(panel.get("aspect") or nearest_supported_aspect(int(panel["width"]), int(panel["height"]))),
            "prompt": prompt,
            "negative_prompt": panel.get("negative_prompt"),
            "output": str(panel["output"]),
            "width": int(panel["width"]),
            "height": int(panel["height"]),
            "characters": as_list(panel.get("characters")),
            "scene_summary": panel.get("scene_summary"),
            "story_job": panel.get("story_job"),
            "continuity": panel.get("continuity"),
            "environment": panel.get("environment"),
            "arc_lock": panel.get("arc_lock"),
        }
        jobs.append(job)
        if limit is not None and len(jobs) >= limit:
            break
    return packet, jobs


def run_packet(
    packet_path: str | Path,
    *,
    output_root: str | None = None,
    only_ids: list[str] | None = None,
    limit: int | None = None,
    backend_override: str | None = None,
    dry_run: bool = False,
) -> Path:
    packet, jobs = build_render_jobs(
        packet_path,
        output_root=output_root,
        only_ids=only_ids,
        limit=limit,
        backend_override=backend_override,
        dry_run=dry_run,
    )
    router_profile = merged_router_profile(packet, output_root=output_root)
    available_backends = check_backends()
    fallback_backend = str(router_profile["fallback_backend"])
    output_root_path = Path(router_profile["output_root"]) / str(packet.get("chapter_id") or "packet")
    output_root_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for job in jobs:
        result = dict(job)
        if dry_run:
            result["ok"] = True
            results.append(result)
            continue
        try:
            generate(
                backend=job["backend"],
                prompt=job["prompt"],
                output=job["output"],
                aspect=job["aspect"],
                reference=None,
                negative_prompt=job.get("negative_prompt"),
                width=job["width"],
                height=job["height"],
            )
            result["ok"] = True
        except Exception as exc:  # pragma: no cover - runtime network path
            if (
                job["backend"] != fallback_backend
                and available_backends.get(fallback_backend, False)
                and should_retry_with_fallback(exc)
            ):
                try:
                    generate(
                        backend=fallback_backend,
                        prompt=job["prompt"],
                        output=job["output"],
                        aspect=job["aspect"],
                        reference=None,
                        negative_prompt=job.get("negative_prompt"),
                        width=job["width"],
                        height=job["height"],
                    )
                    result["ok"] = True
                    result["fallback_from"] = job["backend"]
                    result["backend"] = fallback_backend
                except Exception as retry_exc:
                    result["ok"] = False
                    result["error"] = str(retry_exc)
                    result["fallback_from"] = job["backend"]
                    result["fallback_error"] = str(exc)
            else:
                result["ok"] = False
                result["error"] = str(exc)
        results.append(result)

    manifest_path = output_root_path / f"{Path(packet_path).stem}_router_manifest.json"
    manifest = {
        "packet": str(packet_path),
        "chapter_id": packet.get("chapter_id"),
        "title": packet.get("title"),
        "dry_run": dry_run,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "router_profile": router_profile,
        "panels": results,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path}")
    print(f"Panels planned: {len(results)}")
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render storyboard packets through the live grok image router.")
    parser.add_argument("--packet", required=True, help="Path to a storyboard packet JSON file.")
    parser.add_argument("--output-root", default=None, help="Optional output root override.")
    parser.add_argument(
        "--backend", choices=list(BACKENDS.keys()), default=None, help="Force one backend for all panels."
    )
    parser.add_argument("--only", action="append", default=[], help="Render only specific panel ids.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of panels.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Compile prompts and routing manifest without rendering."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_packet(
        args.packet,
        output_root=args.output_root,
        only_ids=args.only,
        limit=args.limit,
        backend_override=args.backend,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
