#!/usr/bin/env python3
"""
Render all available webtoon prompt packets through the live router.

Defaults to the current packet coverage in artifacts/webtoon/panel_prompts,
preferring the beat-expanded Chapter 1 v4 packet over the older compact packet.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from scripts.render_grok_storyboard_packet import build_render_jobs, run_packet
from scripts.webtoon_quality_gate import govern_packet, lookup_episode_metadata


ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "artifacts" / "webtoon" / "panel_prompts"
SERIES_MANIFEST = ROOT / "artifacts" / "webtoon" / "series_storyboard_manifest.json"
READER_EDITION_DIR = ROOT / "content" / "book" / "reader-edition"


def normalize_title_token(text: str | None) -> str:
    value = str(text or "").strip().lower()
    value = value.replace("—", "-")
    value = value.replace(":", " ")
    parts = value.split()
    if len(parts) >= 3 and parts[0] == "chapter" and parts[1].isdigit():
        parts = parts[2:]
    elif len(parts) >= 2 and parts[0] == "interlude":
        parts = parts[1:]
    return " ".join(parts)


def title_matched_episode(packet_title: str | None) -> dict[str, Any] | None:
    if not SERIES_MANIFEST.exists():
        return None
    token = normalize_title_token(packet_title)
    if not token:
        return None
    manifest = load_json(SERIES_MANIFEST)
    for episode in manifest.get("episodes", []):
        if normalize_title_token(episode.get("title")) == token:
            return episode
    return None


def direct_reader_source(chapter_id: str) -> str | None:
    candidate = READER_EDITION_DIR / f"{chapter_id}.md"
    if candidate.exists():
        return str(candidate.relative_to(ROOT).as_posix())
    return None


def resolve_path(path_value: str | None, packet_path: Path | None) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    root_candidate = (ROOT / candidate).resolve()
    if root_candidate.exists():
        return root_candidate
    if packet_path is not None:
        packet_candidate = (packet_path.parent / candidate).resolve()
        if packet_candidate.exists():
            return packet_candidate
        return packet_candidate
    return root_candidate


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def preferred_prompt_paths() -> list[Path]:
    packet_paths: list[Path] = []
    for path in PROMPTS_DIR.glob("*.json"):
        name = path.name
        if name.endswith("_quality_report.json"):
            continue
        if name.endswith("_merged.json"):
            continue
        if name == "ch01_prompts.json" and (PROMPTS_DIR / "ch01_prompts_v4.json").exists():
            continue
        if name == "ch01_prompts_v4.json":
            packet_paths.append(path)
            continue
        if name.endswith("_prompts.json"):
            packet_paths.append(path)
    return packet_paths


def episode_order_map() -> dict[str, int]:
    if not SERIES_MANIFEST.exists():
        return {}
    data = load_json(SERIES_MANIFEST)
    order: dict[str, int] = {}
    for index, episode in enumerate(data.get("episodes", []), start=1):
        title = str(episode.get("title") or "").strip()
        if title:
            order[title] = index
    return order


def packet_sort_key(path: Path, title_order: dict[str, int]) -> tuple[int, str]:
    try:
        title = str(load_json(path).get("title") or "").strip()
    except Exception:
        title = ""
    return (title_order.get(title, 10_000), path.name)


def ordered_packet_paths() -> list[Path]:
    title_order = episode_order_map()
    return sorted(preferred_prompt_paths(), key=lambda path: packet_sort_key(path, title_order))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render all available webtoon prompt packets through the live router.")
    parser.add_argument(
        "--backend",
        choices=["imagen", "imagen-ultra", "hf", "zimage"],
        default=None,
        help="Force one backend for every packet.",
    )
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "artifacts" / "webtoon" / "generated_router_full_book"),
        help="Output root for generated images and manifests.",
    )
    parser.add_argument("--start-at", default=None, help="Start at this packet stem or chapter id.")
    parser.add_argument(
        "--limit-packets", type=int, default=None, help="Render only the next N packets after filtering."
    )
    parser.add_argument("--dry-run", action="store_true", help="Build manifests without rendering images.")
    parser.add_argument(
        "--no-skip-existing", action="store_true", help="Do not skip panels that already exist on disk."
    )
    return parser.parse_args()


def filter_start(paths: list[Path], start_at: str | None) -> list[Path]:
    if not start_at:
        return paths
    token = start_at.strip().lower()
    for index, path in enumerate(paths):
        stem = path.stem.lower()
        try:
            chapter_id = str(load_json(path).get("chapter_id") or "").strip().lower()
        except Exception:
            chapter_id = ""
        if token in {stem, chapter_id}:
            return paths[index:]
    return paths


def verification_root(output_root: Path) -> Path:
    return output_root / "_verification"


def governed_packets_root(output_root: Path) -> Path:
    return output_root / "_governed_packets"


def packet_verification_dir(output_root: Path, chapter_id: str) -> Path:
    return verification_root(output_root) / chapter_id


def source_stage(packet: dict[str, Any], packet_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    chapter_id = str(packet.get("chapter_id") or packet_path.stem)
    episode_metadata = lookup_episode_metadata(
        chapter_id=chapter_id,
        source_markdown=packet.get("source_markdown"),
    )
    title_match = title_matched_episode(packet.get("title"))
    resolved_packet = dict(packet)
    if episode_metadata:
        resolved_packet.setdefault("episode_id", episode_metadata.get("episode_id"))
        resolved_packet.setdefault("source_markdown", episode_metadata.get("source_markdown"))
        resolved_packet.setdefault("key_script", episode_metadata.get("key_script"))
        resolved_packet.setdefault("section_title", episode_metadata.get("title"))
        resolved_packet.setdefault("section_type", episode_metadata.get("section_type"))
        resolved_packet.setdefault("target_panel_min", episode_metadata.get("target_panel_min"))
        resolved_packet.setdefault("target_panel_max", episode_metadata.get("target_panel_max"))
    else:
        direct_source = direct_reader_source(chapter_id)
        if direct_source:
            resolved_packet.setdefault("source_markdown", direct_source)
        if title_match:
            resolved_packet.setdefault("episode_id", title_match.get("episode_id"))
            resolved_packet.setdefault("key_script", title_match.get("key_script"))
            resolved_packet.setdefault("section_type", title_match.get("section_type"))
            resolved_packet.setdefault("target_panel_min", title_match.get("target_panel_min"))
            resolved_packet.setdefault("target_panel_max", title_match.get("target_panel_max"))

    source_markdown = resolved_packet.get("source_markdown")
    key_script = resolved_packet.get("key_script")
    source_path = resolve_path(str(source_markdown) if source_markdown else None, packet_path)
    key_script_path = resolve_path(str(key_script) if key_script else None, packet_path)

    errors: list[str] = []
    warnings: list[str] = []
    if not resolved_packet.get("episode_id"):
        warnings.append("episode metadata not resolved from storyboard manifest")
    if not source_markdown:
        errors.append("source_markdown could not be resolved")
    elif source_path is None or not source_path.exists():
        errors.append("source_markdown is not readable")
    if not key_script:
        errors.append("key_script could not be resolved")
    elif key_script_path is None or not key_script_path.exists():
        errors.append("key_script is not readable")

    report = {
        "chapter_id": chapter_id,
        "episode_id": resolved_packet.get("episode_id"),
        "packet_path": str(packet_path),
        "source_markdown": source_markdown,
        "source_markdown_path": str(source_path) if source_path else None,
        "key_script": key_script,
        "key_script_path": str(key_script_path) if key_script_path else None,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return resolved_packet, report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def stage_artifact_paths(output_root: Path, packet_path: Path, chapter_id: str) -> dict[str, Path]:
    verify_dir = packet_verification_dir(output_root, chapter_id)
    return {
        "source_report": verify_dir / f"{packet_path.stem}_source_verification.json",
        "prompt_report": verify_dir / f"{packet_path.stem}_quality_report.json",
        "governed_packet": governed_packets_root(output_root) / packet_path.name,
    }


def process_packet(
    packet_path: Path,
    *,
    output_root: Path,
    backend_override: str | None,
    dry_run: bool,
    no_skip_existing: bool,
) -> dict[str, Any]:
    packet = load_json(packet_path)
    chapter_id = str(packet.get("chapter_id") or packet_path.stem)
    title = str(packet.get("title") or chapter_id)
    print(f"[render] {chapter_id} :: {title}")

    summary_entry: dict[str, Any] = {
        "packet": str(packet_path),
        "chapter_id": chapter_id,
        "title": title,
        "status": "pending",
    }

    source_packet, source_report = source_stage(packet, packet_path)
    artifacts = stage_artifact_paths(output_root, packet_path, chapter_id)
    write_json(artifacts["source_report"], source_report)
    summary_entry["source_verification"] = {
        "report": str(artifacts["source_report"]),
        "ok": source_report["ok"],
        "errors": source_report["errors"],
        "warnings": source_report["warnings"],
    }
    if not source_report["ok"]:
        summary_entry["status"] = "blocked-source"
        return summary_entry

    governed_packet, prompt_report = govern_packet(
        source_packet,
        packet_path=packet_path,
        auto_fix=True,
        rewrite_prompts=True,
    )
    write_json(artifacts["prompt_report"], prompt_report)
    summary_entry["prompt_governance"] = {
        "report": str(artifacts["prompt_report"]),
        "approved": prompt_report["approved"],
        "score": prompt_report["score"],
        "errors": prompt_report["errors"],
        "warnings": prompt_report["warnings"],
        "auto_fixes": prompt_report["auto_fixes"],
    }
    if not prompt_report["approved"]:
        summary_entry["status"] = "blocked-prompt"
        return summary_entry

    write_json(artifacts["governed_packet"], governed_packet)
    summary_entry["governed_packet"] = str(artifacts["governed_packet"])

    selected_ids: list[str] | None = None
    skipped_existing = 0
    total_jobs = 0
    if not no_skip_existing and not dry_run:
        _, jobs = build_render_jobs(
            artifacts["governed_packet"],
            output_root=str(output_root),
            backend_override=backend_override,
            dry_run=True,
        )
        total_jobs = len(jobs)
        missing = [job["id"] for job in jobs if not Path(job["output"]).exists()]
        skipped_existing = total_jobs - len(missing)
        if not missing:
            print(f"  skip: all {total_jobs} panels already exist")
            summary_entry["render"] = {
                "status": "skipped-complete",
                "total_jobs": total_jobs,
                "skipped_existing": skipped_existing,
            }
            summary_entry["status"] = "skipped-complete"
            return summary_entry
        selected_ids = missing

    manifest_path = run_packet(
        artifacts["governed_packet"],
        output_root=str(output_root),
        only_ids=selected_ids,
        backend_override=backend_override,
        dry_run=dry_run,
    )
    manifest = load_json(manifest_path)
    ok_count = sum(1 for panel in manifest.get("panels", []) if panel.get("ok"))
    fail_count = sum(1 for panel in manifest.get("panels", []) if not panel.get("ok"))
    summary_entry["render"] = {
        "manifest": str(manifest_path),
        "rendered_jobs": len(manifest.get("panels", [])),
        "ok": ok_count,
        "failed": fail_count,
        "skipped_existing": skipped_existing,
    }
    summary_entry["status"] = "done" if fail_count == 0 else "partial-fail"
    return summary_entry


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    packet_paths = filter_start(ordered_packet_paths(), args.start_at)
    if args.limit_packets is not None:
        packet_paths = packet_paths[: args.limit_packets]

    summary: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "backend_override": args.backend,
        "output_root": str(output_root),
        "dry_run": args.dry_run,
        "pipeline": ["verify-source", "verify-prompt", "generate"],
        "packets": [],
    }

    for packet_path in packet_paths:
        summary["packets"].append(
            process_packet(
                packet_path,
                output_root=output_root,
                backend_override=args.backend,
                dry_run=args.dry_run,
                no_skip_existing=args.no_skip_existing,
            )
        )

    summary_path = output_root / "full_book_render_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[summary] {summary_path}")


if __name__ == "__main__":
    main()
